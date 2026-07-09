# ScanTailor Universal
- Category: dewarp (GUI-pipeline)
- Repo / homepage: https://github.com/trufanov-nok/scantailor-universal (GitLab mirror: https://gitlab.com/truf/scantailor-universal)
- License (code; and model weights if any): GNU GPL-3.0. No model weights.
- Language / runtime: C++ with Qt5/Qt6. Native desktop binaries (Linux, Windows, macOS, FreeBSD, NetBSD).
- Install: download installer / distro package (Ubuntu PPA available), or build from source (Qt + CMake).
- Interface: GUI (interactive post-processing of scanned pages). Bundles command-line helpers for batch/automation, but the workflow is GUI-centric.
- Maintenance: Actively maintained by Alexander Trufanov; ~1,558 commits, 14+ tags, multi-platform CI (Qt5/Qt6). Maintained: yes. (Versioning in the 0.2.x line, e.g. 0.2.x JPEG2000 support.)

## What it does
A "Universal" fork merging the Enhanced + Featured + Master ScanTailor branches into one cross-platform tool. Same scanned-book pipeline: page split, deskew, content/margin selection, dewarping, and bilevel/grayscale output, with broader format support and modern Qt.

## Geometric model / algorithm
Same **distortion-mesh / spline dewarp** as the ScanTailor lineage: a grid bounded by fitted top and bottom page curves is warped so the curves become straight horizontal lines, flattening line bow. Control points can be auto-placed on the curved borders or hand-adjusted. Corrects curl-style bow and deskew; it is a 2D mesh warp, not a calibrated 3D perspective recovery.

## Input-regime fit
Aimed at **flatbed/overhead book scans** with moderate spine curl. Good on low-to-moderate curvature; weaker on heavy curl and on strong perspective/oblique phone photos (no full projective model). Flatbed scans without curl simply skip the dewarp stage.

## Leverages OCR or text-line detection?
No OCR; no automatic textline tracing. Dewarp keys off page-border curvature, with manual mesh refinement for hard pages.

## Even/odd (left vs right page) handling
Two-up spreads are handled by the **Split Pages** stage upstream; left and right halves become separate pages, each dewarped independently. Per-page handling comes from pre-split, not a unified spread model.

## How it would back our Dewarp protocol
Desktop GUI application, not an embeddable library — weak fit for an in-process Dewarp protocol. It produces rectified output images; the internal warp mesh is not exposed as a programmatic dense map_x/map_y, and there is no invertible map handed back. Integration would be out-of-process (drive the CLI/project, read images). Best treated as a manual/reference tool, not a map backend.

## Strengths / weaknesses for book scans
Strengths: actively maintained, broadest platform/format support of the ScanTailor forks, complete scan-cleanup pipeline, manual control. Weaknesses: GUI/operator-driven, not a scriptable map provider; mesh dewarp limited on heavy curl/perspective; GPL; no text-line-aware dewarp.

## Sources
- https://github.com/trufanov-nok/scantailor-universal
- https://github.com/trufanov-nok/scantailor-universal/releases
- https://github.com/scantailor/scantailor/wiki/B.-Output-Tabs:-Dewarping
