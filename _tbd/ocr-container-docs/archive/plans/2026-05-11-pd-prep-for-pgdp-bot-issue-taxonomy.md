---
status: complete
---

# pdomain-prep-for-pgdp Bot Wiring + Issue Taxonomy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enroll pdomain-prep-for-pgdp in the workspace bot suite, fix cross-repo label gaps, and file the full roadmap issue set so ship-issue + decompose-spec can schedule delivery.

**Architecture:** Five independent task groups (A–E) with no shared state — all can run in parallel. No code changes; all work is `gh` CLI and `ctask` CLI commands. Verification is checking GitHub/ctask state after each command group.

**Tech Stack:** `gh` CLI (GitHub), `/workspaces/ocr-container/ctask` (tmux task scheduler)

---

## Task A: Label sync across repos

**Files:** None (GitHub label mutations only)

**Repos touched:** pdomain/pdomain-book-tools, pdomain/pdomain-ocr-labeler-spa, pdomain/pdomain-prep-for-pgdp

- [ ] **Step 1: Add missing labels to pdomain-book-tools**

```bash
gh label create --repo pdomain/pdomain-book-tools \
  --name "bot:ship-issue-ready" \
  --color "0e8a16" \
  --description "Bot-eligibility gate — ship-issue may modify this issue" \
  --force

gh label create --repo pdomain/pdomain-book-tools \
  --name "kind:feature-request" \
  --color "c5def5" \
  --description "Idea pre-triage; will fork a tracking or spec issue" \
  --force

gh label create --repo pdomain/pdomain-book-tools \
  --name "status:bounced" \
  --color "e4e669" \
  --description "Workflow: bot could not ship — needs human triage" \
  --force
```

- [ ] **Step 2: Add missing labels to pdomain-ocr-labeler-spa**

```bash
gh label create --repo pdomain/pdomain-ocr-labeler-spa \
  --name "status:ready" \
  --color "0e8a16" \
  --description "Workflow: queued for ship-issue (with bot:ship-issue-ready) or you" \
  --force

gh label create --repo pdomain/pdomain-ocr-labeler-spa \
  --name "status:in-progress" \
  --color "fbca04" \
  --description "Workflow: currently being worked on" \
  --force

gh label create --repo pdomain/pdomain-ocr-labeler-spa \
  --name "status:bounced" \
  --color "e4e669" \
  --description "Workflow: bot could not ship — needs human triage" \
  --force
```

- [ ] **Step 3: Add missing labels to pdomain-prep-for-pgdp**

```bash
gh label create --repo pdomain/pdomain-prep-for-pgdp \
  --name "status:ready" \
  --color "0e8a16" \
  --description "Workflow: queued for ship-issue (with bot:ship-issue-ready) or you" \
  --force

gh label create --repo pdomain/pdomain-prep-for-pgdp \
  --name "status:in-progress" \
  --color "fbca04" \
  --description "Workflow: currently being worked on" \
  --force

gh label create --repo pdomain/pdomain-prep-for-pgdp \
  --name "status:bounced" \
  --color "e4e669" \
  --description "Workflow: bot could not ship — needs human triage" \
  --force
```

- [ ] **Step 4: Verify all labels are present**

```bash
echo "=== pdomain-book-tools ===" && \
  gh label list --repo pdomain/pdomain-book-tools | grep -E "bot:|status:|kind:feature-request"

echo "=== pdomain-ocr-labeler-spa ===" && \
  gh label list --repo pdomain/pdomain-ocr-labeler-spa | grep "status:"

echo "=== pdomain-prep-for-pgdp ===" && \
  gh label list --repo pdomain/pdomain-prep-for-pgdp | grep "status:"
```

Expected — pdomain-book-tools shows `bot:ship-issue-ready`, `kind:feature-request`, `status:bounced`, `status:in-progress`, `status:ready`. Both spa and pgdp show all three `status:` labels including `status:bounced`.

---

