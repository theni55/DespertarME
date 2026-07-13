from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_JWT_DEFAULT = "change-me-please"


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
    athlete_cache_ttl_seconds: int = 604800  # 7 días (los atletas cambian rara vez)

    # Polling & alertas (D15-D23)
    scheduler_enabled: bool = True
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
    jwt_secret: str = _INSECURE_JWT_DEFAULT
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

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

    @model_validator(mode="after")
    def _check_production_secrets(self) -> "Settings":
        """En producción el JWT_SECRET no puede ser el default inseguro."""
        if self.app_env == "production" and self.jwt_secret == _INSECURE_JWT_DEFAULT:
            raise ValueError(
                "JWT_SECRET debe configurarse en producción (no uses el default). "
                'Genera uno con: python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
