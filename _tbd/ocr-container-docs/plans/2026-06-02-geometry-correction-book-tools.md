---
repo: pdomain-book-tools
spec: docs/specs/2026-06-02-geometry-correction-design.md
---

# Geometry Correction (Deskew / Dewarp) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `geometry_correction` package to `pdomain-book-tools` exposing
swappable `Deskew` / `Dewarp` / `PageSideDetector` / `CurvatureDetector` protocols
with permissive built-in backends (and UVDoc dewarp behind an extra), so consumers
can straighten and flatten single page images before their own OCR step.

**Architecture:** Page-level protocols return a composable, invertible
`GeometryTransform` (affine matrix or dense `cv2.remap` backward-map) rather than
pixels. Splitting happens upstream; this package operates on one single page. A
curvature gate decides whether dewarp runs, protecting flat scans. Backends are
registered by name; consumers orchestrate ordering (a thin `GeometryPipeline` helper
offers the reference sequence).

**Tech Stack:** Python ≥3.10, numpy, OpenCV (`cv2`), `deskew` (PyPI), pytest;
optional extra `[dewarp-dl]` = `onnxruntime` for the UVDoc backend.

## Backend choices (aligned with spec D9)

- **Leptonica dropped.** No maintained Python binding; ctypes is fragile and
  wheel-hostile. Its deskew *is* projection-profile variance — already covered by
  the OpenCV `projection` backend. Its uniquely valuable textline-disparity dewarp
  is reimplemented clean-room as a NumPy + CuPy backend in the follow-on, not bound.
- **lmmx/page-dewarp deferred.** CLI-only, no public API, binarizes output; needs
  forking for clean maps.
- **UVDoc is the v1 dewarp** (photo path), behind the `[dewarp-dl]` extra, so v1
  dewarp needs `pip install pdomain-book-tools[dewarp-dl]` + a UVDoc ONNX artifact;
  the no-extra install still has full deskew/curvature/page-side.
- v1 `GeometryTransform.apply` is CPU (`cv2.remap`). The CuPy GPU branch lands with
  the textline dewarp follow-on (where the heavy resample makes it worthwhile).

## File structure

```
pdomain_book_tools/geometry_correction/
  __init__.py        # public exports
  transforms.py      # GeometryTransform + helpers
  protocols.py       # Protocols + result dataclasses + PageSide enum
  registry.py        # name -> backend factory registry
  pipeline.py        # GeometryPipeline reference sequence
  backends/
    __init__.py
    deskew/projection.py      # OpenCV projection-profile variance
    deskew/sbrunner.py        # wraps deskew.determine_skew
    curvature/image_based.py  # projection sharpness + edge-bend
    page_side/supplied.py     # hint passthrough
    page_side/gutter_shadow.py# dark binding-band detection
    dewarp/uvdoc.py           # ONNX UVDoc -> backward map  (extra)
    dewarp/_uvdoc_model.py    # ONNX fetch + grid->map_x/map_y math (extra)
tests/geometry_correction/
  test_transforms.py
  test_protocols_registry.py
  test_pipeline.py
  test_deskew_projection.py
  test_deskew_sbrunner.py
  test_curvature.py
  test_page_side.py
  test_dewarp_uvdoc.py
```

---

## Milestone 1 — Transform model

### Task 1: `GeometryTransform` — identity & affine

**Files:**
- Create: `pdomain_book_tools/geometry_correction/transforms.py`
- Test: `tests/geometry_correction/test_transforms.py`

- [ ] **Step 1: Write the failing test**

```python
import numpy as np
import cv2
from pdomain_book_tools.geometry_correction.transforms import GeometryTransform


def _checker(h=40, w=60):
    img = np.zeros((h, w), np.uint8)
    img[::4, :] = 255
    img[:, ::4] = 255
    return img


def test_identity_apply_is_noop():
    img = _checker()
    t = GeometryTransform.identity((img.shape[0], img.shape[1]))
    out = t.apply(img)
    assert np.array_equal(out, img)
    assert t.invertible is True


def test_affine_rotation_then_invert_roundtrips():
    img = _checker()
    h, w = img.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), 5.0, 1.0)  # 2x3
    t = GeometryTransform.affine(m, (h, w))
    inv = t.invert()
    restored = inv.apply(t.apply(img))
    # interior pixels should match closely after round trip
    inner = (slice(6, h - 6), slice(6, w - 6))
    diff = np.abs(restored[inner].astype(int) - img[inner].astype(int))
    assert diff.mean() < 12.0


def test_affine_map_points_matches_cv2():
    h, w = 40, 60
    m = cv2.getRotationMatrix2D((w / 2, h / 2), 5.0, 1.0)
    t = GeometryTransform.affine(m, (h, w))
    pts = np.array([[10.0, 12.0], [30.0, 25.0]], np.float32)
    expected = cv2.transform(pts.reshape(-1, 1, 2), m).reshape(-1, 2)
    np.testing.assert_allclose(t.map_points(pts), expected, atol=1e-4)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/geometry_correction/test_transforms.py -v`
Expected: FAIL — `ModuleNotFoundError: ... geometry_correction.transforms`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np

TransformKind = Literal["identity", "affine", "homography", "grid", "rectified"]


