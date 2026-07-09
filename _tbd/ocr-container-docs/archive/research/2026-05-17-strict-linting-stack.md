# Strict linting + type-check stack — prescriptive recommendation (2026-05-17)

## Executive summary

**Python stack:** `ruff 0.15.13` (linter + formatter) + `basedpyright 1.39.4`
(type checker, `typeCheckingMode = "recommended"`) enforced at commit time via
the `pre-commit` framework (pre-commit.com). `ruff` handles format, import
sort, and 15+ lint rule groups including annotations (`ANN`), security (`S`),
type-checking imports (`TC`), and return-value conventions (`RET`). `basedpyright`
in `"recommended"` mode turns every diagnostic into a warning/error with
`failOnWarnings = true`, which is stricter than vanilla `pyright --strict`.

**TypeScript / React stack:** `typescript-eslint 8.59.3` with
`strictTypeChecked` + `stylisticTypeChecked` (both requiring `projectService:
true` for type-aware rules) + `eslint-plugin-react-hooks 7.1.1` (v6-era flat
config) + `eslint-plugin-jsx-a11y ^6.10` + `eslint-config-prettier` as the
last entry. `prettier 3.x` owns formatting. The flat `eslint.config.js` is the
single source of truth for TS/React strictness; no Biome.

**Cross-cutting:** The Python `pre-commit` framework (pre-commit.com) is the
umbrella for all repos — it already runs hooks in every pd-* repo and can
host both Python and JS/TS hooks (via `language: node` or `language: system`
entries). No per-ecosystem husky/simple-git-hooks separate installs needed.

**Top 5 leverage wins (LLM-correctness per hour of setup work):**

1. Add `ANN` + `TC` to every Python `pyproject.toml` `[tool.ruff.lint] select`
   — forces LLMs to annotate every function signature, which makes downstream
   type errors deterministic rather than silent.
2. Upgrade `basedpyright` to `typeCheckingMode = "recommended"` in every repo
   (currently all repos use `"basic"` for tests and `"strict"` for src, but
   `"recommended"` in basedpyright is stricter than `"strict"` in vanilla
   pyright and gives more actionable per-diagnostic messages).
3. Add `strict-type-checked` + `stylisticTypeChecked` + `parserOptions.projectService: true`
   to both frontend `eslint.config.js` files — currently both use
   `tseslint.configs.recommended` without type-checking, so dozens of
   type-aware rules are silently disabled.
4. Add `S` (bandit) + `PT` (pytest-style) + `RET` (return conventions) + `PERF`
   to every Python `[tool.ruff.lint] select` — catches the LLM anti-patterns
   that slip through pyflakes (assert instead of exception, no return type
   annotation, inefficient list materializations).
5. Add `gitleaks` to the pre-commit config in every repo — zero setup once
   added, prevents the most damaging class of committed secrets that LLMs
   occasionally produce when writing test fixtures with fake-looking credentials.

---

## Current state of the workspace

| Repo | Ecosystem | ruff select (gaps) | Type checker | Pre-commit | Frontend lint | Biggest LLM-correctness gap |
|---|---|---|---|---|---|---|
| `pdomain-book-tools` | Python | E F W I N B SIM UP RUF ERA T20 — **missing ANN S PERF TC PT RET C4 D** | pyright basic(tests) / strict(src) — **not basedpyright** | ruff+hooks+markdownlint | n/a | No annotation enforcement; security rules absent; isort still in dev deps (redundant with ruff I) |
| `pdomain-ocr-cli` | Python | E F W I N B SIM UP RUF ERA T20 — **same gaps** | pyright basic/strict | ruff+hooks | n/a | Same as pdomain-book-tools; coverage floor 100% but type gaps |
| `pd-ocr-labeler` | Python | E F W I N B SIM UP RUF ERA T20 | pyright basic/strict | ruff+hooks+markdownlint | n/a | Legacy NiceGUI — deprioritize migration; no coverage floor (`fail_under = 0`) |
| `pdomain-ocr-synth` | Python | E F W I N B C4 SIM UP RUF ERA T20 — **missing ANN S PERF TC PT RET** | pyright basic/strict | no pre-commit config present | n/a | No pre-commit at all; annotation enforcement absent |
| `pd-ocr-trainer` | Python | E W F I N B SIM C4 UP RUF ERA T20 — **missing ANN S PERF TC PT RET** | pyright basic/strict | no pre-commit config present | n/a | setuptools build backend (non-standard vs peers); no pre-commit |
| `pd-png-optimizer` | Python+Rust | E W F I B C4 UP — **missing N SIM RUF ERA T20 ANN S PERF TC** | none | cargo-fmt+cargo-clippy+ruff | n/a | Python facade has minimal lint; no type checker at all; `cargo deny` absent |
| `pdomain-prep-for-pgdp` | Python + TS/React | E F W I N B SIM UP RUF ERA T20 (B008 UP042 ignored) | pyright basic/strict | ruff+hooks+markdownlint+tsc+eslint+prettier | `tseslint.configs.recommended` only — **no type-checked variant** | Frontend: `@typescript-eslint/no-explicit-any` is only a `warn`; no type-aware rules |
| `pdomain-ocr-labeler-spa` | Python + TS/React | E F W I N B SIM UP RUF ERA T20 | pyright basic | ruff+hooks+markdownlint+tsc+eslint+prettier+pyright | `tseslint.configs.recommended` only — **no type-checked variant** | Same frontend gap as pgdp-prep; pyright pre-commit hook present but `"basic"` mode |
| `pdomain-ocr-ops` | Python | E F W I only — **most groups absent** | none | none | n/a | Barely linted; greenfield — ideal first migration target |
| `pdomain-ui` (planned) | TypeScript/React lib | — | — | — | — | Needs full TS strict stack from day 1 |
| `pdomain-index-npm` (planned) | TypeScript (Node) | — | — | — | — | Needs TS strict + Node globals |
| `se-llm-skills` | Python | (not surveyed — skills framework) | — | — | n/a | Likely under-linted |

