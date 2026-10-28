"""Primitivas Ed25519 para carteiras e transações assinadas."""

from __future__ import annotations

import base64
import json
from decimal import Decimal
from hashlib import sha256

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def _encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _decode(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"), validate=True)


def address_from_public_key(public_key: str) -> str:
    """Deriva um endereço curto e determinístico da chave pública."""

    return sha256(_decode(public_key)).hexdigest()[:40]


def canonical_transaction_payload(
    *, sender: str, recipient: str, amount: Decimal, nonce: int
) -> bytes:
    payload = {
        "amount": str(amount),
        "nonce": nonce,
        "recipient": recipient,
        "sender": sender,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def generate_wallet() -> dict[str, str]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_raw = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    public_encoded = _encode(public_raw)
    return {
        "address": address_from_public_key(public_encoded),
        "public_key": public_encoded,
        "private_key": _encode(private_raw),
    }


def sign_transaction(
    *,
    private_key: str,
    sender: str,
    recipient: str,
    amount: Decimal,
    nonce: int,
) -> str:
    key = Ed25519PrivateKey.from_private_bytes(_decode(private_key))
    signature = key.sign(
        canonical_transaction_payload(
            sender=sender,
            recipient=recipient,
            amount=amount,
            nonce=nonce,
        )
    )
    return _encode(signature)


def verify_transaction_signature(
    *,
    public_key: str,
    signature: str,
    sender: str,
    recipient: str,
    amount: Decimal,
    nonce: int,
) -> bool:
    try:
        key = Ed25519PublicKey.from_public_bytes(_decode(public_key))
        key.verify(
            _decode(signature),
            canonical_transaction_payload(
                sender=sender,
                recipient=recipient,
                amount=amount,
                nonce=nonce,
            ),
        )
    except (InvalidSignature, ValueError):
        return False
    return True
