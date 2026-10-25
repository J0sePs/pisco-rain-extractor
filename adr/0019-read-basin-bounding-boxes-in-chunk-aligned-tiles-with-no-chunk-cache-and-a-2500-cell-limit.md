# ADR-0019: Read basin bounding boxes in chunk-aligned tiles with no chunk cache and a 2500-cell limit

- **Status:** Accepted
- **Date:** 2026-10-25
- **Deciders:** Project owner
- **Supersedes:** [ADR-0017](0017-read-basin-bounding-boxes-in-time-blocks-with-a-2500-cell-limit.md)
- **Related change:** openspec/changes/add-basin-extraction/ (design D5)

## Context

ADR-0017 reads a basin's bounding box in time blocks aligned with the file's time chunks, one
`isel` per block. It estimated the peak at under 150 MB above the idle process, which keeps the
process within about 300 MB. `scripts/check_basin_memory.py` measured the real `PISCOp_d.nc`
(float32, zlib, chunks of 2740 × 35 × 29, so 11.1 MB per decompressed chunk) for a 50 × 50-cell
box over 1981–2025. All measurements are peak working set above the idle process, each in a
fresh process:

| Read strategy | Peak above idle |
|---|---|
| ADR-0017: one xarray `isel` per block, plus the areal mean | +191 MB (302 MB total) |
| One xarray `isel` per block, read only | +156 MB |
| One netCDF4 read per block, chunk cache 0 | +136 MB |
| Reads aligned with spatial chunks, default 64 MB chunk cache | +109 MB |
| **Reads aligned with spatial chunks, chunk cache 0** | **+46 MB** |

In one read, HDF5 decompresses every chunk the hyperslab touches (up to 3 × 3 per block at the
limit) and also keeps chunks in its 64 MB per-variable cache. Setting the cache through the
global netCDF4 default before `xr.open_dataset` did not help, because netCDF-C applies it only
when the variable is first used. Point reads need the cache: a repeated single-cell read takes
about 1 ms with the cache and about 0.15 s without it (ADR-0013).

## Options considered

1. **Chunk-aligned tiles through a dedicated netCDF4 variable with no chunk cache**: the
   repository opens the daily file a second time at startup with netCDF4 only for basin reads.
   It sets that variable's chunk cache to 0 and reads each time block tile by tile, one spatial
   chunk at a time. Measured at +46 MB, 1.8 s. Point reads keep the cached xarray handle.
2. **Keep ADR-0017 and lower the limit**: no new code, but large Andean basins are rejected and
   the estimate still has to be corrected.
3. **Turn off the cache for the xarray handle as well**: one handle, but every point read
   becomes about 100 times slower and contradicts the measurements of ADR-0013.
4. **Reach the netCDF4 variable through xarray internals** (`variable._data…`): no second
   handle, but it depends on private xarray API, which can break on any upgrade.

## Decision

We will use option 1. ADR-0017 is unchanged except for the read mechanism and the memory budget:

- **Bounding box**: unchanged. It contains the grid rows and columns whose rounded centers lie
  within the basin bounds, clipped to the grid domain. Latitude goes through `lat_slice`
  (ADR-0010) and longitude through `lon_slice`, using only the 1-D coordinates of the xarray
  handle.
- **Limit**: unchanged at `MAX_BOX_CELLS = 2500`. A larger box is rejected with its cell count
  before any read.
- **Read handle**: at startup the repository opens `PISCOp_d.nc` a second time with netCDF4 only
  for box reads. It keeps the detected precipitation variable with
  `set_var_chunk_cache(size=0)` and `set_auto_maskandscale(False)`, and closes it at shutdown.
  The handle is opened lazily: no precipitation value is read at open. This refines ADR-0005,
  because the repository is still the only code that opens NetCDF files.
- **Missing values**: values equal to the variable's `_FillValue` or `missing_value` become NaN.
  NaN stays NaN. The real file uses `_FillValue = -1.175494e+38`. If the variable declares
  `scale_factor` or `add_offset`, the handle is not used and reads fall back to the xarray
  handle (PISCOp declares neither).
- **Time blocks**: unchanged. Blocks are aligned with the time chunks (2740 days in the real
  file, or 1461 days when the file is not chunked).
- **Tiles**: within a block, one read per spatial chunk that the box touches, written into the
  block array (float32, time × lat × lon). Each block is then reduced to the daily areal values
  and per-cell valid counts (ADR-0016) and released.
- **Memory budget at the limit**: measured at +46 MB for reading and about +80 MB with the
  areal mean, which keeps the process well under 300 MB. `scripts/check_basin_memory.py` must
  stay under 300 MB.

Rejected: lowering the limit (option 2), because it rejects useful basins. Rejected: no cache
for everything (option 3), because it slows every point read by about 100 times. Rejected:
xarray internals (option 4), because they are private API.

## Consequences

- **Positive:** peak memory at the limit drops by more than half, and the read is slightly
  faster. Point reads keep their warm-cache speed.
- **Negative / trade-offs:** the daily file has two open handles. The repository decodes fill
  values itself for basin reads, which is a second decoding path, tested against xarray's on the
  same cells.
- **Follow-up:** `basin-extraction` spec (bounding-box read only, maximum basin size) is
  unchanged. `/adr-review` checks that basin reads go through the tile reader and that no other
  code opens NetCDF files.
