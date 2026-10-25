"""Exports of a point or basin analysis: CSV tables for R and Python and one XLSX workbook.

The format follows ADR-0014; basin tables and file names follow ADR-0016.

Each table is built once as a DataFrame and only serialized by the CSV and XLSX writers, so both
formats share columns and rounding. No FastAPI and no NetCDF access.
"""

import io
from collections.abc import Iterable
from datetime import datetime
from enum import StrEnum

import pandas as pd

from app.services.analysis_service import (
    COMPLETENESS_PERCENT,
    Analysis,
    BasinAnalysis,
)
from app.services.basin_service import BasinResult
from app.services.point_service import PointResult

DECIMALS = 4
CSV_MEDIA_TYPE = "text/csv; charset=utf-8"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

SOURCE = "SENAMHI PISCOp v3.0 daily precipitation (PISCOp_d.nc), 0.1° grid"
ATTRIBUTION = (
    "Servicio Nacional de Meteorología e Hidrología del Perú (SENAMHI). Data extracted with "
    "pisco-rain-extractor; cite SENAMHI PISCOp v3.0 when using these values."
)
COMPLETENESS_RULE = (
    f"A year or month is complete with at least {COMPLETENESS_PERCENT}% valid days (ADR-0012); "
    "only complete years enter the mean annual rainfall and only complete months the "
    "climatology."
)
CELL_SELECTION = "cell centers inside the basin (boundary included)"
FALLBACK_SELECTION = "nearest cell to the basin centroid (no cell center inside)"
AREAL_MEAN = (
    "arithmetic mean of the selected cells with a valid value each day; cells without data in "
    "the period are excluded (ADR-0016)"
)


class ExportTable(StrEnum):
    """Tables that can be exported."""

    DAILY = "daily"
    ANNUAL = "annual"
    CLIMATOLOGY = "climatology"
    CELLS = "cells"


POINT_TABLES = (ExportTable.DAILY, ExportTable.ANNUAL, ExportTable.CLIMATOLOGY)
BASIN_TABLES = (*POINT_TABLES, ExportTable.CELLS)

COLUMNS: dict[ExportTable, list[str]] = {
    ExportTable.DAILY: ["date", "precipitation_mm"],
    ExportTable.ANNUAL: ["year", "total_mm", "max_24h_mm", "valid_days", "complete"],
    ExportTable.CLIMATOLOGY: ["month", "mean_mm", "sd_mm", "n_years"],
    ExportTable.CELLS: ["cell_lon", "cell_lat", "used", "valid_days"],
}


def tables_for(analysis: Analysis) -> tuple[ExportTable, ...]:
    """The tables a result can export: basins add `cells`."""
    return BASIN_TABLES if isinstance(analysis, BasinAnalysis) else POINT_TABLES


def table_frame(table: ExportTable, analysis: Analysis) -> pd.DataFrame:
    """One export table: exact columns, missing values as NaN, floats rounded to 4 decimals."""
    if table not in tables_for(analysis):
        raise ValueError(f"table {table} is not available for this result")
    if table is ExportTable.DAILY:
        series = analysis.result.series
        data = {"date": series.index.date, "precipitation_mm": series.to_numpy(dtype=float)}
    elif table is ExportTable.ANNUAL:
        data = {
            "year": [s.year for s in analysis.annual],
            "total_mm": _floats(s.total_mm for s in analysis.annual),
            "max_24h_mm": _floats(s.max_24h_mm for s in analysis.annual),
            "valid_days": [s.valid_days for s in analysis.annual],
            "complete": [s.complete for s in analysis.annual],
        }
    elif table is ExportTable.CELLS:
        assert isinstance(analysis, BasinAnalysis)
        cells = analysis.result.cells
        data = {
            "cell_lon": [c.lon for c in cells],
            "cell_lat": [c.lat for c in cells],
            "used": [c.used for c in cells],
            "valid_days": [c.valid_days for c in cells],
        }
    else:
        data = {
            "month": [m.month for m in analysis.climatology],
            "mean_mm": _floats(m.mean_mm for m in analysis.climatology),
            "sd_mm": _floats(m.std_mm for m in analysis.climatology),
            "n_years": [m.years for m in analysis.climatology],
        }
    frame = pd.DataFrame(data, columns=COLUMNS[table])
    floats = frame.select_dtypes("float").columns
    frame[floats] = frame[floats].round(DECIMALS)
    return frame


