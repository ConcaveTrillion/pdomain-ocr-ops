---
status: draft
date: 2026-05-19
repo: ConcaveTrillion/ocr-container-meta
---

# Workspace `docs/` folder template

Standardized `docs/` layout for every repo CT actively edits in the
`/workspaces/ocr-container/` workspace. Applies to all 13 repos: 8 `pd-*`
projects + `pdomain-ops` + `pdomain-ui` + `pdomain-ocr-simple-gui` + `se-llm-skills` +
the workspace root itself.

## Context — why

Each repo's `docs/` tree grew ad-hoc. Today's layouts include `architecture/`,
`archive/`, `audit/`, `design-brief/`, `futures/`, `milestones/`, `planning/`,
`review/`, `review-notes/`, `roadmap/`, `specs/`, `superpowers/`, `usage/` —
no two repos match. New contributors (human or AI) can't predict where a
given doc lives. Superpowers skills hard-code `docs/superpowers/{specs,plans}/`,
forcing repos into a sub-namespace they don't otherwise use.

This spec defines a single nine-folder schema, an empty-folder convention, a
canonical `docs/README.md`, a per-repo `CLAUDE.md` block that redirects
superpowers writes, a scaffold script for new and existing repos, and a
two-pass migration for existing content.

## §1. Folder schema

Each repo's `docs/` has exactly ten top-level entries: nine active folders
plus `archive/`, where `archive/` mirrors the nine active folders.

```
docs/
├── README.md
├── architecture/       # durable reference: how the system works today
├── archive/            # cold storage; mirrors the nine active folders
│   ├── architecture/
│   ├── decisions/
│   ├── plans/
│   ├── process/
│   ├── research/
│   ├── runbooks/
│   ├── specs/
│   ├── templates/
│   └── usage/
├── decisions/          # ADRs: dated, append-only design choices
├── plans/              # active execution: what order to make a spec real
├── process/            # cross-cutting workflow conventions
├── research/           # investigation in progress; messy by design
├── runbooks/           # operational reference: something is broken
├── specs/              # aspirational, pre-implementation design
├── templates/          # issue / spec / plan / ADR boilerplate
└── usage/              # downstream reference: how to consume this
```

Genre categorization (architecture vs decisions vs plans, etc.) is exactly
one level deep. Topic subfolders *inside* a category are allowed when an
area accumulates many files (e.g. `docs/specs/labeler/`).

## §2. Empty-folder marker

Every empty folder (active and archive) contains a single `.gitkeep` file.
The scaffold script writes them; nobody edits them. Convention follows the
existing precedent at `pdomain-prep-for-pgdp/docs/design-brief/existing-ui/screenshots/.gitkeep`.

## §3. `docs/README.md` (canonical template)

A single ~40-line file, identical structure in every repo. The repo's own
name is the only variable; the table itself is byte-identical workspace-wide.

```markdown
# docs/

How documentation is organized in this repo.

| Folder | Purpose | Use when |
|---|---|---|
| `architecture/` | Durable reference — how the system works today. | Capturing current shape (modules, data flow, contracts, current-state diagrams). |
| `archive/` | Cold storage. Mirrors the nine active folders. | A doc is no longer in force (shipped, superseded, abandoned). |
| `decisions/` | ADRs — dated, append-only "we chose X because Y." | Recording a specific design choice with context, alternatives, consequences. |
| `plans/` | Active execution — what order to make a spec real. | Sequencing work for an approved spec. |
| `process/` | Cross-cutting workflow conventions (verification rules, merge strategy, release process). | Capturing how the team works, not what the system does. |
| `research/` | Investigation in progress. Messy by design. | Exploring before committing to a design. |
| `runbooks/` | Operational reference — something is broken or being operated. | An on-call or ops task needs a recipe. |
| `specs/` | Aspirational, pre-implementation design. | Describing what to build, before code. |
| `templates/` | Issue, spec, plan, ADR boilerplate. | Adding a starter template for a new doc type. |
| `usage/` | Downstream reference — how to consume this app/tool/library. | A user or integrator needs to know how to use it. |

Empty folders are intentional and tracked via `.gitkeep`.

Active docs map to GitHub issues — see this repo's issue tracker for status.
This layout is workspace-standard; see
`/workspaces/ocr-container/docs/README.md` for the master.
```

