# RDGR (Revisiting Document Image Dewarping by Grid Regularization)
- Category: dewarp (deep-learning)
- Paper + year: "Revisiting Document Image Dewarping by Grid Regularization" — **CVPR 2022** (arXiv 2203.16850). NOTE: the request labeled this "ECCV'22"; the verified venue is CVPR 2022.
- Repo / homepage: https://github.com/XiangWeiJiang/Document_Geometry_Dewarping
- Pretrained weights public? Yes — `docunet.pth` and `unet.pth` on OneDrive, placed in `pkl/`. WEIGHTS license: governed by repo license; no explicit separate restriction noted.
- Code license: confirm `LICENSE` in tree (not clearly stated in repo metadata; treat as unconfirmed before shipping).
- Framework / runtime: PyTorch. GPU recommended; two-network pipeline, CPU feasible but slow.
- Maintenance: 2022 research repo, low ongoing activity.

## What it does
Dewarps distorted document images, emphasizing geometric validity of the predicted warp by **regularizing the rectification grid** so the output mapping stays well-formed (no folds/overlaps).

## Model / approach
A UNet-style segmentation/crop stage plus a dewarp network that predicts a **dense rectification grid / flow** which is then **grid-regularized** to enforce a smooth, monotonic, fold-free mapping. The regularized grid yields a backward map that is `cv2.remap`-able and invertible. Run via `predict.py --method grid --docunet pkl/docunet.pth --unet pkl/unet.pth`. Evaluated on the DocUNet benchmark with competitive MS-SSIM / LD at publication; the grid-regularization contribution targets mapping quality over raw metric gains.

## Input-regime fit
Trained on synthetic phone-photo distortion. The grid-regularization helps the output mapping stay smooth, which somewhat reduces wild artifacts on near-flat input, but the model still predicts a non-trivial warp and can over-correct a flat scan. Validate on a flat-scan sample; gate behind curl detection for a mostly-flat corpus.

## Even/odd (left vs right page) handling
Single page per image. No facing-page/gutter model; two-up spreads must be split before dewarping.

## How it would back our Dewarp protocol
Dense, grid-regularized backward map (invertible, `cv2.remap`-compatible) fits a flow protocol. Two weight files (UNet crop + dewarp net) and a multi-step `predict.py` pipeline. No ONNX. License status unconfirmed — must verify before shipping.

## Strengths / weaknesses for book scans
Strengths: grid regularization gives geometrically valid, fold-free maps; invertible dense output. Weaknesses: unconfirmed license, phone-photo training distribution, two-stage complexity, low maintenance, no ONNX, no spread handling.

## Sources
- https://github.com/XiangWeiJiang/Document_Geometry_Dewarping
- https://arxiv.org/abs/2203.16850
- https://openaccess.thecvf.com/content/CVPR2022/html/Jiang_Revisiting_Document_Image_Dewarping_by_Grid_Regularization_CVPR_2022_paper.html
