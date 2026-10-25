"""Charts of a point or basin analysis rendered as PNG with matplotlib (design D7).

Only the object-oriented API is used (`Figure` + the Agg canvas through `savefig`); `pyplot` is
never imported, so there is no global figure registry and no GUI backend. A module-level lock
serializes rendering because matplotlib does not guarantee thread safety.
"""

import math
import threading
from enum import StrEnum
from io import BytesIO

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Polygon as PolygonPatch
from matplotlib.patches import Rectangle
from shapely.geometry.base import BaseGeometry

from app.services.analysis_service import Analysis, BasinAnalysis, PointAnalysis

# Reference palette of the dataviz skill (light surface); blue/orange validated as a pair.
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e6e5e0"
SERIES_1 = "#2a78d6"  # blue: the data
SERIES_1_LIGHT = "#b7d3f6"  # blue step 150: incomplete years (plus hatch texture)
SERIES_2 = "#eb6834"  # orange: the requested point

MONTH_LABELS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

_LOCK = threading.Lock()


class ChartKind(StrEnum):
    """The charts of the result page, by URL name."""

    DAILY = "daily"
    ANNUAL_TOTALS = "annual-totals"
    ANNUAL_MAXIMA = "annual-maxima"
    CLIMATOLOGY = "climatology"
    LOCATION = "location"
    CELLS = "cells"


SERIES_CHARTS = (
    ChartKind.DAILY,
    ChartKind.ANNUAL_TOTALS,
    ChartKind.ANNUAL_MAXIMA,
    ChartKind.CLIMATOLOGY,
)
POINT_CHARTS = (*SERIES_CHARTS, ChartKind.LOCATION)
BASIN_CHARTS = (*SERIES_CHARTS, ChartKind.CELLS)


def build_figure(kind: ChartKind, analysis: Analysis) -> Figure:
    """Build the figure of one chart kind (not rendered).

    `location` needs a point analysis and `cells` a basin analysis.
    """
    allowed = POINT_CHARTS if isinstance(analysis, PointAnalysis) else BASIN_CHARTS
    if kind not in allowed:
        raise ValueError(f"chart {kind} is not available for this result")
    fig = Figure(figsize=(8, 3.5), dpi=100, facecolor=SURFACE, layout="constrained")
    ax = fig.add_subplot()
    _style(ax)
    if kind is ChartKind.DAILY:
        _daily(ax, analysis)
    elif kind is ChartKind.ANNUAL_TOTALS:
        _annual(ax, analysis, "total_mm", "Annual total", "Annual total (mm)")
    elif kind is ChartKind.ANNUAL_MAXIMA:
        _annual(ax, analysis, "max_24h_mm", "Annual maximum 24 h rainfall", "Max 24 h (mm)")
    elif kind is ChartKind.CLIMATOLOGY:
        _climatology(ax, analysis)
    elif kind is ChartKind.LOCATION:
        assert isinstance(analysis, PointAnalysis)
        fig.set_size_inches(5, 5)
        _location(ax, analysis)
    else:
        assert isinstance(analysis, BasinAnalysis)
        fig.set_size_inches(7, 5)
        _cells(ax, analysis)
    return fig


def render_png(kind: ChartKind, analysis: Analysis) -> bytes:
    """Render one chart as PNG bytes."""
    with _LOCK:
        fig = build_figure(kind, analysis)
        buffer = BytesIO()
        fig.savefig(buffer, format="png", facecolor=SURFACE)
    return buffer.getvalue()


def _style(ax: Axes) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)


def _title(ax: Axes, text: str) -> None:
    ax.set_title(text, loc="left", color=TEXT_PRIMARY, fontsize=11)


def _ylabel(ax: Axes, text: str) -> None:
    ax.set_ylabel(text, color=TEXT_SECONDARY, fontsize=9)


def _daily(ax: Axes, analysis: Analysis) -> None:
    series = analysis.result.series
    ax.plot(series.index.to_numpy(), series.to_numpy(), color=SERIES_1, linewidth=0.8)
    _title(ax, "Daily precipitation")
    _ylabel(ax, "Precipitation (mm)")
    ax.set_ylim(bottom=0)


def _annual(ax: Axes, analysis: Analysis, field: str, title: str, ylabel: str) -> None:
    for complete, color, hatch, label in (
        (True, SERIES_1, None, "Complete year"),
        (False, SERIES_1_LIGHT, "//", "Incomplete year"),
    ):
        stats = [
            s for s in analysis.annual if s.complete is complete and getattr(s, field) is not None
        ]
        if stats:
            ax.bar(
                [s.year for s in stats],
                [getattr(s, field) for s in stats],
                width=0.6,
                color=color,
                hatch=hatch,
                edgecolor=SURFACE if hatch is None else SERIES_1,
                linewidth=0,
                label=label,
            )
    years = [s.year for s in analysis.annual]
    ax.set_xlim(min(years) - 0.7, max(years) + 0.7)
    ax.xaxis.get_major_locator().set_params(integer=True)
    _title(ax, title)
    _ylabel(ax, ylabel)
    ax.legend(
        frameon=False,
        fontsize=9,
        labelcolor=TEXT_SECONDARY,
        loc="lower right",
        bbox_to_anchor=(1, 1),
        ncols=2,
        borderaxespad=0,
    )


