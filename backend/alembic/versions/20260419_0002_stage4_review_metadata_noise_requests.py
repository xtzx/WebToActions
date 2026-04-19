"""stage4 review metadata additions

Revision ID: 20260419_0002
Revises: 20260419_0001
Create Date: 2026-04-19 17:15:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision = "20260419_0002"
down_revision = "20260419_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reviewed_metadata",
        sa.Column(
            "noise_request_ids_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("reviewed_metadata", "noise_request_ids_json")


def _unused(_: Sequence[object]) -> None:
    return None
