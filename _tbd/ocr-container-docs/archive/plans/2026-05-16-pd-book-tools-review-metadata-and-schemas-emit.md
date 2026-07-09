---
status: complete
---

# pdomain-book-tools — ReviewMetadata + schemas.emit CLI

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional `review: ReviewMetadata | None` field to `Word`, `Block`, and `Page` in `pdomain-book-tools`, and ship a `python -m pd_book_tools.schemas.emit` CLI that dumps every public domain model as JSON Schema for downstream codegen (pdomain-ui, pdomain-ocr-ops).

**Architecture:** pdomain-book-tools models are stdlib `@dataclass`, not Pydantic. Add a new `ReviewMetadata` dataclass under `pd_book_tools/ocr/review.py` with three fields (`validated`, `reviewer_note`, `flagged_for_attention`). Wire it as an optional field on existing `Word`/`Block`/`Page` dataclasses, updating their `to_dict`/`from_dict` to preserve the existing wire shape when `review` is absent (the new key only appears in the dict when set). Add `pd_book_tools/schemas/emit.py` — a CLI that uses `pydantic.TypeAdapter(<model>).json_schema()` to emit JSON Schema for each public model. `TypeAdapter` works on plain stdlib dataclasses in Pydantic 2; no need to migrate any existing class.

**Tech Stack:** Python 3.10+, hatchling build backend, stdlib `@dataclass` models, pytest via `uv run pytest -n auto`, new direct dep: `pydantic>=2.0` (used only for `TypeAdapter` in the schema emitter).

**Scope explicitly deferred to a follow-up plan:** `GTMatchMetadata` cluster refactor. The existing top-level Word fields `ground_truth_text`, `ground_truth_bounding_box`, `ground_truth_match_keys` already serve most of the matching role; clustering them into `matching: GTMatchMetadata | None` is a larger refactor of every caller and is best done in its own plan. This plan adds only `review`, which has no existing top-level equivalent.

**Working directory for all commands:** `/workspaces/ocr-container/pdomain-book-tools/`

---

## Task 1: Add `pydantic>=2.0` as a direct dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Inspect current dependencies**

Run: `grep -n "pydantic" pyproject.toml uv.lock 2>&1 | head -5`
Expected: pydantic may appear in `uv.lock` (transitive via doctr/transformers) but NOT in `pyproject.toml` `[project].dependencies`.

- [ ] **Step 2: Add the direct dependency**

Find the `dependencies = [...]` list in `pyproject.toml` (under `[project]`). Add a line, sorted alphabetically, between `"pillow-avif-plugin>=1.4",` and `"pytesseract (>=0.3.13,<0.4.0)",`:

```toml
    "pydantic>=2.0",
```

The comment block above pillow-avif-plugin lines should remain undisturbed. The new line ends with a comma so the list remains valid.

- [ ] **Step 3: Sync the lockfile**

Run: `uv sync`
Expected: lockfile updated; pydantic now appears as a direct dep. No version conflicts.

- [ ] **Step 4: Smoke-test the import**

Run: `uv run python -c "from pydantic import TypeAdapter; print('ok')"`
Expected output: `ok`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "$(cat <<'EOF'
chore(deps): add pydantic>=2.0 as direct dependency

Needed for the upcoming pd_book_tools.schemas.emit CLI, which uses
pydantic.TypeAdapter to dump JSON Schema for stdlib @dataclass models.
Pydantic was already transitively present (doctr / transformers); this
elevates it to a direct dep so the schema-emission code can rely on it
without breaking under transitive-dep churn.
EOF
)"
```

---

## Task 2: Create the `ReviewMetadata` dataclass

**Files:**
- Create: `pd_book_tools/ocr/review.py`
- Create: `tests/ocr/test_review_metadata.py`

- [ ] **Step 1: Write the failing test**

Create `tests/ocr/test_review_metadata.py`:

```python
"""Tests for the ReviewMetadata dataclass on pd_book_tools.ocr.review."""
from __future__ import annotations

import pytest

from pd_book_tools.ocr.review import ReviewMetadata


