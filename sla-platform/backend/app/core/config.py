from pydantic_settings import BaseSettings

from app.core.version import VERSION


class Settings(BaseSettings):
    PROJECT_NAME: str = "SLA Analytics Platform"
    VERSION: str = VERSION
    CORS_ORIGINS: list[str] = ["http://localhost:80", "http://localhost:5173"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://sla_user:sla_password@postgres:5432/sla_platform"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # Security
    SECRET_KEY: str = "sla-platform-secret-key-change-in-production-2026"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENCRYPTION_ENABLED: bool = True

    # Storage
    DATA_DIR: str = "/data"

    # HA
    REDIS_SENTINEL_HOSTS: list[str] = []
    POSTGRES_REPLICA_URL: str = ""
    DEGRADATION_MODE: str = "auto"  # auto, readonly, full

    # Integration defaults
    TELEGRAM_BOT_TOKEN: str = ""
    SLACK_WEBHOOK_URL: str = ""
    JIRA_BASE_URL: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
