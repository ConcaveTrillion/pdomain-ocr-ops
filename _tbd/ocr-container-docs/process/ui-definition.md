# UI Definition

> **Status: DRAFT - pending maintainer review.** This process defines the
> target shape of a new or redesigned user-facing unit before behavior
> capture and implementation planning begin.

## Agent Index

- **Kind:** process
- **Use when:** a UI, TUI, CLI, or component target shape must be defined.
- **Inputs:** product intent, design-system docs, prototypes, and repo map.
- **Outputs:** per-unit UI contracts under `docs/specs/ui/`.
- **Template:** `docs/templates/ui-unit-definition.md`
- **Feeds:** `docs/process/behavior-e2e-capture.md`
- **Upstream:** `docs/process/document-existing-repo.md`
- **Related:** `docs/architecture/design-system/`,
  `docs/process/writing-style.md`
- **Search terms:** UI definition, target UI, Claude Design handoff,
  screen spec, component spec, widget spec, selector inventory

## Purpose

UI Definition turns a maintainer's product intent, visual direction, and
workflow knowledge into an approved UI contract for one unit.

A *unit* can be a whole surface or a component inside a surface:

- Web / GUI: a screen, route, panel, drawer, dialog, toolbar, reusable
  component, or widget.
- TUI: a view, panel, modal, shared widget, or command palette.
- CLI: a command, subcommand, argument group, prompt, or output block.

Use the smallest unit that has a coherent job and behavior worth naming.
A page can have its own UI definition, and the important components on
that page can also have their own UI definitions. Shared components
should be defined once, then cited by the screens or views that compose
them.

The output is a per-unit UI definition under `docs/specs/ui/`. That file
names the layout, regions, elements, states, selectors, and interaction
candidates that behavior capture will use as its inventory.

## When to use

Use this process when:

- A screen, view, command, or behavior-bearing component does not exist
  yet.
- An existing unit is being redesigned.
- The current UI exists, but the intended workflow is unclear.
- Claude Design, another prototype tool, or the brainstorming visual
  companion produced a mockup that needs to become an implementation
  contract.

For an already-built and stable UI, skip this process and go straight to
`docs/process/behavior-e2e-capture.md`.

## Where docs live

Per-app target UI definitions live in:

```text
docs/specs/ui/
```

Use one file per unit. Prefix the filename with the unit kind:

```text
docs/specs/ui/screen-home.md
docs/specs/ui/view-review-queue.md
docs/specs/ui/command-run.md
docs/specs/ui/component-upload-dropzone.md
docs/specs/ui/component-job-status-card.md
```

Prototype exports and screenshots live beside the UI specs:

```text
docs/specs/ui/assets/<unit-slug>/
```

Keep reusable design-system rules in `docs/architecture/`, not in UI
specs. For example, tokens, primitives, app-shell contracts, and durable
layout rules belong under `docs/architecture/design-system/`. A UI spec
may cite those docs, but should not copy them.

Decision rule:

- If the doc answers "what should this workflow look like?", put it in
  `docs/specs/ui/`.
- If the doc answers "what reusable design rule should all workflows
  follow?", put it in `docs/architecture/`.

## Relationship to the rest of the process

```text
document-existing-repo.md
  -> ui-definition.md, when an existing repo has unclear or changing UI

brainstorming
  -> Claude Design or visual companion
  -> ui-definition.md
  -> behavior-e2e-capture.md
  -> writing-plans
  -> implementation
```

`superpowers:brainstorming` defines intent, constraints, success
criteria, and alternatives. Claude Design or the visual companion turns
that intent into one or more visual workflow options. UI Definition then
normalizes the approved option into a durable spec that behavior capture
can consume.

Behavior capture owns runtime behavior: triggers, observable output,
backend side effects, failure paths, tiers, regressions, and tests. UI
Definition owns target structure: layout, regions, element inventory,
states, selectors, accessibility notes, and responsive rules.

When documenting an existing repo from scratch, run
`docs/process/document-existing-repo.md` first. It inventories current
screens, commands, components, tests, and architecture, then routes only
unclear or changing UI units into this process.

## Agent Workflow

Use Superpowers before starting UI Definition work.

- In Codex, invoke the relevant `$superpowers:<skill>` form.
- In Claude, use the matching `/superpowers:<skill>` form.
- Use `brainstorming` when the target UI needs product or design choices.
- Use `dispatching-parallel-agents` for independent discovery.
- Use `verification-before-completion` before treating the UI contract as
  ready for behavior capture.

Keep user review for product and design decisions. Do not ask the user to
watch routine discovery.

When the work is autonomous, use parallel agents or subagents to gather
context:

- One agent inventories current routes, screens, and components.
- One agent maps existing tests, selectors, and behavior records.
- One agent checks design-system rules and reusable primitives.
- One agent finds similar screens or shared components in sibling repos.
- One agent reviews screenshots, prototypes, or Claude Design handoffs.

The parent agent owns the UI contract. Subagents return source-backed
findings and open questions. The parent agent decides which units need UI
definitions, which components are shared, and which questions require the
maintainer.

