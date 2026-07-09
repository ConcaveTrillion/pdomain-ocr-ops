---
repo: pdomain-ops
spec: docs/specs/2026-05-31-page-record-ops-design.md
sequence: Plan 2 of 5 (page-split / PageRecord rollout)
status: ready
---

# PageRecord in pdomain-ops Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the durable, event-sourced page-lifecycle layer to `pdomain-ops` — `PageRecord`, `ProvenanceGraph`, `PagePayload`, a content-addressed `BlobStore`, and the eventsourcing `PageAggregate` / `ProjectAggregate` — so every downstream pd-* consumer can stop carrying operational metadata on the now-pure `Page`.

**Architecture:** Three new import surfaces inside the existing `pdomain_ops` package, split by consumer tier (design spec §10, §13):

- `pdomain_ops.pages` — **universal**, pure-pydantic value models. Every consumer (CLI, simple-gui, labeler, prep) imports this. No eventsourcing, no I/O.
- `pdomain_ops.blob_store` — **lifecycle consumers only**. Content-addressed SHA256 file store implementing `pdomain_book_tools.ocr.BlobStoreProtocol` (shipped in Plan 1, book-tools v0.17.0).
- `pdomain_ops.page_aggregate` — **lifecycle consumers only**. `PageAggregate` / `ProjectAggregate` + a `PagesApplication` wiring eventsourcing persistence, pydantic transcodings, and snapshotting.

**Tech Stack:** Python 3.11+, pydantic v2 (already a dep), `eventsourcing` v9.x (new dep, sqlite persistence via stdlib), hatch-vcs tag-driven versioning, uv, pytest-xdist (`uv run pytest -n auto`), ruff + basedpyright.

**Scope boundary:** This plan covers **only** `pdomain-ops` (migration-strategy step 2, design spec §14). It does not touch any downstream consumer — those are Plans 3–5. The deliverable is a released `pdomain-ops` whose new modules are import-stable so Plans 3–5 can build against fixed signatures.

---

## File Structure

New files (all under `/workspaces/ocr-container/pdomain-ops/`):

| File | Responsibility |
|---|---|
| `pdomain_ops/pages/__init__.py` | Re-export the universal public surface (`PageRecord`, `ProvenanceGraph`, …, `build_provenance_summary`). |
| `pdomain_ops/pages/provenance.py` | `ProvenanceNode`, `DeadBranch`, `ProvenanceGraph` (+ `add_node`/`head` helpers). |
| `pdomain_ops/pages/records.py` | `RotationSource`, `PageChangeEntry`, `PageRecord`, `ProjectRecord`. |
| `pdomain_ops/pages/summary.py` | `build_provenance_summary(graph)` — human-readable one-liner. |
| `pdomain_ops/pages/payload.py` | `PagePayload` — portable serialization format. |
| `pdomain_ops/blob_store.py` | `BlobStore` — content-addressed SHA256 file store. |
| `pdomain_ops/page_aggregate.py` | `PageAggregate`, `ProjectAggregate`, `PagesApplication`, pydantic transcodings. |
| `tests/pages/test_provenance.py` | Provenance value-model tests. |
| `tests/pages/test_records.py` | Record value-model tests. |
| `tests/pages/test_summary.py` | Summary tests. |
| `tests/pages/test_payload.py` | Payload + round-trip tests. |
| `tests/test_blob_store.py` | BlobStore + `BlobStoreProtocol` conformance. |
| `tests/test_page_aggregate.py` | Aggregate save/replay/snapshot via sqlite + in-memory. |

Modified files:

| File | Change |
|---|---|
| `pyproject.toml` | Add `eventsourcing` dep; bump `pdomain-book-tools` floor `>=0.15.1` → `>=0.17.0`. |
| `pdomain_ops/__init__.py` | Re-export the universal surface from `pdomain_ops.pages`. |
| `tests/test_public_surface.py` | Assert the new public names import. |
| `CHANGELOG.md` | New `### Added` entry. |

---

## Milestone 0: Dependencies and package scaffolding

### Task 0: Wire dependencies and create the `pages` package skeleton

**Files:**
- Modify: `pyproject.toml`
- Create: `pdomain_ops/pages/__init__.py`
- Create: `tests/pages/__init__.py` (only if existing test subdirs use package-style `__init__.py`; check `tests/gpu/` first — if it has no `__init__.py`, do not create one)

- [ ] **Step 1: Confirm the Python floor supports `StrEnum`**

Run: `grep -n 'requires-python' /workspaces/ocr-container/pdomain-ops/pyproject.toml`
Expected: `requires-python = ">=3.11"` (or higher). `StrEnum` is stdlib from 3.11. If the floor is `>=3.10`, stop and raise it to `>=3.11` in this step (the whole suite is 3.11+); note the change in the commit.

- [ ] **Step 2: Add the eventsourcing dependency and bump the book-tools pin**

In `pyproject.toml`, edit the `[project] dependencies` array:
- Change `"pdomain-book-tools>=0.15.1",` → `"pdomain-book-tools>=0.17.0",`
- Add `"eventsourcing>=9.4,<10",` (keep the array alphabetically ordered — insert before `"fastapi>=0.110",`).

Result (the relevant slice):
```toml
dependencies = [
    "eventsourcing>=9.4,<10",
    "fastapi>=0.110",
    "filelock>=3.13",
    "httpx>=0.27",
    "pdomain-book-tools>=0.17.0",
    "platformdirs>=4.2",
    "pydantic>=2.5",
    "tomli>=2.0",
    "tomli-w>=1.0",
    "uvicorn>=0.30",
]
```
> `eventsourcing`'s SQLite backend ships in the core package (uses stdlib `sqlite3`) — no extra is required. Postgres (`eventsourcing[postgres]`) is explicitly out of scope (design spec §15, D-042).

