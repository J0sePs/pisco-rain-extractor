# rainfall-analysis Specification

## Purpose

Turns the daily rainfall series of a point into the summaries users interpret (completeness,
annual totals and maxima, mean annual rainfall, monthly climatology) and shows them with charts
on a tabbed result page, all computed from the same cell and period the user requested.

## Requirements

### Requirement: Result tabs without JavaScript
The result page SHALL group its content in five tabs, Summary, Daily, Annual, Climatology and
Location, switched with links and CSS only. Summary SHALL be visible when no tab is selected.
The page SHALL NOT include JavaScript.

#### Scenario: Tabs present
- **WHEN** a user opens a valid result URL
- **THEN** the page has links to `#summary`, `#daily`, `#annual`, `#climatology` and `#location`
- **AND** one section with each of those ids

#### Scenario: No scripts on the result page
- **WHEN** a user opens a valid result URL
- **THEN** the HTML contains no `<script>` element and no `http://` or `https://` URL in `href`
  or `src` attributes of `link`, `script` or `img` elements

### Requirement: Year completeness
A calendar year SHALL be complete when its valid (non-missing) days are at least 95% of the
days of that calendar year (365 or 366), counting days absent from the file as missing.

#### Scenario: Complete year at the threshold
- **GIVEN** 1981 has 18 missing days (347 valid of 365, 95.07%)
- **WHEN** the annual statistics are computed
- **THEN** 1981 is complete

#### Scenario: Incomplete year below the threshold
- **GIVEN** 1981 has 19 missing days (346 valid of 365, 94.79%)
- **WHEN** the annual statistics are computed
- **THEN** 1981 is incomplete

#### Scenario: Leap year threshold
- **GIVEN** 2000 has 348 valid days of 366
- **THEN** 2000 is complete, and with 347 valid days it is incomplete

#### Scenario: Year cut by the end of the file
- **GIVEN** the daily file ends on 2025-06-30
- **WHEN** a user requests years 2025 to 2025
- **THEN** 2025 has 181 valid days and is incomplete

### Requirement: Annual statistics
For each requested year the system SHALL compute the total (sum of valid days, mm), the
maximum 24 h rainfall (largest single daily value, mm) and the valid days, and the Annual tab
SHALL list them with incomplete years flagged as "Incomplete".

#### Scenario: One rainy day
- **GIVEN** a year whose only non-zero day is 50.0 mm and no day is missing
- **WHEN** the annual statistics are computed
- **THEN** that year has total 50.0 mm, maximum 24 h 50.0 mm and 365 valid days

#### Scenario: Synthetic series
- **GIVEN** a cell with rainfall `(day index % 7) * 1.5` mm from 1981-01-01, missing on
  1981-01-03 and 1981-06-01
- **WHEN** a user requests years 1981 to 1985
- **THEN** the Annual tab shows 1981 with total 1629.0 mm, maximum 9.000 mm and 363 valid days
- **AND** 1984 with total 1648.5 mm and 366 valid days, and no year is flagged

#### Scenario: Year with every day missing
- **GIVEN** every day of 1982 is missing in the selected cell, and 1981 has data
- **WHEN** a user requests years 1981 to 1982
- **THEN** 1982 shows total and maximum as "missing", 0 valid days, flagged "Incomplete"

#### Scenario: Real-data reference maxima
- **GIVEN** the real daily file and point -76.1390222, -12.2935861, years 1981 to 2024
- **WHEN** the annual statistics are computed
- **THEN** the maximum 24 h is, within 0.001 mm, 14.754 (1981), 10.826 (1982), 18.961 (1983),
  13.368 (1984), 12.017 (1985), 19.406 (1997) and 22.168 (1998)
- **AND** every year has 365 valid days, or 366 in leap years

### Requirement: Mean annual rainfall
The mean annual rainfall SHALL be the mean of the annual totals of complete years only, shown
with 1 decimal and the number of complete years used.

#### Scenario: Incomplete year excluded
- **GIVEN** totals 400.0 mm (1981, complete), 600.0 mm (1982, complete), 100.0 mm (1983, incomplete)
- **WHEN** the mean annual rainfall is computed
- **THEN** it is 500.0 mm from 2 complete years

#### Scenario: No complete year
- **GIVEN** every requested year is incomplete
- **WHEN** the Summary tab is shown
- **THEN** the mean annual rainfall is shown as "Not available (no complete year)"

