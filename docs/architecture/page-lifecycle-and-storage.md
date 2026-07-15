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

The page lifecycle layer stores durable operational metadata for each physical
page in `PageRecord`. The record's `page_id` is also the `PageAggregate`
identifier. `ProjectRecord.page_ids` defines the page order within a project.
OCR content models remain outside this layer.

`PageRecord.extensions` stores application-specific state as namespaced,
JSON-serializable dictionaries. The typed extension helpers validate each
namespace against a Pydantic model. Callers can use the free `set_extension()`
helper before the first persistence. After persistence, they must use
`PageAggregate.set_extension()`. This method captures the change in an
`ExtensionSet` event. Replay loses any direct mutation made after a save.

`PageAggregate` records ingest, preprocessing, OCR, ground-truth mapping,
labeler edits, export, rotation, and extension changes. `ProjectAggregate`
records project creation, page membership, ordering, and export. Event
arguments become event-owned data. Callers must not mutate them between the
command and save. When replay isolation requires it, the aggregate copies
mutable inputs.

`PagesApplication` registers Pydantic transcodings. It snapshots page and
project aggregates every 20 events. Persistence is in-memory by default. A
caller can select the shipped eventsourcing SQLite persistence through the
application environment.

## Storage and routing seams

Storage and routing use the runtime-checkable `BlobBackend`, `PageStore`, and
`ShardRouter` protocols. `BlobStore` provides local content-addressed files.
`LocalPageStore` adapts one `PagesApplication`. `SingleShard` provides the
no-routing default. `ShardedPageStore` sends a project and its pages to an
in-process map of stores while keeping that project on one shard.

These protocols let consumers depend on storage behavior without depending on
a network transport. `RemotePageStore` is an explicit stub. Every operation
raises `NotImplementedError`. This repository ships no HTTP, gRPC, managed
database, or networked blob backend. `ShardedPageStore` composes local store
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
