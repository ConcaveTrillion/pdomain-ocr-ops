---
milestone: 2
repo: ConcaveTrillion/ocr-container-meta
status: complete
synced: 2026-05-17
---

# Workspace agent definitions for pdomain-ui and pdomain-ocr-ops

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Scope

Implements Phase 1 Track 1.6 of the cross-cut design spec
([docs/superpowers/specs/2026-05-16-cross-cut-design.md §7.1, row 1.6](../specs/2026-05-16-cross-cut-design.md)):
create the four workspace-level agent definition files for the two new
foundation repos introduced by the spec — `pdomain-ui` (TS/React shared
frontend lib) and `pdomain-ocr-ops` (Python shared ops + suite plumbing) —
plus update the workspace-level `CLAUDE.md` routing table so those repos
are reachable through the standard `<repo>` / `<repo>-docs` agent pair
convention every other pd-* project already uses.

This plan is **agent-prompt scaffolding only**. The `pdomain-ui/` and
`pdomain-ocr-ops/` repo trees do not exist yet; this plan deliberately does
not create them. Each full-power agent runs the standard
pre-flight identity check (cwd vs expected repo path) and will report
"wrong directory" until the repos are scaffolded by their own future
plans — that is intended and acceptable. This plan unblocks
delegation-by-name (`subagent_type="pdomain-ui"`, `subagent_type="pdomain-ocr-ops"`,
plus their `-docs` siblings) so that the spec's other Phase 1 tracks
(1.3 pdomain-ocr-ops, 1.5 pdomain-ui) can be delegated to per-repo agents the
moment those repos are scaffolded.

**Structural template:** mirror the existing `pdomain-prep-for-pgdp` agent
pair (`.claude/agents/pdomain-prep-for-pgdp.md` + `pdomain-prep-for-pgdp-docs.md`)
for `pdomain-ocr-ops`, and the existing `pdomain-ocr-labeler-spa` pair (which also
includes a pre-flight identity check) for `pdomain-ui`. Skim
`.claude/agents/pdomain-book-tools{,-docs}.md` for variations on the
"foundation library that everyone else depends on" framing — `pdomain-ui` and
`pdomain-ocr-ops` are both new foundation libraries.

**Working directory for all commands:** `/workspaces/ocr-container/`

---

## Task 1: Write `.claude/agents/pdomain-ui.md` (full-power agent) {#write-claudeagentspd-uimd-full-power-agent}

**Why:** Without a `pdomain-ui` subagent the workspace cannot route work to
the new shared frontend library; every parent context would have to edit
`pdomain-ui/` directly, violating the workspace-level rule that each `pd-*`
tree is owned by its dedicated agent. The agent is needed before track
1.5 (scaffold `pdomain-ui` repo) so the scaffold work itself can be
delegated.

**What:** Create `/workspaces/ocr-container/.claude/agents/pdomain-ui.md`,
mirroring the shape of
`/workspaces/ocr-container/.claude/agents/pdomain-prep-for-pgdp.md` (also
borrow the `## Pre-flight identity check` block from
`pdomain-ocr-labeler-spa.md` — `pdomain-ui` ships first as spec-only and the
identity check guards against a stale cwd landing the agent in a sibling
repo, just like the labeler-spa case).

Files:

- Create: `.claude/agents/pdomain-ui.md`

- [ ] **Step 1: Write the YAML front-matter**

The front-matter must include:

- `name: pdomain-ui` (exact, matches the filename).
- `description:` — phrased as a `MUST BE USED PROACTIVELY for any work
  in the pdomain-ui repo` sentence per the existing convention. Trigger
  words to include explicitly (so fuzzy dispatch picks the right agent):
  `pdomain-ui`, `@concavetrillion/pdomain-ui`, `shared frontend library`,
  `PageImageCanvas`, `WordList`, `AppShell`, `launcherSlot`, `pd-suite.json`,
  `UIPrefs`, `pdomain-ui icons`, `tokens.css`, `primitives.css`,
  `pdomain-index-npm`, `useSuiteSiblings`, `useStageCall`, `useLongJob`,
  and the path anchor `anything under /workspaces/ocr-container/pdomain-ui/`.
- `memory: project` (mirrors other full-power agents).

- [ ] **Step 2: Write the `Pre-flight identity check` block**

Adapt the corresponding section from
`pdomain-ocr-labeler-spa.md` (it is the only existing template that handles
the "repo may not exist yet" case implicitly via the cwd + git toplevel
check). Specifically:

- cwd target: `/workspaces/ocr-container/pdomain-ui/`.
- `git rev-parse --show-toplevel` must return that exact path.
- Verify the loaded agent file is this one by `head -2`-ing the agent
  prompt and confirming the `name:` line is `pdomain-ui`.
