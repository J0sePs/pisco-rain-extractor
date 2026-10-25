# ADR-0008: Catalog the PISCOp climatology file without using it for analysis

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Project owner
- **Supersedes:** -
- **Related change:** openspec/changes/bootstrap-app/ (design D11)

## Context

PISCOp v3.0 ships three files. Two of them, the daily (`PISCOp_d.nc`) and monthly
(`PISCOp_m.nc`) series, share one grid (210 x 174, longitude -81.35 to -64.05) and one period
(1981–2025). The third, `PISCOp_clim2.nc`, is different:

- Its variable is `PISCOp_clim2` and it has **no `units`** attribute.
- Its grid is **210 x 180** (longitude -81.95 to -64.05), so its cells do not line up with
  the daily grid by index.
- `data/readme.txt` describes it as "monthly normal **1991-2015** rainfall", a period that
  differs from the 1981–2025 daily series users extract.

The planned point analysis (change `add-point-analysis`) shows a monthly climatology next to
the daily and annual results for the **same cell and the same period the user chose**. Mixing
in a precomputed normal from another period and grid would put numbers side by side that
cannot be compared.

## Options considered

1. **Catalog only** – list the file and its metadata on `/dataset`; the repository refuses to
   hand its precipitation values to analysis features. The monthly climatology is computed from
   the daily series for the user's period.
2. **Use it directly for the climatology tab** – no computation, but different period (1991–2015),
   different grid (180 longitudes) and undeclared units.
3. **Regrid it to the daily grid and use it** – aligns the cells, but adds interpolation choices
   and produces a derived copy of SENAMHI data.
4. **Ignore the file entirely** – simpler, but hides from users a file they downloaded and may
   expect to see.

## Decision

We will **catalog the climatology file without using it for analysis** (option 1):

- `/dataset` lists `PISCOp_clim2.nc` with its own grid, bounds and period ("months 1 to 12"),
  and shows its units as "not provided".
- `PiscoRepository.dataset(CLIMATOLOGY)` raises `ValueError("climatology is catalog-only")`;
  only its metadata is available.
- Every monthly climatology shown by the app is computed from the daily file for the period the
  user requested.
- No code compares, aligns or combines grids across files; each file keeps its own coordinates.

Rejected: using it directly – period, grid and units do not match the series users analyze.
Rejected: regridding – introduces interpolation (against the spirit of ADR-0006) and a derived
copy of third-party data. Rejected: ignoring the file – users would not see why it is not used.

## Consequences

- **Positive:** every result on a page comes from the same series, cell and period; no grid
  alignment bugs; no assumption about the missing units.
- **Negative / trade-offs:** the official 1991–2015 normals are not shown; computing the
  climatology from daily data costs a read of the cell's full period (one cell, lazy, ADR-0005).
- **Follow-up:** `add-point-analysis` computes the monthly climatology from the daily series.
  Showing the official normals later would require a new ADR that supersedes this one and states
  how to handle the grid and units.
