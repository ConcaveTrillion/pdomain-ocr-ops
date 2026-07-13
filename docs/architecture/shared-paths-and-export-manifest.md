---
Status: built
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-13
Kind: architecture
---

# Shared paths and DocTR export manifests

## Agent Index

- **Kind:** architecture
- **Status:** built
- **Read when:** changing suite path discovery or the shared DocTR export format.
- **Search terms:** shared paths, shared-paths.json, DocTR export manifest, atomic write.

## Shared-path registry

Suite applications publish and resolve named filesystem paths through
`shared-paths.json` in the suite data directory. Updates use a bounded file lock
and an atomic replacement, so concurrent publishers do not expose partial JSON.
The public suite package exports the path helper, publish and resolve functions,
and the lock-timeout exception.

Publishing the same key is last-writer-wins. Resolving an absent key, missing
registry, or corrupt registry returns `None`. Resolution returns a published
path even when the target no longer exists; the consumer decides whether a
stale path is usable. Lock timeout precedence is the explicit argument, then
`PDOMAIN_SHARED_PATHS_LOCK_TIMEOUT`, then the five-second default.

## Export manifest

The shared Pydantic models describe DocTR export metadata and task statistics.
Manifest reads validate JSON into those models. Writes use a temporary file and
`os.replace` so consumers see either the old complete manifest or the new one.
The schema emitter includes the public manifest models.

The JSON key `schema` maps to the Python field `schema_id`. Unknown model fields
are ignored for forward compatibility. A manifest version greater than 1 is
parsed with a warning rather than rejected; callers choose whether that newer
version is acceptable. A missing manifest returns `None`, while corrupt JSON or
model data raises `ValueError`.

## Evidence

- **Code:** `pdomain_ops/suite/shared_paths.py`, `pdomain_ops/suite/paths.py`,
  `pdomain_ops/suite/__init__.py`, `pdomain_ops/schemas/doctr_export.py`,
  `pdomain_ops/schemas/emit.py`
- **Tests:** `tests/suite/test_shared_paths.py`,
  `tests/suite/test_paths_shared_paths_json.py`,
  `tests/test_schemas_doctr_export.py`, `tests/test_schemas_emit.py`,
  `tests/test_public_surface.py`
- **Commits:** `4111e95`, `808abf6`, `4898f33`, `36eab34`, `603f275`,
  `d7209ab`, `b568838`, `60ef0a4`, `676fe90`
- **Verified:** 2026-07-13; the focused suite passed 44 tests.
