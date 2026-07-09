---
status: complete
---

# R2 — Lifecycle E2E + Chain-State Backfill on pdomain-book-tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate the feature-request lifecycle skills end-to-end against a real (or sandbox-test) feature-request on pdomain-book-tools; complete the partial backfill workspace-rc started (the one missing feature-request issue for spec #29); verify the chain-state report renders correctly and the ctask schedule is firing.

**Architecture:** Three phases gated by acceptance bullets. Phase A drives one feature-request through `/triage` → `/spec-from-issue` → `/decompose-spec` end-to-end and observes each handoff produces the expected artifact (label state, spec file, milestone, child issues). Phase B closes the backfill gap workspace-rc left open. Phase C runs the chain-state report against the now-complete pdomain-book-tools chain, verifies the dashboard panel renders, confirms ctask scheduling.

**Tech Stack:** `gh` CLI, the three lifecycle skills (`/triage`, `/spec-from-issue`, `/decompose-spec`), `scripts/spec_chain_data.py`, `scripts/build-spec-chain-report.py`, `scripts/build-cost-dashboard.py`, `ctask`.

**Source plans:**
- `docs/superpowers/plans/2026-05-10-feature-request-lifecycle-plan-1.md` (Task 17 — Phase A)
- `docs/superpowers/plans/2026-05-10-feature-request-lifecycle-plan-2.md` (Phases 2 + 3)
- `docs/superpowers/plans/2026-05-11-INDEX.md`

