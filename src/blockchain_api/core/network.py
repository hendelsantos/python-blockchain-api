"""Descoberta de peers e consenso pela cadeia válida mais longa."""

from __future__ import annotations

import asyncio
import os
import socket
from decimal import Decimal
from urllib.parse import urlparse

import httpx

from blockchain_api.core.blockchain import Blockchain
from blockchain_api.domain.models import Block, Transaction


def normalize_peer_url(url: str) -> str:
    normalized = url.strip().rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("a URL do peer deve usar http ou https")
    if parsed.username or parsed.password:
        raise ValueError("credenciais não são permitidas na URL do peer")
    return normalized


def deserialize_chain(data: list[dict[str, object]]) -> list[Block]:
    blocks: list[Block] = []
    for raw_block in data:
        raw_transactions = raw_block.get("transactions")
        if not isinstance(raw_transactions, list):
            raise ValueError("lista de transações inválida")
        transactions = tuple(
            Transaction(
                sender=str(transaction["sender"]),
                recipient=str(transaction["recipient"]),
                amount=Decimal(str(transaction["amount"])),
                nonce=(int(transaction["nonce"]) if transaction.get("nonce") is not None else None),
                public_key=(
                    str(transaction["public_key"])
                    if transaction.get("public_key") is not None
                    else None
                ),
                signature=(
                    str(transaction["signature"])
                    if transaction.get("signature") is not None
                    else None
                ),
            )
            for transaction in raw_transactions
            if isinstance(transaction, dict)
        )
        blocks.append(
            Block(
                index=int(raw_block["index"]),
                timestamp=str(raw_block["timestamp"]),
                transactions=transactions,
                previous_hash=str(raw_block["previous_hash"]),
                nonce=int(raw_block["nonce"]),
            )
        )
    return blocks


class NodeManager:
    def __init__(
        self,
        *,
        node_id: str | None = None,
        initial_peers: list[str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.node_id = node_id or os.getenv("NODE_ID") or socket.gethostname()
        configured_peers = initial_peers or [
            peer for peer in os.getenv("PEER_URLS", "").split(",") if peer.strip()
        ]
        self._peers = {normalize_peer_url(peer) for peer in configured_peers}
        self._transport = transport

    @property
    def peers(self) -> tuple[str, ...]:
        return tuple(sorted(self._peers))

    def register(self, urls: list[str]) -> tuple[str, ...]:
        self._peers.update(normalize_peer_url(url) for url in urls)
        return self.peers

    async def _fetch_chain(self, client: httpx.AsyncClient, peer: str) -> tuple[str, list[Block]]:
        response = await client.get(f"{peer}/api/v1/chain")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload.get("chain"), list):
            raise ValueError("resposta do peer não contém uma cadeia")
        return peer, deserialize_chain(payload["chain"])

    async def resolve_conflicts(self, blockchain: Blockchain) -> dict[str, object]:
        if not self._peers:
            return {
                "replaced": False,
                "length": len(blockchain.chain),
                "source": None,
                "errors": {},
            }

        errors: dict[str, str] = {}
        best_chain: list[Block] | None = None
        source: str | None = None
        async with httpx.AsyncClient(timeout=4, transport=self._transport) as client:
            results = await asyncio.gather(
                *(self._fetch_chain(client, peer) for peer in self.peers),
                return_exceptions=True,
            )

        for peer, result in zip(self.peers, results, strict=True):
            if isinstance(result, BaseException):
                errors[peer] = type(result).__name__
                continue
            result_peer, candidate = result
            if (
                len(candidate) > len(blockchain.chain)
                and (best_chain is None or len(candidate) > len(best_chain))
                and blockchain.validate_chain(candidate)
            ):
                best_chain = candidate
                source = result_peer

        replaced = bool(best_chain and blockchain.replace_chain(best_chain))
        return {
            "replaced": replaced,
            "length": len(blockchain.chain),
            "source": source if replaced else None,
            "errors": errors,
        }
