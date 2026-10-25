---
name: git-discipline
description: Git hygiene for every SDD phase - check the working tree, commit planning before implementation, one Conventional Commit per task group, never commit data or secrets, never commit without user confirmation. Use at the start of /opsx:apply, before /opsx:archive, and whenever a commit is about to be proposed.
---

# Git discipline

Keep history small, readable and traceable to OpenSpec changes and ADRs.

## Golden rules
- **Never** run `git commit` or `git push` without the user's explicit confirmation.
  Propose the message and wait.
- **Never** stage `data/`, `*.nc`, `.env`, credentials, `.venv/` or `outputs/`.
- **Never** use `git push --force`, `git reset --hard` or rewrite published history.
- Never edit `.gitignore` rules for `data/`.

## Before staging
1. Run `git status --short` and `git diff --stat`.
2. Check that no forbidden path appears:
   `git status --short | grep -E '(^|/)data/|\.nc$|\.env$'` must print nothing
   (except `data/.gitkeep` and `data/README.md`).
3. Stage explicit paths (`git add <path> ...`), never `git add -A` blindly.

## Per phase
| Phase | Rule |
|---|---|
| Planning (`/opsx:propose`, `/opsx:new`, `/opsx:ff`, `/opsx:update`, `/adr`) | Commit the artifacts alone: `docs(openspec): propose <change>` or `docs(adr): NNNN <title>`. |
| Start of `/opsx:apply` | Tree must be clean and the plan committed. If not, stop and propose the planning commit first. |
| During `/opsx:apply` | One commit per task group, after `uv run pytest` and `uv run ruff check .` pass. |
| `/opsx:archive` | Commit the archive move and synced specs: `docs(openspec): archive <change>`. |

## Commit messages (Conventional Commits, in English)
```
<type>(<scope>): <imperative summary, max ~72 chars>

<optional body: what and why, wrapped at 72>

Refs: openspec/changes/<change>  |  ADR-NNNN
```
- Types: `feat`, `fix`, `docs`, `chore`, `test`, `refactor`.
- Scope: the layer or capability (`repositories`, `point-extraction`, `adr`, `openspec`).
- Reference the change or ADR in the footer when one applies.

## Branches
- Optional but recommended: one branch per change, `change/<change-name>`.
- Never work directly on a branch with unrelated uncommitted changes.

## Output
Show the user (in Spanish) the staged file list and the proposed message, then wait.
