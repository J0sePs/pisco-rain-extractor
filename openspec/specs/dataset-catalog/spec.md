# dataset-catalog Specification

## Purpose

Makes the three PISCOp v3.0 NetCDF files available to the application at startup and lets
users see what each file contains (variables, grid, bounds, time range) and whether it is present.

## Requirements

### Requirement: Open dataset files at startup
On startup the system SHALL open `PISCOp_d.nc` (daily), `PISCOp_m.nc` (monthly) and
`PISCOp_clim2.nc` (climatology) from the configured data directory (`DATA_DIR`, default
`data/`) once, without loading their precipitation values into memory.

#### Scenario: All files present
- **GIVEN** `DATA_DIR` contains the three PISCOp files
- **WHEN** the application starts
- **THEN** the daily, monthly and climatology datasets are reported as available

#### Scenario: Custom data directory
- **GIVEN** `DATA_DIR` is set to a folder `/tmp/pisco` that contains the three files
- **WHEN** the application starts
- **THEN** the files are read from `/tmp/pisco` and reported as available

#### Scenario: Startup does not read precipitation values
- **GIVEN** a daily file of 16436 days on a 210 x 174 grid
- **WHEN** the application starts
- **THEN** no precipitation values are loaded into memory

### Requirement: Tolerate missing or unreadable files
The system SHALL start even if one or more dataset files are missing or unreadable, and
SHALL mark each such file as unavailable with the reason.

#### Scenario: Daily file missing
- **GIVEN** `DATA_DIR` contains only `PISCOp_m.nc` and `PISCOp_clim2.nc`
- **WHEN** the application starts
- **THEN** startup succeeds
- **AND** the daily dataset is marked unavailable with reason "file not found: PISCOp_d.nc"

#### Scenario: Corrupt file
- **GIVEN** `PISCOp_m.nc` is a text file that is not NetCDF
- **WHEN** the application starts
- **THEN** startup succeeds
- **AND** the monthly dataset is marked unavailable with a reason saying it could not be read

#### Scenario: Empty data directory
- **GIVEN** `DATA_DIR` exists but contains no files
- **WHEN** the application starts
- **THEN** startup succeeds and all three datasets are marked unavailable

### Requirement: Detect variable and coordinate names
The system SHALL detect, from each file's contents, the precipitation variable and the
latitude, longitude and time dimension names, instead of relying on fixed names.

#### Scenario: PISCOp naming
- **GIVEN** a file with variable `precipitation` on dimensions (`Z1`, `latitude`, `longitude`)
- **WHEN** the file is opened
- **THEN** the precipitation variable is `precipitation`, latitude is `latitude`,
  longitude is `longitude` and time is `Z1`

#### Scenario: Alternative naming
- **GIVEN** a file with variable `PISCOp_clim2` on dimensions (`month`, `lat`, `lon`)
- **WHEN** the file is opened
- **THEN** the precipitation variable is `PISCOp_clim2`, latitude is `lat`, longitude is
  `lon` and time is `month`

#### Scenario: No precipitation variable
- **GIVEN** a file whose only variables are coordinates and `crs`
- **WHEN** the file is opened
- **THEN** the dataset is marked unavailable with reason "no precipitation variable found"

### Requirement: Build calendar dates from the time index
The system SHALL assign ISO 8601 dates to the integer time index: one Gregorian day (with
leap years) per daily step from the daily start date, one month (first day) per monthly step
from the monthly start date, and calendar months 1–12 for the climatology. A length that does
not fit the expected range SHALL be reported.

#### Scenario: Full daily period
- **GIVEN** a daily file with 16436 time steps
- **WHEN** the file is opened
- **THEN** the time range is 1981-01-01 to 2025-12-31

#### Scenario: Leap days are counted
- **GIVEN** a daily file with 16425 time steps (45 x 365, as in a no-leap calendar)
- **WHEN** the file is opened
- **THEN** the time range is 1981-01-01 to 2025-12-20, not 2025-12-31

#### Scenario: Monthly period
- **GIVEN** a monthly file with 540 time steps
- **WHEN** the file is opened
- **THEN** the time range is 1981-01-01 to 2025-12-01

#### Scenario: Climatology months
- **GIVEN** a climatology file with 12 time steps
- **WHEN** the file is opened
- **THEN** the time range is reported as months 1 to 12

#### Scenario: Unexpected climatology length
- **GIVEN** a climatology file with 13 time steps
- **WHEN** the file is opened
- **THEN** the dataset is marked unavailable with a reason stating 12 steps were expected and 13 were found

### Requirement: Cross-check daily and monthly periods
At startup the system SHALL compare the last month derived from the daily file with the last
month of the monthly file. If they differ, both files SHALL be flagged with a warning that
names both months; startup SHALL continue and both files SHALL stay available.

#### Scenario: Periods agree
- **GIVEN** a daily file with 16436 steps and a monthly file with 540 steps
- **WHEN** the application starts
- **THEN** the daily last month is 2025-12, the monthly last month is 2025-12
- **AND** no period warning is attached to either file

#### Scenario: Periods disagree
- **GIVEN** a daily file with 16436 steps (last month 2025-12) and a monthly file with
  528 steps (last month 2024-12)
- **WHEN** the application starts
- **THEN** startup succeeds and both files are still available
- **AND** both files carry the warning "Period mismatch: daily file ends in 2025-12, monthly
  file ends in 2024-12"

