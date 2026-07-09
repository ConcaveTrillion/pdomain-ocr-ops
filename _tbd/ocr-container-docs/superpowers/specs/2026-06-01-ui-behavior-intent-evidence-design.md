# UI and behavior intent evidence process

## Status

Draft approved in conversation on 2026-06-01. This spec defines process
changes for `docs/process/ui-definition.md`,
`docs/process/behavior-e2e-capture.md`, and their templates. It does not
implement those process changes yet.

## Problem

The current UI Definition and Behavior E2E Capture processes help agents
inventory UI, behavior records, and tests, but they do not force agents
to separate product intent from observed implementation.

That creates two failure modes:

1. Existing code behavior can be documented as intended behavior without
   maintainer confirmation.
2. Intended behavior that is missing, unwired, or untested can disappear
   into prose instead of producing executable pressure or an explicit
   decision.

Claude Design wireframes and handoff bundles add another source of
evidence. They are useful, but they must not become product truth by
accident. The process needs a round-trip that can send behavior intent to
Claude Design, receive wireframes/prototypes back, normalize them into a
UI Definition, and then feed Behavior Capture and tests.

## Goals

- Use one unified intent/evidence process for new UI, redesigned UI, and
  existing UI.
- Treat implementation, tests, docs, wireframes, and Claude Design output
  as evidence sources, not independent authorities.
- Give AI agents a required way to classify intended, observed-only,
  accidental, missing, and unknown behavior.
- Require mismatches affecting interactive elements or user-visible
  workflows to create documentation plus either executable pressure or an
  explicit maintainer decision.
- Connect Claude Design briefs, handoff bundles, screenshots, generated
  prototype code, UI definitions, behavior specs, implementation files,
  and tests under one stable unit slug.

## Non-goals

- Do not add a generated audit script in the first implementation. The
  first change is process and template discipline.
- Do not make Claude Design generated code an implementation source of
  truth.
- Do not require every non-interactive visual detail to block behavior
  capture.
- Do not require full-unit blocking before behavior capture; blocking is
  scoped to incomplete interactive elements and their interactions.

## Unified intent model

Every UI Definition uses the same capture discipline regardless of
whether the unit is new, redesigned, or already implemented.

Interactive elements and interaction candidates must carry an intent
status:

- `intended`: maintainer, design handoff, issue, spec, ADR, or approved
  UI definition says this is desired product behavior.
- `observed-only`: code or prototype currently shows this, but product
  intent is not confirmed.
- `accidental`: code or prototype currently shows this, and it should not
  be relied on without explicit approval.
- `missing`: intended behavior has no current UI trigger, wiring, or
  implementation path.
- `unknown`: evidence conflicts, or intent cannot be inferred.

The core rule is:

> Code is evidence, not authority. Agents may document what code does,
> but they must not silently promote observed behavior into intended
> behavior.

## Evidence blocks

Every interactive element and interaction candidate in a UI Definition
must include an evidence block:

- UI evidence: selector, component, screenshot, prototype, DOM evidence,
  or code path.
- Product evidence: maintainer decision, Claude Design handoff, issue,
  spec, ADR, or none.
- Backend evidence: endpoint, state object, job, file, event store, or
  none.
- Test evidence: test path and test name, or none.
- Mismatch disposition: `fix-now`, `xfail`, `defer`,
  `accept-observed`, `do-not-test`, or `none`.

Behavior records should inherit intent status from the cited UI
interaction candidate unless Behavior Capture discovers drift.

## Mismatch handling

A mismatch is any gap between intended behavior, observed UI, backend
behavior, and test evidence. Examples:

- Intended UI element missing from implementation.
- Implemented element not found in the approved UI Definition.
- Interaction exists but triggers the wrong backend behavior.
- Backend behavior exists but no UI trigger reaches it.
- Test exists for behavior not declared in UI or behavior docs.
- Behavior docs describe a model the current code no longer uses.
- API-only behavior is documented as user-facing product behavior.

Each mismatch gets a disposition:

- `fix-now`: implementation should be brought into line immediately.
- `xfail`: intended behavior is not implemented yet, but executable
  pressure is desired.
- `defer`: documented and tracked elsewhere, with no immediate test
  pressure.
- `accept-observed`: current behavior becomes intended after maintainer
  approval.
- `do-not-test`: explicitly not worth executable coverage.

If a mismatch affects an interactive element or user-visible workflow,
agents cannot leave it as prose only. They must either add or request an
xfail/pending test, or record an explicit maintainer decision not to test
it.

## Handoff gate

Behavior Capture may start for a unit, but it may not treat an
interactive element as behavior-ready unless that element has:

- Stable selector, widget id, or command arg.
- Intent status.
- Evidence block.
- Interaction candidate.
- Mismatch disposition, if evidence conflicts or implementation is
  missing.

