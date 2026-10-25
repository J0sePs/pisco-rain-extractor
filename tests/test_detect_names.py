from pathlib import Path

import pytest
import xarray as xr

from app.repositories.pisco_repository import DatasetStructureError, detect_names
from tests.conftest import write_pisco_file


def _open(path: Path) -> xr.Dataset:
    return xr.open_dataset(path, engine="netcdf4", decode_times=False)


def test_pisco_naming(tmp_path: Path) -> None:
    path = write_pisco_file(tmp_path / "d.nc", 10)
    with _open(path) as ds:
        names = detect_names(ds)
    assert (names.variable, names.lat, names.lon, names.time) == (
        "precipitation",
        "latitude",
        "longitude",
        "Z1",
    )


def test_alternative_naming(tmp_path: Path) -> None:
    path = write_pisco_file(
        tmp_path / "c.nc",
        12,
        variable="PISCOp_clim2",
        units=None,
        lat_name="lat",
        lon_name="lon",
        time_name="month",
    )
    with _open(path) as ds:
        names = detect_names(ds)
    assert (names.variable, names.lat, names.lon, names.time) == (
        "PISCOp_clim2",
        "lat",
        "lon",
        "month",
    )


def test_no_precipitation_variable(tmp_path: Path) -> None:
    path = write_pisco_file(tmp_path / "empty.nc", 10, include_precipitation=False)
    with _open(path) as ds, pytest.raises(DatasetStructureError, match="no precipitation"):
        detect_names(ds)