Surface items to the user when they affect the target UI:

- Which variant to approve.
- Which workflow is canonical.
- Whether a component should be shared.
- Whether current behavior is desired or accidental.
- Any naming choice that will become a durable selector or public prop.

## Claude Design handoff

Claude Design is a prototype generator, not the final source of truth.
Use it to explore variants, then turn the approved variant into a UI
definition file.

Before asking Claude Design for UI work, provide:

- Product goal and target user.
- The relevant `docs/architecture/design-system/` docs.
- Existing screenshots or routes, if any.
- Parent surfaces and child components, if the unit is composed.
- Known workflow constraints and non-goals.
- Required states: empty, loading, populated, error, disabled, and large
  data volume.
- Required naming discipline: every region and interactive element needs
  a stable name that can become a selector, widget id, or command arg.

Ask for 2-3 variants when the workflow is still open:

- Conservative: closest to existing app patterns.
- Workflow-first: optimized for repeated use.
- Recovery-first: optimized for bad states, review, and auditability.

After the maintainer picks a variant, ask Claude Design for an engineering
handoff with:

- Unit list, including shared components and their parent contexts.
- Region list.
- Element inventory.
- Component mapping.
- State table.
- Interaction table.
- Edge cases.
- Accessibility notes.
- Implementation assumptions.

Store the resulting link, export, screenshots, or bundle under the unit's
`docs/specs/ui/assets/<unit-slug>/` folder. The UI definition file links
to those artifacts and records which variant was approved.

## Per-unit process

Work one unit at a time.

1. **Collect context.** Read existing specs, architecture docs, design
   system docs, screenshots, routes, components, and tests.
2. **Define the unit.** Name the unit type, address, owner app, target
   user, main job, parent unit, child units, and whether the unit is
   shared.
3. **Prototype or sketch.** Use Claude Design, the visual companion, or a
   text sketch to explore the workflow.
4. **Choose the variant.** Record which option the maintainer approved and
   why.
5. **Write the UI contract.** Fill in the template from
   `docs/templates/ui-unit-definition.md`.
6. **Review states.** Confirm empty, loading, populated, error, disabled,
   and large-data states.
7. **Review selectors.** Every interactive element must have a stable
   selector, widget id, or command arg name before behavior capture starts.
8. **Handoff to behavior capture.** Use the element inventory and
   interaction candidates to draft behavior records.

## UI definition schema

Each UI definition must include:

- Unit metadata: type, address, implementation target, design-system
  inputs, prototype artifacts, parent unit, child units, and shared-use
  contexts.
- User goal: the job this unit helps the user complete.
- Layout regions: named areas and what each one contains.
- Element inventory: stable IDs, labels, roles, selectors, components,
  and state notes.
- State matrix: what changes across empty, loading, populated, error,
  disabled, and large-data states.
- Interaction candidates: user triggers and immediate UI responses.
- Responsive and accessibility notes: keyboard path, focus order, screen
  reader labels, and viewport behavior.
- Handoff to behavior capture: proposed behavior records, flow records,
  regressions, and open questions.

Shared units need one extra section: **Composition Contract**. It records
which props, slots, events, selectors, and state inputs the parent may
control. If a shared component behaves differently in different parents,
do not hide that behind one vague record. Define the shared baseline once,
then add context-specific behavior records in the parent unit or in a
clearly named component-context spec.

The template is intentionally strict because behavior capture depends on
the inventory. If an element can be clicked, typed into, focused, expanded,
submitted, dismissed, or selected, it needs a row in the inventory.

## Handoff contract

Behavior capture can start when the UI definition has:

- An approved variant or target shape.
- A stable unit slug.
- Parent and child unit links, when the unit is composed.
- A complete element inventory.
- Stable selector, widget id, or arg names for every interactive element.
- A state matrix that includes good and bad states.
- Interaction candidates that name the expected immediate UI response.
- Links to prototype artifacts or screenshots, if they exist.

The behavior spec should cite the UI definition source in its header.

Example:

```markdown
- **UI definition:** `docs/specs/ui/screen-home.md`
```

## Applying this to a new repo

1. Pick the interface profile: Web / GUI, TUI, or CLI.
2. Copy `docs/templates/ui-unit-definition.md` into the target repo's
   `docs/specs/ui/`.
3. Create one UI definition per unit. Use screen/view/command units for
   whole surfaces and component units for panels, dialogs, toolbars,
   reusable widgets, and other behavior-bearing pieces.
4. Store Claude Design exports and screenshots under
   `docs/specs/ui/assets/<unit-slug>/`.
5. Review the UI definition with the maintainer.
6. Start behavior capture only after the handoff contract is complete.

## Templates

Blank scaffolds live in `docs/templates/`:

- `ui-unit-definition.md` - per-unit UI definition skeleton for screens,
  views, commands, components, and widgets.
- `behavior-unit-spec.md` - per-unit behavior record skeleton.
- `behavior-flows.md` - cross-unit flow skeleton.
