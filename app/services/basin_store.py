"""Server-side store of basin results under random UUIDv4 ids with expiry (ADR-0018).

Each result is one JSON file `<id>.json` in the store directory (gitignored). Ids are validated
before any path is built, so invalid input never reaches the file system. The uploaded file is
never stored: only the dissolved geometry and the computed result. No FastAPI imports.
"""

import json
import math
import os
import re
import time
import uuid
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from shapely.geometry import mapping, shape

from app.services.basin_geometry import BasinGeometry
from app.services.basin_service import BasinCell, BasinResult

RESULT_ID = re.compile(r"[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}")
EXPIRED_MESSAGE = "This result has expired; upload the basin again"
FORMAT_VERSION = 1


def is_result_id(text: str) -> bool:
    """True only for the 32-character lowercase hex form of a version-4 UUID (no disk access)."""
    return (
        isinstance(text, str)
        and RESULT_ID.fullmatch(text) is not None
        and uuid.UUID(text).hex == text
    )


class BasinStore:
    """Basin results saved as JSON files that expire after `ttl`."""

    def __init__(self, directory: Path, ttl: timedelta) -> None:
        self._directory = Path(directory)
        self._ttl_seconds = ttl.total_seconds()

    @property
    def ttl_hours(self) -> float:
        """How long a result is kept, in hours (shown on the pages)."""
        return self._ttl_seconds / 3600

    def save(self, result: BasinResult) -> str:
        """Purge expired results, then write `result` atomically and return its new id."""
        self.purge_expired()
        self._directory.mkdir(parents=True, exist_ok=True)
        result_id = uuid.uuid4().hex
        target = self._directory / f"{result_id}.json"
        temporary = self._directory / f".{result_id}.tmp"
        temporary.write_text(json.dumps(_encode(result), allow_nan=False), encoding="utf-8")
        os.replace(temporary, target)
        return result_id

    def load(self, result_id: str) -> BasinResult | None:
        """The stored result, or None when the id is invalid, unknown or expired.

        An invalid id returns None before any path is built; an expired file is deleted.
        """
        if not is_result_id(result_id):
            return None
        path = self._directory / f"{result_id}.json"
        try:
            modified = path.stat().st_mtime
        except FileNotFoundError:
            return None
        if self._expired(modified):
            path.unlink(missing_ok=True)
            return None
        try:
            return _decode(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError, TypeError):
            return None  # deleted meanwhile, or not written by this version

    def purge_expired(self) -> int:
        """Delete expired results and stale temporary files; return how many were deleted."""
        if not self._directory.is_dir():
            return 0
        deleted = 0
        with os.scandir(self._directory) as entries:
            for entry in entries:
                stem, _, suffix = entry.name.lstrip(".").partition(".")
                if suffix not in ("json", "tmp") or not is_result_id(stem):
                    continue  # never touch files this store did not write
                if self._expired(entry.stat().st_mtime):
                    Path(entry.path).unlink(missing_ok=True)
                    deleted += 1
        return deleted

    def _expired(self, modified: float) -> bool:
        return time.time() - modified > self._ttl_seconds


def _encode(result: BasinResult) -> dict:
    return {
        "version": FORMAT_VERSION,
        "basin_file": result.basin.filename,
        "features": result.basin.features,
        "geometry": mapping(result.basin.geometry),
        "area_km2": result.area_km2,
        "centroid_lon": result.centroid_lon,
        "centroid_lat": result.centroid_lat,
        "fallback": result.fallback,
        "resolution_deg": result.resolution_deg,
        "cells": [[c.lon, c.lat, c.used, c.valid_days] for c in result.cells],
        "start_year": result.start_year,
        "end_year": result.end_year,
        "period_start": result.period_start.isoformat(),
        "values": [None if math.isnan(v) else float(v) for v in result.series.to_numpy()],
    }


def _decode(data: dict) -> BasinResult:
    if data["version"] != FORMAT_VERSION:
        raise ValueError("unsupported basin result format")
    values = [math.nan if v is None else float(v) for v in data["values"]]
    index = pd.date_range(data["period_start"], periods=len(values), freq="D", name="date")
    series = pd.Series(values, index=index, name="precipitation_mm", dtype=float)
    return BasinResult(
        basin=BasinGeometry(
            filename=data["basin_file"],
            features=data["features"],
            geometry=shape(data["geometry"]),
        ),
        area_km2=data["area_km2"],
        centroid_lon=data["centroid_lon"],
        centroid_lat=data["centroid_lat"],
        fallback=data["fallback"],
        cells=[BasinCell(lon, lat, used, valid) for lon, lat, used, valid in data["cells"]],
        resolution_deg=data["resolution_deg"],
        start_year=data["start_year"],
        end_year=data["end_year"],
        period_start=date.fromisoformat(data["period_start"]),
        period_end=index[-1].date(),
        total_days=len(series),
        missing_days=int(series.isna().sum()),
        series=series,
    )
