"""Router de log de alertas (Fase 3).

Usuario ve sus propias alertas; admin ve todas.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import AlertLogOut
from app.auth.dependencies import get_current_user
from app.db.models import AlertLog, User
from app.db.session import get_session

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertLogOut])
async def list_alerts(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=500),
) -> list[AlertLog]:
    stmt = select(AlertLog).order_by(AlertLog.fired_at.desc()).limit(limit)
    if user.role != "admin":
        stmt = stmt.where(AlertLog.user_id == user.id)
    result = await session.execute(stmt)
    return list(result.scalars().all())
