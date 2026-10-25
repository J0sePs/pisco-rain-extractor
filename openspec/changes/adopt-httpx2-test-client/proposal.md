# Proposal

## Why

Starlette 1.10 (used by FastAPI's `TestClient`) now imports `httpx2` and falls back to `httpx`
with a `StarletteDeprecationWarning` on every test run. The fallback will eventually be removed,
which would break the whole test suite at once. Switching now removes the warning and the risk.

## What Changes

- Add `httpx2` as a dev dependency with `uv add --dev httpx2`.
- Remove `httpx` from the dev dependencies with `uv remove --dev httpx`: no test or app module
  imports `httpx` directly, and no other package depends on it (`uv tree --invert --package httpx`
  shows only the dev group).
- Verify that the suite runs with no `StarletteDeprecationWarning`.
- No application code, no test logic and no observable behavior change; `skip_specs: true`.

### Out of scope

- Changing any test, the `TestClient` usage or FastAPI/Starlette versions.
- Other warnings or deprecations.
- Editing `openspec/config.yaml` (the Quality line is updated only after explicit confirmation).

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- None (tooling only; `skip_specs: true`).

## Decisions

- The project stack in `openspec/config.yaml` lists "pytest + httpx (FastAPI TestClient)" and
  states that changing the stack requires an ADR. Replacing `httpx` with `httpx2` is a small,
  test-only change, but it alters that line: see ADR-0009: Use httpx2 for the FastAPI test
  client (Accepted).
- ADR-0002 mentions "httpx/TestClient" as a consequence; it is accepted and is not edited.

## Impact

- `pyproject.toml` (`[dependency-groups].dev`) and `uv.lock`.
- `openspec/config.yaml` context, Quality line (approved by the user; task 3.1).
- No change under `app/` or `tests/`.
