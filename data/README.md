# Data

This folder is intentionally empty in the repository.

The PISCOp v3.0 files are **property of SENAMHI** (Servicio Nacional de Meteorología e
Hidrología del Perú). They are **not redistributed** here: never commit them, copy them
into `tests/` or share them. Git ignores everything in `data/` except this file and
`.gitkeep`.

## How to get the data

1. Open the official dataset page on figshare:
   <https://figshare.com/articles/dataset/High-resolution_grids_of_rainfall_for_Peru_-_PISCOp_v3_0_dataset/32411886>
2. Read the license and citation terms on that page.
3. Download the three NetCDF files below and place them **directly in this folder**
   with these exact names:

| File | Contents |
|---|---|
| `PISCOp_d.nc` | Daily rainfall (mm), 1981–2025, 0.10° grid |
| `PISCOp_m.nc` | Monthly rainfall (mm), 1981–2025, 0.10° grid |
| `PISCOp_clim2.nc` | Monthly climatology (normals 1991–2015, mm), 0.10° grid |

Expected layout:

```
data/
├── .gitkeep
├── README.md
├── PISCOp_d.nc
├── PISCOp_m.nc
└── PISCOp_clim2.nc
```

## Configuration

The app reads the files from `data/` by default. To use another location, set the
`DATA_DIR` environment variable (for example in `.env`, which is also gitignored).

## Notes

- The daily file is large; the app opens it lazily and never loads the full grid
  into memory.
- Tests do not need these files: they use small synthetic NetCDF fixtures built in
  `tests/conftest.py`.
- When publishing results, cite PISCOp v3.0 as indicated by SENAMHI on the dataset page.
