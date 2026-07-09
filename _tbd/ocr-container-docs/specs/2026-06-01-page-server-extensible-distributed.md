# Page server v2 — extensible record + distributable server model

**Date:** 2026-06-01
**Status:** Approved (CT decisions 2026-06-01) — supersedes the composition/Phase-A
recommendations in `2026-06-01-page-split-downstream-rollout.md`
**Base:** `2026-05-31-page-record-ops-design.md` (Plan 2 shipped as ops 0.6.0)

## CT decisions (2026-06-01)

1. **One canonical page model, extensible** — not per-app duplicate `PageRecord`s,
   and **not** a literal fold-in of every app field. The ops `PageRecord` keeps a
   clean lifecycle/provenance/rotation core plus an **open `extensions` slot** for
   namespaced app state. ops imports **no** app-domain types.
2. **Full event-store + BlobStore adoption now, greenfield** — apps drop bespoke
   persistence and use the event store. **No data migration** (no legacy data to
   preserve).
3. **Stub the future server model as interfaces** in pdomain-ops, designed so the
   store can **shard and distribute** later without touching consumers — mirroring
   the existing `StageDispatcher`/`LongJobRunner` Protocol + Local-impl pattern.

## 1. Extensible PageRecord (ops 0.7.0)

Add one field to `pdomain_ops.pages.PageRecord`:

```python
extensions: dict[str, dict[str, Any]] = Field(default_factory=dict)
# namespaced, JSON-able app state. e.g.
#   extensions["labeler"] = {"page_number": 42, "page_source": "ocr",
#                            "cached_images": {...}, "payload_error": None}
#   extensions["prep"]    = {"idx0": 42, "splits": [...], "page_type": "normal",
#                            "config_overrides": {...}, "outputs": [...]}
```

- It serializes for free through the existing `_PageRecordTranscoding`
  (`model_dump(mode="json")`/`model_validate`) — no new transcoding.
- Apps define their own typed models for their namespace and
  `model_dump()`/`model_validate()` in/out of `extensions[ns]`. ops never imports
  `PageType`, `PageSplit`, `CachedImageSet`, etc.
- `cli`/`simple-gui` ignore `extensions` entirely (end-state producers).
- Optional ergonomics (nice-to-have, not required): a tiny generic helper
  `get_extension(record, ns, Model)` / `set_extension(record, ns, model)` that
  wraps the dict round-trip with a caller-supplied pydantic type.

Everything else in `PageRecord` is unchanged from 0.6.0. This is an **additive**
field → ops 0.7.0 (minor).

## 2. Server model — Protocols + Local impls (ops 0.7.0)

New module `pdomain_ops/page_server.py` (lifecycle-consumer surface; NOT re-exported
at top level, like `blob_store`/`page_aggregate`). Three Protocols, each with a
Local implementation now and a documented seam for sharded/remote later.

```python
from typing import Protocol, runtime_checkable
from uuid import UUID

@runtime_checkable
class BlobBackend(Protocol):
    def write(self, data: bytes) -> str: ...
    def read(self, hash: str) -> bytes: ...
    def exists(self, hash: str) -> bool: ...
    def prune_orphans(self, live_refs: set[str]) -> list[str]: ...
# pdomain_ops.blob_store.BlobStore already satisfies this verbatim (local impl).

@runtime_checkable
class PageStore(Protocol):
    def save_page(self, aggregate: PageAggregate) -> None: ...
    def get_page(self, page_id: UUID) -> PageAggregate: ...
    def save_project(self, aggregate: ProjectAggregate) -> None: ...
    def get_project(self, project_id: UUID) -> ProjectAggregate: ...

@runtime_checkable
class ShardRouter(Protocol):
    def shard_for(self, project_id: UUID) -> str: ...   # PROJECT is the shard unit
    def shards(self) -> list[str]: ...
```

