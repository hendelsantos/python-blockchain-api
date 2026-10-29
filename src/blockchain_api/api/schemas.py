"""Contratos públicos da API."""

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class TransactionCreate(BaseModel):
    sender: str = Field(min_length=1, max_length=100, examples=["alice"])
    recipient: str = Field(min_length=1, max_length=100, examples=["bob"])
    amount: Decimal = Field(gt=0, decimal_places=8, examples=[10.5])
    nonce: int = Field(ge=0, examples=[0])
    public_key: str = Field(min_length=40, max_length=128)
    signature: str = Field(min_length=40, max_length=256)

    @field_validator("sender", "recipient")
    @classmethod
    def strip_names(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("não pode conter apenas espaços")
        return value


class MessageResponse(BaseModel):
    message: str
    data: dict[str, object]


class PeerRegistration(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=20)


class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    document: str | None = Field(default=None, max_length=32)


class ProductCreate(BaseModel):
    company_id: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=160)


class BatchCreate(BaseModel):
    product_code: str = Field(min_length=2, max_length=64)
    code: str = Field(min_length=2, max_length=80)


class TraceEventCreate(BaseModel):
    event_type: str = Field(min_length=2, max_length=64)
    location: str = Field(min_length=2, max_length=160)
    details: dict[str, object] = Field(default_factory=dict)
