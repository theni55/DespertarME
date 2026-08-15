"""Modelo de log de alertas (Fase 2b + Fase 7a).

Audita cada alerta disparada. UNIQUE constraint `(subscription_id, bout_id,
fired_at_epoch_hour)` para idempotencia en BD (D16 / E6).

`fired_at_epoch_hour` es `int(timestamp) // 3600` (E6): la versión anterior
`now.hour` colisionaba entre días distintos a la misma hora local y permitía
duplicados si un retry cruzaba el cambio de hora. Hora absoluta UTC elimina
ambas clases de colisión.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base


class AlertLog(Base):
    __tablename__ = "alert_log"
    __table_args__ = (
        # A10: la idempotencia real solo aplica a mensajes terminales
        # `started`/`cancelled`. Las filas `update` son audit puro y se guardan
        # todas (varias por hora, si la estimacion se mueve). Un `update` y un
        # `started` en la misma hora ya no colisionan.
        Index(
            "uq_alert_status_idem",
            "subscription_id",
            "bout_id",
            "message_type",
            unique=True,
            sqlite_where=text("message_type IN ('started', 'cancelled')"),
            postgresql_where=text("message_type IN ('started', 'cancelled')"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    subscription_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("bout_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bout_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    message_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    fired_at_epoch_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    notifier_response: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("fired", "failed", "skipped", name="alert_status"),
        default="fired",
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    subscription: Mapped[BoutSubscription] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="alerts"
    )