def test_review_metadata_defaults():
    rm = ReviewMetadata()
    assert rm.validated is False
    assert rm.reviewer_note is None
    assert rm.flagged_for_attention is False


def test_review_metadata_explicit_values():
    rm = ReviewMetadata(
        validated=True,
        reviewer_note="checked against original",
        flagged_for_attention=False,
    )
    assert rm.validated is True
    assert rm.reviewer_note == "checked against original"
    assert rm.flagged_for_attention is False


def test_review_metadata_to_dict_full():
    rm = ReviewMetadata(
        validated=True,
        reviewer_note="ok",
        flagged_for_attention=True,
    )
    assert rm.to_dict() == {
        "validated": True,
        "reviewer_note": "ok",
        "flagged_for_attention": True,
    }


def test_review_metadata_to_dict_defaults_omit_none_note():
    rm = ReviewMetadata()
    d = rm.to_dict()
    # validated and flagged_for_attention always present (bools);
    # reviewer_note is included as None so consumers can disambiguate
    # "absent field" vs "explicit null" — the rule: to_dict is the wire shape,
    # absent fields handled at the parent (Word/Block/Page) level by
    # omitting `review` entirely when None.
    assert d == {
        "validated": False,
        "reviewer_note": None,
        "flagged_for_attention": False,
    }


def test_review_metadata_from_dict_full():
    rm = ReviewMetadata.from_dict({
        "validated": True,
        "reviewer_note": "n",
        "flagged_for_attention": True,
    })
    assert rm == ReviewMetadata(
        validated=True,
        reviewer_note="n",
        flagged_for_attention=True,
    )


def test_review_metadata_from_dict_missing_keys_use_defaults():
    rm = ReviewMetadata.from_dict({"validated": True})
    assert rm == ReviewMetadata(
        validated=True,
        reviewer_note=None,
        flagged_for_attention=False,
    )


