# Deskew & Dewarp: pluggable-backend guide

Date: 2026-06-02
Status: research / design input (no code yet)
Audience: `pdomain-book-tools` (likely protocol home), `pdomain-prep-for-pgdp`
(curvature-gated deskew step), any pd-* consumer.

## Goal

Define two thin **protocols** — `Deskew` and `Dewarp` — each with several
swappable backends, plus a shared **curvature/flatness detector** that decides
which correction a page actually needs. The prep-for-pgdp "deskew" step is a
natural host for the detector.

**In scope:** the geometry-correction step only — take a page image in, return
a flattened/straightened page (and the transform used). **Out of scope:** OCR
itself; you already have a separate OCR stage. A backend that *internally*
leverages OCR or text-line detection to estimate geometry is fine and is called
out explicitly below.

**Input regimes are mixed.** Two distinct sources:

- **Flatbed scan** — page is physically flat. Dominant defect is in-plane
  **skew**; sometimes mild **gutter curl** near the spine on thick books.
- **Photo** (phone/camera, increasingly common) — adds **perspective/keystone**
  distortion, stronger **3D curl**, lifted corners, and a cluttered background
  the page must be **located and cropped** out of first.

A backend that's great for one regime can be wrong for the other, so the
protocol must let callers pick (or auto-pick) per page.

## The problem is really three sub-problems

1. **Page localization / crop** (photos only) — find the page quadrilateral in
   a cluttered photo and cut it out.
2. **Geometric rectification:**
   - **Perspective** (keystone): flat page, wrong viewing angle → a homography.
   - **Curl / warp**: page surface bends in 3D (spine gutter, wave, fold) → a
     dense non-linear remap.
   - **Skew**: residual in-plane rotation → a single angle.
3. **Decision**: which of the above a given page needs (flatness/curvature
   detection), so flat pages skip the expensive/risky steps.

Skew correction is cheap, robust, and well-solved. Curl correction is not
solved for the flatbed case specifically — every strong dewarp model is trained
on **phone photos** of curled pages, so it's a good fit for your photo inputs
but can *introduce* distortion on an already-flat scan. That asymmetry is why
dewarp must be **gated**, and why deskew and dewarp are separate protocols
rather than one "rectify" call.

## Recommended decomposition into protocols

| Protocol | Responsibility | Cost | When it runs |
|---|---|---|---|
| `Deskew` | estimate + correct in-plane rotation | cheap | always (or as residual cleanup) |
| `Dewarp` | produce a dense backward-map flattening curl (+ usually perspective) | heavy | only when the page is curved |
| `CurvatureDetector` (shared) | flatness/curl score → gate | cheap | before dewarp; can also inform deskew |
| `PageDetector` (optional) | quad detection + crop for photos | medium | photos only, before dewarp |

Keep `PageDetector` and perspective correction conceptually separate from curl
dewarp, but note that several DL dewarp models do **page-crop + perspective +
curl jointly** — so for the photo regime a single DL `Dewarp` backend may cover
all three, while the classical/flatbed path wires them as distinct stages.

## Protocol shapes (sketch, not final)

Return **transforms**, not just pixels. A backward-map / angle that you apply
separately is composable (deskew ∘ dewarp), cacheable, and **invertible** — so
downstream you can map OCR boxes from the rectified page back to the original
(or vice-versa) even though OCR is a separate stage. This costs nothing now and
avoids a painful retrofit later.

```python
class DeskewResult(Protocol):
    angle_degrees: float
    confidence: float          # 0..1, comparable across backends where possible
    method: str
    def apply(self, image: Image) -> Image: ...

class Deskew(Protocol):
    def estimate(
        self,
        image: Image,
        *,
        mask: Image | None = None,        # binarized text mask, if caller has one
        text_lines: Sequence[Box] | None = None,  # OCR/line boxes, if available
    ) -> DeskewResult: ...

class DewarpResult(Protocol):
    map_x: NDArray            # backward map for cv2.remap (dst->src sampling)
    map_y: NDArray
    forward: Transform | None # optional, for remapping coords the other way
    confidence: float
    method: str
    def apply(self, image: Image) -> Image: ...

class Dewarp(Protocol):
    def estimate(
        self,
        image: Image,
        *,
        text_lines: Sequence[Box] | None = None,
        page_quad: Quad | None = None,    # from PageDetector, if photo
    ) -> DewarpResult: ...

class CurvatureDetector(Protocol):
    def score(
        self, image: Image, *, text_lines: Sequence[Box] | None = None
    ) -> CurvatureReport: ...   # flatness score + recommended action
```

