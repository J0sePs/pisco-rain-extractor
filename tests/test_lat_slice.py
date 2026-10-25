import numpy as np
import xarray as xr

from app.repositories.pisco_repository import lat_slice

SOUTH, NORTH = -1.05, 0.95


def _grid(dtype: type = np.float64) -> xr.DataArray:
    lat = np.round(1.95 - 0.1 * np.arange(210), 2).astype(dtype)
    return xr.DataArray(np.arange(lat.size), coords={"lat": lat}, dims="lat")


def test_descending_grid_selects_21_rows() -> None:
    da = _grid()
    selected = da.sel(lat=lat_slice(da["lat"].values, SOUTH, NORTH))
    assert selected.sizes["lat"] == 21
    assert np.isclose(selected["lat"][0], 0.95)
    assert np.isclose(selected["lat"][-1], -1.05)


def test_ascending_grid_selects_21_rows() -> None:
    da = _grid().sortby("lat")
    selected = da.sel(lat=lat_slice(da["lat"].values, SOUTH, NORTH))
    assert selected.sizes["lat"] == 21


def test_border_stored_as_float32_is_kept() -> None:
    da = _grid(np.float32)
    lat = da["lat"].values.copy()
    border = int(np.argmin(np.abs(lat - np.float32(SOUTH))))
    lat[border] = np.nextafter(np.float32(SOUTH), np.float32(-2))  # -1.05000007
    da = da.assign_coords(lat=lat)
    assert lat[border] < SOUTH

    assert da.sel(lat=lat_slice(lat, SOUTH, NORTH)).sizes["lat"] == 21
    # Without the tolerance the border row is lost: the bug lat_slice prevents.
    assert da.sel(lat=slice(NORTH, SOUTH)).sizes["lat"] == 20


def test_range_outside_grid_selects_nothing() -> None:
    da = _grid()
    assert da.sel(lat=lat_slice(da["lat"].values, 5.0, 6.0)).sizes["lat"] == 0
