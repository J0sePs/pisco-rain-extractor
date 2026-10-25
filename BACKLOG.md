# Backlog

Pending improvements and ideas, not yet planned. Each item becomes an OpenSpec change
(`/opsx:propose`) before any implementation.

## Point form
- Accept typographic minus signs (U+2212, U+2013) in coordinates.
- Accept comma as decimal separator, or explain it in the error.
- Show the received value in validation errors.
- "is required" message for empty fields.
- Show all validation errors at once.

## Layout
- Footer: use the site link colors for the figshare link.

## Tests
- Move the `precipitation_reads` spy fixture to `tests/conftest.py` (duplicated in
  `tests/test_point_result_pages.py` and `tests/test_export_pages.py`, and imported from
  `test_point_result_pages.py` by `test_basin_repository.py`, `test_basin_service.py`,
  `test_basin_pages.py` and `test_basin_export_pages.py`). Move the basin spies there too
  (`_spy_store_access`, `_spy_loads` in `test_basin_pages.py`, and the `filesystem_calls`
  fixture in `test_basin_store.py`): `test_basin_export_pages.py` imports helpers from
  `test_basin_pages.py`.

## Basin analysis
- Area-weighted areal mean (cell fraction inside the basin, optionally cos(latitude)); requires
  superseding ADR-0016.

## Analysis ideas
- Mann-Kendall trend test and Sen's slope on annual maxima.
- Gumbel/GEV return periods from annual maxima.