**Cross-cutting gaps:**
- No `.editorconfig` in any repo.
- No secret detection (`gitleaks`) in any repo.
- No commit-message lint in any repo (workspace uses conventional commits by convention but unenforced).
- No dependency-update bot configured on any repo.
- `isort` remains in `pdomain-book-tools` and `pd-ocr-trainer` dev deps despite `ruff I` handling it.
- `pylint` in `pdomain-book-tools` dev deps is largely superseded by `ruff PL` rules.
- `pd-ocr-trainer` uses `setuptools` build backend rather than `hatchling` (non-standard).

---

## Python stack — prescriptive recommendation

### Tool selection

- **ruff 0.15.13** (linter + formatter): replaces black, isort, flake8, pydocstyle, and 90% of pylint. Single binary, runs in <200ms on any pd-* repo. Machine-readable `path:line:col: RULEXXXX message` output that LLMs parse perfectly. Reason over runner-up (pylint): ruff's PL rules cover pylint's correctness rules at 50× speed; pylint adds no LLM-feedback value.

- **basedpyright 1.39.4** (type checker): pyright fork with two modes not in vanilla pyright — `"recommended"` (all diagnostics active as warnings/errors, `failOnWarnings = true`) and `"all"`. Bundles a Node.js runtime via nodejs-wheel so `uv add --dev basedpyright` works without a separate npm install. Reason over runner-up (mypy --strict): basedpyright checks unannotated functions by default (mypy skips them without `--check-untyped-defs`); it has 97.8% typing-spec conformance vs mypy's 58.3%; and it produces pyright-style inline error messages that are more actionable for LLMs. Reason over ty 0.0.32: ty is still in beta with 53.2% spec conformance; not production-ready for strict enforcement.

- **pre-commit framework 4.2.0+** (hook runner): already in use across the workspace. Python-native, no additional tooling. Hooks are language-agnostic — the JS/TS hooks run as `language: system` entries using the already-installed Node from mise.

### Drop-in config

#### `[tool.ruff]` and `[tool.ruff.lint]` (put in `pyproject.toml`)

```toml
[tool.ruff]
line-length = 100
target-version = "py313"   # or py311 for pdomain-ocr-ops

[tool.ruff.lint]
select = [
    "E",     # pycodestyle errors
    "W",     # pycodestyle warnings
    "F",     # pyflakes
    "I",     # isort (replaces standalone isort)
    "N",     # pep8-naming
    "ANN",   # flake8-annotations — enforces type hints on all sigs
    "S",     # flake8-bandit — security rules (assert, hardcoded creds, etc.)
    "B",     # flake8-bugbear — mutable defaults, broad excepts, etc.
    "C4",    # flake8-comprehensions — list/dict/set comp idioms
    "SIM",   # flake8-simplify
    "UP",    # pyupgrade — syntax modernisation
    "PERF",  # perflint — performance anti-patterns
    "RUF",   # ruff-specific rules
    "ERA",   # eradicate — commented-out code
    "T20",   # flake8-print — print() in non-script code
    "PT",    # flake8-pytest-style — pytest conventions
    "RET",   # flake8-return — return value consistency
    "TC",    # flake8-type-checking — move type-only imports to TYPE_CHECKING
    "TID",   # flake8-tidy-imports — ban relative imports where appropriate
    "PL",    # pylint (PLC + PLE + PLR + PLW subset)
    "D",     # pydocstyle — docstring presence and format
]
ignore = [
    # FastAPI Depends() in default args — enable globally only if the repo has no FastAPI
    # "B008",
    # D rules: enable the google/numpy convention, disable conflicting rules
    "D100",  # Missing docstring in public module — noisy for __init__.py files
    "D104",  # Missing docstring in public package — same
    "D107",  # Missing docstring in __init__ — covered by class-level docstring
    "D203",  # one-blank-line-before-class — conflicts with D211
    "D212",  # Multi-line summary first line — conflicts with D213
    # ANN: self/cls annotations are noise
    "ANN101",  # missing-type-self
    "ANN102",  # missing-type-cls
    # S: assert in tests is expected — use per-file-ignores instead
    # "S101",
    # PL: some pylint refactor suggestions are too aggressive
    "PLR0913",  # too-many-arguments (common in FastAPI route handlers)
    "PLR2004",  # magic-value-comparison (too noisy in tests)
]

[tool.ruff.lint.pydocstyle]
convention = "google"   # or "numpy"; pick one and hold it

[tool.ruff.lint.per-file-ignores]
# Test files: relax security + print + annotation strictness
"tests/**/*.py" = ["S101", "S105", "S106", "S311", "T201", "ANN", "D"]
# CLI scripts: print() is the output mechanism
"scripts/**/*.py" = ["T201", "D"]
# __init__.py re-export files: annotations are often redundant
"**/__init__.py" = ["D104", "F401", "TC"]
# FastAPI repos: Depends() in default args is canonical
# "src/**/api/**/*.py" = ["B008"]

[tool.ruff.lint.isort]
known-first-party = ["pd_book_tools"]  # adjust per repo
```

**Per-repo deviations:**
- `pdomain-prep-for-pgdp` and `pdomain-ocr-labeler-spa` (FastAPI): add `"B008"` and `"UP042"` to `ignore` (already present).
- `pd-png-optimizer`: `target-version = "py39"` (multi-Python facade).
- `pd-ocr-labeler` (legacy NiceGUI): exclude `D` until docstrings are backfilled; set `fail_under = 0` separately.
- `pdomain-ocr-ops`: use `target-version = "py311"`.

#### `[tool.basedpyright]` (put in `pyproject.toml`)