## §4. Per-repo `CLAUDE.md` addition

Every repo's `CLAUDE.md` (and the workspace's) gains one short block:

```markdown
## docs/ folder

This repo follows the workspace docs/ template — see `docs/README.md`. Active
folders: `architecture/`, `decisions/`, `plans/`, `process/`, `research/`,
`runbooks/`, `specs/`, `templates/`, `usage/`, plus parallel `archive/`
subfolders.

**Superpowers redirect.** When a superpowers skill (e.g. `brainstorming`,
`writing-plans`) instructs you to save to `docs/superpowers/specs/<file>.md`
or `docs/superpowers/plans/<file>.md`, save to `docs/specs/<file>.md` or
`docs/plans/<file>.md` instead. There is no `docs/superpowers/` subdirectory
in this repo.
```

## §5. `scripts/scaffold-docs.sh`

Single Bash script at `/workspaces/ocr-container/scripts/scaffold-docs.sh`.
Idempotent. Two modes:

```bash
scaffold-docs.sh <repo-path>             # create or top up missing pieces
scaffold-docs.sh <repo-path> --check     # verify; exit nonzero on drift
scaffold-docs.sh <repo-path> --force     # overwrite docs/README.md from template
```

Behavior (creation mode):

1. `mkdir -p docs/{architecture,decisions,plans,process,research,runbooks,specs,templates,usage}`
2. `mkdir -p docs/archive/{architecture,decisions,plans,process,research,runbooks,specs,templates,usage}`
3. `touch <each-folder>/.gitkeep` — but only for folders currently empty.
4. Write `docs/README.md` from the §3 template if absent (or always under `--force`).
5. Print a one-line summary of created/skipped paths.

Does **not** modify `CLAUDE.md`. That's a separate per-repo edit so each
repo keeps its own surrounding context.

`--check` mode prints `MISSING: <path>` for each gap and exits 1 if any.
Suitable for CI or a pre-commit hook later.

## §6. Existing-content migration

Companion script: `/workspaces/ocr-container/scripts/migrate-docs.sh`.
Two passes per repo.

### Pass 1 — scripted obvious moves

Pure `git mv` operations for well-known source paths:

| Source | Destination |
|---|---|
| `docs/superpowers/plans/*.md` | `docs/plans/*.md` |
| `docs/superpowers/specs/*.md` | `docs/specs/*.md` |
| `docs/superpowers/research/*.md` | `docs/research/*.md` |
| `docs/superpowers/decisions/*.md` | `docs/decisions/*.md` |
| `docs/superpowers/reminders/*.md` | `docs/runbooks/*.md` |
| `docs/usage/*` (already named correctly) | `docs/usage/*` (no-op) |
| `docs/architecture/*` (already named) | `docs/architecture/*` (no-op) |

After the moves, empty legacy directories are removed and any newly-empty
active folder gets a `.gitkeep`.

### Pass 2 — dry-run report for ambiguous content

Every doc not handled in Pass 1 is printed with a *suggested* home; you
confirm or override before moves happen. No silent classification. Examples
the dry-run will surface:

| Repo | Source | Suggested |
|---|---|---|
| workspace | `docs/superpowers/*.md` (loose handoffs, bot-workspaces, ship-issue-interactive, …) | `docs/process/` for workflow rules; `docs/architecture/` for durable reference; `docs/archive/research/` for ephemeral handoffs |
| workspace | `docs/doc-cleanup-plan.md`, `docs/label-taxonomy.md`, `docs/python-coding-guidelines.md`, `docs/update-post.md` | hand-curated |
| pd-ocr-labeler | `docs/planning/*` | `docs/plans/` or `docs/archive/plans/` |
| pdomain-prep-for-pgdp | `docs/audit/*` | `docs/archive/architecture/` |
| pdomain-prep-for-pgdp | `docs/design-brief/*` | `docs/specs/` or `docs/archive/specs/` |
| pdomain-prep-for-pgdp | `docs/futures/*` | `docs/specs/` |
| pd-ocr-labeler | `docs/review/*`, `docs/review-notes/*` | `docs/archive/research/` |
| pdomain-book-tools | `docs/review/*` | `docs/archive/research/` |
| pdomain-ocr-synth | `docs/roadmap/*` | `docs/plans/` or `docs/archive/plans/` |
| pd-png-optimizer | `docs/milestones/*` | `docs/plans/` or `docs/archive/plans/` |

