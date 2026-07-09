---
status: complete
synced: 2026-05-17
milestone: 44
repo: pdomain/pdomain-ocr-labeler-spa
---

# pdomain-ocr-labeler-spa — strict linting + type-check rollout (Python + TypeScript/React)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans`. Rollout step 6 — second repo with BOTH Python and TS/React sides. This is the **LARGEST codebase** in the workspace (87 src + 123 test Python; 219 TS files). Mirror pdomain-book-tools `f809701` for Python AND apply TS/React canonical from decision doc §TypeScript/React stack.

**Reference:**
- Canonical Python pattern memory: `/home/vscode/.claude/projects/-workspaces-ocr-container/memory/project_strict_linting_canonical_pattern.md`
- Decision doc: [`docs/decisions/2026-05-17-strict-linting.md`](../decisions/2026-05-17-strict-linting.md)
- Full canonical Python template: [`docs/plans/2026-05-17-pdomain-book-tools-strict-linting-rollout.md`](2026-05-17-pdomain-book-tools-strict-linting-rollout.md)
- pdomain-prep-for-pgdp plan (sister-repo): [`docs/plans/2026-05-17-pdomain-prep-for-pgdp-strict-linting.md`](2026-05-17-pdomain-prep-for-pgdp-strict-linting.md)

