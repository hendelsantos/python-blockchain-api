"""Implementação em memória de uma blockchain com proof-of-work."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from threading import RLock

from blockchain_api.domain.models import Block, Transaction


class InvalidTransactionError(ValueError):
    """A transação não atende às regras mínimas do domínio."""


class Blockchain:
    """Gerencia blocos, transações pendentes e mineração.

    O estado é protegido por lock para que requisições concorrentes não
    produzam dois blocos para a mesma posição da cadeia.
    """

    def __init__(self, difficulty: int = 3, mining_reward: Decimal = Decimal("1")) -> None:
        if not 1 <= difficulty <= 6:
            raise ValueError("difficulty deve estar entre 1 e 6")
        if mining_reward <= 0:
            raise ValueError("mining_reward deve ser maior que zero")

        self.difficulty = difficulty
        self.mining_reward = mining_reward
        self._lock = RLock()
        self._pending_transactions: list[Transaction] = []
        self._chain: list[Block] = [self._create_genesis_block()]

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def _create_genesis_block(self) -> Block:
        return Block(
            index=0,
            timestamp="2026-01-01T00:00:00+00:00",
            transactions=(),
            previous_hash="0" * 64,
        )

    @property
    def chain(self) -> tuple[Block, ...]:
        with self._lock:
            return tuple(self._chain)

    @property
    def pending_transactions(self) -> tuple[Transaction, ...]:
        with self._lock:
            return tuple(self._pending_transactions)

    def add_transaction(self, sender: str, recipient: str, amount: Decimal) -> Transaction:
        sender = sender.strip()
        recipient = recipient.strip()
        if not sender or not recipient:
            raise InvalidTransactionError("remetente e destinatário são obrigatórios")
        if sender == recipient:
            raise InvalidTransactionError("remetente e destinatário devem ser diferentes")
        if amount <= 0:
            raise InvalidTransactionError("o valor deve ser maior que zero")

        transaction = Transaction(sender=sender, recipient=recipient, amount=amount)
        with self._lock:
            self._pending_transactions.append(transaction)
        return transaction

    def mine_pending_transactions(self, miner: str) -> Block:
        miner = miner.strip()
        if not miner:
            raise InvalidTransactionError("o identificador do minerador é obrigatório")

        with self._lock:
            reward = Transaction(sender="NETWORK", recipient=miner, amount=self.mining_reward)
            block = Block(
                index=len(self._chain),
                timestamp=self._now(),
                transactions=(*self._pending_transactions, reward),
                previous_hash=self._chain[-1].calculate_hash(),
            )
            mined_block = self._proof_of_work(block)
            self._chain.append(mined_block)
            self._pending_transactions.clear()
            return mined_block

    def _proof_of_work(self, block: Block) -> Block:
        target = "0" * self.difficulty
        candidate = block
        while not candidate.calculate_hash().startswith(target):
            candidate = replace(candidate, nonce=candidate.nonce + 1)
        return candidate

    def is_valid(self) -> bool:
        with self._lock:
            for position, current in enumerate(self._chain[1:], start=1):
                previous = self._chain[position - 1]
                if current.index != position:
                    return False
                if current.previous_hash != previous.calculate_hash():
                    return False
                if not current.calculate_hash().startswith("0" * self.difficulty):
                    return False
            return True
