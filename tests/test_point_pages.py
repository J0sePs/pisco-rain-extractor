import re
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.conftest import write_default_files

REF_FORM = {
    "lon": "-76.1390222",
    "lat": "-12.2935861",
    "start_year": "1981",
    "end_year": "1981",
    "action": "extract",
}
RESULT_QUERY = "lon=-76.1390222&lat=-12.2935861&start_year=1981&end_year=1981"
UTM_FORM = {
    "easting": "376135.41",
    "northing": "8640719.67",
    "zone": "18",
    "hemisphere": "South",
    "action": "convert",
}


@pytest.fixture
def ref_client(make_client: Callable[[Path], TestClient], reference_dir: Path) -> TestClient:
    return make_client(reference_dir)


def _input_value(html: str, name: str) -> str:
    match = re.search(rf'<input name="{name}" value="([^"]*)"', html)
    assert match, f"input {name} not found"
    return match.group(1)


def test_get_shows_default_years(ref_client: TestClient) -> None:
    response = ref_client.get("/point")
    assert response.status_code == 200
    assert _input_value(response.text, "start_year") == "1981"
    assert _input_value(response.text, "end_year") == "2025"


def test_daily_missing(make_client: Callable, tmp_path: Path) -> None:
    client = make_client(write_default_files(tmp_path / "d", skip=("PISCOp_d.nc",)))
    response = client.get("/point")
    assert response.status_code == 200
    assert "Daily data is not available" in response.text
    assert 'href="/dataset"' in response.text
    assert "<form" not in response.text


def test_convert_fills_coordinates(ref_client: TestClient) -> None:
    response = ref_client.post("/point", data=UTM_FORM)
    assert response.status_code == 200
    assert _input_value(response.text, "lon") == "-76.139022"
    assert _input_value(response.text, "lat") == "-12.293586"
    assert 'id="result"' not in response.text


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"zone": "20"}, "UTM zone must be 17, 18 or 19"),
        ({"easting": "abc"}, "Easting must be a number"),
    ],
)
def test_convert_errors(ref_client: TestClient, fields: dict, message: str) -> None:
    response = ref_client.post("/point", data={**UTM_FORM, "lon": "-70", "lat": "-10", **fields})
    assert response.status_code == 422
    assert message in response.text
    assert _input_value(response.text, "lon") == "-70"  # unchanged


def test_extract_redirects_to_result(ref_client: TestClient) -> None:
    response = ref_client.post(
        "/point", data={**REF_FORM, "end_year": "1985"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == (
        "/point/result?lon=-76.1390222&lat=-12.2935861&start_year=1981&end_year=1985"
    )


def test_reference_extraction(ref_client: TestClient) -> None:
    response = ref_client.post("/point", data=REF_FORM)  # follows the redirect
    assert response.status_code == 200
    assert str(response.url).endswith("/point/result?" + RESULT_QUERY)
    result = response.text.split('id="result"', 1)[1]
    assert "longitude -76.15, latitude -12.25" in result
    assert "4.991 km" in result
    assert "1981-01-01 to 1981-12-31" in result
    assert "<dd>365</dd>" in result and "<dd>2</dd>" in result
    assert "<td>1981-01-03</td><td>missing</td>" in result
    assert "First days" not in result and "Last days" not in result


def test_tie_point(ref_client: TestClient) -> None:
    response = ref_client.post("/point", data={**REF_FORM, "lon": "-76.15", "lat": "-12.30"})
    assert "longitude -76.15, latitude -12.25" in response.text
    assert "5.560 km" in response.text


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"lon": "-60.0", "lat": "-12.0"}, "The point is outside the PISCOp grid"),
        ({"start_year": "2010", "end_year": "2000"}, "Start year must not be later than end year"),
        ({"start_year": "1975", "end_year": "1990"}, "Years must be between 1981 and 2025"),
        ({"lat": "twelve"}, "Latitude must be a number"),
    ],
)
def test_extraction_errors(ref_client: TestClient, fields: dict, message: str) -> None:
    response = ref_client.post("/point", data={**REF_FORM, **fields}, follow_redirects=False)
    assert response.status_code == 422
    assert 'role="alert"' in response.text
    assert message in response.text
    assert 'id="result"' not in response.text


def test_no_data_cell(ref_client: TestClient) -> None:
    response = ref_client.post("/point", data={**REF_FORM, "lon": "-76.35", "lat": "-12.45"})
    assert response.status_code == 200
    assert "No data available for this location" in response.text
    assert 'id="result"' not in response.text


def test_navigation_marks_point(ref_client: TestClient) -> None:
    html = ref_client.get("/point").text
    nav = html.split("<nav", 1)[1].split("</nav>", 1)[0]
    assert re.findall(r'href="([^"]+)"', nav) == ["/", "/point", "/dataset"]
    assert '<a href="/point" aria-current="page">' in nav


def test_no_scripts(ref_client: TestClient) -> None:
    for response in (ref_client.get("/point"), ref_client.post("/point", data=REF_FORM)):
        assert "<script" not in response.text.lower()
