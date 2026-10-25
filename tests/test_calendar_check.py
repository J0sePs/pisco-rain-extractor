import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.services import calendar_check
from app.services.calendar_check import alignment_scores, best_offset


@pytest.fixture
def daily() -> pd.Series:
    """Three years of irregular daily rainfall (deterministic)."""
    days = pd.date_range("1981-01-01", "1983-12-31", freq="D")
    values = np.random.default_rng(7).gamma(0.5, 4.0, len(days))
    return pd.Series(values, index=days)


def _monthly_sums(daily: pd.Series) -> pd.Series:
    sums = daily.groupby(daily.index.to_period("M")).sum()
    sums.index = sums.index.to_timestamp()
    return sums


def test_aligned_files(daily: pd.Series) -> None:
    scores = alignment_scores(daily, _monthly_sums(daily))
    assert best_offset(scores) == 0
    aligned = next(s for s in scores if s.offset_days == 0)
    assert aligned.mean_abs_diff_mm == pytest.approx(0.0)
    assert aligned.max_abs_diff_mm == pytest.approx(0.0)


def test_daily_one_day_late(daily: pd.Series) -> None:
    late = pd.Series(daily.to_numpy(), index=daily.index + pd.Timedelta(days=1))
    assert best_offset(alignment_scores(late, _monthly_sums(daily))) == -1


def test_same_months_for_every_offset(daily: pd.Series) -> None:
    scores = alignment_scores(daily, _monthly_sums(daily))
    assert [s.offset_days for s in scores] == [-2, -1, 0, 1, 2]
    assert {s.months for s in scores} == {34}  # 36 months minus the first and the last


def test_module_imports_neither_fastapi_nor_xarray() -> None:
    tree = ast.parse(Path(calendar_check.__file__).read_text(encoding="utf-8"))
    modules = {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not modules & {"fastapi", "starlette", "xarray"}
