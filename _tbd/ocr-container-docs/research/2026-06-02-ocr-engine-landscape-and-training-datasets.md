# OCR engine landscape & training datasets: PaddleOCR and beyond

Date: 2026-06-02
Status: research / strategy input (no code yet)
Audience: `pdomain-book-tools` (OCR engine host), `pdomain-ocr-training`
(DocTR training library), `pdomain-ocr-synth` (synthetic-data generator),
any pd-* consumer of OCR output.

## Why this exists

CT asked whether **PaddleOCR** is worth adopting versus our current
**DocTR-on-PyTorch** pipeline with its custom fine-tuning integration, and to
survey the wider OCR-engine field and find public datasets we could train on.
This doc is the synthesis of four parallel research streams (general engines,
historical-script engines, a PaddleOCR deep-dive, and a Hugging Face / public
dataset sweep), reconciled against our actual architecture.

## TL;DR

- **Keep DocTR as the core engine.** Our entire training spine
  (`ITrainingRunner` Protocol, separate `train_detection` / `train_recognition`,
  `ExportManager` dataset layout, `.pt` checkpoint reload via
  `get_finetuned_torch_doctr_predictor`) is DocTR-shaped and PyTorch-native.
  Nothing surveyed beats DocTR *as a swap* for our use case once we fine-tune.
- **Do not adopt PaddlePaddle as a second training framework.** PaddleOCR's
  headline strengths (CJK, 100+ languages, document-VL parsing) are largely
  off-target for scanned **English / Latin historical books**. Its "ancient
  texts" gains are CJK classical script, not Fraktur / long-ſ / Antiqua.
- **The real prize is data and a few borrowable ideas, not a new engine:**
  - **Datasets** — `GT4HistOCR`, `CATMuS`, `OCR-D-GT-VD-SBB`,
    `Reichsanzeiger-GT`, the `An Gaodhal` Cló Gaelach corpus — all CC-BY 4.0,
    all convertible to DocTR line-pairs.
  - **Calamari's voting-ensemble** idea (cross-fold + confidence voting) is
    reimplementable in PyTorch and is *the* reason Calamari hits <1% CER on
    Fraktur.
  - **OCR-D preprocessing** (`sbb-binarize`, deskew) is Apache-2.0 and composes
    upstream of DocTR.
- **PaddleOCR as an optional second opinion:** if we ever want PP-OCRv5's
  accuracy, run its **weights via ONNX** (RapidOCR / `paddle2onnx`) — zero
  PaddlePaddle at runtime — never as a training target.
- **Watch, don't integrate:** VLM engines (Surya 2, olmOCR-2, dots.ocr,
  GOT-OCR2) are advancing fast but carry licence friction, no historical
  pretraining, and heavy fine-tune cost. Re-evaluate in ~12 months.

## 1. Our current stack (the baseline to beat)

Sourced from repo docs:

- **Inference** (`pdomain-book-tools`): DocTR predictor invoked via
  `Document.from_image_ocr_via_doctr` → `run_page_ocr` in
  `ocr/doctr_support.py`. Tesseract exists as a secondary path. Output is the
  recursive `Page → Block → Line → Word` tree with per-`Word` `BoundingBox` +
  `ocr_confidence`. Only *layout* detectors are pluggable
  (`register_detector`); there is **no top-level swappable OCR-engine
  protocol** — a second engine is a bolt-on today, not a drop-in.
- **Training** (`pdomain-ocr-training`): DocTR on PyTorch behind the
  `ITrainingRunner` Protocol — `train_detection(run_id, DetectionConfig)` /
  `train_recognition(run_id, RecognitionConfig)` each returning an
  `Iterator[TrainingEvent]`. Legacy `detect.py` / `recog.py` do the work;
  `ExportManager` (`datasets.py`) defines the dataset layout. torch/DocTR are
  optional `[train]` extras, deliberately isolated so other SPA backends stay
  torch-free.
- **Fine-tunes** reload via `get_finetuned_torch_doctr_predictor(det, reco)`
  from `.pt` checkpoints. Known hardening gap: HF downloads default to
  `revision=None`.

**Architectural consequence:** anything that requires a *second ML framework*
(PaddlePaddle, TensorFlow) breaks the torch-isolation design and forces a
parallel training integration. That cost is the lens for everything below.

