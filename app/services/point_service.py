"""Point extraction: validate the request, pick the nearest cell and summarize its series."""

from dataclasses import dataclass
from datetime import date

import pandas as pd

from app.repositories.pisco_repository import CellRef, DatasetKind, PiscoRepository
from app.services.coordinates import CoordinateError, haversine_km, utm_to_wgs84

NO_DATA_MESSAGE = "No data available for this location"
PREVIEW_ROWS = 5

Row = tuple[str, float | None]


@dataclass(frozen=True)
class PointForm:
    """Form values exactly as posted (strings; empty when not filled)."""

    lon: str = ""
    lat: str = ""
    start_year: str = ""
    end_year: str = ""
    easting: str = ""
    northing: str = ""
    zone: str = ""
    hemisphere: str = "South"


class PointInputError(ValueError):
    """Invalid user input; the message is shown to the user."""


class NoDataError(ValueError):
    """The selected cell has no data for the requested period."""

    def __init__(self) -> None:
        super().__init__(NO_DATA_MESSAGE)


@dataclass(frozen=True)
class PointResult:
    """A successful extraction and its summary."""

    lon: float
    lat: float
    cell: CellRef
    distance_km: float
    period_start: date
    period_end: date
    total_days: int
    missing_days: int
    head: list[Row]
    tail: list[Row]
    series: pd.DataFrame  # columns: date (ISO 8601), precipitation_mm


def year_defaults(repo: PiscoRepository) -> tuple[int, int] | None:
    """First year and last complete year of the daily file, or None if it is unavailable."""
    index = repo.time_index(DatasetKind.DAILY)
    if index is None or len(index) == 0:
        return None
    first, last = index[0], index[-1]
    last_complete = last.year if (last.month, last.day) == (12, 31) else last.year - 1
    return first.year, last_complete


def convert_utm(form: PointForm) -> tuple[float, float]:
    """Convert the UTM fields of the form to WGS84 `(longitude, latitude)`."""
    easting = _number(form.easting, "Easting")
    northing = _number(form.northing, "Northing")
    zone = _integer(form.zone, "UTM zone", "UTM zone must be 17, 18 or 19")
    try:
        return utm_to_wgs84(easting, northing, zone, form.hemisphere)
    except CoordinateError as exc:
        raise PointInputError(str(exc)) from exc


def extract_point(repo: PiscoRepository, form: PointForm) -> PointResult:
    """Validate the form, read the nearest cell for the requested years and summarize it.

    Validation follows design D2 and finishes before any precipitation value is read.
    """
    lon = _number(form.lon, "Longitude")
    lat = _number(form.lat, "Latitude")
    start_year = _integer(form.start_year, "Start year")
    end_year = _integer(form.end_year, "End year")

    extent = repo.grid_extent()
    years = _data_years(repo)
    if extent is None or years is None:
        raise PointInputError("Daily data is not available")
    if not extent.contains(lon, lat):
        raise PointInputError(
            "The point is outside the PISCOp grid "
            f"(longitude {extent.lon_min:.1f} to {extent.lon_max:.1f}, "
            f"latitude {extent.lat_min:.1f} to {extent.lat_max:.1f})"
        )
    if start_year > end_year:
        raise PointInputError("Start year must not be later than end year")
    first, last = years
    if start_year < first or end_year > last:
        raise PointInputError(f"Years must be between {first} and {last}")

    cell = repo.nearest_cell(lon, lat)
    series = repo.read_cell_series(cell, date(start_year, 1, 1), date(end_year, 12, 31))
    if series.empty or series.isna().all():
        raise NoDataError()

    dates = series.index.strftime("%Y-%m-%d")
    frame = pd.DataFrame({"date": dates, "precipitation_mm": series.to_numpy()})  # full precision
    rows = [(day, _value(v)) for day, v in zip(dates, series.to_numpy(), strict=True)]
    return PointResult(
        lon=lon,
        lat=lat,
        cell=cell,
        distance_km=round(haversine_km(lon, lat, cell.lon, cell.lat), 3),
        period_start=series.index[0].date(),
        period_end=series.index[-1].date(),
        total_days=len(series),
        missing_days=int(series.isna().sum()),
        head=rows[:PREVIEW_ROWS],
        tail=rows[-PREVIEW_ROWS:],
        series=frame,
    )


def _data_years(repo: PiscoRepository) -> tuple[int, int] | None:
    index = repo.time_index(DatasetKind.DAILY)
    if index is None or len(index) == 0:
        return None
    return index[0].year, index[-1].year


def _number(text: str, label: str) -> float:
    try:
        return float(text.strip())
    except ValueError:
        raise PointInputError(f"{label} must be a number") from None


def _integer(text: str, label: str, message: str | None = None) -> int:
    try:
        return int(text.strip())
    except ValueError:
        raise PointInputError(message or f"{label} must be an integer") from None


def _value(value: float) -> float | None:
    return None if pd.isna(value) else round(float(value), 2)
