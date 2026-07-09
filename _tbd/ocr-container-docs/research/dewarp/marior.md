# Marior
- Category: dewarp (deep-learning)
- Paper + year: "Marior: Margin Removal and Iterative Content Rectification for Document Dewarping in the Wild", ACM MM 2022 (arXiv 2207.11515).
- Repo / homepage: https://github.com/ZZZHANG-jx/Marior
- Pretrained weights public? Yes — checkpoints published in the repo's release/README links (Google Drive / BaiduYun). WEIGHTS license: governed by repo license; no explicit separate non-commercial clause noted.
- Code license: repo by ZZZHANG-jx (same author as DocRes); check `LICENSE` in tree — DocRes is MIT, Marior follows the same author's permissive pattern but confirm before shipping.
- Framework / runtime: PyTorch. GPU recommended; CPU feasible but slow.
- Maintenance: 2022-era research repo, low ongoing activity (author's attention has moved to DocRes).

## What it does
Dewarps documents photographed "in the wild," explicitly handling images where the page does not fill the frame (margins/background present).

## Model / approach
Two modules: a **Margin Removal Module (MRM)** predicts a segmentation mask to crop away background/margin, then an **Iterative Content Rectification Module (ICRM)** predicts **dense displacement flows** (backward-map style) and refines them iteratively on the cropped content. Output is a dense flow → `cv2.remap`-able and invertible. Reported SOTA on DocUNet at publication (strong MS-SSIM / LD).

## Input-regime fit
Trained on synthetic phone-photo distortion. Best on phone photos with surrounding background. The iterative refinement can over-correct nearly-flat input; the MRM crop step is also risky on flatbed scans where the page already fills the frame (it may crop legitimate page edge content). Validate on flat input before use.

## Even/odd (left vs right page) handling
Single page per image. The MRM is specifically relevant here: it removes margin/background, so on a two-up spread it would attempt to segment "the page" as one region and likely mis-handle the gutter — split spreads first. MRM is useful for our pipeline as a standalone page-crop primitive, separate from dewarp.

## How it would back our Dewarp protocol
Dense backward map (invertible, `cv2.remap`-compatible) fits a flow protocol. No official ONNX. Two-stage (mask net + rectification net) means two weight files and more orchestration than a single-pass model. MRM crop could be wired as an optional pre-crop stage.

## Strengths / weaknesses for book scans
Strengths: explicit margin handling, invertible dense flow, iterative refinement. Weaknesses: phone-photo training distribution, MRM crop hazard on full-frame scans, two-stage complexity, low maintenance, no ONNX.

## Sources
- https://github.com/ZZZHANG-jx/Marior
- https://arxiv.org/abs/2207.11515
- https://dl.acm.org/doi/10.1145/3503161.3548214
