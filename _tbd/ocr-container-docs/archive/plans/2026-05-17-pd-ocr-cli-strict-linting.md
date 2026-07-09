---
status: complete
synced: 2026-05-17
milestone: 1
repo: pdomain/pdomain-ocr-cli
---

# pdomain-ocr-cli — strict linting + type-check rollout (mirror of pdomain-book-tools)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement task-by-task. This is the **3rd repo** in the workspace-wide rollout; the canonical pattern was established in pdomain-book-tools at commit `f809701` (2026-05-17). For any decision NOT covered here, defer to pdomain-book-tools' final state — your job is to MIRROR what landed there, not invent new patterns.

**Reference:** Canonical pattern memory at `/home/vscode/.claude/projects/-workspaces-ocr-container/memory/project_strict_linting_canonical_pattern.md`. Decision doc: [`docs/decisions/2026-05-17-strict-linting.md`](../decisions/2026-05-17-strict-linting.md). Full canonical 8-task template: [`docs/plans/2026-05-17-pdomain-book-tools-strict-linting-rollout.md`](2026-05-17-pdomain-book-tools-strict-linting-rollout.md).

**Working directory:** `/workspaces/ocr-container/pdomain-ocr-cli/`
**Package:** `pd_ocr_cli/` (flat layout)
**Current head:** `576b863` (small well-linted CLI; 100% coverage floor)
**Discovery:** 6 source files + 12 test files. Vanilla `[tool.pyright]` at hybrid `basic` + per-env `strict`. Ruff baseline already has 11 codes (`E F W I N B SIM UP RUF ERA T20`). Pre-commit is thin (only ruff + 4 basic hooks). 49 noqa total — 45 are legitimate `T201` (CLI prints). **No `# type: ignore` anywhere.** `fail_under = 100` MUST be preserved.

---

## Suppression policy (read before starting)

Verbatim from [pdomain-book-tools plan §Suppression policy](2026-05-17-pdomain-book-tools-strict-linting-rollout.md). Same 7 rules.

---

## Notable repo-specific concerns

- **Coverage floor is 100%** — `[tool.coverage.report] fail_under = 100` at `pyproject.toml:103`. Adding `--cov-branch` will likely drop the measured number. **Use the canonical Task 7 pattern**: drop floor 2pp temporarily, ratchet back up as branch-coverage gaps close. Document in commit message.
- **45 of 49 noqa are `T201`** (CLI prints in `ocr_to_txt.py`). These are legitimate — expanding ruff won't cause a T201 avalanche. Real new noise will come from `ANN` (annotations) and `D` (docstrings) on the 6 source files.
- **Hybrid `[tool.pyright]`** is unusual (`basic` overall + `strict` for src). Task 2 must untangle this — replace entire block with `[tool.basedpyright]` at `standard` mode, then Task 8 upgrades to `recommended`. The agent should NOT preserve the per-env split; canonical is uniform `recommended` with `executionEnvironments` placeholders only.
- **No `# type: ignore` anywhere** — clean slate for basedpyright. Expect any new suppressions to be small.
- **Ruff pin currently `>=0.12.5`** — bump to `>=0.15.13`. Pre-commit ruff rev currently `v0.15.12` — bump to `v0.15.13`.
- **Task 3 (remove isort/pylint) is NOOP** — neither present.

---

## Task 1: Add canonical `.editorconfig` (TRIVIAL) {#add-canonical-editorconfig-trivial}