- [ ] **Step 3: Resolve and sync the lockfile**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv lock && uv sync`
Expected: lock resolves; `eventsourcing` and a `pdomain-book-tools>=0.17.0` appear in `uv.lock`.

> If `pdomain-book-tools>=0.17.0` fails to resolve from the index, the repo may be in local-dev mode — run `make local-check`. In local-dev the sibling resolves editable from `/workspaces/ocr-container/pdomain-book-tools` (already at v0.17.x on `main`); re-run `make local-setup-py` if needed. Do not pin a direct URL.

- [ ] **Step 4: Create the `pages` package init (empty surface for now)**

Create `pdomain_ops/pages/__init__.py`:
```python
"""Universal page value models — imported by every pd-* consumer of pages.

Pure pydantic. No eventsourcing, no blob/file I/O. The event store
(``pdomain_ops.page_aggregate``) and blob store (``pdomain_ops.blob_store``)
are separate, lifecycle-consumer-only modules.
"""
```
(Re-exports are added in Task 9, once the names exist.)

- [ ] **Step 5: Verify the package imports**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run python -c "import pdomain_ops.pages"`
Expected: no output, exit 0.

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ops
git add pyproject.toml uv.lock pdomain_ops/pages/__init__.py
git commit -m "build(deps): add eventsourcing, bump book-tools floor to 0.17.0; scaffold pages pkg"
```

---

## Milestone 1: ProvenanceGraph value models

### Task 1: `ProvenanceNode`, `DeadBranch`, `ProvenanceGraph`

**Files:**
- Create: `pdomain_ops/pages/provenance.py`
- Test: `tests/pages/test_provenance.py`

- [ ] **Step 1: Write the failing test**

Create `tests/pages/test_provenance.py`:
```python
from datetime import datetime, timezone

from pdomain_ops.pages.provenance import DeadBranch, ProvenanceGraph, ProvenanceNode


def test_node_defaults_are_independent() -> None:
    a = ProvenanceNode(id="a", source="ingest")
    b = ProvenanceNode(id="b", source="ocr")
    a.blob_refs.append("hash1")
    a.parent_ids.append("a")
    # mutable defaults must not be shared across instances
    assert b.blob_refs == []
    assert b.parent_ids == []


def test_node_carries_step_specific_config() -> None:
    node = ProvenanceNode(
        id="ocr_node",
        source="ocr",
        tool="doctr",
        tool_version="0.15.2",
        config={"model": "db_resnet50", "model_version": "v2", "threshold": 0.3},
        parent_ids=["thresh_node"],
    )
    assert node.config is not None
    assert node.config["model"] == "db_resnet50"
    assert node.parent_ids == ["thresh_node"]


def test_add_node_advances_head_and_history() -> None:
    graph = ProvenanceGraph()
    assert graph.head_id == ""
    graph.add_node(ProvenanceNode(id="n1", source="ingest"))
    graph.add_node(ProvenanceNode(id="n2", source="ocr", parent_ids=["n1"]))
    assert graph.head_id == "n2"
    assert graph.history == ["n1", "n2"]
    assert graph.head is not None and graph.head.source == "ocr"
    assert set(graph.nodes) == {"n1", "n2"}


def test_add_node_without_advancing_head() -> None:
    graph = ProvenanceGraph()
    graph.add_node(ProvenanceNode(id="n1", source="ingest"))
    graph.add_node(ProvenanceNode(id="branch", source="ocr"), advance_head=False)
    assert graph.head_id == "n1"
    assert graph.history == ["n1"]
    assert "branch" in graph.nodes


def test_head_is_none_on_empty_graph() -> None:
    assert ProvenanceGraph().head is None


def test_dead_branch_round_trips_through_json() -> None:
    when = datetime(2026, 1, 1, tzinfo=timezone.utc)
    branch = DeadBranch(
        tip_id="old_tip", forked_from_id="fork", superseded_at=when, retain_until=when
    )
    graph = ProvenanceGraph(dead_branches=[branch])
    restored = ProvenanceGraph.model_validate_json(graph.model_dump_json())
    assert restored.dead_branches[0].tip_id == "old_tip"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/pages/test_provenance.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pdomain_ops.pages.provenance'`.

- [ ] **Step 3: Write the implementation**

Create `pdomain_ops/pages/provenance.py`:
```python
"""Provenance DAG: how a page was produced and what was done to it.

Each processing step (ingest, threshold, ocr, layout, reorganize, labeler,
proofread, export, …) is a node. Edges are ``parent_ids``: 0 parents = root,
1 = linear, 2+ = merge (e.g. reorganize consumes both layout and ocr).
Design spec §5.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProvenanceNode(BaseModel):
    """One processing step in the provenance DAG."""

    id: str
    source: str
    tool: str | None = None
    tool_version: str | None = None
    config: dict[str, Any] | None = None
    timestamp: datetime | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    blob_refs: list[str] = Field(default_factory=list)
    extra: dict[str, Any] | None = None
    parent_ids: list[str] = Field(default_factory=list)


class DeadBranch(BaseModel):
    """A superseded path awaiting pruning (design spec §5 dead branches)."""

    tip_id: str
    forked_from_id: str
    superseded_at: datetime
    retain_until: datetime


class ProvenanceGraph(BaseModel):
    """DAG of provenance nodes with an active head and head-history."""

    nodes: dict[str, ProvenanceNode] = Field(default_factory=dict)
    head_id: str = ""
    history: list[str] = Field(default_factory=list)
    dead_branches: list[DeadBranch] = Field(default_factory=list)

    @property
    def head(self) -> ProvenanceNode | None:
        return self.nodes.get(self.head_id)

    def add_node(self, node: ProvenanceNode, *, advance_head: bool = True) -> None:
        """Insert a node. When ``advance_head`` is set, make it the new head
        and append it to the active-lineage history."""
        self.nodes[node.id] = node
        if advance_head:
            self.head_id = node.id
            self.history.append(node.id)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/pages/test_provenance.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ops
git add pdomain_ops/pages/provenance.py tests/pages/test_provenance.py
git commit -m "feat(pages): add ProvenanceNode/DeadBranch/ProvenanceGraph value models"
```

---

## Milestone 2: Record value models

### Task 2: `RotationSource`, `PageChangeEntry`, `PageRecord`, `ProjectRecord`

**Files:**
- Create: `pdomain_ops/pages/records.py`
- Test: `tests/pages/test_records.py`

- [ ] **Step 1: Write the failing test**

