"""add composite indexes on credit_transactions and outbox

Revision ID: 018
Revises: 017
Create Date: 2026-03-31

"""
from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_credit_transactions_type_created",
        "credit_transactions",
        ["transaction_type", "created_at"],
    )
    op.create_index(
        "ix_outbox_undelivered",
        "outbox",
        ["delivered_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_undelivered", table_name="outbox")
    op.drop_index("ix_credit_transactions_type_created", table_name="credit_transactions")
