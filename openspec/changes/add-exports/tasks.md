# Tasks

No new dependencies (pandas and openpyxl are declared in `pyproject.toml`).

## 1. Services: export tables and CSV

- [x] 1.1 Create `app/services/export_service.py` with `ExportTable`, `COLUMNS`, `DECIMALS`, the media type constants, `table_frame` (None → NaN, `round(4)` on float columns, `datetime.date` dates, month 1..12) and `to_csv` (`index=False`, `lineterminator="\n"`, `na_rep=""`, `complete` → `TRUE`/`FALSE`) (D1–D4) — verify: covered by 1.2
- [x] 1.2 Add `tests/test_export_service.py` (synthetic `pd.Series` → `PointResult` → `analyze_point`, no NetCDF): reference series 1981–1985 → daily CSV header `date,precipitation_mm`, 1826 rows, `1981-01-01,0.0`, `1981-01-03,`, last `1985-12-31,7.5`; annual rows `1981,1629.0,9.0,363,TRUE` and `1984,1648.5,9.0,366,TRUE`; all-missing 1982 → `1982,,,0,FALSE`; climatology 12 rows, January `1,137.7,6.6577,5`; single year 1985 → every `sd_mm` empty, `n_years` 1; float32 0.1 → field `0.1`; body has no BOM, no `\r`, no `nan`/`None`; `pandas.read_csv` of each CSV gives float/int/bool dtypes and ISO dates as in the spec; module imports neither fastapi nor xarray — verify: `uv run pytest tests/test_export_service.py -q` passes

## 2. Services: workbook and file names

- [x] 2.1 Add `metadata_rows`, `to_xlsx` (`pd.ExcelWriter` with openpyxl, `date_format="YYYY-MM-DD"`, sheets `daily`, `annual`, `climatology`, `metadata`) and `export_filename` (`.4f` stripped coordinates, latitude first) to `app/services/export_service.py` (D5, D6) — verify: covered by 2.2
- [x] 2.2 Extend `tests/test_export_service.py`: workbook read back with `pandas.read_excel(sheet_name=None)` has the four sheets in order; `daily` 1826 rows with A2 a date 1981-01-01 (openpyxl `number_format` `YYYY-MM-DD`) and empty 1981-01-03; `annual` 1981 row 1981, 1629.0, 9.0, 363, True; all-missing 1982 → NaN, NaN, 0, False; `metadata` has the 13 fields of the spec, `cell_lon` -76.15, `cell_lat` -12.25, `completeness_rule` containing "95%", `generated_at_utc` `2026-10-25T12:00:00Z` for a fixed `datetime(2026, 10, 25, 12, tzinfo=UTC)`; series ending 1985-06-30 → `period_end` 1985-06-30 and `end_year` 1985; `export_filename` → `pisco_-12.25_-76.15_1981-1985_daily.csv` and `pisco_-12.25_-76.15_1981-1985.xlsx` — verify: `uv run pytest tests/test_export_service.py -q` passes

## 3. Routes and templates

- [x] 3.1 In `app/routes/point.py` extract the chart route's query handling into `_analysis_from_query` (404 / 422 mapping of D1) and switch the chart route to it — verify: `uv run pytest tests/test_point_result_pages.py -q` passes unchanged
- [x] 3.2 Add `GET /point/export/{table}.csv` and `GET /point/export.xlsx` to `app/routes/point.py` (unknown table → 404 before any read, attachment `Content-Disposition`, `datetime.now(UTC)`) (D1) — verify: covered by 3.4
- [x] 3.3 Add the Downloads `<nav>` with the four `download` links and the format note of the spec (CSV for R and Python, XLSX for Excel) to `app/templates/point_result.html`, and its style to `app/static/css/style.css` (D1) — verify: covered by 3.4
- [x] 3.4 Add `tests/test_export_pages.py` (reference fixtures, read spy as in `test_point_result_pages.py`): result page with `page=2` links to the four export URLs with the query without `page` and contains the exact format note; ocean result page has no export link and no format note; daily CSV → 200 `text/csv; charset=utf-8`, `Content-Disposition` `attachment; filename="pisco_-12.25_-76.15_1981-1985_daily.csv"` and `pandas.read_csv` columns/values as in 1.2; point (-76.16, -12.26) → `pisco_-12.25_-76.15_1981-1985_annual.csv`; workbook → XLSX media type, file name `pisco_-12.25_-76.15_1981-1985.xlsx`, four sheets; start 1985 > end 1981 → 422 "Start year must not be later than end year"; `lon=abc` on the workbook → 422 "Longitude must be a number"; `monthly.csv` → 404 with zero reads; ocean CSV → 404; daily file missing → 404; workbook download performs exactly one single-cell read — verify: `uv run pytest tests/test_export_pages.py -q` passes

## 4. Integration verification

- [x] 4.1 Quality gate — verify: `uv run pytest -q -W error::starlette.exceptions.StarletteDeprecationWarning`, `uv run ruff check .` and `uv run ruff format --check .` pass; `grep -rnE --include=*.py "^\s*(import|from)\s.*(xarray|fastapi)" app/services/export_service.py` prints nothing
- [x] 4.2 Real data in the browser: `uv run uvicorn app.main:app --reload`, open http://127.0.0.1:8000/point, extract -76.1390222 / -12.2935861, 1981–2024, then click each download link — verify: files `pisco_-12.25_-76.15_1981-2024_daily.csv`, `_annual.csv`, `_climatology.csv` and `pisco_-12.25_-76.15_1981-2024.xlsx` download; the annual CSV has `max_24h_mm` 22.168 for 1998 and 44 rows all `TRUE`; the workbook opens in Excel with four sheets, dates shown `yyyy-mm-dd` and the metadata attribution to SENAMHI
- [x] 4.3 RStudio check: `d <- readr::read_csv("pisco_-12.25_-76.15_1981-2024_daily.csv")` — verify: `readr::spec(d)` shows `date = col_date()` and `precipitation_mm = col_double()` with no parsing problems; `nrow(d)` is 16071; `max(d$precipitation_mm[format(d$date, "%Y") == "1998"], na.rm = TRUE)` is 22.168

## Workflow follow-up

- ADR-0014 (design D8) was recorded as Accepted with this plan.
- `/adr-review add-exports` → `/opsx:verify add-exports` → `/opsx:archive add-exports`.
