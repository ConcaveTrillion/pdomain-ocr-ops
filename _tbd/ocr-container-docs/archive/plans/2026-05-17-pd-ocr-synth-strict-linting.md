---
status: complete
synced: 2026-05-17
milestone: 1
repo: pdomain/pdomain-ocr-synth
---

# pdomain-ocr-synth — strict linting + type-check rollout (mirror of pdomain-book-tools)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement task-by-task. This is the **4th repo** in the workspace-wide rollout; the canonical pattern was established in pdomain-book-tools at commit `f809701` (2026-05-17). For any decision NOT covered here, defer to pdomain-book-tools' final state — your job is to MIRROR what landed there, not invent new patterns.

**Reference:** Canonical pattern memory at `/home/vscode/.claude/projects/-workspaces-ocr-container/memory/project_strict_linting_canonical_pattern.md`. Decision doc: [`docs/decisions/2026-05-17-strict-linting.md`](../decisions/2026-05-17-strict-linting.md). Full canonical 8-task template: [`docs/plans/2026-05-17-pdomain-book-tools-strict-linting-rollout.md`](2026-05-17-pdomain-book-tools-strict-linting-rollout.md).

**Working directory:** `/workspaces/ocr-container/pdomain-ocr-synth/`
**Package:** `src/pd_ocr_synth/` (**src-layout** — NOT flat like pdomain-book-tools)
**Current head:** `b456aa5` (140 commits; **substantial implementation**, despite CLAUDE.md still claiming spec-only)
**Discovery:** 65 src files + 62 test files (much larger than discovery expected). Ruff baseline has 12 codes (`E F W I N B C4 SIM UP RUF ERA T20`). Vanilla `[tool.pyright]` (basic + per-env strict on `src`). Pre-commit exists but thin (no gitleaks, no debug-statements, no basedpyright, no gitlint). `requires-python = ">=3.13"`.

---

## Suppression policy (read before starting)

Verbatim from [pdomain-book-tools plan §Suppression policy](2026-05-17-pdomain-book-tools-strict-linting-rollout.md). Same 7 rules. **Pay extra attention to time budget — this repo is the largest of the batch-1 trio.**

---

## Notable repo-specific concerns

- **src-layout** (`src/pd_ocr_synth/`) — ALL canonical patterns must adapt path references. Example: `basedpyright include = ["src", "tests"]` (NOT `["pd_ocr_synth", ...]`); pre-commit `basedpyright` hook `files: ^src/pd_ocr_synth/.*\.py$`; Makefile `typecheck` runs `uv run basedpyright src/pd_ocr_synth --level error`.
- **Largest repo of the trio** (65 src + 62 test files). Task 6 (ruff expansion) is **HEAVY** per discovery — ANN + D alone will surface hundreds of violations. Per suppression policy, **STOP and report if Task 6 exceeds 90 min**; the user will decide whether to continue or split.
- **`requires-python = ">=3.13"`** — newer than pdomain-book-tools' `>=3.10`. ruff `target-version` may need explicit setting (`target-version = "py313"`) if not auto-detected from `requires-python`.
- **Existing pre-commit has `--maxkb=512`**; canonical is `--maxkb=1000`. Mirror canonical (1000) when replacing.
- **Existing ruff rev `v0.15.12`**; bump to `v0.15.13`.
- **No `.editorconfig`, `.gitlint`**, no `basedpyright`, no `gitleaks`, no `gitlint`, no `default_install_hook_types`, no `uv-lock-check`.
- **Task 3 (remove isort/pylint) is NOOP**.
- **Dependency groups use include-group pattern** (`test` + `lint` + `dev = [{include-group = "test"}, ...]`). Add new deps to the appropriate sub-group: `basedpyright` to `lint`, `gitlint` to `lint`, `pytest-cov` already in `test`.
- **Recommended sequencing change per discovery agent:** consider doing Task 6 (ruff expansion) BEFORE Task 4 (pre-commit additions including basedpyright hook), so the pre-commit gate is clean before adding the type-check gate. Decide based on whether ruff expansion fix-work blows up; if it does, defer ruff-expansion as a focused commit and continue the rest.

---

## Task 1: Add canonical `.editorconfig` (TRIVIAL) {#add-canonical-editorconfig-trivial}

- [ ] **Step 1:** `cat /workspaces/ocr-container/pdomain-book-tools/.editorconfig > .editorconfig`
- [ ] **Step 2:** Verify first line.
- [ ] **Step 3:** Commit:
```
chore: add canonical .editorconfig

Workspace-canonical file per docs/decisions/2026-05-17-strict-linting.md.
Mirrors pdomain-book-tools f809701.
```

