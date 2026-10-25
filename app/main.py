"""FastAPI application factory and entry point (`uvicorn app.main:app`)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.repositories.pisco_repository import PiscoRepository
from app.routes import pages

STATIC_DIR = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application; the PISCOp files are opened once in the lifespan."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        repository = PiscoRepository.open(settings)
        app.state.repository = repository
        try:
            yield
        finally:
            repository.close()

    app = FastAPI(title="pisco-rain-extractor", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(pages.router)
    return app


app = create_app()
