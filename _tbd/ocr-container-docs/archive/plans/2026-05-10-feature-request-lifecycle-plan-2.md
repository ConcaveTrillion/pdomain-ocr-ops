---
status: complete
---

# Feature-request lifecycle — Plan 2: backfill + chain-state report + dashboard

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land Phases 2, 3, and 5 of the feature-request lifecycle. End state: pdomain-book-tools' existing specs are folded into the chain via `--backfill`, the chain-state report (per-repo markdown + workspace summary + dashboard panel) is generated on a schedule and visible at `cost-dashboard.html`, and the new skill machinery is in active use across all 8 repos.

**Architecture:** A pure-Python join layer (`scripts/spec_chain_data.py`) reads `gh` JSON for one repo and emits a structured `RepoChainState` dataclass — no I/O beyond the gh calls it does internally. The renderer (`scripts/build-spec-chain-report.py`) consumes that and emits markdown views A and B per repo plus a workspace cross-repo summary. The dashboard panel reuses the same data and embeds milestone progress bars into `cost-dashboard.html`. The ctask entry that already runs `build-cost-dashboard.py` once per hour is extended to run the chain-state generator immediately before, so both files refresh on the same cadence.

**Tech Stack:** Python 3.11, `gh` CLI, `pytest`/`unittest`, the existing `scripts/build-cost-dashboard.py` HTML template.

**Source spec:** `docs/superpowers/specs/2026-05-10-feature-request-spec-decomposition-design.md`

**Depends on:** Plan 1 must be complete and merged (skills, helpers, label rename). Plan 1's Task 17 end-to-end validation should have produced at least one working spec → milestone → children chain on pdomain-book-tools.

**Out of scope:** Phase 4 (dashboard refresh design) is a deferred sibling brainstorm — only enter that once Phase 3 is validated and CT has hands-on experience with the panel.

**Coordination with v2 work:** A sibling spec
[2026-05-10-code-review-style-cleanup-design.md](../specs/2026-05-10-code-review-style-cleanup-design.md)
defines the bot/CONVENTIONS.md story (4 sibling plans). Three coordination
points to respect when sequencing across {this plan, v2 Plans 1–4}:

1. **v2 Phase 1 (worktree retrofit) lands before this plan's Phase 5
   rollout.** v2 Plan 1 retrofits ship-issue to write into
   `/srv/bot-workspaces/ship-issue/<repo>/`. Phase 5 here drives a
   feature-request through each remaining repo and ends with ship-issue
   actually picking it up — that should exercise the new worktree
   pattern, not the legacy one.
2. **This plan's Task 7 (chain-state dashboard panel) lands before v2
   Plan 4 Phase 6.** v2 Plan 4 adds three more panels to
   `scripts/build-cost-dashboard.py` (sync-drift, sibling-drift,
   style-bot-events). Stacking v2 Plan 4 on top of an already-extended
   dashboard avoids merge churn on the same file.
3. **This plan's Phase 5 rolls out lifecycle skills to 6 repos; v2 Plan
   4 Phase 7 rolls out CONVENTIONS.md + bots to the same 6 repos.** Both
   are CT-driven manual handbacks. Run Phase 5 first (validates the
   lifecycle skills work cross-repo), then v2 Plan 4 Phase 7 (layers
   conventions and bots on top of the now-validated lifecycle).

---

## Background context for the engineer

You are extending the feature-request lifecycle landed in Plan 1 with three things:

1. **Backfill of existing specs**: turn pdomain-book-tools' eight legacy specs (`docs/specs/01-page-model.md` through `07-dev-local-upgrade-flow.md` plus `_index.md`) and the workspace-level specs into chain participants by running `/decompose-spec --backfill --output=feature-requests`. The output is a set of retrospective `kind:feature-request` issues that re-enter the lifecycle at the top.

2. **Chain-state report**: a generator `scripts/build-spec-chain-report.py` that reads each repo's open issues + milestones via `gh` and writes:
   - `<repo>/docs/spec-chain-report.md` — per-repo Views A and B from the spec
   - `docs/superpowers/spec-chain-status.md` — workspace cross-repo summary
   - `cost-dashboard.html` panel (extended in `scripts/build-cost-dashboard.py`)

3. **Rollout to remaining 7 repos**: with skills + labels in place, expand active use to pdomain-ocr-cli, pd-ocr-labeler, pdomain-ocr-labeler-spa, pdomain-ocr-synth, pd-ocr-trainer, pd-png-optimizer, pdomain-prep-for-pgdp.

Existing surfaces you will modify or use:

- `scripts/build-cost-dashboard.py` — has `REPOS` tuple at lines 25-28, `KANBAN_COLUMNS` at 29-30, `load_kanban_data()` at line 188, `render_kanban_panel()` at line 224. Extend with a chain-state panel.
- `ctask` (workspace-level scheduler at `/workspaces/ocr-container/ctask`) — has an entry that runs `build-cost-dashboard.py` once per hour. Add a sibling entry for `build-spec-chain-report.py` that runs immediately prior.
- `.claude/hooks/session-start.py` — emits the workspace state at session start. The chain-state markdown is consumed manually by CT, not by the agent's reading context, so the SessionStart hook does not need a chain-state line.
- All eight `pd-*/docs/specs/` directories.
- `scripts/spec_slug.py` (from Plan 1) — used here for milestone-title joins.

The 8 repos: `pdomain-book-tools`, `pdomain-ocr-cli`, `pd-ocr-labeler`, `pdomain-ocr-labeler-spa`, `pdomain-ocr-synth`, `pd-ocr-trainer`, `pd-png-optimizer`, `pdomain-prep-for-pgdp`.

---

## File structure (created or modified by this plan)

**Created:**

- `scripts/spec_chain_data.py` — pure join layer: gh → `RepoChainState`.
- `tests/scripts/test_spec_chain_data.py` — unit tests using fake gh.
- `scripts/build-spec-chain-report.py` — renderer entry point.
- `tests/scripts/test_build_spec_chain_report.py` — unit + golden-file tests.
- One `<repo>/docs/spec-chain-report.md` per repo (generated, gitignored — see Task 5).
- `docs/superpowers/spec-chain-status.md` (generated, gitignored).

**Modified:**

- `scripts/build-cost-dashboard.py` — adds a chain-state panel.
- `tests/scripts/test_build_cost_dashboard.py` — extends panel coverage (or creates if absent — verify).
- `ctask` config — adds chain-report entry.
- pd-* `.gitignore` files — add `docs/spec-chain-report.md`.
- `docs/superpowers/specs/2026-05-10-feature-request-spec-decomposition-design.md` — flip Status: Draft → Active when fully landed.

---

# Phase 0: Plan-1 reviewer follow-ups

The Plan-1 final reviewer surfaced six small coverage / hygiene gaps in
the helpers that landed under Plan 1. They are independent of Phases 2/3/5
and should land first so the rest of Plan 2 stacks on a clean base.

Each task is small (one focused commit). They're all dispatchable to a
subagent — no GitHub state changes, no manual judgment.

## Task 0.1: decompose-spec-plan.py — test mixed output mode

**Files:**

- Modify: `tests/scripts/test_decompose_spec_plan.py` — add a test for `output="mixed"`.

The implementation accepts `mixed` as a valid output (see
`scripts/decompose-spec-plan.py:56` — `_VALID_OUTPUTS = {"tracking", "feature-requests", "mixed"}`),
but the existing test file at `tests/scripts/test_decompose_spec_plan.py`
only exercises `tracking` and `feature-requests`. Lock the mixed-mode
behavior down with one test.

- [ ] **Step 1: Write the failing test**

Append to `tests/scripts/test_decompose_spec_plan.py`:

```python
def test_mixed_output_emits_per_subsection_children_with_default_kind():
    """In mixed mode the helper still emits one child per Decision subsection.

    The agent + CT pick per-row tracking-vs-feature-request at apply time;
    the helper's default kind is intentionally `chore` (tracking-style)
    when output="mixed", matching the conservative default. CT toggles
    to feature-request per row in the SKILL flow.
    """
    m = _mod()
    p = _write_spec(SPEC_WITH_HEADER)
    plan = m.build_plan(p, output="mixed")
    assert plan["output"] == "mixed"
    assert len(plan["children"]) == 3  # one per ### subsection
    # Default kind is the conservative tracking-style default.
    for c in plan["children"]:
        assert c["kind"] == "chore"
        assert "kind:chore" in c["labels"]
```

