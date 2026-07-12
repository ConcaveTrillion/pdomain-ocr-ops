# Design Spec: PageRecord in pdomain-ops

**Date:** 2026-05-31
**Status:** Draft
**Repos affected:** pdomain-ops, pdomain-book-tools, pdomain-ocr-labeler-spa, pdomain-prep-for-pgdp, pdomain-ocr-cli, pdomain-ocr-simple-gui

---

## 1. Problem

`Page` in `pdomain-book-tools` mixes two concerns:

- **OCR content** — blocks, lines, words, bounding boxes, ground-truth text
- **Operational metadata** — image path, source, provenance, rotation history, failure flags

This conflation means every consumer of `Page` carries operational baggage (disk paths, OCR engine history, rotation records) even when it only needs the content tree. It also means there is no canonical suite-wide record for tracking a page through its full lifecycle — from raw image ingestion through preprocessing, OCR, labeling, and export.

`pdomain-prep-for-pgdp` makes this concrete: prep starts with no OCR at all. A page exists as an image-management record long before text is added. There is no good place to anchor that record today.

---

## 2. Goal

Split `Page` into two distinct objects with a clear layer boundary:

- **`Page`** (pdomain-book-tools) — pure in-memory OCR content tree. No knowledge of where the image came from or what processing history it has.
- **`PageRecord`** (pdomain-ops) — durable, versioned, event-sourced record of a page's full lifecycle. Owns all operational metadata, provenance, and change history.

---

## 3. Layer Boundary

```
pdomain-book-tools          pdomain-ops (depends on book-tools)
─────────────────           ──────────────────────────────────
Page                        PageRecord
  page_id: UUID  ← stable identity (same UUID on both sides)
  width, height               page_id: UUID
                              page_index  ← positional/ordering; lives here only
  blocks / lines / words      image_path
  bboxes                      source
  image_blob_hash (ref)       ocr_failed
  thumbnail_blob_hash (ref)
  _image_array (cache)
  _thumbnail_array (cache)
  name (display label)        provenance: ProvenanceGraph
  review                      provenance_summary
  gt_orphans (GtOrphans)      changelog: list[PageChangeEntry]

OCRProvenance               PageAggregate (eventsourcing wrapper)
  (stays here — OCR           BlobStore
   engines construct it)
```

`Page.page_id == PageRecord.page_id == PageAggregate.aggregate_id` — the same UUID
on all three.

**This identifies the physical page entity** (e.g. "page 42 of this book"), not a
specific version of its content. Multiple historical `Page` states (post-OCR,
post-GT, post-labeler, post-proofread) all share the same `page_id`.

| Want | How |
|---|---|
| Current state | Load aggregate → replay to head → current `Page` |
| State at point N | Load aggregate → replay to event N → `Page` at that version |
| Entity lookup | `page_id` |
| Version lookup | eventsourcing event sequence number |

`page_index` is a positional label for display ordering only — never used as a
lookup key.

### Branching vs. linear event store

Eventsourcing stores events in a **linear sequence** per aggregate. Dead branches
(§5) do not create separate aggregates or event forks — branching lives entirely
inside the `ProvenanceGraph` data carried by events. When a step is redone, a new
event fires with an updated `ProvenanceGraph` that records the superseded path as
a `DeadBranch`. The eventsourcing event stream stays linear; the graph inside it
is the branching mechanism.

`Page` is an in-memory object. Its content is persisted as a serialized JSON blob
in the blob store, referenced by `OcrCompleted.blob_refs`. There is no separate
sidecar file per page — `UserPageEnvelope` is retired. The event store + blob
store together form the complete persistence layer (see §9).

---

## 4. Page (after split)

### Fields removed from `Page`

| Field | Destination |
|---|---|
| `image_path` | `PageRecord` |
| `source` / `page_source` | `PageRecord` |
| `ocr_failed` | `PageRecord` |
| `ocr_provenance` | `PageRecord.provenance` (DAG node) |
| `provenance_live_ocr` | `PageRecord.provenance` (DAG node config) |
| `provenance_saved_ocr` | `PageRecord.provenance` (DAG node config) |
| `provenance_saved` | `PageRecord.provenance` (DAG node config) |
| `rotation_applied` | `PageRecord` (see §6 rotation model) |
| `original_ocr_tool_text` | `OcrCompleted` event config — snapshot of raw OCR text at ingestion |
| `original_ground_truth_text` | `GtMapped` event config — snapshot of GT text at import time |
| `unmatched_ground_truth_lines` | Replaced by `gt_orphans: GtOrphans` (see below) |

