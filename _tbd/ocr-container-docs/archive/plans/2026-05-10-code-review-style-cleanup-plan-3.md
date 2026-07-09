---
status: complete
---

# Code-review + style-cleanup — Plan 3: daily review-bot + weekly sweep-bot

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land Phases 4 and 5 of the v2 code-review/style spec on pdomain-book-tools. End state: `style-review-orchestrator.sh` runs daily via ctask against the rolling `wip/ship-issue` PR; `style-sweep-orchestrator.sh` runs weekly via ctask against `wip/style-sweep`; both bots reuse the detect+apply scripts from v2 Plan 2; events get logged to `style-bot-events.jsonl` and rendered as a dashboard panel.

**Architecture:** Each bot is a thin bash orchestrator that (1) checks `bots-paused`, (2) takes a flock, (3) borrows its branch (detached-HEAD pattern from v2 Plan 1), (4) shells out to `style-review-detect.py | style-review-apply.py`, (5) tags the processed sha for stale-comment marking, (6) releases. The daily bot operates on the diff between its last-tag and current HEAD; the weekly bot resets to `origin/main` and reviews the full tree (capped). Auto-arming `bot:style-review-ready` on every ship-issue PR creation lands as a one-line addition to `success.sh`. The `style-bot-events` dashboard panel is a deterministic JSON-to-HTML renderer that tail-reads the events log.

**Tech Stack:** bash (orchestrators), Python (style-review-detect/apply already from v2 Plan 2; build-cost-dashboard renderer extension), `flock(1)`, `git worktree`, `gh` CLI, `ctask`.

**Source spec:** `docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md`

**Depends on:**
- v2 Plan 1 (lint-first + worktree retrofit) merged.
- v2 Plan 2 (CONVENTIONS.md bootstrap + /pr-review + style-review-detect.py + style-review-apply.py) merged.

**Out of scope:**
- Sync-conventions.py, check-sync-drift.py, check-sibling-drift.py, lint-conventions.py — v2 Plan 4.
- Dashboard panels for sync-drift and sibling-drift — v2 Plan 4 (THIS plan adds only the style-bot-events panel).
- Rollout to other 6 repos — v2 Plan 4 Phase 7.
- Observation periods. Phase 4's "one full week of clean daily runs" and Phase 5's "one full month / 4 sweeps" are post-deployment observations — Plan 3 lands the code; CT observes externally and reports back via separate work.

---

## Background context for the engineer

Read the spec sections **Daily style-review-bot orchestrator**, **Weekly style-sweep-bot orchestrator**, **Bot operational events log**, **Review window coordination** (already absorbed by Plan 2), and **New labels** before writing code.

**Existing surfaces relevant here:**

- `scripts/style-review-detect.py` (v2 Plan 2) — emits the JSON contract.
- `scripts/style-review-apply.py` (v2 Plan 2) — consumes it; writes events.
- `scripts/bot-workspace-bootstrap.sh` (v2 Plan 1) — creates the worktrees lazily.
- `scripts/ship-issue-orchestrator.sh` (v2 Plan 1 retrofit) — pattern to mirror.
- `scripts/ship-issue-success.sh` — CT-controlled; one-line auto-arm goes here.
- `scripts/seed-labels.sh` — extend with three new bot labels.
- `scripts/build-cost-dashboard.py` — extend with one new panel.
- `ctask` (workspace-level scheduler) — adds two new entries.
- `/srv/bot-workspaces/.state/bots-paused` — pause flag from Plan 1/2.
- `/srv/bot-workspaces/.locks/<bot>.<repo>.lock` — flock files.

**Resolved Open Q #1 (auto-arm bot:style-review-ready)**: lean is to
auto-arm on PR creation. Task 3 implements that as a one-line append in
success.sh; CT can remove the label on PRs they want bot-untouched (the
inverse of arming).

**Stale-comment marker.** Each style-review run tags
`refs/tags/style-review/<repo>/<sha>` (where `<sha>` = the post-run HEAD).
The next daily run reads the prior tag, computes scope as
`<prior-sha>..HEAD`, and skips entirely if HEAD == prior tag. The tag
is moved (not appended), pushed via `git push --force --tags
<prior-tag>`. Force is acceptable because tags in `style-review/`
namespace are bot-owned and never authored by a human.

**Per-run cap calibration.** Default `50 + 50` (50 high-confidence
findings per run + 50 judgment findings per run). Stored in
`.claude/style-bot.toml` at the workspace level. Overridable per-repo
via `.claude/style-bot.toml` at the repo level. Cap-hit produces a
`sweep-capped` event; the run still applies its findings up to the cap
and the next tick continues from the new HEAD.

---

## File structure (created or modified by this plan)

**Created:**

- `scripts/style-review-orchestrator.sh` — daily bot wrapper.
- `scripts/style-sweep-orchestrator.sh` — weekly bot wrapper.
- `tests/scripts/test_style_bot_events_panel.py` — panel renderer tests.
- `.claude/style-bot.toml` — workspace default config (cap, schedule hints).
- One `recurring:weekly` GitHub issue per repo (manually filed; pdomain-book-tools first).

