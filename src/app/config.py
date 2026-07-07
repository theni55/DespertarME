from functools import lru_cache

from pydantic import Field
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
    espn_timeout_seconds: float = 10.0
    espn_max_retries: int = 5
    espn_circuit_breaker_fails: int = 5
    espn_circuit_breaker_open_seconds: int = 60

    # Polling & alertas (D15-D23)
    lead_minutes_default: int = 15
    buffer_intercombate_seconds: int = 300
    alert_idempotency_ttl_seconds: int = 7200
    poll_default_seconds: int = 60
    poll_prev_in_advanced_seconds: int = 10
    poll_prev_post_seconds: int = 5
    default_timezone: str = "Europe/Madrid"

    # Notifier (D23, Fase 5)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    # Auth (Fase 3)
    jwt_secret: str = "change-me-please"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
