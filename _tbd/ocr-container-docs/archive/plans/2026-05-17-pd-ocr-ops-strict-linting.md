---
milestone: 1
repo: ConcaveTrillion/pdomain-ocr-ops
status: complete
synced: 2026-05-17
---

# pdomain-ocr-ops — strict linting + type-check rollout (mirror of pdomain-book-tools)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement task-by-task. This is the **2nd repo** in the workspace-wide rollout; the canonical pattern was established in pdomain-book-tools at commit `f809701` (2026-05-17). For any decision NOT covered here, defer to pdomain-book-tools' final state — your job is to MIRROR what landed there, not invent new patterns.

**Reference:** Canonical pattern memory at `/home/vscode/.claude/projects/-workspaces-ocr-container/memory/project_strict_linting_canonical_pattern.md`. Decision doc: [`docs/superpowers/decisions/2026-05-17-strict-linting.md`](../decisions/2026-05-17-strict-linting.md). Full canonical 8-task template: [`docs/superpowers/plans/2026-05-17-pdomain-book-tools-strict-linting-rollout.md`](2026-05-17-pdomain-book-tools-strict-linting-rollout.md).

**Working directory:** `/workspaces/ocr-container/pdomain-ocr-ops/`
**Package:** `pd_ocr_ops/` (flat layout, NOT src-layout)
**Current head:** `181bb43` (greenfield, 1 commit, scaffold-only)
**Discovery:** 20 source files + 40 test files; minimal ruff (`E F W I`); no basedpyright, no pre-commit, no .editorconfig, no .gitlint. Already-present: 8 `# type: ignore` (GPU optional imports + Pydantic defaults).

---

## Suppression policy (read before starting)

Verbatim from [pdomain-book-tools plan §Suppression policy](2026-05-17-pdomain-book-tools-strict-linting-rollout.md):
1. Auto-fix first: `uv run ruff check --fix` and `uv run ruff format`. If `--fix` resolves it, the agent did nothing.
2. Per-file-ignores for whole categories.
3. Inline `# noqa: RULE  # brief reason` for individual exceptions.
4. For basedpyright: prefer narrowing over `# pyright: ignore`. Use `# pyright: ignore[reportXxx]` only when third-party stubs lag runtime.
5. Drop suppressions to specific rule codes; never blanket.
6. **Docstring backlog (D rule):** add docstrings on functions touched in this rollout; for untouched code use per-file-ignores. Misleading docstrings worse than missing ones.
7. **Time budget per task:** 90 min max. STOP and report if a task overruns.

---

## Notable repo-specific concerns

- **8 existing `# type: ignore` comments** must be upgraded to `# pyright: ignore[reportXxx]` companions when basedpyright lands (Task 7). Pre-existing locations:
  - `pd_ocr_ops/gpu/local_stage.py:76` — `[arg-type]`
  - `pd_ocr_ops/suite/types.py:39,87,127` — `[assignment]` (Pydantic field defaults)
  - `pd_ocr_ops/gpu/device.py:15,25,48,63` — `[import]`, `[return-value]` (optional GPU imports: cupy, torch)