`hints` like `text_lines`/`mask` are optional: a backend that can use them does,
one that can't ignores them. This is the clean seam for "leverages OCR" backends
without coupling the protocol to your OCR engine.

## Backend catalog — Deskew

| Backend | Signal | Flat | Photo | Uses OCR/text-lines | License | Maint. | Notes |
|---|---|---|---|---|---|---|---|
| **Leptonica** `pixDeskew` | projection-profile variance | ✅ | ◐ | no | BSD-2 | active | C; what Tesseract trusts internally. Strongest battle-tested option. |
| **sbrunner/deskew** | Hough (scikit-image) | ✅ | ◐ | no | MIT | **v1.6.0 Apr 2026** | pure-pip, trivial integrate; `num_peaks` tuning matters on noisy pages. |
| **jdeskew** | Fourier/Radon (ICIP'22) | ✅ | ◐ | no | Apache-2.0 | active | ±45°; good fallback on figure-heavy pages. |
| **OCR-baseline angle** | median slope of detected text baselines | ✅ | ✅ | **yes** | n/a (yours) | n/a | If line boxes already exist, near-free and very robust. Needs a detect pass *before* deskew, or deskew runs post-OCR. |
| **minAreaRect** (OpenCV) | bbox of text mask | ◐ | ◐ | no | BSD | n/a (DIY) | Simplest; fragile on book pages (gutters/marginalia skew the rect). |
| **Tesseract OSD** `--psm 0` | orientation | ✅ | ✅ | (it is OCR) | Apache-2.0 | active | **Coarse only** — 0/90/180/270, *not* fine angle. Use to fix upside-down/rotated-90, then a real deskewer for the residual. |

Avoid **Alyn** (abandoned 2017, Py2). Wire-in order: start with Leptonica +
sbrunner; add OCR-baseline as the high-accuracy backend once line boxes are
available in the pipeline.

## Backend catalog — Dewarp

| Backend | Model | Flat | Photo | Uses OCR/text-lines | License | Maint. | Notes |
|---|---|---|---|---|---|---|---|
| **lmmx/page-dewarp** | cubic-sheet (Zucker, packaged) | ✅ | ◐ | no (uses text *contours*, not OCR) | MIT | **v0.3.4 May 2026, PyPI** | Best classical wrap target; CLI + library. Single-column curled pages; struggles on tight spreads. |
| **Leptonica** `dewarp.c` | textline disparity field | ✅ | ◐ | **yes** (traces baselines) | BSD-2 | active | Strong on dense text; vertical curl robust, horizontal needs justified margins; may fail to build a model on sparse pages. |
| **UVDoc** | DL grid prediction (SIGGRAPH'23) | ◐ | ✅ | no | **MIT (incl. weights)** | active | ONNX + HuggingFace; CPU-feasible; grid-based → **degrades gracefully on flat input**. Lowest-risk DL pick. |
| **DocRes** | DL multitask (CVPR'24) | ◐ | ✅ | no | **MIT** | active | One model: dewarp + deshadow + deblur + binarize. GPU preferred. |
| **DocTr / DocGeoNet** | DL transformer (MM'21/ECCV'22) | ◐ | ✅ | no | repo license | active | Mature, widely forked; weights public. |
| **TPS from control points** | thin-plate spline remap | ✅ | ✅ | **yes** (you supply baseline points) | Apache-2.0 (OpenCV) | n/a (DIY) | Engine only — you detect baselines/grid, it warps. Flexible, all geometry logic is yours. |
| **OpenCV 4-point perspective** | homography | ◐ | ✅ (keystone) | no | BSD | n/a (DIY) | **Perspective only, no curl.** Either a `Dewarp` backend for keystone-only photos or the output stage of `PageDetector`. |

**DL caveat (applies to UVDoc/DocRes/DocTr/DocGeoNet):** trained on
Doc3D/DocUNet *synthetic phone-photo* distortion. Great for your photo inputs;
on a genuinely flat scan they can warp a clean page. Always run behind the
curvature gate; prefer grid/control-point models (UVDoc, DDCP) which degrade
most gracefully when input is already flat.

Skip: **ocrd_anybaseocr** pix2pixHD dewarp (removed in OCR-D v3, would need an
old pinned tag) and **ScanTailor** (best interactive quality but GUI-only, not
batchable).

## Curvature / flatness detector (the shared gate)

The component that decides *deskew-only* vs *dewarp*. Candidate signals, best
first:

1. **Text-baseline curvature** (best when line boxes are available): fit a
   straight line to each text-line's baseline, measure max deviation / residual;
   aggregate per-line residuals into a page curvature score. Near-free if OCR
   line boxes already exist; directly meaningful ("how bent is the text?").
2. **Page-border curvature**: detect top/bottom page edges, fit a low-order
   polynomial, measure the bend. Works without text; good for blank-margin
   detection on photos.
3. **DL displacement magnitude**: if you're already running a DL dewarp model,
   the predicted grid's deviation from identity *is* a curvature measure — but
   that defeats the "gate before the expensive step" purpose, so use only as a
   confirmation/telemetry signal.
4. **Cheap heuristic**: sharpness of the horizontal projection profile (crisp
   peaks ⇒ flat, smeared ⇒ curled). Fast pre-filter.

Output a `CurvatureReport`: `flatness_score`, `recommended_action ∈ {none,
deskew_only, dewarp}`, and the per-line residuals for debugging. This is what
prep-for-pgdp's deskew step computes and acts on.

## Recommended pipeline order

```
Photo:    PageDetect/crop → Dewarp(perspective + curl) → Deskew(residual)
Flatbed:  CurvatureDetect → [Dewarp only if curved] → Deskew
```

Two invariants:

- **Deskew runs last.** Whatever perspective/curl correction did, finish with a
  cheap residual-rotation cleanup. It's robust and idempotent on flat input.
- **Dewarp is gated.** Flat pages never enter a DL dewarp model.

## Suggested wiring phases

1. **`Deskew` protocol + Leptonica + sbrunner backends.** Immediate value, low
   risk, covers the flatbed common case end-to-end.
2. **`CurvatureDetector`** (text-baseline signal) wired into prep-for-pgdp's
   deskew step as the gate. Add **OCR-baseline** deskew backend here (reuses the
   same line boxes).
3. **`Dewarp` protocol + lmmx/page-dewarp (classical) + UVDoc (DL).** Gated by
   phase 2. Classical for no-ML environments; UVDoc (MIT, ONNX) for photos.
4. **`PageDetector`** (OpenCV quad + perspective) for the photo regime, feeding
   `Dewarp`. Optionally a `DocRes` backend if deshadow/deblur is also wanted.

## Open questions for CT

- Is `PageDetector`/perspective its own protocol, or folded into a photo-mode
  `Dewarp` backend (since DL models do it jointly)?
- Should backends return transforms only (compose + apply downstream) or also
  offer an `apply()` convenience? (Sketch above does both.)
- Do we want a hard no-ML deployment target? That decides whether classical
  backends are mandatory or just fallbacks.
- Confidence comparability: do we need cross-backend-comparable confidence (for
  auto-selecting a backend per page), or is per-backend confidence enough?

## Source research

See the four sub-agent research passes summarized in the originating session;
key repos: DanBloomberg/leptonica, sbrunner/deskew, phamquiluan/jdeskew,
lmmx/page-dewarp, tanguymagne/UVDoc (+ FahNos/UVDoc_onnx), ZZZHANG-jx/DocRes,
fh2019ustc/DocTr & DocGeoNet, fh2019ustc/Awesome-Document-Image-Rectification.
