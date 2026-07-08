"""Web de usuario (Jinja2 + HTMX) — vista funcional (Fase 3 ext).

Flujo del usuario:
1. /app/register o /app/login → cookie de token.
2. /app → dashboard: eventos próximos + sus suscripciones activas.
3. /app/events → lista eventos UFC próximos (ESPN).
4. /app/events/{id} → tarjeta de combates con botón "Crear alerta".
5. /app/subscriptions (POST) → crea alerta (autodetecta combate previo).
6. /app/subscriptions/{id}/delete (POST) → cancela suscripción.
7. /app/my-alerts → historial de alertas del usuario.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import new_uuid
from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.models import AlertLog, BoutSubscription, User
from app.db.session import get_session
from app.providers.espn_ufc import EspnUfcProvider
from app.providers.models import EventSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/app", tags=["web-user"])
templates = Jinja2Templates(directory="src/app/web/templates")


# --- Auth helpers (cookie-based, iguales que admin pero sin requerir role) ---


def _set_auth_cookie(resp: RedirectResponse, token: str) -> RedirectResponse:
    resp.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, max_age=3600)
    return resp


async def _get_user_from_cookie(request: Request, session: AsyncSession) -> User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    token = token.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
    except Exception:
        return None
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    return user


def _provider() -> EspnUfcProvider:
    return EspnUfcProvider()


# --- Auth ---


@router.get("/register", response_class=HTMLResponse)
async def user_register_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "user_register.html", {})


@router.post("/register")
async def user_register(
    email: str = Form(...),
    password: str = Form(...),
    phone: str = Form(default=""),
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    existing = await session.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email ya registrado")
    user = User(
        id=new_uuid(),
        email=email,
        hashed_password=hash_password(password),
        phone_normalized=phone or None,
        timezone="Europe/Madrid",
        role="user",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    token = create_access_token(user.id, user.role)
    resp = RedirectResponse(url="/app", status_code=303)
    return _set_auth_cookie(resp, token)


@router.get("/login", response_class=HTMLResponse)
async def user_login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "user_login.html", {})


@router.post("/login")
async def user_login(
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token = create_access_token(user.id, user.role)
    resp = RedirectResponse(url="/app", status_code=303)
    return _set_auth_cookie(resp, token)


@router.post("/logout")
async def user_logout() -> RedirectResponse:
    resp = RedirectResponse(url="/app/login", status_code=303)
    resp.delete_cookie("access_token")
    return resp


# --- Dashboard ---


@router.get("", response_class=HTMLResponse)
async def user_dashboard(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Response:
    user = await _get_user_from_cookie(request, session)
    if user is None:
        return RedirectResponse(url="/app/login", status_code=303)

    subs = (
        (
            await session.execute(
                select(BoutSubscription)
                .where(BoutSubscription.user_id == user.id, BoutSubscription.status == "active")
                .order_by(BoutSubscription.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    recent_alerts = (
        (
            await session.execute(
                select(AlertLog)
                .where(AlertLog.user_id == user.id)
                .order_by(AlertLog.fired_at.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )

    events: list[EventSummary] = []
    try:
        async with _provider() as provider:
            events = list(await provider.list_upcoming_events())
    except Exception:
        logger.warning("No se pudieron cargar eventos de ESPN para el dashboard")

    return templates.TemplateResponse(
        request,
        "user_dashboard.html",
        {
            "user": user,
            "events": events,
            "subscriptions": subs,
            "recent_alerts": recent_alerts,
        },
    )


# --- Eventos ---


@router.get("/events", response_class=HTMLResponse)
async def user_events(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Response:
    user = await _get_user_from_cookie(request, session)
    if user is None:
        return RedirectResponse(url="/app/login", status_code=303)

    events: list[EventSummary] = []
    error: str | None = None
    try:
        async with _provider() as provider:
            events = list(await provider.list_upcoming_events())
    except Exception as exc:
        logger.warning("ESPN events falló: %s", exc)
        error = "No se pudieron cargar los eventos en este momento. Inténtalo más tarde."

    return templates.TemplateResponse(
        request,
        "event_list.html",
        {"user": user, "events": events, "error": error},
    )


@router.get("/events/{event_id}", response_class=HTMLResponse)
async def user_event_detail(
    request: Request,
    event_id: str,
    session: AsyncSession = Depends(get_session),
) -> Response:
    user = await _get_user_from_cookie(request, session)
    if user is None:
        return RedirectResponse(url="/app/login", status_code=303)

    event = None
    bouts: list[Any] = []
    error: str | None = None
    try:
        async with _provider() as provider:
            event = await provider.get_event_card(event_id)
            bouts = sorted(event.bouts, key=lambda b: b.match_number, reverse=True)
    except Exception as exc:
        logger.warning("ESPN event detail falló: %s", exc)
        error = "No se pudo cargar la tarjeta del evento."

    existing_subs = (
        (
            await session.execute(
                select(BoutSubscription).where(
                    BoutSubscription.user_id == user.id,
                    BoutSubscription.event_id == event_id,
                    BoutSubscription.status == "active",
                )
            )
        )
        .scalars()
        .all()
    )
    existing_bout_ids = {s.bout_id for s in existing_subs}

    return templates.TemplateResponse(
        request,
        "event_detail.html",
        {
            "user": user,
            "event": event,
            "bouts": bouts,
            "error": error,
            "existing_bout_ids": existing_bout_ids,
        },
    )


# --- Suscripciones ---


@router.post("/subscriptions/create")
async def create_alert(
    request: Request,
    event_id: str = Form(...),
    event_name: str = Form(default=""),
    bout_id: str = Form(...),
    target_match_number: int = Form(...),
    lead_minutes: int = Form(default=15),
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    user = await _get_user_from_cookie(request, session)
    if user is None:
        return RedirectResponse(url="/app/login", status_code=303)

    prev_bout_id: str | None = None
    prev_match_number: int | None = None
    try:
        async with _provider() as provider:
            event = await provider.get_event_card(event_id)
            prev = next(
                (b for b in event.bouts if b.match_number == target_match_number + 1),
                None,
            )
            if prev:
                prev_bout_id = prev.id
                prev_match_number = prev.match_number
    except Exception:
        logger.warning("No se pudo autodetectar combate previo para bout %s", bout_id)

    sub = BoutSubscription(
        id=new_uuid(),
        user_id=user.id,
        event_id=event_id,
        bout_id=bout_id,
        target_match_number=target_match_number,
        previous_bout_id=prev_bout_id,
        previous_match_number=prev_match_number,
        lead_minutes=lead_minutes,
        status="active",
    )
    session.add(sub)
    await session.commit()
    return RedirectResponse(url="/app", status_code=303)


@router.post("/subscriptions/{sub_id}/delete")
async def delete_alert(
    request: Request,
    sub_id: str,
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    user = await _get_user_from_cookie(request, session)
    if user is None:
        return RedirectResponse(url="/app/login", status_code=303)

    result = await session.execute(
        select(BoutSubscription).where(
            BoutSubscription.id == sub_id, BoutSubscription.user_id == user.id
        )
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.status = "cancelled"
        await session.commit()
    return RedirectResponse(url="/app", status_code=303)


# --- Mis alertas ---


@router.get("/my-alerts", response_class=HTMLResponse)
async def user_my_alerts(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Response:
    user = await _get_user_from_cookie(request, session)
    if user is None:
        return RedirectResponse(url="/app/login", status_code=303)

    alerts = (
        (
            await session.execute(
                select(AlertLog)
                .where(AlertLog.user_id == user.id)
                .order_by(AlertLog.fired_at.desc())
                .limit(100)
            )
        )
        .scalars()
        .all()
    )

    return templates.TemplateResponse(
        request,
        "my_alerts.html",
        {"user": user, "alerts": alerts},
    )