def test_review_metadata_roundtrip():
    rm = ReviewMetadata(validated=True, reviewer_note="hi", flagged_for_attention=True)
    assert ReviewMetadata.from_dict(rm.to_dict()) == rm
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/ocr/test_review_metadata.py -v`
Expected: All tests FAIL with `ModuleNotFoundError: No module named 'pd_book_tools.ocr.review'`.

- [ ] **Step 3: Implement `ReviewMetadata`**

Create `pd_book_tools/ocr/review.py`:

```python
"""Human-review metadata for OCR words, lines (blocks), and pages.

This module is foundation-level: it carries no per-app logic and is
designed to be shared across every consumer of pdomain-book-tools data models
(labeler, pgdp-prep, proofreader, simple-ocr-gui).

The dataclass is intentionally minimal in this first revision. A future
extension migrates ``ReviewMetadata`` to a list of per-pass review
records (P1/P2/P3/F1/F2 in Distributed Proofreaders parlance) once the
proofreader app spec lands. Until then, treat it as a single most-recent
review state.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReviewMetadata:
    """Human-review state on a Word, Block (line), or Page.

    Fields:
        validated:            A reviewer has confirmed this item is correct.
        reviewer_note:        Optional free-text note left by the reviewer.
        flagged_for_attention: Flagged for follow-up review by a different
                               reviewer or for an automated pass.
    """

    validated: bool = False
    reviewer_note: str | None = None
    flagged_for_attention: bool = False

    def to_dict(self) -> dict:
        return {
            "validated": self.validated,
            "reviewer_note": self.reviewer_note,
            "flagged_for_attention": self.flagged_for_attention,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ReviewMetadata":
        return cls(
            validated=d.get("validated", False),
            reviewer_note=d.get("reviewer_note"),
            flagged_for_attention=d.get("flagged_for_attention", False),
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/ocr/test_review_metadata.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add pd_book_tools/ocr/review.py tests/ocr/test_review_metadata.py
git commit -m "feat(ocr): add ReviewMetadata dataclass

Shared human-review metadata for words, lines (blocks), and pages.
Three fields: validated, reviewer_note, flagged_for_attention. All
optional with sensible defaults. Roundtrips via to_dict/from_dict.

Foundation-level — no per-app logic. Future extension migrates to a
list of per-pass review records once the proofreader app spec lands."
```

---

## Task 3: Add `review` field to `Word`

**Files:**
- Modify: `pd_book_tools/ocr/word.py`
- Create: `tests/ocr/test_word_review.py`

- [ ] **Step 1: Write the failing test**

Create `tests/ocr/test_word_review.py`:

```python
"""Tests for Word.review (optional ReviewMetadata cluster)."""
from __future__ import annotations

import pytest

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.ocr.review import ReviewMetadata
from pd_book_tools.ocr.word import Word


def _bbox():
    # Use whatever shape BoundingBox accepts in this codebase — keep tests
    # consistent with existing Word fixtures.
    return BoundingBox.from_dict({
        "top_left": {"x": 0, "y": 0},
        "bottom_right": {"x": 10, "y": 10},
    })


def test_word_review_defaults_to_none():
    w = Word(text="hello", bounding_box=_bbox())
    assert w.review is None


def test_word_review_accepts_metadata():
    rm = ReviewMetadata(validated=True, reviewer_note="ok")
    w = Word(text="hello", bounding_box=_bbox(), review=rm)
    assert w.review is rm


def test_word_to_dict_omits_review_key_when_none():
    w = Word(text="hello", bounding_box=_bbox())
    d = w.to_dict()
    assert "review" not in d


def test_word_to_dict_includes_review_when_set():
    rm = ReviewMetadata(validated=True, reviewer_note="ok", flagged_for_attention=True)
    w = Word(text="hello", bounding_box=_bbox(), review=rm)
    d = w.to_dict()
    assert d["review"] == {
        "validated": True,
        "reviewer_note": "ok",
        "flagged_for_attention": True,
    }


def test_word_from_dict_without_review_key():
    base = {
        "type": "Word",
        "text": "hello",
        "bounding_box": _bbox().to_dict(),
    }
    w = Word.from_dict(base)
    assert w.review is None


def test_word_from_dict_with_review_key():
    base = {
        "type": "Word",
        "text": "hello",
        "bounding_box": _bbox().to_dict(),
        "review": {
            "validated": True,
            "reviewer_note": "n",
            "flagged_for_attention": False,
        },
    }
    w = Word.from_dict(base)
    assert w.review == ReviewMetadata(
        validated=True,
        reviewer_note="n",
        flagged_for_attention=False,
    )


def test_word_review_roundtrip():
    rm = ReviewMetadata(validated=True, reviewer_note="hi")
    w = Word(text="hello", bounding_box=_bbox(), review=rm)
    w2 = Word.from_dict(w.to_dict())
    assert w2.review == rm
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/ocr/test_word_review.py -v`
Expected: Tests fail — initially with `TypeError: __init__() got an unexpected keyword argument 'review'` for the constructor tests, and `AttributeError`/`KeyError` for the to_dict/from_dict tests.

- [ ] **Step 3: Add the `review` field to Word**

In `pd_book_tools/ocr/word.py`, near the top of the `Word` `@dataclass` block (alongside the other dataclass fields, *after* the `ClassVar` declarations and before any method definitions), add an import and a field. First the import — add to the top-of-file import block:

```python
from pd_book_tools.ocr.review import ReviewMetadata
```

Then add the field. Locate the `Word` field block (you'll see entries like `text: str`, `bounding_box: BoundingBox | None`, etc.). Add the following field, sorted alongside the existing optional fields (keep the existing field order otherwise — just append within the optional-fields section):

```python
    # Optional human-review metadata (Word-scope). None when no review pass
    # has touched this word. See pd_book_tools/ocr/review.py.
    review: ReviewMetadata | None = None
```

Then update `Word.to_dict()` (currently around line 624) to omit the `review` key when None and include it when set. Replace the existing `to_dict` `return { ... }` block with:

```python
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary"""
        d = {
            "type": "Word",
            "text": self.text,
            "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
            "ocr_confidence": self.ocr_confidence,
            "word_labels": self.word_labels,
            "text_style_labels": self.text_style_labels,
            "text_style_label_scopes": self.text_style_label_scopes,
            "word_components": self.word_components,
            "baseline": self.baseline,
            "ground_truth_text": (
                self.ground_truth_text if self.ground_truth_text else None
            ),
            "ground_truth_bounding_box": (
                self.ground_truth_bounding_box.to_dict()
                if self.ground_truth_bounding_box
                else None
            ),
            "ground_truth_match_keys": self.ground_truth_match_keys,
        }
        if self.review is not None:
            d["review"] = self.review.to_dict()
        return d
