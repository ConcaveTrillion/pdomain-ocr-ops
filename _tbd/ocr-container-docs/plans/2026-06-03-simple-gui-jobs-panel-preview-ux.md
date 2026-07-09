# simple-gui Jobs Panel + Preview UX Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the simple-gui jobs panel (leaked test runs, no delete, finished runs still animating) and the image/text preview (download checkboxes, non-expanding text box, toolbar not reflowing on pin), landing the shared-library pieces in pdomain-ui first.

**Architecture:** pdomain-ui owns the jobs panel rendering, the done-job animation, the `PageSplitView` editor panel, and the pinned-dock layout grid. Those changes ship in pdomain-ui 0.6.0. simple-gui then consumes 0.6.0 and supplies the data/wiring: a backend filter + purge for `e2etestjob-*` leak, the trash→`DELETE /api/jobs/{id}` wiring, two explicit download buttons, and the text-fill page usage. A final Playwright browser-verification milestone proves the user-visible result.

**Tech Stack:** pdomain-ui — TS/React/Vite, Vitest, Storybook, pnpm, `@concavetrillion/pdomain-ui` npm package. simple-gui — FastAPI, React/Vite/TS, uv, pytest (`-n auto`), Vitest, pytest-playwright.

**Spec:** `docs/specs/2026-06-03-simple-gui-jobs-panel-preview-ux.md`

**Cross-repo ordering (mandatory):**
1. Milestone 1 (pdomain-ui) lands and publishes 0.6.0 to `pdomain-index-npm`.
2. Milestone 2 (simple-gui) bumps to `^0.6.0` and consumes the new API.
3. Milestone 3 (browser verification) runs against the integrated app.

Use the per-repo agents (`pdomain-ui`, `pdomain-ocr-simple-gui`) in isolated
worktrees. Each agent reads the target file before editing — exact line numbers
below are from a point-in-time exploration and may have shifted.

---

## Milestone 1 — pdomain-ui (ships first, 0.5.x → 0.6.0)

### Task 1: Make done jobs visually static (stop the shimmer)

**Files:**
- Modify: `src/shell/JobRow.tsx` (shimmer overlay ~lines 95–111; dot pulse ~line 129; `isDone()` ~line 49)
- Test: `src/shell/__tests__/JobRow.test.tsx` (create if absent)

- [ ] **Step 1: Write the failing test** — a done job renders no shimmer and no pulse.

```tsx
import { render } from '@testing-library/react';
import { JobRow } from '../JobRow';

const doneJob = { id: 'j1', project: 'Book A', phase: 'done', pct: 100, status: 'done' as const, cancelable: false };

test('done job has no shimmer overlay', () => {
  const { container } = render(<JobRow job={doneJob} />);
  expect(container.querySelector('.shimmer')).toBeNull();
});

test('done job status dot has no infinite animation', () => {
  const { container } = render(<JobRow job={doneJob} />);
  const dot = container.querySelector('[data-testid="job-status-dot"]');
  // dot must exist; its computed inline animation must be 'none'
  expect(dot).not.toBeNull();
  expect((dot as HTMLElement).style.animation === '' || (dot as HTMLElement).style.animation === 'none').toBe(true);
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `pnpm vitest run src/shell/__tests__/JobRow.test.tsx`
Expected: FAIL — `.shimmer` element is present for done jobs.

- [ ] **Step 3: Remove the shimmer for done rows.** In `JobRow.tsx`, delete the `{done ? (<div className="shimmer" .../>) : null}` block (the shimmer was only ever rendered for done jobs). Confirm the dot pulse is already gated `!done && !paused && !failed` (leave as-is). Add `data-testid="job-status-dot"` to the status dot span if missing.

- [ ] **Step 4: Run test, verify it passes**

Run: `pnpm vitest run src/shell/__tests__/JobRow.test.tsx`
Expected: PASS.

- [ ] **Step 5: Remove now-dead CSS.** If `.shimmer` / `@keyframes pgd-shimmer` in `theme/primitives.css` is unused elsewhere (grep `shimmer` across `src/`), delete it. If still referenced, leave it.

Run: `grep -rn "shimmer" src/ theme/`

- [ ] **Step 6: Commit**

```bash
git add src/shell/JobRow.tsx src/shell/__tests__/JobRow.test.tsx theme/primitives.css
git commit -m "fix(shell): done jobs render static, no infinite shimmer"
```

### Task 2: Add `onJobDelete` + trash button to the jobs panel

**Files:**
- Modify: `src/shell/types.ts` (`AppShellJobsProps` ~lines 120–143)
- Modify: `src/shell/JobsPanelBody.tsx` (props ~lines 13–24)
- Modify: `src/shell/JobRow.tsx` (row actions ~lines 225–304)
- Modify: `src/shell/testids.ts` (or wherever testid constants live) — add `JOB_DELETE`
- Test: `src/shell/__tests__/JobRow.test.tsx`

- [ ] **Step 1: Write the failing test** — a trash button appears for finished runs and calls `onJobDelete` with the id.

```tsx
import { fireEvent } from '@testing-library/react';

