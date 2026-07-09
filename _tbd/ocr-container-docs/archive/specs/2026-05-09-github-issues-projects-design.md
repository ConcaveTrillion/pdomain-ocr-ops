# GitHub Issues + ship-issue — workspace design

> **Status**: Draft
> **Last updated**: 2026-05-09
> **Related**: [docs/doc-cleanup-plan.md](../../doc-cleanup-plan.md)

> **2026-05-09 design pivot:** the original draft put workflow status on a per-repo GitHub **Project board** (Status field). That required a fine-grained PAT scope (`Projects: Read and write`) that **does not exist for user-owned PATs** — it's an Organization-level permission only, and `ConcaveTrillion` is a user account. Workflow status is now carried as a `status:*` label family instead. The label-family approach was originally listed under "Trade-offs considered" as rejected; it is now the chosen design. See the updated tradeoff table for the reasoning.

> **Note (2026-05-10):** the `claude-ok` label was renamed to `bot:ship-issue-ready` in the `bot:` family by [the feature-request lifecycle spec](2026-05-10-feature-request-spec-decomposition-design.md). Mentions below predate the rename.

## TL;DR

Replace per-repo `ROADMAP.md` files with GitHub Issues that carry workflow status as a `status:*` label family. Rename the `ship-slice` skill family to `ship-issue` and have it pick work from the `status:ready` queue (`gh issue list -l status:ready -l claude-ok`). Telemetry (tokens, API cost, plan usage %) is captured locally per run and rendered as a static HTML dashboard. Specs stay co-located with code as `.md` files but follow a standard 9-section template enforced by a pre-commit lint hook with a legacy-file allowlist.

## Context

The workspace is eight `pd-*` repos maintained by a one-person team with AI-agent collaborators. Today, open work is tracked in `ROADMAP.md` (or `docs/roadmap/`) per repo, with inline `(S)/(M)/(L)` effort tags. Two compounding problems:

1. **Token cost**: Claude reads every non-ignored `.md` at session start. ROADMAP files plus reference specs add up to ~10k+ lines of context that's read every session and used in maybe 1% of them.
2. **Discovery friction**: Picking the next slice means grepping eight markdown files. There's no cross-repo dashboard, no triage queue, and no audit trail of what was done when.

GitHub already provides Issues (work items) and Labels (filterable taxonomy). They were unused because there was no migration path and no agent integration. This design provides both. Project boards were considered for workflow status but ruled out — see the design pivot note above.

## Constraints

- **Public repos**, so external users can file issues; the design must prevent agent-injection via attacker-supplied content.
- **One-person team**, so no review-burden multiplier from creating ceremony for ceremony's sake. Overnight automation must yield at most one PR per session, not one PR per issue.
- **Existing scaffolding** is partly built: `pd-gh` (scoped `gh issue` wrapper), `pd-gh-issue-guard.py` hook (gates issue mutations on `claude-ok` label), `ctask` (local cron). The design **retains and extends `ctask`**, but **replaces** `pd-gh` and `pd-gh-issue-guard.py` with the unified `bash-command-guard.py` rule set + scoped PAT + branch protection (option C below). The `claude-ok` mutation-gate semantics are preserved; the enforcement just moves from a wrapper to a hook.
- **Subscription plan billing** (max-20x): telemetry must capture both subscription-cap usage % and theoretical API cost in case the user later switches to API billing.
- **Spec content can be sensitive** but is currently public-by-default. Stay co-located with code unless that changes.
- **Hard requirement**: cross-references between issues, code, and specs must not silently rot. Spec anchor stability is non-negotiable.

## Decision

### Architecture

- **Per-repo Issues, no Project boards.** Eight independent issue trackers. Cross-repo dependencies are captured as plain-text `Depends on: ConcaveTrillion/<repo>#N` lines in the issue body — no automation.
- **ROADMAP.md is retired.** Each repo's `docs/ROADMAP.md` (or `docs/roadmap/`) is deleted. CLAUDE.md gains a 5-line milestone-status table.
- **Labels carry both routing data and workflow state.** Both are queryable cheaply via `gh issue list -l <label>`. Workflow state lives in a `status:*` single-select label family enforced convention-side by the scripts that move issues between states (always strip existing `status:*` before adding the new one).
- **`ship-slice` is renamed to `ship-issue`** (1 orchestrator + 8 per-repo skills).
- **Procedural work is in scripts; agent skills only orchestrate.** Querying issues, validating eligibility, claiming, pushing, opening draft PRs, computing telemetry, scanning for denials — all deterministic glue lives in `scripts/`, owned `vscode:vscode` and immutable to the bot. The agent's skill prompts are short orchestrators that delegate to scripts and only reason where judgment is required (TDD slice work, spec splitting, triage decisions).
- **Scripts use bare `gh` and `git` with `GH_TOKEN_PD` in env.** No `pd-gh` wrapper. The PAT's fine-grained scope plus branch protection on `main` plus the `bash-command-guard` PreToolUse hook are the security layers. `pd-push` remains as the single push wrapper because branch-target restriction (only `wip/ship-issue`) cannot be expressed by PAT scope or branch protection alone.

### Label taxonomy

Six single-select label families plus two boolean labels. Single-select means at most one value per family on any given issue:

| Family | Values | Required when |
|---|---|---|
| `kind:` | `feature`, `bug`, `spec`, `chore` | always (exactly one) |
| `effort:` | `S`, `M`, `L` | required for `feature`, `bug`, `chore`; optional for `spec` (research work is hard to size before doing). If you can't size a bug before investigating, default to `effort:M` and update on triage. |
| `model:` | `haiku`, `sonnet`, `opus` | required for ship-issue eligibility |
| `model-effort:` | `low`, `medium`, `high`, `xhigh`, `max` | required for ship-issue eligibility; `xhigh` requires `model:opus` |
| `area:` | free per repo (`backend`, `frontend`, `cli`, `ui`, `docs`, …) | optional |
| `recurring:` | `weekly`, `monthly`, `quarterly` | only on recurring chores |
| `status:` | `backlog`, `ready`, `in-progress`, `done`, `blocked` | always (exactly one); `blocked` is optional in steady state |
| `claude-ok` | (boolean) | manual mutation gate from the existing hook |
| `triage:tracking` | (boolean) | optional, marks an internal issue that shadows an external user report |

The `status:*` family is single-select by convention: the scripts that transition state (`ship-issue-pick.py`, `ship-issue-failure.sh`, `ctask` chore creation) always remove all existing `status:*` labels before adding the new one. GitHub does not enforce this server-side, so any tooling that mutates status must follow the same discipline.

### Issue body templates

Five templates in `.github/ISSUE_TEMPLATE/`:

- `feature.md` — Context, Spec, Acceptance, Out of scope
- `bug.md` — Repro, Expected, Actual, Notes
- `spec.md` — Question, Constraints, Options on the table, Notes
- `chore-recurring.md` — Routine, Checks, When done
- `chore-migrate-legacy-spec.md` — Routine, Procedure (1 or 4), Acceptance, When done

The `Spec:` line in feature bodies points at the relevant per-repo spec by `path:anchor` (e.g., `Spec: docs/specs/02-backend.md#decision`). Acceptance bullets are concrete checkboxes a reviewer or test can verify.

### Bug handling — the bug IS the work item

A `kind:bug` issue is what ship-issue runs on directly. There is no separate "fix" issue spawned from a bug. The bug body's Repro/Expected/Actual gives ship-issue everything needed to:

1. Write a failing test that reproduces the bug.
2. Implement the fix.
3. Verify the test now passes.

This matches the standard TDD slice flow used for features. The agent's "investigate" phase is implicit in writing the failing test — the act of reproducing the bug typically surfaces the root cause.

When a bug genuinely requires investigation before any fix can be designed, file a separate `kind:spec` issue (`"Investigate root cause of #N"`); ship-issue runs on the spec, produces a written analysis, and the original `kind:bug` then gets picked up with a known fix path. This is the exception, not the rule.

### Eligibility rules (ship-issue)

An issue is eligible for ship-issue iff:

1. Has the `status:ready` label
2. Has the `claude-ok` label
3. `authorAssociation` ∈ {`OWNER`, `MEMBER`, `COLLABORATOR`}
4. Has exactly one `kind:*` label
5. Has exactly one `model:*` label
6. Has exactly one `model-effort:*` label
7. If `model-effort:xhigh`, then `model:opus`
8. Body contains a `Spec:` line OR `kind:` is `bug`, `chore`, or `spec`