@dataclass(frozen=True)
class GeometryTransform:
    """A page-geometry correction expressed as a reusable, (usually) invertible map.

    - affine/homography keep a `matrix` and invert exactly.
    - grid keeps dense backward maps (`map_x`/`map_y`) for cv2.remap.
    - rectified holds a precomputed output image from a black-box backend
      (non-invertible).
    """

    kind: TransformKind
    size: tuple[int, int]  # (height, width) of the target/output
    matrix: np.ndarray | None = None
    map_x: np.ndarray | None = None
    map_y: np.ndarray | None = None
    output: np.ndarray | None = None
    invertible: bool = True

    @classmethod
    def identity(cls, size: tuple[int, int]) -> "GeometryTransform":
        return cls(kind="identity", size=size, invertible=True)

    @classmethod
    def affine(cls, matrix: np.ndarray, size: tuple[int, int]) -> "GeometryTransform":
        return cls(kind="affine", size=size, matrix=np.asarray(matrix, np.float64), invertible=True)

    def apply(self, image: np.ndarray) -> np.ndarray:
        h, w = self.size
        if self.kind == "identity":
            return image.copy()
        if self.kind == "affine":
            return cv2.warpAffine(image, self.matrix, (w, h), flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_REPLICATE)
        if self.kind == "homography":
            return cv2.warpPerspective(image, self.matrix, (w, h), flags=cv2.INTER_CUBIC,
                                       borderMode=cv2.BORDER_REPLICATE)
        raise NotImplementedError(self.kind)

    def invert(self) -> "GeometryTransform | None":
        if not self.invertible:
            return None
        if self.kind == "identity":
            return self
        if self.kind == "affine":
            full = np.vstack([self.matrix, [0, 0, 1]])
            inv = np.linalg.inv(full)[:2, :]
            return GeometryTransform.affine(inv, self.size)
        if self.kind == "homography":
            return GeometryTransform(kind="homography", size=self.size,
                                     matrix=np.linalg.inv(self.matrix), invertible=True)
        return None

    def map_points(self, pts: np.ndarray) -> np.ndarray:
        pts = np.asarray(pts, np.float32).reshape(-1, 1, 2)
        if self.kind == "affine":
            return cv2.transform(pts, self.matrix).reshape(-1, 2)
        if self.kind == "homography":
            return cv2.perspectiveTransform(pts, self.matrix).reshape(-1, 2)
        if self.kind == "identity":
            return pts.reshape(-1, 2)
        raise NotImplementedError(self.kind)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/geometry_correction/test_transforms.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add pdomain_book_tools/geometry_correction/transforms.py tests/geometry_correction/test_transforms.py
git commit -m "feat(geometry): GeometryTransform identity/affine"
```

### Task 2: `GeometryTransform` — grid (dense backward map) & rectified

**Files:**
- Modify: `pdomain_book_tools/geometry_correction/transforms.py`
- Test: `tests/geometry_correction/test_transforms.py`

- [ ] **Step 1: Write the failing test (append)**

```python
def test_grid_identity_map_is_noop():
    img = _checker()
    h, w = img.shape
    map_x, map_y = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    t = GeometryTransform.grid(map_x, map_y, (h, w))
    out = t.apply(img)
    # remap with identity maps reproduces the image (interior exact)
    assert np.array_equal(out[2:-2, 2:-2], img[2:-2, 2:-2])
    assert t.invertible is False  # grid is not analytically invertible by default


def test_rectified_holds_precomputed_output():
    img = _checker()
    rect = img[::-1].copy()
    t = GeometryTransform.rectified(rect, (img.shape[0], img.shape[1]))
    assert np.array_equal(t.apply(img), rect)  # ignores input, returns precomputed
    assert t.invert() is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/geometry_correction/test_transforms.py -k "grid or rectified" -v`
Expected: FAIL — `AttributeError: type object 'GeometryTransform' has no attribute 'grid'`

- [ ] **Step 3: Write minimal implementation (add classmethods + apply branches)**

```python
    @classmethod
    def grid(cls, map_x: np.ndarray, map_y: np.ndarray, size: tuple[int, int]) -> "GeometryTransform":
        return cls(kind="grid", size=size,
                   map_x=np.asarray(map_x, np.float32),
                   map_y=np.asarray(map_y, np.float32),
                   invertible=False)

    @classmethod
    def rectified(cls, output: np.ndarray, size: tuple[int, int]) -> "GeometryTransform":
        return cls(kind="rectified", size=size, output=np.asarray(output), invertible=False)
```

Add to `apply()` before the `raise`:

```python
        if self.kind == "grid":
            return cv2.remap(image, self.map_x, self.map_y, interpolation=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)
        if self.kind == "rectified":
            return self.output.copy()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/geometry_correction/test_transforms.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add pdomain_book_tools/geometry_correction/transforms.py tests/geometry_correction/test_transforms.py
git commit -m "feat(geometry): GeometryTransform grid + rectified kinds"
```

---

## Milestone 2 — Protocols, registry, pipeline

### Task 3: Protocols & result types

**Files:**
- Create: `pdomain_book_tools/geometry_correction/protocols.py`
- Create: `pdomain_book_tools/geometry_correction/__init__.py`
- Test: `tests/geometry_correction/test_protocols_registry.py`

- [ ] **Step 1: Write the failing test**

```python
from pdomain_book_tools.geometry_correction.protocols import (
    PageSide, DeskewResult, DewarpResult, PageSideResult, CurvatureReport,
)
from pdomain_book_tools.geometry_correction.transforms import GeometryTransform


def test_pageside_enum_members():
    assert {m.name for m in PageSide} == {"LEFT", "RIGHT", "SINGLE", "UNKNOWN"}


def test_result_dataclasses_hold_transform():
    t = GeometryTransform.identity((10, 10))
    d = DeskewResult(angle_degrees=1.5, confidence=0.9, transform=t, method="x")
    assert d.angle_degrees == 1.5 and d.transform is t
    w = DewarpResult(transform=t, confidence=0.5, method="y")
    assert w.transform is t
    ps = PageSideResult(side=PageSide.LEFT, gutter_edge="right", confidence=0.8, method="z")
    assert ps.gutter_edge == "right"
    cr = CurvatureReport(flatness=0.1, recommended="deskew_only", per_line_residuals=None, method="q")
    assert cr.recommended == "deskew_only"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/geometry_correction/test_protocols_registry.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

`protocols.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Protocol, Sequence, runtime_checkable

import numpy as np

from .transforms import GeometryTransform

GutterEdge = Literal["left", "right", "none"]
Recommended = Literal["none", "deskew_only", "dewarp"]
BBox = tuple[int, int, int, int]


class PageSide(Enum):
    LEFT = "left"
    RIGHT = "right"
    SINGLE = "single"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DeskewResult:
    angle_degrees: float
    confidence: float
    transform: GeometryTransform
    method: str


@dataclass(frozen=True)
class DewarpResult:
    transform: GeometryTransform
    confidence: float
    method: str


@dataclass(frozen=True)
class PageSideResult:
    side: PageSide
    gutter_edge: GutterEdge
    confidence: float
    method: str


@dataclass(frozen=True)
class CurvatureReport:
    flatness: float
    recommended: Recommended
    per_line_residuals: list[float] | None
    method: str


@runtime_checkable
class Deskew(Protocol):
    name: str
    def estimate(self, image: np.ndarray, *, page_side: PageSide | None = None,
                 text_lines: Sequence[BBox] | None = None) -> DeskewResult: ...


@runtime_checkable
class Dewarp(Protocol):
    name: str
    def estimate(self, image: np.ndarray, *, gutter_edge: GutterEdge | None = None,
                 text_lines: Sequence[BBox] | None = None) -> DewarpResult: ...


@runtime_checkable
class PageSideDetector(Protocol):
    name: str
    def detect(self, image: np.ndarray, *, hint: PageSide | None = None) -> PageSideResult: ...


@runtime_checkable
class CurvatureDetector(Protocol):
    name: str
    def score(self, image: np.ndarray, *,
              text_lines: Sequence[BBox] | None = None) -> CurvatureReport: ...
```

