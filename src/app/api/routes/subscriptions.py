"""Router de suscripciones de combate (Fase 3).

CRUD de bout_subscriptions para el usuario autenticado.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import BoutSubscriptionCreate, BoutSubscriptionOut
from app.auth.dependencies import get_current_user, new_uuid
from app.db.models import BoutSubscription, User
from app.db.session import get_session

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


@router.get("", response_model=list[BoutSubscriptionOut])
async def list_my_subscriptions(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[BoutSubscription]:
    result = await session.execute(
        select(BoutSubscription).where(BoutSubscription.user_id == user.id)
    )
    return list(result.scalars().all())


@router.post("", response_model=BoutSubscriptionOut, status_code=201)
async def create_subscription(
    body: BoutSubscriptionCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BoutSubscription:
    sub = BoutSubscription(
        id=new_uuid(),
        user_id=user.id,
        event_id=body.event_id,
        bout_id=body.bout_id,
        target_match_number=body.target_match_number,
        previous_bout_id=body.previous_bout_id,
        previous_match_number=body.previous_match_number,
        lead_minutes=body.lead_minutes,
        status="active",
    )
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return sub


@router.delete("/{sub_id}", status_code=204)
async def delete_subscription(
    sub_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    result = await session.execute(
        select(BoutSubscription).where(
            BoutSubscription.id == sub_id, BoutSubscription.user_id == user.id
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")
    await session.delete(sub)
    await session.commit()
