"""Public beta hardening tables

Revision ID: 4f6d2c9a1b34
Revises: 8a7f0d9c3b21
Create Date: 2026-05-11 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "4f6d2c9a1b34"
down_revision = "8a7f0d9c3b21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dataset_columns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("data_type", sa.String(), nullable=False),
        sa.Column("semantic_type", sa.String(), nullable=False),
        sa.Column("stats", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_id", "name", name="uq_dataset_column_name"),
    )
    op.create_index(op.f("ix_dataset_columns_id"), "dataset_columns", ["id"], unique=False)
    op.create_index("ix_dataset_columns_dataset_id", "dataset_columns", ["dataset_id"], unique=False)

    op.create_table(
        "dataset_rows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("values_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_id", "row_index", name="uq_dataset_row_index"),
    )
    op.create_index(op.f("ix_dataset_rows_id"), "dataset_rows", ["id"], unique=False)
    op.create_index("ix_dataset_rows_dataset_id", "dataset_rows", ["dataset_id"], unique=False)

    op.create_table(
        "dataset_cells",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("row_id", sa.Integer(), nullable=False),
        sa.Column("column_id", sa.Integer(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("column_name", sa.String(), nullable=False),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("formula", sa.String(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["column_id"], ["dataset_columns.id"]),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.ForeignKeyConstraint(["row_id"], ["dataset_rows.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_id", "row_index", "column_name", name="uq_dataset_cell"),
    )
    op.create_index(op.f("ix_dataset_cells_id"), "dataset_cells", ["id"], unique=False)
    op.create_index(
        "ix_dataset_cells_dataset_row",
        "dataset_cells",
        ["dataset_id", "row_index"],
        unique=False,
    )
    op.create_index(
        "ix_dataset_cells_dataset_column",
        "dataset_cells",
        ["dataset_id", "column_name"],
        unique=False,
    )

    op.create_table(
        "sheet_shares",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sheet_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["sheet_id"], ["sheets.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sheet_id", "user_id", name="uq_sheet_share_user"),
    )
    op.create_index(op.f("ix_sheet_shares_id"), "sheet_shares", ["id"], unique=False)
    op.create_index("ix_sheet_shares_sheet_id", "sheet_shares", ["sheet_id"], unique=False)
    op.create_index("ix_sheet_shares_user_id", "sheet_shares", ["user_id"], unique=False)

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_events_id"), "audit_events", ["id"], unique=False)
    op.create_index("ix_audit_events_actor_created", "audit_events", ["actor_id", "created_at"], unique=False)
    op.create_index("ix_audit_events_entity", "audit_events", ["entity_type", "entity_id"], unique=False)
    op.create_index("ix_audit_events_action_created", "audit_events", ["action", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_events_action_created", table_name="audit_events")
    op.drop_index("ix_audit_events_entity", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_created", table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_id"), table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_sheet_shares_user_id", table_name="sheet_shares")
    op.drop_index("ix_sheet_shares_sheet_id", table_name="sheet_shares")
    op.drop_index(op.f("ix_sheet_shares_id"), table_name="sheet_shares")
    op.drop_table("sheet_shares")
    op.drop_index("ix_dataset_cells_dataset_column", table_name="dataset_cells")
    op.drop_index("ix_dataset_cells_dataset_row", table_name="dataset_cells")
    op.drop_index(op.f("ix_dataset_cells_id"), table_name="dataset_cells")
    op.drop_table("dataset_cells")
    op.drop_index("ix_dataset_rows_dataset_id", table_name="dataset_rows")
    op.drop_index(op.f("ix_dataset_rows_id"), table_name="dataset_rows")
    op.drop_table("dataset_rows")
    op.drop_index("ix_dataset_columns_dataset_id", table_name="dataset_columns")
    op.drop_index(op.f("ix_dataset_columns_id"), table_name="dataset_columns")
    op.drop_table("dataset_columns")
