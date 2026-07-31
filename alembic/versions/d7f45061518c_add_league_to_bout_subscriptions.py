"""add_league_to_bout_subscriptions

Revision ID: d7f45061518c
Revises: 8df6f9297a34
Create Date: 2026-07-31 13:42:54.485105

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd7f45061518c'
down_revision: Union[str, None] = '8df6f9297a34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bout_subscriptions",
        sa.Column("league", sa.String(length=50), nullable=False, server_default=""),
    )
    op.create_index(op.f("ix_bout_subscriptions_league"), "bout_subscriptions", ["league"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bout_subscriptions_league"), table_name="bout_subscriptions")
    op.drop_column("bout_subscriptions", "league")