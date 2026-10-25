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
  `tests/test_point_result_pages.py` and `tests/test_export_pages.py`).

## Analysis ideas
- Mann-Kendall trend test and Sen's slope on annual maxima.
- Gumbel/GEV return periods from annual maxima.
