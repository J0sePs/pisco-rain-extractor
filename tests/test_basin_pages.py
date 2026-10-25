import os
import pathlib
import re
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import LineString, box

from app.services.basin_geometry import MAX_UPLOAD_BYTES, NO_PRJ_MESSAGE, UNSUPPORTED_MESSAGE
from app.services.basin_store import BasinStore
from tests.basin_files import geojson_bytes, rectangle_frame, rectangle_geojson, zipped_shapefile
from tests.conftest import write_default_files, write_pisco_file
from tests.test_point_result_pages import precipitation_reads  # noqa: F401 (fixture)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
RESULT_URL = re.compile(r"^/basin/result/[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$")
EXPIRED = "This result has expired; upload the basin again"
FOUR_CELLS = (-76.30, -12.40, -76.10, -12.20)
OCEAN_BASIN = (-76.40, -12.50, -76.20, -12.30)
YEARS = {"start_year": "1981", "end_year": "1985"}
INVALID_IDS = (
    "not-a-uuid",
    "3F2B8C1E9D4A4B7C8E6F1A2B3C4D5E6F",
    "3f2b8c1e-9d4a-4b7c-8e6f-1a2b3c4d5e6f",
    "0123456789abcdef0123456789abcdef",
)


@pytest.fixture
def store_dir(tmp_path: Path) -> Path:
    return tmp_path / "store"


@pytest.fixture
def basin_client(make_client: Callable, reference_dir: Path, store_dir: Path) -> TestClient:
    return make_client(reference_dir, store_dir)


def _post(
    client: TestClient,
    content: bytes,
    filename: str = "basin.geojson",
    years: dict[str, str] = YEARS,
) -> object:
    files = {"basin_file": (filename, content, "application/octet-stream")}
    return client.post("/basin", data=years, files=files, follow_redirects=False)


def _result_url(client: TestClient, rect: tuple[float, ...] = FOUR_CELLS, **kwargs: object) -> str:
    response = _post(client, rectangle_geojson(*rect), **kwargs)  # type: ignore[arg-type]
    assert response.status_code == 303, response.text
    return response.headers["location"]


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _section(html: str, tab: str) -> str:
    return html.split(f'id="{tab}"', 1)[1].split("</section>", 1)[0]


# --- form ------------------------------------------------------------------------------------


def test_form_defaults(basin_client: TestClient) -> None:
    html = basin_client.get("/basin").text
    assert '<form method="post" action="/basin" enctype="multipart/form-data"' in html
    assert '<input type="file" name="basin_file" accept=".geojson,.json,.zip">' in html
    assert '<input name="start_year" value="1981"' in html
    assert '<input name="end_year" value="2025"' in html


def test_form_without_daily_file(make_client: Callable, tmp_path: Path) -> None:
    client = make_client(write_default_files(tmp_path / "d", skip=("PISCOp_d.nc",)))
    html = client.get("/basin").text
    assert "Daily data is not available" in html
    assert "<form" not in html


# --- errors ----------------------------------------------------------------------------------


def _bad_files(tmp_path: Path) -> list[tuple[str, bytes, str]]:
    frame = rectangle_frame(*FOUR_CELLS)
    return [
        ("basin.kml", b"<kml/>", UNSUPPORTED_MESSAGE),
        ("basin.geojson", b" " * (MAX_UPLOAD_BYTES + 1), "The file is larger than 10 MB"),
        ("basin.zip", zipped_shapefile(tmp_path / "a", frame, drop=(".prj",)), NO_PRJ_MESSAGE),
        (
            "basin.zip",
            zipped_shapefile(tmp_path / "b", frame, drop=(".dbf",)),
            "The ZIP must contain .shp, .shx, .dbf and .prj files (missing: .dbf)",
        ),
        (
            "basin.zip",
            zipped_shapefile(tmp_path / "c", frame, rename={"basin.shp": "../basin.shp"}),
            "The ZIP contains an invalid file path",
        ),
        (
            "basin.zip",
            zipped_shapefile(tmp_path / "d", frame, prj_text="not a projection"),
            "The .prj file does not describe a known coordinate system",
        ),
        ("basin.geojson", geojson_bytes([]), "The file contains no polygon"),
        (
            "basin.geojson",
            geojson_bytes([LineString([(-76.3, -12.4), (-76.1, -12.2)])]),
            "The basin must be a polygon or multipolygon",
        ),
        ("basin.geojson", b"hello", "The file could not be read as GeoJSON"),
        (
            "basin.geojson",
            rectangle_geojson(-70.50, -10.50, -70.00, -10.00),
            "The basin is outside the PISCOp grid "
            "(longitude -76.4 to -76.0, latitude -12.5 to -12.0)",
        ),
    ]


