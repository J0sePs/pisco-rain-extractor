---
description: Replace an accepted ADR with a new one and link both
argument-hint: <old ADR number> <new decision title>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(ls:*), Bash(git status:*), Bash(openspec list:*)
---

Supersede an accepted ADR. Arguments: **$ARGUMENTS**
(first token: number of the ADR to replace, e.g. `0002`; the rest: title of the new decision).

Apply the `adr-manager` skill (section "Supersede").

## Current state
- Existing ADRs: !`ls adr`

## Steps
1. If the number or the title is missing, ask the user and stop.
2. Read the old ADR. If its status is not `Accepted`, stop and explain:
   a `Proposed` ADR is edited directly instead of superseded.
3. Ask the user (or use the `grill-me` skill) why the old decision no longer holds,
   unless the reason is already clear from the conversation or the active change.
4. Create the new ADR from `adr/0000-template.md` with the next number,
   status `Proposed` (or `Accepted` if the user confirms), today's date and
   `Supersedes: [ADR-OLD](<old file>)`. Explain in Context what changed.
5. In the old ADR, change **only** the status line to
   `Superseded by [ADR-NEW](<new file>)`. Edit nothing else in it.
6. Update both rows in `adr/README.md`.
7. If an active change in `openspec/changes/` depends on the old decision,
   suggest `/opsx:update` for it.
8. Show the user (in Spanish) a summary and the proposed commit message
   `docs(adr): supersede ADR-OLD with ADR-NEW`. Do not commit.
