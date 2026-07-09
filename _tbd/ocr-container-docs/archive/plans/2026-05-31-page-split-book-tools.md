# Page Split — pdomain-book-tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strip all operational metadata from `Page`, add `page_id` (stable UUID identity), replace `image_array` InitVar with a blob-store-protocol lazy-load model, add `GtOrphans` for unmatched GT entries at all levels.

**Architecture:** `Page` becomes a pure in-memory OCR content tree. Operational fields (`image_path`, `source`, `ocr_failed`, `ocr_provenance`, `provenance_*`, `rotation_applied`, `original_ocr_tool_text`, `original_ground_truth_text`) are removed entirely — they will be owned by `PageRecord` in `pdomain-ops` (Plan 2). Image access moves to `get_image(blob_store)` / `get_thumbnail(blob_store)` via a `BlobStoreProtocol` defined here to avoid a circular dependency with `pdomain-ops`. `page_index` is retained on `Page` (deferred removal — used for training-image file naming; will be removed once all downstream consumers migrate).

**Tech Stack:** Python 3.11+, dataclasses, `uuid.UUID`, numpy ndarray, `typing.Protocol`, `cv2` (decode PNG), `oxipng` (not used here — blob writing happens in pdomain-ops). Tests: `uv run pytest -n auto`. Lint/format: `ruff`. CI: `make ci AI=1`.

**Spec:** `docs/specs/2026-05-31-page-record-ops-design.md`

**This plan covers pdomain-book-tools only.** Plans 2–5 cover pdomain-ops and downstream repos.

---

## Absorbed: pdomain rename releases (folded in 2026-06-01)

This plan family (Plans 1–5) now **carries the remaining releases of the
pdomain-prefix rename** (`docs/plans/2026-05-31-pdomain-prefix-finalization.md`,
Stage 7 — deferred). The rename is fully merged on `main` in every repo; its
standalone release train was stopped after 3 repos. Each page-split release of a
repo below also ships its already-merged rename — do not cut a separate
rename-only release.

**Already released standalone (do NOT re-bump for the rename):**
`pdomain-book-tools` v0.16.0, `pdomain-ui` v0.3.0, `pdomain-ops` v0.5.0.

**Rename still unreleased — ship via this plan's release steps:**
`pdomain-ocr-cli`, `pdomain-ocr-training`, `pdomain-ocr-synth`,
`pdomain-ocr-trainer-spa`, `pdomain-prep-for-pgdp`, plus the two blocked apps
`pdomain-ocr-labeler-spa` and `pdomain-ocr-simple-gui`.

**Release prerequisites carried in from the rename plan (clear before releasing):**

1. **Enable GitHub Actions** (disabled by the org migration) on each unreleased
   repo before its release, or the release workflow silently never runs:
   `gh api --method PUT repos/pdomain/<repo>/actions/permissions --field enabled=true`.
   Still disabled: `pdomain-ocr-training`, `pdomain-ocr-synth`,
   `pdomain-ocr-labeler-spa`, `pdomain-ocr-trainer-spa`, `pdomain-ocr-simple-gui`,
   `pdomain-prep-for-pgdp`.
2. **`PD_NPM_DISPATCH_TOKEN` 403** + **`pdomain-index-npm` Pages env protection** —
   CT must rotate the token / adjust env rules so npm publishes auto-refresh
   (affects any future `pdomain-ui` release reaching downstream SPAs).
3. **`pdomain-ocr-cli` OCR preflight failure** (`rotated_page.png` → empty text)
   must be triaged before cli/prep release; prime suspect is the Stage-1 HF model
   relocation. See the rename plan's "Known release-preflight failure" note.

---

## File map

