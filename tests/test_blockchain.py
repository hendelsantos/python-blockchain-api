from dataclasses import replace
from decimal import Decimal

import pytest

from blockchain_api.core.blockchain import (
    Blockchain,
    InsufficientFundsError,
    InvalidNonceError,
    InvalidSignatureError,
    InvalidTransactionError,
)
from blockchain_api.core.crypto import generate_wallet, sign_transaction


def add_signed_transaction(
    blockchain: Blockchain,
    wallet: dict[str, str],
    recipient: str,
    amount: Decimal,
) -> None:
    nonce = blockchain.get_next_nonce(wallet["address"])
    signature = sign_transaction(
        private_key=wallet["private_key"],
        sender=wallet["address"],
        recipient=recipient,
        amount=amount,
        nonce=nonce,
    )
    blockchain.add_transaction(
        wallet["address"],
        recipient,
        amount,
        nonce=nonce,
        public_key=wallet["public_key"],
        signature=signature,
    )


def test_add_and_mine_transaction() -> None:
    blockchain = Blockchain(difficulty=1)
    alice = generate_wallet()
    blockchain.mine_pending_transactions(alice["address"])
    add_signed_transaction(blockchain, alice, "bob", Decimal("0.75"))
    transaction = blockchain.pending_transactions[0]

    assert transaction in blockchain.pending_transactions

    block = blockchain.mine_pending_transactions("miner-01")

    assert block.index == 2
    assert len(block.transactions) == 2
    assert block.transactions[-1].recipient == "miner-01"
    assert block.calculate_hash().startswith("0")
    assert blockchain.pending_transactions == ()
    assert blockchain.is_valid()
    assert blockchain.get_balance(alice["address"])["confirmed"] == Decimal("0.25")
    assert blockchain.get_balance("bob")["confirmed"] == Decimal("0.75")


def test_rejects_insufficient_funds_and_pending_double_spend() -> None:
    blockchain = Blockchain(difficulty=1)
    alice = generate_wallet()
    blockchain.mine_pending_transactions(alice["address"])
    add_signed_transaction(blockchain, alice, "bob", Decimal("0.75"))

    with pytest.raises(InsufficientFundsError):
        add_signed_transaction(blockchain, alice, "charlie", Decimal("0.50"))

    balance = blockchain.get_balance(alice["address"])
    assert balance["confirmed"] == Decimal("1")
    assert balance["available"] == Decimal("0.25")
    assert balance["pending_outgoing"] == Decimal("0.75")


def test_rejects_invalid_signature_and_replayed_nonce() -> None:
    blockchain = Blockchain(difficulty=1)
    alice = generate_wallet()
    blockchain.mine_pending_transactions(alice["address"])
    signature = sign_transaction(
        private_key=alice["private_key"],
        sender=alice["address"],
        recipient="bob",
        amount=Decimal("0.25"),
        nonce=0,
    )

    with pytest.raises(InvalidSignatureError):
        blockchain.add_transaction(
            alice["address"],
            "charlie",
            Decimal("0.25"),
            nonce=0,
            public_key=alice["public_key"],
            signature=signature,
        )

    blockchain.add_transaction(
        alice["address"],
        "bob",
        Decimal("0.25"),
        nonce=0,
        public_key=alice["public_key"],
        signature=signature,
    )
    with pytest.raises(InvalidNonceError):
        blockchain.add_transaction(
            alice["address"],
            "bob",
            Decimal("0.25"),
            nonce=0,
            public_key=alice["public_key"],
            signature=signature,
        )


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
        blockchain.add_transaction(
            sender,
            recipient,
            amount,
            nonce=0,
            public_key="invalid-public-key",
            signature="invalid-signature",
        )


def test_detects_a_tampered_chain() -> None:
    blockchain = Blockchain(difficulty=1)
    blockchain.mine_pending_transactions("alice")

    original = blockchain._chain[1]
    blockchain._chain[1] = replace(original, previous_hash="invalid")

    assert not blockchain.is_valid()


def test_replaces_chain_only_when_candidate_is_valid_and_longer() -> None:
    local = Blockchain(difficulty=1)
    remote = Blockchain(difficulty=1)
    remote.mine_pending_transactions("miner-a")
    remote.mine_pending_transactions("miner-b")

    assert local.replace_chain(list(remote.chain))
    assert len(local.chain) == 3
    assert not local.replace_chain(list(remote.chain))
