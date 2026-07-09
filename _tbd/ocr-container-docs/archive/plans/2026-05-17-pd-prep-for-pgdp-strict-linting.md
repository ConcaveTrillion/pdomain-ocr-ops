---
status: complete
synced: 2026-05-17
milestone: 13
repo: pdomain/pdomain-prep-for-pgdp
---

# pdomain-prep-for-pgdp — strict linting + type-check rollout (Python + TypeScript/React)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans`. This is rollout step 5 — first repo with BOTH Python and TS/React sides. Mirror pdomain-book-tools `f809701` for the Python canonical pattern AND apply the TS/React canonical additions from decision doc §TypeScript/React stack.

**Reference:**
- Canonical Python pattern memory: `/home/vscode/.claude/projects/-workspaces-ocr-container/memory/project_strict_linting_canonical_pattern.md`
- Decision doc: [`docs/decisions/2026-05-17-strict-linting.md`](../decisions/2026-05-17-strict-linting.md)
- Full canonical Python template: [`docs/plans/2026-05-17-pdomain-book-tools-strict-linting-rollout.md`](2026-05-17-pdomain-book-tools-strict-linting-rollout.md)

**Working directory:** `/workspaces/ocr-container/pdomain-prep-for-pgdp/`
**Python package:** `src/pd_prep_for_pgdp/` (src-layout)
**Current head:** `c1b40b5`
**Discovery:** 80 src + 133 test Python; 132 TS/TSX. Vanilla `[tool.pyright]` hybrid (basic+strict on src). 133 Python suppressions (49 = lazy optional import `type: ignore[import-not-found]`). Frontend pipeline already in `make ci` (frontend-tsc, frontend-eslint, frontend-prettier as local pre-commit hooks). tsconfig.app.json has `strict: true` but is **missing 4 of 5 canonical strict flags** (`noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `noPropertyAccessFromIndexSignature`). ESLint at `recommended` not `strictTypeChecked`. No jsx-a11y. No knip. `@typescript-eslint/no-explicit-any = "warn"`.

---

## Suppression policy

Verbatim from [pdomain-book-tools plan §Suppression policy](2026-05-17-pdomain-book-tools-strict-linting-rollout.md). Same 7 rules; ~90 min per task max.

For TS: same spirit. Auto-fix first (`eslint --fix`, `tsc -b`), then narrow types, then `eslint-disable-next-line` with rule code + comment as last resort.

---

## Notable repo-specific concerns

- **src-layout** — paths use `src/pd_prep_for_pgdp/`. basedpyright `include = ["src", "tests", "scripts"]`. Pre-commit `basedpyright` hook `files: ^src/pd_prep_for_pgdp/.*\.py$`. Makefile `typecheck` runs `uv run basedpyright src/pd_prep_for_pgdp --level error`.
- **`requires-python = ">=3.13,<3.14"`** — set `target-version = "py313"` if needed.
- **Preserve existing ignores**: `"B008", "UP042"` (FastAPI `Depends()` pattern) — keep in canonical replacement.
- **49 `type: ignore[import-not-found]` from optional imports** (cv2, numpy, cupy, modal): these should become `# pyright: ignore[reportMissingImports]` or be wrapped in `if TYPE_CHECKING:` blocks. Mostly mechanical translation.
- **Tests use `httpx`/`asyncio`/`Pydantic v2`** — `filterwarnings = ["error"]` will surface their deprecations. Add `ignore::DeprecationWarning:httpx.*` etc. as they appear with comments.
- **No coverage floor currently** — leave it that way (out of scope).
- **Frontend pre-commit hooks** (frontend-tsc/eslint/prettier) already exist — don't duplicate. Mirror their pattern when adding the basedpyright local hook.
- **`make ci` already includes frontend pipeline** — preserve frontend-build, frontend-format-check, frontend-lint, frontend-test. Add typecheck between pre-commit-check and frontend-build.
- **TS migration is the heaviest lift in this rollout.** Discovery flagged `noUncheckedIndexedAccess` + `strictTypeChecked` ESLint as HEAVY. They interact: strict-type-checked ESLint needs a built TS project, which `noUncheckedIndexedAccess` may break. **Sequence: tsconfig strict flags → fix compile errors → then enable strictTypeChecked ESLint.** Split TS-side into its own multi-commit task if needed.
- **Task 3 (remove isort/pylint) is NOOP** — neither present.

---

## Python tasks (1-8) mirror pdomain-book-tools f809701

### Task 1: Add canonical `.editorconfig` (TRIVIAL) {#add-canonical-editorconfig-trivial}
- [ ] `cat /workspaces/ocr-container/pdomain-book-tools/.editorconfig > .editorconfig`
- [ ] Commit: `chore: add canonical .editorconfig` (mirror pdomain-book-tools commit message).

### Task 2: Migrate pyright → basedpyright (standard mode) (MODERATE) {#migrate-pyright-basedpyright-standard-mode-moderat}
- [ ] Add `"basedpyright>=1.39.4",` to `[dependency-groups] dev`.
- [ ] Replace `[tool.pyright]` + executionEnvironments with:
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
- [ ] `uv sync`. Run `uv run basedpyright src 2>&1 | tail -60`. Triage. For the 49 `type: ignore[import-not-found]` lines: translate to `# pyright: ignore[reportMissingImports]` (basedpyright doesn't honor mypy codes).
- [ ] Commit (per pdomain-book-tools template).

### Task 3: NOOP (no isort/pylint) {#noop-no-isortpylint}

### Task 4: Expand pre-commit (TRIVIAL+) {#expand-pre-commit-trivial}
- [ ] Start from current `.pre-commit-config.yaml` (DO NOT replace — it has the frontend-tsc/eslint/prettier local hooks that need to be preserved). Insert from canonical (pdomain-book-tools `.pre-commit-config.yaml`):
  - Add `default_install_hook_types: [pre-commit, commit-msg]` at top if missing.
  - Add `pre-commit-hooks` additions: `check-toml`, `check-added-large-files [--maxkb=1000]`, `debug-statements`, `check-merge-conflict`.
  - Add `gitleaks` repo (v8.30.1).
  - Add local hooks: `uv-lock-check` (verbatim from pdomain-book-tools) + `basedpyright` (entry: `uv run basedpyright src/pd_prep_for_pgdp --level error`, files: `^src/pd_prep_for_pgdp/.*\.py$`).
- [ ] Install + run all hooks + fix any new findings.
- [ ] Commit (per pdomain-book-tools template).

### Task 5: Add gitlint (TRIVIAL) {#add-gitlint-trivial}
- [ ] `cp /workspaces/ocr-container/pdomain-book-tools/.gitlint .gitlint`
- [ ] Add `"gitlint>=0.19.1",` to dev deps. `uv sync`.
- [ ] Add gitlint repo to `.pre-commit-config.yaml`.
- [ ] Re-install commit-msg hook.
- [ ] Commit.

### Task 6: Expand ruff select to canonical (MODERATE-HEAVY) {#expand-ruff-select-to-canonical-moderate-heavy}
Current 11 codes → 24-rule canonical. Discovery classifies as HEAVY due to 80 src files no prior ANN/D baseline.

- [ ] Bump `"ruff>=0.7"` → `"ruff>=0.15.13"`. `uv sync`.
- [ ] Replace `[tool.ruff.lint]` block with canonical from pdomain-book-tools (lines 122-297 of its pyproject.toml). PRESERVE existing `"B008", "UP042"` in `ignore` (FastAPI). Drop pdomain-book-tools-specific per-file-ignores; KEEP existing pdomain-prep-for-pgdp per-file-ignores for `tests/`, `scripts/`, `src/.../illustrations.py`, `src/.../pipeline/*.py`, etc.
- [ ] Add `[tool.ruff.lint.pydocstyle] convention = "google"`.
- [ ] Auto-fix: `uv run ruff check --fix --unsafe-fixes src/ tests/ scripts/`.
- [ ] Triage remaining. For ANN/D on whole subpackages, add focused per-file-ignores (not blanket fixes). Document deferred backlog in commit message.
- [ ] **STOP at 90 min and report** if fix work exceeds budget.
- [ ] Commit per pdomain-book-tools template (mention preserved B008/UP042).

### Task 7: Pytest hardening (MODERATE) {#pytest-hardening-moderate}
- [ ] Replace `[tool.pytest.ini_options]`:
```toml
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--cov=pd_prep_for_pgdp",
    "--cov-branch",
    "--cov-report=term-missing:skip-covered",
]
testpaths = ["tests"]
pythonpath = ["src"]
asyncio_mode = "auto"
filterwarnings = ["error"]
```
- [ ] Add `"pytest-cov>=6.2.1",` to dev deps. `uv sync`.
- [ ] Run pytest. For warning-errors from httpx/Pydantic/asyncio/transformers: add `ignore::DeprecationWarning:pkg.*` with comments.
- [ ] Commit.

### Task 8: basedpyright recommended + Makefile/CI wiring (MODERATE-HEAVY) {#basedpyright-recommended-makefileci-wiring-moderat}
- [ ] `typeCheckingMode = "standard"` → `"recommended"`; add `reportImportCycles = "none"` + deferred-`failOnWarnings` comment (adapt to FastAPI/Pydantic/optional-extras context).
- [ ] Add `typecheck:` Makefile target:
```makefile
typecheck: ## Run basedpyright at recommended mode (workspace canonical)
	uv run basedpyright src/pd_prep_for_pgdp --level error
```
- [ ] Restructure `ci:` target to insert `typecheck` between `pre-commit-check` and `openapi-export`:
```makefile
ci: setup frontend-install pre-commit-check typecheck openapi-export frontend-build test frontend-format-check frontend-lint frontend-test
```
- [ ] Update pre-commit `basedpyright` entry to use `--level error` (Task 4 may have already done this).
- [ ] Run basedpyright at recommended. Triage. **STOP at 90 min** if heavy.
- [ ] Commit per pdomain-book-tools template.

---

## TypeScript/React tasks (TS-1..TS-5) — per decision doc §TypeScript/React stack

### TS-1: Add 4 missing strict flags to tsconfig.app.json (HEAVY)

Decision doc requires all 5 strict flags. Currently `strict: true` is present; the other 4 are absent.

- [ ] Edit `frontend/tsconfig.app.json` `compilerOptions`:
```jsonc
{
  "compilerOptions": {
    "strict": true,                                  // already on
    "noUncheckedIndexedAccess": true,                // NEW
    "exactOptionalPropertyTypes": true,              // NEW
    "noImplicitOverride": true,                      // NEW
    "noPropertyAccessFromIndexSignature": true,      // NEW
    "useUnknownInCatchVariables": true               // NEW (or rely on strict — both safe to add explicitly)
  }
}
```
- [ ] `cd frontend && npx tsc -b --noEmit 2>&1 | tail -80`. Expected: 10-50 errors. Fix path per decision doc:
  1. Optional chaining (`items[0]?.id`) where TS can't narrow.
  2. Non-null assertion `!` only after a guard, with comment.
  3. For `exactOptionalPropertyTypes`: spread `{ foo?: T }` patterns may need explicit `foo: T | undefined`.
- [ ] `make ci AI=1` must pass (includes `frontend-build` which compiles).
- [ ] **STOP at 90 min** if errors exceed expected; split into TS-1a/1b.
- [ ] Commit:
```
feat(ts): add 5 canonical strict compiler flags to tsconfig.app.json

Per docs/decisions/2026-05-17-strict-linting.md
§TypeScript/React stack. Adds noUncheckedIndexedAccess,
exactOptionalPropertyTypes, noImplicitOverride,
noPropertyAccessFromIndexSignature, useUnknownInCatchVariables.

noUncheckedIndexedAccess is highest-leverage flag for catching
off-by-one and null-dereference patterns. Fixes apply optional
chaining and post-guard non-null assertions per the decision doc's
fix-path guidance.
```

### TS-2: Upgrade typescript-eslint to strictTypeChecked (HEAVY — depends on TS-1)

- [ ] Edit `frontend/eslint.config.js` to add `parserOptions.projectService: true` and switch preset:
```js
import tseslint from 'typescript-eslint';
// ...
export default tseslint.config(
  // ...
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  // existing rules continue
);
```
- [ ] Run `cd frontend && npm run lint 2>&1 | tail -80`. Expect ~30 new type-aware rule findings (unsafe assignment/member/call/return). Triage:
  - Hand-fix: add explicit type or `unknown` cast.
  - Last resort: `// eslint-disable-next-line @typescript-eslint/no-unsafe-X  -- reason` with comment.
- [ ] **STOP at 90 min** if heavy; can be partial commit.
- [ ] Commit:
```
feat(ts/eslint): upgrade to strictTypeChecked + stylisticTypeChecked

Per docs/decisions/2026-05-17-strict-linting.md. Enables
~30 type-aware rules previously skipped: no-unsafe-assignment,
no-unsafe-member-access, no-unsafe-call, no-unsafe-return.
Adds parserOptions.projectService for TS language service access.
```

### TS-3: Flip @typescript-eslint/no-explicit-any to error (MODERATE)

- [ ] In `frontend/eslint.config.js` src-scope rules: change `'@typescript-eslint/no-explicit-any': 'warn'` to `'error'`. Keep test-file scope at `'off'`.
- [ ] Run lint, hand-fix or cast to `unknown`.
- [ ] Commit:
```
feat(ts/eslint): flip no-explicit-any from warn to error (src/)

Per docs/decisions/2026-05-17-strict-linting.md. Tests
remain off (mocks/spies/casts are legit).
```

### TS-4: Add eslint-plugin-jsx-a11y (MODERATE)

- [ ] `cd frontend && npm install --save-dev eslint-plugin-jsx-a11y`.
- [ ] In `eslint.config.js` add `import jsxA11y from 'eslint-plugin-jsx-a11y'` and append to configs: `jsxA11y.flatConfigs.recommended`.
- [ ] Run lint, triage findings on Radix/Konva components.
- [ ] Commit.

### TS-5: Add knip (CI-only, non-blocking) (TRIVIAL)

- [ ] `cd frontend && npm install --save-dev knip`.
- [ ] Create `frontend/knip.json` with sensible config (entry: vite.config.ts + src/main.tsx).
- [ ] Add to Makefile `frontend-lint` target (or new `frontend-knip`):
```makefile
frontend-knip:
	cd frontend && npx knip || true
```
- [ ] Wire into `make ci` after `frontend-lint`. Non-blocking via `|| true` initially.
- [ ] Commit.

---

## Self-review checklist

- [ ] 7 Python commits land (Task 3 NOOP).
- [ ] 5 TS commits land (TS-1..TS-5).
- [ ] No `--no-verify`.
- [ ] `make ci AI=1` green at tip.
- [ ] `uv run basedpyright src/pd_prep_for_pgdp --level error` clean.
- [ ] `cd frontend && npx tsc -b --noEmit` clean.
- [ ] `cd frontend && npm run lint` clean.
- [ ] All canonical files present (.editorconfig, .gitlint, .pre-commit-config.yaml mirroring pdomain-book-tools content + frontend hooks preserved).

## Notes for the agent

- Total: up to 12 commits (7 Python + 5 TS). This is the longest rollout in the workspace.
- Plan extra time for TS-1 + TS-2 — they're the heaviest.
- If a task overruns ~90min, STOP and report. The user may split or pause.
- Final report shape: "<N> Python commits + <M> TS commits landed (Task 3 NOOP); final SHA: <X>; make ci AI=1 green; <flagged divergences>; <whether TS-1/TS-2 needed to be split>".
