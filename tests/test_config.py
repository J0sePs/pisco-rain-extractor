from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in (
        "DATA_DIR",
        "DAILY_START_DATE",
        "MONTHLY_START_DATE",
        "BASIN_STORE_DIR",
        "BASIN_TTL_HOURS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)  # ignore any local .env file


def test_defaults() -> None:
    settings = Settings()
    assert settings.data_dir == Path("data")
    assert settings.daily_start_date == date(1981, 1, 1)
    assert settings.monthly_start_date == date(1981, 1, 1)
    assert settings.basin_store_dir == Path("uploads/basins")
    assert settings.basin_ttl_hours == 24


def test_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", "/tmp/pisco")
    monkeypatch.setenv("DAILY_START_DATE", "1982-01-01")
    settings = Settings()
    assert settings.data_dir == Path("/tmp/pisco")
    assert settings.daily_start_date == date(1982, 1, 1)


def test_invalid_start_date(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DAILY_START_DATE", "1981-13-01")
    with pytest.raises(ValidationError, match="daily_start_date"):
        Settings()


def test_basin_store_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BASIN_STORE_DIR", "/tmp/basins")
    monkeypatch.setenv("BASIN_TTL_HOURS", "2")
    settings = Settings()
    assert settings.basin_store_dir == Path("/tmp/basins")
    assert settings.basin_ttl_hours == 2
