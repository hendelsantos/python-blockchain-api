"""Descoberta de peers e consenso pela cadeia válida mais longa."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import socket
import time
from decimal import Decimal
from urllib.parse import urlparse

import httpx

from blockchain_api.core.blockchain import Blockchain
from blockchain_api.domain.models import Block, Transaction

NODE_SIGNATURE_TTL_SECONDS = 30


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
        node_url: str | None = None,
        initial_peers: list[str] | None = None,
        shared_secret: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.node_id = node_id or os.getenv("NODE_ID") or socket.gethostname()
        configured_url = node_url if node_url is not None else os.getenv("NODE_URL")
        self.node_url = normalize_peer_url(configured_url) if configured_url else None
        self.shared_secret = (
            shared_secret if shared_secret is not None else os.getenv("NODE_SHARED_SECRET", "")
        )
        configured_peers = (
            initial_peers
            if initial_peers is not None
            else [peer for peer in os.getenv("PEER_URLS", "").split(",") if peer.strip()]
        )
        self._peers: set[str] = set()
        self.register(configured_peers)
        self._transport = transport

    @property
    def peers(self) -> tuple[str, ...]:
        return tuple(sorted(self._peers))

    @property
    def authentication_enabled(self) -> bool:
        return bool(self.shared_secret)

    def register(self, urls: list[str]) -> tuple[str, ...]:
        normalized = {normalize_peer_url(url) for url in urls}
        if self.node_url:
            normalized.discard(self.node_url)
        self._peers.update(normalized)
        return self.peers

    @staticmethod
    def _signature_payload(node_id: str, timestamp: str, method: str, path: str) -> bytes:
        return f"{node_id}:{timestamp}:{method.upper()}:{path}".encode()

    def signed_headers(
        self,
        method: str,
        path: str,
        *,
        timestamp: int | None = None,
    ) -> dict[str, str]:
        if not self.authentication_enabled:
            return {}
        timestamp_value = str(timestamp if timestamp is not None else int(time.time()))
        signature = hmac.new(
            self.shared_secret.encode(),
            self._signature_payload(self.node_id, timestamp_value, method, path),
            hashlib.sha256,
        ).hexdigest()
        return {
            "X-Node-ID": self.node_id,
            "X-Node-Timestamp": timestamp_value,
            "X-Node-Signature": signature,
        }

    def verify_signature(
        self,
        *,
        node_id: str | None,
        timestamp: str | None,
        signature: str | None,
        method: str,
        path: str,
        now: int | None = None,
    ) -> bool:
        if not self.authentication_enabled:
            return True
        if not node_id or not timestamp or not signature:
            return False
        try:
            timestamp_number = int(timestamp)
        except ValueError:
            return False
        current_time = now if now is not None else int(time.time())
        if abs(current_time - timestamp_number) > NODE_SIGNATURE_TTL_SECONDS:
            return False
        expected = hmac.new(
            self.shared_secret.encode(),
            self._signature_payload(node_id, timestamp, method, path),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def _fetch_chain(self, client: httpx.AsyncClient, peer: str) -> tuple[str, list[Block]]:
        path = "/api/v1/nodes/chain"
        response = await client.get(
            f"{peer}{path}",
            headers=self.signed_headers("GET", path),
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload.get("chain"), list):
            raise ValueError("resposta do peer não contém uma cadeia")
        return peer, deserialize_chain(payload["chain"])

    async def _fetch_peers(self, client: httpx.AsyncClient, peer: str) -> tuple[str, list[str]]:
        path = "/api/v1/nodes/peers"
        response = await client.get(
            f"{peer}{path}",
            headers=self.signed_headers("GET", path),
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload.get("peers"), list):
            raise ValueError("resposta do peer não contém uma lista de peers")
        return peer, [str(url) for url in payload["peers"]]

    async def discover_peers(self) -> dict[str, object]:
        seeds = self.peers
        if not seeds:
            return {"discovered": [], "peers": [], "errors": {}}

        errors: dict[str, str] = {}
        discovered: set[str] = set()
        async with httpx.AsyncClient(timeout=4, transport=self._transport) as client:
            results = await asyncio.gather(
                *(self._fetch_peers(client, peer) for peer in seeds),
                return_exceptions=True,
            )

        for peer, result in zip(seeds, results, strict=True):
            if isinstance(result, BaseException):
                errors[peer] = type(result).__name__
                continue
            _, urls = result
            before = set(self.peers)
            self.register(urls)
            discovered.update(set(self.peers) - before)

        return {
            "discovered": sorted(discovered),
            "peers": list(self.peers),
            "errors": errors,
        }

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
