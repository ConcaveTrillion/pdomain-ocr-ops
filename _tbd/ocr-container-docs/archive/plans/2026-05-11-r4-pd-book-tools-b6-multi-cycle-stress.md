---
status: complete
---

# R4 — pdomain-book-tools B6 Multi-Cycle Ship-Issue Stress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Plan-B Phase B6 (multi-cycle stress) and B7 (final pilot debrief) by running 3 ship-issue cycles on pdomain-book-tools across a mix of issue kinds. Catches any regressions introduced by post-Session-2 `[pilot-feedback]` commits + post-workspace-rc infrastructure changes (especially the worktree retrofit from R0/v2 Plan 1).

**Architecture:** This is an operational plan — no new code. Pick 3 eligible pdomain-book-tools issues (mix of `kind:chore` / `kind:bug` / `kind:feature`), arm them with `bot:ship-issue-ready` + `status:ready`, run the orchestrator three times (one per issue, or `--runs 3` for batched), triage each outcome (success → merge or amend PR; bounce → file pilot-feedback issue), update STATUS.md and the Plan-B debrief with final results.

**Tech Stack:** `scripts/ship-issue-orchestrator.sh`, `scripts/ship-issue-pick.py`, `scripts/ship-issue-success.sh`, `scripts/ship-issue-failure.sh`, `gh` CLI, claude-bot user.

**Source plans:**
- `docs/superpowers/plans/2026-05-10-pilot-pdomain-book-tools.md` (Phase B6 + B7)
- `docs/superpowers/plans/2026-05-10-pilot-pdomain-book-tools-debrief.md` (Session 1 + 2 debrief)
- `docs/superpowers/plans/2026-05-11-INDEX.md`

**Depends on:** R1 (worktree retrofit + workspace canonical landed; not strictly blocking but cleanest baseline).

**Out of scope:**
- Rollout to other repos (R3a / R3b).
- Any architectural changes to ship-issue machinery (those would be a separate `[pilot-feedback]` PR if R4 surfaces them).

---

## Background context for the engineer

