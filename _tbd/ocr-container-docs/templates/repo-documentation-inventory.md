# Repo Documentation Inventory - <repo name>

> Template. Copy to `docs/research/YYYY-MM-DD-doc-audit.md` in the target
> repo and fill in before writing polished docs. See
> `docs/process/document-existing-repo.md` for the full process.

## Agent Index

- **Kind:** template
- **Use with:** `docs/process/document-existing-repo.md`
- **Copy to:** `docs/research/YYYY-MM-DD-doc-audit.md`
- **Purpose:** inventory an existing repo before writing durable docs.
- **Promote to:** `docs/architecture/`, `docs/specs/`, and `docs/runbooks/`
- **Search terms:** repo inventory, doc audit, module map, source map,
  existing repo documentation

- **Repo:** <name>
- **Date:** <YYYY-MM-DD>
- **Reviewer:** <name or agent>
- **Goal:** <why this repo is being documented>
- **Status:** draft | reviewed | promoted

## Repo Identity

- **Purpose:** <what this repo does today>
- **Primary users:** <end users, maintainers, agents, downstream packages>
- **Repo type:** app | library | CLI | shared UI | ops | mixed
- **Owns:** <responsibilities>
- **Does not own:** <boundaries>
- **Upstream deps:** <sibling packages, services, external tools>
- **Downstream consumers:** <apps/packages/repos that depend on this>

## Existing Signals Read

| Source | Path | What it says | Freshness / notes |
|--------|------|--------------|-------------------|
| README | `README.md` | <summary> | fresh/stale/unknown |
| Config | `<path>` | <summary> | fresh/stale/unknown |
| Tests | `<path>` | <summary> | fresh/stale/unknown |
| Docs | `<path>` | <summary> | fresh/stale/unknown |

## Source Map

### <area>

- **Path:** `<path>`
- **Responsibility:** <what it owns>
- **Public API / entrypoint:** <exports/commands/routes>
- **Notes:** <notes>

## Entrypoints

### <entrypoint>

- **Kind:** CLI | web | library | worker | generated export
- **Name:** <command, route, app, or export>
- **Path:** `<path>`
- **How it starts:** `<command ...>` or <import path>
- **Notes:** <notes>

## User-Facing Surfaces

Include whole screens/views/commands and behavior-bearing components.

### <unit>

- **Type:** screen | component | view | widget | command
- **Address:** <route/path/invocation>
- **Implementation:** `<path>`
- **Needs UI definition:** yes | no
- **Needs behavior capture:** yes | no
- **Notes:** <notes>

## Runtime Flows

### <flow>

- **Steps:** <high-level sequence>
- **Code paths:** `<path>` -> `<path>`
- **Data / side effects:** <files/api/state>
- **Notes:** <notes>

## Data And State

### <data or state name>

- **Location:** `<path>` or service
- **Owner:** <module>
- **Read/write paths:** <code paths>
- **Notes:** <notes>

## Generated Files And Ignored State

### `<path>`

- **Producer:** <command/module>
- **Consumer:** <command/module>
- **Safe to delete:** yes | no
- **Notes:** <notes>

## Verification

Mark commands honestly. Do not mark a command verified unless it was run
for this audit.

### <purpose>

- **Command:** `<command>`
- **Status:** verified | unverified | failing
- **Date:** <date>
- **Notes:** <output summary>

## Existing Docs To Keep

| Doc | Why it stays | Updates needed |
|-----|--------------|----------------|
| `<path>` | <reason> | <none or changes> |

## Docs To Create Or Update

### `<target doc>`

- **Purpose:** <purpose>
- **Source evidence:** <paths>
- **Priority:** high | medium | low

## Gaps And Risks

### <gap>

- **Evidence:** `<path>`
- **Impact:** <risk>
- **Recommended next step:** <action>

## Promotion Checklist

- [ ] Repo purpose and boundaries are documented.
- [ ] Source map covers the main modules and entrypoints.
- [ ] Runtime flows cover the important data/control paths.
- [ ] User-facing surfaces are listed.
- [ ] Shared components/widgets are listed once and linked to parents.
- [ ] Verification commands are marked verified or unverified.
- [ ] Stale docs are identified.
- [ ] Durable facts are promoted to `docs/architecture/`.
- [ ] Target UI or behavior work is routed to `docs/specs/`.
- [ ] Temporary findings stay in `docs/research/`.