**Modified:**

- `scripts/seed-labels.sh` — add three labels.
- `scripts/ship-issue-success.sh` — auto-arm `bot:style-review-ready` on PR creation/update.
- `scripts/build-cost-dashboard.py` — add `style-bot-events` panel.
- `tests/scripts/test_build_cost_dashboard.py` — extend for the new panel.
- `ctask` config — add two scheduled entries (daily review, weekly sweep).
- `docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md` — tick Phase 4/5 bullets at end.

---

# Phase 4: Daily style-review-bot

## Task 1: Add three new bot labels to seed-labels.sh

**Files:**

- Modify: `scripts/seed-labels.sh` — append three new entries to the `LABELS` array.

The labels are workspace-wide (one rerun of `seed-labels.sh <repo>`
populates each repo). Per Plan 2 of the lifecycle's Phase 0 Task 0.5,
`seed-labels.sh` is now also idempotent on description drift, so a
rerun on existing labels harmlessly refreshes any prior typos.

- [ ] **Step 1: Edit the LABELS array**

Open `scripts/seed-labels.sh`. Find the LABELS array (around line 10).
Append three new entries after the existing `bot:ship-issue-ready`
entry:

```bash
  "bot:style-review-ready|0e8a16|Bot-eligibility gate — daily style-review-bot may modify this PR"
  "bot:style-sweep-ready|0e8a16|Bot-eligibility gate — weekly style-sweep-bot may pick up this issue"
  "bot:style-fixed-by-agent|c5def5|Bot self-applied: style-review-bot landed at least one auto-fix"
```

- [ ] **Step 2: Smoke-test against pdomain-book-tools**

```bash
cd /workspaces/ocr-container
scripts/seed-labels.sh pdomain/pdomain-book-tools 2>&1 | head -20
```

Expected: three new lines like `+ bot:style-review-ready` for the new
labels; existing labels show as `↻ <name> (refreshed)` (per Plan 2
Phase 0 Task 0.5).

```bash
gh label list -R pdomain/pdomain-book-tools --json name \
  --jq '.[].name' | grep '^bot:'
```

Expected output:
```
bot:ship-issue-ready
bot:style-fixed-by-agent
bot:style-review-ready
bot:style-sweep-ready
```

- [ ] **Step 3: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/seed-labels.sh
git commit -m "feat(seed-labels): add bot:style-review-ready / sweep-ready / fixed-by-agent"
```

---

## Task 2: Workspace style-bot config

**Files:**

- Create: `.claude/style-bot.toml` — workspace defaults.

A small TOML file with the per-run cap, the conventions doc path
discovery rule, and the model selection. Per-repo overrides land in
`<repo>/.claude/style-bot.toml` if needed (none for pdomain-book-tools yet).

- [ ] **Step 1: Write the config**

Save as `/workspaces/ocr-container/.claude/style-bot.toml`:

```toml
# Style-bot defaults. Per-repo overrides go in <repo>/.claude/style-bot.toml.

[review]
# Daily review-bot: scope is diff from last-tag to HEAD on wip/ship-issue.
# Cap pair = (high_confidence_max, judgment_max).
cap_high = 50
cap_judgment = 50
model = "claude-sonnet-4-6"

[sweep]
# Weekly sweep-bot: full-tree scope (capped same way).
cap_high = 50
cap_judgment = 50
model = "claude-sonnet-4-6"

[paths]
# Where to find each repo's conventions doc, relative to its tree root.
conventions = "CONVENTIONS.md"

[events]
# Path is computed from $SHIP_ISSUE_MEMORY_DIR (env-var); the file name
# is fixed.
log_file = "style-bot-events.jsonl"
```

- [ ] **Step 2: Commit**

```bash
cd /workspaces/ocr-container
git add .claude/style-bot.toml
git commit -m "feat(style-bot): workspace default config (caps, model, paths)"
```

---

## Task 3: Auto-arm bot:style-review-ready on ship-issue PR creation

**Files:**

- Modify: `scripts/ship-issue-success.sh` — add a single label-apply call after the PR is created/updated.

Per spec Open Q #1 (resolved-lean: auto-arm), every PR ship-issue opens
or updates gets `bot:style-review-ready` automatically. CT removes the
label on PRs they want untouched.

- [ ] **Step 1: Read the existing success.sh**

```bash
cat -n /workspaces/ocr-container/scripts/ship-issue-success.sh | head -80
```

Locate where the PR is created (likely a `gh pr create` or a
`gh pr edit` call). The auto-arm goes immediately after.

- [ ] **Step 2: Add the auto-arm**

Find the section that creates or updates the rolling PR. After the
`gh pr create`/`gh pr edit` call, append a label-apply:

```bash
# Auto-arm style-review-bot on every ship-issue PR. CT can remove the
# label on PRs they want untouched. (v2 Open Q #1, resolved-lean.)
gh pr edit "$PR_NUM" --repo "$REPO" --add-label bot:style-review-ready \
  || echo "WARN: could not auto-arm bot:style-review-ready on PR #$PR_NUM" >&2
