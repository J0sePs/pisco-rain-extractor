"""Point extraction page: collects raw form values and renders the service result."""

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from app.routes.pages import RepositoryDep, templates
from app.services.point_service import (
    NoDataError,
    PointForm,
    PointInputError,
    convert_utm,
    extract_point,
    year_defaults,
)

router = APIRouter()

FormText = Annotated[str, Form()]


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
) -> HTMLResponse:
    """Convert UTM coordinates or extract the daily series, depending on `action`."""
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
        else:
            context["result"] = extract_point(repo, form)
    except PointInputError as exc:
        return _render(request, {**context, "error": str(exc)}, status_code=422)
    except NoDataError as exc:
        context["no_data"] = str(exc)
    return _render(request, context)