def test_upload_errors(basin_client: TestClient, tmp_path: Path, store_dir: Path) -> None:
    for filename, content, message in _bad_files(tmp_path):
        response = _post(basin_client, content, filename)
        assert response.status_code == 422, filename
        assert message in response.text, message
    assert not store_dir.exists() or not any(store_dir.iterdir())


def test_invalid_geometry(basin_client: TestClient) -> None:
    bow_tie = {
        "type": "Polygon",
        "coordinates": [
            [[-76.3, -12.4], [-76.1, -12.2], [-76.1, -12.4], [-76.3, -12.2], [-76.3, -12.4]]
        ],
    }
    response = _post(basin_client, geojson_bytes([bow_tie]))
    assert response.status_code == 422
    assert "The basin geometry is invalid" in response.text


def test_no_file_chosen(basin_client: TestClient) -> None:
    for response in (
        basin_client.post("/basin", data=YEARS),
        _post(basin_client, b"", filename=""),
    ):
        assert response.status_code == 422
        assert "Choose a basin file to upload" in response.text


@pytest.mark.parametrize(
    ("years", "message"),
    [
        ({"start_year": "1985", "end_year": "1981"}, "Start year must not be later than end year"),
        ({"start_year": "1980", "end_year": "1985"}, "Years must be between 1981 and 2025"),
    ],
)
def test_year_errors(basin_client: TestClient, years: dict[str, str], message: str) -> None:
    response = _post(basin_client, rectangle_geojson(*FOUR_CELLS), years=years)
    assert response.status_code == 422
    assert message in response.text
    assert 'value="1985"' in response.text  # years kept in the form


def test_years_checked_before_parsing(basin_client: TestClient) -> None:
    response = _post(basin_client, b"hello", years={"start_year": "1985", "end_year": "1981"})
    assert "Start year must not be later than end year" in response.text


def test_basin_too_large(make_client: Callable, tmp_path: Path) -> None:
    (tmp_path / "large").mkdir()
    write_pisco_file(tmp_path / "large" / "PISCOp_d.nc", 365, n_lat=60, n_lon=60)
    client = make_client(tmp_path / "large")
    response = _post(
        client,
        rectangle_geojson(-81.35, -3.05, -76.45, 1.95),
        years={"start_year": "1981", "end_year": "1981"},
    )
    assert response.status_code == 422
    assert "covers 2550 grid cells (maximum 2500)" in response.text


# --- result ----------------------------------------------------------------------------------


def test_redirect_and_result_without_reads(
    basin_client: TestClient,
    precipitation_reads: list[tuple[int, ...]],  # noqa: F811
) -> None:
    url = _result_url(basin_client)
    assert RESULT_URL.match(url)
    precipitation_reads.clear()
    assert basin_client.get(url).status_code == 200
    assert precipitation_reads == []


def test_two_posts_two_ids(basin_client: TestClient) -> None:
    assert _result_url(basin_client) != _result_url(basin_client)


def test_tabs_and_no_scripts(basin_client: TestClient) -> None:
    html = basin_client.get(_result_url(basin_client)).text
    for tab in ("summary", "daily", "annual", "climatology", "cells"):
        assert f'href="#{tab}"' in html
        assert f'id="{tab}"' in html
    assert "<script" not in html.lower()
    for tag in re.findall(r"<(?:link|script|img)\b[^>]*>", html, re.I):
        assert not re.search(r'(?:href|src)="https?://', tag), tag


def test_daily_pagination(basin_client: TestClient) -> None:
    url = _result_url(basin_client)
    html = basin_client.get(f"{url}?page=2").text
    daily = _section(html, "daily")
    assert "Page 2 of 6" in daily
    assert "<td>1982-01-01</td>" in daily
    assert f'href="{url}?page=1#daily"' in daily