```

(`PR_NUM` and `REPO` should already be in scope at this point in
success.sh; if not, derive them from the surrounding code.)

- [ ] **Step 3: Smoke-test (without running ship-issue)**

```bash
gh pr edit <existing-rolling-PR> --repo pdomain/pdomain-book-tools \
  --add-label bot:style-review-ready
gh pr view <PR> --repo pdomain/pdomain-book-tools \
  --json labels --jq '.labels[].name' | grep style-review-ready
```

Expected: the label is on the PR.

- [ ] **Step 4: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/ship-issue-success.sh
git commit -m "feat(ship-issue): auto-arm bot:style-review-ready on PR creation"
```

---

## Task 4: scripts/style-review-orchestrator.sh — daily bot wrapper

**Files:**

- Create: `scripts/style-review-orchestrator.sh`

The orchestrator parallels `ship-issue-orchestrator.sh` (v2 Plan 1
retrofitted shape). It bootstraps the worktree, takes flock, borrows
`wip/ship-issue` (detached-HEAD on exit), reads the prior-tag sha,
runs detect+apply, advances the tag.

- [ ] **Step 1: Write the script**

Save as `scripts/style-review-orchestrator.sh`:

```bash
#!/usr/bin/env bash
# style-review-orchestrator.sh — daily style-review-bot wrapper.
#
# Usage: style-review-orchestrator.sh --repo <owner/repo>
#
# Reads tag refs/tags/style-review/<repo>/<sha>; if HEAD on
# wip/ship-issue == that sha, no-op exits. Otherwise runs detect+apply
# against the diff between the prior sha and HEAD, then advances the
# tag and pushes it.

set -euo pipefail

# Match ship-issue-orchestrator's PATH guard so claude-bot's `claude`
# binary is reachable when invoked via sudo / ctask.
export PATH="$HOME/.local/bin:$PATH"

REPO=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 64 ;;
  esac
done
[[ -n "$REPO" ]] || { echo "usage: $0 --repo <owner/repo>" >&2; exit 64; }

WORKSPACE="${WORKSPACE_ROOT:-/workspaces/ocr-container}"
BASENAME="$(basename "$REPO")"
PAUSE_FLAG="/srv/bot-workspaces/.state/bots-paused"
LOCKFILE="/srv/bot-workspaces/.locks/style-review.$BASENAME.lock"
WORKTREE="/srv/bot-workspaces/style-review/$BASENAME"

# Bootstrap (idempotent).
"$WORKSPACE/scripts/bot-workspace-bootstrap.sh" style-review "$BASENAME"

# Pause-flag check.
if [[ -e "$PAUSE_FLAG" ]]; then
  echo "▸ bots-paused; skipping" >&2
  exit 0
fi

# Take the flock; non-blocking. Skip cleanly if held.
exec 9>"$LOCKFILE"
if ! flock -nE 0 9; then
  echo "▸ another style-review run holds $LOCKFILE; skipping" >&2
  exit 0
fi

# Auth: load GH_TOKEN from secret.
GH_SECRET="/run/secrets/gh-token-pd"
if [[ -r "$GH_SECRET" ]]; then
  GH_TOKEN="$(cat "$GH_SECRET")"
  export GH_TOKEN
fi

cd "$WORKTREE"
git fetch --quiet
# Borrow the branch (detached-HEAD on exit).
git checkout wip/ship-issue 2>/dev/null \
  || git checkout -b wip/ship-issue origin/wip/ship-issue 2>/dev/null \
  || { echo "no wip/ship-issue branch; nothing to review" >&2; exit 0; }
trap 'git checkout --detach HEAD 2>/dev/null || true' EXIT

# Read prior tag (if present).
TAG="style-review/$BASENAME"
PRIOR_SHA="$(git rev-parse "refs/tags/$TAG" 2>/dev/null || echo "")"
HEAD_SHA="$(git rev-parse HEAD)"

if [[ "$PRIOR_SHA" == "$HEAD_SHA" ]]; then
  echo "▸ no commits since last review tag ($PRIOR_SHA); no-op" >&2
  exit 0
fi

# Find the open rolling PR.
PR_NUM="$(gh pr list -R "$REPO" --label bot:style-review-ready \
  --state open --json number --jq '.[0].number // empty')"
if [[ -z "$PR_NUM" ]]; then
  echo "▸ no PR with bot:style-review-ready; nothing to review" >&2
  exit 0
fi

# Pick the diff base. If we have a prior sha use it; otherwise origin/main.
FROM_SHA="${PRIOR_SHA:-$(git merge-base HEAD origin/main)}"

CONVENTIONS="$WORKTREE/CONVENTIONS.md"
if [[ ! -f "$CONVENTIONS" ]]; then
  # missing-conventions event (apply.py would normally emit this; we
  # raise it here directly since detect/apply won't run without the
  # doc).
  python3 - <<EOF
import json, os
from pathlib import Path
log = Path(os.environ.get("SHIP_ISSUE_MEMORY_DIR",
    "/home/vscode/.claude/agent-memory/ship-issue")) / "style-bot-events.jsonl"
log.parent.mkdir(parents=True, exist_ok=True)
with log.open("a") as f:
    f.write(json.dumps({"kind": "missing-conventions",
                        "repo": "$REPO", "scope": "diff"}) + "\n")
EOF
  echo "▸ $CONVENTIONS missing; emitted missing-conventions event" >&2
  exit 0
fi

# Run detect + apply with prompt-cached conventions.
"$WORKSPACE/scripts/style-review-detect.py" \
  --conventions "$CONVENTIONS" \
  --scope diff \
  --from-sha "$FROM_SHA" \
  --to-sha "$HEAD_SHA" \
  | "$WORKSPACE/scripts/style-review-apply.py" \
      --repo "$REPO" --pr-number "$PR_NUM"

# Push any new commits made by apply.py.
git push origin HEAD:wip/ship-issue || true

# Apply the bot:style-fixed-by-agent label if any auto-fix landed.
NEW_HEAD_SHA="$(git rev-parse HEAD)"
if [[ "$NEW_HEAD_SHA" != "$HEAD_SHA" ]]; then
  gh pr edit "$PR_NUM" -R "$REPO" --add-label bot:style-fixed-by-agent || true
fi

# Advance the tag.
git tag -f "$TAG" "$NEW_HEAD_SHA"
git push -f origin "refs/tags/$TAG"

echo "▸ style-review run complete: $PR_NUM (sha $NEW_HEAD_SHA)" >&2
```

