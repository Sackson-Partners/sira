from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AIP - Alternative Investment Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite:///./aip_dev.db"

    # Security
    SECRET_KEY: str = "aip-super-secret-key-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Azure AD B2C
    AZURE_AD_B2C_TENANT_NAME: str = ""
    AZURE_AD_B2C_CLIENT_ID: str = ""
    AZURE_AD_B2C_CLIENT_SECRET: str = ""
    AZURE_AD_B2C_POLICY_NAME: str = "B2C_1_signupsignin"
    AZURE_AD_B2C_TENANT_ID: str = ""
    AZURE_AD_B2C_SCOPE: str = ""
    # Derived
    AZURE_AD_B2C_AUTHORITY: str = ""
    AZURE_AD_B2C_JWKS_URI: str = ""

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # AI
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    AI_MODEL: str = "claude-sonnet-4-6"

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_EMAIL: str = "noreply@aip-platform.com"
    EMAILS_FROM_NAME: str = "AIP Platform"

    # File storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 50

    # Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER: str = "aip-documents"

    def model_post_init(self, __context):
        if self.AZURE_AD_B2C_TENANT_NAME:
            self.AZURE_AD_B2C_AUTHORITY = (
                f"https://{self.AZURE_AD_B2C_TENANT_NAME}.b2clogin.com/"
                f"{self.AZURE_AD_B2C_TENANT_NAME}.onmicrosoft.com/"
                f"{self.AZURE_AD_B2C_POLICY_NAME}"
            )
            self.AZURE_AD_B2C_JWKS_URI = (
                f"https://{self.AZURE_AD_B2C_TENANT_NAME}.b2clogin.com/"
                f"{self.AZURE_AD_B2C_TENANT_NAME}.onmicrosoft.com/"
                f"{self.AZURE_AD_B2C_POLICY_NAME}/discovery/v2.0/keys"
            )

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