Plan B Session 2 closed all 20 pilot-feedback findings; one TDD slice shipped end-to-end (issue #11 → PR #15 → merged). The debrief left two open questions for B6:

1. **How many runs to declare confidence?** Original Plan B said 5; debrief revised to 3-4. R4 picks **3** as the right number — enough to span chore/bug/feature, lightweight enough to bail early if something regresses.
2. **Mixed kinds vs all chores?** Mixed — the bot has only proven on a chore so far.

### Issue selection

Three candidates by kind (verify state first; replace if any has changed status):

| Kind | Candidate issue | Why chosen |
|---|---|---|
| `kind:chore` | #8, #9, or #10 (TEST_COVERAGE chores) | Already `bot:ship-issue-ready`; smallest scope; proven path |
| `kind:bug` | the (post-pilot) flaky-test issue if any new one filed, OR #7 if status:blocked has been cleared | Exercises bug path with code change beyond test-add |
| `kind:feature` | #2-#6 (any of the original ROADMAP migrations) | First feature-kind through the bot |

If no `kind:bug` is bot-ready, drop to 2 chores + 1 feature.

### Operational flow

```
claude-bot user
  └── scripts/ship-issue-orchestrator.sh --repo pdomain/pdomain-book-tools --runs 3
       │
       ├── per cycle:
       │    ├── throttle-check (skip if <X days since last run)
       │    ├── pick.py (claim 1 issue with status:ready + bot:ship-issue-ready)
       │    ├── claude -p (haiku, low effort) executes the slice
       │    │     └── claim issue → write tests → implement → commit
       │    ├── success.sh (make ci → push → open/update draft PR)
       │    │     OR
       │    │    failure.sh (reset wip/ship-issue → bounce comment on issue)
       │    └── orchestrator exits 0 if any succeeded, nonzero if all failed
```

### Worktree retrofit consequence

Per R1 / v2 Plan 1, the orchestrator now runs *inside* `/srv/bot-workspaces/ship-issue/pdomain-book-tools/` (claude-bot's worktree), not in CT's `/workspaces/ocr-container/pdomain-book-tools/`. The branch (`wip/ship-issue`) is borrowed via `git checkout` inside a flock window, and released via `git checkout --detach HEAD` after. R4 validates that pattern works under load.

### What "success" looks like for R4

- 3 cycles attempted.
- ≥2 cycles produce a clean draft PR that CT can review (CI green; commits attributable; PR description sane).
- 0 cycles leave the workspace in a broken state (no stuck flock, no orphan branches, no claude-bot processes hanging).
- Any failures produce a clean bounce comment on the issue + reset wip/ship-issue.

A "1 success + 2 bounces" outcome is acceptable IF the bounces are due to test infrastructure issues (like pdomain-book-tools flaky tests) and not orchestrator/skill regressions.

---

## File structure

**No code files created.** R4 produces:

- 3 draft PRs on pdomain-book-tools (one per successful cycle).
- 1+ bot comments on each cycled issue.
- STATUS.md update (R4 outcome).
- Debrief update (`2026-05-10-pilot-pdomain-book-tools-debrief.md` — append a "B6 multi-cycle stress" section).
- Possibly N pilot-feedback issues if anything regresses.

---

## Tasks

### Task 1: Pre-flight — verify orchestrator + bot state

**Files:** none (verification only)

- [ ] **Step 1: Confirm 3 ship-ready issues exist on pdomain-book-tools**

```bash
gh issue list -R pdomain/pdomain-book-tools \
  --label "bot:ship-issue-ready,status:ready" \
  --state open --json number,title,labels,milestone \
  --jq '.[] | "\(.number)\t\(.title)\t\([.labels[].name]|join(\",\"))"'
```

Expected: ≥3 issues. If <3, arm more via:

```bash
gh issue edit <N> -R pdomain/pdomain-book-tools --add-label "bot:ship-issue-ready,status:ready"
```

Aim for a mix: 1 chore, 1 bug-or-feature, 1 chore-or-feature. Capture the 3 numbers as `$N1 $N2 $N3`.

- [ ] **Step 2: Confirm bot worktree is clean**

```bash
sudo -u claude-bot bash -c '
  cd /srv/bot-workspaces/ship-issue/pdomain-book-tools 2>/dev/null || exit 1
  git status --short
  git branch --show-current
'
```

Expected: working tree clean (no modified/untracked files); branch is `wip/ship-issue` or `HEAD` (detached). If dirty, reset:

```bash
sudo -u claude-bot bash -c '
  cd /srv/bot-workspaces/ship-issue/pdomain-book-tools
  git reset --hard origin/main
  git checkout --detach HEAD
'
```

- [ ] **Step 3: Confirm bots are not paused**

```bash
ls /srv/bot-workspaces/.state/bots-paused 2>&1
```

Expected: "No such file or directory". If present, remove it:

```bash
sudo -u claude-bot rm /srv/bot-workspaces/.state/bots-paused
```

- [ ] **Step 4: Confirm no stale flocks**

```bash
ls -la /srv/bot-workspaces/.locks/
```

Expected: lock files exist but none currently held (orchestrator uses non-blocking flock). If `lsof` reports any process holding the lock, identify + decide whether to wait or terminate.

- [ ] **Step 5: Commit point (no commit)**

### Task 2: Run cycle 1 (smallest scope — chore)

**Files:** GitHub state + bot worktree

- [ ] **Step 1: Pick the smallest chore from $N1 $N2 $N3**

If unsure which is smallest, view bodies:

```bash
gh issue view $N1 -R pdomain/pdomain-book-tools --json title,body --jq '.title + "\n" + .body' | head -30
```

- [ ] **Step 2: Run orchestrator for 1 cycle**

```bash
sudo -u claude-bot bash -c '
  source /run/secrets/load-gh-token-pd  # or however the PAT is loaded
  /workspaces/ocr-container/scripts/ship-issue-orchestrator.sh \
    --repo pdomain/pdomain-book-tools \
    --runs 1
' 2>&1 | tee /tmp/r4-cycle1.log
echo "Exit: $?"
```

Expected: exit 0 if at least 1 cycle succeeded; nonzero if all failed. Watch for:
- "claim issue #N" — orchestrator picked something
- "running claude -p" — slice work in progress (~3-10 min)
- "success.sh: make ci passed" — slice clean
- "draft PR opened" or "draft PR updated" — PR visible

- [ ] **Step 3: Verify outcome**

```bash
# Was a PR opened/updated?
gh pr list -R pdomain/pdomain-book-tools --head wip/ship-issue --state open --json number,title,headRefOid --jq '.[] | "PR#\(.number)\t\(.headRefOid[0:8])\t\(.title)"'
# Did the issue close, or did it get a bounce comment?
gh issue view $PICKED_NUM -R pdomain/pdomain-book-tools --json state,comments --jq '.state + " comments:" + (.comments | length | tostring)'
```

Record outcome in `/tmp/r4-state.json`:

```bash
python3 - <<EOF
import json
state = {"cycles": [], "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
state["cycles"].append({"n": 1, "issue": $PICKED_NUM, "outcome": "success|bounce|orchestrator-error", "pr": "PR#... or null"})
json.dump(state, open("/tmp/r4-state.json", "w"), indent=2)
EOF
```

- [ ] **Step 4: Commit point (no commit; orchestrator commits in-repo)**

### Task 3: Run cycle 2 (different kind)

**Files:** GitHub state

- [ ] **Step 1: Run orchestrator for the second cycle**

Same command as Task 2 Step 2. Orchestrator picks the next-eligible issue (oldest first, or per pick.py ordering).

- [ ] **Step 2: Verify outcome + record**

Same as Task 2 Step 3. Append to `/tmp/r4-state.json`.

### Task 4: Run cycle 3 (third kind)

Same as Task 3, third iteration.

### Task 5: Triage outcomes

**Files:** GitHub state

- [ ] **Step 1: Summarize cycle outcomes**

```bash
cat /tmp/r4-state.json
```

Expected: 3 cycle entries each with `outcome` field.

- [ ] **Step 2: For each successful cycle, review the produced PR**

CT-only step in practice, but the orchestrator can dry-validate:

```bash
for PR in <list-of-PRs>; do
  gh pr checks $PR -R pdomain/pdomain-book-tools
  gh pr diff $PR -R pdomain/pdomain-book-tools | head -100
done
```

- [ ] **Step 3: For each bounce, decide if it's:**
  - **Infrastructure bounce** (flaky test, network, etc.) — note in STATUS.md; not a pilot-feedback finding.
  - **Orchestrator regression** (something that worked in Session 2 doesn't work now) — file a `[pilot-feedback]` issue on the workspace, fix before declaring R4 done.
  - **Skill / claude-p regression** (the slice itself broke for a reason the bot should have caught) — file `[pilot-feedback]` issue + decide whether to retry.

- [ ] **Step 4: Merge what's clean**

```bash
# For each PR that's reviewed and clean:
gh pr merge $PR -R pdomain/pdomain-book-tools --squash --delete-branch
```

- [ ] **Step 5: Commit point (no commit; merges happen on GitHub)**

### Task 6: Final Plan-B debrief update + STATUS.md

**Files:**
- Modify: `docs/superpowers/plans/2026-05-10-pilot-pdomain-book-tools-debrief.md`
- Modify: `docs/superpowers/plans/STATUS.md`

- [ ] **Step 1: Append "B6 multi-cycle stress" section to the debrief**

```bash
cat >> /workspaces/ocr-container/docs/superpowers/plans/2026-05-10-pilot-pdomain-book-tools-debrief.md <<EOF

## B6 multi-cycle stress (2026-05-11 / R4)

3 cycles run on pdomain-book-tools, mixed kinds:

| Cycle | Issue | Kind | Outcome | PR | Notes |
|---|---|---|---|---|---|
| 1 | #N | chore | success/bounce | PR# | ... |
| 2 | #N | bug/feature | success/bounce | PR# | ... |
| 3 | #N | chore/feature | success/bounce | PR# | ... |

**Results:** S successes + B bounces + E orchestrator errors. (Acceptance threshold: 2 successes + 0 orchestrator regressions.)

**New pilot-feedback findings:** (list of [pilot-feedback] issues filed, if any)

**Worktree retrofit validated:** Yes/No. Bot ran inside /srv/bot-workspaces/ship-issue/pdomain-book-tools/ for all 3 cycles. Flock + detached-HEAD pattern clean.

## B7 final pilot decision

Pilot **declared done** vs **continued** based on B6 outcomes. Per R4 acceptance threshold, this is [DONE / CONTINUE].

If DONE: ship-issue is operationally proven on pdomain-book-tools. Downstream repos (pdomain-ocr-cli, pd-ocr-labeler, pdomain-prep-for-pgdp via R3a/R3b) can adopt the same pattern. No further pilot stress runs needed.

If CONTINUE: file pilot-feedback issues for any regressions found in B6 and plan a B6.5 stress retry.
EOF
```

Fill in actual numbers from `/tmp/r4-state.json`.

- [ ] **Step 2: Append R4 section to STATUS.md**

```bash
cat >> /workspaces/ocr-container/docs/superpowers/plans/STATUS.md <<EOF

## R4 — pdomain-book-tools B6 multi-cycle stress (YYYY-MM-DDTHH:MM:SSZ)

3 cycles complete: S successes + B bounces. Pilot declared [DONE/CONTINUE]. Worktree retrofit validated under load.

See debrief append for full per-cycle table.

Plan B (pdomain-book-tools pilot) now closed.
EOF
```

- [ ] **Step 3: Commit**

```bash
cd /workspaces/ocr-container
git add docs/superpowers/plans/2026-05-10-pilot-pdomain-book-tools-debrief.md docs/superpowers/plans/STATUS.md
git commit -m "$(cat <<'EOF'
chore(pilot): R4 B6 multi-cycle stress outcome + Plan-B closeout

3 cycles run, mixed kinds. Worktree retrofit validated. Plan B
declared [DONE/CONTINUE per actual outcome].

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4: Cleanup**

```bash
rm /tmp/r4-state.json /tmp/r4-cycle*.log
```

---

## Acceptance

R4 is complete when:

- [ ] 3 ship-issue cycles attempted on pdomain-book-tools.
- [ ] ≥2 cycles produced a draft PR (or merged PR if CT moved them through review).
- [ ] No stuck flocks, no orphan branches, no claude-bot process leaks after the runs.
- [ ] All bounces are documented (infrastructure vs regression categorized).
- [ ] Any orchestrator regressions filed as `[pilot-feedback]` issues.
- [ ] Debrief + STATUS.md updated with final outcome.
- [ ] Plan B explicitly declared DONE (or CONTINUE with concrete next step).

## Trade-offs considered

| Decision | Pro | Con |
|---|---|---|
| `--runs 1` × 3 vs `--runs 3` once | Lets us inspect between cycles; debug any one regression cleanly | Slower wall-clock; 3 separate orchestrator startups |
| Mixed kinds vs all chores | Truly validates the skill, not just one path | One unexpected kind-specific bug delays R4 by a session |
| 3 runs (vs Plan-B's original 5) | Faster; debrief said 3-4 was enough | Less statistical confidence; reserve right to add R4.5 if needed |
| Run as claude-bot (vs interactive) | Validates the bot's auth + env minimization (#15-#20 from Session 2) | Slightly slower to dispatch (sudo + secrets) |

## References

- `docs/superpowers/plans/2026-05-10-pilot-pdomain-book-tools.md` (B6 + B7 original spec)
- `docs/superpowers/plans/2026-05-10-pilot-pdomain-book-tools-debrief.md` (S1 + S2 closures; 20 findings)
- `scripts/ship-issue-orchestrator.sh`, `scripts/ship-issue-pick.py`, `scripts/ship-issue-success.sh`, `scripts/ship-issue-failure.sh`
- `/srv/bot-workspaces/README.md` (R1 — bot ownership + worktree gotchas)