## 2. PaddleOCR (3.x / PP-OCRv5 / PaddleOCR-VL) deep-dive

**Model lineup (current, releases through v3.6.0 May 2026):**

| Tier | Det / Rec | Notes |
|---|---|---|
| PP-OCRv5 server | `PP-OCRv5_server_det/rec` | rec weighted-avg **0.8401**; printed-text **0.9013** |
| PP-OCRv5 mobile | `PP-OCRv5_mobile_det/rec` | ~5M params; CPU >370 chars/s |
| PP-StructureV3 | modular 5-stage | layout/table/formula/seal; OmniDocBench 0.145 EN edit-dist |
| PaddleOCR-VL-1.5 | 0.9B end-to-end VLM | NaViT + ERNIE-4.5-0.3B; **94.5%** OmniDocBench |
| PP-DocLayoutV3 | layout model | handles skew/warp/illumination/screen-photo natively |

- **Genuinely best-in-class:** broad text-type coverage (CJK, handwriting,
  vertical), 22.6M training samples, monthly release cadence, and the
  scan-defect-robust PP-DocLayoutV3 — which overlaps our *own* in-flight
  geometry-correction (deskew/dewarp) work.
- **Framework lock-in:** PaddlePaddle is **required for training** (~760 MB GPU
  wheel on Baidu's own index, not standard PyPI — known resolver conflicts).
  It is **optional for inference**: PaddleOCR 3.2+ supports ONNX Runtime;
  **RapidOCR** (active, v3.8.1 Apr 2026) ships pre-converted ONNX with a pure
  Python wrapper over ORT / OpenVINO / TensorRT / PyTorch — no PaddlePaddle at
  runtime.
- **PyTorch ports:** `frotms/PaddleOCR2Pytorch` added PP-OCRv5 det/rec May 2025
  (weight-copy port). **Gaps:** PP-StructureV3, the VL model, and unwarping are
  **not** ported. So: PyTorch path exists for plain OCR det/rec; not for the
  document-parsing stack.
- **Fine-tuning:** YAML configs (`configs/rec/`, `configs/det/`), tab-separated
  label files or LMDB, `.pdparams` → exported `.pdmodel` → ONNX. More ceremony
  and more opaque than DocTR's standalone-script + `.pt` flow, and it requires
  PaddlePaddle installed even to fine-tune a recognition head.
- **Historical relevance:** the 960k "ancient books" samples are almost
  certainly CJK classical script. **No evidence of Fraktur / long-ſ / Antiqua
  coverage.** Strong on modern printed English (0.9013) and scan defects, but
  the historical-typography gap is real.
- **Licence:** Apache 2.0 (code **and** released weights). Commercial OK.

**Verdict:** adopt PP-OCRv5 **inference weights via ONNX** as an optional
second-opinion / ensemble signal if benchmarks justify it. Do **not** take on
PaddlePaddle as a second training framework. Treat PP-DocLayoutV3 as a possible
ONNX preprocessing stage, not a training target.

## 3. General OCR-engine survey (mid-2026)

Licence and framework corrections matter here — several "Apache" assumptions
are wrong.

| Engine | Framework | Fine-tune | Historical scripts | Licence | Maint. | Verdict |
|---|---|---|---|---|---|---|
| **DocTR** | PyTorch/TF | Moderate | Good *after* fine-tune | Apache 2.0 | Active (v1.0.1) | **Keep — Tier 1** |
| **Kraken v5** | PyTorch | Low–mod (`ketos`) | **Excellent (pretrained)** | Apache 2.0 | Active (ICDAR'25) | **Borrow data/ideas — Tier 1** |
| **TrOCR** | PyTorch/HF | Low (HF Trainer) | Good (community models) | MIT | via `transformers` | Benchmark recog head |
| **MMOCR** | PyTorch | High (MMEngine) | Good (config) | Apache 2.0 | Active | Tier 2 (arch experiments) |
| **Calamari** | **TensorFlow** | Low–mod | **Excellent (pretrained)** | **GPL-3.0** | Quiet/active | Borrow *ensemble idea* + GT |
| **PaddleOCR** | **PaddlePaddle** | Moderate (YAML) | Needs fine-tune; CJK-lean | Apache 2.0 | Very active | ONNX inference only |
| **Surya 2** | PyTorch+vLLM | Moderate (VLM) | Unknown | **GPL-3.0 code / CC-BY-NC weights** | Very active | Tier 3 (licence/VLM) |
| **olmOCR-2** | PyTorch/HF | High (7B RLVR) | Moderate | **CC-BY-4.0** | Active (Oct'25) | Tier 3 (monitor) |
| **dots.ocr** | PyTorch+vLLM | None documented | Unknown | MIT + supplemental | Active (Mar'26) | Tier 3 (no fine-tune) |
| **GOT-OCR2** | PyTorch/HF | Moderate (LoRA) | Unknown | Apache 2.0 | via `transformers` | Tier 3 |
| **Tesseract 5** | C++ | High (`tesstrain`) | Fraktur `deu_latf` exists | Apache 2.0 | Slow | Baseline only |
| **EasyOCR** | PyTorch | High (sparse docs) | Poor | Apache 2.0 | **Stalled mid-2024** | No |

**Licence corrections to remember:** Surya is **GPL-3.0 code + CC-BY-NC-SA-4.0
weights** (commercial waiver under $5M revenue), *not* Apache. Calamari went
**GPL-3.0** at v2.0 and is **TensorFlow**, not PyTorch. EasyOCR is effectively
unmaintained.

## 4. Historical-document / HTR ecosystem

This is where our actual domain (early-modern print, long-ſ, Fraktur, Cló
Gaelach, polytonic Greek) is best served — mostly as *data and pretrained
references*, since the best engines here are PyTorch-friendly but not drop-in
for our DocTR training spine.

- **Kraken v5** (PyTorch, Apache 2.0) — the closest philosophical fit;
  purpose-built for historical/non-Latin material, trainable
  segmentation+recognition+reading-order via `ketos`, large Zenodo model zoo.
  **CATMuS-Print** (CC-BY 4.0) is its flagship multilingual diachronic print
  model and preserves long-ſ. We can't load Kraken `.mlmodel` into DocTR, but
  its *training data* converts to line-pairs, and its binarization/segmentation
  is reusable upstream.
- **Calamari** (TF, GPL-3.0) — best published Early-Modern-Latin results
  (<1.5% CER) thanks to **cross-fold voting ensembles**. Borrow the ensemble
  *technique* in PyTorch; the pretrained models (`gt4histocr`,
  `fraktur_historical`, `antiqua_historical`) are MIT-licensed and their *GT*
  is reusable even though the weights are TF/GPL.
- **PyLaia / Transkribus** — PyLaia core is **MIT** PyTorch CNN+BiLSTM+CTC.
  Transkribus hosts the **best existing Cló Gaelach model** (*An Gaodhal*,
  CER 1.4%) and strong Fraktur/Antiqua "Super Models", but the best weights are
  platform-locked. **However the An Gaodhal training data (ALTO XML) is openly
  released** — that's the usable asset.
- **eScriptorium** — web GUI over Kraken for human-in-the-loop annotation →
  training. Best path to *build* GT for scripts with no existing model. Not a
  library; infra-heavy.
- **OCR4all / OCR-D** — German-historical-print workflow ecosystems wrapping
  Tesseract/Calamari/Kraken. **OCR-D's `sbb-binarize` and deskew preprocessing
  (Apache 2.0) are worth integrating upstream of DocTR.** Model registry exposes
  GT4HistOCR-trained Calamari/Tesseract Fraktur models.

**Pretrained models by script (best available):**

| Target | Best model(s) | Tool | Licence |
|---|---|---|---|
| Fraktur 15th–19th c. | `fraktur_historical`, `gt4histocr`; Tesseract `deu_latf` | Calamari/Tesseract | MIT / Apache |
| Early-Modern Latin print | `antiqua_historical`; CATMuS-Print | Calamari/Kraken | MIT / CC-BY 4.0 |
| Long-ſ English / early-modern | CATMuS-Print; OCR17plus | Kraken | CC-BY 4.0 |
| Cló Gaelach / Irish | *An Gaodhal* mono + bilingual | Transkribus/PyLaia | platform (GT is CC-BY 4.0) |
| Polytonic Greek | Pogretra / Ajax-commentary Kraken models | Kraken | open |

## 5. Public training datasets (Hugging Face + Zenodo)

Prioritised for **historical Latin-script book** fine-tuning. All Tier-1 are
CC-BY 4.0 and convert cleanly to DocTR line-image/label pairs.

| Rank | Dataset | Contents | Script | Licence |
|---|---|---|---|---|
| 1 | **GT4HistOCR** (Zenodo 1344132) | 313k line-pairs, 15th–19th c., long-ſ + ligatures | German Fraktur + EM Latin | CC-BY 4.0 |
| 2 | **CATMuS/Medieval** (HF) | 195k lines, 200+ MSS, rich metadata | Latin + multilingual | CC-BY 4.0 |
| 3 | **OCR-D-GT-VD-SBB** (HF/Zenodo) | 348 pages, Level-3 GT, PAGE-XML | German/Latin 1509–1827 | CC-BY 4.0 |
| 4 | **Reichsanzeiger-GT** (Zenodo) | 119k lines, ſ/ꝛ/currency glyphs | German Fraktur | CC-BY 4.0 |
| 5 | **DocLayNet v1.2** (HF) | 80k pages, 11 region classes, COCO | layout/detection | CDLA-Permissive-1.0 |
| 6 | **British Library Books** (HF) | ~25M pages 1510–1900, noisy, filterable | EN/FR/DE | **CC0** |
| 7 | **Patrologia Graeca GT** (Zenodo 7296539) | 100 pages, 2,579 lines, pageXML | polytonic Greek + Latin | CC-BY 4.0 |
| 8 | **MJSynth / Union14M** | modern-font bootstrap for rec-head init | EN scene text | MJSynth: **restrictive**; Union14M: MIT |
| 9 | **An Gaodhal** (HF / NYU ALTO XML) | 2,298 pages, ~1.86M tokens, <1% CER GT | Cló Gaelach + Roman | CC-BY 4.0 |
| 10 | **OCR17 / OCR17plus** (Zenodo) | 17th-c. prints, long-ſ preserved | Early-Modern French | CC-BY 4.0 |

**Non-commercial / licence flags:** MJSynth & SynthText (Oxford VGG, research-
only — verify before shipping), the Zenodo-3366686 font-group dataset
(CC-BY-NC-SA), IAM handwriting (Bern, non-commercial). PubLayNet (CDLA) is fine
for detection pretraining.

**Synthetic generation (for `pdomain-ocr-synth`):** **SynthTIGER** (MIT) is the
strongest generator and accepts custom fonts — point it at OFL historical
faces (**Junicode** for medieval/long-ſ, **IM Fell**, **Cormorant**, **Noto**
for polytonic Greek) to synthesise Fraktur / long-ſ / Cló Gaelach / Greek
training data. This is the realistic path for Cló Gaelach, where real GT is
only ~2,300 pages.

## 6. Recommended actions

Ordered by value-to-effort. None require leaving DocTR/PyTorch.

1. **Ingest GT4HistOCR + CATMuS-Print GT into the DocTR fine-tune set.** Write
   a converter from line-image/`.gt.txt` and PAGE/ALTO XML into `ExportManager`
   layout. Highest-leverage move; closes most of the historical-typography gap.
2. **Extend the recognition vocabulary** to cover long-ſ, ligatures, Tironian
   notes, polytonic Greek (DocTR `VOCABS` / codec resize). Prerequisite for the
   above to actually learn the glyphs.
3. **Cló Gaelach:** convert the open *An Gaodhal* ALTO XML to line-pairs and
   supplement heavily with **SynthTIGER**-generated Cló Gaelach from OFL fonts
   in `pdomain-ocr-synth`. Only viable path; expect rare-letter gaps.
4. **Borrow Calamari's voting ensemble** — cross-fold-train N DocTR recognition
   heads + confidence-weighted character voting. Cheap PyTorch reimplementation;
   biggest single CER win on degraded Fraktur.
5. **Add OCR-D `sbb-binarize` / deskew (Apache 2.0) as an optional preprocessing
   stage** upstream of DocTR — complements our in-flight geometry-correction
   work.
6. **Optional, gated on benchmarks:** export PP-OCRv5 to ONNX (RapidOCR) and
   benchmark it as a second-opinion engine on our actual corpus. Only pursue if
   it beats fine-tuned DocTR on pages DocTR misses. No PaddlePaddle runtime dep.
7. **Prerequisite for any multi-engine future:** introduce a real OCR-engine
   *predictor protocol* in `pdomain-book-tools` (today only layout is
   pluggable). Without it, any second engine is a bolt-on.
8. **Monitor (re-evaluate ~mid-2027):** olmOCR-2 (CC-BY-4.0, permissive),
   Surya 2, dots.ocr — VLM fine-tuning tooling and historical coverage are
   improving but not yet worth the compute/licence cost.

## Caveats

- Benchmark numbers are vendor/self-reported; there is **no published
  head-to-head on European scanned-book corpora**. Any engine claim must be
  validated on our own pages before acting.
- Licences were spot-checked across multiple sources but **must be re-verified
  at adoption time** — several (Surya, Calamari, dots.ocr, MJSynth) are
  non-obvious or have changed.
- "Convertible to DocTR line-pairs" assumes transcription-convention
  normalisation (diplomatic vs. normalised) — GT4HistOCR subcorpora differ.

## Sources

Engine landscape: [docTR/PyTorch](https://pytorch.org/blog/doctr-joins-pytorch-ecosystem/),
[DocTR custom training](https://mindee.github.io/doctr/latest/using_doctr/custom_models_training.html),
[Kraken v5 (ICDAR'25)](https://inria.hal.science/hal-05144723),
[Kraken docs](https://kraken.re/5.2/index.html),
[Calamari](https://github.com/Calamari-OCR/calamari),
[Calamari models](https://github.com/Calamari-OCR/calamari_models),
[Surya](https://github.com/datalab-to/surya),
[olmOCR-2](https://arxiv.org/pdf/2510.19817),
[dots.ocr](https://github.com/rednote-hilab/dots.ocr),
[GOT-OCR2](https://huggingface.co/docs/transformers/model_doc/got_ocr2),
[MMOCR](https://github.com/open-mmlab/mmocr/releases),
[TrOCR medieval print](https://huggingface.co/medieval-data/trocr-medieval-print),
[PyLaia (Teklia)](https://huggingface.co/collections/Teklia/pylaia),
[An Gaodhal model](https://www.transkribus.org/models/an-gaodhal-gaeilge-irish-monolingual-model),
[eScriptorium](https://gitlab.com/scripta/escriptorium),
[OCR4all](https://github.com/OCR4all/OCR4all),
[OCR-D models](https://ocr-d.de/en/models).

PaddleOCR: [PP-OCRv5 docs](http://www.paddleocr.ai/main/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5.html),
[PaddleOCR 3.0 report](https://arxiv.org/html/2507.05595v1),
[PaddleOCR-VL](https://huggingface.co/PaddlePaddle/PaddleOCR-VL),
[PaddleOCR2Pytorch](https://github.com/frotms/PaddleOCR2Pytorch),
[RapidOCR](https://github.com/RapidAI/RapidOCR),
[PaddleOCR releases](https://github.com/PaddlePaddle/PaddleOCR/releases).

Datasets: [GT4HistOCR](https://zenodo.org/records/1344132),
[CATMuS/Medieval](https://huggingface.co/datasets/CATMuS/medieval),
[CATMuS-Print Large](https://zenodo.org/records/10592716),
[OCR-D-GT-VD-SBB](https://huggingface.co/datasets/SBB/OCR-D-GT-VD-SBB),
[Reichsanzeiger-GT](https://pmc.ncbi.nlm.nih.gov/articles/PMC10980999/),
[British Library Books](https://huggingface.co/datasets/TheBritishLibrary/blbooks),
[DocLayNet v1.2](https://huggingface.co/datasets/docling-project/DocLayNet-v1.2),
[Patrologia Graeca GT](https://zenodo.org/records/7296539),
[An Gaodhal correction set](https://huggingface.co/datasets/ancatmara/an-gaodhal-ocr-correction),
[An Gaodhal ALTO XML](https://ultraviolet.library.nyu.edu/records/5ya5n-mc504),
[OCR17](https://zenodo.org/records/3826894),
[SynthTIGER](https://github.com/clovaai/synthtiger),
[Mixed-model historical Latin](https://arxiv.org/pdf/2106.07881).
