# Feature-request → spec → child-issues lifecycle (v1)

> **Status**: Active (operational rollout pending; see 2026-05-11-INDEX.md)
> **Last updated**: 2026-05-11

## TL;DR

Three new CT-interactive workspace skills (`/triage`, `/spec-from-issue`, `/decompose-spec`) plus a new `kind:feature-request` label and a `bot:*` per-bot eligibility family fill the gap between "I have an idea" and "ship-issue picks it up". `/decompose-spec` also creates a per-repo GitHub milestone (`spec: <slug> (#M)`) and assigns each child to it, giving every spec a native progress bar with no extra tooling. Specs that exist today get folded in via `/decompose-spec --backfill`. A chain-state report (markdown + local dashboard panel) shows where each idea is along the pipeline; the dashboard surfaces both per-spec milestone progress and the unified across-repos view that GitHub's per-repo milestones can't.

## Context

Today's pipeline starts at `gh issue create` with hand-chosen labels. There is no automation for turning an idea into a spec, or a spec into child issues. The existing GitHub-issues design ([2026-05-09](2026-05-09-github-issues-projects-design.md)) explicitly defers auto-triage to a "Future state" section (lines 780–822), but that section is scoped to **external bug reports** only. The pilot debrief from B6 (`docs/plans/2026-05-10-pilot-pdomain-book-tools.md`) confirmed the gap: B4 produced 12 issues for pdomain-book-tools by walking `docs/ROADMAP.md` and `TEST_COVERAGE_WORKPLAN.md` by hand. With seven `pd-*` repos to onboard, hand-walking is not scalable.

Two needs surfaced:

1. A predictable lifecycle for converting feature ideas into shippable issues, with sized intermediate steps (small ideas ship direct; larger ideas spawn a spec first).
2. Visibility into where each idea sits in the pipeline — what's untriaged, what has a spec but no children, what has children but isn't armed for the bot.

This spec covers the v1 of both, with explicit hooks reserved for future bot-driven triage and bot-driven spec writing.

## Constraints

- **Per-repo locality.** Feature-requests are filed against the repo they target. Workspace-meta tracker only sees workspace-tooling feature-requests. Cross-repo decomposition is deferred to v2.
- **CT-interactive in v1.** All three new skills run in the user's interactive Claude session as `vscode`. The `claude-bot` user gets no new authority. Future bot-driven variants are documented as v2 hooks but not implemented here.
- **Coexists with existing ship-issue v1.** The bot's pick.py contract is unchanged: bot still picks issues with `bot:ship-issue-ready` (renamed from `claude-ok`) and `status:ready`. The new skills produce issues that fit that contract.
- **Single user (CT) is the only `claude-ok`-equivalent gate.** `bot:*-ready` labels are added by CT, never by an agent in v1.
- **No new file-format inventions.** Spec files keep the existing 9-section template. The only addition is an optional `Spec-Issue: #N` header line.
- **Milestones are scoped to spec-grouping only.** No release-train, version-tag, or sprint milestones — that would conflate two grouping mechanisms. The 1-spec-to-1-milestone invariant keeps the model uniform across all 8 repos.
- **Solo-dev cadence.** Each skill is a single-conversation interactive flow; no multi-day ceremonies.

## Decision

### Architecture

Three CT-interactive workspace skills produce one new issue per invocation, threading the existing ship-issue pipeline:

```
[CT files issue]              [you run skill]                     [ship-issue ships]

kind:feature-request   ──/triage N──►   triage:approved/rejected
                                       + forks ONE child:
                                       (a) tracking issue (kind:bug/
                                           chore/feature, status:backlog)
                                                ──[CT arms bot:ship-issue-ready]──►
                                                ────────────► ship-issue ─► PR
                                       OR
                                       (b) spec issue (kind:spec)
                                           ──/spec-from-issue──►
                                           docs/specs/file.md + spec-PR
                                                ──/decompose-spec──►
                                                N child tracking issues
                                                ──[CT arms bot:ship-issue-ready]──► ship-issue ─► PR
```

