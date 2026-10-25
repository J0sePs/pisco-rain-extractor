# ADR-0020: Read basin bounding boxes in chunk-aligned tiles through the shared xarray handle

- **Status:** Accepted
- **Date:** 2026-10-25
- **Deciders:** Project owner
- **Supersedes:** [ADR-0019](0019-read-basin-bounding-boxes-in-chunk-aligned-tiles-with-no-chunk-cache-and-a-2500-cell-limit.md)
- **Related change:** openspec/changes/add-basin-extraction/ (design D5)

## Context

ADR-0019 reads a basin's bounding box in chunk-aligned tiles through a second netCDF4 handle of
the daily file whose chunk cache is 0. It expected about +80 MB above the idle process at the
2500-cell limit. When implemented, the second handle did not behave as measured in isolation:

- With the xarray handle already open on the same file, HDF5 shares the underlying dataset, so
  the second handle's chunk cache of 0 has no effect. A tiled read went from +47 MB alone to
  +110 MB with the xarray handle open.
- Full `extract_basin` runs on the real `PISCOp_d.nc` (a 50 × 50 = 2500-cell box, 1981–2025,
  idle process at 111 MB, a fresh process each time) gave:

| Read strategy | Peak | Time |
|---|---|---|
| One xarray `isel` per time block (ADR-0017) | 302 MB | 2.5 s |
| Chunk-aligned tiles, second netCDF4 handle (ADR-0019) | 282 MB | 2.4 s |
| **Chunk-aligned tiles through the shared xarray handle** | **287 MB** | 2.5 s |

The second handle saves about 5 MB but adds a second open handle and a second way of turning
fill values into NaN. Most of the remaining peak is the shared HDF5 chunk cache (up to 64 MB,
which point reads also use), the 27 MB block, and the areal mean (about 33 MB).

## Options considered

1. **Chunk-aligned tiles through the shared xarray handle**: one `isel` per spatial chunk per
   time block. xarray keeps decoding fill values and packing. Measured 287 MB.
2. **Keep ADR-0019 and correct its numbers**: 282 MB, but the extra handle and decoding path
   remain for about 5 MB.
3. **Lower the limit for more margin**: rejects the larger Andean basins.
4. **One `isel` per block (ADR-0017)**: measured 302 MB, over the limit.

## Decision

We will use option 1:

- **Bounding box and limit**: unchanged from ADR-0019. The box holds the rows and columns whose
  rounded centers lie within the clipped basin bounds (`lat_slice`, `lon_slice`, 1-D
  coordinates only), and `MAX_BOX_CELLS = 2500` is checked before any read.
- **Time blocks**: aligned with the time chunks of the daily variable (2740 days in the real
  file, or 1461 days when the variable is not chunked).
- **Tiles**: within a block, one xarray `isel` per spatial chunk that the box touches, written
  into a float32 block (time × lat × lon). The variable is not chunked in space, the whole box is
  one tile. Fill values and packing are decoded by xarray, as for point reads.
- **One handle**: the daily file stays open once (ADR-0005), and its default chunk cache keeps
  warm point reads fast (ADR-0013).
- **Budget**: the measured peak at the limit is 287 MB, against a target of about 300 MB.
  `scripts/check_basin_memory.py` must stay under 300 MB, and any change to the read path or the
  limit must be measured with it.

Rejected: the second handle (option 2), because its cache setting is overridden by HDF5's shared
dataset and it gains about 5 MB for extra code. Rejected: a lower limit (option 3) while the
measurement is under the target. Rejected: one `isel` per block (option 4), because it is over
the limit.

## Consequences

- **Positive:** a single read path and a single fill-value decoding, both through xarray. The
  budget is measured, not estimated. Point reads are unchanged.
- **Negative / trade-offs:** the margin is thin (287 of about 300 MB). A larger limit, a
  heavier areal-mean step or a bigger HDF5 cache would need a new measurement and probably a
  new ADR. Reducing the areal-mean temporaries (about 33 MB) is the next lever if the margin
  is needed.
- **Follow-up:** design D5 records the measurement. `/adr-review` checks that basin reads go
  through `iter_box_blocks` and that `scripts/check_basin_memory.py` stays under 300 MB.