```

Update `Word.from_dict()` to parse `review` when present. Replace the existing `return Word(...)` block in `from_dict` with:

```python
    @classmethod
    def from_dict(cls, dict: dict) -> Word:
        """Create OCRWord from dictionary"""
        review = (
            ReviewMetadata.from_dict(dict["review"])
            if dict.get("review") is not None
            else None
        )
        return Word(
            text=dict["text"],
            bounding_box=BoundingBox.from_dict(dict["bounding_box"]),
            ocr_confidence=dict.get("ocr_confidence"),
            word_labels=dict.get("word_labels", []),
            text_style_labels=dict.get("text_style_labels", []),
            text_style_label_scopes=dict.get("text_style_label_scopes"),
            word_components=dict.get("word_components", []),
            baseline=dict.get("baseline"),
            ground_truth_text=dict.get("ground_truth_text"),
            ground_truth_bounding_box=(
                BoundingBox.from_dict(dict["ground_truth_bounding_box"])
                if dict.get("ground_truth_bounding_box")
                else None
            ),
            ground_truth_match_keys=dict.get("ground_truth_match_keys", {}),
            review=review,
        )
```

- [ ] **Step 4: Run the new test to verify it passes**

Run: `uv run pytest tests/ocr/test_word_review.py -v`
Expected: 7 passed.

- [ ] **Step 5: Run the full Word test suite to verify no regression**

Run: `uv run pytest tests/ocr/test_word.py tests/ocr/test_word_review.py -v 2>&1 | tail -30`
Expected: Pre-existing Word tests still pass; the 7 new tests also pass.

- [ ] **Step 6: Commit**

```bash
git add pd_book_tools/ocr/word.py tests/ocr/test_word_review.py
git commit -m "feat(ocr): add optional Word.review field

Optional ReviewMetadata cluster on Word; None when no review pass has
touched the word. to_dict omits the key when None to preserve the
existing wire shape for unreviewed corpora. from_dict accepts presence
or absence."
```

---

## Task 4: Add `review` field to `Block`

**Files:**
- Modify: `pd_book_tools/ocr/block.py`
- Create: `tests/ocr/test_block_review.py`

- [ ] **Step 1: Write the failing test**

Create `tests/ocr/test_block_review.py`:

```python
"""Tests for Block.review (optional ReviewMetadata cluster).

Block covers both block-scope and line-scope review semantics, since
'Line' in the pdomain-book-tools model is a Block with block_category=LINE."""
from __future__ import annotations

import pytest

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.review import ReviewMetadata


def _bbox():
    return BoundingBox.from_dict({
        "top_left": {"x": 0, "y": 0},
        "bottom_right": {"x": 100, "y": 50},
    })


def _line_block(words=None) -> Block:
    return Block(
        items=list(words or []),
        child_type=BlockChildType.WORDS,
        block_category=BlockCategory.LINE,
        bounding_box=_bbox(),
    )


def test_block_review_defaults_to_none():
    b = _line_block()
    assert b.review is None


def test_block_review_accepts_metadata():
    rm = ReviewMetadata(validated=True)
    b = _line_block()
    b.review = rm
    assert b.review is rm


def test_block_to_dict_omits_review_key_when_none():
    b = _line_block()
    d = b.to_dict()
    assert "review" not in d


def test_block_to_dict_includes_review_when_set():
    rm = ReviewMetadata(validated=True, reviewer_note="line ok")
    b = _line_block()
    b.review = rm
    d = b.to_dict()
    assert d["review"] == {
        "validated": True,
        "reviewer_note": "line ok",
        "flagged_for_attention": False,
    }


def test_block_from_dict_without_review_key():
    b = _line_block()
    base = b.to_dict()
    assert "review" not in base
    b2 = Block.from_dict(base)
    assert b2.review is None