Three "rings" in the chain when a spec is required: feature-request → spec issue → N child tracking issues. Two rings for ship-direct: feature-request → tracking issue. The bot's surface (`bot:ship-issue-ready` + `status:ready`) is unchanged from ship-issue v1; the new skills only add upstream plumbing.

### Label taxonomy

New labels (all repos via `seed-labels.sh` update):

| family | values | meaning |
|---|---|---|
| `kind:` | + `feature-request` | new value alongside existing `bug`/`chore`/`feature`/`spec`/`recurring` |
| `triage:` | `proposed-by-agent`, `approved`, `rejected`, `needs-spec` | triage state on the feature-request itself |
| `bot:` | `ship-issue-ready` | replaces `claude-ok`. Per-bot eligibility (room for `bot:triage-ready`, `bot:spec-write-ready` later) |

`triage:proposed-by-agent` is reserved for future bot-driven triage; in v1, CT-interactive `/triage` writes `triage:approved` or `triage:rejected` directly (CT IS the gate, no proposal stage).

### Skill responsibilities

All three skills live in workspace `.claude/skills/`, run as `vscode` in CT's interactive session, and use `gh` directly (no per-repo agent delegation — see "Agent routing" below).

**`/triage <N>`** — invoked when CT decides a feature-request is ready for triage.
Reads: feature-request body, recent code in the target repo, recent issues for dup-detection, the `bot:ship-issue-ready` queue size for spec-vs-direct sizing.
Produces:
- A reasoning comment on `#N` ("Why I classified this X")
- Label updates on `#N` (`triage:approved` or `triage:rejected`; if approved, also `triage:needs-spec` if a spec is required)
- ONE forked child issue:
  - `(a) tracking issue` (`kind:bug|chore|feature`, `effort:*`, `model:*`, `model-effort:*`, `status:backlog`, body has `Tracks: #N`) — for direct-ship cases. **No milestone**: direct-ship is one issue, not a multi-issue group; a milestone of size 1 adds no signal.
  - `(b) spec issue` (`kind:spec`, `effort:*`, `status:backlog`, body has `Tracks: #N`) — for spec-required cases. The spec issue itself is **not** assigned to its own future milestone; only the spec's *children* (filed by `/decompose-spec`) populate the milestone.
- A pointer comment on `#N` linking to the forked issue.

Idempotent: refuses to re-triage if `triage:approved`/`triage:rejected` is already present, unless `--force` is passed.

**`/spec-from-issue <N>`** — invoked for a `kind:spec` issue when CT is ready to write the spec.
Wraps the existing `superpowers:brainstorming` skill, scoped to the spec issue's body and the `Tracks:` parent. Output:
- `<repo>/docs/specs/YYYY-MM-DD-<topic>-design.md` (per-repo specs) OR `docs/specs/...` (workspace-level), with the standard 9-section template plus a header line `> **Spec-Issue**: ConcaveTrillion/<repo>#N`
- A draft PR opening the new spec file
- An edit to the spec issue body adding `Spec: <relative path>` line so `/decompose-spec` can find the file

Idempotent: refuses if spec issue body already has a `Spec:` line, unless `--force`.

**`/decompose-spec <path>`** — invoked when a spec is written and CT is ready to file children. Two orthogonal axes: source (new vs backfill) × output kind (tracking vs feature-request vs mixed).

Source axis:
- **New flow**: spec file has a `Spec-Issue: #N` header; skill links children to that.
- **Backfill**: spec file has no header; skill optionally creates a retrospective `kind:spec` issue first (`Backfill: pre-existing spec at <path>`), edits the spec to add the header, then proceeds. Backfill mode dry-runs by default; `--apply` required to actually file.

