"""Auth/session and websocket ticket hardening

Revision ID: 9c8b7a6d5e21
Revises: 4f6d2c9a1b34
Create Date: 2026-05-11 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "9c8b7a6d5e21"
down_revision = "4f6d2c9a1b34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(), nullable=False),
        sa.Column("family_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_jti", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti"),
    )
    op.create_index(op.f("ix_refresh_tokens_id"), "refresh_tokens", ["id"], unique=False)
    op.create_index("ix_refresh_tokens_jti", "refresh_tokens", ["jti"], unique=True)
    op.create_index("ix_refresh_tokens_user_active", "refresh_tokens", ["user_id", "revoked_at", "expires_at"], unique=False)
    op.create_index("ix_refresh_tokens_family", "refresh_tokens", ["family_id"], unique=False)

    op.create_table(
        "websocket_tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_hash", sa.String(), nullable=False),
        sa.Column("sheet_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["sheet_id"], ["sheets.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_hash"),
    )
    op.create_index(op.f("ix_websocket_tickets_id"), "websocket_tickets", ["id"], unique=False)
    op.create_index("ix_websocket_tickets_hash", "websocket_tickets", ["ticket_hash"], unique=True)
    op.create_index("ix_websocket_tickets_sheet_user", "websocket_tickets", ["sheet_id", "user_id"], unique=False)
    op.create_index("ix_websocket_tickets_expires", "websocket_tickets", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_websocket_tickets_expires", table_name="websocket_tickets")
    op.drop_index("ix_websocket_tickets_sheet_user", table_name="websocket_tickets")
    op.drop_index("ix_websocket_tickets_hash", table_name="websocket_tickets")
    op.drop_index(op.f("ix_websocket_tickets_id"), table_name="websocket_tickets")
    op.drop_table("websocket_tickets")
    op.drop_index("ix_refresh_tokens_family", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_active", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_jti", table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
