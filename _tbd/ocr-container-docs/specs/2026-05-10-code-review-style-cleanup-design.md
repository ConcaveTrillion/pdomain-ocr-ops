# Code-review + style-cleanup workflow (v2)

> **Status**: Active (operational rollout pending; see 2026-05-11-INDEX.md)
> **Last updated**: 2026-05-11

## TL;DR

Two new bots, one new CT-interactive skill (`/pr-review`), and a handful of deterministic scripts extend the v1 ship-issue chain with a code-review and style-cleanup story. A daily `style-review-bot` reviews each rolling `wip/ship-issue` PR and lands auto-fixes for high-confidence rule violations alongside flagged comments for judgment-call findings. A weekly `style-sweep-bot` does the same against full-repo drift on its own rolling `wip/style-sweep` branch. CT walks flagged comments via `/pr-review`, which pauses all bots for the duration of the review window. Each pd-* repo gets a self-contained `CONVENTIONS.md` with a synced cross-repo block plus a repo-specific section. All bots run in isolated worktrees under `/srv/bot-workspaces/`; ship-issue is retrofitted to the same pattern so CT's main checkouts stay pristine. The design draws an explicit script-vs-LLM boundary: only rule-violation detection and sibling-drift comparison invoke an LLM; everything else (sync, format-validation, fix application, dashboard rendering) is deterministic.

## Context

Today's pipeline (v1, [2026-05-10-feature-request-spec-decomposition-design](2026-05-10-feature-request-spec-decomposition-design.md) and [2026-05-09-github-issues-projects-design](2026-05-09-github-issues-projects-design.md)) ships PRs end-to-end via `ship-issue`, which delegates the TDD slice to whichever model the issue's `model:` label selects (haiku, sonnet, opus). Most slices run on Haiku for cost reasons. Haiku's output is functionally correct but stylistically inconsistent: it over-comments, hedges with backwards-compat shims, adds error handling for cases that can't happen, and drifts from the conventions encoded in workspace CLAUDE.md feedback memories. Pre-commit hooks (ruff, markdownlint) catch the mechanical violations; everything else accumulates as drift and lands in PRs CT reviews under fatigue.

Two needs surface:

1. A **per-PR review pass** that catches style/convention drift on each rolling ship-issue PR, applies high-confidence fixes automatically, and surfaces judgment calls for CT.
2. A **periodic sweep** that catches accumulated drift in code ship-issue didn't recently touch — including legacy code that pre-dates the conventions doc.

Plus prerequisite work: the conventions themselves don't exist as a written artifact today (they live as scattered CLAUDE.md memories), so this design includes the bootstrap path. And ship-issue currently writes to the main `/workspaces/ocr-container/<repo>/` checkout, which means CT's interactive `git status` is dirty whenever a bot runs — an issue that gets worse as more bots land. This design also retrofits ship-issue to the new isolated-worktree pattern.

## Constraints

- **Builds on v1, doesn't change it.** The `bot:*-ready` family, the rolling-`wip/ship-issue` PR pattern, and the `claude-bot` user's existing scope all carry forward unchanged.
- **Lint-first.** Mechanical violations (formatting, naming, dead imports) are caught by tightened ruff/markdownlint/pyright configs in Phase 0. The bot reviews against prose conventions only; mechanical findings are out of its scope.
- **CT as final arbiter on taste.** Judgment-call findings never auto-apply — they become PR review comments CT walks via `/pr-review`. High-confidence findings auto-apply but are reverted if `make fast-check` breaks.
- **External-contributor friendly.** Each pd-* repo's `CONVENTIONS.md` is self-contained: cross-repo conventions are inlined (synced from a workspace canonical via marker-delimited block), repo-specific conventions follow below. An external contributor cloning a single repo sees the full picture.
- **No simultaneous bot writes to the same branch.** A single workspace pause flag plus per-branch flock serialize ship-issue, style-review-bot, and style-sweep-bot.
- **Existing ship-issue invariants preserved.** Bot never pushes to main; rolling PR pattern preserved; `pd-push` remains the only push path; `bash-command-guard.py` enforcement unchanged.
- **No new gh PAT scope.** Existing `claude-bot` token covers PR creation, label management, and review-comment posting.

## Decision

