---
status: deferred
---

# R3a — Bot Infrastructure Rollout to 3 Mature Repos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Roll the CONVENTIONS.md + daily review-bot + weekly sweep-bot machinery from pdomain-book-tools to three more mature repos: **pdomain-ocr-cli**, **pd-ocr-labeler**, **pdomain-prep-for-pgdp**. Each repo ends with: a CONVENTIONS.md whose cross-repo block matches the workspace canonical, `bot:style-review-ready` + `bot:style-sweep-ready` labels seeded, a daily ctask entry, a weekly ctask entry, and one recurring weekly-sweep chore issue filed.

**Architecture:** Three independent per-repo workflows dispatched as parallel subagents (one per repo). Each subagent does the same 7 steps (extract conventions, review draft, finalize file, sync from canonical, seed labels, add ctask entries, file weekly chore). The orchestrator (this plan's executor) is responsible for: launching the 3 subagents in parallel, tracking progress in a transient state file, verifying each subagent's acceptance before declaring R3a complete.

**Tech Stack:** `scripts/extract-conventions.py`, `scripts/sync-conventions.py`, `scripts/seed-labels.sh`, `ctask`, `gh` CLI, per-repo agents (`pdomain-ocr-cli`, `pd-ocr-labeler`, `pdomain-prep-for-pgdp`).

**Source plans:**
- `docs/superpowers/plans/2026-05-10-code-review-style-cleanup-plan-4.md` (Phase 7 rollout, scoped down to 3 repos)
- `docs/superpowers/plans/2026-05-10-code-review-style-cleanup-plan-3.md` (Tasks 5, 8 — per-repo ctask + chore)
- `docs/superpowers/plans/2026-05-11-INDEX.md`

**Depends on:** R1 (workspace canonical CONVENTIONS.md exists). Parallel-safe with R2 and R4.

**Out of scope:**
- The other 4 published pd-* repos (pdomain-ocr-labeler-spa, pdomain-ocr-synth, pd-ocr-trainer, pd-png-optimizer) — deferred per CT scope decision.
- Lifecycle drive-through (feature-request → spec → children) on these 3 repos — R3b.
- Multi-week observation periods — manual CT monitoring.

---

## Background context for the engineer

You are running the per-repo rollout for 3 of the 6 remaining pd-* repos. The other 3 (`pdomain-ocr-labeler-spa`, `pdomain-ocr-synth`, `pd-ocr-trainer`) are deferred per CT decision; revisit when these 3 bake. `pd-png-optimizer` is permanently out of scope (Rust core; v2 spec Open Q #4).

### Per-repo subagent prompt template

Each of the 3 repo agents (`pdomain-ocr-cli`, `pd-ocr-labeler`, `pdomain-prep-for-pgdp`) runs this same workflow. The orchestrator dispatches them in parallel.

```
You are completing v2 Plan 4 Phase 7 + v2 Plan 3 Tasks 5/8 for ONE pd-*
repo: <REPO>.

Workspace canonical CONVENTIONS.md lives at
/workspaces/ocr-container/CONVENTIONS.md. The cross-repo block between
<!-- workspace-conventions:start --> and <!-- workspace-conventions:end -->
is what gets mirrored.

Steps (do them in order; report each acceptance check):

1. **Generate convention draft.** Run:
   uv run python scripts/extract-conventions.py --repo <REPO>
   Save the draft output to <REPO>/CONVENTIONS.md.draft for CT review.

2. **Review draft.** Open <REPO>/CONVENTIONS.md.draft and check:
   - Does it open with the workspace marker block (will be overwritten by sync)?
   - Are any repo-specific rules captured below the markers?
   - Anything obviously wrong (hallucinated rule, wrong file paths)?
   If yes to all three (top, middle, no), proceed. If anything looks off,
   STOP and report back to orchestrator.

3. **Finalize.** Rename .draft → CONVENTIONS.md:
   mv <REPO>/CONVENTIONS.md.draft <REPO>/CONVENTIONS.md

4. **Sync cross-repo block.** Run:
   uv run python scripts/sync-conventions.py --target <REPO>
   This overwrites the marker block in <REPO>/CONVENTIONS.md with the
   canonical content from /workspaces/ocr-container/CONVENTIONS.md.
   Then verify:
   uv run python scripts/lint-conventions.py <REPO>/CONVENTIONS.md
   Expected: exit 0.

5. **Seed bot labels.** Run from workspace root:
   ./scripts/seed-labels.sh ConcaveTrillion/<REPO>
   Verify the three new labels exist:
   gh label list -R ConcaveTrillion/<REPO> | grep -E "bot:style-(review|sweep)-ready|recurring:weekly"

6. **Add ctask entries.** Run (workspace root):
   /workspaces/ocr-container/ctask add --name "style-review-<REPO>" \
     --cmd "scripts/style-review-orchestrator.sh ConcaveTrillion/<REPO>" \
     --interval "1d" --user claude-bot
   /workspaces/ocr-container/ctask add --name "style-sweep-<REPO>" \
     --cmd "scripts/style-sweep-orchestrator.sh ConcaveTrillion/<REPO>" \
     --interval "7d" --user claude-bot
   Verify:
   /workspaces/ocr-container/ctask list | grep <REPO>
   Expected: 2 entries.

7. **File recurring weekly-sweep chore.** Run:
   gh issue create -R ConcaveTrillion/<REPO> \
     --title "Recurring: weekly style-sweep on full tree" \
     --label "kind:chore,recurring:weekly,bot:style-sweep-ready,status:ready" \
     --body "## Recurring chore

Weekly style-sweep across the whole tree (vs daily-bot's diff-only review).

## Cadence

Every Monday 04:00 UTC via ctask. See workspace
docs/superpowers/plans/2026-05-10-code-review-style-cleanup-plan-3.md
section 'Weekly style-sweep-bot orchestrator' for the bot's behavior.

## How to pause

touch /srv/bot-workspaces/.state/bots-paused

## Outcome

This issue stays open as a tracking anchor. The bot opens (or updates) a
draft PR each week with style-fix commits."

8. **Commit the convention file.** In <REPO>/:
   git add CONVENTIONS.md
   git commit -m "feat(conventions): add per-repo CONVENTIONS.md with workspace-canonical cross-repo block"
   git push origin HEAD:main (or a chore branch if you prefer PR review;
   CT preference is direct-to-main for the convention seed since the
   sync infrastructure enforces correctness afterwards).

Report back the issue number (step 7), the two ctask entry names (step 6),
and any anomalies in steps 1-4 review.
```

### Subagent dispatch pattern (workspace-rc lesson)

Workspace-rc found that 3+ parallel subagents are hard to track without an explicit state file. The orchestrator should:

1. Write `/tmp/r3a-state.json` with `{"started_at": ..., "agents": {"pdomain-ocr-cli": "running", "pd-ocr-labeler": "running", "pdomain-prep-for-pgdp": "running"}}` before dispatch.
2. Dispatch 3 Agent calls in **one tool-call block** (parallel).
3. As each returns, update its state in `/tmp/r3a-state.json` to `"complete"` or `"failed"`.
4. After all 3 return, validate each repo's acceptance via the orchestrator (Task 5 below).

---

## File structure

**Created per repo (3×):**
- `<repo>/CONVENTIONS.md`

**Modified per repo (3×):**
- GitHub labels (3 added per repo)
- 1 new recurring-weekly chore issue per repo
- 2 new ctask entries per repo

**Workspace state:**
- `/tmp/r3a-state.json` (transient — orchestrator's parallel-dispatch tracking)
- `docs/superpowers/plans/STATUS.md` (R3a outcome appended)

---

## Tasks

### Task 1: Pre-flight — confirm R1 landed

**Files:** none

- [ ] **Step 1: Verify workspace canonical exists**

```bash
ls -la /workspaces/ocr-container/CONVENTIONS.md
uv run python scripts/lint-conventions.py /workspaces/ocr-container/CONVENTIONS.md
```

Expected: file exists; lint exits 0. If missing, STOP — run R1 first.

- [ ] **Step 2: Verify the 3 mature repos exist with current state**

```bash
for r in pdomain-ocr-cli pd-ocr-labeler pdomain-prep-for-pgdp; do
  echo "=== $r ==="
  ls -d /workspaces/ocr-container/$r/.git
  ls /workspaces/ocr-container/$r/CONVENTIONS.md 2>&1
done
```

Expected: each repo has `.git/`. None have `CONVENTIONS.md` yet (file not found — that's correct, R3a creates them).

- [ ] **Step 3: Verify R0 PRs landed (if blocking)**

```bash
for r in pdomain-ocr-cli pd-ocr-labeler pdomain-prep-for-pgdp; do
  gh pr list -R "ConcaveTrillion/$r" --state merged --head chore/lint-first-selectors --json number,mergedAt --jq '.[] | "\(.number)\t\(.mergedAt)"'
done
```

Expected: each repo has 1 merged PR with mergedAt timestamp. If not yet merged, R3a can still proceed (lint-first selectors don't gate CONVENTIONS.md), but the `extract-conventions.py` output may include suggested rules referencing pre-merge ruff state. Note in the per-repo agent's prompt that "lint-first is in-flight."

- [ ] **Step 4: Commit point (no commit)**

### Task 2: Initialize parallel-dispatch state file

**Files:**
- Create: `/tmp/r3a-state.json`

- [ ] **Step 1: Write the state file**

```bash
cat > /tmp/r3a-state.json <<'EOF'
{
  "started_at": "REPLACE_ISO_TIMESTAMP",
  "agents": {
    "pdomain-ocr-cli": "pending",
    "pd-ocr-labeler": "pending",
    "pdomain-prep-for-pgdp": "pending"
  },
  "results": {}
}
EOF
sed -i "s/REPLACE_ISO_TIMESTAMP/$(date -u +%Y-%m-%dT%H:%M:%SZ)/" /tmp/r3a-state.json
cat /tmp/r3a-state.json
```

- [ ] **Step 2: Commit point (no commit — transient)**

### Task 3: Dispatch 3 parallel per-repo subagents

**Files:** GitHub state + per-repo files (handled by subagents)

- [ ] **Step 1: In a single tool-call block, dispatch 3 Agent calls in parallel**

Use the per-repo agent's subagent_type (`pdomain-ocr-cli`, `pd-ocr-labeler`, `pdomain-prep-for-pgdp`). For each, pass the per-repo prompt template above with `<REPO>` substituted. Expected return: each agent reports back the recurring-chore issue number, the 2 ctask entry names, and any anomalies from review.

Mark `pending` → `running` in `/tmp/r3a-state.json` before dispatch.

- [ ] **Step 2: As each agent returns, update /tmp/r3a-state.json**

For each completion:

```bash
python3 - <<EOF
import json, time
path = "/tmp/r3a-state.json"
data = json.load(open(path))
data["agents"]["<REPO>"] = "complete"  # or "failed"
data["results"]["<REPO>"] = {
    "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "chore_issue": "<NUM>",
    "ctask_entries": ["style-review-<REPO>", "style-sweep-<REPO>"],
    "anomalies": "<short string or empty>"
}
json.dump(data, open(path, "w"), indent=2)
EOF
```

- [ ] **Step 3: Commit point (no commit; orchestrator state only)**

### Task 4: Verify each repo's acceptance

**Files:** none (verification only)

- [ ] **Step 1: For each repo, run the 5 acceptance checks**

```bash
for r in pdomain-ocr-cli pd-ocr-labeler pdomain-prep-for-pgdp; do
  echo "=== $r ==="
  # 1. CONVENTIONS.md exists + lints
  ls -la /workspaces/ocr-container/$r/CONVENTIONS.md
  uv run python scripts/lint-conventions.py /workspaces/ocr-container/$r/CONVENTIONS.md
  # 2. Marker block matches canonical (no drift)
  uv run python scripts/check-sync-drift.py --repo $r
  # 3. Three new labels exist
  gh label list -R ConcaveTrillion/$r | grep -E "bot:style-(review|sweep)-ready|recurring:weekly"
  # 4. ctask entries exist
  /workspaces/ocr-container/ctask list | grep -E "style-(review|sweep)-$r"
  # 5. Recurring chore issue filed
  gh issue list -R ConcaveTrillion/$r --label "recurring:weekly,bot:style-sweep-ready" --state open --json number,title --jq '.[] | "\(.number)\t\(.title)"'
done
```

Expected per repo: 5 of 5 checks green.

- [ ] **Step 2: If any check fails, re-dispatch that single repo's agent with the specific failure feedback**

- [ ] **Step 3: Commit point (no commit)**

### Task 5: Smoke-test one daily-bot run on each repo

**Files:** none (operational)

- [ ] **Step 1: Force-run the daily style-review on each of the 3 repos**

```bash
for r in pdomain-ocr-cli pd-ocr-labeler pdomain-prep-for-pgdp; do
  echo "=== $r daily ==="
  sudo -u claude-bot bash -c "/workspaces/ocr-container/scripts/style-review-orchestrator.sh ConcaveTrillion/$r" 2>&1 | tail -20
done
```

Expected per repo: orchestrator either (a) reports "no review window yet — no rolling wip/ship-issue PR" (acceptable on a repo with no active ship-issue cycle), or (b) processes the current PR diff and posts a comment. Exit code 0 in both cases.

If exit code nonzero, check `/srv/bot-workspaces/.locks/style-review-<repo>` for stale flock + inspect the orchestrator's stderr.

- [ ] **Step 2: Commit point (no commit)**

### Task 6: Update STATUS.md

**Files:**
- Modify: `docs/superpowers/plans/STATUS.md`

- [ ] **Step 1: Append**

```bash
cat >> /workspaces/ocr-container/docs/superpowers/plans/STATUS.md <<EOF

## R3a — Bot infra rollout to 3 mature repos (YYYY-MM-DDTHH:MM:SSZ)

Three repos onboarded to daily/weekly style bots:
- **pdomain-ocr-cli** — CONVENTIONS.md committed, labels seeded, ctask entries \`style-review-pdomain-ocr-cli\` (daily) + \`style-sweep-pdomain-ocr-cli\` (weekly); recurring chore #N1.
- **pd-ocr-labeler** — CONVENTIONS.md committed, labels seeded, ctask entries; recurring chore #N2.
- **pdomain-prep-for-pgdp** — CONVENTIONS.md committed, labels seeded, ctask entries; recurring chore #N3.

All 3 daily-bot smoke runs exit 0. sync-conventions verification + check-sync-drift green.

Deferred per CT scope: pdomain-ocr-labeler-spa, pdomain-ocr-synth, pd-ocr-trainer (revisit after R3a + R3b bake).

Ready for R3b (lifecycle drive-through on the same 3 repos).
EOF
```

Replace timestamp + issue numbers from `/tmp/r3a-state.json`.

- [ ] **Step 2: Commit**

```bash
cd /workspaces/ocr-container
git add docs/superpowers/plans/STATUS.md
git commit -m "$(cat <<'EOF'
chore(status): R3a outcome — bot infra rolled to 3 mature repos

CONVENTIONS.md, labels, ctask entries, recurring chores landed for
pdomain-ocr-cli, pd-ocr-labeler, pdomain-prep-for-pgdp. 3 deferred repos
queued for a later wave.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 3: Clean up transient state**

```bash
rm /tmp/r3a-state.json
```

---

## Acceptance

R3a is complete when:

- [ ] Each of 3 repos has `CONVENTIONS.md` with markers and zero drift from canonical (`check-sync-drift.py` exit 0).
- [ ] Each of 3 repos has `bot:style-review-ready`, `bot:style-sweep-ready`, `recurring:weekly` labels.
- [ ] Each of 3 repos has 2 ctask entries (`style-review-<repo>`, `style-sweep-<repo>`).
- [ ] Each of 3 repos has 1 open recurring weekly-sweep chore issue.
- [ ] All 3 daily-bot smoke runs exited 0.
- [ ] STATUS.md updated.

## Trade-offs considered

| Decision | Pro | Con |
|---|---|---|
| 3 parallel subagents vs sequential | Fast (1 session for the wave) | State tracking overhead per workspace-rc lesson |
| 3 mature repos vs all 6 | Cuts risk; CT bandwidth manageable for review | 3 repos remain to onboard later |
| Direct-to-main commit on CONVENTIONS.md (vs PR) | Sync infrastructure enforces correctness post-merge; PR review on a copy-of-canonical is low-signal | Slightly less visibility |
| Force a daily-bot smoke run vs wait for ctask | Validates the orchestrator end-to-end immediately | Burns 3 small Sonnet calls on style-review-detect |

## References

- Workspace canonical: `/workspaces/ocr-container/CONVENTIONS.md` (R1)
- Per-repo agents: `pdomain-ocr-cli`, `pd-ocr-labeler`, `pdomain-prep-for-pgdp` (CLAUDE.md routing)
- Sync infrastructure: `scripts/sync-conventions.py`, `scripts/check-sync-drift.py`
- Orchestrators: `scripts/style-review-orchestrator.sh`, `scripts/style-sweep-orchestrator.sh`
- ctask: `/workspaces/ocr-container/ctask`
