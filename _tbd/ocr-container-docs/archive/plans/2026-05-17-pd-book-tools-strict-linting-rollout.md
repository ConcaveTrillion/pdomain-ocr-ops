---
status: complete
synced: 2026-05-17
milestone: 11
repo: pdomain/pdomain-book-tools
---

# pdomain-book-tools — strict linting + type-check rollout (canonical pattern)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This is the **first** repo in the workspace-wide strict-linting rollout; every later pd-* repo will mirror the patterns established here. Be careful about decisions that don't have prior precedent — they become the workspace canon.

**Goal:** Migrate pdomain-book-tools to the strict lint + type-check stack captured in [`docs/decisions/2026-05-17-strict-linting.md`](../decisions/2026-05-17-strict-linting.md). Establishes the canonical config, suppression patterns, and pre-commit shape that pdomain-ocr-ops, pdomain-ocr-cli, pdomain-ocr-synth, pdomain-prep-for-pgdp, pdomain-ocr-labeler-spa, pd-png-optimizer, pdomain-ui, pdomain-index-npm, and (eventually) the rewritten trainer + replacement labeler will copy.

**Architecture:** Eight commits, each a discrete unit. Sequence is ordered so blocking work happens first (basedpyright migration + config additions) and the heaviest fix-work surfaces last (`recommended` mode + ruff strict groups). Each commit ends with `make ci AI=1` green. No `--no-verify`; if a hook complains, fix the underlying issue.

**Tech Stack:** Python 3.10+, hatchling, uv. Adds direct dev deps: `basedpyright>=1.39.4`, `gitlint>=0.19.1`. Removes direct dev deps: `isort`, `pylint`, `pyright` (was indirect via pre-commit only). Bumps `ruff>=0.15.13`.

**Working directory for all commands:** `/workspaces/ocr-container/pdomain-book-tools/`

---

## Suppression policy (read before starting)

Every rule expansion in this plan will surface violations. The agent has discretion to fix vs suppress, guided by these rules:

1. **Auto-fix first.** Run `uv run ruff check --fix` and `uv run ruff format` before considering anything a "violation". If `--fix` resolves it, the agent did nothing.
2. **Per-file-ignores for whole categories.** If a rule fires on every file in `tests/` or every file in `**/_*.py`, add a `[tool.ruff.lint.per-file-ignores]` entry rather than inline `# noqa` markers.
3. **Inline `# noqa: RULE` for individual exceptions.** Always include a brief comment explaining why: `# noqa: PLR2004  # well-known HTTP status code`.
4. **For basedpyright: prefer narrowing over `# type: ignore`.** Add explicit type hints, `cast(...)` from `typing`, or `assert isinstance(...)` to narrow. Use `# type: ignore[...]` only when the runtime is provably correct but the type system can't prove it (e.g., third-party stubs that lag the runtime).
5. **Drop `# type: ignore` to specific rule codes.** Never `# type: ignore` blanket. Always `# type: ignore[reportAttributeAccessIssue]` or similar so the suppression is narrow.
6. **Docstring backlog (rule `D`):** Add docstrings on every public function/class touched in this rollout. For untouched code, use the per-file-ignores pattern; do NOT add a docstring without reading the function. Misleading docstrings are worse than missing ones.
7. **Time budget per task:** if a task's fix work exceeds ~90 minutes, STOP and report. The agent should not silently expand scope; the user can decide whether to keep going or split the task.

---

## Task 1: Switch pyright → basedpyright (config + deps; keep `typeCheckingMode = "standard"` initially) {#switch-pyright-basedpyright-config-deps-keep-typec}

**Files:**
- Modify: `pyproject.toml` (remove `[tool.pyright]`, add `[tool.basedpyright]`, update `[dependency-groups]`)
- Modify: `.pre-commit-config.yaml` (no change in this task; basedpyright local hook lands in Task 4)

- [ ] **Step 1: Inspect the current pyright config**

Run: `grep -n "^\[tool\.pyright\]\|^\[\[tool.pyright" pyproject.toml`

Expected: `[tool.pyright]` at one line + `[[tool.pyright.executionEnvironments]]` at another. The current config is `typeCheckingMode = "basic"` overall with `"strict"` for `src`.

- [ ] **Step 2: Add `basedpyright>=1.39.4` to dev deps**

In `pyproject.toml`, locate `[dependency-groups] dev = [...]`. Insert (preserving alphabetical order):

```toml
    "basedpyright>=1.39.4",
```

immediately after the opening `dev = [` line and before the next existing entry.

- [ ] **Step 3: Replace `[tool.pyright]` with `[tool.basedpyright]`**

In `pyproject.toml`, replace the entire two-block sequence:

```toml
[tool.pyright]
include = ["src", "tests", "scripts"]
typeCheckingMode = "basic"

[[tool.pyright.executionEnvironments]]
root = "src"
typeCheckingMode = "strict"
```

