# Design

## Context

See `proposal.md` (Why). Observed in the current code:

- `tests/conftest.py:57` writes the time coordinate with fixed values `1..N` and
  `units: "unknown"`; there is no way to build a file with CF dates.
- `_time_index` (`app/repositories/pisco_repository.py:167-174`) decodes the time coordinate
  with `xr.decode_cf` when its `units` contain `" since "` (not for the climatology), and
  otherwise calls `build_time_index` with the start date from settings.
- CF offsets are counted from the reference date: with `units: "days since 1981-01-01"`,
  value `1` decodes to **1981-01-02** and value `0` to 1981-01-01 (checked with xarray).
- `_rounded` (line 177) already has a comment on float32 noise; it does not mention bounds.
- `app/routes/pages.py:30` uses `Depends(get_repository)` as a default value with `# noqa: B008`.

Follows ADR-0004, ADR-0005 and ADR-0007; no decision changes.

## Goals / Non-Goals

**Goals:**
- Cover the settings → repository path for a custom start date, and the CF-dates branch.
- Remove the `noqa` with the idiomatic FastAPI form.

**Non-Goals:**
- New behavior, new specs, or edits to the archived change.

## Decisions

### D1. Fixture helper gains optional time encoding
`write_pisco_file` gets two keyword arguments: `time_units: str = "unknown"` and
`time_start_value: int = 1`. Defaults keep every existing fixture identical (integer `Z1`
from 1, `units: "unknown"`), so `tests/test_fixtures.py` still holds.
Rejected: a separate CF fixture function – duplicates the whole file layout.

### D2. W2 test isolates the daily file
The test writes only `PISCOp_d.nc` (365 steps) in its own directory, so the daily/monthly
cross-check is skipped and no unrelated warning appears. It opens the repository with
`Settings(data_dir=..., daily_start_date=date(1982, 1, 1))` and asserts
`time_start == "1982-01-01"`, `time_end == "1982-12-31"` and `warnings == []`.
Rejected: setting `DAILY_START_DATE` through the environment – `test_config.py` already
covers env parsing; this test is about the repository using the setting.

### D3. S2 test proves file dates win over settings
The fixture uses `time_units="days since 1981-01-01"` and `time_start_value=0`, 365 steps.
The repository is opened with `daily_start_date=date(1990, 1, 1)`, a deliberately different
start, and the test asserts `time_start == "1981-01-01"` and `time_end == "1981-12-31"`.
A second assertion with `time_start_value=1` expects `1981-01-02`, documenting the CF offset.
Memory: only the 1-D time coordinate is decoded (ADR-0005).
Rejected: testing `_time_index` directly – it is private; going through `PiscoRepository.open`
tests the real path.

### D4. Typed dependency in routes
```python
from typing import Annotated
RepositoryDep = Annotated[PiscoRepository, Depends(get_repository)]
def dataset(request: Request, repo: RepositoryDep) -> HTMLResponse: ...
```
A module-level alias keeps the signature short and is reusable by later routes.
Rejected: keeping `# noqa: B008` – hides a real lint rule for every future route.

### D5. Comment and lesson
`_rounded`: one comment line stating that **bounds** are rounded to 4 decimals to remove
float32 noise (keep the existing example). `AGENTS.md` "Lessons learned": one line about
filtering `StarletteDeprecationWarning` by its own class.

## Risks / Trade-offs

- [Changing `write_pisco_file` could alter existing fixtures] → Defaults reproduce the current
  output; the full suite and `tests/test_fixtures.py` must pass unchanged.
- [`Annotated` dependency changes route signature] → Behavior is identical; `tests/test_pages.py`
  covers `/dataset`.