### Fields kept on `Page`

`page_id` (UUID, assigned at `ImageIngested`), `width`, `height`,
blocks/items, `bounding_box`, `page_labels`, `gt_orphans`, `name`, `review`.

`page_index` is removed from `Page` — ordering is `PageRecord`'s concern.

`image_array` (the old `InitVar`) is removed as a public field.

### Image and thumbnail lazy-load

```python
# persistent blob store references (serialized with Page)
image_blob_hash: str | None = None        # full upright image in blob store
thumbnail_blob_hash: str | None = None    # small display thumbnail in blob store

# in-memory caches — not serialized, not part of page_id or to_dict()
_image_array: ndarray | None             # populated on first get_image() call
_thumbnail_array: ndarray | None         # populated on first get_thumbnail() call

def get_image(self, blob_store: BlobStore) -> ndarray | None:
    if self._image_array is None and self.image_blob_hash:
        self._image_array = decode_png(blob_store.read(self.image_blob_hash))
    return self._image_array

def get_thumbnail(self, blob_store: BlobStore) -> ndarray | None:
    if self._thumbnail_array is None and self.thumbnail_blob_hash:
        self._thumbnail_array = decode_png(blob_store.read(self.thumbnail_blob_hash))
    return self._thumbnail_array
```

**Thumbnail generation**: produced at `ImageIngested` / `ImagePreprocessed` (whichever
is first in the pipeline), stored as an optimized PNG blob. Extended to all pages
in all pipelines — not just prep. A 400-page book load retrieves only thumbnails
for display; full images are fetched only when a page is opened for editing.

**Retires `cached_images: CachedImageSet`** on labeler-spa's `PageRecord` — blob
store refs replace the old path-based thumbnail cache.

### `GtOrphans`

GT entries that could not be matched to any OCR word/line/block during `GtMapped`.
Preserved on `Page` so the labeler can surface them to the human reviewer.
Pages with no GT never have a `GtMapped` event; `gt_orphans` remains `None`.

```python
@dataclass
class GtOrphans:
    words: list[...]        # GT words with no OCR word match
    lines: list[...]        # GT lines with no OCR line match
    paragraphs: list[...]   # GT paragraphs with no block match
    page: list[str]         # page-level GT content that could not be placed
```

`unmatched_ground_truth_lines` is removed; `gt_orphans.lines` is its replacement.

### `image_array`

Remains optional (`ndarray | None`). When present, it holds the image **already in upright orientation** — rotation was applied at ingestion time (best-of-4 OCR selection), not recorded as a field. Consumers that need bbox-to-pixel mapping use `image_array` directly; no rotation correction needed.

---

## 5. ProvenanceGraph

Each processing step is a node in a DAG. The graph records the full lineage of how a page was produced and what was done to it.

```python
class ProvenanceNode(BaseModel):
    id: str                               # UUID or deterministic slug
    source: str                           # "ingest", "threshold", "ocr", "layout",
                                          #   "reorganize", "labeler", "proofread",
                                          #   "export", …
    tool: str | None = None               # "doctr", "labeler-spa", "prep-for-pgdp", …
    tool_version: str | None = None       # "0.15.2"
    config: dict[str, Any] | None = None  # model, model_version, thresholds, params —
                                          #   all step-specific data lives here
    timestamp: datetime | None = None
    input_hash: str | None = None         # hash of inputs (image bytes, parent outputs)
    output_hash: str | None = None        # hash of this step's output; None for LLMs
    blob_refs: list[str] = []             # SHA256 hashes of blobs produced/consumed
    extra: dict[str, Any] | None = None
    parent_ids: list[str] = []            # DAG edges — 0=root, 1=linear, 2+=merge

class DeadBranch(BaseModel):
    tip_id: str                           # head of the superseded path
    forked_from_id: str                   # where it diverged from active path
    superseded_at: datetime
    retain_until: datetime                # eligible for pruning after this

class ProvenanceGraph(BaseModel):
    nodes: dict[str, ProvenanceNode]      # id → node
    head_id: str                          # active tip
    history: list[str]                    # ordered list of head_id values over time
    dead_branches: list[DeadBranch] = []  # superseded paths awaiting pruning
```

