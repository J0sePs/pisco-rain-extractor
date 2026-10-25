# Spec Delta

## ADDED Requirements

### Requirement: Basin download links
The basin result page SHALL show five download links, daily CSV, annual CSV, climatology CSV,
cells CSV and Excel workbook, under `/basin/result/<id>/export/`, with the same format note as
the point result page.

#### Scenario: Links of a stored result
- **GIVEN** a stored basin result with id `<id>`
- **WHEN** a user opens `/basin/result/<id>?page=2`
- **THEN** the page links to `/basin/result/<id>/export/daily.csv`, `…/annual.csv`,
  `…/climatology.csv`, `…/cells.csv` and `/basin/result/<id>/export.xlsx`, without `page`
- **AND** shows the note "CSV files are for R and Python. To open the data in Excel, use the
  .xlsx workbook: with Spanish regional settings, Excel does not split the columns of a
  comma-separated file."

#### Scenario: No links without a result
- **WHEN** every selected cell has no data
- **THEN** the form page shows "No data available for this basin" and no download link

### Requirement: Basin download validation
Basin downloads SHALL be built from the stored result without reading precipitation. An unknown
table, or an unknown, expired or malformed id, SHALL return 404 and no file.

#### Scenario: Valid basin download
- **WHEN** a user requests `/basin/result/<id>/export/daily.csv` for a stored result
- **THEN** the response is 200 with media type `text/csv; charset=utf-8` and no precipitation
  read

#### Scenario: Unknown table
- **WHEN** a user requests `/basin/result/<id>/export/location.csv`
- **THEN** the response is 404

#### Scenario: Expired result
- **WHEN** a user requests `/basin/result/<id>/export.xlsx` for a result deleted after 24 hours
- **THEN** the response is 404

### Requirement: Basin tables
The basin daily, annual and climatology CSVs SHALL have the columns, rows and CSV format of the
point tables, computed from the areal series.

#### Scenario: Basin daily and annual CSV
- **WHEN** a user downloads the CSVs of Rectangle (-76.30, -12.40, -76.10, -12.20) for 1981 to 1985
- **THEN** the daily header is `date,precipitation_mm` with 1826 data rows and the row
  `1981-01-03,3.0`
- **AND** the annual 1981 row is `1981,1638.0,9.0,365,TRUE`

#### Scenario: Basin day without data
- **GIVEN** every selected cell is missing on 1981-02-01
- **WHEN** a user downloads the daily CSV
- **THEN** its row is `1981-02-01,` (empty value)

### Requirement: Basin cells table export
The cells CSV SHALL have exactly the columns `cell_lon, cell_lat, used, valid_days`, one row per
selected cell ordered by latitude descending then longitude ascending, with `used` as `TRUE` or
`FALSE` and `valid_days` the cell's valid days in the requested period.

#### Scenario: Cells with one excluded
- **WHEN** a user downloads the cells CSV of Rectangle (-76.40, -12.50, -76.20, -12.30) for 1981 to 1985
- **THEN** there are 4 data rows, the first `-76.35,-12.35,TRUE,1826`
- **AND** the row of (-76.35, -12.45) is `-76.35,-12.45,FALSE,0`

#### Scenario: Fallback cell
- **WHEN** a user downloads the cells CSV of Rectangle (-76.14, -12.24, -76.12, -12.22) for 1981 to 1985
- **THEN** there is 1 data row, `-76.15,-12.25,TRUE,1824`

### Requirement: Basin workbook
The basin workbook SHALL contain the sheets `daily`, `annual`, `climatology`, `cells` and
`metadata`, in that order, with the same columns, rows and rounding as the CSVs and the Excel
conventions of the point workbook.

#### Scenario: Reference basin workbook
- **WHEN** a user downloads `/basin/result/<id>/export.xlsx` for a stored result
- **THEN** the media type is `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **AND** the sheet names are `daily`, `annual`, `climatology`, `cells`, `metadata`
- **AND** `cells` has `used` as booleans

#### Scenario: Excluded cell in the workbook
- **WHEN** the workbook of Rectangle (-76.40, -12.50, -76.20, -12.30) is downloaded
- **THEN** the `cells` row of (-76.35, -12.45) has `used` FALSE and `valid_days` 0

### Requirement: Basin workbook metadata
The basin `metadata` sheet SHALL have the columns `field, value` with the data source and
SENAMHI attribution, the uploaded file name, the number of dissolved features, the basin area,
the centroid, the cells used and excluded, the selection and areal mean methods, the years, the
period, the 95% completeness rule and the generation time in UTC.

#### Scenario: Reference basin metadata
- **WHEN** a user downloads the workbook of Rectangle (-76.40, -12.50, -76.20, -12.30) uploaded as
  `basin.geojson`, 1981 to 1985
- **THEN** the fields are `source`, `attribution`, `basin_file`, `features`, `basin_area_km2`,
  `centroid_lon`, `centroid_lat`, `cells_used`, `cells_excluded`, `cell_selection`,
  `areal_mean`, `start_year`, `end_year`, `period_start`, `period_end`, `completeness_rule` and
  `generated_at_utc`
- **AND** `basin_file` is `basin.geojson`, `features` is 1, `basin_area_km2` is 481.2,
  `cells_used` is 3 and `cells_excluded` is 1

#### Scenario: Fallback recorded in the metadata
- **WHEN** the workbook of Rectangle (-76.14, -12.24, -76.12, -12.22) is downloaded
- **THEN** `cell_selection` says "nearest cell to the basin centroid (no cell center inside)"

### Requirement: Basin export file names
Basin downloads SHALL be attachments named from the basin centroid (latitude first, rounded to
3 decimals, shortest form) and the requested years:
`pisco_basin_<lat>_<lon>_<start>-<end>_<table>.csv` and `pisco_basin_<lat>_<lon>_<start>-<end>.xlsx`.

#### Scenario: Basin CSV file name
- **WHEN** a user downloads the cells CSV of Rectangle (-76.30, -12.40, -76.10, -12.20) for 1981 to 1985
- **THEN** the `Content-Disposition` header is
  `attachment; filename="pisco_basin_-12.3_-76.2_1981-1985_cells.csv"`

#### Scenario: Basin workbook file name
- **WHEN** a user downloads the workbook of the same result
- **THEN** the file name is `pisco_basin_-12.3_-76.2_1981-1985.xlsx`
