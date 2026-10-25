"""Point extraction: validate the request, pick the nearest cell and summarize its series."""

from dataclasses import dataclass
from datetime import date
from urllib.parse import urlencode

import pandas as pd

from app.repositories.pisco_repository import CellRef, DatasetKind, PiscoRepository
from app.services.coordinates import CoordinateError, haversine_km, utm_to_wgs84

NO_DATA_MESSAGE = "No data available for this location"


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
class PointQuery:
    """A validated point request."""

    lon: float
    lat: float
    start_year: int
    end_year: int


@dataclass(frozen=True)
class PointResult:
    """A successful extraction and its summary."""

    lon: float
    lat: float
    cell: CellRef
    distance_km: float
    resolution_deg: float
    start_year: int
    end_year: int
    period_start: date
    period_end: date
    total_days: int
    missing_days: int
    series: pd.Series  # DatetimeIndex "date", float mm, NaN = missing, as read


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


def validate_point(repo: PiscoRepository, form: PointForm) -> PointQuery:
    """Validate the form in the order of design D2; no precipitation value is read."""
    lon = _number(form.lon, "Longitude")
    lat = _number(form.lat, "Latitude")
    start_year = _integer(form.start_year, "Start year")
    end_year = _integer(form.end_year, "End year")

    extent = repo.grid_extent()
    if extent is None or _data_years(repo) is None:
        raise PointInputError("Daily data is not available")
    if not extent.contains(lon, lat):
        raise PointInputError(
            "The point is outside the PISCOp grid "
            f"(longitude {extent.lon_min:.1f} to {extent.lon_max:.1f}, "
            f"latitude {extent.lat_min:.1f} to {extent.lat_max:.1f})"
        )
    _check_years(repo, start_year, end_year)
    return PointQuery(lon=lon, lat=lat, start_year=start_year, end_year=end_year)


def validate_years(repo: PiscoRepository, start_text: str, end_text: str) -> tuple[int, int]:
    """Validate a year range with the messages of the point form; no precipitation is read."""
    start_year = _integer(start_text, "Start year")
    end_year = _integer(end_text, "End year")
    _check_years(repo, start_year, end_year)
    return start_year, end_year


def extract_point(repo: PiscoRepository, query: PointQuery) -> PointResult:
    """Read the cell nearest to a validated point for the requested years and summarize it."""
    cell = repo.nearest_cell(query.lon, query.lat)
    series = repo.read_cell_series(cell, date(query.start_year, 1, 1), date(query.end_year, 12, 31))
    if series.empty or series.isna().all():
        raise NoDataError()

    resolution = repo.metadata(DatasetKind.DAILY).resolution_deg
    assert resolution is not None  # an available daily file always has a resolution
    return PointResult(
        lon=query.lon,
        lat=query.lat,
        cell=cell,
        distance_km=round(haversine_km(query.lon, query.lat, cell.lon, cell.lat), 3),
        resolution_deg=resolution,
        start_year=query.start_year,
        end_year=query.end_year,
        period_start=series.index[0].date(),
        period_end=series.index[-1].date(),
        total_days=len(series),
        missing_days=int(series.isna().sum()),
        series=series,
    )


def result_query(form: PointForm) -> str:
    """Query string of the result URL, built from the stripped form values (ADR-0013)."""
    return urlencode(
        {
            "lon": form.lon.strip(),
            "lat": form.lat.strip(),
            "start_year": form.start_year.strip(),
            "end_year": form.end_year.strip(),
        }
    )


def _check_years(repo: PiscoRepository, start_year: int, end_year: int) -> None:
    years = _data_years(repo)
    if years is None:
        raise PointInputError("Daily data is not available")
    if start_year > end_year:
        raise PointInputError("Start year must not be later than end year")
    first, last = years
    if start_year < first or end_year > last:
        raise PointInputError(f"Years must be between {first} and {last}")


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
