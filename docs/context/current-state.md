---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-13
Kind: context
---

# Current state

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** starting work that depends on current repository documentation.
- **Search terms:** current state, active work, risks, docs migration.

## What matters now

Docgraph is initialized for this repository. Shipped OCR batching and
shared-path/export-manifest behavior live in
[`batched-ocr-dispatch.md`](../architecture/batched-ocr-dispatch.md) and
[`shared-paths-and-export-manifest.md`](../architecture/shared-paths-and-export-manifest.md).

## In-flight work

- The [lint-deviation catalog](../process/lint-deviations.md) is reconciled
  with the current source tree.
- Remote Modal and shared-container OCR batch dispatch remains deferred.
- Red-team each of the 210 salvaged Markdown files under `_tbd/` against
  implementation and current practice. Preserve useful material in
  architecture, decisions, or the intent map before superseding or retiring a
  materially diverged source. The holding area remains outside the governed
  graph during this review.

## Verification

The migration baseline passed 460 tests with 1 optional Modal import test
skipped on 2026-07-13.