**Shard by project, not by page.** Per base-spec §11 a project is already a
self-contained store (one `events.db` + one `blobs/` dir = one portable project).
That is the natural distribution unit: a whole book/job lives on one shard, so all
of a project's pages — including split families — stay co-located. Pages are always
accessed *within* their project's store, so `PageStore` is project-scoped and the
router keys on `project_id`. This keeps every intra-project query (list pages, list
a parent's split children, reorder) single-shard; distribution spreads *projects*
across shards/nodes, never individual pages.

Local implementations:

```python
class LocalPageStore:
    """Single-process event store backed by one PagesApplication (sqlite/POPO)."""
    def __init__(self, app: PagesApplication) -> None: ...
    # save_page -> app.save(agg); get_page -> app.repository.get(page_id); etc.

class SingleShard:
    """Trivial router: everything maps to one shard. The no-op default."""
    def shard_for(self, key: UUID) -> str: return "local"
    def shards(self) -> list[str]: return ["local"]
```

Distribution seam (stubbed, implementable later — provide the skeletons now):

```python
class ShardedPageStore:
    """Routes each page/project to a per-shard PageStore via a ShardRouter.
    Constructed with a router + a {shard_id: PageStore} map (or a factory).
    Concrete composition; the only 'distribution' it lacks is cross-process
    transport — that arrives via RemotePageStore."""
    def __init__(self, router: ShardRouter, stores: dict[str, PageStore]) -> None: ...

class RemotePageStore:
    """PageStore Protocol stub for a networked shard (HTTP/gRPC to a page-server
    process). Methods raise NotImplementedError until the transport ships.
    Present so consumers can depend on PageStore and swap this in later."""
    # raises NotImplementedError in every method for now
```

Optional thin facade composing the three (the "page server" entry point):

```python
class PageService:
    """Local default composition of the page server model. Swap in
    ShardedPageStore / RemotePageStore / an S3 BlobBackend via the Protocols
    without changing call sites."""
    def __init__(self, store: PageStore, blobs: BlobBackend,
                 router: ShardRouter | None = None) -> None: ...
    # high-level helpers consumers actually call (load_page -> Page+content, etc.)
```

**Why this satisfies "shard and distribute as needed":** consumers depend only on
`PageStore`/`BlobBackend`/`ShardRouter`. `LocalPageStore`+`SingleShard`+`BlobStore`
is the default. Sharding = supply a real `ShardRouter` + `ShardedPageStore`.
Distribution = supply `RemotePageStore` / an S3-backed `BlobBackend`. No consumer
change. Postgres is still just an eventsourcing `PERSISTENCE_MODULE` env swap.

## 3. Downstream adoption (revises Plans 3/4/5)

Greenfield (no migration). Apps become lifecycle consumers of the server model:

- **labeler-spa (Plan 3):** delete local `PageRecord`/`RotationSource`/
  `UserPageEnvelope`; persist via `PageStore` + `BlobStore`; store labeler
  view-state in `extensions["labeler"]`; API responses assemble from ops
  `PagePayload` + the labeler extension; `build_provenance_summary` from ops.
- **prep-for-pgdp (Plan 4):** delete local `PageRecord`; create page lifecycles at
  ingest via `PageStore` (`ImageIngested`); store prep state in `extensions["prep"]`;
  images/thumbnails via `BlobStore`; `ProjectRecord` ordering.

  **Page splits (handled cleanly):** a split turns one parent page into N sibling
  child pages. Each child is a **first-class page** — its own `page_id` and its own
  `PageAggregate`, created by a split event on the parent; the cropped child image
  goes to `BlobStore`. The split linkage (`parent_page_id` → parent's `page_id`,
  `source_crop_bbox`, `split_index`, `split_at_stage`, `split_suffix`,
  `reading_order`) lives in a prep-owned typed model serialized into
  `extensions["prep"]` — **including prep's all-or-none validator**; ops never sees
  these fields. Because children share the parent's **project**, they live in the
  same project store/shard (locality preserved). Global order, with children spliced
  in at `reading_order`, lives in `ProjectRecord.page_ids` via the `ProjectAggregate`.
  *Gap to close in ops 0.7.0:* split-replaces-parent reorder semantics may want a
  `ProjectAggregate.remove_page` / `replace_page` event (currently only
  `PageAdded`/`PageReordered` exist) — add it.
- **cli + simple-gui (Plan 5):** unchanged from the existing Plan 5 — core model
  only, ignore `extensions`, no store.

All pin `pdomain-ops>=0.7.0`.

## 4. Build order

1. **ops 0.7.0** — `extensions` field + `page_server.py` (Protocols + Local impls +
   sharded/remote skeletons) + tests; release.
2. Rewrite Plans 3/4 (greenfield, event-store, extensions) + keep Plan 5.
3. Execute Plan 5, then Plans 3/4.

## 5. Out of scope (unchanged)

Real sharded/remote transport implementation, Postgres wiring beyond the env swap,
auth — all later. The interfaces exist now; impls are stubs.
