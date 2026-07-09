# se-llm-skills strict-linting survey (2026-05-17)

Commissioned by: `docs/decisions/2026-05-17-strict-linting.md` §se-llm-skills
("survey separately").  
Status: survey only; no config changes applied.

---

## Codebase composition

| Language / kind | Count (excl. `.venv/`, `.git/`, `dist/`) | Notes |
|---|---|---|
| Python (`.py`) | 28 source files | Excludes dist/ copies; includes 15 test files and 13 skill scripts |
| TypeScript / TSX | 0 | No frontend |
| JavaScript / MJS / CJS | 0 | None in source tree (all JS under `.venv/` is third-party) |
| Markdown (`.md`) | ~30 source docs | Excludes ~50 `test-ebooks/*/LICENSE.md` stubs and `.pytest_cache/README.md` |
| Shell scripts (`.sh`) | 2 | `adapters/claude.sh` (build adapter), `scripts/pull-test-ebooks.sh` |
| Skill sources | 3 `SKILL.md` files | `skills/se-llm-review/SKILL.md`, `skills/se-llm-classify/SKILL.md`, `skills/se-llm-commitcheck/SKILL.md` |
| Rulebook markdown | 7 `.md` files | `skills/se-llm-review/rulebook/`, `skills/se-llm-classify/rulebook/` |

**Python breakdown (source, excl. dist/):**

- `skills/se-llm-review/scripts/` — 4 files: `generate_review.py` (heavy), `chunk_file.py`, `apply_edits.py`, `validate_rulebook.py`
- `skills/se-llm-classify/scripts/` — 4 files: `classify_driver.py`, `collect_results.py`, `render_classify_report.py`, `__init__.py`
- `skills/se-llm-commitcheck/scripts/` — 1 file: `classify_hunks.py` (1,040 LOC — largest file)
- `skills/shared/scripts/` — 2 files: `char_diff.py`, `check_metadata_guard.py`
- `tests/` — 15 test files + `conftest.py` + `__init__.py`
- Total LOC (excl. dist/): ~6,736 lines

**Key structural insight:** roughly 40% of Python files (11/28) are currently **excluded** from ruff enforcement via `pyproject.toml` `extend-exclude`. These are the pre-existing skill scripts that predate the strict-lint migration plan — they are active production code shipped inside the Claude plugin artifact.

---

## Current tooling state

### pyproject.toml — exists; already canonical

```toml
[tool.ruff]
line-length = 100
target-version = "py312"
extend-exclude = [
  # Pre-existing scripts deferred from strict-lint
  "skills/se-llm-review/scripts/generate_review.py",
  "skills/se-llm-review/scripts/chunk_file.py",
  "skills/se-llm-review/scripts/apply_edits.py",
  "skills/se-llm-classify",
  "skills/se-llm-commitcheck",
  "skills/shared",
  "adapters",
  "dist",
  ".venv",
  # Pre-existing tests deferred until matching scripts are migrated
  "tests/conftest.py",
  "tests/test_apply_edits.py",
  ... (13 test files)
]

[tool.ruff.lint]
select = [
  "E", "W", "F", "I", "N", "B", "SIM", "UP", "RUF", "ERA", "T20",
  "ANN", "S", "C4", "PERF", "TC", "TID", "PT", "RET", "PL", "D",
  "BLE", "TRY", "LOG", "G"
]
ignore = ["E741", "E501", "D203", "D212", "D100", "D104", "D107",
          "PLR0913", "PLR2004", "TRY003", "COM812"]
```

The **full canonical ruff rule set** (per decision doc) is already selected. Only the `extend-exclude` list is non-canonical. Current state: `ruff check` passes clean on the opted-in files (`validate_rulebook.py` + `test_validate_rulebook.py`).

```toml
[tool.basedpyright]
include = [
  "skills/se-llm-review/scripts/validate_rulebook.py",
  "tests/test_validate_rulebook.py",
]
typeCheckingMode = "recommended"
failOnWarnings = true
pythonVersion = "3.12"
```

basedpyright is already installed and configured at `recommended` mode. Current state: `basedpyright` passes clean (0 errors, 0 warnings). The `include` list is narrow — only 2 of 28 source files are type-checked. Six `reportUnknown*` and `reportAny` suppressions are in place for idiomatic argparse/yaml patterns.

