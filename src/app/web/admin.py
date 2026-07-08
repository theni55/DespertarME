"""Panel admin web (Jinja2 + HTMX, D21).

Vistas:
- /admin/login: login del admin (form POST → cookie de token).
- /admin: dashboard con lista de usuarios, suscripciones y alertas.
- /admin/users: gestión de usuarios.
- /admin/alerts: log de alertas.

Monolítico en el mismo proceso FastAPI. HTMX para interacciones sin reload.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import create_access_token, decode_access_token
from app.db.models import AlertLog, BoutSubscription, User
from app.db.session import get_session

router = APIRouter(prefix="/admin", tags=["web"])
templates = Jinja2Templates(directory="src/app/web/templates")


def _set_auth_cookie(resp: RedirectResponse, token: str) -> RedirectResponse:
    resp.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, max_age=3600)
    return resp


async def _get_admin_from_cookie(request: Request, session: AsyncSession) -> User | None:
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
    if user is None or user.role != "admin":
        return None
    return user


# --- Login ---


@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "login.html", {})


@router.post("/login")
async def admin_login(
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    from app.auth.security import verify_password

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Requiere rol admin")
    token = create_access_token(user.id, user.role)
    resp = RedirectResponse(url="/admin", status_code=303)
    return _set_auth_cookie(resp, token)


@router.post("/logout")
async def admin_logout() -> RedirectResponse:
    resp = RedirectResponse(url="/admin/login", status_code=303)
    resp.delete_cookie("access_token")
    return resp


# --- Dashboard ---


@router.get("", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Response:
    admin = await _get_admin_from_cookie(request, session)
    if admin is None:
        return RedirectResponse(url="/admin/login", status_code=303)

    users_count = (await session.execute(select(func.count(User.id)))).scalar_one()
    subs_count = (
        await session.execute(
            select(func.count(BoutSubscription.id)).where(BoutSubscription.status == "active")
        )
    ).scalar_one()
    alerts_count = (await session.execute(select(func.count(AlertLog.id)))).scalar_one()

    recent_alerts = (
        (await session.execute(select(AlertLog).order_by(AlertLog.fired_at.desc()).limit(10)))
        .scalars()
        .all()
    )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "admin": admin,
            "users_count": users_count,
            "subs_count": subs_count,
            "alerts_count": alerts_count,
            "recent_alerts": recent_alerts,
            "now": datetime.now(UTC),
        },
    )


# --- Usuarios ---


@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Response:
    admin = await _get_admin_from_cookie(request, session)
    if admin is None:
        return RedirectResponse(url="/admin/login", status_code=303)

    users = (await session.execute(select(User).order_by(User.created_at.desc()))).scalars().all()

    return templates.TemplateResponse(
        request,
        "users.html",
        {"admin": admin, "users": users},
    )


# --- Alertas ---


@router.get("/alerts", response_class=HTMLResponse)
async def admin_alerts(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Response:
    admin = await _get_admin_from_cookie(request, session)
    if admin is None:
        return RedirectResponse(url="/admin/login", status_code=303)

    alerts = (
        (await session.execute(select(AlertLog).order_by(AlertLog.fired_at.desc()).limit(100)))
        .scalars()
        .all()
    )

    return templates.TemplateResponse(
        request,
        "alerts.html",
        {"admin": admin, "alerts": alerts},
    )
