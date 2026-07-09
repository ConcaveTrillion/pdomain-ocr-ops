# Doc Cleanup Plan — workspace-wide

Audit date: 2026-05-09. Problems found and per-repo actions.

---

## Cross-cutting findings

### 1. No frontmatter anywhere

None of the eight repos use YAML/TOML frontmatter. This is fine — don't add it.
The lack is not the problem; the inconsistency in *structure within files* is.

### 2. Inconsistent CLAUDE.md structure

Each repo's CLAUDE.md has drifted to a different shape. Proposed standard (≤120 lines):

```markdown
# <Project>
[one-sentence description]

## Commands
| Command | Purpose |

## Rules
- ...

## Key docs (read before touching X)
- [topic]: [path] — [one line why]

## Sibling deps
- pdomain-book-tools (foundation); editable in uv.toml
```

Every CLAUDE.md should be a *routing index*, not a reference manual.
If a section grows past 10 bullet points, split it into a dedicated doc and replace with a pointer.

### 3. AGENTS.md stubs are noise

pd-ocr-labeler (6 lines) and pdomain-book-tools (5 lines) have AGENTS.md stubs that say
"see CLAUDE.md." Delete these — every modern AI tool reads CLAUDE.md first; the stub
adds a redundant hop and a file to load.

### 4. Large files are loaded silently

Claude Code reads every non-ignored `.md` it can find on session start.
Files >200 lines that are *reference material* (spec details, review notes, archives,
benchmark reports) inflate context for no benefit. The fix is `.claudeignore` entries,
not file deletion. Add an index pointer in CLAUDE.md so humans can still find them.

### 5. Archive dirs need blanket exclusion

---

### 6. ROADMAP files lack effort estimates

Each open ROADMAP item should carry an effort tag so the ship-slice
orchestrator can select the right model without reading the full slice
description:

| Tag | Meaning | → Model |
|-----|---------|---------|
| `(S)` | small / mechanical — CRUD wiring, rename, field add, config | haiku |
| `(M)` | medium / standard — typical feature + tests, modest design surface | sonnet |
| `(L)` | large / architectural — novel subsystem, tricky invariant, cross-file refactor | opus |

Example:

```markdown
- [ ] Slice 15 — wire GET /artifacts/:id  (S)
- [ ] Slice 16 — design multi-step chain runner  (L)
```

**Backfill rule:** add tags incrementally when each ROADMAP is next touched
during a ship-slice run — not as a separate sweep. The doc-realign commit
is the natural place. Active ROADMAPs without tags are acceptable until
then; the ship-slice skill falls back to assessing from the description.

Pattern: `docs/archive/`, `docs/review/detail-files`, `bench/`.
Add `docs/archive/**` to each repo's `.claudeignore`. Keep only the index README.

---

## Per-repo action list

### pdomain-book-tools

**Large files (>200 lines):**

| File | Lines | Action |
| ---- | ----- | ------ |
| docs/review/README.md | 1,194 | Claudeignore; add pointer in CLAUDE.md |
| docs/specs/word-reference-lines-spec.md | 874 | Claudeignore (spec-only, not shipped) |
| docs/specs/reorganize_pipeline.md | 438 | Claudeignore; keep architecture/README.md index |
| docs/specs/glyph-annotations-spec.md | 416 | Claudeignore (spec-only) |
| docs/specs/layout_regression_fixtures.md | 239 | Claudeignore |
| GPU_TESTING.md | 215 | Claudeignore |
| README.md | 210 | Trim: move GPU details to GPU_TESTING.md, keep README ≤120 lines |

**Consistency actions:**

- Delete AGENTS.md (5-line stub).
- Add `.claudeignore`: `docs/review/*.md`, `docs/specs/word-reference-lines-spec.md`, `docs/specs/glyph-annotations-spec.md`, `docs/specs/reorganize_pipeline.md`, `docs/specs/layout_regression_fixtures.md`, `GPU_TESTING.md`.
- CLAUDE.md (34 lines) is already lean — just add doc pointers section.
- docs/README.md (45 lines) is a good index — keep and maintain.

---

### pdomain-ocr-cli

**Large files:**

| File | Lines | Action |
| ---- | ----- | ------ |
| README.md | 351 | Trim: move flag reference to docs/usage.md, keep README ≤150 lines |
| docs/usage.md | 274 | Claudeignore; it's a reference, not session context |

**Consistency actions:**

- Add `.claudeignore`: `docs/usage.md`.
- CLAUDE.md (42 lines) is fine; add pointer to usage.md.
- Smallest doc set in the workspace — don't over-engineer.

---

### pd-ocr-labeler

Largest doc set: 63 files, 7,056 lines. Most token waste is in planning and review.

**Large files (worst offenders):**

