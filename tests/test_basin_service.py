import math
from collections.abc import Callable, Iterator
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.config import Settings
from app.repositories.pisco_repository import PiscoRepository
from app.services.basin_geometry import BasinGeometry, BasinInputError, parse_basin_file
from app.services.basin_service import (
    NO_BASIN_DATA_MESSAGE,
    BasinResult,
    NoBasinDataError,
    extract_basin,
)
from app.services.point_service import PointInputError, validate_years
from tests.basin_files import rectangle_geojson
from tests.conftest import (
    REF_LAT_START,
    REF_LON_START,
    write_pisco_file,
)
from tests.test_point_result_pages import precipitation_reads  # noqa: F401 (fixture)

OUTSIDE = "The basin is outside the PISCOp grid (longitude -76.4 to -76.0, latitude -12.5 to -12.0)"


@pytest.fixture
def open_repo() -> Iterator[Callable[[Path], PiscoRepository]]:
    repos: list[PiscoRepository] = []

    def factory(directory: Path) -> PiscoRepository:
        repo = PiscoRepository.open(Settings(data_dir=directory))
        repos.append(repo)
        return repo

    yield factory
    for repo in repos:
        repo.close()


def _basin(w: float, s: float, e: float, n: float) -> BasinGeometry:
    return parse_basin_file("basin.geojson", rectangle_geojson(w, s, e, n))


def _extract(
    repo: PiscoRepository, rect: tuple[float, ...], years: tuple[int, int] = (1981, 1985)
) -> BasinResult:
    return extract_basin(repo, _basin(*rect), *years)


def _centers(result: BasinResult) -> list[tuple[float, float]]:
    return [(cell.lon, cell.lat) for cell in result.cells]


# --- selection -------------------------------------------------------------------------------


def test_four_centers_inside(basin_dir: Path, open_repo: Callable) -> None:
    result = _extract(open_repo(basin_dir), (-76.30, -12.40, -76.10, -12.20))
    assert _centers(result) == [
        (-76.25, -12.25),
        (-76.15, -12.25),
        (-76.25, -12.35),
        (-76.15, -12.35),
    ]
    assert not result.fallback


def test_centers_on_the_boundary(basin_dir: Path, open_repo: Callable) -> None:
    result = _extract(open_repo(basin_dir), (-76.25, -12.35, -76.05, -12.15))
    assert len(result.cells) == 9
    assert sorted({c.lon for c in result.cells}) == [-76.25, -76.15, -76.05]
    assert sorted({c.lat for c in result.cells}) == [-12.35, -12.25, -12.15]


def test_basin_partly_outside(basin_dir: Path, open_repo: Callable) -> None:
    result = _extract(open_repo(basin_dir), (-76.10, -12.30, -75.80, -12.10))
    assert _centers(result) == [(-76.05, -12.15), (-76.05, -12.25)]


def test_basin_outside(basin_dir: Path, open_repo: Callable) -> None:
    with pytest.raises(BasinInputError) as error:
        _extract(open_repo(basin_dir), (-70.50, -10.50, -70.00, -10.00))
    assert str(error.value) == OUTSIDE


def test_small_basin_uses_centroid_cell(
    basin_dir: Path,
    open_repo: Callable,
    precipitation_reads: list[tuple[int, ...]],  # noqa: F811
) -> None:
    result = _extract(open_repo(basin_dir), (-76.14, -12.24, -76.12, -12.22))
    assert result.fallback
    assert _centers(result) == [(-76.15, -12.25)]
    assert result.cells[0].valid_days == 1824
    assert all(shape[1:] == (1, 1) for shape in precipitation_reads)


def test_centroid_on_a_cell_edge(basin_dir: Path, open_repo: Callable) -> None:
    result = _extract(open_repo(basin_dir), (-76.105, -12.305, -76.095, -12.295))
    assert _centers(result) == [(-76.05, -12.25)]


def test_centroid_outside_the_grid(basin_dir: Path, open_repo: Callable) -> None:
    with pytest.raises(BasinInputError) as error:
        _extract(open_repo(basin_dir), (-76.02, -12.04, -75.90, -11.90))
    assert str(error.value) == OUTSIDE


# --- size limit ------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def large_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("large")
    write_pisco_file(directory / "PISCOp_d.nc", 365, n_lat=60, n_lon=60)
    return directory


