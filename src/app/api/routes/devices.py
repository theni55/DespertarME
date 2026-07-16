"""Router de devices (Fase 7a, D37 device model).

- `POST /api/devices`: registro/upsert. El cliente genera el UUID con
  `expo-secure-store` y lo envía; el backend persiste/actualiza el `fcm_token`.
- `DELETE /api/devices/me`: marque el device como inactivo (soft delete).
- `POST /api/devices/me/test-alarm`: envía un push tipo `fire` para validar la
  plomería del sonido (el handler foreground de la app arranca el `AlarmService`
  del spike en Fase 7b).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import DeviceCreate, DeviceOut
from app.db.models.devices import Device
from app.db.session import get_session
from app.notifiers import get_notifier
from app.notifiers.base import AlertPayload
from app.security.device import get_current_device

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.post("", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
async def register_device(
    body: DeviceCreate,
    session: AsyncSession = Depends(get_session),
) -> Device:
    """Crea o actualiza un device. Si el `device_id` ya existe, upsert del token."""
    result = await session.execute(select(Device).where(Device.id == body.device_id))
    device = result.scalar_one_or_none()
    if device is None:
        device = Device(
            id=body.device_id,
            fcm_token=body.fcm_token,
            platform=body.platform,
            timezone=body.timezone,
            locale=body.locale,
            is_active=True,
        )
        session.add(device)
    else:
        device.fcm_token = body.fcm_token
        if body.platform is not None:
            device.platform = body.platform
        if body.locale is not None:
            device.locale = body.locale
        device.timezone = body.timezone
        device.is_active = True
    await session.commit()
    await session.refresh(device)
    return device


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_my_device(
    device: Device = Depends(get_current_device),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Soft delete: marca el device como inactivo (conserva el historial)."""
    device.is_active = False
    await session.commit()


@router.post("/me/test-alarm", status_code=status.HTTP_200_OK)
async def test_alarm(
    device: Device = Depends(get_current_device),
) -> dict[str, str | bool]:
    """Envía un push `fire` al device para validar el sonido de alarma."""
    if not device.fcm_token:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El device no tiene fcm_token configurado.",
        )
    payload = AlertPayload(
        device_id=device.id,
        fcm_token=device.fcm_token,
        message_type="fire",
        event_id="test",
        bout_id="test",
        event_name="DespertarME — Test de alarma",
        fighters=None,
    )
    notifier = get_notifier()
    result = await notifier.send(payload)
    return {
        "success": result.success,
        "message_id": result.message_id or "",
        "error": result.error or "",
    }