## Task B: ctask wiring

**Files:** `~/.local/share/claude-tasks/tasks.json` (written by ctask, not directly)

- [ ] **Step 1: Add ship-issue-pdomain-prep-for-pgdp**

```bash
/workspaces/ocr-container/ctask add ship-issue-pdomain-prep-for-pgdp \
  --interval 1800 \
  --dir /workspaces/ocr-container \
  --prompt "sudo -u claude-bot bash -c 'env -u GH_TOKEN /workspaces/ocr-container/scripts/ship-issue-orchestrator.sh --repo pdomain/pdomain-prep-for-pgdp --runs 1'"
```

- [ ] **Step 2: Add style-review-pdomain-prep-for-pgdp**

```bash
/workspaces/ocr-container/ctask add style-review-pdomain-prep-for-pgdp \
  --interval 86400 \
  --dir /workspaces/ocr-container \
  --prompt "sudo -u claude-bot bash -c 'env -u GH_TOKEN /workspaces/ocr-container/scripts/style-review-orchestrator.sh --repo pdomain/pdomain-prep-for-pgdp'"
```

- [ ] **Step 3: Add style-sweep-pdomain-prep-for-pgdp**

```bash
/workspaces/ocr-container/ctask add style-sweep-pdomain-prep-for-pgdp \
  --interval 604800 \
  --dir /workspaces/ocr-container \
  --prompt "sudo -u claude-bot bash -c 'env -u GH_TOKEN /workspaces/ocr-container/scripts/style-sweep-orchestrator.sh --repo pdomain/pdomain-prep-for-pgdp'"
```

- [ ] **Step 4: Add decompose-spec-pdomain-prep-for-pgdp**

```bash
/workspaces/ocr-container/ctask add decompose-spec-pdomain-prep-for-pgdp \
  --interval 604800 \
  --dir /workspaces/ocr-container \
  --prompt "sudo -u claude-bot bash -c 'env -u GH_TOKEN /workspaces/ocr-container/scripts/decompose-spec-auto-orchestrator.sh --repo pdomain/pdomain-prep-for-pgdp --model sonnet'"
```

- [ ] **Step 5: Add decompose-spec-pdomain-book-tools**

```bash
/workspaces/ocr-container/ctask add decompose-spec-pdomain-book-tools \
  --interval 604800 \
  --dir /workspaces/ocr-container \
  --prompt "sudo -u claude-bot bash -c 'env -u GH_TOKEN /workspaces/ocr-container/scripts/decompose-spec-auto-orchestrator.sh --repo pdomain/pdomain-book-tools --model sonnet'"
```

- [ ] **Step 6: Start all 5 tasks**

```bash
/workspaces/ocr-container/ctask start ship-issue-pdomain-prep-for-pgdp
/workspaces/ocr-container/ctask start style-review-pdomain-prep-for-pgdp
/workspaces/ocr-container/ctask start style-sweep-pdomain-prep-for-pgdp
/workspaces/ocr-container/ctask start decompose-spec-pdomain-prep-for-pgdp
/workspaces/ocr-container/ctask start decompose-spec-pdomain-book-tools
```

- [ ] **Step 7: Verify all 5 are running**

```bash
/workspaces/ocr-container/ctask list | grep -E "pdomain-prep-for-pgdp|decompose-spec-pdomain-book-tools"
```

Expected: 5 rows, all showing `RUNNING`.

---

## Task C: Triage existing open issues (#1 and #2)

**Repo:** pdomain/pdomain-prep-for-pgdp

- [ ] **Step 1: Label issue #1 (requires-python upper bound)**

```bash
gh issue edit 1 --repo pdomain/pdomain-prep-for-pgdp \
  --add-label "kind:chore,effort:S,model:haiku,model-effort:low,status:backlog"
```

- [ ] **Step 2: Label issue #2 (oxipng)**

