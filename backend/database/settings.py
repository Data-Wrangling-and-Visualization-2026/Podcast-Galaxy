from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    real_database_url: str = Field(
        default="postgresql+asyncpg://postgres:gosha14062007@localhost:5432/proba1",
        alias="REAL_DATABASE_URL"
    )

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
print(f"Database URL: {settings.real_database_url}")  # Для отладки