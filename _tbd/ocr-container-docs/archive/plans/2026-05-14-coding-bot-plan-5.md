---
status: complete
---

# coding-bot Plan 5: Parallel Run + Cutover (M5 + M6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install coding-bot on both users, run it in parallel with ctask for 48–72 hours to verify parity, then cut over by stopping ctask, flipping pre-commit configs in all pd-* repos, deleting the migrated scripts, and updating CLAUDE.md files.

**Architecture:** M5 is operational — no new code. M6 is a sequence of one-shot mutation steps (deletes, config flips, CLAUDE.md updates). After M6, ctask is archived and coding-bot is the sole scheduler.

**Tech Stack:** bash (install steps), coding-bot CLI, gh CLI.

**Reference spec:** `docs/superpowers/specs/2026-05-14-coding-bot-design.md` sections 17 (migration plan), 16 (packaging), 13.2 (pre-commit hooks), 13.3 (what gets deleted).

**Rollback window:** Through M5 trivial (stop coding-bot, ctask still running). Through ~30 days post-M6 (re-arm ctask from archive, revert pre-commit flips). After ~30 days, cost.db history makes rollback lossy.

---

## File changes after Plan 5

```
M5 (no code changes — installs + runtime verification):
  ~/.local/bin/coding-bot       # vscode user
  ~claude-bot/.local/bin/coding-bot  # claude-bot user
  /srv/coding-bot/state.db      # created
  /srv/coding-bot/cost.db       # created

M6 (deletions + updates):
  scripts/ — delete ~35 files (see Task F.3 for exact list)
  pd-*/  .pre-commit-config.yaml — hook entries updated (8 repos)
  pd-*/  CLAUDE.md — Commands section updated (8 repos + workspace)
```

---

## Phase A — Pre-flight verification (before any M5 work)

### Task A.1: Verify M4 acceptance criteria

- [ ] **Step 1: Run M4 acceptance checks**

```bash
cd /workspaces/ocr-container/coding-bot
make ci AI=1
git log --oneline | head -5  # should show v0.4-m4 tag
uv run coding-bot --help
uv run coding-bot doctor
```