### Architecture overview

Two bots, one CT-interactive skill, and a set of scripts:

**Bots and skills (LLM-bound):**

| name | runs as | model | trigger | output target |
|---|---|---|---|---|
| `style-review-bot` | claude-bot | sonnet (low) | daily ctask, no-op if no commits since last review | additional commits + review comments on rolling `wip/ship-issue` PR |
| `style-sweep-bot` | claude-bot | sonnet (medium) | weekly ctask via `recurring:weekly` chore issue armed with `bot:style-sweep-ready` | own rolling `wip/style-sweep` branch + draft PR |
| `/pr-review` | vscode | n/a (interactive) | CT invokes when ready to walk a PR | applied fixes, flagged comments resolved, optional new conventions rules |

**Scripts (deterministic or one-shot LLM):**

| name | when it runs | what it does |
|---|---|---|
| `scripts/sync-conventions.py` | invoked manually after CT edits the workspace canonical | regenerates the marker block in each pd-* repo, commits, pd-pushes |
| `scripts/check-sync-drift.py` | every dashboard refresh (SessionEnd hook + hourly ctask) | byte-compares each repo's marker block against the canonical; emits `sync-drift.json` |
| `scripts/check-sibling-drift.py` | weekly via ctask | one Sonnet call comparing all repos' Repo-specific sections; emits `sibling-drift.json` |
| `scripts/extract-conventions.py` | one-shot bootstrap per repo | gathers inputs deterministically; one LLM call to draft rules; CT reviews the draft |
| `scripts/lint-conventions.py` | pre-commit + bot pre-flight | mechanical format check on `CONVENTIONS.md` (rule-template structure, marker integrity) |
| `scripts/style-review-detect.py` | invoked by both bots and `/pr-review` | LLM call: classifies findings against `CONVENTIONS.md`; emits a JSON contract |
| `scripts/style-review-apply.py` | invoked after `style-review-detect.py` | deterministic: applies high-confidence patches, runs `make fast-check`, reverts on failure, posts comments via `gh` |
| `scripts/style-review-orchestrator.sh` | ctask entry | the daily wrapper around detect+apply for `wip/ship-issue` |
| `scripts/style-sweep-orchestrator.sh` | ctask entry | the weekly wrapper around detect+apply for `wip/style-sweep` |

### Bot-isolation topology

```
/workspaces/ocr-container/             # CT's main, pristine
  pdomain-book-tools/                       # CT's interactive checkout
  ...

/srv/bot-workspaces/                   # NEW — owned by claude-bot
  ship-issue/pdomain-book-tools/            # git worktree on wip/ship-issue
  style-review/pdomain-book-tools/          # git worktree, also tracks wip/ship-issue
  style-sweep/pdomain-book-tools/           # git worktree on wip/style-sweep
  .locks/                              # flock files
  .state/bots-paused                   # pause flag (presence = pause)
  ...
```

Single `.git/` per repo lives under CT's main checkout; the three bot worktrees share its object DB via `git worktree add`. Ship-issue is retrofitted in Phase 1 — its orchestrator `cd`'s into `/srv/bot-workspaces/ship-issue/<repo>/` instead of `/workspaces/ocr-container/<repo>/`. CT's main checkout is never written to by any bot.

**Branch-contention coordination.** Git allows only one worktree per branch, so `style-review` and `ship-issue` cannot both have `wip/ship-issue` checked out at the same time. Resolution: each bot's worktree sits at **detached HEAD** between runs, pointed at the last sha it processed. When a bot becomes active inside its flock window, it runs `git checkout wip/ship-issue` (succeeds because no peer holds the branch), does its work, pushes, then `git checkout --detach HEAD` before releasing the lock. The flock at `/srv/bot-workspaces/.locks/ship-issue.<repo>.lock` serializes the borrow-the-branch windows. Style-sweep uses a different branch (`wip/style-sweep`) so no contention with the other two.

### Review window coordination

`/pr-review` is the one place that pauses all bots. Concurrency model:

- `/srv/bot-workspaces/.state/bots-paused` flag file. Presence = paused; mtime = pause-start; 6h TTL auto-recovers from abandoned `/pr-review` sessions.
- All ctask-scheduled orchestrators check the flag at startup; skip + reschedule if present.
- `/pr-review` lifecycle:
  1. **Pre-check**: touch `bots-paused`; wait (bounded, with status messages) for any in-flight bot run to finish naturally — never kill mid-commit.
  2. **Fresh final review**: invoke `style-review-detect.py` then `style-review-apply.py` against current `wip/ship-issue` HEAD; auto-fixes commit and push; flagged comments are written fresh, replacing prior daily-run comments.
  3. **Walkthrough**: CT walks each flagged comment one at a time via the `AskUserQuestion` tool: file, line, rule citation, proposed diff, four options (apply / dismiss / dismiss-and-add-rule / edit-then-apply).
  4. **Post**: remove `bots-paused`; tell CT "schedules resumed". If CT marked PR ready-for-review, ship-issue's existing locked-PR rule kicks in.

**Stale-comment marker.** Each style-review run tags `style-review/<repo>/<sha>`. `/pr-review` reads it to decide whether prior comments are reusable (no commits since → keep) or stale (any new commits → throw out, regenerate fresh).

### Conventions docs

**Two-layer prose, lint-first, per-repo self-contained.**

- Workspace canonical: `/workspaces/ocr-container/CONVENTIONS.md` (CT edits here).
- Per-repo: `<repo>/CONVENTIONS.md`, structured as:
  - Cross-repo block, marker-delimited (`<!-- workspace-conventions:start -->...end -->`), regenerated by `/sync-conventions` from the canonical. Manual edits inside the markers are drift and get overwritten.
  - Repo-specific section below the markers, freely editable, never overwritten.

The bot reads only the per-repo file (already self-contained). External contributors clone one repo, see one `CONVENTIONS.md`, get the full picture.

**Rule format** (per-rule heading inside each section):

```markdown
## Rule: <rule statement>

**The rule.** <one paragraph stating it precisely>

**Why.** <one sentence — links to a CLAUDE.md feedback memory or
prior-incident commit when applicable>

**Common high-confidence violations** (bot auto-fix candidates)
- <pattern>
- <pattern>

**Common judgment-call violations** (bot flags, CT decides)
- <pattern>
- <pattern>
```

The "common violations" lists are **guidance** for the bot's tier judgment, not a binding per-rule policy. The bot still classifies each individual finding's confidence; the examples anchor it.

**Lint-first prep work** (Phase 0, applies workspace-wide before any bot lands):

- ruff: enable `N` (naming), `B` (bugbear), `SIM` (simplify), `UP` (pyupgrade), `RUF` (ruff-specific), `ERA` (commented-out code), `T20` (no print in library code) on top of existing `I` (imports).
- pyright/ty: strict mode on `src/`, default on `tests/`.
- markdownlint stays as-is.
- pre-commit: add a `no-trailing-todos` hook (TODO without tracking issue or date is rejected).

Mechanical violations are blocked at commit time and never reach a PR; the bot's prose review concentrates on judgment-level rules where its value is highest.

### Script vs LLM boundary

Drawing the boundary explicitly so future contributors don't accidentally route deterministic work through an LLM session.

**LLM-bound steps** (the only places token cost is incurred):

- **Rule-violation detection and confidence classification** — `style-review-detect.py`. Reads `CONVENTIONS.md` plus the input scope (diff or full-tree); emits a JSON list of findings with proposed patches and confidence tier. Conventions doc is the cacheable prefix; scope is the variable suffix.
- **Sibling-drift comparison across repos** — `scripts/check-sibling-drift.py`. One weekly Sonnet call comparing all repos' Repo-specific sections.
- **Bootstrap synthesis from CLAUDE.md memories** — `scripts/extract-conventions.py`. One Sonnet call per repo at first-time bootstrap.
- **`/pr-review` walkthrough** — interactive Claude session presenting findings to CT via `AskUserQuestion`. Cost is per CT review session; bounded by the number of flagged comments.

**Deterministic steps** (no token cost):

- Reading `CONVENTIONS.md`, computing diffs, gathering memories, scanning files.
- Sync-drift detection (byte-comparing the marker block against the canonical).
- Applying patches (`git apply`), running `make fast-check`, reverting on failure, posting comments via `gh`, moving git tags, applying labels, taking flocks.
- Format validation of `CONVENTIONS.md` (rule-template structure, marker integrity).
- All orchestrator wrappers (`*-orchestrator.sh`).
- Dashboard panel rendering (reads JSON, emits HTML).

