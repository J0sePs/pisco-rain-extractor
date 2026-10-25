# Spec Delta

## ADDED Requirements

### Requirement: Bookmarkable result URL
A valid "Extract" submission of `POST /point` SHALL respond 303 with a redirect to
`/point/result?lon=<lon>&lat=<lat>&start_year=<start>&end_year=<end>`, reading no precipitation
values. `GET /point/result` SHALL apply the same validation as the form and, when invalid,
SHALL respond 422 with the form page showing the error and the submitted values.

#### Scenario: Redirect after a valid extraction
- **GIVEN** longitude -76.1390222, latitude -12.2935861, start year 1981 and end year 1985
- **WHEN** the user submits `POST /point` with the "Extract" action
- **THEN** the response status is 303
- **AND** the `Location` header is `/point/result?lon=-76.1390222&lat=-12.2935861&start_year=1981&end_year=1985`
- **AND** no precipitation values are read by the POST request

#### Scenario: Invalid form is not redirected
- **WHEN** a user submits `POST /point` with start year 2010 and end year 2000
- **THEN** the response status is 422
- **AND** the page shows the error "Start year must not be later than end year"

#### Scenario: Result URL opened directly
- **GIVEN** the real daily file
- **WHEN** a user opens `GET /point/result?lon=-76.1390222&lat=-12.2935861&start_year=1981&end_year=2024`
- **THEN** the response status is 200 and the page shows the selected cell -76.15, -12.25

#### Scenario: Tampered result URL
- **WHEN** a user opens `GET /point/result?lon=abc&lat=-12.29&start_year=1981&end_year=1985`
- **THEN** the response status is 422
- **AND** the form page shows the error "Longitude must be a number" with latitude -12.29 kept

#### Scenario: Missing query parameter
- **WHEN** a user opens `GET /point/result?lon=-76.14&lat=-12.29&start_year=1981`
- **THEN** the response status is 422
- **AND** the page shows the error "End year must be an integer"

## MODIFIED Requirements

### Requirement: Point result summary
After a successful extraction the result page `GET /point/result` SHALL show, in its Summary
tab, the requested point, the selected cell center, the distance in km, the period, total days,
missing days and the mean annual rainfall.

#### Scenario: Summary values
- **GIVEN** a cell with 2 missing days in 1981
- **WHEN** a user requests years 1981 to 1981 for that cell
- **THEN** the Summary tab shows period 1981-01-01 to 1981-12-31, 365 total days and 2 missing days

#### Scenario: Reference summary
- **GIVEN** the real daily file
- **WHEN** a user requests longitude -76.1390222, latitude -12.2935861, years 1981 to 2024
- **THEN** the Summary tab shows cell -76.15, -12.25, distance 4.991 km, 16071 total days,
  0 missing days and mean annual rainfall 468.6 mm from 44 complete years

#### Scenario: Missing values displayed
- **GIVEN** 1981-01-03 is missing in the selected cell
- **WHEN** page 1 of the Daily tab is shown
- **THEN** the precipitation of 1981-01-03 is shown as "missing"

#### Scenario: No preview tables
- **WHEN** a successful result page is shown
- **THEN** the Summary tab contains no "First days" or "Last days" table

### Requirement: Cell without data
If every value of the selected cell is missing for the requested period, `GET /point/result`
SHALL respond 200 with the form page showing "No data available for this location" instead of
a result.

#### Scenario: Ocean cell
- **GIVEN** the cell nearest to longitude -80.05, latitude -15.05 has only missing values
- **WHEN** a user opens the result URL for that point and years 1981 to 1981
- **THEN** the response status is 200
- **AND** the page shows "No data available for this location"
- **AND** no tabs and no series rows are shown