#### Scenario: Daily file ends mid-month
- **GIVEN** a daily file with 16426 steps (last day 2025-12-21) and a monthly file with
  540 steps (last month 2025-12)
- **WHEN** the application starts
- **THEN** no period warning is attached to either file, because both end in 2025-12

#### Scenario: Monthly file missing
- **GIVEN** the daily file is present and the monthly file is missing
- **WHEN** the application starts
- **THEN** no period warning is attached to the daily file

### Requirement: Latitude order independence
The system SHALL report bounds and select latitude ranges correctly whether a file stores
latitudes in descending order (north to south, as PISCOp v3.0) or ascending order, and SHALL
keep grid rows whose stored coordinate differs from a requested bound by at most 1e-6 degrees.

#### Scenario: Descending latitude bounds
- **GIVEN** a file with latitudes stored from 1.95 down to -18.95 in steps of 0.1
- **WHEN** the file is opened
- **THEN** its bounds are latitude -18.95 to 1.95 and its resolution is 0.1°

#### Scenario: Ascending latitude bounds
- **GIVEN** the same grid with latitudes stored from -18.95 up to 1.95
- **WHEN** the file is opened
- **THEN** its reported bounds and resolution are identical to the descending case

#### Scenario: Latitude range on a descending grid
- **GIVEN** latitudes 1.95, 1.85, ..., -18.95 and a requested range from south -1.05 to north 0.95
- **WHEN** the latitude rows in that range are selected
- **THEN** 21 rows are selected, from 0.95 down to -1.05, not zero

#### Scenario: Border stored as float32
- **GIVEN** float32 latitudes on a descending grid where the southern border row is stored as
  -1.05000007 (the float32 value just beyond -1.05)
- **WHEN** the range from south -1.05 to north 0.95 is selected
- **THEN** 21 rows are selected, including the border row

#### Scenario: Range outside the grid
- **GIVEN** latitudes from 1.95 down to -18.95
- **WHEN** the range from south 5.0 to north 6.0 is selected
- **THEN** no rows are selected

### Requirement: Grids described per file
The system SHALL describe each file's grid independently and SHALL NOT assume that the daily,
monthly and climatology grids are identical.

#### Scenario: Climatology with a different grid
- **GIVEN** a daily file of 210 x 174 cells (longitude -81.35 to -64.05) and a climatology file
  of 210 x 180 cells (longitude -81.95 to -64.05)
- **WHEN** a user opens `GET /dataset`
- **THEN** each file shows its own grid size and bounds
- **AND** no warning is raised for the difference between the grids

### Requirement: Climatology is catalog-only
The climatology file SHALL be listed on `/dataset` with its metadata only; its precipitation
values SHALL NOT be available to analysis features.

#### Scenario: Climatology data access refused
- **GIVEN** the climatology file is available
- **WHEN** any feature requests its precipitation data from the repository
- **THEN** the request is rejected with the message "climatology is catalog-only"
- **AND** its metadata is still listed on `/dataset`

### Requirement: Configurable calendar start dates
The start dates used to build the daily and monthly calendars SHALL come from the application
settings (defaults 1981-01-01 for both) and SHALL be overridable through environment variables.

#### Scenario: Default start dates
- **GIVEN** no calendar environment variables are set
- **WHEN** a daily file with 16436 steps is opened
- **THEN** its time range is 1981-01-01 to 2025-12-31

#### Scenario: Overridden daily start date
- **GIVEN** `DAILY_START_DATE=1982-01-01`
- **WHEN** a daily file with 365 steps is opened
- **THEN** its time range is 1982-01-01 to 1982-12-31

#### Scenario: Invalid start date
- **GIVEN** `DAILY_START_DATE=1981-13-01`
- **WHEN** the settings are loaded
- **THEN** loading fails with a validation error that names `daily_start_date`

### Requirement: Dataset information page
`GET /dataset` SHALL respond 200 with, for each of the three files: file name, availability,
variables with units, grid size (lat x lon), latitude and longitude bounds, grid
resolution in degrees, and time range.

#### Scenario: Daily file details
- **GIVEN** the daily file is available with 210 latitudes from 1.95 to -18.95 and
  174 longitudes from -81.35 to -64.05
- **WHEN** a user opens `GET /dataset`
- **THEN** the page shows `PISCOp_d.nc`, variable `precipitation` in `mm`, grid 210 x 174,
  latitude -18.95 to 1.95, longitude -81.35 to -64.05, resolution 0.1° and
  period 1981-01-01 to 2025-12-31

#### Scenario: Variable without units
- **GIVEN** the climatology variable has no `units` attribute
- **WHEN** a user opens `GET /dataset`
- **THEN** the units are shown as "not provided"

### Requirement: Warn about unavailable files
`GET /dataset` SHALL show a clearly visible warning for each unavailable file, with its
reason and a pointer to `data/README.md`, and SHALL still respond 200.

#### Scenario: Missing daily file
- **GIVEN** the daily file is missing
- **WHEN** a user opens `GET /dataset`
- **THEN** the response status is 200
- **AND** the page shows a warning "PISCOp_d.nc is not available: file not found" that
  refers to `data/README.md`
- **AND** the monthly and climatology details are still shown

#### Scenario: Period mismatch warning
- **GIVEN** the daily file ends in 2025-12 and the monthly file ends in 2024-12
- **WHEN** a user opens `GET /dataset`
- **THEN** the response status is 200
- **AND** the sections of `PISCOp_d.nc` and `PISCOp_m.nc` both show the period mismatch
  warning and still show their details
