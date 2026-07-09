# Cross-unit flows — <app name>

> Template. Copy to `docs/specs/behavior/flows.md` in the target repo and
> fill in. See `docs/process/behavior-e2e-capture.md` for the full
> process. A *unit* can be a whole surface or a behavior-bearing
> component inside a surface.

## Agent Index

- **Kind:** template
- **Use with:** `docs/process/behavior-e2e-capture.md`
- **Copy to:** `docs/specs/behavior/flows.md`
- **Purpose:** chain unit behavior records into cross-unit flows.
- **Inputs:** locked `B-<UNIT>-NNN` behavior record IDs.
- **Feeds:** E2E tests and coverage reports.
- **Search terms:** behavior flows, cross-unit flow, E2E flow,
  regression flow, behavior ID chain

Flows are named multi-step scenarios that cross units. Each flow chains
already-locked per-unit behavior records (by ID) into one end-to-end
path. A flow can include screen-level records and component-level records
when both matter. Flows are where the most valuable regression coverage
lives.

### F-<FLOW>-01 — <flow name>

- **Units:** <home → upload-dropzone → results → page-view (web), or a
  chain of commands>
- **Steps (record IDs in order):**
  1. <B-HOME-003> — <one-line>
  2. <B-RESULTS-002> — <one-line>
  3. <B-PAGEVIEW-012> — <one-line>
- **Expected end state (UI + backend):** <what is true once the flow
  completes — on screen and on disk>
- **Bad-state / error:** <a failure injected mid-flow and the expected
  recovery>
- **Tier(s):** <A | A+B>
- **Regression:** <no | yes (#issue or commit)>
- **Test:** <path::name | — if not yet written>

<!-- Worked example — delete when filling in:

### F-UPLOAD-OCR-DOWNLOAD-01 — Upload ZIP, OCR, review, download

- **Units:** home → upload-dropzone → results → page-view → results
- **Steps (record IDs in order):**
  1. B-HOME-002 — drag-drop a ZIP, set engine=tesseract, start job
  2. B-RESULTS-001 — job progresses to done; per-page table populates
  3. B-PAGEVIEW-012 — open a page, edit text, save
  4. B-RESULTS-004 — download output ZIP
- **Expected end state (UI + backend):** downloaded ZIP contains the
  edited combined `.txt` and the updated sidecar
- **Bad-state / error:** one page fails OCR → marked failed, retry
  succeeds, others unaffected
- **Tier(s):** A+B
- **Regression:** no
- **Test:** tests/e2e/test_real_ocr_pipeline.py::test_upload_ocr_download
-->