def _climatology(ax: Axes, analysis: Analysis) -> None:
    months = [m for m in analysis.climatology if m.mean_mm is not None]
    ax.bar(
        [m.month for m in months],
        [m.mean_mm for m in months],
        yerr=[np.nan if m.std_mm is None else m.std_mm for m in months],
        width=0.6,
        color=SERIES_1,
        error_kw={"ecolor": TEXT_SECONDARY, "elinewidth": 1, "capsize": 3},
    )
    ax.set_xticks(range(1, 13), MONTH_LABELS)
    ax.set_xlim(0.3, 12.7)
    _title(ax, "Monthly climatology (mean ± standard deviation)")
    _ylabel(ax, "Monthly total (mm)")


def _location(ax: Axes, analysis: PointAnalysis) -> None:
    result = analysis.result
    half = result.resolution_deg / 2
    cell = result.cell
    ax.grid(axis="both", color=GRID, linewidth=1)
    ax.add_patch(
        Rectangle(
            (cell.lon - half, cell.lat - half),
            result.resolution_deg,
            result.resolution_deg,
            fill=False,
            edgecolor=TEXT_SECONDARY,
            linewidth=1.5,
            label="Cell edges",
        )
    )
    ax.plot(cell.lon, cell.lat, "s", color=SERIES_1, markersize=9, label="Cell center")
    ax.plot(result.lon, result.lat, "o", color=SERIES_2, markersize=9, label="Requested point")
    span = max(result.resolution_deg, abs(result.lon - cell.lon), abs(result.lat - cell.lat))
    ax.set_xlim(cell.lon - span * 1.2, cell.lon + span * 1.2)
    ax.set_ylim(cell.lat - span * 1.2, cell.lat + span * 1.2)
    ax.set_aspect(1 / math.cos(math.radians(cell.lat)))
    ax.set_xlabel("Longitude (°)", color=TEXT_SECONDARY, fontsize=9)
    _ylabel(ax, "Latitude (°)")
    _title(ax, f"Requested point and selected cell ({result.distance_km:.3f} km)")
    ax.legend(frameon=False, fontsize=9, labelcolor=TEXT_SECONDARY, loc="upper left")


def _rings(geometry: BaseGeometry) -> list[np.ndarray]:
    polygons = getattr(geometry, "geoms", [geometry])
    return [
        np.asarray(ring.coords)
        for polygon in polygons
        for ring in (polygon.exterior, *polygon.interiors)
    ]


def _cells(ax: Axes, analysis: BasinAnalysis) -> None:
    result = analysis.result
    half = result.resolution_deg / 2
    ax.grid(axis="both", color=GRID, linewidth=1)
    for k, ring in enumerate(_rings(result.basin.geometry)):
        ax.add_patch(
            PolygonPatch(
                ring,
                closed=True,
                fill=False,
                edgecolor=TEXT_PRIMARY,
                linewidth=1.2,
                gid="outline",
                label="Basin outline" if k == 0 else None,
            )
        )
    for cell in result.cells:
        ax.add_patch(
            Rectangle(
                (cell.lon - half, cell.lat - half),
                result.resolution_deg,
                result.resolution_deg,
                fill=False,
                edgecolor=TEXT_SECONDARY,
                linewidth=0.6,
            )
        )
    used = [c for c in result.cells if c.used]
    excluded = [c for c in result.cells if not c.used]
    ax.plot(
        [c.lon for c in used],
        [c.lat for c in used],
        "s",
        color=SERIES_1,
        markersize=6,
        label="Used cell",
    )
    if excluded:
        ax.plot(
            [c.lon for c in excluded],
            [c.lat for c in excluded],
            "s",
            markerfacecolor="none",
            markeredgecolor=TEXT_SECONDARY,
            markersize=6,
            label="Excluded cell (no data)",
        )
    west, south, east, north = result.basin.geometry.bounds
    west = min(west, *(c.lon - half for c in result.cells))
    east = max(east, *(c.lon + half for c in result.cells))
    south = min(south, *(c.lat - half for c in result.cells))
    north = max(north, *(c.lat + half for c in result.cells))
    pad = max(east - west, north - south) * 0.05
    ax.set_xlim(west - pad, east + pad)
    ax.set_ylim(south - pad, north + pad)
    ax.set_aspect(1 / math.cos(math.radians((south + north) / 2)))
    ax.set_xlabel("Longitude (°)", color=TEXT_SECONDARY, fontsize=9)
    _ylabel(ax, "Latitude (°)")
    _title(
        ax,
        f"Basin and selected cells ({result.cells_used} used, {result.cells_excluded} excluded)",
    )
    ax.legend(
        frameon=False,
        fontsize=9,
        labelcolor=TEXT_SECONDARY,
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
        borderaxespad=0,
    )
