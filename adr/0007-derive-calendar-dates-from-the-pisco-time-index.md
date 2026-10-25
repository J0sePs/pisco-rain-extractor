# ADR-0007: Derive calendar dates from the PISCOp time index

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Project owner
- **Supersedes:** -
- **Related change:** openspec/changes/bootstrap-app/

## Context

In the three PISCOp v3.0 files the time dimension is `Z1`, an integer index 1..N with
`units: unknown`; there is no date coordinate. Every feature that filters by year or shows
dates depends on how this index is turned into dates.

### Evidence

- **Step counts** (read from file metadata): daily 16436, monthly 540, climatology 12.
- **Dataset readme** (`data/readme.txt`, distributed with the files) states only years,
  not a start date or a calendar:
  > - 'PISCOp_m.nc': monthly rainfall (mm) from 1981 to 2025 at 0.10° spatial resolution.
  > - 'PISCOp_d.nc': daily rainfall (mm) from 1981 to 2025 at 0.10° spatial resolution.
  > - 'PISCOp_clim2.nc': monthly normal 1991-2015 rainfall (mm) at 0.10° spatial resolution.

  The start date (1981-01-01) and the calendar are therefore **inferred, not declared**.
- **Calendar check**: 1981-01-01 to 2025-12-31 is 16436 days only in the Gregorian
  calendar with leap years (45 x 365 = 16425, plus 11 leap days: 1984, 1988, ..., 2024).
  A fixed 365-day (`noleap`) calendar would give 16425 steps, a 360-day calendar 16200.
  The observed 16436 matches the Gregorian calendar exactly.
- **Monthly check**: 540 = 45 x 12 months, 1981-01 to 2025-12, consistent with the daily file.

## Options considered

1. **Fixed start date per file kind** – daily from 1981-01-01 (one step per Gregorian day),
   monthly from 1981-01-01 (month start), climatology months 1–12; checked by length and by
   cross-validation between files.
2. **User-supplied start date** – flexible, but error-prone and meaningless for users.
3. **Rewrite the files with a proper time coordinate** – clean, but creates a derived copy
   of SENAMHI data.

## Decision

We will build the calendar in the repository from fixed PISCOp v3.0 start dates (option 1):

- The start dates are defined **in one place only**, `app/config.py` (settings with
  defaults `1981-01-01` for daily and monthly); no other module hardcodes them.
- Daily: Gregorian calendar with leap years, one step per day. Monthly: one step per month
  (first day). Climatology: exactly 12 steps (months 1–12), otherwise unavailable.
- If a file already has a decodable datetime coordinate, it is used instead.
- **Cross-validation at startup**: the last month derived from the daily file must equal the
  last month of the monthly file. If they differ, both files are flagged with a warning on
  `/dataset`; the app still starts and the files stay available.
- Dates are exposed as ISO 8601 (`YYYY-MM-DD`).

Rejected: user-supplied start – shifts every result if mistyped. Rejected: rewriting files –
redistributes a modified copy of third-party data. Rejected: `noleap`/360-day calendars –
they do not match the observed 16436 steps.

## Consequences

- **Positive:** one place defines dates; the inference is checked twice (exact Gregorian
  day count and daily/monthly agreement); services and routes work with real dates.
- **Negative / trade-offs:** tied to PISCOp v3.0; a new version with another start date
  needs this ADR superseded (or the settings changed with justification). The
  cross-validation only detects inconsistent end dates, not a shift applied equally to both files.
- **Follow-up:** point extraction (year filters) relies on this calendar.
