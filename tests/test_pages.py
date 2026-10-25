import re
from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient

MISMATCH = "Period mismatch: daily file ends in 2025-12, monthly file ends in 2024-12"


def _section(html: str, kind: str) -> str:
    match = re.search(rf'<section[^>]*id="{kind}".*?</section>', html, re.S)
    assert match, f"section {kind} not found"
    return match.group(0)


def test_home_page(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    for text in ("pisco-rain-extractor", "PISCOp v3.0", "SENAMHI", 'href="/dataset"'):
        assert text in response.text


def test_home_page_without_data(make_client: Callable, tmp_path: Path) -> None:
    assert make_client(tmp_path).get("/").status_code == 200


def test_dataset_daily_details(client: TestClient) -> None:
    response = client.get("/dataset")
    assert response.status_code == 200
    daily = _section(response.text, "daily")
    for text in (
        "PISCOp_d.nc",
        "<code>precipitation</code> (mm)",
        "5 x 4",
        "1.55 to 1.95",
        "-81.35 to -81.05",
        "0.1°",
        "1981-01-01 to 2025-12-31",
    ):
        assert text in daily
    assert 'role="alert"' not in daily


def test_dataset_climatology_section(client: TestClient) -> None:
    clim = _section(client.get("/dataset").text, "climatology")
    assert "<code>PISCOp_clim2</code> (not provided)" in clim
    assert "5 x 5" in clim
    assert "months 1 to 12" in clim
    assert 'role="alert"' not in clim


def test_missing_daily_file_warning(make_client: Callable, make_data_dir: Callable) -> None:
    response = make_client(make_data_dir(skip=("PISCOp_d.nc",))).get("/dataset")
    assert response.status_code == 200
    daily = _section(response.text, "daily")
    assert 'role="alert"' in daily
    assert "PISCOp_d.nc is not available: file not found" in daily
    assert "data/README.md" in daily
    assert "months 1 to 12" in _section(response.text, "climatology")
    assert "1981-01-01 to 2025-12-01" in _section(response.text, "monthly")


def test_period_mismatch_warning(make_client: Callable, make_data_dir: Callable) -> None:
    response = make_client(make_data_dir(monthly_steps=528)).get("/dataset")
    assert response.status_code == 200
    for kind in ("daily", "monthly"):
        section = _section(response.text, kind)
        assert MISMATCH in section
        assert "5 x 4" in section  # details still shown


def test_navigation_marks_current_page(client: TestClient) -> None:
    html = client.get("/dataset").text
    assert re.search(r'<a href="/dataset" aria-current="page">', html)
    assert '<a href="/">' in html
    assert '<a href="/point">' in html
    assert "SENAMHI" in html.split("<footer", 1)[1]


def test_unknown_page_is_404(client: TestClient) -> None:
    assert client.get("/does-not-exist").status_code == 404


def test_stylesheet_served_locally(client: TestClient) -> None:
    html = client.get("/").text
    href = re.search(r'<link rel="stylesheet" href="([^"]+)"', html).group(1)
    assert "/static/" in href
    response = client.get(href)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")


def test_missing_static_file_is_404(client: TestClient) -> None:
    assert client.get("/static/missing.css").status_code == 404


def test_no_scripts_or_external_resources(client: TestClient) -> None:
    for path in ("/", "/dataset"):
        html = client.get(path).text
        assert "<script" not in html.lower()
        for tag in re.findall(r"<(?:link|script|img)\b[^>]*>", html, re.I):
            assert not re.search(r'(?:href|src)="https?://', tag), tag
