# Architecture Decision Records

Structural decisions of pisco-rain-extractor. Accepted ADRs take precedence over
`openspec/config.yaml` and over any `design.md`.

- New decision: `/adr <title>`
- Replace an accepted decision: `/adr-supersede <number> <new title>`
- Check compliance (read-only): `/adr-review [change]`
- Template: [0000-template.md](0000-template.md)

Rules: accepted ADRs are never edited (only their status line when superseded);
numbers are never reused; this index is updated in the same commit as the ADR.

## Index

| ADR | Title | Status | Date |
|---|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted | 2026-10-24 |
| [0002](0002-use-fastapi-with-server-rendered-jinja2-templates.md) | Use FastAPI with server-rendered Jinja2 templates | Accepted | 2026-10-24 |
| [0003](0003-use-uv-as-the-python-package-manager.md) | Use uv as the Python package manager | Accepted | 2026-10-24 |
| [0004](0004-adopt-a-layered-architecture-with-a-netcdf-repository.md) | Adopt a layered architecture with a NetCDF repository | Accepted | 2026-10-24 |
| [0005](0005-read-netcdf-files-lazily-with-xarray.md) | Read NetCDF files lazily with xarray | Accepted | 2026-10-24 |
| [0006](0006-use-the-nearest-grid-cell-for-point-extraction.md) | Use the nearest grid cell for point extraction | Accepted | 2026-10-24 |
| [0007](0007-derive-calendar-dates-from-the-pisco-time-index.md) | Derive calendar dates from the PISCOp time index | Accepted | 2026-10-24 |
| [0008](0008-catalog-the-pisco-climatology-file-without-using-it-for-analysis.md) | Catalog the PISCOp climatology file without using it for analysis | Accepted | 2026-10-24 |
| [0009](0009-use-httpx2-for-the-fastapi-test-client.md) | Use httpx2 for the FastAPI test client | Accepted | 2026-10-24 |
| [0010](0010-select-latitude-ranges-through-an-order-aware-helper-with-float-tolerance.md) | Select latitude ranges through an order-aware helper with float tolerance | Accepted | 2026-10-24 |
| [0011](0011-define-the-point-validity-domain-as-the-grid-cell-edges.md) | Define the point validity domain as the grid cell edges | Accepted | 2026-10-25 |
| [0012](0012-use-a-95-percent-valid-day-threshold-for-complete-years-and-months.md) | Use a 95% valid-day threshold for complete years and months | Accepted | 2026-10-25 |
| [0013](0013-serve-point-results-and-charts-from-stateless-get-urls-that-re-read-the-cell.md) | Serve point results and charts from stateless GET URLs that re-read the cell | Accepted | 2026-10-25 |
| [0014](0014-define-the-tabular-export-format-for-csv-and-xlsx.md) | Define the tabular export format for CSV and XLSX | Accepted | 2026-10-25 |
| [0015](0015-store-basin-results-server-side-under-a-random-id-with-a-24-hour-expiry.md) | Store basin results server-side under a random id with a 24-hour expiry | Superseded by [ADR-0018](0018-store-basin-results-server-side-under-a-uuid-validated-id-with-a-24-hour-expiry.md) | 2026-10-25 |
| [0016](0016-compute-the-basin-areal-mean-as-the-arithmetic-mean-of-valid-cells-whose-centers-fall-inside.md) | Compute the basin areal mean as the arithmetic mean of valid cells whose centers fall inside | Accepted | 2026-10-25 |
| [0017](0017-read-basin-bounding-boxes-in-time-blocks-with-a-2500-cell-limit.md) | Read basin bounding boxes in time blocks with a 2500-cell limit | Superseded by [ADR-0019](0019-read-basin-bounding-boxes-in-chunk-aligned-tiles-with-no-chunk-cache-and-a-2500-cell-limit.md) | 2026-10-25 |
| [0018](0018-store-basin-results-server-side-under-a-uuid-validated-id-with-a-24-hour-expiry.md) | Store basin results server-side under a UUID-validated id with a 24-hour expiry | Accepted | 2026-10-25 |
| [0019](0019-read-basin-bounding-boxes-in-chunk-aligned-tiles-with-no-chunk-cache-and-a-2500-cell-limit.md) | Read basin bounding boxes in chunk-aligned tiles with no chunk cache and a 2500-cell limit | Accepted | 2026-10-25 |
