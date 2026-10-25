# ADR-0012: Use a 95% valid-day threshold for complete years and months

- **Status:** Accepted
- **Date:** 2026-10-25
- **Deciders:** Project owner
- **Supersedes:** -
- **Related change:** openspec/changes/add-point-analysis/ (design D2)

## Context

Point analysis aggregates the daily series into annual totals, annual 24 h maxima, a mean
annual rainfall and a monthly climatology. Some cells or periods have missing days, and a year
can be cut by the end of the file (a daily file ending on 2025-06-30 has 181 days of 2025).
Summing only the days present makes such a year look like a dry year, and that low total then
drags down the mean. Exports and basin analysis will aggregate the same way, so the rule must be
the same everywhere.

## Options considered

1. **Threshold on calendar days (95%)**: a year or month counts as complete when its valid
   (non-missing) days are at least 95% of its calendar days. Days missing from the file count as
   missing days. Incomplete periods are still shown, but flagged.
2. **No threshold**: aggregate whatever is present. Simple, but cut or gappy periods bias
   totals and means downward without telling the user.
3. **Treat missing days as 0 mm**: same bias, hidden inside the data.
4. **Require 100% valid days**: strict, but a single missing day discards a whole year.

## Decision

We will use option 1:

- `complete := valid_days * 100 >= 95 * calendar_days`, computed with integers so the limit
  values are decided exactly. The limits are 347 of 365 and 348 of 366 days for a year, and
  30 of 31, 29 of 30, 27 of 28 and 28 of 29 days for a month.
- `calendar_days` is the length of the calendar year or month, never the number of rows read.
- The mean annual rainfall uses complete years only. The monthly climatology uses complete
  months only. Annual tables list every year and flag incomplete ones as "Incomplete".
- Totals are sums of valid days. A period with no valid day has no total (shown as "missing").

Rejected: no threshold, because cut years enter the mean. Rejected: missing as 0 mm, because
it hides the bias. Rejected: 100%, because it discards years over isolated gaps.

## Consequences

- **Positive:** aggregates are comparable across cells and periods. Users see which years
  were excluded and why.
- **Negative / trade-offs:** the 95% value is a convention, not a dataset property. A short
  request may have no complete year, and then the mean is shown as unavailable.
- **Follow-up:** `rainfall-analysis` spec (year completeness, mean annual rainfall, monthly
  climatology). Future exports and basin aggregates reuse this rule. Changing the threshold
  requires superseding this ADR.
