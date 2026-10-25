# Spec Delta

## Purpose

Lets users upload a basin boundary and get the areal mean daily rainfall of the PISCOp cells
inside it, with the same analysis as a point plus the list and map of the cells used.

Scenarios use the reference test grid: daily cell centers at latitude -12.05 to -12.45 and
longitude -76.35 to -76.05 every 0.1° (edges: longitude -76.4 to -76.0, latitude -12.5 to
-12.0), rainfall `(day index % 7) * 1.5` mm from 1981-01-01 in every cell, cell (-76.15, -12.25)
missing on 1981-01-03 and 1981-06-01, and cell (-76.35, -12.45) missing on every day.
"Rectangle (W, S, E, N)" is a one-feature WGS84 GeoJSON polygon with those bounds.

## ADDED Requirements

### Requirement: Basin request form
`GET /basin` SHALL show a form with a file input and the start and end year inputs, prefilled
with the same default years as the point form. When the daily file is unavailable it SHALL show
the same unavailable message as the point form and no form.

#### Scenario: Default years
- **GIVEN** a daily file covering 1981-01-01 to 2025-12-31
- **WHEN** a user opens `GET /basin`
- **THEN** the response is 200 with a `multipart/form-data` form posting to `/basin`
- **AND** a file input named `basin_file`, and year inputs prefilled with 1981 and 2025

#### Scenario: Daily file unavailable
- **GIVEN** `DATA_DIR` has no daily file
- **WHEN** a user opens `GET /basin`
- **THEN** the page says "Daily data is not available" and contains no form

### Requirement: Supported file types
The system SHALL accept a GeoJSON file (`.geojson` or `.json`) or a ZIP archive (`.zip`)
containing one Shapefile, identified by the file name extension, case-insensitive. Any other
type SHALL be rejected with status 422 and a message naming the accepted types.

#### Scenario: GeoJSON accepted
- **WHEN** a user posts Rectangle (-76.30, -12.40, -76.10, -12.20) as `basin.GeoJSON` for 1981 to 1985
- **THEN** the response is a 303 redirect to a basin result URL

#### Scenario: Zipped Shapefile accepted
- **WHEN** a user posts a `.zip` with `basin.shp`, `basin.shx`, `basin.dbf` and `basin.prj`
  (EPSG:4326) of the same rectangle
- **THEN** the response is a 303 redirect and the result selects the same 4 cells

#### Scenario: Unsupported type
- **WHEN** a user posts `basin.kml`
- **THEN** the response is 422 and the form shows "Unsupported file type: upload a GeoJSON
  (.geojson, .json) or a zipped Shapefile (.zip)"

#### Scenario: No file chosen
- **WHEN** a user posts the form without a file
- **THEN** the response is 422 with "Choose a basin file to upload"

### Requirement: Upload size limit
The system SHALL reject an uploaded file larger than 10 MB (10,485,760 bytes) with status 422,
without parsing it.

#### Scenario: File over the limit
- **WHEN** a user posts a `.geojson` of 10,485,761 bytes
- **THEN** the response is 422 with "The file is larger than 10 MB"

#### Scenario: File at the limit
- **WHEN** a user posts a valid `.geojson` of exactly 10,485,760 bytes (padded with spaces)
- **THEN** the size check passes

### Requirement: Shapefile components
A ZIP archive SHALL contain exactly one `.shp` file together with `.shx`, `.dbf` and `.prj`
files of the same name. A missing `.prj` SHALL get its own message because the coordinate
system is then unknown. Archive members with absolute paths or `..` SHALL be rejected.

#### Scenario: Missing projection file
- **WHEN** a user posts a `.zip` with `basin.shp`, `basin.shx` and `basin.dbf` only
- **THEN** the response is 422 with "The Shapefile has no .prj file, so its coordinate system
  is unknown. Include the .prj file in the ZIP."

#### Scenario: Missing attribute file
- **WHEN** a user posts a `.zip` with `basin.shp`, `basin.shx` and `basin.prj`
- **THEN** the response is 422 with "The ZIP must contain .shp, .shx, .dbf and .prj files
  (missing: .dbf)"

