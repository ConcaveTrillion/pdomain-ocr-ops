# UVDoc
- Category: dewarp (deep-learning)
- Paper + year: "UVDoc: Neural Grid-based Document Unwarping", Verhoeven, Magne, Sorkine-Hornung (ETH Zürich) — SIGGRAPH Asia 2023 (arXiv 2302.02887)
- Repo / homepage: https://github.com/tanguymagne/UVDoc (dataset: https://github.com/tanguymagne/UVDoc-Dataset)
- Pretrained weights public? Yes — `model/best_model.pkl` shipped in-repo for the demo. WEIGHTS license: covered by repo **MIT** license (no separate restriction).
- Code license: **MIT** — the only commercial-friendly model in this set.
- Framework / runtime: PyTorch (repo's C++ is the dataset-capture tooling, not inference). Small fully-convolutional net — CPU inference is practical; GPU optional.
- Maintenance: small repo (few commits), low issue traffic, but authors posted an erratum correcting benchmark numbers — they monitor it. Lightly maintained, not actively developed.

## What it does
Single-image geometric unwarping via a compact fully-convolutional net, trained on the new **UVDoc** dataset (pseudo-photorealistic renders with accurate 3D shape + unwarping-function ground truth) plus Doc3D.

## Model / approach
Dual-task FCN: predicts a **3D grid mesh** of the document surface AND the corresponding **2D unwarping grid** jointly. The 2D grid is a sparse control-grid that is interpolated to a dense sampling map and applied via `grid_sample`. Despite its small size it reaches state-of-the-art DocUNet numbers (post-erratum) — competitive with/ahead of DocGeoNet while far lighter weight.

## Input-regime fit
Trained on synthetic/pseudo-photorealistic phone-photo distortion (UVDoc + Doc3D). Single-page warped-photo assumption. As with the others, it predicts a non-trivial grid for any input, so an already-flat scan can be mildly re-warped; no identity passthrough. Guard before applying to clean scans — though its grid is smooth/low-frequency, so spurious warp tends to be gentler than transformer-flow models.

## Even/odd (left vs right page) handling
Single-page. The 3D-mesh + 2D-grid are fit to one surface; a two-page spread violates the single-surface assumption and the grid bends across the gutter. No page-splitting. Pre-split at the gutter, feed each page separately.

## How it would back our Dewarp protocol
Best operational fit. It natively predicts a **2D unwarping grid** → trivially expanded (interpolate) into a dense `cv2.remap` map, and invertible. Small FCN with no exotic ops, so ONNX export is straightforward (no official ONNX shipped, but trace-friendly). Tiny weight file (`best_model.pkl`, single-digit to low-tens MB). Light PyTorch + numpy/opencv deps.

## Strengths / weaknesses for book scans
Strengths: **MIT (commercial-safe)**, weights in-repo, smallest/fastest, grid output maps cleanly to `cv2.remap`, SOTA-ish accuracy, easiest to ONNX-export and self-host. Weaknesses: single-page only (needs gutter pre-split), no flat-input safety, lightly maintained, control-grid is lower-resolution than dense-flow models (may miss sharp local folds).

## Sources
- https://github.com/tanguymagne/UVDoc
- https://arxiv.org/abs/2302.02887
- https://dl.acm.org/doi/10.1145/3610548.3618174
- https://www.research-collection.ethz.ch/handle/20.500.11850/652324