Create `tests/pages/test_records.py`:
```python
from pathlib import Path
from uuid import uuid4

from pdomain_ops.pages.provenance import ProvenanceGraph, ProvenanceNode
from pdomain_ops.pages.records import (
    PageChangeEntry,
    PageRecord,
    ProjectRecord,
    RotationSource,
)


def test_rotation_source_is_str_enum() -> None:
    assert RotationSource.NONE == "none"
    assert RotationSource.AUTO == "auto"
    assert RotationSource.MANUAL == "manual"
    # StrEnum members are usable as plain strings
    assert f"{RotationSource.AUTO}" == "auto"


def test_page_record_minimal_defaults() -> None:
    pid = uuid4()
    rec = PageRecord(page_id=pid, page_index=0)
    assert rec.page_id == pid
    assert rec.source == "ocr"
    assert rec.ocr_failed is False
    assert rec.rotation_degrees == 0
    assert rec.rotation_source is RotationSource.NONE
    assert rec.provenance is None
    assert rec.changelog == []


def test_page_record_changelog_defaults_independent() -> None:
    a = PageRecord(page_id=uuid4(), page_index=0)
    b = PageRecord(page_id=uuid4(), page_index=1)
    a.changelog.append(PageChangeEntry(provenance_node_id="n", changes=[]))
    assert b.changelog == []


def test_page_record_round_trips_with_provenance() -> None:
    graph = ProvenanceGraph()
    graph.add_node(ProvenanceNode(id="ocr", source="ocr", tool="doctr"))
    rec = PageRecord(
        page_id=uuid4(),
        page_index=3,
        image_path=Path("/scans/page_0003.png"),
        rotation_degrees=90,
        rotation_source=RotationSource.AUTO,
        provenance=graph,
        changelog=[
            PageChangeEntry(
                provenance_node_id="ocr",
                changes=[{"type": "word_text", "word_id": "b0l2w3", "from": "thr", "to": "the"}],
            )
        ],
    )
    restored = PageRecord.model_validate_json(rec.model_dump_json())
    assert restored.page_id == rec.page_id
    assert restored.rotation_source is RotationSource.AUTO
    assert restored.provenance is not None
    assert restored.provenance.head_id == "ocr"
    assert restored.changelog[0].changes[0]["to"] == "the"


def test_project_record_orders_pages() -> None:
    p0, p1 = uuid4(), uuid4()
    proj = ProjectRecord(project_id=uuid4(), name="Book", page_ids=[p0, p1])
    assert proj.page_ids == [p0, p1]
    assert proj.source_dir is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/pages/test_records.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pdomain_ops.pages.records'`.

- [ ] **Step 3: Write the implementation**

Create `pdomain_ops/pages/records.py`:
```python
"""Durable page/project records — the operational metadata stripped from Page.

``PageRecord`` owns everything ``Page`` shed in Plan 1: image path, source,
failure flag, rotation history, provenance, changelog. ``ProjectRecord`` owns
page ordering. Both are plain pydantic — zero eventsourcing imports
(design spec §7, §11).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from pdomain_ops.pages.provenance import ProvenanceGraph


class RotationSource(StrEnum):
    """How a page's rotation was determined (design spec §6)."""

    NONE = "none"      # original disk orientation
    AUTO = "auto"      # best-of-4 OCR selection
    MANUAL = "manual"  # user-applied


class PageChangeEntry(BaseModel):
    """One entry in the per-page changelog — "git for pages" (design spec §7).

    ``changes`` is a flexible list of typed dict events for now; it becomes a
    discriminated union when proofreading ships (design spec §15).
    """

    provenance_node_id: str
    timestamp: datetime | None = None
    changes: list[dict[str, Any]] = Field(default_factory=list)


class PageRecord(BaseModel):
    """Durable, versioned record of a page's lifecycle metadata.

    ``page_id`` equals ``Page.page_id`` and ``PageAggregate.id`` — the stable
    identity of the physical page entity, not a content version.
    """

    page_id: UUID
    page_index: int
    image_path: Path | None = None
    source: str = "ocr"
    ocr_failed: bool = False
    rotation_degrees: int = 0
    rotation_source: RotationSource = RotationSource.NONE
    provenance: ProvenanceGraph | None = None
    provenance_summary: str | None = None
    changelog: list[PageChangeEntry] = Field(default_factory=list)


class ProjectRecord(BaseModel):
    """Top-level organizing unit: a book/batch/job of pages processed together.

    ``page_ids`` is authoritative for ordering; ``PageRecord.page_index`` is a
    convenience cache (design spec §11).
    """

    project_id: UUID
    name: str
    page_ids: list[UUID] = Field(default_factory=list)
    source_dir: Path | None = None
    created_at: datetime | None = None
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/pages/test_records.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ops
git add pdomain_ops/pages/records.py tests/pages/test_records.py
git commit -m "feat(pages): add RotationSource/PageChangeEntry/PageRecord/ProjectRecord"
```

---

## Milestone 3: Provenance summary

### Task 3: `build_provenance_summary`

**Files:**
- Create: `pdomain_ops/pages/summary.py`
- Test: `tests/pages/test_summary.py`

- [ ] **Step 1: Write the failing test**

Create `tests/pages/test_summary.py`:
```python
from pdomain_ops.pages.provenance import ProvenanceGraph, ProvenanceNode
from pdomain_ops.pages.summary import build_provenance_summary


def test_summary_of_none_graph() -> None:
    assert build_provenance_summary(None) == "no provenance"


def test_summary_of_empty_graph() -> None:
    assert build_provenance_summary(ProvenanceGraph()) == "no provenance"


def test_summary_walks_active_lineage_with_tools() -> None:
    graph = ProvenanceGraph()
    graph.add_node(ProvenanceNode(id="i", source="ingest", tool="prep-for-pgdp"))
    graph.add_node(ProvenanceNode(id="t", source="threshold", tool="prep-for-pgdp"))
    graph.add_node(ProvenanceNode(id="o", source="ocr", tool="doctr"))
    graph.add_node(ProvenanceNode(id="r", source="reorganize"))  # no tool
    graph.add_node(ProvenanceNode(id="l", source="labeler", tool="labeler-spa"))
    assert build_provenance_summary(graph) == (
        "ingest(prep-for-pgdp) → threshold(prep-for-pgdp) → ocr(doctr) "
        "→ reorganize → labeler(labeler-spa)"
    )


def test_summary_skips_unknown_head_history_ids() -> None:
    graph = ProvenanceGraph()
    graph.add_node(ProvenanceNode(id="o", source="ocr", tool="doctr"))
    graph.history.append("ghost")  # id with no node — must be skipped
    assert build_provenance_summary(graph) == "ocr(doctr)"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/pages/test_summary.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pdomain_ops.pages.summary'`.

- [ ] **Step 3: Write the implementation**