#### Scenario: Two Shapefiles
- **WHEN** a user posts a `.zip` with `a.shp` and `b.shp` and their companion files
- **THEN** the response is 422 with "The ZIP must contain exactly one Shapefile"

#### Scenario: Unsafe member path
- **WHEN** a user posts a `.zip` whose member is named `../basin.shp`
- **THEN** the response is 422 with "The ZIP contains an invalid file path"

### Requirement: Reprojection to WGS84
The system SHALL reproject a Shapefile to WGS84 (EPSG:4326) using its `.prj`. A GeoJSON file
SHALL be read as WGS84 unless it declares another coordinate system, which SHALL then be
reprojected.

#### Scenario: Shapefile in UTM zone 18 South
- **GIVEN** the Rectangle (-76.30, -12.40, -76.10, -12.20) projected to EPSG:32718 and saved as
  a zipped Shapefile with its `.prj`
- **WHEN** a user posts it for 1981 to 1985
- **THEN** the result selects the same 4 cells as the WGS84 GeoJSON of that rectangle

#### Scenario: Unreadable projection
- **WHEN** the `.prj` of a zipped Shapefile contains `not a projection`
- **THEN** the response is 422 with "The .prj file does not describe a known coordinate system"

### Requirement: Basin geometry validation
The basin SHALL be made of polygons or multipolygons. A file with no polygon, with an empty
geometry, or that cannot be read SHALL be rejected with 422; an invalid geometry (for example
self-intersecting) SHALL be rejected with a message that starts with "The basin geometry is
invalid" and is not repaired.

#### Scenario: No features
- **WHEN** a user posts a GeoJSON `FeatureCollection` with no features
- **THEN** the response is 422 with "The file contains no polygon"

#### Scenario: Only lines
- **WHEN** a user posts a GeoJSON with one `LineString` feature
- **THEN** the response is 422 with "The basin must be a polygon or multipolygon"

#### Scenario: Self-intersecting polygon
- **WHEN** a user posts a "bow-tie" polygon (-76.3 -12.4, -76.1 -12.2, -76.1 -12.4, -76.3 -12.2,
  -76.3 -12.4)
- **THEN** the response is 422 and the message starts with "The basin geometry is invalid"

#### Scenario: Not a geographic file
- **WHEN** a user posts `basin.geojson` containing the text `hello`
- **THEN** the response is 422 with "The file could not be read as GeoJSON"

### Requirement: Dissolve several features
When the file has more than one polygon feature, the system SHALL dissolve them into one
geometry and SHALL tell the user on the result page how many features were dissolved.

#### Scenario: Two adjacent features
- **GIVEN** two features, Rectangle (-76.30, -12.40, -76.20, -12.20) and Rectangle
  (-76.20, -12.40, -76.10, -12.20)
- **WHEN** a user posts them for 1981 to 1985
- **THEN** the result selects the same 4 cells as Rectangle (-76.30, -12.40, -76.10, -12.20)
- **AND** the Summary says "2 features were dissolved into one basin"

#### Scenario: One feature
- **WHEN** a user posts Rectangle (-76.30, -12.40, -76.10, -12.20) as one feature
- **THEN** the result page has no dissolve notice

### Requirement: Basin period validation
The start and end years SHALL be validated with the same rules and messages as the point form,
and the file SHALL NOT be parsed when the years are invalid.

#### Scenario: Start after end
- **WHEN** a user posts a valid basin with start year 1985 and end year 1981
- **THEN** the response is 422 with "Start year must not be later than end year"

#### Scenario: Year outside the data
- **WHEN** a user posts a valid basin with years 1980 to 1985 on a file covering 1981 to 2025
- **THEN** the response is 422 with "Years must be between 1981 and 2025"

### Requirement: Basin inside the grid
A basin SHALL be rejected with 422 when it does not intersect the grid domain (outer cell
edges, ADR-0011). A basin that only partly overlaps the grid SHALL be accepted and SHALL use
the cells of the overlapping part.

