"""Add B2B traceability resources.

Revision ID: 20261029_0003
Revises: 20261028_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261029_0003"
down_revision: str | None = "20261028_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("document", sa.String(32)),
    )
    op.create_table(
        "products",
        sa.Column("code", sa.String(64), primary_key=True),
        sa.Column("company_id", sa.String(64), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
    )
    op.create_index("ix_products_company_id", "products", ["company_id"])
    op.create_table(
        "batches",
        sa.Column("code", sa.String(80), primary_key=True),
        sa.Column("product_code", sa.String(64), sa.ForeignKey("products.code"), nullable=False),
    )
    op.create_index("ix_batches_product_code", "batches", ["product_code"])
    op.create_table(
        "traceability_events",
        sa.Column("event_hash", sa.String(64), primary_key=True),
        sa.Column("batch_code", sa.String(80), sa.ForeignKey("batches.code"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("location", sa.String(160), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.String(64), nullable=False),
        sa.Column("block_index", sa.Integer()),
        sa.Column("block_hash", sa.String(64)),
    )
    op.create_index("ix_traceability_events_batch_code", "traceability_events", ["batch_code"])


def downgrade() -> None:
    op.drop_index("ix_traceability_events_batch_code", table_name="traceability_events")
    op.drop_table("traceability_events")
    op.drop_index("ix_batches_product_code", table_name="batches")
    op.drop_table("batches")
    op.drop_index("ix_products_company_id", table_name="products")
    op.drop_table("products")
    op.drop_table("companies")
