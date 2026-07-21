---
Status: active
Owner: CT
Created: 2026-05-19
Last verified: 2026-07-13
Kind: process
---

# docs/

This directory organizes the repo's documentation by purpose and stage of work.

| Folder | Purpose | Use when |
| --- | --- | --- |
| `architecture/` | Durable reference for how the system works today. | Capturing the current modules, data flow, contracts, and current-state diagrams. |
| `decisions/` | Dated, append-only architecture decision records (ADRs): "we chose X because Y." | Recording a specific design choice, including its context, alternatives, and consequences. |
| `issues/` | Canonical tracker for bounded work, with evidence, ownership, dependencies, and resolution. | Filing or checking a bug, feature, chore, regression, or investigation. |
| `plans/` | Active execution steps that put a spec into effect. | Setting the work order for an approved spec. |
| `process/` | Cross-cutting workflow conventions (verification rules, merge strategy, release process). | Capturing how the team works, not what the system does. |
| `research/` | Investigation in progress. Messy by design. | Exploring before committing to a design. |
| `runbooks/` | Operational reference for broken systems and routine operations. | Following a recipe for an on-call or ops task. |
| `specs/` | Aspirational, pre-implementation design. | Describing what to build, before code. |
| `templates/` | Issue, spec, plan, ADR boilerplate. | Adding a starter template for a new doc type. |
| `usage/` | Downstream reference for using this app, tool, or library. | Explaining its use to a user or integrator. |

Retired docs are deleted after their durable behavior, rationale, and residual
intent move into architecture, decisions, and context docs. The repo does not
keep a parallel archive tree.

Active work maps to governed reports in [`docs/issues/`](issues/README.md).
Their `Resolution` fields and the issue index are authoritative. GitHub Issues
is not a work-tracking source for this repository. [`DOCGRAPH.md`](../DOCGRAPH.md)
defines the document lifecycle rules.
