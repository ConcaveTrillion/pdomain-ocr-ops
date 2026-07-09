# Handoff — resume the cross-cut workstream

> Paste the body of this file (or just point at it) in a fresh Claude session to
> pick up where the 2026-05-16 `cross-cut` brainstorming session ended.

---

**Resume from prior session — cross-cut design + first implementation plan committed.**

Working directory: `/workspaces/ocr-container/`. Multi-repo workspace with 8 `pd-*` projects (`pdomain-book-tools`, `pdomain-ocr-cli`, `pd-ocr-labeler`, `pdomain-ocr-labeler-spa`, `pdomain-ocr-synth`, `pd-ocr-trainer`, `pd-png-optimizer`, `pdomain-prep-for-pgdp`) plus `se-llm-skills`. Per-repo agents at `.claude/agents/<repo>.md`; routing rules in the workspace `CLAUDE.md`.

## What is already on `main`

- **Cross-cut design spec** — `docs/superpowers/specs/2026-05-16-cross-cut-design.md` (commits `8b475da` initial, `0616083` revision). Defines two new shared libraries (`pdomain-ui` TS/React + `pdomain-ocr-ops` Python), two release indexes (`pdomain-index-npm` new, `pd-index` → `pdomain-index-pip` rename), foundation Pydantic-schema codegen pipeline, `docs/design-system/` fold-in as pdomain-ui's runtime source-of-truth, `uv tool install` distribution, file-based sibling discovery, GPU dispatch protocols (short stages + long jobs), hosted-mode adapter seams. See §7 for phase staging, §9 for Phase-1-done criteria, and the "Decision log (Q1–Q8)" near the bottom.
- **First implementation plan** — `docs/superpowers/plans/2026-05-16-pdomain-book-tools-review-metadata-and-schemas-emit.md` (commit `3470091`). Scoped to the `pdomain-book-tools` row of §7.1: add optional `ReviewMetadata` to Word/Block/Page; ship `python -m pd_book_tools.schemas.emit`. 7 TDD tasks. `GTMatchMetadata` explicitly deferred — the existing top-level `ground_truth_*` fields need a cluster refactor that's its own plan.
- **Two reminders** for deferred specs:
  - `docs/superpowers/reminders/spec-pdomain-ocr-simple-gui.md`
  - `docs/superpowers/reminders/desktop-launcher-integration.md`

## What's still ahead

Six unwritten plans, in suggested execution order:

1. ✅ `pdomain-book-tools` schema + emitter — **plan written, not executed**
2. Workspace agent definitions (`pdomain-ui`, `pdomain-ui-docs`, `pdomain-ocr-ops`, `pdomain-ocr-ops-docs`) + routing table update — small, ~5 tasks
3. `pd-index` → `pdomain-index-pip` rename — chore across all 8 repos, ~10–15 tasks
4. `pdomain-index-npm` new repo (Verdaccio-style npm index on GitHub Pages) — ~8 tasks
5. `pdomain-ocr-ops` new repo (suite registry / prefs / `mount_routes` / desktop stub / sibling-spawn / GPU adapter protocols + local impl / SQLite jobs) — ~30–50 tasks
6. `pdomain-ui` new repo (depends on #1: scaffold / codegen / canvas / worklist / shell / primitives / icons / theme migration from `docs/design-system/` / Storybook) — ~40–60 tasks
7. Phase 1.7 GPU adapter migration (depends on #5: move pgdp-prep's existing `STAGE_IMPL` + Modal + shared-container adapters into `pdomain-ocr-ops`) — ~10–15 tasks

## Pick one to do first

- **(a) Execute plan #1** (`pdomain-book-tools`) via the `superpowers:subagent-driven-development` skill, dispatching tasks into the `pdomain-book-tools` agent one at a time.
- **(b) Write plan #2** — workspace agent definitions. Smallest, independent, useful prep before any of the new repos exists.
- **(c) Write a different plan** from the list above.
- **(d) Revisit something in the spec** before any execution (e.g., refine a deferred item, second-guess a Q1–Q8 decision).

## Pre-session checks (optional, ≤30 s each)

- `git log --oneline -5` — confirm you're at `3470091` or later on `main`.
- Skim the spec's §7 "Phase staging" if you need a refresher on dependencies.
- Skim `docs/design-system/README.md` (short, ~100 lines) — it's the visual contract pdomain-ui will adopt.

## Useful context

- Workspace `CLAUDE.md` has the agent-routing table and the leakage-check rule for `.claude/agent-memory/`.
- Each repo has a `<repo>-docs` Haiku agent for cheap doc lookups; use it before reaching into a sibling tree.
- The `cross-cut` session's brainstorming visual companion artifacts live at `.superpowers/brainstorm/<session-id>/` (gitignored). The server auto-exits after 30 min of inactivity — restart if needed via the brainstorming skill's `start-server.sh`.

## Tone calibration from the prior session (so the new Claude doesn't have to guess)

- User is decisive and terse — "C", "B", "OK", short directives. Match that pace.
- Strong preference for honest pushback when a proposal duplicates or contradicts existing artifacts (the `docs/design-system/` fold-in came after the user asked "did you fold that into your spec?" and the honest answer was "no").
- "Each pd-* app independently installable" is a load-bearing design principle — every later decision has to respect it.
- The user pushes back on overengineering ("what does Tailwind/CVA get me?", "what does Radix offer?") — explain the actual value-add of each dep honestly before adding it.