Output-kind axis (`--output=...`):
- `--output=tracking` (default): each child is a `kind:bug|chore|feature` tracking issue ready for ship-issue once armed. Right when the spec describes ONE cohesive feature with sub-tasks.
- `--output=feature-requests`: each child is a `kind:feature-request` issue that re-enters the lifecycle at the top (will need its own `/triage`, possibly its own spec). Right when the spec is a *cluster* of distinct features that each deserve independent triage and possibly their own sub-specs (common for backfilled meta-specs like the GitHub-issues design spec, which covers triage + spec creation + decomposition + dashboard as four largely-independent capabilities).
- `--output=mixed` (intended default once CT trusts the heuristic): agent proposes per item — sub-task style → tracking; cluster member → feature-request. CT reviews and toggles per row before commit.

Reads the whole spec, presents CT with a proposed list of children (per-item: kind, title, body summary, target labels). CT edits/removes/adds/toggles per row, confirms, then skill files them via `gh issue create`. Each child gets `Tracks: #<spec-issue-id>` and `Spec: <path>` body lines (regardless of output kind). Tracking-output children land at `status:backlog` without `bot:ship-issue-ready` — CT arms them manually after review. Feature-request-output children land at `status:backlog` and re-enter the lifecycle via `/triage`.

**Milestone creation.** Before filing children, `/decompose-spec` ensures a milestone titled `spec: <slug> (#M)` exists in the target repo (where `M` is the spec issue number and `<slug>` is derived from the spec issue title — slugged, lowercase, dashed, truncated to 40 chars). Idempotent: if the milestone already exists (e.g., from a prior partial run or backfill), reuse it. Each filed child is assigned to that milestone via `gh issue create --milestone` (or `gh issue edit --milestone` for diff-mode children that pre-exist without one). Milestone description holds a back-link to the spec issue and to the spec file path. No due date by default; `--due-date YYYY-MM-DD` opt-in for time-boxed specs only. The milestone is closed when CT closes the spec issue (manual; the close trigger is documented in the skill but not automated in v1).