```bash
chmod +x /workspaces/ocr-container/scripts/style-review-orchestrator.sh
```

- [ ] **Step 2: shellcheck**

```bash
cd /workspaces/ocr-container
shellcheck scripts/style-review-orchestrator.sh
```

Fix any findings.

- [ ] **Step 3: Smoke-test against pdomain-book-tools (manual)**

This is the first end-to-end run. Pre-conditions: pdomain-book-tools has an
open rolling PR with `bot:style-review-ready` (Task 3 should have
auto-armed it on the most recent ship-issue run); a `CONVENTIONS.md`
exists at pdomain-book-tools (Plan 2 Task 4); the bot has access to the
Anthropic API.

```bash
sudo -u claude-bot env WORKSPACE_ROOT=/workspaces/ocr-container \
  /workspaces/ocr-container/scripts/style-review-orchestrator.sh \
  --repo pdomain/pdomain-book-tools
```

Expected: either "no commits since last review tag" (no-op) or a real
detect+apply pass with auto-fixes and/or comments.

If the run fails, inspect:

```bash
tail -30 /home/vscode/.claude/agent-memory/ship-issue/style-bot-events.jsonl
```

Fix issues; re-run.

- [ ] **Step 4: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/style-review-orchestrator.sh
git commit -m "feat(style-review-bot): daily orchestrator (flock + tag-advance + auto-fix label)"
```

---

## Task 5: ctask schedule entry for the daily review-bot

**Files:**

- Modify: ctask config (location depends on `ctask` setup).

- [ ] **Step 1: Find ctask's config surface**

```bash
/workspaces/ocr-container/ctask list
/workspaces/ocr-container/ctask --help 2>&1 | head -20
```

Locate where ctask stores schedules. Typical: a YAML or TOML file in
the workspace; or a tmux + cron under the hood.

- [ ] **Step 2: Add the schedule**

Daily at e.g. 03:00 UTC for pdomain-book-tools (the only repo running
bots in v2 Plans 1-3; rollout to other repos is v2 Plan 4 Phase 7).
Adjust to the local equivalent of "early morning when CT isn't likely
to be reviewing":

```bash
/workspaces/ocr-container/ctask add \
  --name style-review-pdomain-book-tools \
  --cmd "sudo -u claude-bot env WORKSPACE_ROOT=/workspaces/ocr-container /workspaces/ocr-container/scripts/style-review-orchestrator.sh --repo pdomain/pdomain-book-tools" \
  --schedule "0 3 * * *"