```bash
gh issue edit 2 --repo pdomain/pdomain-prep-for-pgdp \
  --add-label "kind:feature,effort:M,model:sonnet,model-effort:medium,status:backlog"
```

- [ ] **Step 3: Verify labels on both issues**

```bash
gh issue view 1 --repo pdomain/pdomain-prep-for-pgdp --json labels \
  -q '.labels[].name' | sort

gh issue view 2 --repo pdomain/pdomain-prep-for-pgdp --json labels \
  -q '.labels[].name' | sort
```

Expected for #1: `effort:S kind:chore model-effort:low model:haiku status:backlog`
Expected for #2: `effort:M kind:feature model-effort:medium model:sonnet status:backlog`

---

## Task D: File M2 carry-forward feature issues

**Repo:** pdomain/pdomain-prep-for-pgdp  
All issues: `kind:feature status:backlog`. None get `bot:ship-issue-ready` at filing time — CT adds that when promoting to `status:ready`.

- [ ] **Step 1: File bounded deferred-write executor issue**

```bash
gh issue create --repo pdomain/pdomain-prep-for-pgdp \
  --title "Pipeline: bounded deferred-write executor (Q8)" \
  --label "kind:feature,effort:M,model:sonnet,model-effort:medium,status:backlog" \
  --body "$(cat <<'BODY'
Implement the bounded deferred-write executor from the pipeline task-model spec (Q8).

**Spec:** \`docs/specs/pipeline-task-model.md\` §"Open questions — Locked (2026-05-07)" Q8
**Roadmap:** \`docs/08-roadmap.md\` §M2 "Queued for M2 follow-up slices"

## Context

Today all stage writes go through synchronously. The bounded queue lets a
"Run all dirty stages" fan-out limit how many writes pile up at once. Knobs:
\`PGDP_STAGE_WRITE_POOL_SIZE\` and \`PGDP_STAGE_WRITE_QUEUE_CAP\`.

## Acceptance

- Both env knobs are documented in README / Settings.
- Dual-write reconciler routes through the bounded queue instead of writing synchronously.
- A fan-out of N dirty stages does not enqueue more than \`PGDP_STAGE_WRITE_QUEUE_CAP\` writes simultaneously.
- Existing stage-runner integration tests pass unchanged.
BODY
)"
```

- [ ] **Step 2: File ResolvedPageConfig plumbing issue**

```bash
gh issue create --repo pdomain/pdomain-prep-for-pgdp \
  --title "Pipeline: ResolvedPageConfig plumbing into stage runner" \
  --label "kind:feature,effort:M,model:sonnet,model-effort:medium,status:backlog" \
  --body "$(cat <<'BODY'
Plumb \`ResolvedPageConfig\` into the stage runner so config-aware stages read per-page config.

**Spec:** \`docs/specs/pipeline-task-model.md\`
**Roadmap:** \`docs/08-roadmap.md\` §M2 "Queued for M2 follow-up slices"

## Context

Three stages currently take no-op / default branches because the runner does not
pass config: \`initial_crop\` (should call real \`crop_edges\`), \`manual_deskew_pre\`
(should call \`rotate_image\` when angle is set), \`threshold\` (should respect manual
override). The M3 stage-controls panel needs this plumbing to be useful.

## Acceptance

- \`initial_crop\` calls the real \`crop_edges\` path (not the no-op default branch).
- \`manual_deskew_pre\` calls \`rotate_image\` when a manual angle is configured.
- \`threshold\` respects the manual override when set in \`ResolvedPageConfig\`.
- End-to-end chain test (ingest_source → canvas_map) still passes.
BODY
)"
```

- [ ] **Step 3: File async stage run flag issue**

