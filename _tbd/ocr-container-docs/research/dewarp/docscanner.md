# DocScanner
- Category: dewarp (deep-learning)
- Paper + year: "DocScanner: Robust Document Image Rectification with Progressive Learning", IJCV 2025 (accepted Mar 2025; arXiv 2110.14968, 2021).
- Repo / homepage: https://github.com/fh2019ustc/DocScanner
- Pretrained weights public? Yes — DocScanner-T/-B/-L on Google Drive (`model_pretrained/`). WEIGHTS license: covered by the repo's custom non-commercial license (commercial use prohibited without written permission from the author).
- Code license: Custom proprietary academic license (Hao Feng); "Commercial Use of the Algorithm is strictly prohibited without explicit prior written permission." NOT MIT/Apache.
- Framework / runtime: PyTorch. GPU expected; DocScanner-L is small (8.5M params) so CPU inference is feasible but slow.
- Maintenance: ~55 commits, code released Apr 2024, IJCV accepted Mar 2025. Lightly maintained, single-author research repo.

## What it does
Rectifies geometrically distorted document photos (curled/folded pages shot by phone) into flat, readable images for downstream OCR.

## Model / approach
Two stages: a Document Localization Module (segments the page) then a Progressive Rectification Module with a recurrent unit that iteratively refines a predicted **backward mapping** (dense displacement field), converging on a clean rectification. The backward map is `cv2.remap`-able. DocUNet benchmark (DocScanner-L): MS-SSIM 0.5178, LD 7.45, ED 390.43, CER 0.1486 — among the stronger published numbers.

## Input-regime fit
Trained on Doc3D synthetic phone-photo distortion. Best on phone photos of curled/folded pages. On already-flat flatbed scans the localization + progressive refinement should converge near-identity, but like all synthetic-distortion models it can hallucinate mild warp; validate on a flat-scan sample before trusting it on a clean corpus.

## Even/odd (left vs right page) handling
Single-page-per-image assumption. A two-up spread would be localized and rectified as one page; the gutter/fold between facing pages is not modeled and would likely be mis-rectified. Split spreads before invoking.

## How it would back our Dewarp protocol
Produces a dense backward map (invertible, `cv2.remap`-compatible) — fits a flow-based Dewarp protocol cleanly. No official ONNX export; would need tracing. Weights are several model variants on Google Drive (no fixed mirror), and the non-commercial license is a blocker for any shipping product.

## Strengths / weaknesses for book scans
Strengths: strong accuracy, dense invertible map, compact -L model. Weaknesses: non-commercial license (disqualifying for distribution), phone-photo training distribution mismatched to flatbed book scans, no spread handling, no ONNX.

## Sources
- https://github.com/fh2019ustc/DocScanner
- https://github.com/fh2019ustc/DocScanner/blob/main/LICENSE.md
- https://link.springer.com/article/10.1007/s11263-025-02431-5
- https://arxiv.org/pdf/2110.14968