Pass 2 output format (one row per file, machine-parseable):

```
<repo>\t<src-path>\t<suggested-dst>\t<rationale-tag>
```

The user reviews the report, accepts/edits, and re-runs the script with
`--apply <approved-file>`.

### Migration commit shape

One commit per repo: `docs: migrate to workspace-standard layout`. Use
`git mv` exclusively so history follows. Don't bundle migration with any
content edits — pure restructuring only.

## §7. Issue reconnection (deferred)

Captured here, **not** done as part of this work. Two things will need
attention after migration:

1. **Plan frontmatter `repo:` field** — no change needed; it names a GitHub
   repo, not a path.
2. **GitHub issue bodies that reference doc paths** — any
   `Spec: docs/superpowers/specs/<file>.md` line in an issue body becomes
   stale. A follow-up pass will `grep` issue bodies for `docs/superpowers/`
   and `gh issue edit` to update them. Out of scope for this design.

The `decompose-spec --sync` flow already accepts `--plan <path>` and is
path-agnostic, so it keeps working without code changes.

## §8. Rollout sequence

Pilot order (small → high-value → parallel batch):

1. **`pdomain-ocr-cli`** — empty `docs/` today. Pure scaffold test; zero
   migration. Validates §5.
2. **`pdomain-book-tools`** — small, already partially structured (`docs/review/`,
   `docs/specs/`). Validates §6 migration on a low-risk repo.
3. **Workspace root `/workspaces/ocr-container/docs/`** — biggest content
   (17 plans + 14 specs + decisions/research/reminders/handoffs + loose
   top-level files). Highest-value, most ambiguous content. Validates §6
   dry-run report.
4. **Remaining 10 repos in parallel batches** — once scaffold + migrate
   scripts are battle-tested, fan them out.

Per-repo work after the scripts run:

- Append the §4 `CLAUDE.md` block.
- Manually file the Pass-2 ambiguous content using the dry-run report.
- Commit (`docs: migrate to workspace-standard layout`).

## §9. Open follow-ups

Tracked as separate work after this spec ships:

- **F1. Issue-reconnection sweep.** `gh search issues body:'docs/superpowers/'`
  across all repos; update bodies via `gh issue edit` to point at new paths.
- **F2. CI check.** Add `scaffold-docs.sh --check` as a pre-commit hook or CI
  step in each repo so drift is caught early.
- **F3. Upstream PR (optional).** Propose configurable `paths.specs` /
  `paths.plans` in superpowers itself, so future repos don't need the §4
  CLAUDE.md instruction. Low priority — instruction works.

## §10. Implementation notes (post-rollout addendum, 2026-05-19)

Captured after executing the rollout against all 13 repos. None of these
change the design; they record where reality diverged from §1–§8 and the
small adjustments that landed.

### Canonical README table style — padded, not compact

§3 originally showed `|---|---|---|` (compact table style). Several repo
`.markdownlint-cli2.jsonc` configs default to "compact = false" which then
fails MD060/table-column-style on those tight separators. The template
was updated mid-rollout to padded form (`| --- | --- | --- |`), accepted
by every config. The `scaffold-docs.sh --force` mode was used to update
already-migrated repos. The template at
`scripts/templates/docs-readme.md` is the authoritative form.

### Pass-2 report format — three columns, not four

§6 specifies `<repo>\t<src-path>\t<suggested-dst>\t<rationale-tag>` (4 cols
with repo prefix). The implementation emits 3 cols (`<src>\t<dst>\t<reason>`);
the `--apply` reader matches. Since the script is invoked per-repo
(`migrate-docs.sh <repo>`), repo context is already an argument. The
simplification is internally consistent and the round-trip works.

### Per-repo markdownlint ignores