def test_summary(basin_client: TestClient) -> None:
    text = _text(_section(basin_client.get(_result_url(basin_client, OCEAN_BASIN)).text, "summary"))
    for expected in (
        "481.2 km²",
        "3 cells used",
        "1 cell excluded (no data)",
        "1981-01-01 to 1985-12-31",
        "Total days 1826",
    ):
        assert expected in text, expected
    assert "dissolved" not in text


def test_dissolve_notice(basin_client: TestClient) -> None:
    content = geojson_bytes(
        [box(-76.30, -12.40, -76.20, -12.20), box(-76.20, -12.40, -76.10, -12.20)]
    )
    response = _post(basin_client, content)
    html = basin_client.get(response.headers["location"]).text
    assert "2 features were dissolved into one basin" in html
    assert "4 cells used" in _text(html)


def test_fallback_warning(basin_client: TestClient) -> None:
    html = basin_client.get(_result_url(basin_client, (-76.14, -12.24, -76.12, -12.22))).text
    assert (
        "No cell center falls inside the basin; the cell nearest to its centroid was used" in html
    )


def test_cells_tab(basin_client: TestClient) -> None:
    cells = _section(basin_client.get(_result_url(basin_client, OCEAN_BASIN)).text, "cells")
    rows = re.findall(r"<tr[^>]*><td>(.*?)</td><td>(.*?)</td><td>(.*?)</td></tr>", cells)
    assert len(rows) == 4
    assert ("-76.35", "-12.45", "Excluded (no data)") in rows
    assert '/chart/cells.png"' in cells


def test_shapefile_in_utm(basin_client: TestClient, tmp_path: Path) -> None:
    content = zipped_shapefile(tmp_path, rectangle_frame(*FOUR_CELLS, epsg=32718))
    response = _post(basin_client, content, "basin.zip")
    assert response.status_code == 303
    assert "4 cells used" in _text(basin_client.get(response.headers["location"]).text)


