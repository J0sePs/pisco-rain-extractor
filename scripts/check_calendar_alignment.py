"""Check that the daily calendar is aligned with the monthly file (design D10, ADR-0007).

Sums the daily values of one cell per month, re-dated by -2..+2 days, compares them with the
same cell of the monthly file and exits 1 unless offset 0 gives the smallest difference.
Reads two single cells (ADR-0005). Usage:

    uv run python scripts/check_calendar_alignment.py [--lon -76.15 --lat -12.25]
"""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.repositories.pisco_repository import DatasetKind, PiscoRepository  # noqa: E402
from app.services.calendar_check import alignment_scores, best_offset  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    """Print the offset table and return the exit code (0 when offset 0 wins)."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lon", type=float, default=-76.15)
    parser.add_argument("--lat", type=float, default=-12.25)
    args = parser.parse_args(argv)

    repo = PiscoRepository.open(get_settings())
    try:
        daily_index = repo.time_index(DatasetKind.DAILY)
        if daily_index is None or repo.time_index(DatasetKind.MONTHLY) is None:
            print("The daily and monthly files are both required.", file=sys.stderr)
            return 2
        daily_cell = repo.nearest_cell(args.lon, args.lat)
        monthly_cell = repo.nearest_cell(args.lon, args.lat, DatasetKind.MONTHLY)
        daily = repo.read_cell_series(
            daily_cell, daily_index[0].date(), date(daily_index[-1].year, 12, 31)
        )
        monthly = repo.read_monthly_cell_series(monthly_cell)
    finally:
        repo.close()

    scores = alignment_scores(daily, monthly)
    print(
        f"Daily cell {daily_cell.lon}, {daily_cell.lat}; monthly cell {monthly_cell.lon}, "
        f"{monthly_cell.lat}; {scores[0].months} months compared"
    )
    print(f"{'offset':>6}  {'mean abs diff (mm)':>18}  {'max abs diff (mm)':>17}")
    for s in scores:
        print(f"{s.offset_days:>+6d}  {s.mean_abs_diff_mm:>18.3f}  {s.max_abs_diff_mm:>17.2f}")
    best = best_offset(scores)
    print(f"Best offset: {best:+d} day(s) -> {'aligned' if best == 0 else 'NOT aligned'}")
    return 0 if best == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