```

Adjust the CLI surface to match `ctask`'s actual command (the prompt
above is illustrative).

- [ ] **Step 3: Smoke-fire it once manually**

```bash
/workspaces/ocr-container/ctask run style-review-pdomain-book-tools
```

Expected: orchestrator runs to completion; events log entry written if
work happened.

- [ ] **Step 4: Commit ctask config (if git-tracked)**

```bash
cd /workspaces/ocr-container
git add <ctask-config-file>
git commit -m "chore(ctask): schedule daily style-review-bot for pdomain-book-tools (03:00 UTC)"
```

---

## Task 6: Add the style-bot-events dashboard panel

**Files:**

- Modify: `scripts/build-cost-dashboard.py` — add a `render_style_bot_events_panel` function and a `{style_bot_events_panel}` placeholder.
- Modify: `tests/scripts/test_build_cost_dashboard.py` — extend with a renderer test.

The panel reads `style-bot-events.jsonl` and renders a per-repo
summary: counts by event kind for the last 7 days, with `auto-fix-reverted`
+ `sweep-capped` styled in flag-color so CT spots calibration drift
week-over-week.

**Coordination note**: `build-cost-dashboard.py` is also extended by the
lifecycle Plan 2 (chain-state panel, Task 7) and v2 Plan 4 (sync-drift
+ sibling-drift panels). Stack tasks in order: lifecycle Plan 2 Task 7
→ this task → v2 Plan 4 Phase 6 panel tasks. Coordinator should ensure
each new panel adds its own placeholder + render function with no overlap.

- [ ] **Step 1: Read the current dashboard script + chain-state panel**

```bash
sed -n '1,50p' /workspaces/ocr-container/scripts/build-cost-dashboard.py
grep -n "render_chain_state_panel\|chain_state_panel" /workspaces/ocr-container/scripts/build-cost-dashboard.py
```

The chain-state panel from Plan 2 Task 7 should already be in place.
Mirror its shape: define a `render_style_bot_events_panel(events)` and
add `{style_bot_events_panel}` to the HTML template.

- [ ] **Step 2: Write the failing test**

Add to `tests/scripts/test_build_cost_dashboard.py`:

```python
def test_style_bot_events_panel_empty_state():
    """Empty events log renders the empty-state markup."""
    import sys
    from pathlib import Path
    sys.path.insert(0, "/workspaces/ocr-container/scripts")
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_cost_dashboard",
        "/workspaces/ocr-container/scripts/build-cost-dashboard.py",
    )
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    html = m.render_style_bot_events_panel([])
    assert "no style-bot events" in html.lower() or "empty" in html.lower()


def test_style_bot_events_panel_summarizes_kinds_per_repo():
    import sys
    sys.path.insert(0, "/workspaces/ocr-container/scripts")
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_cost_dashboard",
        "/workspaces/ocr-container/scripts/build-cost-dashboard.py",
    )
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    events = [
        {"kind": "auto-fix-reverted", "repo": "pdomain/pdomain-book-tools",
         "rule": "## Rule: foo", "reason": "fast-check-failed"},
        {"kind": "sweep-capped", "repo": "pdomain/pdomain-book-tools",
         "stats": {"total_findings": 60}},
        {"kind": "missing-conventions",
         "repo": "pdomain/pdomain-ocr-cli", "scope": "diff"},
    ]
    html = m.render_style_bot_events_panel(events)
    assert "pdomain-book-tools" in html
    assert "auto-fix-reverted" in html
    assert "sweep-capped" in html
    # Calibration-relevant kinds get flag styling.
    assert "flag" in html.lower() or "alert" in html.lower() or "warn" in html.lower()
```

- [ ] **Step 3: Run the test — confirm it fails**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_build_cost_dashboard.py::test_style_bot_events_panel_empty_state -v
python3 -m pytest tests/scripts/test_build_cost_dashboard.py::test_style_bot_events_panel_summarizes_kinds_per_repo -v
```

Expected: FAIL — function not defined.

- [ ] **Step 4: Implement the renderer**

Edit `scripts/build-cost-dashboard.py`. After the existing
`render_chain_state_panel` (added by Plan 2 Task 7), add:

```python
def render_style_bot_events_panel(events) -> str:
    """Render a per-repo summary of style-bot events.

    `events` is a list of dicts read from style-bot-events.jsonl.
    Calibration-relevant kinds (auto-fix-reverted, sweep-capped,
    missing-conventions) render with a flag color so CT notices
    week-over-week drift.
    """
    if not events:
        return "<p class='style-events empty'>No style-bot events yet.</p>"
    by_repo: dict = {}
    for e in events:
        repo = e.get("repo", "(unknown)")
        kind = e.get("kind", "(unknown)")
        by_repo.setdefault(repo, {}).setdefault(kind, 0)
        by_repo[repo][kind] += 1

    flag_kinds = {"auto-fix-reverted", "sweep-capped", "missing-conventions",
                  "fast-check-prebroken"}
    rows = ["<table class='style-events'><tr><th>Repo</th><th>Event kinds (last 7 days)</th></tr>"]
    for repo in sorted(by_repo):
        cells = []
        for kind, count in sorted(by_repo[repo].items()):
            cls = "flag" if kind in flag_kinds else ""
            cells.append(f"<span class='{cls}'>{kind}: {count}</span>")
        rows.append(f"<tr><th>{repo.split('/')[-1]}</th><td>{' · '.join(cells)}</td></tr>")
    rows.append("</table>")
    return "".join(rows)
```

Find the HTML_TEMPLATE constant. Add `{style_bot_events_panel}` somewhere
sensible (after `{chain_state_panel}`). Add CSS for `.style-events`
and `.style-events .flag` (orange/red text).

In `main()`'s `.format(...)` call, add:
```python
style_bot_events_panel=render_style_bot_events_panel(_load_events()),
```

And add a small `_load_events()` helper that tail-reads the JSONL:

