"""Point analysis: completeness, annual statistics, mean annual rainfall, climatology, pages.

Pure functions on the daily series of one cell; no FastAPI and no NetCDF access. Completeness
follows ADR-0012 and the climatology is computed from the daily series (ADR-0008).
"""

import math
from dataclasses import dataclass

import pandas as pd

from app.services.point_service import PointResult

COMPLETENESS_PERCENT = 95
PAGE_SIZE = 365

Row = tuple[str, float | None]


@dataclass(frozen=True)
class AnnualStat:
    """Statistics of one calendar year."""

    year: int
    total_mm: float | None
    max_24h_mm: float | None
    valid_days: int
    calendar_days: int
    complete: bool


@dataclass(frozen=True)
class MeanAnnual:
    """Mean of the annual totals of complete years."""

    mean_mm: float | None
    complete_years: int


@dataclass(frozen=True)
class MonthlyClimate:
    """Mean and sample standard deviation of the totals of one calendar month."""

    month: int
    mean_mm: float | None
    std_mm: float | None
    years: int


@dataclass(frozen=True)
class DailyPage:
    """One page of the daily table."""

    page: int
    page_count: int
    rows: list[Row]


@dataclass(frozen=True)
class PointAnalysis:
    """Everything the result page and the charts show for one point request."""

    result: PointResult
    annual: list[AnnualStat]
    mean_annual: MeanAnnual
    climatology: list[MonthlyClimate]


def is_complete(valid_days: int, calendar_days: int) -> bool:
    """Return True when at least 95% of the calendar days are valid (integer arithmetic)."""
    return valid_days * 100 >= COMPLETENESS_PERCENT * calendar_days


def annual_stats(series: pd.Series, start_year: int, end_year: int) -> list[AnnualStat]:
    """Total, maximum daily value and valid days of every year from `start_year` to `end_year`.

    Days absent from `series` count as missing, so a year cut by the end of the file is
    incomplete.
    """
    full = _calendar(series, start_year, end_year)
    stats = []
    for year, values in full.groupby(full.index.year):
        valid = int(values.count())
        stats.append(
            AnnualStat(
                year=int(year),
                total_mm=_optional(values.sum(min_count=1)),
                max_24h_mm=_optional(values.max()),
                valid_days=valid,
                calendar_days=len(values),
                complete=is_complete(valid, len(values)),
            )
        )
    return stats


def mean_annual_rainfall(annual: list[AnnualStat]) -> MeanAnnual:
    """Mean of the annual totals of complete years only (ADR-0012)."""
    totals = [s.total_mm for s in annual if s.complete and s.total_mm is not None]
    if not totals:
        return MeanAnnual(mean_mm=None, complete_years=0)
    return MeanAnnual(mean_mm=sum(totals) / len(totals), complete_years=len(totals))


def monthly_climatology(series: pd.Series, start_year: int, end_year: int) -> list[MonthlyClimate]:
    """Mean and sample standard deviation (ddof=1) of complete monthly totals per month."""
    full = _calendar(series, start_year, end_year)
    grouped = full.groupby([full.index.year, full.index.month])
    months = pd.DataFrame(
        {
            "total": grouped.sum(min_count=1),
            "valid": grouped.count(),
            "days": grouped.size(),
        }
    )
    complete = months[
        [is_complete(int(v), int(d)) for v, d in zip(months["valid"], months["days"], strict=True)]
    ]
    climate = []
    for month in range(1, 13):
        totals = complete["total"][complete.index.get_level_values(1) == month]
        years = len(totals)
        climate.append(
            MonthlyClimate(
                month=month,
                mean_mm=float(totals.mean()) if years else None,
                std_mm=float(totals.std(ddof=1)) if years >= 2 else None,
                years=years,
            )
        )
    return climate


def daily_page(series: pd.Series, page_text: str) -> DailyPage:
    """Rows of one page of `PAGE_SIZE` days; invalid or out-of-range pages are clamped."""
    page_count = max(1, math.ceil(len(series) / PAGE_SIZE))
    try:
        page = int(page_text.strip())
    except ValueError:
        page = 1
    page = min(max(page, 1), page_count)
    chunk = series.iloc[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]
    rows = [
        (day, _optional(value))
        for day, value in zip(chunk.index.strftime("%Y-%m-%d"), chunk.to_numpy(), strict=True)
    ]
    return DailyPage(page=page, page_count=page_count, rows=rows)


def analyze_point(result: PointResult) -> PointAnalysis:
    """Compute the annual statistics, mean annual rainfall and climatology of a result."""
    annual = annual_stats(result.series, result.start_year, result.end_year)
    return PointAnalysis(
        result=result,
        annual=annual,
        mean_annual=mean_annual_rainfall(annual),
        climatology=monthly_climatology(result.series, result.start_year, result.end_year),
    )


def _calendar(series: pd.Series, start_year: int, end_year: int) -> pd.Series:
    days = pd.date_range(f"{start_year}-01-01", f"{end_year}-12-31", freq="D", name="date")
    return series.reindex(days)


def _optional(value: float) -> float | None:
    return None if pd.isna(value) else float(value)