- **GPU optional imports** will trigger basedpyright noise similar to pdomain-book-tools (cupy, torch). The `--level error` pattern from pdomain-book-tools applies — see [canonical pattern memory](file:///home/vscode/.claude/projects/-workspaces-ocr-container/memory/project_strict_linting_canonical_pattern.md) for the deferred-failOnWarnings workaround.
- **Task 3 (remove isort/pylint) is NOOP** — neither is present. Skip the task with an empty commit explanation OR fold into Task 4 as a one-line note.
- **`requires-python = ">=3.11"`** (pdomain-book-tools is `>=3.10,<4.0`; both work with the canonical ruff/basedpyright pins).
- **Initial Makefile is minimal** — only has `lint`, `test`, `ci: lint test`. Task 4 needs to expand it (`pre-commit-check` target) and Task 8 must add `typecheck` + restructure `ci` to include the full canonical chain.

---

## Task 1: Add canonical `.editorconfig` (TRIVIAL) {#add-canonical-editorconfig-trivial}

Copy the canonical `.editorconfig` from pdomain-book-tools verbatim (workspace-canonical file).

- [ ] **Step 1:** Run `cat /workspaces/ocr-container/pdomain-book-tools/.editorconfig` and copy verbatim to `/workspaces/ocr-container/pdomain-ocr-ops/.editorconfig`.
- [ ] **Step 2:** Verify with `cat .editorconfig | head -5` (first line: `# .editorconfig — workspace canonical`).
- [ ] **Step 3:** Commit:
```
chore: add canonical .editorconfig

Workspace-canonical file per docs/superpowers/decisions/2026-05-17-strict-linting.md.
Mirrors pdomain-book-tools f809701. Standardises charset, EOL, indent-style.
```

---

## Task 2: Migrate pyright → basedpyright (TRIVIAL — no pyright config currently exists) {#migrate-pyright-basedpyright-trivial-no-pyright-co}

Since there's no `[tool.pyright]`, this is a fresh install of `[tool.basedpyright]` at `"standard"` mode initially (Task 8 upgrades to `"recommended"`).

- [ ] **Step 1:** In `pyproject.toml` `[dependency-groups] dev`, add `"basedpyright>=1.39.4",` (alphabetical order — first entry).
- [ ] **Step 2:** Append to `pyproject.toml`:
```toml
[tool.basedpyright]
include = ["pd_ocr_ops", "tests", "scripts"]
exclude = ["**/__pycache__", "**/.venv", "**/node_modules"]
typeCheckingMode = "standard"
venvPath = "."
venv = ".venv"

[[tool.basedpyright.executionEnvironments]]
root = "tests"

[[tool.basedpyright.executionEnvironments]]
root = "scripts"
```
(Note: `scripts/` may not exist — that's fine; basedpyright tolerates missing roots.)
- [ ] **Step 3:** Run `uv sync`.
- [ ] **Step 4:** Run `uv run basedpyright pd_ocr_ops 2>&1 | tail -60` and triage diagnostics. Upgrade existing 8 `# type: ignore[...]` comments to ALSO carry `# pyright: ignore[reportXxx]` (basedpyright doesn't honor mypy-style codes). The canonical pattern used in pdomain-book-tools was to REPLACE `type: ignore` with `pyright: ignore` — same here.
- [ ] **Step 5:** Run `make ci AI=1` (currently just `lint test`); should pass.
- [ ] **Step 6:** Commit:
```
chore(types): add basedpyright (standard mode)

Mirrors pdomain-book-tools f809701 canonical pattern. basedpyright is the
workspace-canonical type checker (97.8% typing-spec conformance).
Starting at typeCheckingMode = "standard"; Task 8 upgrades to
"recommended" after ruff expansion and the type-ignore→pyright-ignore
migration land.

Per docs/superpowers/decisions/2026-05-17-strict-linting.md.
```

---

## Task 3: Remove isort + pylint dev deps — **NOOP** (neither present) {#remove-isort-pylint-dev-deps-noop-neither-present}

**SKIP** — discovery confirmed neither `isort` nor `pylint` is in `[dependency-groups] dev`. No commit.

---

## Task 4: Expand pre-commit (TRIVIAL — file doesn't exist; create it) {#expand-pre-commit-trivial-file-doesnt-exist-create}

Create `.pre-commit-config.yaml` mirroring pdomain-book-tools' final state.

- [ ] **Step 1:** Run `cat /workspaces/ocr-container/pdomain-book-tools/.pre-commit-config.yaml` and copy verbatim to `/workspaces/ocr-container/pdomain-ocr-ops/.pre-commit-config.yaml`. Then edit:
  - Replace `pd_book_tools` → `pd_ocr_ops` in the `basedpyright` local hook entry (both `entry:` and `files:`).
- [ ] **Step 2:** Add `"pre-commit>=4.2.0",` to `[dependency-groups] dev` if not present.
- [ ] **Step 3:** Run `uv sync` then `uv run pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg`.
- [ ] **Step 4:** Run `uv run pre-commit run --all-files 2>&1 | tail -60`. Fix any violations (debug statements, malformed YAML, etc.). Do NOT use `--no-verify`.
- [ ] **Step 5:** Add `pre-commit-check` target to Makefile:
```makefile
pre-commit-check: ## Run all pre-commit hooks against all files (read-only check)
	uv run pre-commit run --all-files
```
- [ ] **Step 6:** Commit:
```
chore(precommit): add canonical hooks (gitleaks + check-* + uv-lock-check + basedpyright)

Mirrors pdomain-book-tools f809701 canonical pattern:
- pre-commit-update (auto-rev bumper, manual stage)
- pre-commit-hooks v6.0.0 (trailing/EOF/yaml/json/toml/large-files/debug/merge)
- gitleaks v8.30.1 (staged-diff secret scan)
- ruff-pre-commit v0.15.13 (I-fix → general-fix → format)
- markdownlint-cli2 v0.22.1
- local uv-lock-check + basedpyright (pd_ocr_ops scope, --level error)

Per docs/superpowers/decisions/2026-05-17-strict-linting.md.
```

---

## Task 5: Add gitlint (TRIVIAL) {#add-gitlint-trivial}

- [ ] **Step 1:** Copy canonical `.gitlint` from pdomain-book-tools: `cat /workspaces/ocr-container/pdomain-book-tools/.gitlint` → write to `/workspaces/ocr-container/pdomain-ocr-ops/.gitlint`.
- [ ] **Step 2:** Confirm `.pre-commit-config.yaml` (added Task 4) already includes the gitlint repo + `default_install_hook_types: [pre-commit, commit-msg]`. If you copied verbatim from pdomain-book-tools, both are present.
- [ ] **Step 3:** Add `"gitlint>=0.19.1",` to `[dependency-groups] dev`.
- [ ] **Step 4:** Run `uv sync`. Re-install hooks (Task 4 may not have installed commit-msg hook if `default_install_hook_types` was missing): `uv run pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg`.
- [ ] **Step 5:** Smoke test: `uv run pre-commit run gitlint --hook-stage commit-msg --commit-msg-filename <(git log -1 --pretty=%B)`. Existing commits should pass.
- [ ] **Step 6:** Commit:
```
chore(precommit): add gitlint for commit-message hygiene

Mirrors pdomain-book-tools f809701. gitlint v0.19.1 enforces title ≤72,
body ≤100, bans WIP titles. Pure Python — no Node required.

Per docs/superpowers/decisions/2026-05-17-strict-linting.md.
```

---

## Task 6: Expand ruff `select` to canonical set (MODERATE) {#expand-ruff-select-to-canonical-set-moderate}

Current select: `["E", "F", "W", "I"]`. Target: full 24-rule canonical set from pdomain-book-tools.

- [ ] **Step 1:** Bump ruff pin: in `[dependency-groups] dev`, replace `"ruff>=0.7"` with `"ruff>=0.15.13"`.
- [ ] **Step 2:** Replace the entire `[tool.ruff.lint]` block in `pyproject.toml` with the canonical block. Copy from pdomain-book-tools `pyproject.toml` lines 122-297 (entire `[tool.ruff.lint]` section including `select`, `ignore`, `per-file-ignores`, and `[tool.ruff.lint.pydocstyle]`). Then edit the per-file-ignores:
  - Replace any `pd_book_tools/...` paths with empty (don't carry over pdomain-book-tools' deferred files — pdomain-ocr-ops files are fresh).
  - Keep the canonical baseline: `tests/**/*.py`, `scripts/*.py`, `**/__init__.py`, `**/_*.py`.
- [ ] **Step 3:** `uv sync` then `uv run ruff check --fix --unsafe-fixes pd_ocr_ops/ tests/`.
- [ ] **Step 4:** Re-run without `--fix`: `uv run ruff check pd_ocr_ops/ tests/ 2>&1 | tail -80`. Triage remaining violations per suppression policy. For Pydantic/FastAPI patterns that pdomain-prep-for-pgdp/labeler-spa carry: consider adding `"B008", "UP042"` to the global `ignore` if you see them on the suite/ Pydantic models (FastAPI `Depends()` pattern).
- [ ] **Step 5:** `make ci AI=1` should pass.
- [ ] **Step 6:** Commit:
```
chore(lint): expand ruff select to workspace canonical set

Mirrors pdomain-book-tools f809701. Adds 20 rule groups beyond the prior
baseline (E F W I → full canonical: + N B SIM UP RUF ERA T20 ANN S
C4 PERF TC TID PT RET PL D BLE TRY LOG G).

ruff dep pin bumped to >=0.15.13. New per-file-ignores cover tests,
scripts, __init__.py, private modules per canonical exemption set.
Fix-vs-suppress decisions follow the suppression policy.

Per docs/superpowers/decisions/2026-05-17-strict-linting.md.
```

---

## Task 7: Pytest hardening (MODERATE) {#pytest-hardening-moderate}

- [ ] **Step 1:** Replace `[tool.pytest.ini_options]` block:
```toml
[tool.pytest.ini_options]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--cov=pd_ocr_ops",
    "--cov-branch",
    "--cov-report=term-missing:skip-covered",
    "--cov-report=html",
]
testpaths = ["tests"]
asyncio_mode = "auto"
filterwarnings = [
    "error",
    # Add ignores below as new warnings surface — each with a comment.
]
```
- [ ] **Step 2:** Add `"pytest-cov>=6.2.1",` to `[dependency-groups] dev` if missing. `uv sync`.
- [ ] **Step 3:** Run `uv run pytest 2>&1 | tail -40`. For each warning that becomes an error: if it's third-party noise (FastAPI/Pydantic/httpx/uvicorn deprecations), add `ignore::DeprecationWarning:packagename.*` to filterwarnings with a comment. If it's our code, FIX IT.
- [ ] **Step 4:** Note the post-`--cov-branch` coverage number. (No `fail_under` is currently configured — leave it that way; adding a floor is out of scope.)
- [ ] **Step 5:** `make ci AI=1` should pass.
- [ ] **Step 6:** Commit:
```
test(pytest): adopt filterwarnings=error and --cov-branch

Mirrors pdomain-book-tools f809701. filterwarnings = ['error'] turns silent
deprecations into test failures. --cov-branch measures branch coverage.
Also normalises addopts to a list, adds -ra and --strict-markers /
--strict-config per workspace convention.

Per docs/superpowers/decisions/2026-05-17-strict-linting.md.
```

---

## Task 8: Upgrade basedpyright to `recommended` + Makefile/CI wiring (MODERATE) {#upgrade-basedpyright-to-recommended-makefileci-wir}

- [ ] **Step 1:** In `pyproject.toml` `[tool.basedpyright]`:
  - Change `typeCheckingMode = "standard"` → `typeCheckingMode = "recommended"`.
  - Add `reportImportCycles = "none"` (canonical — structural cycles resolved via TYPE_CHECKING).
  - Add comment block before `# failOnWarnings = true` documenting the deferral (mirror pdomain-book-tools' comment):
```toml
# NOTE: failOnWarnings deferred — recommended mode surfaces warnings from
# optional GPU dep stubs (cupy/torch) that lag runtime. Enable incrementally
# as stub coverage improves.
# failOnWarnings = true
```
- [ ] **Step 2:** Add `typecheck` target to Makefile:
```makefile
typecheck: ## Run basedpyright at recommended mode (workspace canonical)
	uv run basedpyright pd_ocr_ops --level error
```
- [ ] **Step 3:** Restructure the `ci:` target to mirror pdomain-book-tools:
```makefile
ci: ## Run complete CI pipeline (setup, pre-commit, lint-check, typecheck, test, build)
	@$(MAKE) --no-print-directory setup
	@$(MAKE) --no-print-directory pre-commit-check
	@$(MAKE) --no-print-directory lint-check
	@$(MAKE) --no-print-directory typecheck
	@$(MAKE) --no-print-directory test
```
(Add `setup`, `lint-check` targets if missing — copy from pdomain-book-tools Makefile.)
- [ ] **Step 4:** Run `uv run basedpyright pd_ocr_ops --level error 2>&1 | tail -80`. Triage. For optional-GPU import warnings (cupy/torch unknown-member): add `# pyright: ignore[reportXxx]` inline with comment, OR if a whole file is GPU-dep-heavy add a per-file-ignore via `executionEnvironments` (sparingly).
- [ ] **Step 5:** Update the pre-commit `basedpyright` hook entry to use `--level error` (mirror pdomain-book-tools):
```yaml
      entry: uv run basedpyright pd_ocr_ops --level error
      name: basedpyright type check (recommended mode; workspace canonical)
```
- [ ] **Step 6:** Run `make ci AI=1` end-to-end. Must pass.
- [ ] **Step 7:** Commit:
```
feat(types): basedpyright recommended mode + wire into make ci

Mirrors pdomain-book-tools f809701. typeCheckingMode = 'recommended'
catches unannotated functions, inferred-Any propagation, untyped
decorators, and missing return types.

failOnWarnings deferred via --level error (in both pre-commit hook
and Makefile typecheck target) due to optional GPU dep stub noise
(cupy/torch). Enable incrementally as stubs improve.

make typecheck added as discrete target; make ci now invokes
setup → pre-commit-check → lint-check → typecheck → test in order.

Per docs/superpowers/decisions/2026-05-17-strict-linting.md.
```

---

## Self-review checklist

- [ ] 7 commits land in order (Task 3 NOOP skipped): editorconfig, basedpyright, pre-commit, gitlint, ruff expansion, pytest hardening, basedpyright recommended.
- [ ] No commit uses `--no-verify`.
- [ ] `make ci AI=1` is green at tip.
- [ ] `uv run basedpyright pd_ocr_ops --level error` is clean.
- [ ] `uv run ruff check pd_ocr_ops tests` is clean.
- [ ] All 8 pre-existing `# type: ignore` have `# pyright: ignore[reportXxx]` companions (or were replaced).
- [ ] `.editorconfig`, `.gitlint`, `.pre-commit-config.yaml` at repo root, all mirroring pdomain-book-tools exact content.
- [ ] `default_install_hook_types: [pre-commit, commit-msg]` at top of `.pre-commit-config.yaml`.

## Notes for the agent

- This plan MIRRORS pdomain-book-tools `f809701`. For any step where the procedure doesn't quite match what you find, defer to pdomain-book-tools' final config files as ground truth.
- The greenfield nature should make this much faster than pdomain-book-tools (which had heavy legacy debt). Expect Tasks 6 + 8 to be MODERATE not HEAVY.
- If a task overruns ~90min, STOP and report; do not silently expand scope.
- Final report shape: "7 of 7 commits landed (Task 3 NOOP); final SHA: <X>; make ci AI=1 green at recommended mode + --level error; <N> suppressions added; <flagged divergences from pdomain-book-tools>".
