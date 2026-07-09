---
status: complete
---

# Code-review + style-cleanup — Plan 1: Foundation (lint-first + worktree retrofit)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land Phases 0 and 1 of the v2 code-review/style spec. End state: ruff/pyright lint configs are tightened across the seven Python pd-* repos so mechanical violations get caught at commit time rather than by a future bot; ship-issue is retrofitted to operate inside `/srv/bot-workspaces/ship-issue/<repo>/` worktrees so CT's main checkouts stay pristine; the worktree topology is documented and reusable for future bots.

**Architecture:** Phase 0 is a fan-out: a canonical lint-first config delta is described once in this plan's appendix; each per-repo agent applies it to its own repo and lands a small commit (one task per repo). Phase 1 is a single architectural change: a new `/srv/bot-workspaces/` directory tree (owned by `claude-bot`) holds one worktree per (bot, repo) pair, sharing the underlying `.git/` object DB with CT's interactive checkout via `git worktree add`. The `ship-issue-orchestrator.sh` script becomes worktree-aware: borrow the branch via `git checkout` inside a flock window, work, push, then `git checkout --detach HEAD` before releasing. Future bots inherit the same pattern.

**Tech Stack:** Python 3.11, `ruff`, `pyright` (or `ty`), `pre-commit`, `flock(1)`, `git worktree`, bash scripts.

**Source spec:** `docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md`

**Depends on:** None. This plan can land independently of Plan 2 (the feature-request lifecycle backfill plan); it operates on disjoint files.

**Why this plan exists separately:** Phase 0 + Phase 1 are foundational for everything in v2 Plans 2/3/4. Landing them as a separate plan means: (1) the worktree retrofit is in place before Plan 2's `/pr-review` skill or Plan 3's bots ever run; (2) lint-first cleanup waves don't intermingle with bot-engine code review; (3) Plan 2 of the lifecycle work (backfill on pdomain-book-tools) can stack on top without merge churn. Plan-1's tasks are mostly subagent-dispatchable (deterministic config edits + a single bash script rewrite); CT's only required involvement is fielding the lint-cleanup PRs as they land per repo.

