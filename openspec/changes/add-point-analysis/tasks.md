# Tasks

No new dependencies (matplotlib is declared in `pyproject.toml`).

## 1. Repository: monthly cell read

- [x] 1.1 In `app/repositories/pisco_repository.py` add the `kind` parameter to `nearest_cell` (DAILY or MONTHLY, same ADR-0011 rule on that file's coordinates) and `read_monthly_cell_series(cell)` (one `isel`, index = monthly calendar) (D10) — verify: covered by 1.2
- [x] 1.2 Extend `tests/test_point_repository.py`: `nearest_cell(-81.35, 1.95, MONTHLY)` on the default fixture selects the monthly center (-81.35, 1.95); `read_monthly_cell_series` returns 540 rows from 1981-01-01 to 2025-12-01; the read spy records exactly one read covering one cell; existing daily tests pass unchanged — verify: `uv run pytest tests/test_point_repository.py -q` passes

## 2. Services: point validation split

- [x] 2.1 In `app/services/point_service.py` add `PointQuery` and `validate_point(repo, form)` (D2 order of `add-point-extraction`, no read), change `extract_point(repo, query)`, add `resolution_deg`, `start_year`, `end_year` to `PointResult`, make `series` a `pd.Series`, and add `result_query(form)`; update the call in `app/routes/point.py` to `extract_point(repo, validate_point(repo, form))` so the current page keeps working (head/tail stay until 5.1) (D1) — verify: `uv run pytest tests/test_point_pages.py -q` passes
- [x] 2.2 Update `tests/test_point_service.py`: validation messages and "no read before validation" now target `validate_point`; `extract_point` returns `resolution_deg == 0.1`, `series` as `pd.Series` with NaN on 1981-01-03; `result_query` of form (" -76.1390222", "-12.2935861", "1981", "1985") is `lon=-76.1390222&lat=-12.2935861&start_year=1981&end_year=1985` — verify: `uv run pytest tests/test_point_service.py -q` passes

## 3. Services: analysis

- [x] 3.1 Create `app/services/analysis_service.py` with `is_complete`, `AnnualStat`, `annual_stats`, `MeanAnnual`, `mean_annual_rainfall` (D2, D3) — verify: covered by 3.2
- [x] 3.2 Add `tests/test_analysis_service.py` (synthetic `pd.Series`, no NetCDF): one 50 mm day → total 50.0, max 50.0, 365 valid; 347/365 complete, 346/365 incomplete, 348/366 complete, 347/366 incomplete; series ending 2025-06-30 → 2025 has 181 valid and is incomplete; all-missing 1982 → total/max None, 0 valid, incomplete; totals 400/600/100(incomplete) → mean 500.0 from 2 years; no complete year → mean None; module imports neither fastapi nor xarray — verify: `uv run pytest tests/test_analysis_service.py -q` passes
- [x] 3.3 Add `MonthlyClimate` and `monthly_climatology` to `app/services/analysis_service.py` (complete months only, `std(ddof=1)`, None below 2 years) (D3) — verify: covered by 3.4
- [x] 3.4 Extend `tests/test_analysis_service.py`: January 100.0/140.0 → mean 120.0, std 28.28 (±0.01), 2 years; January 1982 with 2 missing days excluded (1 year), January 1981 with 1 missing day kept; single year 2000 → mean = month total, std None; every February incomplete → mean None, std None, 0 years — verify: `uv run pytest tests/test_analysis_service.py -q` passes
- [x] 3.5 Add `PAGE_SIZE`, `DailyPage`, `daily_page`, `PointAnalysis` and `analyze_point` to `app/services/analysis_service.py` (D4) — verify: covered by 3.6
- [x] 3.6 Extend `tests/test_analysis_service.py`: 1826 rows 1981–1985 → 6 pages; page "2" starts 1982-01-01; page "6" has the single row 1985-12-31; "99" → 6, "0" → 1, "abc" → 1, "" → 1; missing day is None; `analyze_point` on a `PointResult` gives one `AnnualStat` per requested year and 12 `MonthlyClimate` — verify: `uv run pytest tests/test_analysis_service.py -q` passes

- [x] 3.7 Create `app/services/calendar_check.py` with `OffsetScore`, `alignment_scores` and `best_offset` (same month set for every offset) (D10) — verify: covered by 3.8
- [x] 3.8 Add `tests/test_calendar_check.py` (synthetic `pd.Series`, no NetCDF): a monthly series equal to the daily monthly sums gives best offset 0 with mean diff 0.0; the same daily values re-dated by +1 day give best offset −1; every offset is scored on the same number of months; module imports neither fastapi nor xarray — verify: `uv run pytest tests/test_calendar_check.py -q` passes

## 4. Services: charts

- [x] 4.1 Load the `dataviz` skill, then create `app/services/chart_service.py` with `ChartKind`, `build_figure` for the five kinds and `render_png` (OO `Figure`, never `pyplot`, module-level lock) (D7) — verify: covered by 4.2
- [x] 4.2 Add `tests/test_chart_service.py`: annual totals for 1981–1983 with 1982 incomplete → 3 bars and legend texts "Complete year", "Incomplete year"; all complete → no "Incomplete year" entry; climatology 1981–1985 → 12 bars with an error bar container; every February incomplete → 11 bars; location for (-76.1390222, -12.2935861) / (-76.15, -12.25) / 0.1° → rectangle from (-76.2, -12.3) with width and height 0.1, axis labels "Longitude (°)" and "Latitude (°)"; daily chart has one line; `render_png` output starts with `b"\x89PNG\r\n\x1a\n"`; `matplotlib.pyplot` not in `sys.modules` after rendering in a subprocess; module does not import fastapi — verify: `uv run pytest tests/test_chart_service.py -q` passes

## 5. Routes and templates

- [x] 5.1 Remove `head`, `tail`, `PREVIEW_ROWS` and `_value` from `app/services/point_service.py` and the "First days"/"Last days" tables from `app/templates/point.html` (D1) — verify: `uv run pytest tests/test_point_service.py -q` passes after dropping the head/tail asserts
- [x] 5.2 In `app/routes/point.py`: `POST /point` extract → validate and `RedirectResponse(f"/point/result?{query}", 303)`; add `GET /point/result` (422 → `point.html` with error and values, `NoDataError` → `point.html` 200, daily unavailable → `available=False`) (D1, D5) — verify: `uv run python -c "from app.main import app"` exits 0
- [x] 5.3 Add `GET /point/chart/{kind}.png` to `app/routes/point.py`: unknown kind → 404 before any read, `PointInputError` → 422 plain text, `NoDataError` or daily unavailable → 404, else `image/png` (D1) — verify: covered by 5.6
- [x] 5.4 Create `app/templates/point_result.html`: tab nav (`#summary`, `#daily`, `#annual`, `#climatology`, `#location`, plus a link back to `/point`), Summary `<dl>` with mean annual ("Not available (no complete year)" when None), Daily table + "Page N of M" + prev/next links ending in `#daily`, Annual table with "Incomplete" flag and "missing" for None, Climatology table with "–" for None, chart `<img>` with `alt` and `loading="lazy"` (D3, D8) — verify: covered by 5.6
- [x] 5.5 Add the tab rules (`:target`, `:has()`, `@supports` fallback) and the incomplete-row style to `app/static/css/style.css` (D8) — verify: covered by 5.6
- [x] 5.6 Rewrite the extraction tests in `tests/test_point_pages.py` for the redirect and add `tests/test_point_result_pages.py`: 303 with the exact `Location` and no read in the POST (spy); start > end → 422 without redirect; `lon=abc` → 422 with latitude kept; missing `end_year` → "End year must be an integer"; 1981 summary 365 total / 2 missing; 1981–1985: Annual 1981 "1629.0", "9.000", 363; 1984 "1648.5", 366; mean annual "1640.7" from 5 years; January "137.7" and "6.7"; page 6 "Page 6 of 6" with only 1985-12-31 and prev link `page=5#daily`; page 99/0/abc clamp; 1981-01-03 shown "missing"; tab links and section ids present; no `<script>` nor external URLs; ocean cell → 200 "No data available for this location" without tabs; each chart kind → 200 `image/png`; `pie.png` → 404; invalid chart query → 422; ocean chart → 404; one single-cell read per request (spy) — verify: `uv run pytest tests/test_point_pages.py tests/test_point_result_pages.py -q` passes

## 6. Integration verification

- [x] 6.1 Quality gate — verify: `uv run pytest -q -W error::starlette.exceptions.StarletteDeprecationWarning`, `uv run ruff check .` and `uv run ruff format --check .` pass; `grep -rnE --include=*.py "^\s*(import|from)\s.*(pyplot|xarray)|isel\(" app/services app/routes` prints nothing
- [x] 6.2 Add `scripts/check_calendar_alignment.py` (args `--lon`/`--lat`, default -76.15/-12.25; uses `PiscoRepository` and `calendar_check` only, never xarray directly; prints the offset table; exit 1 when `best_offset != 0`) (D10) — verify: `uv run python scripts/check_calendar_alignment.py` on the real data prints offset 0 with mean abs. diff ≈ 0.236 mm (±1 ≈ 1.25–1.28 mm) and exits 0
- [x] 6.3 Real data in the browser: `uv run uvicorn app.main:app --reload`, open http://127.0.0.1:8000/point, extract -76.1390222 / -12.2935861, 1981–2024 — verify: the URL becomes `/point/result?...`; Summary shows cell -76.15 / -12.25, 4.991 km, 16071 days, 0 missing, mean annual 468.6 mm from 44 years; Annual shows max 24 h 14.754 (1981), 10.826 (1982), 18.961 (1983), 13.368 (1984), 12.017 (1985), 19.406 (1997), 22.168 (1998) with 365/366 valid days and no "Incomplete" flag; every tab switches without JavaScript and keeps the Daily tab when paging; the five charts render; point -80.05 / -15.05 shows "No data available for this location"; the server process stays under ~300 MB

## Workflow follow-up

- ADR-0012 (D2) and ADR-0013 (D5) were recorded as Accepted with this plan.
- `/adr-review add-point-analysis` → `/opsx:verify add-point-analysis` → `/opsx:archive add-point-analysis`.
