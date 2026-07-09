---
status: complete
synced: 2026-05-17
milestone: 5
repo: ConcaveTrillion/ocr-container-meta
---

# Phase 1.7 — pgdp-prep GPU dispatch → pdomain-ocr-ops migration

> **⚠️ NEEDS PARTIAL REFRAME — DEFERRED until pdomain-ocr-ops M8 ships
> (per #181 decision, 2026-05-17).**
>
> #181 changed the OCR-dispatch story: **simple-gui** (not Phase 1.7)
> drives building the OCR-dispatch surface in pdomain-ocr-ops as its reference
> consumer. Phase 1.7 reframes from "lift pgdp-prep's GPU code wholesale"
> to "**adopt the validated surface; lift only what's genuinely
> pgdp-prep-specific**." Concrete task-by-task impact when the rewrite
> happens:
>
> | Task | Reframe impact |
> |---|---|
> | 1 Inventory | Survives unchanged |
> | 2 Move-vs-copy decision | Survives unchanged |
> | 3 CI baseline | Survives unchanged |
> | **4 STAGE_IMPL registry plumbing** | **Shrinks substantially** — registry data structure + `register_stage()` already land in pdomain-ocr-ops M8.2/M8.3; this task becomes "pgdp-prep adopts `register_default_stages()` (built by simple-gui) + registers pgdp-specific stages via existing `register_stage()` helper" |
> | **5 Dispatcher Protocols + Immediate/Batched** | **Likely shrinks** — Protocols already in pdomain-ocr-ops M8; only `BatchDispatcher` (5-min flush-window batcher) is genuinely new infra |
> | 6 Request/response types | Survives — types belong in pdomain-ocr-ops |
> | 7 ModalBackend | Survives — pgdp-prep-specific GPU adapter, belongs in pdomain-ocr-ops |
> | 8 SharedContainerBackend | Survives — same rationale as 7 |
> | 9 Env-var rename | Survives unchanged |
> | 10 Re-point pgdp-prep imports | Survives — minor expansion to also import `register_default_stages` |
> | 11 Regression verify | Survives unchanged |
> | 12 Publish 0.2.0 | Survives unchanged |
> | 13 Cleanup | Survives unchanged |
>
> **Why deferred:** doing the Task 4/5 rewrite now would redesign against a
> speculative pdomain-ocr-ops M8 surface. Defer to when pdomain-ocr-ops M8 actually
> ships AND simple-gui's `register_default_stages()` task lands — both are
> required inputs. Task bodies below describe the pre-#181 design and will
> be updated then.
>
> See `docs/specs/2026-05-17-pdomain-ocr-simple-gui-design.md` §5
> "OCR dispatch surface" and §9 "Reference-consumer role" for the upstream
> framing.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lift `pdomain-prep-for-pgdp`'s existing GPU dispatch primitives — the
`STAGE_IMPL` registry pattern, the `ModalBackend`/Modal-app pair (with its
5-min flush-window batching collaborator `BatchDispatcher`), and the
`SharedContainerBackend` HTTP client — out of pgdp-prep and into
`pdomain-ocr-ops` as the canonical workspace home. After the move, pgdp-prep
imports them from pdomain-ocr-ops and ships with **no user-visible functional
change**. Rename the env var `PGDP_GPU_BACKEND` → `PD_GPU_BACKEND`, keeping
the old name working as a deprecation alias (one-release-cycle grace
window) that emits a `DeprecationWarning` when used.

**Scope preamble — hard dependencies:**

1. **Plan #5 (`pdomain-ocr-ops` foundation) must have shipped first.** This plan
   does not create `pdomain-ocr-ops`; it *moves code into* it. Specifically it
   needs the following already-landed pdomain-ocr-ops surface:
   - `pd_ocr_ops/gpu/` package exists with `pd_ocr_ops.gpu.StageDispatcher`
     and `pd_ocr_ops.gpu.LongJobRunner` Protocols defined (`§8 GPU
     dispatch`).
   - `pd_ocr_ops.gpu.pick_device()` helper defined.
   - `LocalStageDispatcher` (the in-process Phase-1 adapter) exists so
     this migration only adds *out-of-process* dispatcher
     implementations (Modal, shared-container) plus the `STAGE_IMPL`
     registry the local adapter dispatches through.
   - `pdomain-ocr-ops` is publishing to `pdomain-index-pip` (the renamed `pd-index`
     from plan #3) at some pinnable version, and pgdp-prep already
     consumes it transitively (or this plan adds the dep — Task 4).
2. **This is the first cross-repo Phase 1.7 work.** No prior plan has
   moved code *out of* pgdp-prep into pdomain-ocr-ops. That means the
   `pdomain-prep-for-pgdp` ↔ `pdomain-ocr-ops` upgrade-coupling cycle (bump
   pdomain-ocr-ops minor → re-pin pgdp-prep → verify pgdp-prep CI green) is
   being exercised end-to-end for the first time. Treat the dual-CI
   verification (Task 11) as load-bearing, not ceremonial.

**Architecture:** The existing pgdp-prep code already conforms to the spec
shapes (the `GPUBackend` Protocol in `adapters/gpu/base.py` is exactly
what `§8 GPU dispatch` calls `StageDispatcher`; the `BatchDispatcher` in
`dispatcher/batched.py` is the 5-min flush-window collaborator the spec
mentions at `specs/04-gpu-acceleration.md:327`; and the `STAGE_IMPL` table
in `core/pipeline/stage_registry.py` is the canonical registry pattern).
This migration is therefore a **package move + rename**, not a redesign.
The pre-move file sizes are small enough that a copy-then-delete approach
is viable (`adapters/gpu/base.py:113`, `modal_backend.py:119`,
`shared_container.py:44`, `dispatcher/batched.py:100`,
`dispatcher/immediate.py:34`, `dispatcher/base.py:20` — total ~430 lines
of dispatch code plus the 776-line `stage_registry.py` and its
collaborators).

**Tech stack:** Python 3.13 in pgdp-prep; pdomain-ocr-ops targets 3.10+ (per
plan #5). Both use `hatchling`, `uv`, `pytest`. The `modal` dep stays an
optional extra in pdomain-ocr-ops (mirroring pgdp-prep's
`[project.optional-dependencies] modal = ["modal>=0.66"]`).

**Working directories:**
- pdomain-prep-for-pgdp work: `/workspaces/ocr-container/pdomain-prep-for-pgdp/`
- pdomain-ocr-ops work: `/workspaces/ocr-container/pdomain-ocr-ops/`

---

## Task 1: Inventory the current pgdp-prep GPU dispatch surface {#inventory-the-current-pgdp-prep-gpu-dispatch-surfa}

**Why:** Before moving anything, freeze the exact list of files,
symbols, env-var sites, and test fixtures that constitute the
"GPU dispatch" surface. A clean inventory becomes the checklist for
every later move/delete task and the regression net for the final
sweep. Doing this as a discrete first task means later tasks can refer
back to "the inventory list" without re-doing the search each time.

**What:** Produce a markdown inventory at
`pdomain-prep-for-pgdp/docs/phase-1-7-inventory.md` listing exactly what
moves (with line counts), what stays (env-var indirection, settings
glue, FastAPI wiring), and which tests cover each piece. The file is
deleted in the final cleanup task (Task 13) — it's scaffolding for the
migration, not a permanent artifact.

- [ ] **Step 1: Inventory the GPU adapter package (moves out)**

Run (from `/workspaces/ocr-container/pdomain-prep-for-pgdp/`):

```sh
wc -l src/pd_prep_for_pgdp/adapters/gpu/*.py
```

Expected output: `base.py` 113 lines, `modal_backend.py` 119 lines,
`shared_container.py` 44 lines, `modal_app.py` 89 lines, `__init__.py` 21
lines.

These five files **move to pdomain-ocr-ops in Tasks 4–7**. Confirm no
additional files have appeared since this plan was written; if any did,
add them to the inventory and decide per-file whether they move.

- [ ] **Step 2: Inventory the dispatcher package (moves out)**

Run:

```sh
wc -l src/pd_prep_for_pgdp/dispatcher/*.py
```

Expected: `base.py` 20, `batched.py` 100, `immediate.py` 34, `__init__.py` 7.

These four files move to pdomain-ocr-ops in Task 6. The `BatchDispatcher`
in `batched.py` is the 5-min flush-window collaborator the spec names
explicitly.

- [ ] **Step 3: Inventory the STAGE_IMPL registry (moves out, partially)**

Run:

```sh
grep -n "^def \|^class \|^STAGE_IMPL" src/pd_prep_for_pgdp/core/pipeline/stage_registry.py | head -50
```

Note which symbols are **registry plumbing** (the `STAGE_IMPL` dict
itself, `StageNotImplemented` exception, `get_stage_impl`,
`_make_placeholder`, `_build_registry`) vs which are
**pgdp-prep-specific stage implementations** (everything matching
`_<stage_id>_cpu`). The registry plumbing moves; the stage
implementations stay in pgdp-prep and re-register themselves into the
canonical registry on import.

Document the boundary in the inventory file: the pdomain-ocr-ops side defines
the registry data structure and lookup function; pgdp-prep keeps its
per-stage `_grayscale_cpu`, `_threshold_cpu`, …, callables and registers
them against the relocated registry. Same shape as the current
`_build_registry()` call site, just with the registry object imported
instead of defined locally.

- [ ] **Step 4: Inventory env-var and settings sites**

Run:

```sh
grep -rn "PGDP_GPU_BACKEND\|gpu_backend\|GpuBackend" src/ tests/ docs/ --include="*.py" --include="*.md"
```

Expected hits (do not exhaustively list — capture the file:line set in
the inventory file):
- `src/pd_prep_for_pgdp/settings.py` — declares the `gpu_backend` field
  on `Settings` (env prefix `PGDP_` → `PGDP_GPU_BACKEND`).
- `src/pd_prep_for_pgdp/bootstrap.py` — `_autodetect_gpu_backend()` and
  `build_gpu_backend()` consume the setting.
- `src/pd_prep_for_pgdp/core/models.py:435` — `Job.gpu_backend` Literal.
- `src/pd_prep_for_pgdp/api/healthz.py` — emits `gpu_backend` in the
  healthz payload.
- Various test files asserting backend name.

The settings field name (`gpu_backend`) stays — it's the **env-var
binding mechanism** that changes. The `pydantic-settings` `env_prefix =
"PGDP_"` is what produces `PGDP_GPU_BACKEND`; Task 8 introduces a
prefix-agnostic alias so both `PGDP_GPU_BACKEND` and `PD_GPU_BACKEND`
resolve to the same `Settings.gpu_backend` value.

- [ ] **Step 5: Inventory the test surface (the regression net)**

Run:

```sh
find tests -name "test_modal*" -o -name "test_dispatcher*" -o -name "test_stage_registry*" -o -name "test_gpu*"
```

Expected files: `test_modal_backend.py`, `test_modal_app_import.py`,
`test_dispatcher_immediate.py`, `test_dispatcher_batched.py`,
`test_dispatcher_batched_loop.py`, `test_gpu_dispatch_routes.py`,
`test_gpu_illustration_routes.py`, plus any `test_stage_registry*`
present. List each with its line count.

These are the existing regression net. The dispatcher / Modal-backend
tests move with their code to pdomain-ocr-ops (Tasks 5–7); the FastAPI
gpu-routes tests stay in pgdp-prep but get re-pointed to the new import
path (Task 9). Settings-rebinding tests for the env-var alias are new
(Task 8).

- [ ] **Step 6: Write the inventory file**

Create `pdomain-prep-for-pgdp/docs/phase-1-7-inventory.md` with four sections
(MOVES, STAYS, ENV-VAR SITES, TESTS), each populated from Steps 1–5.
Keep it short — this is a checklist, not prose.

- [ ] **Step 7: Commit the inventory**

```bash
git add docs/phase-1-7-inventory.md
git commit -m "$(cat <<'EOF'
docs(phase-1-7): inventory pgdp-prep GPU dispatch surface pre-migration

Scaffolding for the spec-§7 Phase 1.7 migration of STAGE_IMPL + Modal +
shared-container dispatchers into pdomain-ocr-ops. File enumerates what
moves, what stays, the env-var rename targets, and the existing test
regression net. Will be deleted in the final cleanup task once the
migration lands.
EOF
)"
```

---

## Task 2: Decision — git-history-preserving move vs copy-then-delete {#decision-git-history-preserving-move-vs-copy-then-}

**Why:** Moving Python modules between two separate Git repositories is
not a `git mv`. The two valid approaches have different costs and
different "what does `git log` show me" trade-offs that downstream
spelunking will care about. Locking the decision **before** any code
moves prevents a half-done migration that can't be cleanly switched.

**What:** Pick one of two strategies. The plan recommends **(B) copy-then-delete**
but flags this choice for CT to confirm before Task 4. Decision lands in
the inventory file (Task 1's output) under a new `DECISION:` section.

### Option A — git-history-preserving subdirectory extract

Use `git filter-repo --subdirectory-filter src/pd_prep_for_pgdp/adapters/gpu`
(plus separate runs for `dispatcher/` and the registry-plumbing slice of
`core/pipeline/stage_registry.py`) on a throwaway clone of
`pdomain-prep-for-pgdp`, then graft the rewritten history onto the
`pdomain-ocr-ops` tree.

**Cost:** Multiple invocations because `filter-repo` operates on one
subdirectory per pass; the `stage_registry.py` symbol-level extraction
is **not** a clean subdirectory boundary (the file mixes registry
plumbing with pgdp-specific stage callables — see Task 1 Step 3), so
that slice would have to be a file-level extract followed by manual
trimming in-tree. The merged history would carry pgdp-prep's old commit
SHAs into pdomain-ocr-ops's `git log`, which conflicts with pdomain-ocr-ops being
a clean foundation lib with no project-specific provenance.

**Benefit:** `git log --follow` on the moved files shows their full
history. For a 430-line dispatch package and a ~200-line registry slice,
the history payoff is modest.

### Option B — copy-then-delete (RECOMMENDED)

Copy the files into pdomain-ocr-ops with their imports rewritten to
pdomain-ocr-ops paths (Tasks 4–7); land them as a single feat commit
attributing the source with a `Cherry-picked-from: pdomain-prep-for-pgdp@<sha>`
trailer pointing at the pgdp-prep commit that introduced each file
(captured from `git log --diff-filter=A --format=%H -- <path>`). Then
delete the files from pgdp-prep in Task 9 with a commit message that
links forward to the pdomain-ocr-ops commit.

**Cost:** `git log --follow` on the moved files in pdomain-ocr-ops stops at
the cherry-pick commit; spelunkers have to chase the trailer to find
the pgdp-prep history. The trailer is mechanical to add.

**Benefit:** Each side's `git log` is clean. Single forward-link from
pgdp-prep's delete commit to pdomain-ocr-ops's add commit; single backward
trailer from pdomain-ocr-ops's add commit to pgdp-prep's origin commit. No
`filter-repo` tooling required, no throwaway clones, no symbol-level
extraction headaches for `stage_registry.py`.

### Recommendation

Go with **(B)**. The history payoff of (A) is low for files this small,
and the stage_registry.py slice can't cleanly subdirectory-extract
anyway. The bidirectional trailer + delete-commit link gives 90% of the
spelunking value at 10% of the cost.

- [ ] **Step 1: Surface the decision to CT**

Post the recommendation above (Option A vs B summary, plus the
RECOMMENDED line) as a comment on the issue tracking this plan, or — if
this plan is being executed without an issue — present it inline at the
start of the executing session and wait for explicit confirmation
("A", "B", "go ahead with B", etc.) before continuing.

**Do not proceed to Task 3 until the decision is recorded.**

- [ ] **Step 2: Record the decision in the inventory file**

Append to `pdomain-prep-for-pgdp/docs/phase-1-7-inventory.md`:

```markdown
## DECISION: migration strategy

CT chose **Option <A|B>** on <date>. <one-line rationale>.
```

- [ ] **Step 3: Commit**

```bash
git add docs/phase-1-7-inventory.md
git commit -m "docs(phase-1-7): record migration-strategy decision (Option <A|B>)"
```

---

## Task 3: Capture pgdp-prep's pre-migration CI baseline {#capture-pgdp-preps-pre-migration-ci-baseline}

**Why:** The migration is a no-functional-change refactor. The way to
prove that is "the exact same `make ci AI=1` exit code and test count
before and after." Capture the baseline now so the post-migration
verification in Task 11 has an unambiguous comparator.

**What:** Run `make ci AI=1` from a clean `main` checkout of pgdp-prep,
record passing test count and exit code in the inventory file.

- [ ] **Step 1: Run the baseline**

From `/workspaces/ocr-container/pdomain-prep-for-pgdp/`:

```sh
make ci AI=1 2>&1 | tail -20
```

Expected: exit code 0. The tail should show the pytest summary line
("`N passed in M.MMs`"). Capture both numbers.

If `make ci AI=1` is not green on `main` already, **stop**. This
migration is not a triage exercise — fix the pre-existing failure on
`main` in a separate PR first, then resume Task 3.

- [ ] **Step 2: Record the baseline**

Append to `pdomain-prep-for-pgdp/docs/phase-1-7-inventory.md`:

```markdown
## CI BASELINE (pre-migration)

- Command: `make ci AI=1`
- Date: <YYYY-MM-DD>
- Exit code: 0
- Pytest summary: `N passed in M.MMs` (captured 2026-05-XX)
```

- [ ] **Step 3: Commit**

```bash
git add docs/phase-1-7-inventory.md
git commit -m "docs(phase-1-7): record pre-migration CI baseline"
```

---

## Task 4: Add `pdomain-ocr-ops` GPU package skeleton and move `STAGE_IMPL` registry plumbing {#add-pdomain-ocr-ops-gpu-package-skeleton-and-move-stage}

**Files (pdomain-ocr-ops):**
- Create: `pd_ocr_ops/gpu/__init__.py` (re-exports — additive to the existing file from plan #5)
- Create: `pd_ocr_ops/gpu/stage_registry.py`
- Create: `tests/gpu/test_stage_registry.py`

**Why:** The registry data structure (`STAGE_IMPL: dict[str, dict[str, Callable]]`),
its lookup helper (`get_stage_impl`), its sentinel exception
(`StageNotImplemented`), and the placeholder-callable factory
(`_make_placeholder`) are foundation-level — every dispatcher
implementation looks stages up through them. They live in pdomain-ocr-ops so
both the local-mode dispatcher already shipped by plan #5 and the
forthcoming Modal/shared-container dispatchers go through one canonical
registry.

**What:** Extract only the registry **plumbing** (no stage callables) from
`pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/core/pipeline/stage_registry.py`
into a new pdomain-ocr-ops module. The pgdp-prep file keeps every
`_<stage_id>_cpu` function plus a `register_pgdp_stages()` function that
populates the relocated registry; Task 9 calls that registration at
pgdp-prep startup.

- [ ] **Step 1: Write the failing test (pdomain-ocr-ops side)**

In `/workspaces/ocr-container/pdomain-ocr-ops/`, create `tests/gpu/test_stage_registry.py`:

```python
"""Tests for pd_ocr_ops.gpu.stage_registry — the canonical STAGE_IMPL.

This is foundation-level: no per-app stage callables live here. Apps
register their own stage impls against this registry at startup.
"""
from __future__ import annotations

import pytest

from pd_ocr_ops.gpu.stage_registry import (
    STAGE_IMPL,
    StageNotImplemented,
    get_stage_impl,
    register_stage_impl,
)


def test_stage_impl_starts_empty():
    # New process — no one has registered anything yet.
    # (Other tests must clear any registrations they make.)
    assert isinstance(STAGE_IMPL, dict)


def test_register_and_lookup_roundtrip():
    def my_cpu_impl(image, cfg=None):
        return image

    register_stage_impl("custom_stage", "cpu", my_cpu_impl)
    try:
        fn = get_stage_impl("custom_stage", "cpu")
        assert fn is my_cpu_impl
    finally:
        STAGE_IMPL.pop("custom_stage", None)


def test_get_stage_impl_unknown_stage_raises_stage_not_implemented():
    with pytest.raises(StageNotImplemented) as ei:
        get_stage_impl("never_registered_stage", "cpu")
    assert "never_registered_stage" in str(ei.value)


def test_get_stage_impl_unknown_device_falls_through_to_stage_not_implemented():
    def cpu_impl(image, cfg=None):
        return image

    register_stage_impl("device_test_stage", "cpu", cpu_impl)
    try:
        with pytest.raises(StageNotImplemented):
            get_stage_impl("device_test_stage", "cuda")
    finally:
        STAGE_IMPL.pop("device_test_stage", None)


def test_stage_not_implemented_is_runtime_error_not_notimplementederror():
    # Spec Q9 rationale: built-in NotImplementedError means "abstract
    # method", which is the wrong signal. We use a RuntimeError subclass.
    assert issubclass(StageNotImplemented, RuntimeError)
    assert not issubclass(StageNotImplemented, NotImplementedError)
```

Run: `uv run pytest tests/gpu/test_stage_registry.py -v`
Expected: all tests fail with `ModuleNotFoundError: No module named 'pd_ocr_ops.gpu.stage_registry'`.

- [ ] **Step 2: Extract the registry plumbing from pgdp-prep**

Open
`/workspaces/ocr-container/pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/core/pipeline/stage_registry.py`
and locate the **plumbing-only** symbols:
- The module docstring's "Why a typed `StageNotImplemented` sentinel" section.
- The `StageNotImplemented` class (line 53).
- `_make_placeholder(stage_id)` (line 62).
- The `STAGE_IMPL: dict[str, dict[str, Callable]]` declaration (line 760).
- `get_stage_impl(stage_id, device)` (line 768).

Create `/workspaces/ocr-container/pdomain-ocr-ops/pd_ocr_ops/gpu/stage_registry.py`:

```python
"""Canonical STAGE_IMPL[stage_id][device] registry.

The single map every dispatcher implementation looks up against. Apps
register their per-stage callables here at startup via
:func:`register_stage_impl`; the local-mode dispatcher
(:class:`pd_ocr_ops.gpu.LocalStageDispatcher`) and out-of-process
dispatchers (Modal, shared-container) all dispatch through the same
table.

This module is intentionally **thin and side-effect free**. No
implementations live here; no app-specific imports. The per-stage
callables are registered by each consuming app at startup.

## StageNotImplemented (typed sentinel)

Built-in :class:`NotImplementedError` is conventionally raised by
abstract methods to signal "subclass must implement this" — the wrong
shape for "we know this stage exists but no one wired the code yet."
:class:`StageNotImplemented` is a :class:`RuntimeError` subclass so
``except Exception`` paths catch it without needing to know the
sentinel exists, and runners can distinguish "real bug" from "not yet
wired" for clear user-facing error messages.

History: extracted from
``pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/core/pipeline/stage_registry.py``
in spec-§7 Phase 1.7 (2026-05-17).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class StageNotImplemented(RuntimeError):  # noqa: N818  # signals "not yet wired", not an error state
    """Raised when a stage lookup misses or a placeholder callable is invoked."""


def _make_placeholder(stage_id: str, device: str = "cpu") -> Callable[..., Any]:
    """Build a placeholder callable for stages without a real impl yet.

    Closure-bound so the message names the right stage without
    relying on traceback-walk hacks.
    """

    def _placeholder(*_args: Any, **_kwargs: Any) -> Any:
        raise StageNotImplemented(
            f"stage {stage_id!r} has no implementation registered for "
            f"device {device!r} (placeholder — register one via "
            "pd_ocr_ops.gpu.register_stage_impl)"
        )

    _placeholder.__name__ = f"placeholder_{stage_id}_{device}"
    _placeholder.__doc__ = (
        f"Placeholder for stage {stage_id!r} device {device!r} — raises StageNotImplemented."
    )
    return _placeholder


STAGE_IMPL: dict[str, dict[str, Callable[..., Any]]] = {}
"""``{stage_id: {device: callable}}``. Populated at startup by each app."""


def register_stage_impl(stage_id: str, device: str, impl: Callable[..., Any]) -> None:
    """Register one ``(stage_id, device)`` → callable mapping.

    Idempotent on identical re-registration of the same callable; raises
    :class:`ValueError` on conflicting re-registration so accidental
    double-import doesn't silently shadow a real impl.
    """
    existing = STAGE_IMPL.get(stage_id, {}).get(device)
    if existing is not None and existing is not impl:
        raise ValueError(
            f"stage {stage_id!r} device {device!r} already registered to "
            f"{existing!r}; refusing to shadow with {impl!r}"
        )
    STAGE_IMPL.setdefault(stage_id, {})[device] = impl


def get_stage_impl(stage_id: str, device: str) -> Callable[..., Any]:
    """Look up an impl; raise :class:`StageNotImplemented` if missing."""
    devices = STAGE_IMPL.get(stage_id)
    if not devices:
        raise StageNotImplemented(
            f"stage {stage_id!r} has no registered implementations "
            "(call pd_ocr_ops.gpu.register_stage_impl(...) at startup)"
        )
    impl = devices.get(device)
    if impl is None:
        raise StageNotImplemented(
            f"stage {stage_id!r} has no implementation for device {device!r} "
            f"(registered devices: {sorted(devices)})"
        )
    return impl
```

Update `/workspaces/ocr-container/pdomain-ocr-ops/pd_ocr_ops/gpu/__init__.py` to
re-export the new symbols. The file already exists from plan #5; add:

```python
from .stage_registry import (
    STAGE_IMPL,
    StageNotImplemented,
    get_stage_impl,
    register_stage_impl,
)
```

…and append those names to the module's `__all__`.

- [ ] **Step 3: Run the test to verify it passes**

Run: `uv run pytest tests/gpu/test_stage_registry.py -v`
Expected: 5 passed.

- [ ] **Step 4: Run pdomain-ocr-ops's full CI**

Run: `make ci AI=1` (or pdomain-ocr-ops's equivalent gate).
Expected: green. The new module is additive and only depends on stdlib.

- [ ] **Step 5: Commit (pdomain-ocr-ops side)**

```bash
git add pd_ocr_ops/gpu/stage_registry.py pd_ocr_ops/gpu/__init__.py tests/gpu/test_stage_registry.py
git commit -m "$(cat <<'EOF'
feat(gpu): add canonical STAGE_IMPL registry + register_stage_impl/get_stage_impl

Extracts the registry plumbing from pdomain-prep-for-pgdp's
core/pipeline/stage_registry.py — the data structure
(STAGE_IMPL[stage_id][device]), the typed StageNotImplemented sentinel
(spec Q9 rationale), the placeholder-callable factory, and the
lookup/register helpers. No per-app stage callables live here; apps
register their own at startup.

The local-mode dispatcher already shipped by plan #5 and the Modal /
shared-container dispatchers to be moved in later tasks of the §7
Phase 1.7 migration all dispatch through this one canonical table.

Cherry-picked-from: pdomain-prep-for-pgdp@<sha of the commit that introduced
the equivalent code in pgdp-prep; capture via
git log --diff-filter=A --format=%H -- src/pd_prep_for_pgdp/core/pipeline/stage_registry.py>
EOF
)"
```

(If Task 2's decision was Option A, replace this whole step with the
`filter-repo` invocation that produces an equivalent commit on the
pdomain-ocr-ops branch.)

---

## Task 5: Move dispatcher Protocols + Immediate/Batched implementations into pdomain-ocr-ops {#move-dispatcher-protocols-immediatebatched-impleme}

**Files (pdomain-ocr-ops):**
- Create: `pd_ocr_ops/gpu/dispatcher.py`
- Create: `tests/gpu/test_dispatcher_immediate.py`
- Create: `tests/gpu/test_dispatcher_batched.py`
- Create: `tests/gpu/test_dispatcher_batched_loop.py`

**Why:** The `IDispatcher` Protocol + `ImmediateDispatcher` +
`BatchDispatcher` triplet is the **5-min flush-window batching primitive**
the spec names at `specs/04-gpu-acceleration.md:327`. It belongs in
pdomain-ocr-ops so any consumer (pgdp-prep, future trainer, future
simple-gui) gets the same batch-flush semantics for free. The
implementations are already minimal (`ImmediateDispatcher` 34 lines;
`BatchDispatcher` 100 lines) and depend only on a `GPUBackend`
Protocol-shaped object — which the spec already names
`StageDispatcher`.

**What:** Copy the three dispatcher files from pgdp-prep into
pdomain-ocr-ops, rewriting the import of `..adapters.gpu` to the (also being
moved) request/response types in `pd_ocr_ops.gpu.types`. Copy the
existing pgdp-prep tests verbatim (they're pure behavior tests — they
don't reach into pgdp-prep state).

- [ ] **Step 1: Inspect the existing pgdp-prep dispatcher code**

Read (in `/workspaces/ocr-container/pdomain-prep-for-pgdp/`):
- `src/pd_prep_for_pgdp/dispatcher/base.py` (20 lines)
- `src/pd_prep_for_pgdp/dispatcher/immediate.py` (34 lines)
- `src/pd_prep_for_pgdp/dispatcher/batched.py` (100 lines)

The only pgdp-prep-specific import is `from ..adapters.gpu import
BatchJobItem, BatchJobResult, GPUBackend`. Those types move in Task 6.

- [ ] **Step 2: Create a placeholder `pd_ocr_ops/gpu/types.py`**

Defer the full type-move to Task 6, but the dispatcher needs *something*
to import. Create a stub that re-exports the types from the (about-to-move)
location. The full move lands in Task 6; this is a minimum-viable shim:

```python
"""Request/response types for short-task stage dispatch.

Full type definitions land in Task 6 (move from
pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/adapters/gpu/base.py). This file
exists so Task 5's dispatcher copy compiles before Task 6 runs.
"""
from __future__ import annotations

# Stubs — replaced wholesale in Task 6.
# Tests in this task use trivial fakes that match the Protocol shape,
# so the real implementations don't have to exist yet.
```

- [ ] **Step 3: Write the failing tests (copy from pgdp-prep)**

Copy these files verbatim from pgdp-prep to pdomain-ocr-ops, rewriting **only**
the imports:
- `pdomain-prep-for-pgdp/tests/test_dispatcher_immediate.py` → `pdomain-ocr-ops/tests/gpu/test_dispatcher_immediate.py`
- `pdomain-prep-for-pgdp/tests/test_dispatcher_batched.py` → `pdomain-ocr-ops/tests/gpu/test_dispatcher_batched.py`
- `pdomain-prep-for-pgdp/tests/test_dispatcher_batched_loop.py` → `pdomain-ocr-ops/tests/gpu/test_dispatcher_batched_loop.py`

Rewrite each `from pd_prep_for_pgdp.dispatcher...` → `from pd_ocr_ops.gpu.dispatcher...`
and each `from pd_prep_for_pgdp.adapters.gpu...` → `from pd_ocr_ops.gpu.types...`
(or the test-local fake equivalent).

Run: `uv run pytest tests/gpu/test_dispatcher_immediate.py tests/gpu/test_dispatcher_batched.py tests/gpu/test_dispatcher_batched_loop.py -v`
Expected: all fail with `ModuleNotFoundError: No module named 'pd_ocr_ops.gpu.dispatcher'`.

- [ ] **Step 4: Create `pd_ocr_ops/gpu/dispatcher.py`**

Concatenate the three pgdp-prep dispatcher source files into one
pdomain-ocr-ops module (since their combined size is small enough — ~154 lines
— that a single file is easier to maintain than a sub-package).
Rewrite imports as in Step 3. Module docstring:

```python
"""Short-task dispatcher Protocol + Immediate/Batched implementations.

Two dispatcher shapes for short, sync-ish stage calls:

- :class:`ImmediateDispatcher` — local/self-hosted; submitted items run
  on the wrapped StageDispatcher straight away.
- :class:`BatchDispatcher` — managed-mode 5-min flush-window batching
  per spec §8 GPU dispatch (referencing pdomain-prep-for-pgdp
  ``specs/04-gpu-acceleration.md:327``). Amortises out-of-process
  cold starts across many pages.

Both implement :class:`IDispatcher`.

History: lifted verbatim from pdomain-prep-for-pgdp's ``dispatcher/`` package
in spec-§7 Phase 1.7 (2026-05-17). Originally shipped in pgdp-prep
because that was the only consumer at the time; lives here now so
trainer / simple-gui / future apps get the same batching primitive for
free.
"""
```

Body: the contents of pgdp-prep's `base.py`, `immediate.py`, and
`batched.py`, in that order, with imports consolidated at the top and
the `..adapters.gpu` import replaced with `.types`.

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/gpu/test_dispatcher_immediate.py tests/gpu/test_dispatcher_batched.py tests/gpu/test_dispatcher_batched_loop.py -v`
Expected: all pass with the same counts as pgdp-prep's pre-migration runs
(captured in Task 3's baseline output).

If `pd_ocr_ops.gpu.types` is too stubbed for the dispatcher tests to
import their fake-backend fixtures, do the type-move now (advance Task 6
into this task) rather than ship a half-stubbed types module.

- [ ] **Step 6: Update `pd_ocr_ops/gpu/__init__.py` re-exports**

Add `BatchDispatcher`, `IDispatcher`, `ImmediateDispatcher` to the
module's re-export block and `__all__`.

- [ ] **Step 7: Commit (pdomain-ocr-ops side)**

```bash
git add pd_ocr_ops/gpu/dispatcher.py pd_ocr_ops/gpu/types.py pd_ocr_ops/gpu/__init__.py tests/gpu/test_dispatcher_*.py
git commit -m "$(cat <<'EOF'
feat(gpu): add IDispatcher + Immediate/Batch implementations

Lifted from pdomain-prep-for-pgdp dispatcher/ package; BatchDispatcher is
the 5-min flush-window batching primitive the spec names at
specs/04-gpu-acceleration.md:327. Tests copied verbatim from
pgdp-prep — they're pure behavior tests with no pgdp-prep coupling.

Cherry-picked-from: pdomain-prep-for-pgdp@<sha capture from
git log --diff-filter=A --format=%H -- src/pd_prep_for_pgdp/dispatcher/>
EOF
)"
```

---

## Task 6: Move request/response types into `pd_ocr_ops/gpu/types.py` {#move-requestresponse-types-into-pdocropsgputypespy}

**Files (pdomain-ocr-ops):**
- Modify: `pd_ocr_ops/gpu/types.py` (replace the Task 5 stub)
- Create: `tests/gpu/test_types.py` (if not already covered by dispatcher tests)

**Why:** `ProcessPageRequest`, `OcrPageRequest`, `BatchJobItem`, etc.,
are the **wire shapes** that every dispatcher (local / Modal /
shared-container) serializes across its boundary. The spec
(`§8 GPU dispatch`) calls the dispatcher Protocol `StageDispatcher` with
a `run_stage(stage_id, page_id, **kwargs) -> StageResult` shape; the
pgdp-prep existing code uses more specific request types
(`ProcessPageRequest`, `OcrPageRequest`). Both shapes need to coexist
during migration — the spec shape is the **new generic** future
dispatcher signature, while the pgdp-prep shapes are the **legacy
specific** ones that pgdp-prep still uses.

**What:** Move the wire-shape Pydantic models from
`pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/adapters/gpu/base.py` to
`pdomain-ocr-ops/pd_ocr_ops/gpu/types.py`. Replace the Task 5 stub. The
generic `StageDispatcher` Protocol from plan #5 stays unchanged (already
shipped); the legacy `GPUBackend` Protocol — which is the same shape
under a different name — gets re-exported as an alias for one release
cycle, with a deprecation comment pointing at `StageDispatcher`.

- [ ] **Step 1: Identify the move boundary**

In
`pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/adapters/gpu/base.py`, identify
the parts to move:
- `ProcessPageRequest`, `ProcessPageResponse`
- `OcrPageRequest`, `OcrPageResponse`
- `BatchJobItem`, `BatchJobResult`
- `BatchProgressCb` type alias
- `GPUBackend` Protocol
- `words_key_for()` and `load_words_from_storage()` helpers

The first six move cleanly. `words_key_for` / `load_words_from_storage`
import `OcrWord` from `pd_prep_for_pgdp.core.models` — that's
pgdp-prep-specific OCR-artifact glue, **not** a GPU dispatch concern, so
those two helpers **stay in pgdp-prep**. Move them to
`pd_prep_for_pgdp/core/ocr_artifacts.py` (or wherever an existing OCR-IO
module lives) in Task 9.

The `GPUBackend` Protocol's `name` Literal includes `"local"`, `"cpu"`,
`"mps"`, `"modal"`, `"shared_container"`. That's fine — the same Literal
shape is fine on the moved Protocol. The Protocol gets renamed in spirit
(it **is** the generic `StageDispatcher`) but for one release cycle we
keep both the new spec name (`StageDispatcher`, already defined in plan
#5) and the legacy alias (`GPUBackend`) exported.

- [ ] **Step 2: Write a deprecation-alias test**

Create `pdomain-ocr-ops/tests/gpu/test_gpubackend_alias.py`:

```python
"""Verify GPUBackend is a legacy alias for StageDispatcher.

During the §7 Phase 1.7 migration we accept both names; downstream
plans remove the legacy alias when pgdp-prep + any other consumer have
migrated their type annotations to StageDispatcher.
"""
from __future__ import annotations

from pd_ocr_ops.gpu import GPUBackend, StageDispatcher


def test_gpubackend_is_stagedispatcher_alias():
    assert GPUBackend is StageDispatcher or GPUBackend.__name__ == "GPUBackend"
    # Same Protocol shape — either re-export of the same class, or a
    # separate Protocol with identical members (acceptable during
    # the deprecation window).
```

Run: `uv run pytest tests/gpu/test_gpubackend_alias.py -v`
Expected: fails (no `GPUBackend` export yet).

- [ ] **Step 3: Replace the Task 5 stub with the real `types.py`**

Replace `pdomain-ocr-ops/pd_ocr_ops/gpu/types.py` with the moved wire-shape
models. Module docstring:

```python
"""Wire-shape models for short-task stage dispatch.

Pydantic models that cross the dispatcher boundary — same on every
backend (in-process local, Modal, shared-container). Reused as the
``/api/gpu/*`` route schemas by every app that mounts pdomain-ocr-ops's
GPU routes.

Generic Protocol: :class:`pd_ocr_ops.gpu.StageDispatcher` (from plan
#5). The legacy alias :class:`GPUBackend` (kept for one release cycle)
is the same Protocol shape under pdomain-prep-for-pgdp's original name.

History: lifted from
pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/adapters/gpu/base.py in spec-§7
Phase 1.7 (2026-05-17). The original module also contained two OCR
artifact helpers (``words_key_for``, ``load_words_from_storage``) that
were pgdp-prep-specific OCR-IO glue rather than dispatch shapes;
those stayed in pgdp-prep.
"""
```

Body: the moved `ApiModel`-based request/response models, the
`BatchProgressCb` type alias, and the `GPUBackend` Protocol (re-exported
as `StageDispatcher` for the migration window).

If `ApiModel` itself is pgdp-prep-specific (it lives in
`pd_prep_for_pgdp.core.models`), replicate it as a minimal
`pydantic.BaseModel` subclass in pdomain-ocr-ops or use `BaseModel` directly.
Check `pd_prep_for_pgdp.core.models.ApiModel` first — if it's a
thin wrapper (e.g., `populate_by_name=True`), inline the equivalent
ConfigDict in pdomain-ocr-ops rather than carrying the pgdp-prep base
class along.

- [ ] **Step 4: Re-export from `pd_ocr_ops/gpu/__init__.py`**

Add to the re-export block: `BatchJobItem`, `BatchJobResult`,
`BatchProgressCb`, `GPUBackend`, `OcrPageRequest`, `OcrPageResponse`,
`ProcessPageRequest`, `ProcessPageResponse`. Append all to `__all__`.

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/gpu/ -v`
Expected: every test in `tests/gpu/` passes, including the new alias
test and the dispatcher tests from Task 5 (which now have real types to
import instead of a stub).

- [ ] **Step 6: Commit (pdomain-ocr-ops side)**

```bash
git add pd_ocr_ops/gpu/types.py pd_ocr_ops/gpu/__init__.py tests/gpu/test_gpubackend_alias.py
git commit -m "$(cat <<'EOF'
feat(gpu): move request/response types from pdomain-prep-for-pgdp

Lifts ProcessPageRequest, OcrPageRequest, BatchJobItem, BatchJobResult,
BatchProgressCb, and the GPUBackend Protocol from
pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/adapters/gpu/base.py. GPUBackend
re-exported as an alias for StageDispatcher (the spec §8 name) for the
one-release-cycle deprecation window.

OCR-IO helpers (words_key_for, load_words_from_storage) stay in
pgdp-prep — they're project-artifact glue, not dispatch shapes.

Cherry-picked-from: pdomain-prep-for-pgdp@<sha from
git log --diff-filter=A --format=%H -- src/pd_prep_for_pgdp/adapters/gpu/base.py>
EOF
)"
```

---

## Task 7: Move `ModalBackend` and the Modal app definition into pdomain-ocr-ops {#move-modalbackend-and-the-modal-app-definition-int}

**Files (pdomain-ocr-ops):**
- Create: `pd_ocr_ops/gpu/modal_dispatcher.py`
- Create: `pd_ocr_ops/gpu/modal_app.py`
- Create: `tests/gpu/test_modal_dispatcher.py`
- Create: `tests/gpu/test_modal_app_import.py`
- Modify: `pyproject.toml` (add `[project.optional-dependencies] modal = ["modal>=0.66"]`)

**Why:** The 5-min flush-window batching pattern only pays off when
there's an out-of-process backend whose cold start is worth amortising.
`ModalBackend` (paired with `modal_app.py`) is that backend in pgdp-prep
today, and the spec names Modal as the canonical hosted/managed-mode
short-task dispatcher (`§8 GPU dispatch`: `ModalStageDispatcher`).
Moving it to pdomain-ocr-ops makes it available to every app without each
maintaining its own Modal scaffolding.

**What:** Copy `modal_backend.py` (the client) and `modal_app.py` (the
Modal Function definitions) from pgdp-prep, renaming `ModalBackend` to
`ModalStageDispatcher` (the spec name) while keeping a `ModalBackend =
ModalStageDispatcher` alias for the deprecation window. The Modal-app
file's stub function bodies stay as scaffolds (matching today's
`NotImplementedError` placeholders) — wiring real function bodies is out
of scope for this migration.

- [ ] **Step 1: Inspect the existing pgdp-prep Modal code**

Read:
- `pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/adapters/gpu/modal_backend.py` (119 lines)
- `pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/adapters/gpu/modal_app.py` (89 lines)
- `pdomain-prep-for-pgdp/tests/test_modal_backend.py` (153 lines)
- `pdomain-prep-for-pgdp/tests/test_modal_app_import.py` (55 lines)

Note: `modal_app.py` references `pd_prep_for_pgdp.adapters.gpu.base` in
its `run_batch` placeholder. That import rewrites to
`pd_ocr_ops.gpu.types` in the moved file.

Note: the `APP_NAME = "pgdp-prep"` constant in `ModalBackend` is the
deployed Modal app name. In pdomain-ocr-ops the **default** app name becomes
something generic (`"pdomain-ocr-ops"` or configurable via constructor arg);
the actual deployed app name in any consumer is overridable so pgdp-prep
can keep its existing `"pgdp-prep"` deployment alive. Add a
`app_name: str = "pdomain-ocr-ops"` constructor arg to `ModalStageDispatcher`
that defaults to the generic name; pgdp-prep passes `app_name="pgdp-prep"`
at instantiation time (Task 9).

- [ ] **Step 2: Write the failing tests (copy + adapt from pgdp-prep)**

Copy `tests/test_modal_backend.py` and `tests/test_modal_app_import.py`
from pgdp-prep to `pdomain-ocr-ops/tests/gpu/test_modal_dispatcher.py` and
`tests/gpu/test_modal_app_import.py`. Rewrite imports
(`pd_prep_for_pgdp.adapters.gpu...` → `pd_ocr_ops.gpu...`). Rename
`ModalBackend` references to `ModalStageDispatcher` in the new test
file's assertions. Keep one regression test that imports the legacy
`ModalBackend` alias to verify the deprecation alias works.

Run: `uv run pytest tests/gpu/test_modal_dispatcher.py tests/gpu/test_modal_app_import.py -v`
Expected: all fail (modules don't exist yet).

- [ ] **Step 3: Add `[modal]` extra to pdomain-ocr-ops pyproject**

In `pdomain-ocr-ops/pyproject.toml`, under `[project.optional-dependencies]`,
add:

```toml
modal = [
    "modal>=0.66",
]
```

If `[project.optional-dependencies]` doesn't exist yet (pdomain-ocr-ops is
new), add the whole block.

- [ ] **Step 4: Create `pd_ocr_ops/gpu/modal_dispatcher.py`**

Copy `pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/adapters/gpu/modal_backend.py`
content with these rewrites:
- Module docstring: rewrite to name pdomain-ocr-ops as the home; preserve the
  "Two pieces: Modal app + ModalBackend client" structure but reference
  `modal_app.py` next to this file in pdomain-ocr-ops.
- Class `ModalBackend` → `ModalStageDispatcher`. Add a constructor
  parameter `app_name: str = "pdomain-ocr-ops"` and replace the class-level
  `APP_NAME = "pgdp-prep"` with `self._app_name = app_name`. Threads
  through `_load_function` to `Function.lookup(self._app_name, fn_name)`.
- Append at module bottom (after the class definition):

  ```python
  # Deprecation alias — pgdp-prep's pre-migration name. Re-pin and
  # rename at consumer-side over the next release cycle, then drop
  # this alias.
  ModalBackend = ModalStageDispatcher
  ```
- Imports: `from .types import (...)` instead of `from .base import (...)`.

Append a `Cherry-picked-from:` trailer in the future commit message.

- [ ] **Step 5: Create `pd_ocr_ops/gpu/modal_app.py`**

Copy `pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/adapters/gpu/modal_app.py`
with these rewrites:
- Module docstring: replace pgdp-prep references with pdomain-ocr-ops; deploy
  command becomes `modal deploy
  src/pd_ocr_ops/gpu/modal_app.py`. Note that any consuming app can
  *override* the Modal app name by deploying its own copy of this file
  with the app name swapped.
- `app = modal.App("pgdp-prep", image=image)` → `app = modal.App("pdomain-ocr-ops", image=image)`.
- The `.add_local_python_source("pd_prep_for_pgdp")` line → `.add_local_python_source("pd_ocr_ops")`.
- Inside the `run_batch` function body: `from
  pd_prep_for_pgdp.adapters.gpu.base import BatchJobItem, BatchJobResult`
  → `from pd_ocr_ops.gpu.types import BatchJobItem, BatchJobResult`.
- Function bodies stay as `NotImplementedError` scaffolds — exactly as
  today. Wiring real S3 storage into the Modal functions is out of
  scope for this migration.

- [ ] **Step 6: Re-export from `pd_ocr_ops/gpu/__init__.py`**

Add to the re-export block + `__all__`:

```python
from .modal_dispatcher import ModalBackend, ModalStageDispatcher
```

The `modal` import inside `modal_dispatcher.py` is already lazy
(matches the existing pgdp-prep code), so the re-export doesn't force
the `modal` package as a hard runtime dep.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run pytest tests/gpu/test_modal_dispatcher.py tests/gpu/test_modal_app_import.py -v`
Expected: all pass with the same counts as pgdp-prep's pre-migration
runs.

- [ ] **Step 8: Commit (pdomain-ocr-ops side)**

```bash
git add pd_ocr_ops/gpu/modal_dispatcher.py pd_ocr_ops/gpu/modal_app.py pd_ocr_ops/gpu/__init__.py tests/gpu/test_modal_dispatcher.py tests/gpu/test_modal_app_import.py pyproject.toml
git commit -m "$(cat <<'EOF'
feat(gpu): move ModalBackend + Modal app definitions into pdomain-ocr-ops

Lifted ModalBackend client (renamed to ModalStageDispatcher per spec
§8) and the paired modal_app.py Function definitions from
pdomain-prep-for-pgdp. Default Modal app name becomes "pdomain-ocr-ops"; the
new app_name= constructor arg lets pgdp-prep keep its existing
"pgdp-prep" deployment alive without re-deploying anything.

ModalBackend retained as a deprecation alias for one release cycle;
drop in a later cleanup chore.

Adds [modal] optional dep group to pyproject.toml (pinned modal>=0.66,
matching pgdp-prep).

Cherry-picked-from: pdomain-prep-for-pgdp@<sha>
EOF
)"
```

---

## Task 8: Move `SharedContainerBackend` into pdomain-ocr-ops {#move-sharedcontainerbackend-into-pdomain-ocr-ops}

**Files (pdomain-ocr-ops):**
- Create: `pd_ocr_ops/gpu/shared_container_dispatcher.py`
- Create: `tests/gpu/test_shared_container_dispatcher.py` (smoke-test only — pgdp-prep doesn't have one)

**Why:** Symmetric reason to Task 7 — pdomain-ocr-ops is the canonical home
for every short-task dispatcher implementation. `SharedContainerBackend`
is currently a 44-line stub in pgdp-prep with `NotImplementedError`
method bodies; the move is mechanical.

**What:** Copy `shared_container.py` from pgdp-prep, rename
`SharedContainerBackend` to `SharedContainerStageDispatcher` (with a
legacy alias), rewrite imports, and add a minimal import-smoke test
since pgdp-prep didn't carry one.

- [ ] **Step 1: Inspect the source**

Read
`pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/adapters/gpu/shared_container.py`
(44 lines). It's a stub — three methods, all `NotImplementedError`. No
real HTTP wiring yet.

- [ ] **Step 2: Write the smoke test**

Create `pdomain-ocr-ops/tests/gpu/test_shared_container_dispatcher.py`:

```python
"""Smoke tests for SharedContainerStageDispatcher import + Protocol shape.

The pgdp-prep source is a stub (NotImplementedError on every method);
real HTTP wiring is deferred to a follow-up plan. This test only
verifies the class imports, instantiates, and has the right
StageDispatcher-shaped methods.
"""
from __future__ import annotations

import pytest

from pd_ocr_ops.gpu import (
    SharedContainerBackend,
    SharedContainerStageDispatcher,
    StageDispatcher,
)


def test_legacy_alias_points_at_new_class():
    assert SharedContainerBackend is SharedContainerStageDispatcher


def test_instantiates_with_base_url_and_api_key():
    d = SharedContainerStageDispatcher("https://gpu.example.com", "secret-key")
    assert d.name == "shared_container"


def test_methods_raise_not_implemented_until_wired():
    # Mirrors today's pgdp-prep state. Replace with real assertions when
    # the HTTP client is wired in a follow-up plan.
    import asyncio

    from pd_ocr_ops.gpu.types import ProcessPageRequest

    d = SharedContainerStageDispatcher("https://gpu.example.com", "k")
    # Build a minimal valid request — adapt to whatever the
    # ProcessPageRequest fixture in tests/gpu/conftest.py provides.
    with pytest.raises(NotImplementedError):
        asyncio.run(d.process_page(ProcessPageRequest.model_construct()))
```

Run: `uv run pytest tests/gpu/test_shared_container_dispatcher.py -v`
Expected: fails (module doesn't exist).

- [ ] **Step 3: Create `pd_ocr_ops/gpu/shared_container_dispatcher.py`**

Copy `pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/adapters/gpu/shared_container.py`
with these rewrites:
- Module docstring: replace pgdp-prep references; note the file is a
  stub awaiting HTTP wiring in a follow-up plan.
- `from .base import (...)` → `from .types import (...)`.
- Class `SharedContainerBackend` → `SharedContainerStageDispatcher`.
- Append: `SharedContainerBackend = SharedContainerStageDispatcher`
  (deprecation alias).

- [ ] **Step 4: Re-export from `pd_ocr_ops/gpu/__init__.py`**

Add `SharedContainerBackend, SharedContainerStageDispatcher` to the
re-export block + `__all__`.

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/gpu/test_shared_container_dispatcher.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit (pdomain-ocr-ops side)**

```bash
git add pd_ocr_ops/gpu/shared_container_dispatcher.py pd_ocr_ops/gpu/__init__.py tests/gpu/test_shared_container_dispatcher.py
git commit -m "$(cat <<'EOF'
feat(gpu): move SharedContainerBackend into pdomain-ocr-ops

Lifted as-is from pdomain-prep-for-pgdp; renamed
SharedContainerBackend → SharedContainerStageDispatcher per spec §8.
SharedContainerBackend retained as deprecation alias for one release
cycle. Methods stay as NotImplementedError stubs — HTTP wiring is a
separate follow-up plan, not part of this migration.

Cherry-picked-from: pdomain-prep-for-pgdp@<sha>
EOF
)"
```

---

## Task 9: Env-var rename — `PGDP_GPU_BACKEND` → `PD_GPU_BACKEND` with deprecation alias {#env-var-rename-pgdpgpubackend-pdgpubackend-with-de}

**Files (pdomain-prep-for-pgdp):**
- Modify: `src/pd_prep_for_pgdp/settings.py`
- Create: `tests/test_settings_env_var_alias.py`

**Why:** Spec §7 Phase 1.7 specifies the env-var rename. The `PD_*`
prefix matches the cross-cut naming convention (every other workspace
env var is migrating to `PD_*`); the old `PGDP_GPU_BACKEND` keeps
working for one release cycle so users with deployment scripts or
docker-compose files don't break overnight.

**What:** Use pydantic-settings' `AliasChoices` to bind the
`Settings.gpu_backend` field to both env-var names, with a custom
validator that emits a `DeprecationWarning` when the value came from
the legacy `PGDP_GPU_BACKEND` name. Other `PGDP_*` env vars stay as-is
— only the GPU backend selector is in scope for this rename.

- [ ] **Step 1: Write the failing test**

Create `pdomain-prep-for-pgdp/tests/test_settings_env_var_alias.py`:

```python
"""Tests for PGDP_GPU_BACKEND → PD_GPU_BACKEND env-var alias.

§7 Phase 1.7 renames the GPU backend selector to the cross-cut PD_*
prefix; the old name keeps working for one release cycle and emits a
DeprecationWarning.
"""
from __future__ import annotations

import warnings

import pytest

from pd_prep_for_pgdp.settings import Settings


def test_new_env_var_pd_gpu_backend_is_read(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("PGDP_GPU_BACKEND", raising=False)
    monkeypatch.setenv("PD_GPU_BACKEND", "cpu")
    s = Settings()
    assert s.gpu_backend == "cpu"


def test_legacy_env_var_pgdp_gpu_backend_still_works(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("PD_GPU_BACKEND", raising=False)
    monkeypatch.setenv("PGDP_GPU_BACKEND", "cpu")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        s = Settings()
    assert s.gpu_backend == "cpu"
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert any("PGDP_GPU_BACKEND" in str(w.message) for w in deprecations), (
        f"expected a DeprecationWarning naming PGDP_GPU_BACKEND, got: {[str(w.message) for w in deprecations]}"
    )


def test_new_env_var_wins_when_both_set(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PD_GPU_BACKEND", "cpu")
    monkeypatch.setenv("PGDP_GPU_BACKEND", "modal")
    s = Settings()
    assert s.gpu_backend == "cpu"


def test_no_warning_when_only_new_var_set(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("PGDP_GPU_BACKEND", raising=False)
    monkeypatch.setenv("PD_GPU_BACKEND", "cpu")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Settings()
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert not deprecations, f"unexpected DeprecationWarning(s): {deprecations}"


def test_no_warning_when_neither_var_set(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("PD_GPU_BACKEND", raising=False)
    monkeypatch.delenv("PGDP_GPU_BACKEND", raising=False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Settings()
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert not deprecations
```

Run: `uv run pytest tests/test_settings_env_var_alias.py -v`
Expected: all 5 tests fail — the field currently binds only to
`PGDP_GPU_BACKEND`, so the `PD_GPU_BACKEND` read tests fail outright;
the deprecation-warning test fails because there is no warning emission
today.

- [ ] **Step 2: Update `Settings.gpu_backend` to accept both names**

Edit `pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/settings.py`. Replace the
`gpu_backend: GpuBackend | None = None` line with an `AliasChoices`
binding plus a validator. Add at the top of the file:

```python
import os
import warnings

from pydantic import AliasChoices, Field, model_validator
```

(`Field` and `model_validator` may already be imported; just additive.)

Replace the field:

```python
    gpu_backend: GpuBackend | None = Field(
        default=None,
        validation_alias=AliasChoices("PD_GPU_BACKEND", "PGDP_GPU_BACKEND"),
    )
    """When None, auto-detect at startup (CUDA → local, mac arm64 → mps, else cpu).

    Env var: ``PD_GPU_BACKEND``. The legacy ``PGDP_GPU_BACKEND`` name is
    still honored for one release cycle and emits a DeprecationWarning;
    if both are set, ``PD_GPU_BACKEND`` wins.
    """
```

Note: with `AliasChoices`, the **first** entry wins when both are set —
hence `PD_GPU_BACKEND` first. The `env_prefix="PGDP_"` setting on the
`SettingsConfigDict` would otherwise auto-bind to `PGDP_GPU_BACKEND`;
the explicit `validation_alias` overrides that auto-binding.

Add a `model_validator` (after the field declarations) that emits the
deprecation warning by checking `os.environ` directly. We have to read
env at validator time because pydantic-settings doesn't surface which
alias hit:

```python
    @model_validator(mode="after")
    def _warn_on_legacy_gpu_backend_env(self) -> "Settings":
        # Only warn when the legacy var is set AND the new var is not —
        # if both are set, the new var won and the user has already
        # migrated; no point nagging.
        if "PGDP_GPU_BACKEND" in os.environ and "PD_GPU_BACKEND" not in os.environ:
            warnings.warn(
                "PGDP_GPU_BACKEND is deprecated; rename to PD_GPU_BACKEND "
                "(this alias will be removed in a future pdomain-prep-for-pgdp "
                "release).",
                DeprecationWarning,
                stacklevel=2,
            )
        return self
```

- [ ] **Step 3: Run the test to verify it passes**

Run: `uv run pytest tests/test_settings_env_var_alias.py -v`
Expected: 5 passed.

- [ ] **Step 4: Run the existing settings-related tests as a regression check**

Run: `uv run pytest tests/ -k settings -v 2>&1 | tail -20`
Expected: no regressions. Any test that explicitly sets
`PGDP_GPU_BACKEND` will now see the deprecation warning — that's
expected; only fail if a test was asserting absence-of-warning.

- [ ] **Step 5: Commit (pgdp-prep side)**

```bash
git add src/pd_prep_for_pgdp/settings.py tests/test_settings_env_var_alias.py
git commit -m "$(cat <<'EOF'
feat(settings): accept PD_GPU_BACKEND with PGDP_GPU_BACKEND deprecation alias

Spec §7 Phase 1.7 renames the GPU backend selector to the cross-cut
PD_* prefix. PGDP_GPU_BACKEND still works for one release cycle and
emits a DeprecationWarning when used; if both vars are set, the new
PD_GPU_BACKEND name wins.

Only the GPU backend env var is in scope for this rename — other
PGDP_* env vars stay as-is.
EOF
)"
```

---

## Task 10: Re-point pgdp-prep imports at pdomain-ocr-ops {#re-point-pgdp-prep-imports-at-pdomain-ocr-ops}

**Files (pdomain-prep-for-pgdp):**
- Modify: `pyproject.toml` (add `pdomain-ocr-ops>=0.2,<0.3` to `dependencies`)
- Modify: `src/pd_prep_for_pgdp/bootstrap.py`
- Modify: `src/pd_prep_for_pgdp/api/dependencies.py`
- Modify: `src/pd_prep_for_pgdp/api/healthz.py`
- Modify: `src/pd_prep_for_pgdp/api/gpu/*.py` (illustrations, ingest, jobs, schemas)
- Modify: `src/pd_prep_for_pgdp/core/pipeline/stage_registry.py` (replace plumbing with import + registration)
- Delete: `src/pd_prep_for_pgdp/adapters/gpu/base.py`
- Delete: `src/pd_prep_for_pgdp/adapters/gpu/modal_backend.py`
- Delete: `src/pd_prep_for_pgdp/adapters/gpu/modal_app.py`
- Delete: `src/pd_prep_for_pgdp/adapters/gpu/shared_container.py`
- Delete: `src/pd_prep_for_pgdp/dispatcher/base.py`
- Delete: `src/pd_prep_for_pgdp/dispatcher/batched.py`
- Delete: `src/pd_prep_for_pgdp/dispatcher/immediate.py`
- Modify: `src/pd_prep_for_pgdp/adapters/gpu/__init__.py` (re-export from pdomain-ocr-ops for back-compat)
- Modify: `src/pd_prep_for_pgdp/dispatcher/__init__.py` (re-export from pdomain-ocr-ops for back-compat)
- Delete (later — see Task 13): the inventory file scaffolding

**Why:** Once pdomain-ocr-ops has the canonical implementations (Tasks 4–8),
the pgdp-prep copies are dead weight. Deleting them and re-pointing
imports is the heart of the migration. The local `__init__.py` files
become thin re-exports so any out-of-tree consumer that imported the
old paths still works for the deprecation window.

**What:** This is the most surgical task in the plan. Do it in **import
sweeps**, not file-by-file — sweep each symbol cluster across all
consumers in one pass, then move on to the next cluster. The test net
captured in Task 1 is the safety net.

- [ ] **Step 1: Add pdomain-ocr-ops as a pgdp-prep dependency**

In `pdomain-prep-for-pgdp/pyproject.toml`, under `[project].dependencies`,
add (sorted alphabetically — between `pdomain-book-tools` and `pydantic`):

```toml
    "pdomain-ocr-ops>=0.2,<0.3",
```

If pdomain-ocr-ops is published through `pdomain-index-pip`, also confirm the
`[tool.uv.sources]` or `[[tool.uv.index]]` block points at the right
index URL — pdomain-ocr-ops at this point is not a public PyPI package.
(This is the pin to **0.2.x**, anticipating the version bump in Task
12. If 0.1.x is installed today via plan #5's release, the pin will be
re-evaluated after Task 12 ships the 0.2.0 release of pdomain-ocr-ops.)

Run: `uv sync`
Expected: lockfile updated; pdomain-ocr-ops appears.

- [ ] **Step 2: Sweep dispatcher imports**

Search:

```sh
grep -rn "from pd_prep_for_pgdp.dispatcher\|from \.dispatcher\|from ..dispatcher" src/ tests/
```

Rewrite every match: `pd_prep_for_pgdp.dispatcher` (or the relative
equivalent) → `pd_ocr_ops.gpu`. Same symbol names — `BatchDispatcher`,
`IDispatcher`, `ImmediateDispatcher` — so the only edit is the
module path.

Replace `pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/dispatcher/__init__.py`
with a back-compat shim:

```python
"""Deprecated — dispatchers now live in pd_ocr_ops.gpu.

This shim re-exports for one release cycle. Update imports to
``from pd_ocr_ops.gpu import BatchDispatcher, IDispatcher, ImmediateDispatcher``
to silence the DeprecationWarning.
"""
from __future__ import annotations

import warnings

from pd_ocr_ops.gpu import BatchDispatcher, IDispatcher, ImmediateDispatcher

warnings.warn(
    "pd_prep_for_pgdp.dispatcher is deprecated; import from pd_ocr_ops.gpu instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["BatchDispatcher", "IDispatcher", "ImmediateDispatcher"]
```

Delete `src/pd_prep_for_pgdp/dispatcher/base.py`,
`dispatcher/batched.py`, `dispatcher/immediate.py`.

- [ ] **Step 3: Sweep GPU backend imports**

Search:

```sh
grep -rn "from pd_prep_for_pgdp.adapters.gpu\|from \.adapters.gpu\|from ..adapters.gpu" src/ tests/
```

Rewrite every match — module path → `pd_ocr_ops.gpu`. Symbols stay the
same (`GPUBackend`, `ModalBackend`, `SharedContainerBackend`,
`ProcessPageRequest`, etc.) thanks to the deprecation aliases in pdomain-ocr-ops.

Special cases:
- `words_key_for` and `load_words_from_storage` did NOT move to
  pdomain-ocr-ops (decision in Task 6). They stay accessible from
  pgdp-prep. Move their *file home* in pgdp-prep to
  `src/pd_prep_for_pgdp/core/ocr_artifacts.py` (or the nearest existing
  OCR-IO module) and update the small number of consumers that import
  them. They're not GPU dispatch surface.

Replace `pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/adapters/gpu/__init__.py`
with a back-compat shim:

```python
"""Deprecated — GPU dispatch primitives now live in pd_ocr_ops.gpu.

This shim re-exports for one release cycle. Update imports to
``from pd_ocr_ops.gpu import ...`` to silence the DeprecationWarning.
"""
from __future__ import annotations

import warnings

from pd_ocr_ops.gpu import (
    BatchJobItem,
    BatchJobResult,
    GPUBackend,
    OcrPageRequest,
    OcrPageResponse,
    ProcessPageRequest,
    ProcessPageResponse,
)

warnings.warn(
    "pd_prep_for_pgdp.adapters.gpu is deprecated; import from pd_ocr_ops.gpu instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "BatchJobItem",
    "BatchJobResult",
    "GPUBackend",
    "OcrPageRequest",
    "OcrPageResponse",
    "ProcessPageRequest",
    "ProcessPageResponse",
]
```

Delete `src/pd_prep_for_pgdp/adapters/gpu/base.py`,
`modal_backend.py`, `modal_app.py`, `shared_container.py`.

Update `src/pd_prep_for_pgdp/bootstrap.py`:
- `from .adapters.gpu.modal_backend import ModalBackend` → `from pd_ocr_ops.gpu import ModalStageDispatcher as ModalBackend` (kept name for grep stability).
- `from .adapters.gpu.shared_container import SharedContainerBackend` → `from pd_ocr_ops.gpu import SharedContainerStageDispatcher as SharedContainerBackend`.
- Pass `app_name="pgdp-prep"` to `ModalStageDispatcher` so the deployed Modal app keeps its existing name.

- [ ] **Step 4: Rewire the STAGE_IMPL registry inside pgdp-prep**

Edit `pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/core/pipeline/stage_registry.py`:

- Replace the `class StageNotImplemented`, `_make_placeholder`,
  `STAGE_IMPL = {}`, and `get_stage_impl` definitions with imports
  from pdomain-ocr-ops:

  ```python
  from pd_ocr_ops.gpu import (
      STAGE_IMPL,
      StageNotImplemented,
      get_stage_impl,
      register_stage_impl,
  )
  ```

- Replace the existing `_build_registry()` function with a
  `register_pgdp_stages()` function that walks every
  `_<stage_id>_cpu` callable and calls
  `register_stage_impl(stage_id, "cpu", impl)`.

- Add a module-bottom call site that runs `register_pgdp_stages()` at
  import time (preserving today's "import the registry, get the
  callables" behavior) — OR, prefer-explicit: invoke
  `register_pgdp_stages()` from `bootstrap.build_app()` so the
  registration order is visible in startup logs. Pick whichever matches
  pgdp-prep's existing convention; document the choice inline.

- Module docstring: prepend a "History" paragraph noting the registry
  plumbing now lives in pdomain-ocr-ops; this file keeps only pgdp-prep's
  per-stage callables and the registration call.

- [ ] **Step 5: Run the full pgdp-prep test suite**

Run: `make ci AI=1`
Expected: exit 0, same pytest passing count as Task 3's baseline (the
five new tests from Task 9 add to the count; nothing else should change).

If anything fails, **read the failure carefully**: the most likely
cause is a missed import rewrite (a sibling-relative `from ..gpu`
that the sweep grep missed). Re-run the Step 2/Step 3 greps after every
fix to confirm cleanliness.

- [ ] **Step 6: Commit (pgdp-prep side)**

```bash
git add pyproject.toml uv.lock src/pd_prep_for_pgdp/ tests/
git rm src/pd_prep_for_pgdp/adapters/gpu/base.py \
       src/pd_prep_for_pgdp/adapters/gpu/modal_backend.py \
       src/pd_prep_for_pgdp/adapters/gpu/modal_app.py \
       src/pd_prep_for_pgdp/adapters/gpu/shared_container.py \
       src/pd_prep_for_pgdp/dispatcher/base.py \
       src/pd_prep_for_pgdp/dispatcher/batched.py \
       src/pd_prep_for_pgdp/dispatcher/immediate.py
git commit -m "$(cat <<'EOF'
refactor(gpu): re-point GPU dispatch imports at pdomain-ocr-ops

Spec §7 Phase 1.7 migration: pdomain-ocr-ops is now the canonical home for
STAGE_IMPL, the IDispatcher Protocol, ImmediateDispatcher,
BatchDispatcher, ModalStageDispatcher, and SharedContainerStageDispatcher.
pgdp-prep imports them from there.

Local pd_prep_for_pgdp.dispatcher and pd_prep_for_pgdp.adapters.gpu
become re-export shims for one release cycle so out-of-tree consumers
have a grace period; both emit DeprecationWarning on import.

stage_registry.py keeps pgdp-prep's per-stage _<stage_id>_cpu callables
and registers them against the relocated registry via
register_stage_impl(); the registry plumbing itself is gone from
pgdp-prep.

Adds pdomain-ocr-ops>=0.2,<0.3 as a runtime dep (pin re-evaluated when the
0.2.0 release lands in Task 12 of this plan).

Forward-link: see pdomain-ocr-ops commits cherry-picked from
pdomain-prep-for-pgdp@<this commit sha> for the moved code.
EOF
)"
```

---

## Task 11: Regression verification — both repos' CI green {#regression-verification-both-repos-ci-green}

**Why:** This is the load-bearing dual-CI step the plan-preamble called
out. If pgdp-prep's CI is green AND pdomain-ocr-ops's CI is green AND
pgdp-prep's test count matches Task 3's baseline (modulo the five new
env-var-alias tests from Task 9), the migration is functionally
equivalent.

**What:** Run `make ci AI=1` in **both** repos and compare against
baselines. Document any unexpected delta.

- [ ] **Step 1: pgdp-prep CI**

From `/workspaces/ocr-container/pdomain-prep-for-pgdp/`:

```sh
make ci AI=1 2>&1 | tail -20
```

Expected: exit 0, pytest summary `(N + 5) passed in M.MMs` where N is
Task 3's baseline number.

If the count is off by more than +5, investigate. The most likely
explanations:
- The test discovery picked up a deprecated `DeprecationWarning`
  through the `dispatcher/__init__.py` or `adapters/gpu/__init__.py`
  shim and `filterwarnings = ["error"]` in pytest config promoted it
  to an error — fix by tightening the warning filter to only-pgdp-prep.
- A test was implicitly relying on a now-deleted file path being
  importable as an attribute of the pgdp-prep namespace — fix by
  re-pointing the assertion at the new pdomain-ocr-ops path.

- [ ] **Step 2: pdomain-ocr-ops CI**

From `/workspaces/ocr-container/pdomain-ocr-ops/`:

```sh
make ci AI=1
```

Expected: exit 0. Test count = pre-migration pdomain-ocr-ops count + every
new test added across Tasks 4–8.

- [ ] **Step 3: Manual smoke test — `pgdp-prep` boots and serves**

From `/workspaces/ocr-container/pdomain-prep-for-pgdp/`:

```sh
make run-cpu
```

(Or whatever the `make` target is for "start the server with the CPU
backend." The cpu adapter is the no-extra-deps path and exercises every
import the migration touched.)

Expected: server starts, no Python import errors in the logs, GET
`http://127.0.0.1:8765/api/healthz` returns 200 with
`"gpu_backend": "cpu"`. Stop the server (`Ctrl-C`).

- [ ] **Step 4: Capture the post-migration baseline**

Append to `pdomain-prep-for-pgdp/docs/phase-1-7-inventory.md`:

```markdown
## CI POST-MIGRATION

- Date: <YYYY-MM-DD>
- pgdp-prep `make ci AI=1`: exit 0, `<N+5> passed`
- pdomain-ocr-ops `make ci AI=1`: exit 0, `<M> passed`
- Manual: `make run-cpu` boots, /api/healthz returns gpu_backend=cpu.
```

- [ ] **Step 5: Commit**

```bash
git add docs/phase-1-7-inventory.md
git commit -m "docs(phase-1-7): record post-migration CI baseline (both repos green)"
```

---

## Task 12: Bump pdomain-ocr-ops to 0.2.0 and publish to pdomain-index-pip {#bump-pdomain-ocr-ops-to-020-and-publish-to-pdomain-index-pip}

**Files (pdomain-ocr-ops):**
- Modify: `CHANGELOG.md` (or equivalent)
- Tag: `v0.2.0`

**Files (pdomain-prep-for-pgdp):**
- Modify: `pyproject.toml` (lift the upper bound or re-pin if the published wheel's SHA changed)

**Why:** The migration adds substantial new public surface to pdomain-ocr-ops
(STAGE_IMPL + 4 dispatcher classes + wire-shape types). That's a
**minor-version-worthy** addition by semver. Bumping to 0.2.0 and
publishing makes the new surface available to other consumers (future
trainer, future simple-gui) without forcing them onto pre-release pins.

**What:** Update pdomain-ocr-ops's changelog, bump the version, publish to
pdomain-index-pip per the workspace release strategy (the self-hosted PEP
503 index — see `project_release_strategy` in workspace memory). Then
re-pin pgdp-prep to the published version.

- [ ] **Step 1: Update pdomain-ocr-ops CHANGELOG**

Edit (or create) `pdomain-ocr-ops/CHANGELOG.md`. Add a `## 0.2.0 — <YYYY-MM-DD>`
section. Bullets:
- `Add STAGE_IMPL canonical registry (register_stage_impl / get_stage_impl / StageNotImplemented sentinel) — moved from pdomain-prep-for-pgdp.`
- `Add IDispatcher Protocol + ImmediateDispatcher + BatchDispatcher (5-min flush-window batching, spec §8 GPU dispatch) — moved from pdomain-prep-for-pgdp.`
- `Add ModalStageDispatcher + paired modal_app.py Function definitions, [modal] optional dep group — moved from pdomain-prep-for-pgdp.`
- `Add SharedContainerStageDispatcher (HTTP client stub) — moved from pdomain-prep-for-pgdp.`
- `Add wire-shape Pydantic models: ProcessPageRequest/Response, OcrPageRequest/Response, BatchJobItem/Result — moved from pdomain-prep-for-pgdp.`
- `Add legacy aliases: GPUBackend (= StageDispatcher), ModalBackend (= ModalStageDispatcher), SharedContainerBackend (= SharedContainerStageDispatcher). Aliases retained for one release cycle.`

- [ ] **Step 2: Bump version**

If pdomain-ocr-ops uses `hatch-vcs` (matches other pd-* repos), the version
is taken from the git tag — skip the `pyproject.toml` edit and tag
`v0.2.0` in Step 4. If it uses a static `version = "..."` in
`pyproject.toml`, bump it now.

- [ ] **Step 3: Final CI check before tagging**

Run: `make ci AI=1` in pdomain-ocr-ops.
Expected: green.

- [ ] **Step 4: Tag and publish**

```sh
git tag v0.2.0
git push origin v0.2.0
```

The release-automation hook (matches other pd-* repos — GitHub Actions
builds the wheel and uploads it to ConcaveTrillion/pd-index per the
workspace release strategy) publishes the wheel.

Verify the wheel is installable:

```sh
uv pip install --index-url <pdomain-index-pip URL> pdomain-ocr-ops==0.2.0
```

- [ ] **Step 5: Re-pin pgdp-prep**

If Task 10's pin (`pdomain-ocr-ops>=0.2,<0.3`) is already in
`pdomain-prep-for-pgdp/pyproject.toml`, no change needed — `uv lock --upgrade`
picks up 0.2.0 from the index. Otherwise, edit the dep to exactly
`pdomain-ocr-ops>=0.2,<0.3` now.

Run in pgdp-prep:

```sh
uv lock --upgrade-package pdomain-ocr-ops
make ci AI=1
```

Expected: lockfile updated to pin pdomain-ocr-ops==0.2.0; CI green.

- [ ] **Step 6: Commit**

In pdomain-ocr-ops:

```bash
git add CHANGELOG.md pyproject.toml
git commit -m "chore(release): pdomain-ocr-ops 0.2.0 — GPU dispatch migration from pdomain-prep-for-pgdp"
git tag v0.2.0 -m "0.2.0 — GPU dispatch (STAGE_IMPL + dispatchers + types) from pdomain-prep-for-pgdp"
```

In pgdp-prep:

```bash
git add pyproject.toml uv.lock
git commit -m "chore(deps): pin pdomain-ocr-ops>=0.2,<0.3 (consume migrated GPU dispatch surface)"
```

---

## Task 13: Delete inventory scaffolding {#delete-inventory-scaffolding}

**Why:** The inventory file (Task 1) and the post-migration baseline
notes (Tasks 3, 11) were scaffolding for the migration, not a permanent
artifact. Once the migration ships and both repos are green, delete it.
The history of *what moved where* lives in the commit messages and the
`Cherry-picked-from:` trailers — there's no need to carry the inventory
file forward.

- [ ] **Step 1: Delete the inventory file**

```sh
git rm pdomain-prep-for-pgdp/docs/phase-1-7-inventory.md
```

- [ ] **Step 2: Commit**

```bash
git commit -m "$(cat <<'EOF'
chore(phase-1-7): remove inventory scaffolding

Migration shipped (pdomain-ocr-ops 0.2.0); the inventory file was a
checklist for the migration, not a permanent artifact. Forward-history
of what-moved-where lives in the relevant commit messages and the
Cherry-picked-from trailers on pdomain-ocr-ops's gpu/ modules.
EOF
)"
```

---

## Self-review checklist (for the engineer; before declaring the migration done)

- [ ] `pdomain-ocr-ops` `make ci AI=1` is green.
- [ ] `pdomain-prep-for-pgdp` `make ci AI=1` is green AND test count is baseline + 5 (Task 9's new env-var tests).
- [ ] `pdomain-prep-for-pgdp` boots via `make run-cpu` and `/api/healthz`
      returns `gpu_backend: "cpu"`.
- [ ] No file under `pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/adapters/gpu/`
      except the `__init__.py` re-export shim.
- [ ] No file under `pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/dispatcher/`
      except the `__init__.py` re-export shim.
- [ ] `core/pipeline/stage_registry.py` does NOT define `STAGE_IMPL`,
      `StageNotImplemented`, `_make_placeholder`, or `get_stage_impl` —
      it imports them from `pd_ocr_ops.gpu`.
- [ ] `Settings.gpu_backend` reads from both `PD_GPU_BACKEND` (new
      canonical) and `PGDP_GPU_BACKEND` (deprecated alias);
      `PD_GPU_BACKEND` wins when both set; deprecation warning fires
      only when the legacy alone is used.
- [ ] `pdomain-ocr-ops` ships `0.2.0` to `pdomain-index-pip` and pgdp-prep's
      lockfile pins it.
- [ ] No `Cherry-picked-from:` trailer is missing a real SHA (placeholder
      angle-brackets all resolved during Tasks 4–8).
- [ ] Inventory file deleted (Task 13).

---

## Follow-up plans (not in scope here)

1. **Trainer-specific `LongJobRunner` variants.** The spec §8 GPU
   dispatch table names `ModalLongJobRunner` for "training runs, big
   synth runs — minutes to hours." That's a separate
   implementation — not the short-task `StageDispatcher` family this
   plan migrates. It belongs in its own plan once `pdomain-ocr-trainer-spa`
   (spec §7 Phase 3) starts.
2. **New GPU adapters.** Examples named in the spec:
   `K8sScaleLauncher` (sibling-launch adapter for hosted mode),
   per-tenant fairness-weighted dispatchers, etc. New adapters land in
   pdomain-ocr-ops as additive features — each gets its own plan.
3. **Wire real bodies into Modal app functions.** Today's
   `process_page`, `run_ocr`, `run_batch` Modal functions are
   `NotImplementedError` scaffolds. Real bodies need S3 storage wired
   into the Modal container and a per-stage dispatch through the
   relocated `STAGE_IMPL`. Out of scope for the migration; its own plan
   once a managed-mode deployment is actually wanted.
4. **Wire `SharedContainerStageDispatcher` HTTP client.** Same shape as
   #3 — the methods raise `NotImplementedError` today; wiring real
   HTTPX calls + the matching `/api/gpu/*` route handlers is a
   separate piece of work.
5. **Drop the deprecation aliases** (`PGDP_GPU_BACKEND` env var,
   `pd_prep_for_pgdp.dispatcher` shim, `pd_prep_for_pgdp.adapters.gpu`
   shim, `GPUBackend = StageDispatcher`, `ModalBackend =
   ModalStageDispatcher`, `SharedContainerBackend =
   SharedContainerStageDispatcher`). One-release-cycle chore — open
   the issue with a target version (e.g., pgdp-prep 0.next+1 /
   pdomain-ocr-ops 0.3) and grep for any out-of-tree consumers that still
   import the deprecated names before deleting.
6. **Rename other `PGDP_*` env vars to `PD_*`.** This plan only
   renamed the GPU backend selector. The rest of pgdp-prep's `PGDP_*`
   env vars (`PGDP_THUMBNAIL_WORKERS`, `PGDP_STAGE_WRITE_POOL_SIZE`,
   `PGDP_STAGE_WRITE_QUEUE_CAP`, etc.) keep their prefix for now; a
   sweep-rename is its own opt-in chore plan.