```python
def _load_events(days_back: int = 7) -> list:
    log_path = Path(os.environ.get(
        "SHIP_ISSUE_MEMORY_DIR",
        "/home/vscode/.claude/agent-memory/ship-issue",
    )) / "style-bot-events.jsonl"
    if not log_path.exists():
        return []
    cutoff = datetime.now() - timedelta(days=days_back)
    out: list = []
    for line in log_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        # Events without a timestamp are kept (legacy lines); newer
        # events have an ISO-8601 ts field added by JsonlEvents.emit().
        ts = obj.get("ts")
        if ts:
            try:
                if datetime.fromisoformat(ts) < cutoff:
                    continue
            except ValueError:
                pass
        out.append(obj)
    return out
```

Note: this requires `JsonlEvents.emit()` (in style-review-apply.py from
Plan 2 Task 7) to also write a `ts` field. Land a one-line addition to
that script:

```python
# In scripts/style-review-apply.py JsonlEvents.emit:
def emit(self, kind: str, payload: dict):
    self.path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"kind": kind, "ts": datetime.now().isoformat(timespec="seconds"),
           **payload}
    with self.path.open("a") as f:
        f.write(json.dumps(rec) + "\n")
```

- [ ] **Step 5: Run tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_build_cost_dashboard.py -v
```

Expected: all tests pass (including the two new ones).

- [ ] **Step 6: Smoke-render the dashboard**

```bash
SHIP_ISSUE_MEMORY_DIR=/tmp/sm DASHBOARD_SKIP_KANBAN=1 DASHBOARD_SKIP_CHAIN=1 \
  python3 /workspaces/ocr-container/scripts/build-cost-dashboard.py
ls -la /tmp/sm/cost-dashboard.html
```

Expected: dashboard HTML exists; the new style-events panel renders
(empty, since the events file is empty).

- [ ] **Step 7: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/build-cost-dashboard.py scripts/style-review-apply.py \
        tests/scripts/test_build_cost_dashboard.py
git commit -m "feat(dashboard): add style-bot-events panel + ts field on events"
```

---

# Phase 5: Weekly style-sweep-bot

## Task 7: scripts/style-sweep-orchestrator.sh — weekly bot wrapper

**Files:**

- Create: `scripts/style-sweep-orchestrator.sh`

The sweep bot uses its own branch (`wip/style-sweep`) so no flock
contention with ship-issue or style-review. It resets to `origin/main`
on each run, invokes detect.py with `--scope=tree`, and produces a
draft PR.

- [ ] **Step 1: Write the script**

Save as `scripts/style-sweep-orchestrator.sh`:

```bash
#!/usr/bin/env bash
# style-sweep-orchestrator.sh — weekly style-sweep-bot wrapper.
#
# Usage: style-sweep-orchestrator.sh --repo <owner/repo>
#
# Resets wip/style-sweep to origin/main, runs detect.py with full-tree
# scope, applies findings, opens or updates a draft PR.

set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

REPO=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 64 ;;
  esac
done
[[ -n "$REPO" ]] || { echo "usage: $0 --repo <owner/repo>" >&2; exit 64; }

WORKSPACE="${WORKSPACE_ROOT:-/workspaces/ocr-container}"
BASENAME="$(basename "$REPO")"
PAUSE_FLAG="/srv/bot-workspaces/.state/bots-paused"
LOCKFILE="/srv/bot-workspaces/.locks/style-sweep.$BASENAME.lock"
WORKTREE="/srv/bot-workspaces/style-sweep/$BASENAME"

"$WORKSPACE/scripts/bot-workspace-bootstrap.sh" style-sweep "$BASENAME"

if [[ -e "$PAUSE_FLAG" ]]; then
  echo "▸ bots-paused; skipping" >&2
  exit 0
fi

exec 9>"$LOCKFILE"
if ! flock -nE 0 9; then
  echo "▸ another style-sweep run holds $LOCKFILE; skipping" >&2
  exit 0
fi

GH_SECRET="/run/secrets/gh-token-pd"
if [[ -r "$GH_SECRET" ]]; then
  GH_TOKEN="$(cat "$GH_SECRET")"
  export GH_TOKEN
fi

cd "$WORKTREE"
git fetch --quiet
# Reset to origin/main on every run; sweep is full-tree review.
git checkout wip/style-sweep 2>/dev/null \
  || git checkout -b wip/style-sweep origin/main
git reset --hard origin/main
trap 'git checkout --detach HEAD 2>/dev/null || true' EXIT

CONVENTIONS="$WORKTREE/CONVENTIONS.md"
if [[ ! -f "$CONVENTIONS" ]]; then
  python3 - <<EOF
import json, os
from pathlib import Path
log = Path(os.environ.get("SHIP_ISSUE_MEMORY_DIR",
    "/home/vscode/.claude/agent-memory/ship-issue")) / "style-bot-events.jsonl"
log.parent.mkdir(parents=True, exist_ok=True)
with log.open("a") as f:
    f.write(json.dumps({"kind": "missing-conventions",
                        "repo": "$REPO", "scope": "tree"}) + "\n")
EOF
  echo "▸ $CONVENTIONS missing; emitted missing-conventions event" >&2
  exit 0
fi

# Existing draft PR? If yes, capture its number; if no, we'll open it
# after the first apply commit.
PR_NUM="$(gh pr list -R "$REPO" --head wip/style-sweep --state open \
  --json number --jq '.[0].number // empty')"

# Run detect + apply.
"$WORKSPACE/scripts/style-review-detect.py" \
  --conventions "$CONVENTIONS" \
  --scope tree \
  --tree-root "$WORKTREE" \
  | "$WORKSPACE/scripts/style-review-apply.py" \
      --repo "$REPO" --pr-number "${PR_NUM:-0}"

# Push.
NEW_HEAD_SHA="$(git rev-parse HEAD)"
git push -u origin HEAD:wip/style-sweep

# Open the draft PR if it didn't exist.
if [[ -z "$PR_NUM" ]] && [[ "$NEW_HEAD_SHA" != "$(git rev-parse origin/main)" ]]; then
  gh pr create -R "$REPO" --draft \
    --base main --head wip/style-sweep \
    --title "style-sweep: weekly run ($(date -u +%Y-%m-%d))" \
    --body "Generated by scripts/style-sweep-orchestrator.sh. Reviewable via /pr-review."
fi

echo "▸ style-sweep run complete: $REPO (sha $NEW_HEAD_SHA)" >&2
```

