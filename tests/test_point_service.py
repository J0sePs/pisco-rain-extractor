import ast
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from xarray.backends import netCDF4_

from app.config import Settings
from app.repositories.pisco_repository import PiscoRepository
from app.services import point_service
from app.services.point_service import (
    NO_DATA_MESSAGE,
    NoDataError,
    PointForm,
    PointInputError,
    convert_utm,
    extract_point,
    year_defaults,
)
from tests.conftest import DAILY_STEPS, write_reference_dir

REF = {"lon": "-76.1390222", "lat": "-12.2935861"}


def _open(directory: Path) -> PiscoRepository:
    return PiscoRepository.open(Settings(data_dir=directory))


@pytest.fixture
def repo(reference_dir: Path) -> Iterator[PiscoRepository]:
    repository = _open(reference_dir)
    yield repository
    repository.close()


def _form(**values: str) -> PointForm:
    return PointForm(**{"start_year": "1981", "end_year": "1981", **REF, **values})


def test_year_defaults(repo: PiscoRepository) -> None:
    assert year_defaults(repo) == (1981, 2025)


def test_year_defaults_last_year_incomplete(tmp_path: Path) -> None:
    # 184 days fewer: the file ends on 2025-06-30.
    repository = _open(write_reference_dir(tmp_path / "short", daily_steps=DAILY_STEPS - 184))
    try:
        assert year_defaults(repository) == (1981, 2024)
    finally:
        repository.close()


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"lon": "west"}, "Longitude must be a number"),
        ({"lat": "twelve"}, "Latitude must be a number"),
        ({"start_year": "x"}, "Start year must be an integer"),
        ({"end_year": ""}, "End year must be an integer"),
        (
            {"lon": "-60.0", "lat": "-12.0"},
            "The point is outside the PISCOp grid "
            "(longitude -76.4 to -76.0, latitude -12.5 to -12.0)",
        ),
        ({"start_year": "2010", "end_year": "2000"}, "Start year must not be later than end year"),
        ({"start_year": "1975", "end_year": "1990"}, "Years must be between 1981 and 2025"),
    ],
)
def test_validation_messages(repo: PiscoRepository, fields: dict, message: str) -> None:
    with pytest.raises(PointInputError) as error:
        extract_point(repo, _form(**fields))
    assert str(error.value) == message


@pytest.mark.parametrize(
    "fields",
    [{"lon": "-60.0", "lat": "-12.0"}, {"start_year": "1975", "end_year": "1990"}],
)
def test_errors_happen_before_any_read(
    repo: PiscoRepository, monkeypatch: pytest.MonkeyPatch, fields: dict
) -> None:
    if not hasattr(netCDF4_.NetCDF4ArrayWrapper, "_getitem"):
        pytest.fail("xarray internals changed; update the read spy")
    reads: list[str] = []
    original = netCDF4_.NetCDF4ArrayWrapper._getitem

    def spy(self: netCDF4_.NetCDF4ArrayWrapper, key: object) -> np.ndarray:
        reads.append(self.variable_name)
        return original(self, key)

    monkeypatch.setattr(netCDF4_.NetCDF4ArrayWrapper, "_getitem", spy)
    with pytest.raises(PointInputError):
        extract_point(repo, _form(**fields))
    assert "precipitation" not in reads


def test_summary_with_missing_days(repo: PiscoRepository) -> None:
    result = extract_point(repo, _form())
    assert (result.cell.lon, result.cell.lat) == (-76.15, -12.25)
    assert result.distance_km == 4.991
    assert (str(result.period_start), str(result.period_end)) == ("1981-01-01", "1981-12-31")
    assert (result.total_days, result.missing_days) == (365, 2)
    assert [d for d, _ in result.head] == [f"1981-01-0{i}" for i in range(1, 6)]
    assert [d for d, _ in result.tail] == [f"1981-12-{i}" for i in range(27, 32)]
    assert result.head[2] == ("1981-01-03", None)  # missing day
    assert result.head[1] == ("1981-01-02", 1.5)
    assert list(result.series.columns) == ["date", "precipitation_mm"]
    assert len(result.series) == 365


def test_single_leap_year(repo: PiscoRepository) -> None:
    result = extract_point(repo, _form(start_year="2000", end_year="2000"))
    assert result.total_days == 366


def test_tie_point_goes_north(repo: PiscoRepository) -> None:
    result = extract_point(repo, _form(lon="-76.15", lat="-12.30"))
    assert result.cell.lat == -12.25
    assert result.distance_km == 5.560


def test_all_missing_cell_raises_no_data(repo: PiscoRepository) -> None:
    with pytest.raises(NoDataError) as error:
        extract_point(repo, _form(lon="-76.35", lat="-12.45"))
    assert str(error.value) == NO_DATA_MESSAGE


def test_convert_utm_reference() -> None:
    form = PointForm(easting="376135.41", northing="8640719.67", zone="18", hemisphere="South")
    assert convert_utm(form) == (-76.139022, -12.293586)


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"easting": "abc"}, "Easting must be a number"),
        ({"northing": ""}, "Northing must be a number"),
        ({"zone": "20"}, "UTM zone must be 17, 18 or 19"),
        ({"zone": "x"}, "UTM zone must be 17, 18 or 19"),
        ({"hemisphere": "West"}, "Hemisphere must be North or South"),
    ],
)
def test_convert_utm_errors(fields: dict, message: str) -> None:
    base = {"easting": "376135.41", "northing": "8640719.67", "zone": "18", "hemisphere": "South"}
    with pytest.raises(PointInputError) as error:
        convert_utm(PointForm(**{**base, **fields}))
    assert str(error.value) == message


def test_service_does_not_import_fastapi() -> None:
    tree = ast.parse(Path(point_service.__file__).read_text(encoding="utf-8"))
    modules = {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not modules & {"fastapi", "starlette", "xarray"}
