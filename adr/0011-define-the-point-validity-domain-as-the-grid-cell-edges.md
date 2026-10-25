# ADR-0011: Define the point validity domain as the grid cell edges

- **Status:** Accepted
- **Date:** 2026-10-25
- **Deciders:** Project owner
- **Supersedes:** -
- **Related change:** openspec/changes/add-point-extraction/ (design D3)

## Context

ADR-0006 selects the nearest grid cell and rejects points outside the grid, but does not say
where the grid ends or what happens when a point is exactly between two cell centers. Both
questions have observable effects and will come back in basin extraction (centroid fallback,
polygon bounding boxes):

- The daily PISCOp grid has centers from latitude -18.95 to 1.95 and longitude -81.35 to -64.05,
  every 0.1°. Each center represents a 0.1° cell, so the area covered by data reaches half a
  cell beyond the outermost centers.
- A point such as latitude -12.30 is exactly halfway between the centers -12.25 and -12.35.
  With float coordinates the two distances differ only by representation noise (3.8e-7° with
  float32 coordinates, checked), so a plain `argmin` or pandas `method="nearest"` picks a cell
  by accident, and the choice can change with the file's storage type.

## Options considered

1. **Cell edges as the domain, half-open cells for ties** – the grid covers the outer cell
   edges (centers ± resolution/2); a point exactly on an interior edge belongs to the cell to
   its north (latitude) or east (longitude); ties are detected with a 1e-6° tolerance.
2. **Centers as the domain** – accept only points between the outermost centers; simple, but
   rejects valid points in the outer half of every border cell.
3. **Keep the library's nearest rule for ties** – no extra code, but the result depends on float
   noise and on the axis order, so it is not reproducible across files.

## Decision

We will use option 1:

- **Validity domain:** a point is inside the grid when
  `min_center - res/2 <= coordinate <= max_center + res/2` for both latitude and longitude
  (inclusive), where `res` is the file's resolution. For the daily file: longitude -81.4 to
  -64.0 and latitude -19.0 to 2.0. Points outside are rejected (ADR-0006: never snapped).
- **Nearest cell with explicit ties:** on each axis the cell with the smallest
  `|center - coordinate|` is chosen. If two centers are within `1e-6` degrees of the same
  distance (the tolerance of ADR-0010), the one with the **larger** coordinate wins: the
  northern cell for latitude, the eastern cell for longitude. Each cell therefore covers
  `[center - res/2, center + res/2)`, with its southern and western edges inclusive.
- **Outer edges:** the northern and eastern outer edges belong to the border cell, so the domain
  stays closed as stated above.
- The rule is computed from the coordinate values, so it does not depend on whether the axis is
  stored ascending or descending (ADR-0010).
- Inside the domain, a cell whose values are all missing (ocean, outside the data mask) is a
  separate, explicit "no data" outcome, not an out-of-grid error.

Examples: latitude -12.30 selects -12.25; longitude -76.10 selects -76.05; longitude -64.0
selects -64.05.

This complements ADR-0006, which stays in force: the selected cell is still the nearest one.
Only the tie case, which ADR-0006 leaves to the library, is now defined.

Rejected: centers as the domain – rejects valid border points. Rejected: library tie rule –
not reproducible.

## Consequences

- **Positive:** every point maps to exactly one cell, reproducibly, for float32 or float64 and any
  axis order; the out-of-grid message can state the exact domain.
- **Negative / trade-offs:** nearest-cell selection is implemented explicitly (numpy on the 1-D
  coordinates) instead of relying on `method="nearest"`.
- **Follow-up:** basin extraction reuses the same domain and tie rule for its centroid fallback.
