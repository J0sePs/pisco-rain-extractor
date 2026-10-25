# Proposal

## Why

The app can open and describe the PISCOp files, but users cannot get any rainfall yet. The
core need of students and practitioners is the daily series at one site (a station, a project
location) for a chosen period. Every later feature (analysis, exports, basins) builds on this
extraction, so it comes next.

## What Changes

- New page `/point`, linked from the navigation, with a form: longitude, latitude, start year
  and end year. Year defaults are the first year and the last complete year of the daily file.
- Optional UTM input (easting, northing, zone 17/18/19, hemisphere, default South). A
  "Convert" button fills longitude and latitude in WGS84 (pyproj) and re-renders the form.
- Extraction selects the nearest grid cell (ADR-0006), filters years with the calendar dates of
  ADR-0007 (never raw `Z1` values) and reads only that cell for that period (ADR-0005).
- The result shows the requested point, the selected cell center, the distance in km, the
  period, total days, missing days, and the first and last rows of the series.
- Clear errors for: a point outside the grid, invalid years, invalid UTM input, and a cell with
  no data ("No data available for this location").

### Out of scope

- Analysis tabs, statistics and charts (`add-point-analysis`); CSV/XLSX exports (`add-exports`).
- Basin or multi-point extraction; interpolation between cells (ADR-0006).
- Monthly or climatology files (ADR-0008 keeps the climatology catalog-only).
- JavaScript; the "Convert" action is a normal form submission.

## Capabilities

### New Capabilities
- `point-extraction`: point input (WGS84 or UTM), nearest-cell selection, period validation and
  the daily series of one cell, with its summary page.

### Modified Capabilities
- `web-shell`: the shared navigation adds a link to `/point`.

## Decisions

- Nearest cell, lazy single-cell reads, calendar filtering and order-aware latitude handling are
  already decided (ADR-0005, ADR-0006, ADR-0007, ADR-0010). Point extraction needs no latitude
  range, so `lat_slice` is not called here.
- **"Inside the grid" means inside the outer cell edges** (centers ± half the resolution:
  latitude -19.0 to 2.0, longitude -81.4 to -64.0 for the daily file). Points inside the grid
  but on a cell without data (ocean, outside the mask) are a separate error. Ties between two
  equidistant centers go to the northern/eastern cell. See ADR-0011: Define the point validity
  domain as the grid cell edges (Accepted).

## Impact

- New: `app/services/coordinates.py`, `app/services/point_service.py`, `app/routes/point.py`,
  `app/templates/point.html`, tests.
- Changed: `app/repositories/pisco_repository.py` (cell lookup and single-cell read),
  `app/main.py` (router), `app/templates/base.html` (nav), `app/static/css/style.css`.
- No new dependencies (pyproj is already installed).
