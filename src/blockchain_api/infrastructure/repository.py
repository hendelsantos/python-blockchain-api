"""Persistência da cadeia e da fila de transações com SQLAlchemy."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import JSON, Engine, ForeignKey, Integer, String, delete, select
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


class CompanyRecord(Base):
    __tablename__ = "companies"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    document: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ProductRecord(Base):
    __tablename__ = "products"
    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)


class BatchRecord(Base):
    __tablename__ = "batches"
    code: Mapped[str] = mapped_column(String(80), primary_key=True)
    product_code: Mapped[str] = mapped_column(
        ForeignKey("products.code"), nullable=False, index=True
    )


class TraceabilityEventRecord(Base):
    __tablename__ = "traceability_events"
    event_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    batch_code: Mapped[str] = mapped_column(ForeignKey("batches.code"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    location: Mapped[str] = mapped_column(String(160), nullable=False)
    details_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    occurred_at: Mapped[str] = mapped_column(String(64), nullable=False)
    block_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    block_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


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

    def replace_chain(self, blocks: list[Block]) -> None:
        """Substitui a cadeia de forma atômica após validação pelo domínio."""

        with self._session_factory.begin() as session:
            session.execute(delete(PendingTransactionRecord))
            session.execute(delete(BlockRecord))
            session.add_all(self._to_record(block) for block in blocks)


class SQLAlchemyTraceabilityRepository:
    def __init__(self, engine: Engine) -> None:
        self._session_factory = sessionmaker(engine, expire_on_commit=False)

    def create_company(self, name: str, document: str | None) -> dict[str, object]:
        identifier = f"company-{name.lower().replace(' ', '-')[:40]}"
        with self._session_factory.begin() as session:
            if session.get(CompanyRecord, identifier):
                raise ValueError("empresa já cadastrada")
            session.add(CompanyRecord(id=identifier, name=name, document=document))
        return {"id": identifier, "name": name, "document": document}

    def create_product(self, company_id: str, code: str, name: str) -> dict[str, object]:
        with self._session_factory.begin() as session:
            if not session.get(CompanyRecord, company_id):
                raise ValueError("empresa não encontrada")
            if session.get(ProductRecord, code):
                raise ValueError("código de produto já cadastrado")
            session.add(ProductRecord(company_id=company_id, code=code, name=name))
        return {"company_id": company_id, "code": code, "name": name}

    def create_batch(self, product_code: str, code: str) -> dict[str, object]:
        with self._session_factory.begin() as session:
            if not session.get(ProductRecord, product_code):
                raise ValueError("produto não encontrado")
            if session.get(BatchRecord, code):
                raise ValueError("código de lote já cadastrado")
            session.add(BatchRecord(product_code=product_code, code=code))
        return {"product_code": product_code, "code": code}

    def create_event(self, event: dict[str, object]) -> dict[str, object]:
        with self._session_factory.begin() as session:
            if not session.get(BatchRecord, str(event["batch_code"])):
                raise ValueError("lote não encontrado")
            session.add(
                TraceabilityEventRecord(
                    event_hash=str(event["event_hash"]),
                    batch_code=str(event["batch_code"]),
                    event_type=str(event["event_type"]),
                    location=str(event["location"]),
                    details_json=dict(event["details"]),
                    occurred_at=str(event["occurred_at"]),
                )
            )
        return event

    def confirm_event(self, event_hash: str, block_index: int, block_hash: str) -> None:
        with self._session_factory.begin() as session:
            event = session.get(TraceabilityEventRecord, event_hash)
            if event:
                event.block_index, event.block_hash = block_index, block_hash

    def get_public_batch(self, code: str) -> dict[str, object] | None:
        with self._session_factory() as session:
            batch = session.get(BatchRecord, code)
            if batch is None:
                return None
            product = session.get(ProductRecord, batch.product_code)
            company = session.get(CompanyRecord, product.company_id)
            events = session.scalars(
                select(TraceabilityEventRecord)
                .where(TraceabilityEventRecord.batch_code == code)
                .order_by(TraceabilityEventRecord.occurred_at)
            ).all()
            return {
                "batch": {"code": batch.code, "product_code": batch.product_code},
                "product": {"code": product.code, "name": product.name},
                "company": {"id": company.id, "name": company.name},
                "events": [
                    {
                        "event_hash": event.event_hash,
                        "event_type": event.event_type,
                        "location": event.location,
                        "details": event.details_json,
                        "occurred_at": event.occurred_at,
                        "block_index": event.block_index,
                        "block_hash": event.block_hash,
                    }
                    for event in events
                ],
            }
