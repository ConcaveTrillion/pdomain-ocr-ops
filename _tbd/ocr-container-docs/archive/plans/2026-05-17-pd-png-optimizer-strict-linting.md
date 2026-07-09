---
status: complete
synced: 2026-05-17
milestone: 1
repo: ConcaveTrillion/pd-png-optimizer
---

# pd-png-optimizer — strict linting + type-check rollout (Python facade + Rust supply chain)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans`. Rollout step 7 — Rust + Python facade. The Python side is TINY (4 src + 5 test files, 0 existing suppressions). Per decision doc, this is the one repo where **`failOnWarnings = true` should be attempted from day 1** since there are no GPU/stub-noise deps. Rust side already has clippy + fmt; only `cargo deny` is missing.

**Reference:**
- Canonical Python pattern memory: `/home/vscode/.claude/projects/-workspaces-ocr-container/memory/project_strict_linting_canonical_pattern.md`
- Decision doc: [`docs/decisions/2026-05-17-strict-linting.md`](../decisions/2026-05-17-strict-linting.md) §Rust supply chain
- Full canonical Python template: [`docs/plans/2026-05-17-pdomain-book-tools-strict-linting-rollout.md`](2026-05-17-pdomain-book-tools-strict-linting-rollout.md)

**Working directory:** `/workspaces/ocr-container/pd-png-optimizer/`
**Python package:** `python/pd_png_optimizer/` (multi-Python facade, `requires-python = ">=3.9"`, `target-version = "py39"`)
**Rust workspace:** `crates/pd_png_optimizer/` + `crates/pd-png-opt/`
**Current head:** `d312a83`
**Discovery:**
- Python: 4 src + 5 test files, **0 suppressions**. No `[tool.pyright]` at all. Ruff at 7 codes (`E W F I B C4 UP`). No basedpyright, no gitleaks, no gitlint, no .editorconfig, no debug-statements/check-toml.
- Rust: `cargo clippy --workspace --all-targets -- -D warnings` and `cargo fmt --check` ALREADY wired in `.pre-commit-config.yaml` and Makefile. Pure Rust + PyO3 + maturin. No `deny.toml`.
- **GPU-irrelevant** (pure Rust) — no CuPy/cv2/DocTR stub noise. **`failOnWarnings = true` is achievable from day 1.**

---

## Suppression policy

Verbatim from [pdomain-book-tools plan §Suppression policy](2026-05-17-pdomain-book-tools-strict-linting-rollout.md). 7 rules; ~90 min per task max.

---

## Notable repo-specific concerns

- **Multi-Python facade** — `requires-python = ">=3.9"`, `target-version = "py39"`. **Do NOT use Python 3.10+ syntax** (`match` statements, `int | None` unions, `Self` types) — basedpyright + ruff target-version both protect against this.
- **basedpyright `pythonVersion = "3.9"`** must be set explicitly in `[tool.basedpyright]` (without it, basedpyright defaults to the host Python).
- **failOnWarnings = TRUE** (deviation from pdomain-book-tools deferral). 0 existing suppressions + no GPU stubs → enable directly. Document in commit.
- **Rust side: clippy + fmt already wired** — Tasks 4 (pre-commit) and 8 (basedpyright) DON'T touch the existing Rust hooks. Add a Rust-side task (Task R) for `cargo deny`.
- **`--all-features` is FORBIDDEN** in cargo commands here per decision doc (the `extension-module` feature breaks `cargo test` linking on Linux — enabled by maturin only at wheel build time). The existing clippy hook correctly omits `--all-features`.
- **PyO3 `_native` module** — basedpyright may flag the C-extension import as missing. Add `# pyright: ignore[reportMissingModuleSource]` or stub if needed.
- **No coverage floor currently** — leave it (out of scope).
- **Task 3 (remove isort/pylint) is NOOP** — neither present.

---

## Python tasks (1-8) mirror pdomain-book-tools f809701 — with deviations for failOnWarnings + pythonVersion

### Task 1: Add canonical `.editorconfig` (TRIVIAL) {#add-canonical-editorconfig-trivial}
- [ ] `cat /workspaces/ocr-container/pdomain-book-tools/.editorconfig > .editorconfig`
- [ ] Commit per pdomain-book-tools template.

### Task 2: Add basedpyright (standard mode initially) (TRIVIAL — no existing pyright config) {#add-basedpyright-standard-mode-initially-trivial-n}
- [ ] Add `"basedpyright>=1.39.4",` to `[dependency-groups] lint` (per existing pattern in this repo — `lint` is its own group).
- [ ] Append to `pyproject.toml`:
```toml
[tool.basedpyright]
include = ["python", "tests"]
exclude = ["**/__pycache__", "**/.venv", "**/node_modules", "target"]
typeCheckingMode = "standard"
pythonVersion = "3.9"
venvPath = "."
venv = ".venv"

[[tool.basedpyright.executionEnvironments]]
root = "tests"
```
**Note**: `pythonVersion = "3.9"` — critical for the multi-Python facade.
- [ ] `uv sync`. Run `uv run basedpyright python/ 2>&1 | tail -40`. With 4 source files and 0 suppressions, should be clean or near-clean at standard.
- [ ] Commit per pdomain-book-tools template (mention `pythonVersion = "3.9"`).

