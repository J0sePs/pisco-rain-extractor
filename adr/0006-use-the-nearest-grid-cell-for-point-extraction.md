# ADR-0006: Use the nearest grid cell for point extraction

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Project owner
- **Supersedes:** -
- **Related change:** -

## Context

Users request rainfall at a point (a station, a project site) given in WGS84 or UTM.
PISCOp is a 0.1° grid (about 11 km), so the point almost never matches a cell center.
Results are often compared with station records, and users need to know exactly which
cell the values came from.

## Options considered

1. **Nearest grid cell** – return the values of the cell whose center is closest;
   values are the dataset's own, traceable to one cell.
2. **Bilinear interpolation of the four surrounding cells** – smoother, but produces
   values that do not exist in the dataset and smooths daily extremes.
3. **Inverse distance weighting over a neighborhood** – same drawbacks as (2), plus
   extra parameters to justify.

## Decision

We will select the **nearest grid cell** to the requested WGS84 point (xarray
`method="nearest"` on the detected lat/lon coordinates), and always report the selected
cell's center coordinates and the great-circle distance (km) to the requested point.
If the point is outside the grid bounds, the request is rejected instead of snapping
to the border.

Rejected: bilinear interpolation and IDW – they create synthetic values and
attenuate maximum 24 h rainfall, which users compare against station data.

## Consequences

- **Positive:** reproducible, transparent results; reads a single cell (low memory).
- **Negative / trade-offs:** values can jump between neighboring points; a cell may be
  missing (no data) where a neighbor has data – this is reported, not filled.
- **Follow-up:** interpolation could be added later as an explicit option through a new ADR.
