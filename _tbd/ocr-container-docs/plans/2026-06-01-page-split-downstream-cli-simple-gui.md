---
repo: ocr-container-meta
spec: docs/specs/2026-05-31-page-record-ops-design.md
rollout: docs/specs/2026-06-01-page-split-downstream-rollout.md
sequence: Plan 5 of 5 (page-split rollout) — end-state producers
status: ready (execution gated on the release gate below)
---

# Page-split downstream — cli + simple-gui (end-state producers) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the two end-state producers — `pdomain-ocr-cli` and
`pdomain-ocr-simple-gui` — compatible with book-tools 0.17 (`Page` operational-field
split) and pdomain-ops 0.7.0, as part of the coordinated page-split release.

**Architecture:** These two repos are **end-state producers** (design spec §10): they
run a pipeline once and emit output; no event store, no blob store, no `PageAggregate`.
Exploration confirmed neither reads any removed `Page` field and neither owns a competing
domain model — so this plan is **purely compatibility**: floor bumps, one tuple-return
adoption (cli), and test-double cleanup (both). The additive `ProvenanceGraph` /
`PagePayload` emission described in design spec §10/§12 is **explicitly deferred** (no
consumer yet) — see "Deferred" at the end.

**Tech Stack:** Python 3.11+, book-tools 0.17, pdomain-ops 0.7.0, uv, pytest-xdist.

---

## Release gate (CLEARED 2026-06-01)

The release gate is **cleared**: `pdomain-book-tools` 0.17.1, `pdomain-ops` 0.6.0, and
`pdomain-ops` 0.7.0 are all published to `pdomain-index-pip`. Bump straight to the index
sources (`uv lock && uv sync` resolves from the index — no temporary `[tool.uv.sources]`
editable needed). This plan is executable now.

Each repo is independently shippable; Part A (cli) and Part B (simple-gui) have no
ordering dependency on each other.

---

## Part A — pdomain-ocr-cli

Files of interest (from exploration; **read them before editing**):
- `pyproject.toml` (deps)
- `pdomain_ocr_cli/ocr_to_txt.py:450-485` — `_run_doctr_batch_single_image_compat`
  (the only direct `Document.from_image_ocr_via_doctr` call site)
- `tests/_fakes.py:32-102` — `FakePage` test double
- `tests/conftest.py:80-192` — `mock_heavy_deps`

### Task A1: Bump dependency floors

**Files:** Modify `pyproject.toml`

- [ ] **Step 1: Bump the floors**

In `[project] dependencies`:
- `"pdomain-book-tools>=0.15.1",` → `"pdomain-book-tools>=0.17.0",`
- `"pdomain-ops>=0.4.0",` → `"pdomain-ops>=0.7.0",`

- [ ] **Step 2: Resolve**

