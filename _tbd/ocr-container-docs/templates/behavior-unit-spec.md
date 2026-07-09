# Behavior unit spec — <Unit name>

> Template. Copy to `docs/specs/behavior/<unit>-<name>.md` —
> `screen-…` / `component-…` (web), `view-…` / `widget-…` (TUI), or
> `command-…` (CLI). See
> `docs/process/behavior-e2e-capture.md` and pick your **interface
> profile** there for what each slot means on your surface.

## Agent Index

- **Kind:** template
- **Use with:** `docs/process/behavior-e2e-capture.md`
- **Copy to:** `docs/specs/behavior/<unit>-<name>.md`
- **Purpose:** capture behavior records for one unit.
- **Upstream:** `docs/specs/ui/<unit>-<name>.md`, when present
- **Feeds:** `docs/templates/behavior-flows.md` and E2E tests
- **Search terms:** behavior unit spec, behavior record, observable
  output, backend side effects, regression record

- **Unit type:** screen | component | view | widget | command
- **Address:** <route / component path / view path / command invocation —
  e.g. `/jobs/:id`, `UploadDropzone`, or `pd-ocr run <path>`>
- **UI definition:** <`docs/specs/ui/<unit>-<name>.md`, or `none -
  existing stable UI`>
- **Parent unit(s):** <screen/view/command behavior specs that compose
  this unit, or `none`>
- **Child unit(s):** <component/widget behavior specs this unit composes,
  or `none`>
- **Shared unit:** yes | no
- **Implementation:** <source file path(s)>
- **Backend / collaborators touched:** <api paths, services, files>

## Behavior records

A record is **incomplete** until both *Observable output* and *Backend /
side-effects* are filled. Every record needs a good path and at least one
bad path. *Observable output* is whatever the user perceives on your
surface — web: DOM / toasts / route; TUI: rendered frame / widget state;
CLI: stdout / stderr / exit code.

For shared units, define baseline behavior once. Add separate
context-specific records when a parent changes props, slots, permissions,
available actions, backend collaborators, or error handling.

### B-<UNIT>-001 — <short title>

- **Flow(s):** <F-…-NN, or — if none>
- **Composed by:** <parent behavior record IDs, or — if none>
- **Trigger:** <user action: click / keypress / command invocation>
- **Preconditions:** <required state before the trigger>
- **Observable output:** <what the user perceives; cite selector / testid
  where the profile has one>
- **Backend / side-effects:** <API call + response; files written
  (sidecar JSON, combined `.txt`, output dir); persisted state>
- **Bad-state / error:** <what happens on the failure path>
- **Tier(s):** <A | A+B>
- **Regression:** <no | yes (#issue or commit)>
- **Test:** <path::name | — if not yet written>

<!-- Worked examples — delete when filling in:

WEB / GUI
### B-PAGEVIEW-012 — Save edited text
- Trigger: edit the text area, press Ctrl+S
- Observable output: "Saved" toast appears; the dirty-dot clears
- Backend / side-effects: PUT /api/pages/{id}/{idx}/text → 200; the page
  sidecar .json text field is updated; the combined .txt is regenerated
- Bad-state / error: save while disconnected → error toast; dirty-dot
  stays; no sidecar mutation
- Tier(s): A   Regression: yes (#fixed-2026-04)
- Test: tests/e2e/test_click_paths_page_viewer.py::test_save_text

CLI
### B-RUN-003 — OCR a folder to text
- Trigger: `pd-ocr run ./scans --engine tesseract`
- Observable output: progress on stderr; "Wrote 12 pages" on stdout;
  exit code 0
- Backend / side-effects: 12 per-page .txt + a combined.txt written to
  the output dir
- Bad-state / error: an unreadable image → nonzero exit, error on stderr,
  no partial combined.txt left behind
- Tier(s): A+B   Regression: no
- Test: tests/e2e/test_cli_run.py::test_run_folder
-->

## Known regressions

List the IDs of records tagged `Regression: yes`, with a one-line note on
what re-broke before, so reviewers know which behaviors are load-bearing.

- <B-UNIT-NNN> — <what broke, when>
