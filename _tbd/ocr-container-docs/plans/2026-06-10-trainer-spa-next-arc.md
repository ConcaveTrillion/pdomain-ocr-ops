---
repo: ConcaveTrillion/ocr-container-meta
status: done
executed: 2026-06-10 — all six tracks merged; 2026-06-11 pdomain-ops v0.11.0
  released, deps bumped, stopgaps retired, all repo mains pushed
---

# Trainer-SPA Next Arc — Umbrella Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring pdomain-ocr-trainer-spa onto pdomain-ui, ship the labeler→trainer labeled-page import pipeline (auto-discovery + freshness), deliver M12 typeface classifier, and re-enable downgraded ESLint rules — executed as parallel subagent tracks.

**Architecture:** Six tracks across four repos. pdomain-ops grows two small shared APIs (shared-paths registry + DocTR export-manifest schema); the labeler publishes its export root and writes the manifest; the trainer auto-discovers the root and flags fresh exports in its kanban. Independently, the trainer adopts the shared pdomain-ui AppShell (unlocking the compute settings panel) and ships M12. Each track has its own detailed TDD plan in its repo's `docs/plans/`.

**Tech Stack:** Python/FastAPI + Pydantic (ops, backends), React/Vite/TS + pdomain-ui (frontends), pytest + Playwright, uv local-dev mode for cross-repo development.

---

## Track index — detailed plans (authoritative for implementation)

| Track | Repo | Plan doc | Branch |
|---|---|---|---|
| B — shared-paths API + export-manifest schema | pdomain-ops | `pdomain-ops/docs/plans/2026-06-10-shared-paths-and-export-manifest.md` | `feat/shared-paths-export-manifest` |
| A — pdomain-ui adoption + compute panel | pdomain-ocr-trainer-spa | `pdomain-ocr-trainer-spa/docs/plans/2026-06-10-pdomain-ui-adoption-and-compute-panel.md` | `feat/pdomain-ui-adoption` |
| C — manifest write + publish root + Send-to-trainer | pdomain-ocr-labeler-spa | `pdomain-ocr-labeler-spa/docs/plans/2026-06-10-export-manifest-and-send-to-trainer.md` | `feat/export-manifest-send-to-trainer` |
| D — import auto-discovery + freshness + banner | pdomain-ocr-trainer-spa | `pdomain-ocr-trainer-spa/docs/plans/2026-06-10-labeler-import-discovery.md` | `feat/labeler-import-discovery` |
| E — M12 typeface classifier (SPA side) | pdomain-ocr-trainer-spa | `pdomain-ocr-trainer-spa/docs/plans/2026-06-10-m12-typeface-classifier.md` | `feat/m12-typeface-classifier` |
| F — ESLint rules re-enable | pdomain-ocr-trainer-spa | `pdomain-ocr-trainer-spa/docs/plans/2026-06-10-eslint-rules-reenable.md` | `chore/eslint-reenable` |

## Pinned cross-repo contract

All three import-pipeline tracks (B, C, D) code against this surface. Track B implements it; C and D consume it via local-dev mode until the ops release ships.

```python
# shared-paths (storage: <suite_data_dir>/shared-paths.json + .lock, 5s bounded FileLock)
from <ops_pkg>.suite.shared_paths import publish_shared_path, resolve_shared_path
publish_shared_path("doctr-export-root", export_root, app="pdomain-ocr-labeler-spa")
resolve_shared_path("doctr-export-root")  # -> Path | None; stale paths returned as-is

# manifest (at <export_root>/manifest.json, atomic tmp+os.replace)
from <ops_pkg>.schemas.doctr_export import (
    DoctrExportManifest, DoctrExportProject, DoctrExportTaskStats,
    read_manifest, write_manifest,
)
```

JSON contract: `{schema: "pdomain.doctr-export-manifest", version: 1, generated_at, app, projects.{project_id}.{exported_at, page_count, tasks.{task}.item_count}}`. Unknown task keys round-trip; reading `version > 1` warns, never crashes.

`<ops_pkg>` — the actual ops package name (`pdomain_ops` vs `pd_ocr_ops`) is verified in each consumer plan's Task 0 against the sibling checkout; the ops plan is authoritative.

## Decisions resolved at planning time

- **Manifest schema lives in pdomain-ops** and its models join `PUBLIC_MODELS` in `emit.py` so pdomain-ui codegen emits TS types. (Answers ops open question 3.)
- **`publish_shared_path` requires an absolute path** — raise `ValueError` on relative. (Answers ops open question 1.)
- **`generated_at` stays a required field** — the labeler controls the timestamp explicitly. (Answers ops open question 2.)
- **`"schema"` JSON key** via Pydantic `Field(alias="schema")` + `populate_by_name`; dump `by_alias=True`.
- **Explicit `labeler_export_root` setting always beats discovery** in the trainer; absent both → current behavior, zero regression.
- **Track D degrades gracefully on pre-Track-B ops wheels** (`try/except ImportError` isolation in `domain/labeler_export.py`) — the SPA boots either way.
- **Track F (ESLint) runs last** — its 60-violation inventory was measured pre-migration and Track A deletes many offending files; counts are re-measured at execution.

## CT decision gates (surfaced, not blocking wave 1)

