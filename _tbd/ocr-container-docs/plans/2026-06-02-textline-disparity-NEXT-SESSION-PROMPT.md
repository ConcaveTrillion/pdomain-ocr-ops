# Next-session prompt — plan the textline-disparity dewarp

Paste the block below into a fresh Claude Code session in `/workspaces/ocr-container`.

---

Write the implementation plan for the **textline-disparity dewarp** backend, using
the `superpowers:writing-plans` skill. The design is already approved and committed —
do NOT re-brainstorm; go straight to writing the plan.

**Read first (in order):**
- Spec: `docs/specs/2026-06-02-textline-disparity-dewarp-design.md` (the thing to plan)
- Parent spec: `docs/specs/2026-06-02-geometry-correction-design.md` (esp. decision D9,
  the `Dewarp` protocol, `GeometryTransform`, the curvature/regime gate)
- v1 plan it depends on: `docs/plans/2026-06-02-geometry-correction-book-tools.md`
- Backgrounders if useful: `docs/research/dewarp/leptonica-dewarp.md`, `uvdoc.md`

**Target repo:** `pdomain-book-tools`. Plan tasks land there. Per workspace rules:
delegate implementation to the `pdomain-book-tools` agent in a **worktree**
(`isolation: "worktree"`); TDD (failing test first); local commits only — **no push,
no GitHub PRs**. Save the plan to `docs/plans/2026-06-02-textline-disparity-dewarp.md`
with frontmatter `repo: pdomain-book-tools`.

**Hard dependency — sequence this:** the backend needs the v1 `geometry_correction`
package (protocols, registry, `GeometryPipeline`, `GeometryTransform`), which is
planned in the v1 plan above but **not yet implemented**. Decide explicitly in the
plan: either (a) gate this plan behind v1 execution, or (b) have Task 1 stand up the
minimal v1 surface it imports. State the choice in the plan header.

**Locked design decisions (do not re-litigate — from spec §2):**
- Full-fidelity Leptonica model: vertical + horizontal disparity + even/odd line-end
  referencing, built together. NOT Hough (Hough is straight-line/deskew only).
- Method: morph-consolidation → per-column vertical centroid → **order-2** quadratic
  LSF baselines; vertical disparity from centerline fits; horizontal disparity from
  line-END positions, **min for even/verso(left), max for odd/recto(right)** pages
  (parity from `gutter_edge`).
- **Strict parallel modules**: full NumPy impl in
  `image_processing/cv2_processing/textline_dewarp.py`, full CuPy mirror in
  `image_processing/cupy_processing/textline_dewarp.py`, identical APIs (like the
  existing `rotate.py`/`deskew.py` pairs). Backend wrapper in
  `geometry_correction/backends/dewarp/textline.py` picks the module via
  `_cupy_compat` / a `prefer_gpu` flag.
- `TextlineDetector` seam + **one** default detector (morph-centroid). Strip-projection
  and ML (kraken/DocTR) detectors are future drop-ins — do not build them.
- This plan also lands the **CuPy `apply` branch on `GeometryTransform`** (NumPy →
  `cv2.remap`, CuPy → `cupyx.scipy.ndimage.map_coordinates`).
- Regime detector (`geometry_correction/regime.py`) classifies flat / flat_curl /
  oblique and the pipeline routes flat_curl→textline_disparity, oblique→UVDoc, with
  caller override.
- Fallback: < `min_textlines` ⇒ return `GeometryTransform.identity` + `confidence=0`.

**Reuse existing code (both cv2 + cupy variants exist):** `threshold.py` (Otsu),
`morph.py` (close/open/dilate/erode), `contours.py` (connected components + size
filter). No textline detection, no `cv2.remap`/`map_coordinates` helper, and no
adaptive threshold exist yet — those are new.

**Testing conventions:** mirror `tests/image_processing/{cv2,cupy}_processing/`.
GPU/parity tests must be gated with the existing `conftest.py` fixtures
(`skipif_no_cupy`, `@pytest.mark.gpu`, `gpu_array_factory`) so CI on GPU-less runners
stays green — heavy GPU tests run locally only ("no heavy tests on GitHub"). Include:
synthetic-warp round-trip, even/odd line-end referencing, sparse-page fallback,
detector-seam contract, NumPy↔CuPy parity, regime classification.

**Do FIRST, before finalizing detector defaults (spec §8):** dispatch a quick agent
to copy the morphological SEL sequence + `csize1`/`csize2` formulas **verbatim** from
`src/dewarp2.c` in `DanBloomberg/leptonica` (the prior research read them via a
summarized fetch, not a raw paste). Bake the confirmed values into the plan.

Use spec §7's phases A–F as the starting decomposition. Bite-sized TDD steps, exact
file paths, real code in every step, exact `uv run pytest` commands with expected
output.
