"""Persist blockchain and pending transactions.

Revision ID: 20261028_0001
Revises:
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261028_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "blocks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("block_index", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.String(length=64), nullable=False),
        sa.Column("transactions_json", sa.JSON(), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=False),
        sa.Column("nonce", sa.Integer(), nullable=False),
        sa.Column("block_hash", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("block_hash"),
    )
    op.create_index("ix_blocks_block_index", "blocks", ["block_index"], unique=True)
    op.create_table(
        "pending_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sender", sa.String(length=100), nullable=False),
        sa.Column("recipient", sa.String(length=100), nullable=False),
        sa.Column("amount", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pending_transactions_recipient",
        "pending_transactions",
        ["recipient"],
    )
    op.create_index(
        "ix_pending_transactions_sender",
        "pending_transactions",
        ["sender"],
    )


def downgrade() -> None:
    op.drop_index("ix_pending_transactions_sender", table_name="pending_transactions")
    op.drop_index("ix_pending_transactions_recipient", table_name="pending_transactions")
    op.drop_table("pending_transactions")
    op.drop_index("ix_blocks_block_index", table_name="blocks")
    op.drop_table("blocks")