Every repo that runs markdownlint via pre-commit needed at least one
ignore added before migration files could land:

- `docs/archive/**` — historical content frequently violates current
  style rules; freeze it rather than rewrite.
- `docs/plans/**` — plans inherit prose styles from upstream sources
  (pasted from other docs, agent-generated, etc.) where uniformity isn't
  worth gating commits over.

Repos `pdomain-ops` and `pdomain-ocr-simple-gui` lacked a
`.markdownlint-cli2.jsonc` entirely; both got one (copied from
`pdomain-ocr-cli`) with the two ignores plus MD013/MD060 disables.

### Untracked files in legacy locations

Some repos had untracked content under `docs/superpowers/` that the script's
`git mv -k` would not move (it skips untracked sources). Workaround used:
plain `mv` for untracked files before `git add` at commit time. This came
up in the workspace (one new plan) and pdomain-prep-for-pgdp (the entire
`docs/superpowers/` directory was untracked).

### Nested `archived/` subfolders inside legacy directories

Several legacy folders had their own `archived/` subdirectory (e.g.,
`docs/superpowers/plans/archived/`, `docs/review/archive/`,
`docs/superpowers/research/archived/`). Pass 1 only handled top-level
files inside the named legacy folders. Each `archived/` child needed an
inline `git mv` loop to land at `docs/archive/<type>/`. The migration
script's Pass-1 list could be extended in a future patch but the
ad-hoc loops were small enough not to warrant it.

### Gitignored regenerator artifacts

Per-repo `docs/spec-chain-report.md` and the workspace's
`docs/superpowers/spec-chain-status.md` were referenced as gitignored
"hourly-regenerated" artifacts. Inspection showed the regenerator was
retired (the on-disk files were stale, mtime 2026-05-14). Cleanup was
to delete the artifacts and remove the `.gitignore` entries rather than
redirect output paths. If a regenerator returns, re-add entries at the
new path.

### pdomain-ocr-cli was NOT empty

§8 picked `pdomain-ocr-cli` as the "pure scaffold" pilot on the assumption
that its `docs/` was empty. It actually held five loose top-level
markdown files (`usage.md`, `layout-aware-ocr.md`, `ROADMAP.md`,
`dev-local-upgrade-flow.md`, `spec-chain-report.md`). All five were
hand-curated. The pilot still served its purpose (validating the
scaffold path), but the assumption that any repo's `docs/` is "empty"
is risky; always inspect first.

### `run_test` harness mechanic

The plan's test snippets define `run_test() { CURRENT_TEST="$1"; shift;
"$@"; }` and call it as `run_test test_foo` (single arg). After
`shift`, `$@` is empty — the test function never runs. The implementer
applied a two-arg workaround (`run_test test_foo test_foo`), and a
subsequent refactor switched the function to single-arg form (`"$1"`).
The current `scripts/tests/lib.sh` has the simpler form; future plans
should follow it.

### CLAUDE.md append gotchas

Several mishaps appending the §4 block to per-repo `CLAUDE.md`:

- A leading newline in the appended heredoc combined with the file's
  trailing newline produced two consecutive blanks (MD012 failure).
  Fixed pattern: trim trailing newlines from the file first, then
  append with one separating blank.
- One repo (`pdomain-ops`) had no pre-existing `CLAUDE.md`; the append
  created a header-less file. Added a `# CLAUDE — pdomain-ops` title +
  short description.
- `pd-* suite` and similar phrases with bare `*` triggered MD037
  ("spaces inside emphasis"); backtick-wrap (`` `pd-*` ``) avoids it.

### Updated path references vs intentional legacy quotes

The follow-up sweep updated active references (`docs/superpowers/X/` →
`docs/X/`) across CLAUDE.md, scripts, agent prompts, and active plans/
specs. It deliberately preserved:

- `scripts/migrate-docs.sh` and its tests (operational migration code).
- `CLAUDE.md` §4 superpowers-redirect blocks (must quote legacy paths
  to describe the redirect).
- This spec and its plan (describe the migration, quote legacy paths).
- `docs/archive/**` (historical snapshots, frozen at the form they
  shipped in).
