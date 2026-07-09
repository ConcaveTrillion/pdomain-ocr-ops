---
status: complete
synced: 2026-05-18
milestone: 13
repo: ConcaveTrillion/ocr-container-meta
---

# pdomain-ocr-simple-gui — Browser Verification Milestone

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Properly exercise `pdomain-ocr-simple-gui` end-to-end in a real browser via Playwright, including a happy-path OCR job flow, so that the app is genuinely verified working — not just CI-green.

**Architecture:** Add Playwright (`pytest-playwright`) as a `uv` `e2e` dependency group. Write browser-based tests that start the server via subprocess, open Chromium, and exercise the full happy path: app loads → DropZone visible → job submitted → ResultsPage shows → PageView shows. Complement with a strengthened httpx e2e that rejects `state="error"`.

**Tech Stack:** pytest-playwright 0.5+, Playwright 1.59, Chromium, pytest, uv dependency groups.

**Why this milestone didn't exist in the original plan:** The original M8 "CI gate green" included only an `httpx` smoke test that accepted `state="error"` as success. No browser verification milestone was written. This gap has now been captured as a process rule in `ship-slice.md` and `CLAUDE.md`: every FastAPI+SPA plan must end with a browser verification milestone.

---

## File map

| File | Action | Purpose |
|------|--------|---------|
| `frontend/src/components/JobConfigDialog.tsx` | Modify | Add `data-testid` to form, engine select, submit button |
| `frontend/src/pages/ResultsPage.tsx` | Modify | Add `data-testid="page-row"` to each `<tr>` |
| `pyproject.toml` | Modify | Add `pytest-playwright` to `[dependency-groups] e2e` |
| `Makefile` | Modify | Add `e2e-browser` target; add it to `ci` target |
| `tests/e2e/__init__.py` | Create | empty |
| `tests/e2e/conftest.py` | Create | Server fixture (subprocess + health poll) |
| `tests/e2e/test_browser_smoke.py` | Create | App loads test |
| `tests/e2e/test_browser_job_flow.py` | Create | Full happy-path: submit → results → page view |
| `tests/smoke/test_e2e.py` | Modify | Reject `state="error"` with xfail guard |

---

## Task 1 — Add data-testid to JobConfigDialog  {#testid-dialog}

model: haiku  effort: S  area: frontend

**Context:** `JobConfigDialog` renders the engine dropdown, language input, and submit button but has no `data-testid` attributes, making it unselectable in Playwright without fragile text/CSS selectors.

**Approach:** Add `data-testid` to the form element, engine `<select>`, language `<input>`, and the "Run OCR →" submit button.

**Files:**
- Modify: `frontend/src/components/JobConfigDialog.tsx`

**Verification:** `cd frontend && pnpm run test` passes.

**Acceptance:**
- [ ] `data-testid="job-config-dialog-form"` on the `<form>` element
- [ ] `data-testid="engine-select"` on the engine `<select>`
- [ ] `data-testid="language-input"` on the language `<input>`
- [ ] `data-testid="run-ocr-button"` on the submit `<Button type="submit">`
- [ ] `make frontend-test` (vitest) passes

- [ ] **Step 1: Locate the elements in JobConfigDialog.tsx**

  In `frontend/src/components/JobConfigDialog.tsx`, find:
  - The `<form>` opening tag (around line 100)
  - The engine `<select>` element (around line 140)
  - The language `<input>` element (around line 165)
  - The submit `<Button type="submit">` (around line 227)

- [ ] **Step 2: Add testids to the form**

  Edit the `<form>` opening tag to add `data-testid="job-config-dialog-form"`:
  ```tsx
  <form
    data-testid="job-config-dialog-form"
    onSubmit={handleSubmit}
    ...
  >
  ```

- [ ] **Step 3: Add testids to the engine select and language input**

  On the engine `<select>`:
  ```tsx
  <select
    id="jcd-engine"
    data-testid="engine-select"
    value={engine}
    ...
  >
  ```

  On the language `<input>`:
  ```tsx
  <input
    id="jcd-language"
    data-testid="language-input"
    type="text"
    value={language}
    ...
  />
  ```

