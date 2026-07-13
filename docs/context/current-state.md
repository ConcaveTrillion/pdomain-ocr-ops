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

Docgraph is initialized for this repository. Shipped OCR batching and GPU
adapter ownership live in
[`batched-ocr-dispatch.md`](../architecture/batched-ocr-dispatch.md). Page
lifecycle and local storage seams live in
[`page-lifecycle-and-storage.md`](../architecture/page-lifecycle-and-storage.md).
Shared device, update, desktop, path, and schema boundaries live in
[`suite-services.md`](../architecture/suite-services.md) and
[`shared-paths-and-export-manifest.md`](../architecture/shared-paths-and-export-manifest.md).

## In-flight work

- The [lint-deviation catalog](../process/lint-deviations.md) is reconciled
  with the current source tree.
- Remote Modal and shared-container OCR batch dispatch remains deferred.
- The evidence review of all 210 salvaged Markdown files is complete. The
  [salvaged documentation red-team ledger](../research/2026-07-13-salvaged-docs-red-team.md)
  records each recommendation. The [intent map](intent-map.md) now preserves
  20 deduplicated active, deferred, blocked, rejected, or owner-decision items.
  Promote remaining shipped truth and rationale before retiring or deleting
  any `_tbd/` source. The holding area remains outside the governed graph.

## Verification

The migration baseline passed 460 tests with 1 optional Modal import test
skipped on 2026-07-13.
