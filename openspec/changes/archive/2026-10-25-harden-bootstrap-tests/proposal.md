# Proposal

## Why

The `/opsx:verify` report of the archived `bootstrap-app` left one warning and three
suggestions: an environment start date that is never tested end to end (W2), an untested
branch for files with real CF dates (S2), a `noqa` that a typed dependency would remove (S3),
and a rounding rule not explained where it lives (S1). Closing them now keeps the repository
layer trustworthy before point extraction builds on it.

## What Changes

- **W2:** add an end-to-end test that opens a 365-step daily file through
  `PiscoRepository.open` with `Settings(data_dir=..., daily_start_date=date(1982, 1, 1))` and
  expects `time_end == "1982-12-31"`.
- **S2:** add a test for the CF-dates branch of `_time_index`: a daily file whose time
  coordinate has `units: "days since 1981-01-01"` must take its dates from the file, not from
  settings. The fixture helper in `tests/conftest.py` gains optional time units and values.
- **S3:** in `app/routes/pages.py`, declare the dependency as
  `repo: Annotated[PiscoRepository, Depends(get_repository)]` and remove `# noqa: B008`.
- **S1:** make the comment in `_rounded` (`app/repositories/pisco_repository.py`) state that
  bounds are rounded to 4 decimals to remove float32 noise (a comment already exists; it does
  not name bounds).
- Add a "Lessons learned" line to `AGENTS.md`: `StarletteDeprecationWarning` inherits from
  `UserWarning`, so filter it as `starlette.exceptions.StarletteDeprecationWarning`, not as
  `DeprecationWarning`.
- No observable behavior change; `skip_specs: true`.

### Out of scope

- Any edit under `openspec/changes/archive/` (the archived `bootstrap-app` design stays as is).
- Changing `openspec/specs/` or any runtime behavior.
- Other refactors in routes, services or repositories.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- None (tests, comments and docs only; `skip_specs: true`).

## Decisions

- No new ADR: the changes follow ADR-0004 (layers), ADR-0005 (lazy reads) and ADR-0007
  (calendar; the CF-dates branch is already part of its decision).

## Impact

- `tests/conftest.py`, `tests/test_pisco_repository.py`, `app/routes/pages.py`,
  `app/repositories/pisco_repository.py` (comment only), `AGENTS.md`.
- No dependency changes.
