from collections.abc import Iterator
from datetime import date
from pathlib import Path

import numpy as np
import pytest
from xarray.backends import netCDF4_

from app.config import Settings
from app.repositories.pisco_repository import CellRef, DatasetKind, PiscoRepository
from tests.conftest import NAN_CELL, REF_CELL, write_default_files, write_reference_dir

SPY_BROKEN = "xarray internals changed; update the read spy"


def _open(directory: Path) -> PiscoRepository:
    return PiscoRepository.open(Settings(data_dir=directory))


@pytest.fixture
def ref_repo(reference_dir: Path) -> Iterator[PiscoRepository]:
    repo = _open(reference_dir)
    yield repo
    repo.close()


@pytest.fixture
def read_spy(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, tuple[int, ...]]]:
    """Record the variable name and shape of every value read from a NetCDF file.

    `_getitem` is private xarray API: if it disappears the test fails, never skips.
    """
    wrapper = netCDF4_.NetCDF4ArrayWrapper
    if not hasattr(wrapper, "_getitem"):
        pytest.fail(SPY_BROKEN)
    reads: list[tuple[str, tuple[int, ...]]] = []
    original = wrapper._getitem

    def spy(self: netCDF4_.NetCDF4ArrayWrapper, key: object) -> np.ndarray:
        result = original(self, key)
        reads.append((self.variable_name, np.shape(result)))
        return result

    monkeypatch.setattr(wrapper, "_getitem", spy)
    return reads


# --- grid extent and nearest cell ------------------------------------------------------


def test_extent_of_default_grid(data_dir: Path) -> None:
    repo = _open(data_dir)
    try:
        extent = repo.grid_extent()
    finally:
        repo.close()
    assert extent is not None
    assert (extent.lon_min, extent.lon_max) == (-81.4, -81.0)
    assert (extent.lat_min, extent.lat_max) == (1.5, 2.0)


def test_extent_none_without_daily(tmp_path: Path) -> None:
    repo = _open(write_default_files(tmp_path / "d", skip=("PISCOp_d.nc",)))
    try:
        assert repo.grid_extent() is None
    finally:
        repo.close()


def test_reference_point(ref_repo: PiscoRepository) -> None:
    cell = ref_repo.nearest_cell(-76.1390222, -12.2935861)
    assert (cell.lon, cell.lat) == (-76.15, -12.25)
    assert (cell.lat_index, cell.lon_index) == REF_CELL


def test_exact_center_selects_itself(ref_repo: PiscoRepository) -> None:
    cell = ref_repo.nearest_cell(-76.25, -12.15)
    assert (cell.lon, cell.lat) == (-76.25, -12.15)


def test_outer_edge_selects_border_cell(ref_repo: PiscoRepository) -> None:
    extent = ref_repo.grid_extent()
    assert extent is not None and extent.lon_max == -76.0
    assert extent.contains(-76.0, -12.25)
    assert ref_repo.nearest_cell(-76.0, -12.25).lon == -76.05


@pytest.mark.parametrize("fixture_name", ["reference_dir", "reference_dir_float64"])
def test_ties_go_north_and_east(fixture_name: str, request: pytest.FixtureRequest) -> None:
    repo = _open(request.getfixturevalue(fixture_name))
    try:
        assert repo.nearest_cell(-76.15, -12.30).lat == -12.25
        assert repo.nearest_cell(-76.10, -12.25).lon == -76.05
    finally:
        repo.close()


def test_ties_same_on_ascending_latitude(tmp_path: Path) -> None:
    repo = _open(write_reference_dir(tmp_path / "asc", ascending_lat=True, daily_steps=10))
    try:
        assert repo.nearest_cell(-76.15, -12.30).lat == -12.25
        assert repo.nearest_cell(-76.10, -12.25).lon == -76.05
    finally:
        repo.close()


# --- single-cell reads -------------------------------------------------------------------


def _cell(repo: PiscoRepository, position: tuple[int, int]) -> CellRef:
    ds = repo.dataset(DatasetKind.DAILY)
    assert ds is not None
    lon = float(ds["longitude"][position[1]])
    lat = float(ds["latitude"][position[0]])
    return repo.nearest_cell(lon, lat)


def test_period_from_calendar(ref_repo: PiscoRepository) -> None:
    series = ref_repo.read_cell_series(
        _cell(ref_repo, REF_CELL), date(1981, 1, 1), date(1982, 12, 31)
    )
    assert len(series) == 730
    assert series.index[0].strftime("%Y-%m-%d") == "1981-01-01"
    assert series.index[-1].strftime("%Y-%m-%d") == "1982-12-31"


def test_leap_year(ref_repo: PiscoRepository) -> None:
    series = ref_repo.read_cell_series(
        _cell(ref_repo, REF_CELL), date(2000, 1, 1), date(2000, 12, 31)
    )
    assert len(series) == 366


def test_missing_days_are_nan(ref_repo: PiscoRepository) -> None:
    series = ref_repo.read_cell_series(
        _cell(ref_repo, REF_CELL), date(1981, 1, 1), date(1981, 12, 31)
    )
    missing = series[series.isna()].index.strftime("%Y-%m-%d").tolist()
    assert missing == ["1981-01-03", "1981-06-01"]
    assert series.iloc[1] == 1.5  # day 2 -> (1 % 7) * 1.5


def test_nan_cell_is_all_missing(ref_repo: PiscoRepository) -> None:
    series = ref_repo.read_cell_series(
        _cell(ref_repo, NAN_CELL), date(1981, 1, 1), date(1981, 12, 31)
    )
    assert series.isna().all()


def test_only_the_selected_cell_is_read(
    ref_repo: PiscoRepository, read_spy: list[tuple[str, tuple[int, ...]]]
) -> None:
    cell = ref_repo.nearest_cell(-76.1390222, -12.2935861)
    assert not [r for r in read_spy if r[0] == "precipitation"], "lookup must not read data"

    series = ref_repo.read_cell_series(cell, date(1981, 1, 1), date(1985, 12, 31))

    precipitation_reads = [shape for name, shape in read_spy if name == "precipitation"]
    if not precipitation_reads:
        pytest.fail(SPY_BROKEN)
    for shape in precipitation_reads:
        assert len(shape) <= 1, f"read covered more than one cell: {shape}"
    assert sum(int(np.prod(s)) for s in precipitation_reads) == len(series) == 1826
    ds = ref_repo.dataset(DatasetKind.DAILY)
    assert ds is not None
    assert not ds["precipitation"].variable._in_memory
