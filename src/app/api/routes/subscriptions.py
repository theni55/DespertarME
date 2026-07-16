"""Router de suscripciones de combate (Fase 7a, device model).

CRUD de bout_subscriptions para el device autenticado vía header `X-Device-Id`.
El cliente NO manda `previous_bout_id` (E4): el backend lo deriva en runtime
desde la card fresca en cada poll.

UNIQUE `(device_id, bout_id)` (E6) impide re-suscribirse al mismo combate:
el segundo intento devuelve 409.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import BoutSubscriptionCreate, BoutSubscriptionOut
from app.common.ids import new_uuid
from app.db.models import BoutSubscription
from app.db.models.devices import Device
from app.db.session import get_session
from app.security.device import get_current_device

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


@router.get("", response_model=list[BoutSubscriptionOut])
async def list_my_subscriptions(
    device: Device = Depends(get_current_device),
    session: AsyncSession = Depends(get_session),
) -> list[BoutSubscription]:
    result = await session.execute(
        select(BoutSubscription).where(BoutSubscription.device_id == device.id)
    )
    return list(result.scalars().all())


@router.post(
    "",
    response_model=BoutSubscriptionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription(
    body: BoutSubscriptionCreate,
    device: Device = Depends(get_current_device),
    session: AsyncSession = Depends(get_session),
) -> BoutSubscription:
    sub = BoutSubscription(
        id=new_uuid(),
        device_id=device.id,
        event_id=body.event_id,
        bout_id=body.bout_id,
        target_match_number=body.target_match_number,
        lead_minutes=body.lead_minutes,
        status="active",
    )
    session.add(sub)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una suscripción activa para este combate en este device.",
        ) from None
    await session.refresh(sub)
    return sub


@router.delete("/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    sub_id: str,
    device: Device = Depends(get_current_device),
    session: AsyncSession = Depends(get_session),
) -> None:
    result = await session.execute(
        select(BoutSubscription).where(
            BoutSubscription.id == sub_id, BoutSubscription.device_id == device.id
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")
    await session.delete(sub)
    await session.commit()