### Example: prep → OCR → labeler

```
ingest_node    {source="ingest",    tool="prep-for-pgdp",  parents=[]}
thresh_node    {source="threshold", tool="prep-for-pgdp",  parents=["ingest_node"]}
layout_node    {source="layout",    tool="layout-model",   parents=["thresh_node"]}
ocr_node       {source="ocr",       tool="doctr",          parents=["thresh_node"]}
                 config={"model":"db_resnet50","model_version":"v2","threshold":0.3}
reorg_node     {source="reorganize",               parents=["layout_node","ocr_node"]}
label_node     {source="labeler",   tool="labeler-spa",    parents=["reorg_node"]}
                                                            ← head
```

`reorg_node` has two parents — this is where the DAG (not just a linked list) is required.

### Dead branches

When a step is redone (e.g. re-OCR with a different model), a new node branches from the fork point. The old path tip is recorded in `dead_branches` with a `retain_until` timestamp (default: 30 days). On pruning, dead nodes are removed from `nodes` and their `blob_refs` are orphan-checked — blobs with no remaining refs are deleted from the blob store.

---

## 6. Rotation model

Rotation is determined at OCR ingestion by running four passes (0°/90°/180°/270°) and selecting the best result. The `Page` object produced by this process has `image_array` already in the chosen orientation. `rotation_applied` is removed from `Page`.

`PageRecord` records the rotation history:

```python
class RotationSource(StrEnum):
    NONE   = "none"    # original disk orientation
    AUTO   = "auto"    # best-of-4 OCR selection
    MANUAL = "manual"  # user-applied

# On PageRecord:
rotation_degrees: int = 0
rotation_source: RotationSource = RotationSource.NONE
```

`rotation_degrees` is the total cumulative rotation from the original disk image. A subsequent user rotation adds to it and sets `rotation_source = MANUAL`.

---

## 7. PageRecord

```python
class PageRecord(BaseModel):
    page_id: UUID                              # = PageAggregate.aggregate_id; stable identity
    page_index: int                            # positional within document; display only
    image_path: Path | None = None
    source: str = "ocr"                        # "raw", "ocr", "saved", …
    ocr_failed: bool = False
    rotation_degrees: int = 0
    rotation_source: RotationSource = RotationSource.NONE
    provenance: ProvenanceGraph | None = None
    provenance_summary: str | None = None      # assembled at payload-build time by
                                               # pdomain_ops.pages.build_provenance_summary();
                                               # not auto-updated on graph mutation
    changelog: list[PageChangeEntry] = []
```

`page_id` is assigned once at `ImageIngested` and never changes. All cross-references
between components (event store, blob store, in-memory `PageState`) use `page_id`.
`page_index` may change if pages are reordered; it is never used as a lookup key.

`provenance_summary` is a human-readable one-liner assembled by walking the provenance graph. It replaces the `_build_provenance_summary` function in labeler-spa's `api/pages.py`.

### Changelog — "git for pages"

```python
class PageChangeEntry(BaseModel):
    provenance_node_id: str            # which step in the DAG caused this change
    timestamp: datetime | None = None
    changes: list[dict[str, Any]]      # typed change events (flexible dict for now;
                                       #   discriminated union when proofreading ships)
```

Example change events:
```python
{"type": "word_text",   "word_id": "b0l2w3", "from": "thr",    "to": "the"}
{"type": "block_role",  "block_id": "b1",     "from": "body",   "to": "footnote"}
{"type": "line_split",  "line_id": "b0l4",    "at": 3}
```

The changelog entries are authored by the same steps that create provenance nodes. Each labeler save or proofreading correction appends a `PageChangeEntry` referencing its `ProvenanceNode.id`. Walking the changelog from beginning gives the full edit history; walking from any entry gives the delta from that point — enabling diff between any two versions.

---

## 8. PageAggregate (eventsourcing)

`PageRecord` is a plain Pydantic model — zero eventsourcing imports. `PageAggregate` is a separate file that wraps it and provides the event store interface.

