# DocUNet benchmark + dataset
- Category: dewarp (benchmark/dataset)
- Paper + year: "DocUNet: Document Image Unwarping via a Stacked U-Net", Ma, Shu, Bai, Wang, Samaras — CVPR 2018
- Repo / homepage: https://www3.cs.stonybrook.edu/~cvl/docunet.html
- Pretrained weights public? n/a — this is the *benchmark*, not a released model. The CVPR'18 stacked-U-Net weights were never released as a usable checkpoint; the lasting artifact is the 130-image evaluation benchmark.
- Code license: not distributed as code; the benchmark images are research-use.
- Framework / runtime: n/a (it is a dataset + MATLAB eval scripts). Eval (MS-SSIM/LD) runs on CPU.
- Maintenance: static reference artifact; no active maintenance, but it is the de-facto standard every later paper reports against.

## What it does
DocUNet contributed (1) a large synthetic training set (~100k images built by warping flat docs with a synthetic 2D deformation field) and (2) a 130-image real-photo benchmark used to compare unwarping methods. The benchmark is the part that matters today: DewarpNet, DocTr, DocGeoNet, DocTr++, UVDoc and DocScanner all report on it.

## Metrics — what they mean
- **MS-SSIM** (multi-scale structural similarity): image-similarity between rectified output and scanned ground truth. Higher is better. Sensitive to global alignment/illumination, weak at local geometric fidelity.
- **LD** (Local Distortion): mean local deformation between dense SIFT-flow correspondences of output vs. GT. Lower is better. Measures residual local warp.
- **AD / ED / CER** (Aligned Distortion, edit distance, char error rate) are reported by newer papers as OCR-oriented complements.
Caveat: recent work (UVDoc erratum; ScienceDirect 2025) shows MS-SSIM and LD do not always track real dewarping quality — treat single-number leaderboard gaps with skepticism.

## Input-regime fit
Benchmark photos are handheld phone captures of single-page documents with folds/curls — *not* flatbed scans and *not* two-up book spreads. A method tuned to top DocUNet scores is optimized for phone-photo distortion. This is the central risk for our use case: such models assume warp is present and may "correct" already-flat scans into new distortion.

## Even/odd (left vs right page) handling
Benchmark is strictly single-page. There is no two-page-spread case, so nothing here validates left/right-page behavior. Any model that tops DocUNet is unvalidated on book spreads.

## How it would back our Dewarp protocol
Not a model — provides no backward-map. Its role for us is as a *yardstick*: when we pick a model, its published DocUNet MS-SSIM/LD/AD numbers let us rank candidates, and we can reuse the MATLAB eval harness to score our own pipeline on the same 130 images.

## Strengths / weaknesses for book scans
Strength: universal, lets us compare all candidate models on one axis. Weakness: phone-photo single-page domain only; metrics are contested; says nothing about flat-input safety or two-up spreads — exactly the regimes we care about.

## Sources
- https://openaccess.thecvf.com/content_cvpr_2018/papers/Ma_DocUNet_Document_Image_CVPR_2018_paper.pdf
- https://www3.cs.stonybrook.edu/~cvl/docunet.html
- https://ieeexplore.ieee.org/document/8578592/
- https://arxiv.org/html/2302.02887v2 (UVDoc — benchmark caveats/erratum)
- https://www.sciencedirect.com/science/article/abs/pii/S0167865525001801 (metric-accuracy critique, 2025)
