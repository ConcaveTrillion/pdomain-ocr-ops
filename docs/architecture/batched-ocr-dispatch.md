---
Status: built
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-13
Kind: architecture
---

# Batched OCR dispatch

## Agent Index

- **Kind:** architecture
- **Status:** built
- **Read when:** changing DocTR batch sizing, local OCR dispatch, or OOM recovery.
- **Search terms:** batched OCR, DocTR, OOM backoff, StageDispatcher, predictor cache.

## Current behavior

`pdomain-ops` owns the application-neutral GPU boundary: request and result
types, device selection, stage registration, dispatcher protocols, and local
execution. Applications own product workflow, persistence, and UI. A stage
implementation receives the resolved device through the dispatcher seam; it
does not discover application state or reach into a sibling repository.

Local OCR accepts a batch request through the stage-dispatch protocol. The
worker sizes DocTR detection and recognition batches for the selected device,
reuses predictors by batch size, and retries CUDA allocation failures with a
smaller detection batch. The worker returns page objects, while the dispatcher
serializes results at its boundary.

The worker accepts image bytes or arrays, not filesystem paths. This keeps the
dispatcher contract usable across local and remote transports. The caller owns
predictor caching and supplies any smaller-predictor builder; the worker remains
location-independent. If detection batch size 1 still exhausts memory, the
worker falls back to per-image CPU OCR. Non-memory failures surface unchanged.

CPU and GPU use the same batched worker without a second concurrent worker
pool. Consumer orchestration may split work into chunks so one failed chunk
does not discard earlier results, but chunk size and DocTR's internal detection
batch size remain separate controls.

Remote Modal and shared-container batch dispatch remain explicit unsupported
stubs. A future implementation can use the existing request and protocol seam;
it is not part of the shipped local path.

## Ownership boundary

The package extends sibling applications through typed adapters. It does not
replace their orchestration or make one transport mandatory. The shipped path
is local dispatch with registered default stages. Remote Modal and
shared-container transports are unbuilt, and their stubs must not be described
as available backends.

## Open calibration questions

- Real GPU measurements may justify changing the device-to-batch-size table.
- The single-image OCR protocol remains separate from the batch API until a
  consumer migration proves that removing it is safe.

## Evidence

- **Code:** `pdomain_ops/gpu/doctr_batch.py`, `pdomain_ops/gpu/device.py`,
  `pdomain_ops/gpu/protocols.py`, `pdomain_ops/gpu/types.py`,
  `pdomain_ops/gpu/local_stage.py`, `pdomain_ops/gpu/default_stages.py`
- **Tests:** `tests/gpu/test_doctr_batch.py`,
  `tests/gpu/test_pick_doctr_batch_sizes.py`,
  `tests/gpu/test_local_batch_dispatcher.py`,
  `tests/gpu/test_remote_batch_stubs.py`
- **Commits:** `8703224`, `eee600b`, `bcb369d`, `fa1ae94`, `2015ef5`
- **Salvaged sources:**
  `_tbd/ocr-container-docs/archive/plans/2026-05-16-pd-ocr-ops-new-repo.md`,
  `_tbd/ocr-container-docs/archive/plans/2026-05-16-phase-1-7-gpu-adapter-migration.md`,
  `_tbd/ocr-container-docs/specs/2026-05-16-cross-cut-design.md`
- **Verified:** 2026-07-13 with the focused source and test evidence above.
