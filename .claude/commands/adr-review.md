---
description: Read-only check of the working tree and active changes against accepted ADRs
argument-hint: "[change name]"
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git status:*), Bash(openspec status:*), Bash(openspec list:*)
---

Review compliance with the accepted ADRs. Optional change to focus on: **$ARGUMENTS**

This command is **read-only**: never create, edit or delete files, never stage or commit.
Apply the `adr-manager` skill (section "Review").

## Current state
- Working tree: !`git status --short`
- Diff summary: !`git diff --stat`
- Active changes: !`openspec list`

## Steps
1. Read `adr/README.md` and every ADR with status `Accepted`.
2. Pick the scope: the change named in `$ARGUMENTS`, or every active change listed above.
   For each, run `openspec status --change "<name>"` and read its `proposal.md`,
   `design.md` and `tasks.md`.
3. Inspect the code touched by the change (`git diff`, plus `Read`/`Grep` on `app/` and `tests/`).
4. Check each accepted ADR and the layering rule (routes → services → repositories;
   only repositories read `data/`). Use `Grep` for forbidden patterns, for example
   `xarray`/`open_dataset` outside `app/repositories/` or `fastapi` imports in `app/services/`.
5. Report in Spanish, grouped as:
   - **VIOLATION** (file:line, ADR, why)
   - **MISSING ADR** (decision found, where, suggested `/adr <title>`)
   - **STALE** (index or supersede links out of sync)
   - **OK** (ADRs checked with no findings)
6. End with a verdict: `PASS` (no violations) or `FAIL`, and the next step
   (`/opsx:verify` on PASS; fixes or `/adr-supersede` on FAIL).
