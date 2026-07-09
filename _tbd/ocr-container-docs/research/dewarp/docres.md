# DocRes
- Category: dewarp (deep-learning)
- Paper + year: "DocRes: A Generalist Model Toward Unifying Document Image Restoration Tasks", CVPR 2024 (arXiv 2405.04408).
- Repo / homepage: https://github.com/ZZZHANG-jx/DocRes
- Pretrained weights public? Yes — `docres.pkl` (and `mbd.pkl` for the masking/border-detection helper) on OneDrive, dropped into `./checkpoints/`. WEIGHTS license: no explicit separate weights license; repo is MIT, no stated non-commercial restriction.
- Code license: MIT.
- Framework / runtime: PyTorch (Python 100%). GPU recommended; single generalist model so CPU inference is possible but slow.
- Maintenance: news entries through 2025; actively maintained by the author (ZZZHANG-jx, who also authored Marior).

## What it does
A single generalist model that performs five document restoration tasks — dewarping, deshadowing, appearance enhancement, deblurring, binarization — selected at inference via a Dynamic Task-Specific Prompt (DTSPrompt).

## Model / approach
Image-to-image restoration conditioned on a visual prompt. For the dewarp task the prompt carries geometric priors and the network predicts a **backward mapping (bm)** used to remap the input — i.e. a dense flow field, `cv2.remap`-able and invertible, not just a rectified raster. Dewarp is evaluated on DocUNet; DocRes is competitive with task-specific dewarpers while also covering the other four tasks.

## Input-regime fit
Dewarp head trained on synthetic phone-photo distortion (Doc3D-style). Strong on phone photos. On flat flatbed scans the dewarp task can introduce small spurious warp; prefer running only the enhancement/deshadow/binarization tasks on already-flat input, or gate the dewarp task behind a curl-detection check.

## Even/odd (left vs right page) handling
Single page per image. No facing-page/gutter model; a two-up spread should be split first or the rectification will treat the whole spread as one warped surface.

## How it would back our Dewarp protocol
Strong fit: MIT-licensed, dense invertible backward map output, one weight file (`docres.pkl`), permissive enough to ship. No official ONNX export (PyTorch only) — tracing would be required. The multitask design is a bonus: one model could also back deshadow/enhance protocols.

## Strengths / weaknesses for book scans
Strengths: permissive MIT license, invertible backward map, maintained, multitask reuse. Weaknesses: phone-photo dewarp training distribution, no spread handling, no ONNX, single large model is heavier than a dedicated lightweight dewarper.

## Sources
- https://github.com/ZZZHANG-jx/DocRes
- https://arxiv.org/html/2405.04408v1
- https://openaccess.thecvf.com/content/CVPR2024/papers/Zhang_DocRes_A_Generalist_Model_Toward_Unifying_Document_Image_Restoration_Tasks_CVPR_2024_paper.pdf