with:

```toml
[tool.basedpyright]
# Include source, tests, and scripts. Match the layout this repo uses.
include = ["pd_book_tools", "tests", "scripts"]
exclude = ["**/__pycache__", "**/.venv", "**/node_modules"]

# Start at "standard" — Task 7 upgrades to "recommended" after the easy wins land.
# "standard" gives us most basedpyright value without the unannotated-function
# avalanche. "recommended" mode is the workspace target per the strict-linting
# decisions doc.
typeCheckingMode = "standard"

# Tell basedpyright where the venv is so it finds third-party stubs.
venvPath = "."
venv = ".venv"

# Per-execution-environment overrides: tests get more leniency for now.
[[tool.basedpyright.executionEnvironments]]
root = "tests"
typeCheckingMode = "standard"

[[tool.basedpyright.executionEnvironments]]
root = "scripts"
typeCheckingMode = "standard"
```

Note: the `include` path is `pd_book_tools` (the package directory), not `src`. Confirm by running `ls pd_book_tools/` — if the package lives under a different name, adjust.

- [ ] **Step 4: Sync deps**

Run: `uv sync`
Expected: lockfile updated; `basedpyright 1.39.x` and its `nodejs-wheel` bundled Node appear in the resolution.

- [ ] **Step 5: Smoke-test basedpyright**

Run: `uv run basedpyright --version`
Expected: prints `basedpyright 1.39.x` (or later).

Run: `uv run basedpyright pd_book_tools/ocr/review.py`
Expected: exits 0 (`review.py` is a small clean dataclass — should pass with no diagnostics).

- [ ] **Step 6: Run the standard-mode check across the whole repo and triage**

Run: `uv run basedpyright 2>&1 | tail -60`

Expected: a non-zero count of diagnostics surfaces (this is the migration). Most should be of category `reportMissingTypeStubs` (for third-party packages without stubs), `reportUnknownArgumentType`, or `reportAttributeAccessIssue`.

Fix policy for this task:
- `reportMissingTypeStubs`: add `# pyright: reportMissingTypeStubs=false` at the top of files that import the offending package, OR install the appropriate `types-<pkg>` stub if available. Prefer the latter when an official stub exists.
- `reportUnknownArgumentType` on `pd_book_tools.*` internal calls: fix by adding type hints to the call site or the called function.
- `reportAttributeAccessIssue` on third-party (e.g., `cv2.*`, `numpy.*`): add `# type: ignore[reportAttributeAccessIssue]` inline with a comment.

Apply the suppression policy from the top of this plan: prefer narrowing/annotation over `# type: ignore`. The goal of Task 1 is just to get `standard` mode clean; `recommended` is Task 7.

- [ ] **Step 7: Run `make ci AI=1`**

Run: `make ci AI=1`
Expected: passes. (`ci` does NOT currently include basedpyright; we add it in Task 6. So this step confirms nothing else broke.)

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock
# Plus any files where you added suppression comments
git add pd_book_tools/ tests/ scripts/
git commit -m "chore(types): migrate from pyright to basedpyright (standard mode)

basedpyright is the workspace-canonical type checker per the
2026-05-17 strict-linting decisions. It is stricter than vanilla
pyright (97.8% typing-spec conformance vs lower); bundles its own
Node runtime via nodejs-wheel; ships a 'recommended' mode that
catches unannotated functions vanilla pyright skips.

Starting at typeCheckingMode = 'standard' for now; Task 7 upgrades
to 'recommended' once the easy wins from ruff expansion + pre-commit
additions have landed.

No behavior change. Suppression comments added inline where
third-party stubs lag the runtime (cv2, etc.); see the inline noqa
comments for the rationale of each."
```

---

## Task 2: Add canonical `.editorconfig` {#add-canonical-editorconfig}

**Files:**
- Create: `.editorconfig`

- [ ] **Step 1: Write `.editorconfig`**

Create `.editorconfig` at repo root with this exact content (it is the workspace canonical config per the decisions doc):

```ini
# .editorconfig — workspace canonical
# Establishes file conventions editors respect before any formatter runs.
root = true

