"""Implementação de uma blockchain persistível com proof-of-work."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from threading import RLock

from blockchain_api.core.repository import BlockchainRepository, InMemoryBlockchainRepository
from blockchain_api.domain.models import Block, Transaction


class InvalidTransactionError(ValueError):
    """A transação não atende às regras mínimas do domínio."""


class InsufficientFundsError(InvalidTransactionError):
    """A carteira não possui saldo disponível para a transação."""


class Blockchain:
    """Gerencia blocos, transações pendentes e mineração.

    O estado é protegido por lock para que requisições concorrentes não
    produzam dois blocos para a mesma posição da cadeia.
    """

    def __init__(
        self,
        difficulty: int = 3,
        mining_reward: Decimal = Decimal("1"),
        repository: BlockchainRepository | None = None,
    ) -> None:
        if not 1 <= difficulty <= 6:
            raise ValueError("difficulty deve estar entre 1 e 6")
        if mining_reward <= 0:
            raise ValueError("mining_reward deve ser maior que zero")

        self.difficulty = difficulty
        self.mining_reward = mining_reward
        self._repository = repository or InMemoryBlockchainRepository()
        self._lock = RLock()
        self._pending_transactions = self._repository.load_pending_transactions()
        self._chain = self._repository.load_chain()
        if not self._chain:
            genesis = self._create_genesis_block()
            self._repository.save_genesis(genesis)
            self._chain = [genesis]
        if not self.is_valid():
            raise ValueError("a blockchain persistida está corrompida")

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
        if sender.upper() == "NETWORK":
            raise InvalidTransactionError("NETWORK é um remetente reservado")
        if amount <= 0:
            raise InvalidTransactionError("o valor deve ser maior que zero")

        with self._lock:
            available = self.get_balance(sender)["available"]
            if amount > available:
                raise InsufficientFundsError(
                    f"saldo insuficiente: disponível {available}, solicitado {amount}"
                )
            transaction = Transaction(sender=sender, recipient=recipient, amount=amount)
            self._repository.add_pending_transaction(transaction)
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
            self._repository.commit_mined_block(mined_block)
            self._chain.append(mined_block)
            self._pending_transactions.clear()
            return mined_block

    def get_balance(self, address: str) -> dict[str, Decimal]:
        """Retorna os saldos confirmado e disponível de uma carteira."""

        address = address.strip()
        if not address:
            raise InvalidTransactionError("o endereço da carteira é obrigatório")

        confirmed = Decimal("0")
        for block in self._chain:
            for transaction in block.transactions:
                if transaction.recipient == address:
                    confirmed += transaction.amount
                if transaction.sender == address:
                    confirmed -= transaction.amount

        pending_outgoing = sum(
            (
                transaction.amount
                for transaction in self._pending_transactions
                if transaction.sender == address
            ),
            start=Decimal("0"),
        )
        return {
            "confirmed": confirmed,
            "available": confirmed - pending_outgoing,
            "pending_outgoing": pending_outgoing,
        }

    def list_wallets(self) -> list[dict[str, object]]:
        """Lista endereços conhecidos e seus saldos, exceto a conta da rede."""

        addresses: set[str] = set()
        for block in self._chain:
            for transaction in block.transactions:
                if transaction.sender != "NETWORK":
                    addresses.add(transaction.sender)
                if transaction.recipient != "NETWORK":
                    addresses.add(transaction.recipient)
        for transaction in self._pending_transactions:
            addresses.update((transaction.sender, transaction.recipient))

        return [{"address": address, **self.get_balance(address)} for address in sorted(addresses)]

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
