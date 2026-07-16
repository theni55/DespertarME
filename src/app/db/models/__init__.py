"""Exporta todos los modelos para que Alembic y SQLAlchemy los detecten."""

from app.db.models.alert_log import AlertLog
from app.db.models.base import Base
from app.db.models.devices import Device
from app.db.models.subscriptions import BoutSubscription

__all__ = ["AlertLog", "Base", "BoutSubscription", "Device"]