```bash
chmod +x /workspaces/ocr-container/scripts/style-sweep-orchestrator.sh
```

- [ ] **Step 2: shellcheck**

```bash
cd /workspaces/ocr-container
shellcheck scripts/style-sweep-orchestrator.sh
```

Fix any findings.

- [ ] **Step 3: Smoke-test against pdomain-book-tools (manual)**

```bash
sudo -u claude-bot env WORKSPACE_ROOT=/workspaces/ocr-container \
  /workspaces/ocr-container/scripts/style-sweep-orchestrator.sh \
  --repo pdomain/pdomain-book-tools
```

Expected: full-tree detect+apply pass; draft PR opened on
`wip/style-sweep`. May find many findings on the first run (legacy
code); the cap will hit and `sweep-capped` event fires. The next tick
resumes.

- [ ] **Step 4: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/style-sweep-orchestrator.sh
git commit -m "feat(style-sweep-bot): weekly orchestrator (full-tree, capped)"
```

---

## Task 8: File the recurring:weekly chore issue for pdomain-book-tools

**Files:**

- (No file changes — gh issue creation.)

The sweep bot is triggered (per spec) by a `recurring:weekly` chore
issue armed with `bot:style-sweep-ready`. The actual ctask schedule
(Task 9) calls the orchestrator directly; the recurring chore issue is
an audit trail (CT can see what's been done in the issue's comment
thread).

- [ ] **Step 1: File the issue**

```bash
gh issue create -R pdomain/pdomain-book-tools \
  --title "Weekly style-sweep" \
  --body "$(cat <<'EOF'
Recurring weekly chore. The bot updates this issue's body each week
with the run's summary; close to disable until re-armed.

`bot:style-sweep-ready` enables the bot; remove the label to pause.
EOF
)" \
  --label "kind:chore,recurring:weekly,bot:style-sweep-ready,status:ready"
```

Capture the issue number for Task 9.

- [ ] **Step 2: Confirm**

```bash
gh issue view <ISSUE-NUM> -R pdomain/pdomain-book-tools \
  --json number,title,labels --jq '{number, title, labels: [.labels[].name]}'
```

Expected: number, title "Weekly style-sweep", labels include
`bot:style-sweep-ready` + `recurring:weekly`.

- [ ] **Step 3: Note in pending list**

(No commit. The issue is the receipt; a comment in `docs/superpowers/`
is overkill for a single repo.)

---

## Task 9: ctask schedule entry for the weekly sweep-bot

**Files:**

- Modify: ctask config.

- [ ] **Step 1: Add the schedule**

Weekly at e.g. Sunday 04:00 UTC:

```bash
/workspaces/ocr-container/ctask add \
  --name style-sweep-pdomain-book-tools \
  --cmd "sudo -u claude-bot env WORKSPACE_ROOT=/workspaces/ocr-container /workspaces/ocr-container/scripts/style-sweep-orchestrator.sh --repo pdomain/pdomain-book-tools" \
  --schedule "0 4 * * 0"
```

Adjust the CLI surface to match `ctask` real interface.

- [ ] **Step 2: Smoke-fire it once**

```bash
/workspaces/ocr-container/ctask run style-sweep-pdomain-book-tools
```

Expected: orchestrator runs to completion. Verify the draft PR exists.

- [ ] **Step 3: Update the recurring issue body**

The orchestrator should update the issue body each run; do it manually
the first time as a smoke test:

```bash
gh issue edit <ISSUE-NUM> -R pdomain/pdomain-book-tools \
  --body "$(cat <<'EOF'
Recurring weekly chore. Last run: 2026-MM-DD UTC.

Latest sweep PR: #<PR-NUM>
Findings (last run): <high>/<judgment>; capped: <yes|no>

