---
repo: pdomain-book-tools
depends-on: docs/specs/2026-06-02-geometry-correction-design.md
---

# Textline-disparity dewarp (NumPy + CuPy) — design

Date: 2026-06-02
Status: design drafted; pending review → implementation plan
Primary home: `pdomain-book-tools`
Parent: [`2026-06-02-geometry-correction-design.md`](2026-06-02-geometry-correction-design.md) (D9)

## 1. Goal

A classical, **weights-free** `textline_disparity` backend implementing the
`Dewarp` protocol from the `geometry_correction` package — the **scanned-page
workhorse** that UVDoc (ML/photo) and page_dewarp (cubic-sheet/photo) don't cover.
Full-fidelity, clean-room reimplementation of Leptonica's textline-disparity model:
vertical + horizontal disparity, **even/odd-page aware**. NumPy default, CuPy GPU
path for the heavy resample. Routed against UVDoc by a regime signal.

Why clean-room and not a Leptonica binding: no maintained Python binding, fragile
ctypes, and cross-platform-wheel-hostile C linkage — versus an owned, Unlicense-clean,
invertible, GPU-capable implementation that fits the repo's existing
`cv2_processing`/`cupy_processing` pattern. (Leptonica's license is BSD-style and
even port-compatible; we reimplement from the published algorithm to stay
Unlicense-clean.)

## 2. Decisions

