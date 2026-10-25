from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from app.config import Settings
from app.repositories.pisco_repository import DatasetKind, PiscoRepository
from tests.conftest import write_default_files, write_pisco_file

MISMATCH = "Period mismatch: daily file ends in 2025-12, monthly file ends in 2024-12"


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


def test_all_files_available(open_repo: Callable, data_dir: Path) -> None:
    repo = open_repo(data_dir)
    assert [m.available for m in repo.all_metadata()] == [True, True, True]
    assert [m.kind for m in repo.all_metadata()] == list(DatasetKind)


def test_custom_data_dir(open_repo: Callable, tmp_path: Path) -> None:
    custom = write_default_files(tmp_path / "pisco")
    repo = open_repo(custom)
    assert repo.metadata(DatasetKind.DAILY).available


def test_missing_daily_file(open_repo: Callable, make_data_dir: Callable) -> None:
    repo = open_repo(make_data_dir(skip=("PISCOp_d.nc",)))
    daily = repo.metadata(DatasetKind.DAILY)
    assert not daily.available
    assert daily.reason == "file not found: PISCOp_d.nc"
    assert repo.dataset(DatasetKind.DAILY) is None


def test_corrupt_file(open_repo: Callable, make_data_dir: Callable) -> None:
    directory = make_data_dir(skip=("PISCOp_m.nc",))
    (directory / "PISCOp_m.nc").write_text("not a netcdf file")
    monthly = open_repo(directory).metadata(DatasetKind.MONTHLY)
    assert not monthly.available
    assert monthly.reason == "could not be read as NetCDF"


def test_empty_data_dir(open_repo: Callable, tmp_path: Path) -> None:
    repo = open_repo(tmp_path)
    assert not any(m.available for m in repo.all_metadata())


def test_unexpected_climatology_length(open_repo: Callable, make_data_dir: Callable) -> None:
    directory = make_data_dir(skip=("PISCOp_clim2.nc",))
    write_pisco_file(directory / "PISCOp_clim2.nc", 13, variable="PISCOp_clim2", units=None)
    clim = open_repo(directory).metadata(DatasetKind.CLIMATOLOGY)
    assert not clim.available
    assert clim.reason == "expected 12 time steps, found 13"


def test_precipitation_not_loaded(open_repo: Callable, data_dir: Path) -> None:
    repo = open_repo(data_dir)
    ds = repo.dataset(DatasetKind.DAILY)
    assert ds is not None
    assert not ds["precipitation"].variable._in_memory


def test_daily_metadata(open_repo: Callable, data_dir: Path) -> None:
    daily = open_repo(data_dir).metadata(DatasetKind.DAILY)
    assert (daily.variable, daily.lat_name, daily.lon_name, daily.time_name) == (
        "precipitation",
        "latitude",
        "longitude",
        "Z1",
    )
    assert (daily.n_time, daily.n_lat, daily.n_lon) == (16436, 5, 4)
    assert (daily.lat_min, daily.lat_max) == (1.55, 1.95)
    assert (daily.lon_min, daily.lon_max) == (-81.35, -81.05)
    assert daily.resolution_deg == 0.1
    assert (daily.time_start, daily.time_end) == ("1981-01-01", "2025-12-31")
    assert daily.warnings == []


def test_ascending_latitude_gives_same_bounds(open_repo: Callable, tmp_path: Path) -> None:
    descending = tmp_path / "desc"
    ascending = tmp_path / "asc"
    for directory, flag in ((descending, False), (ascending, True)):
        directory.mkdir()
        write_pisco_file(directory / "PISCOp_d.nc", 30, ascending_lat=flag)
    desc = open_repo(descending).metadata(DatasetKind.DAILY)
    asc = open_repo(ascending).metadata(DatasetKind.DAILY)
    assert (asc.lat_min, asc.lat_max, asc.resolution_deg) == (
        desc.lat_min,
        desc.lat_max,
        desc.resolution_deg,
    )


def test_period_mismatch_on_both_files(open_repo: Callable, make_data_dir: Callable) -> None:
    repo = open_repo(make_data_dir(monthly_steps=528))
    daily = repo.metadata(DatasetKind.DAILY)
    monthly = repo.metadata(DatasetKind.MONTHLY)
    assert daily.available and monthly.available
    assert daily.warnings == [MISMATCH]
    assert monthly.warnings == [MISMATCH]


def test_no_mismatch_when_monthly_missing(open_repo: Callable, make_data_dir: Callable) -> None:
    repo = open_repo(make_data_dir(skip=("PISCOp_m.nc",)))
    assert repo.metadata(DatasetKind.DAILY).warnings == []


def test_climatology_grid_kept_separate(open_repo: Callable, data_dir: Path) -> None:
    repo = open_repo(data_dir)
    clim = repo.metadata(DatasetKind.CLIMATOLOGY)
    daily = repo.metadata(DatasetKind.DAILY)
    assert (clim.n_lat, clim.n_lon) == (5, 5)
    assert (daily.n_lat, daily.n_lon) == (5, 4)
    assert clim.warnings == []
    assert (clim.time_start, clim.time_end) == ("1", "12")
    assert clim.variables[0].units is None


def test_climatology_is_catalog_only(open_repo: Callable, data_dir: Path) -> None:
    repo = open_repo(data_dir)
    with pytest.raises(ValueError, match="climatology is catalog-only"):
        repo.dataset(DatasetKind.CLIMATOLOGY)
    assert repo.metadata(DatasetKind.CLIMATOLOGY).available
