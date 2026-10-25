import ast
from pathlib import Path

from app.repositories.pisco_repository import (
    DatasetKind,
    DatasetMetadata,
    VariableInfo,
)
from app.services import dataset_service
from app.services.dataset_service import summarize

DAILY = DatasetMetadata(
    kind=DatasetKind.DAILY,
    filename="PISCOp_d.nc",
    available=True,
    variables=[VariableInfo("precipitation", "mm")],
    n_time=16436,
    n_lat=210,
    n_lon=174,
    lat_min=-18.95,
    lat_max=1.95,
    lon_min=-81.35,
    lon_max=-64.05,
    resolution_deg=0.1,
    time_start="1981-01-01",
    time_end="2025-12-31",
)


def test_daily_summary() -> None:
    summary = summarize(DAILY)
    assert summary.variables == [("precipitation", "mm")]
    assert summary.grid == "210 x 174"
    assert summary.lat_range == "-18.95 to 1.95"
    assert summary.lon_range == "-81.35 to -64.05"
    assert summary.resolution == "0.1°"
    assert summary.period == "1981-01-01 to 2025-12-31"
    assert summary.warnings == []


def test_climatology_summary() -> None:
    clim = DatasetMetadata(
        kind=DatasetKind.CLIMATOLOGY,
        filename="PISCOp_clim2.nc",
        available=True,
        variables=[VariableInfo("PISCOp_clim2", None)],
        n_time=12,
        n_lat=210,
        n_lon=180,
        lon_min=-81.95,
        lon_max=-64.05,
        time_start="1",
        time_end="12",
    )
    summary = summarize(clim)
    assert summary.period == "months 1 to 12"
    assert summary.variables == [("PISCOp_clim2", "not provided")]
    assert summary.grid == "210 x 180"  # differs from daily, no warning
    assert summary.warnings == []


def test_unavailable_file_warning() -> None:
    meta = DatasetMetadata(
        kind=DatasetKind.DAILY,
        filename="PISCOp_d.nc",
        available=False,
        reason="file not found: PISCOp_d.nc",
    )
    summary = summarize(meta)
    assert summary.warnings[0].startswith("PISCOp_d.nc is not available: file not found")
    assert summary.grid is None and summary.period is None


def test_period_mismatch_kept_on_available_file() -> None:
    warning = "Period mismatch: daily file ends in 2025-12, monthly file ends in 2024-12"
    meta = DatasetMetadata(**{**DAILY.__dict__, "warnings": [warning]})
    summary = summarize(meta)
    assert summary.available
    assert summary.warnings == [warning]
    assert summary.grid == "210 x 174"


def test_service_does_not_import_fastapi() -> None:
    tree = ast.parse(Path(dataset_service.__file__).read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert "fastapi" not in imported
    assert "starlette" not in imported
