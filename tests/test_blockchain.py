from dataclasses import replace
from decimal import Decimal

import pytest

from blockchain_api.core.blockchain import Blockchain, InvalidTransactionError


def test_add_and_mine_transaction() -> None:
    blockchain = Blockchain(difficulty=1)
    transaction = blockchain.add_transaction("alice", "bob", Decimal("10.5"))

    assert transaction in blockchain.pending_transactions

    block = blockchain.mine_pending_transactions("miner-01")

    assert block.index == 1
    assert len(block.transactions) == 2
    assert block.transactions[-1].recipient == "miner-01"
    assert block.calculate_hash().startswith("0")
    assert blockchain.pending_transactions == ()
    assert blockchain.is_valid()


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
    blockchain.add_transaction("alice", "bob", Decimal("3"))
    blockchain.mine_pending_transactions("miner-01")

    original = blockchain._chain[1]
    blockchain._chain[1] = replace(original, previous_hash="invalid")

    assert not blockchain.is_valid()
