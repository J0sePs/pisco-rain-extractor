# Tasks

## 1. Project setup

- [ ] 1.1 Run `uv init --app --python 3.12 --name pisco-rain-extractor --vcs none`, then delete the generated root `main.py` — verify: `pyproject.toml` and `.python-version` (3.12) exist and no root `main.py` remains
- [ ] 1.2 Add runtime dependencies: `uv add fastapi uvicorn jinja2 python-multipart pydantic-settings xarray netcdf4 pandas numpy pyproj geopandas shapely matplotlib openpyxl` — verify: `uv run python -c "import fastapi, xarray, netCDF4, geopandas, matplotlib"` exits 0
- [ ] 1.3 Add dev dependencies: `uv add --dev pytest httpx ruff` — verify: `uv run pytest --version` and `uv run ruff --version` print versions
- [ ] 1.4 Configure ruff (`line-length = 100`, `target-version = "py312"`, `select = ["E","F","I","UP","B","SIM"]`) and pytest (`testpaths = ["tests"]`) in `pyproject.toml` — verify: `uv run ruff check .` exits 0
- [ ] 1.5 Create packages `app/`, `app/routes/`, `app/services/`, `app/repositories/` (each with `__init__.py`), folders `app/templates/`, `app/static/css/` and `tests/` (`__init__.py`) — verify: `uv run python -c "import app.routes, app.services, app.repositories"` exits 0

## 2. Settings

- [ ] 2.1 Implement `Settings` (`data_dir`, `daily_start_date`, `monthly_start_date`) and `get_settings()` in `app/config.py` (D2, D4) — verify: covered by 2.2
- [ ] 2.2 Add `tests/test_config.py`: default `data_dir` is `data` and both start dates are 1981-01-01; `DATA_DIR=/tmp/pisco` and `DAILY_START_DATE=1982-01-01` override them; `DAILY_START_DATE=1981-13-01` raises a validation error naming `daily_start_date` — verify: `uv run pytest tests/test_config.py -q` passes

## 3. Repository (dataset-catalog)

- [ ] 3.1 Build synthetic NetCDF fixtures in `tests/conftest.py` (D9): daily 16436 / monthly 540 (or a custom length) / climatology 12 (`PISCOp_clim2`, no units), 5 x 4 grid with descending latitudes, plus a factory for custom and corrupt files — verify: `uv run pytest --collect-only -q` collects without errors
- [ ] 3.2 Implement `detect_names(ds)` in `app/repositories/pisco_repository.py` (D3) — verify: covered by 3.3
- [ ] 3.3 Add `tests/test_detect_names.py`: PISCOp naming, alternative naming (`month`/`lat`/`lon`), no precipitation variable — verify: `uv run pytest tests/test_detect_names.py -q` passes
- [ ] 3.4 Implement `build_time_index(kind, n, start)` (D4) in the repository module, taking the start date as a parameter (no date literals in the module) — verify: covered by 3.5
- [ ] 3.5 Add `tests/test_time_index.py`: daily 16436 → 1981-01-01..2025-12-31, daily 16425 → ends 2025-12-20 (leap days counted), daily 365 from 1982-01-01 → ends 1982-12-31, monthly 540 → 1981-01-01..2025-12-01, climatology 12 → months 1..12, climatology 13 → error — verify: `uv run pytest tests/test_time_index.py -q` passes
- [ ] 3.6 Implement `check_period_consistency(daily, monthly)` (D7) — verify: covered by 3.7
- [ ] 3.7 Add `tests/test_period_consistency.py`: 16436 days vs 540 months → no warning; 16436 days vs 528 months → "Period mismatch: daily file ends in 2025-12, monthly file ends in 2024-12" — verify: `uv run pytest tests/test_period_consistency.py -q` passes
- [ ] 3.8 Implement `DatasetKind`, `DatasetMetadata` (with `warnings`), `PiscoRepository.open(settings)/metadata/all_metadata/dataset/time_index/close` with per-file error handling and the cross-check after opening (D2, D5, D6, D7) — verify: covered by 3.9
- [ ] 3.9 Add `tests/test_pisco_repository.py`: all files available, custom data dir, missing daily file reason, corrupt file reason, empty dir, precipitation not loaded in memory, bounds/resolution with descending latitudes, mismatch warning on both files while both stay available, no warning when the monthly file is missing — verify: `uv run pytest tests/test_pisco_repository.py -q` passes and `grep -rn "1981" app/ --include=*.py` only matches `app/config.py`

## 4. Service

- [ ] 4.1 Implement `DatasetSummary` and `list_dataset_summaries(repo)` in `app/services/dataset_service.py` (units "not specified", grid "210 x 174", resolution "0.1°", period text, `warnings` list) — verify: covered by 4.2
- [ ] 4.2 Add `tests/test_dataset_service.py`: formatted daily summary, climatology "months 1 to 12" and "not specified", unavailable file warning, period mismatch warning kept on an available file; assert the module does not import fastapi — verify: `uv run pytest tests/test_dataset_service.py -q` passes

## 5. Routes and app

- [ ] 5.1 Implement `create_app()` with lifespan open/close, static mount and `app = create_app()` in `app/main.py` (D2) — verify: `uv run python -c "from app.main import app"` exits 0
- [ ] 5.2 Implement `get_repository` and `GET /`, `GET /dataset` in `app/routes/pages.py` — verify: covered by 6.4

## 6. Templates and CSS (web-shell)

- [ ] 6.1 Create `app/templates/base.html` (header, nav with `aria-current`, SENAMHI footer) and `app/static/css/style.css` — verify: covered by 6.4
- [ ] 6.2 Create `app/templates/home.html` — verify: covered by 6.4
- [ ] 6.3 Create `app/templates/dataset.html` with per-file sections and `role="alert"` warnings mentioning `data/README.md` — verify: covered by 6.4
- [ ] 6.4 Add `tests/test_pages.py`: home 200 with required texts and `/dataset` link, home 200 without data, `/dataset` daily details, missing daily file warning with 200, period mismatch warning in both daily and monthly sections with their details still shown, nav marks current page, 404 for unknown page and missing static file, stylesheet 200 `text/css`, no `<script>` and no external URLs in `link`/`script`/`img` — verify: `uv run pytest tests/test_pages.py -q` passes

## 7. Integration verification

- [ ] 7.1 Full quality gate — verify: `uv run pytest -q`, `uv run ruff check .` and `uv run ruff format --check .` all pass
- [ ] 7.2 Start with the real data: `uv run uvicorn app.main:app --reload`, open http://127.0.0.1:8000/dataset — verify: the three files appear with grid 210 x 174 (climatology 210 x 180), period 1981-01-01 to 2025-12-31 for the daily file, no period mismatch warning, and the app's memory stays under ~300 MB
- [ ] 7.3 Temporarily start with `DATA_DIR=missing-dir` — verify: the app starts and `/dataset` shows three warnings

## Workflow follow-up

- `/adr-review bootstrap-app` → `/opsx:verify bootstrap-app` → `/opsx:archive bootstrap-app`.
