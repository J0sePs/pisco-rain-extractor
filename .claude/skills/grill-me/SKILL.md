---
name: grill-me
description: Interrogate the user about an ambiguous request before writing a proposal, spec or design. Use when scope, observable behavior or acceptance criteria are unclear, when the user says "grill me", or when openspec/config.yaml rules ask for it (proposal phase).
---

# Grill me

Turn a vague request into concrete, testable decisions **before** any artifact is written.
This skill writes nothing; it only asks questions and summarizes the answers.

## When to use
- The request does not state what is in or out of scope.
- The observable behavior (input, output, errors) is not defined.
- There are no acceptance criteria that could become test scenarios.
- The proposal rules in `openspec/config.yaml` point here.

## Procedure
1. Read `openspec/config.yaml` (`context`), `adr/README.md` and the relevant specs in
   `openspec/specs/` so you do not ask what is already decided.
2. List the open questions, grouped by:
   - **Scope**: what is included, what is explicitly out of scope.
   - **Behavior**: inputs (form fields, units, ranges), outputs (table, chart, file), errors.
   - **Data**: which PISCOp file (daily, monthly, climatology), period, spatial extent.
   - **Acceptance**: concrete examples with real values (coordinates, years, mm).
   - **Constraints**: performance, memory, dependencies, conflicts with accepted ADRs.
3. Ask **one question at a time** (or at most three closely related ones). For each one:
   - Offer 2–4 concrete options and mark your recommendation with the reason.
   - Prefer questions whose answer changes the design; skip anything with an obvious default
     (state the default instead).
4. Challenge weak answers: if an answer is vague ("fast", "a few years"), ask for a number.
5. Stop when every group has a concrete answer or an explicit "out of scope".

## Output
Reply in Spanish with a short summary the next artifact can use directly:

```
Decisions
- Scope: ...
- Out of scope: ...
- Behavior: ...
- Acceptance examples: ...
- Open points / possible ADRs: ...
```

Then hand back to the workflow that invoked this skill (for example `/opsx:propose`).

## Rules
- Never write files or code while grilling.
- Never invent an answer for the user; unresolved items stay under "Open points".
- If an answer contradicts an accepted ADR, say so and suggest `/adr-supersede`.
