# Handoff — resume the cross-cut workstream (2026-05-17)

> Paste the body of this file (or just point at it) in a fresh Claude session
> to pick up where the 2026-05-17 cross-cut session ended.
>
> Supersedes [handoff-2026-05-16-cross-cut.md](handoff-2026-05-16-cross-cut.md).

---

**Resume from prior session — cross-cut design rewritten + 6 new plans committed.**

Working directory: `/workspaces/ocr-container/`. Multi-repo workspace with 8 `pd-*` projects plus `se-llm-skills`. Per-repo agents at `.claude/agents/<repo>.md`; routing rules in the workspace `CLAUDE.md`.

## What's new on `main` since 2026-05-16

```
71e9a6e docs(plan): pdomain-ui — align *Like reductions to spec §5 rewrite
91fa207 docs(spec): rewrite §5 — type-system roadmap, PageCategory, subpages
12ed3ce docs(plan): phase 1.7 — GPU adapter migration (pgdp-prep → pdomain-ocr-ops)
ea4600f docs(plan): pdomain-ui — new repo (TS/React component library)
61abe1e docs(plan): pdomain-ocr-ops — new repo (suite plumbing + local GPU adapters)
675cac0 docs(plan): pdomain-index-npm — new repo (npm index on GitHub Pages)
fc4da63 docs(plan): workspace — rename pd-index to pdomain-index-pip
59f27a1 docs(plan): workspace — pdomain-ui + pdomain-ocr-ops agent definitions  ← also bundles preexisting workspace state (see commit body)
```

### What changed in spec §5 (commit `91fa207`)

The original §5 declared a "post-promotion shape" that silently dropped a lot of real pdomain-book-tools fields, used a separate `class Line(BaseModel)`, used a single `Page.id: str`, and proposed several taste-only renames. After grounding in the actual code + active-consumer call counts (pdomain-ocr-labeler-spa is the dominant downstream), §5 was rewritten:

- **Honest about today's state**: pdomain-book-tools is stdlib `@dataclass`, not Pydantic. Plan #1 adds `pydantic>=2.0` only for `TypeAdapter`-based schema emission. Native Pydantic migration deferred (lowest priority).
- **Restored Word fields** the prior draft silently dropped: `word_labels`, `word_components`, `text_style_labels`, `text_style_label_scopes`, `baseline` (kept top-level — labeler-spa has 41–71 active refs per cluster).
- **Clustered into sub-objects** (as deferred follow-up plans): `Page.provenance: OCRProvenance` (49 refs), `Word.matching: GTMatchMetadata` (155 refs).
- **Lines are blocks**: no separate `Line` class; `Block(category=LINE)`. Added `BlockCategory.CAPTION` so PLATE pages can still carry proofable caption text via a CAPTION child block.
- **PageCategory enum**: COVER/TITLE/FRONTMATTER/TOC/BODY/PLATE/FOOTNOTES/INDEX/BACKMATTER/BLANK/OTHER + `category_subtype` free-text refinement.
- **Subpages** (foldouts split into panels, tall pages split horizontally): full model with `parent_page_index`, `subpage_children` (bidirectional), `subpage_position` enum, `subpage_subname`, `subpage_index`, `parent_bbox`. Subpages share parent's `page_index`.
- **`rotation_applied`** promoted to canonical top-level Page field (active render state, not provenance).
- **Rejected taste-only renames**: `bbox`/`confidence`/`natural_width`/`natural_height`/`Page.id` all explicitly rejected with rationale + call-site counts.
- **Dropped vestigial** `Page.unmatched_ground_truth_lines` (0 refs).

## What's still ahead

Seven unwritten plans, each enumerated explicitly in the new "Deferred type-system migration" section of spec §5:

1. **`Word.matching: GTMatchMetadata` fold** — fold existing top-level `Word.ground_truth_*` fields into `matching`. ~155 call-site updates in `pdomain-ocr-labeler-spa`.
2. **`Page.provenance: OCRProvenance` fold** — fold existing top-level provenance fields. ~49 call-site updates in `pdomain-ocr-labeler-spa`.
3. **`Page.image_path` → `Page.image_url` rename** — the only canonical rename. ~59 call sites across `pdomain-ocr-labeler-spa` + `pdomain-prep-for-pgdp`.
4. **`rotation_applied` documented as canonical** (no code change; spec-only promotion).
5. **`page_category` + subpages + `parent_bbox` + `subpage_children`** — new fields, default `None`/`[]`, no migration impact.
6. **`BlockCategory.CAPTION`** — new enum value; producers (DocTR/Tesseract pipelines + pdomain-ocr-synth recipes) need to start emitting it.
7. **Native-Pydantic migration of Word/Block/Page/Character** — largest item. `TypeAdapter` already gives codegen consumers what they need; this is Python-side ergonomics only. Optional / lowest priority.