```python
# pdomain_ops/page_aggregate.py
from eventsourcing.domain import Aggregate
from pdomain_ops.pages import PageRecord

class PageAggregate(Aggregate):

    class ImageIngested(Aggregate.Event):
        record: PageRecord

    class ImagePreprocessed(Aggregate.Event):
        provenance_node: ProvenanceNode
        blob_refs: list[str]

    class OcrCompleted(Aggregate.Event):
        provenance_node: ProvenanceNode
        blob_refs: list[str]           # hashes: [page_content_hash, source_image_hash, ...]
                                       # page_content_hash → Page JSON in blob store
                                       # config holds original_ocr_text snapshot

    class GtMapped(Aggregate.Event):
        provenance_node: ProvenanceNode   # config holds original_gt_text snapshot
        # Page content updated in-place with GT matches; orphans stored in gt_orphans
        # Pages with no GT simply never receive this event

    class LabelerEdited(Aggregate.Event):
        provenance_node: ProvenanceNode
        changes: list[dict[str, Any]]

    class ProofreadingCorrected(Aggregate.Event):   # future
        provenance_node: ProvenanceNode
        changes: list[dict[str, Any]]

    class Exported(Aggregate.Event):
        provenance_node: ProvenanceNode

    def __init__(self, record: PageRecord) -> None:
        self._record = record

    @property
    def record(self) -> PageRecord:
        return self._record

    def apply(self, event: ImageIngested) -> None:
        self._record = event.record

    def apply(self, event: OcrCompleted) -> None:
        # update provenance graph, set ocr_failed=False, etc.
        ...
```

Consumers that only need the current state import `PageRecord` from `pdomain_ops.pages`.
Only the labeler, prep pipeline, and future proofreading tools import `PageAggregate`.

### Persistence and snapshotting

`eventsourcing[sqlite]` stores all events in `<project>/.pd-pages/events.db`,
including `OcrCompleted.page_content` (serialized Page JSON). Image bytes never
enter the event store — only blob hashes do.

**Snapshotting is required.** A 400-page book processed through ingest →
threshold → layout → OCR → GT mapping → labeler → proofread → export accumulates
many events per page. Replaying all events on every load is unacceptable.

Eventsourcing supports snapshots natively — a snapshot captures the full aggregate
state (current `PageRecord` + current serialized `Page`) at a point in time.
On load: find the latest snapshot, then replay only events that occurred after it.

**Snapshot policy:**
- After `OcrCompleted` — first stable content state
- After `GtMapped` — GT baseline established
- After each labeler session close (`LabelerEdited` batch ends)
- After `Exported` — final state
- Additionally: every 20 events as a safety net

**Migration to Postgres:** swap `PERSISTENCE_MODULE=eventsourcing.sqlite` →
`eventsourcing.postgres` via environment variable. No code changes required.

---

## 9. Blob store

Content-addressed storage for **all large content**: images, thumbnails, and
serialized Page JSON. The event store stays metadata + hashes only — this is
essential for a 400-page book where Page JSON alone would be 40-80MB inline.

`UserPageEnvelope` is retired — no per-page JSON sidecar files.

```
<project>/.pd-pages/
    events.db              ← eventsourcing SQLite: events + snapshots (metadata + hashes only)
    blobs/
        <sha256>           ← any large content: PNG images, thumbnails, Page JSON
        <sha256>
        …
```

The blob store is **content-type agnostic** — raw bytes keyed by SHA256. Callers
decide what to write and how to pre-process it:
- Images/thumbnails: caller runs `oxipng.optimize_from_memory()` first
- Page JSON: caller calls `page.to_dict()` → UTF-8 bytes, stored as-is

### BlobStore interface

```python
class BlobStore:
    def __init__(self, project_dir: Path) -> None: ...
    def write(self, data: bytes) -> str:
        """SHA256 data, store if new. Returns hash. Caller pre-processes."""
    def read(self, hash: str) -> bytes: ...
    def exists(self, hash: str) -> bool: ...
    def prune_orphans(self, live_refs: set[str]) -> list[str]:
        """Delete blobs not in live_refs. Returns deleted hashes."""
```

### Write path (image or thumbnail)