| File | Change |
|---|---|
| `pdomain_book_tools/ocr/gt_orphans.py` | **Create** — `GtOrphans` dataclass |
| `pdomain_book_tools/ocr/blob_protocol.py` | **Create** — `BlobStoreProtocol` |
| `pdomain_book_tools/ocr/page.py` | **Modify** — add `page_id`, `image_blob_hash`, `thumbnail_blob_hash`, lazy-load methods; remove 11 operational fields; replace `image_array` InitVar |
| `pdomain_book_tools/ocr/document.py` | **Modify** — remove `rotation_applied` assignment, remove `original_ocr_tool_text` assignment, return rotation choice via new return type |
| `pdomain_book_tools/ocr/reorganize_page_utils.py` | **Modify** — remove `page.image_path` access, accept `image_path` as parameter |
| `pdomain_book_tools/ocr/__init__.py` | **Modify** — export `GtOrphans`, `BlobStoreProtocol` |
| `tests/ocr/test_page.py` | **Modify** — update all `Page()` constructors, add `page_id`, remove stripped field assertions |
| `tests/ocr/test_page_pydantic_schema.py` | **Modify** — update schema tests |
| `tests/ocr/test_document.py` | **Modify** — update `rotation_applied` tests, update `original_ocr_tool_text` tests |
| `tests/ocr/test_page_coverage.py` | **Modify** — update coverage tests |
| `tests/test_page_behavior_pin.py` | **Modify** — update behavior pin tests |

---

## Milestone 1: GtOrphans + BlobStoreProtocol

### Task 1: Create `GtOrphans` and `BlobStoreProtocol`

**Files:**
- Create: `pdomain_book_tools/ocr/gt_orphans.py`
- Create: `pdomain_book_tools/ocr/blob_protocol.py`
- Test: `tests/ocr/test_gt_orphans.py`

- [ ] **Step 1: Write failing test for GtOrphans**

```python
# tests/ocr/test_gt_orphans.py
from pdomain_book_tools.ocr.gt_orphans import GtOrphans


def test_gt_orphans_defaults_empty():
    o = GtOrphans()
    assert o.words == []
    assert o.lines == []
    assert o.paragraphs == []
    assert o.page == []


def test_gt_orphans_with_data():
    o = GtOrphans(words=["foo"], lines=["bar"], paragraphs=["baz"], page=["qux"])
    assert o.words == ["foo"]
    assert o.lines == ["bar"]
    assert o.paragraphs == ["baz"]
    assert o.page == ["qux"]


def test_gt_orphans_is_empty():
    assert GtOrphans().is_empty()
    assert not GtOrphans(words=["x"]).is_empty()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/ocr/test_gt_orphans.py -v
```
Expected: `ImportError` or `ModuleNotFoundError`

- [ ] **Step 3: Create `gt_orphans.py`**

```python
# pdomain_book_tools/ocr/gt_orphans.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GtOrphans:
    """GT entries that could not be matched to any OCR content during GtMapped.

    Preserved so the labeler can surface unmatched ground truth to the reviewer.
    Pages with no GT mapping will never populate this — it stays None on Page.
    """

    words: list[object] = field(default_factory=list)
    lines: list[object] = field(default_factory=list)
    paragraphs: list[object] = field(default_factory=list)
    page: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.words or self.lines or self.paragraphs or self.page)
```

- [ ] **Step 4: Create `blob_protocol.py`**

```python
# pdomain_book_tools/ocr/blob_protocol.py
from __future__ import annotations

from typing import Protocol


class BlobStoreProtocol(Protocol):
    """Minimum interface Page needs from a blob store.

    Defined here (in pdomain-book-tools) so Page can type-hint get_image() and
    get_thumbnail() without importing pdomain-ops — which would create a circular
    dependency (pdomain-ops depends on pdomain-book-tools).

    The concrete BlobStore in pdomain-ops implements this protocol.
    """

    def read(self, hash: str) -> bytes:
        """Return raw bytes for a blob identified by its SHA256 hash."""
        ...
```

- [ ] **Step 5: Run test to verify it passes**

```bash
uv run pytest tests/ocr/test_gt_orphans.py -v
```
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add pdomain_book_tools/ocr/gt_orphans.py pdomain_book_tools/ocr/blob_protocol.py tests/ocr/test_gt_orphans.py
git commit -m "feat: add GtOrphans dataclass and BlobStoreProtocol"
```

---

## Milestone 2: Page — add new fields

### Task 2: Add `page_id`, `image_blob_hash`, `thumbnail_blob_hash`, `gt_orphans` to `Page`

**Files:**
- Modify: `pdomain_book_tools/ocr/page.py`
- Test: `tests/ocr/test_page.py`

- [ ] **Step 1: Write failing tests for new fields**

Add to `tests/ocr/test_page.py`:

```python
from uuid import UUID
from pdomain_book_tools.ocr.gt_orphans import GtOrphans


