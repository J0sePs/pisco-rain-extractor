---
name: adr-manager
description: Create, supersede, index and review Architecture Decision Records in adr/. Use when a structural decision is made or detected (stack, layering, data access, dependencies, file formats), when design.md marks something "Requires ADR", or when running /adr, /adr-supersede or /adr-review.
---

# ADR manager

Architecture decisions live in `adr/` as numbered Markdown files (MADR-lite format).
Accepted ADRs take precedence over `openspec/config.yaml` and over any `design.md`.

## Layout
```
adr/
├── README.md                  # index (table), always kept in sync
├── 0000-template.md           # template, never numbered as a decision
└── NNNN-kebab-case-title.md   # one decision per file
```

## Status lifecycle
`Proposed` → `Accepted` → (`Deprecated` | `Superseded by ADR-NNNN`)
- A `Proposed` ADR may be edited freely.
- An `Accepted` ADR is **immutable**. The only allowed edit is its status line when it is
  superseded or deprecated (plus the matching link). Any other change requires a new ADR.

## What deserves an ADR
Yes: changing the stack, adding a dependency with architectural impact, layering rules,
how NetCDF data is opened or cached, file/export formats, coordinate handling, deployment.
No: naming of a local variable, a bug fix, a refactor inside one module.

## Create (used by /adr)
1. Next number: highest `NNNN` in `adr/` + 1, zero-padded to 4 digits.
2. Slug: title in English, lowercase kebab-case.
3. Copy `adr/0000-template.md`, fill every section; status `Proposed` unless the user
   says it is already accepted; date in ISO 8601 (today).
4. Every decision lists at least one rejected alternative with the reason.
5. Link the related OpenSpec change if there is one (`openspec/changes/<change>/`).
6. Add a row to the index in `adr/README.md`.

## Supersede (used by /adr-supersede)
1. Read the old ADR; it must be `Accepted`.
2. Create the new ADR as above; in its header set `Supersedes: ADR-OLD`.
3. In the old ADR change **only** the status line to `Superseded by [ADR-NEW](NNNN-....md)`.
4. Update both rows in `adr/README.md`.

## Review (used by /adr-review)
Read-only. Compare the working tree / active change against every `Accepted` ADR and report:
- **VIOLATION**: code or design contradicts an accepted ADR (file, line, ADR).
- **MISSING ADR**: a structural decision appears in the diff or `design.md` with no ADR.
- **STALE**: index rows that do not match the files, or broken supersede links.
- **OK**: ADRs checked with no findings.

## Writing rules
- Files in English; reply to the user in Spanish.
- Keep each ADR short (about one page). Context explains forces, not history.
- Use the c4-diagrams skill when a diagram makes the decision clearer.
- Never commit; hand off to the git-discipline skill and wait for confirmation.
