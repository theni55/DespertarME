import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.routes import alert_log, auth, subscriptions, users
from app.config import settings
from app.scheduler import poller_scheduler
from app.web.admin import router as admin_router
from app.web.user import router as user_router

logging.basicConfig(
    level=settings.app_log_level,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Arranca/para el scheduler del Poller junto con la app (D31)."""
    poller_scheduler.start()
    try:
        yield
    finally:
        await poller_scheduler.stop()


class StaticCacheMiddleware(BaseHTTPMiddleware):
    """Añade cabeceras Cache-Control a los assets estáticos (D35)."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/static/fonts/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=86400"
        return response


app = FastAPI(
    title="Avisador",
    description="Avisador de alertas deportivas en tiempo real (MMA/Boxeo/Tenis)",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(StaticCacheMiddleware)

# API REST
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(subscriptions.router)
app.include_router(alert_log.router)

# Web
app.include_router(admin_router)
app.include_router(user_router)

# Assets estáticos (CSS/JS/fuentes propios, sin build step — D35)
app.mount("/static", StaticFiles(directory="src/app/web/static"), name="static")

_landing_templates = Jinja2Templates(directory="src/app/web/templates")


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    logger.debug("healthcheck requested")
    return {"status": "ok", "env": settings.app_env}


@app.get("/", tags=["meta"], response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    """Landing pública (D35): siempre se muestra, incluso con sesión activa."""
    return _landing_templates.TemplateResponse(request, "landing.html", {})