- If the repo does not exist yet, the agent should **stop, do no
  work, and reply with a routing-error notice** that says so — the
  human caller is then responsible for scaffolding the repo (which is
  itself a future plan's job, not this one's).

Also list the sibling naming traps explicitly (`pdomain-ui-docs` is the
read-only Haiku sibling — not this agent; do not silently merge the
two).

- [ ] **Step 3: Write the `Persistent memory` block**

Reuse the standard text from `pdomain-prep-for-pgdp.md` verbatim shape,
substituting:

- Memory directory:
  `/workspaces/ocr-container/.claude/agent-memory/pdomain-ui/`.
- The "things future sessions would otherwise re-discover" hints
  appropriate to a TS library: codegen pipeline quirks
  (`codegen:fetch` / `codegen:emit` / `codegen:tsgen` /
  `codegen:check`), Storybook conventions, Konva slot patterns
  promoted out of `pdomain-ocr-labeler-spa`, design-system token sync
  script behavior, Zustand store-factory gotchas, Radix-vs-CSS
  primitives split rules, lucide-react re-export discipline.
- Repeat the "always write to the absolute path above" rule and the
  workspace-leakage check (per
  [workspace CLAUDE.md "Agent memory" section](../../../CLAUDE.md)).

- [ ] **Step 4: Write the `What this repo is` block**

Two short paragraphs:

1. The TS/React shared frontend library that other pd-* SPAs (labeler,
   pgdp-prep, future trainer-spa, future simple-gui, future
   proofreader) import via `@concavetrillion/pdomain-ui` from the
   self-hosted `pdomain-index-npm` registry.
2. Owns the runtime canonical copy of the workspace
   `docs/design-system/` (`tokens.css` + `primitives.css`) plus the
   slot-based canvas, virtualized worklist, AppShell + launcher, curated
   icon module, structural type contract (codegen from `pdomain-book-tools`
   + `pdomain-ocr-ops`), Zustand store factories, and the `testids`
   constants catalog the Playwright drivers depend on.