**Pattern for "is X drifting?" questions across the workspace:** deterministic check → frequent + free; LLM check → periodic + cached → dashboard renders the cache. Sync-drift and sibling-drift both follow this pattern. Future drift questions (e.g., "are CLAUDE.md feedback memories drifting from observed behavior?") can reuse the same shape.

### Shared review engine — split for prompt-caching

The engine is **two scripts** with a JSON contract between them, not one script with both responsibilities:

**`scripts/style-review-detect.py`** (LLM-bound):

1. Read per-repo `CONVENTIONS.md`.
2. Read input scope: a list of commits (daily review) or full working tree (sweep).
3. Single LLM call (sonnet) classifying findings: rule citation, file:line, proposed patch (unified diff), confidence (high or judgment).
4. Output: JSON to stdout — `{ "findings": [...], "stats": {...} }`.

The conventions doc is the static prefix in the LLM prompt — explicit prompt-caching boundary. A given repo's conventions are paid for once per cache window, not per finding or per file.

**`scripts/style-review-apply.py`** (deterministic):

1. Read JSON output from `style-review-detect.py` (file or stdin).
2. For each finding:
   - **High** → `git apply` the patch; `make fast-check`; if green, commit; if red, demote to judgment and revert.
   - **Judgment** → emit a PR-review-comment record.
3. Push commits via `pd-push`.
4. Post comments via `gh pr review --comment`.
5. Move tags, apply labels.
6. Output: summary stats; events appended to `style-bot-events.jsonl`.

The split also means the apply step is independently testable with fixture JSON — no LLM needed in the test loop.

### Daily style-review-bot orchestrator

`scripts/style-review-orchestrator.sh`, parallel to `ship-issue-orchestrator.sh`:

```
1. Check bots-paused → skip + reschedule if present
2. Take .locks/ship-issue.<repo>.lock (flock)
3. cd /srv/bot-workspaces/style-review/<repo>/
4. git fetch; git checkout wip/ship-issue; git pull
5. Read style-review/<repo>/<sha> tag → if HEAD == tag, no-op exit (release lock + return)
6. Invoke style-review-detect.py with scope = `git rev-list <tag>..HEAD` → JSON
7. Pipe JSON to style-review-apply.py (handles: git apply, make fast-check, commit, pd-push, gh pr review --comment, events log)
8. Move style-review/<repo>/<sha> tag to new HEAD; push tag
9. If any auto-fix landed: apply bot:style-fixed-by-agent label
10. git checkout --detach HEAD (release the branch for the next bot)
11. Release lock
```

### Weekly style-sweep-bot orchestrator

`scripts/style-sweep-orchestrator.sh`, triggered by a per-repo `recurring:weekly` chore issue armed with `bot:style-sweep-ready`:

```
1. Check bots-paused → skip + reschedule if present
2. cd /srv/bot-workspaces/style-sweep/<repo>/
3. git fetch; git checkout wip/style-sweep (create from main HEAD if missing)
4. git reset --hard origin/master
5. Invoke style-review-detect.py with scope = full repo + cap (default 50 + 50) → JSON
   - detect.py honors the cap; emits sweep-capped event in JSON if hit
6. Pipe JSON to style-review-apply.py (handles: git apply, make fast-check, commit, pd-push, comment posting, events log)
7. If wip/style-sweep PR doesn't exist: gh pr create --draft (apply.py creates it on first commit; otherwise no-op)
8. Update the chore issue body with a summary
9. git checkout --detach HEAD
```

The cap is informational, not bouncy: the PR carries the partial set; the next weekly tick continues from the new HEAD. Cap is configurable via `.claude/style-bot.toml`.

### Bot operational events log

`$SHIP_ISSUE_MEMORY_DIR/style-bot-events.jsonl` — append-only, mirrors v1's `permission-denials.jsonl`. Surfaced as a "Style-bot events" panel on `cost-dashboard.html`.

Initial event kinds (extensible):