```toml
[tool.basedpyright]
# Point at source + tests. Adjust per repo layout.
include = ["src", "tests", "scripts"]
exclude = ["**/__pycache__", "**/.venv", "**/node_modules"]
# "recommended" mode = all diagnostics active, failOnWarnings = true.
# Stricter than vanilla pyright "strict" — catches unannotated functions
# and inferred-Any propagation that "strict" misses.
typeCheckingMode = "recommended"
# Tell basedpyright where the venv is so it finds third-party stubs.
venvPath = "."
venv = ".venv"

# Dataclasses: basedpyright ≥1.21 fully understands stdlib @dataclass,
# attrs, and Pydantic v2 models without any special flags.
# No additional stubs needed for these patterns.

# Per-execution-environment overrides (optional — only needed if you
# have scripts or tests that can't meet "recommended" strictness yet):
[[tool.basedpyright.executionEnvironments]]
root = "tests"
typeCheckingMode = "standard"
```

**For repos that can't immediately meet `"recommended"`:**
Start at `"standard"` for all and `"recommended"` for src only. The split
`executionEnvironments` pattern already used in several repos is valid.

#### `[tool.pytest.ini_options]` (standardised across all repos)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "-n", "auto",            # pytest-xdist parallelism
    "--cov=<package_name>",  # replace with actual package
    "--cov-report=term-missing:skip-covered",
]
asyncio_mode = "auto"        # only for async repos (FastAPI, labeler-spa)
markers = [
    "slow: skip with -m 'not slow'",
    "integration: requires live stack",
    "gpu: requires CUDA",
]
filterwarnings = [
    "error",   # turn all unhandled warnings into test failures
    # Add specific ignores for third-party noise:
    # "ignore::DeprecationWarning:torch.*",
]
```

**`filterwarnings = ["error"]` is the highest-leverage single-line addition.**
It catches deprecated API usage and LLM-generated code that silently swallows
warnings. Add specific ignores for known noisy third-party packages.

### Pre-commit hooks (`.pre-commit-config.yaml`)

This is the canonical template for all Python repos (without a frontend).
Repos with a frontend add the `local` hooks from the Frontend section below.

```yaml
# .pre-commit-config.yaml — canonical pd-* Python template
# Pin every rev. Run `pre-commit autoupdate` quarterly to advance pins.

default_install_hook_types: [pre-commit]

repos:
  # Automatic hook version bumping (runs on manual stage only)
  - repo: https://gitlab.com/vojko.pribudic.foss/pre-commit-update
    rev: v0.9.0
    hooks:
      - id: pre-commit-update
        stages: [manual]

  # General file hygiene
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-toml
      - id: check-added-large-files
        args: [--maxkb=1000]
      - id: debug-statements      # catches leftover pdb/ipdb
      - id: check-merge-conflict

  # Secret detection — gitleaks scans staged diff only (fast)
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.2
    hooks:
      - id: gitleaks

  # Ruff: import sort, lint, format
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.13
    hooks:
      - id: ruff-check
        args: [--select, I, --fix]
      - id: ruff-check
        args: [--fix]
      - id: ruff-format

  # Markdown lint
  - repo: https://github.com/DavidAnson/markdownlint-cli2
    rev: v0.22.1
    hooks:
      - id: markdownlint-cli2
      - id: markdownlint-cli2
        alias: markdownlint-cli2-fix
        args: [--fix]
        stages: [manual]

  # uv lockfile drift gate
  - repo: local
    hooks:
      - id: uv-lock-check
        name: uv.lock is in sync with pyproject.toml
        entry: uv lock --check
        language: system
        stages: [pre-commit]
        pass_filenames: false
        files: ^(pyproject\.toml|uv\.lock)$

      # basedpyright type check (runs on src only for speed)
      - id: basedpyright
        name: basedpyright type check
        entry: uv run basedpyright
        language: system
        stages: [pre-commit]
        pass_filenames: false
        files: ^src/.*\.py$
```

**Why `basedpyright` in pre-commit rather than just CI?** LLMs iterate locally.
Catching `Unknown` propagation at commit time lets the LLM see the error
immediately and fix the annotation before the diff lands in a PR.

### Makefile additions / changes to `make ci`

Amend the `ci` target in every repo to include `basedpyright`:

```makefile
ci: setup pre-commit-check lint-check typecheck test

typecheck: ## Run basedpyright type checker
	uv run basedpyright
```

And add `basedpyright>=1.39.4` to `[dependency-groups] dev` in `pyproject.toml`:

```toml
[dependency-groups]
dev = [
    "basedpyright>=1.39.4",
    "pre-commit>=4.2.0",
    "pytest>=8.3",
    "pytest-asyncio>=0.24",   # for async repos
    "pytest-cov>=6.0",
    "pytest-xdist>=3.8",
    "ruff>=0.15.13",
]
```

Remove `isort`, `pylint` from dev deps where present — ruff subsumes both.

### CI workflow additions (`.github/workflows/ci.yml`)

The existing workflow pattern is already correct. Add `basedpyright` invocation
explicitly for transparency:

```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
permissions:
  contents: read
