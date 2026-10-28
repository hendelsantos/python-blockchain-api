"""Modelos imutáveis que formam a blockchain."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class Transaction:
    """Transferência registrada em um bloco."""

    sender: str
    recipient: str
    amount: Decimal

    def to_dict(self) -> dict[str, str]:
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": str(self.amount),
        }


@dataclass(frozen=True, slots=True)
class Block:
    """Bloco com conteúdo determinístico e hash SHA-256."""

    index: int
    timestamp: str
    transactions: tuple[Transaction, ...]
    previous_hash: str
    nonce: int = 0

    def calculate_hash(self) -> str:
        payload = json.dumps(
            self.to_dict(include_hash=False),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self, *, include_hash: bool = True) -> dict[str, object]:
        data: dict[str, object] = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [transaction.to_dict() for transaction in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        if include_hash:
            data["hash"] = self.calculate_hash()
        return data