Copy verbatim from pdomain-book-tools. See [pdomain-book-tools §Task 2](2026-05-17-pdomain-book-tools-strict-linting-rollout.md#task-2-add-canonical-editorconfig) for exact content.

- [ ] **Step 1:** `cat /workspaces/ocr-container/pdomain-book-tools/.editorconfig > .editorconfig`
- [ ] **Step 2:** Verify first line: `# .editorconfig — workspace canonical`.
- [ ] **Step 3:** Commit:
```
chore: add canonical .editorconfig

Workspace-canonical file per docs/decisions/2026-05-17-strict-linting.md.
Mirrors pdomain-book-tools f809701.
```

---

## Task 2: Migrate pyright → basedpyright (standard mode) (MODERATE) {#migrate-pyright-basedpyright-standard-mode-moderat}

Replace the hybrid `[tool.pyright]` config with a clean `[tool.basedpyright]` at `standard`.

- [ ] **Step 1:** Add `"basedpyright>=1.39.4",` to `[dependency-groups] dev`.
- [ ] **Step 2:** Replace entire `[tool.pyright]` + `[[tool.pyright.executionEnvironments]]` blocks with:
```toml
[tool.basedpyright]
include = ["pd_ocr_cli", "tests"]
exclude = ["**/__pycache__", "**/.venv", "**/node_modules"]
typeCheckingMode = "standard"
venvPath = "."
venv = ".venv"

[[tool.basedpyright.executionEnvironments]]
root = "tests"
```
(No `scripts/` env since the repo has no `scripts/` dir per discovery.)
- [ ] **Step 3:** `uv sync` and verify with `uv run basedpyright --version`.
- [ ] **Step 4:** Run `uv run basedpyright pd_ocr_cli 2>&1 | tail -60`. Triage. The hybrid `basic`+`strict` previous config means some annotation gaps may have been silently tolerated; standard mode surfaces them. Hand-fix preferred (add annotations).
- [ ] **Step 5:** `make ci AI=1` should pass (typecheck isn't wired in yet).
- [ ] **Step 6:** Commit:
```
chore(types): migrate from pyright to basedpyright (standard mode)

Mirrors pdomain-book-tools f809701. Replaces the prior hybrid
[tool.pyright] (basic + per-env strict) with uniform basedpyright at
standard mode. Task 8 upgrades to recommended.

basedpyright is workspace-canonical (97.8% typing-spec conformance);
bundles its own Node via nodejs-wheel.

Per docs/decisions/2026-05-17-strict-linting.md.
```

---

## Task 3: Remove isort + pylint dev deps — **NOOP** (neither present) {#remove-isort-pylint-dev-deps-noop-neither-present}

**SKIP** — discovery confirmed neither is in `[dependency-groups] dev`.

---

## Task 4: Expand pre-commit (TRIVIAL — extend thin existing config) (TRIVIAL) {#expand-pre-commit-trivial-extend-thin-existing-con}

Existing `.pre-commit-config.yaml` has only 4 hooks + ruff. Replace with the canonical pdomain-book-tools file, edited for this repo.

- [ ] **Step 1:** `cp /workspaces/ocr-container/pdomain-book-tools/.pre-commit-config.yaml .pre-commit-config.yaml`
- [ ] **Step 2:** Edit: replace `pd_book_tools` → `pd_ocr_cli` in the local basedpyright hook (both `entry:` and `files:`).
- [ ] **Step 3:** Install: `uv run pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg`.
- [ ] **Step 4:** Run `uv run pre-commit run --all-files 2>&1 | tail -60`. Fix any new violations (no `--no-verify`).
- [ ] **Step 5:** Confirm Makefile has `pre-commit-check` target. If missing, add:
```makefile
pre-commit-check: ## Run all pre-commit hooks against all files (read-only check)
	uv run pre-commit run --all-files
```
- [ ] **Step 6:** Commit:
```
chore(precommit): add canonical hooks (gitleaks + check-* + uv-lock-check + basedpyright)

Mirrors pdomain-book-tools f809701 canonical pattern:
- pre-commit-update (auto-rev bumper, manual stage)
- pre-commit-hooks v6.0.0 (full canonical set including
  debug-statements, check-toml, check-merge-conflict)
- gitleaks v8.30.1 (staged-diff secret scan)
- ruff-pre-commit v0.15.13 (bumped from v0.15.12)
- markdownlint-cli2 v0.22.1
- local uv-lock-check + basedpyright (pd_ocr_cli scope, --level error)

Per docs/decisions/2026-05-17-strict-linting.md.
```

---

## Task 5: Add gitlint (TRIVIAL) {#add-gitlint-trivial}

- [ ] **Step 1:** `cp /workspaces/ocr-container/pdomain-book-tools/.gitlint .gitlint`
- [ ] **Step 2:** Add `"gitlint>=0.19.1",` to `[dependency-groups] dev`. `uv sync`.
- [ ] **Step 3:** Re-install commit-msg hook: `uv run pre-commit install --install-hooks --hook-type commit-msg` (Task 4 may have installed it, but safe to repeat).
- [ ] **Step 4:** Smoke test: `uv run pre-commit run gitlint --hook-stage commit-msg --commit-msg-filename <(git log -1 --pretty=%B)`.
- [ ] **Step 5:** Commit:
```
chore(precommit): add gitlint for commit-message hygiene

Mirrors pdomain-book-tools f809701. gitlint v0.19.1 enforces title ≤72,
body ≤100, bans WIP titles. Pure Python — no Node required.

Per docs/decisions/2026-05-17-strict-linting.md.
```

---

## Task 6: Expand ruff `select` to canonical set (MODERATE) {#expand-ruff-select-to-canonical-set-moderate}

Current select (11 codes): `["E", "F", "W", "I", "N", "B", "SIM", "UP", "RUF", "ERA", "T20"]`. Target: full 24-rule canonical (adds 13 groups).

- [ ] **Step 1:** Bump pin: `"ruff>=0.12.5"` → `"ruff>=0.15.13"`. `uv sync`.
- [ ] **Step 2:** Replace entire `[tool.ruff.lint]` block with canonical from pdomain-book-tools (lines 122-297 of its pyproject.toml). Then edit per-file-ignores:
  - Keep canonical baseline (`tests/**`, `scripts/*`, `**/__init__.py`, `**/_*.py`).
  - Drop all pdomain-book-tools-specific `pd_book_tools/...` entries.
  - **Preserve current `"scripts/*.py" = ["T201"]`** — pdomain-ocr-cli has `scripts/` per existing per-file-ignores.
- [ ] **Step 3:** Add `[tool.ruff.lint.pydocstyle] convention = "google"` (canonical workspace setting).
- [ ] **Step 4:** Auto-fix: `uv run ruff check --fix --unsafe-fixes pd_ocr_cli/ tests/ scripts/`.
- [ ] **Step 5:** Re-check: `uv run ruff check pd_ocr_cli/ tests/ scripts/ 2>&1 | tail -80`. Triage per suppression policy. Expected hotspots:
  - `ANN`: 6 source files + 12 test files need annotations. Tests are auto-ignored via per-file-ignores. Source-side ANN fixes are real work.
  - `D`: source-side docstring gaps. Use `# noqa: D103  # TODO` for trivial getters; add real docstrings for public API touched.
  - `T201`: 45 existing — already noqa'd; no new ones expected.
- [ ] **Step 6:** `make ci AI=1` should pass.
- [ ] **Step 7:** Commit:
```
chore(lint): expand ruff select to workspace canonical set

Mirrors pdomain-book-tools f809701. Adds 13 rule groups beyond baseline:
ANN S C4 PERF TC TID PT RET PL D (per 2026-05-17 strict-linting
decisions) + BLE TRY LOG G (per guidelines audit — rolls
docs/python-coding-guidelines.md exception/logging rules into tools).

ruff dep pin bumped v0.12.5 → v0.15.13. New per-file-ignores cover
canonical exemption set: tests, scripts, __init__.py, private modules.

Per docs/decisions/2026-05-17-strict-linting.md.
```

---

## Task 7: Pytest hardening (MODERATE — coverage floor pressure) {#pytest-hardening-moderate-coverage-floor-pressure}

- [ ] **Step 1:** Replace `[tool.pytest.ini_options]` `addopts`:
```toml
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--cov=pd_ocr_cli",
    "--cov-branch",
    "--cov-report=term-missing:skip-covered",
]
filterwarnings = [
    "error",
    # Add ignores below as new warnings surface — each with a comment.
]
```
- [ ] **Step 2:** Run `uv run pytest 2>&1 | tail -40`. For each warning-turned-error: third-party noise → add `ignore::DeprecationWarning:pkg.*` with comment; our code → FIX IT.
- [ ] **Step 3:** Check post-`--cov-branch` coverage: `uv run pytest --cov=pd_ocr_cli --cov-branch --cov-report=term 2>&1 | tail -10`. Note the percentage.
- [ ] **Step 4:** Coverage floor handling: current `fail_under = 100`. If `--cov-branch` drops below 100:
  - Option A (preferred): write quick tests for uncovered branches (small codebase — likely feasible).
  - Option B (fallback): drop `fail_under` 2pp (to 98) with a TODO comment scheduling the ratchet-up.
  - **Choose A first**; only fall back to B if branch-coverage gaps would take >60 min to close. Document the choice in commit message.
- [ ] **Step 5:** `make ci AI=1` (which runs `coverage` per existing target) must pass.
- [ ] **Step 6:** Commit:
```
test(pytest): adopt filterwarnings=error and --cov-branch

Mirrors pdomain-book-tools f809701. filterwarnings = ['error'] turns
silent deprecations into failures. --cov-branch measures branch
coverage (gates except-path testing).

Coverage floor (100%) <preserved | dropped to 98% with TODO to
ratchet up — depending on Step 4 choice>.

Per docs/decisions/2026-05-17-strict-linting.md.
```

---

## Task 8: Upgrade basedpyright to `recommended` + Makefile/CI wiring (MODERATE) {#upgrade-basedpyright-to-recommended-makefileci-wir}

- [ ] **Step 1:** In `[tool.basedpyright]`:
  - `typeCheckingMode = "standard"` → `typeCheckingMode = "recommended"`
  - Add `reportImportCycles = "none"` (canonical)
  - Add deferred-failOnWarnings comment block (mirror pdomain-book-tools — adapt the third-party list; pdomain-ocr-cli doesn't have CuPy but does import optional `cupy` per noqa in `ocr_to_txt.py:218`):
```toml
# NOTE: failOnWarnings deferred — recommended mode surfaces warnings from
# optional stubs (cupy probe, DocTR, etc.) that lag runtime. Enable
# incrementally as stub coverage improves.
# failOnWarnings = true
```
- [ ] **Step 2:** Add `typecheck` Makefile target:
```makefile
typecheck: ## Run basedpyright at recommended mode (workspace canonical)
	uv run basedpyright pd_ocr_cli --level error
```
- [ ] **Step 3:** Wire into `ci:` target. Current is `setup → pre-commit-check → coverage → build`. Insert `typecheck` between `pre-commit-check` and `coverage`:
```makefile
ci:
	$(MAKE) --no-print-directory setup
	$(MAKE) --no-print-directory pre-commit-check
	$(MAKE) --no-print-directory typecheck
	$(MAKE) --no-print-directory coverage
	$(MAKE) --no-print-directory build
```
- [ ] **Step 4:** Update pre-commit `basedpyright` entry to `--level error` (mirror pdomain-book-tools):
```yaml
      entry: uv run basedpyright pd_ocr_cli --level error
      name: basedpyright type check (recommended mode; workspace canonical)
```
- [ ] **Step 5:** Run `uv run basedpyright pd_ocr_cli --level error 2>&1 | tail -80`. Triage. Small codebase (6 files) — annotations should be quick. For cupy/DocTR optional-import warnings: `# pyright: ignore[reportXxx]` inline with comment.
- [ ] **Step 6:** `make ci AI=1` end-to-end must pass.
- [ ] **Step 7:** Commit:
```
feat(types): basedpyright recommended mode + wire into make ci

Mirrors pdomain-book-tools f809701. typeCheckingMode = 'recommended'
catches unannotated functions, inferred-Any propagation, missing
return types.

failOnWarnings deferred via --level error due to optional cupy/DocTR
stub noise. Enable incrementally as stubs improve.

make typecheck added as discrete target; make ci now invokes it
between pre-commit-check and coverage.

Per docs/decisions/2026-05-17-strict-linting.md.
```

---

## Self-review checklist

- [ ] 7 commits land in order (Task 3 NOOP).
- [ ] No `--no-verify`.
- [ ] `make ci AI=1` green at tip.
- [ ] `uv run basedpyright pd_ocr_cli --level error` clean.
- [ ] `uv run ruff check pd_ocr_cli tests scripts` clean.
- [ ] Coverage at 100% (preferred) OR dropped 2pp with TODO comment.
- [ ] Pre-existing 45 T201 noqa comments still present and valid.
- [ ] `.editorconfig`, `.gitlint`, `.pre-commit-config.yaml` at repo root matching pdomain-book-tools content.

## Notes for the agent

- This plan MIRRORS pdomain-book-tools `f809701`. Where this plan and pdomain-book-tools' final config files conflict, pdomain-book-tools is ground truth.
- Small codebase (6 src + 12 test files) — expect Tasks 6 + 8 to be quick MODERATE not HEAVY.
- The 100% coverage floor is the only non-trivial pressure. Plan extra time for Task 7 if branches end up uncovered.
- If a task overruns ~90min, STOP and report.
- Final report: "7 of 7 commits landed (Task 3 NOOP); final SHA: <X>; make ci AI=1 green; <coverage floor outcome>; <N> suppressions added; <flagged divergences from pdomain-book-tools>".
