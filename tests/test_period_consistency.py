from datetime import date

from app.repositories.pisco_repository import (
    DatasetKind,
    build_time_index,
    check_period_consistency,
)

START = date(1981, 1, 1)


def _check(daily_steps: int, monthly_steps: int) -> str | None:
    daily = build_time_index(DatasetKind.DAILY, daily_steps, START)
    monthly = build_time_index(DatasetKind.MONTHLY, monthly_steps, START)
    return check_period_consistency(daily, monthly)


def test_periods_agree() -> None:
    assert _check(16436, 540) is None


def test_daily_file_ends_mid_month() -> None:
    assert _check(16426, 540) is None  # daily ends 2025-12-21, still 2025-12


def test_periods_disagree() -> None:
    assert _check(16436, 528) == (
        "Period mismatch: daily file ends in 2025-12, monthly file ends in 2024-12"
    )
