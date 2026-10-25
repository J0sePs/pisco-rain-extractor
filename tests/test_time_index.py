from datetime import date

import pandas as pd
import pytest

from app.repositories.pisco_repository import (
    DatasetKind,
    DatasetStructureError,
    build_time_index,
)

START = date(1981, 1, 1)


def _range(index: pd.Index) -> tuple[str, str]:
    return index[0].strftime("%Y-%m-%d"), index[-1].strftime("%Y-%m-%d")


def test_full_daily_period() -> None:
    index = build_time_index(DatasetKind.DAILY, 16436, START)
    assert _range(index) == ("1981-01-01", "2025-12-31")


def test_leap_days_are_counted() -> None:
    index = build_time_index(DatasetKind.DAILY, 16425, START)
    assert _range(index) == ("1981-01-01", "2025-12-20")


def test_overridden_daily_start() -> None:
    index = build_time_index(DatasetKind.DAILY, 365, date(1982, 1, 1))
    assert _range(index) == ("1982-01-01", "1982-12-31")


def test_monthly_period() -> None:
    index = build_time_index(DatasetKind.MONTHLY, 540, START)
    assert _range(index) == ("1981-01-01", "2025-12-01")


def test_climatology_months() -> None:
    index = build_time_index(DatasetKind.CLIMATOLOGY, 12, None)
    assert list(index) == list(range(1, 13))


def test_unexpected_climatology_length() -> None:
    with pytest.raises(DatasetStructureError, match="expected 12 time steps, found 13"):
        build_time_index(DatasetKind.CLIMATOLOGY, 13, None)