### Task 3: NOOP {#noop}

### Task 4: Extend pre-commit (TRIVIAL — extend, don't replace, to preserve Rust hooks) {#extend-pre-commit-trivial-extend-dont-replace-to-p}
- [ ] Edit `.pre-commit-config.yaml`. PRESERVE existing `cargo-fmt` + `cargo-clippy` local hooks.
- [ ] Add (from canonical):
  - `default_install_hook_types: [pre-commit, commit-msg]` at top.
  - Extend `pre-commit-hooks` block: add `check-toml`, `check-added-large-files [--maxkb=1000]`, `debug-statements`, `check-merge-conflict`.
  - Add `gitleaks v8.30.1` repo.
  - Add local hooks for `uv-lock-check` and `basedpyright` (entry: `uv run basedpyright python/pd_png_optimizer --level error`, files: `^python/pd_png_optimizer/.*\.py$`).
- [ ] Install + run + fix.
- [ ] Commit.

### Task 5: Add gitlint (TRIVIAL) {#add-gitlint-trivial}
- [ ] `cp /workspaces/ocr-container/pdomain-book-tools/.gitlint .gitlint`
- [ ] Add `"gitlint>=0.19.1",` to `[dependency-groups] lint`. `uv sync`.
- [ ] Add gitlint repo to `.pre-commit-config.yaml`.
- [ ] Re-install commit-msg hook.
- [ ] Commit.

### Task 6: Expand ruff select to canonical (TRIVIAL — clean slate) {#expand-ruff-select-to-canonical-trivial-clean-slat}
Current 7 codes → 24-rule canonical. 4 source files + 5 test files, 0 suppressions. Auto-fix likely handles most.

- [ ] Bump `"ruff>=0.13"` → `"ruff>=0.15.13"`.
- [ ] Replace `[tool.ruff.lint]` with canonical from pdomain-book-tools. KEEP `target-version = "py39"` in `[tool.ruff]`. KEEP `line-length = 100`.
- [ ] Add `[tool.ruff.lint.pydocstyle] convention = "google"`.
- [ ] Auto-fix: `uv run ruff check --fix --unsafe-fixes python/ tests/`. Should be minimal.
- [ ] Commit.

### Task 7: Pytest hardening (TRIVIAL) {#pytest-hardening-trivial}
- [ ] Replace `[tool.pytest.ini_options]`:
```toml
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--cov=pd_png_optimizer",
    "--cov-branch",
    "--cov-report=term-missing:skip-covered",
]
testpaths = ["tests"]
filterwarnings = ["error"]
```
- [ ] Add `"pytest-cov>=6.2.1",` to dev deps (already in `[dependency-groups] test`? verify). `uv sync`.
- [ ] Run pytest. Should be clean (small test suite, no stub-noise deps).
- [ ] Commit.

### Task 8: basedpyright recommended + **failOnWarnings = true** + Makefile/CI wiring (MODERATE) {#basedpyright-recommended-failonwarnings-true-makef}
**Deviation from pdomain-book-tools**: enable `failOnWarnings = true` directly. Document why in commit.

- [ ] In `[tool.basedpyright]`:
  - `typeCheckingMode = "standard"` → `typeCheckingMode = "recommended"`
  - Add `failOnWarnings = true` (NOT commented out)
  - Add `reportImportCycles = "none"`
- [ ] Add `typecheck:` Makefile target:
```makefile
typecheck: ## Run basedpyright at recommended mode (workspace canonical)
	uv run basedpyright python/pd_png_optimizer
```
**Note**: NO `--level error` here — we WANT warnings to fail since failOnWarnings=true makes basedpyright exit non-zero on them.
- [ ] Wire into `ci:` target. Current is `setup → lint → test → build`. Insert `typecheck` between `lint` and `test`:
```makefile
ci: ## Run complete CI pipeline (setup, lint, typecheck, test, build)
	@$(MAKE) --no-print-directory setup
	@$(MAKE) --no-print-directory lint
	@$(MAKE) --no-print-directory typecheck
	@$(MAKE) --no-print-directory test
	@$(MAKE) --no-print-directory build
```
- [ ] Update pre-commit `basedpyright` hook entry — drop `--level error` since failOnWarnings is now true. Use just `uv run basedpyright python/pd_png_optimizer`.
- [ ] Run `uv run basedpyright python/pd_png_optimizer 2>&1 | tail -40`. Triage anything that surfaces. With 4 source files and PyO3 facade, only the `_native` import may need annotation. Add `# pyright: ignore[reportMissingModuleSource]` on the import line with a comment.
- [ ] `make ci AI=1` must pass.
- [ ] Commit (note the failOnWarnings deviation from pdomain-book-tools):
```
feat(types): basedpyright recommended mode + failOnWarnings=true + wire into make ci

Mirrors pdomain-book-tools f809701 canonical pattern. typeCheckingMode =
'recommended' catches unannotated functions, inferred-Any propagation,
missing return types.

DEVIATION FROM pdomain-book-tools: failOnWarnings = true (not deferred).
This Python facade has 4 source files, no GPU/cv2/DocTR stub
dependencies, and zero pre-existing suppressions — the stub noise
that justified pdomain-book-tools' deferral does NOT apply here. Enable
strict mode from day 1.

pythonVersion = "3.9" preserved for multi-Python facade.

Per docs/decisions/2026-05-17-strict-linting.md.
```

