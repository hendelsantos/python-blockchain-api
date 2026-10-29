"""Rastreabilidade de produtos ancorada na blockchain."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol

from blockchain_api.core.blockchain import Blockchain


class TraceabilityError(ValueError):
    """O recurso de rastreabilidade não atende às regras de negócio."""


class TraceabilityRepository(Protocol):
    def create_company(self, name: str, document: str | None) -> dict[str, object]: ...
    def create_product(self, company_id: str, code: str, name: str) -> dict[str, object]: ...
    def create_batch(self, product_code: str, code: str) -> dict[str, object]: ...
    def create_event(self, event: dict[str, object]) -> dict[str, object]: ...
    def confirm_event(self, event_hash: str, block_index: int, block_hash: str) -> None: ...
    def get_public_batch(self, code: str) -> dict[str, object] | None: ...


class InMemoryTraceabilityRepository:
    def __init__(self) -> None:
        self.companies: dict[str, dict[str, object]] = {}
        self.products: dict[str, dict[str, object]] = {}
        self.batches: dict[str, dict[str, object]] = {}
        self.events: list[dict[str, object]] = []

    def create_company(self, name: str, document: str | None) -> dict[str, object]:
        identifier = f"company-{len(self.companies) + 1}"
        company = {"id": identifier, "name": name, "document": document}
        self.companies[identifier] = company
        return company

    def create_product(self, company_id: str, code: str, name: str) -> dict[str, object]:
        if company_id not in self.companies:
            raise TraceabilityError("empresa não encontrada")
        if code in self.products:
            raise TraceabilityError("código de produto já cadastrado")
        product = {"company_id": company_id, "code": code, "name": name}
        self.products[code] = product
        return product

    def create_batch(self, product_code: str, code: str) -> dict[str, object]:
        if product_code not in self.products:
            raise TraceabilityError("produto não encontrado")
        if code in self.batches:
            raise TraceabilityError("código de lote já cadastrado")
        batch = {"product_code": product_code, "code": code}
        self.batches[code] = batch
        return batch

    def create_event(self, event: dict[str, object]) -> dict[str, object]:
        if event["batch_code"] not in self.batches:
            raise TraceabilityError("lote não encontrado")
        self.events.append(event)
        return event

    def confirm_event(self, event_hash: str, block_index: int, block_hash: str) -> None:
        for event in self.events:
            if event["event_hash"] == event_hash:
                event.update({"block_index": block_index, "block_hash": block_hash})
                return

    def get_public_batch(self, code: str) -> dict[str, object] | None:
        batch = self.batches.get(code)
        if batch is None:
            return None
        product = self.products[batch["product_code"]]
        company = self.companies[product["company_id"]]
        events = [event for event in self.events if event["batch_code"] == code]
        return {"batch": batch, "product": product, "company": company, "events": events}


class TraceabilityService:
    def __init__(self, repository: TraceabilityRepository) -> None:
        self._repository = repository

    def create_company(self, name: str, document: str | None = None) -> dict[str, object]:
        return self._repository.create_company(name.strip(), document.strip() if document else None)

    def create_product(self, company_id: str, code: str, name: str) -> dict[str, object]:
        return self._repository.create_product(company_id, code.strip().upper(), name.strip())

    def create_batch(self, product_code: str, code: str) -> dict[str, object]:
        return self._repository.create_batch(product_code.strip().upper(), code.strip().upper())

    def register_event(
        self,
        *,
        batch_code: str,
        event_type: str,
        location: str,
        details: dict[str, object],
        blockchain: Blockchain,
    ) -> dict[str, object]:
        event = {
            "batch_code": batch_code.strip().upper(),
            "event_type": event_type.strip().upper(),
            "location": location.strip(),
            "details": details,
            "occurred_at": datetime.now(UTC).isoformat(),
        }
        canonical = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        event["event_hash"] = sha256(canonical.encode()).hexdigest()
        self._repository.create_event(event)
        block = blockchain.anchor_traceability_event(event["event_hash"])
        event.update({"block_index": block.index, "block_hash": block.calculate_hash()})
        self._repository.confirm_event(event["event_hash"], block.index, block.calculate_hash())
        return event

    def get_public_batch(self, code: str) -> dict[str, object] | None:
        return self._repository.get_public_batch(code.strip().upper())
