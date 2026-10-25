# ADR-0014: Define the tabular export format for CSV and XLSX

- **Status:** Accepted
- **Date:** 2026-10-25
- **Deciders:** Project owner
- **Supersedes:** -
- **Related change:** openspec/changes/add-exports/ (design D3–D6, D8)

## Context

Users take the point analysis tables (daily series, annual statistics, monthly climatology)
into R (`readr::read_csv`), Python (pandas) and Excel. Future basin exports will produce the
same kinds of tables, so the file format is a contract, not a detail of one change. Facts that
shape it:

- The daily values are float32 in the file. As float64, 0.1 becomes 0.10000000149011612, and
  pandas writes that verbatim.
- pandas writes `os.linesep` by default, which is `\r\n` on Windows, writes booleans as
  `True`/`False` and NaN as an empty field only if `na_rep` is set.
- Excel with Spanish regional settings expects `;` as the CSV separator and `,` as the decimal
  mark, so a comma-separated file opens as a single column.
- Missing days and periods with no valid day already exist (ADR-0012), so the format must say
  how to write them.

## Options considered

1. **R/pandas-first CSV plus an XLSX workbook for Excel**: UTF-8 without BOM, `,` separator,
   `.` decimal mark, `\n` line endings, one header line, no index column, ISO 8601 dates,
   missing values as empty fields, booleans as `TRUE`/`FALSE`, decimals rounded to 4 places.
   The workbook holds the same tables plus a metadata sheet. Pros: `read_csv` defaults work in
   R and pandas, with no arguments. Cons: Excel users in Spanish locales must use the workbook.
2. **Excel-locale CSV** (`;` separator, `,` decimal mark, BOM): opens directly in a Spanish
   Excel. Cons: R needs `read_csv2` and pandas needs `sep=";", decimal=","`, and the files
   depend on the locale of the reader.
3. **Raw pandas defaults** (no rounding, `True`/`False`, `NA`/`nan` text): no code. Cons:
   float32 noise in every value, platform-dependent line endings, `nan` text that R reads as a
   string.
4. **Metadata as comment lines at the top of the CSV**: attribution travels with the file.
   Cons: `read_csv` defaults then fail or need `comment = "#"` / `skip`.

## Decision

We will use option 1:

- **CSV**: UTF-8 without BOM, `,` separator, `.` decimal mark, `\n` line endings, a single
  header line with `snake_case` column names that carry the unit (`precipitation_mm`,
  `total_mm`), no index column, dates `YYYY-MM-DD`, missing values as empty fields, booleans
  `TRUE`/`FALSE`, decimal values rounded to 4 places and written in their shortest form
  (`22.168`, not `22.1680`). No comment or metadata lines.
- **Rounding** applies only to output: aggregates are computed from unrounded values.
- **XLSX**: one workbook with one sheet per table (same columns, rows and rounding as the CSVs,
  real Excel dates formatted `yyyy-mm-dd`, native booleans, empty cells for missing values)
  followed by a `metadata` sheet (`field, value`) with source, SENAMHI attribution, request,
  selected cell, period, the completeness rule (ADR-0012) and the generation time in UTC.
- **File names**: `pisco_<lat>_<lon>_<start>-<end>_<table>.csv` and
  `pisco_<lat>_<lon>_<start>-<end>.xlsx`, using the selected cell center (latitude first,
  shortest decimal form) and the requested years.
- The result page tells users that CSV files are for R and Python and that Excel users should
  open the workbook.

Rejected: Excel-locale CSV, because it breaks the default readers of the main audience (R and
Python) and ties the file to one locale. Rejected: raw pandas defaults, because of float32
noise, `\r\n` on Windows and `nan` text. Rejected: metadata comment lines, because they break
`read_csv` defaults; the workbook carries the attribution instead.

## Consequences

- **Positive:** files load with `readr::read_csv(path)` and `pandas.read_csv(path)` with
  correct types; names are stable for any point that selects the same cell; CSV and XLSX can
  never disagree because they share the same tables.
- **Negative / trade-offs:** CSV files carry no attribution; Excel users in Spanish locales
  cannot open the CSV directly; values below 0.0001 mm are lost (far below the precision of
  PISCOp).
- **Follow-up:** `data-export` spec (add-exports). Basin and any later exports follow this
  format; changing it requires superseding this ADR.
