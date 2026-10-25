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


def make_coords(
    n: int, start: float, step: float, ascending: bool = True, dtype: type = np.float32
) -> np.ndarray:
    """Return coordinates `start, start+step, ...` (or descending with `-step`)."""
    values = start + (step if ascending else -step) * np.arange(n)
    return np.round(values, 6).astype(dtype)


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
    time_units: str = "unknown",
    time_start_value: int = 1,
    lat_start: float = LAT_START,
    values: Callable[[tuple[int, int, int]], np.ndarray] | np.ndarray | None = None,
    coord_dtype: type = np.float32,
    chunksizes: tuple[int, int, int] | None = None,
) -> Path:
    """Write a small NetCDF file with the PISCOp v3.0 layout and return its path.

    By default the time axis is an integer index 1..N with `units: unknown`, as in the real
    files. Pass CF units (e.g. "days since 1981-01-01") to build a file with real dates.
    `values` fills the precipitation grid (time, lat, lon) in descending-latitude order; it is
    an array or a callable receiving the shape. Default: zeros. `chunksizes` stores the
    precipitation variable chunked (time, lat, lon), like the real files; default: contiguous.
    """
    lat = make_coords(n_lat, lat_start, STEP, ascending=False, dtype=coord_dtype)
    lon = make_coords(n_lon, lon_start, STEP, dtype=coord_dtype)
    shape = (n_time, n_lat, n_lon)
    if values is None:
        grid = np.zeros(shape, dtype=np.float32)
    else:
        grid = np.asarray(values(shape) if callable(values) else values, dtype=np.float32)
    if ascending_lat:
        lat = lat[::-1].copy()
        grid = grid[:, ::-1, :].copy()  # keep each value on its own coordinate
    coords = {
        time_name: (
            time_name,
            np.arange(time_start_value, time_start_value + n_time, dtype=np.int32),
            {"units": time_units},
        ),
        lat_name: (lat_name, lat, {"units": "degrees_north", "long_name": "latitude"}),
        lon_name: (lon_name, lon, {"units": "degrees_east", "long_name": "longitude"}),
    }
    data_vars: dict = {"crs": ((), np.int32(0), {"proj4": "+proj=longlat +datum=WGS84"})}
    if include_precipitation:
        attrs = {"grid_mapping": "crs"}
        if units is not None:
            attrs["units"] = units
        data_vars[variable] = ((time_name, lat_name, lon_name), grid, attrs)
    ds = xr.Dataset(data_vars=data_vars, coords=coords)
    encoding = {}
    if chunksizes is not None and include_precipitation:
        encoding[variable] = {"chunksizes": chunksizes}
    ds.to_netcdf(path, engine="netcdf4", encoding=encoding)
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


# Reference grid around the PREC-TJGO point (-76.1390222, -12.2935861): centers at latitude
# -12.05 .. -12.45 (descending) and longitude -76.35 .. -76.05, so (-76.15, -12.25) is a center
# and latitude -12.30 / longitude -76.10 are exact ties between two centers (ADR-0011).
REF_LAT_START = -12.05
REF_LON_START = -76.35
REF_CELL = (2, 2)  # (lat index, lon index) of center (-76.15, -12.25)
REF_MISSING_DAYS = (2, 151)  # 1981-01-03 and 1981-06-01
NAN_CELL = (4, 0)  # center (-76.35, -12.45): every value missing, like an ocean cell


def reference_values(shape: tuple[int, int, int]) -> np.ndarray:
    """Deterministic rainfall: (day % 7) * 1.5 mm, with the missing values described above."""
    n_time, n_lat, n_lon = shape
    daily = (np.arange(n_time) % 7) * 1.5
    grid = np.broadcast_to(daily[:, None, None], shape).astype(np.float32).copy()
    missing = [day for day in REF_MISSING_DAYS if day < n_time]  # short files keep fewer
    grid[missing, REF_CELL[0], REF_CELL[1]] = np.nan
    grid[:, NAN_CELL[0], NAN_CELL[1]] = np.nan
    return grid


def write_reference_dir(directory: Path, coord_dtype: type = np.float32, **kwargs: object) -> Path:
    """Write a daily-only data directory on the reference grid."""
    directory.mkdir(parents=True, exist_ok=True)
    write_pisco_file(
        directory / "PISCOp_d.nc",
        kwargs.pop("daily_steps", DAILY_STEPS),  # type: ignore[arg-type]
        lat_start=REF_LAT_START,
        lon_start=REF_LON_START,
        values=kwargs.pop("values", reference_values),  # type: ignore[arg-type]
        coord_dtype=coord_dtype,
        **kwargs,  # type: ignore[arg-type]
    )
    return directory


@pytest.fixture(scope="session")
def reference_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Daily file on the reference grid with float32 coordinates (shared, read-only)."""
    return write_reference_dir(tmp_path_factory.mktemp("reference"))


@pytest.fixture(scope="session")
def reference_dir_float64(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Same as `reference_dir` with float64 coordinates, as in the real files."""
    return write_reference_dir(tmp_path_factory.mktemp("reference64"), coord_dtype=np.float64)


BASIN_ALL_MISSING_DAY = 31  # 1981-02-01: every cell missing in the varied grid
BASIN_CHUNKS = (100, 2, 2)


def varied_values(shape: tuple[int, int, int]) -> np.ndarray:
    """Cell (i, j) holds `i * 4 + j` mm on every day; all cells missing on 1981-02-01.

    The all-missing cell of the reference grid (`NAN_CELL`) stays missing on every day.
    """
    n_time, n_lat, n_lon = shape
    cells = (np.arange(n_lat)[:, None] * 4 + np.arange(n_lon)[None, :]).astype(np.float32)
    grid = np.broadcast_to(cells[None, :, :], shape).astype(np.float32).copy()
    if n_time > BASIN_ALL_MISSING_DAY:
        grid[BASIN_ALL_MISSING_DAY] = np.nan
    grid[:, NAN_CELL[0], NAN_CELL[1]] = np.nan
    return grid


def write_basin_dir(
    directory: Path,
    *,
    values: Callable[[tuple[int, int, int]], np.ndarray] = reference_values,
    chunksizes: tuple[int, int, int] | None = None,
    **kwargs: object,
) -> Path:
    """Write a daily-only data directory on the reference grid for basin tests."""
    return write_reference_dir(directory, values=values, chunksizes=chunksizes, **kwargs)


@pytest.fixture(scope="session")
def basin_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Reference grid and values, contiguous storage (shared, read-only)."""
    return write_basin_dir(tmp_path_factory.mktemp("basin"))


@pytest.fixture(scope="session")
def varied_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Reference grid with a different constant value per cell (shared, read-only)."""
    return write_basin_dir(tmp_path_factory.mktemp("varied"), values=varied_values)


@pytest.fixture(scope="session")
def chunked_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Reference grid and values stored in chunks of `BASIN_CHUNKS` (shared, read-only)."""
    return write_basin_dir(tmp_path_factory.mktemp("chunked"), chunksizes=BASIN_CHUNKS)


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
def make_client(tmp_path: Path) -> Iterator[Callable[..., TestClient]]:
    """Factory returning a started TestClient for a given data directory.

    The basin result store defaults to `tmp_path / "basins"`, never the repository's `uploads/`.
    """
    from app.config import Settings
    from app.main import create_app

    clients: list[TestClient] = []

    def factory(directory: Path, store_dir: Path | None = None) -> TestClient:
        settings = Settings(data_dir=directory, basin_store_dir=store_dir or tmp_path / "basins")
        client = TestClient(create_app(settings))
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
