"""Modelo de Device (Fase 7a, D37).

Un Device es el actor que sustituye a User en el modelo sin cuentas: la app
genera un UUID opaco en `expo-secure-store`, lo envía como header `X-Device-Id`
en cada request, y se registra/upserta su `fcm_token` vía `POST /api/devices`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    fcm_token: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    platform: Mapped[str | None] = mapped_column(String(10), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Europe/Madrid")
    locale: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
