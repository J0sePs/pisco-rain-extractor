# ADR-0002: Use FastAPI with server-rendered Jinja2 templates

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Project owner
- **Supersedes:** -
- **Related change:** -

## Context

The app serves environmental engineering students and practitioners who fill in a
form (point or basin), get tables and charts, and download files. There is no need
for real-time interaction, user accounts or a database. The team works in Python
(xarray, pandas, matplotlib) and wants a single language, no build step and no
JavaScript toolchain. Static assets must not come from a CDN.

## Options considered

1. **FastAPI + Jinja2 server-rendered HTML** – Python only, HTML forms posted to the
   server, typed request handling, built-in TestClient for tests.
2. **FastAPI JSON API + SPA (React/Vue)** – richer UI, but adds a JS toolchain,
   duplicated validation and a second codebase.
3. **Streamlit / Dash** – fast prototypes, but less control over routes, layout,
   downloads and testing, and harder to keep a layered architecture.
4. **Django** – complete framework, but its ORM, admin and auth are unused here.

## Decision

We will build the app with **FastAPI + Uvicorn**, rendering **Jinja2 templates** on the
server, with HTML forms (python-multipart) and **plain CSS** in `app/static/`.
No JS framework and no CDN; vanilla JS only when a spec explicitly requires it.

Rejected: SPA – unnecessary complexity for form-and-report pages. Rejected: Streamlit/Dash –
weak control over structure and tests. Rejected: Django – heavy for an app without a database.

## Consequences

- **Positive:** one language; pages testable with `httpx`/TestClient; works without JS.
- **Negative / trade-offs:** interactive features (tabs, maps) must be CSS-only or
  server-rendered images; every interaction is a page round trip.
- **Follow-up:** charts are rendered server-side as PNG (matplotlib Agg).