---

## Rust task R: Add `cargo deny` (MODERATE)

Per decision doc §Rust supply chain. Adds 10-30s to CI but catches real vulnerability/license drift.

- [ ] Create `/workspaces/ocr-container/pd-png-optimizer/deny.toml`:
```toml
# cargo-deny configuration
# Per docs/decisions/2026-05-17-strict-linting.md §Rust supply chain.

[advisories]
db-path = "~/.cargo/advisory-db"
db-urls = ["https://github.com/rustsec/advisory-db"]
yanked = "deny"
ignore = []

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
deny = []
copyleft = "warn"
confidence-threshold = 0.93

[bans]
multiple-versions = "warn"
wildcards = "allow"

[sources]
unknown-registry = "warn"
unknown-git = "warn"
allow-registry = ["https://github.com/rust-lang/crates.io-index"]
allow-git = []
```
- [ ] Install `cargo-deny` locally (one-time): if not present, the Makefile target will fail with a clear instruction. Document in target comment.
- [ ] Add Makefile target:
```makefile
rust-deny: ## Run cargo deny check (license + advisory + multiple-versions)
	cargo deny check
```
- [ ] Wire into `ci:` target. Current (after Task 8) is `setup → lint → typecheck → test → build`. Add `rust-deny` after `lint`:
```makefile
ci:
	@$(MAKE) --no-print-directory setup
	@$(MAKE) --no-print-directory lint
	@$(MAKE) --no-print-directory rust-deny
	@$(MAKE) --no-print-directory typecheck
	@$(MAKE) --no-print-directory test
	@$(MAKE) --no-print-directory build
```
- [ ] Add CI step in `.github/workflows/ci.yml` (or wherever CI lives). If it currently just runs `make ci`, the new target is automatically picked up — verify by running `cargo deny check` locally first to catch any deny.toml gotchas.
- [ ] If CI runner doesn't have cargo-deny pre-installed, add an install step BEFORE `make ci`:
```yaml
      - name: Install cargo-deny
        run: cargo install cargo-deny --locked
```
OR use the action: `EmbarkStudios/cargo-deny-action@v2`.
- [ ] Run `cargo deny check`. Triage: bumps deny may flag license issues on existing crate deps. Adjust `licenses.allow` list if needed (with justification in comment).
- [ ] `make ci AI=1` must pass.
- [ ] Commit:
```
chore(rust): add cargo deny check for license + advisory + multi-version

Per docs/decisions/2026-05-17-strict-linting.md §Rust supply chain.

License allowlist: MIT, Apache-2.0 (incl. LLVM-exception variant),
BSD-2/3-Clause, ISC, Unlicense, Zlib. Yanked crates denied; unknown
registries warn (not present in our deps).

Wired into make ci between lint and typecheck; CI workflow gains
cargo-deny install step.
```

---

## Self-review checklist

- [ ] 7 Python commits land (Task 3 NOOP) + 1 Rust commit (Task R) = 8 total.
- [ ] No `--no-verify`.
- [ ] `make ci AI=1` green.
- [ ] `uv run basedpyright python/pd_png_optimizer` clean at recommended + failOnWarnings=true.
- [ ] `uv run ruff check python/ tests/` clean.
- [ ] `cargo deny check` clean.
- [ ] `cargo clippy --workspace --all-targets -- -D warnings` clean (already wired).
- [ ] `pythonVersion = "3.9"` set in basedpyright config.
- [ ] `target-version = "py39"` set in ruff config.
- [ ] failOnWarnings = true (deviation from pdomain-book-tools — documented in commit).

## Notes for the agent

- This is the SMALLEST Python rollout in the workspace (4 source files) but adds Rust supply chain on top. Total commits ~8.
- failOnWarnings=true is a deliberate deviation; the commit message must explain.
- DO NOT use `--all-features` in any cargo command.
- DO NOT use Python 3.10+ syntax in the Python facade.
- If a task overruns ~90min, STOP.
- Final report: "8 commits landed (Task 3 NOOP); final SHA: <X>; make ci AI=1 green; failOnWarnings=true ENABLED (no deferral needed — no stub-noise deps); cargo deny baseline clean; <flagged divergences from pdomain-book-tools>".