#### Scenario: Basin outside the grid
- **WHEN** a user posts Rectangle (-70.50, -10.50, -70.00, -10.00)
- **THEN** the response is 422 with "The basin is outside the PISCOp grid (longitude -76.4 to
  -76.0, latitude -12.5 to -12.0)"

#### Scenario: Basin partly outside the grid
- **WHEN** a user posts Rectangle (-76.10, -12.30, -75.80, -12.10)
- **THEN** the result selects the 2 cells (-76.05, -12.15) and (-76.05, -12.25)

### Requirement: Maximum basin size
The system SHALL reject a basin whose bounding box covers more than 2500 grid cells, counted as
the grid rows and columns whose centers lie within the basin bounds, with 422 and the counted
size, before reading any precipitation value.

#### Scenario: Bounding box over the limit
- **GIVEN** a daily grid of 60 × 60 cells
- **WHEN** a user posts a basin whose bounds contain 51 rows and 50 columns of centers
- **THEN** the response is 422 with "The basin is too large: its bounding box covers 2550 grid
  cells (maximum 2500)"
- **AND** no precipitation value is read

#### Scenario: Bounding box at the limit
- **GIVEN** the same grid
- **WHEN** a user posts a basin whose bounds contain 50 rows and 50 columns of centers
- **THEN** the response is a 303 redirect

### Requirement: Cells inside the basin
The system SHALL select the cells whose centers, rounded to 4 decimals, lie inside the basin
or on its boundary.

#### Scenario: Four centers inside
- **WHEN** a user posts Rectangle (-76.30, -12.40, -76.10, -12.20)
- **THEN** the selected cells are (-76.25, -12.25), (-76.15, -12.25), (-76.25, -12.35) and
  (-76.15, -12.35)

#### Scenario: Centers on the boundary
- **WHEN** a user posts Rectangle (-76.25, -12.35, -76.05, -12.15)
- **THEN** 9 cells are selected, longitudes -76.25, -76.15, -76.05 and latitudes -12.35,
  -12.25, -12.15

### Requirement: Centroid fallback for small basins
When no cell center lies inside the basin, the system SHALL use the cell nearest to the basin
centroid, computed in the UTM zone (southern hemisphere) of the basin, with the tie rule of
ADR-0011, and SHALL show a warning. A centroid outside the grid domain SHALL be rejected as a
basin outside the grid.

#### Scenario: Small basin
- **WHEN** a user posts Rectangle (-76.14, -12.24, -76.12, -12.22)
- **THEN** the single selected cell is (-76.15, -12.25)
- **AND** the result page warns "No cell center falls inside the basin; the cell nearest to its
  centroid was used"

#### Scenario: Centroid on a cell edge
- **WHEN** a user posts Rectangle (-76.105, -12.305, -76.095, -12.295), centroid (-76.10, -12.30)
- **THEN** the selected cell is (-76.05, -12.25), the northern and eastern cell

#### Scenario: Centroid outside the grid
- **WHEN** a user posts Rectangle (-76.02, -12.04, -75.90, -11.90)
- **THEN** the response is 422 with "The basin is outside the PISCOp grid (longitude -76.4 to
  -76.0, latitude -12.5 to -12.0)"

### Requirement: Bounding-box read only
Basin extraction SHALL read precipitation only for the grid rows and columns of the basin
bounding box and the requested period, never the full grid.

#### Scenario: Reads limited to the bounding box
- **WHEN** a user posts Rectangle (-76.30, -12.40, -76.10, -12.20) for 1981 to 1985
- **THEN** every precipitation read covers at most 2 latitude rows and 2 longitude columns
- **AND** the reads together cover only the days of 1981 to 1985

#### Scenario: Fallback reads one cell
- **WHEN** a user posts Rectangle (-76.14, -12.24, -76.12, -12.22)
- **THEN** every precipitation read covers 1 row and 1 column

### Requirement: Daily areal mean
For each day the basin value SHALL be the arithmetic mean of the selected cells that have a
valid value that day. A day SHALL be missing only when no selected cell has a value.