| # | Decision | Rationale |
|---|---|---|
| T1 | **Full-fidelity** model: vertical disparity + horizontal disparity + even/odd line-end referencing, built together. | The even/odd handling is the unique value; horizontal disparity is where it lives. |
| T2 | **Strict parallel modules**: full NumPy impl in `cv2_processing/`, full CuPy mirror in `cupy_processing/`, identical APIs. | Matches the repo's established `rotate.py`/`deskew.py` convention; clear, explicit device separation (CT's call). |
| T3 | **Gate emits a regime**; pipeline routes. flat→deskew-only, flat_curl→`textline_disparity`, oblique→UVDoc; caller override. | One automatic decision point; keeps the two dewarp backends in their correct regimes. |
| T4 | **`TextlineDetector` seam + one default** (morph-centroid-quadratic, Leptonica-faithful). | Structural room for strip-projection / ML baseline detectors later, without building them now (YAGNI). |
| T5 | **Leptonica-faithful method** (confirmed against source). | Proven on dense book text; reuses existing `morph.py` + `contours.py`; deliberately NOT Hough (Hough = straight-line/deskew tool, can't trace curved baselines). |
| T6 | Backend returns a **`grid` `GeometryTransform`** (dense backward map), and this work lands the **CuPy `apply` branch** on `GeometryTransform`. | Invertible-ish, composable, cacheable; GPU resample where it pays. |

## 3. Algorithm (clean-room, Leptonica-faithful)

Confirmed against `src/dewarp1.c` / `dewarp2.c` / `dewarp.h` and the dewarping docs.

1. **Binarize** — Otsu (reuse `cv2_processing/threshold.py` / `cupy_processing/threshold.py`).
2. **Textline detection** (`TextlineDetector`, default = morph-centroid):
   - Horizontal morphological consolidation fusing each row into a solid bar — a
     close/open sequence with sizes scaled to page width (Leptonica uses
     `"o1.3 + c{csize1}.1 + o{csize1}.1 + c{csize2}.1"`, `csize1=max(15,w/80)`,
     `csize2=max(40,w/30)`; reuse `morph.py`).
   - Tall-component removal (erosion seed + seedfill) to strip figures / drop-caps
     (reuse `contours.py` size filtering).
   - **Per-column vertical centroid**: for each consolidated line component, the
     weighted-center y at each x → `(x, y_center)` sample points.
3. **Baseline fit** — per line, **order-2 least-squares** quadratic
   `y(x)=c₂x²+c₁x+c₀` (Leptonica's `ptaGetQuadraticLSF`; order 2 by design — higher
   orders amplify outliers/print defects).
4. **Vertical disparity `V(x,y)`** — flatten each baseline to a reference y; quadratic
   fit horizontally (per line) then vertically (across lines) on a subsampled grid;
   interpolate to a dense full-res field.
5. **Horizontal disparity `H(x,y)`** — from the **left/right line-END positions** of
   full-length textlines. **Even/odd referencing**: relative to the **minimum**
   line-ends for **even/verso (left)** pages and the **maximum** for **odd/recto
   (right)** pages — parity taken from the `gutter_edge` passed into `estimate()`.
   (Leptonica enforces parity: an even-page model is applied only to even pages.)
6. **Backward map** — `map_x = x_grid + H`, `map_y = y_grid + V` → `GeometryTransform.grid(map_x, map_y, size)`.
7. **Apply** — NumPy: `cv2.remap`; CuPy: `cupyx.scipy.ndimage.map_coordinates`.
8. **Fallback** — fewer than `min_textlines` detected (sparse text, heavy figure
   pages, strong perspective) ⇒ return `GeometryTransform.identity` + `confidence=0`.
   The gate/caller then defers to UVDoc (if enabled) or skips dewarp.

## 4. Module layout (strict parallel)

```
pdomain_book_tools/
  image_processing/
    cv2_processing/textline_dewarp.py     # NumPy: detect, fit, build maps, apply (cv2.remap)
    cupy_processing/textline_dewarp.py     # CuPy mirror, identical API, require_cupy() guard
  geometry_correction/
    backends/dewarp/textline.py            # Dewarp backend wrapper (picks np/cupy module)
    detectors/textline.py                  # TextlineDetector seam + morph-centroid default
    transforms.py                          # + array-module-aware apply (CuPy branch) — D9
    regime.py                              # regime classifier feeding the routing gate
```

Each `textline_dewarp.py` exposes the same functions, e.g.:

```python
def detect_textlines(binary, *, page_width) -> list[LineSamples]: ...   # (x, y_center) per line
def fit_baselines(lines) -> list[QuadCoeffs]: ...                       # c2, c1, c0
def build_disparity_maps(coeffs, line_ends, size, *, gutter_edge) -> tuple[map_x, map_y]: ...
def apply_disparity(image, map_x, map_y) -> ndarray: ...                # cv2.remap | map_coordinates
```

The backend wrapper selects the module by GPU availability / a `prefer_gpu` flag
(via `_cupy_compat`), returns `DewarpResult(transform=GeometryTransform.grid(...),
confidence, method="textline_disparity")`, and passes `gutter_edge` through.

`TextlineDetector` seam:

```python
class TextlineDetector(Protocol):
    name: str
    def detect(self, binary, *, page_width) -> list[LineSamples]: ...
# default: MorphCentroidDetector  (the Leptonica-faithful method above)
# future drop-ins: StripProjectionDetector, MLBaselineDetector (kraken/DocTR)
```

## 5. Routing — regime detector

`regime.py` classifies a page into `regime ∈ {flat, flat_curl, oblique}` (extends
the curvature gate's output):

- **flat** — low baseline curvature, parallel straight page edges → deskew only.
- **flat_curl** — bowed baselines + roughly parallel page edges (near-frontal scan
  with spine curl) → `textline_disparity`.
- **oblique** — converging page edges / strong keystone (phone perspective) → UVDoc.

Signals: page-edge straightness & convergence (line fits to detected page borders) +
aggregate baseline curvature. The pipeline maps regime→backend; the **caller may
override** (e.g. prep forces `textline_disparity` for a known-scanned batch).

## 6. Testing

- **Synthetic warp round-trip**: flat synthetic text page + known vertical bow
  (quadratic/sinusoidal) → dewarp → assert baseline-curvature residual drops below
  threshold and recovered `map ≈` inverse of the applied warp.
- **Even/odd**: synthetic left vs right page with opposite-side line-end stretch →
  assert `H` references the correct side per `gutter_edge` (min for even, max for odd).
- **Fallback**: blank / sparse page → identity transform, `confidence=0`.
- **Detector contract**: a fake `TextlineDetector` proves the seam; the morph-centroid
  detector recovers known line positions on a synthetic page.
- **NumPy↔CuPy parity** + **`GeometryTransform` CuPy-apply parity**: same input →
  maps/outputs match within tolerance. Gated by `skipif_no_cupy` / `@pytest.mark.gpu`
  (runs on the workspace GPU; skipped in CI — honors "no heavy tests on GitHub").
- **Regime detector**: flat / flat_curl / oblique fixtures → correct class.
- Mirrors `tests/image_processing/{cv2,cupy}_processing/` layout.

## 7. Scope & phasing

Full model in one plan, phased as commits: (A) `TextlineDetector` seam +
morph-centroid detector (NumPy) + baseline fit; (B) vertical disparity + NumPy
apply; (C) horizontal disparity + even/odd; (D) CuPy mirror + `GeometryTransform`
CuPy apply; (E) regime detector + pipeline routing; (F) backend registration.
`repo: pdomain-book-tools`. Depends on the v1 `geometry_correction` package.

## 8. Verify before shipping

- Copy the morphological sel sequence + `csize` formulas **verbatim** from
  `src/dewarp2.c` (the research pass read them via a summarized fetch, not a raw
  paste) before finalizing the detector defaults.
- CuPy/CUDA availability assumptions: NumPy fallback must keep CI green on GPU-less
  runners; the heavy GPU parity tests run only where CUDA is present.
- Confirm `cupyx.scipy.ndimage.map_coordinates` matches `cv2.remap` conventions
  (coordinate order, border handling) within the parity tolerance.
