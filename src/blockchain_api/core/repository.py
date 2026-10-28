"""Contrato de persistência da blockchain."""

from __future__ import annotations

from typing import Protocol

from blockchain_api.domain.models import Block, Transaction


class BlockchainRepository(Protocol):
    """Porta usada pelo domínio sem acoplá-lo a um banco específico."""

    def load_chain(self) -> list[Block]: ...

    def load_pending_transactions(self) -> list[Transaction]: ...

    def save_genesis(self, block: Block) -> None: ...

    def add_pending_transaction(self, transaction: Transaction) -> None: ...

    def commit_mined_block(self, block: Block) -> None: ...

    def replace_chain(self, blocks: list[Block]) -> None: ...


class InMemoryBlockchainRepository:
    """Implementação rápida para testes unitários e usos efêmeros."""

    def __init__(self) -> None:
        self._chain: list[Block] = []
        self._pending: list[Transaction] = []

    def load_chain(self) -> list[Block]:
        return list(self._chain)

    def load_pending_transactions(self) -> list[Transaction]:
        return list(self._pending)

    def save_genesis(self, block: Block) -> None:
        self._chain.append(block)

    def add_pending_transaction(self, transaction: Transaction) -> None:
        self._pending.append(transaction)

    def commit_mined_block(self, block: Block) -> None:
        self._chain.append(block)
        self._pending.clear()

    def replace_chain(self, blocks: list[Block]) -> None:
        self._chain = list(blocks)
        self._pending.clear()