Expected:
- `make ci AI=1` → `✅ ci passed`
- `git log` shows `v0.4-m4` tag
- `coding-bot --help` lists all sub-apps (spec, label, conventions, triage, wip-pr, hook, budget, agents, setup, scheduler, schedule, status, ps, history, inspect, cost, audit, pause, resume, kill, doctor, db)
- `coding-bot doctor` shows which checks pass/fail (expected: binaries ok; /srv/coding-bot may not exist yet — that's fine)

If any acceptance check fails, fix M4 before proceeding.

- [ ] **Step 2: Verify ctask is still running normally**

```bash
ctask list
```

Expected: ctask lists its current schedule entries without error. This confirms the baseline before parallel run.

---

## Phase B — One-time system setup

### Task B.1: Create /srv/coding-bot with correct ownership

Run as root (or sudo):

- [ ] **Step 1: Create directory + set ownership**

```bash
sudo groupadd -f coding-bot
sudo usermod -aG coding-bot vscode
sudo usermod -aG coding-bot claude-bot
sudo mkdir -p /srv/coding-bot/locks /srv/coding-bot/backend-runs /srv/coding-bot/logs/scheduler /srv/coding-bot/backups /srv/coding-bot/tmp
sudo chown -R root:coding-bot /srv/coding-bot
sudo chmod -R 2770 /srv/coding-bot
```

- [ ] **Step 2: Verify**

```bash
ls -la /srv/coding-bot
stat -c "%G %a" /srv/coding-bot
```

Expected: group `coding-bot`, mode `2770`.

- [ ] **Step 3: Run coding-bot setup to confirm**

```bash
uv run coding-bot setup
```

Expected: all checks green.

---

## Phase C — Install coding-bot for both users

### Task C.1: Install for vscode user

- [ ] **Step 1: Install editable**

```bash
cd /workspaces/ocr-container/coding-bot
uv sync
uv tool install --editable /workspaces/ocr-container/coding-bot
```

- [ ] **Step 2: Verify**

```bash
coding-bot --version
which coding-bot
```

Expected: `coding-bot 0.1.0` (or current version), path in `~vscode/.local/bin/`.

### Task C.2: Install for claude-bot user

- [ ] **Step 1: Install as claude-bot**

```bash
sudo -u claude-bot bash -lc \
    'uv tool install --editable /workspaces/ocr-container/coding-bot'
```

- [ ] **Step 2: Verify**

```bash
sudo -u claude-bot bash -lc 'coding-bot --version'
```

Expected: version printed without error.

---

## Phase D — Initialize databases and create config

### Task D.1: Run Alembic migrations and create keys.toml

- [ ] **Step 1: Run DB upgrade**

```bash
cd /workspaces/ocr-container/coding-bot
coding-bot db upgrade
```

Expected: `✓ both DBs at head`. Creates `/srv/coding-bot/state.db` and `/srv/coding-bot/cost.db`.

- [ ] **Step 2: Create keys.toml for vscode**

```bash
mkdir -p ~/.config/coding-bot
chmod 700 ~/.config/coding-bot
cat > ~/.config/coding-bot/keys.toml << 'EOF'
[profiles.bot-claude]
backend = "claude"
api_key = ""  # leave empty; claude CLI uses its own auth
plan = "claude-api-200"
EOF
chmod 600 ~/.config/coding-bot/keys.toml
```

Note: The API key field can be blank for v0.1 — the `claude` CLI manages its own credentials. The plan name is used for cost attribution only.

- [ ] **Step 3: Create pricing.toml for vscode**

```bash
cat > ~/.config/coding-bot/pricing.toml << 'EOF'
[claude.haiku]
input_per_mtok = 0.80
output_per_mtok = 4.00
cache_write_per_mtok = 1.00
cache_read_per_mtok = 0.08

[claude.sonnet]
input_per_mtok = 3.00
output_per_mtok = 15.00
cache_write_per_mtok = 3.75
cache_read_per_mtok = 0.30

[claude.opus]
input_per_mtok = 15.00
output_per_mtok = 75.00
cache_write_per_mtok = 18.75
cache_read_per_mtok = 1.50
EOF
chmod 600 ~/.config/coding-bot/pricing.toml
```

- [ ] **Step 4: Create config for claude-bot user**

```bash
sudo -u claude-bot bash -lc 'mkdir -p ~/.config/coding-bot && chmod 700 ~/.config/coding-bot'
sudo -u claude-bot bash -lc 'cp ~/.config/coding-bot/keys.toml ~/.config/coding-bot/keys.toml' 2>/dev/null || \
    sudo cp ~/.config/coding-bot/keys.toml ~claude-bot/.config/coding-bot/keys.toml
sudo -u claude-bot bash -lc 'chmod 600 ~/.config/coding-bot/keys.toml'
sudo cp ~/.config/coding-bot/pricing.toml ~claude-bot/.config/coding-bot/pricing.toml
sudo -u claude-bot bash -lc 'chmod 600 ~/.config/coding-bot/pricing.toml'
```

- [ ] **Step 5: Run doctor for both users**

```bash
coding-bot doctor
sudo -u claude-bot bash -lc 'coding-bot doctor'
```

Expected: all checks green (or only non-critical warnings like "APScheduler not running").

---

## Phase E — Mirror ctask schedules + run parallel

### Task E.1: Import ctask history and create matching schedule entries

- [ ] **Step 1: Dry-run import**

```bash
coding-bot db import-ctask --dry-run
```

Expected: prints count of schedule entries + cost rows that would be imported. Review the output and confirm it looks correct.

- [ ] **Step 2: Run import**

```bash
coding-bot db import-ctask
```

Expected:
- Schedule entries created in `state.db`
- Cost history rows imported into `cost.db`
- ctask dir renamed to `~/.local/share/claude-tasks-archived-YYYY-MM-DD/`

**IMPORTANT:** After this step, ctask's original tasks.json is gone. ctask is now read-only (archive). Do NOT run `ctask` to add new tasks after this point.

- [ ] **Step 3: Verify imported schedule entries**

```bash
coding-bot schedule list
```

Expected: lists the imported entries that mirror what ctask had.

- [ ] **Step 4: Add any missing schedule entries manually**

Compare ctask's archived tasks with `coding-bot schedule list`. For any missing entries, add them:

```bash
# Example: ship-issue on pdomain-book-tools every 30 minutes
coding-bot schedule add ship-issue-pdomain-book-tools \
    --workflow ship-issue \
    --trigger "interval:minutes=30" \
    --context "repo=pdomain/pdomain-book-tools,slot=2"
```

Repeat for each repo/workflow combination that was in ctask.

### Task E.2: Start the scheduler and run in parallel

- [ ] **Step 1: Ensure bot worktrees exist**

For each repo+workflow that coding-bot will run, bootstrap the worktree:

```bash
coding-bot bot-workspace bootstrap ship-issue pdomain/pdomain-book-tools --slot 2
coding-bot bot-workspace bootstrap ship-issue pdomain/pdomain-ocr-labeler-spa --slot 0
# ... repeat for each repo in the schedule
```

- [ ] **Step 2: Start the coding-bot scheduler**

```bash
coding-bot scheduler start
```

Expected: `Scheduler started in tmux session 'coding-bot-scheduler'`.

- [ ] **Step 3: Verify scheduler is running**

```bash
coding-bot scheduler status
```

Expected: `✓ Scheduler is running (tmux:coding-bot-scheduler)`.

- [ ] **Step 4: Watch for first fire events**

```bash
coding-bot status --watch
```

After the first interval fires (within 30 minutes for a `interval:minutes=30` job), you should see a run appear in `coding-bot status`.

- [ ] **Step 5: Run parallel for 48–72 hours**

During this window:
- Both ctask (via archived data) and coding-bot scheduler are conceptually running, but since ctask's tasks.json was archived in Step E.1.2, only coding-bot fires new jobs.
- Monitor daily with:

```bash
coding-bot status
coding-bot history --limit 20
coding-bot cost --since 2d
```

Watch for:
- `terminal_state=shipped` runs → bot successfully shipped issues
- `terminal_state=bounced` runs → expected; escalation logic working
- `is_error=True` runs → investigate with `coding-bot inspect <run-id> --events`
- Cost rows matching expected token usage

- [ ] **Step 6: Verify parity gate**

Before proceeding to M6, answer yes to all:

```
[ ] At least 3 successful ship-issue runs completed (terminal_state=shipped)
[ ] cost.db rows have non-zero input_tokens
[ ] coding-bot doctor exits 0
[ ] No unexplained is_error=True runs in the last 24h
[ ] coding-bot history shows expected run frequency (roughly matching old ctask intervals)
```

If any gate fails, investigate and fix before M6. The M5 parallel run is the safety net.

---

## Phase F — Cutover (M6)

**Warning:** M6 is irreversible within this session. The 30-day rollback window (re-arm ctask from archive) still applies, but the workspace CLAUDE.md and script deletions are permanent changes that other users and agents will see immediately.

### Task F.1: Stop the old ctask daemon (if still running)

- [ ] **Step 1: Check if ctask tmux session is live**

```bash
tmux list-sessions 2>/dev/null | grep -i ctask || echo "(no ctask session found)"
```

- [ ] **Step 2: Kill ctask session if found**

```bash
tmux kill-session -t ctask 2>/dev/null || true
```

- [ ] **Step 3: Confirm ctask is not running**

```bash
ctask status 2>/dev/null || echo "ctask not running (expected)"
```

---

### Task F.2: Update pre-commit configs in all pd-* repos

Each pd-* repo's `.pre-commit-config.yaml` has hooks pointing to bash scripts. Replace them with `coding-bot hook` entries.

- [ ] **Step 1: Show current hook entries**

```bash
for repo in pdomain-book-tools pdomain-ocr-cli pd-ocr-labeler pdomain-ocr-labeler-spa pdomain-ocr-synth pd-ocr-trainer pd-png-optimizer pdomain-prep-for-pgdp; do
    echo "=== $repo ==="
    grep -A3 "entry:" /workspaces/ocr-container/$repo/.pre-commit-config.yaml 2>/dev/null || echo "(no pre-commit config)"
done
```

- [ ] **Step 2: Replace hook entries in each repo's `.pre-commit-config.yaml`**

For each repo that has a `no-trailing-todos.sh` entry, replace it with `coding-bot hook trailing-todos`. Example replacement (adapt per repo's actual config):

```yaml
# OLD:
- id: trailing-todos
  entry: bash scripts/no-trailing-todos.sh
  language: system
  types: [text]

# NEW:
- id: trailing-todos
  entry: coding-bot hook trailing-todos
  language: system
  types: [text]
```

Repeat for `spec-lint`, `conventions-lint`, `issue-labels-lint` hooks if present.

Run this for each repo:

```bash
REPO=pdomain-book-tools  # change per repo
CONFIG=/workspaces/ocr-container/$REPO/.pre-commit-config.yaml
if [[ -f "$CONFIG" ]]; then
    sed -i 's|bash scripts/no-trailing-todos.sh|coding-bot hook trailing-todos|g' "$CONFIG"
    sed -i 's|uv run python scripts/lint-spec.py|coding-bot hook spec-lint|g' "$CONFIG"
    sed -i 's|uv run python scripts/lint-conventions.py|coding-bot hook conventions-lint|g' "$CONFIG"
    sed -i 's|uv run python scripts/lint-issue-labels.py|coding-bot hook issue-labels-lint --repo|g' "$CONFIG"
    echo "Updated $REPO/.pre-commit-config.yaml"
fi
```

- [ ] **Step 3: Commit pre-commit updates in each repo**

For each repo with changes:

```bash
cd /workspaces/ocr-container/pdomain-book-tools
git add .pre-commit-config.yaml
git commit -m "chore(hooks): switch to coding-bot hook entry points"
```

Repeat for all 8 repos. **Do not push yet** — push after verifying pre-commit works locally.

- [ ] **Step 4: Verify pre-commit works in one repo**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
pre-commit run trailing-todos --all-files
```

Expected: exits 0 (no violations) or lists actual violations (not ImportError / "not found").

---

### Task F.3: Delete migrated scripts from workspace `scripts/`

These scripts are now replaced by `coding-bot` subcommands. Delete them.

- [ ] **Step 1: Show the files to be deleted**

```bash
ls /workspaces/ocr-container/scripts/ | grep -E \
    "ship-issue|style-review|style-sweep|decompose-spec|lint-spec|lint-issue-labels|lint-conventions|arm-issue|seed-labels|triage-|auto-merge-wip-prs|pr-wip-status|merge-wip-ship-issue|bot-workspace-bootstrap|verify-protections|no-trailing-todos|spec-from-issue-finalize|build-spec-chain-report|build-spec-index|spec_chain_data|spec_slug|extract-conventions|sync-conventions|check-sync-drift|check-sibling-drift"
```

Review this list. Verify each file has been ported before deleting.

- [ ] **Step 2: Delete the migrated scripts**

```bash
cd /workspaces/ocr-container
git rm -f \
    scripts/ship-issue-orchestrator.sh \
    scripts/ship-issue-preflight.sh \
    scripts/ship-issue-success.sh \
    scripts/ship-issue-failure.sh \
    scripts/ship-issue-escalate.sh \
    scripts/ship-issue-throttle-check.sh \
    scripts/ship-issue-pick.py \
    scripts/ship-issue-file-broken-ci.py \
    scripts/ship-issue-triage-ci-failure.py \
    scripts/ship-issue-cleanup-bounced.py \
    scripts/style-review-orchestrator.sh \
    scripts/style-review-detect.py \
    scripts/style-review-apply.py \
    scripts/style-sweep-orchestrator.sh \
    scripts/decompose-spec-auto-orchestrator.sh \
    scripts/decompose-spec-plan.py \
    scripts/decompose-spec-apply.py \
    scripts/lint-spec.py \
    scripts/lint-issue-labels.py \
    scripts/lint-conventions.py \
    scripts/arm-issue.py \
    scripts/seed-labels.sh \
    scripts/triage-sweep.py \
    scripts/triage-fork.py \
    scripts/auto-merge-wip-prs.sh \
    scripts/pr-wip-status.sh \
    scripts/merge-wip-ship-issue-pr.sh \
    scripts/bot-workspace-bootstrap.sh \
    scripts/verify-protections.sh \
    scripts/no-trailing-todos.sh \
    scripts/spec-from-issue-finalize.py \
    scripts/build-spec-chain-report.py \
    scripts/build-spec-index.py \
    scripts/spec_chain_data.py \
    scripts/spec_slug.py \
    scripts/extract-conventions.py \
    scripts/sync-conventions.py \
    scripts/check-sync-drift.py \
    scripts/check-sibling-drift.py \
    2>/dev/null || echo "(some files already gone — that's fine)"
```

Also move (don't delete) `scripts/build-cost-dashboard.py` — it belongs in a future `cost-dashboard/` sibling repo:

```bash
mkdir -p /workspaces/ocr-container/cost-dashboard
mv /workspaces/ocr-container/scripts/build-cost-dashboard.py \
   /workspaces/ocr-container/cost-dashboard/
git add /workspaces/ocr-container/cost-dashboard/
```

Files to **keep** (not in scope):
- `scripts/statusline-with-ratelimits.sh`
- `scripts/export-models.sh`
- `scripts/upload-models.sh`
- `scripts/patch-brainstorming-skill.sh`
- `scripts/tooling-change-guard.sh`
- `scripts/check-ci-failures.sh` (replaced by `coding-bot ci check` but not deleted until confirmed working)
- `scripts/migrate-legacy-spec-auto.py`, `scripts/eval-spec-model.py`, `scripts/file-legacy-migration-issues.py`, `scripts/migrate-claude-ok-to-bot-label.sh` (one-shot migration scripts; archive separately if desired)
- `scripts/ocr_to_txt.py` (OCR utility, not a bot script)

- [ ] **Step 3: Commit script deletions**

```bash
cd /workspaces/ocr-container
git add -u scripts/
git add cost-dashboard/
git commit -m "chore(cutover): delete migrated scripts, move cost-dashboard"
```

---

### Task F.4: Update CLAUDE.md in workspace and all pd-* repos

Each repo's CLAUDE.md has a "Commands" or "CI" section that references the old scripts. Update to reference `coding-bot` instead.

- [ ] **Step 1: Update workspace CLAUDE.md**

Find the section in `/workspaces/ocr-container/CLAUDE.md` that references scripts. Add a note:

```bash
# Check what the workspace CLAUDE.md says about bot scripts
grep -n "ship-issue\|scripts/\|ctask\|coding-bot" /workspaces/ocr-container/CLAUDE.md | head -20
```

Edit `/workspaces/ocr-container/CLAUDE.md` to replace references to `scripts/ship-issue-orchestrator.sh`, `ctask`, and related commands with their `coding-bot` equivalents:

| Old | New |
|-----|-----|
| `ctask list` | `coding-bot schedule list` |
| `ctask add ...` | `coding-bot schedule add ...` |
| `bash scripts/ship-issue-orchestrator.sh` | `coding-bot ship-issue run` |
| `bash scripts/auto-merge-wip-prs.sh` | `coding-bot wip-pr auto-merge` |
| `python3 scripts/lint-spec.py` | `coding-bot spec lint` |
| `python3 scripts/triage-sweep.py` | `coding-bot triage sweep` |
| `python3 scripts/arm-issue.py` | `coding-bot label arm` |
| `bash scripts/no-trailing-todos.sh` | `coding-bot hook trailing-todos` |

- [ ] **Step 2: Update each pd-* repo's CLAUDE.md Commands section**

Each pd-* CLAUDE.md has a "## Commands" section with `make ci`. These don't reference bot scripts directly, so usually no change is needed. Check for any stale script references:

```bash
for repo in pdomain-book-tools pdomain-ocr-cli pd-ocr-labeler pdomain-ocr-labeler-spa pdomain-ocr-synth pd-ocr-trainer pd-png-optimizer pdomain-prep-for-pgdp; do
    echo "=== $repo ==="
    grep -n "scripts/\|ctask\|bot-workspace-bootstrap\|no-trailing-todos" \
        /workspaces/ocr-container/$repo/CLAUDE.md 2>/dev/null | head -5 || echo "(clean)"
done
```

For any repo with matches, edit the CLAUDE.md to replace with `coding-bot X` equivalents, then commit:

```bash
cd /workspaces/ocr-container/$REPO
git add CLAUDE.md
git commit -m "chore(docs): update CLAUDE.md to reference coding-bot"
```

- [ ] **Step 3: Commit workspace CLAUDE.md**

```bash
cd /workspaces/ocr-container
git add CLAUDE.md
git commit -m "chore(cutover): update workspace CLAUDE.md to reference coding-bot"
```

---

### Task F.5: Update coding-bot CLAUDE.md and CONVENTIONS.md

Now that the bot is live, update its own docs to reflect the operational state.

- [ ] **Step 1: Check coding-bot's CLAUDE.md for any stale TODOs**

```bash
grep -n "TODO\|FIXME\|M4\|M5\|M6\|ctask\|parallel run" \
    /workspaces/ocr-container/coding-bot/CLAUDE.md 2>/dev/null | head -20
```

- [ ] **Step 2: Update version in pyproject.toml to 0.1.0-stable**

```bash
grep "^version" /workspaces/ocr-container/coding-bot/pyproject.toml
```

If still at `0.1.0`, that's fine for now. The spec says v0.1 ships after M6.

- [ ] **Step 3: Commit any CLAUDE.md updates in coding-bot**

```bash
cd /workspaces/ocr-container/coding-bot
git add CLAUDE.md pyproject.toml
git commit -m "docs(coding-bot): mark M6 cutover complete, update operational notes"
```

---

### Task F.6: Final verification

- [ ] **Step 1: Run `coding-bot doctor` as both users**

```bash
coding-bot doctor
sudo -u claude-bot bash -lc 'coding-bot doctor'
```

Expected: all checks green.

- [ ] **Step 2: Verify scheduler still running after cutover steps**

```bash
coding-bot scheduler status
```

- [ ] **Step 3: Run `make ci` in one pd-* repo to verify pre-commit hooks work**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
make ci AI=1
```

Expected: `✅ ci passed`. The pre-commit hooks now call `coding-bot hook trailing-todos` etc.

- [ ] **Step 4: Tag coding-bot v0.1.0**

```bash
cd /workspaces/ocr-container/coding-bot
git tag v0.1.0
```

- [ ] **Step 5: Confirm ctask is archived and not running**

```bash
ls ~/.local/share/claude-tasks-archived-* 2>/dev/null && echo "archived" || echo "no archive (check import-ctask ran)"
tmux list-sessions 2>/dev/null | grep ctask || echo "(ctask not running — correct)"
```

---

## Acceptance criteria

1. `coding-bot doctor` exits 0 on both vscode and claude-bot users.
2. `/srv/coding-bot/state.db` and `/srv/coding-bot/cost.db` exist and are at Alembic head.
3. `coding-bot schedule list` shows the migrated schedule entries.
4. `coding-bot scheduler status` shows scheduler running in tmux.
5. `coding-bot history --limit 10` shows at least 3 completed runs from the parallel-run period.
6. `coding-bot cost --since 4d` shows cost rows with non-zero tokens.
7. Pre-commit hooks in at least one pd-* repo call `coding-bot hook trailing-todos` (not the old bash script).
8. All migrated scripts listed in Task F.3 are gone from `scripts/`.
9. `ctask` is archived, not running.
10. Tag `v0.1.0` exists on the coding-bot repo.
11. `make ci AI=1` passes in both the coding-bot repo and at least one pd-* repo.

---

## Rollback procedure (if needed within 30 days)

```bash
# 1. Stop coding-bot scheduler
coding-bot scheduler stop

# 2. Restore ctask archive
mv ~/.local/share/claude-tasks-archived-YYYY-MM-DD ~/.local/share/claude-tasks

# 3. Re-arm ctask (if ctask binary is still installed)
ctask list  # verify tasks restored

# 4. Revert pre-commit config changes in each pd-* repo
#    (restore from git history — `git show HEAD~1:.pre-commit-config.yaml > .pre-commit-config.yaml`)

# 5. The deleted scripts are gone from the workspace scripts/ directory.
#    Restore from git: git checkout <cutover-commit>~1 -- scripts/
```

Cost data in `/srv/coding-bot/cost.db` is NOT rolled back — it's kept as history.
