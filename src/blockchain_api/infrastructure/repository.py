"""Persistência da cadeia e da fila de transações com SQLAlchemy."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import JSON, Engine, Integer, String, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from blockchain_api.domain.models import Block, Transaction


class Base(DeclarativeBase):
    pass


class BlockRecord(Base):
    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    block_index: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    transactions_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    nonce: Mapped[int] = mapped_column(Integer, nullable=False)
    block_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)


class PendingTransactionRecord(Base):
    __tablename__ = "pending_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    sender: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    recipient: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    amount: Mapped[str] = mapped_column(String(80), nullable=False)
    nonce: Mapped[int | None] = mapped_column(Integer, nullable=True)
    public_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    signature: Mapped[str | None] = mapped_column(String(256), nullable=True)


class SQLAlchemyBlockchainRepository:
    def __init__(self, engine: Engine) -> None:
        self._session_factory = sessionmaker(engine, expire_on_commit=False)

    @staticmethod
    def _to_block(record: BlockRecord) -> Block:
        block = Block(
            index=record.block_index,
            timestamp=record.timestamp,
            transactions=tuple(
                Transaction(
                    sender=str(transaction["sender"]),
                    recipient=str(transaction["recipient"]),
                    amount=Decimal(str(transaction["amount"])),
                    nonce=(
                        int(transaction["nonce"]) if transaction.get("nonce") is not None else None
                    ),
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
                for transaction in record.transactions_json
            ),
            previous_hash=record.previous_hash,
            nonce=record.nonce,
        )
        if block.calculate_hash() != record.block_hash:
            raise ValueError(f"hash persistido inválido no bloco {record.block_index}")
        return block

    @staticmethod
    def _to_record(block: Block) -> BlockRecord:
        return BlockRecord(
            block_index=block.index,
            timestamp=block.timestamp,
            transactions_json=[transaction.to_dict() for transaction in block.transactions],
            previous_hash=block.previous_hash,
            nonce=block.nonce,
            block_hash=block.calculate_hash(),
        )

    def load_chain(self) -> list[Block]:
        with self._session_factory() as session:
            records = session.scalars(select(BlockRecord).order_by(BlockRecord.block_index)).all()
            return [self._to_block(record) for record in records]

    def load_pending_transactions(self) -> list[Transaction]:
        with self._session_factory() as session:
            records = session.scalars(
                select(PendingTransactionRecord).order_by(PendingTransactionRecord.id)
            ).all()
            return [
                Transaction(
                    sender=record.sender,
                    recipient=record.recipient,
                    amount=Decimal(record.amount),
                    nonce=record.nonce,
                    public_key=record.public_key,
                    signature=record.signature,
                )
                for record in records
            ]

    def save_genesis(self, block: Block) -> None:
        with self._session_factory.begin() as session:
            session.add(self._to_record(block))

    def add_pending_transaction(self, transaction: Transaction) -> None:
        with self._session_factory.begin() as session:
            session.add(
                PendingTransactionRecord(
                    sender=transaction.sender,
                    recipient=transaction.recipient,
                    amount=str(transaction.amount),
                    nonce=transaction.nonce,
                    public_key=transaction.public_key,
                    signature=transaction.signature,
                )
            )

    def commit_mined_block(self, block: Block) -> None:
        """Grava o bloco e limpa a fila na mesma transação de banco."""

        with self._session_factory.begin() as session:
            session.add(self._to_record(block))
            session.execute(delete(PendingTransactionRecord))
