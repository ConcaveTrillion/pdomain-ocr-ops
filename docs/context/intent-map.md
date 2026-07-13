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

- **Lint catalog maintenance — active.** The catalog now matches the current
  source tree. Keep it current because `CONVENTIONS.md` requires every
  suppression to be documented.
- **Salvaged `_tbd/` red-team review — active.** Compare each of the 210
  tracked Markdown files with implementation and current practice. A material
  divergence routes the source to supersession or retirement only after useful
  ideas move to the right durable destination: architecture for shipped truth,
  decisions for rationale, or this intent map for promising unbuilt work.
  Label anything that did not ship or no longer matches current practice. Do
  not manufacture conformance headings or discard a diverged document
  wholesale.

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

None. The owner authorized the `_tbd/` red-team review on 2026-07-13.

## Legacy-unverified sweep

<!-- can-retire: docs/plans/2026-05-28-batched-ocr-dispatch.md; shipped local scope promoted to docs/architecture/batched-ocr-dispatch.md, with remote work retained above. -->
<!-- can-retire: docs/plans/2026-06-10-shared-paths-and-export-manifest.md; shipped behavior promoted to docs/architecture/shared-paths-and-export-manifest.md. -->
<!-- still-active: docs/process/writing-style.md; CLAUDE.md and CONVENTIONS.md still name it as authoritative. -->
<!-- needs-owner-review resolved as active: docs/process/lint-deviations.md; the catalog is reconciled against current source. -->
