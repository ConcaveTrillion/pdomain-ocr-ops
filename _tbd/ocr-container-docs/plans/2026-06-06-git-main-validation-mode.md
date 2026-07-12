# git-main Pre-Release Validation Mode — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a transient `make ci-against-main` to every pd-* Python repo that temporarily resolves its pd-* dependencies from each sibling's latest `master` on GitHub, runs the release preflight (`ci-slow`), then restores the tree — so we can catch "sibling master will break me once released" before cutting a release.

**Architecture:** A pure-Python source-rewriter (`scripts/git_main_sources.py`) flips `[tool.uv.sources]` pd-* entries from `{ index = "pdomain-index-pip" }` to `{ git = ".../<sib>.git", branch = "master" }`. A bash orchestrator (`scripts/ci-against-main.sh`) backs up `pyproject.toml`/`uv.lock`, applies the flip, runs `uv lock` (capturing each sibling's current master SHA → reproducible per run) + `uv sync`, runs the preflight, and restores both files via an `EXIT` trap (green or red). An opt-in `VALIDATE_AGAINST_MAIN=1` hook in the shared `release-common.sh` runs it before a release. Scope is **Python siblings only** — npm/`pdomain-ui` is explicitly out of scope.

**Tech Stack:** bash, Python 3.11+ (`re`, `tomllib` for validation), `uv`, GNU make, pytest.

**Scope (rollout set — 7 repos with pd-* siblings):** `pdomain-ops` (reference), `pdomain-ocr-simple-gui`, `pdomain-ocr-cli`, `pdomain-prep-for-pgdp`, `pdomain-ocr-labeler-spa`, `pdomain-ocr-trainer-spa`, `pdomain-ocr-training`. Excluded (no pd-* siblings): `pdomain-ocr-synth`, `pdomain-book-tools`.

---

## Execution orchestration (how to run this plan)

- **Milestone 0** (reference impl in `pdomain-ops`) is **sequential, TDD** — it produces the canonical script + transform + tests + release hook, validated end-to-end.
- **Milestone 1** (rollout to the other 6 repos) is **fully PARALLEL** — one fresh subagent per repo (`model: sonnet`, `isolation: "worktree"`), each copying the canonical files and self-determining `PY_SIBLINGS` from its own `[tool.uv.sources]`.
- **Reviews are independent fresh subagents, not the implementer:**
  - **Per-task review** after each implementation task (Milestone 0 tasks, and each Milestone 1 repo): a separate `model: sonnet` reviewer checks the diff against the five gates below and returns `APPROVE` or `REQUEST-CHANGES` + findings. Implementer fixes; re-review until APPROVE.
  - **End-of-plan review** (Milestone 3): a holistic independent reviewer across all 7 repos.
- **The five review gates (every review):** (1) **Security** — no injection via sibling/owner config, git URLs pinned to the `pdomain` org, restore cannot clobber unrelated work, no arbitrary-code surprises beyond our own repos' normal build; (2) **Correctness** — flip is exact, lock captures main SHAs, trap restores on both success and failure with the preflight's exit code preserved; (3) **Simplicity** — no needless abstraction, reuses existing patterns; (4) **Common style** — matches sibling `scripts/*.sh` + Makefile idioms (header comments, `##` help text, `set -euo pipefail`); (5) **NO DEFERRED WORK** — zero `TODO`/`later`/stubbed branches; every repo in scope is fully done and its `make ci-against-main` actually runs green.

---

## File structure (per repo)

- Create: `scripts/git_main_sources.py` — pure transform: rewrite `[tool.uv.sources]` pd-* entries to git+master. No side effects beyond writing the target file when run as `__main__`.
- Create: `scripts/ci-against-main.sh` — orchestrator: guard → backup → flip → `uv lock`/`sync` → preflight → restore (trap).
- Create: `tests/test_git_main_sources.py` — unit tests for the transform.
- Modify: `Makefile` — add the `ci-against-main` target.
- Modify: `scripts/release-common.sh` — add the `VALIDATE_AGAINST_MAIN=1` pre-release hook.
- Modify (workspace, once): `docs/process/local-dev.md` + new `docs/process/ci-against-main.md`.

---

## Milestone 0 — Reference implementation (`pdomain-ops`, sequential TDD)

Reference repo: `/workspaces/ocr-container/pdomain-ops`. Its only pd-* sibling is `pdomain-book-tools`, it has no frontend, and `ci-slow` is fast — ideal to prove the mechanism.

### Task 1: Pure source-rewriter + unit tests

**Files:**
- Create: `scripts/git_main_sources.py`
- Test: `tests/test_git_main_sources.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_git_main_sources.py
"""Unit tests for the git-main [tool.uv.sources] rewriter."""
from __future__ import annotations

import pytest

from scripts.git_main_sources import flip_sources

_SRC = """\
[tool.uv.sources]
pdomain-book-tools = { index = "pdomain-index-pip" }
pdomain-ops = { index = "pdomain-index-pip" }
some-other = { index = "elsewhere" }
"""


def test_flip_single_sibling_to_git_main() -> None:
    out = flip_sources(_SRC, "pdomain", ["pdomain-book-tools"])
    assert (
        'pdomain-book-tools = { git = "https://github.com/pdomain/pdomain-book-tools.git", branch = "master" }'
        in out
    )
    # the flipped entry no longer points at the registry index
    assert 'pdomain-book-tools = { index' not in out


def test_flip_leaves_other_entries_untouched() -> None:
    out = flip_sources(_SRC, "pdomain", ["pdomain-book-tools"])
    assert 'pdomain-ops = { index = "pdomain-index-pip" }' in out
    assert 'some-other = { index = "elsewhere" }' in out


def test_flip_multiple_siblings() -> None:
    out = flip_sources(_SRC, "pdomain", ["pdomain-book-tools", "pdomain-ops"])
    assert 'pdomain-book-tools = { git = "https://github.com/pdomain/pdomain-book-tools.git", branch = "master" }' in out
    assert 'pdomain-ops = { git = "https://github.com/pdomain/pdomain-ops.git", branch = "master" }' in out


def test_missing_sibling_entry_raises() -> None:
    with pytest.raises(ValueError, match="no \\[tool.uv.sources\\] entry"):
        flip_sources(_SRC, "pdomain", ["pdomain-not-present"])


def test_result_is_valid_toml() -> None:
    import tomllib

    out = flip_sources(_SRC, "pdomain", ["pdomain-book-tools", "pdomain-ops"])
    parsed = tomllib.loads(out)
    src = parsed["tool"]["uv"]["sources"]["pdomain-book-tools"]
    assert src == {"git": "https://github.com/pdomain/pdomain-book-tools.git", "branch": "master"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /workspaces/ocr-container/pdomain-ops && uv run pytest tests/test_git_main_sources.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.git_main_sources'`

- [ ] **Step 3: Implement the rewriter**

```python
# scripts/git_main_sources.py
#!/usr/bin/env python3
"""Flip pd-* ``[tool.uv.sources]`` entries to each sibling's git ``main``.

Transient helper for ``ci-against-main.sh``. Pure text transform so it is
unit-testable; the orchestrator backs up and restores the file, so this never
needs to preserve formatting beyond producing valid TOML.
"""
from __future__ import annotations

import re
import sys
import tomllib


def flip_sources(text: str, owner: str, siblings: list[str]) -> str:
    """Return *text* with each sibling's uv source rewritten to git ``main``.

    Args:
        text: Full ``pyproject.toml`` contents.
        owner: GitHub org/owner (e.g. ``"pdomain"``).
        siblings: pd-* package names whose ``[tool.uv.sources]`` entry should
            be flipped from a registry index to ``{ git = ..., branch = "master" }``.

    Raises:
        ValueError: if a requested sibling has no ``[tool.uv.sources]`` entry.
    """
    for sib in siblings:
        # Match a single-line table entry: `name = { ... }` (entries in this
        # codebase are always one-line index pins).
        pattern = re.compile(
            rf"(?m)^{re.escape(sib)}\s*=\s*\{{[^}}]*\}}\s*$"
        )
        replacement = (
            f'{sib} = {{ git = "https://github.com/{owner}/{sib}.git", '
            f'branch = "master" }}'
        )
        text, count = pattern.subn(replacement, text)
        if count == 0:
            raise ValueError(
                f"no [tool.uv.sources] entry found for {sib!r} to flip"
            )
    # Fail loudly if we produced invalid TOML.
    tomllib.loads(text)
    return text


def _main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            "usage: git_main_sources.py <pyproject.toml> <owner> <sibling>...",
            file=sys.stderr,
        )
        return 2
    path, owner, siblings = argv[0], argv[1], argv[2:]
    with open(path, encoding="utf-8") as fh:
        original = fh.read()
    flipped = flip_sources(original, owner, siblings)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(flipped)
    print(f"flipped {len(siblings)} pd-* source(s) to git main in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_git_main_sources.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/git_main_sources.py tests/test_git_main_sources.py
git commit -m "feat(ci): pure rewriter to flip uv sources to sibling git main"
```

### Task 2: Orchestrator script + Makefile target

**Files:**
- Create: `scripts/ci-against-main.sh`
- Modify: `Makefile` (add `ci-against-main` target near the other `local-*`/`ci-*` targets)

- [ ] **Step 1: Write the orchestrator**

```bash
# scripts/ci-against-main.sh
#!/usr/bin/env bash
# Validate this repo against its pd-* siblings' latest GitHub `main`.
#
# Transient: backs up pyproject.toml + uv.lock, flips pd-* uv sources to
# git+main (locking each sibling's current main SHA for a reproducible run),
# runs the release preflight, then ALWAYS restores the two files and re-syncs.
# Leaves zero committed churn. Refuses to run in local-dev mode.
#
# Per-repo config: OWNER + PY_SIBLINGS below.
# Override the preflight with PREFLIGHT="make test" for a faster smoke.
set -euo pipefail

OWNER="pdomain"
PY_SIBLINGS=(pdomain-book-tools)          # repo-specific; keep in sync with [tool.uv.sources]
PREFLIGHT="${PREFLIGHT:-make ci-slow}"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Guard 1: never mix with local-dev editable mode.
for marker in \
    .venv/.pdomain-local-mode \
    .venv/.pdomain-dev-local; do
    if [ -f "$marker" ]; then
        echo "ERROR: leave local-dev mode before ci-against-main ($marker)" >&2
        exit 1
    fi
done

# Guard 2: pyproject.toml / uv.lock must be clean — we restore them by backup.
if ! git diff --quiet -- pyproject.toml uv.lock; then
    echo "ERROR: pyproject.toml/uv.lock have uncommitted changes." >&2
    echo "       Commit or stash them before running ci-against-main." >&2
    exit 1
fi

BACKUP_DIR="$(mktemp -d)"
cp pyproject.toml "$BACKUP_DIR/pyproject.toml"
cp uv.lock "$BACKUP_DIR/uv.lock"

restore() {
    rc=$?
    echo ""
    echo "Restoring pyproject.toml + uv.lock and re-syncing registry deps..."
    cp "$BACKUP_DIR/pyproject.toml" pyproject.toml
    cp "$BACKUP_DIR/uv.lock" uv.lock
    rm -rf "$BACKUP_DIR"
    uv sync --quiet || true
    exit $rc
}
trap restore EXIT

echo "Flipping pd-* sources to git main: ${PY_SIBLINGS[*]}"
python3 scripts/git_main_sources.py pyproject.toml "$OWNER" "${PY_SIBLINGS[@]}"

echo "Locking against sibling main (captures current SHAs)..."
uv lock
uv sync

echo "Running preflight against sibling main: $PREFLIGHT"
sh -c "$PREFLIGHT"

echo ""
echo "✅ ci-against-main passed — validated against sibling main."
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x scripts/ci-against-main.sh`

- [ ] **Step 3: Add the Makefile target**

Add near the `local-*` targets (match the file's existing `##`-help idiom):

```makefile
ci-against-main: ## Validate against pd-* siblings' latest main, then revert (transient)
	@./scripts/ci-against-main.sh
```

- [ ] **Step 4: Verify the target is discoverable and the script parses**

Run: `make help 2>/dev/null | grep ci-against-main && bash -n scripts/ci-against-main.sh && echo OK`
Expected: the help line prints and `OK` prints (no syntax errors).

- [ ] **Step 5: Commit**

```bash
git add scripts/ci-against-main.sh Makefile
git commit -m "feat(ci): make ci-against-main — transient sibling-main validation"
```

### Task 3: Release-preflight hook

**Files:**
- Modify: `scripts/release-common.sh` (insert the hook just before the existing `RELEASE_PREFLIGHT` run)

- [ ] **Step 1: Locate the preflight block**

Run: `grep -n 'RELEASE_PREFLIGHT' scripts/release-common.sh`
Expected: the `if ! sh -c "$RELEASE_PREFLIGHT"; then` line (the normal preflight invocation).

- [ ] **Step 2: Insert the opt-in hook immediately before that block**

```bash
    if [ "${VALIDATE_AGAINST_MAIN:-0}" = "1" ]; then
        if [ -x ./scripts/ci-against-main.sh ]; then
            echo ""
            echo "VALIDATE_AGAINST_MAIN=1: validating against sibling main first..."
            ./scripts/ci-against-main.sh
        else
            echo "WARNING: VALIDATE_AGAINST_MAIN=1 set but scripts/ci-against-main.sh not found; skipping." >&2
        fi
    fi
```

- [ ] **Step 3: Verify the script still parses**

Run: `bash -n scripts/release-common.sh && echo OK`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add scripts/release-common.sh
git commit -m "feat(release): VALIDATE_AGAINST_MAIN hook runs ci-against-main pre-tag"
```

### Task 4: End-to-end validation in pdomain-ops

- [ ] **Step 1: Confirm not in local-dev mode**

Run: `make local-check`
Expected: `MODE: registry`. If it says local-dev, run the repo's documented exit (e.g. `rm .venv/.pdomain-local-mode && uv sync`) first.

- [ ] **Step 2: Run the new target end-to-end**

Run: `make ci-against-main`
Expected: flips `pdomain-book-tools` to git main, `uv lock`/`sync` resolves book-tools from GitHub main, `make ci-slow` runs and passes, then the restore message prints. Final line: `✅ ci-against-main passed`.

- [ ] **Step 3: Verify the tree was fully restored**

Run: `git status --porcelain pyproject.toml uv.lock`
Expected: empty output (both files reverted to their committed state).

- [ ] **Step 4: Verify failure path also restores (trap correctness)**

Run: `PREFLIGHT="sh -c 'exit 7'" make ci-against-main; echo "exit=$?"; git status --porcelain pyproject.toml uv.lock`
Expected: the run flips + locks, the preflight fails, `exit=7` is preserved, and `git status` is empty (restored despite failure).

- [ ] **Step 5: Commit (nothing to commit if clean — record the validation in the task notes instead)**

No file changes expected. If `make ci-against-main` produced any unintended tracked change, STOP — the trap is broken; fix Task 2 before proceeding.

### Task 5: Milestone 0 independent review (fresh subagent)

- [ ] Dispatch a fresh `model: sonnet` reviewer (NOT the implementer) over the full Milestone 0 diff in `pdomain-ops`. Prompt it with the five gates (Security / Correctness / Simplicity / Common style / NO DEFERRED WORK) and require a verdict `APPROVE` or `REQUEST-CHANGES` with specific `path:line` findings. Specifically have it confirm: the regex cannot match across multiple entries; the trap preserves the preflight exit code; `git diff --quiet` guard prevents clobbering uncommitted work; git URLs are hard-pinned to the `pdomain` org; no `TODO`/deferred branches. Fix all REQUEST-CHANGES and re-review until APPROVE.

---

## Milestone 1 — Parallel rollout (6 repos, one subagent each)

Run all six **in parallel** — one fresh `model: sonnet` subagent per repo, each with `isolation: "worktree"`. Each subagent performs the identical procedure below for its repo, then an independent per-repo reviewer (separate subagent) applies the five gates before the branch is integrated.

**Target repos and their `PY_SIBLINGS` (from `[tool.uv.sources]`):**

| Repo | `PY_SIBLINGS` | Frontend? (affects `ci-slow` weight) |
|---|---|---|
| `pdomain-ocr-cli` | `pdomain-book-tools pdomain-ops` | no |
| `pdomain-ocr-training` | `pdomain-book-tools` | no |
| `pdomain-prep-for-pgdp` | `pdomain-book-tools pdomain-ops` | yes (npm stays on registry) |
| `pdomain-ocr-simple-gui` | `pdomain-book-tools pdomain-ops` | yes (npm stays on registry) |
| `pdomain-ocr-labeler-spa` | `pdomain-book-tools pdomain-ops` | yes (npm stays on registry) |
| `pdomain-ocr-trainer-spa` | `pdomain-book-tools pdomain-ops pdomain-ocr-training` | yes (npm stays on registry) |

### Task 6 (×6, PARALLEL): roll the mechanism into each repo

For each target repo, the subagent does:

- [ ] **Step 1: Copy the three canonical files** from `pdomain-ops` verbatim:
  - `scripts/git_main_sources.py` (identical — no per-repo changes)
  - `scripts/ci-against-main.sh` (then edit only the `PY_SIBLINGS=(...)` line to this repo's siblings from the table above)
  - `tests/test_git_main_sources.py` (identical)
  Ensure `scripts/ci-against-main.sh` is `chmod +x`.

- [ ] **Step 2: Add the Makefile target** (identical block from Task 2 Step 3), placed near the repo's `local-*`/`ci-*` targets, matching local `##`-help idiom.

- [ ] **Step 3: Add the release hook** to this repo's `scripts/release-common.sh` (identical block from Task 3 Step 2). If a repo lacks `scripts/release-common.sh`, STOP and report — do not invent one.

- [ ] **Step 4: Run the transform unit tests**

Run: `uv run pytest tests/test_git_main_sources.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Confirm registry mode, then run the target end-to-end**

Run: `make local-check` (expect `MODE: registry`; exit local-dev first if needed), then `make ci-against-main`.
Expected: the repo's `PY_SIBLINGS` flip to git main, `uv lock`/`sync` succeed, `ci-slow` passes, tree is restored. (Frontend repos: `ci-slow` builds the SPA against the **registry** npm `pdomain-ui` — unchanged — since npm is out of scope.)
If `ci-slow` is too heavy for the worktree environment, the subagent may first prove the mechanism with `PREFLIGHT="make test" make ci-against-main`, then run the full `make ci-against-main`; both must end green and restored. Report which was run.

- [ ] **Step 6: Verify restoration**

Run: `git status --porcelain pyproject.toml uv.lock`
Expected: empty.

- [ ] **Step 7: Commit on the worktree branch (do NOT push, do NOT open a PR, do NOT merge to main)**

```bash
git add scripts/git_main_sources.py scripts/ci-against-main.sh tests/test_git_main_sources.py Makefile scripts/release-common.sh
git commit -m "feat(ci): add ci-against-main sibling-main validation"
```
Return the worktree path + branch + which preflight was run + the five-gate self-check result.

### Task 6-review (×6): independent per-repo review

- [ ] For each rolled-out repo, a fresh `model: sonnet` reviewer (not that repo's implementer) checks the diff against the five gates, with extra attention to: `PY_SIBLINGS` exactly matches that repo's `[tool.uv.sources]` (no missing/extra sibling), the copied files are byte-identical to the `pdomain-ops` canon except the `PY_SIBLINGS` line, and `make ci-against-main` actually ran green (no skipped/deferred validation). Verdict `APPROVE`/`REQUEST-CHANGES`. The orchestrator integrates each repo's branch (rebase → ff-merge) only after APPROVE.

---

## Milestone 2 — Documentation

### Task 7: Document the third mode

**Files:**
- Modify: `docs/process/local-dev.md` (workspace)
- Create: `docs/process/ci-against-main.md` (workspace)

- [ ] **Step 1: Update the modes description in `docs/process/local-dev.md`**

Add a row/paragraph distinguishing the three resolutions: **registry** (default — published wheels from `pdomain-index-pip`), **local-dev** (editable sibling checkouts, marker-gated — for active cross-repo iteration), and **git-main validation** (`make ci-against-main` — transient, resolves siblings from GitHub `main`, for pre-release validation; leaves no committed churn; not a persistent mode). Cross-link `ci-against-main.md`.

- [ ] **Step 2: Write `docs/process/ci-against-main.md`**

Cover: purpose (catch "sibling main breaks me once released" before tagging); what it does (flip → lock SHAs → preflight → restore via trap); scope (Python siblings only — npm stays on registry, with the one-line rationale: `pdomain-ui` is a built lib needing a `dist`/`prepare` path, deferred out of scope by decision 2026-06-06); usage (`make ci-against-main`, `PREFLIGHT=...` override, `VALIDATE_AGAINST_MAIN=1 make release-patch`); guards (refuses in local-dev mode; refuses on dirty `pyproject.toml`/`uv.lock`); and the rollout repo list.

- [ ] **Step 3: Commit**

```bash
git add docs/process/local-dev.md docs/process/ci-against-main.md
git commit -m "docs(process): document ci-against-main git-main validation mode"
```

---

## Milestone 3 — End-of-plan holistic review

### Task 8: Independent cross-repo review

- [ ] Dispatch one fresh `model: sonnet` reviewer over the whole change set across all 7 repos + the docs. It must:
  - Re-apply the five gates holistically (Security, Correctness, Simplicity, Common style, **NO DEFERRED WORK**).
  - Confirm the canonical files are consistent across repos (only `PY_SIBLINGS` differs).
  - Confirm every in-scope repo's `make ci-against-main` was actually exercised green (not stubbed/skipped) and the tree restores.
  - Confirm the docs match the shipped behavior.
  - Spot-check the security posture: git URLs pinned to `pdomain`; no shell-injection from config; trap robust to Ctrl-C/failure; clean-tree guard intact.
  - Return a single report with any residual findings. Fix all findings; re-run the affected repo's `make ci-against-main`. Only then is the plan complete.

---

## Self-review (author checklist — completed)

- **Spec coverage:** purpose (pre-release validation) → Tasks 2–4 + release hook; transient/reproducible → backup+trap + `uv lock` SHA capture; Python-only scope → explicit in script config + docs; parallel rollout + per-task + end review → Milestones 1 & 3. Covered.
- **Placeholder scan:** no `TBD`/`TODO`/"implement later" — all steps carry real code/commands.
- **Type/name consistency:** `flip_sources(text, owner, siblings)` signature identical across the module, tests, and `ci-against-main.sh` invocation (`git_main_sources.py pyproject.toml "$OWNER" "${PY_SIBLINGS[@]}"`); `PY_SIBLINGS`, `OWNER`, `PREFLIGHT`, `VALIDATE_AGAINST_MAIN` used consistently.
- **FastAPI + SPA check:** this plan adds dev tooling, not a FastAPI app or new SPA serving surface, so the browser-verification milestone does not apply. (Frontend repos' existing `ci-slow` still runs their own SPA checks against registry npm.)