Diff-mode for re-runs: skill detects existing children via `Tracks: #<spec-issue-id>` queries; offers to file only the missing ones. Recovery from partial-failure mid-decomposition is the same code path. Re-runs respect the original `--output` choice per child (tracked in the child's `kind:` label) and re-attach any orphaned children to the spec's milestone.

### Milestones

GitHub milestones serve as the per-repo "spec progress" container. One milestone per spec issue, named `spec: <slug> (#M)`, owned by `/decompose-spec`. Properties:

- **1-to-1 with spec issues.** Every `kind:spec` issue with at least one filed child has exactly one milestone; specs with no children yet have none.
- **Repo-local.** Cross-repo workspace specs (under `docs/specs/`) whose children land in different `pd-*` repos get one milestone per target repo, all sharing the same `(#M)` suffix for grep-ability.
- **Free progress bar.** GitHub renders closed/total automatically. `gh issue list -R <repo> --milestone "spec: <slug> (#M)"` is the canonical "what's left on this spec" query.
- **Closed = shipped.** Closing the milestone is the explicit "spec shipped" signal, complementary to the spec markdown's `Status: Locked` blockquote. The two should agree but neither auto-flips the other in v1; CT closes both when she closes the parent spec issue.
- **No other uses.** Release-train, sprint, and version milestones are explicitly out of scope to keep the model uniform.

Coexistence with existing groupings: the `Spec-Issue: #M` body header and the spec-file path in the `Spec:` body line remain the source of truth for the chain-state report's joins. The milestone is a derived view that GitHub maintains automatically — useful in the GitHub UI and via `gh`, but the chain-state report does not depend on it for correctness (just for the progress numerator/denominator, which can also be computed from `Tracks: #M` queries if a milestone is missing).

### Chain-state report

Two markdown views per repo plus a workspace cross-repo summary plus a panel on `cost-dashboard.html`. Generator: `scripts/build-spec-chain-report.py`. Triggered on demand and via the existing SessionEnd hook + once-per-hour ctask entry (same cadence as the cost-dashboard panel). The local dashboard is the unified across-repos view that GitHub's per-repo milestone bars cannot provide on their own; the milestone bars are the in-GitHub view, and `cost-dashboard.html` stitches them together.

**View A: feature-request lifecycle.** Per-repo markdown table:

```
Feature-request   Triaged?           Spec issue(s)        Milestone progress     Children armed?
#42 "X tuning"    triage:approved    #43 (kind:spec)      spec: x-tuning (#43)   0/3 (spec done; 3 children, none ship-issue-ready)
                                                          0/3 closed
#44 "Y heuristic" — (untriaged)      —                    —                      —
#46 "Z rewrite"   triage:approved    #47 (spec)+#48(spec) spec: z-rewrite (#47)  5/8 (mix)
                                                          5/8 closed
#50 "Trivial fix" triage:approved    none (ship-direct)   — (no milestone)       #51 ready, ship-issue-ready'd
```

The "Milestone progress" column is the progress bar GitHub renders natively, captured here for the markdown view; the dashboard panel renders the actual GitHub bars by linking to the milestone URL.

**View B: orphan specs.** Spec files with no corresponding `kind:spec` issue (the backfill queue):

```
Spec file                                              Spec issue   Children
docs/specs/03-reorganize-pipeline.md                   none         (run /decompose-spec --backfill)
docs/specs/06-word-reference-lines.md (legacy)         none         skip — on .specrc:legacy
```

**Workspace cross-repo summary** at `docs/superpowers/spec-chain-status.md` aggregates Views A+B across all eight repos, sorted by "most stuck" (longest time since last state advancement). The dashboard panel renders the same data with HTML cards and links, and embeds each spec's GitHub milestone progress bar inline (links to the milestone URL; falls back to a computed `closed/total` count if the milestone is missing).

### Implementation concerns

**Idempotence.** Each skill rerunnable without harm: `/triage` refuses if already triaged, `/spec-from-issue` refuses if spec already written, `/decompose-spec` enters diff-mode (file only missing children) and reuses the existing milestone if one is already open for the spec issue. Milestone lookup is by exact title match — no fuzzy dedup, no rename detection — so the slug derivation must be deterministic for a given spec issue title.

**Error handling.** All gh-mutation skills follow a transactional pattern: collect planned changes → present to CT for confirm/edit → apply atomically. Mid-flight failures emit a recovery hint pointing back at diff-mode rerun.

**Testing.** Pure helpers (label parsing, body parsing, dry-run formatting) get unit tests in `tests/`. Integration tests use a fake `gh` CLI shim that records calls and returns canned responses. Skill `.md` files themselves aren't auto-testable but the helpers they invoke are. Pattern matches existing `tests/test_bash_command_guard.py`.

**Agent routing.** Per `CLAUDE.md`, pd-* file mods normally go through the per-repo agent — but that policy is for **autonomous** work. These skills run in CT-interactive context with CT supervising every step (per the brainstorming-flow `/decompose-spec` design). The per-repo agent layer is bypassed; spec file creation/edits happen directly. This exception is documented here to prevent re-litigation in future sessions.

### Migration

One-time chores landing before the new skills go live:

1. **Rename `claude-ok` → `bot:ship-issue-ready`.** Atomic via `scripts/migrate-claude-ok-to-bot-label.sh`. Touches: `seed-labels.sh`, `ship-issue-pick.py`, `bash-command-guard.py` (`_claude_ok_check` becomes `_bot_ship_issue_check`), all workspace + pdomain-book-tools `.md` references, all open issues with `claude-ok` (workspace-wide gh edit), and finally the `claude-ok` label deletion in each repo. Workspace commit + per-repo PRs.
2. **Add new labels to all 8 repos via updated `seed-labels.sh`.** `kind:feature-request`, `triage:proposed-by-agent`, `triage:approved`, `triage:rejected`, `triage:needs-spec`, `bot:ship-issue-ready`.
3. **Backlog conversion of existing #2–#13 in pdomain-book-tools.** Each gets a manually-filed `kind:feature-request` parent (one per cluster, or skip if low value), then `triage:approved` retroactively, then `Tracks: #<feature-request>` line added to each existing tracking issue. Optional — could leave existing issues as-is and start the chain on new work only.
4. **Backfill spec issues for existing specs.** Run `/decompose-spec --backfill` (dry-run first) on each spec under `pdomain-book-tools/docs/specs/` and `docs/specs/`. Creates retrospective spec issues *and* their milestones; CT reviews which children to actually file. Backfill creates milestones in the same `spec: <slug> (#M)` form even when no children get filed (so the GitHub UI shows the spec as 0/0 — empty bar — until children land).

### Future state hooks (out of v1 scope)

Documented so the v1 design preserves room:

| future capability | what v1 already preserves |
|---|---|
| Triage bot auto-classifies feature-requests | `triage:proposed-by-bot` label slots into existing `triage:` family. Adds a proposal stage that v1 doesn't need (CT IS the gate today). |
| Triage bot generates multiple specs per feature-request | feature-request body designed to list `Spec issues: #N1, #N2, …` — no schema change. The chain-state report's View A renders 1-to-many naturally. |
| Auto-spec writing (bot writes the spec file) | `bot:spec-write-ready` slots into the existing `bot:` family. CT arms a spec issue with this label; bot picks it up via a new `spec-write` orchestrator parallel to ship-issue. |

Each future bot gets its own `bot:*-ready` label so arming one doesn't authorize the others.

## Contract / Acceptance

This spec is implemented when:

- [x] `seed-labels.sh` adds the new labels to all 8 repos
- [x] `scripts/migrate-claude-ok-to-bot-label.sh` runs successfully workspace-wide
- [x] `bash-command-guard.py` `_bot_ship_issue_check` (renamed from `_claude_ok_check`) gates on `bot:ship-issue-ready`
- [x] `ship-issue-pick.py` filters on `bot:ship-issue-ready` not `claude-ok`
- [x] `.claude/skills/triage/SKILL.md` + helpers exist and pass unit tests
- [x] `.claude/skills/spec-from-issue/SKILL.md` + helpers exist and pass unit tests
- [x] `.claude/skills/decompose-spec/SKILL.md` + helpers exist; backfill dry-run mode tested against an existing spec; both `--output=tracking` and `--output=feature-requests` exercised end-to-end
- [x] `scripts/build-spec-chain-report.py` produces both per-repo `docs/spec-chain-report.md` files and a workspace-level `docs/superpowers/spec-chain-status.md`
- [x] Dashboard panel renders the chain-state data alongside the existing cost-dashboard kanban
- [x] `/decompose-spec` creates a `spec: <slug> (#M)` milestone in the target repo and assigns each filed child to it; diff-mode rerun reuses the existing milestone
- [x] Chain-state report's View A renders the milestone progress column; dashboard panel embeds milestone progress bars or a computed fallback
- [ ] At least one end-to-end pass: file `kind:feature-request`, `/triage`, `/spec-from-issue`, write spec, `/decompose-spec` (verify milestone created with all children attached), arm a child, ship-issue picks it up, PR opens.

## Trade-offs considered

| Approach | Pro | Con |
|---|---|---|
| Per-repo locality (chosen) | Matches existing pd-* pattern; no central bottleneck; cross-repo deferred cleanly | Workspace-spanning ideas need manual decomposition into per-repo feature-requests |
| Workspace-only entry, fan-out to repos | Single front door; easier to find untriaged ideas | One repo as the bottleneck; cross-repo routing adds new tooling complexity |
| Fork tracking issue from feature-request (chosen) | Quarantines external content automatically; matches existing tracking-issue pattern from GitHub-issues spec | Two URLs per work item; slightly more bookkeeping |
| Mutate feature-request in place | One stable URL per work item | Fails the existing security model for external authors; would diverge from the established pattern |
| Triage forks `kind:spec` issue (chosen) | Three-rings model is inspectable; the spec issue is the natural umbrella for decomposition; future bots fit (`bot:spec-write-ready` against the spec issue) | More label/issue creation work upfront |
| `needs-spec` label only, no spec issue | Lightest weight | No GitHub-side handle to attach `bot:spec-write-ready` for the future bot; report can't easily show "spec file written but children not yet filed" |
| `/decompose-spec` reads whole spec, agent proposes (chosen) | Minimum spec-template change; reuses existing 9-section template; agent judgment captures nuance CT might miss | Agent's proposal quality varies; CT must always review |
| `/decompose-spec` reads `## Acceptance` checklist only | Most mechanical; no agent judgment | Acceptance bullets are usually too coarse-grained for issues; loses information |
| `/decompose-spec` auto-trigger on spec PR merge | No manual gate | Re-decomposes on every spec edit; risky for backfill of existing specs |
| Markdown-only chain-state report | Greppable; git-trackable | No at-a-glance view |
| Dashboard panel only | Visual | Not greppable; not git-trackable |
| Both markdown + dashboard panel (chosen) | Best of both; modest extra generator code | More surface to maintain |
| GitHub milestone per spec, scoped to spec-grouping only (chosen) | Free per-spec progress bar in the GitHub UI; canonical `gh issue list --milestone` query; closing the milestone is a clean shipped-signal | Third grouping mechanism alongside `Spec-Issue:` headers and `Tracks:` body lines; repo-local so workspace specs need one milestone per target repo |
| No milestones; rely solely on `Tracks: #M` queries | Zero new state to maintain | No native progress bar; every consumer has to compute closed/total themselves |
| Milestones for releases / sprints / versions too | Familiar GitHub idiom | Conflates spec-progress with release planning; explicitly out of scope to keep the model uniform |

## Consequences

- The `bot:` label namespace is established workspace-wide. Future bots add their own `bot:*-ready` label rather than overloading `bot:ship-issue-ready`.
- The 9-section spec template gains an optional `Spec-Issue: #N` header line. `lint-spec.py` does not enforce its presence (specs without the header are valid; `/decompose-spec` enters backfill mode).
- The `.specrc:legacy` allowlist remains a "skip from /decompose-spec --backfill" hint — legacy specs need manual splitting first via the existing `fixing-specs` Procedure 4.
- The chain-state report becomes a new operational surface CT consults. Expected weekly usage. Not part of any agent's reading context (avoids prompt-injection risk).
- Pilot-feedback findings #21 and #22 from the B6 stress run are unrelated to this design but inform the implementation: the `/spec-from-issue` skill's PR-creation step must respect the same setfacl + PATH-export guards that ship-issue learned the hard way.
- The new skills' integration tests will use a fake `gh` shim. This pattern can be lifted into a workspace test helper for use by future skills.
- GitHub milestones become a workspace convention scoped to spec-grouping only. Anyone (CT, agents, future bots) creating milestones for any other purpose violates the v1 invariant; surface that in PR review rather than in tooling enforcement.
- The slug-derivation function for milestone titles is a small new utility that needs deterministic, ASCII-safe behavior across re-runs and on backfill — non-deterministic output (e.g., timestamp suffixes) would break diff-mode dedup.
- `decompose-spec-plan.py` parses children from the `## Decision` section in priority order: (1) `### ` subsections, (2) numbered bold items (`1. **label**: ...`), (3) spec H1 as single-child fallback. New specs should use `### ` subsections in `## Decision` when there are multiple deliverables; the numbered-bold path is a compatibility fallback for pre-existing specs.

## Open questions

1. ~~**Workspace meta-repo for feature-requests about workspace tooling itself**~~ — **Resolved**: create `ConcaveTrillion/ocr-container-meta` as a **private** repo (sensitive to local state, e.g. ctask configs, hook details, claude-bot setup). Workspace-tooling feature-requests live there; pd-* repos stay public.
2. **Spec file path for cross-repo workspace specs** — workspace-level specs live in `docs/specs/`. Where do their generated child issues go? Lean: each child names its target repo via a `Repo: ConcaveTrillion/<repo>` body line; `/decompose-spec` files each child against the named repo. Out of scope for v1 single-repo invariant but worth noting. Status: **open, not blocking**.
3. **Triage skill's "ship-direct vs spec-required" sizing heuristic** — what makes a feature "needs a spec"? Initial heuristic: if estimated effort > S, or touches >2 files, or new public API. Subject to iteration once the skill exists. Status: **open, accept initial heuristic and iterate**.
4. ~~**Backlog conversion of existing #2–#13**~~ — **Resolved**: do the conversion. Run `/decompose-spec --backfill --output=feature-requests` against pdomain-book-tools' existing specs to produce retrospective feature-requests; existing #2–#13 then get `Tracks: #<feature-request>` body edits to thread them onto the chain. Validates the new flow on real data.
5. ~~**Better dashboard overall**~~ — **Resolved (sequencing)**: not deferred — moved to implementation sequencing (see "Implementation sequencing" subsection below). The chain-state dashboard panel must be working locally and reviewable before this design rolls out beyond pdomain-book-tools.

## Implementation sequencing

Phases must land in this order; no skipping ahead:

1. **v1 skills, labels, migration** — `/triage`, `/spec-from-issue`, `/decompose-spec` (both output modes), `bot:ship-issue-ready` rename, new label seeding. Scope = pdomain-book-tools only.
2. **Backfill validation on pdomain-book-tools** — run `/decompose-spec --backfill --output=feature-requests` against pdomain-book-tools/docs/specs/ to seed retrospective feature-requests. Convert existing #2–#13 to thread onto the chain (per resolved Open Q #4).
3. **Chain-state report (markdown + dashboard panel) running locally** — `scripts/build-spec-chain-report.py` produces the per-repo markdown and the workspace summary; dashboard panel renders cleanly. CT can `open cost-dashboard.html` and review the chain state visually for pdomain-book-tools.
4. **Dashboard refresh design** (sibling brainstorm, deferred) — only enter this once Phase 3 is validated and CT has hands-on experience with the chain-state panel.
5. **Roll out to remaining 6 pd-* repos + meta repo** — only after the dashboard is working locally for pdomain-book-tools and any refresh from Phase 4 has landed.

The constraint is explicit: do not push the new labels and skill machinery to the other 6 pd-* repos until the local dashboard story is solid for pdomain-book-tools.

## References

- `docs/specs/2026-05-09-github-issues-projects-design.md` (parent design; Future state section lines 780–822)
- `docs/plans/2026-05-10-pilot-pdomain-book-tools.md` (Plan B — first onboarding)
- `docs/plans/2026-05-10-pilot-pdomain-book-tools-debrief.md` (B6 evidence: hand-walking specs into issues isn't scalable)
- `scripts/ship-issue-pick.py` (`bot:ship-issue-ready` filter target)
- `scripts/lint-spec.py` (9-section template enforcement)
- `scripts/file-legacy-migration-issues.py` (existing narrow spec→issues automation, for legacy migration only)
- `.claude/hooks/bash-command-guard.py` (`_claude_ok_check` → `_bot_ship_issue_check` rename target)
- GitHub milestones REST + `gh` CLI: `gh api repos/:owner/:repo/milestones`, `gh issue create --milestone`, `gh issue edit --milestone`