# --- charts ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kind", ["daily", "annual-totals", "annual-maxima", "climatology", "cells"]
)
def test_chart_png_without_reads(
    basin_client: TestClient,
    kind: str,
    precipitation_reads: list[tuple[int, ...]],  # noqa: F811
) -> None:
    url = _result_url(basin_client)
    precipitation_reads.clear()
    response = basin_client.get(f"{url}/chart/{kind}.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(PNG_SIGNATURE)
    assert precipitation_reads == []


def test_unknown_chart_or_id(basin_client: TestClient) -> None:
    url = _result_url(basin_client)
    assert basin_client.get(f"{url}/chart/location.png").status_code == 404
    assert (
        basin_client.get(
            "/basin/result/3f2b8c1e9d4a4b7c8e6f1a2b3c4d5e6f/chart/daily.png"
        ).status_code
        == 404
    )


# --- no data ---------------------------------------------------------------------------------


def test_all_cells_without_data(basin_client: TestClient, store_dir: Path) -> None:
    response = _post(basin_client, rectangle_geojson(-76.40, -12.50, -76.30, -12.40))
    assert response.status_code == 200
    assert "No data available for this basin" in response.text
    assert "/export/" not in response.text
    assert not store_dir.exists() or not any(store_dir.iterdir())


# --- expired, unknown and invalid ids ----------------------------------------------------------


def test_unknown_id(basin_client: TestClient) -> None:
    response = basin_client.get("/basin/result/3f2b8c1e9d4a4b7c8e6f1a2b3c4d5e6f")
    assert response.status_code == 404
    assert EXPIRED in _text(response.text)
    assert '<a href="/basin">upload the basin again</a>' in response.text


def test_expired_id(basin_client: TestClient, store_dir: Path) -> None:
    url = _result_url(basin_client)
    path = store_dir / f"{url.rsplit('/', 1)[1]}.json"
    stamp = time.time() - 25 * 3600
    os.utime(path, (stamp, stamp))
    response = basin_client.get(url)
    assert response.status_code == 404
    assert EXPIRED in _text(response.text)
    assert '<a href="/basin">' in response.text
    assert not path.exists()


def test_expired_result_removed_by_new_post(basin_client: TestClient, store_dir: Path) -> None:
    old = _result_url(basin_client)
    path = store_dir / f"{old.rsplit('/', 1)[1]}.json"
    stamp = time.time() - 25 * 3600
    os.utime(path, (stamp, stamp))
    _result_url(basin_client)
    assert not path.exists()
    assert EXPIRED in _text(basin_client.get(old).text)


FILE_SYSTEM_CALLS = (
    (os, "stat"),
    (os, "scandir"),
    (os, "remove"),
    (os, "unlink"),
    (pathlib.Path, "open"),
    (pathlib.Path, "stat"),
    (pathlib.Path, "exists"),
    (pathlib.Path, "unlink"),
    (pathlib.Path, "read_text"),
)


def _spy_store_access(monkeypatch: pytest.MonkeyPatch, store_dir: Path) -> list[str]:
    """Record file-system calls whose arguments name the store or `pyproject.toml`.

    Unrelated I/O (such as Jinja checking its template files) is ignored: only the paths a
    result id could reach are watched.
    """
    calls: list[str] = []

    def spy(name: str, original: Callable) -> Callable:
        def wrapper(*args: object, **kwargs: object) -> object:
            text = " ".join(str(a) for a in args)
            if str(store_dir) in text or "pyproject" in text:
                calls.append(f"{name} {text}")
            return original(*args, **kwargs)

        return wrapper

    for owner, attr in FILE_SYSTEM_CALLS:
        monkeypatch.setattr(owner, attr, spy(attr, getattr(owner, attr)))
    return calls


def _spy_loads(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    loads: list[str] = []
    original = BasinStore.load

    def load(self: BasinStore, result_id: str) -> object:
        loads.append(result_id)
        return original(self, result_id)

    monkeypatch.setattr(BasinStore, "load", load)
    return loads


@pytest.mark.parametrize("result_id", INVALID_IDS)
def test_invalid_ids_never_touch_the_disk(
    basin_client: TestClient, store_dir: Path, result_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _result_url(basin_client)  # the store directory exists and holds a result
    calls = _spy_store_access(monkeypatch, store_dir)
    loads = _spy_loads(monkeypatch)

    for path in (
        f"/basin/result/{result_id}",
        f"/basin/result/{result_id}/chart/daily.png",
        f"/basin/result/{result_id}/export/daily.csv",
        f"/basin/result/{result_id}/export.xlsx",
    ):
        response = basin_client.get(path)
        assert response.status_code == 404, path
    assert EXPIRED in _text(basin_client.get(f"/basin/result/{result_id}").text)
    assert calls == [] and loads == []


def test_path_traversal(
    basin_client: TestClient, store_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    before = pyproject.stat().st_mtime_ns
    calls = _spy_store_access(monkeypatch, store_dir)
    loads = _spy_loads(monkeypatch)
    response = basin_client.get("/basin/result/..%2F..%2Fpyproject.toml")
    assert response.status_code == 404
    assert calls == [] and loads == []
    monkeypatch.undo()
    assert pyproject.stat().st_mtime_ns == before


def test_no_upload_left_behind(basin_client: TestClient, tmp_path: Path, store_dir: Path) -> None:
    before = set(Path(tempfile.gettempdir()).glob("*.zip")) | set(
        Path(tempfile.gettempdir()).glob("*.shp")
    )
    _post(basin_client, zipped_shapefile(tmp_path / "z", rectangle_frame(*FOUR_CELLS)), "basin.zip")
    stored = list(store_dir.iterdir())
    assert len(stored) == 1 and stored[0].suffix == ".json"
    after = set(Path(tempfile.gettempdir()).glob("*.zip")) | set(
        Path(tempfile.gettempdir()).glob("*.shp")
    )
    assert after <= before


def test_store_spy_sees_valid_ids(
    basin_client: TestClient, store_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Positive control: a well-formed id does reach the store, and the spies notice it.
    _result_url(basin_client)
    calls = _spy_store_access(monkeypatch, store_dir)
    loads = _spy_loads(monkeypatch)
    basin_client.get("/basin/result/3f2b8c1e9d4a4b7c8e6f1a2b3c4d5e6f")
    assert calls and loads == ["3f2b8c1e9d4a4b7c8e6f1a2b3c4d5e6f"]
