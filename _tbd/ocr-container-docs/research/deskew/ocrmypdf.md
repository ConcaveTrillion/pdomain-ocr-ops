# OCRmyPDF (deskew capability)
- Category: deskew (CLI-pipeline)
- Repo / homepage: https://github.com/ocrmypdf/OCRmyPDF — https://ocrmypdf.readthedocs.io/
- License (code; and model weights if any): Mozilla Public License 2.0 (MPL-2.0). Bundles Tesseract OCR (Apache-2.0); Tesseract language data are separate downloads, not weights shipped by OCRmyPDF.
- Language / runtime: Python 3; CLI plus a Python API.
- Install: `pip install ocrmypdf` (also needs system Tesseract, Ghostscript; optional unpaper, pngquant). Latest 17.5.0 (2025-05-27).
- Interface: CLI (`ocrmypdf --deskew in.pdf out.pdf`) and Python API (`ocrmypdf.ocr(...)`).
- Maintenance: latest 17.5.0 (2025-05-27); very active, regular releases; maintained yes.

## What it does
End-to-end PDF OCR pipeline; `--deskew` is one optional preprocessing stage. With `--deskew`, each rasterized page is straightened before OCR and the corrected raster is written back into the output PDF. Operates per page within a multi-page document.

## Algorithm
Delegates the actual skew estimation to Leptonica: "Postl's variance of line sums" projection-profile method (same engine as `pixDeskew`). OCRmyPDF rasterizes the page, calls Leptonica to find the angle, rotates, and re-emits. (`--clean` separately invokes unpaper, which is a distinct mask-based path.)

## Input-regime fit
PDF/flatbed scans of text: good — its native input is a scanned PDF, exactly the book-scan regime. Phone photos: only via PDF wrapping, and inherits Leptonica's affine-only limits (no perspective/dewarp). Two-up spreads: per-page single angle; no built-in splitting of a two-up page into independent halves (would need pre-splitting upstream).

## Leverages OCR or text-line detection?
The OCR stage uses Tesseract, but the deskew stage itself does not — deskew runs before OCR and uses Leptonica's pixel-profile statistics, not recognized text.

## Even/odd (left vs right page) handling
Per-page single-angle only. A two-up spread page gets one global angle; OCRmyPDF has no left/right per-side deskew. To handle divergent spreads, split pages into single-page images before feeding OCRmyPDF.

## How it would back our Deskew protocol
OCRmyPDF is PDF-oriented, so it is a poor fit for a per-image Deskew protocol unless our pipeline is already PDF-centric. For raw page images, prefer calling Leptonica directly (the engine OCRmyPDF wraps) rather than round-tripping through PDF. If used: `apply()` would shell out `ocrmypdf --deskew --tesseract-timeout 0 in.pdf out.pdf` (or `--rotate-pages` for orientation). It returns a corrected PDF, not a numeric angle, so `estimate()` is not naturally exposed. Dependencies: Python OCRmyPDF + Tesseract + Ghostscript.

## Strengths / weaknesses for book scans
Strengths: production-grade, well-maintained, batch PDF workflow, deskew + OCR + optional `--clean` (unpaper) in one tool, MPL-2.0. Weaknesses: PDF-in/PDF-out (heavy for per-image deskew); no exposed angle; per-page single angle (no two-up split); deskew quality is just Leptonica's, so the direct Leptonica route is leaner for our protocol.

## Sources
- https://github.com/ocrmypdf/OCRmyPDF
- https://ocrmypdf.readthedocs.io/en/latest/advanced.html
- https://ocrmypdf.readthedocs.io/en/latest/cookbook.html
- https://ocrmypdf.readthedocs.io/en/v12.0.0/cookbook.html
- https://pypi.org/project/ocrmypdf/