def test_block_review_roundtrip():
    rm = ReviewMetadata(validated=True, reviewer_note="n")
    b = _line_block()
    b.review = rm
    b2 = Block.from_dict(b.to_dict())
    assert b2.review == rm
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/ocr/test_block_review.py -v`
Expected: tests fail with `AttributeError: 'Block' object has no attribute 'review'` and the to_dict/from_dict tests fail correspondingly.

- [ ] **Step 3: Add the `review` field to Block**

Open `pd_book_tools/ocr/block.py`. Add to the imports block:

```python
from pd_book_tools.ocr.review import ReviewMetadata
```

In the `Block` `@dataclass` body (declaration at line 29), add the new optional field alongside the other optional-field declarations:

```python
    # Optional human-review metadata (Block-scope; also serves line-scope
    # when block_category == LINE). See pd_book_tools/ocr/review.py.
    review: ReviewMetadata | None = None
```

Find `Block.to_dict()` in the file. Just before its `return` statement, build the dict into a local variable and add:

```python
        if self.review is not None:
            d["review"] = self.review.to_dict()
```

If the existing implementation returns a literal `{...}` directly, refactor to a local `d = {...}` then `return d` with the conditional insertion above. Preserve every existing key and order.

Find `Block.from_dict()`. Before constructing the `Block`, add:

```python
        review = (
            ReviewMetadata.from_dict(dict["review"])
            if dict.get("review") is not None
            else None
        )
```

And pass `review=review` in the Block constructor call.

- [ ] **Step 4: Run the new test to verify it passes**

Run: `uv run pytest tests/ocr/test_block_review.py -v`
Expected: 6 passed.

- [ ] **Step 5: Run the full Block test suite to verify no regression**

Run: `uv run pytest tests/ocr/test_block.py tests/ocr/test_block_review.py tests/ocr/test_block_coverage2.py -v 2>&1 | tail -30`
Expected: All pre-existing Block tests pass; the 6 new tests also pass.

- [ ] **Step 6: Commit**

```bash
git add pd_book_tools/ocr/block.py tests/ocr/test_block_review.py
git commit -m "feat(ocr): add optional Block.review field

Optional ReviewMetadata cluster on Block; covers both block-scope and
line-scope review semantics (line is Block with block_category=LINE).
to_dict omits the key when None; from_dict accepts presence or absence."
```

---

## Task 5: Add `review` field to `Page`

**Files:**
- Modify: `pd_book_tools/ocr/page.py`
- Create: `tests/ocr/test_page_review.py`

- [ ] **Step 1: Write the failing test**

Create `tests/ocr/test_page_review.py`:

```python
"""Tests for Page.review (optional ReviewMetadata cluster)."""
from __future__ import annotations

import pytest

from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.review import ReviewMetadata


def _minimal_page() -> Page:
    """Build a minimal Page suitable for review-field tests.

    Mirror whatever the smallest valid constructor call is in existing
    Page tests — typically empty `items` and small `width`/`height`."""
    return Page(items=[], width=100, height=100)


def test_page_review_defaults_to_none():
    p = _minimal_page()
    assert p.review is None


def test_page_review_accepts_metadata():
    rm = ReviewMetadata(validated=True, reviewer_note="page ok")
    p = _minimal_page()
    p.review = rm
    assert p.review is rm


def test_page_to_dict_omits_review_key_when_none():
    p = _minimal_page()
    d = p.to_dict()
    assert "review" not in d


def test_page_to_dict_includes_review_when_set():
    rm = ReviewMetadata(validated=True, flagged_for_attention=True)
    p = _minimal_page()
    p.review = rm
    d = p.to_dict()
    assert d["review"] == {
        "validated": True,
        "reviewer_note": None,
        "flagged_for_attention": True,
    }