**Out of scope:**
- pd-png-optimizer's Rust core. Per spec Open Q #4 (lean: Python only in v2). The repo's Python facade (`python/pd_png_optimizer/`) IS in scope for Phase 0 lint-first if its pre-commit covers Python files; otherwise also out of scope. Phase 1 worktree retrofit applies to pd-png-optimizer only if/when ship-issue ever runs against it, which today it does not (the repo is local-only per CT's pending decision #4).
- Style review semantics. Phase 0 only tightens *mechanical* lint; the prose-rule story arrives in v2 Plans 2–4.
- The `bot:style-*-ready` labels. Those land in v2 Plans 2/3 alongside their consumers.

---

## Background context for the engineer

You are the FIRST plan in a four-plan v2 rollout. Read the spec at `docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md` end-to-end — it's 387 lines and the `Architecture overview`, `Bot-isolation topology`, `Lint-first prep work`, and `Implementation sequencing` sections (in particular) define the acceptance criteria for both phases.

The seven pd-* repos covered by Phase 0:
1. `pdomain-book-tools`
2. `pdomain-ocr-cli`
3. `pd-ocr-labeler`
4. `pdomain-ocr-labeler-spa`
5. `pdomain-ocr-synth`
6. `pd-ocr-trainer`
7. `pdomain-prep-for-pgdp`

`pd-png-optimizer` is excluded from Phase 0 because the spec scopes lint-first to "All 7 pd-* repos" (the eighth has a Rust core; its Python facade can be evaluated separately later — out of scope here).

Each pd-* repo has its own `pyproject.toml` and `.pre-commit-config.yaml` (verified at plan-write time). Following workspace agent-routing (`CLAUDE.md`), every code change inside a pd-* tree should be delegated to that repo's full-power agent (`pdomain-book-tools`, `pdomain-ocr-cli`, `pd-ocr-labeler`, `pdomain-ocr-labeler-spa`, `pdomain-ocr-synth`, `pd-ocr-trainer`, `pdomain-prep-for-pgdp`). The parent (this) session dispatches; the per-repo agent owns the pyproject/precommit edits + new lint findings + commit.

Existing surfaces relevant to Phase 1:
- `scripts/ship-issue-orchestrator.sh` — currently `cd $WORKSPACE/$(basename "$REPO")` (workspace = `/workspaces/ocr-container`); needs to point at `/srv/bot-workspaces/ship-issue/<repo>` instead.
- `scripts/ship-issue-pick.py`, `scripts/ship-issue-success.sh`, `scripts/ship-issue-failure.sh` — invoked from inside the orchestrator's cwd; they generally use `git rev-parse`/`git fetch`/`git push` and don't hardcode paths, but VERIFY this when retrofitting.
- `.claude/hooks/bash-command-guard.py` — the cwd-aware bash guard. The bot still needs to be allowed in the new path.
- `pd-push` (workspace script) — used by ship-issue-success.sh; works from any working tree as long as origin is set, and worktrees inherit origin from the parent repo.

**Caveats from prior bot work** (debrief findings already absorbed by ship-issue-orchestrator.sh:11-17, lines 50-56, 80-87):
- claude-bot has no `gh auth login` state; `GH_TOKEN` from `/run/secrets/gh-token-pd` is the only auth path. The retrofit must continue exporting it before any `gh` call.
- `--settings $WORKSPACE/.claude/settings.json` MUST be passed when invoking `claude` so the bash-command-guard hook fires regardless of `cwd`-based find-up.
- `env -u GH_TOKEN claude …` strips the bot PAT from the inner claude session (per ship-issue's no-gh-from-the-skill rule).

---

## File structure (created or modified by this plan)

**Created:**

- `/srv/bot-workspaces/` (NEW directory tree, owned by `claude-bot:claude-bot`).
- `/srv/bot-workspaces/.locks/` (flock files).
- `/srv/bot-workspaces/.state/` (state flag files; `bots-paused` flag lives here from v2 Plan 2 onward).
- `/srv/bot-workspaces/ship-issue/<repo>/` (one worktree per pd-* repo as needed; created lazily by the bootstrap script).
- `scripts/bot-workspace-bootstrap.sh` — idempotent helper that ensures the topology + per-repo worktrees exist.
- `tests/scripts/test_bot_workspace_bootstrap.py` — light unit coverage (path-derivation logic only; the actual `git worktree add` is not test-driven, smoke-validated by Task 13).
- `docs/superpowers/bot-workspaces.md` — short architecture doc explaining the topology, flock pattern, and detached-HEAD dance. Linked from `CLAUDE.md`.

**Modified:**

- `scripts/ship-issue-orchestrator.sh` — cd target + flock + detached-HEAD dance.
- One commit per pd-* repo with: `pyproject.toml` (ruff selector additions, pyright/ty strict bumps where applicable), `.pre-commit-config.yaml` if any new hook needed, plus the lint cleanup needed to make the new selectors pass.
- `.pre-commit-config.yaml` (workspace level, `/workspaces/ocr-container/.pre-commit-config.yaml`) — add a `no-trailing-todos` local hook.
- `scripts/no-trailing-todos.sh` — new local hook script (workspace).
- `tests/scripts/test_no_trailing_todos.py` — unit tests for the hook.
- `CLAUDE.md` — add a one-paragraph note pointing at `docs/superpowers/bot-workspaces.md` so future agents (especially per-repo agents) understand why some bot paths look unfamiliar.

**Untouched** (deliberately): pd-png-optimizer's `pyproject.toml` (Rust-Python facade — out of scope per Open Q #4); CT's interactive checkouts under `/workspaces/ocr-container/<repo>/` (those stay pristine — the whole point of Phase 1).

---

## Canonical lint-first delta (reference for Phase 0 tasks)

Each Phase 0 task applies a *subset* of the deltas below — the subset that the target repo doesn't already have. The per-repo agent compares the repo's current `[tool.ruff.lint]` and pyright/ty config to this canonical and proposes the minimum diff that achieves it.

**`[tool.ruff.lint]`** — add these selectors (preserve any existing `select`/`ignore` that the repo already has; the existing `E741` ignore on pdomain-book-tools, for instance, must be preserved):

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "B", "SIM", "UP", "RUF", "ERA", "T20"]
# Repo-specific ignores stay as they are. New selectors may surface
# findings the repo's existing code doesn't satisfy yet — those are
# fixed (or `# noqa`'d with a one-line justification) inside this same
# task's commit. Wholesale ignores of new families are NOT permitted —
# we want the families on, even if we squelch a specific code.
```

| Family | What it catches |
|---|---|
| `N` | Naming conventions (PEP 8 names) |
| `B` | flake8-bugbear (likely bugs and design problems) |
| `SIM` | Simplification (unnecessary if/else, redundant comparisons) |
| `UP` | pyupgrade (use newer Python idioms) |
| `RUF` | Ruff-specific rules |
| `ERA` | eradicate (commented-out code) |
| `T20` | flake8-print (no `print()` in library code; tests/scripts may opt out per-file) |

The existing baseline (`E`, `F`, `W`, `I`) stays; `I` is the import sorter the repos already rely on.

**Pyright/ty** — strict on `src/`, default on `tests/` and `scripts/`. If a repo doesn't yet have a `[tool.pyright]` (or equivalent `[tool.ty]`) block, add:

```toml
[tool.pyright]
include = ["src", "tests", "scripts"]
typeCheckingMode = "basic"  # default; tests + scripts inherit

[[tool.pyright.executionEnvironments]]
root = "src"
typeCheckingMode = "strict"
```

If the repo uses `ty` instead of pyright, mirror the structure with `[tool.ty.environments]` per the upstream `ty` docs. Each per-repo agent should follow whatever the repo already uses; don't introduce a new type-checker.

**Markdownlint** stays as-is across all repos. No changes here.

**No-trailing-todos hook** lands once at the workspace level (Task 8), so per-repo work doesn't repeat it. The hook script lives at `scripts/no-trailing-todos.sh` and rejects any `TODO:` / `FIXME:` / `XXX:` that's not paired with either an issue ID (`#NNN`) or a date (`(YYYY-MM-DD)`).

---

# Phase 0: Lint-first config tightening across 7 pd-* repos

This phase is a fan-out. Each repo gets its own commit (one PR per repo). The pilot repo is `pdomain-book-tools` because (a) Plan 2 will exercise pdomain-book-tools first, (b) it already has the most-mature lint config (only `E741` ignored). The per-repo agent applies the canonical delta, runs ruff to surface new findings, fixes or `# noqa`s each one with a justification, and commits.

## Task 1: pdomain-book-tools lint-first (pilot)

**Files:**

- Modify: `pdomain-book-tools/pyproject.toml` — `[tool.ruff.lint]` block (extend `select`).
- Modify (if absent): `pdomain-book-tools/pyproject.toml` — `[tool.pyright]` block (or existing equivalent) to enable strict on `src/`.
- Modify: any `pdomain-book-tools/src/` or `pdomain-book-tools/tests/` files where the new selectors surface findings.

**Process:** delegate to the `pdomain-book-tools` agent. The agent is scoped to the pdomain-book-tools tree and owns this commit end-to-end.

- [ ] **Step 1: Dispatch the per-repo agent**

Use the Agent tool with `subagent_type=pdomain-book-tools`. Prompt template (substitute repo name):

```
Repo path: /workspaces/ocr-container/pdomain-book-tools/

Task: apply the v2 lint-first delta from
docs/superpowers/plans/2026-05-10-code-review-style-cleanup-plan-1.md
("Canonical lint-first delta" section). For pdomain-book-tools specifically:

1. Open pdomain-book-tools/pyproject.toml. Find the [tool.ruff.lint] block
   (currently only `ignore = ["E741"]`). Add a `select` line bringing
   the canonical selectors on:
       select = ["E", "F", "W", "I", "N", "B", "SIM", "UP", "RUF", "ERA", "T20"]
   PRESERVE the existing `ignore = ["E741"]` line (the loop-variable
   `l` rationale documented above the line is correct; do not touch it).

2. If [tool.pyright] is absent, add the canonical block. If pyright
   already exists with a different shape, leave its existing config
   alone EXCEPT to ensure src/ is in strict mode.

3. Run `ruff check .` from the repo root. Iterate: for each new finding,
   either fix in place (preferred) or add a `# noqa: <code>` with a
   one-line justification comment. Do NOT silence the entire family
   in pyproject (e.g., do not add "T20" to ignore globally) — squelch
   specific codes only when truly unavoidable.

4. Run `pre-commit run --all-files` to confirm everything else still
   passes.

5. Run `make fast-check` (the repo's standard pre-PR gate).

6. Commit with message:
       chore(lint): adopt v2 lint-first selectors (N/B/SIM/UP/RUF/ERA/T20) + pyright strict on src/
   in a feature branch (do NOT push), then open a draft PR via pd-push.
   The PR should be reviewable by CT before merge.

7. Report back: number of new findings surfaced, how many fixed in
   place vs noqa'd, and the PR URL.

Return a short summary including the diff stat (lines added / removed
in pyproject + total source files modified).
```

- [ ] **Step 2: Read agent's report; review the PR; merge after CT approval**

After the agent returns, read its summary. Open the PR URL and skim the
non-pyproject diffs (the lint cleanup). Most fixes should be small.
Anything large is a signal that the new selector is misconfigured —
flag back to the agent.

- [ ] **Step 3: Workspace-level commit (none)**

This task has no workspace-meta commit. The PR lands in the
pdomain-book-tools repo via `pd-push`. The workspace's main `git log` does
not include this work — it's per-repo.

---

## Task 2: pdomain-ocr-cli lint-first

Repeat Task 1's pattern, dispatching `pdomain-ocr-cli` agent with the same
prompt (substitute repo name). This task is independent of Task 1 and
can run in parallel; if running sequentially, prefer this order so the
canonical delta is applied to the simpler / smaller repos first
(easier to spot mistakes).

- [ ] **Step 1: Dispatch `pdomain-ocr-cli` agent** with the prompt template
  from Task 1, substituting `pdomain-ocr-cli` for `pdomain-book-tools`. The
  pdomain-ocr-cli pyproject may not have an existing `[tool.ruff.lint]`
  block — agent decides: append a fresh one with the canonical select.

- [ ] **Step 2: Review and merge the PR.**

---

## Task 3: pd-ocr-labeler lint-first

Same pattern.

- [ ] **Step 1: Dispatch `pd-ocr-labeler` agent.**
- [ ] **Step 2: Review and merge the PR.**

---

## Task 4: pdomain-ocr-labeler-spa lint-first

Same pattern.

- [ ] **Step 1: Dispatch `pdomain-ocr-labeler-spa` agent.**

Note: pdomain-ocr-labeler-spa has both Python (FastAPI backend) and
TypeScript (Vite/React frontend) sides. The lint-first delta applies
ONLY to the Python side (`backend/` or wherever the FastAPI lives;
agent verifies). TypeScript already has its own lint chain via the SPA's `.pre-commit-config.yaml`; not in scope here.

- [ ] **Step 2: Review and merge the PR.**

---

## Task 5: pdomain-ocr-synth lint-first

Same pattern.

- [ ] **Step 1: Dispatch `pdomain-ocr-synth` agent.**

Note: pdomain-ocr-synth is currently spec-only (no `src/` yet). Phase 0
still applies because it tightens the lint config the future code will
land against. If the agent reports "no source files yet — only specs",
that's expected; the pyproject change is still landed.

- [ ] **Step 2: Review and merge the PR.**

---

## Task 6: pd-ocr-trainer lint-first

Same pattern.

- [ ] **Step 1: Dispatch `pd-ocr-trainer` agent.**
- [ ] **Step 2: Review and merge the PR.**

---

## Task 7: pdomain-prep-for-pgdp lint-first

Same pattern.

- [ ] **Step 1: Dispatch `pdomain-prep-for-pgdp` agent.**

Note: pdomain-prep-for-pgdp also has a TypeScript SPA frontend; the lint
delta only applies to the FastAPI backend's Python side. Same logic as
pdomain-ocr-labeler-spa.

- [ ] **Step 2: Review and merge the PR.**

---

## Task 8: Workspace-level no-trailing-todos pre-commit hook

**Files:**

- Create: `scripts/no-trailing-todos.sh`
- Create: `tests/scripts/test_no_trailing_todos.py`
- Modify: `.pre-commit-config.yaml` (workspace) — add a `local` hook entry that invokes `scripts/no-trailing-todos.sh`.

**Why workspace-level not per-repo.** A trailing TODO in any markdown
or python file (specs, plans, scripts, helpers) is unwanted, and the
pre-commit at the workspace root already runs across the whole tree.
Per-repo replication would invite drift. Each pd-* repo can layer its
own additional hooks but inherits this one transitively for files
touched by workspace commits.

- [ ] **Step 1: Write the failing test**

Save as `tests/scripts/test_no_trailing_todos.py`:

```python
"""Tests for scripts/no-trailing-todos.sh.

The hook script accepts file paths as args (pre-commit's `pass_filenames`
contract), reads each file, and exits nonzero on the first TODO/FIXME/XXX
that isn't paired with a tracking marker (issue # or YYYY-MM-DD date).
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
HOOK = WORKSPACE / "scripts/no-trailing-todos.sh"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(HOOK), *args],
        capture_output=True, text=True,
    )


def test_passes_when_no_todos():
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write("# Title\n\nNo trailing markers here.\n")
        path = f.name
    r = _run(path)
    assert r.returncode == 0, r.stderr


def test_passes_with_issue_paired_todo():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write("# TODO #42: refactor when bug is fixed\n")
        path = f.name
    r = _run(path)
    assert r.returncode == 0, r.stderr


def test_passes_with_date_paired_todo():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write("# TODO (2026-05-10): revisit when v2 lands\n")
        path = f.name
    r = _run(path)
    assert r.returncode == 0, r.stderr


def test_rejects_unpaired_todo():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write("# TODO: fix this\n")
        path = f.name
    r = _run(path)
    assert r.returncode != 0
    assert "TODO" in r.stderr or "TODO" in r.stdout


def test_rejects_unpaired_fixme_and_xxx():
    for marker in ("FIXME", "XXX"):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(f"<!-- {marker}: hand-wave -->\n")
            path = f.name
        r = _run(path)
        assert r.returncode != 0, f"expected {marker} unpaired to fail"


def test_rejects_only_first_match_with_clear_message():
    """The hook should print which file:line failed."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write("a = 1\n# TODO: nope\nb = 2\n")
        path = f.name
    r = _run(path)
    assert r.returncode != 0
    assert path in (r.stdout + r.stderr)
    assert ":2:" in (r.stdout + r.stderr)  # line 2 is where TODO lives
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_no_trailing_todos.py -v
```

Expected: FAIL — script does not exist yet.

- [ ] **Step 3: Implement the hook script**

Save as `scripts/no-trailing-todos.sh`:

```bash
#!/usr/bin/env bash
# no-trailing-todos.sh — reject TODO/FIXME/XXX without an issue or date pairing.
#
# Pre-commit invokes this with file paths as arguments. The hook scans
# each file and exits nonzero on the first unpaired marker, printing
# `path:line: <marker>: <text>`.
#
# Pairing rule: an immediate `#NNN` issue ref (e.g., "#42") OR a
# parenthesized YYYY-MM-DD date suffix anywhere on the same logical
# line marks the TODO as tracked. Anything else is rejected.

set -euo pipefail

if [[ $# -eq 0 ]]; then
  exit 0
fi

# Marker words we care about.
MARKERS='\b(TODO|FIXME|XXX)\b'
# Acceptable pairing: any of "#<digits>" or "(YYYY-MM-DD)" appears on
# the same line after the marker.
PAIRING='(#[0-9]+|\([0-9]{4}-[0-9]{2}-[0-9]{2}\))'

failed=0
for f in "$@"; do
  [[ -f "$f" ]] || continue
  # Use grep -n for line numbers; -P for Perl regex (lookahead-friendly).
  while IFS= read -r line; do
    lineno="${line%%:*}"
    rest="${line#*:}"
    # Inspect the line: does it contain a pairing AFTER the marker?
    if echo "$rest" | grep -qE "$PAIRING"; then
      continue
    fi
    echo "$f:$lineno: unpaired marker — $rest" >&2
    failed=1
    break
  done < <(grep -nE "$MARKERS" "$f" || true)
done

exit "$failed"
```

```bash
chmod +x /workspaces/ocr-container/scripts/no-trailing-todos.sh
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_no_trailing_todos.py -v
```

Expected: 6 tests pass.

- [ ] **Step 5: Wire into workspace pre-commit**

Read the workspace `.pre-commit-config.yaml`:

```bash
cat /workspaces/ocr-container/.pre-commit-config.yaml
```

Add a new `local` hook entry, structured like the existing local hooks
in the file (the file already includes lint-spec.py and other locals).
Append to the appropriate `repos:` block:

```yaml
- repo: local
  hooks:
    - id: no-trailing-todos
      name: no trailing todos
      description: Reject TODO/FIXME/XXX without an issue ref or YYYY-MM-DD pairing.
      entry: scripts/no-trailing-todos.sh
      language: script
      types_or: [python, markdown, shell]
```

Adjust `types_or` to match what the existing locals use (the file may
already have a workspace-wide language and pattern convention).

- [ ] **Step 6: Smoke-test against the existing tree**

```bash
cd /workspaces/ocr-container
pre-commit run no-trailing-todos --all-files
```

Expected: the hook flags any pre-existing unpaired TODOs across the
workspace tree. If anything fails, fix in a separate commit (pair the
TODO with an issue or date, or remove it). The intent is for the hook
to land on a clean tree.

- [ ] **Step 7: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/no-trailing-todos.sh tests/scripts/test_no_trailing_todos.py .pre-commit-config.yaml
git commit -m "feat(pre-commit): no-trailing-todos hook (rejects unpaired TODO/FIXME/XXX)"
```

---

# Phase 1: Worktree retrofit + ship-issue isolation

Phase 1 turns CT's main checkout from "where the bot writes" into "where
CT works", and gives the bot its own isolated worktree under `/srv/`.
Existing ship-issue work continues unchanged in semantics; only the
filesystem location moves.

## Task 9: Document the bot-workspaces topology

**Files:**

- Create: `docs/superpowers/bot-workspaces.md`
- Modify: `CLAUDE.md` — append a one-paragraph reference to the new doc.

This task is documentation-first so subsequent tasks have a single place
to point at. The doc describes the topology, the flock pattern, and the
detached-HEAD dance.

- [ ] **Step 1: Write the doc**

Save as `docs/superpowers/bot-workspaces.md`:

```markdown
# Bot workspaces

Per-bot isolated git worktrees under `/srv/bot-workspaces/`, owned by
`claude-bot`. CT's interactive checkouts at
`/workspaces/ocr-container/<repo>/` stay pristine; bots write to their
own subtree.

## Topology

    /srv/bot-workspaces/
      .locks/                       # flock files (one per (bot,repo))
      .state/                       # state flags (e.g., bots-paused)
      ship-issue/<repo>/            # worktree on wip/ship-issue
      style-review/<repo>/          # worktree (also tracks wip/ship-issue)
      style-sweep/<repo>/           # worktree on wip/style-sweep
      ...

A single `.git/` directory lives under CT's main checkout; the bot
worktrees share its object DB via `git worktree add`. One worktree per
(bot, repo) — added lazily by `scripts/bot-workspace-bootstrap.sh`.

## Branch-contention coordination

Git allows only one worktree per branch. Both `ship-issue/<repo>` and
`style-review/<repo>` need to operate on `wip/ship-issue`. Resolution:
each bot's worktree sits at **detached HEAD** between runs. A bot:

1. Acquires the flock at `/srv/bot-workspaces/.locks/<bot>.<repo>.lock`.
2. Runs `git checkout wip/ship-issue` (succeeds because no peer holds
   the branch — flock guarantees).
3. Does its work, pushes via `pd-push`.
4. Runs `git checkout --detach HEAD` to release the branch.
5. Releases the flock.

style-sweep uses a different branch (`wip/style-sweep`), so no
contention with the other two.

## Permissions

`/srv/bot-workspaces/` is owned `claude-bot:claude-bot`, mode 0755.
CT's vscode user can read everything but not write — explicit
permission boundary that keeps CT's interactive sessions from
accidentally writing into bot trees.

## Setup

`scripts/bot-workspace-bootstrap.sh <bot> <repo>` is idempotent:
creates the topology if missing, adds the worktree if missing, leaves
existing worktrees alone. Safe to call from every orchestrator startup.

## Why a single .git/

Disk efficiency. Three worktrees × N repos × ~100MB pack data each
would balloon. `git worktree add` shares the object DB — only the
HEAD/index/working tree are duplicated, which is small.
```

- [ ] **Step 2: Reference from CLAUDE.md**

Append to `/workspaces/ocr-container/CLAUDE.md`, after the
"Cross-repo work" section:

```markdown
## Bot workspaces

Bots (ship-issue, style-review, style-sweep, …) run inside isolated
worktrees under `/srv/bot-workspaces/`, NOT inside CT's interactive
checkouts at `/workspaces/ocr-container/<repo>/`. See
[`docs/superpowers/bot-workspaces.md`](docs/superpowers/bot-workspaces.md)
for the topology, flock + detached-HEAD coordination model, and the
bootstrap helper. Agents should never assume `/workspaces/ocr-container/<repo>/`
is the bot's cwd; orchestrators self-cd into the right worktree before
delegating to the inner agent.
```

- [ ] **Step 3: Commit**

```bash
cd /workspaces/ocr-container
git add docs/superpowers/bot-workspaces.md CLAUDE.md
git commit -m "docs(bot-workspaces): document /srv/bot-workspaces topology + flock pattern"
```

---

## Task 10: Bootstrap script for bot-workspace topology

**Files:**

- Create: `scripts/bot-workspace-bootstrap.sh`
- Create: `tests/scripts/test_bot_workspace_bootstrap.py` — unit tests on the path-derivation helper logic only (the actual `git worktree add` is filesystem-side; smoke-tested in Task 13).

The bootstrap script is idempotent: callable from every orchestrator's
prelude; ensures the directory tree, locks dir, state dir, and the
specific (bot, repo) worktree all exist; no-op if everything already
exists.

- [ ] **Step 1: Write the failing test**

Save as `tests/scripts/test_bot_workspace_bootstrap.py`:

```python
"""Tests for scripts/bot-workspace-bootstrap.sh.

The script also exposes a small helper function via an ``--print-paths``
flag for use in test code: it prints the four paths it would create as
JSON, without doing any filesystem work. Tests target that surface.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/bot-workspace-bootstrap.sh"


def _print_paths(bot: str, repo: str) -> dict:
    r = subprocess.run(
        ["bash", str(SCRIPT), "--print-paths", bot, repo],
        capture_output=True, text=True, check=True,
    )
    return json.loads(r.stdout)


def test_print_paths_for_ship_issue_pd_book_tools():
    p = _print_paths("ship-issue", "pdomain-book-tools")
    assert p["root"] == "/srv/bot-workspaces"
    assert p["locks_dir"] == "/srv/bot-workspaces/.locks"
    assert p["state_dir"] == "/srv/bot-workspaces/.state"
    assert p["worktree"] == "/srv/bot-workspaces/ship-issue/pdomain-book-tools"
    assert p["lockfile"].endswith("/.locks/ship-issue.pdomain-book-tools.lock")


def test_print_paths_for_style_sweep():
    p = _print_paths("style-sweep", "pdomain-book-tools")
    assert p["worktree"].endswith("/style-sweep/pdomain-book-tools")
    assert "style-sweep.pdomain-book-tools.lock" in p["lockfile"]


def test_rejects_invalid_bot_name():
    r = subprocess.run(
        ["bash", str(SCRIPT), "--print-paths", "../bad", "pdomain-book-tools"],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "invalid bot" in (r.stderr + r.stdout).lower()


def test_rejects_invalid_repo_name():
    r = subprocess.run(
        ["bash", str(SCRIPT), "--print-paths", "ship-issue", "../escape"],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "invalid repo" in (r.stderr + r.stdout).lower()
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_bot_workspace_bootstrap.py -v
```

Expected: FAIL — script does not exist.

- [ ] **Step 3: Implement the script**

Save as `scripts/bot-workspace-bootstrap.sh`:

```bash
#!/usr/bin/env bash
# bot-workspace-bootstrap.sh — idempotently ensure /srv/bot-workspaces
# topology and a per-(bot,repo) worktree exist.
#
# Usage:
#   scripts/bot-workspace-bootstrap.sh <bot> <repo>
#       creates /srv/bot-workspaces/.locks, .state, and adds a git
#       worktree at /srv/bot-workspaces/<bot>/<repo> tracking the
#       expected branch (wip/ship-issue for ship-issue + style-review;
#       wip/style-sweep for style-sweep). Idempotent.
#
#   scripts/bot-workspace-bootstrap.sh --print-paths <bot> <repo>
#       prints a JSON object with the four canonical paths and exits.
#       Used by tests; never touches the filesystem.

set -euo pipefail

ROOT="/srv/bot-workspaces"
WORKSPACE="${WORKSPACE_ROOT:-/workspaces/ocr-container}"

PRINT_ONLY=0
if [[ "${1:-}" == "--print-paths" ]]; then
  PRINT_ONLY=1
  shift
fi

BOT="${1:?usage: $0 [--print-paths] <bot> <repo>}"
REPO="${2:?usage: $0 [--print-paths] <bot> <repo>}"

# Reject path-traversal in either name.
case "$BOT" in
  *..*|*/*) echo "invalid bot name: $BOT" >&2; exit 64 ;;
esac
case "$REPO" in
  *..*|*/*) echo "invalid repo name: $REPO" >&2; exit 64 ;;
esac

# Pick the branch this bot tracks. style-sweep is the only one with its
# own branch; everything else borrows wip/ship-issue.
case "$BOT" in
  style-sweep) BRANCH="wip/style-sweep" ;;
  *)           BRANCH="wip/ship-issue" ;;
esac

LOCKS_DIR="$ROOT/.locks"
STATE_DIR="$ROOT/.state"
WORKTREE="$ROOT/$BOT/$REPO"
LOCKFILE="$LOCKS_DIR/$BOT.$REPO.lock"

if [[ "$PRINT_ONLY" == "1" ]]; then
  cat <<EOF
{
  "root": "$ROOT",
  "locks_dir": "$LOCKS_DIR",
  "state_dir": "$STATE_DIR",
  "worktree": "$WORKTREE",
  "lockfile": "$LOCKFILE",
  "branch": "$BRANCH"
}
EOF
  exit 0
fi

# --- filesystem mutations from here on -------------------------------------

# Ensure the root + subdirs exist with the right ownership. Run as
# claude-bot to inherit the right uid/gid; if invoked as another user,
# require sudo for the umask/own bits.
[[ -d "$ROOT" ]] || sudo install -d -o claude-bot -g claude-bot -m 0755 "$ROOT"
[[ -d "$LOCKS_DIR" ]] || sudo install -d -o claude-bot -g claude-bot -m 0755 "$LOCKS_DIR"
[[ -d "$STATE_DIR" ]] || sudo install -d -o claude-bot -g claude-bot -m 0755 "$STATE_DIR"

# Touch the lockfile so flock has a target. Don't truncate if it exists.
[[ -e "$LOCKFILE" ]] || sudo install -o claude-bot -g claude-bot -m 0644 /dev/null "$LOCKFILE"

# Add the worktree if missing. Both `git worktree list` and `git worktree
# add` run from the parent repo (the canonical .git/ lives under
# CT's interactive checkout).
PARENT="$WORKSPACE/$REPO"
if [[ ! -d "$PARENT/.git" ]]; then
  echo "bootstrap: parent repo $PARENT is not a git tree" >&2
  exit 65
fi

if ! git -C "$PARENT" worktree list --porcelain | grep -q "^worktree $WORKTREE$"; then
  # Detached-HEAD on creation; bot will checkout its branch when it runs.
  sudo -u claude-bot git -C "$PARENT" worktree add --detach "$WORKTREE"
fi

# State-flag file the bots check at startup. Empty = not paused.
[[ -e "$STATE_DIR/bots-paused" ]] || true  # absence-as-flag; leave alone here.

echo "bootstrap: ready — $WORKTREE on $BRANCH (lock=$LOCKFILE)"
```

```bash
chmod +x /workspaces/ocr-container/scripts/bot-workspace-bootstrap.sh
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_bot_workspace_bootstrap.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Smoke-fire the bootstrap once for ship-issue + pdomain-book-tools**

```bash
sudo /workspaces/ocr-container/scripts/bot-workspace-bootstrap.sh ship-issue pdomain-book-tools
```

Expected: `bootstrap: ready — /srv/bot-workspaces/ship-issue/pdomain-book-tools on wip/ship-issue (lock=/srv/bot-workspaces/.locks/ship-issue.pdomain-book-tools.lock)`

Verify:

```bash
ls -la /srv/bot-workspaces/
git -C /workspaces/ocr-container/pdomain-book-tools worktree list
```

Expected: the new worktree appears in `git worktree list`. The
top-level dirs `.locks`, `.state`, and `ship-issue/pdomain-book-tools`
exist with `claude-bot:claude-bot` ownership.

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/bot-workspace-bootstrap.sh tests/scripts/test_bot_workspace_bootstrap.py
git commit -m "feat(bot-workspaces): bootstrap script + path-derivation tests"
```

---

## Task 11: Retrofit ship-issue-orchestrator.sh to use the bot worktree

**Files:**

- Modify: `scripts/ship-issue-orchestrator.sh:35-47` — change the cd
  target from `$WORKSPACE/$(basename "$REPO")` to
  `/srv/bot-workspaces/ship-issue/$(basename "$REPO")`, with a flock
  window and the detached-HEAD dance around the working span.

The retrofit's invariants:

1. `bot-workspace-bootstrap.sh ship-issue <repo>` runs first (creates
   the worktree on first call; no-op afterward).
2. The orchestrator then does its work inside a `flock` window around
   the lockfile.
3. Inside the window, the orchestrator runs `git checkout wip/ship-issue`
   if needed (the bootstrap left the worktree at detached HEAD).
4. When all RUNS finish (or the orchestrator exits early), the
   orchestrator does `git checkout --detach HEAD` to release the
   branch back to the pool.
5. flock auto-releases on script exit; the detached-HEAD step is a
   defense-in-depth so even if flock semantics change later, the next
   bot's `git checkout wip/ship-issue` always succeeds.

- [ ] **Step 1: Read the existing orchestrator**

```bash
cat -n /workspaces/ocr-container/scripts/ship-issue-orchestrator.sh
```

Confirm the current structure: lines 35-47 set up `REPO_DIR` and `cd`.
Lines 60-100 are the per-run loop. Lines 50-56 export `GH_TOKEN`. The
patch wraps the `cd` + per-run loop inside a flock + detached-HEAD
window.

- [ ] **Step 2: Apply the retrofit**

Find the section starting at line 35. Replace lines 35-47 (the
`WORKSPACE`, `REPO_DIR`, and `cd "$REPO_DIR"` block) with:

```bash
WORKSPACE="${WORKSPACE_ROOT:-/workspaces/ocr-container}"

# Worktree retrofit (v2 Plan 1 Phase 1). ship-issue writes inside an
# isolated worktree under /srv/bot-workspaces/ship-issue/<repo>/, NOT
# inside CT's interactive checkout. The bootstrap is idempotent.
"$WORKSPACE/scripts/bot-workspace-bootstrap.sh" ship-issue "$(basename "$REPO")"

REPO_DIR="/srv/bot-workspaces/ship-issue/$(basename "$REPO")"
LOCKFILE="/srv/bot-workspaces/.locks/ship-issue.$(basename "$REPO").lock"
PAUSE_FLAG="/srv/bot-workspaces/.state/bots-paused"

if [[ ! -d "$REPO_DIR/.git" && ! -f "$REPO_DIR/.git" ]]; then
  echo "orchestrator: $REPO_DIR is not a worktree (bootstrap failed?)" >&2
  exit 64
fi

# Pause-flag check. /pr-review (v2 Plan 2) sets this; absence = run.
if [[ -e "$PAUSE_FLAG" ]]; then
  echo "▸ bots-paused flag present at $PAUSE_FLAG; skipping" >&2
  exit 0
fi

# Acquire the lockfile for the duration of the script. -E sets the
# nonzero-exit code path; -w 0 means non-blocking — abort cleanly if
# another bot already holds it.
exec 9>"$LOCKFILE"
if ! flock -nE 0 9; then
  echo "▸ another bot already holds $LOCKFILE; skipping" >&2
  exit 0
fi

cd "$REPO_DIR"

# Borrow the branch. The worktree sits at detached HEAD between runs;
# only one worktree per branch is allowed, so we own wip/ship-issue
# inside the flock window. Trap to release on any exit.
git fetch --quiet
git checkout wip/ship-issue 2>/dev/null || git checkout -b wip/ship-issue origin/wip/ship-issue 2>/dev/null \
  || git checkout -b wip/ship-issue origin/main
trap 'git checkout --detach HEAD 2>/dev/null || true' EXIT
```

This new block:
- Bootstraps the worktree (idempotent).
- Checks the pause flag.
- Takes a non-blocking flock (skips cleanly if another bot is in there).
- cd into the worktree.
- Borrows `wip/ship-issue` (creating from origin or main if first run).
- Sets a trap so the branch is released to detached-HEAD on exit.

The rest of the orchestrator (GH_TOKEN load, per-run loop, summary
print) is unchanged.

- [ ] **Step 3: Verify the diff**

```bash
cd /workspaces/ocr-container
git diff scripts/ship-issue-orchestrator.sh | head -80
```

Confirm: only lines 35-47 are replaced; the per-run loop (60-100) is
untouched.

- [ ] **Step 4: Lint the script**

```bash
shellcheck scripts/ship-issue-orchestrator.sh
```

Fix any new findings.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/ship-issue-orchestrator.sh
git commit -m "refactor(ship-issue): cd into /srv/bot-workspaces worktree + flock + detached-HEAD"
```

---

## Task 12: Audit ship-issue-success.sh and ship-issue-failure.sh for path assumptions

**Files:**

- Read (review only): `scripts/ship-issue-success.sh`, `scripts/ship-issue-failure.sh`, `scripts/ship-issue-pick.py`.
- Modify (only if the audit finds a hardcoded path or an assumption that breaks under the worktree): the offending file.

These scripts are invoked from inside the orchestrator's cwd (now the
worktree). Most operations should already work cwd-relative; this task
verifies and fixes any hidden assumptions.

- [ ] **Step 1: Audit each script**

```bash
cd /workspaces/ocr-container
grep -nE '/workspaces/ocr-container|\$WORKSPACE_ROOT|\$WORKSPACE\b' \
  scripts/ship-issue-success.sh \
  scripts/ship-issue-failure.sh \
  scripts/ship-issue-pick.py
```

For each hit, decide:
- Path that ALWAYS resolves to the same absolute location (e.g.,
  `$WORKSPACE/.claude/agent-memory/ship-issue/...` is fine — these
  files are workspace-meta artifacts, not repo-tree artifacts).
- Path that assumes the cwd-equivalent of CT's interactive checkout
  (e.g., reading `pyproject.toml` from `pwd` is fine because the
  worktree has the same content).
- Path that explicitly reads from CT's interactive checkout (e.g.,
  `/workspaces/ocr-container/$REPO/something`) — this one needs
  fixing OR documenting why it's correct.

- [ ] **Step 2: Document or fix each finding**

For findings that are correct as-is (workspace-meta artifacts), leave
unchanged. For findings that need a fix, change to use `pwd`-based or
`$REPO_DIR`-based references. Commit each fix separately:

```bash
git add scripts/<file>
git commit -m "fix(ship-issue-<file>): use cwd-relative path under bot worktree"
```

- [ ] **Step 3: Confirm nothing is left**

```bash
cd /workspaces/ocr-container
grep -nE '/workspaces/ocr-container/\b(pd-[a-z-]+)\b' \
  scripts/ship-issue-*.sh scripts/ship-issue-pick.py 2>&1 | head -20
```

Expected: no hits, or only hits inside comments.

If this audit finds zero changes, the task ends with no commit — that's
fine; document in the report that the audit produced no findings.

---

## Task 13: Smoke-test the retrofit end-to-end against pdomain-book-tools

This is the integration test for Phase 1. It runs ship-issue against a
real (small) issue, confirms the work happens in the worktree, and
verifies CT's main checkout stays clean.

- [ ] **Step 1: Pick a small unattached issue in pdomain-book-tools**

You need a `bot:ship-issue-ready` + `status:ready` issue that's small.
If none exists, file one yourself (CT sign-off may be required).
Alternatively, drop the `bot:ship-issue-ready` label after the smoke
run completes so it's a proper test of the orchestrator's claim path.

```bash
gh issue list -R pdomain/pdomain-book-tools \
  --label "bot:ship-issue-ready,status:ready" \
  --json number,title,labels --jq '.[]'
```

Pick the smallest by `effort:S` and label.

- [ ] **Step 2: Snapshot CT's main checkout state**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
git status --porcelain | tee /tmp/before-smoke.txt
git rev-parse HEAD | tee -a /tmp/before-smoke.txt
git symbolic-ref --short HEAD | tee -a /tmp/before-smoke.txt
```

- [ ] **Step 3: Run the orchestrator under sudo -u claude-bot**

```bash
sudo -u claude-bot env WORKSPACE_ROOT=/workspaces/ocr-container \
  /workspaces/ocr-container/scripts/ship-issue-orchestrator.sh \
  --repo pdomain/pdomain-book-tools --runs 1
```

Expected: the orchestrator picks the issue, claims it, runs the inner
claude session, and either commits + pushes (success) or bounces.

- [ ] **Step 4: Confirm CT's main checkout is unchanged**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
git status --porcelain | tee /tmp/after-smoke.txt
git rev-parse HEAD | tee -a /tmp/after-smoke.txt
git symbolic-ref --short HEAD | tee -a /tmp/after-smoke.txt
diff /tmp/before-smoke.txt /tmp/after-smoke.txt
```

Expected: the diff is empty. CT's main checkout HEAD, branch, and dirty
state are all preserved.

- [ ] **Step 5: Confirm the work happened in the worktree**

```bash
cd /srv/bot-workspaces/ship-issue/pdomain-book-tools
git log --oneline -5
git symbolic-ref --short HEAD || echo "(detached)"
```

Expected: HEAD is detached (the trap fired on orchestrator exit), but
recent commits show the slice's work.

- [ ] **Step 6: Confirm the PR was opened correctly**

```bash
gh pr list -R pdomain/pdomain-book-tools --state open
```

Expected: the rolling `wip/ship-issue` PR (or a new one if this is the
first slice) shows the new commit.

- [ ] **Step 7: Document the smoke run**

Append to `docs/superpowers/bot-workspaces.md`:

```markdown
## Smoke-tested 2026-MM-DD

First end-to-end run via the worktree retrofit completed cleanly
against pdomain-book-tools issue #<NN>. CT's main checkout state at
`/workspaces/ocr-container/pdomain-book-tools/` was bit-identical before
and after; the slice landed under
`/srv/bot-workspaces/ship-issue/pdomain-book-tools/`.
```

(Substitute today's date and the issue number.)

- [ ] **Step 8: Commit the smoke documentation**

```bash
cd /workspaces/ocr-container
git add docs/superpowers/bot-workspaces.md
git commit -m "docs(bot-workspaces): record first end-to-end smoke run"
```

---

## Task 14: Mark v2 spec Phase 0 + Phase 1 acceptance bullets

This task is documentation: tick the spec acceptance bullets that this
plan completed. The spec stays Status: Draft until ALL of v2 is
landed (after v2 Plan 4 Phase 7); Plan 1 only ticks two of the eleven
contract bullets.

- [ ] **Step 1: Edit the spec**

Open
`docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md`.
Find the Contract / Acceptance section. Tick the first two bullets:

```markdown
- [x] Phase 0 lint-config bumps merged to all 7 pd-* repos; pre-commit passes
- [x] `/srv/bot-workspaces/` topology exists; ship-issue retrofitted; CT's main checkouts stay clean during a ship-issue run
```

The remaining bullets stay unticked.

- [ ] **Step 2: Update Last updated**

Bump the `> **Last updated**:` to today's date.

- [ ] **Step 3: Lint + commit**

```bash
cd /workspaces/ocr-container
python3 scripts/lint-spec.py docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md
git add docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md
git commit -m "spec(code-review-style): mark Phases 0 and 1 contract bullets done"
```

---

## Done — what comes next

Plan 1 lands the foundations of v2. With this plan merged:

- Mechanical lint violations are caught at commit time across all 7
  Python pd-* repos.
- ship-issue runs in `/srv/bot-workspaces/ship-issue/<repo>/` with a
  flock + detached-HEAD pattern that's reusable for future bots.
- The bot-workspaces topology is documented and the bootstrap helper
  is callable by future orchestrators.

**Next plan: v2 Plan 2** — `docs/superpowers/plans/2026-05-10-code-review-style-cleanup-plan-2.md`
covers Phases 2 + 3 (CONVENTIONS.md bootstrap on workspace + pdomain-book-tools, plus the `/pr-review` CT-interactive skill that uses the new shared
`style-review-detect.py` + `style-review-apply.py` engine).

Plan 1's tasks 1-7 (per-repo lint-first) and 9-14 (worktree retrofit) are independent enough to run with parallel subagents during execution; CT triages PRs as they land. Task 8 (no-trailing-todos hook) should land before any of the per-repo lint commits so the workspace tree is clean for the new hook to validate against.