```bash
gh issue create --repo pdomain/pdomain-prep-for-pgdp \
  --title "Pipeline: optional ?async=true flag on stage run route" \
  --label "kind:feature,effort:S,model:sonnet,model-effort:low,status:backlog" \
  --body "$(cat <<'BODY'
Add \`?async=true\` query flag to \`POST /api/data/projects/{id}/pages/{idx0}/stages/{stage_id}/run\`.

**Spec:** \`docs/specs/pipeline-task-model.md\` §"API surface"
**Roadmap:** \`docs/08-roadmap.md\` §M2 "Queued for M2 follow-up slices"

## Context

Slow stages (\`ocr\`, \`extract_illustrations\`) now have real implementations. The
synchronous route times out for DocTR on large pages. The async flag returns a Job
ID immediately and runs the stage in the background.

## Acceptance

- Without flag: synchronous response, existing behavior unchanged.
- With \`?async=true\`: returns \`{"job_id": "<uuid>"}\` with HTTP 202; stage runs in background.
- Job status queryable via existing jobs endpoint.
- \`ocr\` chip in the workbench rail triggers the async path automatically when
  \`?async=true\` is wired into the frontend click handler.
BODY
)"
```

- [ ] **Step 4: File blank_proof_synth + auto_detect_attrs issue**

```bash
gh issue create --repo pdomain/pdomain-prep-for-pgdp \
  --title "Pipeline: real impls for blank_proof_synth and auto_detect_attrs stages" \
  --label "kind:feature,effort:S,model:sonnet,model-effort:medium,status:backlog" \
  --body "$(cat <<'BODY'
Implement the two remaining CPU placeholder stages that currently raise \`StageNotImplemented\`.

**Spec:** \`docs/specs/pipeline-task-model.md\` §"Stage registry"
**Roadmap:** \`docs/08-roadmap.md\` §M2 "Carry-forwards into M3 / next M2 slice"

## Stages

- **\`blank_proof_synth\`**: synthesise a blank proof page — white canvas at \`canvas_map\`
  dimensions (read from \`canvas_map\` artifact metadata or reconstruct from image shape).
  Output: PNG.
- **\`auto_detect_attrs\`**: detect page attributes from the \`canvas_map\` PNG (e.g.
  illustration-heavy, text-only, mixed). Output: JSON dict of detected attributes.
  Acceptable to return \`{}\` as a graceful stub if no detector is available,
  similar to \`auto_detect_illustrations\`.

## Acceptance

- Both stages transition \`not-run → clean\` when clicked in the chip rail.
- Artifacts appear at \`pages/<id>/stages/<stage_id>/output.<ext>\`.
- 21 of 22 stages have real CPU impls; only \`extract_illustrations\` remains deferred to M3.
- Existing end-to-end chain test (ingest_source → canvas_map) still passes.
BODY
)"
```

- [ ] **Step 5: Verify 4 issues were created**

```bash
gh issue list --repo pdomain/pdomain-prep-for-pgdp \
  --label "kind:feature" --state open \
  --json number,title -q '.[] | "\(.number) \(.title)"'
```

Expected: 4 new issues (numbers will be 3–6 approximately) plus #2 (oxipng).

---

## Task E: File spec and chore issues

**Repo:** pdomain/pdomain-prep-for-pgdp  
Spec issues: no `bot:ship-issue-ready` at filing time — CT adds it after writing the spec via `/spec-from-issue`.

- [ ] **Step 1: File M3 spec issue**

```bash
gh issue create --repo pdomain/pdomain-prep-for-pgdp \
  --title "Spec: M3 workbench artifact viewer + stage controls panel" \
  --label "kind:spec,model:sonnet,model-effort:high,status:backlog" \
  --body "$(cat <<'BODY'
Design the M3 workbench milestone: polished stage-chain rail, side-by-side artifact
viewer, stage-filtered config controls panel, and SSE live updates.

**Spec-file:** \`docs/specs/pipeline-m3-artifact-viewer.md\` (to be written)
**Roadmap:** \`docs/08-roadmap.md\` §M3

## Scope to specify

- Polished stage-chain rail: per-stage thumbnails, status pills, click-to-select.
- Side-by-side artifact compare: \`Stage: [▼]\` and \`Compare with: [▼]\` selectors.
- Stage-controls panel: filters \`ResolvedPageConfig\` to fields the selected stage reads;
  Apply + Run buttons. Requires ResolvedPageConfig plumbing (see M2 carry-forward issue).
- SSE per-stage transitions update the rail live without page reload.
- Cache-busting strategy for the artifact endpoint after a re-run.

## Open questions to resolve in spec

- Field-to-stage mapping: where does the frontend learn which config fields a stage reads?
- Artifact URL scheme for cache busting (include \`last_run_at\` or \`input_hash\`?).
- Thumbnail generation: on-demand at artifact serve time, or pre-generated at run time?
BODY
)"
```

