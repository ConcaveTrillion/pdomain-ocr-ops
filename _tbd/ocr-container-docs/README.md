# docs/

How documentation is organized in this repo.

## Agent Entrypoints

Use these process docs when an AI agent is indexing or documenting a repo:

- `process/document-existing-repo.md` - map an existing repo before work.
- `process/ui-definition.md` - define target UI, CLI, TUI, or component
  shape.
- `process/behavior-e2e-capture.md` - turn behavior into regression specs.
- `templates/repo-documentation-inventory.md` - first-pass repo inventory.
- `templates/ui-unit-definition.md` - per-unit UI contract.
- `templates/behavior-unit-spec.md` - per-unit behavior records.
- `templates/behavior-flows.md` - cross-unit behavior flows.

Reusable process docs should include an `Agent Index` near the top. Use
that block for low-token discovery before reading the full doc.

## Folder Index

### `architecture/`

- **Purpose:** durable reference for how the system works today.
- **Use when:** capturing modules, data flow, contracts, or current state.

### `archive/`

- **Purpose:** cold storage. Mirrors the active folders.
- **Use when:** a doc is shipped, superseded, or abandoned.

### `decisions/`

- **Purpose:** dated ADRs.
- **Use when:** recording a design choice with context and consequences.

### `plans/`

- **Purpose:** active execution order.
- **Use when:** sequencing work for an approved spec.

### `process/`

- **Purpose:** cross-cutting workflow conventions.
- **Use when:** capturing how the team works.
- **Note:** lint suppressions live at `process/lint-deviations.md`.
- `process/pdomain-release-and-index-dispatch.md` - pdomain release channels,
  index dispatch PAT permissions, and GitHub Actions policy.

### `research/`

- **Purpose:** investigations in progress.
- **Use when:** exploring before committing to a design.

### `runbooks/`

- **Purpose:** operational recipes.
- **Use when:** something is broken or being operated.

### `specs/`

- **Purpose:** aspirational, pre-implementation design.
- **Use when:** describing what to build before code.

### `templates/`

- **Purpose:** starter templates for docs and issues.
- **Use when:** adding a new doc type or boilerplate.

### `usage/`

- **Purpose:** downstream reference.
- **Use when:** a user or integrator needs to consume this app or library.

Empty folders are intentional and tracked via `.gitkeep`.

Active docs map to GitHub issues — see this repo's issue tracker for status.
This layout is workspace-standard; see
`/workspaces/ocr-container/docs/README.md` for the master.
