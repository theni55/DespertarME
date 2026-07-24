from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "INFO"

    # Postgres
    database_url: str = Field(
        default="postgresql+asyncpg://avisador:changeme@localhost:5432/avisador"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # ESPN Core API (D9, D13)
    espn_base_url: str = "https://sports.core.api.espn.com/v2"
    espn_league: str = "ufc"
    espn_tennis_league: str = "atp"  # D46
    espn_timeout_seconds: float = 10.0
    espn_max_retries: int = 5
    espn_circuit_breaker_fails: int = 5
    espn_circuit_breaker_open_seconds: int = 60
    athlete_cache_ttl_seconds: int = 604800  # 7 dias

    # Polling & alertas (D15-D23, D48)
    scheduler_enabled: bool = True
    lead_minutes_default: int = 15
    buffer_intercombate_seconds: int = 600  # 10 min MMA (revisado D45)
    buffer_intermatch_tennis_seconds: int = 900  # 15 min tenis (D48)
    alert_idempotency_ttl_seconds: int = 7200
    poll_default_seconds: int = 60
    poll_prev_in_advanced_seconds: int = 10
    poll_prev_post_seconds: int = 5
    default_timezone: str = "Europe/Madrid"

    # FCM (D40) — credenciales del service account de Firebase.
    # Se acepta una ruta a un JSON o el JSON inline (preferido en PaaS).
    fcm_credentials_path: str | None = None
    fcm_credentials_json: str | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        """Normaliza URLs de PaaS (Railway da `postgresql://`) al driver async."""
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
