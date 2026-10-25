"""Guard the synthetic fixtures against drifting from the real PISCOp v3.0 structure."""

from pathlib import Path

import numpy as np
import xarray as xr


def _open(path: Path) -> xr.Dataset:
    return xr.open_dataset(path, engine="netcdf4", decode_times=False)


def test_time_axis_is_integer_index(data_dir: Path) -> None:
    with _open(data_dir / "PISCOp_d.nc") as ds:
        z1 = ds["Z1"]
        assert np.issubdtype(z1.dtype, np.integer)
        assert z1.attrs["units"] == "unknown"
        assert int(z1[0]) == 1
        assert ds.sizes["Z1"] == 16436
    with xr.open_dataset(data_dir / "PISCOp_d.nc", engine="netcdf4") as decoded:
        assert np.issubdtype(decoded["Z1"].dtype, np.integer)  # not decoded as dates


def test_latitude_is_descending_float32(data_dir: Path) -> None:
    with _open(data_dir / "PISCOp_d.nc") as ds:
        lat = ds["latitude"].values
        assert lat.dtype == np.float32
        assert np.isclose(lat[0], 1.95)
        assert np.all(np.diff(lat) < 0)
        assert ds["longitude"].dtype == np.float32
        assert np.all(np.diff(ds["longitude"].values) > 0)


def test_daily_variable_and_crs(data_dir: Path) -> None:
    with _open(data_dir / "PISCOp_d.nc") as ds:
        assert ds["precipitation"].attrs["units"] == "mm"
        assert ds["precipitation"].attrs["grid_mapping"] == "crs"
        assert ds["crs"].ndim == 0


def test_climatology_has_no_units_and_another_grid(data_dir: Path) -> None:
    with _open(data_dir / "PISCOp_clim2.nc") as clim, _open(data_dir / "PISCOp_d.nc") as daily:
        assert "units" not in clim["PISCOp_clim2"].attrs
        assert clim.sizes["Z1"] == 12
        assert clim.sizes["longitude"] != daily.sizes["longitude"]


def test_basin_fixtures_shape_and_chunking(
    basin_dir: Path, varied_dir: Path, chunked_dir: Path
) -> None:
    for directory in (basin_dir, varied_dir, chunked_dir):
        with _open(directory / "PISCOp_d.nc") as ds:
            assert ds["precipitation"].shape == (16436, 5, 4)
    with _open(basin_dir / "PISCOp_d.nc") as ds:
        assert ds["precipitation"].encoding.get("chunksizes") is None
    with _open(chunked_dir / "PISCOp_d.nc") as ds:
        assert tuple(ds["precipitation"].encoding["chunksizes"]) == (100, 2, 2)
    with _open(varied_dir / "PISCOp_d.nc") as ds:
        cell = ds["precipitation"].isel(Z1=slice(0, 40), latitude=2, longitude=1).values
        assert np.all(cell[:31] == 9.0)  # i * 4 + j for (2, 1)
        assert np.isnan(cell[31])  # 1981-02-01: every cell missing
