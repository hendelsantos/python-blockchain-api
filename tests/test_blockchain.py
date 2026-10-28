from dataclasses import replace
from decimal import Decimal

import pytest

from blockchain_api.core.blockchain import (
    Blockchain,
    InsufficientFundsError,
    InvalidTransactionError,
)


def test_add_and_mine_transaction() -> None:
    blockchain = Blockchain(difficulty=1)
    blockchain.mine_pending_transactions("alice")
    transaction = blockchain.add_transaction("alice", "bob", Decimal("0.75"))

    assert transaction in blockchain.pending_transactions

    block = blockchain.mine_pending_transactions("miner-01")

    assert block.index == 2
    assert len(block.transactions) == 2
    assert block.transactions[-1].recipient == "miner-01"
    assert block.calculate_hash().startswith("0")
    assert blockchain.pending_transactions == ()
    assert blockchain.is_valid()
    assert blockchain.get_balance("alice")["confirmed"] == Decimal("0.25")
    assert blockchain.get_balance("bob")["confirmed"] == Decimal("0.75")


def test_rejects_insufficient_funds_and_pending_double_spend() -> None:
    blockchain = Blockchain(difficulty=1)
    blockchain.mine_pending_transactions("alice")
    blockchain.add_transaction("alice", "bob", Decimal("0.75"))

    with pytest.raises(InsufficientFundsError):
        blockchain.add_transaction("alice", "charlie", Decimal("0.50"))

    balance = blockchain.get_balance("alice")
    assert balance["confirmed"] == Decimal("1")
    assert balance["available"] == Decimal("0.25")
    assert balance["pending_outgoing"] == Decimal("0.75")


@pytest.mark.parametrize(
    ("sender", "recipient", "amount"),
    [
        ("", "bob", Decimal("1")),
        ("alice", "", Decimal("1")),
        ("alice", "alice", Decimal("1")),
        ("alice", "bob", Decimal("0")),
        ("alice", "bob", Decimal("-1")),
    ],
)
def test_rejects_invalid_transactions(sender: str, recipient: str, amount: Decimal) -> None:
    blockchain = Blockchain(difficulty=1)

    with pytest.raises(InvalidTransactionError):
        blockchain.add_transaction(sender, recipient, amount)


def test_detects_a_tampered_chain() -> None:
    blockchain = Blockchain(difficulty=1)
    blockchain.mine_pending_transactions("alice")

    original = blockchain._chain[1]
    blockchain._chain[1] = replace(original, previous_hash="invalid")

    assert not blockchain.is_valid()
