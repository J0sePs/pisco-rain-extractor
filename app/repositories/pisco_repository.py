"""Access to the PISCOp v3.0 NetCDF files.

This is the only module that opens NetCDF files (ADR-0004). Files are opened once and lazily
(ADR-0005): only 1-D coordinates are read, never precipitation values.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from enum import StrEnum
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from app.config import Settings

LAT_TOLERANCE_DEG = 1e-6
CLIMATOLOGY_STEPS = 12

_LAT_NAMES = {"lat", "latitude", "y"}
_LON_NAMES = {"lon", "longitude", "x"}


class DatasetKind(StrEnum):
    """The three PISCOp v3.0 products."""

    DAILY = "daily"
    MONTHLY = "monthly"
    CLIMATOLOGY = "climatology"


FILES: dict[DatasetKind, str] = {
    DatasetKind.DAILY: "PISCOp_d.nc",
    DatasetKind.MONTHLY: "PISCOp_m.nc",
    DatasetKind.CLIMATOLOGY: "PISCOp_clim2.nc",
}


class DatasetStructureError(ValueError):
    """The file can be opened but does not have the expected PISCOp structure."""


@dataclass(frozen=True)
class DetectedNames:
    """Names of the precipitation variable and its dimensions in one file."""

    variable: str
    lat: str
    lon: str
    time: str


@dataclass(frozen=True)
class VariableInfo:
    """A data variable and its units (None when the file does not declare them)."""

    name: str
    units: str | None


@dataclass(frozen=True)
class DatasetMetadata:
    """Structure and availability of one PISCOp file."""

    kind: DatasetKind
    filename: str
    available: bool
    reason: str | None = None
    variable: str | None = None
    lat_name: str | None = None
    lon_name: str | None = None
    time_name: str | None = None
    variables: list[VariableInfo] = field(default_factory=list)
    n_time: int = 0
    n_lat: int = 0
    n_lon: int = 0
    lat_min: float | None = None
    lat_max: float | None = None
    lon_min: float | None = None
    lon_max: float | None = None
    resolution_deg: float | None = None
    time_start: str | None = None
    time_end: str | None = None
    warnings: list[str] = field(default_factory=list)


def _find_axis(ds: xr.Dataset, names: set[str], units: str, standard_name: str) -> str | None:
    for dim in ds.dims:
        if str(dim).lower() in names:
            return str(dim)
    for var in ds.variables.values():
        attrs = var.attrs
        if var.ndim == 1 and (
            attrs.get("units") == units or attrs.get("standard_name") == standard_name
        ):
            return str(var.dims[0])
    return None


def detect_names(ds: xr.Dataset) -> DetectedNames:
    """Detect the precipitation variable and the latitude, longitude and time dimensions."""
    lat = _find_axis(ds, _LAT_NAMES, "degrees_north", "latitude")
    lon = _find_axis(ds, _LON_NAMES, "degrees_east", "longitude")
    if lat is None or lon is None:
        raise DatasetStructureError("latitude/longitude coordinates not found")

    candidates = [
        str(name)
        for name, var in ds.data_vars.items()
        if var.ndim == 3 and lat in var.dims and lon in var.dims
    ]
    if not candidates:
        raise DatasetStructureError("no precipitation variable found")

    def rank(name: str) -> tuple[bool, bool]:
        lowered = name.lower()
        has_mm = ds[name].attrs.get("units") == "mm"
        return (not has_mm, not ("prec" in lowered or "pisco" in lowered))

    variable = min(candidates, key=rank)
    time = next(str(d) for d in ds[variable].dims if d not in (lat, lon))
    return DetectedNames(variable=variable, lat=lat, lon=lon, time=time)


def build_time_index(kind: DatasetKind, n: int, start: date | None) -> pd.Index:
    """Turn an integer time index of length `n` into dates (ADR-0007).

    Daily: one Gregorian day per step; monthly: one month (first day) per step;
    climatology: calendar months 1-12.
    """
    if kind is DatasetKind.CLIMATOLOGY:
        if n != CLIMATOLOGY_STEPS:
            raise DatasetStructureError(f"expected {CLIMATOLOGY_STEPS} time steps, found {n}")
        return pd.RangeIndex(1, CLIMATOLOGY_STEPS + 1, name="month")
    if n < 1:
        raise DatasetStructureError("no time steps found")
    if start is None:
        raise ValueError(f"a start date is required for the {kind} calendar")
    freq = "D" if kind is DatasetKind.DAILY else "MS"
    return pd.date_range(start, periods=n, freq=freq, name="date")


def check_period_consistency(daily: pd.Index, monthly: pd.Index) -> str | None:
    """Return a warning when the daily and monthly calendars end in different months."""
    daily_end = pd.Timestamp(daily[-1]).to_period("M")
    monthly_end = pd.Timestamp(monthly[-1]).to_period("M")
    if daily_end == monthly_end:
        return None
    return f"Period mismatch: daily file ends in {daily_end}, monthly file ends in {monthly_end}"


def lat_slice(lat: np.ndarray, south: float, north: float, tol: float = LAT_TOLERANCE_DEG) -> slice:
    """Return a label slice selecting latitudes in [south, north] for either axis order.

    Never apply `slice()` to latitude directly: on a descending axis (as PISCOp) a plain
    `slice(south, north)` selects nothing. `tol` keeps border rows stored as float32 (D10).
    """
    values = np.asarray(lat)
    if values.size > 1 and values[0] > values[-1]:
        return slice(north + tol, south - tol)
    return slice(south - tol, north + tol)


def _time_index(
    ds: xr.Dataset, names: DetectedNames, kind: DatasetKind, start: date | None
) -> pd.Index:
    coord = ds[names.time]
    if kind is not DatasetKind.CLIMATOLOGY and " since " in str(coord.attrs.get("units", "")):
        decoded = xr.decode_cf(xr.Dataset(coords={names.time: coord.variable}))
        return pd.DatetimeIndex(decoded[names.time].values, name="date")
    return build_time_index(kind, ds.sizes[names.time], start)


def _rounded(value: float) -> float:
    # Convert first (rounding a float32 keeps float32 noise: 1.55 -> 1.5499999523). Four
    # decimals: float32 error near 81 degrees is ~1e-5, far below the 0.1 degree grid.
    return round(float(value), 4)


def _describe(
    ds: xr.Dataset, kind: DatasetKind, names: DetectedNames, index: pd.Index
) -> DatasetMetadata:
    lat = ds[names.lat].values
    lon = ds[names.lon].values
    variables = [
        VariableInfo(name=str(name), units=var.attrs.get("units"))
        for name, var in ds.data_vars.items()
        if var.ndim > 0
    ]
    resolution = round(float(np.median(np.abs(np.diff(lat)))), 4) if lat.size > 1 else None
    if isinstance(index, pd.DatetimeIndex):
        time_start, time_end = index[0].strftime("%Y-%m-%d"), index[-1].strftime("%Y-%m-%d")
    else:
        time_start, time_end = str(index[0]), str(index[-1])
    return DatasetMetadata(
        kind=kind,
        filename=FILES[kind],
        available=True,
        variable=names.variable,
        lat_name=names.lat,
        lon_name=names.lon,
        time_name=names.time,
        variables=variables,
        n_time=len(index),
        n_lat=int(lat.size),
        n_lon=int(lon.size),
        lat_min=_rounded(lat.min()),
        lat_max=_rounded(lat.max()),
        lon_min=_rounded(lon.min()),
        lon_max=_rounded(lon.max()),
        resolution_deg=resolution,
        time_start=time_start,
        time_end=time_end,
    )


@dataclass
class _Entry:
    metadata: DatasetMetadata
    dataset: xr.Dataset | None = None
    time_index: pd.Index | None = None


class PiscoRepository:
    """Lazily opened PISCOp files, their detected structure and calendars."""

    def __init__(self, entries: dict[DatasetKind, _Entry]) -> None:
        self._entries = entries

    @classmethod
    def open(cls, settings: Settings) -> PiscoRepository:
        """Open the three files from `settings.data_dir`; never raises for bad files."""
        starts = {
            DatasetKind.DAILY: settings.daily_start_date,
            DatasetKind.MONTHLY: settings.monthly_start_date,
            DatasetKind.CLIMATOLOGY: None,
        }
        entries = {
            kind: _open_entry(Path(settings.data_dir) / FILES[kind], kind, starts[kind])
            for kind in DatasetKind
        }
        _cross_check(entries)
        return cls(entries)

    def metadata(self, kind: DatasetKind) -> DatasetMetadata:
        """Return the metadata of one file."""
        return self._entries[kind].metadata

    def all_metadata(self) -> list[DatasetMetadata]:
        """Return the metadata of all files: daily, monthly, climatology."""
        return [self._entries[kind].metadata for kind in DatasetKind]

    def dataset(self, kind: DatasetKind) -> xr.Dataset | None:
        """Return the lazy dataset handle, or None if the file is unavailable.

        The climatology is catalog-only (ADR-0008) and its data is never handed out.
        """
        if kind is DatasetKind.CLIMATOLOGY:
            raise ValueError("climatology is catalog-only")
        return self._entries[kind].dataset

    def time_index(self, kind: DatasetKind) -> pd.Index | None:
        """Return the calendar of one file, or None if the file is unavailable."""
        return self._entries[kind].time_index

    def close(self) -> None:
        """Close every open file handle."""
        for entry in self._entries.values():
            if entry.dataset is not None:
                entry.dataset.close()
                entry.dataset = None


def _unavailable(kind: DatasetKind, reason: str) -> _Entry:
    return _Entry(DatasetMetadata(kind=kind, filename=FILES[kind], available=False, reason=reason))


def _open_entry(path: Path, kind: DatasetKind, start: date | None) -> _Entry:
    if not path.is_file():
        return _unavailable(kind, f"file not found: {path.name}")
    try:
        ds = xr.open_dataset(path, engine="netcdf4", decode_times=False, cache=False)
    except (OSError, ValueError, RuntimeError):
        return _unavailable(kind, "could not be read as NetCDF")
    try:
        names = detect_names(ds)
        index = _time_index(ds, names, kind, start)
        metadata = _describe(ds, kind, names, index)
    except DatasetStructureError as exc:
        ds.close()
        return _unavailable(kind, str(exc))
    return _Entry(metadata=metadata, dataset=ds, time_index=index)


def _cross_check(entries: dict[DatasetKind, _Entry]) -> None:
    daily = entries[DatasetKind.DAILY]
    monthly = entries[DatasetKind.MONTHLY]
    if daily.time_index is None or monthly.time_index is None:
        return
    warning = check_period_consistency(daily.time_index, monthly.time_index)
    if warning is None:
        return
    for entry in (daily, monthly):
        entry.metadata = replace(entry.metadata, warnings=[*entry.metadata.warnings, warning])
