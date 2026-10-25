# ADR-0010: Select latitude ranges through an order-aware helper with float tolerance

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Project owner
- **Supersedes:** -
- **Related change:** openspec/changes/bootstrap-app/ (design D10)

## Context

The three PISCOp v3.0 files store latitude **north to south** (1.95 down to -18.95). With
xarray, a label slice follows the stored order, so on a descending axis
`ds.sel(latitude=slice(south, north))` returns **zero rows, silently**: no error, just an empty
result that later code may turn into missing values or a wrong areal mean.

Coordinates may also carry float noise. The real files use float64, but a float32 grid (other
dataset versions, user-derived files, test fixtures) stores -1.05 as -1.0500000715, just beyond
the bound: an exact slice from -1.05 to 0.95 then returns 20 rows instead of 21 (checked in
`tests/test_lat_slice.py`). Both problems hit every feature that selects a latitude range:
basin bounding boxes, point neighborhoods and map extents.

## Options considered

1. **One order-aware helper with tolerance** – `lat_slice(lat, south, north, tol=1e-6)` in the
   repository returns `slice(north + tol, south - tol)` on a descending axis and
   `slice(south - tol, north + tol)` on an ascending one; every latitude range goes through it.
2. **Sort the latitude axis at open time** (`ds.sortby("latitude")`) – plain slices then work,
   but sorting reorders the array, breaks lazy reads and the file's chunk layout (ADR-0005).
3. **Select with boolean masks** (`ds.where((lat >= south) & (lat <= north), drop=True)`) –
   order-independent, but evaluates the mask over the data variable and can load it into memory.
4. **Ad-hoc handling at each call site** – no shared code, but every feature must remember the
   order and the tolerance; the descending-axis bug is easy to reintroduce.

## Decision

We will select latitude ranges **only** through `lat_slice` in
`app/repositories/pisco_repository.py` (option 1):

- `slice()` is never applied directly to a latitude coordinate anywhere in `app/`.
- The tolerance is `LAT_TOLERANCE_DEG = 1e-6` degrees (about 0.1 m), far below the 0.1° grid
  spacing, so it keeps border rows stored as float32 without ever adding a neighboring row.
- The axis order is read from the coordinate itself (`lat[0] > lat[-1]`), never assumed.
- Bounds and extents use `min`/`max`, never the first/last element.
- Nearest-cell selection (`method="nearest"`, ADR-0006) does not need the helper.
- Longitude is ascending in all PISCOp files; if a longitude range is ever needed, it follows
  the same rule through an equivalent helper.

Rejected: sorting at open time – breaks lazy, chunked reads (ADR-0005). Rejected: boolean
masks – can load the data variable. Rejected: ad-hoc handling – the silent zero-row bug returns
with the first call site that forgets.

## Consequences

- **Positive:** one tested place for order and tolerance; the silent empty-selection bug cannot
  appear in new features; works for ascending and descending files.
- **Negative / trade-offs:** callers must use the helper instead of the idiomatic
  `sel(slice(...))`; reviewers must enforce it.
- **Follow-up:** `/adr-review` checks that no `slice(` is applied to latitude outside
  `lat_slice`. `add-basin-extraction` uses it for the polygon bounding box.
