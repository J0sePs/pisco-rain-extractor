"""HTML pages: home and dataset catalog (no business logic here)."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.repositories.pisco_repository import PiscoRepository
from app.services.dataset_service import list_dataset_summaries

templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")
router = APIRouter()


def get_repository(request: Request) -> PiscoRepository:
    """Return the repository opened at startup."""
    return request.app.state.repository


RepositoryDep = Annotated[PiscoRepository, Depends(get_repository)]


@router.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    """Render the home page."""
    return templates.TemplateResponse(request, "home.html", {"active": "home"})


@router.get("/dataset", response_class=HTMLResponse)
def dataset(request: Request, repo: RepositoryDep) -> HTMLResponse:
    """Render the catalog of the three PISCOp files."""
    context = {"active": "dataset", "summaries": list_dataset_summaries(repo)}
    return templates.TemplateResponse(request, "dataset.html", context)