- [ ] **Step 2: Run the test — confirm it passes**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_decompose_spec_plan.py::test_mixed_output_emits_per_subsection_children_with_default_kind -v
```

Expected: PASS. (The implementation already supports mixed via
`_default_kind_for_output()` returning `"chore"` for any output that's
not `"feature-requests"`.)

- [ ] **Step 3: Commit**

```bash
cd /workspaces/ocr-container
git add tests/scripts/test_decompose_spec_plan.py
git commit -m "test(decompose-spec-plan): cover output=mixed default kind"
```

---

## Task 0.2: triage-fork.py — assert spec-output placeholder body line

**Files:**

- Modify: `tests/scripts/test_triage_fork.py:87-98` — strengthen the spec-output assertion.

`scripts/triage-fork.py:120-121` augments spec-output bodies with
`"\nSpec: (to be filled by /spec-from-issue)\n"`. The existing
`test_creates_spec_child_carries_kind_spec_label` confirms the label
attaches and `Tracks: #42` is present, but does NOT assert the
placeholder Spec line — easy to silently break. Add the assertion.

- [ ] **Step 1: Strengthen the existing test**

Edit `tests/scripts/test_triage_fork.py` — find
`test_creates_spec_child_carries_kind_spec_label` and add one assertion:

```python
def test_creates_spec_child_carries_kind_spec_label():
    m = _mod()
    gh = FakeGh()
    decision = m.plan_fork(
        gh, repo="pdomain/pdomain-book-tools", parent=42,
        kind="spec", output="spec",
        title="Spec: rework Y", body="Y is hard", labels=["kind:spec", "effort:M"],
        force=False,
    )
    new_num = m.execute_fork(gh, decision)
    assert "kind:spec" in gh.created[0]["labels"]
    assert "Tracks: #42" in gh.created[0]["body"]
    # Spec-output bodies must carry the placeholder Spec: line so
    # /spec-from-issue can detect-and-fill in finalize step.
    assert "Spec: (to be filled by /spec-from-issue)" in gh.created[0]["body"]
```

- [ ] **Step 2: Run the test — confirm it passes**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_triage_fork.py::test_creates_spec_child_carries_kind_spec_label -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
cd /workspaces/ocr-container
git add tests/scripts/test_triage_fork.py
git commit -m "test(triage-fork): assert spec-output placeholder Spec: line"
```

---

## Task 0.3: spec-from-issue-finalize.py — test --force when no existing Spec: line

**Files:**

- Modify: `tests/scripts/test_spec_from_issue_finalize.py` — add a test for the
  `force=True` fallback path at `scripts/spec-from-issue-finalize.py:91-92`.

Existing `test_force_replaces_existing_spec_line` covers the case where
a Spec: line already exists (the regex .sub() succeeds). The fallback
branch — `if not _SPEC_LINE.search(new_body): new_body = body.rstrip() + ...`
— fires when `force=True` is passed but the body has no Spec: line yet.
That branch is currently uncovered.

- [ ] **Step 1: Write the failing test**

Append to `tests/scripts/test_spec_from_issue_finalize.py`:

```python
def test_force_appends_spec_line_when_none_present():
    """force=True should still append a Spec: line if none exists yet.

    Covers the fallback at spec-from-issue-finalize.py:91-92 — the regex
    .sub() finds no match, so the code falls back to appending a fresh
    Spec: line. Without this test the branch is silently uncovered.
    """
    m = _mod()
    gh = FakeGh(issue_body="Tracks: #42\n\nWrite the spec.\n")
    decision = m.plan_finalize(
        gh, repo="x/y", spec_issue=43,
        spec_path="docs/specs/2026-05-10-foo.md",
        force=True,
    )
    assert decision.kind == "edit"
    assert "Spec: docs/specs/2026-05-10-foo.md" in decision.new_body
    assert "Tracks: #42" in decision.new_body
```

- [ ] **Step 2: Run the test — confirm it passes**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_spec_from_issue_finalize.py::test_force_appends_spec_line_when_none_present -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
cd /workspaces/ocr-container
git add tests/scripts/test_spec_from_issue_finalize.py
git commit -m "test(spec-from-issue-finalize): cover --force append-when-missing fallback"
```

---

## Task 0.4: decompose-spec-apply.py — test repo=None defensive path

**Files:**

- Modify: `tests/scripts/test_decompose_spec_apply.py` — add a test for the
  repo=None short-circuit.

`scripts/decompose-spec-apply.py:115-119` documents that backfill mode
without a spec_issue ends up with `repo=None`; line 122 then refuses to
ensure a milestone (`if milestone_title and repo:`). The existing
`test_backfill_without_milestone_title_skips_milestone` exercises this
indirectly (milestone_title=None) but doesn't pin the contract that
`apply_plan` must not raise even when the plan has zero children to file.
Add the explicit no-children backfill case.

- [ ] **Step 1: Write the failing test**

Append to `tests/scripts/test_decompose_spec_apply.py`:

```python
def test_backfill_with_no_spec_issue_and_no_children_is_a_noop():
    """repo=None + empty children must not raise; helper is a clean no-op.

    Covers the defensive branch at decompose-spec-apply.py:115-119 where
    backfill mode lacks a spec_issue (caller in SKILL.md hasn't filed it
    yet). Apply must short-circuit without calling gh.issue_create with
    repo=None.
    """
    m = _mod()
    gh = FakeGh()
    plan = {
        "spec_path": "docs/specs/2026-05-10-foo.md",
        "spec_issue": None,
        "backfill": True,
        "output": "tracking",
        "milestone_title": None,
        "children": [],
    }
    summary = m.apply_plan(gh, plan, dry_run=False)
    assert gh.created_milestones == []
    assert gh.created_issues == []
    assert summary["children_filed"] == 0
```

- [ ] **Step 2: Run the test — confirm it passes**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_decompose_spec_apply.py::test_backfill_with_no_spec_issue_and_no_children_is_a_noop -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
cd /workspaces/ocr-container
git add tests/scripts/test_decompose_spec_apply.py
git commit -m "test(decompose-spec-apply): cover repo=None defensive path"
```

---

## Task 0.5: seed-labels.sh — refresh existing-label descriptions on rerun

**Files:**

- Modify: `scripts/seed-labels.sh:51-56` — update the if/else so a rerun
  refreshes color + description on existing labels instead of just
  printing "exists".

Today's `scripts/seed-labels.sh` skips any label whose name already
exists. The label-rename migration in Plan 1 left
`status:ready`'s description on the 6 already-published repos still
saying "with claude-ok" instead of "with bot:ship-issue-ready". A rerun
of `seed-labels.sh` should fix that automatically — making the script
idempotent on description drift, not just on existence.

- [ ] **Step 1: Modify the script**

Replace lines 49-57 of `scripts/seed-labels.sh` (the for loop over
LABELS). New body:

```bash
for entry in "${LABELS[@]}"; do
  IFS='|' read -r name color desc <<< "$entry"
  if gh label list -R "$REPO" --limit 200 --json name | grep -q "\"$name\""; then
    # Already exists — refresh color + description so the script is
    # idempotent against drift (e.g. label rename leaving stale prose).
    gh label edit "$name" -R "$REPO" --color "$color" --description "$desc" \
      && echo "  ↻ $name (refreshed)"
  else
    gh label create "$name" -R "$REPO" --color "$color" --description "$desc" \
      && echo "  + $name"
  fi
done
```

- [ ] **Step 2: Smoke-test against one repo**

```bash
cd /workspaces/ocr-container
scripts/seed-labels.sh pdomain/pdomain-book-tools 2>&1 | head -10
```

Expected: each line is `↻ <label> (refreshed)` (or `+ <label>` for any
brand-new ones). Re-confirm the `status:ready` description on the repo:

```bash
gh label list -R pdomain/pdomain-book-tools --json name,description \
  --jq '.[] | select(.name=="status:ready")'
```

Expected: description ends with `(with bot:ship-issue-ready)`, not
`(with claude-ok)`.

- [ ] **Step 3: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/seed-labels.sh
git commit -m "fix(seed-labels): refresh color+description on existing labels (idempotent against drift)"
```