---

## Task 2: Migrate pyright → basedpyright (standard mode) (MODERATE) {#migrate-pyright-basedpyright-standard-mode-moderat}

- [ ] **Step 1:** Add `"basedpyright>=1.39.4",` to `[dependency-groups] lint`.
- [ ] **Step 2:** Replace `[tool.pyright]` + `[[tool.pyright.executionEnvironments]]` blocks with:
```toml
[tool.basedpyright]
include = ["src", "tests", "scripts"]
exclude = ["**/__pycache__", "**/.venv", "**/node_modules"]
typeCheckingMode = "standard"
venvPath = "."
venv = ".venv"

[[tool.basedpyright.executionEnvironments]]
root = "tests"

[[tool.basedpyright.executionEnvironments]]
root = "scripts"
```
**Note:** `include = ["src", "tests", "scripts"]` — covers src-layout. basedpyright picks up `src/pd_ocr_synth/` automatically. Verify with `uv run basedpyright src/pd_ocr_synth/cli.py` smoke test.
- [ ] **Step 3:** `uv sync`.
- [ ] **Step 4:** Run `uv run basedpyright 2>&1 | tail -80`. Triage at standard mode (annotation gaps mostly silent at this level; will surface at recommended in Task 8). Fix hard errors only; defer annotation work to Task 8.
- [ ] **Step 5:** `make ci AI=1` should pass.
- [ ] **Step 6:** Commit:
```
chore(types): migrate from pyright to basedpyright (standard mode)

Mirrors pdomain-book-tools f809701. Replaces [tool.pyright] (basic +
per-env strict on src) with uniform basedpyright at standard mode.
Task 8 upgrades to recommended.

include = ["src", "tests", "scripts"] for src-layout.

Per docs/decisions/2026-05-17-strict-linting.md.
```

---

## Task 3: Remove isort + pylint dev deps — **NOOP** {#remove-isort-pylint-dev-deps-noop}

**SKIP** — neither present.

---

## Task 4: Expand pre-commit (TRIVIAL — replace thin existing) (TRIVIAL) {#expand-pre-commit-trivial-replace-thin-existing-tr}

- [ ] **Step 1:** `cp /workspaces/ocr-container/pdomain-book-tools/.pre-commit-config.yaml .pre-commit-config.yaml`
- [ ] **Step 2:** Edit:
  - `pd_book_tools` → `src/pd_ocr_synth` in the basedpyright local hook `entry:` (becomes `uv run basedpyright src/pd_ocr_synth --level error`) and `files:` (becomes `^src/pd_ocr_synth/.*\.py$`).