[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 4
trim_trailing_whitespace = true
insert_final_newline = true

[*.{ts,tsx,js,jsx,json,yaml,yml,toml,md}]
indent_size = 2

[*.{rs}]
indent_size = 4

[Makefile]
indent_style = tab

[*.md]
trim_trailing_whitespace = false
```

- [ ] **Step 2: Verify**

Run: `cat .editorconfig | head -5`
Expected: `# .editorconfig — workspace canonical` is the first line.

- [ ] **Step 3: Commit**

```bash
git add .editorconfig
git commit -m "chore: add canonical .editorconfig

Workspace-canonical file per docs/decisions/2026-05-17-strict-linting.md.
Standardises charset, EOL, indent-style for all file types editors recognise.
Useful for LLM editor environments without format-on-save."
```

---

## Task 3: Remove `isort` and `pylint` from dev deps {#remove-isort-and-pylint-from-dev-deps}

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Confirm both are present**

Run: `grep -n "isort\|pylint" pyproject.toml`

Expected: two lines: `"isort>=6.0",` and `"pylint>=3.3.7",` in the `[dependency-groups] dev` list.

- [ ] **Step 2: Remove both lines**

In `pyproject.toml`, delete:

```toml
    "isort>=6.0",
```

and:

```toml
    "pylint>=3.3.7",
```

from the `[dependency-groups] dev` array.

- [ ] **Step 3: Sync deps**

Run: `uv sync`
Expected: lockfile updated; both packages removed.

- [ ] **Step 4: Confirm nothing in the repo imports them**

Run: `grep -rn "^import isort\|^from isort\|^import pylint\|^from pylint" pd_book_tools tests scripts`
Expected: no output. (If anything does import them, that's a pre-existing dependency on a tool we're removing — surface as a blocker.)

- [ ] **Step 5: Run `make ci AI=1`**

Expected: passes (these were dev-only tools; nothing in src or tests uses them).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore(deps): remove isort and pylint dev deps

ruff 'I' rules subsume standalone isort; ruff 'PL' rules cover ~90%
of pylint's correctness rules at 50× speed. Removing both eliminates
dev-dep churn without losing any check that ruff doesn't already
provide.

Per docs/decisions/2026-05-17-strict-linting.md."
```

---

## Task 4: Expand pre-commit hooks (gitleaks, check-*, debug-statements, uv-lock-check, basedpyright local hook) {#expand-pre-commit-hooks-gitleaks-check-debug-state}

**Files:**
- Modify: `.pre-commit-config.yaml`

- [ ] **Step 1: Inspect the current `.pre-commit-config.yaml`**

Run: `cat .pre-commit-config.yaml`

Identify the existing structure (pre-commit-update at top, pre-commit-hooks middle, ruff-pre-commit, markdownlint-cli2). Keep all of these.

- [ ] **Step 2: Extend the `pre-commit-hooks` block**

Find the `- repo: https://github.com/pre-commit/pre-commit-hooks` block. Replace its `hooks:` list with the canonical set:

```yaml
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-toml
      - id: check-added-large-files
        args: [--maxkb=1000]
      - id: debug-statements      # catches leftover pdb/ipdb/breakpoint()
      - id: check-merge-conflict
```

Bump the `rev:` to `v6.0.0` if it's older.

- [ ] **Step 3: Add the gitleaks hook**

Insert (alphabetically, between `pre-commit-hooks` and `ruff-pre-commit`):

```yaml
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.2
    hooks:
      - id: gitleaks
```

- [ ] **Step 4: Add local hooks for `uv-lock-check` and `basedpyright`**

Append at the bottom of `.pre-commit-config.yaml`:

```yaml
  - repo: local
    hooks:
      - id: uv-lock-check
        name: uv.lock is in sync with pyproject.toml
        entry: uv lock --check
        language: system
        stages: [pre-commit]
        pass_filenames: false
        files: ^(pyproject\.toml|uv\.lock)$

      - id: basedpyright
        name: basedpyright type check (standard mode for now; Task 7 upgrades)
        entry: uv run basedpyright
        language: system
        stages: [pre-commit]
        pass_filenames: false
        files: ^pd_book_tools/.*\.py$
```

The `files:` pattern restricts the type-check hook to source files only (not tests/scripts). Tests/scripts still get checked via `make ci`'s full basedpyright run added in Task 6.

- [ ] **Step 5: Update ruff-pre-commit pin**

Locate the `- repo: https://github.com/astral-sh/ruff-pre-commit` block and bump its `rev:` to `v0.15.13`. (Matches the version we'll pin in pyproject in Task 6.)

- [ ] **Step 6: Install the new hooks**

Run: `uv run pre-commit install`
Expected: installs `.git/hooks/pre-commit`.

- [ ] **Step 7: Run pre-commit against the whole repo to surface any new violations**

Run: `uv run pre-commit run --all-files 2>&1 | tail -60`
Expected: each new hook reports findings. `gitleaks` should be clean (no secrets in the codebase); `check-toml` should pass; `debug-statements` should be clean. `basedpyright` runs again (Task 1 already cleared standard mode).

If any hook fails, fix the violations (remove debug breakpoints, fix malformed TOML/JSON, etc.) before continuing. Do NOT use `--no-verify`.

- [ ] **Step 8: Commit**

```bash
git add .pre-commit-config.yaml
# Plus any files fixed by the new hooks
git add -u
git commit -m "chore(precommit): add gitleaks + check-* + debug-statements + uv-lock-check + basedpyright local hook

Per docs/decisions/2026-05-17-strict-linting.md:
- gitleaks v8.24.2: scans staged diff for secrets (<100ms typical)
- check-toml / check-json / check-added-large-files: catch malformed
  configs and oversized binary commits before they land
- debug-statements: catches leftover pdb/ipdb/breakpoint() calls
- check-merge-conflict: blocks committing unresolved merge markers
- uv-lock-check (local): ensures uv.lock stays in sync with pyproject.toml
- basedpyright (local, src only): catches type errors at commit time

Ruff rev bumped to v0.15.13 to match the pyproject pin landing in
the upcoming ruff-expansion commit."
```

---

## Task 5: Add `gitlint` for commit-message hygiene {#add-gitlint-for-commit-message-hygiene}

**Files:**
- Modify: `.pre-commit-config.yaml`
- Create: `.gitlint`

- [ ] **Step 1: Create the canonical `.gitlint` config**

Create `.gitlint` at repo root:

```ini
[general]
ignore=body-is-missing
# Match the workspace 100-char convention (matches Python line-length).
[title-max-length]
line-length=72
[title-must-not-contain-word]
words=WIP
[body-max-line-length]
line-length=100
```

(72 for title is the git-convention default; 100 for body matches the workspace Python `line-length`.)

- [ ] **Step 2: Add the gitlint hook to `.pre-commit-config.yaml`**

Append to the existing `repos:` list (after the `local` hooks block from Task 4):

```yaml
  - repo: https://github.com/jorisroovers/gitlint
    rev: v0.19.1
    hooks:
      - id: gitlint
        stages: [commit-msg]
```

Note: gitlint runs on `commit-msg` stage, not `pre-commit`. The `default_install_hook_types` at the top of the file needs to include `commit-msg` so the hook actually fires. If `default_install_hook_types` isn't set, add it at the top of the file:

```yaml
default_install_hook_types: [pre-commit, commit-msg]
```

- [ ] **Step 3: Re-install hooks (commit-msg hook is separate)**

Run: `uv run pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg`
Expected: installs both `.git/hooks/pre-commit` and `.git/hooks/commit-msg`.

- [ ] **Step 4: Smoke-test gitlint against the existing log**

Run: `uv run pre-commit run gitlint --hook-stage commit-msg --commit-msg-filename <(git log -1 --pretty=%B)`

Expected: passes (the recent commits in this repo follow the conventional-commits style gitlint expects).

If gitlint complains about the most recent commit, the issue is either (a) a real violation in the message — fix gitlint config to be more lenient, or (b) a config-shape issue with the hook. Investigate.

- [ ] **Step 5: Commit**

```bash
git add .gitlint .pre-commit-config.yaml
git commit -m "chore(precommit): add gitlint for commit-message hygiene

gitlint v0.19.1 enforces title length ≤72, body line length ≤100,
and bans WIP-style titles. Matches the workspace conventional-commits
convention already followed informally.

Pure Python (no Node required), runs at commit-msg stage.
Per docs/decisions/2026-05-17-strict-linting.md."
```

---

## Task 6: Expand ruff `select` to the full proposed set + bump ruff pin {#expand-ruff-select-to-the-full-proposed-set-bump-r}

**Files:**
- Modify: `pyproject.toml`

This is the biggest commit by violation surface. Budget time accordingly; apply the suppression policy strictly.

- [ ] **Step 1: Bump the ruff dev-dep pin**

In `pyproject.toml` `[dependency-groups] dev`:

```toml
    "ruff>=0.15.13",
```

(Replace the existing `"ruff>=0.12.5"`.)

- [ ] **Step 2: Sync deps**

Run: `uv sync`

- [ ] **Step 3: Replace the entire `[tool.ruff.lint]` block**

In `pyproject.toml`, replace:

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "B", "SIM", "UP", "RUF", "ERA", "T20"]
ignore = [
    "E741",
    "E501",
]

[tool.ruff.lint.per-file-ignores]
"scripts/*.py" = ["T201"]
"tests/fixtures/layout_regression/*.py" = ["T201"]
```

with the canonical workspace config:

```toml
[tool.ruff.lint]
select = [
    # Current baseline
    "E", "W",       # pycodestyle errors/warnings
    "F",            # pyflakes
    "I",            # isort (replaces standalone isort)
    "N",            # pep8-naming
    "B",            # flake8-bugbear — mutable defaults, broad excepts, etc.
    "SIM",          # flake8-simplify
    "UP",           # pyupgrade
    "RUF",          # ruff-specific rules
    "ERA",          # eradicate — commented-out code
    "T20",          # flake8-print
    # Added per 2026-05-17 strict-linting decisions
    "ANN",          # flake8-annotations — force type hints on all sigs
    "S",            # flake8-bandit — security rules
    "C4",           # flake8-comprehensions
    "PERF",         # perflint — performance anti-patterns
    "TC",           # flake8-type-checking — move type-only imports to TYPE_CHECKING
    "TID",          # flake8-tidy-imports
    "PT",           # flake8-pytest-style
    "RET",          # flake8-return
    "PL",           # pylint subset (PLC + PLE + PLR + PLW)
    "D",            # pydocstyle
    # Added per 2026-05-17 guidelines audit (BLE/TRY/LOG/G)
    "BLE",          # flake8-blind-except — catches except Exception/BaseException without re-raise
    "TRY",          # tryceratops — TRY400 enforces log.exception over log.error in except
    "LOG",          # flake8-logging — proper log.* usage
    "G",            # flake8-logging-format — lazy formatting in log calls
]

ignore = [
    # Pre-existing: 'l' is canonical loop-var name for "line" in OCR layout code
    "E741",
    # Pre-existing: long docstrings + error messages + URLs; line-length is not load-bearing
    "E501",
    # D conflicts (pick one convention; we use google)
    "D203",         # one-blank-line-before-class — conflicts with D211
    "D212",         # multi-line summary first line — conflicts with D213
    # D rules at module/init level are noise
    "D100",         # missing docstring in public module
    "D104",         # missing docstring in public package
    "D107",         # missing docstring in __init__
    # ANN self/cls noise
    "ANN101",
    "ANN102",
    # PL: some refactor suggestions too aggressive
    "PLR0913",      # too-many-arguments
    "PLR2004",      # magic-value-comparison (re-enable for src only if we want it)
    # TRY003: long messages in raise — common pattern in this codebase
    "TRY003",
    # COM812 conflicts with formatter — leave to ruff format
]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
# Tests: relax security + print + annotations + docstrings
"tests/**/*.py" = ["S101", "S105", "S106", "S311", "T201", "ANN", "D", "PLR2004"]
# Scripts and CLI fixtures: print() is the output mechanism
"scripts/*.py" = ["T201", "D"]
"tests/fixtures/layout_regression/*.py" = ["T201"]
# __init__.py re-exports: F401 unused-imports + TC + D are noise
"**/__init__.py" = ["D104", "F401", "TC"]
# Private modules (leading underscore): D docstrings optional
"**/_*.py" = ["D"]

[tool.ruff.lint.isort]
known-first-party = ["pd_book_tools"]
```

- [ ] **Step 4: Run ruff with auto-fix**

Run: `uv run ruff check --fix --unsafe-fixes pd_book_tools/ tests/ scripts/`

Expected: dozens to hundreds of auto-fixes applied. Most violations of the new rule groups have fixes available.

After auto-fix, re-run without `--fix`:

Run: `uv run ruff check pd_book_tools/ tests/ scripts/ 2>&1 | tail -80`

Expected: remaining violations are the ones the agent must hand-fix or suppress.

- [ ] **Step 5: Triage remaining violations by rule group**

For each rule code in the output, decide one of:
1. **Hand-fix** (preferred): annotate the function, add the docstring, restructure the except, etc.
2. **Per-file-ignore** (acceptable when one rule fires on a single file's ENTIRE category): add to `[tool.ruff.lint.per-file-ignores]`.
3. **Inline `# noqa: RULE`**: with a brief comment, when the violation is intentional in this one spot.

Reminders from the suppression policy at top of this plan:
- Never add a docstring without reading the function. Use `# noqa: D102` with a TODO if a meaningful docstring isn't writable in this commit.
- For `BLE001` and `TRY*` violations: prefer fixing the exception handling per `docs/python-coding-guidelines.md` patterns. These rules ARE the workspace coding guidelines as tools — suppressing them defeats the purpose.

Suggested per-rule fix patterns:
- `ANN201` / `ANN204`: add `-> None` or `-> ReturnType` to function signatures.
- `D102` / `D103`: add a one-line summary docstring, or `# noqa: D103  # TODO: docstring` if writing one would require reading code beyond this commit's scope.
- `BLE001` (blind except): change `except Exception:` to a narrow type, OR add `re-raise` if logging-then-propagating is the intent. If the blind-catch is genuinely intentional (e.g., an "anything else" final arm), add `# noqa: BLE001  # final fallback arm`.
- `TRY400` (use log.exception in except): replace `log.error("...", exc)` with `log.exception("...")` inside `except` blocks.
- `S101` (assert in non-test code): if a runtime assert is intentional, replace with explicit `if not ...: raise AssertionError(...)`.
- `PERF401`: replace manual list-building loops with `list comprehension`.
- `TC001` / `TC002`: move type-only imports into `if TYPE_CHECKING:` blocks, with `from __future__ import annotations` at the top of the file if not present.

- [ ] **Step 6: Run `make ci AI=1`**

Run: `make ci AI=1`
Expected: passes after fixes/suppressions land. If a basedpyright diagnostic appears for the first time (because `from __future__ import annotations` was added and some forward-ref now needs explicit handling), fix it here.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock
git add pd_book_tools/ tests/ scripts/
git commit -m "chore(lint): expand ruff select to workspace canonical set

Adds 13 rule groups beyond the prior baseline:
- ANN S C4 PERF TC TID PT RET PL D (per 2026-05-17 strict-linting decisions)
- BLE TRY LOG G (per 2026-05-17 guidelines audit; rolls
  docs/python-coding-guidelines.md exception/logging rules into tooling)

ruff dep pin bumped to >=0.15.13. New per-file-ignores cover the
canonical exemption set: tests, scripts, __init__.py, private modules.

Fix-vs-suppress decisions follow the suppression policy in
docs/plans/2026-05-17-pdomain-book-tools-strict-linting-rollout.md
- prefer narrowing/annotation over noqa where possible. Suppression
sites have inline comments explaining why."
```

---

## Task 7: Pytest hardening (`filterwarnings = ["error"]` + `--cov-branch`) {#pytest-hardening-filterwarnings-error-cov-branch}

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update `[tool.pytest.ini_options]`**

Replace the existing block:

```toml
[tool.pytest.ini_options]
addopts = "--cov=pd_book_tools --cov-report=term-missing:skip-covered --cov-report=html"
markers = [
    "gpu: marks tests as requiring GPU/CUDA functionality",
    "cupy: marks tests as requiring CuPy library",
    "torch_cuda: marks tests as requiring PyTorch CUDA",
    "slow: marks tests as slow (use -m 'not slow' to skip)",
    "integration: marks tests as integration tests"
]
filterwarnings = [
    "ignore::UserWarning:cupy.*",
    "ignore::FutureWarning:torch.*"
]
```

with:

```toml
[tool.pytest.ini_options]
addopts = [
    "-ra",                       # show short summary of all non-pass outcomes
    "--strict-markers",          # fail on unknown markers
    "--strict-config",           # fail on unknown pytest config keys
    "--cov=pd_book_tools",
    "--cov-branch",              # measure branch coverage (gates except-path testing)
    "--cov-report=term-missing:skip-covered",
    "--cov-report=html",
]
markers = [
    "gpu: marks tests as requiring GPU/CUDA functionality",
    "cupy: marks tests as requiring CuPy library",
    "torch_cuda: marks tests as requiring PyTorch CUDA",
    "slow: marks tests as slow (use -m 'not slow' to skip)",
    "integration: marks tests as integration tests",
]
filterwarnings = [
    # Treat all warnings as errors — surfaces deprecation issues at LLM-iteration time.
    "error",
    # Pre-existing ignores: third-party noise that isn't actionable here.
    "ignore::UserWarning:cupy.*",
    "ignore::FutureWarning:torch.*",
    # Add new ignores below as new warnings surface — each one with a comment
    # explaining the package and why we tolerate it.
]
```

- [ ] **Step 2: Run pytest to surface previously-hidden warnings**

Run: `uv run pytest 2>&1 | tail -40`

Expected: each previously-tolerated warning now becomes a test failure. Triage:
- If the warning is third-party noise that nothing in this codebase produces (e.g., a deprecation in `transformers`), add an `ignore::...:<package>.*` filterwarnings entry with a comment.
- If the warning is something OUR code produces (e.g., a `DeprecationWarning` because we're calling a deprecated stdlib API), FIX IT — don't suppress.

Iterate until `uv run pytest` exits 0 again.

- [ ] **Step 3: Check the coverage drop**

The `--cov-branch` flag will likely drop the measured coverage percentage by 3-8% because uncovered `except` branches now count as misses.

Run: `uv run pytest --cov=pd_book_tools --cov-branch --cov-report=term 2>&1 | tail -10`

Expected: coverage percentage printed. Note the number.

- [ ] **Step 4: Pin the new coverage floor (if a floor is configured)**

Check whether `[tool.coverage.report] fail_under` exists in `pyproject.toml`:

Run: `grep -n "fail_under" pyproject.toml`

- If `fail_under` is set: update it to **2 percentage points below** the post-branch coverage number from Step 3. This gives a small ratchet buffer while the branch-coverage migration completes. Add a TODO comment.
- If `fail_under` is not set: leave it. Adding a coverage floor is its own decision and out of scope for this plan.

- [ ] **Step 5: Run `make ci AI=1`**

Run: `make ci AI=1`
Expected: passes (all warnings either fixed or ignored; coverage floor met if configured).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml
git commit -m "test(pytest): adopt filterwarnings=error and --cov-branch

filterwarnings = ['error'] turns silent deprecations into test
failures so LLM iteration surfaces them immediately. Pre-existing
third-party ignores (cupy UserWarning, torch FutureWarning) are
preserved verbatim.

--cov-branch measures branch coverage in addition to line coverage,
which gates the syntactic portion of guideline #22 (test the error
path, not just the happy path). Coverage floor (if configured)
ratcheted down 2pp to absorb the migration; ratchet up incrementally
once branch-coverage gaps land tests.

Also normalises addopts to a list (multi-line, sorted), adds -ra
and --strict-markers / --strict-config per workspace convention.

Per docs/decisions/2026-05-17-strict-linting.md."
```

---

## Task 8: Upgrade basedpyright to `recommended` mode + Makefile/CI integration + final `make ci AI=1` {#upgrade-basedpyright-to-recommended-mode-makefilec}

**Files:**
- Modify: `pyproject.toml` (basedpyright config + `failOnWarnings`)
- Modify: `Makefile` (add `typecheck` target, wire into `ci`)
- Modify: `.github/workflows/*.yml` (CI annotations, if present)

This is the heaviest fix-work commit. Budget time accordingly.

- [ ] **Step 1: Upgrade `[tool.basedpyright]` to `recommended` mode**

In `pyproject.toml`, change:

```toml
typeCheckingMode = "standard"
```

to:

```toml
typeCheckingMode = "recommended"
failOnWarnings = true
```

For the test/script execution environments, leave at `"standard"` for this rollout (per the policy: tests are noisier; the recommended-mode value comes from src/).

- [ ] **Step 2: Add the `typecheck` Makefile target**

Find the `ci:` target in `Makefile` (around line 172). Note its current recipe (probably calls `pre-commit-check`, `lint-check`, `test`, `build`).

Add a new target ABOVE `ci:`:

```makefile
typecheck: ## Run basedpyright at recommended mode (workspace canonical)
	@$(call ai_run,uv run basedpyright,typecheck)
```

Then update the `ci:` target's dependency list to include `typecheck`:

```makefile
ci: setup pre-commit-check lint-check typecheck test build layout-fork-info
```

(The exact order may vary; just slot `typecheck` after `lint-check`.)

If the Makefile uses a different pattern for `AI=1` logging (e.g., custom `ai_run` function), wrap the basedpyright call in that pattern.

- [ ] **Step 3: Run basedpyright at recommended mode and triage**

Run: `uv run basedpyright 2>&1 | tail -80`

Expected: significantly more diagnostics than at `standard` mode. The recommended-mode additions include:
- `reportMissingParameterType` (every unannotated function parameter)
- `reportMissingReturnType` (every unannotated function return)
- `reportUnknownArgumentType` / `reportUnknownVariableType`
- `reportUntypedFunctionDecorator`
- Cleaner enforcement of inferred-`Any` propagation

Triage with the suppression policy:
1. **Hand-fix preferred.** Most of these are "add type hints". The agent's job.
2. **`cast(...)`** from `typing` when the runtime is provably correct but type can't be inferred from context.
3. **`# type: ignore[reportXxxxx]`** with comment, only for third-party stub gaps.

Per-file overrides in `pyproject.toml` are acceptable for genuinely problematic third-party-heavy modules (e.g., `pd_book_tools/ocr/predictor.py` if it's full of DocTR opaque types):

```toml
[[tool.basedpyright.executionEnvironments]]
root = "pd_book_tools/ocr/predictor.py"   # if needed
typeCheckingMode = "standard"
```

But use sparingly — the canonical answer is to add stubs or annotate.

- [ ] **Step 4: Add CI annotation step (optional but recommended)**

Locate `.github/workflows/ci.yml` (or whatever the CI workflow file is). Add a basedpyright-on-failure annotation step AFTER the existing `make ci` step:

```yaml
      - name: basedpyright annotations
        if: failure()
        run: |
          uv run basedpyright --outputjson | python3 -c "
          import json, sys
          data = json.load(sys.stdin)
          for d in data.get('generalDiagnostics', []):
              f = d['file']
              r = d['range']['start']
              print(f\"::{d['severity']} file={f},line={r['line']+1},col={r['character']+1}::{d['message']}\")"
```

This surfaces basedpyright errors as GitHub PR inline annotations on failure. If the existing CI doesn't follow this pattern, skip this step.

- [ ] **Step 5: Run `make ci AI=1`**

Run: `make ci AI=1`
Expected: passes. `make ci` now runs (in order): setup → pre-commit-check → lint-check → typecheck → test → build → layout-fork-info. Every stage green.

If `make ci AI=1` fails, the failure must be addressed before commit; do not bypass.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml Makefile .github/workflows/
git add pd_book_tools/ tests/ scripts/   # for type-fix changes
git commit -m "feat(types): upgrade basedpyright to recommended mode + wire into make ci

typeCheckingMode = 'recommended' + failOnWarnings = true is the
workspace canonical strict mode per 2026-05-17 decisions. It catches
unannotated functions (vanilla pyright skips), inferred-Any
propagation, untyped decorators, and missing return types.

Test/script execution environments stay at 'standard' for now;
upgrade to 'recommended' there as a follow-up when test-side typing
debt is paid down.

make typecheck added as a discrete target; make ci now invokes it
after lint-check and before test. CI workflow gets a GitHub PR
annotation step for failure visibility.

Hand-fixes preferred; cast() used where runtime is provably correct
but inference can't reach. Per-file type-ignore comments are scoped
to specific rule codes with inline rationale.

Per docs/decisions/2026-05-17-strict-linting.md."
```

---

## Self-review checklist (for the engineer; do this before declaring done)

- [ ] Eight commits land in order: pyright→basedpyright switch, .editorconfig, isort+pylint removal, pre-commit additions, gitlint, ruff expansion, pytest hardening, basedpyright recommended mode + Makefile/CI.
- [ ] No commit uses `--no-verify`; every pre-commit hook ran clean.
- [ ] `make ci AI=1` is green at the tip.
- [ ] `uv run basedpyright` is clean at `recommended` mode with `failOnWarnings = true`.
- [ ] `uv run ruff check pd_book_tools/ tests/ scripts/` is clean.
- [ ] No `# type: ignore` is a bare suppression — every one names a specific rule code AND has a brief comment.
- [ ] No `# noqa` is a bare suppression — every one names a specific rule code AND has a brief comment.
- [ ] Per-file-ignores in `pyproject.toml` match the canonical pattern from the decisions doc.
- [ ] `pyproject.toml` no longer mentions `isort`, `pylint`, or `pyright` (only `basedpyright`, `ruff>=0.15.13`, and the new ruff rule groups).
- [ ] `.pre-commit-config.yaml` includes: pre-commit-update (manual), pre-commit-hooks v6.0.0 (with debug-statements + check-merge-conflict + check-toml + check-added-large-files), gitleaks v8.24.2, ruff-pre-commit v0.15.13, markdownlint-cli2, local hooks (uv-lock-check + basedpyright), gitlint v0.19.1 (commit-msg stage).
- [ ] `.editorconfig` is at repo root with the canonical content.
- [ ] `.gitlint` is at repo root.
- [ ] `default_install_hook_types: [pre-commit, commit-msg]` is set at top of `.pre-commit-config.yaml`.

## Notes for the agent

- This plan establishes the **workspace canonical pattern**. If a config decision in this rollout differs from the decisions doc, FLAG IT in your final report rather than silently diverging — the rest of the workspace will mirror what lands here.
- The biggest time sinks will be Task 6 (ruff expansion → triage hundreds of violations) and Task 8 (basedpyright recommended mode → fix annotation gaps). If either task's fix work exceeds ~90 minutes, STOP and report; the user can decide whether to keep going or split.
- If you encounter a class of suppression that comes up 10+ times in this repo, surface it — it may be a workspace-wide pattern worth documenting in the decisions doc rather than re-applying ad hoc in every later repo.
- The schema-hook code added in plan #1 follow-up (commits `9b5...d6ad9d2`) adds `pydantic_core.core_schema` calls that may surface `reportUnknownMemberType` or similar diagnostics in `recommended` mode. Plan for ~30min of annotation work on those files specifically.

## Follow-up plans (not in scope here)

1. **`docs/python-coding-guidelines.md` migration into LLM coding-guide + review-checklist pair.** Per follow-up #7 in the decisions doc. Plan after this rollout completes — the post-migration codebase gives the concrete data needed to calibrate the LLM review prompts (which suppressions are routine, which signal real anti-patterns).
2. **Workspace canonical config repo.** Once .editorconfig + .gitlint + Renovate config are all established here, extract them into a `pd-meta` repo (or similar) so every other pd-* repo can reference a single source of truth instead of carrying its own copy.
3. **Ratchet test/script execution environments to `recommended`.** Currently `standard` per Task 1 + Task 8. Tackle as a separate test-typing-debt pass.
4. **Coverage floor ratchet.** If `fail_under` was lowered in Task 7 to absorb the branch-coverage migration, schedule incremental ratchets back up as branch-coverage gaps land tests.
5. **Rollout the remaining repos in the order from the decisions doc:** pdomain-ocr-ops → pdomain-ocr-cli → pdomain-ocr-synth (these three parallel after pdomain-book-tools lands the pattern) → pdomain-prep-for-pgdp → pdomain-ocr-labeler-spa → pd-png-optimizer → pdomain-ui → pdomain-index-npm → minimal pass on pd-ocr-labeler + pd-ocr-trainer → se-llm-skills.