jobs:
  ci:
    name: ci
    runs-on: ubuntu-latest
    env:
      UV_PYTHON: "3.13"
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: latest
      - name: Run CI
        run: make ci
      # Optional: surface basedpyright output in GitHub PR annotations
      - name: basedpyright annotations
        if: failure()
        run: uv run basedpyright --outputjson | python3 -c "
          import json, sys
          data = json.load(sys.stdin)
          for d in data.get('generalDiagnostics', []):
              f = d['file']
              r = d['range']['start']
              print(f\"::{d['severity']} file={f},line={r['line']+1},col={r['character']+1}::{d['message']}\")"
```

### pd-png-optimizer: Rust-side checks

Current state: `cargo clippy --workspace --all-targets -- -D warnings` and
`cargo fmt --check` are already in `.pre-commit-config.yaml` and `make ci`.
**Add `cargo deny`** for supply-chain security:

```yaml
# In .pre-commit-config.yaml, add to the local hooks section:
      - id: cargo-deny
        name: cargo deny check
        entry: bash -c '. "$HOME/.cargo/env" 2>/dev/null || true; exec cargo deny check'
        language: system
        types: [toml]
        files: ^(Cargo\.toml|Cargo\.lock|deny\.toml)$
        pass_filenames: false
```

```toml
# deny.toml (root of pd-png-optimizer)
[advisories]
db-path = "~/.cargo/advisory-db"
db-urls = ["https://github.com/rustsec/advisory-db"]
vulnerability = "deny"
unmaintained = "warn"
yanked = "deny"

[licenses]
unlicensed = "deny"
allow = [
    "MIT",
    "Apache-2.0",
    "Apache-2.0 WITH LLVM-exception",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "Unlicense",
    "Zlib",
]

[bans]
multiple-versions = "warn"
```

Add `cargo-deny` to `make ci`:

```makefile
ci: setup lint test build cargo-deny-check

cargo-deny-check: ## Check dependency licenses and advisories
	$(CARGO_ENV) cargo deny check
```

Also add to `Makefile`:

```makefile
rust-fmt-check: ## cargo fmt --check (no-modify)
	$(CARGO_ENV) cargo fmt --all -- --check

rust-lint: rust-fmt-check ## cargo clippy -D warnings
	$(CARGO_ENV) cargo clippy --workspace --all-targets -- -D warnings
```

The existing hooks already cover `cargo clippy` and `cargo fmt`. The `--all-features`
flag should **not** be used — the `extension-module` feature breaks `cargo test`
linking on Linux (it's enabled by maturin only at wheel build time). Current
`--all-targets` without `--all-features` is correct.

### Migration path (5-commit sequence per Python repo)

**Commit 1:** Add `basedpyright>=1.39.4` and remove `isort`/`pylint` from
`[dependency-groups] dev`. Add `[tool.basedpyright]` to `pyproject.toml` with
`typeCheckingMode = "standard"` initially.

**Commit 2:** Extend `[tool.ruff.lint] select` with `ANN S C4 PERF TC TID PT RET PL D`.
Add `ignore` entries for known acceptable suppressions. Run `ruff check --fix`
locally to auto-fix anything fixable; manually fix the rest.

**Commit 3:** Wire `basedpyright` into `Makefile` (`make typecheck`) and `make ci`.
Fix all type errors surfaced. Pin `filterwarnings = ["error"]` in pytest config.

**Commit 4:** Add `gitleaks`, `check-toml`, `debug-statements`,
`check-added-large-files`, `check-merge-conflict` to `.pre-commit-config.yaml`.
Add `uv-lock-check` and `basedpyright` local hooks.

**Commit 5:** Upgrade `typeCheckingMode` to `"recommended"` and fix remaining
diagnostics. This is the hardest commit — budget 30-60min of annotation work
per repo.

---

## TypeScript / React stack — prescriptive recommendation

### Tool selection

- **ESLint 9.x** (linter) + **typescript-eslint 8.59.3**: ESLint 10 is released
  but `eslint-plugin-react-hooks` and `eslint-plugin-jsx-a11y` have not yet
  published ESLint-10-compatible peer ranges as of May 2026. Stay on ESLint 9
  until ecosystem plugins stabilise. Reason over Biome: Biome v2 added some
  type-aware rules but cannot run `strict-type-checked` (which requires
  TypeScript language service). For this workspace — which uses
  `eslint-plugin-react-hooks`, `eslint-plugin-jsx-a11y`, and TanStack Query
  patterns — ESLint is the only tool that can enforce the full rule surface.
  Biome is faster (15×) but missing rules are a correctness regression for
  LLMs, not a speed win.

- **Prettier 3.x** (formatter): already in both frontend repos with consistent
  config. Prettier owns all formatting so ESLint rules that would conflict are
  disabled by `eslint-config-prettier`.

- **`tsc --noEmit` via `tsc -b`** (type check): already in both repos as a
  pre-commit hook. Keep.

- **knip 6.x** (dead-code detection, run in CI only not pre-commit): finds
  unused exports, unused files, unused deps. Adds zero cost at commit time;
  run as a separate CI step.

### Drop-in config

#### `tsconfig.app.json` (the strict application tsconfig)

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": true,
    "useUnknownInCatchVariables": true,
    "useDefineForClassFields": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "isolatedModules": true,
    "resolveJsonModule": true,
    "forceConsistentCasingInFileNames": true,
    "verbatimModuleSyntax": true,
    "noEmit": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "exclude": [
    "src/**/*.test.ts",
    "src/**/*.test.tsx",
    "src/**/*.spec.ts",
    "src/**/*.spec.tsx",
    "src/**/__tests__/**",
    "src/test/**"
  ]
}
```

**Key additions vs current state:**
- `noUncheckedIndexedAccess`: array/object index access returns `T | undefined`,
  not `T`. The most impactful single flag for catching LLM-generated off-by-one
  and null-dereference patterns.
- `exactOptionalPropertyTypes`: `{ foo?: string }` means `foo` can be
  `string | undefined` but NOT explicitly `{ foo: undefined }`. Eliminates a
  class of type-unsound assignment patterns.
- `noImplicitOverride`: class method overrides must use `override` keyword.
- `noPropertyAccessFromIndexSignature`: `obj.key` on an index-signature type
  requires `obj["key"]` syntax, making intent explicit.
- `useUnknownInCatchVariables`: `catch (e)` gives `e: unknown` not `e: any`.

#### `eslint.config.js` (complete, type-checked)

```javascript
// eslint.config.js — strict type-checked flat config for pd-* frontends
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import jsxA11y from "eslint-plugin-jsx-a11y";
import eslintConfigPrettier from "eslint-config-prettier";
import globals from "globals";

export default tseslint.config(
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      // Generated OpenAPI types — never hand-edited
      "src/api/types.gen.ts",
      "src/api/types.ts",
    ],
  },
  js.configs.recommended,

  // Type-checked strict: includes recommended + strict + type-aware rules.
  // Requires parserOptions.projectService (set below).
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,

  // jsx-a11y recommended (flat config export)
  jsxA11y.flatConfigs.recommended,

  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: { ...globals.browser },
      parserOptions: {
        // projectService: true instructs the parser to use the TypeScript
        // language service for type-aware rules. This is the recommended
        // option in typescript-eslint v8.
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      // react-hooks v7.1.1 flat config
      ...reactHooks.configs.flat.recommended.rules,

      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],

      // no-explicit-any: error, not warn. LLMs must use proper types.
      "@typescript-eslint/no-explicit-any": "error",

      // Unused vars: error with underscore escape hatch
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],

      // Enforce exhaustive type narrowing over type assertions
      "@typescript-eslint/no-unsafe-assignment": "error",
      "@typescript-eslint/no-unsafe-member-access": "error",
      "@typescript-eslint/no-unsafe-call": "error",
      "@typescript-eslint/no-unsafe-return": "error",
      "@typescript-eslint/no-unsafe-argument": "error",

      // Return type annotation required on exported functions
      "@typescript-eslint/explicit-module-boundary-types": "error",

      // Require Promise rejection values to be Error instances
      "@typescript-eslint/prefer-promise-reject-errors": "error",

      // Require await in async functions (catches accidental sync-looking code)
      "@typescript-eslint/require-await": "error",

      // Stylistic: prefer `as const` over type assertions on literals
      "@typescript-eslint/prefer-as-const": "error",

      // nullish coalescing over || for nullable types
      "@typescript-eslint/prefer-nullish-coalescing": "error",

      // optional chaining over && guards
      "@typescript-eslint/prefer-optional-chain": "error",
    },
  },

  {
    // Test files: loosen unsafe rules (mocks, casts, spy patterns)
    files: [
      "src/**/*.test.{ts,tsx}",
      "src/test/**/*.{ts,tsx}",
      "src/**/__tests__/**/*.{ts,tsx}",
    ],
    rules: {
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-non-null-assertion": "off",
      "@typescript-eslint/no-unsafe-assignment": "off",
      "@typescript-eslint/no-unsafe-member-access": "off",
      "@typescript-eslint/no-unsafe-call": "off",
      "@typescript-eslint/explicit-module-boundary-types": "off",
    },
  },

  {
    // Vite / Vitest config files: node globals, no DOM
    files: ["vite.config.ts", "vitest.config.ts"],
    languageOptions: {
      globals: { ...globals.node },
    },
    rules: {
      "@typescript-eslint/no-unsafe-assignment": "off",
    },
  },

  // Must be last: disables any ESLint rule that would conflict with Prettier
  eslintConfigPrettier,
);
```

#### `package.json` scripts and devDependencies

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit",
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "test": "vitest run --passWithNoTests",
    "test:coverage": "vitest run --coverage",
    "test:watch": "vitest",
    "knip": "knip",
    "openapi:gen": "openapi-typescript openapi.json -o src/api/types.gen.ts"
  },
  "devDependencies": {
    "@eslint/js": "^9.x",
    "@testing-library/jest-dom": "^6.6",
    "@testing-library/react": "^16.0",
    "@testing-library/user-event": "^14.5",
    "@types/react": "^19.0",
    "@types/react-dom": "^19.0",
    "@vitejs/plugin-react": "^4.3",
    "@vitest/coverage-v8": "^2.1",
    "eslint": "^9.x",
    "eslint-config-prettier": "^10.x",
    "eslint-plugin-jsx-a11y": "^6.10",
    "eslint-plugin-react-hooks": "^7.1.1",
    "eslint-plugin-react-refresh": "^0.5",
    "globals": "^15.x",
    "knip": "^6.x",
    "openapi-typescript": "^7.x",
    "prettier": "^3.8",
    "typescript": "^5.6",
    "typescript-eslint": "^8.59.3",
    "vite": "^6.0",
    "vitest": "^2.x"
  }
}
```

#### `.prettierrc.json` (standardised across all frontends)

```json
{
  "semi": true,
  "singleQuote": false,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "arrowParens": "always",
  "endOfLine": "lf"
}
```

Note: `pdomain-prep-for-pgdp` uses `printWidth: 80`; standardise to 100 to match
the Python `line-length = 100` convention across the workspace.

### Pre-commit hooks for frontends

Add these `local` entries to the Python `pre-commit-config.yaml` in repos
with a `frontend/` directory (currently `pdomain-prep-for-pgdp` and
`pdomain-ocr-labeler-spa`; will apply to `pdomain-ui`):

```yaml
  - repo: local
    hooks:
      # TypeScript type check
      - id: frontend-tsc
        name: frontend tsc -b --noEmit
        entry: bash -c 'if command -v mise >/dev/null 2>&1; then eval "$(mise
          activate bash --shims)" 2>/dev/null || true; fi; cd frontend && exec
          npx tsc -b --noEmit'
        language: system
        files:
          ^frontend/(src/.*\.(ts|tsx)|tsconfig.*\.json|package(-lock)?\.json|vite\.config\.ts)$
        pass_filenames: false

      # ESLint (full type-checked run)
      - id: frontend-eslint
        name: frontend eslint (type-checked)
        entry: bash -c 'if command -v mise >/dev/null 2>&1; then eval "$(mise
          activate bash --shims)" 2>/dev/null || true; fi; cd frontend && exec
          npm run --silent lint'
        language: system
        files:
          ^frontend/(src/.*\.(ts|tsx)|eslint\.config\.js|package(-lock)?\.json)$
        pass_filenames: false

      # Prettier format check
      - id: frontend-prettier
        name: frontend prettier --check
        entry: bash -c 'if command -v mise >/dev/null 2>&1; then eval "$(mise
          activate bash --shims)" 2>/dev/null || true; fi; cd frontend && exec
          npm run --silent format:check'
        language: system
        files:
          ^frontend/(src/.*|\.prettierrc\.json|\.prettierignore|package(-lock)?\.json|tsconfig.*\.json|vite\.config\.ts|vitest\.config\.ts)$
        pass_filenames: false
