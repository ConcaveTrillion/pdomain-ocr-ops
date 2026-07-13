---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-13
Kind: context
---

# Intent map

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** deciding what work remains active, deferred, rejected, or blocked.
- **Search terms:** intent, deferred work, rejected direction, owner decision.

## Active bets

- **Lint catalog reconciliation — active.** Keep the catalog because
  `CONVENTIONS.md` requires it, but fill its current source-coverage gaps.

## Deferred work

- **Remote OCR batch dispatch — deferred.** Modal and shared-container batch
  methods remain explicit unsupported stubs. The protocol seam is available in
  [`batched-ocr-dispatch.md`](../architecture/batched-ocr-dispatch.md).

## Rejected directions

- **Parallel archive tree — rejected.** Retired docs are reduced into durable
  architecture, decisions, and residual intent instead of moved under
  `docs/archive/`.

## Blocked (waiting on)

None.

## Needs owner decision

- **Salvaged `_tbd/` documentation.** Decide which of the 210 tracked Markdown
  files to promote into a pdomain repository and which to delete. The holding
  area says the old OCR meta-repo content is unique historical material, so the
  migration excludes `_tbd/**` rather than inferring lifecycle outcomes.

## Legacy-unverified sweep

<!-- can-retire: docs/plans/2026-05-28-batched-ocr-dispatch.md; shipped local scope promoted to docs/architecture/batched-ocr-dispatch.md, with remote work retained above. -->
<!-- can-retire: docs/plans/2026-06-10-shared-paths-and-export-manifest.md; shipped behavior promoted to docs/architecture/shared-paths-and-export-manifest.md. -->
<!-- still-active: docs/process/writing-style.md; CLAUDE.md and CONVENTIONS.md still name it as authoritative. -->
<!-- needs-owner-review resolved as partial: docs/process/lint-deviations.md; its policy remains active but the catalog is incomplete against current source. -->
