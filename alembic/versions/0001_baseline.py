"""empty baseline

Revision ID: 0001
Revises:
Create Date: 2026-07-07 00:00:00.000000

Migración inicial vacía. Las siguientes migraciones irán creando tablas
(users, bout_subscriptions, alert_log, etc.) cuando se definan en sus
respectivas fases (Fase 2b y Fase 3).

"""

from __future__ import annotations

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