- [ ] **Step 4: Add testid to submit button**

  ```tsx
  <Button type="submit" variant="primary" disabled={submitting} data-testid="run-ocr-button">
    {submitting ? "Running…" : "Run OCR →"}
  </Button>
  ```

- [ ] **Step 5: Run vitest to verify no regressions**

  ```bash
  cd /workspaces/ocr-container/pdomain-ocr-simple-gui/frontend && pnpm run test --run
  ```
  Expected: all tests pass.

- [ ] **Step 6: Commit**

  ```bash
  git add frontend/src/components/JobConfigDialog.tsx
  git commit -m "feat(frontend): add data-testid to JobConfigDialog for Playwright selectors"
  ```

---

## Task 2 — Add data-testid to ResultsPage rows  {#testid-results-rows}

model: haiku  effort: S  area: frontend

**Context:** ResultsPage renders per-page rows as `<tr>` elements with `role="row"` but no `data-testid`. Playwright needs a stable selector to click through to the PageView.

**Approach:** Add `data-testid={`page-row-${page.page_idx}`}` to each row `<tr>`.

**Files:**
- Modify: `frontend/src/pages/ResultsPage.tsx`

**Verification:** `cd frontend && pnpm run test` passes.

**Acceptance:**
- [ ] Each `<tr>` in the results table has `data-testid={`page-row-${page.page_idx}`}`
- [ ] `make frontend-test` passes

- [ ] **Step 1: Find the row `<tr>` in ResultsPage.tsx**

  Around line 188 in `frontend/src/pages/ResultsPage.tsx`:
  ```tsx
  <tr
    key={page.page_idx}
    className="results-page__row"
  ```

- [ ] **Step 2: Add the data-testid**

  ```tsx
  <tr
    key={page.page_idx}
    data-testid={`page-row-${page.page_idx}`}
    className="results-page__row"
    style={{ cursor: "pointer" }}
    tabIndex={0}
    role="row"
    onClick={() => navigate(`/jobs/${id ?? ""}/pages/${page.page_idx}`)}
    ...
  >
  ```

