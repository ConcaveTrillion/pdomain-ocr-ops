---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-13
Kind: context
---

# Decisions

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** checking durable documentation and lifecycle decisions.
- **Search terms:** decisions, retired plan, archive policy, tombstone.

### 2026-07-13 — Retire completed implementation plans

- **Context:** Two inferred-active plans describe behavior that shipped in May
  and June 2026.
- **Decision:** Delete the plans after promoting their durable behavior to
  [`batched-ocr-dispatch.md`](../architecture/batched-ocr-dispatch.md) and
  [`shared-paths-and-export-manifest.md`](../architecture/shared-paths-and-export-manifest.md).
- **Rationale:** Architecture docs are current truth; completed execution
  checklists are not.
- **Evidence:** Commits `8703224`, `eee600b`, `4111e95`, `4898f33`, `d7209ab`,
  and the source and tests cited by both architecture docs.
- **Remaining work:** Remote OCR batch dispatch remains deferred in
  [`intent-map.md`](intent-map.md).

### 2026-07-13 — Retire the parallel archive tree

- **Context:** `docs/archive/` contained nine empty `.gitkeep` files and no
  documentation.
- **Decision:** Remove the archive scaffold and stop treating archive as a
  lifecycle destination.
- **Rationale:** Docgraph retirement preserves durable truth in architecture,
  decisions, and residual intent. Empty cold-storage folders add a competing
  convention without preserving knowledge.
- **Evidence:** Owner direction on 2026-07-13 and commit `a603ce9`, which created
  the otherwise-unused scaffold.
- **Remaining work:** none.

### 2026-07-13 — Exclude the salvaged holding area pending triage

- **Context:** `_tbd/` contains 210 tracked Markdown files salvaged from the old
  OCR meta-repository, and its README requires keep-or-delete review.
- **Decision:** Exclude `_tbd/**` from docgraph indexing and reverse-reference
  scans until the owner classifies that corpus.
- **Rationale:** Those files are not wired into pdomain-ops, but their unique
  historical content makes automatic deletion or lifecycle inference unsafe.
- **Evidence:** `_tbd/README.md` and the tracked-file count on 2026-07-13.
- **Remaining work:** Resolve the owner-decision item in
  [`intent-map.md`](intent-map.md).