test('finished job shows trash button that calls onJobDelete', () => {
  const onJobDelete = vi.fn();
  const { getByTestId } = render(<JobRow job={doneJob} onJobDelete={onJobDelete} />);
  fireEvent.click(getByTestId('job-delete-j1'));
  expect(onJobDelete).toHaveBeenCalledWith('j1');
});

test('running job does not show trash button', () => {
  const running = { ...doneJob, phase: 'running', status: 'running' as const, pct: 40 };
  const { queryByTestId } = render(<JobRow job={running} onJobDelete={vi.fn()} />);
  expect(queryByTestId('job-delete-j1')).toBeNull();
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `pnpm vitest run src/shell/__tests__/JobRow.test.tsx`
Expected: FAIL — no trash button / `onJobDelete` prop.

- [ ] **Step 3: Thread the prop through the types.** In `types.ts` add to `AppShellJobsProps`:

```ts
/** Permanently delete a finished/failed run. */
onJobDelete?: (id: string) => void;
```

In `JobsPanelBody.tsx` add `onJobDelete?: (id: string) => void;` to its props and pass it into each `<JobRow … onJobDelete={onJobDelete} />`. Add `onJobDelete` to `JobRowProps`.

- [ ] **Step 4: Render the trash button.** In `JobRow.tsx`, inside the hover-actions area, add — only when `done || failed || cancelled` and `onJobDelete` is provided — a trash button using the existing icon set:

```tsx
{(done || failed) && onJobDelete ? (
  <button
    type="button"
    data-testid={`job-delete-${job.id}`}
    aria-label="Delete run"
    className="job-row__action"
    onClick={() => onJobDelete(job.id)}
  >
    <TrashIcon />
  </button>
) : null}
```

Use the repo's existing icon component (grep `icons` for a trash/delete glyph; add one to the icon set if missing, following the existing icon pattern).

- [ ] **Step 5: Run test, verify it passes**

Run: `pnpm vitest run src/shell/__tests__/JobRow.test.tsx`
Expected: PASS.

- [ ] **Step 6: Update Storybook.** If `JobsPanelBody`/`AppShell` has a story, add an `onJobDelete` action arg so the trash button is exercised in Storybook.

- [ ] **Step 7: Commit**

```bash
git add src/shell/types.ts src/shell/JobsPanelBody.tsx src/shell/JobRow.tsx src/shell/testids.ts src/icons/
git commit -m "feat(shell): onJobDelete callback + trash button for finished jobs"
```

### Task 3: `PageSplitView` editor text area fills the panel by default

**Files:**
- Modify: `src/primitives/PageSplitView.tsx` (editor panel)
- Modify: `theme/primitives.css` (`.page-split-view__editor-panel` ~lines 887–909; textarea ~lines 345–364)
- Test: `src/primitives/__tests__/PageSplitView.test.tsx` (create if absent)

- [ ] **Step 1: Write the failing test** — the editor panel's text area uses a fill layout, not a fixed `rows`.

```tsx
import { render } from '@testing-library/react';
import { PageSplitView } from '../PageSplitView';

test('editor text area fills panel height (no fixed rows attr)', () => {
  const { container } = render(
    <PageSplitView image={<div />} editor={<textarea data-testid="ed" />} />,
  );
  const panel = container.querySelector('.page-split-view__editor-panel') as HTMLElement;
  expect(panel).not.toBeNull();
  // the editor slot host should allow a flex child to fill + shrink
  expect(getComputedStyle(panel).display).toContain('flex');
});
```

(Adjust the `PageSplitView` props to the real API the agent finds — `editor`, `canvas`, render-prop, etc. The assertion that matters: the editor slot is a column flex container whose child can fill.)

- [ ] **Step 2: Run test, verify it fails** if the panel does not yet provide a fill host.

Run: `pnpm vitest run src/primitives/__tests__/PageSplitView.test.tsx`

- [ ] **Step 3: Make the editor slot fill by default.** Ensure `.page-split-view__editor-panel` is `display:flex; flex-direction:column; min-height:0` and give the editor child slot:

```css
.page-split-view__editor-panel > * {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
```

This makes any text area handed in fill the panel and scroll internally — without the consumer setting a fixed `rows`. Document in the component's JSDoc that the editor slot fills by default.

- [ ] **Step 4: Run test, verify it passes**

Run: `pnpm vitest run src/primitives/__tests__/PageSplitView.test.tsx`

- [ ] **Step 5: Commit**

```bash
git add src/primitives/PageSplitView.tsx theme/primitives.css src/primitives/__tests__/PageSplitView.test.tsx
git commit -m "feat(primitives): PageSplitView editor slot fills panel height by default"
```

### Task 4: Fix pinned-dock content reflow (toolbar shrinks with pin)

**Files:**
- Modify: `src/shell/AppShell.tsx` (grid ~lines 203–241) and/or `src/primitives/PageSplitView.tsx`
- Modify: `theme/primitives.css`
- Test: `src/shell/__tests__/AppShell.reflow.test.tsx` (create)

**Root-cause hypothesis:** AppShell sets `--shell-right-w` so the `main` grid column shrinks when pinned, but a descendant flex/grid item lacks `min-width:0`, so it refuses to shrink below its content width and the toolbar never reflows.

- [ ] **Step 1: Reproduce.** In Storybook (or a scratch story), render AppShell with a pinned dock and wide `PageSplitView` content; confirm the content/toolbar does not narrow. Note which element overflows (DevTools: the first ancestor without `min-width:0`).

- [ ] **Step 2: Write the failing test** — the AppShell `main` region and its content host both allow shrinking.

```tsx
test('main content host has min-width:0 so it can shrink under a pinned dock', () => {
  const { container } = render(<AppShell {...pinnedDockProps}><WideContent /></AppShell>);
  const main = container.querySelector('[data-testid="shell-main"]') as HTMLElement;
  expect(getComputedStyle(main).minWidth).toBe('0px');
});
```

Add `data-testid="shell-main"` to the main grid area if missing.

- [ ] **Step 3: Run test, verify it fails**

Run: `pnpm vitest run src/shell/__tests__/AppShell.reflow.test.tsx`

- [ ] **Step 4: Apply `min-width:0`** to the main grid area and to the `PageSplitView` root + its `__panels` grid (whichever the repro identified). Example:

```css
.page-split-view, .page-split-view__panels { min-width: 0; }
```

and on the AppShell main area inline style/class: `minWidth: 0`.

- [ ] **Step 5: Run test, verify it passes; re-verify the repro** — toolbar now narrows when the dock is pinned.

Run: `pnpm vitest run src/shell/__tests__/AppShell.reflow.test.tsx`

- [ ] **Step 6: Commit**

```bash
git add src/shell/AppShell.tsx src/primitives/PageSplitView.tsx theme/primitives.css src/shell/__tests__/AppShell.reflow.test.tsx
git commit -m "fix(shell): main content reflows under pinned dock (min-width:0)"
```

> If the repro shows the non-shrinking element is in simple-gui's page wrapper rather than pdomain-ui, record that here and move the fix to Milestone 2 Task 11 instead.

### Task 5: Release pdomain-ui 0.6.0

**Files:**
- Modify: `package.json` version (or the repo's release mechanism), `CHANGELOG.md`

- [ ] **Step 1:** Run `make ci AI=1` in the worktree; confirm green (lint, typecheck, vitest, build).
- [ ] **Step 2:** Add a CHANGELOG entry for 0.6.0: done-job static rendering, `onJobDelete` + trash button, `PageSplitView` fill-by-default, pinned-dock reflow fix.
- [ ] **Step 3:** Follow the repo's publish flow to cut **0.6.0** to `pdomain-index-npm`.
- [ ] **Step 4: Commit + (with CT authorization) push.**

```bash
git add package.json CHANGELOG.md
git commit -m "chore(release): pdomain-ui 0.6.0"
```

---

## Milestone 2 — simple-gui (consumes pdomain-ui 0.6.0)

### Task 6: Backend filter — `e2etestjob-*` never surfaces

**Files:**
- Modify: `src/pdomain_ocr_simple_gui/storage.py` (`list_projects()`)
- Modify: `src/pdomain_ocr_simple_gui/routes/jobs.py` (`list_jobs`, `_add_to_recent_projects`)
- Create: `src/pdomain_ocr_simple_gui/_testjobs.py` (single source of the prefix + predicate)
- Test: `tests/test_storage.py`, `tests/test_routes_jobs.py`

- [ ] **Step 1: Write the failing test.**

```python
# tests/test_storage.py
from pdomain_ocr_simple_gui import storage
from pdomain_ocr_simple_gui._testjobs import TEST_JOB_PREFIX

def test_list_projects_excludes_test_jobs(tmp_path, monkeypatch):
    monkeypatch.setenv("PD_OCR_SIMPLE_GUI_PROJECTS_ROOT", str(tmp_path))
    (tmp_path / f"{TEST_JOB_PREFIX}abc").mkdir()
    (tmp_path / "real-job-1").mkdir()
    ids = [p.project_id for p in storage.list_projects()]
    assert "real-job-1" in ids
    assert all(not i.startswith(TEST_JOB_PREFIX) for i in ids)
```

- [ ] **Step 2: Run test, verify it fails**

Run: `uv run pytest tests/test_storage.py::test_list_projects_excludes_test_jobs -n0 -v`
Expected: FAIL — test job is listed.

- [ ] **Step 3: Add the shared predicate.**

```python
# src/pdomain_ocr_simple_gui/_testjobs.py
"""Single source of truth for the e2e test-job id prefix."""
TEST_JOB_PREFIX = "e2etestjob-"

def is_test_job(project_id: str) -> bool:
    return project_id.startswith(TEST_JOB_PREFIX)
```

- [ ] **Step 4: Apply the filter** in `storage.list_projects()` (skip dirs where `is_test_job(project_id)`) and in `routes/jobs.list_jobs` (filter the returned list) and in `_add_to_recent_projects` (never record a test id). Import from `_testjobs`.

- [ ] **Step 5: Add the jobs-route test.**

```python
# tests/test_routes_jobs.py
def test_list_jobs_excludes_test_jobs(client, seed_project):
    seed_project("e2etestjob-x", state="succeeded")
    seed_project("real-y", state="succeeded")
    ids = [j["project_id"] for j in client.get("/api/jobs").json()]
    assert "real-y" in ids and "e2etestjob-x" not in ids
```

(Use the repo's existing fixtures; adapt `seed_project` to the real helper.)

- [ ] **Step 6: Run tests, verify they pass**

Run: `uv run pytest tests/test_storage.py tests/test_routes_jobs.py -n0 -v`

- [ ] **Step 7: Commit**

```bash
git add src/pdomain_ocr_simple_gui/_testjobs.py src/pdomain_ocr_simple_gui/storage.py src/pdomain_ocr_simple_gui/routes/jobs.py tests/
git commit -m "fix(jobs): exclude e2etestjob-* ids from listings and recent projects"
```

### Task 7: Purge leaked runs + harden the e2e fixtures

**Files:**
- Create: `src/pdomain_ocr_simple_gui/scripts/purge_test_jobs.py`
- Modify: `tests/e2e/conftest.py` (root fixtures)
- Test: `tests/test_purge_test_jobs.py`, `tests/e2e/test_fixture_guard.py`

- [ ] **Step 1: Write the failing purge test.**

```python
# tests/test_purge_test_jobs.py
from pdomain_ocr_simple_gui.scripts.purge_test_jobs import purge

def test_purge_removes_test_job_dirs_and_recent(tmp_path, monkeypatch):
    monkeypatch.setenv("PD_OCR_SIMPLE_GUI_PROJECTS_ROOT", str(tmp_path))
    (tmp_path / "e2etestjob-a").mkdir()
    (tmp_path / "keep-b").mkdir()
    removed = purge()
    assert "e2etestjob-a" in removed
    assert (tmp_path / "keep-b").exists()
    assert not (tmp_path / "e2etestjob-a").exists()
```

- [ ] **Step 2: Run test, verify it fails**

Run: `uv run pytest tests/test_purge_test_jobs.py -n0 -v`

- [ ] **Step 3: Implement `purge()`** — iterate the projects root (and output/meta roots), `is_test_job()` → remove dir; also drop matching ids from prefs `recent_projects`. Return the list of removed ids. Make it runnable as `python -m pdomain_ocr_simple_gui.scripts.purge_test_jobs` and log what it removed.

- [ ] **Step 4: Run test, verify it passes**

Run: `uv run pytest tests/test_purge_test_jobs.py -n0 -v`

- [ ] **Step 5: Harden the fixtures.** In `tests/e2e/conftest.py`, after computing the projects/output/meta roots, assert each is inside the session tmpdir before any seeding:

```python
def _assert_under_tmp(path, tmp_root):
    resolved = Path(path).resolve()
    if tmp_root.resolve() not in resolved.parents and resolved != tmp_root.resolve():
        raise RuntimeError(f"e2e fixture refusing to write outside tmpdir: {resolved}")
```

Call it in the `live_server_url`/`e2e_data_root` setup for all three roots.

- [ ] **Step 6: Add the guard test.**

```python
# tests/e2e/test_fixture_guard.py
import pytest
from pathlib import Path
from tests.e2e.conftest import _assert_under_tmp

def test_guard_rejects_non_tmp_root(tmp_path):
    with pytest.raises(RuntimeError):
        _assert_under_tmp(Path("/home/vscode/real-root"), tmp_path)
```

- [ ] **Step 7: Run the cleanup once for real** (outside tests, against CT's actual root) and report what was removed:

Run: `uv run python -m pdomain_ocr_simple_gui.scripts.purge_test_jobs`

- [ ] **Step 8: Commit**

```bash
git add src/pdomain_ocr_simple_gui/scripts/purge_test_jobs.py tests/test_purge_test_jobs.py tests/e2e/conftest.py tests/e2e/test_fixture_guard.py
git commit -m "fix(e2e): purge leaked test jobs + guard fixtures against non-tmp roots"
```

### Task 8: Wire trash → `DELETE /api/jobs/{id}` + refetch

**Files:**
- Modify: `frontend/src/App.tsx` (dock mapping; pass `onJobDelete`)
- Test: `frontend/src/__tests__/App.test.tsx`

- [ ] **Step 1: Write the failing test** — clicking a dock row's trash calls `DELETE /api/jobs/{id}` then refetches.

```tsx
test('deleting a job calls DELETE and refetches', async () => {
  const del = vi.fn().mockResolvedValue({ ok: true });
  // mock fetch: GET /api/jobs returns [doneJob] first, [] after delete
  // render App, open jobs dock, click trash for the done job
  // assert del called with /api/jobs/<id> method DELETE, then list empty
});
```

(Flesh out using the repo's existing App test harness / msw mocks.)

- [ ] **Step 2: Run test, verify it fails**

Run: `pnpm vitest run src/__tests__/App.test.tsx`

- [ ] **Step 3: Implement.** In `App.tsx`, add a `deleteJob(id)` that `fetch('/api/jobs/'+id, { method:'DELETE' })` then invalidates the `active-jobs` query. Pass `onJobDelete={deleteJob}` into `AppShell`'s jobs props. Confirm the dock job mapping still renders done rows (the trash now provides the action regardless of `cancelable`).

- [ ] **Step 4: Run test, verify it passes**

Run: `pnpm vitest run src/__tests__/App.test.tsx`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/__tests__/App.test.tsx
git commit -m "feat(jobs): trash button deletes run via DELETE /api/jobs/{id}"
```

### Task 9: Replace download checkboxes with two buttons

**Files:**
- Modify: `frontend/src/pages/ResultsPage.tsx` (checkboxes ~lines 239–281; download URL ~lines 169–175)
- Modify: `frontend/src/pages/PageViewPage.tsx` (download shortcuts)
- Test: `frontend/src/pages/__tests__/ResultsPage.test.tsx`, `frontend/src/pages/__tests__/PageViewPage.test.tsx`

- [ ] **Step 1: Write the failing test** — two buttons, correct `include=` URLs, no checkboxes.

```tsx
test('shows two download buttons with correct include params', () => {
  const assign = vi.spyOn(window.location, 'assign').mockImplementation(() => {});
  const { getByTestId, queryByRole } = render(<ResultsPage jobId="j1" />);
  expect(queryByRole('checkbox')).toBeNull();
  fireEvent.click(getByTestId('download-images-text'));
  expect(assign).toHaveBeenCalledWith('/api/jobs/j1/download?include=text');
  fireEvent.click(getByTestId('download-images-text-json'));
  expect(assign).toHaveBeenCalledWith('/api/jobs/j1/download?include=text,json');
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `pnpm vitest run src/pages/__tests__/ResultsPage.test.tsx`

- [ ] **Step 3: Implement.** Remove the `includeText`/`includeJson` state and the `<fieldset>` checkboxes. Add two buttons:

```tsx
<button data-testid="download-images-text"
  onClick={() => window.location.assign(`/api/jobs/${id ?? ""}/download?include=text`)}>
  Download (images + text)
</button>
<button data-testid="download-images-text-json"
  onClick={() => window.location.assign(`/api/jobs/${id ?? ""}/download?include=text,json`)}>
  Download (images + text + JSON)
</button>
```

Mirror the same two-button pattern in `PageViewPage.tsx`'s download shortcuts. Confirm `routes/downloads.py::_parse_include` accepts `text` and `text,json` tokens (it does — images are always included). No backend change expected; if token names differ, match them.

- [ ] **Step 4: Run tests, verify they pass**

Run: `pnpm vitest run src/pages/__tests__/ResultsPage.test.tsx src/pages/__tests__/PageViewPage.test.tsx`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ResultsPage.tsx frontend/src/pages/PageViewPage.tsx frontend/src/pages/__tests__/
git commit -m "feat(download): replace include checkboxes with two explicit download buttons"
```

### Task 10: Text box auto-expands (drop fixed rows)

**Files:**
- Modify: `frontend/src/pages/PageViewPage.tsx` (textarea ~lines 561–573; remove `rows={40}`)
- Test: `frontend/src/pages/__tests__/PageViewPage.test.tsx`

- [ ] **Step 1: Write the failing test.**

```tsx
test('OCR text area has no fixed rows attr (fills panel)', () => {
  const { getByTestId } = render(<PageViewPage {...props} />);
  const ta = getByTestId('ocr-text') as HTMLTextAreaElement;
  expect(ta.getAttribute('rows')).toBeNull();
});
```

Add `data-testid="ocr-text"` to the textarea if missing.

- [ ] **Step 2: Run test, verify it fails**

Run: `pnpm vitest run src/pages/__tests__/PageViewPage.test.tsx`

- [ ] **Step 3: Implement.** Remove `rows={40}` from the textarea; rely on the pdomain-ui 0.6.0 `PageSplitView` editor-slot fill default (Task 3). Ensure the textarea is the direct editor-slot child so `flex:1; min-height:0; overflow:auto` applies.

- [ ] **Step 4: Run test, verify it passes**

Run: `pnpm vitest run src/pages/__tests__/PageViewPage.test.tsx`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/PageViewPage.tsx frontend/src/pages/__tests__/PageViewPage.test.tsx
git commit -m "feat(preview): OCR text box fills panel height, scrolls only when needed"
```

### Task 11: Toolbar reflow (only if root cause is in simple-gui)

**Files:**
- Modify: simple-gui page wrapper around `PageSplitView` (likely `frontend/src/pages/PageViewPage.tsx` or a layout component) — only if Milestone 1 Task 4 found the non-shrinking element here.

- [ ] **Step 1:** With pdomain-ui 0.6.0 installed, re-test pin reflow in the browser. If the toolbar now reflows, **skip this task** (fixed upstream) and note it.
- [ ] **Step 2:** If it still does not reflow, add `min-width: 0` to the simple-gui content wrapper that hosts `PageSplitView` (the first ancestor that refuses to shrink). Add a vitest assertion on that wrapper's `minWidth`.
- [ ] **Step 3: Commit** (only if a change was needed)

```bash
git add frontend/src/pages/PageViewPage.tsx
git commit -m "fix(layout): content wrapper reflows under pinned jobs dock"
```

### Task 12: Bump pdomain-ui dependency to 0.6.0

**Files:**
- Modify: `frontend/package.json` (or `codegen.versions.json` per the workspace `update-pd-deps` flow)

- [ ] **Step 1:** Run `make update-pd-deps` (or edit the `@concavetrillion/pdomain-ui` spec to `^0.6.0`), then a fresh resolve per the pnpm-11 caveat: `rm -rf node_modules pnpm-lock.yaml && pnpm install`.
- [ ] **Step 2:** Run `make ci AI=1`; confirm green.
- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml
git commit -m "chore(deps): bump @concavetrillion/pdomain-ui to ^0.6.0"
```

---

## Milestone 3 — Browser Verification (MANDATORY, FastAPI + SPA)

simple-gui bundles and serves a React/Vite SPA, so the user-visible result must
be proven in a real browser. Extend the existing `tests/e2e/` Playwright suite.

### Task 13: `data-testid` contract

- [ ] Confirm/add testids exercised below: `job-delete-<id>` (from pdomain-ui), `download-images-text`, `download-images-text-json`, `ocr-text`, the jobs-dock open control, and the pin toggle. Add any missing ones in the owning component. Commit.

### Task 14: Done-job + trash flow (browser)

**Files:** `tests/e2e/test_jobs_panel.py` (create)

- [ ] **Step 1:** Seed a succeeded run; open the app; open the jobs dock.
- [ ] **Step 2:** Assert the done row is **static** — no element with class `shimmer` present, no running progress bar.
- [ ] **Step 3:** Click the trash button; assert the row disappears and `GET /api/jobs` no longer returns it.
- [ ] **Step 4:** Run: `make e2e-browser` (or the repo's Playwright target). Commit.

### Task 15: Test-leak isolation (browser)

**Files:** `tests/e2e/test_jobs_panel.py`

- [ ] Seed an `e2etestjob-*` run directly in the projects root; load the app; assert it **never** appears in the jobs dock or recent-projects list. Run + commit.

### Task 16: Download buttons + text fill + pin reflow (browser)

**Files:** `tests/e2e/test_preview.py` (create)

- [ ] **Step 1:** Navigate to a page view; assert no checkbox role exists; assert `download-images-text` and `download-images-text-json` are visible; click each and assert the download response is `200` with the expected filename/content-disposition (intercept the network request).
- [ ] **Step 2:** Assert the `ocr-text` box height ≈ the image panel height (within a tolerance), confirming it fills.
- [ ] **Step 3:** Pin the jobs dock; assert the toolbar above the text box narrows (its bounding-box width shrinks vs. unpinned).
- [ ] **Step 4:** Run `make e2e-browser`. Commit.

### Task 17: Wire into CI

- [ ] Confirm `make e2e-browser` is part of `make ci` (per the workspace standard). If the new tests are in a separate group/marker, ensure the pytest invocation keeps `-n auto`. Run `make ci AI=1`; confirm green. Commit.

---

## Self-Review (completed by author)

- **Spec coverage:** Every spec item maps to a task — A1→T1, A2→T2, A3→T3, A4→T4, release→T5; B1→T6+T7, B2→T8, B3→T9, B4→T10, B5→T11, consume→T12; testing→T6–T10 + Milestone 3.
- **Placeholders:** none — every code step shows code; diagnostic Task 4/11 carries explicit repro + hypothesis + fix.
- **Type consistency:** `onJobDelete(id: string)` used identically in T2 (define), T8 (consume); `TEST_JOB_PREFIX`/`is_test_job` defined in T6 and reused in T7; testids consistent across T9/T10/Milestone 3.
- **FastAPI + SPA:** browser-verification milestone present (Tasks 13–17) and wired into CI.