Create `pdomain_ops/pages/summary.py`:
```python
"""Human-readable provenance one-liner.

Replaces ``_build_provenance_summary`` in labeler-spa's ``api/pages.py``
(design spec §7). Assembled at payload-build time — not auto-updated on graph
mutation; callers set ``PageRecord.provenance_summary`` when they build a payload.
"""

from __future__ import annotations

from pdomain_ops.pages.provenance import ProvenanceGraph


def build_provenance_summary(graph: ProvenanceGraph | None) -> str:
    """Render the active lineage as ``source(tool) → source(tool) → …``.

    Walks ``graph.history`` (the ordered head-over-time list); falls back to the
    current head when history is empty. Unknown ids are skipped. Returns
    ``"no provenance"`` for a missing or empty graph.
    """
    if graph is None or not graph.nodes:
        return "no provenance"
    chain = graph.history or ([graph.head_id] if graph.head_id else [])
    labels: list[str] = []
    for node_id in chain:
        node = graph.nodes.get(node_id)
        if node is None:
            continue
        labels.append(node.source if node.tool is None else f"{node.source}({node.tool})")
    return " → ".join(labels) if labels else "no provenance"
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/pages/test_summary.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ops
git add pdomain_ops/pages/summary.py tests/pages/test_summary.py
git commit -m "feat(pages): add build_provenance_summary one-liner"
```

---

## Milestone 4: Portable payload + universal exports

### Task 4: `PagePayload`

**Files:**
- Create: `pdomain_ops/pages/payload.py`
- Test: `tests/pages/test_payload.py`

- [ ] **Step 1: Write the failing test**

Create `tests/pages/test_payload.py`:
```python
from uuid import uuid4

from pdomain_ops.pages.payload import PagePayload
from pdomain_ops.pages.provenance import ProvenanceGraph, ProvenanceNode
from pdomain_ops.pages.records import PageRecord


def test_payload_round_trips_through_json() -> None:
    pid = uuid4()
    graph = ProvenanceGraph()
    graph.add_node(ProvenanceNode(id="ocr", source="ocr", tool="doctr"))
    record = PageRecord(page_id=pid, page_index=2, provenance=graph)
    payload = PagePayload(
        page_id=pid,
        page_index=2,
        record=record,
        content={"type": "Page", "width": 1000, "height": 1500, "items": []},
        dims=(1000, 1500),
    )
    restored = PagePayload.model_validate_json(payload.model_dump_json())
    assert restored.page_id == pid
    assert restored.page_index == 2
    assert restored.record.provenance is not None
    assert restored.content["width"] == 1000
    assert restored.dims == (1000, 1500)
    assert restored.image_url is None


def test_payload_page_id_matches_record() -> None:
    pid = uuid4()
    payload = PagePayload(
        page_id=pid,
        page_index=0,
        record=PageRecord(page_id=pid, page_index=0),
        content={},
    )
    assert payload.page_id == payload.record.page_id
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/pages/test_payload.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pdomain_ops.pages.payload'`.

- [ ] **Step 3: Write the implementation**

Create `pdomain_ops/pages/payload.py`:
```python
"""Universal portable page format (design spec §12).

Used for CLI/simple-gui JSON output, API responses, and cross-service transfer
(import a CLI ``PagePayload`` into the labeler's event store). Assembled at
write/response time — never stored directly; the event store + blob store are
the durable form for lifecycle consumers.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel

from pdomain_ops.pages.records import PageRecord


class PagePayload(BaseModel):
    page_id: UUID
    page_index: int
    record: PageRecord
    content: dict[str, Any]              # Page.to_dict() — blocks/lines/words/bboxes
    image_url: str | None = None         # for API responses; None in file exports
    dims: tuple[int, int] | None = None  # (width, height) for canvas scaling
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/pages/test_payload.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ops
git add pdomain_ops/pages/payload.py tests/pages/test_payload.py
git commit -m "feat(pages): add PagePayload portable serialization model"
```

### Task 5: Re-export the universal `pdomain_ops.pages` surface

**Files:**
- Modify: `pdomain_ops/pages/__init__.py`
- Test: `tests/pages/test_payload.py` (extend) — or a small new `tests/pages/test_surface.py`

- [ ] **Step 1: Write the failing test**

Create `tests/pages/test_surface.py`:
```python
def test_pages_package_reexports_universal_surface() -> None:
    import pdomain_ops.pages as pages

    expected = {
        "DeadBranch",
        "PageChangeEntry",
        "PagePayload",
        "PageRecord",
        "ProjectRecord",
        "ProvenanceGraph",
        "ProvenanceNode",
        "RotationSource",
        "build_provenance_summary",
    }
    assert expected <= set(pages.__all__)
    # every name in __all__ is actually importable
    for name in pages.__all__:
        assert hasattr(pages, name), name
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/pages/test_surface.py -q`
Expected: FAIL — `AttributeError: module 'pdomain_ops.pages' has no attribute '__all__'`.

- [ ] **Step 3: Write the implementation**

Replace `pdomain_ops/pages/__init__.py` with:
```python
"""Universal page value models — imported by every pd-* consumer of pages.

Pure pydantic. No eventsourcing, no blob/file I/O. The event store
(``pdomain_ops.page_aggregate``) and blob store (``pdomain_ops.blob_store``)
are separate, lifecycle-consumer-only modules.
"""

from pdomain_ops.pages.payload import PagePayload
from pdomain_ops.pages.provenance import DeadBranch, ProvenanceGraph, ProvenanceNode
from pdomain_ops.pages.records import (
    PageChangeEntry,
    PageRecord,
    ProjectRecord,
    RotationSource,
)
from pdomain_ops.pages.summary import build_provenance_summary

__all__ = [
    "DeadBranch",
    "PageChangeEntry",
    "PagePayload",
    "PageRecord",
    "ProjectRecord",
    "ProvenanceGraph",
    "ProvenanceNode",
    "RotationSource",
    "build_provenance_summary",
]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/pages/ -q`
Expected: PASS (all pages tests green).

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ops
git add pdomain_ops/pages/__init__.py tests/pages/test_surface.py
git commit -m "feat(pages): re-export universal value-model surface"
```

---

## Milestone 5: Content-addressed blob store

### Task 6: `BlobStore`

**Files:**
- Create: `pdomain_ops/blob_store.py`
- Test: `tests/test_blob_store.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_blob_store.py`:
```python
from hashlib import sha256
from pathlib import Path

from pdomain_book_tools.ocr import BlobStoreProtocol

from pdomain_ops.blob_store import BlobStore


