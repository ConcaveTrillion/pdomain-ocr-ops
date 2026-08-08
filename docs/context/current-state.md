---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-08-08
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

## Completed migration

The salvaged holding corpus is retired. The
[red-team ledger](../research/2026-07-13-salvaged-docs-red-team.md) preserves
all 210 document dispositions.

Architecture, decisions, and the [intent map](intent-map.md) retain shipped
truth and rationale. They also retain promising work and unresolved
external-state blockers.

Repository tooling no longer contains the obsolete `_tbd/` exclusions.

GitHub Issues is not used as a work tracker for this repository. Governed
reports under [`docs/issues/`](../issues/README.md) are canonical, and that
README is the sole open and resolved issue index.

## In-flight work

- No issue is open. `pdomain_ops` type-checks clean under basedpyright strict
  with no baseline file. See
  [the lint-deviation catalog](../process/lint-deviations.md).
- The [lint-deviation catalog](../process/lint-deviations.md) is reconciled
  with the current source tree.
- Remote Modal and shared-container OCR batch dispatch remains deferred.

## Verification

The migration baseline passed 460 tests with 1 optional Modal import test
skipped on 2026-07-13.
