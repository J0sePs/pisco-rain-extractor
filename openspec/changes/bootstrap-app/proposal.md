# Proposal

## Why

There is no application yet. Every later feature (point extraction, analysis, exports,
basins) needs the same foundation: a uv project, the layered skeleton, a repository that
opens the PISCOp v3.0 files safely, and a page that proves the data is readable.
Building it first fixes the architecture before any business logic exists.

## What Changes

- Initialize the project with uv (Python 3.12, `uv init --app`) and add the stack
  dependencies from `openspec/config.yaml`; dev tools: pytest, httpx, ruff.
- Create the layered skeleton: `app/main.py`, `app/config.py` (pydantic-settings,
  `DATA_DIR` default `data/`), `app/routes/`, `app/services/`, `app/repositories/`,
  `app/templates/`, `app/static/`, `tests/`.
- On startup (FastAPI lifespan) the repository opens `PISCOp_d.nc`, `PISCOp_m.nc` and
  `PISCOp_clim2.nc` lazily from `DATA_DIR` and detects the precipitation variable and the
  latitude, longitude and time coordinate names.
- The files store time as an integer index (`Z1`), not dates. The repository builds the
  calendar from a known start (1981-01-01, daily or monthly; climatology = 12 calendar
  months) and checks that the length matches and that the daily and monthly files end in
  the same month.
- `GET /` renders a home page. `GET /dataset` shows, per file: variables, units, grid size,
  lat/lon bounds, resolution and time range.
- A missing or unreadable file does not stop startup; `/dataset` shows a clear warning.
- Base Jinja2 layout (header, nav, footer) with plain CSS.
- pytest with synthetic NetCDF fixtures in `tests/conftest.py`; ruff configured in
  `pyproject.toml`.

### Out of scope

- Point or basin extraction, analysis, charts and exports (later changes).
- Coordinate conversion (UTM), file uploads, any JavaScript.
- Deployment, Docker, CI configuration.

## Capabilities

### New Capabilities
- `dataset-catalog`: opening the PISCOp files at startup, detecting their structure, and
  reporting their metadata and availability on `/dataset`.
- `web-shell`: home page, shared layout and navigation, static assets.

### Modified Capabilities
- None.

## Decisions

- **Time axis reconstruction** (integer `Z1` index → ISO dates from a fixed start date per
  file, start dates in settings) affects every later change: ADR-0007 (Accepted).
- Layering, lazy reads and the web stack follow ADR-0002 to ADR-0005; no new ADR needed.

## Impact

- New code: `app/`, `tests/`, `pyproject.toml`, `uv.lock`, `.python-version`.
- New dependencies (full stack from `openspec/config.yaml`, so later changes do not touch
  the environment): fastapi, uvicorn, jinja2, python-multipart, pydantic-settings, xarray,
  netcdf4, pandas, numpy, pyproj, geopandas, shapely, matplotlib, openpyxl;
  dev: pytest, httpx, ruff.
- Reads `data/` only through `app/repositories/`; no data is committed.