**Depends on:** R0 (lint-first PRs merged or stable) and R1 (workspace canonical CONVENTIONS.md — needed by Phase C if the chain-state report touches conventions data; if it doesn't, the dependency is loose).

**Out of scope:**
- Per-repo lifecycle rollout on the 3 mature repos — R3b.
- Multi-cycle ship-issue stress — R4.

---

## Background context for the engineer

### What workspace-rc already did

Per the audit + the current `gh issue list` state, workspace-rc backfilled most of pdomain-book-tools' spec chain:

| Existing spec | Spec issue | Feature-request issue | Milestone |
|---|---|---|---|
| `docs/specs/01-page-model.md` (Page.to_dict()) | #24 | #25 | #2 |
| `docs/specs/02-page-orientation-detection.md` | #26 | #30 | #3 |
| `docs/specs/03-reorganize-page-pipeline.md` | #27 | #31 | #4 |
| `docs/specs/04-layout-regression-fixture-corpus.md` | #28 | #32 | #5 |
| `docs/specs/05-glyph-level-side-channel-annotations.md` | #29 | **MISSING** | #6 |

Plus there's a milestone #1 (`spec: lifecycle-chain-e2e-validation-smoke (#19)`) with 2 closed issues that's left over from a prior smoke test — leave it alone.

### What the three skills actually do (one-line each)

- `/triage <N>` — read a `kind:feature-request` issue, decide approve/reject, fork ONE child (`kind:tracking` for small mechanical work OR `kind:spec` for design-required), apply triage labels, post reasoning comment.
- `/spec-from-issue <N>` (on a `kind:spec` issue) — brainstorm a design spec via Q&A, write the 9-section spec file under `<repo>/docs/specs/`, edit the spec issue body to add a `Spec: <path>` line, open a draft PR with the spec file.
- `/decompose-spec <path>` (on a spec file) — propose child issues, confirm with CT, create a per-spec milestone, file child issues with `kind:chore`/`kind:bug`/etc. + appropriate labels.

### What "end-to-end smoke" means

Drive **one new** feature-request through the full chain. The test issue should be small, plausibly real (not a manufactured no-op), and end with at least one child issue eligible for ship-issue pickup (`bot:ship-issue-ready` + `status:ready` once CT arms it). The smoke test does NOT need to be merged to main — we're testing the skill machinery, not the produced spec.

A good smoke-test seed: pdomain-book-tools has a recent bug or chore that's small enough for a clean trace. Suggested: pick from existing chores in pdomain-book-tools issues that have not yet been triaged, OR file a synthetic one like "Add `__repr__` to BoundingBox" (3-line scope).

### Three-skill artifact contract

After all three skills run, the pdomain-book-tools repo + GitHub state should have:

1. The original `kind:feature-request` issue, with a `triage:approved` label and a comment from `/triage` pointing at the spec-issue child.
2. A `kind:spec` issue with a `Spec: docs/specs/NN-<slug>.md` line in its body.
3. A new spec file at `pdomain-book-tools/docs/specs/NN-<slug>.md` matching the 9-section template (lint-spec passes).
4. A draft PR with the spec file as the only change.
5. A milestone `spec: <slug> (#<spec-issue-number>)` with child issues linked.
6. ≥1 child issue with `kind:chore` (or `kind:bug`/`kind:feature`) + appropriate labels + body referencing the parent spec.

---

## File structure

**No workspace files created.** Everything lands in:

- pdomain-book-tools GitHub issues + labels + milestones (GitHub API state)
- pdomain-book-tools `docs/specs/NN-<slug>.md` (one new spec file via `/spec-from-issue`)
- pdomain-book-tools draft PR (one)
- Workspace `STATUS.md` (append R2 outcome)

**Verified, not modified:**
- `scripts/spec_chain_data.py`
- `scripts/build-spec-chain-report.py`
- `scripts/build-cost-dashboard.py` (chain-state panel renders)
- ctask entries (chain-state generator runs hourly)

---

## Tasks

### Phase A — End-to-end smoke (lifecycle Plan-1 Task 17)

#### Task A1: Pick a small real feature-request candidate

**Files:** none

- [ ] **Step 1: List pdomain-book-tools' open issues without `triage:*` labels**

```bash
gh issue list -R pdomain/pdomain-book-tools \
  --state open --label "kind:feature-request" --json number,title,labels \
  --jq '.[] | select(.labels | map(.name) | contains(["triage:approved"]) | not)' | head -30
```

Pick ONE that's small (1-3 sentences scope). If none exist, file a synthetic test issue:

```bash
gh issue create -R pdomain/pdomain-book-tools \
  --title "Add __repr__ to BoundingBox for clearer test failures" \
  --label "kind:feature-request,status:backlog,effort:S,model:haiku,model-effort:low" \
  --body "## Feature

\`BoundingBox\` instances appear in pytest assertion failures as
\`<BoundingBox object at 0x...>\`. A simple \`__repr__\` returning the
\`(x0, y0, x1, y1)\` tuple would make assertion diffs immediately readable
without dropping into the debugger.

## Motivation

Reduces debug cycle time for layout-regression failures (where BoundingBox
mismatches are the most common failure mode).

## Acceptance

- \`repr(BoundingBox(0, 0, 10, 10))\` returns \`'BoundingBox(0, 0, 10, 10)'\`
- One unit test asserting the format.

(Test issue for R2 smoke validation of /triage → /spec-from-issue → /decompose-spec chain.)"
```

Capture the issue number as `$FR_NUM`.

- [ ] **Step 2: Commit point (no commit)**

#### Task A2: Run /triage on the feature-request

**Files:** GitHub issue + comments + spec-issue child

- [ ] **Step 1: Invoke the skill**

```
/triage $FR_NUM
```

(In the Claude Code session, type the slash command.)

The skill prompts for approve/reject decision and (if approve) tracking-vs-spec. For a real BoundingBox `__repr__` change, the right call is `triage:approved` + `kind:tracking` (it's small mechanical scope). But for the smoke purpose of exercising the *full chain*, pick `kind:spec` so `/spec-from-issue` is exercised next.

- [ ] **Step 2: Verify artifacts**

```bash
gh issue view $FR_NUM -R pdomain/pdomain-book-tools --json labels,comments \
  --jq '.labels | map(.name)'
```

Expected: `triage:approved` label present. A comment on $FR_NUM contains the reasoning. A new `kind:spec` issue exists, body references $FR_NUM as parent.

Capture the spec-issue number as `$SPEC_NUM`.

- [ ] **Step 3: Commit point (no commit — GitHub state only)**

#### Task A3: Run /spec-from-issue on the spec-issue

**Files:**
- Create (in pdomain-book-tools): `docs/specs/NN-<slug>.md`
- New draft PR on pdomain-book-tools

- [ ] **Step 1: Invoke**

```
/spec-from-issue $SPEC_NUM
```

The skill walks brainstorming Q&A then writes the spec file. Answer Q&A to produce a small spec (≤200 lines is fine for the smoke).

- [ ] **Step 2: Verify**

```bash
gh issue view $SPEC_NUM -R pdomain/pdomain-book-tools --json body \
  --jq '.body' | grep -E "^Spec: docs/specs/"
gh pr list -R pdomain/pdomain-book-tools --state open --json number,title,headRefName --jq '.[] | select(.title | contains("spec"))'
```

Expected: spec-issue body has a `Spec: docs/specs/NN-<slug>.md` line. A draft PR exists with that single file change.

Verify the spec passes lint:

```bash
cd /workspaces/ocr-container/pdomain-book-tools
git fetch origin
git show origin/spec/<slug>:docs/specs/NN-<slug>.md > /tmp/r2-smoke-spec.md
cd /workspaces/ocr-container
uv run python scripts/lint-spec.py /tmp/r2-smoke-spec.md
```

Expected: exit 0.

Capture the spec file path as `$SPEC_PATH` (relative to pdomain-book-tools root).

- [ ] **Step 3: Commit point (no commit — GitHub state + new branch on pdomain-book-tools)**

#### Task A4: Run /decompose-spec on the spec file

**Files:** GitHub milestone + child issues

- [ ] **Step 1: Invoke**

```
/decompose-spec pdomain-book-tools/$SPEC_PATH
```

The skill proposes child issues, confirms with CT, then files them and creates a per-spec milestone.

- [ ] **Step 2: Verify**

```bash
gh api repos/pdomain/pdomain-book-tools/milestones --jq \
  '.[] | select(.title | startswith("spec:")) | "\(.number)\t\(.title)\topen:\(.open_issues)"'
gh issue list -R pdomain/pdomain-book-tools --milestone "<title-from-prev>" \
  --json number,title,labels --jq '.[] | "\(.number)\t\(.title)\t\([.labels[].name]|join(\",\"))"'
```

Expected: a new milestone with the spec-slug title; ≥1 child issue tied to it, each with proper kind label + (for tracking-ready ones) `bot:ship-issue-ready`.

- [ ] **Step 3: Commit point (no commit)**

### Phase B — Close backfill gap

#### Task B1: File the missing feature-request for spec #29

**Files:** GitHub issue

- [ ] **Step 1: Read spec #29's body to understand scope**

```bash
gh issue view 29 -R pdomain/pdomain-book-tools --json title,body --jq '.title + "\n\n" + .body' | head -60
```

- [ ] **Step 2: File the missing feature-request**

```bash
gh issue create -R pdomain/pdomain-book-tools \
  --title "Glyph-Level Side-Channel Annotations on Word" \
  --label "kind:feature-request,status:backlog" \
  --milestone 6 \
  --body "## Backfill

Retroactive feature-request issue for spec #29 (glyph-level annotations).
Filed as part of R2 Phase B to close the chain-backfill gap workspace-rc
left open.

## Spec

See #29 / \`pdomain-book-tools/docs/specs/05-glyph-level-side-channel-annotations.md\`.

## Triage status

Pre-approved by virtue of having a written spec. Skipping /triage; the spec
issue (#29) is the canonical child."
```

Capture as `$FR29_NUM`.

- [ ] **Step 3: Cross-link the spec issue back**

```bash
gh issue comment 29 -R pdomain/pdomain-book-tools \
  --body "Parent feature-request: #$FR29_NUM (backfilled for R2 Phase B chain completion)."
```

- [ ] **Step 4: Commit point (no commit)**

### Phase C — Chain-state report + dashboard verification

#### Task C1: Run the chain-state generator against pdomain-book-tools

**Files:** generated markdown + JSON (transient or committed depending on script behavior)

- [ ] **Step 1: Run it**

```bash
cd /workspaces/ocr-container
uv run python scripts/build-spec-chain-report.py --repo pdomain/pdomain-book-tools \
  --out /tmp/r2-chain-report.md
echo "Exit: $?"
wc -l /tmp/r2-chain-report.md
```

Expected: exit 0; output file 30+ lines containing View A (per-spec table) and View B (cross-cutting summary).

- [ ] **Step 2: Spot-check content**

```bash
grep -E "^#|^\| " /tmp/r2-chain-report.md | head -30
```

Expected: at least 6 spec rows (one per milestone), each with feature-request + spec-issue + child-issue counts.

- [ ] **Step 3: Commit point (no commit)**

#### Task C2: Refresh dashboard and verify chain-state panel

**Files:** `cost-dashboard.html` (regenerated)

- [ ] **Step 1: Find dashboard output location**

```bash
grep -E "OUT_PATH|output|html" scripts/build-cost-dashboard.py | head -10
```

The dashboard's HTML output path is wherever the script writes; default is typically `cost-dashboard.html` in the workspace root or `docs/`.

- [ ] **Step 2: Run dashboard refresh**

```bash
cd /workspaces/ocr-container
uv run python scripts/build-cost-dashboard.py
```

Expected: exit 0. HTML file exists.

- [ ] **Step 3: Verify chain-state panel rendered**

```bash
DASH=$(find . -maxdepth 3 -name "cost-dashboard.html" -newer scripts/build-cost-dashboard.py 2>/dev/null | head -1)
grep -c "chain\|spec\|milestone\|Spec Chain\|Chain State" "$DASH"
```

Expected: ≥3 matches (the panel includes "Spec Chain" header + milestone rows + status counts).

- [ ] **Step 4: (Optional) Open dashboard locally to eyeball**

If running interactively, `python3 -m http.server 8000 --directory $(dirname $DASH)` and visit http://localhost:8000/cost-dashboard.html. Confirm visually: chain-state panel shows pdomain-book-tools' 6 milestones with progress bars (open vs closed children).

- [ ] **Step 5: Commit point (no commit — dashboard HTML is regenerated, not committed)**

#### Task C3: Verify ctask scheduling

**Files:** ctask config (read-only verification)

- [ ] **Step 1: List scheduled tasks**

```bash
/workspaces/ocr-container/ctask list 2>&1
```

Expected: an entry for `build-cost-dashboard.py` (already scheduled hourly per Plan A), AND an entry for the chain-state generator (added by lifecycle Plan 2).

If the chain-state entry is missing, add it:

```bash
/workspaces/ocr-container/ctask add \
  --name "spec-chain-report" \
  --cmd "uv run python scripts/build-spec-chain-report.py --all-repos --out docs/spec-chain-state.md" \
  --interval "1h" \
  --before "build-cost-dashboard"
```

(Replace `--before build-cost-dashboard` with whatever flag your ctask supports for ordering. If ordering can't be expressed, accept that they run independently on the hour.)

- [ ] **Step 2: Force a run to verify the entry works**

```bash
/workspaces/ocr-container/ctask run spec-chain-report
```

Expected: exit 0; `docs/spec-chain-state.md` (or wherever it writes) updated.

- [ ] **Step 3: Commit any ctask config changes if the config is under version control**

```bash
cd /workspaces/ocr-container
git status ctask/  # or wherever ctask config lives
```

If something is staged, commit with:

```
chore(ctask): schedule spec-chain-report hourly before dashboard refresh
```

### Task R2-Final: Update STATUS.md with R2 outcome

**Files:**
- Modify: `docs/superpowers/plans/STATUS.md`

- [ ] **Step 1: Append**

```bash
cat >> /workspaces/ocr-container/docs/superpowers/plans/STATUS.md <<EOF

## R2 — Lifecycle E2E + chain backfill on pdomain-book-tools (YYYY-MM-DDTHH:MM:SSZ)

End-to-end smoke validated:
- /triage on #$FR_NUM produced triage:approved label + spec-issue child #$SPEC_NUM.
- /spec-from-issue on #$SPEC_NUM produced \`$SPEC_PATH\` + draft PR.
- /decompose-spec on $SPEC_PATH produced milestone + N child issues.

Chain-state backfill complete: feature-request #$FR29_NUM filed for spec #29.

Chain-state report renders for pdomain-book-tools (6 milestones visible). Dashboard panel green. ctask schedule confirmed.

Ready for R3a (CONVENTIONS+bot rollout to 3 mature repos) and R3b (lifecycle drive-through on same 3 repos).
EOF
```

Replace placeholders with actual values from Phases A-C.

- [ ] **Step 2: Commit**

```bash
cd /workspaces/ocr-container
git add docs/superpowers/plans/STATUS.md
git commit -m "$(cat <<'EOF'
chore(status): R2 outcome — lifecycle E2E green, backfill closed

Smoke-tested the full /triage → /spec-from-issue → /decompose-spec
chain on pdomain-book-tools. Closed the one missing backfill
feature-request. Chain-state report + dashboard panel confirmed
operational.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Acceptance

R2 is complete when:

- [ ] Phase A produced 1 spec file, 1 milestone, ≥1 child issue, 1 draft PR — all linked back to the original feature-request.
- [ ] Phase B closed the spec-#29 gap (feature-request now exists, milestone has both spec + feature-request as children).
- [ ] Phase C renders chain-state report for pdomain-book-tools showing 6 milestones; dashboard panel shows the same; ctask entry runs cleanly.
- [ ] STATUS.md updated with R2 summary.

## Trade-offs considered

| Decision | Pro | Con |
|---|---|---|
| Real test issue (BoundingBox `__repr__`) vs throw-away | Smoke produces a usable artifact; reviewer sees real Q&A | Smoke spec might get merged → noise in the repo; flag the draft PR `wip:` and let CT decide |
| Phase B (file FR for #29) inside R2 vs as its own plan | Plan stays self-contained; one commit closes the gap | Slight Plan B scope bleed |
| Run /decompose-spec on the smoke spec | Exercises the full chain | Adds 1+ child issues to the repo backlog (one more thing to triage later) |

## References

- `docs/superpowers/plans/2026-05-10-feature-request-lifecycle-plan-1.md` (Task 17)
- `docs/superpowers/plans/2026-05-10-feature-request-lifecycle-plan-2.md` (Phases 2 + 3)
- `.claude/skills/{triage,spec-from-issue,decompose-spec}/SKILL.md`
- `scripts/{spec_chain_data,build-spec-chain-report,build-cost-dashboard}.py`
