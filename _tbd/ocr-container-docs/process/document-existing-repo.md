# Document Existing Repo

> **Status: DRAFT - pending maintainer review.** This process documents
> what an existing repo does today before changing, redesigning, or
> expanding it.

## Agent Index

- **Kind:** process
- **Use when:** an existing repo needs a source-checked documentation map.
- **Inputs:** repo files, existing docs, tests, configs, CI, and runbooks.
- **Outputs:** repo inventory, architecture docs, runbooks, and gap list.
- **Template:** `docs/templates/repo-documentation-inventory.md`
- **Feeds:** `docs/process/ui-definition.md` and
  `docs/process/behavior-e2e-capture.md`
- **Related:** `docs/process/picking-up-cold.md`,
  `docs/process/writing-style.md`
- **Search terms:** document existing repo, repo map, architecture map,
  module map, doc audit, source inventory, stale docs, AI indexing

## Purpose

This process turns an existing repo into a navigable, source-checked set
of docs. A new agent, maintainer, or contributor should be able to answer:

- What does this repo do?
- What are its boundaries?
- How do I run, test, and verify it?
- Where are the main modules, entrypoints, commands, and user-facing
  surfaces?
- Which docs describe shipped architecture, target specs, behavior, and
  runbooks?
- What is stale, missing, risky, or unclear?

Document what exists today first. If discovery reveals a desired redesign,
missing behavior, or unclear workflow, record it as a gap and route it to
the right downstream process. Do not silently turn documentation work into
product design.

## When to use

Use this process when:

- A repo is poorly documented or stale.
- An agent is picking up a repo before feature work.
- A repo has working code but unclear architecture.
- Tests exist but their intent and coverage are hard to understand.
- User-facing workflows exist but are not captured in UI or behavior
  specs.
- A repo is being prepared for handoff, refactoring, migration, or shared
  ownership.

Use `docs/process/picking-up-cold.md` when the goal is to choose and ship
work. Use this process when the goal is to document the repo itself.

## Outputs

The main output is an inventory-backed doc set. Create only the docs the
repo actually needs.

Common outputs:

```text
docs/README.md
docs/architecture/overview.md
docs/architecture/module-map.md
docs/architecture/runtime-flows.md
docs/specs/ui/*.md
docs/specs/behavior/*.md
docs/runbooks/*.md
docs/research/YYYY-MM-DD-doc-audit.md
```

Use `docs/templates/repo-documentation-inventory.md` for the first pass.
The inventory can stay as a research artifact or become the checklist for
the doc update.

## Doc Placement Rules

Put durable facts in durable places:

- `docs/README.md` - index of the docs and how to read them.
- `docs/architecture/` - shipped architecture, module boundaries, data
  models, entrypoints, runtime flows, public APIs, and design-system rules.
- `docs/specs/` - target designs, planned behavior, accepted future
  changes, and implementation specs.
- `docs/specs/ui/` - target or captured UI definitions for screens,
  views, commands, components, and widgets.
- `docs/specs/behavior/` - behavior records and cross-unit flows.
- `docs/runbooks/` - local dev, operations, release, troubleshooting, and
  repeatable human procedures.
- `docs/research/` - temporary audits, discovery notes, comparisons, and
  gap reports.

Do not put target future behavior in architecture docs. Do not put
temporary audit notes in architecture docs. Promote only the stable facts
after review.

## Table And List Style

Keep docs readable in raw Markdown and rendered form.

- Put an `Agent Index` near the top of reusable process docs.
- Use stable headings that name the thing being indexed.
- Prefer explicit paths over "this file" or "above".
- Add search terms when a doc may be found by several names.
- Use tables only for short, regular data.
- Keep tables to four columns or fewer when practical.
- Use record blocks when fields may hold long paths, commands, or notes.
- Prefer this shape for dense inventory items:

```markdown
### <item name>

- **Path:** `<path>`
- **Owner:** <module>
- **Notes:** <notes>
```

Do not force long commands, routes, or explanations into table cells.

## Agent Workflow

Use Superpowers before starting repo documentation work.

- In Codex, invoke the relevant `$superpowers:<skill>` form.
- In Claude, use the matching `/superpowers:<skill>` form.
- Use `dispatching-parallel-agents` when two or more discovery tasks are
  independent.
- Use `verification-before-completion` before calling the doc pass done.
- Use `writing-plans` only if the audit turns into implementation work.

For a large repo, prefer parallel discovery over one long serial read.
Use parallel agents or subagents when the work is independent:

- One agent maps source modules and public APIs.
- One agent maps tests, fixtures, and verification commands.
- One agent maps user-facing screens, commands, and components.
- One agent maps existing docs, specs, runbooks, and stale claims.
- One agent maps CI, packaging, generated files, and ignored state.

The parent agent owns synthesis. Subagents should return source-backed
findings with paths, command names, and uncertainty. They should not make
final placement decisions alone. The parent agent merges findings into
the inventory, resolves conflicts, and chooses which facts belong in
architecture, specs, runbooks, or research.

Do not surface every discovery item to the user. Keep autonomous work
autonomous when it is source-checkable:

- Reading files.
- Mapping modules and commands.
- Listing tests and CI commands.
- Finding user-facing surfaces.
- Checking whether paths exist.
- Drafting inventory sections from code.

Surface items to the user when they need judgment:

- Conflicting sources of truth.
- Unclear product intent.
- Whether a stale behavior is still desired.
- Whether a surface should be redesigned.
- Whether a gap should become implementation work.

Before claiming the doc pass is complete, use the verification skill.
Check paths, commands, stale markers, raw Markdown readability, and any
commands that were marked verified.

## Process

Work in two passes: inventory first, polished docs second.

### 1. Bound The Repo

Identify:

- Repo name and package names.
- Product or library purpose.
- Primary users.
- What the repo owns.
- What the repo explicitly does not own.
- Upstream and downstream dependencies.
- Whether it is an app, library, shared UI package, ops package, CLI, or
  mixed repo.

Write this in the inventory before editing long-form docs.

### 2. Read The Existing Signals

Read the files that define how the repo works:

- `README.md`
- `CLAUDE.md`, `CONVENTIONS.md`, and agent memory where applicable
- `pyproject.toml`, `package.json`, `Makefile`, `tox.ini`, `uv.lock`,
  `pnpm-lock.yaml`, or equivalents
- Existing `docs/`
- Entry points, routes, command modules, app startup files, public exports
- Tests and fixtures
- CI workflows
- Recent specs, plans, handoffs, and runbooks

Record exact paths in the inventory. If a source is stale or contradicts
code, mark it as a gap.

### 3. Build The Repo Map

Create a map of the repo at the level a future worker needs:

- Source roots and packages.
- Main modules and what each owns.
- Public APIs and exports.
- CLI commands, subcommands, prompts, and output blocks.
- Web / GUI screens, routes, panels, dialogs, drawers, toolbars,
  components, and widgets.
- TUI views, panels, modals, and widgets.
- Background jobs, workers, queues, schedulers, or long-running tasks.
- Data files, generated files, cache dirs, and persistent state.
- External services, sibling packages, and local-dev dependencies.
- Test suites, fixtures, and verification commands.

Prefer a short table over prose. The goal is fast orientation.

### 4. Capture Runtime Flows

Document the major data and control flows that explain how the repo
works. Examples:

- CLI invocation to output files.
- Upload to backend job to result screen.
- Frontend action to API call to persisted state.
- Library public function to internal pipeline.
- Background job dispatch to completion.
- Shared UI component props to emitted events.

Keep this at the architecture level. Behavior specs can later turn
user-facing flows into testable records.

### 5. Capture User-Facing Surfaces

For every behavior-bearing surface, decide what it needs:

- If it exists and is stable, document its current shape in the repo map
  and, when useful, seed `docs/specs/ui/`.
- If its intended target shape is unclear or changing, run
  `docs/process/ui-definition.md`.
- If its behavior needs regression coverage, run
  `docs/process/behavior-e2e-capture.md`.
- If it is internal and stable, keep it in architecture docs unless it
  needs a runbook or behavior spec.

A unit can be a whole surface or a component inside a surface. Shared
components should be documented once and composed by parent screens,
views, or flows.

### 6. Capture Verification

Document how to verify the repo:

- Main test command.
- Lint, format, typecheck, build, and package commands.
- E2E commands and required services.
- Slow, GPU, network, or opt-in test tiers.
- Required environment variables.
- Known local-dev modes.
- CI entrypoints.

Run commands when practical. Mark each command as `verified` or
`unverified` with the date. Do not present an unrun command as known-good.

### 7. Write Or Update Docs

Promote inventory findings into the smallest useful doc set:

- `docs/README.md` for navigation.
- `docs/architecture/overview.md` for the repo's purpose, boundaries, and
  shape.
- `docs/architecture/module-map.md` for source layout and ownership.
- `docs/architecture/runtime-flows.md` for important data/control flows.
- `docs/runbooks/*.md` for repeatable operations.
- `docs/specs/ui/*.md` and `docs/specs/behavior/*.md` only when the repo
  needs UI or behavior capture.

Keep docs source-checked. Cite paths for important claims.

### 8. Record Gaps

End with a short gap list:

- Stale or contradictory docs.
- Undocumented public APIs.
- Undocumented user-facing surfaces.
- Missing behavior records.
- Missing or unclear tests.
- Risky modules that need deeper architecture docs.
- Decisions that require maintainer input.

Put temporary findings in `docs/research/YYYY-MM-DD-doc-audit.md` if they
are too noisy for durable docs.

### 9. Self-Review

Before handing off, check:

- Every important path exists.
- Commands are marked verified or unverified.
- Architecture docs describe current code, not desired future code.
- Target designs live under `docs/specs/`, not `docs/architecture/`.
- Temporary audit notes stayed in `docs/research/`.
- User-facing surfaces are routed to UI Definition or Behavior Capture
  when needed.
- The doc set has a clear next step for any gap.

## Relationship To Other Processes

This process sits upstream of UI Definition and Behavior Capture.

```text
document-existing-repo.md
  -> ui-definition.md, when target UI shape is unclear or changing
  -> behavior-e2e-capture.md, when shipped behavior needs regression specs
  -> writing-plans, when the doc audit identifies implementation work
```

Use this process to learn and document the repo. Use UI Definition to
define target surfaces. Use Behavior Capture to turn user-visible
behavior into testable records.

## Template

Start with:

```text
docs/templates/repo-documentation-inventory.md
```

Copy it into the target repo as:

```text
docs/research/YYYY-MM-DD-doc-audit.md
```

Then promote stable findings into architecture, specs, and runbooks.
