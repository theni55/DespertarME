"""Router de log de alertas (Fase 7a, device model).

El device ve solo sus propias alertas (no hay admin diferenciado en el MVP).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import AlertLogOut
from app.db.models import AlertLog
from app.db.models.devices import Device
from app.db.session import get_session
from app.security.device import get_current_device

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertLogOut])
async def list_alerts(
    device: Device = Depends(get_current_device),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=500),
) -> list[AlertLog]:
    stmt = (
        select(AlertLog)
        .where(AlertLog.device_id == device.id)
        .order_by(AlertLog.fired_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
