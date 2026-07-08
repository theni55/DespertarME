import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.routes import alert_log, auth, subscriptions, users
from app.config import settings
from app.web.admin import router as admin_router
from app.web.user import router as user_router

logging.basicConfig(
    level=settings.app_log_level,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Avisador",
    description="Avisador de alertas deportivas en tiempo real (MMA/Boxeo/Tenis)",
    version="0.1.0",
)

# API REST
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(subscriptions.router)
app.include_router(alert_log.router)

# Web
app.include_router(admin_router)
app.include_router(user_router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    logger.debug("healthcheck requested")
    return {"status": "ok", "env": settings.app_env}


@app.get("/", tags=["meta"])
async def root() -> RedirectResponse:
    return RedirectResponse(url="/app", status_code=302)
