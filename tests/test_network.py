import asyncio

import httpx
import pytest

from blockchain_api.core.blockchain import Blockchain
from blockchain_api.core.network import NodeManager, normalize_peer_url


def test_normalizes_and_registers_peers() -> None:
    manager = NodeManager(node_id="node-test")

    peers = manager.register(["http://node2:8000/", "https://example.com"])

    assert peers == ("http://node2:8000", "https://example.com")
    assert manager.node_id == "node-test"

    with pytest.raises(ValueError):
        normalize_peer_url("ftp://invalid.example")


def test_consensus_adopts_a_longer_valid_chain() -> None:
    local = Blockchain(difficulty=1)
    remote = Blockchain(difficulty=1)
    remote.mine_pending_transactions("miner-a")
    remote.mine_pending_transactions("miner-b")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "http://node2.test/api/v1/nodes/chain"
        assert request.headers["X-Node-ID"] == "node-1"
        return httpx.Response(
            200,
            json={
                "length": len(remote.chain),
                "chain": [block.to_dict() for block in remote.chain],
            },
        )

    manager = NodeManager(
        node_id="node-1",
        initial_peers=["http://node2.test"],
        shared_secret="test-network-secret",
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(manager.resolve_conflicts(local))

    assert result["replaced"] is True
    assert result["source"] == "http://node2.test"
    assert len(local.chain) == 3
    assert local.is_valid()


def test_consensus_ignores_unreachable_peer() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    blockchain = Blockchain(difficulty=1)
    manager = NodeManager(
        initial_peers=["http://offline.test"],
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(manager.resolve_conflicts(blockchain))

    assert result["replaced"] is False
    assert result["errors"] == {"http://offline.test": "ConnectError"}


def test_hmac_signature_rejects_tampering_and_expiration() -> None:
    manager = NodeManager(
        node_id="node-1",
        initial_peers=[],
        shared_secret="test-network-secret",
    )
    path = "/api/v1/nodes/chain"
    headers = manager.signed_headers("GET", path, timestamp=1_000)

    assert manager.verify_signature(
        node_id=headers["X-Node-ID"],
        timestamp=headers["X-Node-Timestamp"],
        signature=headers["X-Node-Signature"],
        method="GET",
        path=path,
        now=1_010,
    )
    assert not manager.verify_signature(
        node_id=headers["X-Node-ID"],
        timestamp=headers["X-Node-Timestamp"],
        signature=headers["X-Node-Signature"],
        method="POST",
        path=path,
        now=1_010,
    )
    assert not manager.verify_signature(
        node_id=headers["X-Node-ID"],
        timestamp=headers["X-Node-Timestamp"],
        signature=headers["X-Node-Signature"],
        method="GET",
        path=path,
        now=1_031,
    )


def test_discovers_peers_announced_by_a_seed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "http://node2.test/api/v1/nodes/peers"
        return httpx.Response(
            200,
            json={
                "node_id": "node-2",
                "peers": ["http://node1.test", "http://node3.test"],
            },
        )

    manager = NodeManager(
        node_id="node-1",
        node_url="http://node1.test",
        initial_peers=["http://node2.test"],
        shared_secret="test-network-secret",
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(manager.discover_peers())

    assert result["discovered"] == ["http://node3.test"]
    assert manager.peers == ("http://node2.test", "http://node3.test")
