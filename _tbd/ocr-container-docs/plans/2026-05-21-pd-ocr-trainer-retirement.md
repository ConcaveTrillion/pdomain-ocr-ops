---
repo: ConcaveTrillion/ocr-container-meta
plan_type: cross-cut
status: active
synced: 2026-05-21
milestone: 15
---

# pd-ocr-trainer Retirement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retire the legacy NiceGUI `pd-ocr-trainer` repo by extracting its training code into a new peer package and replacing its UI with a `pdomain-ui`-based SPA.

**Architecture:** Three repos. New `pdomain-ocr-training` peer package owns the torch/DocTR training code behind an `ITrainingRunner` Protocol (ops-style, mirroring `pdomain-ops`). `pdomain-ocr-trainer-spa` is re-spec'd onto `pdomain-ui` + `pdomain-ops` + `pdomain-ocr-training` and built to core parity. `pd-ocr-trainer` is deleted last.

**Tech Stack:** Python 3.11+, hatchling, uv, pytest, torch + DocTR (contained in `pdomain-ocr-training` only); FastAPI + React/Vite/TS + `pdomain-ui` for the SPA.

**Design reference:** `docs/specs/2026-05-21-pd-ocr-trainer-retirement-design.md`

---

## Phasing overview

- **Phase 1 — `pdomain-ocr-training` extraction.** Detailed tasks below. Tasks 1–8 are DONE (GH issues #268–#275 all closed).
- **Phase 2 — `pdomain-ocr-trainer-spa` re-spec.** Milestone-level. Each spec area gets its own `superpowers:brainstorming` → `writing-plans` cycle; this plan only tracks the deliverables.
- **Phase 3 — SPA build to core parity.** Gated on Phase 2. Executed from the per-milestone plans Phase 2 produces.
- **Phase 4 — delete `pd-ocr-trainer`.** Gated on Phase 3 parity acceptance.

**Deferred scope:** The legacy `pd-ocr-trainer` HF-datasets roadmap and glyph-feature-classifier specs were never implemented. They are carried forward into `pdomain-ocr-trainer-spa` as post-core-parity milestones (see Task 13). Kanban and live-log-viewer components are `pdomain-ui` gaps — built SPA-local first, not pre-promoted to `pdomain-ui` (YAGNI).

---

## Task 1 — Scaffold pdomain-ocr-training repo  {#scaffold-repo}
model: sonnet  effort: S  area: pdomain-ocr-training
Status: DONE — 2d82ad9

Context: New repo `/workspaces/ocr-container/pdomain-ocr-training/` required as a peer package owning all torch/DocTR training code. Flat-package layout mirroring `pdomain-ops` (`pd_ocr_training/`, hatchling, `tests/`).
Approach: Copy scaffold from `pdomain-ops` (LICENSE, .gitignore, pyproject.toml), init git, write package init and smoke test.
Verification: `cd /workspaces/ocr-container/pdomain-ocr-training && uv run pytest tests/test_package.py -v`
Acceptance:
- [x] `pdomain-ocr-training/pyproject.toml` present with correct author/email/org metadata
- [x] `pd_ocr_training/__init__.py` exposes `__version__`
- [x] `tests/test_package.py` passes

<details>
<summary>Implementation steps (DONE)</summary>

- Created `pdomain-ocr-training/` directory tree, copied LICENSE + .gitignore from `pdomain-ops`.
- Wrote `pyproject.toml` with `pdomain-ocr-training` name, hatchling backend, torch + DocTR deps, and workspace-standard ruff/basedpyright strict-lint config.
- Wrote `pd_ocr_training/__init__.py` with `__version__ = "0.1.0"`.
- Wrote `tests/test_package.py` asserting the version string.
- Ran `uv run pytest tests/test_package.py -v` → PASS.
- Committed: `2d82ad9 chore: scaffold pdomain-ocr-training peer package`
</details>

---

## Task 2 — Move utils.py  {#move-utils}
model: sonnet  effort: S  area: pdomain-ocr-training
Status: DONE — 6f29ab3

Context: `pd-ocr-trainer/src/pd_ocr_trainer/utils.py` (EarlyStopper, plotting helpers) is the smallest module with no cross-dependencies; it migrates first to validate the move workflow.
Approach: Copy file and its test, rewrite `pd_ocr_trainer` → `pd_ocr_training` imports, verify tests pass.
Verification: `uv run pytest tests/test_utils.py -v`
Acceptance:
- [x] `pd_ocr_training/utils.py` present; no `pd_ocr_trainer` import references remain
- [x] `tests/test_utils.py` passes (same tests as the legacy repo)

<details>
<summary>Implementation steps (DONE)</summary>

- Copied `utils.py` and `tests/test_utils.py` from legacy repo.
- Rewrote all `pd_ocr_trainer.*` imports to `pd_ocr_training`.
- `grep -rn pd_ocr_trainer` returned no matches.
- `uv run pytest tests/test_utils.py -v` → PASS.
- Committed: `6f29ab3 feat: move training utils into pdomain-ocr-training`
</details>

---

## Task 3 — Move dataset_store.py to datasets.py  {#move-datasets}
model: sonnet  effort: S  area: pdomain-ocr-training
Status: DONE — 3d0f8cb / 0763d6d

Context: `dataset_store.py` owns `ExportManager`, which manages the on-disk dataset layout (`ml-training/<profile>/detection|recognition/`, `ml-validation/`, `matched-ocr/`, `dist/`). Renamed to `datasets.py` for clarity.
Approach: Copy and rename, fix imports, write a behavioural test for `ExportManager.list_profiles()` against a `tmp_path` root, verify.
Verification: `uv run pytest tests/test_datasets.py -v`
Acceptance:
- [x] `pd_ocr_training/datasets.py` present; no `pd_ocr_trainer` import references remain
- [x] `ExportManager` round-trip test passes (profile on disk is discoverable)

<details>
<summary>Implementation steps (DONE)</summary>

- Copied `dataset_store.py` → `datasets.py`, rewrote imports.
- Wrote `tests/test_datasets.py` with `test_export_manager_discovers_profile`.
- Initial commit `3d0f8cb`; ruff failures (unused import + legacy-debt ignores) fixed in `0763d6d`.
</details>

---

## Task 4 — Move train_detect/train_recog to detect/recog  {#move-train-modules}
model: sonnet  effort: S  area: pdomain-ocr-training
Status: DONE — dd1d4a4

Context: `train_detect.py` and `train_recog.py` are the core training entrypoints. Renamed to `detect.py` / `recog.py` to match the project-script names (`pdomain-ocr-training-detect`, `pdomain-ocr-training-recog`).
Approach: Copy and rename both modules, rewrite intra-package imports (`pd_ocr_trainer.*` → `pd_ocr_training.*`), write import-smoke tests (no GPU required).
Verification: `uv run pytest tests/test_training_entrypoints.py -v`
Acceptance:
- [x] `pd_ocr_training/detect.py` and `pd_ocr_training/recog.py` present; no legacy import references
- [x] `test_detect_module_imports` and `test_recog_module_imports` pass

<details>
<summary>Implementation steps (DONE)</summary>

- Copied and renamed both modules; confirmed `grep -rn pd_ocr_trainer` returned no matches.
- Wrote smoke tests verifying each module imports and exposes `main`.
- Committed: `dd1d4a4 feat: move detection + recognition training into pdomain-ocr-training`
</details>

---

## Task 5 — Define ITrainingRunner protocol  {#training-runner-protocol}
model: sonnet  effort: S  area: pdomain-ocr-training
Status: DONE — 81e1d3c / 3c00788

Context: The SPA must depend on a Protocol, not the concrete training modules, to stay torch-free. This mirrors how `pdomain-ops` exposes `StageDispatcher`/`LongJobRunner` behind Protocols.
Approach: Catalogue `detect.main` / `recog.main` signatures, define `TrainingEvent(BaseModel)` and `ITrainingRunner(Protocol, runtime_checkable)`, write a struct-check test.
Verification: `uv run pytest tests/test_protocols.py -v`
Acceptance:
- [x] `pd_ocr_training/protocols.py` defines `ITrainingRunner` and `TrainingEvent`
- [x] `ITrainingRunner` is `@runtime_checkable`
- [x] A stub class satisfying the protocol passes `isinstance(Stub(), ITrainingRunner)`

<details>
<summary>Implementation steps (DONE)</summary>

- Defined `TrainingEvent(BaseModel)` with `kind: Literal["log","epoch","metric","done","error"]`, `message: str`, `progress: float | None`.
- Defined `ITrainingRunner(Protocol, runtime_checkable)` with `train_detection` and `train_recognition` methods returning `Iterator[TrainingEvent]`.
- Initial commit `81e1d3c`; review fixes in `3c00788` (future-import comment, Literal kind constraint, test improvements).
</details>

---

## Task 6 — Implement LocalTrainingRunner  {#local-training-runner}
model: sonnet  effort: M  area: pdomain-ocr-training
Status: DONE — f23a84b

Context: `LocalTrainingRunner` is the concrete implementation satisfying `ITrainingRunner`. It invokes `detect.main` / `recog.main`, translates their progress reporting into `TrainingEvent`s, and yields a final `done` event. The SPA backend injects it via the Protocol — no direct torch dep in the SPA.
Approach: TDD: write failing tests (protocol conformance + `done` event emitted); implement class; monkeypatch `detect.main` / `recog.main` to avoid GPU in tests.
Verification: `uv run pytest tests/test_local_runner.py -v`
Acceptance:
- [x] `isinstance(LocalTrainingRunner(), ITrainingRunner)` is True
- [x] `train_detection("demo", {})` yields at least one `TrainingEvent(kind="done", ...)`
- [x] All events are `TrainingEvent` instances; no torch required in tests

<details>
<summary>Implementation steps (DONE)</summary>

- Wrote failing tests; implemented `LocalTrainingRunner` with queue-based progress collection, timeout handling, and concurrency test.
- Commit `f23a84b` also hardened queue timeout and config-mapping edge cases identified during review.
</details>

---

## Task 7 — Public API + workspace-standard repo scaffold  {#repo-scaffold}
model: sonnet  effort: S  area: pdomain-ocr-training
Status: DONE — 8a8a6f8

Context: Before the repo is published and wired into the workspace, it needs a clean public API (`__init__.py` re-exports), a `Makefile` matching the workspace standard, and a `CLAUDE.md` explaining the package contract.
Approach: Re-export `ITrainingRunner`, `LocalTrainingRunner`, `TrainingEvent` from `__init__.py`; copy `Makefile` from `pdomain-ops` and adjust target names; write `CLAUDE.md` modeled on `pdomain-ops/CLAUDE.md`.
Verification: `make ci` (or `uv run pytest -v`)
Acceptance:
- [x] `from pd_ocr_training import ITrainingRunner, LocalTrainingRunner, TrainingEvent` works
- [x] `Makefile` has `ci`, `test`, `lint` targets
- [x] `CLAUDE.md` documents the ITrainingRunner contract and torch-containment rule
- [x] Full test suite passes (`make ci`)

<details>
<summary>Implementation steps (DONE)</summary>

- Updated `__init__.py` to re-export the three public symbols; added `__all__`.
- Copied `Makefile` from `pdomain-ops`; adjusted package name in ruff/basedpyright/pytest targets.
- Wrote `CLAUDE.md` explaining: what the package is, the `ITrainingRunner` contract, that torch lives here and nowhere else in the suite.
- Committed: `8a8a6f8 chore: scaffold workspace-standard repo structure`
</details>

---

## Task 8 — Workspace wiring  {#workspace-wiring}
model: sonnet  effort: S  area: workspace
Status: DONE — GH #275 closed (commit f78a0c4)

Context: `pdomain-ocr-training` exists as a local repo and has been pushed to GitHub (`pdomain/pdomain-ocr-training`, private, `allow_squash_merge=false`). The remaining wiring — subagents and workspace `CLAUDE.md` entries — is not yet done.
Approach: Add `pdomain-ocr-training` and `pdomain-ocr-training-docs` agent files under `.claude/agents/`, modeled on the `pdomain-ops` pair; add `pdomain-ocr-training` row to the workspace `CLAUDE.md` project table and routing section; commit workspace changes.
Verification: `grep pdomain-ocr-training /workspaces/ocr-container/CLAUDE.md`
Acceptance:
- [x] `.claude/agents/pdomain-ocr-training.md` exists, modeled on `pdomain-ops.md`
- [x] `.claude/agents/pdomain-ocr-training-docs.md` exists, modeled on `pdomain-ops-docs.md`
- [x] `CLAUDE.md` project table includes `pdomain-ocr-training/` row with description
- [x] `CLAUDE.md` routing section includes `pdomain-ocr-training` entry

---

## Task 9 — Re-spec overview + decisions onto new stack  {#respec-overview}
model: opus  effort: M  area: pdomain-ocr-trainer-spa
Status: DONE — GH #276 closed

Context: The existing `pdomain-ocr-trainer-spa` specs 00 (overview) and 17 (decisions) conflict with the target architecture — D-004 rejects `pdomain-ui` (shadcn/ui instead) and D-T1 assumes subprocess calls to `pd-ocr-trainer`. Both are now superseded by the `pdomain-ui` + `pdomain-ops` + `pdomain-ocr-training` stack decision.
Approach: `superpowers:brainstorming` → `writing-plans` cycle; rewrite `00-overview` and `17-decisions` targeting the new stack, removing D-004 and D-T1, and adding decisions for `ITrainingRunner` injection, `pdomain-ui` dependency, and `pdomain-ops` GPU dispatch.
Verification: New spec files committed to `pdomain-ocr-trainer-spa/docs/specs/`; all stack conflicts resolved
Acceptance:
- [x] `00-overview` updated: target stack is `pdomain-ui` + `pdomain-ops` + `pdomain-ocr-training`
- [x] `17-decisions` updated: D-004 and D-T1 replaced with new decisions for runner Protocol, pdomain-ui, and LongJobRunner
- [x] No spec references shadcn/ui direct or subprocess training calls

---

## Task 10 — Re-spec frontend mapping screens to pdomain-ui components  {#respec-frontend}
model: opus  effort: M  area: pdomain-ocr-trainer-spa
Status: DONE — GH #277 closed

Context: Spec `03-frontend` must be rewritten to map every trainer screen (profile selector, config cards, kanban, training controls, live log) to `pdomain-ui` components per the design's migration table. The two `pdomain-ui` gaps (DnD kanban and live-log viewer) are specified as SPA-local components.
Approach: `superpowers:brainstorming` → `writing-plans` cycle; produce a new `03-frontend` spec referencing `AppShell`, `TopNav`, `Select`, `Card`, `Accordion`, `Field`/`FieldRow`, `Button`, `Progress`, `JobStatusPip`, `useLongJob`; specify `dnd-kit` kanban and streaming-text log viewer as SPA-local.
Verification: New `03-frontend` spec committed; every screen has a `pdomain-ui` component mapping or explicit "SPA-local" designation
Acceptance:
- [x] All legacy NiceGUI elements have a `pdomain-ui` counterpart or SPA-local spec
- [x] DnD kanban component specified (SPA-local, `dnd-kit`)
- [x] Live-log-viewer component specified (SPA-local, SSE via `useLongJob`)
- [x] `data-testid` contract documented for browser-verification milestone

---

## Task 11 — Re-spec backend + training-runs driving ITrainingRunner  {#respec-backend}
model: opus  effort: M  area: pdomain-ocr-trainer-spa
Status: DONE — GH #278 closed

Context: Specs `02-backend` and `06-training-runs` must be rewritten so the FastAPI backend drives `ITrainingRunner` from `pdomain-ocr-training` (not subprocess calls), with long jobs managed via `pdomain-ops` `LongJobRunner` and SSE for live progress.
Approach: `superpowers:brainstorming` → `writing-plans` cycle; rewrite `02-backend` and `06-training-runs` referencing `ITrainingRunner.train_detection` / `train_recognition`, `LongJobRunner`, SSE endpoints, and the profiles/datasets API surface.
Verification: New specs committed; no subprocess training calls remain in any spec
Acceptance:
- [x] `02-backend` specifies `ITrainingRunner` injection (no direct `torch` import)
- [x] `06-training-runs` specifies `LongJobRunner` + SSE progress stream
- [x] Job lifecycle (start, poll, cancel, result) fully specified

---

## Task 12 — Re-spec remaining specs  {#respec-remaining}
model: sonnet  effort: L  area: pdomain-ocr-trainer-spa
Blocked-by: #respec-overview

Context: Specs for profiles, kanban, eval, models, jobs/SSE, notifications, hotkeys, driver contract, testing, and deployment all predate the `pdomain-ui` + `pdomain-ops` standard and need rewriting to match the shipped `pdomain-ocr-labeler-spa` pattern.
Approach: One `superpowers:brainstorming` → `writing-plans` cycle per spec area; each produces a replacement spec file committed to `pdomain-ocr-trainer-spa/docs/specs/`; modeled on `pdomain-ocr-labeler-spa`'s shipped equivalents.
Verification: All previously-conflicting specs replaced; `pdomain-ocr-trainer-spa/docs/specs/` contains only new-stack specs
Acceptance:
- [ ] Profiles spec updated (references `pdomain-ui` Select + a profiles store)
- [ ] Kanban spec updated (references SPA-local `dnd-kit` component)
- [ ] Jobs/SSE, notifications, hotkeys, driver contract, testing, deployment all updated
- [ ] SPA-serving contract tests (`test_routes_root.py` pattern) specified in testing spec

---

## Task 13 — Carry HF-datasets + glyph-feature-classifier specs forward  {#carry-deferred-specs}
model: sonnet  effort: S  area: pdomain-ocr-trainer-spa
Status: DONE — GH #280 closed

Context: The legacy HF-datasets roadmap (`pd-ocr-trainer/docs/architecture/datasets.md`, `pd-ocr-trainer/docs/plans/roadmap.md`) and glyph-feature-classifier specs were never implemented. They should become post-core-parity milestones in `pdomain-ocr-trainer-spa`, not be abandoned.
Approach: Copy/adapt the relevant legacy spec content into `pdomain-ocr-trainer-spa/docs/specs/` as clearly-labelled deferred milestones; note their dependency on core-parity completion.
Verification: Deferred milestone specs committed to `pdomain-ocr-trainer-spa/docs/specs/`
Acceptance:
- [x] HF-datasets roadmap carried forward as a deferred milestone spec
- [x] Glyph-feature-classifier specs carried forward as a deferred milestone spec
- [x] Both specs note they are blocked on core-parity (Phase 3) completion

---

## Task 14 — decompose-spec sync the new SPA milestone roadmap  {#sync-spa-roadmap}
model: sonnet  effort: S  area: pdomain-ocr-trainer-spa
Status: DONE — GH #281 closed

Context: After all re-spec tasks complete, the new milestone roadmap for `pdomain-ocr-trainer-spa` needs to be synced to GH issues so the ship-issue workflow can pick them up.
Approach: Run `/decompose-spec --sync` on the new `pdomain-ocr-trainer-spa` plan docs to create GH issues in the appropriate tracker; verify milestone and issue count.
Verification: `gh issue list --repo ConcaveTrillion/pdomain-ocr-trainer-spa --milestone "..." --state open`
Acceptance:
- [x] All re-spec milestones have corresponding GH issues
- [x] Plan frontmatter updated (`synced:` and `milestone:` fields set)
- [x] GH milestone created and linked

---

## Task 15 — Scaffold pdomain-ocr-trainer-spa repo  {#scaffold-spa}
model: sonnet  effort: M  area: pdomain-ocr-trainer-spa
Status: DONE — GH #282 closed

Context: `pdomain-ocr-trainer-spa` currently contains only spec files — zero code. The SPA repo needs a FastAPI backend + React/Vite frontend scaffold wired to `pdomain-ui`, `pdomain-ops`, and `pdomain-ocr-training` dependencies, following the `pdomain-ocr-labeler-spa` template.
Approach: Bootstrap FastAPI + React/Vite/TS project structure; add `pdomain-ui`, `pdomain-ops`, `pdomain-ocr-training` to deps; add SPA-serving contract tests (`test_routes_root.py` pattern with monkeypatch); set up Makefile with `ci`, `frontend-build`, `e2e-browser` targets.
Verification: `make ci` passes (backend tests pass; SPA-serving contract tests pass)
Acceptance:
- [x] FastAPI app boots; `GET /` returns 200 HTML (SPA)
- [x] `test_routes_root.py` passes with monkeypatch (no real frontend build required)
- [x] `pdomain-ui`, `pdomain-ops`, `pdomain-ocr-training` listed as dependencies
- [x] GitHub repo configured (`allow_squash_merge=false`); subagents added to workspace

---

## Task 16 — Build core-parity milestones  {#build-core-parity}
model: sonnet  effort: L  area: pdomain-ocr-trainer-spa
Blocked-by: #scaffold-spa

Context: Core parity = the working NiceGUI feature set: profiles, dual (detection + recognition) dataset kanban, detection + recognition config cards, live training log, and training runs. Each milestone is its own plan produced by Task 14's `/decompose-spec --sync` and ships via the standard ship-issue workflow. HF-datasets and glyph milestones are deferred (Task 13).
Approach: Execute each core-parity milestone plan in order, following the per-milestone plans from Task 14; one ship-issue session per milestone; all slices are test-first.
Verification: All core-parity milestone issues closed; `make ci` passes
Acceptance:
- [ ] Profile selector functional (create/select/delete profiles)
- [ ] Dual kanban functional (detection + recognition dataset assignment, drag-drop)
- [ ] Detection + recognition config cards functional (submit config, validation)
- [ ] Live training log functional (SSE stream via `useLongJob`)
- [ ] Training runs functional (start, poll, cancel, result history)

---

## Task 17 — Browser verification milestone  {#browser-verification}
model: sonnet  effort: M  area: pdomain-ocr-trainer-spa
Blocked-by: #build-core-parity

Context: `pdomain-ocr-trainer-spa` is a FastAPI backend that bundles and serves a React/Vite SPA, so its build plan must end with a mandatory browser-verification milestone covering Playwright e2e tests and SPA-serving contract tests. This is a workspace requirement for all FastAPI + SPA repos.
Approach: Add `pytest-playwright>=0.5` in a `[dependency-groups] e2e` uv group; implement `data-testid` contract on key elements; write app-loads, happy-path, and route tests; wire `make e2e-browser` into `make ci`.
Verification: `make e2e-browser` passes (Chromium); `make ci` passes end-to-end
Acceptance:
- [ ] `pytest-playwright>=0.5` in `[dependency-groups] e2e`; `make e2e-browser` target exists
- [ ] `playwright install chromium` in `make setup`
- [ ] App-loads test: Chromium opens `/`, root `data-testid` visible, no `console.error`
- [ ] Happy-path test: start a stubbed training run, see log panel populate
- [ ] Route test: a React Router sub-path renders its page (not 404)
- [ ] `make e2e-browser` wired into `make ci`
- [ ] SPA-serving contract tests (`test_routes_root.py` pattern): `GET /` → 200 HTML; router sub-paths → 200; `/api/*` not shadowed; 503 when frontend dir absent
- [ ] SPA-serving contract tests do NOT skip when frontend not built (monkeypatch + `tmp_path`)

**Reference:** `pdomain-ocr-simple-gui/tests/e2e/` for Playwright pattern; `pdomain-ocr-simple-gui/tests/test_routes_root.py` for SPA-serving contract pattern.

**`data-testid` contract (minimum):** `profile-selector`, `config-submit` (detection), `config-submit` (recognition), `kanban-detection-column`, `kanban-recognition-column`, `training-log-panel`, `run-start-button`.

---

## Task 18 — Confirm core-parity acceptance tests pass  {#confirm-parity}
model: sonnet  effort: S  area: pdomain-ocr-trainer-spa
Blocked-by: #browser-verification

Context: Before any deletion steps begin, all core-parity acceptance criteria (Tasks 16 + 17) must be verified clean in CI. This is the gate for Phase 4.
Approach: Run full CI on `pdomain-ocr-trainer-spa` main branch; confirm all milestone acceptance tests and browser-verification tests pass; get CT sign-off.
Verification: `make ci` green on `pdomain-ocr-trainer-spa` main; `make e2e-browser` green
Acceptance:
- [ ] `make ci` passes on `pdomain-ocr-trainer-spa` main branch
- [ ] `make e2e-browser` passes (all Playwright tests green)
- [ ] CT sign-off on parity before deletion proceeds

---

## Task 19 — Archive + remove pd-ocr-trainer repo  {#delete-legacy-repo}
model: sonnet  effort: S  area: workspace
Blocked-by: #confirm-parity

Context: The legacy NiceGUI `pd-ocr-trainer` has been superseded and its code extracted. Archiving preserves history; removal clears it from the workspace.
Approach: Tag a final release on the legacy repo; archive it on GitHub (`gh repo archive`); remove the local `/workspaces/ocr-container/pd-ocr-trainer/` directory.
Verification: `gh repo view ConcaveTrillion/pd-ocr-trainer --json isArchived` returns `true`; directory absent from workspace
Acceptance:
- [ ] Final tag pushed to `ConcaveTrillion/pd-ocr-trainer` before archive
- [ ] Repo archived on GitHub (`isArchived: true`)
- [ ] `/workspaces/ocr-container/pd-ocr-trainer/` removed from workspace

---

## Task 20 — Remove pd-ocr-trainer + pd-ocr-trainer-docs subagents  {#remove-legacy-agents}
model: sonnet  effort: S  area: workspace
Blocked-by: #delete-legacy-repo

Context: The `.claude/agents/pd-ocr-trainer.md` and `.claude/agents/pd-ocr-trainer-docs.md` subagents become stale once the legacy repo is archived.
Approach: Delete both agent files from `.claude/agents/`; commit the removal.
Verification: `ls /workspaces/ocr-container/.claude/agents/ | grep pd-ocr-trainer` returns empty
Acceptance:
- [ ] `.claude/agents/pd-ocr-trainer.md` deleted
- [ ] `.claude/agents/pd-ocr-trainer-docs.md` deleted

---

## Task 21 — Update workspace CLAUDE.md  {#update-workspace-claude}
model: sonnet  effort: S  area: workspace
Blocked-by: #delete-legacy-repo

Context: The workspace `CLAUDE.md` project table and routing section still reference `pd-ocr-trainer`. These must be updated to drop the legacy entry and confirm the `pdomain-ocr-trainer-spa` and `pdomain-ocr-training` entries are correct.
Approach: Edit `CLAUDE.md`: remove `pd-ocr-trainer/` row from the project table; remove its routing entry; verify `pdomain-ocr-training/` and `pdomain-ocr-trainer-spa/` rows are accurate.
Verification: `grep -c pd-ocr-trainer /workspaces/ocr-container/CLAUDE.md` returns only references to `pdomain-ocr-trainer-spa` and `pdomain-ocr-training` (no bare `pd-ocr-trainer` rows)
Acceptance:
- [ ] `pd-ocr-trainer/` row removed from project table
- [ ] `pd-ocr-trainer` routing entry removed
- [ ] `pdomain-ocr-training/` and `pdomain-ocr-trainer-spa/` entries present and accurate

---

## Task 22 — Update agent memory referencing pd-ocr-trainer  {#update-agent-memory}
model: sonnet  effort: S  area: workspace
Blocked-by: #delete-legacy-repo

Context: Several agent memory files reference `pd-ocr-trainer` by name (notably `feedback_dropcap_trainer_keep.md`, `project_pd_ocr_trainer_retirement.md`, and any trainer-specific entries in per-repo memory). These should be updated to point to the new repos.
Approach: Search `.claude/agent-memory/` and `.claude/memory/` for `pd-ocr-trainer` references; update each file to name `pdomain-ocr-trainer-spa` / `pdomain-ocr-training` as appropriate; remove entries that no longer apply.
Verification: `grep -r "pd-ocr-trainer[^-]" /workspaces/ocr-container/.claude/` lists only archive/historical references
Acceptance:
- [ ] `feedback_dropcap_trainer_keep.md` updated to reference `pdomain-ocr-training`
- [ ] `project_pd_ocr_trainer_retirement.md` updated to record completion
- [ ] No active agent memory still routes to the archived `pd-ocr-trainer` repo

---

## Task 23 — Close the cross-cut tracking issue  {#close-tracking}
model: sonnet  effort: S  area: workspace
Blocked-by: #update-workspace-claude, #update-agent-memory

Context: This retirement plan has a cross-cut tracking issue in `ConcaveTrillion/ocr-container-meta`. Once all other tasks are complete, it should be closed.
Approach: Confirm all other tasks in this plan are closed; close the tracking issue with a summary comment.
Verification: `gh issue view <N> --repo ConcaveTrillion/ocr-container-meta` shows `state: CLOSED`
Acceptance:
- [ ] All Tasks 1–22 are closed (or explicitly deferred with a note)
- [ ] Tracking issue closed with a summary comment

---

## Self-Review

- **Spec coverage:** Design §"Target architecture" → Phase 1 (Tasks 1–8) + Tasks 9–11; §"Component inventory" non-UI half → Tasks 2–4; UI half → Task 10; §"pdomain-ui gaps" → Task 10; §"Retirement sequence" → Phases 1–4 (Tasks 1–23); §"Deferred scope" → Task 13; §"Plan artifacts" (one cross-cut plan) → this document's frontmatter. All design decisions D-1…D-6 are reflected. No gaps.
- **Placeholders:** Phase 1 tasks (1–8) carry concrete code/commands. Phases 2–4 tasks are intentionally milestone-level because they decompose into their own spec→plan cycles — this is decomposition, not a placeholder; each milestone names a concrete deliverable.
- **Type consistency:** `ITrainingRunner`, `TrainingEvent`, `LocalTrainingRunner` used consistently across Tasks 5–7 and Task 11.
- **FastAPI + SPA check:** `pdomain-ocr-trainer-spa` is FastAPI + bundled SPA — the browser-verification milestone (Task 17) is present and mandatory, including the SPA-serving contract tests (`test_routes_root.py` pattern).
- **Dependency order:** Tasks appear in strict dependency order. All `Blocked-by` references point to earlier task slugs. Phase 4 is fully gated on Phase 3 parity.
