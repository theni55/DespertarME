import logging

from fastapi import FastAPI

from app.config import settings

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


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    logger.debug("healthcheck requested")
    return {"status": "ok", "env": settings.app_env}


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"name": "avisador", "version": "0.1.0", "docs": "/docs"}
