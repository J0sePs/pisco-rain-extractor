# Tasks

## 1. Baseline

- [ ] 1.1 Confirm the warning is caught before changing anything — verify: `uv run pytest -q -W error::starlette.exceptions.StarletteDeprecationWarning` fails during collection with "Using `httpx` with `starlette.testclient` is deprecated"

## 2. Dependencies

- [ ] 2.1 Add the new test client backend: `uv add --dev httpx2` — verify: `uv run python -c "import httpx2"` exits 0 and `pyproject.toml` lists `httpx2` under `[dependency-groups].dev`
- [ ] 2.2 Confirm no direct use of httpx, then remove it: `grep -rnE "^\s*(import|from) httpx\b" app tests` prints nothing, then `uv remove --dev httpx` — verify: `httpx` is no longer in `[dependency-groups].dev` and `uv tree --invert --package httpx` reports nothing

## 3. Project context

- [ ] 3.1 Approved by the user on 2026-10-24 (ADR-0009): change the Quality line in `openspec/config.yaml` from `pytest + httpx (FastAPI TestClient)` to `pytest + httpx2 (FastAPI TestClient)` — verify: `grep -n "Quality" openspec/config.yaml` shows `httpx2`

## 4. Integration verification

- [ ] 4.1 Requested check — verify: `uv run pytest -q -W error::DeprecationWarning` passes with no `StarletteDeprecationWarning` in the output
- [ ] 4.2 Real gate (D2) — verify: `uv run pytest -q -W error::starlette.exceptions.StarletteDeprecationWarning` passes (52 tests)
- [ ] 4.3 Quality gate — verify: `uv run ruff check .` and `uv run ruff format --check .` pass

## Workflow follow-up

- `/adr-review adopt-httpx2-test-client` → `/opsx:verify adopt-httpx2-test-client` → `/opsx:archive adopt-httpx2-test-client`.