- [ ] **Step 3:** Add `"pre-commit>=4.3",` to `[dependency-groups] lint` if not already there (per discovery it's present).
- [ ] **Step 4:** `uv sync` then `uv run pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg`.
- [ ] **Step 5:** `uv run pre-commit run --all-files 2>&1 | tail -60`. Fix violations (debug-statements, malformed configs). No `--no-verify`.
- [ ] **Step 6:** Confirm Makefile has `pre-commit-check` target (per discovery: yes). If not, add per pdomain-book-tools.
- [ ] **Step 7:** Commit:
```
chore(precommit): adopt canonical hooks (gitleaks + check-* + uv-lock-check + basedpyright)

Mirrors pdomain-book-tools f809701 canonical pattern. Replaces thin
prior config with full canonical:
- pre-commit-update (auto-rev bumper, manual stage)
- pre-commit-hooks v6.0.0 (full canonical set: trailing/EOF/yaml/
  json/toml/large-files (maxkb=1000)/debug/merge)
- gitleaks v8.30.1 (staged-diff secret scan)
- ruff-pre-commit v0.15.13 (bumped from v0.15.12)
- markdownlint-cli2 v0.22.1 (preserved)
- local uv-lock-check + basedpyright (src/pd_ocr_synth scope,
  --level error)

Per docs/decisions/2026-05-17-strict-linting.md.
```

---

## Task 5: Add gitlint (TRIVIAL) {#add-gitlint-trivial}

- [ ] **Step 1:** `cp /workspaces/ocr-container/pdomain-book-tools/.gitlint .gitlint`
- [ ] **Step 2:** Add `"gitlint>=0.19.1",` to `[dependency-groups] lint`. `uv sync`.
- [ ] **Step 3:** Re-install commit-msg hook.
- [ ] **Step 4:** Smoke test against most recent commit.
- [ ] **Step 5:** Commit:
```
chore(precommit): add gitlint for commit-message hygiene

Mirrors pdomain-book-tools f809701. gitlint v0.19.1 — title ≤72, body
≤100, no WIP. Pure Python.

Per docs/decisions/2026-05-17-strict-linting.md.
```

---

## Task 6: Expand ruff `select` to canonical set (**HEAVY** per discovery) {#expand-ruff-select-to-canonical-set-heavy-per-disc}

**WARNING:** Discovery flagged this as the heaviest task in the rollout — 65 src files + 62 test files with no prior ANN/D/S/TRY history. Apply suppression policy aggressively (per-file-ignores for whole categories). **If fix work exceeds 90 min, STOP and report; do not silently expand scope.**

Current select (12 codes): `["E", "W", "F", "I", "N", "B", "C4", "SIM", "UP", "RUF", "ERA", "T20"]`. Target: full 24-rule canonical (adds 12 groups: `ANN S PERF TC TID PT RET PL D BLE TRY LOG G`).

- [ ] **Step 1:** Bump pin: `"ruff>=0.13"` → `"ruff>=0.15.13"` in `[dependency-groups] lint`. `uv sync`.
- [ ] **Step 2:** First, SIZE the queue: `uv run ruff check --select ANN,D,S,TRY,PL,BLE,LOG,G src/ tests/ 2>&1 | tail -20`. Note the violation count. If it exceeds ~500, consider per-package incremental rollout (suite, then recipe, then degradation, etc.) — discuss in commit message.
- [ ] **Step 3:** Replace `[tool.ruff.lint]` block with canonical from pdomain-book-tools (lines 122-297). Edit per-file-ignores:
  - Keep canonical baseline (`tests/**`, `scripts/*`, `**/__init__.py`, `**/_*.py`).
  - Drop pdomain-book-tools-specific entries.
  - Add `target-version = "py313"` to `[tool.ruff]` if not auto-detected from `requires-python = ">=3.13"`.
- [ ] **Step 4:** Add `[tool.ruff.lint.pydocstyle] convention = "google"`.
- [ ] **Step 5:** Auto-fix: `uv run ruff check --fix --unsafe-fixes src/ tests/`.
- [ ] **Step 6:** Re-check: `uv run ruff check src/ tests/ 2>&1 | tail -80`. Triage. For categories where >10 files have the same violation pattern (e.g. `ANN201` missing return types in publish/ subpackage): add a focused per-file-ignore entry rather than fix in this commit. Document the deferred fix backlog in commit message.
- [ ] **Step 7:** `make ci AI=1` should pass.
- [ ] **Step 8:** Commit:
```
chore(lint): expand ruff select to workspace canonical set

Mirrors pdomain-book-tools f809701. Adds 12 rule groups beyond baseline:
ANN S PERF TC TID PT RET PL D (per 2026-05-17 strict-linting
decisions) + BLE TRY LOG G (per guidelines audit).

ruff dep pin bumped v0.13 → v0.15.13. New per-file-ignores cover
canonical exemption set + focused deferrals for production files
where ANN/D backlog is significant — see inline per-file-ignores
for files marked as deferred.

Per docs/decisions/2026-05-17-strict-linting.md.
```

---

## Task 7: Pytest hardening (MODERATE) {#pytest-hardening-moderate}

- [ ] **Step 1:** Replace `[tool.pytest.ini_options]` `addopts`:
```toml
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--cov=pd_ocr_synth",
    "--cov-branch",
    "--cov-report=term-missing:skip-covered",
]
testpaths = ["tests"]
pythonpath = ["src"]   # KEEP — src-layout requires this
markers = [
    "unit: fast in-process tests",
    "integration: tests touching disk / network",
    "slow: long-running tests",
]
filterwarnings = [
    "error",
    # Add ignores below as new warnings surface — each with a comment.
]
```
- [ ] **Step 2:** Confirm `pytest-cov` is in `[dependency-groups] test` (per discovery: `pytest-cov>=7.0`). `uv sync`.
- [ ] **Step 3:** Run `uv run pytest 2>&1 | tail -60`. For warning-errors: third-party noise (Pydantic, httpx, Pillow, uharfbuzz, etc.) → add `ignore::DeprecationWarning:pkg.*` with comment. Our code → FIX IT.
- [ ] **Step 4:** Check post-`--cov-branch` coverage number (informational; no `fail_under` is currently configured per discovery — leave it that way).
- [ ] **Step 5:** `make ci AI=1` passes.
- [ ] **Step 6:** Commit:
```
test(pytest): adopt filterwarnings=error and --cov-branch

Mirrors pdomain-book-tools f809701. filterwarnings = ['error'] turns
silent deprecations into failures. --cov-branch measures branch
coverage. Also adds --strict-config per workspace convention.

pythonpath = ["src"] preserved for src-layout.

Per docs/decisions/2026-05-17-strict-linting.md.
```

---

## Task 8: Upgrade basedpyright to `recommended` + Makefile/CI wiring (MODERATE) {#upgrade-basedpyright-to-recommended-makefileci-wir}

- [ ] **Step 1:** In `[tool.basedpyright]`:
  - `typeCheckingMode = "standard"` → `typeCheckingMode = "recommended"`
  - Add `reportImportCycles = "none"`
  - Add deferred-failOnWarnings comment (adapt third-party list — pdomain-ocr-synth uses pydantic, pillow, uharfbuzz, freetype-py):
```toml
# NOTE: failOnWarnings deferred — recommended mode surfaces warnings from
# uharfbuzz / freetype-py / pillow stubs that lag runtime. Enable
# incrementally as stub coverage improves.
# failOnWarnings = true
```
- [ ] **Step 2:** Add `typecheck` Makefile target:
```makefile
typecheck: ## Run basedpyright at recommended mode (workspace canonical)
	uv run basedpyright src/pd_ocr_synth --level error
```
- [ ] **Step 3:** Wire into `ci:` target. Current (per discovery): `setup → pre-commit-check → test → build`. Insert `typecheck` between `pre-commit-check` and `test`:
```makefile
ci:
	@$(MAKE) --no-print-directory setup
	@$(MAKE) --no-print-directory pre-commit-check
	@$(MAKE) --no-print-directory typecheck
	@$(MAKE) --no-print-directory test
	@$(MAKE) --no-print-directory build
```
- [ ] **Step 4:** Pre-commit `basedpyright` hook entry already uses `--level error` from Task 4. Verify.
- [ ] **Step 5:** Run `uv run basedpyright src/pd_ocr_synth --level error 2>&1 | tail -80`. Triage. 65 source files — annotation gaps likely numerous. Use per-file-ignore via `executionEnvironments` for genuinely third-party-heavy modules (e.g., freetype-py wrapper). Prefer hand-fixes elsewhere. **STOP at 90 min** and report what landed vs what's deferred.
- [ ] **Step 6:** `make ci AI=1` end-to-end passes.
- [ ] **Step 7:** Commit:
```
feat(types): basedpyright recommended mode + wire into make ci

Mirrors pdomain-book-tools f809701. typeCheckingMode = 'recommended'
catches unannotated functions, inferred-Any propagation, missing
return types.

failOnWarnings deferred via --level error due to
uharfbuzz/freetype-py/pillow stub noise. Enable incrementally.

make typecheck added; make ci now invokes setup →
pre-commit-check → typecheck → test → build in order.

Per docs/decisions/2026-05-17-strict-linting.md.
```

---

## Self-review checklist

- [ ] 7 commits land (Task 3 NOOP).
- [ ] No `--no-verify`.
- [ ] `make ci AI=1` green.
- [ ] `uv run basedpyright src/pd_ocr_synth --level error` clean.
- [ ] `uv run ruff check src tests` clean.
- [ ] `.editorconfig`, `.gitlint`, `.pre-commit-config.yaml` match pdomain-book-tools.
- [ ] basedpyright `include = ["src", "tests", "scripts"]` (src-layout).
- [ ] `pythonpath = ["src"]` preserved in pytest config.
- [ ] `target-version = "py313"` set if needed (verify ruff doesn't complain about py3.13-only syntax).

## Notes for the agent

- This plan MIRRORS pdomain-book-tools `f809701`. pdomain-book-tools' final config files are ground truth.
- **This is the largest repo of the batch-1 trio.** Task 6 is HEAVY per discovery. Plan a per-file-ignores-heavy approach: when 10+ files share a violation pattern (e.g. ANN on the publish/ subpackage), add the per-file-ignore entry; do NOT try to fix all 65 files' annotations in one commit. Document deferred backlog clearly so a future cleanup commit can resume.
- If a task overruns ~90min, STOP and report. The user will decide split vs continue.
- Final report: "<N> of 7 commits landed (Task 3 NOOP); final SHA: <X>; make ci AI=1 green; <H> per-file-ignores added for deferred ANN/D/etc backlog; <N> hand-fixes made; <flagged divergences from pdomain-book-tools>; <whether Task 6 needed to be split into incremental commits>".