### Requirement: Monthly climatology
For each calendar month the system SHALL compute the mean and the sample standard deviation of
the monthly totals of that month over the requested years, using only months whose valid days
are at least 95% of the month's days, and SHALL report how many years were used.

#### Scenario: January climatology
- **GIVEN** January totals of 100.0 mm (1981) and 140.0 mm (1982), both months complete
- **WHEN** the climatology is computed for 1981 to 1982
- **THEN** January has mean 120.0 mm, standard deviation 28.3 mm and 2 years

#### Scenario: Incomplete month excluded
- **GIVEN** January 1982 has 2 missing days (29 of 31 valid, 93.5%) and January 1981 has 1
  missing day (30 of 31, 96.8%)
- **WHEN** the climatology is computed for 1981 to 1982
- **THEN** January uses only 1981 and reports 1 year

#### Scenario: Single year
- **GIVEN** a request for years 2000 to 2000
- **WHEN** the Climatology tab is shown
- **THEN** each month shows its total as the mean and its standard deviation as "–"

#### Scenario: Month without valid data
- **GIVEN** every requested February is incomplete
- **THEN** February shows mean and standard deviation as "–" and 0 years

### Requirement: Paginated daily table
The Daily tab SHALL list the series as `date` and `precipitation_mm` (2 decimals, "missing" for
missing days), 365 rows per page, with the page number, the page count and previous/next links
that open the Daily tab. A `page` outside 1..page count SHALL be clamped to the nearest page.

#### Scenario: Last page
- **GIVEN** a request for years 1981 to 1985 (1826 days)
- **WHEN** a user opens the result URL with `page=6`
- **THEN** the Daily tab shows "Page 6 of 6" with the single row 1985-12-31
- **AND** a previous link to `page=5` ending in `#daily` and no next link

#### Scenario: Second page
- **WHEN** a user opens page 2 of the same request
- **THEN** the first row is 1982-01-01

#### Scenario: Page out of range
- **WHEN** a user opens the same request with `page=99`, `page=0` or `page=abc`
- **THEN** the Daily tab shows page 6, 1 and 1 respectively, with status 200

### Requirement: Charts served as PNG
`GET /point/chart/<kind>.png` with the result query SHALL respond 200 with a PNG image for
kinds `daily`, `annual-totals`, `annual-maxima`, `climatology` and `location`, and each tab SHALL
show its charts as images with alternative text.

#### Scenario: Chart image
- **WHEN** a user requests `GET /point/chart/annual-maxima.png` with a valid result query
- **THEN** the response status is 200, content type `image/png`, and the body starts with the
  PNG signature

#### Scenario: Unknown chart
- **WHEN** a user requests `GET /point/chart/pie.png` with a valid result query
- **THEN** the response status is 404

#### Scenario: Invalid chart query
- **WHEN** a user requests `GET /point/chart/daily.png?lon=abc&lat=-12.29&start_year=1981&end_year=1985`
- **THEN** the response status is 422

#### Scenario: Chart of a cell without data
- **WHEN** a user requests `GET /point/chart/daily.png` for the all-missing cell
- **THEN** the response status is 404

### Requirement: Chart content
Annual charts SHALL draw one bar per year and distinguish incomplete years with their own
legend entry; the climatology chart SHALL draw 12 monthly bars with standard deviation error
bars; the location chart SHALL draw the requested point, the cell center and the cell edges on
longitude/latitude axes.

#### Scenario: Incomplete year in the annual chart
- **GIVEN** years 1981 to 1983 with 1982 incomplete
- **WHEN** the annual totals chart is drawn
- **THEN** it has 3 bars and a legend with "Complete year" and "Incomplete year"

#### Scenario: Climatology error bars
- **GIVEN** a request for years 1981 to 1985
- **WHEN** the climatology chart is drawn
- **THEN** it has 12 bars, each with an error bar

#### Scenario: Month without valid data in the chart
- **GIVEN** every requested February is incomplete
- **WHEN** the climatology chart is drawn
- **THEN** February has no bar and the other 11 months do

#### Scenario: Location chart
- **GIVEN** point -76.1390222, -12.2935861 and cell center -76.15, -12.25 with 0.1 degree cells
- **WHEN** the location chart is drawn
- **THEN** it shows both points and the cell edges -76.2 to -76.1 and -12.3 to -12.2
- **AND** the axes are labeled "Longitude (°)" and "Latitude (°)"