Cite the spec for both surfaces:
[spec §3 (Repo & release layout)](../specs/2026-05-16-cross-cut-design.md#3-repo--release-layout-install--discovery-model)
and
[spec §4 (Component surface inside pdomain-ui)](../specs/2026-05-16-cross-cut-design.md#4-component-surface-inside-pdomain-ui).

- [ ] **Step 5: Write the `Stack & layout (planned)` block**

Match the structure of
`pdomain-ocr-labeler-spa.md` §"Stack & layout (planned)":

- Frontend lib: TS, Vite-library mode, ESM, tree-shakeable subpath
  imports (`/canvas`, `/worklist`, `/shell`, `/primitives`, `/icons`,
  `/types`, `/stores`, `/theme`, `/testids` — per spec §4).
- Build tooling: pnpm; `mise.toml` pins Node 24.
- Tests: Vitest unit + Storybook stories double as visual smokes.
- Codegen: `.codegen/` dir for pinned wheels + emitted JSON Schema;
  `src/types/generated/` is **committed** so PRs surface drift.
- Publish target: `pdomain-index-npm` (self-hosted Verdaccio-style on
  GitHub Pages).
- Dependencies of note: React, Konva, Zustand, Radix UI primitives
  (only behavior-heavy components per spec §4), lucide-react
  (re-exported only via `/icons` — apps never import directly).
- Hard exclusions: no `class-variance-authority` (spec §4 + §9 P1
  criteria); Tailwind allowed for layout utilities only, not color or
  theme (enforced via Tailwind safelist or lint rule per spec §9).

- [ ] **Step 6: Write the `Read these first` block**

List in order: `README.md`, `CONTRIBUTING.md` if present, the workspace
`docs/superpowers/specs/2026-05-16-cross-cut-design.md` (canonical
design — cite via the relative path `../../../docs/superpowers/specs/...`
since the agent's cwd will be `/workspaces/ocr-container/pdomain-ui/`),
`docs/design-system/DESIGN_LANGUAGE.md` (workspace-level — the design
language pdomain-ui's `theme/` mirrors), Storybook entry index when present.

Note that the spec is the authoritative source of design intent until
the per-repo specs are in place inside `pdomain-ui/specs/`.

- [ ] **Step 7: Write the `Standard workflow` block**

Mirror `pdomain-prep-for-pgdp.md`'s shape, adapted for a TS-only library:

- `make help` for targets (once the Makefile exists).
- Before reporting done: `pnpm format`, `pnpm lint`, `pnpm test`
  (Vitest), `pnpm build` (Vite library build), `pnpm storybook:build`.
- Codegen: `pnpm codegen:check` must be clean — if it fails, run
  `pnpm codegen` and commit the regenerated `src/types/generated/`.
- A bumped `pdomain-book-tools` or `pdomain-ocr-ops` dep requires regenerated
  types or CI fails (spec §5 codegen pipeline).
- Storybook dev loop: `pnpm storybook` while iterating; cover both
  `:root` (dark default) and `[data-theme="light"]` per spec §9
  Phase-1-done criteria.

- [ ] **Step 8: Write the `Inter-repo awareness` block**

Bullets:

- **`pdomain-book-tools`** is the upstream source-of-truth for domain types;
  pdomain-ui consumes JSON Schema via `python -m pd_book_tools.schemas.emit`
  (see plan
  [docs/superpowers/plans/2026-05-16-pdomain-book-tools-review-metadata-and-schemas-emit.md](2026-05-16-pdomain-book-tools-review-metadata-and-schemas-emit.md)).
  Cross-repo questions: dispatch `pdomain-book-tools-docs`.
- **`pdomain-ocr-ops`** is the parallel Python foundation; pdomain-ui mounts its
  contract URLs (`/api/suite/prefs`, `/api/suite/installed`,
  `/api/suite/launch`) as callbacks at root. Cross-repo questions:
  dispatch `pdomain-ocr-ops-docs`.
- **`pdomain-ocr-labeler-spa`** is the donor: its `PageImageCanvas.tsx`,
  `Worklist.tsx`, and `StudioShell` are ported into pdomain-ui as slot-based
  components (spec §7 Phase 2). Read-only via `pdomain-ocr-labeler-spa-docs`
  for spec context.
- **`pdomain-prep-for-pgdp`** is the structural model for the FastAPI side
  (relevant when reasoning about how apps will wire pdomain-ui+pdomain-ocr-ops);
  cross-repo questions via `pdomain-prep-for-pgdp-docs`.
- Reads of sibling pd-* repos are allowed via their `-docs` agents;
  edits to siblings are out of scope.

- [ ] **Step 9: Write the `Quirks / gotchas` and `Out of scope` blocks**

Quirks to call out:

- The `src/types/generated/` directory is committed — never edit by
  hand; regenerate via `pnpm codegen`.
- Tokens are CSS custom properties; no hex literals in component code
  (spec §4 key API conventions).
- Zustand stores are factory functions — never export top-level
  singletons (spec §4 key API conventions #3).
- `/testids` constants are a Playwright-driver contract; renaming a
  testid is a breaking change to every consumer.
- `class-variance-authority` is forbidden; component variants are CSS
  class modifiers.
- Tailwind is configured to forbid color/theme utilities.

Out-of-scope:

- Editing outside `/workspaces/ocr-container/pdomain-ui/`.
- Editing `pdomain-book-tools` (route to its agent), `pdomain-ocr-ops` (route to
  its agent), or any consumer app.
- Publishing to `pdomain-index-npm` without explicit user approval.

- [ ] **Step 10: Verification — structural checks**

After writing, run:

```bash
# Front-matter loads cleanly (no YAML syntax errors).
head -10 /workspaces/ocr-container/.claude/agents/pdomain-ui.md

# The required identity-check sentinel is present.
grep -n "Pre-flight identity check" /workspaces/ocr-container/.claude/agents/pdomain-ui.md

# The agent name matches the filename.
grep -n "^name: pdomain-ui$" /workspaces/ocr-container/.claude/agents/pdomain-ui.md

# Memory path is the workspace-canonical absolute path.
grep -n "/workspaces/ocr-container/.claude/agent-memory/pdomain-ui/" \
  /workspaces/ocr-container/.claude/agents/pdomain-ui.md
```

Each grep must return at least one match. The `name:` line must match
exactly `name: pdomain-ui` (no whitespace drift). YAML front-matter must
parse (the file should start with `---` and the closing `---` should be
present before the prose body).

**Acceptance:**

- File exists at `.claude/agents/pdomain-ui.md`.
- YAML front-matter parses; `name: pdomain-ui` exactly.
- Description includes the trigger words enumerated in Step 1.
- Identity-check, memory, what-this-repo-is, stack, read-these-first,
  workflow, inter-repo, quirks, and out-of-scope sections are all
  present.
- Memory path is the absolute workspace-canonical path.

---

## Task 2: Write `.claude/agents/pdomain-ui-docs.md` (read-only Haiku) {#write-claudeagentspd-ui-docsmd-read-only-haiku}

**Why:** Every full-power agent has a `-docs` sibling so callers can
make cheap, citeable doc lookups without paying for the full-power
context. Especially needed cross-repo: when the `pdomain-ocr-labeler-spa`
agent migrates its canvas onto pdomain-ui (Phase 2), it cannot reach into
pdomain-ui's tree — it has to dispatch `pdomain-ui-docs` for "what does
`<PageImageCanvas>`'s `tool` slot expect?"

**What:** Create
`/workspaces/ocr-container/.claude/agents/pdomain-ui-docs.md`, mirroring
`.claude/agents/pdomain-prep-for-pgdp-docs.md` exactly except:

- `name: pdomain-ui-docs`
- `model: sonnet`, `effort: low`, `tools: Read, Glob, Grep` (same as
  the existing `-docs` siblings — Haiku-class doc lookup).
- Repo path: `/workspaces/ocr-container/pdomain-ui/`.
- Description mentions pdomain-ui's doc surface: `README`, `CONTRIBUTING`,
  `docs/`, Storybook MDX (when present), the slot/component API
  contracts. Includes the "not the same as `pdomain-ui` (full-power)"
  guard.
- Fallback line: `Not found in pdomain-ui docs.`

Files:

- Create: `.claude/agents/pdomain-ui-docs.md`

- [ ] **Step 1: Copy the structural template from `pdomain-prep-for-pgdp-docs.md`**

Use the same 7-section shape (Hard scope rules / How to work / Output
exactly this nothing else / Fallback / Hard cap / Search efficiency).
No prose drift outside what the substitutions above require.

- [ ] **Step 2: Adjust scope rules for the spec-only initial state**

In the "Hard scope rules" block, note that during the spec-only window
the agent should still respond — searching the repo's `.md` files
returns no matches until the repo is scaffolded, at which point the
fallback `Not found in pdomain-ui docs.` is the correct response. No need to
special-case "repo doesn't exist yet"; `Glob` simply returns empty.

- [ ] **Step 3: Verification — structural checks**

```bash
head -10 /workspaces/ocr-container/.claude/agents/pdomain-ui-docs.md
grep -n "^name: pdomain-ui-docs$" /workspaces/ocr-container/.claude/agents/pdomain-ui-docs.md
grep -n "^model: sonnet$" /workspaces/ocr-container/.claude/agents/pdomain-ui-docs.md
grep -n "^tools: Read, Glob, Grep$" /workspaces/ocr-container/.claude/agents/pdomain-ui-docs.md
grep -n "Not found in pdomain-ui docs." /workspaces/ocr-container/.claude/agents/pdomain-ui-docs.md
```

Each grep must match.

**Acceptance:**

- File exists at `.claude/agents/pdomain-ui-docs.md`.
- Front-matter: `name: pdomain-ui-docs`, `model: sonnet`, `effort: low`,
  `tools: Read, Glob, Grep`.
- Hard scope restricts reads to
  `/workspaces/ocr-container/pdomain-ui/**/*.md`.
- Fallback string is exactly `Not found in pdomain-ui docs.`
- The "do not use for code changes" sentence is present (mirrors the
  template).

---

## Task 3: Write `.claude/agents/pdomain-ocr-ops.md` (full-power agent) {#write-claudeagentspd-ocr-opsmd-full-power-agent}

**Why:** Symmetric reason to Task 1 for the Python side. `pdomain-ocr-ops`
is the Python foundation lib housing the suite registry, UI-prefs
routes, sibling-spawn helper, GPU dispatch adapters, JSON Schema
emitter, and (Phase 1.7) the migrated `STAGE_IMPL` registry from
pgdp-prep. Without a dedicated agent, every change to that library
would breach the workspace routing rule that each `pd-*` tree has its
own owner.

**What:** Create `/workspaces/ocr-container/.claude/agents/pdomain-ocr-ops.md`,
mirroring `pdomain-prep-for-pgdp.md` very closely — pdomain-ocr-ops is also a
Python+uv FastAPI-route-providing project — and adopting the
spec-only-window guidance from `pdomain-ocr-labeler-spa.md` (pre-flight
identity check, "stop and report routing error if repo missing").

Files:

- Create: `.claude/agents/pdomain-ocr-ops.md`

- [ ] **Step 1: Write the YAML front-matter**

- `name: pdomain-ocr-ops` (exact).
- `description:` — `MUST BE USED PROACTIVELY for any work in the
  pdomain-ocr-ops repo` sentence. Trigger words to include explicitly:
  `pdomain-ocr-ops`, `pd_ocr_ops`, `suite registry`, `installed.toml`,
  `~/.local/share/pd-suite/`, `mount_routes`, `SuiteAdapters`,
  `prefs.read`/`prefs.write`, `sibling_spawn`, `desktop.install_shortcut`,
  `StageDispatcher`, `LongJobRunner`, `pick_device`, `pd_ocr_ops.gpu`,
  `pd_ocr_ops.suite`, `PD_GPU_BACKEND`, `PD_SUITE_MODE`, OCR mutation
  ops (Word/Line/Block reorganize), and the path anchor `anything under
  /workspaces/ocr-container/pdomain-ocr-ops/`.
- `memory: project`.

- [ ] **Step 2: Write the `Pre-flight identity check` block**

Same pattern as Task 1 Step 2 — cwd + `git rev-parse --show-toplevel` +
`head -2` of the agent prompt — with the target path
`/workspaces/ocr-container/pdomain-ocr-ops/`. Call out the naming traps:
`pdomain-ocr-cli`, `pd-ocr-trainer`, `pdomain-ocr-synth`, `pd-ocr-labeler`,
`pdomain-ocr-labeler-spa` all share the `pd-ocr-` prefix and a stale shell
state could land the agent in the wrong tree.

- [ ] **Step 3: Write the `Persistent memory` block**

Same structure as Task 1 Step 3. Path:
`/workspaces/ocr-container/.claude/agent-memory/pdomain-ocr-ops/`. Hints
appropriate to a Python library: adapter-pattern boundaries (which
operations live on `SuiteAdapters` vs free functions), GPU dispatcher
protocol quirks (the `503 Retry-After` contract per spec §6 / §8),
SQLite `jobs.db` schema decisions, `filelock` patterns for the
`installed.toml` registry, `platformdirs` cross-platform quirks,
`schemas.emit` model-discovery rules.

- [ ] **Step 4: Write the `What this repo is` block**

Two short paragraphs:

1. The standardized Python ops library every `pd-*` SPA backend
   imports for suite plumbing (registry, prefs, sibling-spawn, desktop
   shortcuts) + GPU dispatch (short stage calls + long jobs) + JSON
   Schema emission for its own public types.
2. Lives between `pdomain-book-tools` (upstream domain models) and each
   app's FastAPI server — never the other way around. Apps mount its
   routes via `pd_ocr_ops.suite.mount_routes(app, adapters)`.

Cite:
[spec §3 (Repo & release layout)](../specs/2026-05-16-cross-cut-design.md#3-repo--release-layout-install--discovery-model),
[spec §8 (Hosted / web-mode considerations)](../specs/2026-05-16-cross-cut-design.md#8-hosted--web-mode-considerations)
for the adapter seams,
and the Phase-1 ops checklist in
[spec §9 (Phase-1-done success criteria)](../specs/2026-05-16-cross-cut-design.md#phase-1-done-success-criteria).

- [ ] **Step 5: Write the `Stack & layout (planned)` block**

- Python 3.13+, `uv`-managed, `hatchling` build backend.
- `src/pd_ocr_ops/` source root with submodules `suite/` (registry,
  prefs, sibling_spawn, desktop), `gpu/` (StageDispatcher,
  LongJobRunner, pick_device), `ops/` (future home for Word/Line/Block
  mutation primitives extracted from labeler-spa — Phase 2 task per
  spec §9 deferred items), `schemas/` (`emit.py` CLI — same pattern as
  `pd_book_tools.schemas.emit` per plan
  [docs/superpowers/plans/2026-05-16-pdomain-book-tools-review-metadata-and-schemas-emit.md](2026-05-16-pdomain-book-tools-review-metadata-and-schemas-emit.md)).
- Tests: `tests/`, pytest via `uv run pytest -n auto`.
- Direct deps: `pydantic>=2`, `fastapi`, `filelock`, `platformdirs`,
  `pdomain-book-tools` (foundation domain models), `sqlalchemy` or stdlib
  `sqlite3` for the jobs table (defer choice to the scaffold plan).
- Publish target: `pdomain-index-pip` (post-rename — formerly `pd-index`).

- [ ] **Step 6: Write the `Read these first` block**

Order: `README.md`, `CLAUDE.md` (when written), the workspace cross-cut
spec (cite the same relative path as Task 1 Step 6 — `../../../docs/
superpowers/specs/2026-05-16-cross-cut-design.md`) with §§3, 6, 8, 9
called out, the per-repo specs once they exist under `pdomain-ocr-ops/specs/`.

- [ ] **Step 7: Write the `Standard workflow` block**

Mirror `pdomain-prep-for-pgdp.md`:

- `make help`.
- After edits: `make format`, `make lint`, `make test`, `make ci`.
- If the routes / Pydantic models change in a way other repos consume,
  run `uv run python -m pd_ocr_ops.schemas.emit` and confirm
  downstream codegen consumers (pdomain-ui) regenerate.
- Local jobs DB path is `~/.local/share/pd-suite/jobs.db` — call out
  that tests must use a tmp_path isolation pattern, never the user's
  real path.

- [ ] **Step 8: Write the `Inter-repo awareness` block**

- **`pdomain-book-tools`** is the foundation — `pdomain-ocr-ops` imports its
  domain models and depends on its `schemas.emit` CLI as a reference
  pattern. Cross-repo questions: dispatch `pdomain-book-tools-docs`.
- **`pdomain-ui`** consumes pdomain-ocr-ops's `schemas.emit` output via the
  codegen pipeline + mounts its routes via the standard contract
  callbacks. Cross-repo questions: dispatch `pdomain-ui-docs`.
- **`pdomain-prep-for-pgdp`** is the donor for the Phase 1.7 `STAGE_IMPL`
  migration (its existing GPU adapter pattern moves into pdomain-ocr-ops as
  the canonical home — spec §7 Phase 1.7). Until 1.7 ships, pgdp-prep
  remains the source of truth for that code; read it via
  `pdomain-prep-for-pgdp-docs`.
- **`pd-ocr-trainer`** is the consumer for the `LongJobRunner` protocol
  (long-timeout Modal training jobs per spec §6 / §8). Cross-repo
  questions via `pd-ocr-trainer-docs`.
- **`pdomain-ocr-labeler-spa`** is the future consumer that will hand its
  Word/Line/Block mutation primitives to `pd_ocr_ops.ops` in a Phase 2
  follow-up (spec §9 deferred). Read its docs via
  `pdomain-ocr-labeler-spa-docs`.

- [ ] **Step 9: Write the `Quirks / gotchas` and `Out of scope` blocks**

Quirks:

- The `installed.toml` registry is mutated by every pd-* SPA on first
  run; concurrency is governed by `filelock` — never bypass the lock.
- Cross-platform paths come from `platformdirs`; never hard-code
  `~/.local/share/...` outside the lookup helpers.
- The desktop launcher stub raises `NotImplementedError` by design
  (spec §3 + §9 deferred) — implementing real platform writers is
  Phase 4.
- The `PGDP_GPU_BACKEND` → `PD_GPU_BACKEND` env-var rename keeps a
  deprecation alias (spec §7 Phase 1.7) — don't drop the alias
  without an explicit user decision.
- The Phase 1 jobs table is SQLite-backed and single-machine —
  multi-machine queue is a Phase 4 adapter; don't reach for Redis or
  Celery in the Phase 1 implementation.

Out-of-scope:

- Editing outside `/workspaces/ocr-container/pdomain-ocr-ops/`.
- Editing `pdomain-book-tools` or consumer apps (route to their agents).
- Publishing to `pdomain-index-pip` without explicit approval.
- Implementing hosted-mode adapters (Phase 4 per spec §8) — Phase 1
  ships only the interface + local-mode implementation.

- [ ] **Step 10: Verification — structural checks**

```bash
head -10 /workspaces/ocr-container/.claude/agents/pdomain-ocr-ops.md
grep -n "Pre-flight identity check" /workspaces/ocr-container/.claude/agents/pdomain-ocr-ops.md
grep -n "^name: pdomain-ocr-ops$" /workspaces/ocr-container/.claude/agents/pdomain-ocr-ops.md
grep -n "/workspaces/ocr-container/.claude/agent-memory/pdomain-ocr-ops/" \
  /workspaces/ocr-container/.claude/agents/pdomain-ocr-ops.md
grep -n "mount_routes" /workspaces/ocr-container/.claude/agents/pdomain-ocr-ops.md
grep -n "StageDispatcher" /workspaces/ocr-container/.claude/agents/pdomain-ocr-ops.md
```

Each grep must match.

**Acceptance:**

- File exists at `.claude/agents/pdomain-ocr-ops.md`.
- YAML front-matter parses; `name: pdomain-ocr-ops` exactly.
- Description includes the trigger words from Step 1.
- All standard sections present (identity check, memory, what-this-is,
  stack, read-these-first, workflow, inter-repo, quirks, out-of-scope).
- Memory path is the absolute workspace-canonical path.

---

## Task 4: Write `.claude/agents/pdomain-ocr-ops-docs.md` (read-only Haiku) {#write-claudeagentspd-ocr-ops-docsmd-read-only-haik}

**Why:** Same rationale as Task 2. Cross-repo lookups will be common —
`pdomain-ui` will need "what URL does `mount_routes` expose for the suite
launcher endpoint?", `pdomain-prep-for-pgdp` will need "what's the
`StageDispatcher` protocol shape we have to satisfy after the 1.7
migration?", etc.

**What:** Create
`/workspaces/ocr-container/.claude/agents/pdomain-ocr-ops-docs.md`, mirroring
`.claude/agents/pdomain-prep-for-pgdp-docs.md`.

Files:

- Create: `.claude/agents/pdomain-ocr-ops-docs.md`

- [ ] **Step 1: Copy the structural template**

Same 7-section shape as `pdomain-prep-for-pgdp-docs.md`. Substitutions:

- `name: pdomain-ocr-ops-docs`.
- `model: sonnet`, `effort: low`, `tools: Read, Glob, Grep`.
- Repo path: `/workspaces/ocr-container/pdomain-ocr-ops/`.
- Description mentions `pdomain-ocr-ops`'s doc surface: `README`,
  `CLAUDE.md` (when written), `docs/`, `specs/` (when written), the
  suite-route URL contracts, the adapter protocol descriptions. Note
  that `pdomain-ui-docs` is a sibling, not this agent, and `pdomain-ocr-cli-docs`
  / `pd-ocr-trainer-docs` / `pdomain-ocr-synth-docs` /
  `pd-ocr-labeler-docs` / `pdomain-ocr-labeler-spa-docs` share the
  `pd-ocr-` prefix — do not conflate.
- Fallback line: `Not found in pdomain-ocr-ops docs.`

- [ ] **Step 2: Verification — structural checks**

```bash
head -10 /workspaces/ocr-container/.claude/agents/pdomain-ocr-ops-docs.md
grep -n "^name: pdomain-ocr-ops-docs$" /workspaces/ocr-container/.claude/agents/pdomain-ocr-ops-docs.md
grep -n "^model: sonnet$" /workspaces/ocr-container/.claude/agents/pdomain-ocr-ops-docs.md
grep -n "^tools: Read, Glob, Grep$" /workspaces/ocr-container/.claude/agents/pdomain-ocr-ops-docs.md
grep -n "Not found in pdomain-ocr-ops docs." /workspaces/ocr-container/.claude/agents/pdomain-ocr-ops-docs.md
```

**Acceptance:**

- File exists at `.claude/agents/pdomain-ocr-ops-docs.md`.
- Front-matter: `name: pdomain-ocr-ops-docs`, `model: sonnet`,
  `effort: low`, `tools: Read, Glob, Grep`.
- Hard scope restricts reads to
  `/workspaces/ocr-container/pdomain-ocr-ops/**/*.md`.
- Fallback string is exactly `Not found in pdomain-ocr-ops docs.`
- "Do not use for code changes" sentence present.

---

## Task 5: Update workspace `CLAUDE.md` routing table {#update-workspace-claudemd-routing-table}

**Why:** The workspace `CLAUDE.md` is the canonical routing table any
parent context consults to decide which agent to dispatch. Without
updating it, `pdomain-ui` and `pdomain-ocr-ops` are unknown to callers even
though their agent files exist on disk. This is the last step that
turns the agent files from "files that exist" into "routes a caller
can name."

**What:** Two edits to `/workspaces/ocr-container/CLAUDE.md`:

1. Add `pdomain-ui/` and `pdomain-ocr-ops/` rows to the project table at the top.
2. Note the new agent pairs in the "Routing — delegate to per-repo
   agents" section's running commentary, if useful (the per-pair
   `<repo>` / `<repo>-docs` convention is already documented generically
   — adding the rows to the project table may be sufficient).

Files:

- Modify: `/workspaces/ocr-container/CLAUDE.md`

- [ ] **Step 1: Inspect the current project table**

Read `/workspaces/ocr-container/CLAUDE.md` lines 1–20 (the project
table). Confirm the current row count (8 pd-* + `se-llm-skills`) and
column shape (`Path` + `What it is`).

- [ ] **Step 2: Add new rows**

The two new rows go alphabetically — `pdomain-ocr-ops/` after `pdomain-ocr-cli/`
(and before `pd-ocr-labeler/`), and `pdomain-ui/` after `pdomain-prep-for-pgdp/`
(it's the only pd-* repo that doesn't start with `pd-o…`; alphabetical
order places it last among pd-* repos and before `se-llm-skills`).
Suggested cells (keep brief — match the table's existing terseness):

| Path                  | What it is                                                  |
|-----------------------|-------------------------------------------------------------|
| `pdomain-ocr-ops/`         | Shared Python ops + suite plumbing (registry/prefs/sibling-spawn/GPU adapters). |
| `pdomain-ui/`              | Shared TS/React frontend library (canvas / worklist / shell / primitives / icons / theme). |

Use `Edit` (not Write) — preserve the rest of the file.

- [ ] **Step 3: Optional — extend the "Routing" running commentary**

Re-read the "Three labeler-prefixed agents are distinct" block (around
line 29). Consider whether a similar "Five `pd-ocr-…` agents are
distinct; do not conflate" note is justified now that we're adding
`pdomain-ocr-ops` to the existing `pdomain-ocr-cli` / `pd-ocr-labeler` /
`pdomain-ocr-labeler-spa` / `pdomain-ocr-synth` / `pd-ocr-trainer` set. If yes,
add a sibling note. If the project table is sufficient, leave the
routing prose alone (judgment call — both are defensible).

- [ ] **Step 4: Verification — structural checks**

```bash
grep -n "pdomain-ui/" /workspaces/ocr-container/CLAUDE.md | head -5
grep -n "pdomain-ocr-ops/" /workspaces/ocr-container/CLAUDE.md | head -5

# The new rows landed inside the table (sanity).
sed -n '1,25p' /workspaces/ocr-container/CLAUDE.md
```

Both greps must match; the table should still be a valid markdown table
(header row + alignment row + data rows, no stray whitespace breaking
the pipe alignment).

**Acceptance:**

- `CLAUDE.md` lists `pdomain-ocr-ops/` and `pdomain-ui/` in the project table
  with the "What it is" cell describing each repo in one line.
- The markdown table renders cleanly (pipes aligned; alignment row
  intact).
- No other content in `CLAUDE.md` has been disturbed (a `git diff`
  shows only the two new rows + optionally the routing note from
  Step 3).

---

## Self-review checklist (for the engineer; do this before the final commit)

- [ ] All four agent files exist with correct front-matter
  (`name` matches filename, `memory: project` on full-power agents,
  `model: sonnet` + `tools: Read, Glob, Grep` + `effort: low` on
  `-docs` agents).
- [ ] Both full-power agents reference the workspace-canonical absolute
  memory path (never a relative `.claude/agent-memory/...`).
- [ ] Both full-power agents include a `Pre-flight identity check` that
  references the still-not-existing repo path and instructs the agent
  to stop + report a routing error if it lands in the wrong tree
  (acceptable Phase-1 behavior until the repos are scaffolded).
- [ ] Both `-docs` agents have the correct fallback string and the
  "do not use for code changes" sentence.
- [ ] Workspace `CLAUDE.md` lists both new repos in the project table.
- [ ] No edits made to any `pd-*` repo tree (this plan is workspace-
  level only).
- [ ] No edits made to `pdomain-prep-for-pgdp{,-docs}.md` /
  `pdomain-ocr-labeler-spa{,-docs}.md` / `pdomain-book-tools{,-docs}.md` (the
  structural templates are read-only here; only new files are written).

---

## Follow-up plans (not in scope here)

1. **Scaffold the `pdomain-ui` repo (spec §7 Phase 1.5).** Create the
   `pdomain-ui/` tree itself, the `pnpm` scaffold, Vite library config,
   Storybook, the codegen scripts (`codegen:fetch` / `codegen:emit` /
   `codegen:tsgen` / `codegen:check`), the `theme/` directory with
   `tokens.css` + `primitives.css` copied from
   `docs/design-system/`, the first slot-based component ports from
   `pdomain-ocr-labeler-spa`, and the `0.1.0-alpha` release to
   `pdomain-index-npm`. Substantial — should be its own multi-task plan.
2. **Scaffold the `pdomain-ocr-ops` repo (spec §7 Phase 1.3).** Create the
   `pdomain-ocr-ops/` tree, the `uv` scaffold, the `suite/` submodule
   (registry/prefs/sibling-spawn/desktop stub), the `gpu/` submodule
   (StageDispatcher / LongJobRunner protocols + local-mode adapters +
   SQLite jobs table + `pick_device`), the `schemas/` emitter, and
   the `0.1.0` release to `pdomain-index-pip`. Substantial — should be its
   own multi-task plan.
3. **Scaffold the `pdomain-index-npm` repo (spec §7 Phase 1.4).** Verdaccio-
   style index hosted on GitHub Pages, publish script, first release of
   `@concavetrillion/pdomain-ui@0.1.0-alpha`. Independent of this plan.
4. **Rename `pd-index` → `pdomain-index-pip` (spec §7 Phase 1.2).** Touches
   every `pd-*/pyproject.toml`, `Makefile`, the workspace `CLAUDE.md`,
   workspace `.gitignore` anchors, and the index repo itself. Cross-
   cutting chore — own plan, own coordination window.
5. **Phase 1.7 — Migrate `STAGE_IMPL` registry + Modal / shared-
   container GPU adapters out of `pdomain-prep-for-pgdp` and into
   `pdomain-ocr-ops`** as the canonical home (spec §7 Phase 1.7). Includes
   the `PGDP_GPU_BACKEND` → `PD_GPU_BACKEND` env-var rename + alias.
6. **Add `pdomain-ocr-trainer-spa` / `pdomain-ocr-simple-gui` / `pd-proofreader`
   agent definitions when those repos enter Phase 3.** Same pattern as
   this plan, but driven off Phase 3 scope rather than Phase 1.
