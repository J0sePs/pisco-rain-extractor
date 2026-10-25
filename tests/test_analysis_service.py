import ast
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from app.repositories.pisco_repository import CellRef
from app.services import analysis_service
from app.services.analysis_service import (
    AnnualStat,
    analyze_basin,
    analyze_point,
    annual_stats,
    daily_page,
    is_complete,
    mean_annual_rainfall,
    monthly_climatology,
)
from app.services.basin_geometry import BasinGeometry
from app.services.basin_service import BasinResult
from app.services.point_service import PointResult


def _series(start: str, end: str, value: float = 0.0) -> pd.Series:
    days = pd.date_range(start, end, freq="D", name="date")
    return pd.Series(value, index=days, dtype=float, name="precipitation_mm")


def _missing(series: pd.Series, n: int, start: str) -> pd.Series:
    """Copy of `series` with `n` consecutive missing days from `start`."""
    copy = series.copy()
    first = copy.index.get_loc(pd.Timestamp(start))
    copy.iloc[first : first + n] = np.nan
    return copy


def _stat(year: int, total: float, complete: bool) -> AnnualStat:
    return AnnualStat(year, total, None, 365 if complete else 100, 365, complete)


# --- completeness and annual statistics ---------------------------------------------------


def test_one_rainy_day() -> None:
    series = _series("1981-01-01", "1981-12-31")
    series[pd.Timestamp("1981-07-15")] = 50.0
    [stat] = annual_stats(series, 1981, 1981)
    assert (stat.total_mm, stat.max_24h_mm, stat.valid_days) == (50.0, 50.0, 365)
    assert stat.complete


@pytest.mark.parametrize(
    ("year", "missing", "complete"),
    [(1981, 18, True), (1981, 19, False), (2000, 18, True), (2000, 19, False)],
)
def test_threshold(year: int, missing: int, complete: bool) -> None:
    series = _missing(_series(f"{year}-01-01", f"{year}-12-31", 1.0), missing, f"{year}-03-01")
    [stat] = annual_stats(series, year, year)
    assert stat.valid_days == stat.calendar_days - missing
    assert stat.complete is complete


def test_is_complete_limits() -> None:
    assert is_complete(347, 365) and not is_complete(346, 365)
    assert is_complete(348, 366) and not is_complete(347, 366)


def test_year_cut_by_end_of_file() -> None:
    [stat] = annual_stats(_series("2025-01-01", "2025-06-30", 1.0), 2025, 2025)
    assert (stat.valid_days, stat.calendar_days, stat.complete) == (181, 365, False)


def test_year_with_every_day_missing() -> None:
    series = _missing(_series("1981-01-01", "1982-12-31", 1.0), 365, "1982-01-01")
    first, second = annual_stats(series, 1981, 1982)
    assert first.total_mm == 365.0
    assert (second.total_mm, second.max_24h_mm, second.valid_days) == (None, None, 0)
    assert not second.complete


def test_mean_annual_excludes_incomplete_years() -> None:
    mean = mean_annual_rainfall(
        [_stat(1981, 400.0, True), _stat(1982, 600.0, True), _stat(1983, 100.0, False)]
    )
    assert (mean.mean_mm, mean.complete_years) == (500.0, 2)


def test_mean_annual_without_complete_year() -> None:
    mean = mean_annual_rainfall([_stat(1981, 100.0, False)])
    assert (mean.mean_mm, mean.complete_years) == (None, 0)


# --- climatology --------------------------------------------------------------------------


def _january_totals(totals: dict[int, float]) -> pd.Series:
    """Daily series for whole years with each January spread evenly to the given total."""
    years = sorted(totals)
    series = _series(f"{years[0]}-01-01", f"{years[-1]}-12-31")
    for year, total in totals.items():
        january = (series.index.year == year) & (series.index.month == 1)
        series[january] = total / 31
    return series


def test_january_mean_and_std() -> None:
    climate = monthly_climatology(_january_totals({1981: 100.0, 1982: 140.0}), 1981, 1982)
    january = climate[0]
    assert january.mean_mm == pytest.approx(120.0)
    assert january.std_mm == pytest.approx(28.28, abs=0.01)
    assert january.years == 2
    assert len(climate) == 12