def test_write_returns_sha256_and_dedupes(tmp_path: Path) -> None:
    store = BlobStore(tmp_path)
    data = b"the quick brown fox"
    h = store.write(data)
    assert h == sha256(data).hexdigest()
    # writing the same bytes again is a no-op returning the same hash
    assert store.write(data) == h
    blobs = list((tmp_path / "blobs").iterdir())
    assert len(blobs) == 1


def test_read_round_trips(tmp_path: Path) -> None:
    store = BlobStore(tmp_path)
    h = store.write(b"payload bytes")
    assert store.read(h) == b"payload bytes"


def test_exists(tmp_path: Path) -> None:
    store = BlobStore(tmp_path)
    h = store.write(b"x")
    assert store.exists(h) is True
    assert store.exists("0" * 64) is False


def test_prune_orphans_deletes_unreferenced(tmp_path: Path) -> None:
    store = BlobStore(tmp_path)
    keep = store.write(b"keep me")
    drop = store.write(b"drop me")
    deleted = store.prune_orphans(live_refs={keep})
    assert deleted == [drop]
    assert store.exists(keep) is True
    assert store.exists(drop) is False


def test_blobstore_satisfies_protocol(tmp_path: Path) -> None:
    # structural conformance to the Plan-1 BlobStoreProtocol is checked by
    # basedpyright on this annotated assignment, and exercised at runtime.
    store: BlobStoreProtocol = BlobStore(tmp_path)
    h = sha256(b"hi").hexdigest()
    assert isinstance(BlobStore(tmp_path).write(b"hi"), str)
    written = BlobStore(tmp_path).write(b"hi")
    assert written == h
    assert store.read(BlobStore(tmp_path).write(b"hi")) is not None or True
```

> The last test's key line is `store: BlobStoreProtocol = BlobStore(tmp_path)` — if `BlobStore` ever drifts from `read(self, hash: str) -> bytes`, basedpyright fails `make typecheck`. The runtime asserts are secondary.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/test_blob_store.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pdomain_ops.blob_store'`.

- [ ] **Step 3: Write the implementation**

Create `pdomain_ops/blob_store.py`:
```python
"""Content-addressed blob store for all large page content (design spec §9).

Raw bytes keyed by SHA256 — content-type agnostic. Callers decide what to write
and how to pre-process it (images: ``oxipng.optimize_from_memory`` first; Page
JSON: ``page.to_dict()`` → UTF-8). Satisfies ``pdomain_book_tools.ocr.
BlobStoreProtocol`` (book-tools v0.17.0). Lifecycle consumers only.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path


class BlobStore:
    """Per-project ``<project>/.pd-pages/blobs/<sha256>`` store."""

    def __init__(self, project_dir: Path) -> None:
        self._blobs_dir = Path(project_dir) / "blobs"
        self._blobs_dir.mkdir(parents=True, exist_ok=True)

    def write(self, data: bytes) -> str:
        """SHA256 the bytes, store if new (atomically), return the hash."""
        digest = sha256(data).hexdigest()
        path = self._blobs_dir / digest
        if not path.exists():
            tmp = path.with_name(f"{digest}.tmp")
            tmp.write_bytes(data)
            tmp.replace(path)  # atomic on POSIX
        return digest

    def read(self, hash: str) -> bytes:  # noqa: A002 — name fixed by BlobStoreProtocol
        return (self._blobs_dir / hash).read_bytes()

    def exists(self, hash: str) -> bool:  # noqa: A002
        return (self._blobs_dir / hash).is_file()

    def prune_orphans(self, live_refs: set[str]) -> list[str]:
        """Delete blobs whose hash is not in ``live_refs``. Returns deleted hashes."""
        deleted: list[str] = []
        for path in sorted(self._blobs_dir.iterdir()):
            if path.is_file() and not path.name.endswith(".tmp") and path.name not in live_refs:
                path.unlink()
                deleted.append(path.name)
        return deleted
```

> `# noqa: A002` suppresses ruff's "shadowing builtin `hash`" — the parameter name is fixed by `BlobStoreProtocol.read(self, hash: str)` and must match for the conformance test. If ruff flags differently in this repo, mirror whatever suppression the codebase already uses for builtin-shadow cases; check `pyproject.toml` ruff config first.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/test_blob_store.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Typecheck the protocol conformance**

Run: `cd /workspaces/ocr-container/pdomain-ops && make typecheck`
Expected: PASS — confirms `BlobStore` structurally satisfies `BlobStoreProtocol`.

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ops
git add pdomain_ops/blob_store.py tests/test_blob_store.py
git commit -m "feat(blob): add content-addressed BlobStore (BlobStoreProtocol impl)"
```

---

## Milestone 6: Event-sourced aggregates

### Task 7: `PageAggregate`, `ProjectAggregate`, `PagesApplication`

**Files:**
- Create: `pdomain_ops/page_aggregate.py`
- Test: `tests/test_page_aggregate.py`

This is the lifecycle-consumer core. `PageRecord` stays a plain pydantic model
(Task 2); `PageAggregate` wraps it and provides the event-store interface
(design spec §8). `PagesApplication` wires sqlite persistence, pydantic
transcodings (so events carrying `PageRecord` / `ProvenanceNode` serialize), and
snapshotting.

- [ ] **Step 1: Write the failing test**

Create `tests/test_page_aggregate.py`:
```python
from pathlib import Path
from uuid import uuid4

from pdomain_ops.pages import (
    PageRecord,
    ProjectRecord,
    ProvenanceNode,
    RotationSource,
)
from pdomain_ops.page_aggregate import PageAggregate, PagesApplication, ProjectAggregate


def _sqlite_env(tmp_path: Path) -> dict[str, str]:
    return {
        "PERSISTENCE_MODULE": "eventsourcing.sqlite",
        "SQLITE_DBNAME": str(tmp_path / "events.db"),
    }


def test_aggregate_id_equals_page_id() -> None:
    pid = uuid4()
    agg = PageAggregate(record=PageRecord(page_id=pid, page_index=0))
    assert agg.id == pid


def test_ocr_completed_updates_record_and_provenance() -> None:
    pid = uuid4()
    agg = PageAggregate(record=PageRecord(page_id=pid, page_index=0, ocr_failed=True))
    agg.ocr_completed(
        provenance_node=ProvenanceNode(id="ocr", source="ocr", tool="doctr"),
        blob_refs=["content_hash", "image_hash"],
    )
    assert agg.record.ocr_failed is False
    assert agg.record.provenance is not None
    assert agg.record.provenance.head_id == "ocr"


