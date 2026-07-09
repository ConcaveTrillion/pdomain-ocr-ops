---
status: complete
---

# R1 — Workspace Canonical CONVENTIONS.md + Housekeeping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the missing workspace-level pieces that unblock everything downstream — the workspace canonical `CONVENTIONS.md` (currently missing, blocks the cross-repo sync infrastructure in v2 Plans 3 and 4), a bot-workspaces README documenting the ownership model surfaced by workspace-rc, and a STATUS.md / spec-acceptance-bullet sweep that retires the v2 + lifecycle plans cleanly.

**Architecture:** Three lanes, all in the workspace tree (no per-repo edits): (1) author `/workspaces/ocr-container/CONVENTIONS.md` by harvesting cross-repo rules already present in pdomain-book-tools' CONVENTIONS.md plus the workspace memory feedback files; mark the cross-repo block with `<!-- workspace-conventions:start -->` / `<!-- workspace-conventions:end -->` markers consumed by `scripts/sync-conventions.py`. (2) Write `/srv/bot-workspaces/README.md` documenting topology + uid 1000/1001 ownership model + `safe.directory` + `sudo -u claude-bot` pattern. (3) Update workspace STATUS.md to reflect actual landed state, tick acceptance bullets in both v2 and lifecycle specs, commit the staged agent-memory feedback files.

**Tech Stack:** Markdown, `git` (workspace repo), `sync-conventions.py` (verification only).

**Source plans:**
- `docs/superpowers/plans/2026-05-10-code-review-style-cleanup-plan-2.md` (Task 2 was workspace canonical creation)
- `docs/superpowers/plans/2026-05-10-code-review-style-cleanup-plan-4.md` (Task 1 was adding markers to workspace canonical)
- `docs/superpowers/plans/2026-05-11-INDEX.md`

**Depends on:** None. Parallel-safe with R0.

