# DocTr++ (DocTr-Plus)
- Category: dewarp (deep-learning)
- Paper + year: "Deep Unrestricted Document Image Rectification", Feng et al. — IEEE TMM 2023 (arXiv 2304.08796)
- Repo / homepage: https://github.com/fh2019ustc/DocTr-Plus
- Pretrained weights public? Yes — checkpoint on Google Drive/Baidu (put in `model_pretrained/`). WEIGHTS license: same non-commercial terms; commercial use → contact Hao Feng (haof@mail.ustc.edu.cn).
- Code license: custom **non-commercial** license (same family as DocTr). Academic/personal free; commercial prohibited without permission.
- Framework / runtime: PyTorch. GPU recommended; CPU inference feasible.
- Maintenance: part of the actively maintained fh2019ustc rectification family; stable.

## What it does
Generalizes DocTr to **unrestricted** inputs: documents that are incomplete, partially out of frame, arbitrarily cropped, or only partially captured — cases the original DocTr's full-page assumption broke on. Geometry-only (no separate illumination stage emphasized).

## Model / approach
Hierarchical transformer encoder-decoder that predicts a dense **backward unwarping flow** even when document boundaries are absent/partial, applied via `grid_sample`. Introduces a new dataset of unrestricted distortions for training/eval. Reports on DocUNet plus its own unrestricted test set; on standard DocUNet it is competitive with DocTr/DocGeoNet (MS-SSIM ~0.51 range) while being far more robust to partial/cropped inputs.

## Input-regime fit
Still trained on synthetic phone-photo-style distortion, but explicitly for *partial/cropped* documents — the most relevant trait for book pages where the captured region may not show full page edges. Like the rest of the family it has no identity prior for already-flat scans; running it on clean flatbed input risks introducing warp. Guard recommended.

## Even/odd (left vs right page) handling
Still fundamentally single-document. However its "unrestricted/partial" design is the closest in this set to tolerating a cropped single page from a spread — if we crop each page (left/right) and feed separately, DocTr++ handles the missing-boundary case better than DocTr. It does NOT itself split a two-up spread; we must pre-split at the gutter.

## How it would back our Dewarp protocol
Best-of-family for our split-then-dewarp workflow: native dense backward flow (interceptable for `cv2.remap` + inversion) and robustness to the partial single-page crops a book pipeline produces. No official ONNX; traceable. Weight size modest (tens of MB). PyTorch deps.

## Strengths / weaknesses for book scans
Strengths: robust to partial/cropped pages (matches post-gutter-split crops), dense backward-map, active family. Weaknesses: non-commercial license blocker for commercial shipping, no two-up handling (needs pre-split), no flat-input safety.

## Sources
- https://github.com/fh2019ustc/DocTr-Plus
- https://arxiv.org/abs/2304.08796
- https://dl.acm.org/doi/abs/10.1109/TMM.2023.3347094
- https://arxiv.org/html/2304.08796v2
