"""Point pages: the request form, the tabbed result and its PNG charts (ADR-0013)."""

from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response

from app.routes.pages import RepositoryDep, templates
from app.services.analysis_service import analyze_point, daily_page
from app.services.chart_service import ChartKind, render_png
from app.services.point_service import (
    NoDataError,
    PointForm,
    PointInputError,
    convert_utm,
    extract_point,
    result_query,
    validate_point,
    year_defaults,
)

router = APIRouter()

FormText = Annotated[str, Form()]
QueryText = Annotated[str, Query()]


def _render(request: Request, context: dict, status_code: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "point.html", {"active": "point", **context}, status_code=status_code
    )


@router.get("/point", response_class=HTMLResponse)
def point_form(request: Request, repo: RepositoryDep) -> HTMLResponse:
    """Render the empty form with default years."""
    defaults = year_defaults(repo)
    if defaults is None:
        return _render(request, {"available": False})
    form = PointForm(start_year=str(defaults[0]), end_year=str(defaults[1]))
    return _render(request, {"available": True, "form": form})


@router.post("/point", response_class=HTMLResponse)
def point_submit(
    request: Request,
    repo: RepositoryDep,
    lon: FormText = "",
    lat: FormText = "",
    start_year: FormText = "",
    end_year: FormText = "",
    easting: FormText = "",
    northing: FormText = "",
    zone: FormText = "",
    hemisphere: FormText = "South",
    action: FormText = "extract",
) -> Response:
    """Convert UTM coordinates, or validate and redirect to the result URL (303)."""
    if year_defaults(repo) is None:
        return _render(request, {"available": False})
    form = PointForm(lon, lat, start_year, end_year, easting, northing, zone, hemisphere)
    context: dict = {"available": True, "form": form}
    try:
        if action == "convert":
            new_lon, new_lat = convert_utm(form)
            context["form"] = PointForm(
                f"{new_lon:.6f}",
                f"{new_lat:.6f}",
                start_year,
                end_year,
                easting,
                northing,
                zone,
                hemisphere,
            )
            return _render(request, context)
        validate_point(repo, form)
    except PointInputError as exc:
        return _render(request, {**context, "error": str(exc)}, status_code=422)
    return RedirectResponse(f"/point/result?{result_query(form)}", status_code=303)


@router.get("/point/result", response_class=HTMLResponse)
def point_result(
    request: Request,
    repo: RepositoryDep,
    lon: QueryText = "",
    lat: QueryText = "",
    start_year: QueryText = "",
    end_year: QueryText = "",
    page: QueryText = "1",
) -> HTMLResponse:
    """Render the tabbed analysis of the point described by the query string."""
    if year_defaults(repo) is None:
        return _render(request, {"available": False})
    form = PointForm(lon, lat, start_year, end_year)
    context: dict = {"available": True, "form": form}
    try:
        result = extract_point(repo, validate_point(repo, form))
    except PointInputError as exc:
        return _render(request, {**context, "error": str(exc)}, status_code=422)
    except NoDataError as exc:
        return _render(request, {**context, "no_data": str(exc)})
    return templates.TemplateResponse(
        request,
        "point_result.html",
        {
            "active": "point",
            "analysis": analyze_point(result),
            "daily": daily_page(result.series, page),
            "query": result_query(form),
        },
    )


@router.get("/point/chart/{kind}.png")
def point_chart(
    kind: str,
    repo: RepositoryDep,
    lon: QueryText = "",
    lat: QueryText = "",
    start_year: QueryText = "",
    end_year: QueryText = "",
) -> Response:
    """Render one chart of the point described by the query string as PNG."""
    try:
        chart = ChartKind(kind)
    except ValueError:
        raise HTTPException(status_code=404, detail="Unknown chart") from None
    if year_defaults(repo) is None:
        raise HTTPException(status_code=404, detail="Daily data is not available")
    try:
        result = extract_point(
            repo, validate_point(repo, PointForm(lon, lat, start_year, end_year))
        )
    except PointInputError as exc:
        return PlainTextResponse(str(exc), status_code=422)
    except NoDataError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return Response(render_png(chart, analyze_point(result)), media_type="image/png")
