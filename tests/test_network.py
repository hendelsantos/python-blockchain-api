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
        assert request.url == "http://node2.test/api/v1/chain"
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
