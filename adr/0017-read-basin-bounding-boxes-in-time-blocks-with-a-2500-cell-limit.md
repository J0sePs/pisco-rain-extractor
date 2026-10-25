# ADR-0017: Read basin bounding boxes in time blocks with a 2500-cell limit

- **Status:** Accepted
- **Date:** 2026-10-25
- **Deciders:** Project owner
- **Supersedes:** -
- **Related change:** openspec/changes/add-basin-extraction/ (design D3, D5)

## Context

ADR-0005 requires lazy reads that select cells and time first and never load the full daily
grid. A basin needs many cells at once, and the process should stay within about 300 MB.
These facts were measured on the real `PISCOp_d.nc`:

- Precipitation is float32 with shape (16436, 210, 174), stored with zlib level 4 in chunks of
  (2740, 35, 29). One chunk is 11.1 MB once decompressed.
- A full-period read (1981–2025) takes 0.67 s for a 10 × 10-cell box (6.6 MB) and 1.55 s for
  a 30 × 30-cell box (59 MB), cold.
- In a single read, a 50 × 50-cell box for 45 years is 164 MB of float32, and more once it is
  converted to float64.

Memory and time depend on the bounding box that is read, not on how many cells end up inside
the basin.

## Options considered

1. **Bounding box only, read in time blocks aligned with the file chunks, with a limit of 2500
   box cells**: peak memory is one block and does not depend on the period length.
2. **One read of the whole box**: simplest. Cons: 164 MB at 50 × 50, too close to the limit.
3. **A smaller limit with one read** (900 cells, 30 × 30, 59 MB): simple. Cons: it rejects
   common Andean basins.
4. **dask**: chunked computation for free. Cons: a new dependency that ADR-0005 only allows
   with its own ADR, and it is not needed for one mean.
5. **Limit on selected cells instead of box cells**: it sounds fairer to irregular basins.
   Cons: memory follows the box, so a thin diagonal basin could still exceed the budget.

## Decision

We will use option 1:

- **Bounding box**: only the grid rows and columns whose rounded centers lie within the basin
  bounds, clipped to the grid domain, are read. Latitude goes through `lat_slice` (ADR-0010).
  Longitude goes through `lon_slice`, the equivalent helper ADR-0010 anticipates: it uses the
  same tolerance and asserts the ascending order. The box is computed from the 1-D coordinates
  only.
- **Limit**: `MAX_BOX_CELLS = 2500` (rows × columns of the box). This is about 5° × 5°, roughly
  300,000 km². A larger box is rejected with its cell count before any precipitation is read.
  A centroid fallback reads one cell.
- **Time blocks**: the requested period is read in consecutive blocks. Each block is one
  `isel` on time positions taken from the calendar (ADR-0007) combined with the box selection.
  The block length is the time chunk length of the file (2740 days in the real file), or 1461
  days for an unchunked file. Each block is reduced to the daily areal values and the per-cell
  valid counts (ADR-0016) and then released.
- **Memory budget at the limit**: 27.4 MB per float32 block, plus at most one float64 working
  copy (55 MB), plus the HDF5 chunks being decompressed (11.1 MB each). The estimated peak is
  under 150 MB above the idle process. `scripts/check_basin_memory.py` measures the real peak.
- Reads happen once per basin request, in the POST (ADR-0015). Point reads are unchanged.

Rejected: a single read (option 2), because of memory. Rejected: a 900-cell limit (option 3),
because it rejects useful basins to save a loop. Rejected: dask (option 4), because of the
extra dependency, which is not needed. Rejected: a selected-cell limit (option 5), because it
does not bound memory.

## Consequences

- **Positive:** bounded memory for any period. Reads stay aligned with the file chunks. Large
  basins are rejected early with a clear message.
- **Negative / trade-offs:** basins whose box covers more than 2500 cells (for example the
  whole Ucayali or Marañón basins) cannot be processed. A POST at the limit takes a few
  seconds, estimated at about 4 s cold for 45 years.
- **Follow-up:** `basin-extraction` spec (bounding-box read only, maximum basin size).
  `/adr-review` checks that basin reads go through the box helpers and never `.load()` an
  unsliced variable. Raising the limit requires superseding this ADR, together with a new
  memory measurement.