- [ ] **Step 2: File M4 spec issue**

```bash
gh issue create --repo pdomain/pdomain-prep-for-pgdp \
  --title "Spec: M4 lazy migration of existing projects + disk-cost UI" \
  --label "kind:spec,model:sonnet,model-effort:medium,status:backlog" \
  --body "$(cat <<'BODY'
Design M4: lazy-migrate pre-M1 projects on first access, CLI force-rebuild path,
and disk-cost callout in the project header banner.

**Spec-file:** \`docs/specs/pipeline-m4-migration.md\` (to be written)
**Roadmap:** \`docs/08-roadmap.md\` §M4

## Scope to specify

- Lazy-migrate on first access: synthesise \`page_stages\` rows from legacy
  \`processing_status\`; mark every applicable stage \`dirty\`.
- \`pgdp-prep migrate-projects --force-rebuild\` CLI: clear \`page_stages\` rows
  and on-disk stage artifacts for a project; leave source images and thumbnails.
- Disk-cost callout in project header: "Stage artifacts for this project: X GB /
  ~Y GB estimated full-DAG. Reclaim space?" with placeholder click-through.

## Open questions to resolve in spec

- What \`processing_status\` values map to which stages being pre-marked \`dirty\`?
- How to estimate "full-DAG" disk cost without running all stages?
- Should \`--force-rebuild\` be scoped per-project or per-page?
BODY
)"
```

- [ ] **Step 3: File M5 spec issue**

```bash
gh issue create --repo pdomain/pdomain-prep-for-pgdp \
  --title "Spec: M5 project-level fan-out + awaiting_review gate" \
  --label "kind:spec,model:sonnet,model-effort:high,status:backlog" \
  --body "$(cat <<'BODY'
Design M5: project-level stage orchestration, legacy job-type shims, and the
\`awaiting_review\` job state that parks \`build_package\` until pages are attested.

**Spec-file:** \`docs/specs/pipeline-m5-fanout.md\` (to be written)
**Roadmap:** \`docs/08-roadmap.md\` §M5

## Scope to specify

- \`JobType.project_run_stage_all_pages\` and \`project_run_dirty\`: dispatch per-page
  stage tasks; show per-page progress in JobsPage.
- Legacy \`batch_*\` job-type shims: translate to new model; remain until M6 removes them.
- \`awaiting_review\` job state: \`build_package\` parks when any proof-range page
  is unreviewed; project banner + Open Tasks bell update; auto-resume on last attestation.
- Full-power \`STAGE_IMPL\` cutover: every call site routes through the registry.

## Open questions to resolve in spec

- Progress bar granularity: per-stage or per-page? (Recommendation: per-page.)
- Auto-resume trigger: on \`text_review.clean\` write or on explicit "Mark reviewed" action?
- Open Tasks bell: new component or extend existing?
BODY
)"
```

- [ ] **Step 4: File P1 #9a undo/soft-delete spec issue**

