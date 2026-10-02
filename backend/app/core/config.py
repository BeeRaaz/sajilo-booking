import os
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # app/core/config.py -> backend/
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
_env_file = BASE_DIR / (".env.test" if ENVIRONMENT == "test" else ".env")


class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Sajilo Booking API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Database Settings
    DATABASE_URL: str

    # JWT Settings
    JWT_SECRET_KEY: SecretStr
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 3

    # CORS Settings
    CORS_ORIGINS: list[str] = []

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def guard_test_database(cls, value: str, info) -> str:
        if info.data.get("ENVIRONMENT") == "test" and "_test" not in value:
            raise ValueError(
                "ENVIRONMENT=test requires a database name containing '_test'"
            )
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]


settings = get_settings()
