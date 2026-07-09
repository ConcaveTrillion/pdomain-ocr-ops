# Page-split downstream rollout — design & sequencing (Plans 3–5)

**Date:** 2026-06-01
**Status:** Draft — needs CT architectural decisions on the two flagged points below
**Upstream:** `docs/specs/2026-05-31-page-record-ops-design.md` (the authoritative design)
**Predecessors shipped/ready:** Plan 1 (book-tools `Page` split, v0.17.x — tagged, *not yet
published to the index*), Plan 2 (pdomain-ops `PageRecord`/`BlobStore`/aggregates —
dev-complete on branch `feat/page-record-ops`, release-gated).

---

## Why this doc exists

Plan 2's design spec §14 lists steps 3–6 (labeler-spa, prep-for-pgdp, cli, simple-gui)
as if each is a mechanical "import from pdomain-ops" change. Exploration of all four
repos shows that is **only true for the two end-state producers** (cli, simple-gui).
The two **lifecycle consumers** (labeler-spa, prep-for-pgdp) each already own a rich,
shipped domain model that *overlaps but does not match* the pdomain-ops universal
models. Their migration is a **composition/reconciliation** problem with genuine
architectural choices, on apps that are already in daily use.

This doc separates the mechanical work (Plan 5, ready to execute) from the
design-gated work (Plans 3–4), records the per-repo blast radius found during
exploration, and surfaces the two decisions that need CT before Plans 3–4 can be
turned into executable plans.

---

## The release gate (applies to ALL downstream plans)

None of Plans 3–5 can be *released* until:

1. **pdomain-book-tools 0.17.x is published to `pdomain-index-pip`** (currently tagged
   but unpublished — GitHub Actions disabled on several repos; CT's call). The index
   tops out at 0.16.0.
2. **pdomain-ops 0.6.0 is released** (Plan 2 branch merged + tagged + published) —
   itself gated on (1), since Plan 2 pins book-tools `>=0.17.0`.

Until then, downstream repos can only be *developed* against editable siblings, with
the same temporary `[tool.uv.sources]` path-editable workaround Plan 2 used (revert to
`{ index = ... }` before release). Recommendation: **do not start downstream execution
until the gate clears** — developing four repos against a moving editable chain that
isn't on canonical `main` invites the worktree-path-fragility and editable-orphan
hazards already recorded in memory. Write the plans now; execute after release.

---

## Two tiers (confirmed by exploration)

| Repo | Tier | Reads removed Page fields? | Owns a competing domain model? | Migration shape |
|---|---|---|---|---|
| `pdomain-ocr-cli` | end-state producer | No | No | **Mechanical** (Plan 5A) |
| `pdomain-ocr-simple-gui` | end-state producer | No (only its test fake) | No | **Mechanical** (Plan 5B) |
| `pdomain-ocr-labeler-spa` | lifecycle consumer | No direct Page reads* | **Yes** — local `PageRecord`, `RotationSource`, `PagePayload`, `UserPageEnvelope` | **Design-gated** (Plan 3) |
| `pdomain-prep-for-pgdp` | lifecycle consumer | No (pre-OCR) | **Yes** — its own `PageRecord`, `Project`, `IStorage`, `IDatabase` | **Design-gated** (Plan 4) |

\* labeler reads the *stripped* operational fields off its own local `PageRecord`/
envelope, not off book-tools `Page` — so the Page-field removal barely touches it; the
work is replacing its local types + retiring `UserPageEnvelope`.

---

## DECISION 1 (CT) — How do app domain models compose with the ops universal models?

Both lifecycle consumers already have a `PageRecord` that is **not** the ops one:

- **labeler-spa** `core/models.py:133` — fields: `page_index, page_number, image_path,
  page_source, ocr_failed, ocr_provenance, saved_provenance, cached_images,
  rotation_degrees, rotation_source, provenance_summary, payload_error`. A *view/load
  outcome* model.
- **prep-for-pgdp** `core/models.py:203` — fields: `idx0, prefix, source_stem,
  page_type, alignment, config_overrides, splits, illustration_regions, source_key,
  thumbnail_key, processed_image_key, ocr_image_key, processing_status,
  processing_job_id, outputs, parent_page_id, split_index, …`. A *prep-domain* model.

The ops `PageRecord` is narrower and different in intent: `page_id, page_index,
image_path, source, ocr_failed, rotation_degrees, rotation_source, provenance
(ProvenanceGraph), provenance_summary, changelog`. It owns **provenance + rotation +
changelog identity**; the app models own **app-specific page state**.

**These are not the same object and should not be force-merged.** Recommended pattern
(**composition, not replacement**):

> Each app keeps its app-specific page model, and that model **gains a reference to**
> (or embeds) the ops `PageRecord` for the universal lifecycle metadata
> (`page_id`, provenance, rotation history, changelog). The app stops *duplicating*
> `RotationSource`, `rotation_degrees`, `rotation_source`, `provenance_summary`,
> `ocr_provenance` — those move onto the embedded ops `PageRecord`. The app keeps its
> own fields (splits, blob-keys, cached_images, page_type, …).

So: import `RotationSource` from ops (delete the local enum); import/embed ops
`PageRecord` for provenance+rotation+changelog; keep the app's own record for app
state, linked by the shared `page_id`.

**Alternative considered & rejected:** widening the ops `PageRecord` to absorb every
app's fields — that would pollute the universal model with labeler/prep specifics and
couple unrelated consumers. Rejected.

**What CT must confirm:** the composition pattern (embed ops `PageRecord`, keep app
record) vs any preference. This shape determines Plans 3 and 4 entirely.

---

## DECISION 2 (CT) — Persistence: how far do lifecycle consumers adopt the event store?

Design spec §8–§9 prescribe the event store (`eventsourcing[sqlite]`) + content-
addressed `BlobStore` as the durable persistence for lifecycle consumers, and §14
step 3 says labeler "retires `UserPageEnvelope`" in favor of "event store + blob store
load path." But both apps already have working, shipped persistence:

- **labeler-spa**: `UserPageEnvelope` JSON sidecars per page (lanes: cached/labeled),
  across ~12 files (persistence, OCR adapters, export, api). Retiring this is a large
  rewrite of a shipped persistence layer.
- **prep-for-pgdp**: `IDatabase` (SQLite + JSON sidecars) + `IStorage` (filesystem/S3,
  path-keyed, not content-addressed). The ops `BlobStore` (content-addressed) overlaps
  `IStorage`; the ops event store overlaps `IDatabase`.

Adopting the event store fully means **replacing shipped, working persistence** in two
daily-use apps — high risk, and it intersects the standing "converge local-mode first,
JSON-sidecar persistence is in scope, Postgres deferred" directive (2026-05-07). The
event store *is* a local-mode mechanism (sqlite, not Postgres), so it doesn't violate
the Postgres deferral — but swapping persistence engines on shipped apps is a big call.

**Recommended phasing (de-risked):**

- **Phase A (Plans 3/4 v1 — value-model adoption only):** import ops `PageRecord` /
  `ProjectRecord` / `RotationSource` / `ProvenanceGraph` / `build_provenance_summary`;
  delete duplicated local types; thread `page_id` + provenance through the existing
  persistence (envelope/sqlite) unchanged. `PagePayload` used for API responses where
  it fits. **No event store, no blob store yet.** This delivers the page-split benefit
  (one source of truth for provenance/rotation; no operational baggage on `Page`)
  without rewriting persistence.
- **Phase B (separate, later):** migrate persistence to the event store + `BlobStore`
  (`PageAggregate`/`ProjectAggregate`), retire `UserPageEnvelope` sidecars / fold
  `IStorage` into `BlobStore`. Its own spec + plan, with a data-migration story for
  existing projects on disk.

**What CT must confirm:** is Plans 3/4 scope **Phase A only** (value-model adoption,
keep existing persistence) — recommended — or the full §8/§9 event-store adoption now?

---

## Per-repo blast radius (from exploration)

### Plan 3 — labeler-spa (lifecycle consumer; design-gated)

- **Delete local + import from ops:** `RotationSource` (`core/models.py:121`, mirror in
  `core/page_state.py:99`); reconcile local `PageRecord` (`core/models.py:133`) per
  Decision 1.
- **Provenance summary:** replace `api/pages.py:352` `_build_provenance_summary` with
  `pdomain_ops.pages.build_provenance_summary` (adapt the input to a `ProvenanceGraph`).
- **API response:** local `PagePayload` (`api/pages.py:48`) is rich (line_matches,
  selection, encoded_dims, generation, page_text_*). Keep it (rename to avoid the ops
  `PagePayload` import clash, e.g. `LabeledPageResponse`) and let it *contain* an ops
  `PagePayload`/`PageRecord` for the canonical page data. Do **not** flatten to the
  minimal ops payload.
- **UserPageEnvelope (12 files):** Phase B. List in §3 of the exploration; touches
  `core/persistence/*`, `adapters/ocr/local_doctr.py`, `core/jobs/handlers/export.py`,
  `api/pages.py`, `api/words.py`, `core/envelope_lift.py`.
- **PageState relink:** `core/project_state.py:81` `PageState.page_record` → link by
  `page_id` (shared identity with the embedded ops `PageRecord`).
- **`cached_images: CachedImageSet`** retired in favor of blob refs — Phase B.
- Floors: book-tools `>=0.14.1`→`>=0.17.0`, ops `>=0.4.0`→`>=0.6.0`.
- **Additions Plan 3 must make to pdomain-ops** (surfaced by the Plan 2 final review;
  all additive, no break to 0.6.0 — land them in a 0.7.0 or fold into Plan 3's ops PR):
  - `PageAggregate.rotation_updated(rotation_degrees, rotation_source)` event (design
    spec §6 manual rotation) — **Phase B only** (Phase A maps rotation directly onto
    `PageRecord.rotation_degrees`/`rotation_source`, no event needed).
  - `ProjectAggregate.remove_page(page_id)` event (labeler supports page deletion; not
    in spec §11 yet) — **Phase B only**.
  - `PagePayload.thumbnail_url: str | None = None` (the §9 lazy-thumbnail display path;
    additive optional field) — needed whenever the labeler API response uses ops
    `PagePayload` as its inner page model.
  - Construct `BlobStore` with `project_dir / ".pd-pages"` to match the spec §9 path
    convention (`BlobStore.__init__` creates `<project_dir>/blobs/`; the `.pd-pages/`
    parent is the caller's responsibility) — **Phase B**.
- Tests: `tests/{unit,integration,conformance,e2e}`; pytest-asyncio, xdist; conformance
  `test_legacy_envelopes.py` + `test_response_models.py` guard the envelope/response
  shapes — these gate the Phase B persistence change.

### Plan 4 — prep-for-pgdp (lifecycle consumer; design-gated)

- **Name clash:** prep's `PageRecord` (`core/models.py:203`) is prep-domain, not ops.
  Per Decision 1, embed an ops `PageRecord` (provenance/rotation/changelog) on prep's
  record, or alias prep's to `PrepPageRecord`. Confirm with CT.
- **ImageIngested at ingest:** `core/ingest.py:71` `unzip_source` creates one prep
  `PageRecord` per image *before any OCR* — exactly the spec's motivating case. Phase A:
  assign `page_id` + create an ops `PageRecord(source="raw", page_index=idx0)` here.
  Phase B: fire `PageAggregate.ImageIngested`.
- **ProjectRecord + ordering:** prep orders by `PageRecord.idx0` today; ops
  `ProjectRecord.page_ids: list[UUID]` becomes authoritative order. Thread through
  `core/models.py:67` `Project` + the reorder route.
- **Thumbnails / BlobStore:** prep generates thumbnails (`core/ingest.py:285`) and
  stores via path-keyed `IStorage`. ops `BlobStore` is content-addressed — Phase B
  overlap; Phase A keeps `IStorage`.
- **Rotation:** prep tracks `flip_horizontal/vertical`, `manual_deskew_angle`,
  `rotated_standard` in `config_overrides`; map cumulative rotation onto the ops
  `PageRecord.rotation_degrees`/`rotation_source` (Phase A).
- Already pins ops `>=0.4.0` and book-tools `>=0.14.1` — bump to `>=0.6.0` / `>=0.17.0`.
- Tests: 145 files; pytest asyncio+xdist; e2e Playwright + vitest in `make ci`.

### Plan 5 — cli + simple-gui (end-state producers; mechanical — executable now)

See the executable plan `docs/plans/2026-06-01-page-split-downstream-cli-simple-gui.md`.
Summary of the **mandatory (compatibility) scope**:

- **cli:** floor bumps (book-tools `>=0.17.0`, ops `>=0.6.0`); fix the single-image
  compat shim `ocr_to_txt.py:474-484` to unpack the new
  `from_image_ocr_via_doctr -> (Document, int)` tuple; add `page_id`/`image_blob_hash`/
  `gt_orphans` to the `FakePage` test double (`tests/_fakes.py`). No removed-field reads
  exist. `fail_under = 100` — test doubles must track the new Page surface.
- **simple-gui:** floor bumps; remove the now-invalid removed fields (`ocr_provenance`,
  `source`, `ocr_failed`, `rotation_applied`, `image_path`) from the fake dispatcher's
  synthetic Page dict (`testing/fake_dispatcher.py:179-183`); clean main, no in-flight
  branch. SPA contract test unaffected.

**Deferred (additive, NOT in Plan 5 v1):** building a `ProvenanceGraph` across
OCR→Layout→Reorganize and emitting `PagePayload` JSON (cli) / adding provenance to the
API response (simple-gui). These are *new output contracts* with no consumer yet (the
"import CLI PagePayload into the labeler" path is future). Hold until a consumer exists,
then spec separately. Flagged so it isn't silently dropped.

---

## Recommended sequencing

1. **Clear the release gate** (CT): publish book-tools 0.17.x → release pdomain-ops
   0.6.0 (Plan 2 merge+tag, after reverting its temp uv.sources path).
2. **Plan 5** (cli + simple-gui) — mechanical, lowest risk, validates the consumer
   import surface of ops 0.6.0. Execute first once the gate clears.
3. **Decisions 1 & 2** (CT) — confirm composition pattern + Phase-A-only scope.
4. **Plan 3 / Plan 4 — Phase A** (value-model adoption, keep existing persistence).
   Can run in parallel (independent repos) once Decisions land.
5. **Phase B** (event store + BlobStore persistence migration) — separate specs/plans
   per app, with data-migration stories. Only if/when CT wants to retire the
   sidecar/IStorage persistence.

---

## Open items for CT

- [ ] **Decision 1** — confirm composition pattern (embed ops `PageRecord`; keep app
      records; delete duplicated `RotationSource`/rotation/provenance fields).
- [ ] **Decision 2** — confirm Plans 3/4 are **Phase A only** (value-model adoption,
      existing persistence kept) vs full event-store adoption now.
- [ ] Confirm Plan 5's provenance/`PagePayload` emission stays **deferred** (no consumer
      yet) vs wanted now.
- [ ] Release-gate ownership: book-tools 0.17.x publish + Actions re-enable.
