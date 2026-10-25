# ADR-0003: Use uv as the Python package manager

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Project owner
- **Supersedes:** -
- **Related change:** -

## Context

The project depends on a scientific stack with compiled wheels (netCDF4, numpy,
pyproj, geopandas/shapely). Contributors and the AI agent work on Windows and other
platforms and need reproducible environments, a pinned Python version (3.12) and
one command to install and run everything.

## Options considered

1. **uv** (`pyproject.toml` + `uv.lock`) – very fast resolver, cross-platform lock file,
   manages the Python version and the virtual environment, `uv run` for every command.
2. **pip + venv + requirements.txt** – universal, but no real lock file and manual
   environment handling.
3. **Poetry** – lock file and groups, but slower and does not manage Python itself.
4. **conda / mamba** – good for geospatial binaries, but heavy and a separate ecosystem
   from PyPI tooling (ruff, pytest) and harder to lock reproducibly.

## Decision

We will use **uv** to manage Python 3.12, the virtual environment and dependencies.
Dependencies are declared in `pyproject.toml`, locked in `uv.lock` (committed), added
only with `uv add` (dev tools with `uv add --dev`) and every command runs through `uv run`.
`pip` is never used directly.

Rejected: pip + requirements.txt – not reproducible. Rejected: Poetry – slower and no
Python management. Rejected: conda – heavy and outside the PyPI workflow.

## Consequences

- **Positive:** `uv sync` reproduces the environment anywhere; fast CI; single tool.
- **Negative / trade-offs:** contributors must install uv; geospatial wheels depend on
  PyPI availability for the platform.
- **Follow-up:** each new dependency is justified in the change's `design.md`.