1. `oxipng.optimize_from_memory(image_bytes)` → optimized PNG bytes
2. `BlobStore.write(optimized)` → hash stored in `ProvenanceNode.blob_refs`
   and in `Page.image_blob_hash` / `Page.thumbnail_blob_hash`

### Write path (Page JSON)

1. `json.dumps(page.to_dict()).encode()` → UTF-8 bytes
2. `BlobStore.write(bytes)` → hash stored in `OcrCompleted.blob_refs[0]`

### Loading a page (lifecycle consumers)

```
1. Get PageAggregate by page_id (find latest snapshot first)
2. Replay events after snapshot → current PageRecord state
3. Read page_content_hash from OcrCompleted.blob_refs[0]
4. BlobStore.read(hash) → JSON bytes → Page.from_dict()
5. Page.image_blob_hash / thumbnail_blob_hash populated; images lazy-loaded
```

For display of a 400-page book: load all 400 aggregates (snapshot + few events
each) → thumbnails fetched lazily as pages scroll into view. Full images only
fetched when a page is opened for editing.

### Deduplication

Same content → same hash → file already exists → write skipped. Thumbnails and
full images deduplicated independently. Four rotation candidates that are
near-identical after oxipng optimization share blobs automatically.

### Pruning

When a dead branch's `retain_until` passes:
1. Collect all `blob_refs` from dead branch nodes
2. Check each hash for remaining references in live nodes
3. Delete blobs with no live references
4. Remove dead nodes from `ProvenanceGraph.nodes`

---

## 10. Consumer taxonomy

Two tiers of consumers. The split is on event store + blob store usage, not on
`PageRecord` / `ProvenanceGraph` — those are universal.

### End-state producers (CLI, simple-gui)

Run a pipeline once, produce a `PagePayload` snapshot. No event store, no blob
store, no `PageAggregate`. Images remain as file-system paths.

Pipeline (CLI example):
```
load image
  → OcrCompleted     provenance node (tool=doctr, config={model=...})
  → LayoutDetected   provenance node (tool=layout-model)
  → Reorganized      provenance node (parents=[ocr_node, layout_node])  ← DAG merge
```
`ProvenanceGraph` built in memory, bundled into `PagePayload`, written to JSON.

A `PagePayload` produced by CLI can later be **imported** by the labeler —
fire `OcrCompleted` from the payload's provenance + content to start a
lifecycle in the event store.

### Lifecycle consumers (labeler, prep)

Full event store + blob store. Support replay, versioning, dead branches,
proofreading, export. Use `PageAggregate` + `ProjectAggregate`.

---

## 11. ProjectRecord and ProjectAggregate

A **project** is the top-level organizing unit — a collection of pages
processed together (a book, a batch, a job). All events for a project's pages
live in one `events.db`.

```python
class ProjectRecord(BaseModel):
    project_id: UUID
    name: str
    page_ids: list[UUID] = []     # ordered; index = page_index
    source_dir: Path | None = None
    created_at: datetime | None = None

class ProjectAggregate(Aggregate):
    class ProjectCreated(Aggregate.Event):
        record: ProjectRecord
    class PageAdded(Aggregate.Event):
        page_id: UUID
        page_index: int
    class PageReordered(Aggregate.Event):
        page_ids: list[UUID]     # full new order
    class ProjectExported(Aggregate.Event):
        provenance_node: ProvenanceNode
```

`page_index` lives here — it is the project's opinion of page order, not a
property of the page itself. `PageRecord.page_index` is a cached copy for
convenience; `ProjectRecord.page_ids` is authoritative.

### Per-project storage

```
<project>/.pd-pages/
    events.db     ← events for the ProjectAggregate AND all PageAggregates
                  ← all aggregate_ids coexist in one SQLite file
    blobs/        ← all large content for all pages in this project
```

One portable directory = one complete project. Copy or archive the directory
to move a project between machines.

---

## 12. PagePayload — portable serialization

`PagePayload` is the universal portable format for a page — used for:
- CLI / simple-gui JSON output
- API responses (labeler frontend, simple-gui frontend)
- Cross-service transfer (import into labeler from CLI output)

