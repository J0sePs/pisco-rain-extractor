# Proposal

## Why

Point extraction returns a daily series but only a 5-row preview. Users need the standard
hydrological summaries of that series (annual totals, annual 24 h maxima, monthly
climatology) with charts, computed from the same cell and period they requested (ADR-0008).

## What Changes

- `POST /point` (extract) validates and redirects (303) to a bookmarkable
  `GET /point/result?lon=&lat=&start_year=&end_year=&page=`. **BREAKING** for anyone relying on
  the result being rendered by the POST response.
- The result page gets CSS-only tabs (no JavaScript): Summary, Daily, Annual, Climatology,
  Location. The 5-row head/tail preview is replaced by the Daily tab.
- Summary: requested point, selected cell, distance, period, total days, missing days and
  mean annual rainfall (complete years only).
- Daily: table paginated at 365 rows per page and a daily series chart.
- Annual: per year total, max 24 h and valid days; a year is complete with >= 95% valid days,
  incomplete years are flagged. Charts of annual totals and annual maxima.
- Climatology: mean and standard deviation of monthly totals per calendar month (months with
  >= 95% valid days), with an error-bar chart.
- Location: chart of the requested point vs the selected cell center and its edges.
- Charts rendered server-side by a charts service (matplotlib, Agg) and served as PNG by
  `GET /point/chart/{kind}.png`, which re-reads the single cell.

### Out of scope

- CSV/XLSX export, basin (polygon) analysis, multi-point comparison.
- Return periods / frequency analysis of annual maxima, rolling multi-day maxima.
- Caching of extracted series; using `PISCOp_clim2.nc` (ADR-0008).

## Capabilities

### New Capabilities
- `rainfall-analysis`: statistics of a point series (completeness, annual statistics, mean
  annual rainfall, monthly climatology), the tabbed result page and its PNG charts.

### Modified Capabilities
- `point-extraction`: the result moves to a bookmarkable GET URL reached by redirect; the
  summary requirement replaces the head/tail preview; the no-data message is shown there.

## Impact

- Code: `app/services/point_service.py` (split validation from extraction),
  new `app/services/analysis_service.py` and `app/services/chart_service.py`,
  `app/routes/point.py`, new `app/templates/point_result.html`, `app/static/css/style.css`.
- No new dependencies (matplotlib is already declared).
- Each result page and each chart performs one single-cell read (ADR-0005).
- Diagnostic `scripts/check_calendar_alignment.py` (daily monthly sums vs `PISCOp_m.nc`,
  offsets −2..+2) to re-check the calendar on real data.

## Decisions

- Stateless result and chart URLs that re-read the cell on every request (no server cache) —
  [ADR-0013](../../../adr/0013-serve-point-results-and-charts-from-stateless-get-urls-that-re-read-the-cell.md).
- Completeness rule: a year or month counts only with >= 95% valid days, applied to mean annual
  rainfall and climatology —
  [ADR-0012](../../../adr/0012-use-a-95-percent-valid-day-threshold-for-complete-years-and-months.md).
- Charts with matplotlib's object-oriented API (`Figure` + Agg canvas), never `pyplot`, so
  rendering is safe in FastAPI's thread pool.
