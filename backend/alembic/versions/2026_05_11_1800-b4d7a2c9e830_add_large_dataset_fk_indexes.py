"""Add indexes for large dataset cleanup

Revision ID: b4d7a2c9e830
Revises: 9c8b7a6d5e21
Create Date: 2026-05-11 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b4d7a2c9e830"
down_revision = "9c8b7a6d5e21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "create index if not exists ix_sheets_dataset_id on sheets (dataset_id)"
    )
    op.execute("create index if not exists ix_charts_sheet_id on charts (sheet_id)")
    op.execute("create index if not exists ix_comments_sheet_id on comments (sheet_id)")

    # Build these offline for existing Postgres beta databases that already
    # contain materialized cells. Fresh Postgres databases still get them here.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        has_existing_cells = bind.execute(
            sa.text("select exists (select 1 from dataset_cells limit 1)")
        ).scalar()
        if has_existing_cells:
            return

    op.execute(
        "create index if not exists ix_dataset_cells_row_id on dataset_cells (row_id)"
    )
    op.execute(
        "create index if not exists ix_dataset_cells_column_id on dataset_cells (column_id)"
    )


def downgrade() -> None:
    op.execute("drop index if exists ix_dataset_cells_column_id")
    op.execute("drop index if exists ix_dataset_cells_row_id")
    op.execute("drop index if exists ix_comments_sheet_id")
    op.execute("drop index if exists ix_charts_sheet_id")
    op.execute("drop index if exists ix_sheets_dataset_id")
