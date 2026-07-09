# PaddleOCR doc-unwarping module (UVDoc)
- Category: dewarp (OCR-engine-feature) — the `TextImageUnwarping` / doc-unwarping module of PaddleOCR 3.x (PP-StructureV3 preprocessing).
- Paper + year: wraps **UVDoc** ("UVDoc: Neural Grid-based Document Unwarping", Verhoeven et al., SIGGRAPH Asia 2023). PaddleOCR 3.0 technical report: arXiv 2507.05595.
- Repo / homepage: https://github.com/PaddlePaddle/PaddleOCR ; weights https://huggingface.co/PaddlePaddle/UVDoc
- Pretrained weights public? Yes — `UVDoc` model on Hugging Face (PaddlePaddle org), auto-downloaded by PaddleOCR. WEIGHTS license: per the HF model card / PaddleOCR (Apache-2.0 project; confirm UVDoc upstream terms — original UVDoc is non-commercial research, so PaddlePaddle's redistribution terms should be checked before commercial shipping).
- Code license: Apache-2.0 (PaddleOCR).
- Framework / runtime: PaddlePaddle. CPU-feasible (lightweight UV model); GPU optional for speed.
- Maintenance: PaddleOCR is very actively maintained (3.x line, 2025+).

## What it does
Removes rotation/curl distortion from document images as the optional Document Image Preprocessing sub-pipeline of PP-StructureV3, ahead of layout/OCR.

## Model / approach
UVDoc predicts a **grid-based UV / dense coordinate map** of the document surface, converted to a backward map for remapping — dense, `cv2.remap`-style, invertible. Output field is `doctr_img` (the rectified image). UVDoc reports strong DocUNet/UVDoc-benchmark numbers (competitive MS-SSIM / LD) in its SIGGRAPH Asia 2023 paper.

## Input-regime fit
UVDoc trains on synthetic + a real captured set of phone-photo-style warped pages. Best on phone photos. On already-flat flatbed scans it predicts a near-identity grid but, like all learned dewarpers, can still introduce mild warp — gate behind the orientation/curl pre-check (PaddleOCR pairs it with a PP-LCNet orientation classifier).

## Even/odd (left vs right page) handling
Single page per image. No facing-page/gutter model; two-up spreads should be split upstream (PP-StructureV3 layout detection runs after, not before, unwarping).

## How it would back our Dewarp protocol
Good fit and easy to integrate: the **`TextImageUnwarping` model is callable as a standalone module** (instantiate directly, or enable `use_doc_unwarping=True` in the pipeline) **without running OCR**. It outputs a rectified image; the UV/grid is invertible in principle but PaddleOCR's API surfaces the rectified raster (`doctr_img`) — extracting the backward map needs going below the high-level API. Paddle Inference models export to ONNX via Paddle2ONNX. Dependency cost is the full PaddlePaddle runtime.

## Strengths / weaknesses for book scans
Strengths: Apache-2.0 code, actively maintained, standalone-callable, ONNX-exportable, lightweight/CPU-OK. Weaknesses: heavy PaddlePaddle dependency, phone-photo training distribution, no spread handling, UVDoc upstream weights have a research/non-commercial origin worth verifying for shipping.

## Sources
- https://paddlepaddle.github.io/PaddleOCR/main/en/version3.x/module_usage/text_image_unwarping.html
- https://huggingface.co/PaddlePaddle/UVDoc
- https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-StructureV3/PP-StructureV3.en.md
- https://arxiv.org/html/2507.05595v1
