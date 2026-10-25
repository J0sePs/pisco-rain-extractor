# ADR-0013: Serve point results and charts from stateless GET URLs that re-read the cell

- **Status:** Accepted
- **Date:** 2026-10-25
- **Deciders:** Project owner
- **Supersedes:** -
- **Related change:** openspec/changes/add-point-analysis/ (design D5, D6)

## Context

The point result now has a paginated daily table and five PNG charts. Each page link and each
`<img>` is a separate HTTP request, and each one needs the same series. The app has no database
(ADR-0002). It reads NetCDF lazily, one cell at a time (ADR-0005). The data was measured on the
real daily file: reading the full 1981–2025 period of one cell (16436 values, about 130 KB)
takes about 0.15 s on a cold read and about 2 ms on a warm one.

## Options considered

1. **Stateless GET URLs**: `POST /point` validates, without reading, and redirects (303) to
   `GET /point/result?lon=&lat=&start_year=&end_year=&page=`. Each chart is
   `GET /point/chart/{kind}.png` with the same query. Every request validates, reads the cell
   and computes the result again.
2. **Render everything in the POST response**: put the charts inline as base64. There are no
   extra requests, but pagination has to re-post the form, and results cannot be bookmarked or
   shared.
3. **Server-side cache keyed by an id**: the POST stores the series in memory and later
   requests look it up. This saves reads, but adds state, expiry rules and memory growth to save
   about 2 ms per request.

## Decision

We will use option 1:

- The query string fully describes a result. Any result or chart can be reproduced from its URL.
- Routes keep raw query strings and call the same validation as the form. Invalid input returns
  422, and a cell without data returns the no-data page, or 404 for a chart.
- Each request performs exactly one single-cell read through the repository (ADR-0005).
  Nothing is cached in the app. Charts in hidden tabs use `loading="lazy"`.

Rejected: inline base64, because results cannot be bookmarked and pagination would need forms.
Rejected: an in-memory cache, because the state and memory it adds are not justified by a
2 ms read.

## Consequences

- **Positive:** results are bookmarkable and shareable, the server keeps no state, and every
  request is independent.
- **Negative / trade-offs:** a full result view costs up to 6 reads of the same cell (the page
  plus 5 charts). `POST /point` no longer returns the result HTML, which is a breaking change
  for anything that scraped it.
- **Follow-up:** future exports (CSV/XLSX) use the same query string. Caching would require
  superseding this ADR, together with measurements that justify it.
