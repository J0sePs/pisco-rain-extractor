import re
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from xarray.backends import netCDF4_

from tests.conftest import write_default_files

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
QUERY = "lon=-76.1390222&lat=-12.2935861&start_year=1981&end_year=1985"
OCEAN = "lon=-76.35&lat=-12.45&start_year=1981&end_year=1981"
CHART_KINDS = ("daily", "annual-totals", "annual-maxima", "climatology", "location")


@pytest.fixture
def ref_client(make_client: Callable[[Path], TestClient], reference_dir: Path) -> TestClient:
    return make_client(reference_dir)


@pytest.fixture
def five_years(ref_client: TestClient) -> str:
    response = ref_client.get(f"/point/result?{QUERY}")
    assert response.status_code == 200
    return response.text


@pytest.fixture
def precipitation_reads(monkeypatch: pytest.MonkeyPatch) -> list[tuple[int, ...]]:
    """Shapes of every precipitation read (fails, never skips, if the xarray hook changes)."""
    wrapper = netCDF4_.NetCDF4ArrayWrapper
    if not hasattr(wrapper, "_getitem"):
        pytest.fail("xarray internals changed; update the read spy")
    reads: list[tuple[int, ...]] = []
    original = wrapper._getitem

    def spy(self: netCDF4_.NetCDF4ArrayWrapper, key: object) -> np.ndarray:
        result = original(self, key)
        if self.variable_name == "precipitation":
            reads.append(np.shape(result))
        return result

    monkeypatch.setattr(wrapper, "_getitem", spy)
    return reads


def _section(html: str, tab: str) -> str:
    return html.split(f'id="{tab}"', 1)[1].split("</section>", 1)[0]


def _row(html: str, first_cell: str) -> list[str]:
    match = re.search(rf"<tr[^>]*><td>{first_cell}</td>(.*?)</tr>", html)
    assert match, f"row {first_cell} not found"
    return re.findall(r"<td>(.*?)</td>", match.group(1))


def _input_value(html: str, name: str) -> str:
    match = re.search(rf'<input name="{name}" value="([^"]*)"', html)
    assert match, f"input {name} not found"
    return match.group(1)


# --- result URL ---------------------------------------------------------------------------


