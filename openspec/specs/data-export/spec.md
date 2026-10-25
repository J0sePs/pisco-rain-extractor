# data-export Specification

## Purpose

Lets users download the tables of a point analysis (daily series, annual statistics, monthly
climatology) as CSV files that R reads directly and as one Excel workbook with the source
attribution, reproducible from the same stateless query as the result page.

## Requirements

### Requirement: Download links on the result page
The point result page SHALL show four download links, daily CSV, annual CSV, climatology CSV
and Excel workbook, each built from the same `lon`, `lat`, `start_year` and `end_year` query
as the result page and without the `page` parameter.

#### Scenario: Links reuse the result query
- **GIVEN** the result URL `/point/result?lon=-76.1390222&lat=-12.2935861&start_year=1981&end_year=1985&page=2`
- **WHEN** the page is rendered
- **THEN** it links to `/point/export/daily.csv?lon=-76.1390222&lat=-12.2935861&start_year=1981&end_year=1985`
- **AND** to `/point/export/annual.csv?…`, `/point/export/climatology.csv?…` and `/point/export.xlsx?…` with the same query

#### Scenario: Format note next to the links
- **WHEN** a user opens a valid result URL
- **THEN** the download block contains the note "CSV files are for R and Python. To open the
  data in Excel, use the .xlsx workbook: with Spanish regional settings, Excel does not split
  the columns of a comma-separated file."

#### Scenario: No links without a result
- **WHEN** a user opens a result URL for an ocean cell (-76.35, -12.45), 1981 to 1981
- **THEN** the page shows "No data available for this location" and no download link
- **AND** no format note

### Requirement: Download validation
Every download URL SHALL validate its query exactly like the result page. Invalid input SHALL
return 422 with the validation message as plain text; an unknown table, a cell without data or
an unavailable daily file SHALL return 404. No file SHALL be produced in those cases.

#### Scenario: Valid download
- **WHEN** a user requests `/point/export/daily.csv?lon=-76.1390222&lat=-12.2935861&start_year=1981&end_year=1985`
- **THEN** the response is 200 with media type `text/csv; charset=utf-8`

#### Scenario: Invalid period
- **WHEN** a user requests `/point/export/annual.csv?lon=-76.15&lat=-12.25&start_year=1985&end_year=1981`
- **THEN** the response is 422 with the text "Start year must not be later than end year"

#### Scenario: Non-numeric coordinate
- **WHEN** a user requests `/point/export.xlsx?lon=abc&lat=-12.25&start_year=1981&end_year=1981`
- **THEN** the response is 422 with the text "Longitude must be a number"

#### Scenario: Unknown table
- **WHEN** a user requests `/point/export/monthly.csv` with a valid query
- **THEN** the response is 404 and no precipitation value is read

#### Scenario: Cell without data
- **WHEN** a user requests `/point/export/daily.csv?lon=-76.35&lat=-12.45&start_year=1981&end_year=1981`
- **THEN** the response is 404

### Requirement: Daily table export
The daily CSV SHALL have exactly the columns `date, precipitation_mm` and one row per day of the
extracted series, in date order, including missing days with an empty value.

#### Scenario: Reference series
- **GIVEN** the reference cell (-76.15, -12.25) with rainfall `(day index % 7) * 1.5` mm from
  1981-01-01, missing on 1981-01-03 and 1981-06-01
- **WHEN** a user downloads the daily CSV for 1981 to 1985
- **THEN** the header line is `date,precipitation_mm` and there are 1826 data rows
- **AND** the first rows are `1981-01-01,0.0` and `1981-01-02,1.5`
- **AND** the row of 1981-01-03 is `1981-01-03,` (empty value)
- **AND** the last row is `1985-12-31,7.5` (day index 1825)

### Requirement: Annual table export
The annual CSV SHALL have exactly the columns `year, total_mm, max_24h_mm, valid_days,
complete`, one row per requested year, with the values and completeness of the Annual tab
(ADR-0012). `complete` SHALL be `TRUE` or `FALSE`.

#### Scenario: Reference years
- **WHEN** a user downloads the annual CSV of the reference cell for 1981 to 1985
- **THEN** there are 5 data rows, years 1981 to 1985
- **AND** the 1981 row is `1981,1629.0,9.0,363,TRUE`
- **AND** the 1984 row is `1984,1648.5,9.0,366,TRUE`

#### Scenario: Year without data
- **GIVEN** the reference cell misses every day of 1982
- **WHEN** a user downloads the annual CSV for 1981 to 1982
- **THEN** the 1982 row is `1982,,,0,FALSE`

### Requirement: Climatology table export
The climatology CSV SHALL have exactly the columns `month, mean_mm, sd_mm, n_years` and 12 rows,
months 1 to 12 as integers, with the values of the Climatology tab (complete months only,
sample standard deviation).

#### Scenario: Reference climatology
- **WHEN** a user downloads the climatology CSV of the reference cell for 1981 to 1985
- **THEN** there are 12 data rows, months 1 to 12
- **AND** the January row is `1,137.7,6.6577,5`

