# Tasks

## 1. Test fixtures

- [x] 1.1 Extend `write_pisco_file` in `tests/conftest.py` with `lat_start: float = LAT_START`, `values` (callable or array filling the precipitation grid; default zeros) and `coord_dtype` (default float32) (D9) — verify: `uv run pytest tests/test_fixtures.py -q` passes unchanged
- [x] 1.2 Add a fixture `reference_dir` in `tests/conftest.py`: daily file with latitudes -12.05 to -12.45 descending and longitudes -76.35 to -76.05 (5 x 4), one all-NaN cell and one cell with NaN on 1981-01-03 and 1981-06-01; plus a `reference_dir_float64` variant with float64 coordinates — verify: `uv run pytest --collect-only -q` collects without errors

## 2. Repository

- [x] 2.1 Add `GridExtent`, `CellRef`, `grid_extent()`, `nearest_cell()` and `_nearest_index()` with the ADR-0011 tie rule to `app/repositories/pisco_repository.py` (D1, D3) — verify: covered by 2.2
- [x] 2.2 Add `tests/test_point_repository.py`: extent of the default fixture is lon -81.4 to -81.0 and lat 1.5 to 2.0; reference point (-76.1390222, -12.2935861) selects center (-76.15, -12.25); exact center selects itself; a point on the outer edge selects the border cell; latitude -12.30 selects -12.25 and longitude -76.10 selects -76.05 on both the float32 and float64 reference grids; the same ties on an ascending-latitude copy give the same cells; `grid_extent()` is None when the daily file is missing — verify: `uv run pytest tests/test_point_repository.py -q` passes
- [x] 2.3 Add `read_cell_series(cell, start, end)` using calendar positions and a single `isel` (D4, D5) — verify: covered by 2.4
- [x] 2.4 Extend `tests/test_point_repository.py`: years 1981–1982 give 730 rows from 1981-01-01 to 1982-12-31; year 2000 gives 366 rows; NaN days are NaN; spy on `NetCDF4ArrayWrapper._getitem` proves every precipitation read covers one cell and the variable is not in memory afterwards; no read happens before `read_cell_series` is called; the test calls `pytest.fail("xarray internals changed; update the read spy")` if `_getitem` is missing or the spy records no read (never a skip) — verify: `uv run pytest tests/test_point_repository.py -q` passes

## 3. Services

- [x] 3.1 Implement `CoordinateError`, `utm_to_wgs84` and `haversine_km` in `app/services/coordinates.py` (D6, D7) — verify: covered by 3.2
- [x] 3.2 Add `tests/test_coordinates.py`: UTM (376135.41, 8640719.67, 18, South) → (-76.139022, -12.293586); zone 20 raises; North hemisphere uses EPSG:326xx; haversine of the reference pair is 4.991 km; identical points give 0.000 km — verify: `uv run pytest tests/test_coordinates.py -q` passes
- [x] 3.3 Implement `PointForm`, `PointInputError`, `NoDataError`, `PointResult`, `year_defaults`, `convert_utm` and `extract_point` in `app/services/point_service.py` with the validation order and messages of D2 — verify: covered by 3.4
- [x] 3.4 Add `tests/test_point_service.py`: defaults 1981/2025; last year incomplete (daily ends 2025-06-30) → 2024; every D2 message; outside-grid and invalid-year errors happen before any read (spy); summary for a cell with 2 missing days (365 total, 2 missing, head 1981-01-01..05, tail 1981-12-27..31, NaN shown as None); all-NaN cell raises `NoDataError`; the module does not import fastapi — verify: `uv run pytest tests/test_point_service.py -q` passes

## 4. Routes and app

- [x] 4.1 Implement `app/routes/point.py` (`GET /point`, `POST /point` with `action`, 422 on `PointInputError`) and include the router in `app/main.py` (D1) — verify: `uv run python -c "from app.main import app"` exits 0

## 5. Templates and CSS

- [x] 5.1 Create `app/templates/point.html` (form with WGS84 and UTM fieldsets, Convert/Extract buttons, errors with `role="alert"`, result section) and add `.error` and table styles to `app/static/css/style.css` (D8) — verify: covered by 5.3
- [x] 5.2 Add the `/point` link to the navigation in `app/templates/base.html` (order Home, Point, Dataset) — verify: covered by 5.3
- [x] 5.3 Add `tests/test_point_pages.py`: GET defaults; daily missing shows "Daily data is not available"; Convert fills -76.139022/-12.293586 without a result; zone 20 and "abc" errors with 422; reference extraction shows center -76.15/-12.25 and 4.991 km; tie point -76.15/-12.30 shows -12.25 and 5.560 km; outside grid, start > end and out-of-range year errors with 422; ocean cell shows "No data available for this location" with 200; nav on `/point` marks Point as current; no `<script>`. Update `tests/test_pages.py` so the dataset page nav also lists `/point` — verify: `uv run pytest tests/test_point_pages.py tests/test_pages.py -q` passes

## 6. Integration verification

- [x] 6.1 Quality gate — verify: `uv run pytest -q -W error::starlette.exceptions.StarletteDeprecationWarning`, `uv run ruff check .` and `uv run ruff format --check .` pass; `grep -rnE "Z1|isel\(|xarray" app/services app/routes` prints nothing
- [x] 6.2 Real data in the browser: `uv run uvicorn app.main:app --reload`, open http://127.0.0.1:8000/point — verify: UTM 376135.41 / 8640719.67 / 18 / South converts to -76.139022 / -12.293586; extracting 1981–2025 shows cell -76.15 / -12.25, 4.991 km, 16436 total days, 0 missing days; point -80.05 / -15.05 shows "No data available for this location"; the server process stays under ~300 MB

## Workflow follow-up

- `/adr-review add-point-extraction` → `/opsx:verify add-point-extraction` → `/opsx:archive add-point-extraction`.
