---
Status: built
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-13
Kind: architecture
---

# Page lifecycle and storage

## Agent Index

- **Kind:** architecture
- **Status:** built
- **Read when:** changing page records, aggregate events, extension persistence,
  blob storage, sharding, or page-store adapters.
- **Search terms:** PageRecord, PageAggregate, ProjectAggregate, PageStore,
  BlobBackend, extensions, event sourcing, sharding.

## Records and aggregate ownership

`PageRecord` contains durable operational metadata for one physical page. Its
`page_id` is also the `PageAggregate` identifier. `ProjectRecord.page_ids`
defines project page order. OCR content models remain outside this lifecycle
layer.

Application-specific state lives in `PageRecord.extensions` under namespaced,
JSON-serializable dictionaries. The typed extension helpers validate a
namespace against a Pydantic model. Before first persistence, callers can use
the free `set_extension()` helper. After persistence, callers must use
`PageAggregate.set_extension()` so an `ExtensionSet` event captures the change.
Direct mutation after save is lost on replay.

`PageAggregate` records ingest, preprocessing, OCR, ground-truth mapping,
labeler edits, export, rotation, and extension changes. `ProjectAggregate`
records project creation, page membership, ordering, and export. Event
arguments become event-owned data; callers must not mutate them between the
command and save. The aggregate copies mutable inputs where the implementation
needs replay isolation.

`PagesApplication` registers Pydantic transcodings and snapshots page and
project aggregates every 20 events. Its default persistence is in-memory. A
caller can select the shipped eventsourcing SQLite persistence through the
application environment.

## Storage and routing seams

`BlobBackend`, `PageStore`, and `ShardRouter` are runtime-checkable protocols.
`BlobStore` provides local content-addressed files. `LocalPageStore` adapts one
`PagesApplication`, and `SingleShard` provides the no-routing default.
`ShardedPageStore` routes a project and its pages to an in-process map of
stores, keeping a project on one shard.

These seams allow consumers to depend on storage behavior without depending on
a network transport. `RemotePageStore` is an explicit stub: every operation
raises `NotImplementedError`. No HTTP, gRPC, managed database, or networked
blob backend ships in this repository. `ShardedPageStore` composes local store
objects; it is not a distributed service.

## Evidence

- **Code:** `pdomain_ops/pages/records.py`,
  `pdomain_ops/pages/extensions.py`, `pdomain_ops/page_aggregate.py`,
  `pdomain_ops/page_server.py`, `pdomain_ops/blob_store.py`
- **Tests:** `tests/test_page_aggregate.py`,
  `tests/test_extension_mutation.py`, `tests/test_page_server.py`,
  `tests/test_blob_store.py`, `tests/test_lifecycle_integration.py`
- **Salvaged sources:**
  `_tbd/ocr-container-docs/specs/2026-05-31-page-record-ops-design.md`,
  `_tbd/ocr-container-docs/specs/2026-06-01-page-server-extensible-distributed.md`,
  `_tbd/ocr-container-docs/archive/plans/2026-06-01-page-record-ops-pdomain-ops.md`
- **Verified:** 2026-07-13 against the current code and focused tests above.