def test_post_reads_no_precipitation(
    ref_client: TestClient, precipitation_reads: list[tuple[int, ...]]
) -> None:
    form = {"lon": "-76.1390222", "lat": "-12.2935861", "start_year": "1981", "end_year": "1985"}
    response = ref_client.post("/point", data=form, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"/point/result?{QUERY}"
    assert precipitation_reads == []


def test_result_reads_one_cell_once(
    ref_client: TestClient, precipitation_reads: list[tuple[int, ...]]
) -> None:
    assert ref_client.get(f"/point/result?{QUERY}").status_code == 200
    assert precipitation_reads == [(1826,)]


def test_tampered_query(ref_client: TestClient) -> None:
    response = ref_client.get("/point/result?lon=abc&lat=-12.29&start_year=1981&end_year=1985")
    assert response.status_code == 422
    assert "Longitude must be a number" in response.text
    assert _input_value(response.text, "lat") == "-12.29"


def test_missing_parameter(ref_client: TestClient) -> None:
    response = ref_client.get("/point/result?lon=-76.14&lat=-12.29&start_year=1981")
    assert response.status_code == 422
    assert "End year must be an integer" in response.text


def test_ocean_cell(ref_client: TestClient) -> None:
    response = ref_client.get(f"/point/result?{OCEAN}")
    assert response.status_code == 200
    assert "No data available for this location" in response.text
    assert 'class="tabs"' not in response.text
    assert "<td>1981-01-01</td>" not in response.text


def test_daily_file_missing(make_client: Callable, tmp_path: Path) -> None:
    client = make_client(write_default_files(tmp_path / "d", skip=("PISCOp_d.nc",)))
    response = client.get(f"/point/result?{QUERY}")
    assert response.status_code == 200
    assert "Daily data is not available" in response.text


# --- tabs and summary ---------------------------------------------------------------------


def test_tabs(five_years: str) -> None:
    for tab in ("summary", "daily", "annual", "climatology", "location"):
        assert f'<a href="#{tab}">' in five_years
        assert f'<section class="tab" id="{tab}">' in five_years


def test_no_scripts_or_external_resources(five_years: str) -> None:
    assert "<script" not in five_years.lower()
    for tag in re.findall(r"<(?:link|script|img)\b[^>]*>", five_years):
        assert not re.search(r'(?:href|src)="https?://', tag), tag


def test_summary_single_year(ref_client: TestClient) -> None:
    html = ref_client.get(f"/point/result?{QUERY.replace('end_year=1985', 'end_year=1981')}").text
    summary = _section(html, "summary")
    assert "1981-01-01 to 1981-12-31" in summary
    assert "<dd>365</dd>" in summary and "<dd>2</dd>" in summary
    assert "First days" not in html


def test_mean_annual(five_years: str) -> None:
    assert "1640.7 mm from 5 complete years" in _section(five_years, "summary")


def test_mean_annual_unavailable(make_client: Callable, tmp_path: Path) -> None:
    from tests.conftest import DAILY_STEPS, write_reference_dir

    # The file ends on 2025-06-30, so 2025 is the only (incomplete) requested year.
    client = make_client(write_reference_dir(tmp_path / "short", daily_steps=DAILY_STEPS - 184))
    html = client.get("/point/result?lon=-76.15&lat=-12.25&start_year=2025&end_year=2025").text
    assert "Not available (no complete year)" in html
    assert _row(_section(html, "annual"), "2025")[2:] == ["181", "Incomplete"]


# --- annual and climatology ---------------------------------------------------------------


def test_annual_table(five_years: str) -> None:
    annual = _section(five_years, "annual")
    assert _row(annual, "1981") == ["1629.0", "9.000", "363", "Complete"]
    assert _row(annual, "1984") == ["1648.5", "9.000", "366", "Complete"]
    assert "Incomplete" not in annual.split("<tbody>", 1)[1]


def test_climatology_table(five_years: str) -> None:
    assert _row(_section(five_years, "climatology"), "Jan") == ["137.7", "6.7", "5"]


# --- daily pages --------------------------------------------------------------------------


def test_last_page(ref_client: TestClient) -> None:
    daily = _section(ref_client.get(f"/point/result?{QUERY}&page=6").text, "daily")
    assert "Page 6 of 6" in daily
    assert re.findall(r"<tr><td>(\d{4}-\d\d-\d\d)</td>", daily) == ["1985-12-31"]
    assert f'href="/point/result?{QUERY.replace("&", "&amp;")}&amp;page=5#daily"' in daily
    assert 'rel="next"' not in daily


def test_second_page(ref_client: TestClient) -> None:
    daily = _section(ref_client.get(f"/point/result?{QUERY}&page=2").text, "daily")
    assert re.findall(r"<tr><td>(\d{4}-\d\d-\d\d)</td>", daily)[0] == "1982-01-01"


@pytest.mark.parametrize(("page", "shown"), [("99", 6), ("0", 1), ("abc", 1)])
def test_page_clamped(ref_client: TestClient, page: str, shown: int) -> None:
    response = ref_client.get(f"/point/result?{QUERY}&page={page}")
    assert response.status_code == 200
    assert f"Page {shown} of 6" in response.text


def test_missing_day_shown(five_years: str) -> None:
    assert "<td>1981-01-03</td><td>missing</td>" in _section(five_years, "daily")


# --- charts -------------------------------------------------------------------------------


def test_chart_images_in_tabs(five_years: str) -> None:
    for kind in CHART_KINDS:
        src = f'src="/point/chart/{kind}.png?{QUERY.replace("&", "&amp;")}"'
        assert re.search(
            rf'<img class="chart" {re.escape(src)} alt="[^"]+" loading="lazy">', five_years
        )


@pytest.mark.parametrize("kind", CHART_KINDS)
def test_chart_png(
    ref_client: TestClient, kind: str, precipitation_reads: list[tuple[int, ...]]
) -> None:
    response = ref_client.get(f"/point/chart/{kind}.png?{QUERY}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(PNG_SIGNATURE)
    assert precipitation_reads == [(1826,)]


def test_unknown_chart(ref_client: TestClient, precipitation_reads: list[tuple[int, ...]]) -> None:
    assert ref_client.get(f"/point/chart/pie.png?{QUERY}").status_code == 404
    assert precipitation_reads == []


def test_invalid_chart_query(ref_client: TestClient) -> None:
    response = ref_client.get(
        "/point/chart/daily.png?lon=abc&lat=-12.29&start_year=1981&end_year=1985"
    )
    assert response.status_code == 422
    assert response.text == "Longitude must be a number"


def test_chart_of_cell_without_data(ref_client: TestClient) -> None:
    assert ref_client.get(f"/point/chart/daily.png?{OCEAN}").status_code == 404