Plus the six earlier-written plans, all written but **not executed**:

- ✅ `pdomain-book-tools` schema + emitter (plan from 2026-05-16, commit `3470091`) — independent of the §5 rewrite, can ship anytime
- workspace agent definitions for `pdomain-ui` + `pdomain-ocr-ops` (commit `59f27a1`)
- `pd-index` → `pdomain-index-pip` rename (commit `fc4da63`)
- `pdomain-index-npm` new repo (commit `675cac0`)
- `pdomain-ocr-ops` new repo (commit `61abe1e`)
- `pdomain-ui` new repo (commit `ea4600f`)
- Phase 1.7 GPU adapter migration (commit `12ed3ce`)

## Pick one to do first

- **(a) Write the 7 deferred-migration plans** — close out the planning phase before any execution. The 7 items all touch pdomain-book-tools + active consumers. Could be dispatched in parallel like the 6 earlier plans (opus, background subagents); takes ~10–20 min wall time.
- **(b) Execute plan #1 (pdomain-book-tools)** — independent of the deferred-migration items. 7 TDD tasks. Subagent-driven-development workflow.
- **(c) Parallel execution batch** — plan #1 + plan #4 (pdomain-index-npm) + plan #5 (pdomain-ocr-ops) in three concurrent flows. Isolated trees; no conflicts.
- **(d) Other / revisit the spec** — pick something from outside this list.

## Pre-session checks (optional, ≤30 s each)

- `git log --oneline -10` — confirm you're at `71e9a6e` or later on `main`.
- Skim the new spec §5's "Canonical model shape", "Deferred type-system migration", and "Rejected renames" subsections to load context.
- `git status --short` will show one unrelated modified file (`.claude/agent-memory/pdomain-prep-for-pgdp/blocked_items.md`) — preexisting, not from this workstream; leave it alone unless you know what to do with it.

## Useful context that's easy to lose

- **Active downstream consumer that matters**: pdomain-ocr-labeler-spa. pdomain-prep-for-pgdp / pd-ocr-trainer / pdomain-ocr-cli / pdomain-ocr-synth have 0 references to most clustered fields. The legacy pd-ocr-labeler (282 refs) is being superseded — its call-site count was excluded from the active total.
- **The "Adopt with edits" iteration loop**: the §5 rewrite went through a few question rounds about (i) page-category enum names, (ii) plate captions being proofable text (not skipped), (iii) subpage indexing semantics (subpages share parent's `page_index`), (iv) bidirectional parent↔child subpage linking, (v) `parent_bbox` on the canonical model. All those decisions are baked into spec §5 now.
- **Identity cluster**: 1,043 labeler-spa refs to `page_index`. A rename is a non-starter. The §5 rewrite acknowledges this.
- **Commit `59f27a1` warning**: its tree contains 65 files (the plan + ~64 preexisting staged workspace updates: agent-memory cleanup, design-system docs, cost-dashboard helpers, memory feedback note). The commit message documents this so you don't need to re-investigate.

## Tone calibration from the prior session

- User is decisive and terse — "C", "B", "OK", "yes", short directives. Match that pace.
- Push back honestly when a proposal duplicates or contradicts existing artifacts (the §5 rewrite came after the user asked "are those names really messy? what's the problem with them?" and the honest answer revealed the prior draft was much weaker than the existing code).
- "Each pd-* app independently installable" is still a load-bearing design principle.
- "A line truly is just a special kind of block, just as a paragraph is" — corrected the spec's earlier separate-`Line`-class assumption mid-conversation. Spec is now aligned.
- Subpages are real PGDP-driven concern, not theoretical.

## Files referenced

- Spec: `docs/superpowers/specs/2026-05-16-cross-cut-design.md` (§5 rewritten 2026-05-17)
- Existing plans: `docs/superpowers/plans/2026-05-16-*.md` (8 files: pdomain-book-tools + 6 new + se-assist)
- Prior handoff (superseded): `docs/superpowers/handoff-2026-05-16-cross-cut.md`
- Deferred-spec reminders: `docs/superpowers/reminders/spec-pdomain-ocr-simple-gui.md`, `docs/superpowers/reminders/desktop-launcher-integration.md`
