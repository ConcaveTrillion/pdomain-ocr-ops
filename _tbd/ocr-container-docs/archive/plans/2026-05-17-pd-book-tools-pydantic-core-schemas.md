---
status: complete
synced: 2026-05-17
milestone: 12
repo: pdomain/pdomain-book-tools
---

# pdomain-book-tools — pydantic core schemas for geometry + OCR models

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `__get_pydantic_core_schema__` classmethods to `Point`, `BoundingBox`, `Character`, `Word`, `Block`, and `Page` so `pydantic.TypeAdapter(<cls>).json_schema()` produces a precise JSON Schema matching each class's `to_dict()` wire shape. Then re-add all six (plus `ReviewMetadata`, `OCRProvenance`, `OCRModelProvenance`) to `pd_book_tools.schemas.emit.PUBLIC_MODELS` so the schemas-emit CLI emits the full public model set.

**Why:** Plan #1 (2026-05-16) shipped the `ReviewMetadata` cluster + the schemas-emit CLI, but had to narrow `PUBLIC_MODELS` to just `ReviewMetadata` because `TypeAdapter` couldn't auto-introspect the other classes — `Point` isn't a dataclass, `Block` is a plain class, `Page` has `InitVar[Collection]` + `ndarray` cache fields, and `Word`'s dataclass field layout (`_text`, `_ground_truth_text`) diverges from its wire shape. Downstream consumers (pdomain-ui, pdomain-ocr-ops) need the JSON Schema for TypeScript codegen against the wire shape, not the internal class structure.

**Architecture:** Each class gets a `@classmethod __get_pydantic_core_schema__(cls, source_type, handler)` that returns a `core_schema.no_info_after_validator_function`:
- `function=cls.from_dict` — validates a dict by passing it through `from_dict`.
- `schema=core_schema.typed_dict_schema({...})` — describes the wire-shape dict produced by `to_dict()`.
- `serialization=core_schema.plain_serializer_function_ser_schema(cls.to_dict)` — round-trips back to dict.

This is a single-method addition per class. No restructuring of `Block`, no `@dataclass` conversion, no removal of `InitVar` or `ndarray` fields. The hook describes the wire shape; pydantic uses it for both validation and JSON Schema generation.

Shared schema primitives (e.g. "int-or-float", "optional str") live in a new internal helper module `pd_book_tools/schemas/_helpers.py` to keep per-class schemas readable. The Point dict-shape constant is exported from `point.py` so `BoundingBox` and other classes can reuse it without duplicating field declarations.

