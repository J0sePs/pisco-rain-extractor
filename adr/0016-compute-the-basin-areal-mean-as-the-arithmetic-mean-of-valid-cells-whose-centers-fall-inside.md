# ADR-0016: Compute the basin areal mean as the arithmetic mean of valid cells whose centers fall inside

- **Status:** Accepted
- **Date:** 2026-10-25
- **Deciders:** Project owner
- **Supersedes:** -
- **Related change:** openspec/changes/add-basin-extraction/ (design D3, D4, D6)

## Context

A basin result is one daily series that stands for the rainfall over a polygon. The grid holds
0.1° cells (about 11 km), so a basin covers anything from part of one cell to a few thousand
cells. To build that series, three choices must be fixed, and each one has observable effects:

- **Which cells**: a cell may lie wholly inside, partly inside or outside the basin. Small
  basins may contain no cell center at all.
- **How missing values combine**: individual cells have gaps, and ocean or masked cells have no
  value on any day (ADR-0011 calls this "no data").
- **Traceability**: users compare basin rainfall with station records and with other tools, so
  they need to know which cells were used and how.

Point extraction uses the dataset's own values with no interpolation (ADR-0006), and
aggregates follow the 95% completeness rule (ADR-0012).

## Options considered

1. **Arithmetic mean of the valid cells whose centers fall inside**: a day is missing only if
   no selected cell has a value that day, and cells with no value in the period are excluded
   and reported. Small basins fall back to the cell nearest to the centroid. Pros: simple and
   reproducible, it uses dataset values only, and every cell used is listed. Cons: it ignores
   partial cells, so it is less accurate for small or narrow basins.
2. **Area-weighted mean** (each cell weighted by the fraction of it inside the basin, and
   optionally by cos(latitude)): more accurate at the edges. Cons: it needs cell polygons and
   intersections, and the weights must be explained and exported.
3. **A day is missing if any selected cell is missing**: strict. Cons: one gappy cell erases
   days for the whole basin.
4. **Fill missing cells from neighbors**: a complete series, but made of synthetic values,
   which goes against ADR-0006.

## Decision

We will use option 1:

- **Selection**: the cells whose centers, rounded to 4 decimals, lie inside the basin or on
  its boundary (`covers`). The basin is the union of every polygon feature in the file, after
  reprojection to WGS84.
- **Centroid fallback**: when no center is inside, the single cell nearest to the basin
  centroid is used. The centroid is computed in UTM, EPSG `32700 + zone`, with the zone taken
  from the longitude of the basin's bounding-box center, and is then converted back to WGS84.
  Ties follow ADR-0011, and the page shows a warning. A centroid outside the grid domain is
  rejected as "basin outside the grid" (ADR-0006: never snapped).
- **Daily value**: `sum(valid values) / count(valid values)` over the selected cells. The day
  is missing only when the count is 0.
- **Exclusion**: a selected cell with no valid value in the requested period is excluded and
  listed as "Excluded (no data)". If every cell is excluded, the result is "No data available
  for this basin".
- **Aggregates**: the annual statistics, mean annual rainfall and climatology are computed on
  the areal series with the ADR-0012 rules, exactly as for a point.
- **Area**: geodesic area on the WGS84 ellipsoid of the whole basin, in km² with 1 decimal.
- **Exports**: the ADR-0014 format applies unchanged, plus a `cells` table
  (`cell_lon, cell_lat, used, valid_days`). Files are named after the centroid, rounded to 3
  decimals: `pisco_basin_<lat>_<lon>_<start>-<end>[_<table>].csv|.xlsx`. This addition does
  not change any ADR-0014 rule for points.

Rejected: area weighting (option 2). It is kept as a future option in `BACKLOG.md` and requires
superseding this ADR. Rejected: missing if any cell is missing (option 3), because it erases
valid days. Rejected: filling from neighbors (option 4), because it creates synthetic values.

## Consequences

- **Positive:** values are traceable to listed cells. The result is reproducible for float32 or
  float64 grids. Ocean cells never bias the mean. Point and basin tables share one analysis and
  one export format.
- **Negative / trade-offs:** cells that are only partly inside are ignored, so small, narrow or
  coastal basins are less accurate, and a basin narrower than a cell uses a single cell. The
  number of valid cells can change from day to day, and the series does not show it.
- **Follow-up:** `basin-extraction` spec (selection, fallback, areal mean, exclusion) and the
  basin requirements of `data-export`. Area weighting goes in `BACKLOG.md`.
