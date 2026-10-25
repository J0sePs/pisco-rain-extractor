---
name: c4-diagrams
description: Draw C4 architecture diagrams (context, container, component) as Mermaid inside design.md or an ADR. Use when a change crosses layers, is the first change of the project, adds an external dependency or data source, or when the user asks for an architecture diagram.
---

# C4 diagrams

Explain the architecture with the smallest C4 level that answers the question.
Diagrams are Mermaid code blocks embedded in Markdown, so they render on GitHub and
stay diff-friendly. No images, no external tools.

## Choose the level
| Level | Use when | Shows |
|---|---|---|
| 1. System context | First change of the project; new external actor or data source | User, the web app, PISCOp files (SENAMHI) |
| 2. Container | Runtime or deployment changes | Browser, FastAPI/Uvicorn process, `data/` NetCDF files |
| 3. Component | The change crosses layers | Routes → services → repositories inside the app |

Never draw level 4 (code); the contracts in `design.md` already cover it.

## Rules
- Respect the layered architecture: arrows go `routes -> services -> repositories`, never back.
  Only repositories touch `data/`. If the diagram needs another arrow, stop: it requires an ADR.
- Name elements with the real paths/modules (`app/services/extraction.py`), not generic labels.
- Label each arrow with what flows (`form POST`, `lat, lon, dates`, `xarray slice`, `PNG`).
- Keep each diagram under ~12 elements; split if larger.
- Add one sentence below each diagram saying what it shows and what it omits.

## Templates

Level 1 – System context:
```mermaid
flowchart LR
    user["Engineering student / practitioner<br/>[Person]"]
    app["pisco-rain-extractor<br/>[Web app: FastAPI + Jinja2]"]
    data[("PISCOp v3.0 NetCDF<br/>[SENAMHI, local data/]")]
    user -- "HTML forms, downloads CSV/XLSX/PNG" --> app
    app -- "lazy reads (xarray)" --> data
```

Level 3 – Components:
```mermaid
flowchart TB
    subgraph app["FastAPI app"]
        routes["app/routes/*<br/>parse forms, render templates"]
        services["app/services/*<br/>extraction, analysis, charts, exports"]
        repos["app/repositories/*<br/>open NetCDF once (lifespan)"]
    end
    nc[("data/*.nc")]
    routes --> services --> repos --> nc
```

## Where to put it
- In `openspec/changes/<change>/design.md` under a `## Architecture` heading.
- In an ADR, under `## Context` or `## Decision`, when the diagram justifies the decision.