| File | Lines | Action |
| ---- | ----- | ------ |
| docs/planning/next-step.md | 1,276 | Claudeignore; replace with 10-line summary in CLAUDE.md |
| docs/review/2026-05-06-*.md (6 files) | ~1,400 total | Claudeignore all; keep review/README.md index |
| docs/architecture/async/migration-patterns.md | 433 | Claudeignore |
| docs/planning/browser-ui-test-plan.md | 433 | Claudeignore |
| docs/architecture/ui-action-buttons.md | 395 | Claudeignore |
| docs/architecture/gpu-deployment.md | 358 | Claudeignore |
| docs/planning/image-overlay-layer-controls-plan.md | 306 | Claudeignore |
| docs/review/bugs.md | 245 | Claudeignore |
| docs/planning/persistence-session-cache-plan.md | 231 | Claudeignore |
| docs/planning/user-persistence-metadata-schema.md | 206 | Claudeignore |

**Consistency actions:**

- Add `.claudeignore`: `docs/planning/next-step.md`, `docs/review/2026-05-06-*.md`, `docs/review/bugs.md`, `docs/architecture/async/migration-patterns.md`, `docs/architecture/gpu-deployment.md`, `docs/architecture/ui-action-buttons.md`, `docs/planning/browser-ui-test-plan.md`, `docs/planning/image-overlay-layer-controls-plan.md`, `docs/planning/persistence-session-cache-plan.md`, `docs/planning/user-persistence-metadata-schema.md`.
- Delete AGENTS.md (6-line stub).
- CLAUDE.md (68 lines) — add a "Key planning docs" pointer section listing the claudeignored files so humans can find them.
- Consider consolidating the 8 planning/*.md files into a single `docs/planning/PLAN.md` once milestone work is done.

---

### pdomain-ocr-labeler-spa

Largest total: 32 files, 12,850 lines. Most waste is in archive and spec detail files.

**Large files:**

| File | Lines | Action |
| ---- | ----- | ------ |
| docs/archive/BUGS_RESOLVED.md | 2,298 | Claudeignore — archive is not session context |
| docs/specs/17-decisions.md | 1,064 | Claudeignore; keep specs/README.md index |
| docs/specs/01-data-models.md | 775 | Claudeignore |
| docs/specs/16-milestones.md | 752 | Claudeignore (milestone detail lives in ROADMAP.md summary) |
| docs/specs/02-backend.md | 616 | Claudeignore |
| docs/specs/09-deployment.md | 611 | Claudeignore |
| docs/specs/06-page-workbench.md | 610 | Claudeignore |
| docs/specs/03-frontend.md | 603 | Claudeignore |
| docs/ROADMAP.md | 329 | Acceptable (active work); trim shipped items out |
| docs/PARITY_STATUS.md | 211 | Acceptable |

**Large files added after 2026-05-09 audit (found 2026-05-15):**

| File | Lines | Action |
| ---- | ----- | ------ |
| docs/PARITY_GAPS_2026_05_14.md | 448 | TODO: claudeignore or split — parity gap detail; active reference but not daily context |
| docs/specs/2026-05-15-hifi-redesign-plan.md | 414 | TODO: claudeignore or split — dated design plan; keep as reference, not session context |
| specs/20-glyph-annotations.md | 536 | TODO: claudeignore — spec file, same treatment as other active specs |
| specs/21-konva-renderer.md | 426 | TODO: claudeignore — spec file |
| specs/22-page-surface-wireup.md | 315 | TODO: claudeignore — spec file |
| specs/23-page-payload-backend.md | 362 | TODO: claudeignore — spec file |
| CONVENTIONS.md | 224 | TODO: claudeignore or split — conventions reference, not session-start context |
| docs/M9.5-keyboard-audit.md | 211 | TODO: claudeignore or split — keyboard audit reference; not session-start context |

**Consistency actions:**

- Add `.claudeignore`: `docs/archive/**`, `docs/specs/01-data-models.md` through `docs/specs/20-glyph-annotations.md` (all individual spec files; keep `specs/README.md` as the loaded index).
- Also claudeignore the new `specs/20-glyph-annotations.md` through `specs/23-*.md` (same pattern).
- CLAUDE.md (58 lines) — add: "Spec index: specs/README.md — never load individual specs, always start there."
- specs/README.md (49 lines) already exists and is the right index — protect it.

---

### pdomain-ocr-synth

Well-organized. 32 files, mostly small specs (88–330 lines). Milestone files are the noise.

**Large files:**

| File | Lines | Action |
| ---- | ----- | ------ |
| docs/specs/01-cli.md | 330 | Claudeignore (reference, not context) |
| docs/specs/10-publishing.md | 283 | Claudeignore |
| docs/specs/12-glyph-annotations-emission.md | 237 | Claudeignore |
| docs/specs/07-degradation.md | 228 | Claudeignore |
| docs/specs/11-preview-ui.md | 221 | Claudeignore |
| docs/specs/08-output-format.md | 206 | Claudeignore |

**Consistency actions:**

- Add `.claudeignore`: `docs/specs/01-cli.md`, `docs/specs/07-degradation.md`, `docs/specs/08-output-format.md`, `docs/specs/10-publishing.md`, `docs/specs/11-preview-ui.md`, `docs/specs/12-glyph-annotations-emission.md`, `docs/roadmap/M00-*.md` through `docs/roadmap/M12-*.md` (keep `docs/roadmap/README.md`).
- docs/specs/00-overview.md (88 lines) should remain the entry point — verify CLAUDE.md points to it.

---

### pd-ocr-trainer

11 files. Largest are draft specs and a detailed code review.

**Large files:**

| File | Lines | Action |
| ---- | ----- | ------ |
| docs/SPEC-layout-training.md | 947 | Claudeignore (draft, not active milestone) |
| docs/DATASETS.md | 450 | Claudeignore; add 5-line summary in CLAUDE.md |
| docs/ROADMAP.md | 431 | Claudeignore; replace with milestone-status table in CLAUDE.md |
| docs/review/code-review.md | 324 | Claudeignore |
| docs/TOP-50-LABELING-TARGETS.md | 226 | Claudeignore (reference list) |

**Consistency actions:**

- CLAUDE.md currently cross-references ROADMAP.md and DATASETS.md — pointers are fine, but both files need claudeignore so they're not auto-loaded.
- Add `.claudeignore`: `docs/SPEC-layout-training.md`, `docs/DATASETS.md`, `docs/ROADMAP.md`, `docs/review/code-review.md`, `docs/TOP-50-LABELING-TARGETS.md`.
- Add 5-line milestone-status table directly in CLAUDE.md (current milestone, done/next).

---

### pd-png-optimizer

24 files, well-organized. Two clear targets.

**Large files:**

| File | Lines | Action |
| ---- | ----- | ------ |
| bench/REPORT.md | 516 | Claudeignore (benchmark data — not context) |
| docs/OPEN_QUESTIONS.md | 381 | Claudeignore; add pointer in CLAUDE.md |
| docs/specs/04-api-and-integration.md | 308 | Claudeignore |
| docs/research/gpu-zopfli.md | 283 | Claudeignore (parked research) |

**Consistency actions:**

- Add `.claudeignore`: `bench/**`, `docs/OPEN_QUESTIONS.md`, `docs/specs/04-api-and-integration.md`, `docs/research/**`.
- CLAUDE.md (65 lines) is already good. Add one line: "Open design questions: docs/OPEN_QUESTIONS.md."
- Milestone files (8, M1–M8) are small (50–180 lines) — keep them loaded; they're active references.

---

### pdomain-prep-for-pgdp

26 files. Spec directory has the most waste (10 specs, several 400–1005 lines).

**Large files:**

| File | Lines | Action |
| ---- | ----- | ------ |
| docs/specs/pipeline-task-model.md | 1,005 | Claudeignore (locked reference) |
| docs/08-roadmap.md | 756 | Claudeignore; replace with milestone-status table in CLAUDE.md |
| docs/08-roadmap-shipped.md | 641 | Claudeignore (historical) |
| specs/06-page-workbench.md | 611 | Claudeignore |
| specs/09-deployment.md | 610 | Claudeignore |
| specs/08-data-models.md | 532 | Claudeignore |
| specs/04-gpu-acceleration.md | 526 | Claudeignore |
| specs/07-api-design.md | 440 | Claudeignore |
| specs/02-pipeline-steps.md | 425 | Claudeignore |
| specs/01-book-config.md | 435 | Claudeignore |
| specs/03-ui-layout.md | 471 | Claudeignore |
| specs/REFACTOR-PROPOSAL.md | 310 | Claudeignore (historical) |
| specs/00-overview.md | 295 | Claudeignore (summary lives in docs/01-overview.md) |
| docs/futures/managed-adapter-pgdp.md | 237 | Claudeignore (deferred) |
| DEVELOPMENT.md | 237 | Acceptable; trim prerequisites block |
| docs/02-backend.md | 236 | Acceptable |

**Consistency actions:**

- Add `.claudeignore`: `specs/**` (all spec files; docs/README.md already covers them), `docs/08-roadmap.md`, `docs/08-roadmap-shipped.md`, `docs/specs/pipeline-task-model.md`, `docs/futures/**`.
- CLAUDE.md (95 lines) — add one-line current milestone status and pointer to roadmap file.
- Architecture docs (`docs/01-*.md` through `docs/07-*.md`, each 100–240 lines) are useful session context — keep loaded.

---

## Implementation order

Priority order by token savings:

1. **pdomain-ocr-labeler-spa** — worst ratio; single `.claudeignore` edit saves ~10K lines.
2. **pd-ocr-labeler** — second-worst; planning + review files alone are ~5K lines.
3. **pdomain-prep-for-pgdp** — specs directory ~5K lines.
4. **pdomain-book-tools** — review + specs ~3K lines.
5. **pd-ocr-trainer** — drafts + review ~2K lines.
6. **pd-png-optimizer** — bench + research ~800 lines.
7. **pdomain-ocr-synth** — milestone files + large specs ~800 lines.
8. **pdomain-ocr-cli** — lowest priority; usage.md is the main target.

## `.claudeignore` template pattern

Each repo's `.claudeignore` should grow a `# docs — large reference files` section:

```gitignore
# docs — large reference files (too large for session context; read on demand)
docs/archive/**
docs/review/2026-*.md
docs/specs/01-*.md
bench/**
```

Keep short active-milestone docs loaded. Exclude archives, locked references, draft specs,
benchmark data, and parked research.
