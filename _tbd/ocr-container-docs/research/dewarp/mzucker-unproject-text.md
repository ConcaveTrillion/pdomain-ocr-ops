# mzucker/unproject_text
- Category: dewarp (perspective-only)
- Repo / homepage: https://github.com/mzucker/unproject_text (writeup: https://mzucker.github.io/2016/10/11/unprojecting-text-with-ellipses.html)
- License (code; and model weights if any): Open-source (LICENSE.txt in repo; MIT-style, consistent with mzucker's other repos). No model weights.
- Language / runtime: Python 2/3. Depends on numpy, scipy, OpenCV >= 3.0, matplotlib.
- Install: clone the repo; no PyPI package. Run the script on an image.
- Interface: CLI (script).
- Maintenance: 2016 project, ~18 commits, no releases, not actively maintained. Effectively frozen.

## What it does
Recovers the perspective (projective) transform of a flat page of text photographed at an angle, then unprojects it to a fronto-parallel view. A proof-of-concept built to feed an OCR/translation app.

## Geometric model / algorithm
Replaces letters with fitted **ellipses** (each character blob approximated by an ellipse). Under the assumption that letters are, on average, the same size and circular-ish in their canonical frame, the distribution of ellipse axes/orientations across the page encodes the projective distortion. It solves for the homography (affine/perspective) that maps the observed ellipses back to a consistent canonical scale, then warps the image with that transform.

## Input-regime fit
Strictly **flat pages** seen under perspective — corrects perspective only, NOT curl. A flatbed scan has no perspective so it gains nothing; a phone photo of a flat sheet at an angle is the ideal case. A curled book page violates the planar assumption and will not be flattened correctly.

## Leverages OCR or text-line detection?
No OCR. It detects character-like blobs and fits ellipses to them as geometric cues; no recognition.

## Even/odd (left vs right page) handling
No left/right page concept and no curl model. It assumes a single flat plane; a two-up spread of a curved book is out of scope and must be split and would still only get perspective (not curl) correction.

## How it would back our Dewarp protocol
Yields a single 3x3 homography, not a dense map. To satisfy a map_x/map_y protocol you would expand the homography to a dense grid via `cv2.warpPerspective` sampling — trivially invertible (matrix inverse). But it only corrects planar perspective, so it cannot back a protocol that must also remove curl. Best used as a pre-rectify stage, not the primary dewarper. Deps: numpy/scipy/OpenCV/matplotlib.

## Strengths / weaknesses for book scans
Strengths: elegant, cheap, exact homography, easy to invert. Weaknesses: perspective-only (no curl), unmaintained Py2-era code, needs dense uniform text, fragile (known "not a bracketing interval" failures), no library API.

## Sources
- https://github.com/mzucker/unproject_text
- https://mzucker.github.io/2016/10/11/unprojecting-text-with-ellipses.html
- https://github.com/mzucker/unproject_text/blob/master/README.md
