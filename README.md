# pisco-rain-extractor

Web app to extract and analyze daily rainfall from the SENAMHI **PISCOp v3.0** gridded
dataset (Peru, 0.1° grid, 1981–2025).

It runs locally as a small server-rendered app (FastAPI + Jinja2, no JavaScript). You point it
at the PISCOp NetCDF files on your machine and get the daily series of a point or the areal mean
of a basin. The app adds annual statistics, a monthly climatology, charts and files you can
open in R, Python or Excel.

## Features

- **Point extraction.** Enter a point in WGS84 decimal degrees, or convert it from UTM (zones
  17, 18 and 19, north or south). The app uses the nearest grid cell and reports its center
  and its distance to your point. Result URLs are stateless, so they can be bookmarked and
  shared.
- **Basin extraction.** Upload a basin as GeoJSON or as a zipped Shapefile (`.shp`, `.shx`,
  `.dbf`, `.prj`, up to 10 MB).
  - Files in another coordinate system are reprojected to WGS84, and several polygons are
    dissolved into one.
  - The basin value for each day is the arithmetic mean of the cells whose centers fall inside
    it. Cells without data are excluded and listed.
  - A basin too small to contain any cell center uses the cell nearest to its centroid.
  - Basin results are kept on the server for 24 hours.
- **Analysis tabs and charts.**
  - Summary, a paginated daily table, annual totals and 24 h maxima, and a monthly climatology
    with standard deviation.
  - Points add a location map, and basins add a Cells tab with a map of the polygon and the
    cells used.
  - A year or month counts as complete with at least 95% valid days. Only complete years enter
    the mean annual rainfall.
- **Exports.**
  - CSV files ready for `readr::read_csv` and `pandas.read_csv` with their default settings:
    UTF-8, comma separator, ISO dates, empty cells for missing values.
  - One Excel workbook with the same tables plus a metadata sheet (source, attribution,
    request, completeness rule).
- **Dataset page.** Shows which PISCOp files were found and their detected structure.

## Data (not included)

The PISCOp v3.0 files are property of SENAMHI and are **not** distributed with this repository.
Download them from the official
[figshare dataset](https://figshare.com/articles/dataset/High-resolution_grids_of_rainfall_for_Peru_-_PISCOp_v3_0_dataset/32411886)
and place them in `data/` as described in [data/README.md](data/README.md). The files are
`PISCOp_d.nc`, `PISCOp_m.nc` and `PISCOp_clim2.nc`. Cite PISCOp v3.0 as SENAMHI indicates on
that page.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/) to manage the environment and dependencies

## Installation

```bash
git clone https://github.com/J0sePs/pisco-rain-extractor.git
cd pisco-rain-extractor
uv sync
```

## Running the app

```bash
uv run uvicorn app.main:app --reload
```

Then open <http://127.0.0.1:8000>. The app starts without the data files. In that case the
dataset page reports them as unavailable.

Optional settings, as environment variables or in a `.env` file (which git ignores):

| Variable | Default | Purpose |
|---|---|---|
| `DATA_DIR` | `data` | Folder with the PISCOp files |
| `BASIN_STORE_DIR` | `uploads/basins` | Where basin results are kept (gitignored) |
| `BASIN_TTL_HOURS` | `24` | How long basin results are kept |
| `DAILY_START_DATE`, `MONTHLY_START_DATE` | `1981-01-01` | First date of the daily and monthly time index |

## Running the tests

```bash
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
```

The tests do not need the real data. They build small synthetic NetCDF files that mimic the
PISCOp structure. The scripts in `scripts/` run checks against the real files:

```bash
uv run python scripts/check_calendar_alignment.py   # daily vs monthly calendar
uv run python scripts/check_basin_memory.py         # peak memory of a basin at the size limit
```

## Validation

These checks were run on the real PISCOp v3.0 files during development.

- **Annual maxima.** For the point (-76.1390222, -12.2935861), the app selects the cell
  (-76.15, -12.25). Over 1981–2024 its annual 24 h maxima for 1981–1985, 1997 and 1998 match
  reference values obtained independently of this app within 0.001 mm (largest difference
  0.00047 mm), with no missing days. These values are part of the spec
  ([rainfall-analysis](openspec/specs/rainfall-analysis/spec.md)).
- **Calendar alignment.** The daily file has no calendar dates, only an index. For one cell,
  daily values summed per month were compared with `PISCOp_m.nc`, with the daily series shifted
  by −2 to +2 days. The mean absolute difference is smallest without a shift (about 0.24 mm,
  against about 1.25–1.28 mm for a one-day shift). `scripts/check_calendar_alignment.py`
  reproduces this check. It detects an offset between the two files, not a shift shared by
  both ([ADR-0007](adr/0007-derive-calendar-dates-from-the-pisco-time-index.md)).
- **Basin cells and area.** The reference basin was Cuenca Mala (ANA hydrographic unit, via
  MapBiomas Perú), not included in this repository.
  - The app selects 20 cell centers inside it, including (-76.15, -12.25). A separate check
    in R with `sf` gave the same cell count and confirmed that cell.
  - The app reports a geodesic area of 2332.9 km². The same polygon projected to UTM 18S
    measures 2332.1 km² (a 0.03% difference).
- **Memory.** A basin at the size limit (a 50 × 50-cell bounding box, 1981–2025) peaked at
  287 MB with `scripts/check_basin_memory.py`, against a target of about 300 MB
  ([ADR-0020](adr/0020-read-basin-bounding-boxes-in-chunk-aligned-tiles-through-the-shared-xarray-handle.md)).

## How it was built

The project was developed spec-driven with [OpenSpec](https://github.com/Fission-AI/OpenSpec).
Every feature started as a change proposal with specs, a design and a task list, and was
archived after implementation and verification.

- **Specs:** [openspec/specs/](openspec/specs/) describe the current behavior of each
  capability (dataset catalog, point extraction, basin extraction, rainfall analysis, data
  export, web shell). Each scenario has concrete values and is covered by tests.
- **Change history:** archived proposals, designs and tasks are in
  [openspec/changes/archive/](openspec/changes/archive/).
- **Architecture Decision Records:** [adr/](adr/) holds the structural decisions, indexed in
  [adr/README.md](adr/README.md). Examples are the layered architecture, lazy NetCDF reads,
  nearest-cell selection, the completeness rule, the export format and the basin areal mean.
  Superseded decisions are kept and linked to the ones that replaced them.

## Project structure

```
app/
  routes/         FastAPI routes: parse input, call services, render templates
  services/       Extraction, analysis, basins, charts, exports (no FastAPI imports)
  repositories/   The only code that opens the NetCDF files
  templates/      Jinja2 templates
  static/         Plain CSS
tests/            pytest suite with synthetic NetCDF fixtures
scripts/          Checks that run against the real data files
data/             PISCOp files (not versioned, see data/README.md)
openspec/         Specs and archived changes
adr/              Architecture Decision Records
```

## Roadmap

Pending improvements are listed in [BACKLOG.md](BACKLOG.md). They include friendlier point
form validation, an area-weighted basin mean, Mann-Kendall and Sen's slope trends, and
Gumbel/GEV return periods. None of these is implemented yet.

## License

The code is released under the [MIT License](LICENSE).

The license covers **only the code** in this repository. The PISCOp v3.0 data are property of
SENAMHI (Servicio Nacional de Meteorología e Hidrología del Perú). They are not included or
redistributed here, and their use follows SENAMHI's terms on the dataset page.
