# Tasks

## 1. Test fixtures

- [x] 1.1 Add `time_units: str = "unknown"` and `time_start_value: int = 1` to `write_pisco_file` in `tests/conftest.py` (D1) — verify: `uv run pytest tests/test_fixtures.py -q` passes unchanged

## 2. Repository tests

- [x] 2.1 Add to `tests/test_pisco_repository.py` a test that writes only `PISCOp_d.nc` with 365 steps and opens it with `Settings(data_dir=..., daily_start_date=date(1982, 1, 1))`, expecting `time_start` 1982-01-01, `time_end` 1982-12-31 and no warnings (D2) — verify: `uv run pytest tests/test_pisco_repository.py -q` passes
- [x] 2.2 Add to `tests/test_pisco_repository.py` a test with `time_units="days since 1981-01-01"`, `time_start_value=0`, 365 steps and `daily_start_date=date(1990, 1, 1)`, expecting 1981-01-01 to 1981-12-31; plus a case with `time_start_value=1` expecting `time_start` 1981-01-02 (D3) — verify: `uv run pytest tests/test_pisco_repository.py -q` passes

## 3. Routes

- [x] 3.1 In `app/routes/pages.py`, add `RepositoryDep = Annotated[PiscoRepository, Depends(get_repository)]`, use it in `dataset` and remove `# noqa: B008` (D4) — verify: `grep -n "noqa" app/routes/pages.py` prints nothing and `uv run pytest tests/test_pages.py -q` passes

## 4. Comments and docs

- [x] 4.1 Update the comment in `_rounded` (`app/repositories/pisco_repository.py`) to state that bounds are rounded to 4 decimals to remove float32 noise (D5) — verify: `grep -n -A3 "def _rounded" app/repositories/pisco_repository.py` shows "bounds" and "float32"
- [x] 4.2 Add a "Lessons learned" line to `AGENTS.md`: `StarletteDeprecationWarning` inherits from `UserWarning`; filter it as `starlette.exceptions.StarletteDeprecationWarning`, not as `DeprecationWarning` — verify: `grep -n "StarletteDeprecationWarning" AGENTS.md` shows the line

## 5. Integration verification

- [x] 5.1 Quality gate — verify: `uv run pytest -q -W error::starlette.exceptions.StarletteDeprecationWarning`, `uv run ruff check .` and `uv run ruff format --check .` pass, and `git status --short openspec/changes/archive` prints nothing
- [x] 5.2 Manual check in the browser: `uv run uvicorn app.main:app --reload`, open http://127.0.0.1:8000/dataset — verify: the page renders the three files as before (this also closes W1 from the bootstrap-app verify report)

## Workflow follow-up

- `/adr-review harden-bootstrap-tests` → `/opsx:verify harden-bootstrap-tests` → `/opsx:archive harden-bootstrap-tests`.
