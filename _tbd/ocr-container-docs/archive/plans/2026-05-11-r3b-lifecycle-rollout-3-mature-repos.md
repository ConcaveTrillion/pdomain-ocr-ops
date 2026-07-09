---
status: deferred
---

# R3b — Feature-Request Lifecycle Rollout to 3 Mature Repos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate the `/triage` → `/spec-from-issue` → `/decompose-spec` chain on each of pdomain-ocr-cli, pd-ocr-labeler, pdomain-prep-for-pgdp by driving one feature-request through end-to-end per repo. Confirms the skills work on repos other than the foundation library (pdomain-book-tools, where they were piloted in R2).

**Architecture:** Three independent per-repo workflows dispatched as parallel subagents (one per repo). Each follows the same E2E-smoke pattern from R2 Phase A: pick or file a feature-request, run `/triage`, run `/spec-from-issue` (if approved as spec), run `/decompose-spec`. The deliverable per repo is the same artifact set as R2 produced for pdomain-book-tools: 1 spec file + 1 milestone + ≥1 child issue + 1 draft PR.

**Tech Stack:** The three lifecycle skills + `gh` CLI + per-repo agents.

**Source plans:**
- `docs/superpowers/plans/2026-05-10-feature-request-lifecycle-plan-2.md` (Phase 5 rollout, scoped down to 3 repos)
- `docs/superpowers/plans/2026-05-11-r2-lifecycle-e2e-and-chain-backfill-pdomain-book-tools.md` (Phase A pattern reused)
- `docs/superpowers/plans/2026-05-11-INDEX.md`

**Depends on:**
- R2 (E2E smoke green on pdomain-book-tools — proves skills work).
- R3a (bot labels seeded on these 3 repos, including `bot:ship-issue-ready` on the existing label set; though R3a focuses on style-review labels, the lifecycle labels were rolled in lifecycle Plan-1 Task 8 to all 8 repos and should already be present — verify in Task 1).

**Out of scope:**
- Multi-cycle ship-issue stress per repo — R4 covers it for pdomain-book-tools only; downstream stress is post-rollout.
- The other 4 published pd-* repos.

---

## Background context for the engineer

You are running 3 parallel "smoke test" sweeps — one per mature repo — that exercise the three lifecycle skills on a repo other than pdomain-book-tools. The goal is *evidence the skills work everywhere*, not the production of perfect specs.

### Picking the seed feature-request

Each per-repo agent picks (or files) ONE small feature-request as its smoke seed. Suggested seeds:

| Repo | Suggested seed (file as new kind:feature-request) |
|---|---|
| pdomain-ocr-cli | Add a `--dry-run` flag to `pd-ocr` that prints the per-page plan without writing .txt files. |
| pd-ocr-labeler | Surface keyboard shortcut `?` to open a help overlay listing all bindings. |
| pdomain-prep-for-pgdp | Add a "copy to clipboard" button next to the generated PGDP manifest summary view. |

The agent can also pick an existing un-triaged `kind:feature-request` issue if one happens to be small and self-contained. If filing a synthetic one, label it explicitly as a smoke test in the body so CT can close it post-validation without confusion.

### Same artifact contract as R2 Phase A

After all three skills run on each repo:

1. `kind:feature-request` issue → `triage:approved` + spec-issue child.
2. `kind:spec` issue → `Spec: docs/specs/NN-<slug>.md` line in body.
3. New spec file under `<repo>/docs/specs/NN-<slug>.md`, passes `lint-spec.py`.
4. Draft PR with the spec file as the sole change.
5. Milestone `spec: <slug> (#<spec-issue>)` with ≥1 child issue.

### Parallel-dispatch tracking (workspace-rc lesson)

As in R3a, write `/tmp/r3b-state.json` before dispatch. The shape:

```json
{
  "started_at": "...",
  "agents": {
    "pdomain-ocr-cli": "running",
    "pd-ocr-labeler": "running",
    "pdomain-prep-for-pgdp": "running"
  },
  "results": {}
}
```

Update each agent's slot on return. Cleanup transient file at end.

---

## File structure

**Per repo (3×):**
- `<repo>/docs/specs/NN-<slug>.md` (new spec file)
- 1 draft PR on `<repo>` repo
- 1 new milestone + ≥1 child issue + 1 triaged feature-request + 1 spec issue

**Workspace state:**
- `/tmp/r3b-state.json` (transient)
- `docs/superpowers/plans/STATUS.md` (R3b outcome appended)

---

## Tasks

### Task 1: Pre-flight — confirm lifecycle labels exist on all 3 repos

**Files:** none

- [ ] **Step 1: For each repo, check label state**

```bash
for r in pdomain-ocr-cli pd-ocr-labeler pdomain-prep-for-pgdp; do
  echo "=== $r ==="
  gh label list -R "ConcaveTrillion/$r" | grep -E "kind:feature-request|kind:spec|kind:tracking|triage:approved|triage:rejected|bot:ship-issue-ready" | sort
done
```