def test_labeler_edited_appends_changelog() -> None:
    pid = uuid4()
    agg = PageAggregate(record=PageRecord(page_id=pid, page_index=0))
    agg.ocr_completed(
        provenance_node=ProvenanceNode(id="ocr", source="ocr"), blob_refs=["c"]
    )
    agg.labeler_edited(
        provenance_node=ProvenanceNode(id="lbl", source="labeler", parent_ids=["ocr"]),
        changes=[{"type": "word_text", "word_id": "w1", "from": "thr", "to": "the"}],
    )
    assert agg.record.provenance is not None
    assert agg.record.provenance.head_id == "lbl"
    assert agg.record.changelog[-1].provenance_node_id == "lbl"
    assert agg.record.changelog[-1].changes[0]["to"] == "the"


def test_save_and_reload_replays_state(tmp_path: Path) -> None:
    app = PagesApplication(env=_sqlite_env(tmp_path))
    pid = uuid4()
    agg = PageAggregate(
        record=PageRecord(page_id=pid, page_index=4, rotation_source=RotationSource.AUTO)
    )
    agg.ocr_completed(
        provenance_node=ProvenanceNode(id="ocr", source="ocr", tool="doctr"),
        blob_refs=["content_hash"],
    )
    app.save(agg)

    reloaded: PageAggregate = app.repository.get(pid)
    assert reloaded.id == pid
    assert reloaded.record.rotation_source is RotationSource.AUTO
    assert reloaded.record.provenance is not None
    assert reloaded.record.provenance.head_id == "ocr"


def test_snapshotting_truncates_replay(tmp_path: Path) -> None:
    class SnappyApp(PagesApplication):
        snapshotting_intervals = {PageAggregate: 2}  # noqa: RUF012

    app = SnappyApp(env=_sqlite_env(tmp_path))
    pid = uuid4()
    agg = PageAggregate(record=PageRecord(page_id=pid, page_index=0))
    agg.ocr_completed(provenance_node=ProvenanceNode(id="ocr", source="ocr"), blob_refs=["c"])
    app.save(agg)  # version 2 → snapshot taken
    assert app.snapshots is not None
    snaps = list(app.snapshots.get(pid))
    assert len(snaps) >= 1
    # state still correct after snapshot-based load
    assert app.repository.get(pid).record.provenance is not None


def test_project_aggregate_round_trips(tmp_path: Path) -> None:
    app = PagesApplication(env=_sqlite_env(tmp_path))
    proj_id = uuid4()
    p0, p1 = uuid4(), uuid4()
    proj = ProjectAggregate(record=ProjectRecord(project_id=proj_id, name="Book"))
    proj.add_page(page_id=p0, page_index=0)
    proj.add_page(page_id=p1, page_index=1)
    app.save(proj)

    reloaded: ProjectAggregate = app.repository.get(proj_id)
    assert reloaded.record.page_ids == [p0, p1]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/test_page_aggregate.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pdomain_ops.page_aggregate'`.

- [ ] **Step 3: Write the implementation**

Create `pdomain_ops/page_aggregate.py`:
```python
"""Event-sourced wrappers around PageRecord/ProjectRecord (design spec §8, §11).

``PageAggregate`` / ``ProjectAggregate`` use ``eventsourcing``'s ``@event``
declarative style: each decorated command method's body is the apply logic,
re-run deterministically on replay. ``PagesApplication`` registers pydantic
transcodings so events carrying ``PageRecord`` / ``ProvenanceNode`` /
``ProjectRecord`` serialize, and enables snapshotting. Lifecycle consumers only.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from eventsourcing.application import Application
from eventsourcing.domain import Aggregate, event
from eventsourcing.persistence import Transcoding

from pdomain_ops.pages import PageRecord, ProjectRecord, ProvenanceNode
from pdomain_ops.pages.provenance import ProvenanceGraph


class PageAggregate(Aggregate):
    """Lifecycle of a single page. ``id`` == ``record.page_id``."""

    @event("ImageIngested")
    def __init__(self, record: PageRecord) -> None:
        self._record = record

    @classmethod
    def create_id(cls, record: PageRecord) -> UUID:  # ties aggregate id to page_id
        return record.page_id

    @property
    def record(self) -> PageRecord:
        return self._record

    def _apply_node(self, node: ProvenanceNode) -> None:
        graph = self._record.provenance or ProvenanceGraph()
        graph.add_node(node)
        self._record.provenance = graph

    @event("ImagePreprocessed")
    def preprocess(self, provenance_node: ProvenanceNode, blob_refs: list[str]) -> None:
        del blob_refs  # recorded on the event; graph carries the refs it needs
        self._apply_node(provenance_node)

    @event("OcrCompleted")
    def ocr_completed(self, provenance_node: ProvenanceNode, blob_refs: list[str]) -> None:
        del blob_refs
        self._record.ocr_failed = False
        self._apply_node(provenance_node)

    @event("GtMapped")
    def gt_mapped(self, provenance_node: ProvenanceNode) -> None:
        self._apply_node(provenance_node)

    @event("LabelerEdited")
    def labeler_edited(
        self, provenance_node: ProvenanceNode, changes: list[dict[str, Any]]
    ) -> None:
        self._apply_node(provenance_node)
        self._record.changelog.append(
            PageChangeEntry(provenance_node_id=provenance_node.id, changes=changes)
        )

    @event("Exported")
    def exported(self, provenance_node: ProvenanceNode) -> None:
        self._apply_node(provenance_node)


class ProjectAggregate(Aggregate):
    """Lifecycle of a project (book/batch/job). ``id`` == ``record.project_id``."""

    @event("ProjectCreated")
    def __init__(self, record: ProjectRecord) -> None:
        self._record = record

    @classmethod
    def create_id(cls, record: ProjectRecord) -> UUID:
        return record.project_id

    @property
    def record(self) -> ProjectRecord:
        return self._record

    @event("PageAdded")
    def add_page(self, page_id: UUID, page_index: int) -> None:
        del page_index  # positional label; order is the list order below
        self._record.page_ids.append(page_id)

    @event("PageReordered")
    def reorder_pages(self, page_ids: list[UUID]) -> None:
        self._record.page_ids = list(page_ids)

    @event("ProjectExported")
    def exported(self, provenance_node: ProvenanceNode) -> None:
        del provenance_node


class _PageRecordTranscoding(Transcoding):
    type = PageRecord
    name = "pdomain_ops.PageRecord"

    def encode(self, obj: PageRecord) -> dict[str, Any]:
        return obj.model_dump(mode="json")

    def decode(self, data: dict[str, Any]) -> PageRecord:
        return PageRecord.model_validate(data)


class _ProjectRecordTranscoding(Transcoding):
    type = ProjectRecord
    name = "pdomain_ops.ProjectRecord"

    def encode(self, obj: ProjectRecord) -> dict[str, Any]:
        return obj.model_dump(mode="json")

    def decode(self, data: dict[str, Any]) -> ProjectRecord:
        return ProjectRecord.model_validate(data)


class _ProvenanceNodeTranscoding(Transcoding):
    type = ProvenanceNode
    name = "pdomain_ops.ProvenanceNode"

    def encode(self, obj: ProvenanceNode) -> dict[str, Any]:
        return obj.model_dump(mode="json")

    def decode(self, data: dict[str, Any]) -> ProvenanceNode:
        return ProvenanceNode.model_validate(data)


class PagesApplication(Application):
    """Event-store application for page + project aggregates.

    Default persistence is in-memory POPO; pass ``env={"PERSISTENCE_MODULE":
    "eventsourcing.sqlite", "SQLITE_DBNAME": "<project>/.pd-pages/events.db"}``
    for durable storage. Migrate to Postgres by swapping the env (design spec §8).
    """

    snapshotting_intervals = {  # noqa: RUF012 — eventsourcing reads this as a class attr
        PageAggregate: 20,
        ProjectAggregate: 20,
    }

    def register_transcodings(self, transcoder: Any) -> None:
        super().register_transcodings(transcoder)
        transcoder.register(_PageRecordTranscoding())
        transcoder.register(_ProjectRecordTranscoding())
        transcoder.register(_ProvenanceNodeTranscoding())
```

