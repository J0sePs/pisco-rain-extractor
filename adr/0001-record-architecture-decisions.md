# ADR-0001: Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Project owner
- **Supersedes:** -
- **Related change:** -

## Context

pisco-rain-extractor is built with spec-driven development (OpenSpec) and an AI coding
agent. Specs in `openspec/specs/` describe *what* the system does, but not *why* the
structural choices were made (stack, layering, how PISCOp NetCDF files are read).
Without a durable record, the agent and future contributors may silently revert or
contradict earlier decisions, and `openspec/config.yaml` alone cannot capture the
trade-offs behind each choice.

## Options considered

1. **Architecture Decision Records in `adr/`** – one short Markdown file per decision,
   numbered and indexed. Versioned with the code, easy for the agent to read.
2. **Decisions only inside each change's `design.md`** – no extra files, but decisions
   get archived with the change and are hard to find later.
3. **External wiki or documents** – rich editing, but outside version control and
   invisible to the agent.

## Decision

We will record every architecturally significant decision as an ADR in `adr/`,
using `adr/0000-template.md` and the index in `adr/README.md`, managed through the
`adr-manager` skill and the `/adr`, `/adr-supersede` and `/adr-review` commands.

- Accepted ADRs are immutable; a change of mind is a new ADR that supersedes the old one.
- Accepted ADRs take precedence over `openspec/config.yaml` and any `design.md`.
- `/adr-review` runs before `/opsx:verify` when closing a change.

Rejected: decisions only in `design.md` – they are archived with the change and lose
visibility. Rejected: external wiki – not versioned with the code and not readable by the agent.

## Consequences

- **Positive:** decisions are traceable, reviewable in pull requests and readable by the agent.
- **Negative / trade-offs:** small overhead of writing an ADR for each structural decision.
- **Follow-up:** record the fixed stack and the layered architecture from
  `openspec/config.yaml` as their own ADRs.
