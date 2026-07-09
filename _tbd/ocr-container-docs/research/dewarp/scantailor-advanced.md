# ScanTailor Advanced
- Category: dewarp (GUI-pipeline)
- Repo / homepage: https://github.com/4lex4/scantailor-advanced (original); actively maintained fork: https://github.com/ScanTailor-Advanced/scantailor-advanced (also https://scantailor.net/)
- License (code; and model weights if any): GNU GPL-3.0. No model weights.
- Language / runtime: C++ with Qt. Native desktop binaries (Windows, macOS, Linux).
- Install: download platform binary, or build from source (Qt + CMake).
- Interface: GUI (interactive page-by-page post-processing). A `scantailor-cli` exists for batch reprocessing of saved projects, but tuning is GUI-driven.
- Maintenance: Original 4lex4 repo last released v1.0.16 and is dormant. A community fork under the ScanTailor-Advanced org is active — v1.1.1 (2026-04-03) added oblique deskew and more binarization thresholds. Maintained: yes (via fork).

## What it does
Full scanned-book post-processing pipeline: page split, deskew, content/margin selection, dewarping, and binarized output. Dewarping is one stage among many in an interactive operator workflow.

## Geometric model / algorithm
Dewarping uses a **distortion mesh / spline** model inherited from the original ScanTailor: a curved grid (a top and bottom curve, the "blue mesh" with adjustable red control points) is fit along the page's curved top/bottom borders, and the image is warped so those curves map to straight horizontal lines. Marginal/auto dewarp places control points automatically on low-curvature scans; the operator can hand-edit the mesh. It corrects curl-style line bow plus deskew, not full 3D camera perspective.

## Input-regime fit
Built for **flatbed and overhead book scans** with moderate spine curl. Works well on low-to-moderate curvature; struggles with heavy curl or strong oblique perspective (it is a mesh-warp, not a calibrated 3D projection). Phone photos with strong keystone are out of its sweet spot.

## Leverages OCR or text-line detection?
No OCR and no automatic textline tracing. Auto-dewarp keys off page border curves; precise results often need manual mesh adjustment. Text awareness is absent.

## Even/odd (left vs right page) handling
Handles two-up spreads via its **Split Pages** stage upstream of dewarping, producing independent left/right pages that are each dewarped separately. So per-page handling is achieved by pre-split, not by a single spread model.

## How it would back our Dewarp protocol
A GUI desktop app, not a library — poor fit for an in-process Dewarp protocol. It emits rectified output images, not a dense map_x/map_y you can consume programmatically (its internal mesh is not exposed via a Python API). Integration would mean shelling out to the CLI on a saved project and reading back images; no invertible map. Useful as a reference for the mesh model, not as a backend.

## Strengths / weaknesses for book scans
Strengths: mature, free, proven on real book corpora; strong overall pipeline (split/deskew/binarize); manual control for tricky pages. Weaknesses: GUI/operator-driven, not scriptable as a map provider; mesh dewarp limited on heavy curl/perspective; original repo dormant (use the fork); GPL.

## Sources
- https://github.com/4lex4/scantailor-advanced
- https://github.com/ScanTailor-Advanced/scantailor-advanced/releases
- https://github.com/scantailor/scantailor/wiki/B.-Output-Tabs:-Dewarping