```toml
[tool.pytest.ini_options]
addopts = ["-ra", "--strict-markers", "--strict-config"]
testpaths = ["tests"]
filterwarnings = ["error"]
```

`filterwarnings = ["error"]` already enabled. 209 tests collected and passing.

**Missing files vs. canonical workspace pattern:**

| File | Status |
|---|---|
| `.pre-commit-config.yaml` | **ABSENT** — no pre-commit hooks at all |
| `.editorconfig` | **ABSENT** |
| `.gitlint` | **ABSENT** |
| `package.json` | Not applicable (no TS/JS) |
| `.github/workflows/` | **ABSENT** — no CI pipeline |
| `uv.lock` | Present and committed |
| `pyproject.toml` | Present, substantial |
| `Makefile` | Present; `make ci` = build + lint-check + typecheck + test + validate-rulebook |

### Dev dependencies (already installed)

`ruff`, `basedpyright`, `pytest`, `pytest-cov`, `beautifulsoup4`, `pyyaml`, `tiktoken`, `httpx`, `markdown-it-py`, type stubs. No `gitleaks`, no `gitlint` in scope yet.

---

## Strict-linting applicability

### Python stack (basedpyright + ruff + pytest hardening + .editorconfig + gitleaks + gitlint)

**Applies — partially implemented, partially deferred.**

- **Ruff rule set:** Already at full canonical expansion. The gap is the `extend-exclude` list covering 11 source Python files (the pre-existing skill scripts). These files need to be migrated into compliance one skill at a time so the exclude list can shrink to zero.
- **basedpyright:** Already installed at `recommended` mode. The gap is the narrow `include` list — 26 of 28 source files are not type-checked. Expanding `include` (or removing it to type-check everything) requires first clearing ruff compliance in the excluded scripts.
- **pytest:** `filterwarnings = ["error"]` is already on. `--cov-branch` is not in `addopts` yet. No coverage floor (`fail_under`) is configured — the workspace pattern requires one.
- **gitleaks:** Not installed. Skills contain SE ebook content and LLM API call patterns; a stray API key in a test fixture is realistic. Should be added.
- **gitlint:** Not installed. Should be added alongside gitleaks.
- **uv-lock-check:** Not in pre-commit (no pre-commit config at all). Should be added.
- **.editorconfig:** Absent. Should be added.
- **.pre-commit-config.yaml:** Absent entirely. This is the largest gap relative to the canonical pattern — there is no commit-time gate beyond `make ci` running manually.

### TS/React stack

**Not applicable.** Zero TypeScript or JavaScript source files. The `.venv/` tree contains bundled Node bits from `basedpyright`'s `nodejs-wheel` dependency, but those are not authored here.

### Rust supply chain (cargo deny)

**NOOP.** No Rust in this repo.

### Markdown lint

**Relevant, but nuanced.** The repo has two categories of markdown:

1. **Skill source files** (`SKILL.md`, `rulebook/*.md`, `source/*.md`) — these are the **primary build artifacts** that get shipped into the Claude plugin. Their markdown structure is semantically load-bearing (headings, lists, frontmatter). Lint rules that flag cosmetic issues (trailing spaces, bare URLs) would be safe and useful. Rules that try to enforce ATX vs. setext headings or specific list styles could be disruptive to skill authoring.

2. **Docs and test-ebook stubs** — lower stakes; standard workspace markdown hygiene applies.

Recommended approach: add `markdownlint-cli2` (or the pre-commit hook equivalent) with a permissive config that catches only structural errors (missing blank lines, broken link targets), not stylistic ones. Do NOT add markdown lint until the pre-commit infrastructure exists.

### Special note: `dist/` artifact pipeline interaction

The `make build` step (adapter script `adapters/claude.sh`) copies `skills/` into `dist/claude/plugins/se-llm-skills/skills/`. This means the Python scripts inside `skills/*/scripts/` are deployed verbatim into the plugin artifact. Strict-linting these scripts is not just a code-quality concern — it's a **correctness gate on deployed code**. Expanding ruff/basedpyright coverage to the excluded scripts has higher leverage here than in most repos: these files run inside agent subprocesses without a pre-flight linter.

---

## Special concerns

