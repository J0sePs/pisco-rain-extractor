---
description: Create a new Architecture Decision Record in adr/ and add it to the index
argument-hint: <decision title>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(ls:*), Bash(git status:*), Bash(openspec list:*)
---

Create a new ADR titled: **$ARGUMENTS**

Apply the `adr-manager` skill (section "Create").

## Current state
- Existing ADRs: !`ls adr`
- Active OpenSpec changes: !`openspec list`

## Steps
1. If `$ARGUMENTS` is empty, ask the user for the decision title and stop.
2. Read `adr/README.md`, `adr/0000-template.md` and any accepted ADR related to the topic.
   If the new decision contradicts an accepted ADR, stop and suggest `/adr-supersede` instead.
3. If the context, options or consequences are unclear, use the `grill-me` skill first.
4. Compute the next number and slug, create `adr/NNNN-<slug>.md` from the template with
   status `Proposed` (or `Accepted` only if the user says so) and today's date.
5. List at least two options and the rejected alternative with its reason.
6. Link the related change in `openspec/changes/` if one exists.
7. Add the row to the index table in `adr/README.md`.
8. Show the user (in Spanish) a short summary and the proposed commit message
   `docs(adr): add ADR-NNNN <title>`. Do not commit.
