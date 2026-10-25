"""Synthetic NetCDF fixtures that mimic the structure of the real PISCOp v3.0 files.

Mimicked on purpose (see design D9): integer `Z1` time index with `units: unknown`,
descending float32 latitudes starting at 1.95, a scalar `crs` variable, and a climatology
named `PISCOp_clim2` without `units` on a grid with one more longitude than the daily file.
The real SENAMHI files are never used in tests.
"""

from collections.abc import Callable, Iterator
from pathlib import Path

import numpy as np
import pytest
import xarray as xr
from fastapi.testclient import TestClient

DAILY_STEPS = 16436  # 1981-01-01 .. 2025-12-31
MONTHLY_STEPS = 540  # 1981-01 .. 2025-12
CLIMATOLOGY_STEPS = 12

N_LAT = 5
N_LON = 4
N_LON_CLIM = 5  # like the real 180 vs 174 longitudes
LAT_START = 1.95
LON_START = -81.35
LON_START_CLIM = -81.45
STEP = 0.1


def make_coords(n: int, start: float, step: float, ascending: bool = True) -> np.ndarray:
    """Return float32 coordinates `start, start+step, ...` (or descending with `-step`)."""
    values = start + (step if ascending else -step) * np.arange(n)
    return np.round(values, 6).astype(np.float32)


def write_pisco_file(
    path: Path,
    n_time: int,
    *,
    variable: str = "precipitation",
    units: str | None = "mm",
    n_lat: int = N_LAT,
    n_lon: int = N_LON,
    lon_start: float = LON_START,
    lat_name: str = "latitude",
    lon_name: str = "longitude",
    time_name: str = "Z1",
    ascending_lat: bool = False,
    include_precipitation: bool = True,
) -> Path:
    """Write a small NetCDF file with the PISCOp v3.0 layout and return its path."""
    lat = make_coords(n_lat, LAT_START, STEP, ascending=False)
    if ascending_lat:
        lat = lat[::-1].copy()
    lon = make_coords(n_lon, lon_start, STEP)
    coords = {
        time_name: (time_name, np.arange(1, n_time + 1, dtype=np.int32), {"units": "unknown"}),
        lat_name: (lat_name, lat, {"units": "degrees_north", "long_name": "latitude"}),
        lon_name: (lon_name, lon, {"units": "degrees_east", "long_name": "longitude"}),
    }
    data_vars: dict = {"crs": ((), np.int32(0), {"proj4": "+proj=longlat +datum=WGS84"})}
    if include_precipitation:
        attrs = {"grid_mapping": "crs"}
        if units is not None:
            attrs["units"] = units
        values = np.zeros((n_time, n_lat, n_lon), dtype=np.float32)
        data_vars[variable] = ((time_name, lat_name, lon_name), values, attrs)
    ds = xr.Dataset(data_vars=data_vars, coords=coords)
    ds.to_netcdf(path, engine="netcdf4")
    ds.close()
    return path


def write_default_files(
    directory: Path,
    *,
    daily_steps: int = DAILY_STEPS,
    monthly_steps: int = MONTHLY_STEPS,
    skip: tuple[str, ...] = (),
) -> Path:
    """Write the three PISCOp files into `directory`, omitting any name listed in `skip`."""
    directory.mkdir(parents=True, exist_ok=True)
    if "PISCOp_d.nc" not in skip:
        write_pisco_file(directory / "PISCOp_d.nc", daily_steps)
    if "PISCOp_m.nc" not in skip:
        write_pisco_file(directory / "PISCOp_m.nc", monthly_steps)
    if "PISCOp_clim2.nc" not in skip:
        write_pisco_file(
            directory / "PISCOp_clim2.nc",
            CLIMATOLOGY_STEPS,
            variable="PISCOp_clim2",
            units=None,
            n_lon=N_LON_CLIM,
            lon_start=LON_START_CLIM,
        )
    return directory


@pytest.fixture(scope="session")
def data_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A data directory with the three synthetic PISCOp files (shared, read-only)."""
    return write_default_files(tmp_path_factory.mktemp("data"))


@pytest.fixture
def make_data_dir(tmp_path: Path) -> Callable[..., Path]:
    """Factory for custom data directories: `make_data_dir(monthly_steps=528, skip=(...))`."""

    def factory(**kwargs: object) -> Path:
        return write_default_files(tmp_path / "custom", **kwargs)  # type: ignore[arg-type]

    return factory


@pytest.fixture
def make_client() -> Iterator[Callable[[Path], TestClient]]:
    """Factory returning a started TestClient for a given data directory."""
    from app.config import Settings
    from app.main import create_app

    clients: list[TestClient] = []

    def factory(directory: Path) -> TestClient:
        client = TestClient(create_app(Settings(data_dir=directory)))
        client.__enter__()  # run the lifespan (open files)
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client.__exit__(None, None, None)  # close files (Windows file locks)


@pytest.fixture
def client(make_client: Callable[[Path], TestClient], data_dir: Path) -> TestClient:
    """A started TestClient backed by the three synthetic files."""
    return make_client(data_dir)
