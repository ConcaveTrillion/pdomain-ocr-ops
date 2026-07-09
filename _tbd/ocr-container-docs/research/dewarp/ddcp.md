# DDCP (Document Dewarping with Control Points)
- Category: dewarp (deep-learning)
- Paper + year: "Document Dewarping with Control Points" — **ICDAR 2021** (Springer LNCS; arXiv 2203.10543). NOTE: the request labeled this "ICPR'22"; the verified venue is ICDAR 2021.
- Repo / homepage: https://github.com/gwxie/Document-Dewarping-with-Control-Points
- Pretrained weights public? **No** — the repo ships code + a control-point training dataset but does **not** publish pretrained weights; you must train. WEIGHTS license: n/a (none distributed).
- Code license: MIT.
- Framework / runtime: PyTorch (also opencv-python, scipy). GPU for training; the control-point model is lightweight, CPU inference feasible.
- Maintenance: ~48 commits, ~25 open issues, modest community engagement; effectively low ongoing maintenance.

## What it does
Predicts a sparse set of **control points** (and matching reference points) describing the document's deformed shape, then dewarps by interpolating those points into a backward map and remapping.

## Model / approach
Predicts a **sparse control-point grid** rather than a dense per-pixel flow. The sparse mapping is interpolated into a dense backward map (`cv2.remap`-able, invertible). The user can also adjust the number of control points to trade accuracy vs. interactivity. No standout DocUNet leaderboard scores; the contribution is the lighter, interaction-friendly control-point representation rather than top metrics.

## Input-regime fit
Trained on synthetic distortion, but the **control-point representation is inherently gentler on flat input** than dense-flow models: with few control points and small predicted offsets, a near-flat page maps to a near-identity grid, so the risk of introducing spurious warp into an already-flat scan is lower. This makes DDCP the safest of the surveyed dense/grid methods for a corpus that is mostly flat.

## Even/odd (left vs right page) handling
Single page per image. The control-point grid spans one page surface; a two-up spread would be fit as a single warped sheet with no gutter awareness — split spreads first.

## How it would back our Dewarp protocol
Control-point grid → interpolated dense backward map (invertible, `cv2.remap`-compatible), so it satisfies a flow protocol after interpolation. No ONNX. **Biggest gap: no pretrained weights** — adoption requires training on the provided dataset (or our own), which is real upfront cost.

## Strengths / weaknesses for book scans
Strengths: MIT, lightweight, control-point representation degrades gracefully on flat input, adjustable density. Weaknesses: no pretrained weights (must train), no ONNX, low maintenance, no spread handling.

## Sources
- https://github.com/gwxie/Document-Dewarping-with-Control-Points
- https://link.springer.com/chapter/10.1007/978-3-030-86549-8_30
- https://arxiv.org/abs/2203.10543