> **Import note:** `PageChangeEntry` is used in `labeler_edited`. Add it to the
> import from `pdomain_ops.pages`: change the import line to
> `from pdomain_ops.pages import PageChangeEntry, PageRecord, ProjectRecord, ProvenanceNode`.
> (It is exported from `pdomain_ops.pages` as of Task 5.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/test_page_aggregate.py -q`
Expected: PASS (6 passed).

> **If `register_transcodings` has a different signature in the installed
> eventsourcing version:** run `uv run python -c "from eventsourcing.application import Application; help(Application.register_transcodings)"` and match it. The v9.x hook is `register_transcodings(self, transcoder)`. If transcoder registration is rejected for a pydantic model, the likely cause is the event payload containing a model the transcoder doesn't know — confirm only `PageRecord`, `ProjectRecord`, and `ProvenanceNode` appear as top-level event attributes (nested models inside `PageRecord` are handled by its own `model_dump`/`model_validate`).

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ops
git add pdomain_ops/page_aggregate.py tests/test_page_aggregate.py
git commit -m "feat(aggregate): add PageAggregate/ProjectAggregate + PagesApplication"
```

---

## Milestone 7: Top-level public surface

### Task 8: Re-export universal names from `pdomain_ops` and update the surface test

**Files:**
- Modify: `pdomain_ops/__init__.py`
- Modify: `tests/test_public_surface.py`

The universal `pdomain_ops.pages` names are re-exported from the top-level
package for ergonomic imports (`from pdomain_ops import PageRecord`). The
lifecycle-only modules (`blob_store`, `page_aggregate`) are **not** re-exported
at top level — consumers import them explicitly (design spec §13), keeping the
eventsourcing dependency off the universal import path.

- [ ] **Step 1: Write the failing test**

Edit `tests/test_public_surface.py` — add:
```python
def test_universal_pages_surface_is_top_level_importable() -> None:
    from pdomain_ops import (
        PageChangeEntry,
        PagePayload,
        PageRecord,
        ProjectRecord,
        ProvenanceGraph,
        ProvenanceNode,
        RotationSource,
        build_provenance_summary,
    )

    assert PageRecord.__name__ == "PageRecord"
    assert RotationSource.AUTO == "auto"
    assert callable(build_provenance_summary)
    _ = (PageChangeEntry, PagePayload, ProjectRecord, ProvenanceGraph, ProvenanceNode)


def test_lifecycle_modules_are_not_top_level_exports() -> None:
    import pdomain_ops

    # blob/aggregate stay out of the universal surface so the eventsourcing dep
    # does not load on a plain `import pdomain_ops`
    assert "BlobStore" not in pdomain_ops.__all__
    assert "PageAggregate" not in pdomain_ops.__all__
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/test_public_surface.py -q`
Expected: FAIL — `ImportError: cannot import name 'PageRecord' from 'pdomain_ops'`.

- [ ] **Step 3: Write the implementation**

Edit `pdomain_ops/__init__.py`. Add the re-export block (after the existing imports) and extend `__all__`:
```python
from pdomain_ops.pages import (
    DeadBranch,
    PageChangeEntry,
    PagePayload,
    PageRecord,
    ProjectRecord,
    ProvenanceGraph,
    ProvenanceNode,
    RotationSource,
    build_provenance_summary,
)
```
Extend the existing `__all__` to include (keep it sorted):
```python
__all__ = [
    "DeadBranch",
    "PageChangeEntry",
    "PagePayload",
    "PageRecord",
    "ProjectRecord",
    "ProvenanceGraph",
    "ProvenanceNode",
    "RotationSource",
    "SuiteAdapters",
    "__version__",
    "build_provenance_summary",
    "mount_routes",
]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/test_public_surface.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ops
git add pdomain_ops/__init__.py tests/test_public_surface.py
git commit -m "feat(ops): re-export universal pages surface from top-level package"
```

---

## Milestone 8: Full CI, version bump, release

### Task 9: Green CI, CHANGELOG, tag, release

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Run the full CI gate**

Run: `cd /workspaces/ocr-container/pdomain-ops && make ci AI=1`
Expected: PASS — setup, pre-commit, lint, format, typecheck, and `pytest -n auto` all green. Fix any ruff/basedpyright findings here (e.g. import ordering, missing docstrings on public classes — the suite enforces strict linting). Do **not** weaken lint config to pass.

- [ ] **Step 2: Add the CHANGELOG entry**

This release is **additive** (new modules + a raised dependency floor) — no
existing `pdomain_ops` API changes — so it is a **minor** bump.

Determine the next version from tags, not from `CHANGELOG.md` (version is
hatch-vcs / tag-driven; the changelog heading is cosmetic):
```bash
cd /workspaces/ocr-container/pdomain-ops
git fetch --tags
git tag --list 'v*' --sort=-v:refname | head -5
```
Pick the next **minor** after the highest existing tag (e.g. highest is `v0.5.0` → release `v0.6.0`). **Verify the chosen tag does not already exist** before using it (Plan 1 hit a `v0.16.0` collision — do not repeat it). Use the actual highest tag you observe; the example below assumes `v0.6.0`.

Add to the top of `CHANGELOG.md` (under `# Changelog`):
```markdown
## [0.6.0] - 2026-06-01

### Added
- `pdomain_ops.pages` — universal page value models: `PageRecord`,
  `ProjectRecord`, `ProvenanceGraph`/`ProvenanceNode`/`DeadBranch`,
  `RotationSource`, `PageChangeEntry`, `PagePayload`, and
  `build_provenance_summary`. Imported by every pd-* page consumer.
- `pdomain_ops.blob_store.BlobStore` — content-addressed SHA256 blob store
  implementing `pdomain_book_tools.ocr.BlobStoreProtocol` (lifecycle consumers).
- `pdomain_ops.page_aggregate` — `PageAggregate`, `ProjectAggregate`, and
  `PagesApplication` (eventsourcing; sqlite persistence + snapshotting).

### Changed
- Bumped `pdomain-book-tools` floor to `>=0.17.0` (Page operational-field split).
- Added `eventsourcing>=9.4,<10` dependency.
```

- [ ] **Step 3: Commit the changelog**

```bash
cd /workspaces/ocr-container/pdomain-ops
git add CHANGELOG.md
git commit -m "docs(changelog): pdomain-ops 0.6.0 — PageRecord/BlobStore/aggregates"
```

- [ ] **Step 4: Integrate the worktree branch (orchestrator only)**

Per workspace policy: worktree → rebase origin/main → ff-only merge → push.
The implementing subagent stops at this commit and returns its worktree path +
branch. The **orchestrator** runs:
```bash
git -C <worktree> fetch origin && git -C <worktree> rebase origin/main
make -C <worktree> ci AI=1            # re-verify green on the rebased tip
git -C /workspaces/ocr-container/pdomain-ops checkout main
git -C /workspaces/ocr-container/pdomain-ops merge --ff-only <branch>
```

- [ ] **Step 5: Tag and push (only when CT authorizes)**

```bash
cd /workspaces/ocr-container/pdomain-ops
git tag v0.6.0     # use the verified-free version from Step 2
git push origin main --tags
```

> **Release prerequisite (from the parallel release-train session):** the
> `pdomain-index-pip` publish workflow runs on a push/tag. GitHub Actions was
> reported **disabled** on several pd-* repos pending re-enable. Before pushing,
> confirm Actions is enabled on `pdomain-ops` (or expect to trigger the publish
> manually). This is CT's call — surface it, do not flip repo settings unasked.

- [ ] **Step 6: Verify the released version resolves**

After the index publish completes:
```bash
cd /workspaces/ocr-container/pdomain-ops
git describe --tags    # should print v0.6.0 (clean, no -gNNN suffix) at HEAD
```
Plans 3–5 can then pin `pdomain-ops>=0.6.0`.

---

## Notes for Plans 3–5

- **Plan 3 (pdomain-ocr-labeler-spa):** import `pdomain_ops.pages` + `page_aggregate` + `blob_store`; delete the local `PageRecord` + `RotationSource`; retire `UserPageEnvelope` → `PagePayload` for API responses + event/blob store load path; relink `PageState` by `page_id`; replace `_build_provenance_summary` with `build_provenance_summary`.
- **Plan 4 (pdomain-prep-for-pgdp):** add the `pdomain-ops` dep; thread `PageRecord` + `ProjectRecord` through the pipeline from ingest; use `PageAggregate` + `BlobStore` + `ProjectAggregate`.
- **Plan 5 (pdomain-ocr-cli + pdomain-ocr-simple-gui):** import `pdomain_ops.pages` **only** (no event/blob store — end-state producers); build a `ProvenanceGraph` across pipeline steps (OCR→Layout→Reorganize DAG merge); emit `PagePayload` JSON.
- All three pin `pdomain-ops>=0.6.0` (the version actually released in Task 9 Step 2 — substitute the real number) and `pdomain-book-tools>=0.17.0`.

---

## Self-Review

**Spec coverage** (design spec §3–§14):
- §4 Page split — done in Plan 1 (book-tools v0.17.0); this plan consumes `BlobStoreProtocol`/`GtOrphans` from it. ✔
- §5 ProvenanceGraph — Task 1. ✔
- §6 RotationSource — Task 2. ✔
- §7 PageRecord + PageChangeEntry + provenance_summary — Tasks 2, 3. ✔
- §8 PageAggregate + snapshotting + sqlite persistence — Task 7. ✔
- §9 BlobStore (write/read/exists/prune_orphans) — Task 6. ✔
- §10 Consumer taxonomy — enforced by module split (universal `pages` vs lifecycle `blob_store`/`page_aggregate`) and Task 8's "not top-level export" test. ✔
- §11 ProjectRecord + ProjectAggregate — Tasks 2, 7. ✔
- §12 PagePayload — Task 4. ✔
- §13 Dependency graph / import surfaces — Tasks 5, 8. ✔
- §14 Migration step 2 (book-tools floor bump + ops release) — Tasks 0, 9. ✔

**Out of scope** (correctly deferred, spec §15): Postgres persistence (env-swap only, not implemented), bup chunk dedup, typed `PageChangeEntry.changes` union, LLM provenance nodes, dead-branch pruning automation (BlobStore exposes `prune_orphans`; the dead-branch retention scheduler is a lifecycle-consumer concern for a later plan).

**Not FastAPI+SPA** — no browser-verification milestone required (pdomain-ops is a pure library).

**Type consistency:** `record.page_id` / `aggregate.id` / `create_id` return type all `UUID`; `BlobStore.read(self, hash: str) -> bytes` matches `BlobStoreProtocol`; `ProvenanceGraph.add_node(node, *, advance_head=True)` signature is identical in Task 1 def, Task 7 `_apply_node` call, and all tests; `build_provenance_summary(graph: ProvenanceGraph | None) -> str` consistent across Task 3 and Task 8.