**Testing infrastructure:** 209 tests, well-structured (`tests/` with fixtures). Currently running clean. However, 14 of 15 test files are in the `extend-exclude` list — they correspond to the as-yet-unlinted skill scripts. Tests for excluded scripts exist but are themselves excluded from ruff. This creates a coverage asymmetry: the scripts most in need of linting are tested but the tests aren't linted either.

**CI:** No GitHub Actions workflows exist. The only CI gate is `make ci` run locally (or by an agent before commit). This means gitleaks and gitlint have no CI enforcement path — they'd be pre-commit only. Adding a `.github/workflows/ci.yml` that runs `make ci` is a follow-on task; it's out of scope for the strict-linting rollout itself but should be noted.

**Plugin artifact integrity:** The `make ci` target includes `build` as its first step, which regenerates `dist/`. This means lint runs on source; the artifact is always fresh. No interaction conflict with strict-linting.

**Coverage floor:** `pytest-cov` is installed but no `--cov-branch` or `fail_under` is configured in `addopts`. The workspace pattern calls for both. Adding `--cov-branch` may surface uncovered `except` branches in the skill scripts when they're brought into scope.

**Scale:** At 28 Python source files and ~6,700 LOC, this is a small codebase. Migration effort per file is low; the main work is systematic rather than voluminous.

---

## Recommendation

Apply the **full canonical Python stack** with a phased exclude-list drawdown rather than a single big-bang migration. The infrastructure is already more advanced than any other repo at this rollout stage: ruff rule set is fully canonical, basedpyright is installed at `recommended` mode, and `filterwarnings = ["error"]` is already on. The repo is **not** a legacy-bound deprecated codebase (unlike pd-ocr-labeler or pd-ocr-trainer) — it is actively worked and the Python scripts it ships are deployed production code. The minimal-scope treatment is inappropriate here.

The single departure from the canonical pattern is the large `extend-exclude` list, which exists because 11 skill-script files predate the linting infrastructure. These files must be migrated into compliance individually. The recommended rollout sequences this as a series of per-skill commits rather than a single bulk noqa-flood.

Markdown lint is deferred until pre-commit infrastructure is in place; then add it with a permissive config scoped to structural checks only.

No TS/React or Rust work applies.

---

## Suggested rollout plan outline

Commit sequence (not the full plan — that goes in a separate `plans/` doc):

1. **`chore(lint): add .editorconfig`** — canonical workspace file; zero code changes.
2. **`chore(lint): add .pre-commit-config.yaml`** — gitleaks + uv-lock-check + gitlint + ruff-pre-commit hooks. Mirror the pdomain-book-tools canonical template.
3. **`chore(lint): add .gitlint`** — workspace-canonical gitlint config.
4. **`chore(lint): add --cov-branch + fail_under to pytest config`** — measure branch coverage; set floor at whatever the current number is post-branch-mode.
5. **`fix(lint): migrate skills/shared/scripts/ into ruff + basedpyright`** — remove `skills/shared` from `extend-exclude`; fix any violations in `char_diff.py` and `check_metadata_guard.py`. Remove matching tests from exclude list.
6. **`fix(lint): migrate skills/se-llm-commitcheck/scripts/ into ruff + basedpyright`** — largest single file (`classify_hunks.py`, 1,040 LOC). Likely highest noqa + annotation debt. Remove from exclude list.
7. **`fix(lint): migrate skills/se-llm-classify/scripts/ into ruff + basedpyright`** — 4 files; remove from exclude list.
8. **`fix(lint): migrate skills/se-llm-review/scripts/ into ruff + basedpyright`** — 3 remaining files (`generate_review.py`, `chunk_file.py`, `apply_edits.py`). Remove from exclude list.
9. **`chore(lint): remove extend-exclude list from pyproject.toml`** — at this point exclude list should be empty (only `dist/` and `.venv/` remain, which are conventional).
10. **`chore(lint): add markdownlint-cli2 pre-commit hook`** — permissive config; structural checks only. Scoped to `skills/**/*.md` and `docs/**/*.md`.
11. **`chore(ci): add .github/workflows/ci.yml`** — run `make ci` on push/PR; add gitleaks GHA step. (Out of strict-linting scope but natural follow-on.)

**Estimated rollout effort:** commits 1–4 are mechanical (< 1 hour total). Commits 5–8 are the migration work — `classify_hunks.py` alone may take 1–2 hours to annotate fully. Total estimate: **4–6 hours of agent time** across 4 focused sessions. No blockers; no design decisions required.
