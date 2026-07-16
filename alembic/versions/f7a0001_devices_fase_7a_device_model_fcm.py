"""fase 7a: device model + FCM (drop User/Twilio era, recreate bout_subs + alert_log).

Revision ID: f7a0001_devices
Revises: a3657c6166f0
Create Date: 2026-07-16

Pivot del modelo de datos de la era User/Twilio al modelo Device/FCM (D37, D40).
Esta migración es DESTRUCTIVA: no existe forma significativa de migrar datos
existentes (los `User` tenían teléfono para llamadas Twilio; los `Device` tienen
`fcm_token` para pushes). El alcance de Fase 7a incluye:

- Crear `devices` (UUID PK, fcm_token, platform, timezone, locale, is_active,
  created_at, last_seen_at).
- Recrear `bout_subscriptions` sin `previous_bout_id`/`previous_match_number`
  (E4: el backend deriva el previo de la card fresca en runtime), con
  `device_id` FK→devices.id CASCADE, UNIQUE `(device_id, bout_id)` (E6), sin
  `user_id`.
- Recrear `alert_log` con `device_id` (no `user_id`) y `fired_at_epoch_hour`
  (E6: `now.hour` colisionaba entre días) y UNIQUE actualizado.
- Eliminar `sport_subscriptions` y `event_subscriptions` (tablas muertas —
  ningún router las usaba).
- Eliminar tabla `users` y el ENUM `user_role` en Postgres.

Asumimos dev=SQLite y prod=PG sin desplegar todavía: drop-and-recreate es
válido para ambos. Para PG, `sa.Enum(...).drop()` borra el ENUM huérfano
(alembic autogenerate no lo detecta).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7a0001_devices"
down_revision: Union[str, None] = "a3657c6166f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop tablas existentes en orden inverso a dependencias.
    op.drop_table("alert_log")
    op.drop_table("sport_subscriptions")
    op.drop_table("event_subscriptions")
    op.drop_table("bout_subscriptions")
    op.drop_table("users")

    # 2. En Postgres, dropear los ENUMs huérfanos. En SQLite, los "enum" son
    #    CHECK inline y se borran con la tabla → noop. Sa.Enum.drop es seguro
    #    en ambos (se transforma en noop en SQLite via alembic).
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="user_role").drop(bind, checkfirst=True)
        sa.Enum(name="subscription_status").drop(bind, checkfirst=True)
        sa.Enum(name="alert_status").drop(bind, checkfirst=True)

    # 3. Crear tabla `devices`.
    op.create_table(
        "devices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("fcm_token", sa.String(length=255), nullable=True),
        sa.Column("platform", sa.String(length=10), nullable=True),
        sa.Column("timezone", sa.String(length=50), nullable=False),
        sa.Column("locale", sa.String(length=10), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_devices")),
    )
    op.create_index(op.f("ix_devices_fcm_token"), "devices", ["fcm_token"], unique=False)

    # 4. Crear `bout_subscriptions` (nueva forma).
    op.create_table(
        "bout_subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=50), nullable=False),
        sa.Column("bout_id", sa.String(length=50), nullable=False),
        sa.Column("target_match_number", sa.Integer(), nullable=False),
        sa.Column("lead_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "fired", "cancelled", name="subscription_status"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["device_id"], ["devices.id"], ondelete="CASCADE", name=op.f("fk_bout_subscriptions_device_id_devices")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bout_subscriptions")),
        sa.UniqueConstraint("device_id", "bout_id", name="uq_bout_subscriptions_device_bout"),
    )
    op.create_index(op.f("ix_bout_subscriptions_device_id"), "bout_subscriptions", ["device_id"], unique=False)
    op.create_index(op.f("ix_bout_subscriptions_event_id"), "bout_subscriptions", ["event_id"], unique=False)
    op.create_index(op.f("ix_bout_subscriptions_bout_id"), "bout_subscriptions", ["bout_id"], unique=False)
    op.create_index(op.f("ix_bout_subscriptions_status"), "bout_subscriptions", ["status"], unique=False)

    # 5. Crear `alert_log` (nueva forma: device_id + fired_at_epoch_hour).
    op.create_table(
        "alert_log",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("subscription_id", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=36), nullable=False),
        sa.Column("bout_id", sa.String(length=50), nullable=False),
        sa.Column("fired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fired_at_epoch_hour", sa.Integer(), nullable=False),
        sa.Column("payload", sa.String(length=2000), nullable=True),
        sa.Column("notifier_response", sa.String(length=500), nullable=True),
        sa.Column(
            "status",
            sa.Enum("fired", "failed", "skipped", name="alert_status"),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["bout_subscriptions.id"],
            ondelete="CASCADE",
            name=op.f("fk_alert_log_subscription_id_bout_subscriptions"),
        ),
        sa.ForeignKeyConstraint(
            ["device_id"], ["devices.id"], ondelete="CASCADE", name=op.f("fk_alert_log_device_id_devices")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alert_log")),
        sa.UniqueConstraint(
            "subscription_id", "bout_id", "fired_at_epoch_hour", name="uq_alert_idempotency"
        ),
    )
    op.create_index(op.f("ix_alert_log_subscription_id"), "alert_log", ["subscription_id"], unique=False)
    op.create_index(op.f("ix_alert_log_device_id"), "alert_log", ["device_id"], unique=False)
    op.create_index(op.f("ix_alert_log_bout_id"), "alert_log", ["bout_id"], unique=False)
    op.create_index(op.f("ix_alert_log_fired_at"), "alert_log", ["fired_at"], unique=False)


def downgrade() -> None:
    """Best-effort downgrade: recrea el esquema antiguo (datos perdidos)."""
    op.drop_table("alert_log")
    op.drop_table("bout_subscriptions")
    op.drop_index(op.f("ix_devices_fcm_token"), table_name="devices")
    op.drop_table("devices")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="user_role").create(bind, checkfirst=False)
        sa.Enum(name="subscription_status").create(bind, checkfirst=False)
        sa.Enum(name="alert_status").create(bind, checkfirst=False)

    # Recrea el esquema viejo de a3657c6166f0 (sin datos).
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("phone_normalized", sa.String(length=20), nullable=True),
        sa.Column("timezone", sa.String(length=50), nullable=False),
        sa.Column("role", sa.Enum("user", "admin", name="user_role"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_table(
        "bout_subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=50), nullable=False),
        sa.Column("bout_id", sa.String(length=50), nullable=False),
        sa.Column("target_match_number", sa.Integer(), nullable=False),
        sa.Column("previous_bout_id", sa.String(length=50), nullable=True),
        sa.Column("previous_match_number", sa.Integer(), nullable=True),
        sa.Column("lead_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "fired", "cancelled", name="subscription_status"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bout_subscriptions_user_id"), "bout_subscriptions", ["user_id"], unique=False)
    op.create_index(op.f("ix_bout_subscriptions_event_id"), "bout_subscriptions", ["event_id"], unique=False)
    op.create_index(op.f("ix_bout_subscriptions_bout_id"), "bout_subscriptions", ["bout_id"], unique=False)
    op.create_index(op.f("ix_bout_subscriptions_status"), "bout_subscriptions", ["status"], unique=False)
    op.create_table(
        "event_subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=50), nullable=False),
        sa.Column("event_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_event_subscriptions_event_id"), "event_subscriptions", ["event_id"], unique=False)
    op.create_index(op.f("ix_event_subscriptions_user_id"), "event_subscriptions", ["user_id"], unique=False)
    op.create_table(
        "sport_subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("sport", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sport_subscriptions_sport"), "sport_subscriptions", ["sport"], unique=False)
    op.create_index(op.f("ix_sport_subscriptions_user_id"), "sport_subscriptions", ["user_id"], unique=False)
    op.create_table(
        "alert_log",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("subscription_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("bout_id", sa.String(length=50), nullable=False),
        sa.Column("fired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fired_at_hour", sa.Integer(), nullable=False),
        sa.Column("payload", sa.String(length=2000), nullable=True),
        sa.Column("notifier_response", sa.String(length=500), nullable=True),
        sa.Column(
            "status",
            sa.Enum("fired", "failed", "skipped", name="alert_status"),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["subscription_id"], ["bout_subscriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subscription_id", "bout_id", "fired_at_hour", name="uq_alert_idempotency"),
    )
    op.create_index(op.f("ix_alert_log_subscription_id"), "alert_log", ["subscription_id"], unique=False)
    op.create_index(op.f("ix_alert_log_user_id"), "alert_log", ["user_id"], unique=False)
    op.create_index(op.f("ix_alert_log_bout_id"), "alert_log", ["bout_id"], unique=False)
    op.create_index(op.f("ix_alert_log_fired_at"), "alert_log", ["fired_at"], unique=False)