`__init__.py`:

```python
from .protocols import (
    PageSide, Deskew, Dewarp, PageSideDetector, CurvatureDetector,
    DeskewResult, DewarpResult, PageSideResult, CurvatureReport,
)
from .transforms import GeometryTransform

__all__ = [
    "PageSide", "Deskew", "Dewarp", "PageSideDetector", "CurvatureDetector",
    "DeskewResult", "DewarpResult", "PageSideResult", "CurvatureReport",
    "GeometryTransform",
]
```

Also create empty `pdomain_book_tools/geometry_correction/backends/__init__.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/geometry_correction/test_protocols_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pdomain_book_tools/geometry_correction/protocols.py pdomain_book_tools/geometry_correction/__init__.py pdomain_book_tools/geometry_correction/backends/__init__.py tests/geometry_correction/test_protocols_registry.py
git commit -m "feat(geometry): protocols and result types"
```

### Task 4: Backend registry + contract test with a fake backend

**Files:**
- Create: `pdomain_book_tools/geometry_correction/registry.py`
- Test: `tests/geometry_correction/test_protocols_registry.py`

- [ ] **Step 1: Write the failing test (append)**

```python
from pdomain_book_tools.geometry_correction.registry import (
    register_deskew, get_deskew, available, Registry,
)
from pdomain_book_tools.geometry_correction import Deskew, DeskewResult, GeometryTransform


class _FakeDeskew:
    name = "fake"
    def estimate(self, image, *, page_side=None, text_lines=None):
        return DeskewResult(0.0, 1.0, GeometryTransform.identity(image.shape[:2]), self.name)


def test_register_and_get_roundtrip():
    register_deskew("fake", _FakeDeskew)
    inst = get_deskew("fake")
    assert isinstance(inst, Deskew)  # satisfies the Protocol
    assert "fake" in available("deskew")


def test_get_unknown_raises():
    import pytest
    with pytest.raises(KeyError):
        get_deskew("nope-not-registered")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/geometry_correction/test_protocols_registry.py -k register -v`
Expected: FAIL — `ModuleNotFoundError: ... registry`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from typing import Callable

Registry = dict[str, dict[str, Callable[[], object]]]
_REGISTRY: Registry = {"deskew": {}, "dewarp": {}, "page_side": {}, "curvature": {}}


def _register(kind: str, name: str, factory: Callable[[], object]) -> None:
    _REGISTRY[kind][name] = factory


def _get(kind: str, name: str):
    try:
        return _REGISTRY[kind][name]()
    except KeyError as exc:
        raise KeyError(f"no {kind} backend named {name!r}; have {sorted(_REGISTRY[kind])}") from exc


def available(kind: str) -> list[str]:
    return sorted(_REGISTRY[kind])


