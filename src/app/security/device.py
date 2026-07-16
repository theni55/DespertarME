"""Dependencia de auth de Device (Fase 7a, sustituye a `get_current_user`).

El cliente genera un UUID opaco con `expo-secure-store` y lo envía como header
`X-Device-Id` en cada request. El backend valida que el device exista y esté
activo (no autocrea: el registro explícito se hace vía `POST /api/devices`).
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.devices import Device
from app.db.session import get_session


async def get_current_device(
    x_device_id: str | None = Header(default=None, alias="X-Device-Id"),
    session: AsyncSession = Depends(get_session),
) -> Device:
    """Lee el header `X-Device-Id`, busca el Device en BD, valida activo.

    Devuelve 401 si falta el header o el device no está registrado, 403 si está
    inactivo. Usar como dependencia FastAPI: `device: Device = Depends(get_current_device)`.
    """
    if not x_device_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta header X-Device-Id",
        )
    device_id = x_device_id.strip()
    result = await session.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device no registrado. Llama a POST /api/devices primero.",
        )
    if not device.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device inactivo",
        )
    return device


__all__ = ["get_current_device"]
