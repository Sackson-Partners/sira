"""
Application Configuration
Centralized settings management using Pydantic Settings
SIRA Platform v2.0 - Phase 2 MVP
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    APP_NAME: str = "SIRA Platform"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database — defaults to SQLite if DATABASE_URL not set (e.g. Railway without Postgres addon)
    DATABASE_URL: str = "sqlite:///./sira.db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    ALLOWED_ORIGINS: str = "*"

    @property
    def cors_origins(self) -> List[str]:
        if self.ALLOWED_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # Email (SMTP)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@sira-platform.com"
    EMAIL_FROM_NAME: str = "SIRA Platform"

    # File Storage
    STORAGE_TYPE: str = "local"  # local or s3
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # S3 (optional)
    S3_BUCKET_NAME: Optional[str] = None
    S3_REGION: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None

    # Monitoring
    SENTRY_DSN: Optional[str] = None
    PROMETHEUS_ENABLED: bool = False

    # Redis (for WebSocket and caching)
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Phase 2: External Integrations ---

    # Flespi Telematics (MQTT)
    FLESPI_TOKEN: Optional[str] = None
    FLESPI_MQTT_HOST: str = "mqtt.flespi.io"
    FLESPI_MQTT_PORT: int = 1883
    FLESPI_REST_URL: str = "https://flespi.io"

    # MarineTraffic AIS
    MARINETRAFFIC_API_KEY: Optional[str] = None
    MARINETRAFFIC_API_URL: str = "https://services.marinetraffic.com/api"

    # AI Intelligence Engine
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    AI_MODEL: str = "claude-sonnet-4-20250514"
    AI_MAX_TOKENS: int = 4096

    # Mapbox
    MAPBOX_ACCESS_TOKEN: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance"""
    return Settings()


settings = get_settings()