def test_page_review_roundtrip():
    rm = ReviewMetadata(validated=True, reviewer_note="n", flagged_for_attention=True)
    p = _minimal_page()
    p.review = rm
    p2 = Page.from_dict(p.to_dict())
    assert p2.review == rm
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/ocr/test_page_review.py -v`
Expected: tests fail (`AttributeError: 'Page' object has no attribute 'review'`).

If `_minimal_page()` fails because Page's constructor differs from the assumed shape, open `pd_book_tools/ocr/page.py` at line 56 (the `@dataclass(eq=False)` `class Page:` declaration) and adapt the constructor call in the helper to whatever the minimal-valid shape is. Do not modify Page's signature for this — the fixture is what adapts.

- [ ] **Step 3: Add the `review` field to Page**

Open `pd_book_tools/ocr/page.py`. Add to the imports block:

```python
from pd_book_tools.ocr.review import ReviewMetadata
```

In the `Page` `@dataclass(eq=False)` body (line 57), add the new optional field alongside the other optional-field declarations:

```python
    # Optional human-review metadata (Page-scope). See
    # pd_book_tools/ocr/review.py.
    review: ReviewMetadata | None = None
```

Find `Page.to_dict()`. Build the dict into a local variable if it isn't already, then before `return`:

```python
        if self.review is not None:
            d["review"] = self.review.to_dict()
```

Find `Page.from_dict()`. Before constructing the `Page`, add:

```python
        review = (
            ReviewMetadata.from_dict(dict["review"])
            if dict.get("review") is not None
            else None
        )
```

And pass `review=review` in the Page constructor call.

- [ ] **Step 4: Run the new test to verify it passes**

Run: `uv run pytest tests/ocr/test_page_review.py -v`
Expected: 5 passed.

- [ ] **Step 5: Run page-related regression tests**

Run: `uv run pytest tests/ocr/test_page_coverage_ops.py tests/test_page_behavior_pin.py tests/ocr/test_page_review.py -v 2>&1 | tail -30`
Expected: pre-existing page tests still pass; the 5 new tests pass.

- [ ] **Step 6: Commit**

```bash
git add pd_book_tools/ocr/page.py tests/ocr/test_page_review.py
git commit -m "feat(ocr): add optional Page.review field

Optional ReviewMetadata cluster on Page; None when no page-scope review
has been recorded. to_dict omits the key when None; from_dict accepts
presence or absence. Matches the pattern landed for Word and Block."
```

---

## Task 6: Create the `pd_book_tools.schemas.emit` CLI

**Files:**
- Create: `pd_book_tools/schemas/__init__.py`
- Create: `pd_book_tools/schemas/__main__.py`
- Create: `pd_book_tools/schemas/emit.py`
- Create: `tests/test_schemas_emit.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_schemas_emit.py`:

```python
"""Tests for the pd_book_tools.schemas.emit CLI.

The CLI dumps a single JSON document on stdout. Keys are the model names
(Word, Block, Page, ReviewMetadata, BoundingBox, ...). Values are
JSON-Schema documents produced by pydantic.TypeAdapter on each stdlib
@dataclass model. The schema for ReviewMetadata is the easiest to pin
because the dataclass has no nested model dependencies."""
from __future__ import annotations

import json
import subprocess
import sys


