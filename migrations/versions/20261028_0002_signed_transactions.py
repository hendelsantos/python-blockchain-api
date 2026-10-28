"""Add cryptographic data to pending transactions.

Revision ID: 20261028_0002
Revises: 20261028_0001
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261028_0002"
down_revision: str | None = "20261028_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pending_transactions", sa.Column("nonce", sa.Integer(), nullable=True))
    op.add_column(
        "pending_transactions",
        sa.Column("public_key", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "pending_transactions",
        sa.Column("signature", sa.String(length=256), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pending_transactions", "signature")
    op.drop_column("pending_transactions", "public_key")
    op.drop_column("pending_transactions", "nonce")