- [ ] **Step 3: Run vitest**

  ```bash
  cd /workspaces/ocr-container/pdomain-ocr-simple-gui/frontend && pnpm run test --run
  ```
  Expected: all tests pass.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/pages/ResultsPage.tsx
  git commit -m "feat(frontend): add data-testid to ResultsPage rows for Playwright"
  ```

---

## Task 3 — Playwright dependency + infra  {#playwright-infra}

model: sonnet  effort: S  area: backend

**Context:** `pdomain-ocr-simple-gui` has no Playwright dependency. `pdomain-prep-for-pgdp` uses `pytest-playwright>=0.5` in a `[dependency-groups] e2e` uv group — mirror that pattern exactly.

**Approach:** Add `pytest-playwright` to the `e2e` dependency group, add a `make e2e-browser` target that installs Chromium and runs `tests/e2e/`, and create a `conftest.py` with a `live_server` fixture that starts the app on a free port and health-polls until ready.

**Files:**
- Modify: `pyproject.toml`
- Modify: `Makefile`
- Create: `tests/e2e/__init__.py`
- Create: `tests/e2e/conftest.py`

**Verification:** `make e2e-browser` runs without import errors (even with no tests yet).

**Acceptance:**
- [ ] `uv sync --group e2e` installs `playwright` + `pytest-playwright`
- [ ] `uv run --group e2e playwright install chromium` succeeds
- [ ] `tests/e2e/conftest.py` provides a `live_server` fixture that starts the app and returns its base URL
- [ ] `make e2e-browser` target exists

- [ ] **Step 1: Add pytest-playwright to pyproject.toml**

  In `pyproject.toml`, find the `[dependency-groups]` section and add:
  ```toml
  [dependency-groups]
  e2e = [
      "pytest-playwright>=0.5",
  ]
  ```
  If an `e2e` group already exists (check `[dependency-groups]`), add `pytest-playwright` to it.

- [ ] **Step 2: Install and sync**

  ```bash
  cd /workspaces/ocr-container/pdomain-ocr-simple-gui
  uv sync --group e2e
  uv run --group e2e playwright install chromium
  ```
  Expected: exits 0.

- [ ] **Step 3: Create tests/e2e/__init__.py**

  Create an empty `tests/e2e/__init__.py`.

- [ ] **Step 4: Create tests/e2e/conftest.py**

  ```python
  """Shared fixtures for Playwright e2e tests."""

  from __future__ import annotations

  import socket
  import subprocess
  import sys
  import time
  from collections.abc import Generator

  import httpx
  import pytest


  def _free_port() -> int:
      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
          s.bind(("127.0.0.1", 0))
          return s.getsockname()[1]  # type: ignore[return-value]


  def _wait_ready(base_url: str, timeout: float = 30.0) -> None:
      deadline = time.monotonic() + timeout
      while time.monotonic() < deadline:
          try:
              resp = httpx.get(f"{base_url}/api/health", timeout=2.0)
              if resp.status_code == 200:
                  return
          except httpx.TransportError:
              pass
          time.sleep(0.25)
      raise TimeoutError(f"Server at {base_url} not ready within {timeout}s")


  @pytest.fixture(scope="session")
  def live_server() -> Generator[str, None, None]:
      """Start the app on a free port; yield its base URL; terminate after session."""
      port = _free_port()
      base_url = f"http://127.0.0.1:{port}"
      proc = subprocess.Popen(
          [
              sys.executable, "-m", "uvicorn",
              "pd_ocr_simple_gui.app:app",
              "--host", "127.0.0.1",
              "--port", str(port),
          ],
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
      )
      try:
          _wait_ready(base_url)
          yield base_url
      finally:
          proc.terminate()
          try:
              proc.wait(timeout=10)
          except subprocess.TimeoutExpired:
              proc.kill()
  ```

- [ ] **Step 5: Add make e2e-browser target**

  In `Makefile`, after the `smoke` target, add:
  ```makefile
  e2e-browser: ## Run Playwright browser e2e tests (requires chromium)
  	uv run --group e2e playwright install chromium --with-deps
  	uv run --group e2e pytest tests/e2e/ -v -m "slow or e2e"
  ```

  Also add `e2e-browser` to `.PHONY` and to the list of non-default targets.

- [ ] **Step 6: Verify the infra runs**

  ```bash
  cd /workspaces/ocr-container/pdomain-ocr-simple-gui
  uv run --group e2e pytest tests/e2e/ -v --collect-only
  ```
  Expected: `collected 0 items` (no tests yet) — no import errors.

- [ ] **Step 7: Commit**

  ```bash
  git add pyproject.toml Makefile tests/e2e/__init__.py tests/e2e/conftest.py
  git commit -m "feat(e2e): add Playwright dependency + live_server fixture + make e2e-browser"
  ```

---

## Task 4 — Playwright test: app loads  {#playwright-app-loads}

model: sonnet  effort: S  area: backend

**Context:** Verify the most basic contract: `GET /` returns the React app in a real browser, not a JSON 404. Tests that the SPA serving fix (commit 9877055) actually works under Chromium.

**Approach:** A single `@pytest.mark.slow` `@pytest.mark.e2e` test that opens the `live_server` URL in Playwright, asserts the `[data-testid="home-page"]` locator is visible, and checks for no uncaught JS errors in the console.

**Files:**
- Create: `tests/e2e/test_browser_smoke.py`

**Blocked-by:** #playwright-infra

**Verification:** `make e2e-browser` passes.

**Acceptance:**
- [ ] `[data-testid="home-page"]` visible within 10 s
- [ ] `[data-testid="drop-zone"]` visible
- [ ] `[data-testid="recent-projects-list"]` visible
- [ ] No `console.error` about failed resource loads

- [ ] **Step 1: Create tests/e2e/test_browser_smoke.py**

  ```python
  """Playwright smoke test — verifies the app loads in a real browser."""

  from __future__ import annotations

  import pytest
  from playwright.sync_api import Page, ConsoleMessage


  @pytest.mark.slow
  @pytest.mark.e2e
  def test_app_loads_in_browser(page: Page, live_server: str) -> None:
      """GET / returns the React SPA; key home-page elements are visible."""
      errors: list[str] = []

      def _capture(msg: ConsoleMessage) -> None:
          if msg.type == "error":
              errors.append(msg.text)

      page.on("console", _capture)

      page.goto(live_server, wait_until="networkidle")

      # Home page container
      page.locator('[data-testid="home-page"]').wait_for(state="visible", timeout=10_000)

      # DropZone
      page.locator('[data-testid="drop-zone"]').wait_for(state="visible", timeout=5_000)

      # Recent projects list
      page.locator('[data-testid="recent-projects-list"]').wait_for(state="visible", timeout=5_000)

      # No JS resource errors (404s on assets indicate broken SPA serving)
      resource_errors = [e for e in errors if "404" in e or "Failed to load" in e]
      assert not resource_errors, f"JS console errors: {resource_errors}"
  ```

- [ ] **Step 2: Run the test**

  ```bash
  cd /workspaces/ocr-container/pdomain-ocr-simple-gui
  uv run --group e2e pytest tests/e2e/test_browser_smoke.py -v -m "slow or e2e"
  ```
  Expected: `PASSED` — the app renders in Chromium.

- [ ] **Step 3: Commit**

  ```bash
  git add tests/e2e/test_browser_smoke.py
  git commit -m "test(e2e): Playwright smoke — app loads, home-page visible in browser"
  ```

---

## Task 5 — Playwright test: job submission → results page  {#playwright-job-flow}

model: sonnet  effort: M  area: backend

**Context:** The primary user flow: submit a job (via API — file drag is impractical in Playwright), navigate to the results page in the browser, wait for page rows to appear. This exercises React Router, live polling, and the ResultsPage component.

**Approach:** POST a job to `/api/jobs` via `httpx`, then navigate the Playwright browser to `/jobs/{project_id}`, wait for `[data-testid="results-page"]` and at least one `[data-testid^="page-row-"]`. Use the existing OCR fixture image `pdomain-book-tools/tests/ocr-test-image.png`.

**Files:**
- Create: `tests/e2e/test_browser_job_flow.py`

**Blocked-by:** #playwright-app-loads, #testid-results-rows

**Verification:** `make e2e-browser` passes.

**Acceptance:**
- [ ] POST to `/api/jobs` returns 200 with `project_id`
- [ ] Browser navigates to `/jobs/{project_id}` and `[data-testid="results-page"]` is visible
- [ ] At least one `[data-testid^="page-row-"]` appears within 60 s

- [ ] **Step 1: Create tests/e2e/test_browser_job_flow.py**

  ```python
  """Playwright test — submit job via API, verify ResultsPage renders in browser."""

  from __future__ import annotations

  import shutil
  import time
  from pathlib import Path

  import httpx
  import pytest
  from playwright.sync_api import Page

  _FIXTURE_IMAGE = Path("/workspaces/ocr-container/pdomain-book-tools/tests/ocr-test-image.png")
  _POLL_TIMEOUT = 60.0


  @pytest.mark.slow
  @pytest.mark.e2e
  def test_job_submission_shows_results_page(page: Page, live_server: str, tmp_path: Path) -> None:
      """Submit a job via API; browser navigates to results page and shows page rows."""
      if not _FIXTURE_IMAGE.exists():
          pytest.skip(f"Fixture image not found: {_FIXTURE_IMAGE}")

      source_dir = tmp_path / "source"
      source_dir.mkdir()
      shutil.copy(_FIXTURE_IMAGE, source_dir / _FIXTURE_IMAGE.name)
      output_dir = tmp_path / "output"
      output_dir.mkdir()

      # Submit job via API (file drag is impractical in Playwright)
      resp = httpx.post(
          f"{live_server}/api/jobs",
          json={
              "name": "playwright-happy-path",
              "source_path": str(source_dir),
              "output_dir": str(output_dir),
              "engine": "doctr",
              "language": "en",
              "save_json": False,
              "combined_txt": True,
          },
          timeout=10.0,
      )
      assert resp.status_code == 200, f"POST /api/jobs failed: {resp.text}"
      project_id = resp.json()["project_id"]

      # Navigate browser to the results page
      page.goto(f"{live_server}/jobs/{project_id}", wait_until="networkidle")

      # Results page container must appear
      page.locator('[data-testid="results-page"]').wait_for(state="visible", timeout=10_000)

      # Wait for at least one page row (job may still be running)
      deadline = time.monotonic() + _POLL_TIMEOUT
      while time.monotonic() < deadline:
          rows = page.locator('[data-testid^="page-row-"]').all()
          if rows:
              break
          page.reload(wait_until="networkidle")
          time.sleep(2.0)
      else:
          pytest.fail(f"No page rows appeared in ResultsPage within {_POLL_TIMEOUT}s")

      assert len(rows) >= 1, "Expected at least one page row in ResultsPage"
  ```

- [ ] **Step 2: Run the test**

  ```bash
  cd /workspaces/ocr-container/pdomain-ocr-simple-gui
  uv run --group e2e pytest tests/e2e/test_browser_job_flow.py -v -m "slow or e2e" -s
  ```
  Expected: `PASSED`. The test may take up to 60 s for the first DocTR model load.

- [ ] **Step 3: Commit**

  ```bash
  git add tests/e2e/test_browser_job_flow.py
  git commit -m "test(e2e): Playwright happy-path — submit job, results-page renders with page rows"
  ```

---

## Task 6 — Playwright test: PageView opens from results row  {#playwright-page-view}

model: haiku  effort: S  area: backend

**Context:** Clicking a row in ResultsPage should navigate to `/jobs/{id}/pages/{page_idx}` and render `PageViewPage` with a text area. This exercises React Router navigation and the PageViewPage component.

**Approach:** Continuing from Task 5's job submission, click `[data-testid="page-row-0"]` and assert `[data-testid="page-view-page"]` becomes visible.

**Files:**
- Modify: `tests/e2e/test_browser_job_flow.py`

**Blocked-by:** #playwright-job-flow

**Verification:** `make e2e-browser` passes.

**Acceptance:**
- [ ] Clicking `[data-testid="page-row-0"]` navigates to page view
- [ ] `[data-testid="page-view-page"]` visible within 5 s

- [ ] **Step 1: Add the page-view test to test_browser_job_flow.py**

  Append this test to `tests/e2e/test_browser_job_flow.py`:

  ```python
  @pytest.mark.slow
  @pytest.mark.e2e
  def test_page_row_click_opens_page_view(page: Page, live_server: str, tmp_path: Path) -> None:
      """Clicking a page row opens PageViewPage."""
      if not _FIXTURE_IMAGE.exists():
          pytest.skip(f"Fixture image not found: {_FIXTURE_IMAGE}")

      source_dir = tmp_path / "pv-source"
      source_dir.mkdir()
      shutil.copy(_FIXTURE_IMAGE, source_dir / _FIXTURE_IMAGE.name)
      output_dir = tmp_path / "pv-output"
      output_dir.mkdir()

      resp = httpx.post(
          f"{live_server}/api/jobs",
          json={
              "name": "playwright-page-view",
              "source_path": str(source_dir),
              "output_dir": str(output_dir),
              "engine": "doctr",
              "language": "en",
              "save_json": False,
              "combined_txt": True,
          },
          timeout=10.0,
      )
      assert resp.status_code == 200, f"POST /api/jobs failed: {resp.text}"
      project_id = resp.json()["project_id"]

      page.goto(f"{live_server}/jobs/{project_id}", wait_until="networkidle")
      page.locator('[data-testid="results-page"]').wait_for(state="visible", timeout=10_000)

      # Wait for the first row
      deadline = time.monotonic() + 60.0
      while time.monotonic() < deadline:
          rows = page.locator('[data-testid^="page-row-"]').all()
          if rows:
              break
          page.reload(wait_until="networkidle")
          time.sleep(2.0)
      else:
          pytest.fail("No page rows appeared before timeout")

      # Click the first row
      page.locator('[data-testid="page-row-0"]').click()

      # PageViewPage must appear
      page.locator('[data-testid="page-view-page"]').wait_for(state="visible", timeout=5_000)
  ```

- [ ] **Step 2: Run both tests**

  ```bash
  cd /workspaces/ocr-container/pdomain-ocr-simple-gui
  uv run --group e2e pytest tests/e2e/test_browser_job_flow.py -v -m "slow or e2e" -s
  ```
  Expected: both tests pass.

- [ ] **Step 3: Commit**

  ```bash
  git add tests/e2e/test_browser_job_flow.py
  git commit -m "test(e2e): Playwright — click page row opens PageViewPage"
  ```

---

## Task 7 — Strengthen httpx e2e — reject error state  {#strengthen-e2e}

model: haiku  effort: S  area: backend

**Context:** `tests/smoke/test_e2e.py` currently accepts `state="error"` as a valid terminal state ("real OCR may fail on environments without model weights"). This is too lenient — it means the test passes even if OCR is entirely broken. Use `xfail` to mark expected failures on environments without model weights rather than silently swallowing errors.

**Approach:** Assert `state == "done"`. If the state is `"error"`, `pytest.xfail` with a message explaining the environment issue. This preserves the test's value in environments with OCR while not failing CI on machines without model weights.

**Files:**
- Modify: `tests/smoke/test_e2e.py`

**Verification:** `make smoke` passes. On machines with model weights: `state=done`. On machines without: `xfail`.

**Acceptance:**
- [ ] `state="error"` triggers `pytest.xfail(...)` not silent pass
- [ ] `state="done"` asserts `.txt` files exist
- [ ] `make smoke` green

- [ ] **Step 1: Edit tests/smoke/test_e2e.py**

  Find the block that checks `final_status.get("state")`:
  ```python
  # Current (too lenient):
  assert final_status.get("state") in ("done", "error"), ...
  if final_status.get("state") == "done":
      txt_files = ...
      assert txt_files, ...
  ```

  Replace with:
  ```python
  state = final_status.get("state")
  if state == "error":
      pytest.xfail(
          "Job reached state=error — likely missing OCR model weights in this environment. "
          "Run with a full model cache to verify OCR output."
      )

  assert state == "done", f"Expected state=done, got {state!r}. Full status: {final_status}"

  txt_files = list(output_dir.rglob("*.txt")) or list(
      (
          Path.home() / ".local" / "share" / "pd-suite" / "simple-gui" / "projects" / project_id
      ).rglob("*.txt")
  )
  assert txt_files, "Job state=done but no .txt files found in output_dir or project storage"
  ```

- [ ] **Step 2: Run the smoke test**

  ```bash
  cd /workspaces/ocr-container/pdomain-ocr-simple-gui
  uv run pytest tests/smoke/ -v -m "slow or e2e" -s
  ```
  Expected: `PASSED` or `XFAIL` (never a silent pass for a broken OCR run).

- [ ] **Step 3: Commit**

  ```bash
  git add tests/smoke/test_e2e.py
  git commit -m "test(smoke): reject state=error with xfail rather than silent pass"
  ```

---

## Task 8 — Wire e2e-browser into CI  {#ci-integration}

model: haiku  effort: S  area: backend

**Context:** `make ci` currently runs `make smoke` but not `make e2e-browser`. Browser tests are slow and need Chromium installed, but they must run in CI so the verification milestone is enforced going forward.

**Approach:** Add `e2e-browser` to the `ci` target after `smoke`. Add `playwright install chromium` to `setup` so a fresh environment always has the browser.

**Files:**
- Modify: `Makefile`

**Verification:** `make ci AI=1` exits 0 with Playwright tests listed as passed.

**Acceptance:**
- [ ] `make ci` runs `e2e-browser`
- [ ] `make setup` installs Chromium
- [ ] `make ci AI=1` green end-to-end

- [ ] **Step 1: Add Chromium install to make setup**

  In `Makefile`, find the `setup` target. After `uv sync`, add:
  ```makefile
  	uv run --group e2e playwright install chromium --with-deps
  ```

- [ ] **Step 2: Add e2e-browser to ci target**

  Find the `ci` target (currently ends with `frontend-knip` or similar). Append `e2e-browser`:
  ```makefile
  ci: setup lint typecheck test smoke e2e-browser frontend-build ## Full CI pipeline
  ```

- [ ] **Step 3: Run full CI**

  ```bash
  cd /workspaces/ocr-container/pdomain-ocr-simple-gui
  make ci AI=1
  ```
  Expected: `✅` on stdout.

- [ ] **Step 4: Commit**

  ```bash
  git add Makefile
  git commit -m "chore(ci): wire e2e-browser into make ci + install Chromium in setup

  CLOSES #<verification-milestone-issue>"
  ```
