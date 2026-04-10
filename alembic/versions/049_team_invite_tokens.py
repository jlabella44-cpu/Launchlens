"""Add invite-token flow for team member invitations.

Revision ID: 049_team_invite_tokens
Revises: 048_ai_consent
"""

import sqlalchemy as sa

from alembic import op

revision = "049_team_invite_tokens"
down_revision = "048_ai_consent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Invited users exist in the users table without a password until they
    # accept. password_hash must allow NULL for that window.
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)

    # SHA-256 hex of the invite token we email the user. The raw token is
    # never stored — only its hash, so a DB read does not leak the token.
    op.add_column(
        "users",
        sa.Column("invite_token_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("invite_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("invited_by_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.create_index(
        "ix_users_invite_token_hash",
        "users",
        ["invite_token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_users_invite_token_hash", table_name="users")
    op.drop_column("users", "invited_by_user_id")
    op.drop_column("users", "invite_expires_at")
    op.drop_column("users", "invite_token_hash")
    # Any users with NULL password_hash must be deleted or have a password
    # set before the downgrade can run without constraint violation.
    op.execute("DELETE FROM users WHERE password_hash IS NULL")
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
