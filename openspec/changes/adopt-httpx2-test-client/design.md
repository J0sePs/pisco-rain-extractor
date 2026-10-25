# Design

## Context

See `proposal.md` (Why). Observed in the installed environment:

- `starlette==1.10.0` (`starlette/testclient.py`, lines 25–43) does `import httpx2 as httpx`; only
  if that fails it imports `httpx` and emits
  `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`
  The warning fires at import time, when `tests/conftest.py` imports `fastapi.testclient`.
- `StarletteDeprecationWarning` subclasses **`UserWarning`**, not `DeprecationWarning`
  (`starlette/exceptions.py`, line 36).
- `httpx==0.28.1` is a direct dev dependency only; nothing else requires it. No module in `app/`
  or `tests/` imports `httpx`. `uv pip install --dry-run httpx2` resolves `httpx2==2.16.0`
  (+ `httpcore2`, `truststore`).

## Goals / Non-Goals

**Goals:**
- The suite imports `TestClient` through `httpx2` and emits no `StarletteDeprecationWarning`.
- A verification command that actually fails while the warning is present.

**Non-Goals:**
- Turning all warnings into errors project-wide (`filterwarnings` in `pyproject.toml`).
- Upgrading FastAPI or Starlette.

## Decisions

### D1. Replace httpx with httpx2 in the dev group
`uv add --dev httpx2`, then `uv remove --dev httpx`. Justification for the new dependency:
it is the HTTP client Starlette's `TestClient` now requires; it is test-only and never shipped
with the app. `httpx` is removed because nothing imports it directly and keeping both would
leave an unused dependency.
Rejected: keeping `httpx` and silencing the warning with `filterwarnings` – hides the problem
until Starlette drops the fallback. Rejected: pinning an older Starlette – blocks FastAPI updates.

### D2. Verification command
The requested check `uv run pytest -q -W error::DeprecationWarning` does **not** catch this
warning, because it is a `UserWarning` subclass: run today, with the warning present, it reports
`52 passed, 1 warning` and exits 0. The check that fails today and must pass after the change is:

```
uv run pytest -q -W error::starlette.exceptions.StarletteDeprecationWarning
```

Today it errors during collection with the `StarletteDeprecationWarning`. Both commands are kept
in `tasks.md`: the requested one (must still pass) and the qualified one (the real gate).
Rejected: `-W error::UserWarning` – broader than needed and could fail on unrelated warnings
from scientific libraries.

### D3. Project stack text – ADR-0009 (Accepted)
`openspec/config.yaml`, `context` block, Quality line:

```
-  - Quality: pytest + httpx (FastAPI TestClient), ruff (lint + format).
+  - Quality: pytest + httpx2 (FastAPI TestClient), ruff (lint + format).
```

The config states that changing the stack requires an ADR.
See ADR-0009: Use httpx2 for the FastAPI test client. The user approved this edit on 2026-10-24;
it is applied in task 3.1.

## Risks / Trade-offs

- [httpx2 behaves differently from httpx in `TestClient`] → The full suite (52 tests) is the
  check; Starlette 1.10 already targets httpx2 as its primary client.
- [httpx2 is a new, less established package] → Test-only; reverting is `uv remove --dev httpx2`
  plus `uv add --dev httpx`.