```bash
gh issue create --repo pdomain/pdomain-prep-for-pgdp \
  --title "Spec: undo/soft-delete strategy for word-delete editor (P1 #9a follow-up)" \
  --label "kind:spec,model:sonnet,model-effort:medium,status:backlog" \
  --body "$(cat <<'BODY'
Decide and specify the undo strategy for the word-delete editor.

**Spec-file:** \`docs/specs/word-delete-undo-strategy.md\` (to be written)
**Roadmap:** \`docs/08-roadmap.md\` §P1 "9a-followup"

## Context

The v1 endpoint hard-rewrites \`<root>.words.json\` + \`<root>.txt\`, so honest
single-level undo needs a decision between:

- **(a) Server-side soft-delete:** \`OcrWord.deleted: bool\` flag with flip-restore
  endpoint; \`remaining_words\` filtered to non-deleted rows.
- **(b) Client-side debounced commit:** five-second Undo banner that only fires
  the DELETE after dismissal; no server schema change.

## Spec must decide

- Which strategy (a) or (b)?
- Wire contract changes if (a): new \`deleted\` field on \`OcrWord\`, new
  \`PATCH /api/data/.../words/{id}/restore\` endpoint.
- UX spec if (b): Undo banner duration, keyboard shortcut (Ctrl+Z?), what
  happens on navigation away during the window.
BODY
)"
```

- [ ] **Step 5: File P2 #10 Konva rotate/flip spec issue**

```bash
gh issue create --repo pdomain/pdomain-prep-for-pgdp \
  --title "Spec: Konva rotate/flip handles for workbench canvas (P2 #10)" \
  --label "kind:spec,model:sonnet,model-effort:medium,status:backlog" \
  --body "$(cat <<'BODY'
Design rotate and flip affordances for the Konva canvas in the workbench.

**Spec-file:** \`docs/specs/konva-rotate-flip.md\` (to be written)
**Roadmap:** \`docs/08-roadmap.md\` §P2 "#10"

## Context

Currently \`rotateEnabled=false\`, \`flipEnabled=false\` on the Konva Transformer.
Proofers occasionally need to fix scanner-frame skew that falls outside the
auto-deskew range. Spec 06 does not ask for this, so spec must define scope carefully.

## Spec must decide

- Rotation granularity: free-rotate handles, or discrete 90°/180° buttons, or both?
- Flip: horizontal only, vertical only, or both?
- Persistence: does a manual rotate/flip write back to a stage artifact, or is it
  view-state only?
- Interaction with the \`manual_deskew_pre\` stage: does UI rotate feed into that
  stage's \`ResolvedPageConfig\` angle?
- Undo: does rotate/flip participate in the word-delete undo strategy or have
  its own undo?
BODY
)"
```

- [ ] **Step 6: File P2 #13 search spec issue**

```bash
gh issue create --repo pdomain/pdomain-prep-for-pgdp \
  --title "Spec: search across pages (P2 #13)" \
  --label "kind:spec,model:sonnet,model-effort:high,status:backlog" \
  --body "$(cat <<'BODY'
Design full-text search across OCR pages for large books.

**Spec-file:** \`docs/specs/search-across-pages.md\` (to be written)
**Roadmap:** \`docs/08-roadmap.md\` §P2 "#13"

## Context

For books >500 pages, proofers need to search OCR text. The local mode uses
SQLite (FTS5 is available); the deferred remote mode could use Postgres TS.
Local-first priority means FTS5 is the immediate target.

## Spec must decide

- Index column: \`pages.ocr_text\` populated from \`text_postprocess\` artifact, or
  separate FTS5 virtual table?
- Re-index trigger: on \`text_postprocess\` stage clean write, or on-demand?
- Search UI: global search bar in the nav, or per-project search panel?
- Result shape: page number, matched snippet, link to workbench at that page.
- Postgres path: note the deferred adapter contract so the FTS5 impl does not
  preclude a later Postgres TS swap.
BODY
)"
```

- [ ] **Step 7: File M6 cleanup chore issue**

