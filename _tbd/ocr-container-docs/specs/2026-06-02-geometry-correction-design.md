# Geometry correction (deskew / dewarp) — design

Date: 2026-06-02
Status: design approved; plan written; refined post-research (see D9)
Primary home: `pdomain-book-tools`
Consumers: `pdomain-prep-for-pgdp` (first), `pdomain-ocr-cli`, others
Research: [`docs/research/deskew/`](../research/deskew/) (11 files),
[`docs/research/dewarp/`](../research/dewarp/) (21 files),
[`docs/research/2026-06-02-deskew-dewarp-backend-options.md`](../research/2026-06-02-deskew-dewarp-backend-options.md)

## 1. Goal

Provide swappable **`Deskew`** and **`Dewarp`** protocols (plus supporting
`PageSideDetector` and `CurvatureDetector`) in the foundation library, each with
multiple backends, so any pd-* consumer can correct page geometry before its own
(separate) OCR step. Out of scope: OCR itself, and coordinate hand-off to OCR
(kept *possible* via invertible transforms, but not wired here).

Input regimes are mixed and both first-class: **flatbed scans** (mostly skew,
sometimes gutter curl) and **phone photos** (perspective + stronger curl + a page
that must be located in clutter).

## 2. Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | Protocols operate on a **single page**. | Splitting and side-identity are separate concerns; keeps each protocol small and testable. |
| D2 | **Split is an upstream precondition**, not part of this package. | Two-up → L/R happens first (existing `image_processing/cv2_processing/split.py`; prep's `split_ops`). Left/right pages skew & curl differently, so they must already be separate pages before geometry correction. |
| D3 | **Page side = caller hint, else detect.** First-class `PageSideDetector`. | The split stage / page-number parity gives a reliable hint; a content detector confirms/overrides. Side tells dewarp which edge is the gutter (hardest curl). Prior art: Leptonica's dewarp already treats even vs odd pages differently. |
| D4 | **Permissive backends built-in; non-commercial opt-in; weights separately licensed.** | Our code is Unlicense/public-domain. Classical/CV backends carry no weight-license exposure and ship built-in. DL backends are opt-in extras that fetch their own license-flagged weights and are never bundled. |
| D5 | **Image-based curvature/deskew by default; optional line backend; accept `text_lines` hint.** | The real OCR runs *after* this stage, so we can't lean on its line boxes. Image signals (projection profile, edge bend, gutter shadow, FFT) are cheap and public-domain-clean. |
| D6 | **book-tools owns protocols + composable backends; consumers orchestrate ordering.** | Foundation lib already holds the image code (`deskew.py`, `rotate.py`, `perspective_adjustment.py`) and the `typing.Protocol` house style. Consumers decide stage order/skips; DL backends accept an injected GPU dispatcher (prep passes `pdomain-ops`'). |
| D7 | **v1 includes dewarp**: UVDoc behind the `[dewarp-dl]` extra (photo path). | Dewarp is the high-value capability; ship a working slice. The classical scanned-page backend follows (D9). |
| D8 | Package name: `pdomain_book_tools/geometry_correction/`. | — |
| D9 | **Post-research backend reality** (supersedes earlier Leptonica choices). | (1) **Leptonica deskew dropped** — it *is* projection-profile variance (Postl), which our OpenCV `projection` backend already reimplements; nothing unique is lost. (2) **No Leptonica binding, no Rust.** Its uniquely valuable piece is the *textline-disparity dewarp* (classical, weights-free, even/odd-aware, flat-scan-safe) — which UVDoc (ML/photo) and page_dewarp (cubic-sheet/photo) do **not** cover. We reimplement it clean-room as a **NumPy + CuPy** backend (follow-on), mirroring book-tools' existing `cv2_processing`/`cupy_processing` split: NumPy default (CI, no-GPU), CuPy for the heavy resample on the workspace GPU. (3) **lmmx/page-dewarp deferred** (CLI-only, binarizes, needs forking). |

## 3. Module layout

```
pdomain_book_tools/geometry_correction/
  protocols.py      # Deskew, Dewarp, PageSideDetector, CurvatureDetector + result types
  transforms.py     # GeometryTransform: matrix | backward-map, compose(), invert(), map_points()
  registry.py       # name -> backend factory; consumers select backends by string
  pipeline.py       # thin optional GeometryPipeline helper for the reference sequence
  backends/
    deskew/         # projection (OpenCV), sbrunner_hough; ocr_baseline*
    dewarp/         # uvdoc* (photo path); textline_disparity (numpy+cupy, follow-on)  (* = extra)
    page_side/      # supplied, gutter_shadow
    curvature/      # projection, edge_bend
```

`*` = behind an install extra. Splitting is **not** in this package — it stays in
`image_processing/` and runs upstream.

DL deps gated by extras (`pdomain-book-tools[dewarp-dl]`, torch). Nothing heavy or
weight-licensed imports unless that extra is installed and the backend is enabled.

## 4. Protocols

All take a single-page image; `estimate()`/`detect()` return a result carrying a
`GeometryTransform` (not pixels) so stages compose and stay invertible.

```python
class Deskew(Protocol):
    name: str
    def estimate(self, img, *, page_side=None, text_lines=None) -> DeskewResult: ...
    # DeskewResult: angle_degrees: float; confidence: float; transform: GeometryTransform; method: str

class Dewarp(Protocol):
    name: str
    def estimate(self, img, *, gutter_edge=None, text_lines=None) -> DewarpResult: ...
    # DewarpResult: transform: GeometryTransform; confidence: float; method: str

class PageSideDetector(Protocol):
    def detect(self, img, *, hint: "PageSide | None" = None) -> PageSideResult: ...
    # PageSide: LEFT | RIGHT | SINGLE | UNKNOWN
    # PageSideResult: side: PageSide; gutter_edge: Literal["left","right","none"]; confidence; method

class CurvatureDetector(Protocol):
    def score(self, img, *, text_lines=None) -> CurvatureReport: ...
    # CurvatureReport: flatness: float; recommended: Literal["none","deskew_only","dewarp"];
    #                  per_line_residuals: list[float] | None; method: str
```

`text_lines` (optional) is the seam for OCR-leveraging backends without coupling
the protocol to any OCR engine.

## 5. Transform model

```python
@dataclass(frozen=True)
class GeometryTransform:
    kind: Literal["identity", "affine", "homography", "grid", "rectified"]
    matrix: NDArray | None          # affine/homography fast path (exact inverse)
    map_x: NDArray | None           # grid backward map (dst->src) for cv2.remap
    map_y: NDArray | None
    output: NDArray | None          # rectified: precomputed image from a black-box backend
    invertible: bool
    def apply(self, img) -> "Image": ...
    def invert(self) -> "GeometryTransform | None": ...
    def map_points(self, pts) -> "NDArray": ...   # move boxes between original/rectified space
```

`compose()` chains the full stage sequence into one transform. Deskew/perspective
keep a matrix (exact invert); grid dewarp keeps backward maps and a forward map
when the backend supplies one. Non-invertible backends (e.g. a GAN) set
`invertible=False`. This keeps OCR coordinate hand-off *possible* later at zero
cost now.

`apply()` is array-module-aware: with NumPy maps it uses `cv2.remap` (CPU); with
CuPy maps it uses `cupyx.scipy.ndimage.map_coordinates` (GPU). The heavy per-pixel
resample is the main GPU win — it accelerates the classical textline dewarp (D9)
and large-page deskew apply for free, with NumPy as the always-available fallback.

## 6. Orchestration & the even/odd flow

book-tools provides the parts; **consumers own ordering**. Reference sequence:

```
UPSTREAM (separate stage):  Split  (two-up → L/R single pages, each tagged provisional side)
        │
        ▼  one single page in
geometry_correction:  PageSide.detect(hint=parity)
                   →  Curvature.score → gate
                   →  Dewarp(gutter_edge) if curved
                   →  Deskew (residual, ALWAYS last)
```

- Already-split single pages (the common case) skip Split; parity from
  filename/sequence is the `page_side` hint, confirmed/overridden by the detector.
- Page side → `gutter_edge` prior for dewarp (left page ⇒ gutter on right).
- **prep wiring:** `split_ops` feeds provisional side; prep's existing "deskew
  step" hosts Curvature + Deskew and optionally Dewarp; even/odd parity is the hint
  source. A thin `GeometryPipeline` helper offers the reference sequence for
  consumers that don't want to hand-wire it.

Two invariants: **Deskew always runs last** (cheap residual cleanup, idempotent on
flat input); **Dewarp is gated** (never runs on a page the curvature detector calls
flat).

## 7. Curvature gating

Image-based default: horizontal projection-profile sharpness + a low-order
polynomial fit to detected page top/bottom edges → `recommended ∈ {none,
deskew_only, dewarp}`. The pipeline invokes Dewarp only when the gate fires —
this is what stops a phone-photo-trained DL model from warping an already-flat
flatbed page. DL dewarp requires *both* the gate firing *and* the backend enabled.

## 8. Backend menu & verified facts

Built-in (permissive, no weight-license exposure):

| Protocol | Backend | License | Maintained | Notes |
|---|---|---|---|---|
| Deskew | projection (OpenCV) | (ours) | — | **v1**; Postl variance — same algorithm as Leptonica `pixDeskew` |
| Deskew | sbrunner-Hough | MIT | yes — 1.6.0 (2026-04) | **v1**; pure-pip, scikit-image; ±45/±90 |
| Dewarp | `textline_disparity` (NumPy + CuPy, clean-room) | (ours) | — | **follow-on**; classical, weights-free, **even/odd-aware**, flat-scan-safe; dense backward map; GPU resample via CuPy. The scanned-page workhorse (D9) |
| PageSide | supplied / gutter_shadow | (ours) | — | **v1**; hint + dark-binding-band detection |
| Curvature | projection / edge_bend | (ours) | — | **v1**; image-based |

Opt-in DL (extras; **verify weight license before bundling/distributing**):

| Backend | Code license | Weights | Note |
|---|---|---|---|
| UVDoc | MIT | in-repo `best_model.pkl`; research origin — **verify redistribution** | grid/UV map → clean `cv2.remap`; ONNX-friendly; gentle on flat input |
| DocRes | MIT | OneDrive | multitask (dewarp+deshadow+deblur); dewarp head = backward map |
| DewarpNet | MIT | public | older (py2-era deps), heavier setup |

Excluded / deferred (license or readiness):

- **DocTr / DocTr++ / DocGeoNet (fh2019ustc)** — **non-commercial license**;
  opt-in only, never bundled.
- **DocScanner** — **non-commercial license**; opt-in only.
- **DDCP** — MIT code but **no pretrained weights** (train-your-own).
- **ocrd_anybaseocr** GAN dewarp — removed in OCR-D v3; non-invertible raster out.
- **ScanTailor** (Advanced/Universal) — GUI-only, not batch-scriptable.
- **Alyn** — unmaintained (2017), superseded by sbrunner.
- **Leptonica** (deskew + dewarp) — no maintained Python binding; ctypes fragile and
  cross-platform-wheel-hostile. Deskew is redundant; the dewarp algorithm is
  reimplemented clean-room as `textline_disparity` (D9) rather than bound.
- **lmmx/page-dewarp** — deferred: CLI-only, binarizes, needs forking for clean maps.

## 9. Testing

- **Round-trip**: rotate/warp a known image by a known amount → estimator recovers
  it within tolerance; applied transform restores the original.
- **Flat-input identity**: every Dewarp backend must be ~no-op on a flat page
  (guards the warp-introduction risk); curvature returns `none` on flat input,
  `dewarp` on synthetically curled input.
- **Protocol contract**: a fake in-memory backend proves registry + pipeline wiring
  with no model. DL smoke tests are separately marked and skip only when the
  *extra* is absent (never silently skipped on a normal build).
- Mirrors existing `tests/image_processing/` patterns.

## 10. Scope

**v1 builds:** protocols + `transforms` + `registry` + `pipeline`; Deskew
(projection + sbrunner); Curvature (image-based); PageSide (supplied +
gutter_shadow); Dewarp protocol + UVDoc behind the `[dewarp-dl]` extra (photo
path); round-trip + flat-identity + contract tests. v1 `GeometryTransform.apply`
is CPU (`cv2.remap`); the CuPy branch lands with the textline dewarp.

**Follow-on (own spec/plan):** the classical `textline_disparity` dewarp
(NumPy + CuPy) — the scanned-page workhorse; the `GeometryTransform` GPU-apply
path; prep wiring (`pdomain-prep-for-pgdp` plan).

**Deferred:** other DL backends (DocRes, DewarpNet), line-based curvature/deskew
backend, non-commercial opt-in backends, margin-asymmetry/page-number page-side
detectors, lmmx/page-dewarp, and the GPU-dispatch injection hook.

## 11. Verify before shipping

- UVDoc (and any DL) **weight** redistribution terms vs our Unlicense code.
- CuPy/CUDA availability assumptions for the `textline_disparity` GPU path — NumPy
  fallback must keep CI green on GPU-less runners (heavy GPU smoke stays local).
- `mzucker/unproject_text` license (LICENSE.txt didn't render) — only matters if
  we later add ellipse-perspective.
