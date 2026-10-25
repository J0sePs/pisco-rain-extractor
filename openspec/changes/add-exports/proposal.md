# Proposal

## Why

The point result page shows the daily series, annual statistics and climatology only as HTML
tables. Users analyze the data further in R (RStudio) and Excel, so they need the same tables
as files that load without manual cleanup.

## What Changes

- A "Downloads" block on the point result page with four links: daily CSV, annual CSV,
  climatology CSV and an Excel workbook. Each link reuses the result query string
  (`lon`, `lat`, `start_year`, `end_year`, ADR-0013).
- `GET /point/export/{table}.csv` (`daily`, `annual`, `climatology`) and
  `GET /point/export.xlsx`, validated exactly like `/point/result`.
- CSV columns:
  - daily: `date, precipitation_mm`
  - annual: `year, total_mm, max_24h_mm, valid_days, complete`
  - climatology: `month, mean_mm, sd_mm, n_years`
- CSV format: UTF-8 without BOM, comma separator, decimal point, `\n` line endings, ISO dates,
  no index column, missing values as empty fields, `complete` as `TRUE`/`FALSE`, values rounded
  to 4 decimals. Readable with `readr::read_csv` defaults.
- Workbook: sheets `daily`, `annual`, `climatology` (same columns and rounding) plus `metadata`
  (source and SENAMHI attribution, requested point, selected cell, distance, period, the 95%
  completeness rule, generation timestamp in UTC).
- File names from the selected cell center and the requested years:
  `pisco_<lat>_<lon>_<start>-<end>_<table>.csv` and `pisco_<lat>_<lon>_<start>-<end>.xlsx`.

### Out of scope

- Metadata or comment lines inside the CSV files (they would break `read_csv` defaults).
- Exports of basin or multi-point results, monthly series, NetCDF or other formats.
- Zip bundles, streaming responses, caching of generated files.

## Capabilities

### New Capabilities
- `data-export`: CSV and XLSX downloads of the point analysis tables, their columns, format,
  file names and validation.

### Modified Capabilities
- None. The result page gains links, but no existing requirement changes.

## Impact

- New `app/services/export_service.py` (pandas + openpyxl, no FastAPI).
- `app/routes/point.py` (two download routes, shared query handling with the chart route),
  `app/templates/point_result.html`, `app/static/css/style.css`.
- No new dependencies: pandas and openpyxl are already declared.
- Each download performs one single-cell read (ADR-0005, ADR-0013); the workbook builds its
  three tables from that one read.

## Decisions

- Tabular export format (column names, 4-decimal rounding, empty missing values, `TRUE`/`FALSE`,
  ISO dates, UTF-8 without BOM) is a contract that future basin exports must follow —
  [ADR-0014](../../../adr/0014-define-the-tabular-export-format-for-csv-and-xlsx.md).
- Downloads reuse the stateless GET query of ADR-0013; no new ADR.
- Completeness flags and climatology follow ADR-0012 unchanged.
