"""Application settings loaded from environment variables (and an optional .env file)."""

from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    The calendar start dates are the single source of truth for turning the integer PISCOp
    time index into dates (ADR-0007); no other module defines them.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = Path("data")
    daily_start_date: date = date(1981, 1, 1)
    monthly_start_date: date = date(1981, 1, 1)


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
