"""alert_log message_type partial unique index

Revision ID: e533157bd26f
Revises: d7f45061518c
Create Date: 2026-08-15 14:45:56.780069

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e533157bd26f'
down_revision: Union[str, None] = 'd7f45061518c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A10: la UNIQUE antigua (subscription_id, bout_id, fired_at_epoch_hour) hacia
    # que un `update` y un `started` en la misma hora colisionaran y se perdiera
    # la fila de auditoria. La idempotencia real solo aplica a `started`/`cancelled`
    # (mensajes terminales): la pasamos a un partial unique index. Las filas
    # `update` quedan como audit puro (todas se guardan).
    #
    # batch mode: SQLite no soporta ALTER de constraints, requiere copy-and-move.
    with op.batch_alter_table("alert_log") as batch_op:
        batch_op.drop_constraint("uq_alert_idempotency", type_="unique")
        batch_op.add_column(sa.Column("message_type", sa.String(length=20), nullable=True))
    op.create_index(
        "uq_alert_status_idem",
        "alert_log",
        ["subscription_id", "bout_id", "message_type"],
        unique=True,
        postgresql_where=sa.text("message_type IN ('started', 'cancelled')"),
        sqlite_where=sa.text("message_type IN ('started', 'cancelled')"),
    )


def downgrade() -> None:
    op.drop_index("uq_alert_status_idem", table_name="alert_log")
    with op.batch_alter_table("alert_log") as batch_op:
        batch_op.drop_column("message_type")
        batch_op.create_unique_constraint(
            "uq_alert_idempotency",
            ["subscription_id", "bout_id", "fired_at_epoch_hour"],
        )