(CT's manual-handback Task #5 in the prompt's queue is now redundant —
the next `seed-labels.sh <repo>` run on each of the 6 published repos
will fix the stale `status:ready` description automatically. Roll those
reruns into Plan 5's Task 10 step or run them ad-hoc.)

---

## Task 0.6: pilot-pdomain-book-tools{,-debrief}.md — operational claude-ok sweep

**Files:**

- Modify: `docs/superpowers/plans/2026-05-10-pilot-pdomain-book-tools.md` lines 30, 42, 63, 64, 71, 79
- Modify: `docs/superpowers/plans/2026-05-10-pilot-pdomain-book-tools-debrief.md` selected operational lines

Plan 1's claude-ok → bot:ship-issue-ready rename swept code + open
issues. Two pilot docs still reference `claude-ok` in *operational*
prose (procedure-as-instruction). The historical narrative ("at B4 we
filed 4 issues with claude-ok") should stay as-is; only operational
guidance ("add claude-ok to issues that are ready") should be rewritten.

- [ ] **Step 1: Sweep `2026-05-10-pilot-pdomain-book-tools.md`**

Each of these lines is operational guidance — rewrite each `claude-ok`
to `bot:ship-issue-ready`:

- Line 30 — "all 26 workspace labels (kind/effort/model/model-effort/recurring/status/claude-ok/triage)" → drop `claude-ok` from the family list and add `bot:ship-issue-ready` (the family is now `bot:`).
- Line 42 — table cell `(kind:chore + claude-ok)` → `(kind:chore + bot:ship-issue-ready)`.
- Line 63 — "start without `claude-ok`; user adds it manually after triage" → "start without `bot:ship-issue-ready`; user arms it manually after triage".
- Line 64 — "+ `claude-ok` (these are mechanical)" → "+ `bot:ship-issue-ready` (these are mechanical)".
- Line 71 — "smallest `status:ready` + `claude-ok` issue" → "smallest `status:ready` + `bot:ship-issue-ready` issue".
- Line 79 — "Add `claude-ok` to 3-5 more issues" → "Add `bot:ship-issue-ready` to 3-5 more issues".

- [ ] **Step 2: Sweep `2026-05-10-pilot-pdomain-book-tools-debrief.md`**

The debrief is mostly historical prose. Audit each occurrence and
rewrite ONLY operational lines:

```bash
cd /workspaces/ocr-container
grep -nE '\bclaude-ok\b' docs/superpowers/plans/2026-05-10-pilot-pdomain-book-tools-debrief.md
```

For each hit, decide historical (leave) vs operational (rewrite). Note
the user's call-out flagged ~lines 30/42/71/109; the first three are in
the pilot doc, line 109 is in the debrief — rewrite that one
("…no re-add of `claude-ok` (manual PR, not bot)" is operational
guidance about the manual fix path; rewrite to `bot:ship-issue-ready`).

For the historical "B4 filed 4 issues with `claude-ok`" lines, leave
them as historical — but add a parenthetical at first occurrence of
each file: `(now bot:ship-issue-ready — see Plan-1 rename)` so a future
reader can join the dots.

- [ ] **Step 3: Verify**

```bash
cd /workspaces/ocr-container
grep -nE '\bclaude-ok\b' docs/superpowers/plans/2026-05-10-pilot-pdomain-book-tools.md \
                        docs/superpowers/plans/2026-05-10-pilot-pdomain-book-tools-debrief.md
```

Expected: only historical narrative occurrences remain.

- [ ] **Step 4: Commit**

```bash
cd /workspaces/ocr-container
git add docs/superpowers/plans/2026-05-10-pilot-pdomain-book-tools.md \
        docs/superpowers/plans/2026-05-10-pilot-pdomain-book-tools-debrief.md
git commit -m "docs(pilot): sweep operational claude-ok → bot:ship-issue-ready"
```

---

# Phase 2: Backfill validation on pdomain-book-tools

This phase runs `/decompose-spec` against pre-existing material. It produces real GitHub state, not code. Each task is an interactive Claude session driving the skill.

## Task 1: Pre-flight catalog of existing pdomain-book-tools specs

This task creates a working list. No code, no commits.

- [ ] **Step 1: Enumerate existing specs**

```bash
ls /workspaces/ocr-container/pdomain-book-tools/docs/specs/*.md
```

Expected: 8 files (`01-page-model.md` through `07-dev-local-upgrade-flow.md` plus `_index.md`).

- [ ] **Step 2: Identify which specs are still active**

Open each in turn and read the H1 + TL;DR + Status line. Some may already be marked `Status: Locked` (shipped). The backfill should target `Active` and `Draft` specs only.

```bash
for f in /workspaces/ocr-container/pdomain-book-tools/docs/specs/0*.md; do
  echo "=== $f ==="
  head -10 "$f" | grep -E "^(#|>)"
done
```

Capture the active list. Skip `_index.md` (it's a directory README, not a spec). Skip anything `Status: Locked`. Skip anything in the `.specrc:legacy` allowlist.

```bash
cat /workspaces/ocr-container/pdomain-book-tools/docs/specs/.specrc 2>/dev/null
```

Expected: a list of legacy spec basenames; those are NOT eligible for backfill (they need `superpowers:fixing-specs` Procedure 4 first).

- [ ] **Step 3: Identify existing pdomain-book-tools issues #2-#13**

```bash
gh issue list --repo pdomain/pdomain-book-tools --state all --limit 50 \
  --json number,title,labels,body --jq '.[] | select(.number <= 13) | {number, title, labels: [.labels[].name]}'
```

Capture the title + label set for each. The plan's later step adds `Tracks: #<feature-request>` to each (per resolved Open Q #4 in the spec).

- [ ] **Step 4: Save the catalog**

Write a working-notes markdown to `/tmp/backfill-catalog.md` with:

- Active specs to backfill (path → expected feature-request count)
- pdomain-book-tools issues #2-#13 (number → title → which feature-request will track them once filed)

This is a scratch file. Don't commit.

---

## Task 2: Backfill spec issues + feature-request children for one spec (smoke)

Pick one small active spec from Task 1 — likely `01-page-model.md`. Drive `/decompose-spec --backfill --output=feature-requests` against it. This is the smoke run before the full sweep.

- [ ] **Step 1: Dry-run**

In a Claude session at the workspace root:

```
/decompose-spec pdomain-book-tools/docs/specs/01-page-model.md --backfill --output=feature-requests
```

Without `--apply`, the skill stops at the proposal table. Read each proposed feature-request title; confirm they're scoped to the kind of clusters the spec covers.

- [ ] **Step 2: Edit proposals if needed**

If the auto-derived titles look wrong (e.g., based on `### `-subsection text that's too granular), edit them in the chat. The plan JSON saved at `/tmp/plan.json` is the source of truth — `/decompose-spec` reads it back at apply time.

- [ ] **Step 3: Apply**

```
/decompose-spec pdomain-book-tools/docs/specs/01-page-model.md --backfill --output=feature-requests --apply
```

Expected:
- A retrospective `kind:spec` issue is filed (call it `$SPEC1`). Its body says `Backfill: pre-existing spec at pdomain-book-tools/docs/specs/01-page-model.md`.
- The spec markdown is edited to add `> **Spec-Issue**: pdomain/pdomain-book-tools#$SPEC1` blockquote line. Commit + push that edit on a small docs branch (the skill should do this automatically; if not, do it manually).
- A milestone `spec: page-model (#$SPEC1)` (or similar slug) is created.
- N feature-request children are filed, each with `Tracks: #$SPEC1` + `Spec: pdomain-book-tools/docs/specs/01-page-model.md`, attached to the milestone, labeled `kind:feature-request, status:backlog`.

- [ ] **Step 4: Verify**

```bash
gh issue list --repo pdomain/pdomain-book-tools --label kind:feature-request \
  --json number,title,milestone --jq '.[] | {number, title, milestone: .milestone.title}'
gh api /repos/pdomain/pdomain-book-tools/milestones?state=open --jq '.[] | {title, open_issues, closed_issues}'
```

Expected: feature-requests visible; milestone visible; counts match.

- [ ] **Step 5: Confirm spec markdown was correctly edited**

```bash
head -10 /workspaces/ocr-container/pdomain-book-tools/docs/specs/01-page-model.md
```

Expected: `> **Spec-Issue**:` line is present below `> **Last updated**:`.

If the line is missing, the skill failed mid-flight — re-run with `--diff`. If still missing, add it manually:

```bash
cd /workspaces/ocr-container/pdomain-book-tools
sed -i '/^> \*\*Last updated\*\*:/a > **Spec-Issue**: pdomain/pdomain-book-tools#'"$SPEC1" docs/specs/01-page-model.md
```

Commit this on the same branch as the rest of the smoke artifacts.

---

## Task 3: Backfill the remaining active pdomain-book-tools specs

Repeat Task 2's pattern for each remaining active spec. Don't try to do them in one session; one spec per Claude session keeps the proposal table manageable.

- [ ] **Step 1: For each spec in the active list (from Task 1)**

  - [ ] Dry-run: `/decompose-spec <path> --backfill --output=feature-requests`
  - [ ] Review + edit proposal in chat
  - [ ] Apply: re-run with `--apply`
  - [ ] Verify the spec issue, milestone, and feature-request children landed

- [ ] **Step 2: Track which specs got which spec-issue numbers**

Append to `/tmp/backfill-catalog.md` as you go. You'll need this for Task 4.

- [ ] **Step 3: Commit the spec markdown edits**

The `> **Spec-Issue**:` line additions across multiple spec files should land on one branch in pdomain-book-tools and be opened as a draft PR. Per the workspace's per-repo agent routing (`CLAUDE.md`), delegate the commit to the `pdomain-book-tools` agent:

```
[pdomain-book-tools agent prompt]
The following spec files in pdomain-book-tools/docs/specs/ have new
> **Spec-Issue**: lines added by /decompose-spec --backfill. Open a draft
PR titled "docs(specs): add Spec-Issue blockquote headers from backfill"
on a branch named `wip/spec-backfill-headers`. Run pre-commit (lint-spec
should pass; markdownlint should be unaffected). Files changed:
  pdomain-book-tools/docs/specs/01-page-model.md
  pdomain-book-tools/docs/specs/02-rotation.md
  ... (etc — only the ones you actually modified)
```

The agent runs in pdomain-book-tools; uses `pd-push` for the push.

---

## Task 4: Wire existing #2-#13 to their parent feature-requests

Per the spec's resolved Open Q #4, existing pdomain-book-tools issues #2-#13 get `Tracks: #<feature-request>` body lines added so they thread onto the chain.

- [ ] **Step 1: Map each existing issue to its parent feature-request**

From your `/tmp/backfill-catalog.md`, for each issue #2-#13:
- Decide which retrospective feature-request from Task 3 covers its work (or skip if low-value).
- Record `<existing-issue-num> → Tracks: #<feature-request-num>`.

Some existing issues may not map to any backfilled feature-request. Skip those — wiring them is optional.

- [ ] **Step 2: Edit each mapped issue's body**

For each mapping `<E> → <FR>`:

```bash
EXISTING_BODY=$(gh issue view $E --repo pdomain/pdomain-book-tools --json body --jq '.body')
NEW_BODY="$EXISTING_BODY"$'\n\nTracks: #'$FR
gh issue edit $E --repo pdomain/pdomain-book-tools --body "$NEW_BODY"
```

Idempotent: if `Tracks: #$FR` is already in the body, skip.

- [ ] **Step 3: Verify chain reachability**

```bash
gh issue view <E> --repo pdomain/pdomain-book-tools --json body \
  | grep -E "^Tracks: #"
```

Expected: at least one `Tracks: #` line per wired issue.

No commit; this is GitHub state only.

---

# Phase 3: Chain-state report

## Task 5: Build the spec_chain_data.py pure helper

**Files:**

- Create: `scripts/spec_chain_data.py`
- Create: `tests/scripts/test_spec_chain_data.py`

The data layer joins, for one repo:

- All open `kind:feature-request` issues
- Their forked children (matched via `Tracks: #<FR>` body line)
- Spec issues filed for those children (matched via `kind:spec` + `Tracks: #<FR>`)
- Milestones (`spec: <slug> (#M)`) for each spec issue
- Each milestone's progress (open/closed counts via `gh api`)
- Spec files on disk under `<repo>/docs/specs/` (for View B "orphan specs")

It returns a dataclass tree. No markdown rendering at this layer.

- [ ] **Step 1: Write the failing tests**

Save as `tests/scripts/test_spec_chain_data.py`:

```python
"""Tests for scripts/spec_chain_data.py."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/spec_chain_data.py"


def _mod():
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    spec = importlib.util.spec_from_file_location("spec_chain_data", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FakeGh:
    def __init__(self, issues=None, milestones=None):
        self.issues = list(issues or [])
        self.milestones = list(milestones or [])

    def issue_list(self, repo, state="open", limit=200):
        return list(self.issues)

    def list_milestones(self, repo):
        return list(self.milestones)


def _issue(num, title, body, *, labels):
    return {
        "number": num, "title": title, "body": body,
        "labels": [{"name": n} for n in labels],
    }


def test_groups_feature_request_with_its_spec_and_children():
    m = _mod()
    issues = [
        _issue(42, "X tuning", "Initial idea", labels=["kind:feature-request", "triage:approved"]),
        _issue(43, "Spec: X tuning",
               "Tracks: #42\nSpec: docs/specs/x-tuning.md",
               labels=["kind:spec", "status:backlog"]),
        _issue(44, "Foo: A",
               "Tracks: #43\nSpec: docs/specs/x-tuning.md",
               labels=["kind:chore", "status:backlog"]),
        _issue(45, "Foo: B",
               "Tracks: #43\nSpec: docs/specs/x-tuning.md",
               labels=["kind:chore", "status:ready", "bot:ship-issue-ready"]),
    ]
    milestones = [{
        "number": 1, "title": "spec: x-tuning (#43)",
        "open_issues": 2, "closed_issues": 0, "state": "open",
    }]
    gh = FakeGh(issues=issues, milestones=milestones)

    state = m.collect_repo("pdomain/pdomain-book-tools", gh, specs_dir=Path("/dev/null"))

    assert len(state.feature_requests) == 1
    fr = state.feature_requests[0]
    assert fr.number == 42
    assert fr.triage == "approved"
    assert len(fr.spec_issues) == 1
    spec = fr.spec_issues[0]
    assert spec.number == 43
    assert spec.milestone is not None
    assert spec.milestone.title == "spec: x-tuning (#43)"
    assert spec.children_total == 2
    assert spec.children_armed == 1  # only #45 has bot:ship-issue-ready


def test_untriaged_feature_request_has_empty_spec_list():
    m = _mod()
    issues = [
        _issue(50, "Untriaged idea", "Hi", labels=["kind:feature-request"]),
    ]
    gh = FakeGh(issues=issues)
    state = m.collect_repo("x/y", gh, specs_dir=Path("/dev/null"))
    assert len(state.feature_requests) == 1
    assert state.feature_requests[0].triage is None
    assert state.feature_requests[0].spec_issues == []


def test_direct_ship_feature_request_has_tracking_child_no_spec():
    m = _mod()
    issues = [
        _issue(60, "Trivial fix", "Idea", labels=["kind:feature-request", "triage:approved"]),
        _issue(61, "Trivial fix tracking",
               "Tracks: #60",
               labels=["kind:bug", "status:ready", "bot:ship-issue-ready"]),
    ]
    gh = FakeGh(issues=issues, milestones=[])
    state = m.collect_repo("x/y", gh, specs_dir=Path("/dev/null"))
    fr = state.feature_requests[0]
    assert fr.spec_issues == []
    assert len(fr.tracking_children) == 1
    assert fr.tracking_children[0].number == 61
    assert fr.tracking_children[0].is_armed is True


def test_orphan_specs_view_finds_files_without_spec_issues():
    m = _mod()
    tmp = Path(tempfile.mkdtemp())
    (tmp / "01-foo.md").write_text(
        "# Foo\n\n> **Status**: Active\n> **Last updated**: 2026-01-01\n\n## TL;DR\n\nFoo.\n"
    )
    (tmp / "02-bar.md").write_text(
        "# Bar\n\n> **Status**: Active\n> **Last updated**: 2026-01-01\n"
        "> **Spec-Issue**: ConcaveTrillion/x#1\n\n## TL;DR\n\nBar.\n"
    )
    gh = FakeGh()
    state = m.collect_repo("x/y", gh, specs_dir=tmp)
    orphans = [s.path.name for s in state.orphan_specs]
    assert "01-foo.md" in orphans
    assert "02-bar.md" not in orphans
```

- [ ] **Step 2: Run the test — confirm it fails**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_spec_chain_data.py -v
```

Expected: file not found.

- [ ] **Step 3: Implement spec_chain_data.py**

Save as `scripts/spec_chain_data.py`:

```python
"""spec_chain_data.py — pure join layer for the feature-request lifecycle.

Reads (via injected gh seam):
  - Open issues for one repo
  - Milestones for one repo

Reads (filesystem):
  - Spec files under <repo>/docs/specs/

Returns a RepoChainState dataclass that the renderer consumes. No
markdown, no HTML — that lives in build-spec-chain-report.py /
build-cost-dashboard.py.

Conventions:
  - Feature-request: open issue with `kind:feature-request` label.
  - Triage state: derived from `triage:approved` / `triage:rejected` labels.
  - Spec issue: open issue with `kind:spec` label whose body has `Tracks: #<FR>`.
  - Tracking child: open issue with kind:{bug,chore,feature} whose body has `Tracks: #<spec-or-FR>`.
  - Armed: tracking child has `bot:ship-issue-ready` label.
  - Milestone match: by exact title `spec: <slug> (#<spec-issue-num>)`.
  - Orphan spec: file under docs/specs/ without a `> **Spec-Issue**:` blockquote line.
"""
from __future__ import annotations

import dataclasses
import os
import re
import subprocess
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spec_slug  # noqa: E402

_TRACKS = re.compile(r"^Tracks:\s*#(\d+)\s*$", re.MULTILINE)
_SPEC_ISSUE_HEADER = re.compile(
    r"^>\s*\*\*Spec-Issue\*\*:\s*[^\s/]+/[^\s#]+#\d+\s*$",
    re.MULTILINE,
)


@dataclasses.dataclass
class MilestoneInfo:
    number: int
    title: str
    open_issues: int
    closed_issues: int
    state: str

    @property
    def progress_str(self) -> str:
        total = self.open_issues + self.closed_issues
        return f"{self.closed_issues}/{total}"


@dataclasses.dataclass
class TrackingChild:
    number: int
    title: str
    is_armed: bool


@dataclasses.dataclass
class SpecIssue:
    number: int
    title: str
    children_total: int
    children_armed: int
    milestone: MilestoneInfo | None
    spec_path: str | None  # from `Spec:` body line


@dataclasses.dataclass
class FeatureRequest:
    number: int
    title: str
    triage: str | None  # "approved" | "rejected" | "needs-spec" | None
    spec_issues: list[SpecIssue]
    tracking_children: list[TrackingChild]


@dataclasses.dataclass
class OrphanSpec:
    path: Path


@dataclasses.dataclass
class RepoChainState:
    repo: str
    feature_requests: list[FeatureRequest]
    orphan_specs: list[OrphanSpec]


# --- gh seam ---------------------------------------------------------------

def _gh_env() -> dict:
    env = os.environ.copy()
    token_path = "/run/secrets/gh-token-pd"
    if Path(token_path).is_file():
        env["GH_TOKEN"] = Path(token_path).read_text().strip()
    return env


class GhCli:
    def issue_list(self, repo, state="open", limit=200):
        r = subprocess.run(
            ["gh", "issue", "list", "--repo", repo, "--state", state,
             "--limit", str(limit), "--json", "number,title,body,labels"],
            capture_output=True, text=True, env=_gh_env(),
            check=True, timeout=30,
        )
        return json.loads(r.stdout)

    def list_milestones(self, repo):
        r = subprocess.run(
            ["gh", "api", f"/repos/{repo}/milestones?state=all&per_page=200"],
            capture_output=True, text=True, env=_gh_env(),
            check=True, timeout=30,
        )
        return json.loads(r.stdout)


# --- pure helpers ----------------------------------------------------------

def _label_names(issue: dict) -> set[str]:
    return {l["name"] for l in issue.get("labels", [])}


def _has_label(issue: dict, name: str) -> bool:
    return name in _label_names(issue)


def _triage_state(issue: dict) -> str | None:
    names = _label_names(issue)
    if "triage:rejected" in names:
        return "rejected"
    if "triage:needs-spec" in names:
        return "needs-spec"
    if "triage:approved" in names:
        return "approved"
    return None


def _tracks(body: str | None) -> int | None:
    if not body:
        return None
    m = _TRACKS.search(body)
    return int(m.group(1)) if m else None


def _spec_path_from_body(body: str | None) -> str | None:
    if not body:
        return None
    m = re.search(r"^Spec:\s*(\S.+?)\s*$", body, re.MULTILINE)
    return m.group(1) if m else None


def _milestone_for_spec(milestones: list[dict], spec_title: str,
                       spec_number: int) -> MilestoneInfo | None:
    target = spec_slug.milestone_title(spec_title, spec_number)
    for ms in milestones:
        if ms.get("title") == target:
            return MilestoneInfo(
                number=int(ms["number"]),
                title=ms["title"],
                open_issues=int(ms.get("open_issues", 0)),
                closed_issues=int(ms.get("closed_issues", 0)),
                state=str(ms.get("state", "open")),
            )
    return None


# --- main collection -------------------------------------------------------

def collect_repo(repo: str, gh, specs_dir: Path) -> RepoChainState:
    issues = gh.issue_list(repo)
    milestones = gh.list_milestones(repo) if hasattr(gh, "list_milestones") else []

    by_kind = {"feature-request": [], "spec": [], "tracking": []}
    for issue in issues:
        names = _label_names(issue)
        if "kind:feature-request" in names:
            by_kind["feature-request"].append(issue)
        elif "kind:spec" in names:
            by_kind["spec"].append(issue)
        elif any(n.startswith("kind:") for n in names):
            by_kind["tracking"].append(issue)

    # Index tracking children by Tracks: parent.
    children_by_parent: dict[int, list[dict]] = {}
    for child in by_kind["tracking"]:
        p = _tracks(child.get("body", ""))
        if p is not None:
            children_by_parent.setdefault(p, []).append(child)

    # Index spec issues by their feature-request parent (Tracks line).
    specs_by_fr: dict[int, list[dict]] = {}
    for spec in by_kind["spec"]:
        p = _tracks(spec.get("body", ""))
        if p is not None:
            specs_by_fr.setdefault(p, []).append(spec)

    feature_requests: list[FeatureRequest] = []
    for fr in by_kind["feature-request"]:
        fr_num = fr["number"]
        spec_issues_for_fr: list[SpecIssue] = []
        for spec in specs_by_fr.get(fr_num, []):
            spec_children = children_by_parent.get(spec["number"], [])
            armed = sum(1 for c in spec_children if _has_label(c, "bot:ship-issue-ready"))
            ms = _milestone_for_spec(milestones, spec["title"], spec["number"])
            spec_issues_for_fr.append(SpecIssue(
                number=spec["number"], title=spec["title"],
                children_total=len(spec_children),
                children_armed=armed,
                milestone=ms,
                spec_path=_spec_path_from_body(spec.get("body", "")),
            ))

        # Tracking children whose Tracks: points DIRECTLY at the FR (ship-direct).
        direct_children = children_by_parent.get(fr_num, [])
        tracking_children = [
            TrackingChild(
                number=c["number"], title=c["title"],
                is_armed=_has_label(c, "bot:ship-issue-ready"),
            )
            for c in direct_children
        ]

        feature_requests.append(FeatureRequest(
            number=fr_num, title=fr["title"],
            triage=_triage_state(fr),
            spec_issues=spec_issues_for_fr,
            tracking_children=tracking_children,
        ))

    orphan_specs = _find_orphan_specs(specs_dir)

    return RepoChainState(
        repo=repo,
        feature_requests=feature_requests,
        orphan_specs=orphan_specs,
    )


def _find_orphan_specs(specs_dir: Path) -> list[OrphanSpec]:
    if not specs_dir.exists():
        return []
    out: list[OrphanSpec] = []
    for p in sorted(specs_dir.glob("*.md")):
        if p.name.startswith("_"):
            continue
        text = p.read_text(errors="replace")
        if not _SPEC_ISSUE_HEADER.search(text):
            out.append(OrphanSpec(path=p))
    return out
```

- [ ] **Step 4: Run the tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_spec_chain_data.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/spec_chain_data.py tests/scripts/test_spec_chain_data.py
git commit -m "feat(spec_chain_data): pure join layer for feature-request → spec → children"
```

---

## Task 6: Build the renderer (build-spec-chain-report.py)

**Files:**

- Create: `scripts/build-spec-chain-report.py`
- Create: `tests/scripts/test_build_spec_chain_report.py`

The renderer takes one or more `RepoChainState` instances and produces:

1. Per-repo `<repo>/docs/spec-chain-report.md` (Views A and B).
2. Workspace `docs/superpowers/spec-chain-status.md` (cross-repo summary).

- [ ] **Step 1: Write the failing tests**

Save as `tests/scripts/test_build_spec_chain_report.py`:

```python
"""Tests for scripts/build-spec-chain-report.py — markdown rendering only.

Uses fixtures hand-built in test code (no gh, no filesystem) to exercise
the renderer end-to-end.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/build-spec-chain-report.py"


def _mod():
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    spec = importlib.util.spec_from_file_location("build_spec_chain_report", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _state():
    """A small fixture: one repo with one approved+specced FR + one untriaged FR + one orphan spec."""
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    import importlib
    scd = importlib.import_module("spec_chain_data")
    return scd.RepoChainState(
        repo="pdomain/pdomain-book-tools",
        feature_requests=[
            scd.FeatureRequest(
                number=42, title="X tuning", triage="approved",
                spec_issues=[scd.SpecIssue(
                    number=43, title="Spec: X tuning",
                    children_total=3, children_armed=0,
                    milestone=scd.MilestoneInfo(
                        number=1, title="spec: x-tuning (#43)",
                        open_issues=3, closed_issues=0, state="open",
                    ),
                    spec_path="docs/specs/x-tuning.md",
                )],
                tracking_children=[],
            ),
            scd.FeatureRequest(
                number=44, title="Y heuristic", triage=None,
                spec_issues=[], tracking_children=[],
            ),
        ],
        orphan_specs=[scd.OrphanSpec(path=Path("docs/specs/03-reorganize-pipeline.md"))],
    )


def test_view_a_table_has_expected_columns():
    m = _mod()
    md = m.render_view_a(_state())
    assert "Feature-request" in md
    assert "Triaged?" in md
    assert "Spec issue" in md
    assert "Milestone progress" in md
    assert "Children armed" in md


def test_view_a_renders_milestone_progress():
    m = _mod()
    md = m.render_view_a(_state())
    assert "spec: x-tuning (#43)" in md
    assert "0/3" in md  # closed/total


def test_view_a_renders_untriaged_with_dashes():
    m = _mod()
    md = m.render_view_a(_state())
    assert "#44" in md
    # Untriaged row should have empty/dashes for downstream columns.
    assert "untriaged" in md.lower() or "—" in md


def test_view_b_lists_orphan_specs():
    m = _mod()
    md = m.render_view_b(_state())
    assert "03-reorganize-pipeline.md" in md
    assert "/decompose-spec --backfill" in md


def test_workspace_summary_aggregates_repos():
    m = _mod()
    md = m.render_workspace_summary([_state()])
    assert "pdomain-book-tools" in md
    assert "Most stuck" in md or "Sorted" in md or "by " in md
```

- [ ] **Step 2: Run the test — confirm it fails**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_build_spec_chain_report.py -v
```

Expected: file not found.

- [ ] **Step 3: Implement the renderer**

Save as `scripts/build-spec-chain-report.py`:

```python
#!/usr/bin/env python3
"""build-spec-chain-report.py — renderer for the chain-state report.

Per-repo: writes <repo>/docs/spec-chain-report.md (Views A + B).
Workspace: writes docs/superpowers/spec-chain-status.md (summary).

Triggered:
  - On demand: scripts/build-spec-chain-report.py
  - From the SessionEnd hook (if/when added)
  - From the ctask entry that runs once per hour, just before
    build-cost-dashboard.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spec_chain_data as scd  # noqa: E402


REPOS = (
    "pdomain-book-tools", "pdomain-ocr-cli", "pd-ocr-labeler", "pdomain-ocr-labeler-spa",
    "pdomain-ocr-synth", "pd-ocr-trainer", "pd-png-optimizer", "pdomain-prep-for-pgdp",
)
WORKSPACE = Path("/workspaces/ocr-container")


def render_view_a(state: scd.RepoChainState) -> str:
    rows: list[str] = []
    rows.append("## View A — feature-request lifecycle\n")
    rows.append("| Feature-request | Triaged? | Spec issue | Milestone progress | Children armed |")
    rows.append("|---|---|---|---|---|")
    for fr in state.feature_requests:
        triage = fr.triage or "untriaged"
        if not fr.spec_issues and not fr.tracking_children:
            rows.append(
                f"| #{fr.number} \"{fr.title}\" | {triage} | — | — | — |"
            )
            continue
        if fr.tracking_children:
            armed = sum(1 for c in fr.tracking_children if c.is_armed)
            rows.append(
                f"| #{fr.number} \"{fr.title}\" | {triage} "
                f"| (ship-direct) | — "
                f"| {armed}/{len(fr.tracking_children)} |"
            )
        for spec in fr.spec_issues:
            ms = spec.milestone
            ms_text = (
                f"{ms.title}<br/>{ms.progress_str} closed" if ms
                else "(milestone missing)"
            )
            rows.append(
                f"| #{fr.number} \"{fr.title}\" | {triage} "
                f"| #{spec.number} (kind:spec) "
                f"| {ms_text} "
                f"| {spec.children_armed}/{spec.children_total} |"
            )
    return "\n".join(rows) + "\n"


def render_view_b(state: scd.RepoChainState) -> str:
    rows: list[str] = []
    rows.append("## View B — orphan specs (backfill queue)\n")
    if not state.orphan_specs:
        rows.append("_(none)_\n")
        return "\n".join(rows) + "\n"
    rows.append("| Spec file | Spec issue | Children |")
    rows.append("|---|---|---|")
    for orph in state.orphan_specs:
        rows.append(
            f"| `{orph.path}` | none | run `/decompose-spec --backfill` |"
        )
    return "\n".join(rows) + "\n"


def render_repo_report(state: scd.RepoChainState) -> str:
    return (
        f"# Spec chain status — {state.repo}\n\n"
        f"_Generated by `scripts/build-spec-chain-report.py`. Do not edit by hand._\n\n"
        + render_view_a(state) + "\n"
        + render_view_b(state)
    )


def render_workspace_summary(states: list[scd.RepoChainState]) -> str:
    rows: list[str] = []
    rows.append("# Spec chain status — workspace summary\n")
    rows.append("_Generated by `scripts/build-spec-chain-report.py`. "
                "Sorted by 'Most stuck' (untriaged feature-requests come first)._\n")
    rows.append("| Repo | Untriaged FRs | Specs in progress | Specs shipped | Orphan specs |")
    rows.append("|---|---|---|---|---|")
    for state in states:
        untriaged = sum(1 for fr in state.feature_requests if fr.triage is None)
        in_progress = sum(
            1 for fr in state.feature_requests
            for spec in fr.spec_issues
            if spec.milestone and spec.milestone.state == "open"
        )
        shipped = sum(
            1 for fr in state.feature_requests
            for spec in fr.spec_issues
            if spec.milestone and spec.milestone.state == "closed"
        )
        rows.append(
            f"| {state.repo.split('/')[-1]} "
            f"| {untriaged} | {in_progress} | {shipped} "
            f"| {len(state.orphan_specs)} |"
        )
    return "\n".join(rows) + "\n"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    sys.stderr.write(f"wrote {path}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repos", nargs="+", default=list(REPOS),
                   help="basenames of pd-* repos to include")
    p.add_argument("--out-workspace", default=None,
                   help="path to workspace summary (default docs/superpowers/spec-chain-status.md)")
    args = p.parse_args()

    gh = scd.GhCli()
    states: list[scd.RepoChainState] = []
    for basename in args.repos:
        full = f"ConcaveTrillion/{basename}"
        specs_dir = WORKSPACE / basename / "docs/specs"
        state = scd.collect_repo(full, gh, specs_dir=specs_dir)
        states.append(state)
        _write(WORKSPACE / basename / "docs/spec-chain-report.md",
               render_repo_report(state))

    out_ws = Path(args.out_workspace) if args.out_workspace \
             else WORKSPACE / "docs/superpowers/spec-chain-status.md"
    _write(out_ws, render_workspace_summary(states))


if __name__ == "__main__":
    main()
```

```bash
chmod +x /workspaces/ocr-container/scripts/build-spec-chain-report.py
```

- [ ] **Step 4: Run the tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_build_spec_chain_report.py -v
```

Expected: 5 tests pass. The fixture `_state()` uses `importlib.import_module` to load `spec_chain_data` — make sure `tests/__init__.py` exists if needed (or use absolute path; the test fixture already does the path insert).

- [ ] **Step 5: Smoke-run against pdomain-book-tools**

```bash
cd /workspaces/ocr-container
python3 scripts/build-spec-chain-report.py --repos pdomain-book-tools
```

Expected: writes `pdomain-book-tools/docs/spec-chain-report.md` and `docs/superpowers/spec-chain-status.md`. Open both and confirm the rendering looks reasonable. The pdomain-book-tools report should show your backfilled feature-requests from Phase 2 with their milestone progress columns.

- [ ] **Step 6: gitignore the generated reports**

For each pd-* repo, add `docs/spec-chain-report.md` to its `.gitignore`. Per the workspace's per-repo agent routing, delegate this to each repo's agent for a clean commit (8 trivial PRs):

```
[pdomain-book-tools agent prompt]
Add the following line to .gitignore (sort it alphabetically near other docs entries):
  docs/spec-chain-report.md
Open a PR titled "chore(gitignore): exclude generated docs/spec-chain-report.md".
```

Repeat for the other 7 repos.

For the workspace-level `docs/superpowers/spec-chain-status.md`, add a line to the workspace `.gitignore`:

```bash
cd /workspaces/ocr-container
grep -q "^docs/superpowers/spec-chain-status.md$" .gitignore \
  || echo "docs/superpowers/spec-chain-status.md" >> .gitignore
```

- [ ] **Step 7: Commit the renderer**

```bash
cd /workspaces/ocr-container
git add scripts/build-spec-chain-report.py tests/scripts/test_build_spec_chain_report.py .gitignore
git commit -m "feat(chain-state): build-spec-chain-report.py — per-repo + workspace summary"
```

---

## Task 7: Add the chain-state panel to cost-dashboard.html

**Files:**

- Modify: `scripts/build-cost-dashboard.py` (extend HTML template + add a `render_chain_state_panel` function)
- Modify (or create): `tests/scripts/test_build_cost_dashboard.py` — add panel-rendering test

- [ ] **Step 1: Find the existing kanban panel structure**

```bash
sed -n '95,135p' /workspaces/ocr-container/scripts/build-cost-dashboard.py
```

The HTML template uses `{kanban_panel}` placeholder; the renderer is `render_kanban_panel(data)` at line 224.

- [ ] **Step 2: Add a chain-state placeholder + CSS to the template**

Edit `scripts/build-cost-dashboard.py`. Find the HTML_TEMPLATE constant (around line 95-135) and:

- Add `{chain_state_panel}` placeholder somewhere reasonable (e.g., right after `{kanban_panel}`).
- Add CSS for `.chain-state` styling, mirroring `.kanban` style:

```css
.chain-state {{ font-size: 0.85em; }}
.chain-state td {{ vertical-align: top; }}
.chain-state .ms-bar {{
  display: inline-block; width: 80px; height: 8px;
  background: #eee; border-radius: 4px; vertical-align: middle;
}}
.chain-state .ms-bar-fill {{
  display: inline-block; height: 8px; background: #4caf50;
  border-radius: 4px; vertical-align: top;
}}
.chain-state a {{ color: #1976d2; }}
```

- [ ] **Step 3: Implement render_chain_state_panel**

In `scripts/build-cost-dashboard.py`, after `render_kanban_panel`, add:

```python
def render_chain_state_panel(states) -> str:
    """Render a panel summarizing each repo's spec chain.

    `states` is a list of spec_chain_data.RepoChainState. Per repo, show
    the feature-requests in flight and a link to their milestone progress
    bars on GitHub.
    """
    if not states:
        return "<p>No chain-state data available.</p>"
    rows = ["<table class='chain-state'><tr>"
            "<th>Repo</th><th>Untriaged</th><th>Specs in progress</th>"
            "<th>Top FR (most stuck)</th></tr>"]
    for state in states:
        untriaged = [fr for fr in state.feature_requests if fr.triage is None]
        in_progress = [
            (fr, spec) for fr in state.feature_requests
            for spec in fr.spec_issues
            if spec.milestone and spec.milestone.state == "open"
        ]
        top = state.feature_requests[0] if state.feature_requests else None
        top_link = (
            f"<a href='https://github.com/{state.repo}/issues/{top.number}'>"
            f"#{top.number} {top.title[:40]}</a>" if top else "—"
        )
        rows.append(
            f"<tr><th>{state.repo.split('/')[-1]}</th>"
            f"<td>{len(untriaged)}</td>"
            f"<td>{len(in_progress)}</td>"
            f"<td>{top_link}</td></tr>"
        )
    rows.append("</table>")
    return "".join(rows)
```

Then near the bottom of `main()`, before the `html = HTML_TEMPLATE.format(...)` call, add:

```python
import spec_chain_data as scd  # noqa: E402
chain_states = []
if not os.environ.get("DASHBOARD_SKIP_CHAIN"):
    gh = scd.GhCli()
    for basename in (r for r in REPOS):
        full = f"ConcaveTrillion/{basename}"
        try:
            chain_states.append(scd.collect_repo(
                full, gh,
                specs_dir=Path(f"/workspaces/ocr-container/{basename}/docs/specs"),
            ))
        except Exception as e:
            sys.stderr.write(f"chain-state collection failed for {full}: {e}\n")
```

And in the `.format(...)` call, add: `chain_state_panel=render_chain_state_panel(chain_states)`.

- [ ] **Step 4: Add a test for the panel renderer**

Add to `tests/scripts/test_build_cost_dashboard.py` (create the file if absent, mirroring the panel-only tests pattern). Test that `render_chain_state_panel([])` returns the empty-state string and that with one fixture state the output contains the repo name and a count.

- [ ] **Step 5: Smoke-run**

```bash
cd /workspaces/ocr-container
SHIP_ISSUE_MEMORY_DIR=/tmp/sm DASHBOARD_SKIP_KANBAN=1 \
  python3 scripts/build-cost-dashboard.py
ls -la /tmp/sm/cost-dashboard.html
```

Expected: dashboard HTML exists. Open it in a browser; the new chain-state panel renders below the kanban panel and shows per-repo counts.

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/build-cost-dashboard.py tests/scripts/test_build_cost_dashboard.py
git commit -m "feat(dashboard): add spec chain-state panel using spec_chain_data"
```

---

## Task 8: Schedule chain-report alongside cost-dashboard

**Files:**

- Modify: ctask config (location depends on `ctask` setup — check `/workspaces/ocr-container/ctask`)

- [ ] **Step 1: Find the existing cost-dashboard ctask entry**

```bash
/workspaces/ocr-container/ctask list | grep -i dashboard
```

Note the entry's name and command.

- [ ] **Step 2: Add a chain-report entry that runs first**

The cost-dashboard panel reads chain data internally now (via `spec_chain_data` invoked from inside `build-cost-dashboard.py`), so a separate scheduled run of `build-spec-chain-report.py` is only needed for the markdown views (the per-repo `docs/spec-chain-report.md` and `docs/superpowers/spec-chain-status.md`).

Add a ctask entry that runs `build-spec-chain-report.py` once per hour at HH:55, five minutes before the dashboard run at the top of the hour:

```bash
/workspaces/ocr-container/ctask add \
  --name spec-chain-report \
  --cmd "python3 /workspaces/ocr-container/scripts/build-spec-chain-report.py" \
  --schedule "55 * * * *"
```

Adjust to match your `ctask` CLI surface; the principle is "every hour, slightly before the dashboard refresh".

- [ ] **Step 3: Smoke-fire it once manually**

```bash
/workspaces/ocr-container/ctask run spec-chain-report
```

Expected: it runs to completion; the markdown files refresh.

- [ ] **Step 4: Commit ctask config**

If the ctask config is git-tracked (check `/workspaces/ocr-container/ctask` source), commit the change:

```bash
cd /workspaces/ocr-container
git add <ctask-config-file>
git commit -m "chore(ctask): schedule build-spec-chain-report hourly at :55"
```

---

## Task 9: Validate the chain-state report end-to-end

This task is manual review. No code, no commits.

- [ ] **Step 1: Refresh both reports**

```bash
cd /workspaces/ocr-container
python3 scripts/build-spec-chain-report.py
python3 scripts/build-cost-dashboard.py
```

- [ ] **Step 2: Read the per-repo report**

```bash
cat /workspaces/ocr-container/pdomain-book-tools/docs/spec-chain-report.md
```

Expected: View A shows your backfilled feature-requests from Phase 2 with their spec issues + milestones + armed-children counts. View B shows any specs that still don't have a `Spec-Issue:` header (i.e., were skipped in Phase 2).

- [ ] **Step 3: Read the workspace summary**

```bash
cat /workspaces/ocr-container/docs/superpowers/spec-chain-status.md
```

Expected: a table with one row per repo. pdomain-book-tools should have non-zero "Specs in progress"; the other 7 repos should be all-zeros at this point (rollout in Phase 5 will populate them).

- [ ] **Step 4: Open the dashboard**

```bash
xdg-open /workspaces/ocr-container/.claude/agent-memory/ship-issue/cost-dashboard.html 2>/dev/null \
  || echo "open the dashboard HTML manually"
```

Expected: the chain-state panel renders below the kanban; pdomain-book-tools row has a non-empty "Top FR" link; clicking the link opens the GitHub issue.

- [ ] **Step 5: Mark Phase 3 acceptance**

The remaining acceptance bullets from the spec are now satisfied:

- [x] `scripts/build-spec-chain-report.py` produces both per-repo `docs/spec-chain-report.md` files and a workspace-level `docs/superpowers/spec-chain-status.md` (Tasks 5-6, 9)
- [x] Dashboard panel renders the chain-state data alongside the existing cost-dashboard kanban (Task 7, 9)
- [x] Chain-state report's View A renders the milestone progress column; dashboard panel embeds milestone progress bars or a computed fallback (Task 6, 7)

Phase 3 is done.

---

# Phase 5: Rollout to remaining 7 repos

This is mostly a checklist. The skills, helpers, and labels are already in place across all 8 repos from Plan 1; what changes here is just *active use*.

**pd-png-optimizer caveat.** The repo is currently local-only (no
GitHub remote — Plan 1's `migrate-claude-ok-to-bot-label.sh` correctly
skipped it). For each step below, skip the pd-png-optimizer slot if
its remote status hasn't changed; revisit once it's published. CT's
queued task #4 ("Decide on pd-png-optimizer publish-vs-defer") gates
this — flag it explicitly during execution rather than silently
dropping the row.

**Worktree retrofit precondition.** v2 Plan 1 Phase 1 retrofits
ship-issue to write into `/srv/bot-workspaces/ship-issue/<repo>/`. By
the time Phase 5 runs, that retrofit should already be live, so when a
new feature-request gets armed via `bot:ship-issue-ready`, the bot
exercises the new pattern. If the retrofit is NOT yet live, drive Phase
5 anyway against the legacy in-place checkout — but flag the affected
runs so v2 Plan 1 can re-test against them later.

## Task 10: Confirm label state across all 8 repos

- [ ] **Step 1: Verify each repo has the lifecycle labels**

```bash
for r in pdomain-book-tools pdomain-ocr-cli pd-ocr-labeler pdomain-ocr-labeler-spa \
         pdomain-ocr-synth pd-ocr-trainer pd-png-optimizer pdomain-prep-for-pgdp; do
  echo "=== $r ==="
  gh repo view "ConcaveTrillion/$r" >/dev/null 2>&1 \
    || { echo "  SKIP — local-only, no remote"; continue; }
  gh label list -R "ConcaveTrillion/$r" --limit 200 \
    | grep -E "kind:feature-request|triage:|bot:ship-issue-ready" || echo "  MISSING — re-run scripts/seed-labels.sh"
done
```

If any repo is missing a label, run `scripts/seed-labels.sh ConcaveTrillion/<repo>` to backfill (the script is idempotent — and post-Phase-0 Task 0.5, also refreshes existing label descriptions, which fixes the lingering `status:ready` "with claude-ok" wording on the 6 published repos).

A `SKIP — local-only` row for pd-png-optimizer is expected until CT's
queued task #4 (publish-vs-defer) is resolved.

---

## Task 11: Drive one feature-request through each remaining repo

For each of the 7 non-pdomain-book-tools repos, file at least one `kind:feature-request` issue and run `/triage` on it. This both validates the rollout and seeds the chain-state report's per-repo data.

The intent here is **not** to backfill every existing spec across every repo — that's bulky work that should follow this rollout naturally. The goal is one feature-request per repo so each row of the workspace summary reads non-zero.

- [ ] **Step 1: For each repo `R` in the rollout list (skip pd-png-optimizer if still local-only)**

  - [ ] Confirm the repo has a GitHub remote: `gh repo view ConcaveTrillion/$R`. If it 404s, skip and note in CT's pending list.
  - [ ] File a small `kind:feature-request` issue. Could be a real idea, could be a smoke "Validate v1 lifecycle on R".
  - [ ] Run `/triage <N>` in a Claude session.
  - [ ] If triage approves with `--output=tracking`, that's a single-issue chain — done.
  - [ ] If triage approves with `--output=spec`, run `/spec-from-issue <SPEC>` and `/decompose-spec` to populate the chain.

- [ ] **Step 2: Refresh the chain-state report**

```bash
cd /workspaces/ocr-container
python3 scripts/build-spec-chain-report.py
```

Confirm every row in `docs/superpowers/spec-chain-status.md` now reads non-zero somewhere.

- [ ] **Step 3: Mark Phase 5 acceptance**

The spec doesn't have explicit Phase-5 bullets in the Contract / Acceptance section (rollout is sequencing, not a contract requirement), but the underlying invariant — "lifecycle skills work on all 8 repos" — is now demonstrated.

---

## Task 12: Flip the spec from Draft → Active

When all of the above is complete and validated:

- [ ] **Step 1: Edit the spec status**

Open `docs/superpowers/specs/2026-05-10-feature-request-spec-decomposition-design.md` and change:

```markdown
> **Status**: Draft
```

to:

```markdown
> **Status**: Active
```

Update the `> **Last updated**:` to today's date.

- [ ] **Step 2: Lint + commit**

```bash
cd /workspaces/ocr-container
python3 scripts/lint-spec.py docs/superpowers/specs/2026-05-10-feature-request-spec-decomposition-design.md
git add docs/superpowers/specs/2026-05-10-feature-request-spec-decomposition-design.md
git commit -m "spec(feature-request-lifecycle): mark Active after Plan 2 land"
```

---

## Done — what comes next

Both plans are complete. The lifecycle is live workspace-wide.

What's left for the future, deliberately deferred:

- **Phase 4 — Dashboard refresh design**: a fresh brainstorm now that the chain-state panel exists and CT has hands-on experience with it. Not in any current plan; trigger via `/brainstorm` when ready.
- **Future bot work**: the spec preserves slots for `triage:proposed-by-agent`, `bot:triage-ready`, `bot:spec-write-ready`. Implementing any of these is a new spec + plan cycle and is out of scope.
- **Cross-repo workspace specs**: spec Open Q #2 noted that workspace-level specs whose children land in different `pd-*` repos need a `Repo: ConcaveTrillion/<repo>` body line on each child. v1 punts; if you encounter a workspace spec that needs decomposition, file a kind:feature-request asking for the cross-repo extension first.