```

**Note on performance:** Type-checked ESLint (`projectService: true`) is slower
than type-unaware ESLint. On a typical pd-* frontend (~5k LOC), expect ~3–8
seconds per commit hook run. This is acceptable for LLM iteration — the rule
coverage gain outweighs the latency. If latency becomes a blocker, cache the
TypeScript program build with `parserOptions.disallowAutomaticSingleRunInference: false`
(the default) and let the parser cache persist across lint runs.

### CI workflow snippet (frontend)

```yaml
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install frontend dependencies
        run: cd frontend && npm ci

      - name: TypeScript type check
        run: cd frontend && npx tsc -b --noEmit

      - name: ESLint
        run: cd frontend && npm run lint

      - name: Prettier
        run: cd frontend && npm run format:check

      - name: Frontend tests
        run: cd frontend && npm test

      - name: Knip (dead code — informational, non-blocking)
        run: cd frontend && npm run knip || true
        # Remove `|| true` once the initial Knip baseline is clean
```

### Migration path for existing frontends

**pdomain-prep-for-pgdp/frontend** and **pdomain-ocr-labeler-spa/frontend**:

**Commit 1:** Update `devDependencies`: add `eslint-plugin-jsx-a11y ^6.10`,
`knip ^6.x`; bump `eslint-plugin-react-hooks` to `^7.1.1`; bump
`typescript-eslint` to `^8.59.3`. Run `npm install`.

**Commit 2:** Update `tsconfig.app.json`: add `noUncheckedIndexedAccess`,
`exactOptionalPropertyTypes`, `noImplicitOverride`,
`noPropertyAccessFromIndexSignature`, `useUnknownInCatchVariables`. Run
`npx tsc --noEmit` and fix all type errors surfaced (expect 10-50 in a
typical 5k-LOC frontend).

**Commit 3:** Update `eslint.config.js` to `strictTypeChecked` +
`stylisticTypeChecked` with `parserOptions.projectService: true`. Change
`@typescript-eslint/no-explicit-any` from `"warn"` to `"error"`. Run
`npm run lint` and fix all new errors.

**Commit 4:** Add `jsx-a11y.flatConfigs.recommended` to the ESLint config.
Fix any accessibility violations (usually image `alt` attributes and
ARIA roles).

**Commit 5:** Standardise `.prettierrc.json` to the canonical config above.
Run `npm run format` to apply. Commit the resulting diff.

---

## Cross-cutting infrastructure

### Pre-commit framework choice

**Use the Python `pre-commit` framework (pre-commit.com) for all repos.**
Rationale:
- Already used in every Python repo.
- Can host TS/React hooks via `language: system` (already done in
  `pdomain-prep-for-pgdp` and `pdomain-ocr-labeler-spa`).
- Single tool, single install (`uv run pre-commit install`), consistent UX
  across the workspace.
- **Reject** per-repo husky/simple-git-hooks: would require maintaining a
  parallel JS hook runner alongside the existing Python one.

### Secret detection

**Add `gitleaks` (rev: `v8.24.2`) to every repo's `.pre-commit-config.yaml`.**

```yaml
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.2
    hooks:
      - id: gitleaks