```bash
gh issue create --repo pdomain/pdomain-prep-for-pgdp \
  --title "M6: remove batch_* job types, LocalBackend, and process_page_cpu monolith" \
  --label "kind:chore,effort:M,model:sonnet,model-effort:medium,status:backlog" \
  --body "$(cat <<'BODY'
Deletion milestone: remove all deprecated code paths after M5 ships the full registry cutover.

**Roadmap:** \`docs/08-roadmap.md\` §M6

## Scope (deletions only, no new behaviour)

- Remove all \`JobType.batch_*\` enum values and their handlers.
- Remove legacy endpoints: \`/api/gpu/process-page\`, \`/api/gpu/run-ocr-page\`,
  the \`batch_*\` paths on \`/api/gpu/jobs\`.
- Delete \`LocalBackend\` and \`CpuBackend\` classes; \`pick_device()\` + the registry
  become the only path.
- Delete \`process_page_cpu\`'s monolithic body (now dead code after M5 registry cutover).
- Remove M2-era debug panel from the workbench if M3 left dead code paths.

## Acceptance

- \`grep -r "JobType.batch_" src/\` returns empty.
- \`grep -r "class LocalBackend" src/\` returns empty.
- \`grep -r "process_page_cpu" src/\` returns empty.
- \`curl -X POST http://127.0.0.1:8765/api/gpu/process-page\` returns 404.
- Full M5 smoke-test workflow still passes end-to-end.

**Blocked-by:** M5 must ship first (project-level fan-out + STAGE_IMPL cutover).
BODY
)"
```

- [ ] **Step 8: File #13a shadcn/ui chore issue**

```bash
gh issue create --repo pdomain/pdomain-prep-for-pgdp \
  --title "P2 #13a: remaining shadcn/ui Radix primitive swaps (Tabs, Select, Popover, Tooltip)" \
  --label "kind:chore,effort:S,model:haiku,model-effort:low,status:backlog" \
  --body "$(cat <<'BODY'
Swap remaining hand-rolled UI primitives to Radix-backed shadcn/ui components.

**Roadmap:** \`docs/08-roadmap.md\` §P2 "#13a"

## Context

Major library swaps are complete (Dialog, AlertDialog → Radix; toasts → sonner;
hotkeys → react-hotkeys-hook; path aliases via vite-tsconfig-paths). Four primitive
families remain: Tabs, Select, Popover, Tooltip.

The pattern from existing swaps (see \`components/ui/dialog.tsx\`):
1. \`npm install @radix-ui/react-<primitive>\`
2. Write thin wrapper in \`frontend/src/components/ui/<primitive>.tsx\`
3. Swap callers (grep for existing usage of the hand-rolled version)

## Acceptance

- Each primitive family has a wrapper in \`frontend/src/components/ui/\`.
- All callers in the SPA import from the wrapper, not directly from Radix.
- No hand-rolled Tabs, Select, Popover, or Tooltip implementations remain.
- Existing Vitest + Playwright tests pass.
BODY
)"
```

- [ ] **Step 9: Verify all spec + chore issues were created**

```bash
gh issue list --repo pdomain/pdomain-prep-for-pgdp \
  --label "kind:spec" --state open \
  --json number,title -q '.[] | "\(.number) \(.title)"'

gh issue list --repo pdomain/pdomain-prep-for-pgdp \
  --label "kind:chore" --state open \
  --json number,title -q '.[] | "\(.number) \(.title)"'
```

Expected: 6 spec issues (M3, M4, M5, #9a, #10, #13) and 3 chore issues (#1 existing + M6 + #13a).

---

## Self-review notes

- All issues land `status:backlog`; no issue is bot-eligible at filing time.
- M6 chore body includes `Blocked-by:` prose but not a formal `Blocked-by: #N` header — the M5 issue number is unknown at plan-write time. After both are filed, CT should add `Blocked-by: #<M5-number>` to the M6 issue body.
- `status:bounced` hex `e4e669` matches GitHub's default "invalid" label color — visually distinct from ready (green) and in-progress (yellow).
- The plan has no code changes and no test suites — verification is `gh`/`ctask` CLI output checks.