#### Scenario: Mean of valid cells
- **GIVEN** on 1981-01-01 the selected cells hold 2.0, 4.0, missing and 6.0 mm
- **WHEN** the areal mean is computed
- **THEN** the 1981-01-01 value is 4.0 mm

#### Scenario: One cell missing on a day
- **WHEN** a user posts Rectangle (-76.30, -12.40, -76.10, -12.20) for 1981 to 1981
- **THEN** the 1981-01-03 value is 3.0 mm, not missing
- **AND** the Annual row of 1981 is total 1638.0 mm, maximum 9.0 mm, 365 valid days, Complete

#### Scenario: Every cell missing on a day
- **GIVEN** every selected cell is missing on 1981-02-01
- **WHEN** the areal mean is computed
- **THEN** 1981-02-01 is missing and counts as a missing day

### Requirement: Cells without data excluded
A selected cell with no valid value in the requested period SHALL be excluded from the mean and
listed as excluded. When every selected cell is excluded, the system SHALL show "No data
available for this basin" on the form page and store no result.

#### Scenario: Ocean cell excluded
- **WHEN** a user posts Rectangle (-76.40, -12.50, -76.20, -12.30) for 1981 to 1985
- **THEN** 3 cells are used and 1 is excluded, (-76.35, -12.45)

#### Scenario: All cells without data
- **WHEN** a user posts Rectangle (-76.40, -12.50, -76.30, -12.40)
- **THEN** the form page shows "No data available for this basin" with status 200
- **AND** no result is stored

### Requirement: Basin result URL
A valid basin request SHALL be answered with a 303 redirect to `/basin/result/<id>`, where `<id>`
is the 32-character lowercase hexadecimal form of a random version-4 UUID. Opening that URL
SHALL show the result without reading precipitation.

#### Scenario: Redirect and result
- **WHEN** a user posts Rectangle (-76.30, -12.40, -76.10, -12.20) for 1981 to 1985
- **THEN** the response is 303 with `Location` matching
  `^/basin/result/[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$`
- **AND** `GET` on that location is 200 and performs no precipitation read

#### Scenario: Two requests, two ids
- **WHEN** a user posts the same basin twice
- **THEN** the two `Location` ids differ

### Requirement: Result id validation
Every basin result, chart and download URL SHALL accept the id only when it is the 32-character
lowercase hexadecimal form of a version-4 UUID, checked before any file path is built. Any other
value SHALL return 404 with no file-system call on the result store or on any path derived from the id. Unrelated I/O, such as the
template engine checking its own template files, is outside this rule.

#### Scenario: Path traversal attempt
- **WHEN** a user opens `/basin/result/..%2F..%2Fpyproject.toml`, or the result store is asked
  to load the id `../../pyproject.toml`
- **THEN** the response is 404 (the load returns nothing)
- **AND** no file-system call (stat, open, list or delete) is made on the result store or on any path derived from the id

#### Scenario: Malformed id
- **WHEN** a user opens `/basin/result/<id>` with `<id>` equal to `not-a-uuid`, to
  `3F2B8C1E9D4A4B7C8E6F1A2B3C4D5E6F` (uppercase), to
  `3f2b8c1e-9d4a-4b7c-8e6f-1a2b3c4d5e6f` (hyphenated) or to
  `0123456789abcdef0123456789abcdef` (not version 4)
- **THEN** the response is 404 with "This result has expired; upload the basin again"
- **AND** no file-system call is made on the result store or on any path derived from the id

#### Scenario: Malformed id on a chart or download
- **WHEN** a user requests `/basin/result/not-a-uuid/chart/daily.png` or
  `/basin/result/not-a-uuid/export.xlsx`
- **THEN** the response is 404 with no file and no file-system call on the result store or on any path derived from the id

### Requirement: Expired or unknown result
Opening the result page of a well-formed id that is unknown or expired SHALL return 404 with a
page that says "This result has expired; upload the basin again" and links to `/basin`.

#### Scenario: Unknown id
- **WHEN** a user opens `/basin/result/3f2b8c1e9d4a4b7c8e6f1a2b3c4d5e6f`, which was never created
- **THEN** the response is 404 and the page says "This result has expired; upload the basin
  again"
