# ADR-0009: Use httpx2 for the FastAPI test client

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Project owner
- **Supersedes:** -
- **Related change:** openspec/changes/adopt-httpx2-test-client/

## Context

The project stack in `openspec/config.yaml` lists "pytest + httpx (FastAPI TestClient)", and
changing the stack requires an ADR. Route and template tests use FastAPI's `TestClient`, which is
Starlette's. Starlette 1.10 imports `httpx2` first and only falls back to `httpx`, emitting on every
test run:

> StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.

When the fallback is removed, every route test breaks at once. Facts checked in this project:
no module in `app/` or `tests/` imports `httpx` directly; `httpx` is only a direct dev dependency;
`httpx2==2.16.0` resolves cleanly. `StarletteDeprecationWarning` subclasses `UserWarning`, so
`-W error::DeprecationWarning` does not catch it.

## Options considered

1. **Replace `httpx` with `httpx2` in the dev group** – the client Starlette now targets; removes
   the warning; test-only.
2. **Keep `httpx` and silence the warning** (`filterwarnings`) – no dependency change, but hides a
   known future break.
3. **Pin Starlette/FastAPI below the deprecation** – keeps `httpx`, but blocks framework updates
   and security fixes.

## Decision

We will use **`httpx2`** as the HTTP backend of FastAPI's `TestClient` (option 1): add it with
`uv add --dev httpx2` (ADR-0003) and remove `httpx` from the dev group, since nothing imports it
directly. The Quality line of the stack in `openspec/config.yaml` becomes
"pytest + httpx2 (FastAPI TestClient)". Tests keep using `fastapi.testclient.TestClient`; they do
not import `httpx2` directly.

The absence of the warning is checked with
`uv run pytest -q -W error::starlette.exceptions.StarletteDeprecationWarning`.

Rejected: silencing the warning – defers the break and makes it surprising. Rejected: pinning
Starlette/FastAPI – trades a test-only dependency for an outdated web framework.

## Consequences

- **Positive:** clean test output; aligned with Starlette's supported path; no app code changes.
- **Negative / trade-offs:** `httpx2` is a younger package than `httpx`; it is test-only, so the
  impact of a problem is limited to the test suite.
- **Follow-up:** ADR-0002 mentions "httpx/TestClient" among its consequences; that wording is
  historical and does not change ADR-0002's decision. Reverting this ADR means
  `uv remove --dev httpx2` and `uv add --dev httpx`.