```python
class PagePayload(BaseModel):
    """Assembled at write/response time. Never stored directly.
    The event store + blob store are the durable form for lifecycle consumers."""
    page_id: UUID
    page_index: int
    record: PageRecord           # metadata, provenance, changelog
    content: dict[str, Any]      # Page.to_dict() — blocks/lines/words/bboxes
    image_url: str | None = None # for API responses; None in file exports
    dims: tuple[int, int] | None = None  # (width, height) for canvas scaling
```

### End-state write (CLI)

```python
record = PageRecord(page_id=page.page_id, source="ocr",
                    provenance=graph, ...)
payload = PagePayload(page_id=page.page_id, page_index=i,
                      record=record, content=page.to_dict())
Path(f"page_{i:04d}.json").write_text(payload.model_dump_json(indent=2))
```

### Import into labeler

```python
payload = PagePayload.model_validate_json(Path("page_0000.json").read_text())
# Fire OcrCompleted from payload — page enters the event store lifecycle
aggregate = PageAggregate(record=payload.record)
aggregate.ocr_completed(
    provenance_node=payload.record.provenance.nodes[payload.record.provenance.head_id],
    page_content_hash=blob_store.write(json.dumps(payload.content).encode()),
)
```

---

## 13. Dependency graph

```
pdomain-book-tools          (no pd-* deps)
    Page, GtOrphans, BlobStoreProtocol
    OCRProvenance, Block, Line, Word

pdomain-ops                 (depends on pdomain-book-tools)
    pdomain_ops.pages        ← universal; all consumers import this
      PageRecord, ProjectRecord
      ProvenanceGraph, ProvenanceNode, DeadBranch
      RotationSource, PageChangeEntry
      PagePayload
    pdomain_ops.page_aggregate  ← lifecycle consumers only
      PageAggregate, ProjectAggregate
    pdomain_ops.blob_store   ← lifecycle consumers only
      BlobStore

pdomain-ocr-labeler-spa     (depends on pdomain-ops + pdomain-book-tools)
    imports pdomain_ops.pages + page_aggregate + blob_store
    removes local PageRecord + RotationSource definitions
    retires UserPageEnvelope → uses PagePayload for API responses

pdomain-prep-for-pgdp       (depends on pdomain-ops + pdomain-book-tools)
    imports pdomain_ops.pages + page_aggregate + blob_store

pdomain-ocr-cli             (depends on pdomain-ops + pdomain-book-tools)
    imports pdomain_ops.pages only (PageRecord, ProvenanceGraph, PagePayload)
    NO page_aggregate, NO blob_store — end-state producer

pdomain-ocr-simple-gui      (depends on pdomain-ops + pdomain-book-tools)
    imports pdomain_ops.pages only — end-state producer
```

---

## 14. Migration strategy

This is a breaking change to `Page`'s public API. All consumers must update in a coordinated release.

**Order:**

1. **pdomain-book-tools** — remove operational fields from `Page`, cut a new minor release
2. **pdomain-ops** — add `PageRecord`, `ProvenanceGraph`, `PageAggregate`, `BlobStore`; bump pdomain-book-tools floor pin; cut a release
3. **pdomain-ocr-labeler-spa** — replace local `PageRecord` + `RotationSource` with imports from pdomain-ops; retire `UserPageEnvelope` (replace with `PagePayload` for API responses + event store + blob store load path); update `PageState` to link by `page_id`; update all sites reading stripped fields off `Page`
4. **pdomain-prep-for-pgdp** — add pdomain-ops dep; thread `PageRecord` + `ProjectRecord` through pipeline from ingest
5. **pdomain-ocr-cli** — update to new `Page`, import `pdomain_ops.pages` only, build `ProvenanceGraph` across pipeline steps (OCR→Layout→Reorg DAG), emit `PagePayload` JSON
6. **pdomain-ocr-simple-gui** — same as CLI; `PagePayload` in API response
6. **pd-ocr-labeler** (legacy NiceGUI) — skip; being retired

At each step, `make ci` must pass before the next repo is touched.

---

## 15. Out of scope

- Postgres / managed-adapter persistence (deferred per D-042)
- `bup`-style chunk deduplication for blob storage (future optimization)
- Typed discriminated union for `PageChangeEntry.changes` (deferred until proofreading ships)
- LLM provenance nodes (non-deterministic; noted in design but not implemented)
- `pd-png-optimizer` (on indefinite hold; `oxipng-pybind` used instead)
