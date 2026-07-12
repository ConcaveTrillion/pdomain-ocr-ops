# labeler-spa header → workspace-toolbar realignment — Implementation Plan

> **STATUS: EXECUTED & PUSHED — 2026-06-14.** pdomain-ui **0.7.3** released
> (ButtonGroup/IconButton; StageToolbar/DropdownMenu/SettingsModal already
> existed). labeler-spa `origin/master` **d87551b**: chrome-only header +
> `WorkspaceToolbar` band + drawer search + theme→Settings; all `display:none`
> testid-stubs removed (D-049/D-050/D-052) per CT directive; PageActionsCompact
> adopts the pdomain-ui primitives; dead `PageActions.tsx` deleted. `make ci`
> green; `make e2e` green except a **7-test pre-existing baseline** (layer/zoom/
> selection/canvas parity-gaps, proven pre-existing on `db42ed0`, out of arc
> scope). Execution diverged from the milestone split below: M1 absorbed the
> 2B/2C/2D/2E relocations (StudioShell is not in the live render path — band
> mounts in ProjectPage, D-047), so M2 collapsed to primitive-adoption +
> de-stubbing, and a final slice implemented-via-already-existing the two modals.
> Decisions D-047…D-052 in `specs/17-decisions.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move every document/page-scoped control out of the labeler-spa AppShell header into an in-body `StageToolbar` workspace band, leaving the header as pure pdomain-ui chrome, while preserving all `data-testid`s the Playwright driver depends on.

**Architecture:** Upstream-first cross-repo work. (0) pdomain-ui gains/confirms the generic toolbar primitives, releases if needed. (1) A scaffold slice in labeler-spa establishes the chrome-only header + an empty `WorkspaceToolbar` band in `StudioShell` + a drawer worklist-header slot, creating stable non-overlapping insertion points. (2) Parallel content slices each relocate one control domain into its slot with disjoint file ownership. (3) Docs/decisions updated. (4) Browser verification.

**Tech Stack:** React/Vite/TS, `@pdomain/pdomain-ui` (AppShell, StageToolbar, SettingsModal/Appearance, primitives), Vitest, Playwright e2e, FastAPI backend, `make ci AI=1`.

**Repos:** `pdomain-ocr-labeler-spa` (primary), `pdomain-ui` (upstream).

**Design:** `docs/specs/2026-06-14-labeler-spa-header-to-workspace-toolbar-design.md`

---

## File structure map

**pdomain-ui (only if primitives missing in code):**
- `src/primitives/` — `DropdownMenu` (overflow), `ButtonGroup`, `IconButton` (add if absent)
- their tests + barrel exports + Storybook entries as the repo convention requires

**pdomain-ocr-labeler-spa (`frontend/src/`):**
- `components/HeaderBar.tsx` — slim to chrome (confirm path: may be `components/shell/HeaderBar.tsx`)
- `components/shell/WorkspaceToolbar.tsx` — **new**; wraps pdomain-ui `StageToolbar`
- `components/shell/StudioShell.tsx` — mount `WorkspaceToolbar` in the header zone
- `components/shell/Drawer.tsx` — add worklist-header slot for QuickSearch
- `App.tsx` — slot rewiring (remove header injections; pass nothing document-scoped to header)
- `components/PageActionsCompact.tsx` — relocate into toolbar centerSlot
- `components/ProjectNavigationControls.tsx` — relocate into toolbar leftSlot
- metrics strip component (currently inline in HeaderBar) — extract to `components/shell/WorkspaceMetrics.tsx`, mount in toolbar rightSlot
- `components/shell/QuickSearch.tsx` — relocate into Drawer worklist header
- theme handling — drop local theme chips; rely on SettingsModal Appearance panel
- `docs/architecture/03-frontend.md`, `docs/architecture/24-shell-layout.md` — correct to end state
- `specs/17-decisions.md` — add D-0xx (theme testid relocation) + a decision recording the header→toolbar move
- tests: each moved component's `*.test.tsx` re-pointed; new `WorkspaceToolbar.test.tsx`; `HeaderBar.test.tsx` asserts chrome-only; e2e under `frontend/tests/` (or repo's e2e dir)

> Per-repo full-power agents apply TDD at step granularity (write failing test → run red → implement → run green → commit) inside each slice. This plan fixes the boundaries, acceptance criteria, and testid constraints; the agent owns the line-level code in files it reads in its worktree.

---

## Milestone 0 — pdomain-ui upstream gate

**Agent:** `pdomain-ui` (isolation: worktree). **Gates all labeler-spa work.**

### Task 0.1: Verify code-vs-spec for the needed primitives
- [ ] In the pdomain-ui worktree, confirm whether **DropdownMenu/overflow menu**, **ButtonGroup**, and **IconButton** exist *in code* (not just specs). Also confirm `StageToolbar` exports `leftSlot`/`centerSlot`/`rightSlot` and the `SettingsModal` Appearance panel owns theme.
- [ ] Report: for each primitive, EXISTS or MISSING.

### Task 0.2: Add missing primitives (TDD), only those reported MISSING
- [ ] For each MISSING primitive: write failing test (Vitest) for its public API and a11y contract; implement minimal; green; add to barrel export + Storybook per repo convention.
- [ ] Apply the decision rule: only generic toolbar mechanics belong here. No labeler domain logic.

### Task 0.3: CI + release decision
- [ ] `make ci AI=1` green in the worktree.
- [ ] If anything was added: cut a release and publish to `pdomain-index-npm` following the repo's release flow. If everything already EXISTED: **no-op — skip the release**, record that in the return message.
- [ ] Commit on the worktree branch. Do NOT open a PR. Return worktree path + branch + the new version (or "no release needed").

**Acceptance:** Either a published pdomain-ui version exposing DropdownMenu/ButtonGroup/IconButton, or confirmation they already exist. labeler-spa can build the toolbar against released primitives.

**Orchestrator after 0:** Opus review subagent audits the worktree → rebase onto local master → `git merge --ff-only` → (if released) bump labeler-spa via `make update-pd-deps`.

---

## Milestone 1 — Scaffold slice (labeler-spa)

**Agent:** `pdomain-ocr-labeler-spa` (isolation: worktree). **Single worktree, runs after M0, before M2.**

### Task 1.1: Chrome-only HeaderBar shell
- [ ] Failing test in `HeaderBar.test.tsx`: header renders icon, app name, project path breadcrumb, and exposes the SettingsSlot gear + LauncherSlot; asserts **absence** of `nav-prev-button`, `quick-search-input`, `page-actions-compact-save-page`, `header-metrics-strip`, `theme-chips`.
- [ ] Run red.
- [ ] Implement: strip navSlot/searchSlot/actionsSlot/metrics/theme wiring from HeaderBar; keep chrome. Leave the document-scoped child components in the tree (un-mounted from header) — M2 relocates them.
- [ ] Run green. Commit.

### Task 1.2: Empty WorkspaceToolbar band in StudioShell
- [ ] Failing test: new `WorkspaceToolbar.test.tsx` asserts it renders a `StageToolbar` with empty `leftSlot`/`centerSlot`/`rightSlot` and carries `data-testid="workspace-toolbar"`; `StudioShell.test.tsx` asserts the band mounts in the header zone on the project route.
- [ ] Run red.
- [ ] Implement `WorkspaceToolbar.tsx` (wraps pdomain-ui `StageToolbar`, slots accept `ReactNode` props) and mount it in `StudioShell`'s header zone.
- [ ] Run green. Commit.

### Task 1.3: Drawer worklist-header slot
- [ ] Failing test in `Drawer.test.tsx`: the worklist tab renders a header slot region (`data-testid="drawer-worklist-header"`) that accepts injected content.
- [ ] Run red. Implement the slot. Run green. Commit.

### Task 1.4: App.tsx slot rewiring
- [ ] Failing test (integration render): App renders chrome-only header + the WorkspaceToolbar band on a project route; no document-scoped testids in the header subtree.
- [ ] Run red. Rewire `App.tsx`: header gets only chrome; WorkspaceToolbar slots + drawer slot are fed from the project workspace (props threaded to StudioShell). Run green.
- [ ] `make ci AI=1` green. Commit. Return worktree path + branch. No PR.

**Acceptance:** Header is chrome-only; an empty (but mounted) workspace toolbar band and a drawer worklist-header slot exist with stable testids. App still builds and all existing suites pass (relocated controls may be temporarily absent from view — that's expected and M2 restores them; if any existing test asserts a control's *presence in the header*, update it here to assert presence in its new slot's mount point or mark the relocation explicitly).

**Orchestrator after 1:** Opus review → rebase → ff-merge. **M2 slices branch from this merged master.**

---

## Milestone 2 — Parallel content slices (labeler-spa)

**Agent per slice:** `pdomain-ocr-labeler-spa` (isolation: worktree). **Dispatched in parallel; disjoint file ownership.** Each slice: relocate the component into its slot, preserve every `data-testid` exactly (D-014), re-point its unit test, keep behavior identical.

### Slice 2A — Page actions → toolbar centerSlot
- **Owns:** `components/PageActionsCompact.tsx`, `PageActionsCompact.test.tsx`, the centerSlot wiring inside `WorkspaceToolbar.tsx`.
- [ ] Failing test: every page-action testid (`page-actions-compact-reload-ocr`, `-rematch-gt`, `-save-page`, `undo-button`, `redo-button`, `page-actions-compact-export`, `ocr-config-trigger-button`, `page-actions-compact-overflow` + overflow items `reload-ocr-edited-button`, `save-project-button`, `load-page-button`, `rotate-cw-button`, `rotate-ccw-button`, `rotate-180-button`, `auto-rotate-all-button`, `rotation-badge`, `bulk-glyph-mark-button`) renders inside the workspace toolbar centerSlot.
- [ ] Run red. Mount `PageActionsCompact` in centerSlot; rebuild its overflow/grouping using pdomain-ui `DropdownMenu`/`ButtonGroup`/`IconButton` (from M0) instead of any local hand-rolled versions, keeping testids identical. Run green. Commit. Return path+branch.

### Slice 2B — Navigation → toolbar leftSlot
- **Owns:** `components/ProjectNavigationControls.tsx`, its test, the leftSlot wiring.
- [ ] Failing test: `nav-prev-button`, `nav-page-input`, `nav-next-button`, `nav-page-total-label`, `nav-goto-button` render in the toolbar leftSlot; disabled-at-bounds behavior intact.
- [ ] Run red. Mount in leftSlot. Run green. Commit. Return path+branch.

### Slice 2C — Metrics → toolbar rightSlot
- **Owns:** new `components/shell/WorkspaceMetrics.tsx` (extracted from HeaderBar), its test, the rightSlot wiring.
- [ ] Failing test: `header-metrics-strip` (keep testid for driver continuity) renders in the toolbar rightSlot with exact/fuzzy/mismatch/validated/glyph counts.
- [ ] Run red. Extract + mount in rightSlot. Run green. Commit. Return path+branch.

### Slice 2D — ⌘K search → drawer worklist header
- **Owns:** `components/shell/QuickSearch.tsx`, its test, the `drawer-worklist-header` injection.
- [ ] Failing test: `quick-search`, `quick-search-input`, `quick-search-keycap` render inside `drawer-worklist-header`; ⌘K still focuses the input; worklist filtering unchanged.
- [ ] Run red. Inject into drawer slot. Run green. Commit. Return path+branch.

### Slice 2E — Theme → SettingsModal Appearance panel
- **Owns:** theme handling (drop local theme chips from HeaderBar's remnants), App.tsx theme wiring, `HeaderBar.test.tsx` theme assertions.
- [ ] Failing test: theme is changeable via the SettingsModal Appearance panel; the legacy `theme-chips`/`theme-chip-*` are no longer in the header. (If the driver still needs theme testids, add them in the Appearance-panel integration and assert there.)
- [ ] Run red. Remove local theme chips; rely on pdomain-ui Appearance panel; thread `uiPrefsConfig`/`settingsPanels` so theme persists. Run green. Commit. Return path+branch.

**Orchestrator for M2:** Use explicit `git worktree add` per slice with absolute paths in each agent prompt (do not rely on `isolation:"worktree"` alone for parallel agents). After each slice returns: Opus review subagent (correctness, deferred items, inconsistency, testid integrity) → rebase that branch onto current local master → `git merge --ff-only`. Merge **sequentially** so conflicts surface one at a time; re-rebase any later slice if an earlier merge moves master. `git status` the canonical checkout after each dispatch to catch stray canonical writes.

**Acceptance:** All relocated controls live in their slots; header has zero document-scoped testids; every preserved testid present at its new location; all unit suites green.

---

## Milestone 3 — Docs & decisions

**Agent:** `pdomain-ocr-labeler-spa` (isolation: worktree). Runs after M2 merges.
- [ ] Update `docs/architecture/03-frontend.md` (header = chrome only) and `docs/architecture/24-shell-layout.md` (header band = chrome; new workspace toolbar band above the five zones; ⌘K in drawer).
- [ ] Add to `specs/17-decisions.md`: a decision recording the header→workspace-toolbar move, and **D-0xx** for the theme testid relocation (assign the next free number; note legacy testids removed and where theme now lives).
- [ ] `make ci AI=1` green. Commit. Return path+branch.

---

## Milestone 4 — Browser verification (MANDATORY — FastAPI+SPA)

**Agent:** `pdomain-ocr-labeler-spa` (isolation: worktree). labeler-spa already has Playwright e2e infra (reuse it; do not re-bootstrap).
- [ ] **App loads:** open the running server in Chromium; assert the project workspace renders; no `console.error` about failed resource loads.
- [ ] **Header is chrome-only:** assert none of the page-action / nav / search / metrics / theme testids exist within the header element.
- [ ] **Workspace toolbar reachable:** assert `workspace-toolbar` visible; `page-actions-compact-save-page`, `nav-next-button`, `header-metrics-strip` present and enabled in the body.
- [ ] **⌘K focus:** press ⌘K (Meta+K) → assert `quick-search-input` focused (now in the drawer).
- [ ] **Theme via settings:** open SettingsModal ⚙ → switch theme in Appearance → assert document theme attribute changes.
- [ ] **Route test:** navigate directly to a `/project/:id/page/:n` sub-path → assert the workspace renders (not a 404), toolbar present.
- [ ] Wire `make e2e-browser` into `make ci` if not already. `make ci AI=1` green. Commit. Return path+branch.

**Acceptance:** Browser-verified that the toolbar moved, header is chrome-only, search and theme work in their new homes, and routes render.

**Orchestrator after 4:** Opus review → rebase → ff-merge. Push only on explicit CT authorization.

---

## Self-review

- **Spec coverage:** header→chrome (M1.1, 2E), page-actions→centerSlot (2A), nav→leftSlot (2B), metrics→rightSlot (2C), search→drawer (2D, M1.3), theme→Appearance (2E), pdomain-ui primitives (M0), D-014 testid preservation (every M2 slice), theme-testid decision + stale-doc fix (M3), browser verification (M4). All design sections mapped. ✅
- **Placeholder scan:** `D-0xx` is an intentional "assign next free number" instruction, not a gap. No TBD/TODO. ✅
- **Type consistency:** slot names `leftSlot`/`centerSlot`/`rightSlot`, testid `workspace-toolbar`, `drawer-worklist-header` used consistently across M1/M2/M4. ✅
- **FastAPI+SPA check:** Milestone 4 browser verification present and mandatory. ✅
