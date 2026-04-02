from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    real_database_url: str = Field(
        default="postgresql+asyncpg://user:pass@localhost:5432/dbname",
        alias="REAL_DATABASE_URL"
    )

    # real_database_url: str = Field(
    #     ...,
    #     alias="REAL_DATABASE_URL"
    # )

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
print(f"Database URL: {settings.real_database_url}")  # Для отладки