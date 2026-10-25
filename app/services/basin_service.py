"""Basin extraction: select the cells of a basin and compute its daily areal mean.

Cells whose centers fall inside the basin are used, with a centroid fallback for small basins
and all-missing cells excluded (ADR-0016). Only the bounding box is read, in time blocks, up to
`MAX_BOX_CELLS` cells (ADR-0017). No FastAPI and no NetCDF access outside the repository.
"""

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
import shapely
from shapely.geometry import box as box_geometry

from app.repositories.pisco_repository import DatasetKind, GridBox, GridExtent, PiscoRepository
from app.services.basin_geometry import (
    BasinGeometry,
    BasinInputError,
    geodesic_area_km2,
    utm_centroid,
)

MAX_BOX_CELLS = 2500
NO_BASIN_DATA_MESSAGE = "No data available for this basin"
FALLBACK_WARNING = (
    "No cell center falls inside the basin; the cell nearest to its centroid was used"
)


class NoBasinDataError(ValueError):
    """Every selected cell has no data in the requested period."""

    def __init__(self) -> None:
        super().__init__(NO_BASIN_DATA_MESSAGE)


@dataclass(frozen=True)
class BasinCell:
    """A selected cell center and whether it entered the areal mean."""

    lon: float
    lat: float
    used: bool
    valid_days: int


@dataclass(frozen=True)
class BasinResult:
    """A successful basin extraction and its summary."""

    basin: BasinGeometry
    area_km2: float
    centroid_lon: float
    centroid_lat: float
    fallback: bool
    cells: list[BasinCell]  # latitude descending, then longitude ascending
    resolution_deg: float
    start_year: int
    end_year: int
    period_start: date
    period_end: date
    total_days: int
    missing_days: int
    series: pd.Series  # DatetimeIndex "date", float mm, NaN = missing

    @property
    def cells_used(self) -> int:
        """Number of cells in the areal mean."""
        return sum(cell.used for cell in self.cells)

    @property
    def cells_excluded(self) -> int:
        """Number of selected cells without data in the period."""
        return len(self.cells) - self.cells_used


def check_basin_extent(repo: PiscoRepository, basin: BasinGeometry) -> GridExtent:
    """Return the grid extent, or raise when the basin does not intersect it (ADR-0011)."""
    extent = repo.grid_extent()
    if extent is None:
        raise BasinInputError("Daily data is not available")
    domain = box_geometry(extent.lon_min, extent.lat_min, extent.lon_max, extent.lat_max)
    if not basin.geometry.intersects(domain):
        raise BasinInputError(_outside_message(extent))
    return extent


def extract_basin(
    repo: PiscoRepository, basin: BasinGeometry, start_year: int, end_year: int
) -> BasinResult:
    """Select the cells of a validated basin, read its bounding box and average them per day."""
    extent = check_basin_extent(repo, basin)
    west, south, east, north = basin.geometry.bounds
    grid_box = repo.grid_box(
        max(west, extent.lon_min),
        max(south, extent.lat_min),
        min(east, extent.lon_max),
        min(north, extent.lat_max),
    )
    if grid_box.size > MAX_BOX_CELLS:
        raise BasinInputError(
            f"The basin is too large: its bounding box covers {grid_box.size} grid cells "
            f"(maximum {MAX_BOX_CELLS})"
        )
    lon, lat = np.meshgrid(grid_box.lon, grid_box.lat)  # (rows, columns) in file order
    inside = shapely.covers(basin.geometry, shapely.points(lon, lat))
    centroid_lon, centroid_lat = utm_centroid(basin.geometry)
    fallback = not inside.any()
    if fallback:
        if not extent.contains(centroid_lon, centroid_lat):
            raise BasinInputError(_outside_message(extent))
        grid_box = repo.cell_box(repo.nearest_cell(centroid_lon, centroid_lat))
        lon, lat = np.meshgrid(grid_box.lon, grid_box.lat)
        inside = np.ones(lon.shape, dtype=bool)

    series, valid_days = _areal_mean(repo, grid_box, inside, start_year, end_year)
    if series.empty or not valid_days.any():
        raise NoBasinDataError()

    cells = sorted(
        (
            BasinCell(lon=float(x), lat=float(y), used=bool(n > 0), valid_days=int(n))
            for x, y, n in zip(lon[inside], lat[inside], valid_days, strict=True)
        ),
        key=lambda cell: (-cell.lat, cell.lon),
    )
    resolution = repo.metadata(DatasetKind.DAILY).resolution_deg
    assert resolution is not None  # an available daily file always has a resolution
    return BasinResult(
        basin=basin,
        area_km2=geodesic_area_km2(basin.geometry),
        centroid_lon=centroid_lon,
        centroid_lat=centroid_lat,
        fallback=fallback,
        cells=cells,
        resolution_deg=resolution,
        start_year=start_year,
        end_year=end_year,
        period_start=series.index[0].date(),
        period_end=series.index[-1].date(),
        total_days=len(series),
        missing_days=int(series.isna().sum()),
        series=series,
    )


def _areal_mean(
    repo: PiscoRepository, grid_box: GridBox, inside: np.ndarray, start_year: int, end_year: int
) -> tuple[pd.Series, np.ndarray]:
    """Daily mean of the valid selected cells and valid days per selected cell (ADR-0016)."""
    valid_days = np.zeros(int(inside.sum()), dtype=np.int64)
    parts: list[pd.Series] = []
    blocks = repo.iter_box_blocks(grid_box, date(start_year, 1, 1), date(end_year, 12, 31))
    for dates, values in blocks:
        selected = values[:, inside]  # (days, selected cells)
        valid = ~np.isnan(selected)
        valid_days += valid.sum(axis=0)
        counts = valid.sum(axis=1)
        totals = np.nansum(selected, axis=1, dtype=np.float64)
        means = np.full(len(dates), np.nan)
        np.divide(totals, counts, out=means, where=counts > 0)
        parts.append(pd.Series(means, index=dates))
    if not parts:
        return pd.Series([], index=pd.DatetimeIndex([], name="date"), dtype=float), valid_days
    series = pd.concat(parts).rename("precipitation_mm")
    series.index.name = "date"
    return series, valid_days


def _outside_message(extent: GridExtent) -> str:
    return (
        "The basin is outside the PISCOp grid "
        f"(longitude {extent.lon_min:.1f} to {extent.lon_max:.1f}, "
        f"latitude {extent.lat_min:.1f} to {extent.lat_max:.1f})"
    )
