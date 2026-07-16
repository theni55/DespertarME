import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import alert_log, devices, events, subscriptions
from app.config import settings
from app.scheduler import poller_scheduler

logging.basicConfig(
    level=settings.app_log_level,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Arranca/para el scheduler del Poller y los recursos del router de events."""
    poller_scheduler.start()
    try:
        yield
    finally:
        await poller_scheduler.stop()
        # Cerrar los singletons del router events (httpx client + redis).
        from app.api.routes.events import close_events_resources

        await close_events_resources()


app = FastAPI(
    title="DespertarME",
    description="Avisador de alertas deportivas en tiempo real (MMA/Boxeo/Tenis)",
    version="0.1.0",
    lifespan=lifespan,
)

# API REST (Fase 7a — device model, sin User/Twilio).
app.include_router(devices.router)
app.include_router(events.router)
app.include_router(subscriptions.router)
app.include_router(alert_log.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    logger.debug("healthcheck requested")
    return {"status": "ok", "env": settings.app_env}