**Working directory:** `/workspaces/ocr-container/pdomain-ocr-labeler-spa/`
**Python package:** `src/pd_ocr_labeler_spa/` (src-layout)
**Current head:** `6d52367`
**Discovery:** 87 src + 123 test Python; 219 TS/TSX. `[tool.pyright]` at flat `"basic"` mode (weaker than pgdp-prep's hybrid). **253 Python suppressions** (86 `attr-defined`, 48 `arg-type`, 20 N815 noqa). Frontend has mise.toml + bot bootstrap requirements. tsconfig.app.json: `strict: true` covers most; only `noUncheckedIndexedAccess` is the explicit canonical-additional flag missing. ESLint at `recommended`, no `strictTypeChecked`, no jsx-a11y, no knip. Existing pre-commit has frontend-tsc/eslint/prettier local hooks, plus pyright src/, uv lock --check, refresh-version post-hooks.

---

## Suppression policy

Verbatim from [pdomain-book-tools plan §Suppression policy](2026-05-17-pdomain-book-tools-strict-linting-rollout.md). Same 7 rules; ~90 min per task max.

---

## Notable repo-specific concerns

- **LARGEST codebase in workspace** — 87+123 Python + 219 TS files. **Both Task 6 (ruff expansion) AND Task 8 (basedpyright recommended) will be HEAVY.** Expect to per-file-ignore aggressively for ANN/D backlogs. Same for TS-2 (strictTypeChecked).
- **253 Python suppressions** dominated by `type: ignore[attr-defined]` (86) — these come from `pyright basic` not resolving stubs. **basedpyright at "standard" or higher will surface these as real errors.** Translate to `# pyright: ignore[reportAttributeAccessIssue]` with comments OR narrow types (preferred where feasible).
- **src-layout** — `src/pd_ocr_labeler_spa/`. basedpyright `include = ["src", "tests", "scripts"]`. Pre-commit basedpyright `files: ^src/pd_ocr_labeler_spa/.*\.py$` + `entry: uv run basedpyright src/pd_ocr_labeler_spa --level error`. Makefile `typecheck` uses `src/pd_ocr_labeler_spa`.
- **`requires-python = ">=3.13,<3.14"`** — `target-version = "py313"` if needed.
- **Existing pre-commit has `pyright src/`** — REPLACE with the canonical local-hook pattern (basedpyright + `--level error`). Don't keep both.
- **uv lock --check is already present** — preserve, don't duplicate.
- **refresh-version post-* hooks** — preserve as-is.
- **mise.toml present** — pre-commit hooks use `eval "$(mise activate bash --shims)"` guards. Mirror this pattern for the new basedpyright local hook if it needs python access via mise.
- **Recent shipping activity** (FO-1–FO-9 and M9.5 shipped 2026-05-15 per memory) — codebase is actively used; treat lint surfaces with care.
- **Task 3 (remove isort/pylint) is NOOP** — neither present.

---

## Python tasks (1-8) — see [pdomain-prep-for-pgdp plan §Python tasks](2026-05-17-pdomain-prep-for-pgdp-strict-linting.md#python-tasks-1-8-mirror-pdomain-book-tools-f809701) for full structure. Same 8-task sequence; same canonical content. Key deltas:

### Task 1: `.editorconfig` — TRIVIAL (same as pgdp-prep) {#editorconfig-trivial-same-as-pgdp-prep}

### Task 2: Migrate pyright → basedpyright (MODERATE-HEAVY due to 86 attr-defined suppressions) {#migrate-pyright-basedpyright-moderate-heavy-due-to}
- [ ] Replace `[tool.pyright]` with `[tool.basedpyright]` (include = `["src", "tests", "scripts"]`, mode `"standard"`).
- [ ] Add `basedpyright>=1.39.4` to `[dependency-groups] dev`. **Remove existing `"pyright>=1.1"`** (replaced by basedpyright).
- [ ] `uv sync`. Run basedpyright at standard. Translate the 86 `type: ignore[attr-defined]` lines to `# pyright: ignore[reportAttributeAccessIssue]` (basedpyright doesn't honor mypy codes). Mostly mechanical sed-like work; verify each one isn't fixable by narrowing first.
- [ ] **STOP at 90 min** if mechanical translation drags due to context inspection per site.
- [ ] Commit per pdomain-book-tools template.

### Task 3: NOOP {#noop}

### Task 4: Pre-commit (TRIVIAL-MODERATE) {#pre-commit-trivial-moderate}
- [ ] EXTEND existing `.pre-commit-config.yaml` (don't replace — preserve frontend hooks + uv lock check + refresh-version). Add:
  - `default_install_hook_types: [pre-commit, commit-msg]` at top.
  - Extend `pre-commit-hooks` block: add `check-toml`, `check-added-large-files [--maxkb=1000]`, `debug-statements`, `check-merge-conflict`.
  - Add `gitleaks v8.30.1` repo.
  - REPLACE the existing local `pyright src/` hook with the canonical local `basedpyright` hook (entry: `uv run basedpyright src/pd_ocr_labeler_spa --level error`, files: `^src/pd_ocr_labeler_spa/.*\.py$`).
- [ ] Install + run + fix.
- [ ] Commit.

### Task 5: gitlint (TRIVIAL — same as pgdp-prep) {#gitlint-trivial-same-as-pgdp-prep}

### Task 6: Expand ruff select (HEAVY — 87 src files + 123 test files, no prior ANN/D/S/TRY baseline) {#expand-ruff-select-heavy-87-src-files-123-test-fil}
- [ ] Bump ruff pin to `>=0.15.13`.
- [ ] Replace `[tool.ruff.lint]` with canonical, PRESERVING `"B008", "UP042", "RUF002"` in `ignore` and existing per-file-ignores (`tests/*` → `E741`; `scripts/*` → `T201`; etc.).
- [ ] Add `[tool.ruff.lint.pydocstyle] convention = "google"`.
- [ ] Auto-fix; triage. Expect HEAVY ANN/D backlogs — focus on focused per-file-ignores for big subpackages (`api/`, `services/`, `routes/`).
- [ ] **STOP at 90 min** if fix work explodes. Split into ruff-baseline + ruff-ANN-D-defer commits if needed.
- [ ] Commit per pdomain-book-tools template (mention preserved ignore set).

### Task 7: Pytest hardening (MODERATE) {#pytest-hardening-moderate}
- [ ] Replace `[tool.pytest.ini_options]` `addopts` with canonical list (use `--cov=pd_ocr_labeler_spa`, preserve `testpaths = ["tests"]`, `asyncio_mode = "auto"`, existing markers).
- [ ] Preserve `pythonpath = ["src"]` if present (src-layout).
- [ ] Add `filterwarnings = ["error"]`. Triage warning-errors with per-package ignores.
- [ ] Commit.

### Task 8: basedpyright recommended + Makefile/CI (HEAVY — 87 src files) {#basedpyright-recommended-makefileci-heavy-87-src-f}
- [ ] `typeCheckingMode = "recommended"`; add `reportImportCycles = "none"` + deferred-`failOnWarnings` comment.
- [ ] Add `typecheck:` Makefile target running `uv run basedpyright src/pd_ocr_labeler_spa --level error`.
- [ ] Wire into `ci:` between `pre-commit-check` and `openapi-export` (existing ci is `setup frontend-install pre-commit-check openapi-export frontend-build lint test frontend-test`).
- [ ] Run + triage. **STOP at 90 min** if heavy. Per-file-ignores on the worst offenders.
- [ ] Commit.

---

## TypeScript/React tasks (TS-1..TS-5) — see [pdomain-prep-for-pgdp plan §TS tasks](2026-05-17-pdomain-prep-for-pgdp-strict-linting.md#typescriptreact-tasks-ts-1ts-5--per-decision-doc-typescriptreact-stack) for full structure. Same 5-task sequence; same commit-message templates. Key deltas:

### TS-1: Add 4 missing strict flags (only `noUncheckedIndexedAccess` is critical-new) (HEAVY)

Discovery: `strict: true` already covers `strictNullChecks`, `strictFunctionTypes`, `noImplicitAny`. `noUnusedLocals`/`noUnusedParameters`/`noFallthroughCasesInSwitch` already true. **Only `noUncheckedIndexedAccess` is the new explicit-required flag.** Add the others for explicitness.

219 TS files — `noUncheckedIndexedAccess` will surface MANY index-access patterns. **Plan: STOP at 90 min, split into TS-1a/TS-1b/TS-1c if needed by component subdirectory.**

- [ ] Edit `frontend/tsconfig.app.json` to add the 5 canonical flags (same list as pdomain-prep-for-pgdp TS-1).
- [ ] Fix path: optional chaining + post-guard non-null assertion.
- [ ] Commit (can be partial; explicit "TS-1a/1b" in title if split).

### TS-2: strictTypeChecked ESLint (HEAVY)

Same approach as pdomain-prep-for-pgdp TS-2 but at 219-file scale. The existing 15+ `eslint-disable` lines (per discovery) + unknown `any` usage in hooks/Konva will be the hotspots.

- [ ] Add `parserOptions.projectService: true`; switch to `strictTypeChecked` + `stylisticTypeChecked`.
- [ ] Triage; STOP at 90 min.
- [ ] Commit.

### TS-3, TS-4, TS-5: same as pdomain-prep-for-pgdp plan

---

## Self-review checklist

- [ ] Up to 7 Python commits + up to 5 TS commits (some may be split into 2-3 sub-commits if HEAVY).
- [ ] No `--no-verify`.
- [ ] `make ci AI=1` green at tip.
- [ ] `uv run basedpyright src/pd_ocr_labeler_spa --level error` clean.
- [ ] `cd frontend && npx tsc -b --noEmit` clean.
- [ ] `cd frontend && npm run lint` clean.
- [ ] All canonical files (.editorconfig, .gitlint, .pre-commit-config.yaml extended properly).
- [ ] mise activation pattern preserved in any new shell-based pre-commit hooks.

## Notes for the agent

- **This is the largest single rollout in the workspace** (LOC count both Python and TS). Plan for splits. Use the canonical pattern but be aggressive about per-file-ignores for category-wide debt.
- **Don't get into rewriting components for stricter types.** The goal is gate-the-stack, not refactor-the-codebase. Per-file-ignore + TODO comment is the right answer for category-wide ANN/D backlogs.
- Final report: "<N> Python commits + <M> TS commits landed (Task 3 NOOP); final SHA: <X>; make ci AI=1 green; <list of HEAVY tasks that needed splits>; <flagged divergences from pdomain-book-tools>".