```

gitleaks scans only the staged diff (fast; typically <100ms). It catches
API keys, tokens, and passwords before they reach the remote. LLMs are
known to produce plausible-looking test credentials (e.g. `API_KEY =
"sk-test-XXXXXXXX"`) that pattern-match secret detectors — having
gitleaks at commit time surfaces these immediately.

Also add to CI:

```yaml
      - name: gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Commit-message linting

The workspace already uses a consistent conventional-commits style
(`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `build:`,
`style:` with optional `(scope):` parenthetical — visible in git log).

**Add `gitlint` (Python-native, no Node required) as a pre-commit hook:**

```yaml
  - repo: https://github.com/jorisroovers/gitlint
    rev: v0.19.1
    hooks:
      - id: gitlint
```

With `.gitlint` config at repo root:

```ini
[general]
ignore=body-is-missing
max-line-length=100
[title-must-not-contain-word]
words=WIP

[body-max-line-length]
line-length=100
```

**Why `gitlint` over `commitlint`?** `commitlint` is Node-only and would
require a `package.json` in every Python repo. `gitlint` is pure Python,
installs alongside `pre-commit` via `uv`, and integrates cleanly. For the
TS repos (`pdomain-ui`, `pdomain-index-npm`) that already have `package.json`, either
tool works — use `gitlint` for consistency across the workspace.

### Dependency-update bot

**Use Renovate** (not Dependabot). Reasons:
- Renovate groups related updates into a single PR (e.g. all `ruff-pre-commit`
  bumps across 9 repos into one PR). Dependabot creates 9 separate PRs.
- Renovate understands `uv.lock`, `Cargo.lock`, and npm lockfiles natively.
- Renovate's `grouping` and `packageRules` config can pin the ruff/pre-commit
  rev across all repos to the same version simultaneously.
- Renovate works at the org level (ConcaveTrillion org) with a single
  `renovate.json` in a dedicated config repo — one source of truth for all 12
  repos.

Example `renovate.json` for the org:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:base"],
  "packageRules": [
    {
      "matchPackageNames": ["ruff", "astral-sh/ruff-pre-commit"],
      "groupName": "ruff",
      "automerge": true
    },
    {
      "matchPackageNames": ["pre-commit-hooks"],
      "groupName": "pre-commit-hooks",
      "automerge": true
    },
    {
      "matchDepTypes": ["devDependencies"],
      "matchPackagePatterns": ["eslint.*", "typescript.*", "prettier"],
      "groupName": "frontend-dev-tooling",
      "automerge": false
    }
  ],
  "uv": { "enabled": true },
  "cargo": { "enabled": true }
}
```

### `.editorconfig`

**No `.editorconfig` exists in any repo.** Add one to every repo root.
It provides baseline settings that editors respect before any formatter
runs — useful for LLMs running in editor environments that lack format-on-save:

```ini
# .editorconfig
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

---

## What NOT to add (and why)

| Tool | Reason rejected |
|---|---|
| **pylint** | `ruff PL` covers ~90% of pylint's correctness rules at 50× speed. Pylint adds CI latency (typically 10-30s per repo) without meaningfully improving LLM error signal. `pdomain-book-tools` has it as a dev dep — remove it. |
| **mypy** | Basedpyright has 97.8% typing-spec conformance vs mypy's 58.3%. mypy's `--strict` mode still skips unannotated functions unless `--check-untyped-defs` is also added. Basedpyright checks everything by default. The two tools can disagree — running both is confusing for LLMs. Pick one. |
| **ty** (astral's new type checker) | ty 0.0.32 is in beta (May 2026) with 53.2% typing-spec conformance. Significant false-negative rate in strict mode makes it unsuitable as a gate. Revisit when 1.0 ships and conformance reaches ~90%. |
| **Biome** | Cannot run `strict-type-checked` typescript-eslint rules (requires TypeScript language service, which Biome's Rust engine does not use). Cannot run `eslint-plugin-react-hooks` or `eslint-plugin-jsx-a11y`. For a workspace that needs those rules, Biome is a regression not an improvement. |
| **oxlint** | Same limitation as Biome — fast but no type-aware rules. Complementary not competing with ESLint, but adding a second JS linter increases LLM confusion about which error source to trust. |
| **husky / simple-git-hooks** | Would require a `package.json` in every Python-only repo or a separate Git hooks installation path. The pre-commit framework already installed everywhere handles JS hooks via `language: system`. |
| **depcheck / npm-check-updates** | Superseded by Renovate (automated PR-based updates). Running `depcheck` in CI produces noise from peer deps and optional deps that aren't genuine issues. |
| **stylelint** | Neither `pdomain-prep-for-pgdp` nor `pdomain-ocr-labeler-spa` ship hand-written CSS files (all styles are Tailwind utility classes). Stylelint would fire on zero real violations. Add only if a frontend migrates to CSS Modules or plain CSS. |
| **pydocstyle (standalone)** | Integrated into ruff as `D` rules since ruff ≥ 0.1. No reason to run the standalone tool. |
| **isort (standalone)** | Integrated into ruff as `I` rules. Remove `isort` from dev deps in every repo where it appears. |
| **flake8** | Fully superseded by ruff. |

---

## Tradeoffs and known limitations

### `D` docstring rules on internal helpers

Enabling `D` across the board is high-noise in repos with many internal
functions (`_helpers.py`, `utils/`, tests). Recommended suppression pattern:

```toml
[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["D"]          # test functions don't need docstrings
"**/_*.py" = ["D"]               # private modules exempt
"**/migrations/**/*.py" = ["D"]  # generated migration files
```

Apply `# noqa: D102` or `# noqa: D103` on individual functions where
a docstring would be noise rather than signal (e.g. trivial property getters).

### `ANN` with Pydantic v2 models and `@dataclass`

Pydantic v2 fields are already annotated at the model level. `ANN001`
will not fire on Pydantic `BaseModel` subclasses because the fields carry
class-level annotations. For stdlib `@dataclass`, all fields are class-level
annotations so `ANN` is similarly quiet. `ANN` primarily fires on function
parameters and return types — exactly what we want.

Exception: `ANN401` (Dynamically typed expressions using `Any`) will fire
where `Any` is used intentionally. Suppress with `# noqa: ANN401` and a
comment explaining why.

### `TC` (type-checking import) rules and runtime `isinstance` checks

`TC001`/`TC002`/`TC003` suggest moving imports to `TYPE_CHECKING` blocks.
This is correct for pure annotation use but breaks runtime `isinstance(x,
MyClass)` checks where `MyClass` is imported only for typing. The fix:

```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pd_book_tools.ocr.page import Page

def process(page: "Page") -> None: ...  # forward ref works with __future__ annotations
```

Or suppress per-file where runtime imports are required for isinstance:

```toml
"src/**/runtime_checks.py" = ["TC001", "TC002"]
```

### `noUncheckedIndexedAccess` and existing frontend code

This flag changes `arr[0]` from type `T` to `T | undefined`. In existing
frontend code with hundreds of index accesses, enabling this flag will produce
dozens of type errors. The migration approach:
1. Run `tsc --noEmit` with the flag enabled.
2. Where the access is logically safe (e.g. `items[0]` after `if (items.length > 0)`),
   use optional chaining: `items[0]?.id`.
3. Where TypeScript can't narrow, use a non-null assertion with a comment:
   `items[0]!` — but only after a preceding guard.

### `exactOptionalPropertyTypes` and Pydantic-generated types

`openapi-typescript` generates types where optional properties use
`?: T` (potentially meaning `T | undefined`). With `exactOptionalPropertyTypes`,
assigning `undefined` to such a property is an error if the type doesn't
explicitly include `undefined`. The fix is to ensure the generated types
use `?: T | undefined` rather than `?: T`. The `openapi-typescript` v7+
CLI has `--export-type` flags that produce correct output — verify the
generated `types.gen.ts` file is compatible.

### Legacy `pd-ocr-labeler` (NiceGUI)

This repo is on a maintenance trajectory. Recommendations:
- Add `gitleaks` and `uv-lock-check` hooks (zero-friction, no code changes).
- Add `basedpyright>=1.39.4` at `typeCheckingMode = "standard"` (not `"recommended"`).
- Do NOT add `D` (docstring rules) — the codebase has zero docstrings and
  the investment isn't worth it for a repo being replaced.
- Keep `fail_under = 0` in coverage until the NiceGUI migration is complete.

### `pd-ocr-trainer` (setuptools build backend)

The non-standard `setuptools` build backend is a pre-existing divergence from
the workspace convention (`hatchling` everywhere else). This is orthogonal to
linting but should be flagged: migrate to `hatchling` in a dedicated chore
commit. The migration is mechanical — replace `[tool.setuptools]` with
`[tool.hatch.build.targets.wheel]` and update `pyproject.toml` build system.

### Performance of type-checked ESLint in pre-commit

Running `eslint` with `parserOptions.projectService: true` invokes the
TypeScript compiler service, which adds 3-8 seconds per hook run. This is
acceptable. If it becomes a blocker for fast-iteration workflows, the hook
can be moved from `stages: [pre-commit]` to `stages: [push]`:

```yaml
      - id: frontend-eslint
        name: frontend eslint (type-checked)
        # ...
        stages: [push]   # run on git push, not git commit
```

---

## Rollout order

Repos are ordered by: (1) fewest existing suppressions needed, (2) most
actively worked, (3) upstream dependencies first.

| Order | Repo | Why first/last | Est. effort |
|---|---|---|---|
| 1 | `pdomain-ocr-ops` | Greenfield; almost no existing code; set the gold standard now | 1-2h |
| 2 | `pdomain-ocr-cli` | Small codebase, 100% coverage floor, already well-linted | 2-3h |
| 3 | `pdomain-ocr-synth` | No pre-commit at all — establish baseline; spec-only state means less migration noise | 2-3h |
| 4 | `pdomain-book-tools` | Foundation library; strictest guarantees matter most; most suppressions to add | 4-6h |
| 5 | `pdomain-prep-for-pgdp` | Actively worked; frontend migration needed (tsconfig + ESLint) | 4-6h |
| 6 | `pdomain-ocr-labeler-spa` | Similar shape to pgdp-prep; do after pgdp-prep so patterns are established | 3-5h |
| 7 | `pd-png-optimizer` | Add `cargo deny`, expand Python lint rules, add basedpyright to Rust-facade Python | 2-3h |
| 8 | `pd-ocr-trainer` | Setuptools migration + full lint stack | 3-4h |
| 9 | `pdomain-ui` (incoming) | Greenfield TS library — apply full TS strict stack from day 1 | 1-2h |
| 10 | `pdomain-index-npm` (incoming) | Greenfield Node scripts — minimal surface | 1h |
| 11 | `pd-ocr-labeler` | Legacy; minimal investment; add gitleaks + uv-lock-check only | 1h |
| 12 | `se-llm-skills` | Separate framework; survey separately | varies |

**Parallel opportunities:** Steps 1-3 are fully independent and can be done
in parallel by three agents. Steps 5-6 share patterns and should be sequential
(5 first). Steps 9-10 are greenfield and can start any time.

---

## Sources

All URLs retrieved 2026-05-17.

- [Ruff rules reference](https://docs.astral.sh/ruff/rules/) — rule group prefixes and descriptions
- [Ruff configuration reference](https://docs.astral.sh/ruff/configuration/) — select/ignore/per-file-ignores syntax
- [Ruff linter guide](https://docs.astral.sh/ruff/linter/) — default rule sets, ANN/S/PERF/TC/D/PT/RET groups
- [basedpyright PyPI](https://pypi.org/project/basedpyright/) — version 1.39.4 (May 11, 2026)
- [basedpyright config docs](https://docs.basedpyright.com/latest/configuration/config-files/) — `"recommended"` and `"all"` modes, introduced in 1.21.0
- [pydevtools: type checker comparison](https://pydevtools.com/handbook/explanation/how-do-mypy-pyright-and-ty-compare/) — April 2026 benchmarks, conformance scores, version numbers
- [danilchenko.dev: ty vs mypy vs pyright](https://www.danilchenko.dev/posts/ty-vs-mypy-vs-pyright/) — conformance table, speed comparison
- [typescript-eslint shared configs](https://typescript-eslint.io/users/configs/) — strict-type-checked, stylistic-type-checked, projectService
- [typescript-eslint typed linting](https://typescript-eslint.io/getting-started/typed-linting/) — parserOptions.projectService configuration
- [typescript-eslint v8 announcement](https://typescript-eslint.io/blog/announcing-typescript-eslint-v8/) — v8 changes, ESLint v9 compatibility
- [react-hooks v6/v7 flat config](https://x.com/reactjs/status/1973518734708133989) — v6 introduced flat config; v7.1.1 is latest
- [Knip v6](https://knip.dev/) — dead code detection, ~150 plugins, version 6
- [Biome vs ESLint 2026](https://www.pkgpulse.com/blog/biome-vs-eslint-prettier-linting-2026) — performance comparison, type-aware rules limitation
- [Biome case study](https://fireup.pro/news/pre-commit-hooks-15x-faster-biome-vs-eslint-case-study) — 15× pre-commit speedup, but rule coverage gaps
- [gitleaks v8.24.2](https://github.com/gitleaks/gitleaks) — pre-commit hook, staged diff scanning
- [Renovate vs Dependabot monorepo](https://dev.to/alex_aslam/renovate-vs-dependabot-which-bot-will-rule-your-monorepo-4431) — grouping, multi-ecosystem support
- [Renovate bot comparison](https://docs.renovatebot.com/bot-comparison/) — official comparison with Dependabot
- [cargo-deny](https://pocketcmds.com/recipes/rust/rust-dependency-audit) — advisory + license checking, subsumes cargo-audit
- [ruff PyPI](https://pypi.org/project/ruff/) — version 0.15.13 (May 14, 2026)