def register_deskew(name, factory): _register("deskew", name, factory)
def register_dewarp(name, factory): _register("dewarp", name, factory)
def register_page_side(name, factory): _register("page_side", name, factory)
def register_curvature(name, factory): _register("curvature", name, factory)
def get_deskew(name): return _get("deskew", name)
def get_dewarp(name): return _get("dewarp", name)
def get_page_side(name): return _get("page_side", name)
def get_curvature(name): return _get("curvature", name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/geometry_correction/test_protocols_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pdomain_book_tools/geometry_correction/registry.py tests/geometry_correction/test_protocols_registry.py
git commit -m "feat(geometry): backend registry"
```

### Task 5: `GeometryPipeline` reference sequence

**Files:**
- Create: `pdomain_book_tools/geometry_correction/pipeline.py`
- Test: `tests/geometry_correction/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
import numpy as np
from pdomain_book_tools.geometry_correction.pipeline import GeometryPipeline, PipelineResult
from pdomain_book_tools.geometry_correction import (
    PageSide, DeskewResult, DewarpResult, PageSideResult, CurvatureReport, GeometryTransform,
)


class _Side:
    name = "supplied"
    def detect(self, image, *, hint=None):
        return PageSideResult(hint or PageSide.UNKNOWN, "right", 1.0, self.name)


class _Curv:
    def __init__(self, rec): self.rec = rec; self.name = "fake"
    def score(self, image, *, text_lines=None):
        return CurvatureReport(0.0, self.rec, None, self.name)


class _Dewarp:
    name = "fake"
    called = False
    def estimate(self, image, *, gutter_edge=None, text_lines=None):
        _Dewarp.called = True
        return DewarpResult(GeometryTransform.identity(image.shape[:2]), 1.0, self.name)


class _Deskew:
    name = "fake"
    def estimate(self, image, *, page_side=None, text_lines=None):
        return DeskewResult(0.0, 1.0, GeometryTransform.identity(image.shape[:2]), self.name)


def test_pipeline_skips_dewarp_when_curvature_says_flat():
    _Dewarp.called = False
    pipe = GeometryPipeline(page_side=_Side(), curvature=_Curv("deskew_only"),
                            dewarp=_Dewarp(), deskew=_Deskew())
    img = np.zeros((20, 20), np.uint8)
    res = pipe.run(img, page_side_hint=PageSide.LEFT)
    assert isinstance(res, PipelineResult)
    assert _Dewarp.called is False
    assert res.page_side.side is PageSide.LEFT
    assert res.dewarp is None and res.deskew is not None


def test_pipeline_runs_dewarp_when_curved():
    _Dewarp.called = False
    pipe = GeometryPipeline(page_side=_Side(), curvature=_Curv("dewarp"),
                            dewarp=_Dewarp(), deskew=_Deskew())
    pipe.run(np.zeros((20, 20), np.uint8), page_side_hint=PageSide.LEFT)
    assert _Dewarp.called is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/geometry_correction/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: ... pipeline`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .protocols import (
    CurvatureReport, DeskewResult, DewarpResult, PageSide, PageSideResult,
)


@dataclass(frozen=True)
class PipelineResult:
    image: np.ndarray
    page_side: PageSideResult
    curvature: CurvatureReport
    dewarp: DewarpResult | None
    deskew: DeskewResult | None


class GeometryPipeline:
    """Reference sequence: page-side -> curvature gate -> (dewarp) -> deskew (last)."""

    def __init__(self, *, page_side, curvature, deskew, dewarp=None):
        self.page_side = page_side
        self.curvature = curvature
        self.deskew = deskew
        self.dewarp = dewarp

    def run(self, image: np.ndarray, *, page_side_hint: PageSide | None = None,
            text_lines=None) -> PipelineResult:
        side = self.page_side.detect(image, hint=page_side_hint)
        curv = self.curvature.score(image, text_lines=text_lines)
        current = image
        dewarp_res = None
        if curv.recommended == "dewarp" and self.dewarp is not None:
            dewarp_res = self.dewarp.estimate(current, gutter_edge=side.gutter_edge,
                                              text_lines=text_lines)
            current = dewarp_res.transform.apply(current)
        deskew_res = None
        if curv.recommended in ("deskew_only", "dewarp"):
            deskew_res = self.deskew.estimate(current, page_side=side.side, text_lines=text_lines)
            current = deskew_res.transform.apply(current)
        return PipelineResult(current, side, curv, dewarp_res, deskew_res)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/geometry_correction/test_pipeline.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add pdomain_book_tools/geometry_correction/pipeline.py tests/geometry_correction/test_pipeline.py
git commit -m "feat(geometry): GeometryPipeline reference sequence"
```

---

## Milestone 3 — Deskew backends

### Task 6: Projection-profile deskew (OpenCV, built-in default)

**Files:**
- Create: `pdomain_book_tools/geometry_correction/backends/deskew/__init__.py` (empty)
- Create: `pdomain_book_tools/geometry_correction/backends/deskew/projection.py`
- Test: `tests/geometry_correction/test_deskew_projection.py`

- [ ] **Step 1: Write the failing test**

```python
import cv2
import numpy as np
from pdomain_book_tools.geometry_correction.backends.deskew.projection import ProjectionDeskew


def _text_page(angle_deg, h=300, w=400):
    img = np.full((h, w), 255, np.uint8)
    for y in range(40, h - 40, 18):       # horizontal "text" bars
        cv2.rectangle(img, (40, y), (w - 40, y + 6), 0, -1)
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle_deg, 1.0)
    return cv2.warpAffine(img, m, (w, h), borderValue=255)


def test_recovers_known_skew():
    skewed = _text_page(4.0)
    res = ProjectionDeskew().estimate(skewed)
    assert abs(res.angle_degrees - 4.0) < 0.75    # estimated angle ~= applied
    deskewed = res.transform.apply(skewed)
    # variance of row-sum profile is higher when text rows are axis-aligned
    def row_var(im): return float(np.var(np.sum(255 - im, axis=1)))
    assert row_var(deskewed) > row_var(skewed)


def test_flat_page_near_zero_angle():
    res = ProjectionDeskew().estimate(_text_page(0.0))
    assert abs(res.angle_degrees) < 0.75
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/geometry_correction/test_deskew_projection.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

import cv2
import numpy as np

from ...protocols import DeskewResult
from ...transforms import GeometryTransform


class ProjectionDeskew:
    """Projection-profile variance maximization (Postl's method).

    Sweeps candidate angles, rotates a binarized copy, and picks the angle whose
    horizontal pixel-sum profile has maximum variance (text rows aligned).
    """

    name = "projection"

    def __init__(self, limit: float = 15.0, coarse: float = 1.0, fine: float = 0.1):
        self.limit, self.coarse, self.fine = limit, coarse, fine

    def _binary(self, image: np.ndarray) -> np.ndarray:
        gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        return bw

    def _score(self, bw: np.ndarray, angle: float) -> float:
        h, w = bw.shape
        m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        rot = cv2.warpAffine(bw, m, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
        profile = np.sum(rot, axis=1, dtype=np.float64)
        return float(np.var(profile))

    def _search(self, bw: np.ndarray, lo: float, hi: float, step: float) -> float:
        angles = np.arange(lo, hi + step, step)
        scores = [self._score(bw, a) for a in angles]
        return float(angles[int(np.argmax(scores))])

    def estimate(self, image, *, page_side=None, text_lines=None) -> DeskewResult:
        bw = self._binary(image)
        coarse = self._search(bw, -self.limit, self.limit, self.coarse)
        angle = self._search(bw, coarse - self.coarse, coarse + self.coarse, self.fine)
        h, w = image.shape[:2]
        m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        return DeskewResult(angle_degrees=angle, confidence=1.0,
                            transform=GeometryTransform.affine(m, (h, w)), method=self.name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/geometry_correction/test_deskew_projection.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add pdomain_book_tools/geometry_correction/backends/deskew/ tests/geometry_correction/test_deskew_projection.py
git commit -m "feat(geometry): projection-profile deskew backend"
```

### Task 7: sbrunner `deskew` backend (Hough)

**Files:**
- Modify: `pyproject.toml` (add `deskew>=1.6` to dependencies)
- Create: `pdomain_book_tools/geometry_correction/backends/deskew/sbrunner.py`
- Test: `tests/geometry_correction/test_deskew_sbrunner.py`

- [ ] **Step 1: Add the dependency**

Edit `pyproject.toml` `[project] dependencies` to include:

```toml
    "deskew>=1.6",
```

Then: `uv sync`

- [ ] **Step 2: Write the failing test**

```python
import cv2
import numpy as np
from pdomain_book_tools.geometry_correction.backends.deskew.sbrunner import SbrunnerDeskew


def _text_page(angle_deg, h=300, w=400):
    img = np.full((h, w), 255, np.uint8)
    for y in range(40, h - 40, 18):
        cv2.rectangle(img, (40, y), (w - 40, y + 6), 0, -1)
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle_deg, 1.0)
    return cv2.warpAffine(img, m, (w, h), borderValue=255)


def test_recovers_known_skew():
    res = SbrunnerDeskew().estimate(_text_page(3.0))
    assert abs(res.angle_degrees - 3.0) < 0.75
    assert res.method == "sbrunner"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/geometry_correction/test_deskew_sbrunner.py -v`
Expected: FAIL — `ModuleNotFoundError: ... backends.deskew.sbrunner`

- [ ] **Step 4: Write minimal implementation**

```python
from __future__ import annotations

import cv2
import numpy as np
from deskew import determine_skew

from ...protocols import DeskewResult
from ...transforms import GeometryTransform


class SbrunnerDeskew:
    """Hough-transform skew estimate via the `deskew` PyPI package (scikit-image)."""

    name = "sbrunner"

    def estimate(self, image, *, page_side=None, text_lines=None) -> DeskewResult:
        gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        angle = determine_skew(gray)             # degrees; may be None on blank input
        angle = 0.0 if angle is None else float(angle)
        h, w = image.shape[:2]
        m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        return DeskewResult(angle_degrees=angle, confidence=1.0,
                            transform=GeometryTransform.affine(m, (h, w)), method=self.name)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/geometry_correction/test_deskew_sbrunner.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock pdomain_book_tools/geometry_correction/backends/deskew/sbrunner.py tests/geometry_correction/test_deskew_sbrunner.py
git commit -m "feat(geometry): sbrunner Hough deskew backend"
```

---

## Milestone 4 — Curvature detector (image-based gate)

### Task 8: Image-based curvature detector

**Files:**
- Create: `pdomain_book_tools/geometry_correction/backends/curvature/__init__.py` (empty)
- Create: `pdomain_book_tools/geometry_correction/backends/curvature/image_based.py`
- Test: `tests/geometry_correction/test_curvature.py`

- [ ] **Step 1: Write the failing test**

```python
import cv2
import numpy as np
from pdomain_book_tools.geometry_correction.backends.curvature.image_based import ImageBasedCurvature


def _flat_text(h=300, w=400):
    img = np.full((h, w), 255, np.uint8)
    for y in range(40, h - 40, 18):
        cv2.rectangle(img, (40, y), (w - 40, y + 5), 0, -1)
    return img


def _curved_text(h=300, w=400, amp=14):
    img = np.full((h, w), 255, np.uint8)
    xs = np.arange(w)
    for y0 in range(40, h - 40, 18):
        ys = (y0 + amp * np.sin(np.pi * xs / w)).astype(int)  # bow the rows
        for x, y in zip(xs[40:w - 40], ys[40:w - 40]):
            img[y:y + 5, x] = 0
    return img


def test_flat_page_recommends_no_dewarp():
    rep = ImageBasedCurvature().score(_flat_text())
    assert rep.recommended in ("none", "deskew_only")
    assert rep.flatness < 0.3


def test_curved_page_recommends_dewarp():
    rep = ImageBasedCurvature().score(_curved_text())
    assert rep.recommended == "dewarp"
    assert rep.flatness > 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/geometry_correction/test_curvature.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

import cv2
import numpy as np

from ...protocols import CurvatureReport


class ImageBasedCurvature:
    """Estimate page curl from how 'bowed' text rows are.

    For each detected text row we fit its dark-pixel y-position as a function of x;
    a flat row is a horizontal line, a curled row bows. The normalized mean of the
    per-row vertical spans is the flatness score (0 flat .. 1 strongly curled).
    """

    name = "image_based"

    def __init__(self, dewarp_threshold: float = 0.5, deskew_threshold: float = 0.12):
        self.dewarp_threshold = dewarp_threshold
        self.deskew_threshold = deskew_threshold

    def score(self, image, *, text_lines=None) -> CurvatureReport:
        gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        h, w = bw.shape
        # collapse into horizontal bands, then per band measure the vertical spread
        # of dark pixels across columns (a bowed row spreads vertically).
        col_centroids: list[float] = []
        residuals: list[float] = []
        band = max(8, h // 30)
        for top in range(0, h - band, band):
            strip = bw[top:top + band]
            ys, xs = np.nonzero(strip)
            if xs.size < w * 0.2:        # not a text band
                continue
            # centroid y per column bucket
            buckets = np.clip((xs / w * 10).astype(int), 0, 9)
            centers = [ys[buckets == b].mean() for b in range(10) if np.any(buckets == b)]
            if len(centers) >= 5:
                residuals.append(float(np.max(centers) - np.min(centers)))
                col_centroids.extend(centers)
        if not residuals:
            return CurvatureReport(0.0, "deskew_only", [], self.name)
        flatness = float(np.clip(np.mean(residuals) / band, 0.0, 1.0))
        if flatness >= self.dewarp_threshold:
            rec = "dewarp"
        elif flatness >= self.deskew_threshold:
            rec = "deskew_only"
        else:
            rec = "none"
        return CurvatureReport(flatness=flatness, recommended=rec,
                               per_line_residuals=residuals, method=self.name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/geometry_correction/test_curvature.py -v`
Expected: PASS (2 tests). If thresholds need tuning for the synthetic fixtures,
adjust `dewarp_threshold`/`deskew_threshold` defaults so flat→<0.3 and curved→>0.5.

- [ ] **Step 5: Commit**

```bash
git add pdomain_book_tools/geometry_correction/backends/curvature/ tests/geometry_correction/test_curvature.py
git commit -m "feat(geometry): image-based curvature gate"
```

---

## Milestone 5 — Page-side detector

### Task 9: Supplied (hint passthrough) backend

**Files:**
- Create: `pdomain_book_tools/geometry_correction/backends/page_side/__init__.py` (empty)
- Create: `pdomain_book_tools/geometry_correction/backends/page_side/supplied.py`
- Test: `tests/geometry_correction/test_page_side.py`

- [ ] **Step 1: Write the failing test**

```python
import numpy as np
from pdomain_book_tools.geometry_correction.backends.page_side.supplied import SuppliedPageSide
from pdomain_book_tools.geometry_correction import PageSide


def test_passes_hint_through_with_gutter_edge():
    res = SuppliedPageSide().detect(np.zeros((10, 10), np.uint8), hint=PageSide.LEFT)
    assert res.side is PageSide.LEFT
    assert res.gutter_edge == "right"     # left page -> gutter on the right
    res2 = SuppliedPageSide().detect(np.zeros((10, 10), np.uint8), hint=PageSide.RIGHT)
    assert res2.gutter_edge == "left"


def test_no_hint_is_unknown_none_gutter():
    res = SuppliedPageSide().detect(np.zeros((10, 10), np.uint8))
    assert res.side is PageSide.UNKNOWN and res.gutter_edge == "none"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/geometry_correction/test_page_side.py -k supplied -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

import numpy as np

from ...protocols import PageSide, PageSideResult

_GUTTER = {PageSide.LEFT: "right", PageSide.RIGHT: "left"}


class SuppliedPageSide:
    """Trust a caller-supplied side hint (from page-sequence parity / split stage)."""

    name = "supplied"

    def detect(self, image: np.ndarray, *, hint: PageSide | None = None) -> PageSideResult:
        if hint in _GUTTER:
            return PageSideResult(hint, _GUTTER[hint], 1.0, self.name)
        if hint is PageSide.SINGLE:
            return PageSideResult(PageSide.SINGLE, "none", 1.0, self.name)
        return PageSideResult(PageSide.UNKNOWN, "none", 0.0, self.name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/geometry_correction/test_page_side.py -k supplied -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pdomain_book_tools/geometry_correction/backends/page_side/ tests/geometry_correction/test_page_side.py
git commit -m "feat(geometry): supplied page-side backend"
```

### Task 10: Gutter-shadow detector backend

**Files:**
- Create: `pdomain_book_tools/geometry_correction/backends/page_side/gutter_shadow.py`
- Test: `tests/geometry_correction/test_page_side.py`

- [ ] **Step 1: Write the failing test (append)**

```python
import cv2
from pdomain_book_tools.geometry_correction.backends.page_side.gutter_shadow import GutterShadowPageSide


def _page_with_dark_edge(side):
    img = np.full((200, 300), 230, np.uint8)
    for y in range(30, 170, 14):                      # some text
        cv2.rectangle(img, (40, y), (260, y + 4), 60, -1)
    if side == "right":
        img[:, 285:] = 25                              # dark binding band on the right
    else:
        img[:, :15] = 25                               # dark binding band on the left
    return img


def test_detects_gutter_on_right_means_left_page():
    res = GutterShadowPageSide().detect(_page_with_dark_edge("right"))
    assert res.gutter_edge == "right"
    assert res.side is PageSide.LEFT


def test_detects_gutter_on_left_means_right_page():
    res = GutterShadowPageSide().detect(_page_with_dark_edge("left"))
    assert res.gutter_edge == "left"
    assert res.side is PageSide.RIGHT


def test_hint_wins_over_weak_detection():
    blank = np.full((200, 300), 230, np.uint8)         # no clear gutter
    res = GutterShadowPageSide().detect(blank, hint=PageSide.LEFT)
    assert res.side is PageSide.LEFT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/geometry_correction/test_page_side.py -k gutter -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

import cv2
import numpy as np

from ...protocols import PageSide, PageSideResult

_SIDE_FOR_GUTTER = {"right": PageSide.LEFT, "left": PageSide.RIGHT}


class GutterShadowPageSide:
    """Infer the gutter (binding) edge from a dark vertical band near a left/right edge.

    The gutter casts the darkest near-edge column band. We compare mean intensity of
    a thin strip on each side; the markedly darker side is the gutter. A caller hint,
    when given, overrides weak detections.
    """

    name = "gutter_shadow"

    def __init__(self, strip_frac: float = 0.06, min_contrast: float = 20.0):
        self.strip_frac, self.min_contrast = strip_frac, min_contrast

    def detect(self, image: np.ndarray, *, hint: PageSide | None = None) -> PageSideResult:
        gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        s = max(2, int(w * self.strip_frac))
        left_mean = float(gray[:, :s].mean())
        right_mean = float(gray[:, -s:].mean())
        contrast = abs(left_mean - right_mean)
        if contrast >= self.min_contrast:
            gutter = "left" if left_mean < right_mean else "right"
            conf = float(min(1.0, contrast / 128.0))
            return PageSideResult(_SIDE_FOR_GUTTER[gutter], gutter, conf, self.name)
        # weak/no detection: fall back to hint
        if hint in (PageSide.LEFT, PageSide.RIGHT):
            gutter = "right" if hint is PageSide.LEFT else "left"
            return PageSideResult(hint, gutter, 0.3, self.name)
        return PageSideResult(PageSide.UNKNOWN, "none", 0.0, self.name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/geometry_correction/test_page_side.py -v`
Expected: PASS (all page-side tests)

- [ ] **Step 5: Commit**

```bash
git add pdomain_book_tools/geometry_correction/backends/page_side/gutter_shadow.py tests/geometry_correction/test_page_side.py
git commit -m "feat(geometry): gutter-shadow page-side detector"
```

---

## Milestone 6 — UVDoc dewarp backend (extra)

UVDoc isn't on PyPI; we use the **ONNX** path (torch-free at inference). The model
predicts a grid `[1, 2, Gh, Gw]` in `[-1, 1]` (grid_sample convention); we upsample
it to full resolution and convert to `cv2.remap` maps with
`map_x = (gx+1)*(W-1)/2`, `map_y = (gy+1)*(H-1)/2` (verified from UVDoc `utils.py`).

### Task 11: UVDoc grid→map math + ONNX fetch (extra)

**Files:**
- Modify: `pyproject.toml` (add `[project.optional-dependencies] dewarp-dl = ["onnxruntime>=1.17"]`)
- Create: `pdomain_book_tools/geometry_correction/backends/dewarp/__init__.py` (empty)
- Create: `pdomain_book_tools/geometry_correction/backends/dewarp/_uvdoc_model.py`
- Test: `tests/geometry_correction/test_dewarp_uvdoc.py`

- [ ] **Step 1: Add the optional dependency**

Edit `pyproject.toml`:

```toml
[project.optional-dependencies]
dewarp-dl = ["onnxruntime>=1.17"]
```

Then: `uv sync --extra dewarp-dl`

- [ ] **Step 2: Write the failing test (pure math — no model needed)**

```python
import numpy as np
from pdomain_book_tools.geometry_correction.backends.dewarp._uvdoc_model import grid_to_remap


def test_identity_grid_yields_identity_maps():
    H, W, Gh, Gw = 20, 30, 5, 7
    # identity grid in [-1,1] over (Gh, Gw)
    ys = np.linspace(-1, 1, Gh, dtype=np.float32)
    xs = np.linspace(-1, 1, Gw, dtype=np.float32)
    gx, gy = np.meshgrid(xs, ys)
    grid = np.stack([gx, gy])[None]                 # (1, 2, Gh, Gw)
    map_x, map_y = grid_to_remap(grid, (H, W))
    assert map_x.shape == (H, W) and map_y.shape == (H, W)
    # corners map to image corners
    assert abs(map_x[0, 0] - 0) < 1.0 and abs(map_y[0, 0] - 0) < 1.0
    assert abs(map_x[-1, -1] - (W - 1)) < 1.0 and abs(map_y[-1, -1] - (H - 1)) < 1.0
    # applying identity maps to an image is ~no-op
    import cv2
    img = (np.random.default_rng(0).integers(0, 255, (H, W), dtype=np.uint8))
    out = cv2.remap(img, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    assert np.abs(out.astype(int) - img.astype(int)).mean() < 5.0
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/geometry_correction/test_dewarp_uvdoc.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Write minimal implementation**

```python
from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np

# UVDoc inference image size (W, H) — from upstream utils.IMG_SIZE = [488, 712]
UVDOC_INPUT_WH = (488, 712)
# Pre-exported ONNX produced via FahNos/UVDoc_onnx make_onnx.py (opset 11).
# Provided/hosted separately; path overridable for tests and ops.
UVDOC_MODEL_ENV = "PD_UVDOC_ONNX"


def grid_to_remap(grid: np.ndarray, size: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """Convert a UVDoc grid (1,2,Gh,Gw) in [-1,1] to full-res cv2.remap maps."""
    h, w = size
    g = grid[0]                                   # (2, Gh, Gw): channel 0 = x, 1 = y
    gx = cv2.resize(g[0], (w, h), interpolation=cv2.INTER_LINEAR)
    gy = cv2.resize(g[1], (w, h), interpolation=cv2.INTER_LINEAR)
    map_x = ((gx + 1.0) * (w - 1) / 2.0).astype(np.float32)
    map_y = ((gy + 1.0) * (h - 1) / 2.0).astype(np.float32)
    return map_x, map_y


def resolve_model_path(explicit: str | os.PathLike | None = None) -> Path:
    path = explicit or os.environ.get(UVDOC_MODEL_ENV)
    if not path:
        raise FileNotFoundError(
            "UVDoc ONNX model not found. Set PD_UVDOC_ONNX or pass model_path. "
            "Produce it via FahNos/UVDoc_onnx make_onnx.py."
        )
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"UVDoc ONNX model not found at {p}")
    return p


def run_uvdoc(image_rgb: np.ndarray, model_path: Path) -> np.ndarray:
    """Run UVDoc ONNX, returning the grid (1,2,Gh,Gw)."""
    import onnxruntime as ort  # lazy: only when the extra is installed

    inp = cv2.resize(image_rgb.astype(np.float32) / 255.0, UVDOC_INPUT_WH)
    inp = inp.transpose(2, 0, 1)[None]            # (1,3,H,W)
    sess = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    out = sess.run(None, {sess.get_inputs()[0].name: inp.astype(np.float32)})
    return np.asarray(out[0])                     # point_positions2D
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/geometry_correction/test_dewarp_uvdoc.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock pdomain_book_tools/geometry_correction/backends/dewarp/ tests/geometry_correction/test_dewarp_uvdoc.py
git commit -m "feat(geometry): UVDoc grid->remap math + onnx loader"
```

### Task 12: UVDoc `Dewarp` backend

**Files:**
- Create: `pdomain_book_tools/geometry_correction/backends/dewarp/uvdoc.py`
- Test: `tests/geometry_correction/test_dewarp_uvdoc.py`

- [ ] **Step 1: Write the failing test (uses a fake grid producer — no real model)**

```python
import cv2
import numpy as np
import pytest
from pdomain_book_tools.geometry_correction.backends.dewarp.uvdoc import UVDocDewarp
from pdomain_book_tools.geometry_correction import DewarpResult, GeometryTransform


def _identity_grid(Gh=5, Gw=7):
    ys = np.linspace(-1, 1, Gh, dtype=np.float32)
    xs = np.linspace(-1, 1, Gw, dtype=np.float32)
    gx, gy = np.meshgrid(xs, ys)
    return np.stack([gx, gy])[None]


def test_backend_builds_grid_transform_from_injected_runner():
    img = np.random.default_rng(1).integers(0, 255, (40, 60, 3), dtype=np.uint8)
    backend = UVDocDewarp(runner=lambda rgb: _identity_grid())  # inject fake grid
    res = backend.estimate(img)
    assert isinstance(res, DewarpResult)
    assert res.transform.kind == "grid"
    assert res.transform.map_x.shape == (40, 60)
    out = res.transform.apply(img)
    assert np.abs(out.astype(int) - img.astype(int)).mean() < 6.0  # identity ~ no-op


def test_missing_model_raises_helpful_error():
    backend = UVDocDewarp()                       # no runner, no model env set
    with pytest.raises(FileNotFoundError):
        backend.estimate(np.zeros((20, 20, 3), np.uint8))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/geometry_correction/test_dewarp_uvdoc.py -k backend -v`
Expected: FAIL — `ModuleNotFoundError: ... backends.dewarp.uvdoc`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from ...protocols import DewarpResult
from ...transforms import GeometryTransform
from ._uvdoc_model import grid_to_remap, resolve_model_path, run_uvdoc


class UVDocDewarp:
    """UVDoc (ONNX) dewarp: predicts a backward grid, applied via cv2.remap.

    `runner` is injectable for testing; in production it defaults to ONNX inference
    against the model at `model_path` / $PD_UVDOC_ONNX.
    """

    name = "uvdoc"

    def __init__(self, *, model_path: str | Path | None = None,
                 runner: Callable[[np.ndarray], np.ndarray] | None = None):
        self._model_path = model_path
        self._runner = runner

    def _grid(self, image_rgb: np.ndarray) -> np.ndarray:
        if self._runner is not None:
            return self._runner(image_rgb)
        return run_uvdoc(image_rgb, resolve_model_path(self._model_path))

    def estimate(self, image, *, gutter_edge=None, text_lines=None) -> DewarpResult:
        rgb = image if image.ndim == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        grid = self._grid(rgb)
        h, w = image.shape[:2]
        map_x, map_y = grid_to_remap(grid, (h, w))
        return DewarpResult(transform=GeometryTransform.grid(map_x, map_y, (h, w)),
                            confidence=1.0, method=self.name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/geometry_correction/test_dewarp_uvdoc.py -v`
Expected: PASS (all UVDoc tests)

- [ ] **Step 5: Commit**

```bash
git add pdomain_book_tools/geometry_correction/backends/dewarp/uvdoc.py tests/geometry_correction/test_dewarp_uvdoc.py
git commit -m "feat(geometry): UVDoc dewarp backend"
```

---

## Milestone 7 — Default registration, CI, docs

### Task 13: Register defaults + factory helpers + docs

**Files:**
- Modify: `pdomain_book_tools/geometry_correction/__init__.py`
- Create: `pdomain_book_tools/geometry_correction/defaults.py`
- Modify: `pdomain_book_tools/geometry_correction/registry.py` (import defaults on first use)
- Create: `docs/usage/geometry-correction.md` (repo docs)
- Test: `tests/geometry_correction/test_protocols_registry.py`

- [ ] **Step 1: Write the failing test (append)**

```python
def test_builtin_backends_are_registered():
    from pdomain_book_tools.geometry_correction import registry
    registry.ensure_defaults()
    assert "projection" in registry.available("deskew")
    assert "sbrunner" in registry.available("deskew")
    assert "image_based" in registry.available("curvature")
    assert "supplied" in registry.available("page_side")
    assert "gutter_shadow" in registry.available("page_side")
    assert "uvdoc" in registry.available("dewarp")   # registered even if extra absent


def test_default_pipeline_builds_and_runs_on_flat_page():
    import numpy as np, cv2
    from pdomain_book_tools.geometry_correction.defaults import default_pipeline
    img = np.full((200, 300), 255, np.uint8)
    for y in range(30, 170, 14):
        cv2.rectangle(img, (40, y), (260, y + 4), 0, -1)
    res = default_pipeline().run(img)
    assert res.image.shape == img.shape         # flat page: deskew-only, shape preserved
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/geometry_correction/test_protocols_registry.py -k "builtin or default_pipeline" -v`
Expected: FAIL — `AttributeError: ... ensure_defaults` / `ModuleNotFoundError: ... defaults`

- [ ] **Step 3: Write minimal implementation**

Add to `registry.py`:

```python
_DEFAULTS_LOADED = False


def ensure_defaults() -> None:
    global _DEFAULTS_LOADED
    if _DEFAULTS_LOADED:
        return
    from .backends.deskew.projection import ProjectionDeskew
    from .backends.deskew.sbrunner import SbrunnerDeskew
    from .backends.curvature.image_based import ImageBasedCurvature
    from .backends.page_side.supplied import SuppliedPageSide
    from .backends.page_side.gutter_shadow import GutterShadowPageSide
    from .backends.dewarp.uvdoc import UVDocDewarp
    register_deskew("projection", ProjectionDeskew)
    register_deskew("sbrunner", SbrunnerDeskew)
    register_curvature("image_based", ImageBasedCurvature)
    register_page_side("supplied", SuppliedPageSide)
    register_page_side("gutter_shadow", GutterShadowPageSide)
    register_dewarp("uvdoc", UVDocDewarp)
    _DEFAULTS_LOADED = True
```

Create `defaults.py`:

```python
from __future__ import annotations

from .pipeline import GeometryPipeline
from . import registry


def default_pipeline(*, with_dewarp: bool = False) -> GeometryPipeline:
    """Reference pipeline. Dewarp is opt-in (requires the [dewarp-dl] extra + model)."""
    registry.ensure_defaults()
    dewarp = registry.get_dewarp("uvdoc") if with_dewarp else None
    return GeometryPipeline(
        page_side=registry.get_page_side("gutter_shadow"),
        curvature=registry.get_curvature("image_based"),
        deskew=registry.get_deskew("projection"),
        dewarp=dewarp,
    )
```

Write `docs/usage/geometry-correction.md` documenting: the protocols, the
built-in backends, the `[dewarp-dl]` extra + `PD_UVDOC_ONNX` model requirement,
the reference pipeline, and the split-upstream / page-side-hint contract. Link the
spec at `docs/specs/2026-06-02-geometry-correction-design.md`.

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest tests/geometry_correction/ -v`
Expected: PASS (all tests). Then `make ci` (lint + type + test) green.

- [ ] **Step 5: Commit**

```bash
git add pdomain_book_tools/geometry_correction/ docs/usage/geometry-correction.md tests/geometry_correction/test_protocols_registry.py
git commit -m "feat(geometry): register default backends + reference pipeline + docs"
```

---

## Follow-on (separate plan, not this repo)

- **prep wiring** (`pdomain-prep-for-pgdp`): host the curvature gate + deskew (and
  optional UVDoc dewarp) in prep's existing deskew step; feed `page_side` from
  even/odd parity via `split_ops`; consume `GeometryPipeline`. New plan with
  `repo: pdomain-prep-for-pgdp`.
- **classical `textline_disparity` dewarp** (this repo, own spec/plan): clean-room
  NumPy + CuPy reimplementation of Leptonica's textline-disparity model — the
  scanned-page workhorse, even/odd-aware, weights-free; ships with the
  `GeometryTransform` CuPy GPU-apply branch. See its dedicated spec.
- **post-v1 backends** (this repo): DocRes/DewarpNet (extras), line-based
  curvature/deskew, margin-asymmetry page-side, lmmx/page-dewarp (if ever),
  GPU-dispatch injection hook.

## Verify before shipping

- UVDoc ONNX artifact: produce via `FahNos/UVDoc_onnx`, confirm **weight license**
  permits redistribution before hosting alongside our Unlicense code.
- `make ci` xdist (`-n auto`) stays green; the real-model UVDoc smoke test (marked,
  needs `PD_UVDOC_ONNX`) runs only where the model is present.