This gate is element-scoped. If a unit has twenty elements and two are
unclear, agents may capture behavior for the eighteen complete elements,
but the two incomplete elements must remain blocked/open.

Subagent outputs must follow the same model:

- UI inventory agents return elements with status and evidence, not just
  selectors.
- Backend agents return side effects and whether a UI trigger reaches
  them.
- Test agents return what tests prove and what they only touch
  superficially.
- The parent agent owns final classification and asks the maintainer only
  for judgment calls.

## Claude Design evidence bundle

Claude Design output is prototype implementation evidence. Agents may
inspect its generated HTML, CSS, assets, component hierarchy, states, and
interaction assumptions, but they must map those ideas back to the
repo's real design system, components, routes, stores, and backend APIs.

Each unit may have a bundle under:

```text
docs/specs/ui/assets/<unit-slug>/
  claude-design-brief.md
  round-001/
    handoff/
    screenshots/
    notes.md
  round-002/
    handoff/
    screenshots/
    notes.md
```

The UI Definition records:

- Source tool: Claude Design.
- Artifact type: handoff bundle, screenshot, generated code, or mixed.
- Artifact path.
- Approved variant.
- Prototype status: visual reference or prototype evidence.
- Reusable assets.
- Non-authoritative parts.
- Design-system mapping requirements.

Default classification for Claude Design additions:

- Non-interactive visual additions default to `observed-only`.
- New buttons, controls, workflows, shortcuts, data states, or backend
  claims default to `unknown` until maintainer approval.

Rejected Claude Design proposals are kept with rejection notes, so future
agents do not repeatedly propose the same rejected path.

## Claude Design round-trip

The process supports two directions.

Intent-first loop:

```text
Behavior intent -> Claude Design -> UI Definition -> Behavior Capture
```

Use this when the shape is still open and Claude Design should propose
wireframes or prototype structure.

UI-first loop:

```text
Existing UI Definition + mismatch log -> Claude Design -> revised UI Definition
```

Use this when an approved unit exists and needs refinement or redesign.

Each unit may have:

```text
docs/specs/ui/assets/<unit-slug>/claude-design-brief.md
```

The brief includes:

- Product goal.
- Behavior intent.
- Required screens or components.
- Required states.
- Required interactions.
- Backend and data reality.
- Existing design constraints.
- Known missing or unclear behavior.
- Non-goals.

Claude Design output is normalized back into the UI Definition. Behavior
Capture consumes the normalized UI Definition, not raw Claude Design
output.

## Claude Design index

Artifacts stay local to the unit bundle, but `docs/specs/ui/` also gets a
lightweight index:

```text
docs/specs/ui/claude-design-index.md
```

The index lets agents discover active design loops quickly.

Example columns:

| Unit | Current round | Brief | Output | Status | Next action |
|------|---------------|-------|--------|--------|-------------|

Allowed statuses:

- `draft-brief`
- `sent-to-claude-design`
- `output-received`
- `normalizing`
- `accepted`
- `rejected`
- `stale`
- `needs-decision`

## Template changes

`docs/templates/ui-unit-definition.md` should add:

- Top-level capture discipline metadata.
- Prototype evidence section.
- Evidence fields for every interactive element.
- Intent status and evidence summary for every interaction candidate.
- Mismatch log.
- Claude Design bundle/index references where applicable.

`docs/templates/behavior-unit-spec.md` should add:

- UI source: UI interaction candidate ID or `existing stable UI`.
- Intent status: inherited or revised.
- Coverage aspects: trigger, observable, side effect, bad state,
  persistence.
- Mismatch disposition: inherited or none.

`docs/templates/behavior-flows.md` should allow flow records to list
unit evidence bundle links when a flow is driven by a Claude Design
round-trip.

## Process changes

`docs/process/ui-definition.md` should add an intent/evidence
classification step between context collection and final UI contract
writing.

`docs/process/behavior-e2e-capture.md` should add a UI intent check
before behavior drafting. When a UI Definition exists, each behavior
record cites an interaction candidate. When none exists, the behavior
record must explicitly state `UI source: existing stable UI`.

`docs/process/behavior-e2e-gotchas.md` should promote this lesson:

> Agents must not collapse observed behavior into intended behavior. If
> code, docs, tests, and design artifacts disagree, the output is a
> mismatch, not a silent rewrite.

## Success criteria

- Agents can trace a unit from Claude Design artifacts to UI Definition,
  behavior records, implementation files, and tests.
- Interactive elements cannot enter behavior capture without status,
  evidence, and interaction candidates.
- Missing or unintended behavior is captured as a mismatch with a
  disposition.
- Claude Design generated code informs UI capture without becoming
  implementation authority.
- Behavior coverage can later evolve from binary `specified` /
  `test-written` into aspect-aware status without another process reset.