def _run_emit() -> dict:
    """Invoke the CLI in the current uv environment, parse JSON stdout."""
    proc = subprocess.run(
        [sys.executable, "-m", "pd_book_tools.schemas.emit"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stderr == "" or proc.stderr.startswith("WARNING"), (
        f"unexpected stderr: {proc.stderr!r}"
    )
    return json.loads(proc.stdout)


def test_emit_returns_top_level_dict():
    out = _run_emit()
    assert isinstance(out, dict)


def test_emit_includes_review_metadata_schema():
    out = _run_emit()
    assert "ReviewMetadata" in out
    sch = out["ReviewMetadata"]
    # Pydantic TypeAdapter returns a JSON-Schema-shaped dict with at least
    # these standard keys for an object type.
    assert sch["type"] == "object"
    assert "properties" in sch
    assert set(sch["properties"].keys()) == {
        "validated",
        "reviewer_note",
        "flagged_for_attention",
    }


def test_emit_review_metadata_field_types():
    out = _run_emit()
    props = out["ReviewMetadata"]["properties"]
    assert props["validated"]["type"] == "boolean"
    # reviewer_note is `str | None` — JSON Schema represents this as
    # anyOf [string, null] (or oneOf depending on Pydantic version).
    note_schema = props["reviewer_note"]
    assert "anyOf" in note_schema or note_schema.get("type") == "string"
    assert props["flagged_for_attention"]["type"] == "boolean"


def test_emit_includes_word_block_page():
    out = _run_emit()
    for name in ("Word", "Block", "Page"):
        assert name in out, f"missing schema for {name}"
        assert out[name]["type"] == "object"


def test_emit_word_schema_has_review_field():
    out = _run_emit()
    word_props = out["Word"]["properties"]
    assert "review" in word_props
    # review is `ReviewMetadata | None` — should resolve to anyOf
    # including the ReviewMetadata schema (or a $ref to it).
    rev_schema = word_props["review"]
    assert "anyOf" in rev_schema or "$ref" in rev_schema
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_schemas_emit.py -v`
Expected: All 5 tests fail — `subprocess.CalledProcessError` because the module doesn't exist (`No module named pd_book_tools.schemas.emit`).

- [ ] **Step 3: Create the schemas package**

Create `pd_book_tools/schemas/__init__.py`:

```python
"""JSON-Schema emission for pdomain-book-tools public domain models.

The CLI entrypoint is ``python -m pd_book_tools.schemas.emit``. It
dumps a single JSON document on stdout with one key per public model
(Word, Block, Page, BoundingBox, ReviewMetadata, ...) and a JSON-Schema
document as the value, produced via :class:`pydantic.TypeAdapter` on
the stdlib ``@dataclass`` models.

Downstream consumers (pdomain-ocr-ops, pdomain-ui codegen) re-run this command
against a pinned wheel and feed the output to ``openapi-typescript`` or
equivalent.
"""
```

Create `pd_book_tools/schemas/__main__.py`:

```python
"""Allow ``python -m pd_book_tools.schemas`` to dispatch to .emit."""
from pd_book_tools.schemas.emit import main

if __name__ == "__main__":
    main()
```

Create `pd_book_tools/schemas/emit.py`:

```python
"""JSON-Schema emitter for pdomain-book-tools public domain models.

Invocation: ``python -m pd_book_tools.schemas.emit``

Emits a single JSON document on stdout, keyed by model class name, with
each value being a JSON-Schema document produced by
``pydantic.TypeAdapter(<dataclass>).json_schema()``.

Adding a new public model: import it below and add it to ``PUBLIC_MODELS``.
"""
from __future__ import annotations

import json
import sys
from typing import Any

from pydantic import TypeAdapter

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.ocr.block import Block
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.review import ReviewMetadata
from pd_book_tools.ocr.word import Word

# The single source of truth for what counts as a "public" model.
# Order is intentional: simple leaf types first, composite types after.
PUBLIC_MODELS: tuple[type, ...] = (
    BoundingBox,
    ReviewMetadata,
    Word,
    Block,
    Page,
)


def emit_schemas() -> dict[str, dict[str, Any]]:
    """Build {ModelName: json_schema} for every public model."""
    out: dict[str, dict[str, Any]] = {}
    for cls in PUBLIC_MODELS:
        out[cls.__name__] = TypeAdapter(cls).json_schema()
    return out


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. argv is accepted for testability but unused today."""
    schemas = emit_schemas()
    json.dump(schemas, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_schemas_emit.py -v`
Expected: 5 passed.

If any of `BoundingBox`, `Word`, `Block`, or `Page` makes `TypeAdapter` raise (e.g., a field references a non-serializable type like `numpy.ndarray` or a OpenCV image), narrow `PUBLIC_MODELS` for now — keep `ReviewMetadata` and any types whose `TypeAdapter` succeeds, and add a comment naming the failing type so a follow-up plan can decide whether to:
- add a Pydantic-friendly view of that field, or
- exclude that model from the emitter,
- or convert the offending field to a serializable shape.

If you narrow the list, also narrow `test_emit_includes_word_block_page` and `test_emit_word_schema_has_review_field` to the models that did emit successfully. Add an inline comment in the test referencing the narrowed list.

- [ ] **Step 5: Manual smoke test**

Run: `uv run python -m pd_book_tools.schemas.emit | python -m json.tool | head -40`
Expected: pretty-printed JSON output starting with `{` and showing the first model's schema. No traceback.

- [ ] **Step 6: Commit**

```bash
git add pd_book_tools/schemas/ tests/test_schemas_emit.py
git commit -m "feat(schemas): add python -m pd_book_tools.schemas.emit CLI

Dumps JSON Schema for every public domain model via
pydantic.TypeAdapter on the stdlib @dataclass declarations. Output is
a single JSON document keyed by class name. Downstream consumers
(pdomain-ui codegen, pdomain-ocr-ops) re-run this against a pinned wheel and
feed it to openapi-typescript or equivalent."
```

---

## Task 7: Document the new CLI and run the full CI gate

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Locate where to add the new section**

Run: `grep -n "^## " README.md | head -20`
Identify a sensible section heading near "Usage" / "CLI" / "Developer notes" (or whatever exists). Add the new content beneath the matching section.

- [ ] **Step 2: Add the section**

Append (or insert at the located position) a new section to `README.md`:

```markdown
## Emitting JSON Schema for downstream codegen

```sh
uv run python -m pd_book_tools.schemas.emit > schemas.json
```

The output is a single JSON document, keyed by public model class name
(`BoundingBox`, `ReviewMetadata`, `Word`, `Block`, `Page`, ...), whose
values are JSON-Schema documents produced by `pydantic.TypeAdapter`.
Downstream consumers (`pdomain-ocr-ops`, `pdomain-ui` codegen) re-run this command
against a pinned wheel and feed the output to `openapi-typescript` or
equivalent to keep TypeScript types in sync with the Python source of
truth.

The set of public models lives in
`pd_book_tools/schemas/emit.py::PUBLIC_MODELS`. Add new models there.
```
```

- [ ] **Step 3: Run the full CI gate**

Run: `make ci AI=1`
Expected: `make ci AI=1` completes with exit code 0. All pre-existing tests pass; the 23 new tests added by this plan pass.

If `make ci` fails, the failure must be addressed before the final commit — investigate root cause; do not bypass.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): document pd_book_tools.schemas.emit CLI

Brief usage example + pointer to PUBLIC_MODELS as the registration
surface for new emitted models."
```

---

## Self-review checklist (for the engineer; do this before the final commit)

- [ ] Every new dataclass field is `Optional` (defaults to `None`); no breaking change to any existing constructor.
- [ ] Every existing `to_dict` output preserves its prior key set when `review` is None — confirmed by the "omits review key when None" tests.
- [ ] Every existing `from_dict` accepts inputs both with and without `review` — confirmed by the corresponding tests.
- [ ] `pd_book_tools/ocr/review.py` is the ONLY new module under `pd_book_tools/ocr/`; no other refactors snuck in.
- [ ] `PUBLIC_MODELS` in `pd_book_tools/schemas/emit.py` covers Word, Block, Page, BoundingBox, ReviewMetadata at minimum.
- [ ] The CLI dispatch through `python -m pd_book_tools.schemas.emit` works without arguments — no positional / required flags.
- [ ] No new top-level dependency in `pyproject.toml` beyond `pydantic>=2.0`.
- [ ] `make ci AI=1` passes.

## Follow-up plans (not in scope here)

1. **`GTMatchMetadata` cluster refactor on Word.** Cluster the existing top-level `ground_truth_text`, `ground_truth_bounding_box`, `ground_truth_match_keys` fields under `matching: GTMatchMetadata | None`. Big — touches every caller in pgdp-prep / labeler-spa / pdomain-book-tools tests. Will be its own plan once consumers are ready for the refactor.
2. **Per-character bbox extraction landing.** `docs/specs/09-char-bbox-extraction.md` is still Draft; once landed it adds `CharBBox` to `Word.chars`. Add to `PUBLIC_MODELS` then.
3. **Multi-pass review.** Once the proofreader app spec exists, evolve `ReviewMetadata` to a list of `ReviewPass` records (P1/P2/P3/F1/F2 etc). Backwards-compat: a single-element list with `pass_name='unspecified'` corresponds to today's single-state shape.