Rules 2 and 3 are independent safety layers. GitHub already gates label application by repo write access, but the `authorAssociation` check protects against an external user's issue being mistakenly labeled.

### External user issues — the tracking-issue pattern

External user issues are **intake only**. ship-issue never runs on them (filtered out by Rule 3). When you decide a user report deserves work:

1. Read `pdomain-ocr-cli#100` (external user's report).
2. Create a new internal issue `pdomain-ocr-cli#101` authored by you, structured per the template, with `Tracking: #100` in the body and full labels including `claude-ok` + `triage:tracking`.
3. Add `status:ready` to `#101` (replacing `status:backlog`).
4. ship-issue runs on `#101`.
5. On PR merge, `#101` auto-closes via `Closes #101`. You manually post on `#100` ("Fixed in #101 — released vX.Y.Z") and close it.

This isolates user-supplied content from the agent's reading context (prompt-injection firewall), and lets one user report fan out into multiple internal issues if the actual fix is multi-step.

### Runtime — ship-issue

The `/ship-issue` skill is a thin orchestrator that delegates procedural steps to `scripts/`. The agent only does what requires judgment: reading the spec and writing code.

The skill's prompt, in essence:

```
1. bash scripts/ship-issue-throttle-check.sh
   if exit nonzero: report reason, stop.

2. python3 scripts/ship-issue-pick.py
   parse stdout: ISSUE_NUMBER REPO MODEL MODEL_EFFORT KIND SPEC_PATH ACCEPTANCE_JSON PRE_CLAIM_SHA
   if output is "NONE": report "no eligible issues", stop.

3. (claim happened inside ship-issue-pick.py — Status moved, claim comment posted)

4. If SPEC_PATH is non-empty: Read it.

5. Run the TDD slice for ISSUE_NUMBER:
   - Write failing tests for each acceptance bullet
   - Implement until all pass
   - Between commits, run `make fast-check` (per-commit gate)
   - Commits use subject "issue #$ISSUE_NUMBER: <slice>"; final commit body "Closes #$ISSUE_NUMBER"

6. If the slice completes successfully:
   bash scripts/ship-issue-success.sh "$ISSUE_NUMBER" "$REPO" "$PRE_CLAIM_SHA"
     (script runs `make ci`; on fail, internally invokes ship-issue-failure.sh
      and exits nonzero. On success, pushes, opens or updates draft PR.)
   Report "Shipped issue #$ISSUE_NUMBER".

7. If the slice cannot complete:
   bash scripts/ship-issue-failure.sh "$ISSUE_NUMBER" "$REPO" "$PRE_CLAIM_SHA" "<reason>"
   Report "Bounced issue #$ISSUE_NUMBER: <reason>".
```

That's the full agent-side orchestration. ~20 lines of prompt.

What each script does internally:

**`scripts/ship-issue-throttle-check.sh`** — `git log wip/ship-issue --not main --reverse --format=%cI | head -1`; compute age in days; exit nonzero with reason if > `.shipissuerc:max_unmerged_age_days` (default 7).

**`scripts/ship-issue-pick.py`** — `gh issue list -l status:ready -l claude-ok --state open --json …` (one query, both filters), validate eligibility for each candidate in order (skip silently if no `claude-ok`; comment + skip if other rule fails), pick first eligible. For the picked issue: rebase `wip/ship-issue` onto `origin/main` (abort cleanly on conflict and exit); swap `status:ready` → `status:in-progress` (single mutation: `gh issue edit --remove-label status:ready --add-label status:in-progress`); post claim comment with template; capture pre-claim SHA; print one stdout line with the picked issue's parameters for the agent to consume.

**`scripts/ship-issue-success.sh`** — first runs `make ci`; on failure, calls `ship-issue-failure.sh` with the tail of CI output as the reason and exits nonzero. On CI success: `git push origin wip/ship-issue --force-with-lease` (via `pd-push`); check for an existing draft PR for `wip/ship-issue`; create with `--draft` or edit body; if PR exists but is no longer draft, log "PR is locked, skipping update" and continue (the issue still closed via Closes #N).

**`scripts/ship-issue-failure.sh`** — `git reset --hard <pre-claim-sha>`; swap `status:in-progress` → `status:backlog`; strip `claude-ok`; post comment with reason and the SHA so the work is recoverable from reflog.

All scripts use bare `gh` and `git`, with `GH_TOKEN_PD` in env (read from `/run/secrets/gh-token-pd`). They call `pd-push` for branch pushes (the only wrapper that survives in option C).

### Tiered checking — fast per-commit, full pre-push

Three checking tiers with explicit time budgets and clear contracts.

| Tier | When | Target | Time budget | Failure action |
|---|---|---|---|---|
| Per-commit | Agent runs after each TDD commit | `make fast-check` | < 30s | Agent reverts the commit, debugs, retries |
| Per-push | `ship-issue-success.sh` runs before push | `make ci` | < 10 min | Script invokes `ship-issue-failure.sh` with CI tail |
| Per-PR | GitHub Actions on PR push (existing per-repo CI) | repo-defined | varies | GitHub PR check failure visible on the rolling draft PR |

Each repo declares two Make targets (or equivalent justfile/nox/hatch tasks) as a contract ship-issue depends on:

```makefile
fast-check:  ## < 30 sec. Lint + types + impacted unit tests.
	uv run ruff check
	uv run mypy --partial
	uv run pytest -x --picked          # impacted-tests selector

ci:          ## Full suite. Run before push. < 10 min target.
	uv run ruff check
	uv run mypy
	uv run pytest
```

Repos with frontends (`pdomain-prep-for-pgdp`, `pdomain-ocr-labeler-spa`) extend `ci` with `pnpm test` + Playwright. `pd-png-optimizer` extends with `cargo test` + `maturin develop` + Python tests. The repo defines what `ci` means; the script side just runs `make ci`.

**No per-commit pushes.** Commits land on `wip/ship-issue` locally during the TDD loop. `ship-issue-success.sh` is the only entry point that pushes — once per issue completion, after `make ci` passes. This avoids redundant force-pushes triggering GitHub-side CI per commit.

If a repo lacks an impacted-tests selector for `fast-check`, the repo runs the full unit suite under `fast-check` (still meaningfully faster than `ci` if `ci` includes integration / e2e / Playwright stages). Acceptance for "the contract is real" is just: `make fast-check && make ci` both succeed on a clean main.

### Branch model — single rolling work branch + rolling draft PR

`wip/ship-issue` per repo, lives long-term. All ship-issue runs append to it. On each run start, the branch rebases onto `origin/main` to absorb any pushes. On run failure, commits added during that run are reset away.

A **single rolling draft PR** for `wip/ship-issue → main` is opened by ship-issue when the branch has commits and no draft PR exists. Subsequent runs append to the PR body (one section per run, listing issues completed and their commit ranges) and force-push the branch (rebased onto latest main).

```
On every successful ship-issue run end:
  git push origin wip/ship-issue --force-with-lease   (via pd-push)
  if no open draft PR for wip/ship-issue:
      gh pr create --draft --title "ship-issue: rolling work" --body <summary>
  else:
      gh pr edit <pr#> --body <updated summary>
```

The user reviews on the GitHub diff UI any time, marks the PR ready-for-review when satisfied, merges. On merge, GitHub auto-closes referenced issues via `Closes #N` lines in the commits. `wip/ship-issue` branch is deleted; next ship-issue run creates a fresh one and a fresh draft PR.

If the PR has been manually marked ready-for-review (no longer draft), ship-issue treats it as **locked** and does not modify it. Self-throttling (below) handles the case where the user leaves it locked but unmerged.

### Self-throttling — age-based, not count-based

Before claiming any new issue, ship-issue computes the age of the oldest unmerged commit on `wip/ship-issue`:

```
oldest_unmerged_iso=$(git log wip/ship-issue --not main --reverse --format=%cI | head -1)
age_days=$(( (now - oldest_unmerged_iso) / 86400 ))

if age_days > 7:
    refuse to claim new work
    print: "wip/ship-issue has unreviewed commits older than 7 days
            (oldest: <date>, PR: <url>). Merge or close before continuing."
    exit cleanly  (ctask sees no error, just stops)
```

7-day default is configurable per repo via `.shipissuerc:max_unmerged_age_days`. No commit-count threshold — commits-per-issue varies too much to be a reliable signal. Time directly measures "is the human paying attention?" If the answer is "not in a week," ship-issue waits.

This avoids the alternative of one branch per issue, which would yield one PR per issue under overnight automation and bury you in review work.

### Telemetry

Per-run reports are accurate by construction (token counts and theoretical API cost). Plan-% lives only in the dashboard, where it can be sourced fresh.

**Per-run** (in `run-reports.jsonl`, one record per ship-issue session):

- `tokens_in`, `tokens_out` per model — parsed from the session `.jsonl` transcript
- `api_cost_usd` — computed from `claude-pricing.json` rate table
- `wall_seconds`, `commits[]`, `pre_claim_sha`, `issue_ref`, `repo`
- `outcome`: `success` | `failure` | `throttled`

**Per-render in the dashboard** (`cost-dashboard.html`, regenerated on every SessionEnd):

- `plan_5h_pct` and `plan_7d_pct` are read from `/tmp/claude-rate-limits.json` AT RENDER TIME, not stored per run.
- The sidecar is maintained by `scripts/statusline-with-ratelimits.sh`, which captures `rate_limits.five_hour.used_percentage` and `rate_limits.seven_day.used_percentage` on every render of an *interactive* Claude Code session (mode 0644 so both `vscode` writes and `claude-bot` reads work).
- `resets_at` and the sidecar mtime are surfaced in the dashboard so freshness is visible.

**Per-session plan-% contribution (approximate, dashboard-rendered)**:

The dashboard displays a per-session plan-% column computed by rate approximation:

```
rate_5h  ≈ Σ(tokens of sessions in last 5h)  / sidecar.five_hour.used_percentage
session_5h_pct  ≈ session.tokens_total × (1 / rate_5h)
```

Same formula for the 7-day window. Both values are flagged "approximate (rate from sidecar at <timestamp>)" in the dashboard. Accuracy is bounded by how stable the tokens-per-% rate is across the window — typically very stable, so the approximation is within a few percentage points. For exact attribution (sampling sidecar at session boundaries), see the future-state "Sidecar history" item.

This separation — accurate per-session API cost in `run-reports.jsonl`, approximate per-session plan-% derived in the dashboard — keeps the per-run record honest (no fictitious plan-% values stored) while still giving you a "which sessions ate the cap?" view.

**Confirmed** (per Claude Code docs lookup 2026-05-09): no hook event receives `rate_limits` in its stdin payload — only the statusline command does. This rules out a SessionStart-hook-based refresh and is why the per-run plan-% is dropped.

The `SessionEnd` hook `.claude/hooks/ship-issue-report.py`:

1. Parses the session's `.jsonl` transcript for token counts by model.
2. Computes theoretical API cost from `claude-pricing.json`.
3. Reads `git log <pre-claim-sha>..HEAD` for commits.
4. Appends a record to `.claude/agent-memory/ship-issue/run-reports.jsonl`.
5. Scans the same transcript for `permissionDecision: deny` events and appends to `permission-denials.jsonl` (see Permission-denial logging).
6. Posts a brief shipped-marker comment to the issue: `✓ shipped — N commits, Mm wall time, model: <m>/<e>`.
7. Invokes `scripts/build-cost-dashboard.py` to regenerate `cost-dashboard.html`.

The full report (cost, token counts) lives **only** locally. GitHub does not support per-comment visibility on public repos; keeping cost data local avoids exposing it.

`claude-pricing.json` shape:

```json
{
  "api_rates": {
    "claude-opus-4-7":    {"input_per_m": 15.00, "output_per_m": 75.00},
    "claude-sonnet-4-6":  {"input_per_m":  3.00, "output_per_m": 15.00},
    "claude-haiku-4-5":   {"input_per_m":  0.80, "output_per_m":  4.00}
  },
  "_note": "Plan-% comes from the statusline sidecar at dashboard render time, not from this file. This file only carries API-billing rates."
}
```

### Work-status views — dashboard kanban panel + bookmarked URLs

Status lives on labels, so the "where is my work?" question has two complementary answers:

**1. Bookmarkable label-filtered URLs (live, per-repo).** Day-to-day "what's ready to ship?" / "what's blocked?" views. Bookmark these in the browser:

```
https://github.com/ConcaveTrillion/<repo>/issues?q=is:open+label:status:ready
https://github.com/ConcaveTrillion/<repo>/issues?q=is:open+label:status:in-progress
https://github.com/ConcaveTrillion/<repo>/issues?q=is:open+label:status:blocked
```

GitHub's issue list view is fine for these — sortable, has search, links straight to bodies. No tooling needed.

**2. Cross-repo kanban panel inside `cost-dashboard.html` (regenerated on cadence).** When you want a single-page overview across all 8 repos, `scripts/build-cost-dashboard.py` renders an additional panel: 5 columns (`status:backlog`, `status:ready`, `status:in-progress`, `status:done`, `status:blocked`) × 8 rows (one per repo) of issue cards, each card showing `{repo}#N · title · effort · model`.

The panel pulls data via:

```bash
for repo in pdomain-book-tools pdomain-ocr-cli pd-ocr-labeler pdomain-ocr-labeler-spa \
            pdomain-ocr-synth pd-ocr-trainer pd-png-optimizer pdomain-prep-for-pgdp; do
  gh issue list -R ConcaveTrillion/$repo --state open \
    --json number,title,labels --limit 200
done
```

Each issue card links to its GitHub URL. The panel is **read-only** — no drag-drop, no in-page mutations. Status changes happen via the CLI (or a future thin `pd-status` helper) and surface here on the next dashboard regeneration.

The dashboard regenerates on every `SessionEnd` hook firing (already in scope) plus a once-per-hour `ctask` entry so the kanban stays reasonably fresh even on quiet days. A "Generated at <timestamp>" footer makes staleness visible.

**Optional helper (deferred):** a tiny `pd-status` wrapper that runs `gh issue edit … --remove-label status:X --add-label status:Y` enforcing the single-select discipline. Not required at v1; can be added if manual `gh issue edit` invocations get tedious.

### Spec template — `docs/specs/_TEMPLATE.md`

Nine required `##`-level headings, identical across all per-repo specs, all repos:

1. `## TL;DR` — 2–4 sentences
2. `## Context` — why this spec exists
3. `## Constraints` — non-negotiables
4. `## Decision` — the actual design (most-read section)
5. `## Contract / Acceptance` — verifiable checkboxes
6. `## Trade-offs considered` — alternatives + why-not
7. `## Consequences` — what this enables/forecloses
8. `## Open questions`
9. `## References`

Plus a `> **Status**: …` blockquote, `> **Last updated**: YYYY-MM-DD`, and optionally `> **Related**: …` in the file header.

The nine headings are **stable anchors** by contract: agents may rely on `Spec: docs/specs/foo.md#decision` resolving consistently across all conforming specs.

### Spec lint and the `fixing-specs` skill

The lint script lives **once** at the workspace level (`/workspaces/ocr-container/scripts/lint-spec.sh`) and is symlinked into each repo's hook path during per-repo bootstrap. The repo's `.pre-commit-config.yaml` references the symlink at a stable in-repo path (`./.githooks/lint-spec`), so pre-commit's repo-relative resolution works without each repo carrying a duplicate copy of the script. Updates to lint behavior are made once at the workspace level and apply to every repo on next run.

The hook fires on staged `docs/specs/*.md` files only. Six rules:

1. All 9 required `##` headings present (gated by `.specrc:legacy` allowlist)
2. `Status` blockquote present and valid
3. `Last updated` date present
4. File length within `.specrc` cap (default 800 lines)
5. TL;DR ≤ 6 lines (warn-only by default)
6. **Anchor stability**: existing `##` headings cannot be renamed or removed (always enforced, no allowlist)

`.specrc:legacy` lists pre-existing non-conforming specs that are exempt from Rule 1 only. Rule 6 still applies to them. Initial seeding via `scripts/lint-spec.sh --seed-legacy` populates the list once at hook adoption time, so introducing the hook never blocks an in-flight commit on legacy content.

The `fixing-specs` skill (`/workspaces/ocr-container/.claude/skills/fixing-specs/SKILL.md`) walks an agent through five fix procedures:

- Add missing required heading
- Restore renamed/removed heading
- Trim TL;DR
- Split a spec (with reference repair: forwarding stub at original path, optional update of issue bodies via `gh issue edit`, code-comment updates)
- Remove a spec from the legacy allowlist after migration

Splitting is the high-risk procedure; the skill's central rule is: **the original file becomes a forwarding stub with all 9 required headings present (as `_(see split)_`-style stubs)** so existing `Spec:` pointers continue to resolve.

### Legacy spec migration — on-demand chore fan-out

The legacy allowlist (`.specrc:legacy`) intentionally has no time pressure: legacy specs sit there indefinitely until you choose to migrate them. When you want to migrate (one repo at a time, or all at once), a workspace script files migration chores per legacy spec.

**`scripts/file-legacy-migration-issues.sh REPO [--auto-only | --all]`**

For each path listed under `legacy:` in `<REPO>/docs/specs/.specrc`:

1. Run `scripts/lint-spec.sh --no-legacy <path>` to capture the rules currently failing.
2. Classify the migration difficulty:
   - **Auto-runnable**: only Rule 1 (missing headings) fails, file length is within cap, no anchor changes needed. Migration is mechanical: add the missing headings as `_(none)_` placeholders, update the Status header, set Last updated. ship-issue can do this safely.
   - **Human-required**: file length exceeds cap (Procedure 4 split needed), or other judgment calls. ship-issue should not attempt this; you run `fixing-specs` interactively.
3. File a `kind:chore` issue per legacy spec with the `chore-migrate-legacy-spec` template:
   - Title: `Migrate legacy spec: docs/specs/<file>.md`
   - Body: spec path, current line count, captured lint failures, classification, pointer to `fixing-specs` skill (Procedure 1 or 4)
   - Labels: `kind:chore`, `area:docs`, `effort:S` (auto) / `effort:M` (human), `model:haiku` (auto) / `model:sonnet` (human), `model-effort:low` / `medium`
   - **`claude-ok` applied only if auto-runnable**
   - Status: `status:backlog` (you swap to `status:ready` when you're ready for them to be picked)

`--auto-only` files only the auto-runnable subset. `--all` files everything (including the ones that need your hands).

**`chore-migrate-legacy-spec.md` template body**:

```markdown
## Routine

Migrate this legacy spec to the standard 9-section template.

Spec: docs/specs/<file>.md
Current size: <N> lines  (cap: <cap>)
Classification: <auto-runnable | human-required>
Lint failures (from `scripts/lint-spec.sh --no-legacy`):
- [pasted]

## Procedure

Invoke the `fixing-specs` skill. Apply Procedure <1 | 4> as classified above.

## Acceptance

- [ ] All 9 required headings present
- [ ] Status header set (`Active` or `Locked`)
- [ ] Last updated set to today
- [ ] If split: forwarding stub at original path; new files referenced from
  References section; cross-references in code/issues updated
- [ ] `scripts/lint-spec.sh --no-legacy <path>` passes
- [ ] Spec path removed from docs/specs/.specrc:legacy

## When done

Close this issue. The spec is no longer legacy.
```

The Acceptance section maps directly onto `fixing-specs` Procedure 5 (Removing a spec from the legacy allowlist).

This stays out of recurring-chores territory: there's no cadence, no `recurring:*` label. You invoke the script when you want to attack a backlog of legacy specs, the chores fan out, and they close when the migrations are done. The `.specrc:legacy` list shrinks accordingly. Once it's empty, the script is silent on next run.

### Recurring chores — automated vs human

Two flavors of recurring chore, distinguished by whether `claude-ok` is applied at creation time:

| Chore type | `claude-ok` at creation | `status:ready` at creation | Who runs it | Example |
|---|---|---|---|---|
| **Automated** | yes | yes | ship-issue, unattended | `chore-deps-update` |
| **Human** | no | yes (for visibility) | you | `chore-triage-issues` |

Both are `kind:chore` issues created by `ctask` from `.github/ISSUE_TEMPLATE/chore-recurring*.md` templates. The ctask schedule entry decides which labels to apply. Automated chores flow `status:backlog → status:ready → ship-issue → status:done` without intervention. Human chores land in `status:ready` so they show up in label-filtered queries, but lack `claude-ok` so ship-issue skips them — they're for you.

External users cannot bypass either gate: GitHub gates label changes on repo write access, so an external issue can never arrive pre-labeled `claude-ok` + `status:ready`. ctask invokes its commands as `claude-bot` (which has `GH_TOKEN_PD` for label changes), so the only path to those labels is through ctask schedule entries you wrote and committed.

Skip-if-open guard prevents pile-up: before creating, ctask checks `gh issue list -l recurring:<cadence> --state open` for an existing open issue with the same `recurring:` cadence and the same template name; if one exists, ctask skips creation. The pile-up itself becomes a signal you've fallen behind rather than a runaway loop.

### `chore-triage-issues` (human chore — required at v1)

A weekly human chore that surfaces external-author issues across all 8 repos for triage. Because triage requires judgment (drop / answer / track / spec-required) it is not auto-runnable.

The triage chore lives **once at the workspace level**, filed in `pdomain-book-tools` (the foundation library, used as the central repo for cross-repo chores). The body's `## Routine` section runs a bash loop across all 8 repos:

```bash
for r in pdomain-book-tools pdomain-ocr-cli pd-ocr-labeler pdomain-ocr-labeler-spa \
         pdomain-ocr-synth pd-ocr-trainer pd-png-optimizer pdomain-prep-for-pgdp; do
  echo "=== $r ==="
  gh issue list -R ConcaveTrillion/$r \
    --state open --search "-author:@me" \
    --json number,title,author,createdAt
done
```

For each external issue, you decide: drop (comment + close), answer (comment, leave open if more info needed), or track (create internal `kind:bug` or `kind:spec` per the tracking-issue pattern). The chore closes when you've cleared the queue. Next week's chore is created by ctask.

The human-chore distinction matters because `status:ready` on a `chore-triage-issues` issue does **not** mean ship-issue can run it. Eligibility Rule 2 (`claude-ok` required) keeps ship-issue out. The `status:ready` label is purely human-facing (it shows up in label-filtered issue queries so you don't lose track).

### Two-user dev container — `vscode` (interactive) + `claude-bot` (unattended)

The dev container runs two Linux users sharing the workspace via a `claude-dev` group:

- **`vscode`** — your interactive shell. Has the full-scope `gho_***` token in `~/.config/gh/`, your normal `~/.gitconfig`, your SSH keys. Used for daily development including `gh repo` / `gh workflow` ops the agent can't reach.
- **`claude-bot`** — runs unattended `claude -p` sessions invoked by ctask. Has NO gh login, NO SSH keys, NO access to `vscode`'s home. Only `GH_TOKEN_PD` in env (read from a root-owned secrets file `/run/secrets/gh-token-pd` with mode 0440 group-readable by `claude-dev`). Distinct git identity (`ship-issue-bot`) so agent commits are visually distinct from yours in `git log`.

The workspace tree is `chgrp`'d to `claude-dev` with setgid on directories and `umask 002` set in both users' shells, so files created by either user are group-writable by the other. The agent edits code, specs, and telemetry freely; you review and merge.

**Enforcement files are exempt from the shared-write set.** After the bulk chgrp, the following paths are explicitly chown'd back to `vscode:vscode` with `go-w` stripped, so the bot can read+execute but cannot modify:

```
.claude/hooks/                  (bash-command-guard, ship-issue-report)
.claude/settings.json           (allow/deny patterns)
.claude/skills/                 (skill definitions)
.claude/agents/                 (agent definitions)
pd-push                         (the only push wrapper)
scripts/                        (lint-spec, seed-*, build-*, file-legacy-migration-issues)
.devcontainer/                  (Dockerfile, devcontainer.json)
.pre-commit-config.yaml         (per repo, in each pd-* repo)
```

This is the layer that closes the self-modifying-defenses gap: bot can run the enforcement scripts but cannot rewrite them. Output files those scripts produce (telemetry JSONL, dashboard HTML) stay group-writable since they're append-only artifacts, not policy.

ctask schedules invoke `claude -p` via `sudo -u claude-bot --preserve-env=PATH …`. The vscode→claude-bot sudo path is configured passwordless in `/etc/sudoers.d/claude-bot`.

Bot's first-time Claude Code login is a one-shot manual step (interactive `claude` as `claude-bot` to complete the browser auth flow). Same Anthropic account as your interactive sessions; subscription is shared since sessions don't overlap in time.

This separation is the strongest practical hardening short of network-egress isolation. Even if `bash-command-guard` and the wrappers were bypassed somehow, `claude-bot` has no `gho_***` token to discover, no SSH keys to push with, and no read access to `vscode`'s `~/.gitconfig`. The fine-grained `GH_TOKEN_PD` remains the entire blast radius.

### Security boundaries

The defense layers, in order:

1. **Token segregation in the dev container** (interactive `vscode` user has full token, unattended `claude-bot` user has only `GH_TOKEN_PD`).

2. **PAT scope** — fine-grained `GH_TOKEN_PD` lacks Workflows / Administration / Secrets, so even bare `gh` calls cannot reach those API surfaces.

3. **Branch protection on `main`** — configured per repo, blocks direct pushes and force-pushes; requires a PR for changes to main.

4. **`pd-push` wrapper** — the only way to push from scripts; restricts pushes to `wip/ship-issue`. Plain `git push` is rejected by the hook below.

5. **`.claude/settings.json:permissions`** — allow-list covers dev tools (uv, pytest, pnpm, cargo, …) AND common shell idioms (`for *`, `while *`, `if *`, `case *`, `bash -c *`, `sh -c *`, `* | *`, `* && *`, `* || *`, `* ; *`) so the agent isn't prompted on idiomatic compound commands; deny-list covers obvious bypass paths (bare `git push`, direct `api.github.com` calls, credential-file reads, env-var manipulation of `GH_TOKEN*`). Allow-list patterns are coarse and broad by design; the real enforcement is the hook (layer 6). Settings.json is a fast-path that skips the hook on common safe operations — it is **not** a substitute for the hook.

6. **`.claude/hooks/bash-command-guard.py`** — PreToolUse hook with the unified rule set:
   - Bare `gh repo delete`, `gh workflow run`, `gh secret *`, `gh api *admin*`, `gh pr ready`: deny
   - `gh pr create` without `--draft`: deny
   - `gh issue {close,comment,edit,reopen}` on issues without `claude-ok` label: deny (replaces the previous `pd-gh-issue-guard.py`)
   - `git push` (without `pd-push`): deny
   - `uv add`, `pip install <novel>`, `pnpm add`, `cargo add`: deny (lockfile-respecting installs only)
   - Token exfil patterns (`echo $GH_TOKEN`, redirected credential-file writes, `cat ~/.config/gh/...`): deny
   - Direct `curl`/`wget` to `api.github.com`: deny

7. **Protected enforcement files** — `.claude/hooks/`, `.claude/settings.json`, `.claude/skills/`, `.claude/agents/`, `pd-push`, `scripts/` (workspace-level), `.devcontainer/`, per-repo `.pre-commit-config.yaml` are owned `vscode:vscode` mode 0755/0644. Bot can read+execute but not modify.

8. **`tooling-change-guard` pre-commit hook** — rejects commits modifying any enforcement path unless commit message contains `[tooling-change-approved]`. Belt-and-suspenders if filesystem perms get reset.

9. **Permission-denial logging** — every denial is recorded to `.claude/agent-memory/ship-issue/permission-denials.jsonl` with the attempted command, the rule that fired, and the agent's correction trail. Visible in the cost dashboard.

#### Threat model — what this does and does not defend against

| Threat | Defense |
|---|---|
| Benign agent accidentally running `gh repo delete` or `git push origin main` | settings.json deny + bash-command-guard + token segregation block this multiple ways |
| Agent installing a malicious package (`uv add evil-pkg`) that exfiltrates token | bash-command-guard blocks novel package additions; lockfile-respecting `uv sync` is the only install path |
| Agent reading credential files (`cat ~/.config/gh/hosts.yml`) | settings.json deny + bash-command-guard block; with token segregation those files don't exist in the container anyway |
| Agent making direct `api.github.com` calls via Python `requests` to bypass shell-level allowlists | **NOT defended** at the shell layer. Mitigation is the fine-grained PAT scope (limited damage if exfiltrated) and audit logging (denials + telemetry). For higher assurance, run in a network-isolated container with iptables blocking `api.github.com` except via approved auth paths. |
| Agent modifying the wrappers or hook scripts to disable enforcement | Filesystem-level: enforcement files are `vscode:vscode` mode 0755/0644, not in the bot's writable set. Bot can read+execute but cannot modify. Belt-and-suspenders: a `tooling-change-guard` pre-commit hook rejects commits touching `.claude/hooks/`, `.claude/settings.json`, `pd-push`, `scripts/`, or `.devcontainer/` unless the commit message contains `[tooling-change-approved]`. |
| Compromised existing dependency exfiltrating token | Out of scope for this design; standard supply-chain risk that applies regardless of agent involvement. |

The honest framing: the defense layers stop **accidental rule-breaking** very effectively. They raise the bar for **intentional rule-breaking** but do not constitute a security boundary against an adversarial model. For a 1-person workspace using off-the-shelf Claude on a non-sensitive codebase, accident-prevention is the realistic goal.

#### Permission-denial logging

The SessionEnd hook (`ship-issue-report.py`) does a second-pass scan of the session transcript for tool calls with `permissionDecision: deny`. For each denial it captures:

- **timestamp**, **session_id**, **repo**, **issue_ref** (if known)
- **denied_command** — verbatim
- **denied_by** — which source fired (`bash-command-guard.py` or `settings.json`)
- **rule** — the specific rule name (e.g., `rule_git_push`, `rule_uv_add`)
- **reason** — string from the hook
- **corrections** — array of the next 1–3 tool calls from the same agent + each outcome
- **correction_outcome** — `recovered` | `escalated` | `abandoned`

`escalated` (agent hit another denial trying a workaround) is the alarming case. The dashboard surfaces an aggregate count; future-state work would alert when escalations spike.

The denial log is appended to `.claude/agent-memory/ship-issue/permission-denials.jsonl` (gitignored) and rendered in `cost-dashboard.html` under a "Permission denials" panel.

### PAT scoping

`GH_TOKEN_PD` is a fine-grained PAT with:

- Repository access: all `ConcaveTrillion/pd-*`
- Repository permissions: Issues RW, Metadata R, **Contents: Write**, **Pull requests: Write**

No Account/User permissions. No Workflows scope, no Administration, no Secrets. The token is mounted at `/run/secrets/gh-token-pd` (mode 0440, root-owned, group `claude-dev`-readable).

> **Note:** the original draft included `User permissions: Projects RW` for the (now-abandoned) per-repo Project board. That permission does not exist for user-owned PATs (Projects is an Organization-only fine-grained scope), which is what triggered this design's pivot to status labels.

### Layers replacing `pd-gh` (option C)

There is **no `pd-gh` wrapper** in this design. The constraints `pd-gh` would have enforced are distributed across three other layers:

1. **PAT scope** blocks Workflows, Administration — anything the token doesn't have.
2. **Branch protection on `main`** (configured one-time per repo via GitHub UI or `gh api`) blocks direct pushes and force-pushes to main; requires a PR for any change to main.
3. **`bash-command-guard.py`** (the same hook that already blocks bare `git push`, `uv add`, etc.) gains rules to enforce the workflow conventions:
   - `gh pr create` MUST include `--draft` (PR is reviewed before going to ready)
   - `gh pr ready` is denied (only the human marks ready-for-review)
   - `gh issue` mutations on issues without `claude-ok` are denied (replaces what `pd-gh-issue-guard.py` enforced for `pd-gh issue`)
   - Defense in depth still rejects `gh repo delete`, `gh workflow run`, `gh secret set`, etc., even though the PAT already would.

The hook rule list is the single source of truth for `gh` constraints. Adding a new constraint = editing one file. (Previous design with `pd-gh` plus the hook had the same rules in two places.)

### `pd-push` — kept

`pd-push` survives because branch-target restriction on the PUSH side cannot be expressed by PAT scope or branch protection alone (branch protection on `main` doesn't constrain pushes to other branches; Contents:Write is blanket).

```
/workspaces/ocr-container/pd-push:
- Authenticates with GH_TOKEN_PD via git credential helper
- Allows pushing ONLY to wip/ship-issue
- Allows --force-with-lease (needed because runs rebase onto main)
- Refuses pushes to main, master, or any other branch name
- Refuses bare --force (only --force-with-lease)
```

`ship-issue-success.sh` calls `pd-push`. Plain `git push` from the agent or scripts goes through `bash-command-guard`'s deny pattern, which redirects developers to `pd-push`. This keeps the agent unable to push to main even if a future bug tried to.

### Workspace bootstrap (one-time)

```
0. Dev-container two-user setup:
   - Add to .devcontainer/Dockerfile:
       useradd claude-bot, create claude-dev group, vscode + claude-bot both in it
       umask 002 in both .bashrc files
       claude-bot's bashrc: export PATH=/workspaces/...:$PATH; unset GITHUB_TOKEN;
                            export GH_CONFIG_DIR=$HOME/.config/gh-empty
       claude-bot's git config: user.name=ship-issue-bot, user.email=ship-issue-bot@…
       sudoers.d/claude-bot: vscode ALL=(claude-bot) NOPASSWD: ALL
   - One-time after first checkout:
       sudo chgrp -R claude-dev /workspaces/ocr-container
       sudo chmod -R g+rwX /workspaces/ocr-container
       sudo find /workspaces/ocr-container -type d -exec chmod g+s {} \;
       # Then chown enforcement files back so bot cannot modify them:
       PROTECTED=(.claude/hooks .claude/settings.json .claude/skills .claude/agents
                  pd-push scripts .devcontainer)
       for p in "${PROTECTED[@]}"; do
         sudo chown -R vscode:vscode /workspaces/ocr-container/"$p"
         sudo chmod -R go-w /workspaces/ocr-container/"$p"
       done
       for repo in /workspaces/ocr-container/pd-*; do
         [ -f "$repo/.pre-commit-config.yaml" ] && \
           sudo chown vscode:vscode "$repo/.pre-commit-config.yaml" && \
           sudo chmod go-w "$repo/.pre-commit-config.yaml"
       done
   - Provision /run/secrets/gh-token-pd:
       sudo install -m 0440 -o root -g claude-dev <(echo -n "$GH_TOKEN_PD") /run/secrets/gh-token-pd
   - First-time bot login:
       sudo -u claude-bot bash → run `claude` once interactively → complete browser flow
   - Verify:
       sudo -u claude-bot bash -lc 'gh auth status' → "not logged in"
       sudo -u claude-bot bash -lc 'GH_TOKEN=$(cat /run/secrets/gh-token-pd) gh issue list -R pdomain/pdomain-book-tools' → works

1. Create PAT GH_TOKEN_PD with scopes above; install at /run/secrets/gh-token-pd (mode 0440, root:claude-dev).
   Configure branch protection on each pd-* repo's main: no direct push, no force-push, require PR.

2. Create the only push wrapper:
   /workspaces/ocr-container/pd-push           (bash; bot has execute, vscode has edit)

3. Create workspace hooks (all owned vscode:vscode mode 0644/0755):
   .claude/hooks/ship-issue-report.py          (Python; SessionEnd; telemetry + denial scan)
   .claude/hooks/bash-command-guard.py         (Python; PreToolUse Bash policy — gh/git/uv/etc.)
   .claude/hooks/claude-pricing.json           (config)
   .claude/agent-memory/ship-issue/.gitignore  (covers run-reports.jsonl, permission-denials.jsonl, cost-dashboard.html)

4. Create scripts (ship-issue glue + tooling, all owned vscode:vscode):
   scripts/ship-issue-throttle-check.sh        (bash; one git log + arithmetic)
   scripts/ship-issue-pick.py                  (Python; query, validate, claim — see Runtime)
   scripts/ship-issue-success.sh               (bash; make ci, push, draft PR)
   scripts/ship-issue-failure.sh               (bash; reset, status, claude-ok strip, comment)
   scripts/ship-issue-orchestrator.sh          (bash; --runs N loop calling pick/work/success)

   scripts/seed-labels.sh                      (bash; seeds all label families including status:*)
   scripts/lint-spec.py                        (Python; markdown + multi-rule + --seed-legacy)
   scripts/build-spec-index.py                 (Python)
   scripts/file-legacy-migration-issues.py     (Python)
   scripts/migrate-legacy-spec-auto.py         (Python; mechanical Procedure 1 migration)
   scripts/build-cost-dashboard.py             (Python)
   scripts/statusline-with-ratelimits.sh       (bash; writes /tmp/claude-rate-limits.json mode 0644)
   scripts/tooling-change-guard.sh             (bash; pre-commit; rejects unmarked tooling edits)
   scripts/verify-protections.sh               (bash; one-time perms test as claude-bot)

5. Create skills:
   .claude/skills/ship-issue/SKILL.md          (thin orchestrator — see Runtime)
   .claude/skills/fixing-specs/SKILL.md        (5 procedures)

6. Rename ship-slice → ship-issue commands; update ctask schedules to invoke `claude -p "/ship-issue"` via `sudo -u claude-bot --preserve-env=PATH`.
```

### Per-repo bootstrap

Run for each repo in roll-out order:

```
A. Configure GitHub branch protection on main (no direct push, no force-push, require PR).
B. seed-labels.sh ConcaveTrillion/<repo>   (seeds kind:*, effort:*, model:*, model-effort:*, area:*, recurring:*, status:*, claude-ok, triage:tracking)
C. Add issue templates: .github/ISSUE_TEMPLATE/{feature,bug,spec,chore-recurring,chore-migrate-legacy-spec}.md
D. Add docs/specs/_TEMPLATE.md and docs/specs/.specrc
E. Add Makefile (or justfile/nox tasks) with `fast-check` and `ci` targets defined; verify both succeed on a clean main.
F. Create .githooks/lint-spec → ../scripts/lint-spec.py; add .pre-commit-config.yaml entries:
     - lint-spec hook (on docs/specs/*.md)
     - tooling-change-guard hook (on enforcement paths)
G. Run scripts/lint-spec.py --seed-legacy → populates docs/specs/.specrc
H. Migrate ROADMAP.md → issues (agent-drafted via a one-shot script, all `status:backlog`, no `claude-ok`, no `status:ready`)
I. Human triage: fix labels, drop duplicates, swap `status:backlog` → `status:ready` and add `claude-ok` on the next 3-5
J. Delete ROADMAP.md; update CLAUDE.md with milestone-status + work-tracking sections
K. First end-to-end ship-issue run; verify telemetry lands in JSONL + HTML
L. Repo migration done.
```

Roll-out order (priority by value × readiness):

1. `pdomain-prep-for-pgdp` (pilot — actively shipping M2)
2. `pdomain-ocr-labeler-spa` (active development; clean spec/milestone structure; needs `gh repo create` first)
3. `pdomain-book-tools` (foundation library)
4. `pd-ocr-trainer`
5. `pd-ocr-labeler` (legacy NiceGUI)
6. `pdomain-ocr-cli`
7. `pdomain-ocr-synth`
8. `pd-png-optimizer` (lowest velocity; needs `gh repo create` first)

## Contract / Acceptance

Workspace-level:

- [ ] `GH_TOKEN_PD` exists with Issues RW + Metadata R + Contents:Write + Pull-requests:Write; no Workflows, Administration, or Account/User permissions; mounted at `/run/secrets/gh-token-pd` mode 0440 root:claude-dev
- [ ] Each `ConcaveTrillion/pd-*` repo has branch protection on `main`: direct push and force-push blocked, PR required
- [ ] `pd-push` exists at workspace root; allows pushing only to `wip/ship-issue`; allows `--force-with-lease` but rejects plain `--force`; rejects pushes to any other branch
- [ ] `.claude/hooks/ship-issue-report.py` is registered as a SessionEnd hook (telemetry + denial scan)
- [ ] `.claude/hooks/bash-command-guard.py` is registered as a PreToolUse hook on Bash tool calls and enforces the unified rule set: bare `git push`, `gh pr create` without `--draft`, `gh pr ready`, `gh issue {close,comment,edit,reopen}` on issues without `claude-ok`, `gh repo delete`/`workflow run`/`secret *`, novel package adds (`uv add`, `pip install <novel>`, `pnpm add`, `cargo add`), credential-file access, token-exfil patterns, direct `api.github.com` calls
- [ ] `.claude/settings.json:permissions.allow` covers the dev-tool surface (uv, pytest, pnpm, cargo, …) AND common shell idioms (for/while/if/case/bash -c, pipes/chains/sequences) so idiomatic compound commands don't prompt; `permissions.deny` covers documented bypass patterns
- [ ] Verified empirically: an interactive Claude Code session can run `for f in *.py; do python -m py_compile "$f"; done` and similar compound commands without permission prompts
- [ ] `.claude/agent-memory/ship-issue/permission-denials.jsonl` is created on first denial and contains records with denied_command, rule, reason, corrections, correction_outcome
- [ ] Cost dashboard shows a "Permission denials" panel with the most recent 50 events and aggregate counts of recovered / escalated / abandoned
- [ ] `.devcontainer/Dockerfile` provisions `claude-bot` user and `claude-dev` group; both `vscode` and `claude-bot` in the group; passwordless sudo from `vscode` to `claude-bot`
- [ ] Workspace tree is chgrp'd to `claude-dev` with setgid on directories
- [ ] Enforcement paths (`.claude/hooks`, `.claude/settings.json`, `.claude/skills`, `.claude/agents`, `pd-push`, `scripts/`, `.devcontainer/`, per-repo `.pre-commit-config.yaml`) are chown'd to `vscode:vscode` with `go-w` stripped; verified bot cannot modify any of them via `scripts/verify-protections.sh`
- [ ] Per-repo `.pre-commit-config.yaml` includes a `tooling-change-guard` hook that rejects commits modifying enforcement paths unless the commit message contains `[tooling-change-approved]`
- [ ] `scripts/tooling-change-guard.sh` exists and enforces the marker rule
- [ ] `/run/secrets/gh-token-pd` exists, mode 0440, owned root:claude-dev
- [ ] `claude-bot` has no gh auth (`gh auth status` returns "not logged in")
- [ ] `claude-bot` has its own `~/.gitconfig` with `user.name=ship-issue-bot`
- [ ] ctask schedules invoke `claude -p` via `sudo -u claude-bot --preserve-env=PATH`
- [ ] Bot's first-time Claude Code login completed and persisted
- [ ] `.claude/hooks/claude-pricing.json` is populated with current API rates (no plan-cap fallback needed; plan-% comes from sidecar at dashboard render time)
- [ ] `scripts/statusline-with-ratelimits.sh` is wired into `settings.json:statusLine.command` and writes `/tmp/claude-rate-limits.json` (mode 0644) with both `five_hour.used_percentage` and `seven_day.used_percentage`
- [ ] `scripts/build-cost-dashboard.py` reads the sidecar at render time and shows current plan-% with a freshness indicator (sidecar mtime / `resets_at`)
- [ ] Dashboard displays approximate per-session plan-% contribution (5h and 7d) computed via rate approximation (`session.tokens × (sidecar.pct / Σ window-tokens)`); flagged as approximate
- [ ] Dashboard includes a cross-repo kanban panel rendering `status:*`-labeled open issues across all 8 repos (5 columns × 8 rows), with each card linking to its GitHub URL and a "Generated at <timestamp>" footer
- [ ] `ctask` has an hourly entry that re-runs `scripts/build-cost-dashboard.py` so the kanban panel refreshes outside of ship-issue session boundaries
- [ ] `scripts/lint-spec.py` enforces all 6 rules and supports `--seed-legacy`
- [ ] `scripts/file-legacy-migration-issues.py` classifies legacy specs as auto-runnable vs human-required and files chores accordingly
- [ ] All ship-issue procedural scripts exist and are executable: `ship-issue-throttle-check.sh`, `ship-issue-pick.py`, `ship-issue-success.sh`, `ship-issue-failure.sh`, `ship-issue-orchestrator.sh`
- [ ] `.claude/skills/fixing-specs/SKILL.md` exists and covers all 5 procedures
- [ ] All 8 per-repo `ship-issue-<repo>` skill files exist (renamed from `ship-slice-<repo>`)
- [ ] ship-issue's runtime self-throttle refuses to claim new work when oldest unmerged commit on `wip/ship-issue` is > 7 days old (configurable via `.shipissuerc:max_unmerged_age_days`)
- [ ] ship-issue opens a draft PR after the first successful run on a fresh `wip/ship-issue` branch and updates its body on subsequent runs
- [ ] ship-issue treats a non-draft PR as locked (no further updates from the agent)
- [ ] `ctask` schedules updated to invoke `/ship-issue` not `/ship-slice`

Per-repo:

- [ ] Branch protection on `main` configured (no direct/force push, PR required)
- [ ] Label families seeded (including `status:backlog`, `status:ready`, `status:in-progress`, `status:done`, `status:blocked`)
- [ ] Issue templates committed (5: feature, bug, spec, chore-recurring, chore-migrate-legacy-spec)
- [ ] `Makefile` (or equivalent) defines `fast-check` and `ci` targets; both succeed on a clean main
- [ ] `docs/specs/_TEMPLATE.md` and `docs/specs/.specrc` committed
- [ ] `.pre-commit-config.yaml` lint-spec hook entry added
- [ ] All open ROADMAP.md items migrated to issues
- [ ] ROADMAP.md deleted
- [ ] CLAUDE.md updated with Work tracking + Current milestone sections
- [ ] At least one end-to-end ship-issue run succeeded
- [ ] `run-reports.jsonl` has the run's record; HTML dashboard regenerated

## Trade-offs considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Org-level Project across all 8 repos | Single dashboard | The 8 repos are not all directly related; mixes unrelated work; would also need org migration to access via fine-grained PAT | Per-repo gives focus and avoids merging unrelated backlogs |
| Issues mirror ROADMAP.md (markdown stays source of truth) | No agent re-tooling; lowest disruption | Dual-tracking drift; doesn't actually save tokens | Issues replace markdown to actually solve the token problem |
| **Status on a per-repo Project board (Status field)** | Drag-drop UX, single-select enforced server-side | **Requires `Projects: Read and write` permission, which does not exist for user-owned fine-grained PATs (Organization-only scope). Workaround would be a second classic PAT with `project` scope — broader blast radius across all the user's projects.** | **Not viable under the current account model. Rejected 2026-05-09.** |
| Status on a per-repo Project board via second classic PAT | Keeps drag-drop UX | Two secrets to mount/rotate; classic `project` scope has org-wide blast radius; bot principal pays a security regression for convenience | Convenience cost too high; revisit if `ConcaveTrillion` migrates to an org |
| **Status as a `status:*` label family** (chosen) | One PAT with no Projects scope; cheap one-shot query (`gh issue list -l status:ready -l claude-ok`); cross-repo bookmarkable URLs; renderable in the cost dashboard as a kanban panel | No drag-drop; single-select must be enforced convention-side by every tool that mutates status | Chosen — the convention discipline is concentrated in 3 scripts (`ship-issue-pick.py`, `ship-issue-failure.sh`, ctask chore creation), and most status transitions are automated by the bot anyway. Day-to-day human view is bookmarked label-filtered URLs plus the dashboard kanban panel. |
| Branch per issue | Clean isolation, easy revert | One PR per issue under overnight automation = unreviewable | Single rolling branch keeps morning review tractable |
| Per-issue full report on the GitHub issue comment | Visible from GitHub UI | Plan-% and cost data are public on public repos | Local JSONL + HTML keeps personal data off the public surface |
| Hard CI enforcement of spec template from day one | Prevents drift | Blocks legitimate typo fixes on legacy specs | Pre-commit + legacy allowlist gives ratchet without friction |
| One template per kind (feature-spec / data-spec / ADR) | Each kind tuned to its purpose | More templates to remember, more fragile anchors | One unified template with 9 stable anchors is simpler and more reliable |
| No PR automation in v1 | Keeps the agent's surface narrower; smaller PAT scope | Manual `gh pr create` after every overnight session; no bound on unreviewed-work accumulation | Rolling draft PR + 7-day age throttle gives a bounded queue without proliferation; `pd-push` + branch protection preserve the "agent can't push to main" invariant |
| Self-throttle by commit count | Easy to compute | Commits/issue varies wildly under TDD; bad proxy for "human attention" | Age of oldest unmerged commit measures attention directly; 7-day default |
| Chunked PRs every 12 hours | Bounded PR size | Arbitrary cutoff; can split mid-issue; multiple unmerged PRs from quiet periods | Single rolling draft PR scales naturally; throttle handles the quiet-period case |
| Keep `pd-gh` wrapper alongside the hook | Layered enforcement (PAT + wrapper + hook) | Two places to maintain `gh` rules; drift risk; redundant where PAT already constrains | Drop wrapper; consolidate `gh` rules in `bash-command-guard.py`; PAT scope + branch protection cover what wrapper would have. `pd-push` still exists because branch-target restriction can't be expressed elsewhere. |
| All ship-issue logic in agent prompt | Single artifact to read | Wastes tokens reasoning through deterministic glue every session | Procedural work in scripts (`scripts/ship-issue-*`); skill prompt is ~20-line orchestrator. Agent only reasons about TDD slice work. |
| Run `make ci` per commit | Fastest possible feedback | Per-commit CI is minutes × every commit = unworkable | Tiered checks: `fast-check` per commit (< 30s), `ci` per push (full suite). Push only at issue boundary. |
| Per-run plan-% in run report | Visibility per session | Sidecar is stale during `claude -p` (no statusline render); reported value would be misleading | Drop per-run plan-%; dashboard reads sidecar at render time; freshness indicator surfaces staleness honestly |

## Consequences

**Enables:**

- Token cost at session start drops by ~10k+ lines (ROADMAPs gone, specs claudeignored, lazy-read on demand).
- Cross-repo work-status visibility via the cost-dashboard's kanban panel (renders `status:*`-labeled issues across all 8 repos) plus bookmarkable per-repo label-filtered URLs (`…/issues?q=is:open+label:status:ready`).
- Per-run telemetry: cost trend, plan-window usage, per-model cost breakdown.
- Mechanical agent intake: ship-issue picks the next slice in O(1) without grepping markdown.
- Recurring chores fully automated end-to-end via `ctask` + `gh issue create`.
- Stable spec anchors enforce that `Spec:` references in issues survive spec restructuring.

**Forecloses or makes harder:**

- Atomic editing of "all open work" is now a multi-issue operation, not a single markdown edit. Bulk operations need scripting.
- Issue history is on GitHub (subject to GitHub's retention and availability); markdown was offline-readable.
- A future move from public to private repos would mean re-evaluating telemetry exposure (some safeguards become redundant; some become necessary).

**Migration impact:**

- ~50 ROADMAP slices × 8 repos = a one-time agent-drafted batch of ~400 issues. Sweep takes a focused 1–2 hours per repo for triage.
- Two repos (`pdomain-ocr-labeler-spa`, `pd-png-optimizer`) need `gh repo create` first.
- Existing specs do not require backfill (legacy allowlist).

## Future state (out of v1, captured for roadmap)

These are intentionally deferred. They build on v1 primitives without changing them.

### Auto-triage with human-in-the-loop approval

External bug reports currently get triaged manually. As volume grows, an auto-triage agent could pre-process external-authored issues and produce drafts that the human only needs to approve.

Flow:

```
1. ctask schedules pd-claude-triage (weekly, or on-demand)
2. For each open external-authored issue without a `triage:proposed` label:
   - Agent reads issue body, recent code, related issues for dup-detection
   - Agent classifies: drop / answer-only / track-internal / spec-required
   - For "track-internal" / "spec-required", agent drafts an internal tracking issue:
       - title, body (Repro/Expected/Actual or Question), suggested labels,
         suggested effort/model/model-effort, suggested area
   - Agent creates the internal issue WITHOUT `claude-ok`, with `status:backlog`
     and an extra `triage:proposed-by-agent` label
   - Agent posts a comment on the EXTERNAL issue: "Triage drafted: see #N"
   - Agent labels the external issue `triage:proposed` so it isn't re-triaged
3. Human (you) sweeps the `triage:proposed-by-agent` queue:
   - For each proposal, glance at it (~10s/issue rather than several minutes)
   - Approve: add `claude-ok`, swap `status:backlog` → `status:ready`, remove
     `triage:proposed-by-agent`
   - Reject: edit the body, change labels, or just close. Add `claude-rejected`
     to teach future runs
   - On the original external issue, optionally add `triage:approved` or
     `triage:rejected` so the triage agent's "what's been seen" filter works
4. ship-issue runs on the approved internal issues as normal.
```

The human stays gating `claude-ok` per issue. The agent only drafts and labels for review; it never authorizes itself for runtime.

What changes from v1:

- Four new labels: `triage:proposed-by-agent`, `triage:proposed`, `triage:approved`, `triage:rejected`
- New skill: `pd-claude-triage` (separate from `ship-issue`; same security gates apply)
- New template: `chore-recurring-auto-triage.md` for ctask scheduling
- The "human chore" `chore-triage-issues` from v1 evolves into a "review agent's proposals" chore

The threat model is unchanged: external content never enters ship-issue's reading context (the proposed internal issue's body is whatever the triage agent wrote, which is *its* paraphrase of the user's report — same prompt-injection firewall as the manual tracking-issue pattern). The triage agent itself reads external content, so it's the surface that absorbs the prompt-injection risk; mitigation is that its output is bounded (label proposals + an issue draft) and gated on human approval before ship-issue ever sees it.

### Cloud-native scheduling

Replace `ctask` (local tmux scheduler) with Claude cloud routines (`/schedule`) or GitHub Actions cron. The entry point — `gh issue create --template …` — is unchanged; only the trigger surface moves. Migration is a swap of cron registration, not a rewrite.

### Cross-repo dependency report

When `Depends on: ConcaveTrillion/<other>#N` lines accumulate in issue bodies, a workspace-level script could surface a dependency graph: which issues are blocked on which, where the longest chains are. Useful when more than ~10 cross-repo deps are in flight.

### Spec template — hard CI enforcement

v1 enforces via local pre-commit. v2 promotes the same `lint-spec.sh` to a GitHub Actions workflow that fails PRs touching `docs/specs/*.md` if rules fail. Adopt once you're collaborating with others (or bots) who don't run pre-commit locally.

### Dashboard expansion

The cost-dashboard could grow: per-week burn-rate chart, per-issue cost histogram, model-mix over time, prediction of plan-cap hit date. All read-only views over the same JSONL.

### Sidecar history — exact per-session plan-% attribution

v1's per-session plan-% is rate-approximate. For exact attribution, change the statusline to *append* every render to `/tmp/claude-rate-limits-history.jsonl` instead of overwriting `/tmp/claude-rate-limits.json`. Each entry is `{timestamp, five_hour_pct, seven_day_pct}`. The dashboard then correlates session start/end timestamps with the history to compute exact deltas. Cost: file grows; needs rolling-window pruning (`find -mmin +$((7*24*60))` or similar). Worth doing when the rate-approximation error becomes annoying.

### Permission-escalation alerting

When the daily count of `correction_outcome: escalated` permission denials rises above a threshold (e.g., 3 in a 24h window) the dashboard or a separate alert surface should call attention to the session. Suggests a model trying multiple bypass paths after one is blocked, which is suspicious enough to warrant inspection. Trivial to add once the denial JSONL exists; deferred until a few weeks of data show what a normal escalation rate looks like.

### Network-egress isolation for `claude -p` runs

Run `claude -p` (overnight ctask sessions) in a network-isolated container with iptables denying outbound `api.github.com` except via authorized scripts (which use the scoped PAT). Closes the "agent uses Python `requests` to bypass shell allowlists" gap. Heavier setup than v1 warrants but the strongest available defense against an adversarial model.

### Stale-bug sweep

A monthly chore that lists `kind:bug` issues open > 90 days without a comment in 30 days. Either bump priority, ask reporter for re-confirmation, or close as stale. Not needed at v1's volume.

## Open questions

- **Forwarding-stub UX**: when a spec is split, GitHub renders the stub as a real page. Should the stub also redirect via an explicit `<meta refresh>` tag or HTML rewrite? Probably no — markdown stub is fine.
- **Cross-repo dependency UX**: a spec in `pdomain-prep-for-pgdp` depending on a slice in `pdomain-book-tools` is currently a `Depends on:` text line. If this gets common, consider a workspace-level dependency report script.
- **Recurring-chore "skip if open" granularity**: skip when *any* open issue with the same `recurring:` label exists, or only when an issue from the same template exists? Pick the looser one (any open recurring-of-this-cadence) to start; refine if it turns out too aggressive.

## References

- [docs/doc-cleanup-plan.md](../../doc-cleanup-plan.md) — sibling doc-quality plan; this design is complementary
- [.claude/hooks/pd-gh-issue-guard.py](../../../.claude/hooks/pd-gh-issue-guard.py) — existing mutation gate (REMOVED in v1; rules absorbed into the new `bash-command-guard.py`)
- [pd-gh](../../../pd-gh) — existing scoped wrapper (REMOVED in v1; replaced by `bash-command-guard.py` rules + bare `gh` with scoped PAT)
- [ctask](../../../ctask) — existing local cron, retained
- [Anthropic effort docs](https://platform.claude.com/docs/en/build-with-claude/effort) — source for the model-effort enum
- [Claude Code hooks reference](https://code.claude.com/docs/en/hooks.md) — confirmed no hook event receives `rate_limits` (only the statusline command does)
- [Claude Code statusline reference](https://code.claude.com/docs/en/statusline.md) — source for the sidecar field paths
