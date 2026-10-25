"""Dataset catalog summaries for display (no web framework imports)."""

from dataclasses import dataclass

from app.repositories.pisco_repository import DatasetKind, DatasetMetadata, PiscoRepository

UNITS_NOT_PROVIDED = "not provided"


@dataclass(frozen=True)
class DatasetSummary:
    """Display-ready description of one PISCOp file."""

    filename: str
    kind: str
    available: bool
    warnings: list[str]
    variables: list[tuple[str, str]]
    grid: str | None
    lat_range: str | None
    lon_range: str | None
    resolution: str | None
    period: str | None


def _period(meta: DatasetMetadata) -> str | None:
    if meta.time_start is None or meta.time_end is None:
        return None
    if meta.kind is DatasetKind.CLIMATOLOGY:
        return f"months {meta.time_start} to {meta.time_end}"
    return f"{meta.time_start} to {meta.time_end}"


def _range(low: float | None, high: float | None) -> str | None:
    if low is None or high is None:
        return None
    return f"{low:g} to {high:g}"


def summarize(meta: DatasetMetadata) -> DatasetSummary:
    """Turn repository metadata into display strings."""
    warnings = list(meta.warnings)
    if not meta.available:
        warnings.insert(0, f"{meta.filename} is not available: {meta.reason}")
    return DatasetSummary(
        filename=meta.filename,
        kind=str(meta.kind),
        available=meta.available,
        warnings=warnings,
        variables=[(v.name, v.units or UNITS_NOT_PROVIDED) for v in meta.variables],
        grid=f"{meta.n_lat} x {meta.n_lon}" if meta.available else None,
        lat_range=_range(meta.lat_min, meta.lat_max),
        lon_range=_range(meta.lon_min, meta.lon_max),
        resolution=f"{meta.resolution_deg:g}°" if meta.resolution_deg is not None else None,
        period=_period(meta),
    )


def list_dataset_summaries(repo: PiscoRepository) -> list[DatasetSummary]:
    """Summaries of the daily, monthly and climatology files, in that order."""
    return [summarize(meta) for meta in repo.all_metadata()]
