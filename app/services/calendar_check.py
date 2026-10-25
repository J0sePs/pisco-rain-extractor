"""Calendar alignment check: daily monthly sums vs the monthly file at several day offsets.

A diagnostic for the calendar of ADR-0007 (design D10); it is not used by the analysis.
"""

from dataclasses import dataclass

import pandas as pd

DEFAULT_OFFSETS = range(-2, 3)


@dataclass(frozen=True)
class OffsetScore:
    """Agreement between the re-dated daily series and the monthly series."""

    offset_days: int
    months: int
    mean_abs_diff_mm: float
    max_abs_diff_mm: float


def alignment_scores(
    daily: pd.Series, monthly: pd.Series, offsets: range = DEFAULT_OFFSETS
) -> list[OffsetScore]:
    """Score each offset: re-date the daily index by k days, sum per month, compare.

    Every offset is compared on the same months: those of `monthly` strictly inside the daily
    period (a shift cuts the first and last daily month) where every sum is defined.
    """
    first = daily.index[0].to_period("M")
    last = daily.index[-1].to_period("M")
    months = monthly.index.to_period("M")
    inside = monthly[(months > first) & (months < last)].dropna()
    inside.index = inside.index.to_period("M")

    sums = {}
    for k in offsets:
        shifted = pd.Series(daily.to_numpy(), index=daily.index + pd.Timedelta(days=k))
        sums[k] = shifted.groupby(shifted.index.to_period("M")).sum(min_count=1)
    common = inside.index
    for total in sums.values():
        common = common.intersection(total.dropna().index)

    scores = []
    for k, total in sums.items():
        diff = (total.loc[common] - inside.loc[common]).abs()
        scores.append(
            OffsetScore(
                offset_days=k,
                months=len(common),
                mean_abs_diff_mm=float(diff.mean()),
                max_abs_diff_mm=float(diff.max()),
            )
        )
    return scores


def best_offset(scores: list[OffsetScore]) -> int:
    """Offset with the smallest mean absolute difference."""
    return min(scores, key=lambda s: s.mean_abs_diff_mm).offset_days
