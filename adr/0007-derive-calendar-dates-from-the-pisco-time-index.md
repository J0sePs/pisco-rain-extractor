# ADR-0007: Derive calendar dates from the PISCOp time index

- **Status:** Proposed
- **Date:** 2026-10-24
- **Deciders:** Project owner
- **Supersedes:** -
- **Related change:** openspec/changes/bootstrap-app/

## Context

In the three PISCOp v3.0 files the time dimension is `Z1`, an integer index 1..N with
`units: unknown`; there is no date coordinate. The daily file has 16436 steps, which is
exactly 1981-01-01 to 2025-12-31; the monthly file has 540 steps (1981-01 to 2025-12);
the climatology has 12 steps (calendar months). Every feature that filters by year or shows
dates depends on how this index is turned into dates.

## Options considered

1. **Fixed start date per file kind in the repository** – daily from 1981-01-01 (freq D),
   monthly from 1981-01-01 (month start), climatology months 1–12; check the length.
2. **User-supplied start date** – flexible, but error-prone and meaningless for users.
3. **Rewrite the files with a proper time coordinate** – clean, but creates a derived copy
   of SENAMHI data.

## Decision

We will build the calendar in the repository from fixed PISCOp v3.0 start dates
(option 1). If a file already has a decodable datetime coordinate, it is used instead.
The climatology must have exactly 12 steps; otherwise the file is marked unavailable.
Dates are exposed as ISO 8601 (`YYYY-MM-DD`).

Rejected: user-supplied start – shifts every result if mistyped. Rejected: rewriting files –
redistributes a modified copy of third-party data.

## Consequences

- **Positive:** one place defines dates; services and routes work with real dates.
- **Negative / trade-offs:** tied to PISCOp v3.0; a new version with another start date
  needs this ADR superseded.
- **Follow-up:** point extraction (year filters) relies on this calendar.