**Tech Stack:** Python 3.10+, pydantic ≥ 2.0 (already a direct dep as of plan #1's task 1), stdlib `@dataclass` / plain classes for the models, pytest via `uv run pytest -n auto`. No new dependencies.

**Working directory for all commands:** `/workspaces/ocr-container/pdomain-book-tools/`

**Scope explicitly deferred to a follow-up plan:**
- Native-Pydantic migration of Word/Block/Page/Character — these stay as stdlib dataclasses + plain classes; only the `__get_pydantic_core_schema__` hook is added.
- Renaming `Word._text` / `Word._ground_truth_text` to drop the leading underscore — that touches every caller and is its own refactor.
- Per-character bbox extraction (`CharBBox` on `Word.chars`) — already a separate spec (`docs/specs/09-char-bbox-extraction.md`).

---

## Task 1: Add `__get_pydantic_core_schema__` to `Point` {#add-getpydanticcoreschema-to-point}

**Files:**
- Modify: `pd_book_tools/geometry/point.py`
- Create: `tests/geometry/test_point_pydantic_schema.py`

- [ ] **Step 1: Write the failing test**

Create `tests/geometry/test_point_pydantic_schema.py`:

```python
"""Tests for Point.__get_pydantic_core_schema__ — wire-shape JSON Schema."""
from __future__ import annotations

from pydantic import TypeAdapter

from pd_book_tools.geometry.point import Point


def test_point_type_adapter_does_not_raise():
    # Before the hook was added, TypeAdapter(Point) raised
    # ``pydantic.errors.PydanticSchemaGenerationError: Unable to generate
    # pydantic-core schema for <class 'pd_book_tools.geometry.point.Point'>``.
    adapter = TypeAdapter(Point)
    assert adapter is not None


def test_point_json_schema_shape():
    schema = TypeAdapter(Point).json_schema()
    assert schema["type"] == "object"
    props = schema["properties"]
    assert set(props.keys()) == {"x", "y", "is_normalized"}
    # ``x`` and ``y`` accept int OR float; ``is_normalized`` is bool.
    # Pydantic typically renders union-of-int-and-float as ``anyOf``.
    assert "anyOf" in props["x"] or props["x"]["type"] in ("number", "integer")
    assert "anyOf" in props["y"] or props["y"]["type"] in ("number", "integer")
    assert props["is_normalized"]["type"] == "boolean"
    assert set(schema["required"]) == {"x", "y", "is_normalized"}


def test_point_validate_from_dict_roundtrip():
    adapter = TypeAdapter(Point)
    p = Point(0.5, 0.5, is_normalized=True)
    d = p.to_dict()
    validated = adapter.validate_python(d)
    assert isinstance(validated, Point)
    assert validated == p
    # Dump back to dict via pydantic's serializer; should match to_dict().
    dumped = adapter.dump_python(validated)
    assert dumped == d


def test_point_validate_legacy_dict_without_is_normalized():
    # from_dict() infers is_normalized when the key is absent; the schema
    # marks the key as required, but legacy data may omit it. We tolerate
    # the omission via from_dict's existing fallback (.get("is_normalized")).
    adapter = TypeAdapter(Point)
    # We allow the schema to require the key (cleaner for codegen). Legacy
    # dicts go through ``Point.from_dict`` directly, not the TypeAdapter.
    p_dict = {"x": 10, "y": 20, "is_normalized": False}
    validated = adapter.validate_python(p_dict)
    assert validated == Point(10, 20, is_normalized=False)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/geometry/test_point_pydantic_schema.py -v`
Expected: All tests FAIL — the first with `pydantic.errors.PydanticSchemaGenerationError`; the rest cascade because `TypeAdapter(Point)` raises at construction.

- [ ] **Step 3: Add the schema hook to `Point`**

In `pd_book_tools/geometry/point.py`, add imports at the top of the file (after the existing `shapely` import):

```python
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema
```

Then, inside the `Point` class, AFTER `__hash__` (the last method, around line 207), add:

```python
    # ------------------------------------------------------------------
    # Pydantic v2 integration: wire-shape JSON Schema via TypeAdapter.
    #
    # Point is not a dataclass and uses __slots__, so pydantic cannot
    # auto-introspect it. This hook declares the wire shape produced by
    # ``Point.to_dict()`` so ``TypeAdapter(Point).json_schema()`` emits a
    # precise JSON Schema for downstream TypeScript codegen (pdomain-ui,
    # pdomain-ocr-ops).
    # ------------------------------------------------------------------
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            function=cls.from_dict,
            schema=core_schema.typed_dict_schema(
                {
                    "x": core_schema.typed_dict_field(
                        core_schema.union_schema(
                            [
                                core_schema.int_schema(),
                                core_schema.float_schema(),
                            ]
                        ),
                    ),
                    "y": core_schema.typed_dict_field(
                        core_schema.union_schema(
                            [
                                core_schema.int_schema(),
                                core_schema.float_schema(),
                            ]
                        ),
                    ),
                    "is_normalized": core_schema.typed_dict_field(
                        core_schema.bool_schema(),
                    ),
                }
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls.to_dict,
            ),
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/geometry/test_point_pydantic_schema.py -v`
Expected: 4 passed.

- [ ] **Step 5: Run the existing Point test suite to verify no regression**

Run: `uv run pytest tests/geometry/test_point.py tests/geometry/test_point_pydantic_schema.py -v 2>&1 | tail -20`
Expected: pre-existing tests still pass; the 4 new tests also pass.

- [ ] **Step 6: Commit**

```bash
git add pd_book_tools/geometry/point.py tests/geometry/test_point_pydantic_schema.py
git commit -m "feat(geometry): add Point.__get_pydantic_core_schema__

Declares the wire shape produced by Point.to_dict() so TypeAdapter(Point)
can emit a precise JSON Schema for downstream TypeScript codegen
(pdomain-ui, pdomain-ocr-ops). Point uses __slots__ and is not a dataclass, so
pydantic cannot auto-introspect it; this hook makes the gap explicit.

No behavior change. Adds one classmethod; no field or method renames."
```

---

## Task 2: Add shared schema helpers + `__get_pydantic_core_schema__` to `BoundingBox` {#add-shared-schema-helpers-getpydanticcoreschema-to}

**Files:**
- Create: `pd_book_tools/schemas/_helpers.py`
- Modify: `pd_book_tools/geometry/point.py` (export `_POINT_DICT_SCHEMA` constant)
- Modify: `pd_book_tools/geometry/bounding_box.py`
- Create: `tests/geometry/test_bounding_box_pydantic_schema.py`

- [ ] **Step 1: Write the failing test**

Create `tests/geometry/test_bounding_box_pydantic_schema.py`:

```python
"""Tests for BoundingBox.__get_pydantic_core_schema__ — wire-shape JSON Schema."""
from __future__ import annotations

from pydantic import TypeAdapter

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point


def _bbox() -> BoundingBox:
    return BoundingBox(
        top_left=Point(0, 0, is_normalized=False),
        bottom_right=Point(10, 10, is_normalized=False),
    )


def test_bounding_box_type_adapter_does_not_raise():
    adapter = TypeAdapter(BoundingBox)
    assert adapter is not None


def test_bounding_box_json_schema_shape():
    schema = TypeAdapter(BoundingBox).json_schema()
    assert schema["type"] == "object"
    props = schema["properties"]
    assert set(props.keys()) == {"top_left", "bottom_right", "is_normalized"}
    # top_left and bottom_right are themselves Point-shaped dicts; either
    # inlined or referenced via $ref/$defs.
    for corner_key in ("top_left", "bottom_right"):
        corner = props[corner_key]
        if "$ref" in corner:
            # Inlined via $defs — verify it resolves to a Point-shaped dict.
            defs = schema.get("$defs", {})
            ref_name = corner["$ref"].split("/")[-1]
            assert ref_name in defs
            target = defs[ref_name]
            assert set(target["properties"].keys()) == {"x", "y", "is_normalized"}
        else:
            assert set(corner["properties"].keys()) == {"x", "y", "is_normalized"}
    assert set(schema["required"]) == {"top_left", "bottom_right", "is_normalized"}


def test_bounding_box_validate_from_dict_roundtrip():
    adapter = TypeAdapter(BoundingBox)
    bb = _bbox()
    d = bb.to_dict()
    validated = adapter.validate_python(d)
    assert isinstance(validated, BoundingBox)
    assert validated == bb
    dumped = adapter.dump_python(validated)
    assert dumped == d
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/geometry/test_bounding_box_pydantic_schema.py -v`
Expected: All FAIL with `PydanticSchemaGenerationError` or cascade failures.

- [ ] **Step 3: Create the shared helpers module**

Create `pd_book_tools/schemas/_helpers.py`:

```python
"""Shared pydantic-core schema primitives for pdomain-book-tools models.

Internal module — not part of the public API. Other modules import
schema fragments from here to keep per-class ``__get_pydantic_core_schema__``
hooks readable and consistent.

Usage:
    from pd_book_tools.schemas._helpers import (
        NUMBER_SCHEMA,
        NULLABLE_STR_SCHEMA,
        STR_LIST_SCHEMA,
        STR_STR_DICT_SCHEMA,
    )
"""
from __future__ import annotations

from pydantic_core import core_schema

# Int-or-float (coordinates, confidences, etc.).
NUMBER_SCHEMA = core_schema.union_schema(
    [
        core_schema.int_schema(),
        core_schema.float_schema(),
    ]
)

# ``str | None`` — used for optional notes / ground-truth fields.
NULLABLE_STR_SCHEMA = core_schema.nullable_schema(core_schema.str_schema())

# ``list[str]`` — used for labels / components.
STR_LIST_SCHEMA = core_schema.list_schema(core_schema.str_schema())

# ``dict[str, str]`` — used for text_style_label_scopes.
STR_STR_DICT_SCHEMA = core_schema.dict_schema(
    keys_schema=core_schema.str_schema(),
    values_schema=core_schema.str_schema(),
)

# ``dict[str, Any]`` — used for free-form metadata bags
# (ground_truth_match_keys, additional_block_attributes).
STR_ANY_DICT_SCHEMA = core_schema.dict_schema(
    keys_schema=core_schema.str_schema(),
)

# ``dict[str, float | str] | None`` — baseline (m, b, source).
NULLABLE_BASELINE_SCHEMA = core_schema.nullable_schema(
    core_schema.dict_schema(
        keys_schema=core_schema.str_schema(),
        values_schema=core_schema.union_schema(
            [
                core_schema.float_schema(),
                core_schema.str_schema(),
            ]
        ),
    )
)
```

- [ ] **Step 4: Export `_POINT_DICT_SCHEMA` from `point.py`**

In `pd_book_tools/geometry/point.py`, add a module-level constant ABOVE the `Point` class declaration (right after the `from pydantic_core import ...` import added in Task 1):

```python
from pd_book_tools.schemas._helpers import NUMBER_SCHEMA

# Wire shape for a Point dict — extracted as a module-level constant so
# composite models (BoundingBox, etc.) can embed Point's shape without
# triggering Point's full validator pipeline (which would coerce nested
# dicts to Point instances inside parent ``from_dict`` callers that
# expect raw dicts).
_POINT_DICT_SCHEMA = core_schema.typed_dict_schema(
    {
        "x": core_schema.typed_dict_field(NUMBER_SCHEMA),
        "y": core_schema.typed_dict_field(NUMBER_SCHEMA),
        "is_normalized": core_schema.typed_dict_field(
            core_schema.bool_schema(),
        ),
    }
)
```

Then update `Point.__get_pydantic_core_schema__` to use the constant:

```python
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            function=cls.from_dict,
            schema=_POINT_DICT_SCHEMA,
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls.to_dict,
            ),
        )
```

- [ ] **Step 5: Add the schema hook to `BoundingBox`**

In `pd_book_tools/geometry/bounding_box.py`, add imports at the top of the file (with the other imports, after `from numpy import ndarray`):

```python
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

from pd_book_tools.geometry.point import _POINT_DICT_SCHEMA
```

Note: `Point` is already imported elsewhere in the file; do not duplicate that import.

Then, inside the `BoundingBox` `@dataclass` block, add the hook as the LAST method (after the existing `from_dict` classmethod around line 526):

```python
    # ------------------------------------------------------------------
    # Pydantic v2 integration: wire-shape JSON Schema via TypeAdapter.
    # See ``Point.__get_pydantic_core_schema__`` for the pattern rationale.
    # ------------------------------------------------------------------
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            function=cls.from_dict,
            schema=core_schema.typed_dict_schema(
                {
                    "top_left": core_schema.typed_dict_field(_POINT_DICT_SCHEMA),
                    "bottom_right": core_schema.typed_dict_field(
                        _POINT_DICT_SCHEMA
                    ),
                    "is_normalized": core_schema.typed_dict_field(
                        core_schema.bool_schema(),
                    ),
                }
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls.to_dict,
            ),
        )
```

- [ ] **Step 6: Run the new test to verify it passes**

Run: `uv run pytest tests/geometry/test_bounding_box_pydantic_schema.py tests/geometry/test_point_pydantic_schema.py -v`
Expected: 7 passed (3 BoundingBox + 4 Point).

- [ ] **Step 7: Run the existing geometry test suites to verify no regression**

Run: `uv run pytest tests/geometry/ -v 2>&1 | tail -20`
Expected: all pre-existing geometry tests still pass.

- [ ] **Step 8: Commit**

```bash
git add pd_book_tools/schemas/_helpers.py pd_book_tools/geometry/point.py pd_book_tools/geometry/bounding_box.py tests/geometry/test_bounding_box_pydantic_schema.py
git commit -m "feat(geometry): add BoundingBox.__get_pydantic_core_schema__

Adds the same wire-shape pydantic hook to BoundingBox; reuses
_POINT_DICT_SCHEMA exported from point.py to avoid duplicating Point's
field declarations.

Also introduces pd_book_tools/schemas/_helpers.py for shared schema
primitives (NUMBER_SCHEMA, NULLABLE_STR_SCHEMA, STR_LIST_SCHEMA, etc.)
used by the upcoming Character/Word/Block/Page hooks.

No behavior change."
```

---

## Task 3: Add `__get_pydantic_core_schema__` to `Character` {#add-getpydanticcoreschema-to-character}

**Files:**
- Modify: `pd_book_tools/ocr/character.py`
- Create: `tests/ocr/test_character_pydantic_schema.py`

- [ ] **Step 1: Write the failing test**

Create `tests/ocr/test_character_pydantic_schema.py`:

```python
"""Tests for Character.__get_pydantic_core_schema__ — wire-shape JSON Schema."""
from __future__ import annotations

from pydantic import TypeAdapter

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.character import Character


def _bbox() -> BoundingBox:
    return BoundingBox(
        top_left=Point(0, 0, is_normalized=False),
        bottom_right=Point(5, 5, is_normalized=False),
    )


def test_character_type_adapter_does_not_raise():
    adapter = TypeAdapter(Character)
    assert adapter is not None


def test_character_json_schema_shape():
    schema = TypeAdapter(Character).json_schema()
    assert schema["type"] == "object"
    props = schema["properties"]
    assert set(props.keys()) == {
        "type",
        "text",
        "bounding_box",
        "ocr_confidence",
        "text_style_labels",
        "word_components",
    }
    assert props["type"]["const"] == "Character"
    assert props["text"]["type"] == "string"
    assert "anyOf" in props["ocr_confidence"] or "null" in str(
        props["ocr_confidence"]
    )
    assert props["text_style_labels"]["type"] == "array"
    assert props["word_components"]["type"] == "array"


def test_character_validate_from_dict_roundtrip():
    adapter = TypeAdapter(Character)
    c = Character(text="a", bounding_box=_bbox(), ocr_confidence=0.9)
    d = c.to_dict()
    validated = adapter.validate_python(d)
    assert isinstance(validated, Character)
    assert validated == c
    dumped = adapter.dump_python(validated)
    assert dumped == d
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/ocr/test_character_pydantic_schema.py -v`
Expected: tests fail — at minimum the `validate_from_dict_roundtrip` test fails because pydantic's auto-introspection produces a schema that doesn't include the `"type": "Character"` discriminator (which is added in `to_dict` but not present as a dataclass field).

- [ ] **Step 3: Add the schema hook to `Character`**

In `pd_book_tools/ocr/character.py`, add imports at the top of the file (after the existing imports):

```python
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

from pd_book_tools.schemas._helpers import (
    NUMBER_SCHEMA,
    STR_LIST_SCHEMA,
)
```

Then, inside the `Character` `@dataclass` block, add the hook as the LAST method (after `from_dict`):

```python
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        # Local import to avoid a circular: BoundingBox imports Point,
        # Character imports BoundingBox. Module-level is fine here since
        # this module is loaded after both.
        from pd_book_tools.geometry.bounding_box import BoundingBox

        bb_schema = handler.generate_schema(BoundingBox)
        return core_schema.no_info_after_validator_function(
            function=cls.from_dict,
            schema=core_schema.typed_dict_schema(
                {
                    "type": core_schema.typed_dict_field(
                        core_schema.literal_schema(["Character"]),
                        required=False,
                    ),
                    "text": core_schema.typed_dict_field(
                        core_schema.str_schema(),
                    ),
                    "bounding_box": core_schema.typed_dict_field(bb_schema),
                    "ocr_confidence": core_schema.typed_dict_field(
                        core_schema.nullable_schema(NUMBER_SCHEMA),
                        required=False,
                    ),
                    "text_style_labels": core_schema.typed_dict_field(
                        STR_LIST_SCHEMA,
                        required=False,
                    ),
                    "word_components": core_schema.typed_dict_field(
                        STR_LIST_SCHEMA,
                        required=False,
                    ),
                }
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls.to_dict,
            ),
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/ocr/test_character_pydantic_schema.py -v`
Expected: 3 passed.

- [ ] **Step 5: Run the existing Character test suite to verify no regression**

Run: `uv run pytest tests/ocr/test_character.py tests/ocr/test_character_groups.py tests/ocr/test_character_pydantic_schema.py -v 2>&1 | tail -15`
Expected: pre-existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add pd_book_tools/ocr/character.py tests/ocr/test_character_pydantic_schema.py
git commit -m "feat(ocr): add Character.__get_pydantic_core_schema__

Declares the wire shape produced by Character.to_dict() including the
\"type\": \"Character\" discriminator that to_dict adds but isn't a
dataclass field. Recurses through BoundingBox's hook for the
bounding_box field.

No behavior change."
```

---

## Task 4: Add `__get_pydantic_core_schema__` to `Word` {#add-getpydanticcoreschema-to-word}

**Files:**
- Modify: `pd_book_tools/ocr/word.py`
- Create: `tests/ocr/test_word_pydantic_schema.py`

- [ ] **Step 1: Write the failing test**

Create `tests/ocr/test_word_pydantic_schema.py`:

```python
"""Tests for Word.__get_pydantic_core_schema__ — wire-shape JSON Schema."""
from __future__ import annotations

from pydantic import TypeAdapter

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.review import ReviewMetadata
from pd_book_tools.ocr.word import Word


def _bbox() -> BoundingBox:
    return BoundingBox(
        top_left=Point(0, 0, is_normalized=False),
        bottom_right=Point(10, 10, is_normalized=False),
    )


def test_word_type_adapter_does_not_raise():
    adapter = TypeAdapter(Word)
    assert adapter is not None


def test_word_json_schema_shape():
    schema = TypeAdapter(Word).json_schema()
    assert schema["type"] == "object"
    props = schema["properties"]
    # Wire-shape keys (NOT dataclass field names): ``text`` and
    # ``ground_truth_text`` (no leading underscore).
    expected_keys = {
        "type",
        "text",
        "bounding_box",
        "ocr_confidence",
        "word_labels",
        "text_style_labels",
        "text_style_label_scopes",
        "word_components",
        "baseline",
        "ground_truth_text",
        "ground_truth_bounding_box",
        "ground_truth_match_keys",
        "review",
    }
    assert set(props.keys()) == expected_keys
    assert "_text" not in props
    assert "_ground_truth_text" not in props


def test_word_validate_from_dict_roundtrip_minimal():
    adapter = TypeAdapter(Word)
    w = Word(text="hello", bounding_box=_bbox())
    d = w.to_dict()
    validated = adapter.validate_python(d)
    assert isinstance(validated, Word)
    assert validated.text == "hello"
    assert validated.bounding_box == w.bounding_box
    dumped = adapter.dump_python(validated)
    assert dumped == d


def test_word_validate_from_dict_roundtrip_full():
    adapter = TypeAdapter(Word)
    w = Word(
        text="hello",
        bounding_box=_bbox(),
        ocr_confidence=0.95,
        word_labels=["test-label"],
        text_style_labels=["italics"],
        text_style_label_scopes={"italics": "word"},
        word_components=["footnote marker"],
        baseline={"m": 0.0, "b": 5.0, "source": "ocr"},
        ground_truth_text="hello",
        ground_truth_bounding_box=_bbox(),
        ground_truth_match_keys={"matched_text": "hello"},
        review=ReviewMetadata(validated=True, reviewer_note="ok"),
    )
    d = w.to_dict()
    validated = adapter.validate_python(d)
    assert isinstance(validated, Word)
    assert validated == w
    dumped = adapter.dump_python(validated)
    assert dumped == d
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/ocr/test_word_pydantic_schema.py -v`
Expected: All fail — auto-introspection produces a schema using the dataclass field names (`_text`, `_ground_truth_text`) instead of the wire-shape names.

- [ ] **Step 3: Add the schema hook to `Word`**

In `pd_book_tools/ocr/word.py`, add imports at the top of the file (with the other imports, after `from numpy import ndarray`):

```python
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

from pd_book_tools.schemas._helpers import (
    NULLABLE_BASELINE_SCHEMA,
    NULLABLE_STR_SCHEMA,
    NUMBER_SCHEMA,
    STR_ANY_DICT_SCHEMA,
    STR_LIST_SCHEMA,
    STR_STR_DICT_SCHEMA,
)
```

Then, inside the `Word` `@dataclass` block, add the hook as the LAST method (after the existing `from_dict` classmethod added in plan #1):

```python
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        # Local imports to avoid circulars with the lower-level geometry
        # types whose modules import Word transitively.
        from pd_book_tools.geometry.bounding_box import BoundingBox

        bb_schema = handler.generate_schema(BoundingBox)
        review_schema = handler.generate_schema(ReviewMetadata)
        nullable_bb_schema = core_schema.nullable_schema(bb_schema)
        nullable_review_schema = core_schema.nullable_schema(review_schema)
        return core_schema.no_info_after_validator_function(
            function=cls.from_dict,
            schema=core_schema.typed_dict_schema(
                {
                    "type": core_schema.typed_dict_field(
                        core_schema.literal_schema(["Word"]),
                        required=False,
                    ),
                    "text": core_schema.typed_dict_field(
                        core_schema.str_schema(),
                    ),
                    "bounding_box": core_schema.typed_dict_field(bb_schema),
                    "ocr_confidence": core_schema.typed_dict_field(
                        core_schema.nullable_schema(NUMBER_SCHEMA),
                        required=False,
                    ),
                    "word_labels": core_schema.typed_dict_field(
                        STR_LIST_SCHEMA,
                        required=False,
                    ),
                    "text_style_labels": core_schema.typed_dict_field(
                        STR_LIST_SCHEMA,
                        required=False,
                    ),
                    "text_style_label_scopes": core_schema.typed_dict_field(
                        core_schema.nullable_schema(STR_STR_DICT_SCHEMA),
                        required=False,
                    ),
                    "word_components": core_schema.typed_dict_field(
                        STR_LIST_SCHEMA,
                        required=False,
                    ),
                    "baseline": core_schema.typed_dict_field(
                        NULLABLE_BASELINE_SCHEMA,
                        required=False,
                    ),
                    "ground_truth_text": core_schema.typed_dict_field(
                        NULLABLE_STR_SCHEMA,
                        required=False,
                    ),
                    "ground_truth_bounding_box": core_schema.typed_dict_field(
                        nullable_bb_schema,
                        required=False,
                    ),
                    "ground_truth_match_keys": core_schema.typed_dict_field(
                        STR_ANY_DICT_SCHEMA,
                        required=False,
                    ),
                    "review": core_schema.typed_dict_field(
                        nullable_review_schema,
                        required=False,
                    ),
                }
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls.to_dict,
            ),
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/ocr/test_word_pydantic_schema.py -v`
Expected: 4 passed.

- [ ] **Step 5: Run the full Word test suite to verify no regression**

Run: `uv run pytest tests/ocr/test_word.py tests/ocr/test_word_review.py tests/ocr/test_word_pydantic_schema.py -v 2>&1 | tail -20`
Expected: pre-existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add pd_book_tools/ocr/word.py tests/ocr/test_word_pydantic_schema.py
git commit -m "feat(ocr): add Word.__get_pydantic_core_schema__

Declares the wire shape produced by Word.to_dict() — uses the
underscore-stripped public names (text, ground_truth_text) rather than
the internal dataclass field names (_text, _ground_truth_text), so
downstream codegen sees the public surface.

All optional fields are marked required=False so the schema accepts the
compact wire shapes produced by Word's selective to_dict output. Recurses
through BoundingBox's and ReviewMetadata's hooks for nested fields.

No behavior change."
```

---

## Task 5: Add `__get_pydantic_core_schema__` to `Block` {#add-getpydanticcoreschema-to-block}

**Files:**
- Modify: `pd_book_tools/ocr/block.py`
- Create: `tests/ocr/test_block_pydantic_schema.py`

- [ ] **Step 1: Write the failing test**

Create `tests/ocr/test_block_pydantic_schema.py`:

```python
"""Tests for Block.__get_pydantic_core_schema__ — wire-shape JSON Schema."""
from __future__ import annotations

from pydantic import TypeAdapter

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.word import Word


def _bbox() -> BoundingBox:
    return BoundingBox(
        top_left=Point(0, 0, is_normalized=False),
        bottom_right=Point(10, 10, is_normalized=False),
    )


def _word(text: str = "hello") -> Word:
    return Word(text=text, bounding_box=_bbox())


def test_block_type_adapter_does_not_raise():
    adapter = TypeAdapter(Block)
    assert adapter is not None


def test_block_json_schema_shape():
    schema = TypeAdapter(Block).json_schema()
    assert schema["type"] == "object"
    props = schema["properties"]
    expected_keys = {
        "type",
        "child_type",
        "block_category",
        "block_labels",
        "block_role_labels",
        "block_position_labels",
        "line_role_labels",
        "line_position_labels",
        "baseline",
        "bounding_box",
        "items",
        "override_page_sort_order",
        "unmatched_ground_truth_words",
        "additional_block_attributes",
        "base_ground_truth_text",
        "review",
    }
    assert set(props.keys()) == expected_keys


def test_block_validate_from_dict_roundtrip_line_of_words():
    adapter = TypeAdapter(Block)
    block = Block(
        items=[_word("hello"), _word("world")],
        bounding_box=_bbox(),
        child_type=BlockChildType.WORDS,
        block_category=BlockCategory.LINE,
    )
    d = block.to_dict()
    validated = adapter.validate_python(d)
    assert isinstance(validated, Block)
    assert validated.to_dict() == d


def test_block_validate_from_dict_roundtrip_nested_blocks():
    adapter = TypeAdapter(Block)
    line1 = Block(
        items=[_word("hello")],
        bounding_box=_bbox(),
        child_type=BlockChildType.WORDS,
        block_category=BlockCategory.LINE,
    )
    line2 = Block(
        items=[_word("world")],
        bounding_box=_bbox(),
        child_type=BlockChildType.WORDS,
        block_category=BlockCategory.LINE,
    )
    paragraph = Block(
        items=[line1, line2],
        bounding_box=_bbox(),
        child_type=BlockChildType.BLOCKS,
        block_category=BlockCategory.PARAGRAPH,
    )
    d = paragraph.to_dict()
    validated = adapter.validate_python(d)
    assert isinstance(validated, Block)
    assert validated.to_dict() == d
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/ocr/test_block_pydantic_schema.py -v`
Expected: All FAIL — `Block` is a plain class (not @dataclass), so `TypeAdapter` raises `PydanticSchemaGenerationError`.

- [ ] **Step 3: Add the schema hook to `Block`**

In `pd_book_tools/ocr/block.py`, add imports at the top of the file (after `from thefuzz.fuzz import ratio as fuzz_ratio`):

```python
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

from pd_book_tools.schemas._helpers import (
    NULLABLE_BASELINE_SCHEMA,
    NULLABLE_STR_SCHEMA,
    STR_ANY_DICT_SCHEMA,
    STR_LIST_SCHEMA,
)
```

Then, inside the `Block` class, add the hook as the LAST method (after `from_dict`, around line 1083):

```python
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        from pd_book_tools.geometry.bounding_box import BoundingBox
        from pd_book_tools.ocr.review import ReviewMetadata as _Review

        bb_schema = handler.generate_schema(BoundingBox)
        nullable_bb_schema = core_schema.nullable_schema(bb_schema)
        word_schema = handler.generate_schema(Word)
        review_schema = handler.generate_schema(_Review)
        nullable_review_schema = core_schema.nullable_schema(review_schema)
        # ``items`` is a list of EITHER Word dicts OR Block dicts; the
        # discriminator is the sibling ``child_type`` field. We use
        # ``definition-ref`` to allow Block to reference its own schema
        # for nested-block items.
        block_ref = core_schema.definition_reference_schema("Block")
        items_schema = core_schema.list_schema(
            core_schema.union_schema([word_schema, block_ref])
        )
        return core_schema.definitions_schema(
            core_schema.no_info_after_validator_function(
                function=cls.from_dict,
                schema=core_schema.typed_dict_schema(
                    {
                        "type": core_schema.typed_dict_field(
                            core_schema.literal_schema(["Block"]),
                            required=False,
                        ),
                        "child_type": core_schema.typed_dict_field(
                            core_schema.nullable_schema(
                                core_schema.literal_schema(["WORDS", "BLOCKS"])
                            ),
                            required=False,
                        ),
                        "block_category": core_schema.typed_dict_field(
                            core_schema.nullable_schema(
                                core_schema.literal_schema(
                                    ["BLOCK", "PARAGRAPH", "LINE"]
                                )
                            ),
                            required=False,
                        ),
                        "block_labels": core_schema.typed_dict_field(
                            STR_LIST_SCHEMA,
                            required=False,
                        ),
                        "block_role_labels": core_schema.typed_dict_field(
                            STR_LIST_SCHEMA,
                            required=False,
                        ),
                        "block_position_labels": core_schema.typed_dict_field(
                            STR_LIST_SCHEMA,
                            required=False,
                        ),
                        "line_role_labels": core_schema.typed_dict_field(
                            STR_LIST_SCHEMA,
                            required=False,
                        ),
                        "line_position_labels": core_schema.typed_dict_field(
                            STR_LIST_SCHEMA,
                            required=False,
                        ),
                        "baseline": core_schema.typed_dict_field(
                            NULLABLE_BASELINE_SCHEMA,
                            required=False,
                        ),
                        "bounding_box": core_schema.typed_dict_field(
                            nullable_bb_schema,
                            required=False,
                        ),
                        "items": core_schema.typed_dict_field(items_schema),
                        "override_page_sort_order": core_schema.typed_dict_field(
                            core_schema.nullable_schema(
                                core_schema.int_schema()
                            ),
                            required=False,
                        ),
                        "unmatched_ground_truth_words": core_schema.typed_dict_field(
                            STR_LIST_SCHEMA,
                            required=False,
                        ),
                        "additional_block_attributes": core_schema.typed_dict_field(
                            STR_ANY_DICT_SCHEMA,
                            required=False,
                        ),
                        "base_ground_truth_text": core_schema.typed_dict_field(
                            NULLABLE_STR_SCHEMA,
                            required=False,
                        ),
                        "review": core_schema.typed_dict_field(
                            nullable_review_schema,
                            required=False,
                        ),
                    }
                ),
                serialization=core_schema.plain_serializer_function_ser_schema(
                    cls.to_dict,
                ),
                ref="Block",
            ),
            [],
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/ocr/test_block_pydantic_schema.py -v`
Expected: 4 passed. If the `nested_blocks` test fails with a recursion-schema error, double-check the `ref="Block"` argument on the inner `no_info_after_validator_function` and that the outer `definitions_schema` wraps it.

- [ ] **Step 5: Run the full Block test suite to verify no regression**

Run: `uv run pytest tests/ocr/test_block.py tests/ocr/test_block_coverage2.py tests/ocr/test_block_review.py tests/ocr/test_block_pydantic_schema.py -v 2>&1 | tail -20`
Expected: pre-existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add pd_book_tools/ocr/block.py tests/ocr/test_block_pydantic_schema.py
git commit -m "feat(ocr): add Block.__get_pydantic_core_schema__

Declares the wire shape produced by Block.to_dict(). Block is a plain
class (not @dataclass), so pydantic auto-introspection fails — this
hook makes the wire shape explicit.

The recursive items field (list of Word OR Block dicts) uses a
definition_reference_schema(\"Block\") wrapped in definitions_schema
so nested blocks resolve via the same ref.

No behavior change."
```

---

## Task 6: Add `__get_pydantic_core_schema__` to `Page` {#add-getpydanticcoreschema-to-page}

**Files:**
- Modify: `pd_book_tools/ocr/page.py`
- Create: `tests/ocr/test_page_pydantic_schema.py`

- [ ] **Step 1: Write the failing test**

Create `tests/ocr/test_page_pydantic_schema.py`:

```python
"""Tests for Page.__get_pydantic_core_schema__ — wire-shape JSON Schema."""
from __future__ import annotations

from pydantic import TypeAdapter

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word


def _bbox() -> BoundingBox:
    return BoundingBox(
        top_left=Point(0, 0, is_normalized=False),
        bottom_right=Point(100, 100, is_normalized=False),
    )


def _word(text: str = "hello") -> Word:
    return Word(text=text, bounding_box=_bbox())


def _line() -> Block:
    return Block(
        items=[_word()],
        bounding_box=_bbox(),
        child_type=BlockChildType.WORDS,
        block_category=BlockCategory.LINE,
    )


def test_page_type_adapter_does_not_raise():
    adapter = TypeAdapter(Page)
    assert adapter is not None


def test_page_json_schema_shape():
    schema = TypeAdapter(Page).json_schema()
    assert schema["type"] == "object"
    props = schema["properties"]
    # Page.to_dict produces these keys; some are omitted-when-default,
    # but the schema must list all of them.
    expected_keys = {
        "type",
        "width",
        "height",
        "page_index",
        "bounding_box",
        "items",
        "ocr_provenance",
        "image_path",
        "name",
        "source",
        "ocr_failed",
        "provenance_live_ocr",
        "provenance_saved_ocr",
        "provenance_saved",
        "rotation_applied",
        "review",
    }
    assert set(props.keys()) == expected_keys
    # NDArray cache fields must NOT appear in the wire schema.
    for cache_field in (
        "_cv2_numpy_page_image",
        "_cv2_numpy_page_image_page_with_bbox",
        "image_array",
        "blocks",
    ):
        assert cache_field not in props


def test_page_validate_from_dict_roundtrip_minimal():
    adapter = TypeAdapter(Page)
    page = Page(
        width=100,
        height=100,
        page_index=0,
        bounding_box=_bbox(),
        blocks=[_line()],
    )
    d = page.to_dict()
    validated = adapter.validate_python(d)
    assert isinstance(validated, Page)
    assert validated.to_dict() == d


def test_page_validate_from_dict_roundtrip_with_metadata():
    adapter = TypeAdapter(Page)
    page = Page(
        width=100,
        height=100,
        page_index=1,
        bounding_box=_bbox(),
        blocks=[_line()],
        image_path="/tmp/page-1.png",
        name="page-001",
        source="ocr-fixture",
        rotation_applied=90,
    )
    d = page.to_dict()
    validated = adapter.validate_python(d)
    assert isinstance(validated, Page)
    assert validated.to_dict() == d
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/ocr/test_page_pydantic_schema.py -v`
Expected: All FAIL — auto-introspection trips on `InitVar[Collection]` and the `ndarray` cache fields.

- [ ] **Step 3: Add the schema hook to `Page`**

In `pd_book_tools/ocr/page.py`, add imports near the top of the file (with the other imports, after `from numpy import ndarray`):

```python
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

from pd_book_tools.schemas._helpers import (
    NULLABLE_STR_SCHEMA,
    STR_LIST_SCHEMA,
)
```

(Note: `Any` is likely already imported; if not, add `from typing import Any`.)

Then, inside the `Page` `@dataclass(eq=False)` block, add the hook as the LAST method (find the class's last existing method and append after it). Place a clear section comment marker so it's easy to find:

```python
    # ------------------------------------------------------------------
    # Pydantic v2 integration: wire-shape JSON Schema via TypeAdapter.
    #
    # Page is @dataclass(eq=False) but carries InitVar[Collection] and
    # ten ndarray cache fields that pydantic cannot introspect. This
    # hook declares the wire shape produced by Page.to_dict() — which
    # already skips both the InitVars and the ndarray caches — so
    # TypeAdapter can emit a precise JSON Schema for downstream codegen.
    # ------------------------------------------------------------------
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        from pd_book_tools.geometry.bounding_box import BoundingBox
        from pd_book_tools.ocr.block import Block
        from pd_book_tools.ocr.provenance import OCRProvenance
        from pd_book_tools.ocr.review import ReviewMetadata as _Review

        bb_schema = handler.generate_schema(BoundingBox)
        block_schema = handler.generate_schema(Block)
        provenance_schema = handler.generate_schema(OCRProvenance)
        review_schema = handler.generate_schema(_Review)
        return core_schema.no_info_after_validator_function(
            function=cls.from_dict,
            schema=core_schema.typed_dict_schema(
                {
                    "type": core_schema.typed_dict_field(
                        core_schema.literal_schema(["Page"]),
                        required=False,
                    ),
                    "width": core_schema.typed_dict_field(
                        core_schema.int_schema(),
                    ),
                    "height": core_schema.typed_dict_field(
                        core_schema.int_schema(),
                    ),
                    "page_index": core_schema.typed_dict_field(
                        core_schema.int_schema(),
                    ),
                    "bounding_box": core_schema.typed_dict_field(
                        core_schema.nullable_schema(bb_schema),
                        required=False,
                    ),
                    "items": core_schema.typed_dict_field(
                        core_schema.list_schema(block_schema),
                        required=False,
                    ),
                    "ocr_provenance": core_schema.typed_dict_field(
                        core_schema.nullable_schema(provenance_schema),
                        required=False,
                    ),
                    "image_path": core_schema.typed_dict_field(
                        NULLABLE_STR_SCHEMA,
                        required=False,
                    ),
                    "name": core_schema.typed_dict_field(
                        NULLABLE_STR_SCHEMA,
                        required=False,
                    ),
                    "source": core_schema.typed_dict_field(
                        core_schema.str_schema(),
                        required=False,
                    ),
                    "ocr_failed": core_schema.typed_dict_field(
                        core_schema.bool_schema(),
                        required=False,
                    ),
                    "provenance_live_ocr": core_schema.typed_dict_field(
                        NULLABLE_STR_SCHEMA,
                        required=False,
                    ),
                    "provenance_saved_ocr": core_schema.typed_dict_field(
                        NULLABLE_STR_SCHEMA,
                        required=False,
                    ),
                    "provenance_saved": core_schema.typed_dict_field(
                        NULLABLE_STR_SCHEMA,
                        required=False,
                    ),
                    "rotation_applied": core_schema.typed_dict_field(
                        core_schema.nullable_schema(core_schema.int_schema()),
                        required=False,
                    ),
                    "review": core_schema.typed_dict_field(
                        core_schema.nullable_schema(review_schema),
                        required=False,
                    ),
                }
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls.to_dict,
            ),
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/ocr/test_page_pydantic_schema.py -v`
Expected: 4 passed.

- [ ] **Step 5: Run a representative slice of the existing Page test suite to verify no regression**

Run: `uv run pytest tests/ocr/test_page_behavior_pin.py tests/test_page_behavior_pin.py tests/test_page_model_doc.py -v 2>&1 | tail -20`
Expected: pre-existing tests still pass. (Skip ones that don't exist; the goal is to confirm we haven't broken `Page`'s behavior or its `to_dict`/`from_dict` round-trip.)

- [ ] **Step 6: Commit**

```bash
git add pd_book_tools/ocr/page.py tests/ocr/test_page_pydantic_schema.py
git commit -m "feat(ocr): add Page.__get_pydantic_core_schema__

Declares the wire shape produced by Page.to_dict(), which already
skips Page's InitVar[Collection] and ndarray cache fields. Pydantic
cannot auto-introspect those fields; the explicit hook bypasses them.

Recurses through BoundingBox, Block, OCRProvenance, and ReviewMetadata
hooks for nested fields.

No behavior change."
```

---

## Task 7: Re-add models to `PUBLIC_MODELS` + restore narrowed tests + full CI {#re-add-models-to-publicmodels-restore-narrowed-tes}

**Files:**
- Modify: `pd_book_tools/schemas/emit.py`
- Modify: `tests/test_schemas_emit.py`

- [ ] **Step 1: Inspect the current state of `emit.py` and `test_schemas_emit.py`**

Run: `grep -n "PUBLIC_MODELS\|test_emit" pd_book_tools/schemas/emit.py tests/test_schemas_emit.py 2>&1 | head -30`

Expected:
- `emit.py` currently has `PUBLIC_MODELS = (ReviewMetadata,)` plus a NOTE comment listing the excluded classes.
- `tests/test_schemas_emit.py` has narrowed tests (`test_emit_includes_review_metadata_object_type`, `test_emit_review_metadata_is_only_public_model_for_now`) added by plan #1's fallback.

- [ ] **Step 2: Update `PUBLIC_MODELS`**

Replace the entire body of `pd_book_tools/schemas/emit.py` with:

```python
"""JSON-Schema emitter for pdomain-book-tools public domain models.

Invocation: ``python -m pd_book_tools.schemas.emit``

Emits a single JSON document on stdout, keyed by model class name, with
each value being a JSON-Schema document produced by
``pydantic.TypeAdapter(<cls>).json_schema()``.

Adding a new public model: import it below and add it to ``PUBLIC_MODELS``.
Classes that are not natively pydantic-introspectable (plain classes,
__slots__ types, dataclasses with InitVar / ndarray fields) declare a
``__get_pydantic_core_schema__`` classmethod that mirrors their
``to_dict()`` wire shape — see ``pd_book_tools/geometry/point.py`` for
the canonical pattern.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from pydantic import TypeAdapter

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block
from pd_book_tools.ocr.character import Character
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.provenance import OCRModelProvenance, OCRProvenance
from pd_book_tools.ocr.review import ReviewMetadata
from pd_book_tools.ocr.word import Word

# The single source of truth for what counts as a "public" model.
# Order is intentional: leaf geometry types first, OCR review/provenance
# next, then composite OCR models.
PUBLIC_MODELS: tuple[type, ...] = (
    Point,
    BoundingBox,
    ReviewMetadata,
    OCRModelProvenance,
    OCRProvenance,
    Character,
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

- [ ] **Step 3: Restore the full schemas-emit test suite**

Open `tests/test_schemas_emit.py` and replace its contents with the original (un-narrowed) test set, expanded for the full `PUBLIC_MODELS`:

```python
"""Tests for ``pd_book_tools.schemas.emit``: JSON-Schema emission CLI."""
from __future__ import annotations

import io
import json

import pytest

from pd_book_tools.schemas.emit import PUBLIC_MODELS, emit_schemas, main


def test_public_models_includes_full_set():
    names = {cls.__name__ for cls in PUBLIC_MODELS}
    assert names == {
        "Point",
        "BoundingBox",
        "ReviewMetadata",
        "OCRModelProvenance",
        "OCRProvenance",
        "Character",
        "Word",
        "Block",
        "Page",
    }


def test_emit_schemas_returns_dict_keyed_by_class_name():
    schemas = emit_schemas()
    for cls in PUBLIC_MODELS:
        assert cls.__name__ in schemas, f"missing schema for {cls.__name__}"
        assert isinstance(schemas[cls.__name__], dict)


def test_emit_word_schema_has_review_field():
    schemas = emit_schemas()
    word_schema = schemas["Word"]
    props = word_schema.get("properties", {})
    assert "review" in props, (
        "Word's wire schema must expose the optional ``review`` field "
        "(added in plan #1)."
    )


def test_emit_block_schema_has_review_field():
    schemas = emit_schemas()
    block_schema = schemas["Block"]
    props = block_schema.get("properties", {})
    assert "review" in props


def test_emit_page_schema_has_review_field():
    schemas = emit_schemas()
    page_schema = schemas["Page"]
    props = page_schema.get("properties", {})
    assert "review" in props


def test_emit_includes_word_block_page():
    schemas = emit_schemas()
    for required in ("Word", "Block", "Page"):
        assert required in schemas
        assert schemas[required].get("type") == "object"


def test_main_writes_json_to_stdout(capsys: pytest.CaptureFixture[str]):
    rc = main([])
    assert rc == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert "ReviewMetadata" in parsed
    assert "Word" in parsed
    assert "Block" in parsed
    assert "Page" in parsed


def test_main_runs_via_python_dash_m(tmp_path: "object"):
    # Sanity check: ``python -m pd_book_tools.schemas.emit`` produces
    # parseable JSON. We don't shell out here — main([]) is already
    # tested above — but we verify json.dump's output is deterministic
    # by emitting twice and comparing.
    buf1 = io.StringIO()
    buf2 = io.StringIO()
    schemas1 = emit_schemas()
    schemas2 = emit_schemas()
    json.dump(schemas1, buf1, indent=2, sort_keys=True)
    json.dump(schemas2, buf2, indent=2, sort_keys=True)
    assert buf1.getvalue() == buf2.getvalue()
```

If `tests/test_schemas_emit.py` has additional tests beyond these, KEEP them — only replace the narrowed ones added by plan #1's fallback (`test_emit_includes_review_metadata_object_type`, `test_emit_review_metadata_is_only_public_model_for_now`). Use `grep -n "def test_" tests/test_schemas_emit.py` before editing to enumerate; preserve any others verbatim.

- [ ] **Step 4: Run the schemas-emit test suite**

Run: `uv run pytest tests/test_schemas_emit.py -v`
Expected: all tests pass — 8+ tests covering the full PUBLIC_MODELS set.

- [ ] **Step 5: Run the full CI gate**

Run: `make ci AI=1`
Expected: `make ci AI=1` completes with exit code 0. All pre-existing tests pass; the new schema-hook tests pass; the restored schemas-emit tests pass.

If `make ci AI=1` fails, investigate root cause before the final commit; do not bypass.

- [ ] **Step 6: Sanity-check the emitted JSON manually**

Run: `uv run python -m pd_book_tools.schemas.emit | python -c "import json,sys; data=json.load(sys.stdin); print(list(data.keys()))"`
Expected: `['BoundingBox', 'Block', 'Character', 'OCRModelProvenance', 'OCRProvenance', 'Page', 'Point', 'ReviewMetadata', 'Word']` (sorted because `sort_keys=True` in the CLI).

- [ ] **Step 7: Commit**

```bash
git add pd_book_tools/schemas/emit.py tests/test_schemas_emit.py
git commit -m "feat(schemas): re-add all public models to PUBLIC_MODELS

With wire-shape pydantic core schema hooks now present on Point,
BoundingBox, Character, Word, Block, and Page (commits in this series),
TypeAdapter can produce precise JSON Schema for every public domain
model. Restores the original PUBLIC_MODELS set planned for plan #1
plus OCRModelProvenance and OCRProvenance (which auto-introspect).

Replaces plan #1's narrowed schemas-emit tests with the original
unnarrowed set, covering the full model surface."
```

---

## Self-review checklist (for the engineer; do this before the final commit)

- [ ] Every problem class (`Point`, `BoundingBox`, `Character`, `Word`, `Block`, `Page`) has a `__get_pydantic_core_schema__` classmethod.
- [ ] Each hook uses `core_schema.no_info_after_validator_function(function=cls.from_dict, schema=..., serialization=core_schema.plain_serializer_function_ser_schema(cls.to_dict))`.
- [ ] Each hook's `typed_dict_schema` exactly matches the keys produced by the class's `to_dict()` (verified by the per-class `json_schema_shape` test).
- [ ] Each per-class test includes a `validate_from_dict_roundtrip` case proving `validate_python(to_dict()) == original`.
- [ ] `Block`'s recursive `items` field uses `definition_reference_schema("Block")` wrapped in `definitions_schema` for nested-block round-trip.
- [ ] `Word`'s schema uses the WIRE-SHAPE names (`text`, `ground_truth_text`) — NOT the underscored dataclass field names.
- [ ] `Page`'s schema omits all `_cv2_numpy_page_image*` fields and the `image_array` / `blocks` InitVars.
- [ ] `PUBLIC_MODELS` includes all nine classes: Point, BoundingBox, ReviewMetadata, OCRModelProvenance, OCRProvenance, Character, Word, Block, Page.
- [ ] `pd_book_tools/schemas/_helpers.py` exists; its primitives are imported wherever they're used (no duplicated `core_schema.union_schema([int, float])` blocks scattered through model files).
- [ ] `make ci AI=1` passes.
- [ ] No existing OCR test was modified in this plan (all changes are additive — new methods, new tests, expanded `PUBLIC_MODELS`).

## Follow-up plans (not in scope here)

1. **Drop the leading underscore on `Word._text` / `Word._ground_truth_text`.** The schema-hook wire-shape mapping is a workaround for a public API surface that has migrated to non-underscored names but the underlying dataclass field names lag. Renaming the fields would let `Word` auto-introspect via pydantic — but touches every caller (~155 refs in pdomain-ocr-labeler-spa alone), so deferred.
2. **Promote `Block` from plain class to `@dataclass`.** With the hook in place, `Block` no longer NEEDS to be a dataclass for schemas-emit, but the rest of the codebase would benefit from a standard dataclass shape (auto-`__init__`, `__repr__`, `__eq__`). Big refactor — 1,200 lines with many methods + properties + ClassVars.
3. **Per-character bbox extraction (`CharBBox` on `Word.chars`).** See `docs/specs/09-char-bbox-extraction.md` — a CharBBox model would need to be added to PUBLIC_MODELS at that time.
4. **`GTMatchMetadata` cluster on `Word`.** Cluster `ground_truth_text`, `ground_truth_bounding_box`, `ground_truth_match_keys` under a single `matching: GTMatchMetadata | None` field. Deferred per cross-cut spec §5; the wire-shape schema added in this plan continues to expose the top-level fields until that migration ships.