- **AND** the page contains a link to `/basin`

#### Scenario: Expired id
- **GIVEN** a stored result whose file was written 25 hours ago
- **WHEN** a user opens its result URL
- **THEN** the response is 404 with "This result has expired; upload the basin again" and a link
  to `/basin`
- **AND** the stored file is deleted

### Requirement: Result storage and expiry
The system SHALL store each basin result in a configurable directory that is excluded from git,
SHALL NOT store the uploaded file, and SHALL delete results older than 24 hours at startup and
before storing a new result.

#### Scenario: Only the result is stored
- **WHEN** a user posts a zipped Shapefile basin
- **THEN** the store directory gains exactly one file, and no `.zip`, `.shp` or `.geojson`
  file is left in it or in the system temporary directory

#### Scenario: Expired result removed
- **GIVEN** a stored result created 25 hours ago
- **WHEN** a user posts a new valid basin
- **THEN** the old result is deleted and its URL returns 404 with "This result has expired;
  upload the basin again"

#### Scenario: Recent result kept
- **GIVEN** a stored result created 23 hours ago
- **WHEN** a user opens its URL
- **THEN** the response is 200

### Requirement: Basin result tabs
The basin result page SHALL group its content in five tabs, Summary, Daily, Annual,
Climatology and Cells, switched with links and CSS only, with the Daily, Annual and Climatology
content and rules of a point result applied to the areal series. It SHALL NOT include
JavaScript.

#### Scenario: Tabs present
- **WHEN** a user opens a basin result
- **THEN** the page has links to `#summary`, `#daily`, `#annual`, `#climatology` and `#cells`
  and one section with each of those ids
- **AND** no `<script>` element

#### Scenario: Daily pagination
- **WHEN** a user opens a basin result for 1981 to 1985 with `?page=2`
- **THEN** the Daily table shows page 2 of 6, starting on 1982-01-01

### Requirement: Basin summary
The Summary tab SHALL show the basin area in km² (geodesic area on the WGS84 ellipsoid, one
decimal), the number of cells used and excluded, the period, the total and missing days and
the mean annual rainfall, plus the dissolve notice and the fallback warning when they apply.

#### Scenario: Reference summary
- **WHEN** a user opens the result of Rectangle (-76.40, -12.50, -76.20, -12.30) for 1981 to 1985
- **THEN** the Summary shows "481.2 km²", "3 cells used" and "1 cell excluded (no data)"
- **AND** the period 1981-01-01 to 1985-12-31 and 1826 total days

### Requirement: Cells tab
The Cells tab SHALL list every selected cell with its center longitude and latitude and its
status, "Used" or "Excluded (no data)", and SHALL show a map of the basin polygon with the
selected cell centers and edges on longitude/latitude axes.

#### Scenario: Cell table
- **WHEN** a user opens the result of Rectangle (-76.40, -12.50, -76.20, -12.30)
- **THEN** the Cells table has 4 rows and the row of (-76.35, -12.45) says "Excluded (no data)"

#### Scenario: Map image
- **WHEN** a user requests `/basin/result/<id>/chart/cells.png`
- **THEN** the response is 200 with content type `image/png`
- **AND** the map draws the basin outline, used and excluded cells with their own legend
  entries, and axes labeled "Longitude (°)" and "Latitude (°)"

### Requirement: Basin charts
`GET /basin/result/<id>/chart/<kind>.png` SHALL return a PNG for kinds `daily`,
`annual-totals`, `annual-maxima`, `climatology` and `cells`, drawn like the point charts, without
reading precipitation. An unknown kind or id SHALL return 404.

#### Scenario: Chart image
- **WHEN** a user requests `/basin/result/<id>/chart/annual-maxima.png` for a stored result
- **THEN** the response is 200 with `image/png` and no precipitation read

#### Scenario: Unknown chart or id
- **WHEN** a user requests `/basin/result/<id>/chart/location.png`, or a chart of an unknown id
- **THEN** the response is 404