def test_bounding_box_over_the_limit(
    large_dir: Path,
    open_repo: Callable,
    precipitation_reads: list[tuple[int, ...]],  # noqa: F811
) -> None:
    # 51 latitude centers (1.95 .. -3.05) and 50 longitude centers (-81.35 .. -76.45).
    with pytest.raises(BasinInputError) as error:
        _extract(open_repo(large_dir), (-81.35, -3.05, -76.45, 1.95), (1981, 1981))
    assert str(error.value) == (
        "The basin is too large: its bounding box covers 2550 grid cells (maximum 2500)"
    )
    assert precipitation_reads == []


def test_bounding_box_at_the_limit(large_dir: Path, open_repo: Callable) -> None:
    result = _extract(open_repo(large_dir), (-81.35, -2.95, -76.45, 1.95), (1981, 1981))
    assert len(result.cells) == 2500


# --- areal mean ------------------------------------------------------------------------------


def test_mean_of_valid_cells(tmp_path: Path, open_repo: Callable) -> None:
    grid = np.zeros((365, 5, 4), dtype=np.float32)
    grid[0, 2:4, 1:3] = [[2.0, 4.0], [np.nan, 6.0]]  # cells (-76.25|-76.15, -12.25|-12.35)
    write_pisco_file(
        tmp_path / "PISCOp_d.nc", 365, lat_start=REF_LAT_START, lon_start=REF_LON_START, values=grid
    )
    result = _extract(open_repo(tmp_path), (-76.30, -12.40, -76.10, -12.20), (1981, 1981))
    assert result.series.iloc[0] == pytest.approx(4.0)


def test_one_cell_missing_on_a_day(basin_dir: Path, open_repo: Callable) -> None:
    result = _extract(open_repo(basin_dir), (-76.30, -12.40, -76.10, -12.20), (1981, 1981))
    assert result.series[pd.Timestamp("1981-01-03")] == pytest.approx(3.0)
    assert result.series.count() == 365
    assert result.series.sum() == pytest.approx(1638.0)
    assert result.series.name == "precipitation_mm"
    assert result.series.index.name == "date"


def test_every_cell_missing_on_a_day(varied_dir: Path, open_repo: Callable) -> None:
    result = _extract(open_repo(varied_dir), (-76.30, -12.40, -76.10, -12.20), (1981, 1981))
    assert math.isnan(result.series[pd.Timestamp("1981-02-01")])
    assert result.missing_days == 1
    assert result.series.iloc[0] == pytest.approx((9 + 10 + 13 + 14) / 4)


def test_ocean_cell_excluded(basin_dir: Path, open_repo: Callable) -> None:
    result = _extract(open_repo(basin_dir), (-76.40, -12.50, -76.20, -12.30))
    assert (result.cells_used, result.cells_excluded) == (3, 1)
    excluded = [cell for cell in result.cells if not cell.used]
    assert [(c.lon, c.lat, c.valid_days) for c in excluded] == [(-76.35, -12.45, 0)]
    assert result.cells[0].valid_days == 1826
    assert result.area_km2 == 481.2


def test_all_cells_without_data(basin_dir: Path, open_repo: Callable) -> None:
    with pytest.raises(NoBasinDataError, match=NO_BASIN_DATA_MESSAGE):
        _extract(open_repo(basin_dir), (-76.40, -12.50, -76.30, -12.40))


def test_chunked_file_gives_the_same_series(
    basin_dir: Path, chunked_dir: Path, open_repo: Callable
) -> None:
    rect = (-76.40, -12.50, -76.10, -12.20)
    contiguous = _extract(open_repo(basin_dir), rect)
    chunked = _extract(open_repo(chunked_dir), rect)
    pd.testing.assert_series_equal(contiguous.series, chunked.series)
    assert contiguous.cells == chunked.cells


def test_summary_fields(basin_dir: Path, open_repo: Callable) -> None:
    result = _extract(open_repo(basin_dir), (-76.30, -12.40, -76.10, -12.20))
    assert (result.total_days, result.missing_days) == (1826, 0)
    assert str(result.period_start) == "1981-01-01" and str(result.period_end) == "1985-12-31"
    assert result.centroid_lon == pytest.approx(-76.2, abs=1e-3)
    assert result.centroid_lat == pytest.approx(-12.3, abs=1e-3)


# --- years -----------------------------------------------------------------------------------


def test_validate_years(basin_dir: Path, open_repo: Callable) -> None:
    repo = open_repo(basin_dir)
    assert validate_years(repo, " 1981 ", "1985") == (1981, 1985)
    with pytest.raises(PointInputError, match="Start year must not be later than end year"):
        validate_years(repo, "1985", "1981")
    with pytest.raises(PointInputError, match="Years must be between 1981 and 2025"):
        validate_years(repo, "1980", "1985")
