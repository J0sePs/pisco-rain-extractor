import os
import pathlib
import re
import time
import uuid
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from app.services.basin_geometry import BasinGeometry
from app.services.basin_service import BasinCell, BasinResult
from app.services.basin_store import BasinStore, is_result_id

UUID4_HEX = re.compile(r"^[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$")
INVALID_IDS = (
    "../../pyproject.toml",
    "not-a-uuid",
    "3F2B8C1E9D4A4B7C8E6F1A2B3C4D5E6F",
    "3f2b8c1e-9d4a-4b7c-8e6f-1a2b3c4d5e6f",
    "0123456789abcdef0123456789abcdef",
    "3f2b8c1e9d4a4b7c8e6f1a2b3c4d5e6f\n",
    "",
)
HOUR = 3600


def _result() -> BasinResult:
    index = pd.date_range("1981-01-01", periods=5, freq="D", name="date")
    series = pd.Series([1.5, np.nan, 0.1, 3.0, 0.0], index=index, name="precipitation_mm")
    return BasinResult(
        basin=BasinGeometry("basin.geojson", 2, box(-76.30, -12.40, -76.10, -12.20)),
        area_km2=481.4,
        centroid_lon=-76.2000001,
        centroid_lat=-12.3000002,
        fallback=False,
        cells=[BasinCell(-76.25, -12.25, True, 4), BasinCell(-76.35, -12.45, False, 0)],
        resolution_deg=0.1,
        start_year=1981,
        end_year=1981,
        period_start=date(1981, 1, 1),
        period_end=date(1981, 1, 5),
        total_days=5,
        missing_days=1,
        series=series,
    )


@pytest.fixture
def store(tmp_path: Path) -> BasinStore:
    return BasinStore(tmp_path / "basins", timedelta(hours=24))


def _age(path: Path, hours: float) -> None:
    stamp = time.time() - hours * HOUR
    os.utime(path, (stamp, stamp))


def test_round_trip(store: BasinStore) -> None:
    original = _result()
    loaded = store.load(store.save(original))
    assert loaded is not None
    pd.testing.assert_series_equal(loaded.series, original.series, check_freq=False)
    assert loaded.basin.geometry.equals(original.basin.geometry)
    assert (loaded.basin.filename, loaded.basin.features) == ("basin.geojson", 2)
    assert loaded.cells == original.cells
    assert (loaded.period_start, loaded.period_end) == (date(1981, 1, 1), date(1981, 1, 5))
    assert (loaded.total_days, loaded.missing_days) == (5, 1)
    assert loaded.centroid_lon == original.centroid_lon
    assert loaded.area_km2 == 481.4 and loaded.fallback is False


def test_ids_are_random_uuid4(store: BasinStore) -> None:
    first, second = store.save(_result()), store.save(_result())
    assert UUID4_HEX.match(first) and UUID4_HEX.match(second)
    assert first != second


def test_one_json_file_per_result_and_no_temp_file(store: BasinStore, tmp_path: Path) -> None:
    assert not (tmp_path / "basins").exists()
    result_id = store.save(_result())
    assert [p.name for p in (tmp_path / "basins").iterdir()] == [f"{result_id}.json"]


def test_expired_result_purged_on_next_save(store: BasinStore, tmp_path: Path) -> None:
    old = store.save(_result())
    _age(tmp_path / "basins" / f"{old}.json", 25)
    new = store.save(_result())
    assert not (tmp_path / "basins" / f"{old}.json").exists()
    assert store.load(old) is None
    assert store.load(new) is not None


def test_expired_result_deleted_on_load(store: BasinStore, tmp_path: Path) -> None:
    result_id = store.save(_result())
    _age(tmp_path / "basins" / f"{result_id}.json", 25)
    assert store.load(result_id) is None
    assert not (tmp_path / "basins" / f"{result_id}.json").exists()


def test_recent_result_kept(store: BasinStore, tmp_path: Path) -> None:
    result_id = store.save(_result())
    _age(tmp_path / "basins" / f"{result_id}.json", 23)
    assert store.purge_expired() == 0
    assert store.load(result_id) is not None


def test_purge_ignores_foreign_files(store: BasinStore, tmp_path: Path) -> None:
    store.save(_result())
    foreign = tmp_path / "basins" / "notes.json"
    foreign.write_text("{}", encoding="utf-8")
    _age(foreign, 48)
    store.purge_expired()
    assert foreign.exists()


def test_is_result_id() -> None:
    assert is_result_id(uuid.uuid4().hex)
    assert is_result_id("3f2b8c1e9d4a4b7c8e6f1a2b3c4d5e6f")
    for value in INVALID_IDS:
        assert not is_result_id(value), value


@pytest.fixture
def filesystem_calls(monkeypatch: pytest.MonkeyPatch) -> Callable[[], list[str]]:
    """Install spies on file-system entry points; call the returned function to read them."""
    calls: list[str] = []

    def spy(name: str, original: Callable) -> Callable:
        def wrapper(*args: object, **kwargs: object) -> object:
            calls.append(name)
            return original(*args, **kwargs)

        return wrapper

    def install() -> list[str]:
        for owner, attr in (
            (os, "stat"),
            (os, "scandir"),
            (os, "remove"),
            (os, "unlink"),
            (pathlib.Path, "open"),
            (pathlib.Path, "stat"),
            (pathlib.Path, "exists"),
            (pathlib.Path, "unlink"),
            (pathlib.Path, "read_text"),
        ):
            monkeypatch.setattr(owner, attr, spy(f"{owner.__name__}.{attr}", getattr(owner, attr)))
        return calls

    return install


def test_invalid_ids_never_touch_the_disk(
    store: BasinStore, filesystem_calls: Callable[[], list[str]]
) -> None:
    calls = filesystem_calls()
    for value in INVALID_IDS:
        assert store.load(value) is None
    assert calls == []


def test_unknown_valid_id(store: BasinStore) -> None:
    store.save(_result())
    assert store.load("3f2b8c1e9d4a4b7c8e6f1a2b3c4d5e6f") is None


def test_spy_sees_disk_access_for_valid_ids(
    store: BasinStore, filesystem_calls: Callable[[], list[str]]
) -> None:
    # Positive control: the spy above would catch a real file-system call.
    calls = filesystem_calls()
    assert store.load("3f2b8c1e9d4a4b7c8e6f1a2b3c4d5e6f") is None
    assert "Path.stat" in calls
