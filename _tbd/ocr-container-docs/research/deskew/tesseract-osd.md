# Tesseract OSD (--psm 0)
- Category: deskew (OCR-engine-feature)
- Repo / homepage: https://github.com/tesseract-ocr/tesseract
- License (code; and model weights if any): Apache 2.0 (code and the `osd.traineddata` model file)
- Language / runtime: C++ engine; Python via pytesseract/tesserocr. Needs `osd.traineddata` installed.
- Install: system Tesseract (apt/brew) + `osd.traineddata`; `pip install pytesseract` or `tesserocr`
- Interface: CLI (`tesseract img out --psm 0`) and library (tesserocr `Orientation()` API)
- Maintenance: Tesseract actively maintained (5.x). Maintained: yes.

## What it does
Orientation and Script Detection only — no character recognition. Reports page orientation (one of 0/90/180/270), orientation confidence, detected script + confidence, and a small in-plane "deskew angle."

## Algorithm
Runs the OSD classifier (`osd.traineddata`) over candidate page rotations to pick the upright multiple-of-90 orientation and script. The fine deskew angle is a small residual in-plane estimate. CLI `--psm 0` writes an `.osd` file with these fields; the precise deskew-angle float is most reliably read through the API (`tesserocr` `Orientation()` returns orientation, writing direction, textline order, deskew angle).

## Input-regime fit
Built primarily for coarse orientation (is the page upside-down / rotated 90?). Flatbed scans: reliable for the 0/90/180/270 decision. Phone photos: orientation usually fine; fine-angle less dependable. Two-up spreads: OSD assumes a single page; mixed content degrades it.

## Leverages OCR or text-line detection?
Yes — indirectly. OSD is a trained text/script model, so it relies on text presence; it fails on text-sparse or heavily graphical pages.

## Even/odd (left vs right page) handling
Whole-image single result only. No per-side support. A two-up spread yields one orientation/angle; split before calling for per-page results.

## How it would back our Deskew protocol
Best as a coarse orientation stage, not the precise deskewer. `estimate()` → run `--psm 0` (or tesserocr `Orientation()`), parse orientation degrees + deskew angle; rotate by the 90-multiple to make the page upright, then hand off to a fine deskewer (sbrunner/deskew, jdeskew, or our OpenCV pipeline) for the sub-degree correction. `apply()` → our own rotate. Dependency: a Tesseract install + `osd.traineddata` — heavier than a pure-Python lib. Note: the CLI `.osd` deskew-angle output has historically been flaky across releases (issues #1463, #2062); prefer the API.

## Strengths / weaknesses for book scans
Strengths: robust 90-degree orientation + script detection no classical method gives you; well-maintained. Weaknesses: fine deskew angle unreliable/coarse; single global result; requires Tesseract install; needs text to work.

## Sources
- https://github.com/tesseract-ocr/tesseract
- https://github.com/tesseract-ocr/tesseract/issues/1463
- https://github.com/tesseract-ocr/tesseract/issues/2062
- https://issues.apache.org/jira/browse/TIKA-2696