def test_page_has_page_id(minimal_page):
    """page_id must be a UUID assigned at construction."""
    assert isinstance(minimal_page.page_id, UUID)


def test_page_id_unique():
    """Two Pages constructed without explicit page_id get different UUIDs."""
    from pdomain_book_tools.ocr.page import Page
    p1 = Page(width=100, height=100, page_index=0)
    p2 = Page(width=100, height=100, page_index=0)
    assert p1.page_id != p2.page_id


def test_page_id_explicit():
    from uuid import uuid4
    from pdomain_book_tools.ocr.page import Page
    uid = uuid4()
    p = Page(width=100, height=100, page_index=0, page_id=uid)
    assert p.page_id == uid


def test_page_image_blob_hash_default_none(minimal_page):
    assert minimal_page.image_blob_hash is None


def test_page_thumbnail_blob_hash_default_none(minimal_page):
    assert minimal_page.thumbnail_blob_hash is None


def test_page_gt_orphans_default_none(minimal_page):
    assert minimal_page.gt_orphans is None


def test_page_gt_orphans_set():
    from pdomain_book_tools.ocr.page import Page
    orphans = GtOrphans(lines=["unmatched line"])
    p = Page(width=100, height=100, page_index=0, gt_orphans=orphans)
    assert p.gt_orphans.lines == ["unmatched line"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/ocr/test_page.py -k "page_id or blob_hash or gt_orphans" -v
```
Expected: FAIL — `Page` does not yet have these fields.

- [ ] **Step 3: Add new fields to `Page` in `page.py`**

In the `Page` dataclass body, after the existing `page_index: int` field, add:

```python
from uuid import UUID, uuid4
from pdomain_book_tools.ocr.gt_orphans import GtOrphans
from pdomain_book_tools.ocr.blob_protocol import BlobStoreProtocol

# In the dataclass body:
page_id: UUID = field(default_factory=uuid4)
image_blob_hash: str | None = None
thumbnail_blob_hash: str | None = None
gt_orphans: GtOrphans | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/ocr/test_page.py -k "page_id or blob_hash or gt_orphans" -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pdomain_book_tools/ocr/page.py tests/ocr/test_page.py
git commit -m "feat(page): add page_id, image_blob_hash, thumbnail_blob_hash, gt_orphans"
```

---

## Milestone 3: Lazy image loading

### Task 3: Replace `image_array` InitVar with blob-backed lazy load

**Files:**
- Modify: `pdomain_book_tools/ocr/page.py`
- Test: `tests/ocr/test_page.py`

- [ ] **Step 1: Write failing tests**

```python
def test_get_image_returns_none_without_hash(minimal_page):
    """get_image() returns None when image_blob_hash is not set."""
    from unittest.mock import MagicMock
    blob_store = MagicMock()
    assert minimal_page.get_image(blob_store) is None
    blob_store.read.assert_not_called()


def test_get_image_lazy_loads_from_blob(tmp_path):
    """get_image() decodes PNG bytes from blob store on first call."""
    import cv2
    import numpy as np
    from pdomain_book_tools.ocr.page import Page

    # Create a minimal 4x4 white PNG in memory
    img = np.ones((4, 4, 3), dtype=np.uint8) * 255
    png_bytes = cv2.imencode(".png", img)[1].tobytes()

    from unittest.mock import MagicMock
    blob_store = MagicMock()
    blob_store.read.return_value = png_bytes

    p = Page(width=4, height=4, page_index=0, image_blob_hash="abc123")
    result = p.get_image(blob_store)
    assert result is not None
    assert result.shape == (4, 4, 3)
    blob_store.read.assert_called_once_with("abc123")


def test_get_image_caches_result(tmp_path):
    """get_image() caches the ndarray — blob store called only once."""
    import cv2
    import numpy as np
    from pdomain_book_tools.ocr.page import Page
    from unittest.mock import MagicMock

    img = np.ones((4, 4, 3), dtype=np.uint8) * 255
    png_bytes = cv2.imencode(".png", img)[1].tobytes()
    blob_store = MagicMock()
    blob_store.read.return_value = png_bytes

    p = Page(width=4, height=4, page_index=0, image_blob_hash="abc123")
    first = p.get_image(blob_store)
    second = p.get_image(blob_store)
    assert first is second
    assert blob_store.read.call_count == 1


def test_get_thumbnail_returns_none_without_hash(minimal_page):
    from unittest.mock import MagicMock
    blob_store = MagicMock()
    assert minimal_page.get_thumbnail(blob_store) is None


def test_image_array_property_returns_cache(tmp_path):
    """image_array property returns the in-memory cache (backward compat read)."""
    import numpy as np
    from pdomain_book_tools.ocr.page import Page
    p = Page(width=4, height=4, page_index=0)
    assert p.image_array is None
    arr = np.zeros((4, 4, 3), dtype=np.uint8)
    p._image_array = arr
    assert p.image_array is arr
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/ocr/test_page.py -k "get_image or get_thumbnail or image_array_property" -v
```
Expected: FAIL

- [ ] **Step 3: Replace `image_array` InitVar, add `_image_array`/`_thumbnail_array` caches and lazy-load methods**

In `page.py`:

**Remove** the `image_array: InitVar[ndarray | None] = None` field declaration.

**Replace** the existing `_cv2_numpy_page_image` field with:
```python
_image_array: ndarray | None = field(
    default=None, init=False, repr=False, compare=False
)
_thumbnail_array: ndarray | None = field(
    default=None, init=False, repr=False, compare=False
)
```

**Remove** the `__post_init__` block that handled `image_array` (sets `self.cv2_numpy_page_image = image_array`). Keep the rest of `__post_init__` intact.

**Update** the `image_array` property to return `_image_array`:
```python
@property
def image_array(self) -> ndarray | None:
    return self._image_array
```

**Update** `cv2_numpy_page_image` property similarly (backward-compat alias):
```python
@property
def cv2_numpy_page_image(self) -> ndarray | None:
    return self._image_array
```

**Add** `get_image` and `get_thumbnail` methods after the existing properties:
```python
def get_image(self, blob_store: BlobStoreProtocol) -> ndarray | None:
    """Return the upright page image, lazy-loading from blob store if needed.

    Returns None if image_blob_hash is not set.
    The decoded ndarray is cached; subsequent calls do not hit the blob store.
    """
    if self._image_array is None and self.image_blob_hash is not None:
        import cv2
        import numpy as np
        data = blob_store.read(self.image_blob_hash)
        arr = np.frombuffer(data, dtype=np.uint8)
        self._image_array = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return self._image_array

def get_thumbnail(self, blob_store: BlobStoreProtocol) -> ndarray | None:
    """Return the page thumbnail, lazy-loading from blob store if needed.

    Returns None if thumbnail_blob_hash is not set.
    """
    if self._thumbnail_array is None and self.thumbnail_blob_hash is not None:
        import cv2
        import numpy as np
        data = blob_store.read(self.thumbnail_blob_hash)
        arr = np.frombuffer(data, dtype=np.uint8)
        self._thumbnail_array = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return self._thumbnail_array
```

**Update** `cv2_numpy_page_image` setter to set `_image_array`:
```python
@cv2_numpy_page_image.setter
def cv2_numpy_page_image(self, value: ndarray | None) -> None:
    self._image_array = value
```

**Update** the deprecated `__init__` shim at the bottom of the file (the one that translates `cv2_numpy_page_image=` → `image_array=`) — it no longer sets `image_array`; instead set `_image_array` directly:
```python
# In the shim __init__ wrapper:
if cv2_numpy_page_image is not None:
    page_instance._image_array = cv2_numpy_page_image
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/ocr/test_page.py -k "get_image or get_thumbnail or image_array" -v
```
Expected: PASS

- [ ] **Step 5: Run full test suite to catch regressions**

```bash
make test AI=1
```
Expected: PASS. If any test passes `image_array=` to `Page()`, it now fails — fix those callers to set `page._image_array` directly in tests, or construct without image then assign.

- [ ] **Step 6: Commit**

```bash
git add pdomain_book_tools/ocr/page.py tests/ocr/test_page.py
git commit -m "feat(page): replace image_array InitVar with blob-backed lazy-load (get_image/get_thumbnail)"
```

---

## Milestone 4: Remove operational fields

### Task 4: Remove `image_path`, `source`, `ocr_failed`, `ocr_provenance`, `provenance_*`, `rotation_applied`

**Files:**
- Modify: `pdomain_book_tools/ocr/page.py`
- Modify: `pdomain_book_tools/ocr/document.py`
- Modify: `pdomain_book_tools/ocr/reorganize_page_utils.py`

- [ ] **Step 1: Write failing tests confirming fields are gone**

```python
def test_page_has_no_image_path():
    from pdomain_book_tools.ocr.page import Page
    p = Page(width=100, height=100, page_index=0)
    assert not hasattr(p, "image_path")

def test_page_has_no_source():
    from pdomain_book_tools.ocr.page import Page
    p = Page(width=100, height=100, page_index=0)
    assert not hasattr(p, "source")

def test_page_has_no_rotation_applied():
    from pdomain_book_tools.ocr.page import Page
    p = Page(width=100, height=100, page_index=0)
    assert not hasattr(p, "rotation_applied")

def test_page_has_no_ocr_provenance():
    from pdomain_book_tools.ocr.page import Page
    p = Page(width=100, height=100, page_index=0)
    assert not hasattr(p, "ocr_provenance")
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/ocr/test_page.py -k "has_no_" -v
```
Expected: FAIL (fields still present)

- [ ] **Step 3: Remove fields from `Page` dataclass body in `page.py`**

Remove these field declarations from the `Page` dataclass body:
```python
# DELETE:
image_path: pathlib.Path | str | None = None
source: str = "ocr"
ocr_failed: bool = False
provenance_live_ocr: JsonDict | None = None
provenance_saved_ocr: JsonDict | None = None
provenance_saved: JsonDict | None = None
rotation_applied: int = 0
ocr_provenance: OCRProvenance | JsonDict | None = None
original_ocr_tool_text: str | None = ""
original_ground_truth_text: str | None = ""
unmatched_ground_truth_lines: list[object] | None = None
```

**Keep:** `name`, `page_id`, `image_blob_hash`, `thumbnail_blob_hash`, `gt_orphans`, and all OCR content fields (`width`, `height`, `page_index`, `blocks`, `bounding_box`, `page_labels`, `review`).

Remove the `page_source` property (it was an alias for `source`).

Remove from `__post_init__`:
- `self.ocr_provenance = OCRProvenance.coerce(self.ocr_provenance)`
- `if self.rotation_applied not in (0, 90, 180, 270): raise ...`
- `if not self.unmatched_ground_truth_lines: self.unmatched_ground_truth_lines = []`

Remove from `to_dict()`: all references to removed fields.

Remove from `from_dict()` / `copy()`: all references to removed fields.

Remove unused import: `from pdomain_book_tools.ocr.provenance import OCRProvenance` (if no longer used in page.py — check first).

- [ ] **Step 4: Update `document.py`**

`document.py:232` currently does:
```python
ocr_page.rotation_applied = chosen
```
Remove this assignment. The method that contains it (search `document.py` for `rotation_applied = chosen` to find the exact method name) must be updated to return the chosen rotation angle alongside the `Page` so callers can store it on `PageRecord`:

```python
# Pattern — find the exact method name in document.py and apply this shape:
# Before:
#   page.rotation_applied = chosen
#   return page
#
# After:
#   return page, chosen   # caller stores `chosen` on PageRecord.rotation_degrees
```

Update all callers of that method within `document.py` to unpack the tuple `(page, rotation_degrees)`.

`document.py:985` currently does:
```python
result.pages[0].original_ocr_tool_text = tesseract_string
```
Remove this assignment — `original_ocr_tool_text` is gone. The tesseract string is now returned separately or recorded in the `OcrCompleted` event config (Plan 2). For now, simply remove the assignment and update the return/result accordingly.

- [ ] **Step 5: Update `reorganize_page_utils.py`**

Line 1595 accesses `page.image_path`:
```python
# Before:
or (pathlib.Path(page.image_path).stem if page.image_path else None)

# After: accept image_path as an optional parameter
```

Find the function containing this line and add `image_path: pathlib.Path | str | None = None` as a keyword argument. Replace the `page.image_path` reference with the new parameter. Update all call sites within pdomain-book-tools.

- [ ] **Step 6: Run failing tests**

```bash
uv run pytest tests/ocr/test_page.py -k "has_no_" -v
```
Expected: PASS

- [ ] **Step 7: Run full suite**

```bash
make test AI=1
```
Fix any remaining failures — these will be tests that construct `Page` with removed fields or assert their presence.

- [ ] **Step 8: Commit**

```bash
git add pdomain_book_tools/ocr/page.py pdomain_book_tools/ocr/document.py pdomain_book_tools/ocr/reorganize_page_utils.py tests/
git commit -m "feat(page): remove operational metadata fields (image_path, source, provenance, rotation_applied, etc)"
```

---

## Milestone 5: Serialization + `unmatched_ground_truth_lines` → `gt_orphans`

### Task 5: Update `to_dict` / `from_dict`, replace `unmatched_ground_truth_lines`

**Files:**
- Modify: `pdomain_book_tools/ocr/page.py`
- Test: `tests/ocr/test_page_pydantic_schema.py`, `tests/ocr/test_page.py`

- [ ] **Step 1: Write failing tests**

```python
def test_to_dict_includes_page_id(minimal_page):
    d = minimal_page.to_dict()
    assert "page_id" in d
    assert isinstance(d["page_id"], str)  # UUID serialized as str


def test_to_dict_excludes_removed_fields(minimal_page):
    d = minimal_page.to_dict()
    for field in ("image_path", "source", "ocr_failed", "ocr_provenance",
                  "rotation_applied", "original_ocr_tool_text",
                  "original_ground_truth_text", "unmatched_ground_truth_lines",
                  "provenance_live_ocr", "provenance_saved_ocr", "provenance_saved"):
        assert field not in d, f"Unexpected field in to_dict: {field}"


def test_from_dict_round_trip_with_page_id(minimal_page):
    from pdomain_book_tools.ocr.page import Page
    d = minimal_page.to_dict()
    restored = Page.from_dict(d)
    assert restored.page_id == minimal_page.page_id


def test_to_dict_includes_gt_orphans_when_set():
    from pdomain_book_tools.ocr.page import Page
    from pdomain_book_tools.ocr.gt_orphans import GtOrphans
    p = Page(width=100, height=100, page_index=0,
             gt_orphans=GtOrphans(lines=["orphan"]))
    d = p.to_dict()
    assert "gt_orphans" in d
    assert d["gt_orphans"]["lines"] == ["orphan"]
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/ocr/test_page.py -k "to_dict or from_dict" -v
```

- [ ] **Step 3: Update `to_dict()` in `page.py`**

```python
def to_dict(self) -> JsonDict:
    result: JsonDict = {
        "page_id": str(self.page_id),
        "page_index": self.page_index,
        "width": self.width,
        "height": self.height,
        "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
        "items": [item.to_dict() for item in self.items] if self.items else [],
        "page_labels": self.page_labels,
        "original_ocr_tool_text": None,       # field removed; keep key for format compat
        "original_ground_truth_text": None,   # field removed; keep key for format compat
    }
    if self.name is not None:
        result["name"] = self.name
    if self.review is not None:
        result["review"] = self.review.to_dict()
    if self.image_blob_hash is not None:
        result["image_blob_hash"] = self.image_blob_hash
    if self.thumbnail_blob_hash is not None:
        result["thumbnail_blob_hash"] = self.thumbnail_blob_hash
    if self.gt_orphans is not None and not self.gt_orphans.is_empty():
        result["gt_orphans"] = {
            "words": self.gt_orphans.words,
            "lines": self.gt_orphans.lines,
            "paragraphs": self.gt_orphans.paragraphs,
            "page": self.gt_orphans.page,
        }
    return result
```

- [ ] **Step 4: Update `from_dict()` in `page.py`**

```python
@classmethod
def from_dict(cls, data: JsonDict) -> Page:
    from uuid import UUID
    from pdomain_book_tools.ocr.gt_orphans import GtOrphans

    gt_raw = data.get("gt_orphans")
    gt_orphans = None
    if gt_raw:
        gt_orphans = GtOrphans(
            words=gt_raw.get("words", []),
            lines=gt_raw.get("lines", []),
            paragraphs=gt_raw.get("paragraphs", []),
            page=gt_raw.get("page", []),
        )

    page_id_raw = data.get("page_id")
    page_id = UUID(page_id_raw) if page_id_raw else uuid4()

    return cls(
        page_id=page_id,
        page_index=int(cast("str | float | int", data["page_index"])),
        width=int(data["width"]),
        height=int(data["height"]),
        # ... existing block/bbox reconstruction ...
        image_blob_hash=data.get("image_blob_hash"),
        thumbnail_blob_hash=data.get("thumbnail_blob_hash"),
        gt_orphans=gt_orphans,
    )
```

Note: preserve all existing block/bbox/review reconstruction logic — only add the new fields.

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/ocr/test_page.py tests/ocr/test_page_pydantic_schema.py -v
```
Expected: PASS

- [ ] **Step 6: Run full suite**

```bash
make test AI=1
```

- [ ] **Step 7: Commit**

```bash
git add pdomain_book_tools/ocr/page.py tests/
git commit -m "feat(page): update to_dict/from_dict for page_id, gt_orphans; remove serialization of stripped fields"
```

---

## Milestone 6: Exports + backwards-compat audit

### Task 6: Update `__init__.py` exports and run conformance tests

**Files:**
- Modify: `pdomain_book_tools/ocr/__init__.py`
- Test: `tests/test_page_behavior_pin.py`

- [ ] **Step 1: Update `ocr/__init__.py` to export new types**

```python
# Add to exports in pdomain_book_tools/ocr/__init__.py:
from pdomain_book_tools.ocr.gt_orphans import GtOrphans
from pdomain_book_tools.ocr.blob_protocol import BlobStoreProtocol
```

- [ ] **Step 2: Run behavior pin tests**

```bash
uv run pytest tests/test_page_behavior_pin.py tests/test_page_model_doc.py -v
```

Fix any failures from removed fields. These tests pin observable behavior — update assertions that checked for removed fields, replacing them with assertions that confirm the fields are absent.

- [ ] **Step 3: Run full CI**

```bash
make ci AI=1
```
Expected: PASS. This is the green gate before cutting a release.

- [ ] **Step 4: Commit any remaining fixes**

```bash
git add -p
git commit -m "chore(page): update behavior pin tests and exports after operational field removal"
```

---

## Milestone 7: Version bump and release

### Task 7: Bump version and publish

**Files:**
- Modify: `pyproject.toml` (version field)
- Modify: `CHANGELOG.md` or equivalent

- [ ] **Step 1: Bump minor version**

This is a **breaking change** to `Page`'s public API. Bump the minor version (e.g. `0.15.2` → `0.16.0`).

In `pyproject.toml`:
```toml
[project]
version = "0.16.0"   # was 0.15.2
```

- [ ] **Step 2: Run CI one final time**

```bash
make ci AI=1
```
Expected: PASS

- [ ] **Step 3: Commit and tag**

```bash
git add pyproject.toml
git commit -m "chore: bump version to 0.16.0 — Page operational field removal"
git tag v0.16.0
```

- [ ] **Step 4: Push (when CT authorizes)**

```bash
git push origin main --tags
```

After push, the `pdomain-index-pip` release CI will publish the wheel. Downstream Plans 2–5 can then update their floor pins to `pdomain-book-tools>=0.16.0`.

---

## Notes for Plans 2–5

- **Plan 2 (pdomain-ops)**: Add `PageRecord`, `ProvenanceGraph`, `PageAggregate`, `BlobStore`. `BlobStore` implements `BlobStoreProtocol` from this plan. `RotationSource` moves here from labeler-spa.
- **Plan 3 (pdomain-ocr-labeler-spa)**: Replace local `PageRecord`, retire `UserPageEnvelope`, update all `Page` constructors (remove `image_path=`, `source=`, `rotation_applied=`, etc.), update `PageState` to link by `page_id`.
- **Plan 4 (pdomain-prep-for-pgdp)**: Add pdomain-ops dep, thread `PageRecord` through pipeline from ingest. Update all `Page` constructors.
- **Plan 5 (pdomain-ocr-cli + pdomain-ocr-simple-gui)**: Update `Page` constructors, add basic provenance.

All downstream plans must pin `pdomain-book-tools>=0.16.0` in their `pyproject.toml`.
