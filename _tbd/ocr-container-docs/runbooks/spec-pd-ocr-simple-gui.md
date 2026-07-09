# Reminder — spec out `pdomain-ocr-simple-gui`

Created during the `cross-cut` brainstorm (2026-05-16) for the shared pdomain-ui /
pdomain-ops design. The simple OCR GUI is named as a future consumer of pdomain-ui +
pdomain-ops but does not exist yet and has no spec.

## What it is (working definition)

A minimal drag-and-drop OCR app for users who only want "give me text from this
image" and have no interest in the labeler, pgdp-prep, trainer, or proofreader.
The simplest possible consumer of pdomain-ops + pdomain-ui.

## Why it matters in the cross-cut design

It exists in the architecture as the **lower-bound consumer** — it must be
installable on its own (`uv tool install pdomain-ocr-simple-gui`) without dragging in
labeler, pgdp-prep, trainer, etc. If the simple GUI's needs are satisfiable
without forcing users into the wider suite, the "each app independently
installable" design principle is honored.

## Constraints inherited from the cross-cut design

- Installed via `uv tool install pdomain-ocr-simple-gui`.
- Single FastAPI backend + React frontend SPA bundled inside the wheel.
- Depends on:
  - `pdomain-book-tools` (Python foundation — data models, OCR primitives)
  - `pdomain-ops` (Python ops — pipeline orchestration, sidecar IO)
  - `@concavetrillion/pdomain-ui` (TS frontend lib — at minimum `PageImageCanvas`,
    `AppShell`, primitives)
- Registers itself in `~/.local/share/pd-suite/installed.toml` on first run so
  that other installed suite apps can advertise it in their launcher.
- Launcher inside the simple GUI hides itself if no siblings are installed.
- No required coupling to any other pd-* app at runtime.

## What to spec when the time comes

- UX flows: drag image → see OCR → download text. No project, no pages list,
  no review.
- Configuration surface: language, OCR engine choice (DocTR vs Tesseract),
  output format (plain text / JSON / hOCR).
- Whether it persists anything between sessions (probably yes — recent files
  list, last config — single-user local-only).
- Auth: probably none (single-user local).
- How it advertises itself for spawn-from-sibling.

## Related items

- Once specced, this slot fills in the `pd-suite.json` manifest shipped by
  pdomain-ui.
- Should be the smallest pd-* SPA — useful as a reference implementation for
  "minimal pdomain-ui consumer."