#### Scenario: Single year has no standard deviation
- **WHEN** a user downloads the climatology CSV of the reference cell for 1985 to 1985
- **THEN** every row has an empty `sd_mm` and `n_years` 1

### Requirement: CSV format
Every CSV SHALL be UTF-8 without byte order mark, comma separated, with `.` as decimal mark,
`\n` line endings, a single header line, no index column, ISO 8601 dates (`YYYY-MM-DD`),
missing values as empty fields and decimal values rounded to 4 decimals.

#### Scenario: Readable with default parsers
- **WHEN** the three CSVs of the reference cell for 1981 to 1985 are read with `pandas.read_csv`
  defaults
- **THEN** `precipitation_mm`, `total_mm`, `max_24h_mm`, `mean_mm` and `sd_mm` are float
- **AND** `year`, `valid_days`, `month` and `n_years` are integer and `complete` is boolean
- **AND** every `date` matches `^\d{4}-\d{2}-\d{2}$`

#### Scenario: No encoding artifacts
- **WHEN** a user downloads any CSV
- **THEN** the body does not start with the bytes `EF BB BF` and contains no `\r`
- **AND** contains neither the text `nan` nor `None`

#### Scenario: Single-precision noise removed
- **GIVEN** a daily value stored as the single-precision number nearest to 0.1 mm
- **WHEN** it is exported
- **THEN** the CSV field is `0.1`, not `0.10000000149011612`

### Requirement: Excel workbook
The workbook SHALL contain the sheets `daily`, `annual`, `climatology` and `metadata`, in that
order. The three table sheets SHALL have the same columns, rows and rounding as the CSVs, with
dates as Excel dates shown `yyyy-mm-dd`, `complete` as booleans and missing values as empty
cells.

#### Scenario: Reference workbook
- **WHEN** a user downloads `/point/export.xlsx` for the reference cell, 1981 to 1985
- **THEN** the media type is `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **AND** the sheet names are `daily`, `annual`, `climatology`, `metadata`
- **AND** `daily` has 1826 data rows, cell A2 is the date 1981-01-01 and the 1981-01-03 value is empty
- **AND** the `annual` 1981 row is 1981, 1629.0, 9.0, 363, TRUE

#### Scenario: Year without data in the workbook
- **GIVEN** the reference cell misses every day of 1982
- **WHEN** a user downloads the workbook for 1981 to 1982
- **THEN** the `annual` 1982 row has empty `total_mm` and `max_24h_mm`, `valid_days` 0 and
  `complete` FALSE

### Requirement: Workbook metadata
The `metadata` sheet SHALL have the columns `field, value` with the data source and SENAMHI
attribution, the requested point, the selected cell center, the distance in km, the requested
years and the extracted period, the 95% completeness rule and the generation time in UTC.

#### Scenario: Reference metadata
- **WHEN** a user downloads the workbook for (-76.1390222, -12.2935861), 1981 to 1985
- **THEN** the `metadata` sheet has the fields `source`, `attribution`, `requested_lon`,
  `requested_lat`, `cell_lon`, `cell_lat`, `distance_km`, `start_year`, `end_year`,
  `period_start`, `period_end`, `completeness_rule` and `generated_at_utc`
- **AND** `source` contains "SENAMHI PISCOp v3.0", `cell_lon` is -76.15, `cell_lat` is -12.25
  and `period_start` is 1981-01-01
- **AND** `completeness_rule` contains "95%"
- **AND** `generated_at_utc` matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`

#### Scenario: Period cut by the end of the file
- **GIVEN** the daily file ends on 1985-06-30
- **WHEN** a user downloads the workbook for 1985 to 1985
- **THEN** `end_year` is 1985 and `period_end` is 1985-06-30

### Requirement: Export file names
Downloads SHALL be sent as attachments named from the selected cell center (latitude first,
shortest decimal form) and the requested years:
`pisco_<lat>_<lon>_<start>-<end>_<table>.csv` and `pisco_<lat>_<lon>_<start>-<end>.xlsx`.

#### Scenario: CSV file name
- **WHEN** a user downloads the daily CSV for (-76.1390222, -12.2935861), 1981 to 1985
- **THEN** the `Content-Disposition` header is `attachment; filename="pisco_-12.25_-76.15_1981-1985_daily.csv"`

#### Scenario: Workbook file name
- **WHEN** a user downloads the workbook for the same request
- **THEN** the file name is `pisco_-12.25_-76.15_1981-1985.xlsx`

#### Scenario: Same cell, same name
- **WHEN** a user downloads the annual CSV for the point (-76.16, -12.26), which selects the
  same cell, 1981 to 1985
- **THEN** the file name is `pisco_-12.25_-76.15_1981-1985_annual.csv`

### Requirement: One read per download
Each download SHALL read precipitation from exactly one grid cell once, and the workbook SHALL
build its three tables from that single read.

#### Scenario: Workbook read count
- **WHEN** a user downloads the workbook for the reference cell, 1981 to 1985
- **THEN** exactly one precipitation read is performed and it covers one cell

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
