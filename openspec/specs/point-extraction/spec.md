# point-extraction Specification

## Purpose

Lets users obtain the daily PISCOp v3.0 rainfall series of the grid cell nearest to a point
given in WGS84 or UTM, for a chosen range of years, with clear errors when the request cannot
be served.

## Requirements

### Requirement: Point request form
`GET /point` SHALL respond 200 with a form for longitude, latitude, start year and end year.
The year fields SHALL default to the first year and the last complete year of the daily file.

#### Scenario: Default years
- **GIVEN** the daily file covers 1981-01-01 to 2025-12-31
- **WHEN** a user opens `GET /point`
- **THEN** the response status is 200
- **AND** the start year defaults to 1981 and the end year defaults to 2025

#### Scenario: Last year incomplete
- **GIVEN** the daily file covers 1981-01-01 to 2025-06-30
- **WHEN** a user opens `GET /point`
- **THEN** the end year defaults to 2024

#### Scenario: Daily file unavailable
- **GIVEN** the daily file is missing
- **WHEN** a user opens `GET /point`
- **THEN** the response status is 200
- **AND** the page shows "Daily data is not available" with a link to `/dataset` and no form

### Requirement: UTM to WGS84 conversion
The form SHALL accept an optional UTM coordinate (easting, northing, zone 17, 18 or 19,
hemisphere North or South, default South). The "Convert" action SHALL fill longitude and
latitude with the WGS84 equivalent, rounded to 6 decimals, without extracting data.

#### Scenario: Reference conversion
- **GIVEN** easting 376135.41, northing 8640719.67, zone 18, hemisphere South
- **WHEN** the user submits the form with the "Convert" action
- **THEN** the form shows longitude -76.139022 and latitude -12.293586
- **AND** no extraction result is shown

#### Scenario: Zone outside Peru
- **GIVEN** easting 376135.41, northing 8640719.67 and zone 20
- **WHEN** the user submits the "Convert" action
- **THEN** the page shows the error "UTM zone must be 17, 18 or 19"
- **AND** longitude and latitude are not changed

#### Scenario: Non-numeric UTM value
- **GIVEN** easting "abc", northing 8640719.67 and zone 18
- **WHEN** the user submits the "Convert" action
- **THEN** the page shows the error "Easting must be a number"

### Requirement: Nearest cell selection
The system SHALL select the daily grid cell whose center is nearest to the requested WGS84
point, resolving ties within 1e-6 degrees towards the northern or eastern cell, and SHALL
report the cell center and the great-circle distance in km, rounded to 3 decimals.

#### Scenario: Reference point
- **GIVEN** the real daily file
- **WHEN** a user requests longitude -76.1390222, latitude -12.2935861
- **THEN** the selected cell center is longitude -76.15, latitude -12.25
- **AND** the distance is 4.991 km

#### Scenario: Point exactly on a cell center
- **GIVEN** a cell centered at longitude -81.25, latitude 1.75
- **WHEN** a user requests that exact point
- **THEN** that cell is selected and the distance is 0.000 km

#### Scenario: Point equidistant in latitude
- **GIVEN** cell centers at latitude -12.25 and -12.35 and a center at longitude -76.15
- **WHEN** a user requests longitude -76.15, latitude -12.30
- **THEN** the northern cell, latitude -12.25, is selected
- **AND** the distance is 5.560 km

#### Scenario: Point equidistant in longitude
- **GIVEN** cell centers at longitude -76.15 and -76.05 and a center at latitude -12.25
- **WHEN** a user requests longitude -76.10, latitude -12.25
- **THEN** the eastern cell, longitude -76.05, is selected
- **AND** the distance is 5.433 km

#### Scenario: Tie with float32 coordinates
- **GIVEN** the same grid stored as float32, where the distances from -12.30 to -12.25 and to
  -12.35 differ only by 3.8e-7 degrees
- **WHEN** a user requests longitude -76.15, latitude -12.30
- **THEN** latitude -12.25 is selected, as with float64 coordinates

### Requirement: Point inside the grid
The system SHALL extract only when the point lies inside the outer cell edges of the daily
grid (cell centers ± half the resolution); otherwise it SHALL show an error and SHALL NOT read data.

#### Scenario: Point outside the grid
- **GIVEN** the daily grid spans latitude -18.95 to 1.95 and longitude -81.35 to -64.05
- **WHEN** a user requests longitude -60.0, latitude -12.0
- **THEN** the page shows the error "The point is outside the PISCOp grid (longitude -81.4 to -64.0, latitude -19.0 to 2.0)"
- **AND** no precipitation values are read

#### Scenario: Point on the outer edge
- **GIVEN** the same grid
- **WHEN** a user requests longitude -64.0, latitude -12.0
- **THEN** the point is accepted and the cell centered at longitude -64.05 is selected

#### Scenario: Invalid coordinate value
- **WHEN** a user submits latitude "twelve"
- **THEN** the page shows the error "Latitude must be a number"

### Requirement: Period validation
The start year SHALL NOT be later than the end year, and both SHALL lie within the years
covered by the daily file; otherwise the system SHALL show an error and SHALL NOT read data.

#### Scenario: Start after end
- **WHEN** a user requests start year 2010 and end year 2000
- **THEN** the page shows the error "Start year must not be later than end year"

#### Scenario: Year outside the data
- **GIVEN** the daily file covers 1981 to 2025
- **WHEN** a user requests start year 1975 and end year 1990
- **THEN** the page shows the error "Years must be between 1981 and 2025"

#### Scenario: Single year
- **WHEN** a user requests start year 2000 and end year 2000
- **THEN** the period is 2000-01-01 to 2000-12-31 with 366 total days

### Requirement: Daily series extraction
The system SHALL return the daily series of the selected cell for the requested years as rows
of `date` (ISO 8601) and `precipitation_mm`, using the dates of the daily calendar, and SHALL
read only that cell for that period.

#### Scenario: Calendar-based period
- **GIVEN** the daily calendar starts on 1981-01-01
- **WHEN** a user requests years 1981 to 1982
- **THEN** the series has 730 rows from 1981-01-01 to 1982-12-31

#### Scenario: Only the selected cell is read
- **GIVEN** a daily file of 5 x 4 cells
- **WHEN** a point series is extracted for years 1981 to 1985
- **THEN** every read of precipitation values covers exactly one cell
- **AND** the full precipitation variable is never loaded into memory

### Requirement: Point result summary
After a successful extraction the page SHALL show the requested point, the selected cell
center, the distance in km, the period, total days, missing days, and the first 5 and last 5
rows of the series.

#### Scenario: Summary values
- **GIVEN** a cell with 2 missing days in 1981
- **WHEN** a user requests years 1981 to 1981 for that cell
- **THEN** the page shows period 1981-01-01 to 1981-12-31, 365 total days and 2 missing days
- **AND** shows the rows for 1981-01-01 to 1981-01-05 and 1981-12-27 to 1981-12-31

#### Scenario: Missing values displayed
- **GIVEN** 1981-01-03 is missing in the selected cell
- **WHEN** the first rows are shown
- **THEN** the precipitation of 1981-01-03 is shown as "missing"

### Requirement: Cell without data
If every value of the selected cell is missing for the requested period, the system SHALL show
"No data available for this location" instead of a result.

#### Scenario: Ocean cell
- **GIVEN** the cell nearest to longitude -80.05, latitude -15.05 has only missing values
- **WHEN** a user requests that point for 1981 to 1981
- **THEN** the page shows "No data available for this location"
- **AND** no series rows are shown
