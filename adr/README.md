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
| [0007](0007-derive-calendar-dates-from-the-pisco-time-index.md) | Derive calendar dates from the PISCOp time index | Proposed | 2026-10-24 |