Run: `cd /workspaces/ocr-container/pdomain-ocr-cli && uv lock && uv sync`
Expected: resolves. If 0.17.x / 0.6.0 are not yet in the index (pre-release-gate),
this fails — apply the temporary absolute-path `[tool.uv.sources]` editable for
`pdomain-book-tools` and `pdomain-ops` (mirror Plan 2's M0), with a REVERT-before-release
comment. Do **not** commit a worktree-relative path.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build(deps): bump book-tools to 0.17.0 and pdomain-ops to 0.7.0 floors"
```

### Task A2: Adopt the `from_image_ocr_via_doctr -> (Document, int)` tuple return

In book-tools 0.17, `Document.from_image_ocr_via_doctr` returns `tuple[Document, int]`
(document, chosen rotation degrees) instead of `Document`. The cli's single-image compat
shim must unpack it.

**Files:** Modify `pdomain_ocr_cli/ocr_to_txt.py` (the
`_run_doctr_batch_single_image_compat` function, ~lines 450-485); Test:
`tests/` (add/extend a test that exercises the single-image fallback path)

- [ ] **Step 1: Read the shim.** Read `_run_doctr_batch_single_image_compat` in full.
  Identify the `Document.from_image_ocr_via_doctr(...)` call and how its result is used
  (currently `doc = ...; page = doc.pages[0]`).

- [ ] **Step 2: Write a failing test.** Add a test (e.g. `tests/test_main_single_image_compat.py`)
  that patches `pdomain_book_tools.ocr.document.Document.from_image_ocr_via_doctr` to
  return a 2-tuple `(fake_doc, 90)` and drives the single-image fallback, asserting the
  page is extracted correctly (and, if the shim surfaces rotation, that 90 is threaded /
  ignored cleanly). Mirror the mock style already in `tests/conftest.py`. Run it — it
  should FAIL on the current code with a "too many values"/attribute error.

> If the single-image compat shim exists **only** to support book-tools < 0.17 and is
> now dead under a `>=0.17.0` floor, the correct change may be to delete the shim and
> route single images through the batch path. Decide based on what you read in Step 1;
> if you delete it, the test instead asserts the single-image path still produces output
> via the batch path. State which you did in the commit message.

- [ ] **Step 3: Implement.** Unpack the tuple: `doc, _rotation = Document.from_image_ocr_via_doctr(...)`
  (or remove the shim per the note). Keep behavior otherwise identical.

- [ ] **Step 4: Green.** Run the new test + `uv run pytest -q`.

- [ ] **Step 5: Commit**

```bash
git add pdomain_ocr_cli/ocr_to_txt.py tests/
git commit -m "fix(cli): adopt book-tools 0.17 from_image_ocr_via_doctr tuple return"
```

### Task A3: Update the `FakePage` test double for the 0.17 Page surface

`fail_under = 100` — the test doubles must stay faithful to the real `Page`. 0.17 adds
`page_id` (UUID), `image_blob_hash`/`thumbnail_blob_hash` (str|None), `gt_orphans`
(GtOrphans|None) and removes the operational fields. The cli's `FakePage` only needs the
attributes the cli actually reads (`text`, `words`, `reorganize_page`, diagnostics) — so
this task is **only needed if** a test asserts on `to_dict()` output shape or constructs
a real `Page`.

**Files:** Modify `tests/_fakes.py` (`FakePage`, ~lines 32-102); Test: existing suite

- [ ] **Step 1: Check necessity.** Grep the tests for any assertion on `page_id`,
  `to_dict()`, `image_blob_hash`, or `gt_orphans`, and for any place a real
  `pdomain_book_tools` `Page` is constructed/serialized in cli tests. If none, **skip
  this task** (the cli never touches those fields) — note that in the Part A summary.

- [ ] **Step 2 (only if needed): add the fields.** Give `FakePage` a `page_id`
  (a fixed `uuid4()`), `image_blob_hash = None`, `thumbnail_blob_hash = None`,
  `gt_orphans = None`, and ensure any `to_dict()` the fake exposes does not emit removed
  fields. Run the suite green.

- [ ] **Step 3: Commit (only if changed)**

```bash
git add tests/_fakes.py
git commit -m "test(cli): align FakePage double with 0.17 Page surface"
```

### Task A4: Full CI

- [ ] **Step 1:** `cd /workspaces/ocr-container/pdomain-ocr-cli && make ci AI=1` → green
  (the repo enforces 100% coverage on the fast suite; fix any gap the changes introduce).
- [ ] **Step 2:** Add a CHANGELOG entry if the repo keeps one (book-tools 0.17 / ops 0.6
  adoption). Commit.

---

## Part B — pdomain-ocr-simple-gui

Files of interest (from exploration; **read before editing**):
- `pyproject.toml` (deps)
- `src/pdomain_ocr_simple_gui/testing/fake_dispatcher.py:172-185` — `_page_dict_for`
  (emits stale removed fields in synthetic Page dicts)
- `src/pdomain_ocr_simple_gui/pipeline.py:412-456` — `Page.from_dict` → `reorganize_page`
  → `to_dict` → `apply_text_normalizations` (the consumer path)
- `tests/conftest.py`, `tests/test_pipeline.py`, `tests/e2e/`

Git state at exploration: clean `main`, no in-flight branch.

### Task B1: Bump dependency floors

**Files:** Modify `pyproject.toml`

- [ ] **Step 1:** `"pdomain-book-tools>=0.14.1",` → `"pdomain-book-tools>=0.17.0",`;
  `"pdomain-ops>=0.4.0",` → `"pdomain-ops>=0.7.0",`.
- [ ] **Step 2:** `cd /workspaces/ocr-container/pdomain-ocr-simple-gui && uv lock && uv sync`
  (apply the temporary editable `[tool.uv.sources]` workaround if pre-gate; revert-comment).
- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build(deps): bump book-tools to 0.17.0 and pdomain-ops to 0.7.0 floors"
```

### Task B2: Remove stale removed-fields from the fake dispatcher

The fake dispatcher's synthetic Page dict emits fields that no longer exist on the 0.17
`Page` (`ocr_provenance`, `source`, `ocr_failed`, `rotation_applied`, `image_path`).
These must be removed so the test double matches what the real pdomain-ops dispatcher
emits in 0.17 (`page.to_dict()` — none of these keys).

**Files:** Modify `src/pdomain_ocr_simple_gui/testing/fake_dispatcher.py` (`_page_dict_for`,
~lines 172-185); Test: `tests/test_pipeline.py` (or wherever the fake dict is asserted)

- [ ] **Step 1: Write/extend a failing test.** Add an assertion (in the pipeline test
  that round-trips the fake dict through `Page.from_dict(...).to_dict()`) that the
  produced/consumed page dict contains **none** of: `ocr_provenance`, `source`,
  `ocr_failed`, `rotation_applied`, `image_path`. With the current fake it FAILS (the
  fake emits them).

> First verify whether book-tools 0.17 `Page.from_dict` is tolerant of unknown keys or
> strict. If strict, removing them is mandatory for the pipeline to work at all; if
> tolerant, removal keeps the fake honest. Either way, remove them.

- [ ] **Step 2: Implement.** Delete those five keys from `_page_dict_for`'s synthetic
  dict. If a `page_id` is needed for the dict to be a valid 0.17 page, add one
  (`str(uuid4())`); otherwise `Page.from_dict` will generate one.

- [ ] **Step 3: Green.** Run `uv run pytest tests/test_pipeline.py -q` and the broader
  unit suite.

- [ ] **Step 4: Commit**

```bash
git add src/pdomain_ocr_simple_gui/testing/fake_dispatcher.py tests/
git commit -m "test(simple-gui): drop removed Page fields from fake dispatcher (0.17)"
```

### Task B3: Full CI (incl. e2e-fast + frontend)

- [ ] **Step 1:** `cd /workspaces/ocr-container/pdomain-ocr-simple-gui && make ci AI=1`
  → green. `make ci` here includes `e2e-fast` (behavior Playwright with fake dispatcher),
  `frontend-test` (vitest), and the SPA serving contract test (`tests/test_routes_root.py`).
  The fake-dispatcher change exercises the e2e path — confirm the behavior-coverage gate
  (`test_behavior_coverage.py`) stays green.
- [ ] **Step 2:** CHANGELOG entry if kept. Commit.

---

## Integration (orchestrator)

For each repo: worktree → rebase origin/main → ff-only merge → push (on CT auth), per
workspace policy. No GitHub PRs. Each repo bumps its own tag if it cuts a release;
both pin `pdomain-ops>=0.7.0` + `pdomain-book-tools>=0.17.0`. The release gate is
cleared (all deps in the index), so resolve directly from the index — no temporary
`[tool.uv.sources]` editable is required.

---

## Deferred (NOT in this plan — flagged so it isn't dropped)

Design spec §10/§12 envisions end-state producers building a `ProvenanceGraph` across
OCR→Layout→Reorganize (a DAG merge) and emitting a `PagePayload` JSON (cli) / putting
provenance in the API response (simple-gui), so a labeler can later **import** a
CLI-produced `PagePayload` into its event store. This is **additive new output contract
work with no consumer today** — hold it until that import path is actually built, then
spec it separately. Anchors for when it's picked up:
- cli emit point: `pdomain_ocr_cli/ocr_to_txt.py:1120-1184` (current JSON/diagnostic
  serialization; `_SinglePageDoc` at ~268-283).
- simple-gui: `pipeline.py:219-236` `build_sidecar_payload` + `models.py:64-72`
  `PageResponse`.

---

## Self-Review

- **Spec coverage:** design spec §14 steps 5 & 6 (cli, simple-gui) — compatibility
  covered; the §10 provenance/payload emission is consciously deferred with rationale. ✔
- **No competing-model reconciliation needed** (unlike Plans 3/4) — confirmed by
  exploration: neither repo owns a `PageRecord`/`PagePayload` that clashes (simple-gui's
  `PageResponse` is a different name; cli has none). ✔
- **FastAPI+SPA (simple-gui):** has `test_routes_root.py` already (workspace contract);
  no new browser-verification milestone needed — this plan doesn't change routing/serving. ✔
- **Type consistency:** floors (`>=0.17.0`, `>=0.7.0`) identical across both repos; tuple
  unpack `doc, _rotation` matches the book-tools 0.17 signature adopted in Plan 2's M0. ✔
