---
Status: active
Owner: CT
Created: 2026-08-08
Last verified: 2026-08-08
Kind: issue
Level: I2
---

# Concurrent OCR jobs can each build a duplicate DocTR predictor

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I2
- **Last verified:** 2026-08-08
- **Resolution:** Open
- **Issue type:** Bug
- **Priority:** P2
- **Area:** gpu
- **Triage:** Accepted
- **Affected version:** `pdomain-ops` 0.11.1 (commit `b841b96`)
- **Parent:** None
- **Children:** None
- **Blocked by:** None
- **Blocks:** None
- **Read when:** changing `_predictor_cache`, adding concurrency to
  `LocalStageDispatcher`, or investigating unexplained CUDA memory growth
  under parallel OCR jobs.
- **Search terms:** predictor cache, _predictor_cache, thread safety, race,
  check-then-set, duplicate predictor, VRAM growth, run_in_executor,
  build_smaller, OOM backoff, LocalStageDispatcher.
- **Relates to:** [batched OCR dispatch](../architecture/batched-ocr-dispatch.md)

## Summary

`_predictor_cache` is a plain module-level `dict` read and written from more
than one thread with no lock. Both call sites use a non-atomic
check-then-build-then-set sequence, so two threads that miss on the same key
both build a DocTR predictor and the second write discards the first. On CUDA
that leaves an extra predictor resident in VRAM with no reference to free it,
which works against the OOM backoff this code exists to support. Found while
closing out `pdomain-ocr-simple-gui`'s deferred follow-ups, where the leaked
executor thread is already noted as a known limitation.

## Outcome / acceptance criteria

- Two threads racing on the same cache key build the predictor exactly once,
  and both receive the same object.
- A predictor built for one key is never discarded by a concurrent write under
  a different key.
- The fix does not hold a lock across an OCR run — only across cache lookup and
  insertion — so batched OCR stays concurrent.
- A regression test drives two threads at one cold key and asserts a single
  build.

## Evidence / motivation

Observation, from the code as of `b841b96`.

### 1. The cache is an unguarded plain dict

`pdomain_ops/gpu/default_stages.py:54`

```python
_predictor_cache: dict[tuple[str, str, int, int], Any] = {}
```

Neither `default_stages.py` nor `local_stage.py` imports `threading`, so there
is no lock anywhere near it:

```console
$ grep -n 'threading\|Lock' pdomain_ops/gpu/default_stages.py pdomain_ops/gpu/local_stage.py
(no output)
```

### 2. Both call sites are check-then-set, not atomic

`pdomain_ops/gpu/default_stages.py:218-221`

```python
predictor = _predictor_cache.get(cache_key)
if predictor is None:
    predictor = get_finetuned_torch_doctr_predictor(det_path, reco_path)
    _predictor_cache[cache_key] = predictor
```

`pdomain_ops/gpu/local_stage.py:163-171` repeats the same shape inside
`_get_or_build_predictor`. The build between the read and the write is the
expensive one the cache comment describes as "hundreds of ms per call" — a wide
window for a second thread to miss on the same key.

### 3. More than one thread genuinely reaches it

This is the part that turns a theoretical race into a real one.
`local_stage.py` calls `_get_or_build_predictor(det_bs, reco_bs)` on the event
loop thread, then hands `build_smaller` to `run_doctr_batch` and runs that in a
worker thread:

```python
pages = await loop.run_in_executor(
    None,
    lambda: run_doctr_batch(..., build_smaller=build_smaller, ...),
)
```

`build_smaller` closes over `_get_or_build_predictor`, and
`docs/architecture/batched-ocr-dispatch.md` records that `run_doctr_batch` calls
it during OOM backoff — inside that worker thread. So the same dict is touched
from the event loop thread and from the default `ThreadPoolExecutor`, and
`run_in_executor(None, ...)` means concurrent jobs get multiple worker threads.
There is no semaphore in `local_stage.py` serializing this.

## Dependencies

None. This is self-contained within `pdomain_ops/gpu/`.

## Next steps

1. Add a module-level `threading.Lock` beside `_predictor_cache` in
   `default_stages.py` and export it alongside the cache.
2. Wrap both check-then-set sequences so the build happens once per key. Prefer
   a double-checked pattern that holds the lock across the build for a given
   key, rather than releasing it around the build, or the race returns.
3. Add the two-thread regression test described in the acceptance criteria.

## Environment / versions

```text
pdomain-ops 0.11.1 (branch docs/file-open-issues, commit b841b96)
pdomain-book-tools 0.21.0
Python 3.11+ (CPython)
Reachable on any device; consequences are worst on CUDA.
```

## Root-cause hypotheses (ranked)

1. **(Confirmed by reading, not by a repro) Non-atomic check-then-set on shared
   mutable module state.** The read, the build, and the write are three separate
   operations with no mutual exclusion, and two threads demonstrably reach them.
   This is a defect in the code as written, independent of whether a failure has
   been observed in production.
2. **Not a dict-corruption bug.** Under CPython's GIL, individual `dict.get`
   and `dict.__setitem__` calls are atomic, so the dict cannot be structurally
   corrupted. Anyone fixing this should not reach for a concurrent map — the
   defect is the non-atomic *sequence*, not the container.

## Defects to fix

1. **Unsynchronised check-then-set in `local_stage.py:163-171`** — the site
   reachable from two threads. (Primary)
2. **Unsynchronised check-then-set in `default_stages.py:218-221`** — same
   shape; fix both so a future caller cannot reintroduce the race.

## What is NOT broken (to scope the fix)

- **The cache key.** The 4-tuple `(det_path, reco_path, det_bs, reco_bs)` is
  correct; batch sizes are baked into the predictor at build time and are
  rightly part of the key.
- **The `reportPrivateUsage` suppression** on `local_stage.py`'s import of
  `_predictor_cache`, catalogued in
  [lint deviations](../process/lint-deviations.md). The cross-module share is
  deliberate; only the missing synchronisation is at fault.
- **The OOM backoff logic** in `run_doctr_batch`. It behaves correctly given a
  working `build_smaller`; the race is in the callback's cache access, not in
  the backoff.
- **Correctness of OCR output.** A duplicate predictor produces the same
  results. The cost is wasted build time and resident memory, not wrong text.

## Resolution

*Open.* When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit link here, move the README pointer, and route the retirement
through `doc-retirer`.
