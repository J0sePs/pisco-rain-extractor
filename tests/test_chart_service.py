import ast
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from matplotlib.container import ErrorbarContainer
from matplotlib.patches import Rectangle

from app.repositories.pisco_repository import CellRef
from app.services import chart_service
from app.services.analysis_service import PointAnalysis, analyze_point
from app.services.chart_service import ChartKind, build_figure, render_png
from app.services.point_service import PointResult

ROOT = Path(__file__).resolve().parent.parent
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _analysis(series: pd.Series, start_year: int, end_year: int) -> PointAnalysis:
    result = PointResult(
        lon=-76.1390222,
        lat=-12.2935861,
        cell=CellRef(lat_index=2, lon_index=2, lon=-76.15, lat=-12.25),
        distance_km=4.991,
        resolution_deg=0.1,
        start_year=start_year,
        end_year=end_year,
        period_start=series.index[0].date(),
        period_end=series.index[-1].date(),
        total_days=len(series),
        missing_days=int(series.isna().sum()),
        series=series,
    )
    return analyze_point(result)


def _series(start_year: int, end_year: int) -> pd.Series:
    days = pd.date_range(f"{start_year}-01-01", f"{end_year}-12-31", freq="D", name="date")
    return pd.Series((np.arange(len(days)) % 7) * 1.5, index=days, dtype=float)


def _missing(series: pd.Series, start: str, end: str) -> pd.Series:
    copy = series.copy()
    copy[pd.Timestamp(start) : pd.Timestamp(end)] = np.nan
    return copy


@pytest.fixture
def three_years_one_incomplete() -> PointAnalysis:
    return _analysis(_missing(_series(1981, 1983), "1982-03-01", "1982-04-30"), 1981, 1983)


def _legend_texts(kind: ChartKind, analysis: PointAnalysis) -> list[str]:
    legend = build_figure(kind, analysis).axes[0].get_legend()
    return [text.get_text() for text in legend.get_texts()]


@pytest.mark.parametrize("kind", [ChartKind.ANNUAL_TOTALS, ChartKind.ANNUAL_MAXIMA])
def test_annual_chart_flags_incomplete_year(
    kind: ChartKind, three_years_one_incomplete: PointAnalysis
) -> None:
    ax = build_figure(kind, three_years_one_incomplete).axes[0]
    assert len(ax.patches) == 3
    assert _legend_texts(kind, three_years_one_incomplete) == ["Complete year", "Incomplete year"]


def test_annual_chart_all_complete() -> None:
    texts = _legend_texts(ChartKind.ANNUAL_TOTALS, _analysis(_series(1981, 1983), 1981, 1983))
    assert texts == ["Complete year"]


def test_climatology_has_error_bars() -> None:
    ax = build_figure(ChartKind.CLIMATOLOGY, _analysis(_series(1981, 1985), 1981, 1985)).axes[0]
    assert len(ax.patches) == 12
    assert any(isinstance(c, ErrorbarContainer) for c in ax.containers)
    assert [t.get_text() for t in ax.get_xticklabels()][:2] == ["Jan", "Feb"]


def test_climatology_without_february() -> None:
    series = _series(1981, 1982)
    series = _missing(_missing(series, "1981-02-01", "1981-02-02"), "1982-02-01", "1982-02-02")
    ax = build_figure(ChartKind.CLIMATOLOGY, _analysis(series, 1981, 1982)).axes[0]
    assert len(ax.patches) == 11


def test_location_chart() -> None:
    ax = build_figure(ChartKind.LOCATION, _analysis(_series(1981, 1981), 1981, 1981)).axes[0]
    [cell] = [p for p in ax.patches if isinstance(p, Rectangle)]
    assert cell.get_xy() == pytest.approx((-76.2, -12.3))
    assert (cell.get_width(), cell.get_height()) == pytest.approx((0.1, 0.1))
    assert ax.get_xlabel() == "Longitude (°)"
    assert ax.get_ylabel() == "Latitude (°)"
    points = {line.get_label(): (line.get_xdata()[0], line.get_ydata()[0]) for line in ax.lines}
    assert points["Cell center"] == pytest.approx((-76.15, -12.25))
    assert points["Requested point"] == pytest.approx((-76.1390222, -12.2935861))


def test_daily_chart_has_one_line() -> None:
    ax = build_figure(ChartKind.DAILY, _analysis(_series(1981, 1981), 1981, 1981)).axes[0]
    assert len(ax.lines) == 1
    assert len(ax.lines[0].get_xdata()) == 365


@pytest.mark.parametrize("kind", list(ChartKind))
def test_render_png(kind: ChartKind) -> None:
    assert render_png(kind, _analysis(_series(1981, 1982), 1981, 1982)).startswith(PNG_SIGNATURE)


def test_rendering_never_imports_pyplot() -> None:
    code = (
        "import sys\n"
        "from tests.test_chart_service import _analysis, _series\n"
        "from app.services.chart_service import ChartKind, render_png\n"
        "for kind in ChartKind:\n"
        "    render_png(kind, _analysis(_series(1981, 1981), 1981, 1981))\n"
        "assert 'matplotlib.pyplot' not in sys.modules, 'pyplot was imported'\n"
    )
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True)


def test_module_imports_neither_fastapi_nor_pyplot() -> None:
    tree = ast.parse(Path(chart_service.__file__).read_text(encoding="utf-8"))
    modules = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not {m.split(".")[0] for m in modules} & {"fastapi", "starlette", "xarray"}
    assert "matplotlib.pyplot" not in modules