1. **pdomain-ops release** (→ v0.11.0) after Track B merges — releases are CT-gated. C and D develop via local-dev; their final dep-bump commits wait on the release.
2. **M12 classifier arch** — plan defaults `TypefaceConfig.arch = "resnet18"`; confirm before filing the pdomain-ocr-training cross-repo issue (proposed Protocol additions — `train_typeface`, `evaluate_typeface`, configs — are spelled out in the Track E plan).
3. **M12 data sourcing** — Track E assumes `metadata.jsonl` rows `{file_name, typeface}`; the labeler does not export typeface labels today. SPA-side M12 ships against fixture data; a labeler follow-on is needed for real data.
4. **"Open in labeler" kanban deep-link** — deferred follow-on after Track A (needs the suite-sibling hooks the AppShell migration brings).
5. **Long-term PageRecord path** — page-split Plans 3/4 (composition + Phase-A decisions still pending) eventually supersede the manifest convention; this arc is the bridge, not the destination.

---

## Execution

Per-repo agents, `model: sonnet`, one per track. Every implementation dispatch gets an explicit orchestrator-created worktree (memory: `isolation:"worktree"` alone has raced; create the worktree yourself and pass the absolute path). Agents commit on their branch and STOP — no self-merge, no push, no PRs.

### Wave 1 — parallel: Track B + Track A

- [ ] **Step 1: Create worktrees** (cut from LOCAL main HEAD, not origin/main — local mains run ahead):

```bash
git -C /workspaces/ocr-container/pdomain-ops worktree add .claude/worktrees/shared-paths -b feat/shared-paths-export-manifest main
git -C /workspaces/ocr-container/pdomain-ocr-trainer-spa worktree add .claude/worktrees/pdomain-ui-adoption -b feat/pdomain-ui-adoption main
```

- [ ] **Step 2: Dispatch both agents in one message.** Prompt skeleton (both): first line = absolute worktree path; "Execute every task of <plan doc absolute path> with superpowers:executing-plans, TDD steps verbatim; work ONLY in the worktree; commit per task; run `make ci AI=1` at the end; no push, no PR, no merge; return branch + worktree path + CI result + deviations."
- [ ] **Step 3: After each return:** `git -C <repo> status --short` on the canonical checkout (agents have touched canonical despite instructions — verify clean), then review the diff on the branch.
- [ ] **Step 4: Merge Track B** (workspace protocol): rebase the worktree branch onto local `main`, `make ci AI=1` green in worktree, `git -C pdomain-ops merge --ff-only feat/shared-paths-export-manifest` on main, remove worktree, delete branch.
- [ ] **Step 5: Merge Track A** the same way. Gate: the driver-contract e2e suite is green (testid contract preserved).
- [ ] **Step 6: Surface CT gate 1** (ops release) — C/D proceed on local-dev regardless.

### Wave 2 — parallel: Track C + Track D + Track E (after B and A merge)

- [ ] **Step 1: Create worktrees:**

```bash
git -C /workspaces/ocr-container/pdomain-ocr-labeler-spa worktree add .claude/worktrees/export-manifest -b feat/export-manifest-send-to-trainer main
git -C /workspaces/ocr-container/pdomain-ocr-trainer-spa worktree add .claude/worktrees/labeler-import -b feat/labeler-import-discovery main
git -C /workspaces/ocr-container/pdomain-ocr-trainer-spa worktree add .claude/worktrees/m12-typeface -b feat/m12-typeface-classifier main
```

  Labeler-spa caution: canonical has ~47 uncommitted files from the in-flight selection-parity arc. The worktree cuts from committed main so it won't contain them; verify the agent never writes to canonical. Track C touches `ExportDialog`/export jobs — disjoint from the parity arc's canvas/word components.

- [ ] **Step 2: Dispatch all three** (same prompt skeleton; C and D prompts add: "ops APIs come from the sibling checkout via `make local-dev` — Task 0 of your plan").
- [ ] **Step 3: Merge order: D first, then E** (both touch `domain/datasets.py` + kanban; D is 5 tasks and small, E rebases over it), then C. Same rebase + ff-only protocol per repo.
- [ ] **Step 4: Cross-app smoke** (manual or driver): run the labeler, export a project, confirm `manifest.json` written and shared path published; run the trainer with no explicit `labeler_export_root`, confirm discovery + kanban fresh-flag + banner.

### Wave 3 — Track F + closeout

- [ ] **Step 1: Re-measure ESLint counts** on the post-merge tree, update the Track F plan's inventory table, then dispatch on a fresh worktree (`chore/eslint-reenable`).
- [ ] **Step 2: Merge Track F** (rebase + ff-only).
- [ ] **Step 3: File the pdomain-ocr-training M12 cross-repo issue** (Protocol additions; command is in the Track E plan) — gated on CT decision 2.
- [ ] **Step 4: Cleanup:** remove the stale merged worktree at `.worktrees/pdomain-config-release-remediation-repos/pdomain-ocr-trainer-spa` + its branch; close GH issues `pdomain/pdomain-ocr-trainer-spa#24` (F) and `#14` (E, SPA side); after the ops release, dep-bump commits in C/D repos via `make update-pd-deps`.
- [ ] **Step 5: Push** — only per-branch on CT authorization.

## Verification (arc-level)

- `make ci AI=1` green in every repo at every merge point.
- Trainer driver-contract e2e green after A, D, E, F.
- Both Browser Verification milestones (Track A/D/E plans, labeler Track C plan) executed against real servers — not skipped.
- Cross-app smoke (Wave 2 Step 4) is the arc's acceptance test.
