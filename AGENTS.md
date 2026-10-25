# AGENTS.md

Operating index for the agent. Details live in the linked files.

## Language
- Reply to the user in **Spanish**.
- Write everything else in **English**: files, folders, code, comments, docstrings,
  OpenSpec artifacts, ADRs and commit messages.

## Project
pisco-rain-extractor: web app to extract and analyze daily rainfall from the
SENAMHI PISCOp v3.0 gridded dataset (Peru).
Stack, architecture and constraints: `openspec/config.yaml` (`context` block).

## Map
| Path | Contents |
|---|---|
| `openspec/specs/` | Current system behavior (source of truth) |
| `openspec/changes/` | Changes in progress: proposal, specs, design, tasks |
| `adr/` | Architecture decisions (index in `adr/README.md`) |
| `app/routes/` | FastAPI routes (thin, no business logic) |
| `app/services/` | Business logic (no FastAPI imports) |
| `app/repositories/` | NetCDF access (the only code that reads `data/`) |
| `app/templates/`, `app/static/` | Jinja2 templates and plain CSS |
| `tests/` | pytest suite with synthetic NetCDF fixtures |
| `scripts/` | Verification utilities that read the real `data/` files through the repository; not part of the test suite |
| `data/` | Third-party PISCOp files (gitignored) |
| `BACKLOG.md` | Pending improvements and ideas, not yet planned (each becomes an OpenSpec change) |

## Commands
```bash
uv sync
uv run uvicorn app.main:app --reload
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
openspec validate --all
```

## SDD workflow (mandatory)
1. **Planning** (`/opsx:explore`, `/opsx:propose`, `/opsx:new`, `/opsx:continue`,
   `/opsx:ff`, `/opsx:update`): only write artifacts in `openspec/changes/`
   (and ADRs through `/adr`). Never edit application code.
2. **Implementation**: only inside `/opsx:apply`, with a reviewed `tasks.md`.
3. **Closing**: `/adr-review` → `/opsx:verify` with no CRITICAL issues → `/opsx:archive`.
- **Exception**: trivial fixes (lint, typo, broken test) of the active change during
  `/opsx:apply`. Outside a change, only when the user explicitly asks for a "quick fix".

## Data rules (hard)
- `data/` holds SENAMHI property: never commit, copy into `tests/` or redistribute it.
  Never change the `.gitignore` rules for `data/`.
- Never open `.nc` files with the Read tool; inspect them only with
  `uv run python` and xarray, lazily.
- Never load the full daily grid into memory.

## Git
- Apply the `git-discipline` skill in every phase.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`).
- Never commit or push without the user's confirmation. Never add `.env` or credentials.

## Definition of done (per task)
- The scenario behavior is implemented **and** covered by a test.
- `uv run pytest` and `uv run ruff check .` pass.
- The checkbox is marked `[x]` in `tasks.md`.

## Architecture decisions
- Before designing or implementing anything structural, read `adr/README.md`
  and the relevant accepted ADRs.
- An accepted ADR is never edited: replace it with `/adr-supersede`.
- If you detect a new structural decision without an ADR, propose `/adr <title>`.

## Essential conventions
- Type hints on every function; docstrings on public functions.
- Dependencies only through `uv add`, justified in `design.md`.
- No JS framework and no CDN.

## Lessons learned
<!-- One line per mistake the agent repeats. -->
- ruff excludes `openspec/`, `adr/` and `.claude/` (`extend-exclude` in `pyproject.toml`) because it also formats Python code blocks inside `.md` files, and the illustrative snippets in planning docs are not runnable code; do not remove the exclusion.
- `StarletteDeprecationWarning` inherits from `UserWarning`, not `DeprecationWarning`: `-W error::DeprecationWarning` does not catch it. Filter it by its own class, `-W error::starlette.exceptions.StarletteDeprecationWarning`.
- After updating xarray, netCDF4 or h5py (or anything that changes the bundled HDF5 library), rerun `uv run python scripts/check_basin_memory.py`: the basin peak (287 MB of a ~300 MB budget, ADR-0020) depends on how these libraries read and cache chunks, and ADR-0019 failed because HDF5 behaved differently than expected.
- `Rscript` (R 4.5.2 in `C:\Program Files\R\R-4.5.2\bin\`) crashes with a segmentation fault when launched from Git Bash. Run it through PowerShell with a script file: `powershell.exe -NoProfile -Command "& 'C:\Program Files\R\R-4.5.2\bin\Rscript.exe' check.R"`.
