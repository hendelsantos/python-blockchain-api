from decimal import Decimal

from blockchain_api.core.blockchain import Blockchain
from blockchain_api.infrastructure.database import build_repository


def test_chain_and_pending_transactions_survive_restart(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'persistence.db'}"
    first = Blockchain(difficulty=1, repository=build_repository(database_url))
    first.mine_pending_transactions("alice")
    first.add_transaction("alice", "bob", Decimal("0.40"))

    restarted = Blockchain(difficulty=1, repository=build_repository(database_url))
    assert len(restarted.chain) == 2
    assert len(restarted.pending_transactions) == 1
    assert restarted.get_balance("alice")["available"] == Decimal("0.60")

    restarted.mine_pending_transactions("miner-01")
    final = Blockchain(difficulty=1, repository=build_repository(database_url))

    assert len(final.chain) == 3
    assert final.pending_transactions == ()
    assert final.get_balance("alice")["confirmed"] == Decimal("0.60")
    assert final.get_balance("bob")["confirmed"] == Decimal("0.40")
    assert final.get_balance("miner-01")["confirmed"] == Decimal("1")
    assert final.is_valid()