Expected per repo: at least 6 labels present (kind:feature-request, kind:spec, kind:tracking, triage:approved, triage:rejected, bot:ship-issue-ready).

If any label missing, run:

```bash
./scripts/seed-labels.sh ConcaveTrillion/$r
```

- [ ] **Step 2: Confirm `docs/specs/` directory exists in each repo, or create it**

```bash
for r in pdomain-ocr-cli pd-ocr-labeler pdomain-prep-for-pgdp; do
  ls -d /workspaces/ocr-container/$r/docs/specs 2>&1
done
```

If any reports "No such file", delegate to that repo's agent to create the dir + initial `_index.md` first (the agent knows the per-repo doc structure).

- [ ] **Step 3: Confirm R2 acceptance landed**

```bash
grep -A5 "## R2 " /workspaces/ocr-container/docs/superpowers/plans/STATUS.md | head -10
```

Expected: R2 summary section exists.

- [ ] **Step 4: Commit point (no commit)**

### Task 2: Initialize parallel-dispatch state file

**Files:**
- Create: `/tmp/r3b-state.json`

- [ ] **Step 1: Write state file**

```bash
cat > /tmp/r3b-state.json <<EOF
{
  "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "agents": {
    "pdomain-ocr-cli": "pending",
    "pd-ocr-labeler": "pending",
    "pdomain-prep-for-pgdp": "pending"
  },
  "results": {}
}
EOF
```

### Task 3: Dispatch 3 parallel per-repo subagents

**Files:** Per-repo GitHub state + spec files (handled by subagents)

- [ ] **Step 1: Dispatch all 3 in a single tool-call block**

Each subagent gets the per-repo prompt template below, with `<REPO>` substituted to its repo name. The prompts are identical except for the suggested seed feature-request.

**Per-repo subagent prompt template:**

```
You are completing v2 lifecycle Plan 2 Phase 5 rollout for ONE pd-* repo: <REPO>.

Drive ONE feature-request through the full /triage → /spec-from-issue →
/decompose-spec chain. Report the final artifact set (feature-request num,
spec-issue num, spec file path, draft PR num, milestone title, child-issue nums).

Suggested seed feature-request for <REPO>:
  "<SEED_DESCRIPTION>"

(Or pick an existing un-triaged kind:feature-request on the repo; check
gh issue list -R ConcaveTrillion/<REPO> --label "kind:feature-request"
--state open --json number,title,labels --jq '.[] | select(.labels |
map(.name) | contains(["triage:approved"]) | not)')

Steps (interleaved with /triage etc; report each acceptance):

1. **File or pick the seed feature-request.** If synthetic, label as smoke
   test in body:
   gh issue create -R ConcaveTrillion/<REPO> \
     --title "<TITLE>" \
     --label "kind:feature-request,status:backlog,effort:S,model:haiku,model-effort:low" \
     --body "<scope> ... (Smoke test for R3b validation of lifecycle skills on <REPO>.)"
   Capture as $FR_NUM.

2. **Run /triage $FR_NUM.** Decide: approve as kind:spec (we want to
   exercise the full chain). Verify: triage:approved label + spec-issue
   child created.
   Capture spec-issue as $SPEC_NUM.

3. **Run /spec-from-issue $SPEC_NUM.** Walk Q&A; produce a small spec.
   Verify: spec file at <REPO>/docs/specs/NN-<slug>.md exists; spec-issue
   body has Spec: line; draft PR open.
   Capture spec path as $SPEC_PATH, draft PR as $PR_NUM.

4. **Run lint-spec.py.** From workspace root:
   uv run python scripts/lint-spec.py <REPO>/$SPEC_PATH
   Expected: exit 0.

5. **Run /decompose-spec <REPO>/$SPEC_PATH.** Verify: milestone created;
   ≥1 child issue filed; bot:ship-issue-ready set on mechanical children.

6. **Verify in chain-state report.** Run:
   uv run python scripts/build-spec-chain-report.py --repo ConcaveTrillion/<REPO>
   Expected output: a row for the new milestone with FR → spec-issue →
   children chain visible.

Report acceptance: $FR_NUM, $SPEC_NUM, $SPEC_PATH, $PR_NUM, milestone title,
list of child-issue numbers, any anomalies.
```

- [ ] **Step 2: Update state file as agents return**

Same pattern as R3a Task 3 Step 2.

### Task 4: Verify each repo's artifact set

**Files:** none (verification only)

- [ ] **Step 1: For each repo, run 5 acceptance checks**

```bash
for r in pdomain-ocr-cli pd-ocr-labeler pdomain-prep-for-pgdp; do
  echo "=== $r ==="
  # Get the latest spec issue
  spec_num=$(gh issue list -R ConcaveTrillion/$r --label "kind:spec" --state open --json number --jq '.[0].number')
  echo "Spec issue: #$spec_num"
  # Body has Spec: line
  gh issue view $spec_num -R ConcaveTrillion/$r --json body --jq '.body' | grep -E "^Spec: docs/specs/"
  # Milestone exists
  gh api repos/ConcaveTrillion/$r/milestones --jq '.[] | select(.title | startswith("spec:")) | "\(.number)\t\(.title)"'
  # Children exist
  gh issue list -R ConcaveTrillion/$r --milestone "$(gh api repos/ConcaveTrillion/$r/milestones --jq '.[] | select(.title | startswith("spec:")) | .title' | head -1)" --json number,title --jq '.[] | "\(.number)\t\(.title)"'
  # Draft PR exists
  gh pr list -R ConcaveTrillion/$r --state open --draft --json number,title --jq '.[] | "\(.number)\t\(.title)"'
done
```

