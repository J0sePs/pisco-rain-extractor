import io
from collections.abc import Callable, Mapping
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from xarray.backends import netCDF4_

from tests.conftest import write_default_files

QUERY = "lon=-76.1390222&lat=-12.2935861&start_year=1981&end_year=1985"
OCEAN = "lon=-76.35&lat=-12.45&start_year=1981&end_year=1981"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
FORMAT_NOTE = (
    "CSV files are for R and Python. To open the data in Excel, use the .xlsx workbook: with "
    "Spanish regional settings, Excel does not split the columns of a comma-separated file."
)


@pytest.fixture
def ref_client(make_client: Callable[[Path], TestClient], reference_dir: Path) -> TestClient:
    return make_client(reference_dir)


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


def _attachment_name(headers: Mapping[str, str]) -> str:
    disposition = headers["content-disposition"]
    prefix = 'attachment; filename="'
    assert disposition.startswith(prefix) and disposition.endswith('"'), disposition
    return disposition[len(prefix) : -1]


# --- links on the result page ---------------------------------------------------------------


def test_result_page_links(ref_client: TestClient) -> None:
    html = ref_client.get(f"/point/result?{QUERY}&page=2").text
    for path in (
        "/point/export/daily.csv",
        "/point/export/annual.csv",
        "/point/export/climatology.csv",
        "/point/export.xlsx",
    ):
        assert f'href="{path}?{QUERY.replace("&", "&amp;")}" download' in html
    assert "page=2" not in html.split('class="downloads"', 1)[1].split("</nav>", 1)[0]
    assert FORMAT_NOTE in html


def test_no_links_without_result(ref_client: TestClient) -> None:
    html = ref_client.get(f"/point/result?{OCEAN}").text
    assert "No data available for this location" in html
    assert "/point/export" not in html
    assert "CSV files are for R and Python" not in html


# --- downloads ------------------------------------------------------------------------------


def test_daily_csv(ref_client: TestClient) -> None:
    response = ref_client.get(f"/point/export/daily.csv?{QUERY}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert _attachment_name(response.headers) == "pisco_-12.25_-76.15_1981-1985_daily.csv"
    daily = pd.read_csv(io.BytesIO(response.content))
    assert list(daily.columns) == ["date", "precipitation_mm"]
    assert len(daily) == 1826
    assert daily["date"].str.match(r"^\d{4}-\d{2}-\d{2}$").all()
    assert daily["precipitation_mm"].dtype == np.float64
    assert daily.loc[1, "precipitation_mm"] == 1.5
    assert np.isnan(daily.loc[2, "precipitation_mm"])  # 1981-01-03
    assert daily.iloc[-1].tolist() == ["1985-12-31", 7.5]


def test_annual_csv(ref_client: TestClient) -> None:
    response = ref_client.get(f"/point/export/annual.csv?{QUERY}")
    annual = pd.read_csv(io.BytesIO(response.content))
    assert list(annual.columns) == ["year", "total_mm", "max_24h_mm", "valid_days", "complete"]
    assert annual.iloc[0].tolist() == [1981, 1629.0, 9.0, 363, True]
    assert annual["complete"].dtype == bool
    assert "1984,1648.5,9.0,366,TRUE" in response.text


def test_climatology_csv(ref_client: TestClient) -> None:
    response = ref_client.get(f"/point/export/climatology.csv?{QUERY}")
    climate = pd.read_csv(io.BytesIO(response.content))
    assert list(climate.columns) == ["month", "mean_mm", "sd_mm", "n_years"]
    assert climate["month"].tolist() == list(range(1, 13))
    assert climate.iloc[0].tolist() == [1, 137.7, 6.6577, 5]


def test_same_cell_same_name(ref_client: TestClient) -> None:
    query = "lon=-76.16&lat=-12.26&start_year=1981&end_year=1985"
    response = ref_client.get(f"/point/export/annual.csv?{query}")
    assert _attachment_name(response.headers) == "pisco_-12.25_-76.15_1981-1985_annual.csv"


def test_workbook(ref_client: TestClient, precipitation_reads: list[tuple[int, ...]]) -> None:
    response = ref_client.get(f"/point/export.xlsx?{QUERY}")
    assert response.status_code == 200
    assert response.headers["content-type"] == XLSX_MEDIA_TYPE
    assert _attachment_name(response.headers) == "pisco_-12.25_-76.15_1981-1985.xlsx"
    sheets = pd.read_excel(io.BytesIO(response.content), sheet_name=None)
    assert list(sheets) == ["daily", "annual", "climatology", "metadata"]
    assert len(sheets["daily"]) == 1826
    assert precipitation_reads == [(1826,)]


# --- validation -----------------------------------------------------------------------------


def test_invalid_period(ref_client: TestClient) -> None:
    query = "lon=-76.15&lat=-12.25&start_year=1985&end_year=1981"
    response = ref_client.get(f"/point/export/annual.csv?{query}")
    assert response.status_code == 422
    assert response.text == "Start year must not be later than end year"


def test_non_numeric_coordinate(ref_client: TestClient) -> None:
    query = "lon=abc&lat=-12.25&start_year=1981&end_year=1981"
    response = ref_client.get(f"/point/export.xlsx?{query}")
    assert response.status_code == 422
    assert response.text == "Longitude must be a number"


def test_unknown_table(ref_client: TestClient, precipitation_reads: list[tuple[int, ...]]) -> None:
    assert ref_client.get(f"/point/export/monthly.csv?{QUERY}").status_code == 404
    assert precipitation_reads == []


@pytest.mark.parametrize("path", ["/point/export/daily.csv", "/point/export.xlsx"])
def test_cell_without_data(ref_client: TestClient, path: str) -> None:
    assert ref_client.get(f"{path}?{OCEAN}").status_code == 404


def test_daily_file_missing(make_client: Callable, tmp_path: Path) -> None:
    client = make_client(write_default_files(tmp_path / "d", skip=("PISCOp_d.nc",)))
    assert client.get(f"/point/export/daily.csv?{QUERY}").status_code == 404
    assert client.get(f"/point/export.xlsx?{QUERY}").status_code == 404