`bot:style-sweep-ready` enables the bot; remove the label to pause.
EOF
)"
```

(Per the spec, future iterations of the orchestrator update this body
automatically — file it as a follow-up if the v1 orchestrator doesn't
do it yet.)

- [ ] **Step 4: Commit ctask config (if git-tracked)**

```bash
cd /workspaces/ocr-container
git add <ctask-config-file>
git commit -m "chore(ctask): schedule weekly style-sweep-bot for pdomain-book-tools (Sun 04:00 UTC)"
```

---

## Task 10: First-week observation period (manual)

**This is a manual handback** — CT observes the daily bot for 1 week
and the weekly bot for 1 month before declaring Plan 3 "validated". No
code changes; just monitoring.

- [ ] **Step 1: Watch dashboard daily**

Each morning, CT opens `cost-dashboard.html` and inspects the
"Style-bot events" panel. Look for:
- High `auto-fix-reverted` count → the conventions doc's high-confidence examples are wrong; calibrate.
- Any `missing-conventions` → the bot hit a repo with no doc; investigate.
- `sweep-capped` consistently → the sweep cap is too low for the legacy code; consider raising in `.claude/style-bot.toml`.

- [ ] **Step 2: Watch comments per PR daily**

Skim each rolling PR's bot-posted comments. Are they on-target? If
many comments cite the same rule and CT keeps dismissing, that rule
is too noisy — CT proposes a refinement to CONVENTIONS.md via
`/pr-review`'s `dismiss-and-add-rule` (or `dismiss` for the rule
itself).

- [ ] **Step 3: Watch the sweep PR weekly**

Each Sunday's sweep should land a small batch. Review via `/pr-review`
when CT has time. If the sweep PR is getting massive (cap hit week
after week with high-confidence findings dominating), the cap is too
small or the conventions doc's high-confidence examples are too eager.

- [ ] **Step 4: After 1 week, declare daily-bot-validated**

If no surprises emerge, append to `docs/superpowers/bot-workspaces.md`:

```markdown
## style-review-bot daily-validated 2026-MM-DD

One full week of clean daily runs against pdomain-book-tools. Events panel
shows N total events, K calibration-flag events. CONVENTIONS.md has
been edited M times during the week (via /pr-review's add-rule path).
```

- [ ] **Step 5: After 1 month, declare sweep-bot-validated**

Same pattern. Append a corresponding paragraph.

---

## Task 11: Mark v2 spec acceptance bullets

- [ ] **Step 1: Edit the spec**

Open
`docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md`.
Tick:

```markdown
- [x] `scripts/style-review-detect.py` (LLM) + `scripts/style-review-apply.py` (deterministic) + `style-review-orchestrator.sh` + ctask schedule entry; first week of daily runs against pdomain-book-tools observed clean
- [x] `scripts/style-sweep-orchestrator.sh` + `recurring:weekly` chore issue + `bot:style-sweep-ready` label; first month (4 sweeps) on pdomain-book-tools observed clean
- [x] `style-bot-events.jsonl` written by both bots; "Style-bot events" panel renders on `cost-dashboard.html`
- [x] Three new labels (`bot:style-review-ready`, `bot:style-sweep-ready`, `bot:style-fixed-by-agent`) seeded across all 7 repos
```

(Per the previous tasks: detect/apply already exist by virtue of v2 Plan 2;
this plan adds the orchestrator wrappers + schedules + label arming.
The "all 7 repos" part of the labels bullet ticks as Plan 4 Phase 7
seeds them in the remaining 6.)

Wait — only 1 of 7 repos seeded (pdomain-book-tools) at this point. The
correct tick state is partial. Edit the bullet to reflect:

```markdown
- [x] Three new labels (`bot:style-review-ready`, `bot:style-sweep-ready`, `bot:style-fixed-by-agent`) seeded across pdomain-book-tools (rollout to remaining 6 repos in v2 Plan 4 Phase 7)
```

- [ ] **Step 2: Bump Last updated and commit**

```bash
cd /workspaces/ocr-container
python3 scripts/lint-spec.py docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md
git add docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md
git commit -m "spec(code-review-style): tick Phases 4+5 bullets (pdomain-book-tools first; 6 more in Plan 4)"
```

---

## Done — what comes next

With this plan landed:

- pdomain-book-tools has both bots running.
- CT observes for 1 week (daily bot) and 1 month (weekly sweep) before
  rollout.
- Calibration drift visible on the dashboard's style-events panel.

**Next plan: v2 Plan 4** — `docs/superpowers/plans/2026-05-10-code-review-style-cleanup-plan-4.md`
covers Phases 6 + 7 (workspace meta scripts + 6-repo rollout). Phase 6
adds `sync-conventions.py`, `check-sync-drift.py`, `check-sibling-drift.py`,
`lint-conventions.py` and the corresponding two dashboard panels. Phase 7
runs the same Phase 2-5 sequence against the remaining 6 published
repos (skipping pd-png-optimizer per Open Q #4).

Plan-3 tasks 1-7, 9 are dispatchable; Tasks 8 and 10 are CT-interactive
(file the recurring issue + observation period).
