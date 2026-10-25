"""Basin pages: the upload form, the stored result, its PNG charts and file downloads.

Results live in the basin store under UUIDv4 ids (ADR-0018); ids are validated before the store
is touched. Exports follow ADR-0014 and ADR-0016.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.routes.pages import BasinStoreDep, RepositoryDep, templates
from app.services.analysis_service import BasinAnalysis, analyze_basin, daily_page
from app.services.basin_geometry import MAX_UPLOAD_BYTES, BasinInputError, parse_basin_file
from app.services.basin_service import FALLBACK_WARNING, NoBasinDataError, extract_basin
from app.services.basin_store import EXPIRED_MESSAGE, BasinStore, is_result_id
from app.services.chart_service import BASIN_CHARTS, ChartKind, render_png
from app.services.export_service import (
    BASIN_TABLES,
    CSV_MEDIA_TYPE,
    XLSX_MEDIA_TYPE,
    ExportTable,
    export_filename,
    table_frame,
    to_csv,
    to_xlsx,
)
from app.services.point_service import PointInputError, validate_years, year_defaults

router = APIRouter()

FormText = Annotated[str, Form()]
QueryText = Annotated[str, Query()]
UploadField = Annotated[UploadFile | None, File()]


def _render(request: Request, context: dict, status_code: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "basin.html",
        {"active": "basin", "retention_hours": _ttl_hours(request), **context},
        status_code=status_code,
    )


def _form_context(repo: RepositoryDep, **years: str) -> dict:
    defaults = year_defaults(repo)
    if defaults is None:
        return {"available": False}
    start = years.get("start_year", str(defaults[0]))
    end = years.get("end_year", str(defaults[1]))
    return {"available": True, "start_year": start, "end_year": end}


@router.get("/basin", response_class=HTMLResponse)
def basin_form(request: Request, repo: RepositoryDep) -> HTMLResponse:
    """Render the empty upload form with default years."""
    return _render(request, _form_context(repo))


@router.post("/basin", response_class=HTMLResponse)
def basin_submit(
    request: Request,
    repo: RepositoryDep,
    store: BasinStoreDep,
    basin_file: UploadField = None,
    start_year: FormText = "",
    end_year: FormText = "",
) -> Response:
    """Validate the upload, extract the basin once, store the result and redirect (303)."""
    context = _form_context(repo, start_year=start_year, end_year=end_year)
    if not context["available"]:
        return _render(request, context)
    try:
        start, end = validate_years(repo, start_year, end_year)
        filename = (basin_file.filename or "") if basin_file is not None else ""
        # Read at most one byte over the limit: enough to reject a larger file.
        content = basin_file.file.read(MAX_UPLOAD_BYTES + 1) if basin_file and filename else b""
        basin = parse_basin_file(filename, content)
        result = extract_basin(repo, basin, start, end)
    except (PointInputError, BasinInputError) as exc:
        return _render(request, {**context, "error": str(exc)}, status_code=422)
    except NoBasinDataError as exc:
        return _render(request, {**context, "no_data": str(exc)})
    return RedirectResponse(f"/basin/result/{store.save(result)}", status_code=303)


@router.get("/basin/result/{result_id}", response_class=HTMLResponse)
def basin_result(
    request: Request,
    repo: RepositoryDep,
    store: BasinStoreDep,
    result_id: str,
    page: QueryText = "1",
) -> HTMLResponse:
    """Render the tabbed analysis of a stored basin result."""
    analysis = _load(store, result_id)
    if analysis is None:
        context = {**_form_context(repo), "expired": True}  # EXPIRED_MESSAGE, with a link
        return _render(request, context, status_code=404)
    return templates.TemplateResponse(
        request,
        "basin_result.html",
        {
            "active": "basin",
            "analysis": analysis,
            "daily": daily_page(analysis.result.series, page),
            "base": f"/basin/result/{result_id}",
            "fallback_warning": FALLBACK_WARNING,
            "retention_hours": _ttl_hours(request),
        },
    )


@router.get("/basin/result/{result_id}/chart/{kind}.png")
def basin_chart(result_id: str, kind: str, store: BasinStoreDep) -> Response:
    """Render one chart of a stored basin result as PNG."""
    chart = _choice(ChartKind, kind, BASIN_CHARTS, result_id)
    return Response(render_png(chart, _require(store, result_id)), media_type="image/png")


@router.get("/basin/result/{result_id}/export/{table}.csv")
def basin_export_csv(result_id: str, table: str, store: BasinStoreDep) -> Response:
    """Download one table of a stored basin result as CSV (ADR-0014)."""
    export = _choice(ExportTable, table, BASIN_TABLES, result_id)
    analysis = _require(store, result_id)
    return _attachment(
        to_csv(table_frame(export, analysis)),
        CSV_MEDIA_TYPE,
        export_filename(analysis.result, export),
    )


@router.get("/basin/result/{result_id}/export.xlsx")
def basin_export_xlsx(result_id: str, store: BasinStoreDep) -> Response:
    """Download every table of a stored basin result as one workbook."""
    if not is_result_id(result_id):
        raise HTTPException(status_code=404, detail=EXPIRED_MESSAGE)
    analysis = _require(store, result_id)
    return _attachment(
        to_xlsx(analysis, datetime.now(UTC)),
        XLSX_MEDIA_TYPE,
        export_filename(analysis.result, None),
    )


def _load(store: BasinStore, result_id: str) -> BasinAnalysis | None:
    """Analysis of a stored result; an invalid id never reaches the store."""
    if not is_result_id(result_id):
        return None
    result = store.load(result_id)
    return None if result is None else analyze_basin(result)


def _require(store: BasinStore, result_id: str) -> BasinAnalysis:
    analysis = _load(store, result_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail=EXPIRED_MESSAGE)
    return analysis


def _choice[T](kind: type[T], value: str, allowed: tuple[T, ...], result_id: str) -> T:
    """Validate the id, then the chart or table name, before the store is read."""
    if not is_result_id(result_id):
        raise HTTPException(status_code=404, detail=EXPIRED_MESSAGE)
    try:
        choice = kind(value)  # type: ignore[call-arg]
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found") from None
    if choice not in allowed:
        raise HTTPException(status_code=404, detail="Not found")
    return choice


def _ttl_hours(request: Request) -> int:
    store: BasinStore = request.app.state.basin_store
    return round(store.ttl_hours)


def _attachment(content: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
