---
status: complete
---

# pdomain-ocr-labeler-spa Bot Rollout Debrief — 2026-05-11

## Summary

Second-repo rollout of the ship-issue / style-review / style-sweep pipeline
to pdomain-ocr-labeler-spa (FastAPI + React/Vite/TS SPA replacing NiceGUI labeler).

## Phase outcomes

### Phase 1 — Label hygiene
Labels were already identical to pdomain-book-tools (synced at repo creation). No
labels created. 0 single-select violations found.

### Phase 2 — CONVENTIONS.md
4 per-repo rules added below the workspace-conventions block:
1. OpenAPI types are generated, never hand-edited
2. data-testid values must match specs/13-driver-contract.md exactly
3. FastAPI route handlers must declare an explicit response_model
4. New stateful React components require a Vitest test file

Committed: `chore: add per-repo conventions (FastAPI+React patterns)`

### Phase 3 — ctask registration
Three ctasks registered and started:
- ship-issue-pdomain-ocr-labeler-spa (interval: 30 min)
- style-review-pdomain-ocr-labeler-spa (interval: 24 hr)
- style-sweep-pdomain-ocr-labeler-spa (interval: 7 days)

### Phase 4 — Worktree bootstrap
Three worktrees created (claude-bot owned):
- /srv/bot-workspaces/ship-issue/pdomain-ocr-labeler-spa (wip/ship-issue)
- /srv/bot-workspaces/style-review/pdomain-ocr-labeler-spa (wip/ship-issue)
- /srv/bot-workspaces/style-sweep/pdomain-ocr-labeler-spa (wip/style-sweep)

PAT (/run/secrets/gh-token-pd) confirmed push access.

### Phase 5 — Spec migration
All 21 spec docs (specs/00-overview.md through specs/20-glyph-annotations.md)
migrated:
- 42 GitHub issues filed: 21 kind:feature-request + 21 kind:spec, all
  triage:approved, all cross-linked (FR→spec via "Tracks:", spec→FR via "FR:")
- All spec files have Status/Last-updated/Spec-Issue frontmatter
- specs/.specrc created: exempts all 21 specs from Rule 1 (9-section template),
  raises line cap for 17-decisions.md to 2000
- All specs pass lint-spec.py and markdownlint-cli2
- Spec-chain parser required "Tracks:" format (not "FR:"); the Phase 7+8 agent
  caught and fixed this for all 9 initially-filed specs.

Commit: `ce97c59` — `chore: backfill spec frontmatter + FR/spec issues for all 21 specs`

### Phase 6 — Decompose first milestone
Structural difference discovered: pdomain-ocr-labeler-spa uses one milestones doc
(specs/16-milestones.md) covering M0–M9, whereas pdomain-book-tools has one spec
per milestone. Running decompose-spec on the milestones doc produced one
undifferentiated child — wrong.

