# ocrd_anybaseocr dewarp
- Category: dewarp (OCR-engine-feature) — a processor in the OCR-D toolchain.
- Paper + year: no dedicated paper; the dewarp processor wrapped a pix2pixHD GAN (Wang et al., "High-Resolution Image Synthesis... with Conditional GANs", CVPR 2018) trained by DFKI on document images.
- Repo / homepage: https://github.com/OCR-D/ocrd_anybaseocr
- Pretrained weights public? Historically yes — the pix2pixHD dewarp model was hosted on **DFKI cloud storage**, fetched by the v1.x setup. **These are no longer wired up in current releases.** WEIGHTS license: DFKI-distributed, unspecified.
- Code license: Apache-2.0 (OCR-D project standard).
- Framework / runtime: PyTorch pix2pixHD; **GPU effectively required** (high-resolution conditional GAN).
- Maintenance: repo actively maintained by OCR-D, **but the dewarp processor was REMOVED**.

## What it does (historically)
`ocrd-anybaseocr-dewarp` took a page image and emitted a dewarped raster via an image-to-image GAN, as one stage in a binarize → deskew → crop → dewarp → layout OCR-D workflow.

## IMPORTANT: removed in the OCR-D v3 migration
During the OCR-D **v3 API migration, the pix2pixHD dewarp processor was removed** (the `ocrd_anybaseocr.pix2pixhd` module no longer ships — see repo issue #64). The **current package (v2.0.0 line) ships only the `cropper` and `layout-analysis` processors**; there is no dewarp and no deskew/binarize either. To use the GAN dewarp at all you must **pin an old v1.x tag** of `ocrd_anybaseocr` (and source the DFKI weights), with all the dependency/Python-version friction that implies.

## Model / approach
pix2pixHD **GAN image-to-image translation**: outputs a **rectified raster only** — there is NO dense backward map, so the transform is **not invertible** and you cannot map OCR coordinates back to the original. No DocUNet benchmark numbers published for this processor.

## Input-regime fit
GAN trained on DFKI document scans. As an image-to-image GAN it can **hallucinate** texture/warp and degrades unpredictably on out-of-distribution or already-flat input — the highest-risk option here for a flat corpus.

## Even/odd (left vs right page) handling
Operates per page image within an OCR-D workflow; no facing-page model. Spreads handled upstream by the cropper/segmentation, not the dewarper.

## How it would back our Dewarp protocol
Poor fit: **rectified image only, no invertible backward map**, GPU-heavy GAN, weights off a DFKI cloud, and the processor is removed from current releases (requires pinning a stale v1.x). Not recommended.

## Strengths / weaknesses for book scans
Strengths: was a drop-in OCR-D stage. Weaknesses: removed from current OCR-D; non-invertible raster output; GAN hallucination risk; GPU required; weights only via DFKI cloud + old tag.

## Sources
- https://github.com/OCR-D/ocrd_anybaseocr
- https://github.com/OCR-D/ocrd_anybaseocr/issues/64
- https://github.com/OCR-D/ocrd_all/blob/master/CHANGELOG.md
- https://pypi.org/project/ocrd-anybaseocr/
