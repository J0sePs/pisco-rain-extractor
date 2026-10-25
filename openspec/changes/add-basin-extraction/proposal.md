# Proposal

## Why

Hydrological studies need rainfall over a basin, not at one point. Today users must extract
many points and average them by hand. Uploading a basin boundary and getting its areal mean
daily rainfall, with the same analysis and exports as a point, closes that gap.

## What Changes

- New `/basin` page: upload a basin as GeoJSON or zipped Shapefile (`.shp`, `.shx`, `.dbf`,
  `.prj`) with the same year inputs and validation as the point form. Non-WGS84 inputs are
  reprojected; several features are dissolved into one geometry and the page says so.
- Cell selection: cells whose centers fall inside the basin; a basin with no center inside
  falls back to the cell nearest to its centroid (computed in UTM, ties per ADR-0011) with a
  warning. Only the basin bounding box is read, in time blocks, up to 2500 cells.
- Areal mean: per day, the arithmetic mean of selected cells with a valid value; cells with no
  value in the period are excluded and reported.
- Result page with the Summary, Daily, Annual and Climatology tabs plus a Cells tab (cell
  table and a map of the polygon and its cells). Summary adds basin area (km²) and cells used
  and excluded.
- Basin downloads in the ADR-0014 format, plus a `cells` table.
- Basin results are kept server-side under a random UUID for 24 hours in a gitignored
  directory, then deleted. Only the normalized geometry and the result are stored; the
  uploaded file is never written to the repository.
- Clear errors: file over 10 MB, unsupported type, empty or invalid geometry, missing `.prj`,
  basin outside the grid, basin larger than the maximum size.
- Navigation gains a "Basin" link.

### Out of scope

- Area-weighted mean (cell fraction inside the basin); recorded in `BACKLOG.md`.
- KML, GeoPackage or drawing a polygon on the page.
- Multiple basins per request; persistent or shareable-forever basin links.
- Changes to point extraction or its stateless URLs (ADR-0013 stays in force).

## Capabilities

### New Capabilities
- `basin-extraction`: basin upload and validation, cell selection, areal mean, result storage
  and expiry, result page with the Cells tab and basin charts.

### Modified Capabilities
- `data-export`: adds basin downloads (links, `cells` table, metadata, file names).
- `web-shell`: the shared navigation links to `/basin`.

## Decisions

- Basin results stored server-side under a random id with expiry (ADR-0018, superseding ADR-0015; complements,
  does not supersede, ADR-0013).
- Areal mean method: centers-inside selection, centroid fallback, arithmetic mean of valid
  cells, exclusion of all-missing cells (ADR-0016).
- Basin reads: bounding box only, in time blocks, limit of 2500 bounding-box cells (ADR-0017,
  follows ADR-0005 and ADR-0010).

## Impact

- New: `app/services/basin_service.py`, `basin_store.py`, `app/routes/basin.py`, templates
  `basin.html`, `basin_result.html`; repository method for blocked bounding-box reads.
- Refactor (no behavior change): analysis, chart and export services accept any analyzed
  series, not only a point.
- Settings: `BASIN_STORE_DIR`, `BASIN_TTL_HOURS`. `.gitignore` adds the store directory.
- No new dependency: geopandas, pyogrio, shapely and pyproj are already installed.