def to_csv(frame: pd.DataFrame) -> bytes:
    """UTF-8 CSV without BOM: `,` separator, `\\n` endings, empty missing values, TRUE/FALSE."""
    out = frame.copy()
    for column in out.select_dtypes("bool").columns:
        out[column] = out[column].map({True: "TRUE", False: "FALSE"})
    buffer = io.StringIO()
    out.to_csv(buffer, index=False, lineterminator="\n", na_rep="")
    return buffer.getvalue().encode("utf-8")


def metadata_rows(
    analysis: Analysis, generated_at: datetime
) -> list[tuple[str, str | float | int]]:
    """`(field, value)` rows of the workbook's metadata sheet; `generated_at` must be UTC."""
    if isinstance(analysis, BasinAnalysis):
        return _basin_metadata_rows(analysis.result, generated_at)
    result = analysis.result
    return [
        ("source", SOURCE),
        ("attribution", ATTRIBUTION),
        ("requested_lon", result.lon),
        ("requested_lat", result.lat),
        ("cell_lon", result.cell.lon),
        ("cell_lat", result.cell.lat),
        ("distance_km", result.distance_km),
        ("start_year", result.start_year),
        ("end_year", result.end_year),
        ("period_start", result.period_start.isoformat()),
        ("period_end", result.period_end.isoformat()),
        ("completeness_rule", COMPLETENESS_RULE),
        ("generated_at_utc", generated_at.strftime("%Y-%m-%dT%H:%M:%SZ")),
    ]


def to_xlsx(analysis: Analysis, generated_at: datetime) -> bytes:
    """Workbook with one sheet per table of the result (daily, annual, climatology[, cells])
    followed by metadata."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl", date_format="YYYY-MM-DD") as writer:
        for table in tables_for(analysis):
            table_frame(table, analysis).to_excel(writer, sheet_name=table.value, index=False)
        metadata = pd.DataFrame(metadata_rows(analysis, generated_at), columns=["field", "value"])
        metadata.to_excel(writer, sheet_name="metadata", index=False)
    return buffer.getvalue()


def export_filename(result: PointResult | BasinResult, table: ExportTable | None) -> str:
    """`pisco_<lat>_<lon>_<start>-<end>_<table>.csv`, or `.xlsx` without table for the workbook.

    Points use the selected cell center (4 decimals); basins use `pisco_basin_` and the
    centroid rounded to 3 decimals (ADR-0016).
    """
    if isinstance(result, BasinResult):
        place = f"basin_{_coordinate(result.centroid_lat, 3)}_{_coordinate(result.centroid_lon, 3)}"
    else:
        place = f"{_coordinate(result.cell.lat)}_{_coordinate(result.cell.lon)}"
    stem = f"pisco_{place}_{result.start_year}-{result.end_year}"
    return f"{stem}.xlsx" if table is None else f"{stem}_{table.value}.csv"


def _floats(values: Iterable[float | None]) -> pd.Series:
    return pd.Series(list(values), dtype=float)  # None → NaN


def _basin_metadata_rows(
    result: BasinResult, generated_at: datetime
) -> list[tuple[str, str | float | int]]:
    return [
        ("source", SOURCE),
        ("attribution", ATTRIBUTION),
        ("basin_file", result.basin.filename),
        ("features", result.basin.features),
        ("basin_area_km2", result.area_km2),
        ("centroid_lon", round(result.centroid_lon, 6)),
        ("centroid_lat", round(result.centroid_lat, 6)),
        ("cells_used", result.cells_used),
        ("cells_excluded", result.cells_excluded),
        ("cell_selection", FALLBACK_SELECTION if result.fallback else CELL_SELECTION),
        ("areal_mean", AREAL_MEAN),
        ("start_year", result.start_year),
        ("end_year", result.end_year),
        ("period_start", result.period_start.isoformat()),
        ("period_end", result.period_end.isoformat()),
        ("completeness_rule", COMPLETENESS_RULE),
        ("generated_at_utc", generated_at.strftime("%Y-%m-%dT%H:%M:%SZ")),
    ]


def _coordinate(value: float, decimals: int = 4) -> str:
    return f"{value:.{decimals}f}".rstrip("0").rstrip(".")
