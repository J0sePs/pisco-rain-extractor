# ADR-0005: Read NetCDF files lazily with xarray

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Project owner
- **Supersedes:** -
- **Related change:** -

## Context

PISCOp v3.0 daily rainfall covers Peru at 0.1° from 1981 to 2025 (tens of thousands of
time steps). Loading the full daily grid would need several GB of RAM, more than a
student laptop or a small server can offer. Most requests read one cell (point) or a
few hundred cells (basin) over a time range. Variable and coordinate names may differ
between files and dataset versions.

## Options considered

1. **xarray + netCDF4, opened lazily once at startup** – `xr.open_dataset` keeps data
   on disk; selections read only the requested slice.
2. **Load everything into memory** – fastest queries, but memory use is prohibitive.
3. **Convert to Zarr/Parquet or a database** – efficient, but requires a preprocessing
   step and storing a derived copy of third-party data.
4. **Open the file on every request** – simple, but repeats the metadata cost per request.

## Decision

We will open `PISCOp_d.nc`, `PISCOp_m.nc` and `PISCOp_clim2.nc` **once**, lazily, with
**xarray + netCDF4** during the FastAPI lifespan, from `DATA_DIR`, and keep the handles in
the repository. Variable and coordinate names are **detected** from the files, not hardcoded.
Reads select the needed cells and time range first (`.sel`/`.isel`) and only then call
`.load()`/`.values`. The full daily grid is never loaded, not even in tests or scripts.
A missing file does not prevent startup; it is reported as unavailable.

Rejected: in-memory load – exceeds memory. Rejected: Zarr/database – derived copy of
SENAMHI data and an extra pipeline. Rejected: per-request open – unnecessary overhead.

## Consequences

- **Positive:** low memory footprint; startup is fast; works with the original files.
- **Negative / trade-offs:** time series reads for one cell may be slower than an
  optimized store, depending on the file chunking; open handles must be closed on shutdown.
- **Follow-up:** each `design.md` states the memory strategy of its NetCDF reads;
  dask is not added unless a later ADR justifies it.