Expected per repo: 5 of 5 acceptance checks visible.

- [ ] **Step 2: If a repo's smoke artifacts are incomplete, re-dispatch that repo's agent with the specific gap**

- [ ] **Step 3: Commit point (no commit)**

### Task 5: Run chain-state report across all 4 onboarded repos

**Files:** transient markdown output

- [ ] **Step 1: Generate workspace-wide chain report**

```bash
cd /workspaces/ocr-container
uv run python scripts/build-spec-chain-report.py --all-repos --out /tmp/r3b-chain-all.md
wc -l /tmp/r3b-chain-all.md
grep -E "^## " /tmp/r3b-chain-all.md
```

Expected: report includes sections for all 4 onboarded repos (pdomain-book-tools + 3 new ones), each with their milestones and chain rows.

- [ ] **Step 2: Verify dashboard panel reflects the same data**

```bash
uv run python scripts/build-cost-dashboard.py
DASH=$(find . -maxdepth 3 -name "cost-dashboard.html" -newer scripts/build-cost-dashboard.py 2>/dev/null | head -1)
grep -c "pdomain-ocr-cli\|pd-ocr-labeler\|pdomain-prep-for-pgdp" "$DASH"
```

Expected: ≥3 matches (one per new repo).

- [ ] **Step 3: Commit point (no commit)**

### Task 6: Update STATUS.md + cleanup

**Files:**
- Modify: `docs/superpowers/plans/STATUS.md`

- [ ] **Step 1: Append**

```bash
cat >> /workspaces/ocr-container/docs/superpowers/plans/STATUS.md <<EOF

## R3b — Lifecycle drive-through on 3 mature repos (YYYY-MM-DDTHH:MM:SSZ)

Each repo passed /triage → /spec-from-issue → /decompose-spec:

| Repo | FR | Spec issue | Spec file | Draft PR | Milestone | Children |
|---|---|---|---|---|---|---|
| pdomain-ocr-cli | #FR1 | #S1 | docs/specs/N-<slug>.md | PR-N1 | spec: <slug> | [list] |
| pd-ocr-labeler | #FR2 | #S2 | docs/specs/N-<slug>.md | PR-N2 | spec: <slug> | [list] |
| pdomain-prep-for-pgdp | #FR3 | #S3 | docs/specs/N-<slug>.md | PR-N3 | spec: <slug> | [list] |

Workspace-wide chain-state report renders cleanly across 4 onboarded repos.

Lifecycle skills are now repo-agnostic; the v2 + lifecycle workflow is complete on the chosen 3-repo subset. Remaining 3 repos (pdomain-ocr-labeler-spa, pdomain-ocr-synth, pd-ocr-trainer) deferred per CT scope.
EOF
```

Replace placeholders.

- [ ] **Step 2: Commit**

```bash
cd /workspaces/ocr-container
git add docs/superpowers/plans/STATUS.md
git commit -m "$(cat <<'EOF'
chore(status): R3b outcome — lifecycle skills validated on 3 mature repos

/triage → /spec-from-issue → /decompose-spec proven repo-agnostic.
Workspace-wide chain-state report covers 4 repos.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 3: Cleanup transient state**

```bash
rm /tmp/r3b-state.json
```

---

## Acceptance

R3b is complete when:

- [ ] Each of 3 repos has the full artifact set (FR issue, spec issue, spec file, draft PR, milestone, ≥1 child issue).
- [ ] Workspace chain-state report shows 4 repos with milestone data.
- [ ] Dashboard panel reflects the same.
- [ ] STATUS.md updated.

## Trade-offs considered

| Decision | Pro | Con |
|---|---|---|
| Synthetic seed feature-requests vs picking existing ones | Predictable scope; clean trace for review | Adds smoke noise (3 specs that may or may not get merged) |
| Run /decompose-spec on the smoke spec | Exercises the full chain | Adds child issues to each repo (more triage debt) |
| Test in parallel (3 subagents) vs sequential | Fast | Three open draft PRs simultaneously for CT review |

## References

- R2 Phase A pattern: `docs/superpowers/plans/2026-05-11-r2-lifecycle-e2e-and-chain-backfill-pdomain-book-tools.md`
- Three skills: `.claude/skills/{triage,spec-from-issue,decompose-spec}/SKILL.md`
- Chain-state report: `scripts/build-spec-chain-report.py`
- Per-repo agents: `pdomain-ocr-cli`, `pd-ocr-labeler`, `pdomain-prep-for-pgdp`
