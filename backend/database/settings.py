"""settings loader for database scripts and the api app."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    real_database_url: str = Field(
        default="postgresql+asyncpg://user:pass@localhost:5432/dbname",
        alias="REAL_DATABASE_URL",
    )

    # keep configuration local to the database package by default.
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
# print the resolved url during local runs so env loading issues are obvious.
print(f"Database URL: {settings.real_database_url}")