def test_incomplete_month_excluded() -> None:
    series = _january_totals({1981: 100.0, 1982: 140.0})
    series = _missing(_missing(series, 1, "1981-01-10"), 2, "1982-01-10")  # 30/31 and 29/31
    january = monthly_climatology(series, 1981, 1982)[0]
    assert january.years == 1
    assert january.mean_mm == pytest.approx(100.0 * 30 / 31)
    assert january.std_mm is None


def test_single_year() -> None:
    series = _series("2000-01-01", "2000-12-31", 2.0)
    climate = monthly_climatology(series, 2000, 2000)
    assert climate[1].mean_mm == pytest.approx(58.0)  # 29 days of February 2000
    assert all(month.std_mm is None and month.years == 1 for month in climate)


def test_month_without_valid_data() -> None:
    series = _series("1981-01-01", "1982-12-31", 1.0)
    series = _missing(_missing(series, 2, "1981-02-01"), 2, "1982-02-01")
    climate = monthly_climatology(series, 1981, 1982)
    assert (climate[1].mean_mm, climate[1].std_mm, climate[1].years) == (None, None, 0)
    assert climate[0].years == 2


# --- pagination and full analysis ---------------------------------------------------------


@pytest.fixture
def five_years() -> pd.Series:
    return _missing(_series("1981-01-01", "1985-12-31", 1.5), 1, "1981-01-03")


def test_page_count_and_last_page(five_years: pd.Series) -> None:
    page = daily_page(five_years, "6")
    assert (page.page, page.page_count) == (6, 6)
    assert page.rows == [("1985-12-31", 1.5)]


def test_second_page(five_years: pd.Series) -> None:
    page = daily_page(five_years, "2")
    assert page.rows[0][0] == "1982-01-01"
    assert len(page.rows) == 365


@pytest.mark.parametrize(("text", "expected"), [("99", 6), ("0", 1), ("abc", 1), ("", 1)])
def test_page_clamped(five_years: pd.Series, text: str, expected: int) -> None:
    assert daily_page(five_years, text).page == expected


def test_missing_day_row(five_years: pd.Series) -> None:
    assert daily_page(five_years, "1").rows[2] == ("1981-01-03", None)


def test_analyze_point(five_years: pd.Series) -> None:
    result = PointResult(
        lon=-76.1390222,
        lat=-12.2935861,
        cell=CellRef(lat_index=2, lon_index=2, lon=-76.15, lat=-12.25),
        distance_km=4.991,
        resolution_deg=0.1,
        start_year=1981,
        end_year=1985,
        period_start=date(1981, 1, 1),
        period_end=date(1985, 12, 31),
        total_days=1826,
        missing_days=1,
        series=five_years,
    )
    analysis = analyze_point(result)
    assert [s.year for s in analysis.annual] == [1981, 1982, 1983, 1984, 1985]
    assert len(analysis.climatology) == 12
    assert analysis.mean_annual.complete_years == 5


def test_module_imports_neither_fastapi_nor_xarray() -> None:
    tree = ast.parse(Path(analysis_service.__file__).read_text(encoding="utf-8"))
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


def test_basin_series_analyzed_like_a_point() -> None:
    series = _missing(_series("1981-01-01", "1983-12-31", 2.5), 20, "1982-03-01")
    point = analyze_point(
        PointResult(
            lon=-76.15,
            lat=-12.25,
            cell=CellRef(lat_index=2, lon_index=2, lon=-76.15, lat=-12.25),
            distance_km=0.0,
            resolution_deg=0.1,
            start_year=1981,
            end_year=1983,
            period_start=date(1981, 1, 1),
            period_end=date(1983, 12, 31),
            total_days=len(series),
            missing_days=int(series.isna().sum()),
            series=series,
        )
    )
    basin = analyze_basin(
        BasinResult(
            basin=BasinGeometry("basin.geojson", 1, box(-76.3, -12.4, -76.1, -12.2)),
            area_km2=481.4,
            centroid_lon=-76.2,
            centroid_lat=-12.3,
            fallback=False,
            cells=[],
            resolution_deg=0.1,
            start_year=1981,
            end_year=1983,
            period_start=date(1981, 1, 1),
            period_end=date(1983, 12, 31),
            total_days=len(series),
            missing_days=int(series.isna().sum()),
            series=series,
        )
    )
    assert basin.annual == point.annual
    assert basin.mean_annual == point.mean_annual
    assert basin.climatology == point.climatology
    assert not basin.annual[1].complete  # 1982: 20 missing days