- `sweep-capped` — sweep hit its per-run cap; details include `top_rules` for calibration.
- `auto-fix-reverted` — high-confidence fix demoted because `make fast-check` broke. Calibration signal: too many of these on one rule means its high-confidence examples in `CONVENTIONS.md` are wrong.
- `missing-conventions` — repo has no `CONVENTIONS.md` or it's malformed; bot blocks.
- `lock-contention` — bot tried to run inside `bots-paused` or against a held lock; informational.
- `fast-check-prebroken` — repo's `make fast-check` was already failing; bot exits without changes.

Calibration-relevant kinds render with a flag color so CT notices week-over-week patterns.

### CT-interactive skill (the only one)

**`/pr-review [<repo>]`** — lifecycle in "Review window coordination" above.

- Argument optional; defaults to repo of CT's cwd; workspace cwd → prompts CT to pick.
- Walkthrough uses `AskUserQuestion` per finding.
- Add-rule path opens an `Edit` on the appropriate `CONVENTIONS.md` (workspace canonical for cross-repo, per-repo for repo-specific) — CT chooses which. Skill drafts the rule from the comment context; CT edits before saving.
- Pre-walkthrough fresh-review step shells out to `style-review-detect.py` + `style-review-apply.py` (the same two scripts the bots use). The skill is thin: it owns the pause-flag lifecycle and the `AskUserQuestion` walkthrough loop; it does not re-implement detection or application logic.

### Scripts (deterministic and one-shot LLM)

**`scripts/sync-conventions.py`** — replaces the originally-proposed `/sync-conventions` skill:

- Reads workspace canonical → regenerates the marker-delimited block in each repo → if changed, `git add` + `git commit -m "chore: sync cross-repo conventions to <workspace-SHA>"` + `pd-push` to the current branch.
- Refuses to push to a branch the user didn't expect (default-branch only unless `--allow-branch=<name>`).
- Skips repos where regenerated block byte-matches the in-repo block.
- Sets `bots-paused` for the duration so the sync isn't interleaved with a bot run pushing to the same branch.
- Optional `--confirm` flag for per-repo prompt-before-push interactive mode; default is auto-apply across all repos with a final summary.
- Invocable via `make sync-conventions` or directly. No Claude session.

**`scripts/check-sync-drift.py`** — runs every dashboard refresh:

- For each pd-* repo, fetches the in-repo `CONVENTIONS.md` (via `gh api repos/.../contents/CONVENTIONS.md`), extracts the marker-delimited block, byte-compares against a fresh regeneration from the workspace canonical.
- Mismatches written to `$SHIP_ISSUE_MEMORY_DIR/sync-drift.json`.
- No LLM. Idempotent and cheap; safe to run on the existing hourly + SessionEnd cadence alongside the cost-dashboard build.

**`scripts/check-sibling-drift.py`** — runs weekly via ctask:

- Pulls each repo's *Repo-specific conventions* section.
- One Sonnet API call (via the `claude-api` skill's pattern, or direct anthropic SDK call from the script) asking for pairs of rules across repos that overlap in concern but differ in wording.
- Output: `$SHIP_ISSUE_MEMORY_DIR/sibling-drift.json`.
- Cost: one call per week, ~cents.

**`scripts/extract-conventions.py [<repo> | --workspace]`** — bootstrap, replaces the originally-proposed `/extract-conventions` skill:

- Gathers inputs deterministically: workspace CLAUDE.md, repo CLAUDE.md, all `.claude/agent-memory/<agent>/feedback_*.md` and `project_*.md` files, recent commits/PRs (last 90 days), and the workspace canonical if it exists. Pure file I/O.
- One Sonnet API call to draft the per-repo skeleton (cross-repo synced block + proposed repo-specific section).
- Writes the draft to `<repo>/CONVENTIONS.md.draft`. CT reviews, edits, then `mv` to `CONVENTIONS.md`.
- Idempotent: refuses to overwrite an existing `CONVENTIONS.md` unless `--force`; non-force opens diff-mode suggesting additions to a `.diff` file.
- Workspace mode: same shape but only workspace-level inputs; output is the canonical.

**`scripts/lint-conventions.py`** — mechanical format check:

- Verifies rule-template structure (each `## Rule:` heading has the four expected sub-sections).
- Verifies marker integrity in per-repo files (start/end markers present, paired, well-formed).
- Verifies cross-repo block in per-repo file matches the canonical (delegates to `check-sync-drift.py` logic).
- Wired into pre-commit (workspace meta + each pd-* repo) and into the bot's pre-flight (`missing-conventions` event fires on lint failure).

**Dashboard panels** (rendered by `build-cost-dashboard.py`):

- "Sync drift" — reads `sync-drift.json`. Per-repo row showing in-sync / drifted with the offending diff.
- "Sibling drift" — reads `sibling-drift.json`. Candidate-consolidation list with cited rule pairs.
- "Style-bot events" — reads `style-bot-events.jsonl` (already specified above).

All three panels are deterministic rendering of pre-computed JSON. The dashboard build itself never invokes an LLM.

### New labels

Added to `seed-labels.sh` (workspace-wide):

| label | meaning |
|---|---|
| `bot:style-review-ready` | applied by CT to a PR (or auto-armed by ship-issue's orchestrator on PR creation, configurable) to authorize daily review-bot |
| `bot:style-sweep-ready` | applied by CT to the weekly `recurring:weekly` chore issue to authorize sweep-bot |
| `bot:style-fixed-by-agent` | applied by the bot itself after auto-applying any fixes; informational for CT's PR list view |

### Implementation sequencing

Phases must land in order; no skipping ahead.

| phase | scope | what lands | exit criteria |
|---|---|---|---|
| **0** | All 7 pd-* repos | Lint-first config tightening | Pre-commit passes on each repo with new rules |
| **1** | Workspace meta | Per-bot worktree topology + ship-issue retrofit | Ship-issue runs end-to-end against its own worktree; CT's `git status` stays clean during a run |
| **2** | pdomain-book-tools only | Bootstrap `CONVENTIONS.md` (workspace + pdomain-book-tools) | Both files exist, CT-approved |
| **3** | pdomain-book-tools only | `/pr-review` skill (CT-interactive only, no bots yet) | CT can walk a fixture rolling PR end-to-end |
| **4** | pdomain-book-tools only | Daily style-review-bot + events log + dashboard panel | One full week of daily runs without intervention |
| **5** | pdomain-book-tools only | Weekly style-sweep-bot + cap + events | One full month (4 sweeps) without runaway cost or wedged state |
| **6** | Workspace meta | `scripts/sync-conventions.py`, `scripts/check-sync-drift.py`, `scripts/check-sibling-drift.py`, `scripts/lint-conventions.py`, dashboard panels | Sync, sync-drift, sibling-drift panels render on dashboard; sync correctly identifies "no change"; lint-conventions catches malformed test fixtures |
| **7** | Remaining 6 pd-* repos | Roll out: bootstrap each, arm labels, schedule ctask | All 7 repos covered; cross-repo drift report has real content |

The constraint is explicit (mirroring v1 spec): do not roll out bots to other pd-* repos until pdomain-book-tools is solid through Phase 6.

## Contract / Acceptance

This spec is implemented when:

- [ ] Phase 0 lint-config bumps merged to all 7 pd-* repos; pre-commit passes
- [x] `/srv/bot-workspaces/` topology exists; ship-issue retrofitted; CT's main checkouts stay clean during a ship-issue run
- [x] `scripts/extract-conventions.py` exists; workspace `CONVENTIONS.md` and pdomain-book-tools `CONVENTIONS.md` written and CT-approved
- [x] `scripts/lint-conventions.py` exists; pre-commit catches malformed `CONVENTIONS.md` fixtures
- [x] `/pr-review` skill exists; walks fixture flagged comments end-to-end; bots-paused flag toggles correctly
- [ ] `scripts/style-review-detect.py` (LLM) + `scripts/style-review-apply.py` (deterministic) + `style-review-orchestrator.sh` + ctask schedule entry; first week of daily runs against pdomain-book-tools observed clean
- [ ] `scripts/style-sweep-orchestrator.sh` + `recurring:weekly` chore issue + `bot:style-sweep-ready` label; first month (4 sweeps) on pdomain-book-tools observed clean
- [x] `style-bot-events.jsonl` written by both bots; "Style-bot events" panel renders on `cost-dashboard.html`
- [x] `scripts/sync-conventions.py` correctly identifies no-change and applies changes idempotently
- [x] `scripts/check-sync-drift.py` writes `sync-drift.json`; "Sync drift" dashboard panel renders
- [x] `scripts/check-sibling-drift.py` runs weekly via ctask; writes `sibling-drift.json`; "Sibling drift" dashboard panel renders
- [ ] Three new labels (`bot:style-review-ready`, `bot:style-sweep-ready`, `bot:style-fixed-by-agent`) seeded across all 7 repos
- [ ] Phase 7 rollout: `CONVENTIONS.md` exists in all 7 pd-* repos; ctask entries scheduled per repo

## Trade-offs considered

| Approach | Pro | Con |
|---|---|---|
| Daily review on rolling `wip/ship-issue` PR (chosen) | Catches drift in real time; CT reviews everything on one PR; preserves v1's single-rolling-PR model | Bot edits interleave with CT's review; staleness across `/pr-review` window needs explicit coordination (paused-flag, fresh final review) |
| Per-PR fresh PR for review-bot output | Total isolation between ship-issue and review commits | Doubles PR count; contradicts v1's rolling-PR principle |
| Comment-only review-bot, no auto-fix | Bot never breaks anything | Front-loads all the fix work onto CT — defeats the goal |
| Tier fixes by bot judgment + `/pr-review` for flagged (chosen) | Auto-applies the safe wins; CT keeps taste-level authority | Calibration burden falls on the conventions doc's example quality |
| Per-rule auto-fix policy in `CONVENTIONS.md` | Most explicit; bot just follows the doc | Doubles authoring work; risk of getting tier wrong and reclassifying |
| Lint-first + short prose for the rest (chosen) | Mechanical tools handle what they can; prose stays small + readable | Phase 0 is upfront work that delays the visible payoff |
| Prose-only, bot enforces both mechanical + judgment | Single source of truth | Wastes tokens reviewing what ruff already catches; slower runs |
| Per-repo self-contained `CONVENTIONS.md` with synced block (chosen) | External contributors see one file; canonical stays single-source | `/sync-conventions` needs care; manual edits inside markers are drift |
| Per-repo `CONVENTIONS.md` with no shared canonical | Simplest model | Cross-repo rules drift fast; updating one rule means editing 7 files |
| Per-bot isolated worktrees + ship-issue retrofit (chosen) | CT's `git status` stays clean; future bots inherit pattern; shared object DB is disk-efficient | Worktree branch-contention nuance (style-review and ship-issue share `wip/ship-issue`) needs flock |
| Worktrees only for new bots, leave ship-issue alone | Smaller scope | Inconsistent — CT's status still gets churned by ship-issue |
| Lockfile-only, no isolation | Cheapest | Doesn't address dirty `git status` at all |
| Per-run cap with sweep-capped event (chosen) | Bounded cost; CT informed; no bouncy failure | Calibration via dashboard rather than at the source |
| Bounce-back on >N findings | Forces immediate triage | Adds churn for what's usually a normal "lots of legacy code" signal |
| Scripts for mechanical work, skills only where genuinely interactive (chosen) | One LLM call per place that needs judgment; everything else free; testable without tokens; explicit prompt-cache boundary on conventions doc | More files in `scripts/` to maintain; readers must learn which surface is which |
| All four originally-proposed skills (`/pr-review`, `/check-convention-drift`, `/sync-conventions`, `/extract-conventions`) | Uniform framing; one mental model | Three of the four had no judgment to apply; spawning a Claude session per invocation wastes tokens and adds latency |
| Single combined `style-review.py` with both detect + apply | Smaller surface | Conventions doc gets re-tokenized per finding instead of being prompt-cached once per scope; apply step is harder to test independently |
| Detect + apply split with JSON contract (chosen) | Conventions cached once per scope; apply step is fixture-testable; CI can exercise apply without burning tokens | Two files instead of one; the contract becomes a thing that can drift |

## Consequences

- The `bot:` label namespace gains three new values; future bots continue the pattern.
- A new operational surface exists at `$SHIP_ISSUE_MEMORY_DIR/style-bot-events.jsonl` and a corresponding dashboard panel. CT consults it at least weekly to spot calibration drift.
- The `/srv/bot-workspaces/` directory becomes the canonical home for all bot worktrees. Future bots add their own subdirectory; the lockfile pattern is reusable.
- `CONVENTIONS.md` files become a new artifact in every pd-* repo. They're authoritative for code style; existing CLAUDE.md files focus on agent-routing, project-state, and tool-use guidance (not style).
- The `/pr-review` skill becomes CT's primary daily interface for shipped work. The walkthrough UX establishes a pattern other future skills can mirror (e.g., `/triage`'s row-at-a-time CT review).
- Phase 0 lint-config tightening produces a one-time wave of cleanup commits per repo. Existing legacy code may need `# noqa` annotations or fixes; this is contained scope per repo and can land independently of bots.
- The 6h auto-recovery on `bots-paused` means an abandoned `/pr-review` session doesn't wedge the bot schedule indefinitely. The recovery is logged loudly so CT notices.
- The script-vs-LLM split establishes a workspace-wide pattern: deterministic checks render on every dashboard refresh; LLM-bound checks run on a periodic schedule and emit JSON the dashboard reads. Future "is X drifting?" questions reuse the same shape rather than spawning a new skill each time.
- The conventions doc becomes a deliberate prompt-cache prefix in `style-review-detect.py`. Implementations should pass the doc as a cacheable system message (or via the SDK's prompt-caching API) so a busy day's many short reviews share the cost of tokenizing the doc once. This is the single highest-leverage cost choice in the design.
- New skill count is one (`/pr-review`). Three originally-proposed skills (`/check-convention-drift`, `/sync-conventions`, `/extract-conventions`) became plain scripts. Calling out the count explicitly so future contributors don't re-introduce skill wrappers around mechanical work.

## Open questions

1. **Auto-arming `bot:style-review-ready` on PR creation** — should ship-issue's `success.sh` auto-arm the label, or does CT arm it manually per PR? Lean: auto-arm (style review is universally desired); CT can remove the label on PRs they want bot-untouched. Status: **open, lean auto-arm**.
2. **Workspace-tooling repo for the canonical `CONVENTIONS.md`** — v1 spec resolved a similar question for feature-requests by creating `ConcaveTrillion/ocr-container-meta` (private). The workspace canonical conceptually belongs there. Confirm this is the intended home before Phase 2 lands. Status: **open, verify with v1 resolution**.
3. **Per-rule auto-fix calibration loop** — when the events log shows a rule with persistent `auto-fix-reverted` events, should `/check-convention-drift` propose demoting its high-confidence examples to judgment-call examples automatically, or stay read-only? Lean: stay read-only; CT decides. Status: **open, lean read-only**.
4. **Style-sweep on non-Python repos** — pd-png-optimizer's Rust core has different conventions and toolchain (`cargo fmt`, `cargo clippy`). Does style-sweep handle Rust at all in v2, or only the Python facade? Lean: Python only in v2; Rust gets its own variant in a future iteration. Status: **open, lean Python-only**.
5. **Cost ceiling per repo** — if a repo's monthly bot spend exceeds a threshold, should style-sweep skip until next month? No mechanism in v2 — sweep just runs. Could add a `style-bot-events.jsonl` `cost-throttled` kind in v3. Status: **open, no v2 mechanism**.

## References

- [docs/specs/2026-05-09-github-issues-projects-design.md](2026-05-09-github-issues-projects-design.md) — v1 GitHub-issues spec; rolling-PR pattern; `bot:` label family origin
- [docs/specs/2026-05-10-feature-request-spec-decomposition-design.md](2026-05-10-feature-request-spec-decomposition-design.md) — v1 feature-request lifecycle; `bot:ship-issue-ready` rename and label-family precedent
- `scripts/ship-issue-orchestrator.sh` — pattern for the new `style-review-orchestrator.sh` and `style-sweep-orchestrator.sh`
- `scripts/build-cost-dashboard.py` — `permission-denials.jsonl` rendering; new `style-bot-events.jsonl` panel mirrors this
- `scripts/seed-labels.sh` — three new labels added here
- `scripts/lint-spec.py` — 9-section template enforcement
- `.claude/skills/ship-issue/SKILL.md` — bot-side skill pattern; `style-review` and `style-sweep` skills mirror its structure
- `.claude/hooks/bash-command-guard.py` — existing enforcement model preserved; no new rules needed