**Out of scope:**
- Per-repo CONVENTIONS.md updates — those land in R3a via `sync-conventions.py`.
- Running daily/weekly bots — operational arming lands in R3a.
- Decisions about workspace-tooling meta repo (v2 Open Q #2) — independent of this plan.

---

## Background context for the engineer

You are landing the *single most-blocking* missing piece in the entire re-plan: the workspace canonical `CONVENTIONS.md`. Every cross-repo style-sync feature already has code (in `scripts/sync-conventions.py`, `scripts/check-sync-drift.py`, `scripts/check-sibling-drift.py`, `scripts/lint-conventions.py`) but no canonical source to read from.

The canonical lives at `/workspaces/ocr-container/CONVENTIONS.md`. It has two zones separated by markers:

```markdown
# Workspace conventions (canonical)

<!-- workspace-conventions:start -->

## Rule: <Cross-repo rule 1>
...
## Rule: <Cross-repo rule 2>
...

<!-- workspace-conventions:end -->

## Workspace-only notes
...
```

The cross-repo block (between the markers) is what `sync-conventions.py` will copy into the same marker pair inside every per-repo `<repo>/CONVENTIONS.md`. Per-repo files retain their own rules below their own `<!-- workspace-conventions:end -->` marker.

### Source material

pdomain-book-tools already has a CONVENTIONS.md with two cross-repo rules in its marker block:

1. "No comments explaining what code does" (sections + violation buckets)
2. "Unicode escape sequences for ruff-flagged ambiguous characters"

These are the seed rules. Promote them verbatim into the workspace canonical. Additional candidates to consider (from workspace memory feedback files + CLAUDE.md):

- **Always use `uv run`** — memory `feedback_use_uv_not_python3.md`
- **Never use `--no-verify` on commits** — implied by Plan A hook discipline; check if there's a feedback file
- **Never invent author/org/URL metadata** — memory `feedback_no_invented_metadata.md` (scoped to *first commits* on new repos, but still cross-repo)
- **`safe.directory` for bot worktrees** — workspace-rc finding (this is operational, not source-style; consider putting in `/srv/bot-workspaces/README.md` instead)
- **Section dividers are high-confidence violations of "no comments"** — already in pdomain-book-tools' rule body; promote as-is

### Marker contract

`sync-conventions.py` (already exists at `scripts/sync-conventions.py`) expects:

- Canonical: a single contiguous block between `<!-- workspace-conventions:start -->` and `<!-- workspace-conventions:end -->` markers.
- Per-repo: the same marker pair; everything between is replaced; everything before/after the markers is preserved.

`lint-conventions.py` enforces:
- Markers exist exactly once.
- Each rule starts with `## Rule: <Title>` immediately after a blank line.
- Each rule has a `**The rule.**` line and a `**Why.**` line.

### Workspace-rc gotchas to fold in

- **Bot worktree ownership**: claude-bot (uid 1001) writes files with mode 0640; vscode (uid 1000) reads only via `safe.directory`. Any edit-then-commit cycle inside a bot worktree must run as `sudo -u claude-bot bash -c '...'`.
- **Pre-commit in worktrees**: `.git` is a file, not a directory, so `pre-commit install` is skipped automatically. Don't fight it — run `make lint` directly.
- **Parallel subagent dispatch**: keep a running tally in a transient file when 3+ agents are in flight; otherwise visibility is poor.

These go into `/srv/bot-workspaces/README.md`, not the source CONVENTIONS.md.

---

## File structure

**Create:**
- `/workspaces/ocr-container/CONVENTIONS.md` — workspace canonical
- `/srv/bot-workspaces/README.md` — topology + ownership doc

**Modify:**
- `/workspaces/ocr-container/docs/superpowers/plans/STATUS.md` — append R1 status section + retire plan-status lines that are now stale
- `/workspaces/ocr-container/docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md` — tick acceptance bullets that are now complete; mark Status: Active → Done
- `/workspaces/ocr-container/docs/superpowers/specs/2026-05-10-feature-request-spec-decomposition-design.md` — tick acceptance bullets for landed pieces
- `/workspaces/ocr-container/docs/superpowers/bot-workspaces.md` — add a one-paragraph "operational notes (workspace-rc lessons)" pointer to the new README

**Commit (no code change):**
- `.claude/agent-memory/{pdomain-book-tools,pdomain-ocr-cli,pd-ocr-labeler,pdomain-prep-for-pgdp}/feedback_ruf001*.md` + the modified MEMORY.md indexes (these are staged uncommitted at session start)
- `.claude/agent-memory/pd-ocr-labeler/lint_config_noqa_patterns.md`

---

## Tasks

### Task 1: Author workspace canonical CONVENTIONS.md

**Files:**
- Create: `/workspaces/ocr-container/CONVENTIONS.md`
- Reference: `/workspaces/ocr-container/pdomain-book-tools/CONVENTIONS.md`

- [ ] **Step 1: Read the seed rules from pdomain-book-tools**

```bash
sed -n '/^<!-- workspace-conventions:start -->/,/^<!-- workspace-conventions:end -->/p' \
  /workspaces/ocr-container/pdomain-book-tools/CONVENTIONS.md > /tmp/r1-seed-block.md
wc -l /tmp/r1-seed-block.md
```

Expected: ~60 lines containing the two rules ("No comments explaining what code does", "Unicode escape sequences for ruff-flagged ambiguous characters").

- [ ] **Step 2: Write the canonical file**

Write `/workspaces/ocr-container/CONVENTIONS.md` with this structure (copy seed rules verbatim from /tmp/r1-seed-block.md into the marker block, add the third "uv run" rule, add the workspace-only footer):

```markdown
# Workspace conventions (canonical)

> **Role.** This file is the canonical source of cross-repo style rules. Each
> published pd-* repo's `CONVENTIONS.md` mirrors the block between the
> `<!-- workspace-conventions:start/end -->` markers below; the per-repo file
> may add its own repo-specific rules *after* the closing marker.
>
> **Edit discipline.** Inside the marker block, only add/update *cross-repo*
> rules. Repo-specific rules go in the per-repo CONVENTIONS.md, not here. After
> editing this block, run `uv run python scripts/sync-conventions.py` to fan
> out the change. `scripts/lint-conventions.py` enforces marker integrity in
> pre-commit.

<!-- workspace-conventions:start -->

## Rule: No comments explaining what code does

**The rule.** Don't add comments that restate what the code does;
well-named identifiers already do that. Only add a comment when the
WHY is non-obvious: a hidden constraint, a subtle invariant, or a
workaround for a specific bug.

**Why.** Comments rot when code changes and become misleading. The rule
also applies to docstrings — one short line max; no multi-paragraph
docstrings and no multi-line comment blocks.

**Common high-confidence violations** (bot auto-fix candidates)

- One-line summary comment immediately above a function that restates its name.
- `# returns the X` or `# sets the Y` before a return/assignment statement.
- Multi-line docstrings that explain every parameter with no non-obvious WHY.
- Section divider blocks: `# ---…---` / `# ===…===` multi-line banners used as
  navigation headers in test files — class names and blank lines already
  provide structure; remove the banner, keep the blank lines.
- Multi-paragraph module or class docstrings with a "Focus on:" / "Covers:"
  section — collapse to a single-line summary.

**Common judgment-call violations** (bot flags, CT decides)

- Comments that reference the PR, issue, or task that introduced the code — belongs in commit message, not source.
- Multi-line preamble that mixes WHY (worth keeping) with WHAT (worth removing).

## Rule: Unicode escape sequences for ruff-flagged ambiguous characters

**The rule.** Characters ruff flags under RUF001/002/003 (ambiguous Unicode —
curly quotes, en-dashes, em-dashes, multiplication signs, non-breaking spaces,
etc.) must be written as `\uXXXX` escape sequences in string and docstring
literals. In comments, replace with the plain ASCII equivalent. In every case
include a short inline comment naming the character, e.g.
`"“"  # LEFT DOUBLE QUOTATION MARK`.

**Why.** Literal curly quotes and dashes are visually indistinguishable from
ASCII equivalents in most editors and diff views, making string comparisons and
grep silently fragile. Escape sequences make intent explicit and are safe across
all encodings. `# noqa: RUF00x` masks the problem instead of fixing it.

**Common high-confidence violations** (bot auto-fix candidates)

- A string literal containing `"hello – world"` written with the literal
  `–` character instead of the escape sequence.
- `# noqa: RUF001`, `# noqa: RUF002`, or `# noqa: RUF003` suppressions instead
  of escape sequences.
- `RUF002` or `RUF003` added to `[tool.ruff.lint] ignore` in `pyproject.toml`
  to paper over ambiguous characters.

**Common judgment-call violations** (bot flags, CT decides)

- Test strings that intentionally exercise curly-quote round-trip through the
  OCR pipeline and must contain the literal character — keep the literal with an
  explicit `# noqa: RUF001  # intentional: testing curly-quote round-trip`
  comment that names the character and states the reason.

## Rule: Use `uv run` for all Python and tool invocation

**The rule.** Invoke Python, pytest, ruff, mypy/pyright, and any project-local
CLI through `uv run`. Never call bare `python`, `python3`, `pytest`, or
`pre-commit` from a Makefile target, CI step, or hook.

**Why.** Direct invocation skips the project's `.venv` and the lockfile-pinned
toolchain; tests pass locally and fail in CI (or vice versa) because the bare
interpreter sees different installed package versions. `uv run` is uniformly
fast (<200 ms warm) and always selects the project venv.

**Common high-confidence violations** (bot auto-fix candidates)

- `python -m pytest` or `python3 script.py` in any `Makefile`, `*.sh`, `.github/workflows/*.yml`, or `.pre-commit-config.yaml` hook.
- `pre-commit run` (bare) instead of `uv run pre-commit run` in CI or scripts.
- `ruff check` or `pyright` (bare) in scripts that don't activate a venv first.

**Common judgment-call violations** (bot flags, CT decides)

- One-off REPL commands typed in CT's interactive shell — out of scope for this rule.

<!-- workspace-conventions:end -->

## Workspace-only notes

The canonical block above is mirrored into each published pd-* repo by
`scripts/sync-conventions.py`. Per-repo CONVENTIONS.md may add its own
repo-specific rules *after* the closing marker — for example, pdomain-book-tools has
"Never silently drop OCR words" and "Drop-cap Words are training data, not
noise" rules that apply only to the foundation library.

### When to update this file

- A new style/process rule applies to **two or more** pd-* repos → add it here.
- A rule applies to **only one** repo → put it in that repo's CONVENTIONS.md
  below its closing marker.
- A rule is **operational** (file ownership, worktree handling, bot auth) →
  put it in `/srv/bot-workspaces/README.md`, not here. This file is for source
  conventions consumed by `style-review-detect.py`.

### How sync works

```
edit /workspaces/ocr-container/CONVENTIONS.md
        │
        ▼
uv run python scripts/sync-conventions.py
        │
        ▼ rewrites between markers in each:
pdomain-book-tools/CONVENTIONS.md
pdomain-ocr-cli/CONVENTIONS.md
pd-ocr-labeler/CONVENTIONS.md
pdomain-ocr-labeler-spa/CONVENTIONS.md
pdomain-ocr-synth/CONVENTIONS.md
pd-ocr-trainer/CONVENTIONS.md
pdomain-prep-for-pgdp/CONVENTIONS.md
        │
        ▼
uv run python scripts/check-sync-drift.py  # pre-commit hook; rejects manual edits inside the block
```

### Cross-references

- Per-repo rule library lives in each repo's `CONVENTIONS.md` (below the markers).
- Workspace memory feedback files (`/workspaces/ocr-container/.claude/agent-memory/<repo>/feedback_*.md`) capture in-flight learnings; promote stable ones up to the relevant CONVENTIONS.md when they stop being repo-specific.
- Operational/topology notes live in `/srv/bot-workspaces/README.md` and `docs/superpowers/bot-workspaces.md`.
```

- [ ] **Step 3: Run lint-conventions on the new file**

```bash
cd /workspaces/ocr-container
uv run python scripts/lint-conventions.py CONVENTIONS.md
```

Expected: exit 0 with no errors. If errors:
- "marker block missing" — verify the two markers exist and bracket the right content.
- "rule format invalid" — verify every `## Rule:` is followed by a blank line, `**The rule.**`, `**Why.**`.
- "duplicate rule title" — pick distinct names.

- [ ] **Step 4: Smoke-test sync-conventions.py in --check mode**

```bash
cd /workspaces/ocr-container
uv run python scripts/sync-conventions.py --check
```

Expected: report that pdomain-book-tools' block is in sync (it should be — we copied it verbatim); the other 6 repos are MISSING (no CONVENTIONS.md yet — that's R3a's job). Exit code may be nonzero; that's fine for now. Capture output to confirm only pdomain-book-tools is currently mirrored.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add CONVENTIONS.md
git commit -m "$(cat <<'EOF'
feat(conventions): add workspace canonical CONVENTIONS.md

Three cross-repo rules seeded from pdomain-book-tools/CONVENTIONS.md plus
the uv-run-everywhere rule from workspace memory:
1. No comments explaining what code does
2. Unicode escape sequences for ruff-flagged ambiguous characters
3. Use `uv run` for all Python and tool invocation

Marker block consumed by scripts/sync-conventions.py to fan out into
each per-repo CONVENTIONS.md (R3a rollout).

Unblocks v2 Plan 3 + Plan 4 operations (daily/weekly bots, sync-drift,
sibling-drift dashboard panels).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task 2: Write /srv/bot-workspaces/README.md

**Files:**
- Create: `/srv/bot-workspaces/README.md`

- [ ] **Step 1: Confirm path exists and is writable as bot**

```bash
ls -ld /srv/bot-workspaces
```

Expected: owner `claude-bot:claude-bot`, mode 2775. If not present, run `scripts/bot-workspace-bootstrap.sh` first.

- [ ] **Step 2: Write the README via sudo -u claude-bot**

```bash
sudo -u claude-bot tee /srv/bot-workspaces/README.md <<'EOF' >/dev/null
# /srv/bot-workspaces — bot-only worktree topology

This directory tree holds **detached, claude-bot-owned git worktrees** that
isolate bot work (ship-issue, style-review, style-sweep) from CT's interactive
checkouts at `/workspaces/ocr-container/<repo>/`. The two checkouts share the
underlying `.git/` object database via `git worktree add`.

## Topology

```
/srv/bot-workspaces/
├── .locks/                          # flock(1) targets, one per bot×repo
│   ├── ship-issue-pdomain-book-tools
│   ├── style-review-pdomain-book-tools
│   └── style-sweep-pdomain-book-tools
├── .state/                          # cross-bot state
│   └── bots-paused                  # touch this file to pause all bots
├── ship-issue/
│   ├── pdomain-book-tools/               # detached worktree on `wip/ship-issue`
│   └── pdomain-ocr-cli/
├── style-review/
│   └── pdomain-book-tools/               # detached worktree on `wip/ship-issue` (review window)
└── style-sweep/
    └── pdomain-book-tools/               # detached worktree on `wip/style-sweep`
```

Each `<bot>/<repo>/` is a git worktree pointing at the bot's working branch.
The branch is *borrowed* during a run: `git checkout <branch>` enters; on
success/failure cleanup, `git checkout --detach HEAD` releases the branch so
another bot or CT can take it.

## Ownership and permissions

- All files in this tree are owned by `claude-bot:claude-bot` (uid 1001, gid 1001).
- The vscode user (uid 1000) can **read** files in this tree thanks to:
  - Mode 2775 on directories (group `claude-bot` writable; setgid propagates group).
  - `git config --global --add safe.directory '/srv/bot-workspaces/*'` (one-time setup).
- The vscode user **cannot write** files here without `sudo -u claude-bot`. If you
  see `Permission denied` on a `git checkout` or edit, you're running as the wrong
  user.

## Lessons from workspace-rc (2026-05-11)

1. **Always run worktree edits as `sudo -u claude-bot`.** Running `git checkout`,
   `make lint`, or any in-tree edit as vscode will fail mid-pipeline with cryptic
   "permission denied" errors on files created earlier by the bot.

2. **`pre-commit install` is skipped in worktrees.** `.git` is a *file* pointing
   at the main repo's `.git/`, not a directory; `pre-commit install` can't write
   `.git/hooks/pre-commit` because the hooks dir lives in the main checkout. The
   per-repo Makefile has a guard (`[ -f .git/hooks/pre-commit ] || pre-commit install`)
   that skips cleanly — don't override it. Run `make lint` directly to invoke ruff
   without going through the install path.

3. **DNS warm-up before push.** Containerized network occasionally times out the
   first `git push`; a `git remote -v` (which forces DNS resolution) before push
   warms the cache. Subsequent pushes succeed.

4. **Don't `git config --add safe.directory` per-repo from vscode.** Use the
   global wildcard (`/srv/bot-workspaces/*`) once. Per-repo entries multiply and
   are hard to clean up.

5. **flock is advisory** — the orchestrators acquire with non-blocking mode and
   skip cleanly on contention (exit code 0, "skipping due to lock"). If you see
   a flock file persist after a run, the orchestrator crashed; `flock -u <fd>`
   manually or just `rm` the stale lock.

## Operational commands

- **Pause all bots**: `sudo -u claude-bot touch /srv/bot-workspaces/.state/bots-paused`
- **Resume all bots**: `sudo -u claude-bot rm /srv/bot-workspaces/.state/bots-paused`
- **Bootstrap a new repo**: `sudo /workspaces/ocr-container/scripts/bot-workspace-bootstrap.sh <bot-name> <repo-name>` (idempotent)
- **List active worktrees**: `sudo -u claude-bot git -C /workspaces/ocr-container/<repo> worktree list`
- **Force-cleanup a stuck worktree**: `sudo -u claude-bot git -C /workspaces/ocr-container/<repo> worktree remove -f /srv/bot-workspaces/<bot>/<repo>`

## See also

- `docs/superpowers/bot-workspaces.md` — design topology + flock + detached-HEAD pattern
- `scripts/bot-workspace-bootstrap.sh` — idempotent bootstrap
- `scripts/ship-issue-orchestrator.sh` — first consumer (reference for the pattern)
EOF
```

- [ ] **Step 3: Verify readable from vscode**

```bash
cat /srv/bot-workspaces/README.md | head -5
```

Expected: header line visible. (Not committed — this file lives outside the workspace git tree by design.)

- [ ] **Step 4: Add pointer from `docs/superpowers/bot-workspaces.md`**

Read the current contents of `/workspaces/ocr-container/docs/superpowers/bot-workspaces.md`. At the bottom (or wherever fits), append:

```markdown

## Operational notes (live README)

Hands-on operational notes — file ownership gotchas, flock recovery, the
workspace-rc lessons — live at `/srv/bot-workspaces/README.md` (outside the
git tree because it's bot-owned). Refresh that file when running into new
edge cases; refresh this design doc only when topology changes.
```

- [ ] **Step 5: Commit the workspace-tree change**

```bash
cd /workspaces/ocr-container
git add docs/superpowers/bot-workspaces.md
git commit -m "$(cat <<'EOF'
docs(bot-workspaces): point to live operational README

The new /srv/bot-workspaces/README.md captures workspace-rc's
ownership-model + pre-commit-in-worktree + DNS-warmup gotchas as
hands-on operational reference.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task 3: Commit staged agent-memory feedback files

**Files:**
- Modify: `.claude/agent-memory/{pdomain-book-tools,pdomain-ocr-cli,pd-ocr-labeler,pdomain-prep-for-pgdp}/MEMORY.md`
- Add: `.claude/agent-memory/pdomain-book-tools/feedback_ruf001_002_003_convention.md`
- Add: `.claude/agent-memory/pdomain-ocr-cli/feedback_ruf001_escape_convention.md`
- Add: `.claude/agent-memory/pd-ocr-labeler/lint_config_noqa_patterns.md`
- Add: `.claude/agent-memory/pdomain-prep-for-pgdp/feedback_ruf001_convention.md`

- [ ] **Step 1: Check what's staged**

```bash
cd /workspaces/ocr-container
git status .claude/agent-memory/
```

Expected: 4 MEMORY.md modifications + 4 new feedback files.

- [ ] **Step 2: Verify content is non-empty and sane**

```bash
wc -l .claude/agent-memory/pdomain-book-tools/feedback_ruf001_002_003_convention.md \
  .claude/agent-memory/pdomain-ocr-cli/feedback_ruf001_escape_convention.md \
  .claude/agent-memory/pd-ocr-labeler/lint_config_noqa_patterns.md \
  .claude/agent-memory/pdomain-prep-for-pgdp/feedback_ruf001_convention.md
```

Expected: each file 20-80 lines.

- [ ] **Step 3: Commit**

```bash
cd /workspaces/ocr-container
git add .claude/agent-memory/
git commit -m "$(cat <<'EOF'
chore(agent-memory): commit RUF001/002/003 convention feedback files

Four per-repo agents produced consistent feedback during the
chore/lint-first-selectors PR work: use \uXXXX escape sequences
for ruff-flagged ambiguous Unicode characters; no `# noqa` and
no `[tool.ruff.lint] ignore` entries. The rule is now in the
workspace canonical CONVENTIONS.md cross-repo block; these
agent-memory files capture the per-repo context in which the
rule first came up.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task 4: Update STATUS.md with current landed state

**Files:**
- Modify: `/workspaces/ocr-container/docs/superpowers/plans/STATUS.md`

- [ ] **Step 1: Rewrite STATUS.md to reflect actual state**

Read the current file, then rewrite with this content:

```markdown
# Plans status

> Rolling status across the workspace bot/review/issue workflow plans.
> See `docs/superpowers/plans/2026-05-11-INDEX.md` for the active re-plan index.

## Landed plans

- **Plan A — workspace foundation** (2026-05-10) — 9/9 acceptance steps green. See archive.
- **Plan B — pdomain-book-tools pilot, B1–B5** (2026-05-10) — backlog migration + first ship-issue cycle (PR #15, #16 merged). Debrief: `2026-05-10-pilot-pdomain-book-tools-debrief.md`.
- **Lifecycle Plan 1 — skills + labels + migration** (2026-05-10/11) — `/triage`, `/spec-from-issue`, `/decompose-spec` skills + helpers + tests all landed. Label rename `claude-ok` → `bot:ship-issue-ready` complete across all 8 repos. Task 17 E2E smoke → R2.
- **Lifecycle Plan 2 — chain-state code** (2026-05-10/11) — `scripts/spec_chain_data.py`, `build-spec-chain-report.py`, dashboard panel all landed. Backfill on pdomain-book-tools partially done by workspace-rc (issues #24, #26–#29 + feature-requests #25, #30–#32 + 5 milestones). Remaining backfill + verification → R2; per-repo rollout → R3b.
- **v2 Plan 1 — lint-first + worktree retrofit** (2026-05-10/11) — Phase 1 (worktrees + bootstrap + pre-commit no-trailing-todos) merged. Phase 0 (lint-first selectors) in 7 open PRs awaiting merge → R0 unblocks; CT merges.
- **v2 Plans 2–4 code** (2026-05-10/11) — all scripts present: extract-conventions, style-review-detect, style-review-apply, style-review-orchestrator, style-sweep-orchestrator, sync-conventions, check-sync-drift, check-sibling-drift, lint-conventions. `/pr-review` skill landed. pdomain-book-tools/CONVENTIONS.md authored. Operational rollout (workspace canonical + per-repo arming) → R1 + R3a.

## Active plans (this re-plan)

See `2026-05-11-INDEX.md` for the dispatch wave ordering.

- **R0** — lint-first PR unblock (parallel with R1)
- **R1** — workspace canonical CONVENTIONS.md + housekeeping (parallel with R0)
- **R2** — lifecycle E2E + chain backfill on pdomain-book-tools (after R1)
- **R3a** — bot infra rollout to 3 mature repos (after R1)
- **R3b** — lifecycle drive-through on same 3 repos (after R2 + R3a)
- **R4** — pdomain-book-tools B6 multi-cycle stress (after R1; parallel-safe with R2/R3a)

## Historical entries

### Plan A complete: 2026-05-10T01:23:00Z

All 9 acceptance steps passed. (Detail elided — see archive.)

### Plan B pilot resolved: 2026-05-10T03:35:00Z

20 pilot-feedback findings closed. 1 TDD slice shipped end-to-end (PR #15, #16 merged on pdomain-book-tools). B6 multi-cycle stress deferred to R4 of the 2026-05-11 re-plan.
```

- [ ] **Step 2: Commit**

```bash
cd /workspaces/ocr-container
git add docs/superpowers/plans/STATUS.md
git commit -m "$(cat <<'EOF'
chore(status): refresh STATUS.md against actual landed state

Lists what's in code vs what's pending operational rollout. Points
to the 2026-05-11 re-plan index for the active dispatch sequence.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task 5: Tick acceptance bullets in the two specs

**Files:**
- Modify: `docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md`
- Modify: `docs/superpowers/specs/2026-05-10-feature-request-spec-decomposition-design.md`

- [ ] **Step 1: Read each spec's "Contract / Acceptance" section**

```bash
grep -n "## Contract\|## Acceptance\|^- \[ \]\|^- \[x\]" docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md
grep -n "## Contract\|## Acceptance\|^- \[ \]\|^- \[x\]" docs/superpowers/specs/2026-05-10-feature-request-spec-decomposition-design.md
```

- [ ] **Step 2: For each acceptance bullet in the v2 spec, change `- [ ]` → `- [x]` for these (landed in code as of today)**

Use the Edit tool, with `replace_all: false` since each acceptance bullet is unique. Target bullets to flip in the v2 (code-review-style-cleanup) spec:

- Worktree retrofit ships (Phase 1 of Plan 1).
- `style-review-detect.py` + `style-review-apply.py` exist with test coverage.
- `/pr-review` skill exists.
- pdomain-book-tools/CONVENTIONS.md authored.
- Daily review-bot orchestrator script exists.
- Weekly sweep-bot orchestrator script exists.
- `sync-conventions.py`, `check-sync-drift.py`, `check-sibling-drift.py`, `lint-conventions.py` exist.
- Dashboard panels for style-bot-events, sync-drift, sibling-drift exist.

Leave UNCHECKED (still in flight):
- "Workspace canonical CONVENTIONS.md exists" — flips to checked after Task 1 commits in this plan.
- All per-repo rollout bullets — R3a.
- "One full week of clean daily runs" — observation period.
- "One full month of clean weekly sweeps" — observation period.

For the lifecycle spec, flip the acceptance bullets for:
- Three skills exist with helpers + tests.
- Label rename complete across 8 repos.
- Chain-state report scripts exist with tests.
- Dashboard panel for chain state exists.

Leave UNCHECKED:
- E2E smoke validation on pdomain-book-tools (R2 Task).
- Per-repo rollout (R3b).

- [ ] **Step 3: After Task 1 above commits the workspace canonical, return here and flip the canonical bullet too**

(Sequential dependency within this plan — defer this micro-edit until Task 1 has actually committed.)

- [ ] **Step 4: Update Status: Draft → Active on both specs**

```bash
grep -n "^> .Status:\|^Status:" docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md
grep -n "^> .Status:\|^Status:" docs/superpowers/specs/2026-05-10-feature-request-spec-decomposition-design.md
```

Change `Draft` → `Active (operational rollout pending; see 2026-05-11-INDEX.md)` for both.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md docs/superpowers/specs/2026-05-10-feature-request-spec-decomposition-design.md
git commit -m "$(cat <<'EOF'
docs(specs): tick acceptance bullets for landed v2 + lifecycle work

Flips Draft → Active on both 2026-05-10 design specs. Acceptance
bullets for landed pieces (scripts, skills, dashboard panels)
checked; per-repo rollout + observation-period bullets remain
open, tracked in 2026-05-11-INDEX.md.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Acceptance

R1 is complete when:

- [ ] `/workspaces/ocr-container/CONVENTIONS.md` exists, contains 3 rules in the marker block, passes `uv run python scripts/lint-conventions.py CONVENTIONS.md`.
- [ ] `/srv/bot-workspaces/README.md` exists, readable as vscode.
- [ ] `docs/superpowers/bot-workspaces.md` references the new README.
- [ ] 4 staged agent-memory feedback files + 4 MEMORY.md updates committed.
- [ ] `STATUS.md` reflects actual landed state and points to the 2026-05-11 index.
- [ ] Both 2026-05-10 design specs have flipped to Status: Active and accurate acceptance-bullet state.
- [ ] All 5 commits authored with the workspace's standard Co-Authored-By tag.

## Trade-offs considered

| Decision | Pro | Con |
|---|---|---|
| Author canonical from pdomain-book-tools' CONVENTIONS.md seed | Verbatim reuse — proves the sync direction; sync is already tested with this content | If we later add a workspace-only rule that wasn't already on pdomain-book-tools, we owe pdomain-book-tools a sync-conventions run |
| 3 rules to start, not 6+ | Tight initial scope — fewer style-review false positives | We'll add more rules as patterns emerge (judgment-call line item: when?) |
| `/srv/bot-workspaces/README.md` outside git | Lives with the topology it documents; refreshes don't need a workspace commit | Not version-controlled — workspace-rc lessons could drift |
| Spec status Draft → Active vs Draft → Done | "Active" captures "code done, rollout pending" cleanly | We'll need to flip to Done after R3a + R3b — extra trip |

## References

- Workspace-rc transcript: `/home/vscode/.claude/projects/-workspaces-ocr-container/7457da1a-87a0-464b-a01e-5b2ee654ab4d.jsonl`
- pdomain-book-tools CONVENTIONS.md (the seed): `pdomain-book-tools/CONVENTIONS.md`
- Scripts depending on the canonical: `scripts/sync-conventions.py`, `scripts/check-sync-drift.py`, `scripts/check-sibling-drift.py`, `scripts/lint-conventions.py`
- Workspace memory `feedback_use_uv_not_python3.md` (rule #3 source)
