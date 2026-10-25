"""FastAPI application factory and entry point (`uvicorn app.main:app`)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.repositories.pisco_repository import PiscoRepository
from app.routes import basin, pages, point
from app.services.basin_store import BasinStore

STATIC_DIR = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application; the PISCOp files are opened once in the lifespan.

    The basin result store is created there too and purged of expired results (ADR-0018).
    """
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        repository = PiscoRepository.open(settings)
        app.state.repository = repository
        store = BasinStore(settings.basin_store_dir, timedelta(hours=settings.basin_ttl_hours))
        store.purge_expired()
        app.state.basin_store = store
        try:
            yield
        finally:
            repository.close()

    app = FastAPI(title="pisco-rain-extractor", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(pages.router)
    app.include_router(point.router)
    app.include_router(basin.router)
    return app


app = create_app()