User directed: refactor to per-spec decomposition with fine-grained chore
issues and Blocked-by dependency chains. decompose-spec was run on
specs/01-data-models.md (spec issue #6) as the first pilot:

Milestone created: "spec: 01-data-models (#6)" (GitHub milestone #1)
10 children filed (#45–#54), in 4 dependency waves:
- Wave 1 (haiku/S): core domain models, match-state+geometry, Selection+LineFilter
- Wave 2 (haiku/S): project/page wire shapes, word/line wire shapes, refine/job/error wire shapes
- Wave 3 (sonnet/M): UserPageEnvelope, project.json/pages.json, session/config
- Wave 4 (sonnet/M): conformance fixtures + UserPageEnvelope integration tests

Blocked-by chains: #46→#45, #47→#46, #48→#45,46, #49→#48, #50→#49,
#51→#45,46, #52→#45, #53→#45, #54→#51

### Phase 7 — Roadmap rendering

`scripts/build-spec-chain-report.py` ran successfully and produced two files:
- `pdomain-ocr-labeler-spa/docs/spec-chain-report.md` (per-repo detail)
- `docs/superpowers/spec-chain-status.md` (workspace summary)

**Workspace summary row:** `pdomain-ocr-labeler-spa | 0 | 0 | 0 | 0`

The zeroes reflect a classification gap: all 20 feature-request issues are
marked `triage:needs-spec` (not `triage:approved`), so the parser counts
zero "approved" FRs and zero "specs in progress." The issues are properly
cross-linked (#3→#4, #5→#6, #7→#8, …, #43 no link yet), but the label
mismatch means View A shows every FR as "needs-spec" even for specs that
already exist.

**View A detail (20 feature-request rows):**
- #3, #5, #7, #9, #11, #13, #15, #17, #19 — each has a paired kind:spec
  issue (#4, #6, #8, #10, #12, #14, #16, #18, #20) but milestone is missing
  for most; children armed 0/0 except #5→#6 which shows 0/10 (Wave 1–4
  children decomposed but not yet armed)
- #21 through #43 (odd-numbered) — no spec issue linked yet; parser shows "—"

**View B — orphan specs:** none (all spec issues are reachable from a FR).

**Root cause of zero summary:** The `triage:needs-spec` label was applied to
all FRs during bulk creation. FRs that already have a spec issue should be
re-labelled `triage:approved`. This is a label cleanup task, not a code or
parser bug.

### Phase 8 — First bot fire
ship-issue: no-op (no bot:ship-issue-ready issues). Expected — no issues armed yet.
style-review: no-op (no wip/ship-issue branch). Expected.
style-sweep: FAILED — missing `fast-check` Makefile target (see Bugs Found).

## Bugs found during rollout

### Bug 1 — style-sweep: missing `fast-check` target
**Symptom:** style-sweep-orchestrator first run failed:
`make: *** No rule to make target 'fast-check'. Stop.`

**Root cause:** `scripts/style-review-apply.py:134` hardcodes `["make", "fast-check"]`
as the lint gate after every patch application. `fast-check` exists in
pdomain-book-tools/Makefile as `fast-check: lint` but was not present in
pdomain-ocr-labeler-spa/Makefile.

The patch failure on `request_id.py:157` was a cascade symptom: the missing
target triggered the abort path, which logged the file being patched at that moment.

**Fix:** Added `fast-check: lint` alias + `.PHONY` entry to
pdomain-ocr-labeler-spa/Makefile. Commit `d221391`.

**Scope:** Any new pd-* repo onboarded to style-sweep needs `fast-check` in its
Makefile. Candidate for workspace-canonical sync in future.

### Bug 2 — Spec-chain parser: "Tracks:" format strict
**Symptom:** Phase 5 agent initially filed FR issues with `FR: #N` in the body
instead of `Tracks: #N`. The spec-chain-report parser (`spec_chain_data.py:49`)
matches `^Tracks:\s*#(\d+)\s*$` exactly and showed 0 resolved links.

**Fix:** Phase 7+8 agent patched all affected FR issue bodies via `gh issue edit`.
**Scope:** The spec migration prompt for future repos should specify `Tracks: #N`
format explicitly (not `FR: #N`).

## Next steps

1. **Arm first issues:** Apply `bot:ship-issue-ready` + `status:ready` to
   issues #45 and #48 (Wave 1, no Blocked-by) to enable first real ship-issue cycle.
   Use `scripts/arm-issue.py --force` with justification noted.

2. **Fix FR labels:** Re-label FRs #3, #5, #7, #9, #11, #13, #15, #17, #19
   from `triage:needs-spec` to `triage:approved` so the spec-chain parser
   correctly counts them as "specs in progress" rather than "untriaged."

3. **Decompose remaining specs:** Run decompose-spec on specs/02-backend.md,
   specs/03-frontend.md, etc., continuing the per-spec milestone pattern.
   As issues surface cross-repo concerns (e.g. BBox/EncodedDims already in
   pdomain-book-tools), file blocking issues in the upstream repo.

4. **Confirm auto-merge policy:** Per constraint — do not enable auto-merge-wip-prs
   until first ship-issue cycle runs cleanly.

5. **Milestone alignment:** The delivery milestones (M0–M9 in specs/16-milestones.md)
   and the spec milestones (one per spec area file) are two parallel tracking axes.
   Consider adding a "milestone:" field to spec issue bodies to link spec milestones
   to delivery milestones.
