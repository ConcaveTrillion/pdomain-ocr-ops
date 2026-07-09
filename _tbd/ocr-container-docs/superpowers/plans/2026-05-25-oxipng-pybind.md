# oxipng-pybind Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `oxipng-pybind/`, a focused Rust/PyO3 Python package that installs as `oxipng-pybind`, imports as `oxipng`, and supports file optimization `optimize(path, level=6)` usage.

**Architecture:** The repo is a standalone maturin project with a single Rust extension module named `oxipng`. The Rust crate aliases the upstream dependency as `oxi` so the Python module can keep the `oxipng` name. CI, docs, Make targets, and upstream bump automation follow the sibling `pd-*` repository style while keeping the API intentionally narrow.

**Tech Stack:** Rust 2021, PyO3, maturin, upstream `oxipng` crate, uv, pytest, Pillow, ruff, basedpyright, cargo-deny, GitHub Actions.

---

## File Structure

Create this new folder and files:

- `.gitignore`: parent workspace ignore entry for `/oxipng-pybind/`.
- `oxipng-pybind/.github/workflows/ci.yml`: GitHub CI entrypoint that runs `make ci`.
- `oxipng-pybind/.github/workflows/upstream-bump.yml`: scheduled/manual upstream bump workflow that opens a PR and enables auto-merge after checks pass.
- `oxipng-pybind/.gitignore`: ignores Python, Rust, build, and cache artifacts.
- `oxipng-pybind/.markdownlint-cli2.jsonc`: markdownlint config used by pre-commit.
- `oxipng-pybind/.pre-commit-config.yaml`: Python, Rust, and markdown hooks.
- `oxipng-pybind/Cargo.toml`: Rust package, PyO3 extension, and aliased upstream `oxipng` dependency.
- `oxipng-pybind/Cargo.lock`: generated lockfile.
- `oxipng-pybind/Makefile`: local development, CI, build, clean, and release-adjacent targets.
- `oxipng-pybind/README.md`: user-facing package docs.
- `oxipng-pybind/THIRD_PARTY_NOTICES.md`: upstream attribution and license notes.
- `oxipng-pybind/deny.toml`: cargo-deny policy.
- `oxipng-pybind/docs/README.md`: docs index.
- `oxipng-pybind/docs/process/upstream-bumps.md`: workflow and auto-merge setup docs.
- `oxipng-pybind/docs/usage/file-optimization.md`: exact File optimization usage docs.
- `oxipng-pybind/oxipng.pyi`: public typing stub for the extension module.
- `oxipng-pybind/pyproject.toml`: Python package metadata, maturin config, and tool configs.
- `oxipng-pybind/scripts/ai-filter-log.py`: concise CI log filter used by `make AI=1`.
- `oxipng-pybind/scripts/bump_upstream.py`: version bump helper used by the workflow.
- `oxipng-pybind/src/lib.rs`: PyO3 extension implementation.
- `oxipng-pybind/tests/conftest.py`: generated PNG fixtures.
- `oxipng-pybind/tests/test_api.py`: supported Python API contract tests.
- `oxipng-pybind/tests/test_bump_upstream.py`: bump script unit tests.
- `oxipng-pybind/uv.lock`: generated lockfile.

Do not add local-dev or update-pd-deps scripts. This repo has no sibling `pd-*` runtime dependencies.

Repository boundary:

- `ocr-container-meta` must ignore `/oxipng-pybind/`.
- `oxipng-pybind/` must be initialized as its own Git repository.
- Package commits in this plan run inside `oxipng-pybind/`, with paths relative
  to that nested repo.
- The parent meta repo should only track the workspace `.gitignore` and
  planning/spec documents for this work.

---

### Task 1: Scaffold Build Metadata

**Files:**
- Modify: `.gitignore`
- Create: `oxipng-pybind/.git`
- Create: `oxipng-pybind/.gitignore`
- Create: `oxipng-pybind/Cargo.toml`
- Create: `oxipng-pybind/pyproject.toml`
- Create: `oxipng-pybind/oxipng.pyi`
- Create: `oxipng-pybind/README.md`

- [ ] **Step 1: Ignore and create the nested repo folder**

Run:

```bash
grep -qxF '/oxipng-pybind/' .gitignore || sed -i '/\\/se-llm-skills\\//a /oxipng-pybind/' .gitignore
mkdir -p oxipng-pybind/src oxipng-pybind/tests oxipng-pybind/scripts oxipng-pybind/docs/process oxipng-pybind/docs/usage oxipng-pybind/.github/workflows
cd oxipng-pybind && git init -b main
```

Expected: command exits 0 and `oxipng-pybind/.git/` exists.

- [ ] **Step 2: Write `Cargo.toml`**

Create `oxipng-pybind/Cargo.toml`:

```toml
[package]
name = "oxipng-pybind"
version = "10.1.1"
edition = "2021"
license = "MIT"
description = "Focused Python wrapper for oxipng"
repository = "https://github.com/pdomain/oxipng-pybind"
rust-version = "1.85.1"

[lib]
name = "oxipng"
crate-type = ["cdylib", "rlib"]

[dependencies]
oxi = { package = "oxipng", version = "=10.1.1", default-features = false, features = ["parallel", "zopfli"] }
pyo3 = { version = "0.25.1", features = ["extension-module"] }

[profile.release]
lto = "fat"
strip = "symbols"
```

- [ ] **Step 3: Write the initial README required by package metadata**

Create `oxipng-pybind/README.md`:

````markdown
# oxipng-pybind

`oxipng-pybind` is a focused Python wrapper around the Rust `oxipng` library.

The distribution is named `oxipng-pybind`, but the import module is `oxipng`.
The supported API is intentionally narrow:

```python
from oxipng import optimize

optimize(path, level=6)
```
````

- [ ] **Step 4: Write `pyproject.toml`**

Create `oxipng-pybind/pyproject.toml`:

```toml
[build-system]
requires = ["maturin>=1.8,<2.0"]
build-backend = "maturin"

[project]
name = "oxipng-pybind"
version = "10.1.1"
description = "Focused Python wrapper for oxipng."
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
authors = [
    { name = "ConcaveTrillion", email = "ConcaveTrillion@gmail.com" },
]
keywords = ["png", "optimizer", "oxipng", "file-optimization"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Rust",
    "Topic :: Multimedia :: Graphics",
    "Topic :: Utilities",
]
dependencies = []

[project.urls]
Repository = "https://github.com/pdomain/oxipng-pybind"
Issues = "https://github.com/pdomain/oxipng-pybind/issues"
Upstream = "https://github.com/oxipng/oxipng"

[dependency-groups]
test = [
    "pillow>=10.0",
    "pytest>=8.4",
    "pytest-cov>=6.2.1",
    "pytest-xdist>=3.6",
]
lint = [
    "basedpyright>=1.39.4",
    "gitlint>=0.19.1",
    "pre-commit>=4.3",
    "ruff>=0.13",
]
build = [
    "maturin>=1.8,<2.0",
]
automation = [
    "tomlkit>=0.13",
]
dev = [
    { include-group = "test" },
    { include-group = "lint" },
    { include-group = "build" },
    { include-group = "automation" },
]

[tool.maturin]
module-name = "oxipng"
features = ["pyo3/extension-module"]
include = [
    { path = "oxipng.pyi", format = ["sdist", "wheel"] },
]
strip = true

[tool.pytest.ini_options]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
]
testpaths = ["tests"]
filterwarnings = ["error"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = [
    "ANN",
    "B",
    "BLE",
    "C4",
    "D",
    "E",
    "ERA",
    "F",
    "G",
    "I",
    "LOG",
    "N",
    "PERF",
    "PL",
    "PT",
    "RET",
    "RUF",
    "S",
    "SIM",
    "T20",
    "TC",
    "TID",
    "TRY",
    "UP",
    "W",
]
ignore = [
    "COM812",
    "D100",
    "D104",
    "D107",
    "D203",
    "D212",
    "E501",
    "TRY003",
]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["ANN", "D", "PLR2004", "S101", "S108"]
"scripts/*.py" = ["D", "S310", "S603", "T201"]

[tool.basedpyright]
include = ["oxipng.pyi", "tests", "scripts"]
exclude = ["**/__pycache__", "**/.venv", "target"]
typeCheckingMode = "recommended"
failOnWarnings = true
pythonVersion = "3.10"
venvPath = "."
venv = ".venv"
reportAny = "none"
reportExplicitAny = "none"
reportMissingTypeStubs = "none"
reportUnusedCallResult = "none"
```

- [ ] **Step 5: Write the public stub**

Create `oxipng-pybind/oxipng.pyi`:

```python
"""Typing stub for the supported oxipng-pybind API."""

from os import PathLike
from typing import Union

StrOrBytesPath = Union[str, bytes, PathLike[str], PathLike[bytes]]


class PngError(Exception):
    """Raised when oxipng cannot optimize the input PNG."""


def optimize(input: StrOrBytesPath, output: StrOrBytesPath | None = None, *, level: int = 2) -> None:
    """Optimize a PNG file on disk."""
```

- [ ] **Step 6: Write `.gitignore`**

Create `oxipng-pybind/.gitignore`:

```gitignore
.cache/
.coverage
.ci-ai.log
.mypy_cache/
.pytest_cache/
.ruff_cache/
.venv/
__pycache__/
build/
dist/
htmlcov/
target/
*.egg-info/
*.pyc
```

- [ ] **Step 7: Verify metadata parses and generate lockfiles**

Run:

```bash
cd oxipng-pybind && uv sync --group dev && cargo generate-lockfile
```

Expected: uv creates `.venv/` and `uv.lock`, and cargo creates `Cargo.lock`.

- [ ] **Step 8: Commit**

```bash
git add .gitignore Cargo.toml Cargo.lock README.md pyproject.toml oxipng.pyi uv.lock
git commit -m "chore: scaffold oxipng-pybind package metadata"
```

Run the commit commands from inside `oxipng-pybind/`.

---

### Task 2: Implement Minimal Native API

**Files:**
- Create: `oxipng-pybind/src/lib.rs`
- Create: `oxipng-pybind/tests/conftest.py`
- Create: `oxipng-pybind/tests/test_api.py`
- Modify: `oxipng-pybind/Cargo.lock`

- [ ] **Step 1: Write failing API tests**

Create `oxipng-pybind/tests/conftest.py`:

```python
"""Shared test fixtures."""

from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin


@pytest.fixture
def png_path(tmp_path: Path) -> Path:
    """Create a small PNG that oxipng can optimize."""
    path = tmp_path / "cover.png"
    info = PngImagePlugin.PngInfo()
    info.add_text("Comment", "metadata makes this fixture less optimized")
    image = Image.new("RGBA", (32, 32), (255, 255, 255, 255))
    image.save(path, pnginfo=info)
    return path


@pytest.fixture
def corrupt_png_path(tmp_path: Path) -> Path:
    """Create a file that is not a PNG."""
    path = tmp_path / "not-a-png.png"
    path.write_bytes(b"not a png")
    return path
```

Create `oxipng-pybind/tests/test_api.py`:

```python
"""Supported public API tests."""

from pathlib import Path

import pytest
from PIL import Image


def assert_readable_png(path: Path) -> None:
    """Assert that Pillow can read the optimized PNG."""
    with Image.open(path) as image:
        image.verify()


def test_import_supported_api() -> None:
    from oxipng import PngError, optimize

    assert callable(optimize)
    assert issubclass(PngError, Exception)


def test_optimize_in_place_with_file_optimization_level(png_path: Path) -> None:
    from oxipng import optimize

    optimize(png_path, level=6)

    assert_readable_png(png_path)


def test_optimize_to_output_path(png_path: Path, tmp_path: Path) -> None:
    from oxipng import optimize

    output = tmp_path / "optimized.png"
    optimize(png_path, output, level=6)

    assert output.exists()
    assert_readable_png(output)
    assert_readable_png(png_path)


@pytest.mark.parametrize("level", [-1, 7])
def test_invalid_level_raises_value_error(png_path: Path, level: int) -> None:
    from oxipng import optimize

    with pytest.raises(ValueError, match="level must be between 0 and 6"):
        optimize(png_path, level=level)


def test_unsupported_keyword_raises_type_error(png_path: Path) -> None:
    from oxipng import optimize

    with pytest.raises(TypeError, match="unsupported option: strip"):
        optimize(png_path, level=6, strip="safe")  # type: ignore[call-arg]


def test_corrupt_input_raises_png_error(corrupt_png_path: Path) -> None:
    from oxipng import PngError, optimize

    with pytest.raises(PngError):
        optimize(corrupt_png_path, level=6)
```

- [ ] **Step 2: Run tests and verify import failure**

Run:

```bash
cd oxipng-pybind && uv run pytest tests/test_api.py -v
```

Expected: FAIL because `oxipng` is not importable yet.

- [ ] **Step 3: Implement `src/lib.rs`**

Create `oxipng-pybind/src/lib.rs`:

```rust
use pyo3::create_exception;
use pyo3::exceptions::{PyException, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::path::PathBuf;

create_exception!(oxipng, PngError, PyException);

fn parse_options(kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<oxi::Options> {
    let mut level = 2_u8;

    if let Some(dict) = kwargs {
        for (key, value) in dict.iter() {
            let key: String = key.extract()?;

            match key.as_str() {
                "level" => {
                    let parsed: i64 = value.extract().map_err(|_| {
                        PyValueError::new_err("level must be an integer from 0 to 6")
                    })?;

                    if !(0..=6).contains(&parsed) {
                        return Err(PyValueError::new_err(
                            "level must be between 0 and 6 inclusive",
                        ));
                    }

                    level = parsed as u8;
                }
                _ => {
                    return Err(PyTypeError::new_err(format!("unsupported option: {key}")));
                }
            }
        }
    }

    Ok(oxi::Options::from_preset(level))
}

fn map_png_error(error: oxi::PngError) -> PyErr {
    PngError::new_err(error.to_string())
}

#[pyfunction]
#[pyo3(signature = (input, output=None, **kwargs))]
fn optimize(
    input: PathBuf,
    output: Option<PathBuf>,
    kwargs: Option<&Bound<'_, PyDict>>,
) -> PyResult<()> {
    let input_file = oxi::InFile::Path(input);
    let output_file = match output {
        Some(path) => oxi::OutFile::from_path(path),
        None => oxi::OutFile::Path {
            path: None,
            preserve_attrs: false,
        },
    };

    oxi::optimize(&input_file, &output_file, &parse_options(kwargs)?).map_err(map_png_error)
}

#[pymodule]
fn oxipng(py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add("PngError", py.get_type::<PngError>())?;
    module.add_function(wrap_pyfunction!(optimize, module)?)?;
    Ok(())
}
```

- [ ] **Step 4: Build editable extension**

Run:

```bash
cd oxipng-pybind && uv run maturin develop
```

Expected: maturin builds and installs the local `oxipng` extension into `.venv/`.

- [ ] **Step 5: Run API tests**

Run:

```bash
cd oxipng-pybind && uv run pytest tests/test_api.py -v
```

Expected: PASS for all tests in `tests/test_api.py`.

- [ ] **Step 6: Run Rust tests**

Run:

```bash
cd oxipng-pybind && cargo test
```

Expected: PASS. There may be zero Rust unit tests at this point; compilation is the check.

- [ ] **Step 7: Commit**

```bash
git add src/lib.rs tests/conftest.py tests/test_api.py Cargo.lock
git commit -m "feat: add file optimization oxipng API"
```

Run the commit commands from inside `oxipng-pybind/`.

---

### Task 3: Add Makefile And Quality Tooling

**Files:**
- Create: `oxipng-pybind/Makefile`
- Create: `oxipng-pybind/scripts/ai-filter-log.py`
- Create: `oxipng-pybind/.pre-commit-config.yaml`
- Create: `oxipng-pybind/.markdownlint-cli2.jsonc`
- Create: `oxipng-pybind/deny.toml`

- [ ] **Step 1: Write `scripts/ai-filter-log.py`**

Create `oxipng-pybind/scripts/ai-filter-log.py`:

```python
#!/usr/bin/env python3
"""Print a concise tail of a failed command log."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    """Print the final log lines for quick agent feedback."""
    if len(sys.argv) != 2:
        print("usage: ai-filter-log.py LOG", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"log file not found: {path}", file=sys.stderr)
        return 1

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-120:]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Write `Makefile`**

Create `oxipng-pybind/Makefile`:

```makefile
AI ?=
LOG := .ci-ai.log

ifdef AI
_goals := $(or $(MAKECMDGOALS),ci)
.PHONY: $(_goals)
$(_goals):
	@rm -f $(LOG)
	@$(MAKE) --no-print-directory AI= $@ > $(LOG) 2>&1 \
		&& echo "$@ passed (log: $(LOG))" \
		|| (echo "$@ failed:"; uv run scripts/ai-filter-log.py $(LOG); echo "(full log: $(LOG))"; exit 1)

else

.PHONY: help setup develop test test-rust test-py lint lint-fix py-lint py-lint-fix \
	rust-lint rust-lint-fix md-lint md-lint-fix format format-check typecheck \
	rust-deny pre-commit-check build wheel clean clean-cache reset remove-venv \
	upgrade-deps ci

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

setup: ## Sync deps, build editable extension, and install pre-commit hooks
	uv sync --group dev
	uv run maturin develop
	-uv run pre-commit install

develop: ## Build and install the editable extension
	uv run maturin develop

test: test-rust test-py ## Run all tests

test-rust: ## Run Rust tests
	cargo test

test-py: ## Run Python tests against editable extension
	uv run maturin develop --quiet
	uv run pytest -v -ra -n auto

lint: rust-lint py-lint md-lint ## Run all lint checks

lint-fix: rust-lint-fix py-lint-fix md-lint-fix ## Apply automatic lint fixes

rust-lint: ## Run cargo clippy
	cargo clippy --workspace --all-targets -- -D warnings

rust-lint-fix: ## Run cargo clippy --fix
	cargo clippy --workspace --all-targets --fix --allow-dirty --allow-staged -- -D warnings

py-lint: ## Run ruff check
	uv run ruff check .

py-lint-fix: ## Run ruff format and ruff check --fix
	uv run ruff format
	uv run ruff check --fix .

md-lint: ## Run markdownlint via pre-commit
	-uv run pre-commit run markdownlint-cli2 --all-files

md-lint-fix: ## Run markdownlint auto-fix via pre-commit
	-uv run pre-commit run --hook-stage manual markdownlint-cli2-fix --all-files

format: ## Format Rust and Python, then run lint
	cargo fmt --all
	uv run ruff format
	@$(MAKE) --no-print-directory lint

format-check: ## Check formatting without writes
	cargo fmt --all -- --check
	uv run ruff format --check .

typecheck: ## Run basedpyright
	uv run basedpyright

rust-deny: ## Run cargo deny
	cargo deny check

pre-commit-check: ## Run all pre-commit hooks
	uv run pre-commit run --all-files

build: wheel ## Build release artifacts

wheel: ## Build optimized Python wheel
	uv run maturin build --release

clean: ## Remove generated files and build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ htmlcov/ target/wheels/ 2>/dev/null || true
	@$(MAKE) --no-print-directory clean-cache

clean-cache: ## Remove project cache
	rm -rf .cache/ 2>/dev/null || true

remove-venv: ## Remove virtual environment
	rm -rf .venv

reset: clean remove-venv setup ## Rebuild local environment

upgrade-deps: ## Upgrade Python and Rust lockfiles
	uv lock --upgrade
	cargo update
	uv sync --group dev
	uv run maturin develop

ci: ## Run full CI
	@$(MAKE) --no-print-directory setup
	@$(MAKE) --no-print-directory lint
	@$(MAKE) --no-print-directory rust-deny
	@$(MAKE) --no-print-directory typecheck
	@$(MAKE) --no-print-directory test
	@$(MAKE) --no-print-directory build

.DEFAULT_GOAL := help

-include Makefile.local

endif
```

- [ ] **Step 3: Write pre-commit config**

Create `oxipng-pybind/.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-toml
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.13.0
    hooks:
      - id: ruff-check
        args: ["--fix"]
      - id: ruff-format
  - repo: https://github.com/DavidAnson/markdownlint-cli2
    rev: v0.18.1
    hooks:
      - id: markdownlint-cli2
      - id: markdownlint-cli2-fix
        stages: [manual]
  - repo: local
    hooks:
      - id: cargo-fmt
        name: cargo fmt
        entry: cargo fmt --all -- --check
        language: system
        pass_filenames: false
      - id: cargo-clippy
        name: cargo clippy
        entry: cargo clippy --workspace --all-targets -- -D warnings
        language: system
        pass_filenames: false
```

- [ ] **Step 4: Write markdownlint config**

Create `oxipng-pybind/.markdownlint-cli2.jsonc`:

```jsonc
{
  "config": {
    "MD013": false,
    "MD033": false
  },
  "globs": ["**/*.md", "!target/**", "!.venv/**"]
}
```

- [ ] **Step 5: Write cargo-deny config**

Create `oxipng-pybind/deny.toml`:

```toml
[advisories]
ignore = []

[licenses]
allow = [
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "MIT",
    "Unicode-3.0",
    "Zlib",
]
confidence-threshold = 0.8

[bans]
multiple-versions = "warn"
wildcards = "deny"

[sources]
unknown-registry = "deny"
unknown-git = "deny"
```

- [ ] **Step 6: Verify Make targets**

Run:

```bash
cd oxipng-pybind && make AI=1 format-check
```

Expected: PASS.

Run:

```bash
cd oxipng-pybind && make AI=1 test
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add Makefile scripts/ai-filter-log.py .pre-commit-config.yaml .markdownlint-cli2.jsonc deny.toml
git commit -m "chore: add oxipng-pybind quality tooling"
```

Run the commit commands from inside `oxipng-pybind/`.

---

### Task 4: Add Documentation And Notices

**Files:**
- Modify: `oxipng-pybind/README.md`
- Create: `oxipng-pybind/THIRD_PARTY_NOTICES.md`
- Create: `oxipng-pybind/docs/README.md`
- Create: `oxipng-pybind/docs/process/upstream-bumps.md`
- Create: `oxipng-pybind/docs/usage/file-optimization.md`

- [ ] **Step 1: Replace README with full package docs**

Replace `oxipng-pybind/README.md` with:

````markdown
# oxipng-pybind

`oxipng-pybind` is a focused Python wrapper around the Rust
[`oxipng`](https://github.com/oxipng/oxipng) library.

It exists to support the PNG optimization API currently used by Standard
Ebooks tooling while tracking current upstream `oxipng` releases.

## Install

```bash
pip install oxipng-pybind
```

## Supported API

The distribution is named `oxipng-pybind`, but the import module is `oxipng`.

```python
from oxipng import optimize

optimize(path, level=6)
```

Supported objects:

- `oxipng.optimize(input, output=None, *, level=2)`
- `oxipng.PngError`

`input` and `output` may be strings, bytes paths, or `os.PathLike` values.
When `output` is omitted, the input file is optimized in place.

`level` must be an integer from `0` through `6`.

## Unsupported pyoxipng APIs

This package is not a full `pyoxipng` replacement. These APIs are intentionally
not provided:

- `optimize_from_memory`
- `RawImage`
- `ColorType`
- `RowFilter`
- `Interlacing`
- `StripChunks`
- `Deflaters`

Unsupported keyword arguments to `optimize()` raise `TypeError`.

## Development

```bash
make setup
make test
make lint
make typecheck
make ci
```

## Upstream Tracking

Package versions mirror upstream `oxipng` versions when practical. The
scheduled upstream bump workflow opens a pull request when a new upstream
release is available. Auto-merge is enabled only after the repository's
required checks pass.

## License

This wrapper is MIT licensed. Upstream `oxipng` is MIT licensed. See
`THIRD_PARTY_NOTICES.md`.
````

- [ ] **Step 2: Write docs index**

Create `oxipng-pybind/docs/README.md`:

```markdown
# oxipng-pybind Docs

- [File optimization usage](usage/file-optimization.md)
- [Upstream bump process](process/upstream-bumps.md)
```

- [ ] **Step 3: Write File optimization usage docs**

Create `oxipng-pybind/docs/usage/file-optimization.md`:

````markdown
# File optimization Usage

File-based callers can import `optimize` from the `oxipng` module and calls
it with `level=6`.

```python
from pathlib import Path

from oxipng import optimize

path = Path("cover.png")
optimize(path, level=6)
```

This package supports that API directly. It does not require file-based callers to
change the import from `oxipng` to `oxipng_pybind`.
````

- [ ] **Step 4: Write upstream bump docs**

Create `oxipng-pybind/docs/process/upstream-bumps.md`:

```markdown
# Upstream Bumps

`oxipng-pybind` tracks upstream `oxipng` releases.

The scheduled `upstream-bump.yml` workflow:

1. Reads the latest release from `oxipng/oxipng`.
2. Updates `Cargo.toml`, `Cargo.lock`, and `pyproject.toml`.
3. Runs the full repository CI.
4. Opens a pull request when files changed.
5. Enables auto-merge for that pull request.

The workflow does not push directly to `main`.

## Required Repository Settings

Enable these GitHub settings for CI-gated auto-merge:

- Allow GitHub Actions to create and approve pull requests.
- Enable auto-merge for the repository.
- Protect `main`.
- Require the `ci` workflow to pass before merging.

If upstream `oxipng` changes break the wrapper, CI fails and the bump PR remains
open for manual repair.
```

- [ ] **Step 5: Write third-party notices**

Create `oxipng-pybind/THIRD_PARTY_NOTICES.md`:

```markdown
# Third-Party Notices

`oxipng-pybind` wraps upstream `oxipng`.

## oxipng

- Project: https://github.com/oxipng/oxipng
- License: MIT
- Purpose: lossless PNG optimization library

Rust and Python build dependencies retain their own licenses. Run
`make rust-deny` to verify Rust dependency license policy.
```

- [ ] **Step 6: Run docs checks**

Run:

```bash
cd oxipng-pybind && make AI=1 md-lint
```

Expected: PASS or markdownlint hook reports no blocking errors.

- [ ] **Step 7: Commit**

```bash
git add README.md THIRD_PARTY_NOTICES.md docs
git commit -m "docs: document oxipng-pybind usage and upstream bumps"
```

Run the commit commands from inside `oxipng-pybind/`.

---

### Task 5: Add Upstream Bump Script

**Files:**
- Create: `oxipng-pybind/scripts/bump_upstream.py`
- Create: `oxipng-pybind/tests/test_bump_upstream.py`

- [ ] **Step 1: Write failing script tests**

Create `oxipng-pybind/tests/test_bump_upstream.py`:

```python
"""Tests for upstream bump helpers."""

from pathlib import Path

import tomlkit

from scripts.bump_upstream import normalize_version, update_cargo_toml, update_pyproject_toml


def test_normalize_version_strips_v_prefix() -> None:
    assert normalize_version("v10.1.1") == "10.1.1"
    assert normalize_version("10.1.1") == "10.1.1"


def test_update_pyproject_toml(tmp_path: Path) -> None:
    path = tmp_path / "pyproject.toml"
    path.write_text(
        """
[project]
name = "oxipng-pybind"
version = "10.1.0"
""".lstrip(),
        encoding="utf-8",
    )

    update_pyproject_toml(path, "10.1.1")

    data = tomlkit.parse(path.read_text(encoding="utf-8"))
    assert data["project"]["version"] == "10.1.1"


def test_update_cargo_toml(tmp_path: Path) -> None:
    path = tmp_path / "Cargo.toml"
    path.write_text(
        """
[package]
name = "oxipng-pybind"
version = "10.1.0"

[dependencies]
oxi = { package = "oxipng", version = "=10.1.0", default-features = false, features = ["parallel", "zopfli"] }
""".lstrip(),
        encoding="utf-8",
    )

    update_cargo_toml(path, "10.1.1")

    data = tomlkit.parse(path.read_text(encoding="utf-8"))
    assert data["package"]["version"] == "10.1.1"
    assert data["dependencies"]["oxi"]["version"] == "=10.1.1"
```

- [ ] **Step 2: Make script importable in tests**

Run:

```bash
touch oxipng-pybind/scripts/__init__.py
```

Expected: `scripts` becomes an importable package for pytest.

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
cd oxipng-pybind && uv run pytest tests/test_bump_upstream.py -v
```

Expected: FAIL because `scripts.bump_upstream` does not exist.

- [ ] **Step 4: Write bump script**

Create `oxipng-pybind/scripts/bump_upstream.py`:

```python
#!/usr/bin/env python3
"""Bump oxipng-pybind to the latest upstream oxipng release."""

from __future__ import annotations

import json
import subprocess
import urllib.request
from pathlib import Path

import tomlkit

ROOT = Path(__file__).resolve().parents[1]
LATEST_RELEASE_URL = "https://api.github.com/repos/oxipng/oxipng/releases/latest"


def normalize_version(version: str) -> str:
    """Normalize GitHub tag names to packaging versions."""
    return version.removeprefix("v")


def latest_upstream_version() -> str:
    """Fetch the latest upstream oxipng release version."""
    with urllib.request.urlopen(LATEST_RELEASE_URL, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return normalize_version(str(payload["tag_name"]))


def update_pyproject_toml(path: Path, version: str) -> None:
    """Update the Python package version."""
    document = tomlkit.parse(path.read_text(encoding="utf-8"))
    document["project"]["version"] = version
    path.write_text(tomlkit.dumps(document), encoding="utf-8")


def update_cargo_toml(path: Path, version: str) -> None:
    """Update the Rust package and upstream dependency versions."""
    document = tomlkit.parse(path.read_text(encoding="utf-8"))
    document["package"]["version"] = version
    document["dependencies"]["oxi"]["version"] = f"={version}"
    path.write_text(tomlkit.dumps(document), encoding="utf-8")


def update_cargo_lock(version: str) -> None:
    """Refresh Cargo.lock for the requested upstream oxipng version."""
    subprocess.run(
        ["cargo", "update", "-p", "oxipng", "--precise", version],
        cwd=ROOT,
        check=True,
    )


def main() -> int:
    """Bump all tracked version files to the latest upstream release."""
    version = latest_upstream_version()
    update_pyproject_toml(ROOT / "pyproject.toml", version)
    update_cargo_toml(ROOT / "Cargo.toml", version)
    update_cargo_lock(version)
    print(f"updated oxipng-pybind to oxipng {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run bump script tests**

Run:

```bash
cd oxipng-pybind && uv run pytest tests/test_bump_upstream.py -v
```

Expected: PASS.

- [ ] **Step 6: Run ruff on script**

Run:

```bash
cd oxipng-pybind && uv run ruff check scripts tests/test_bump_upstream.py
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/__init__.py scripts/bump_upstream.py tests/test_bump_upstream.py
git commit -m "chore: add upstream bump helper"
```

Run the commit commands from inside `oxipng-pybind/`.

---

### Task 6: Add GitHub Actions

**Files:**
- Create: `oxipng-pybind/.github/workflows/ci.yml`
- Create: `oxipng-pybind/.github/workflows/upstream-bump.yml`

- [ ] **Step 1: Write CI workflow**

Create `oxipng-pybind/.github/workflows/ci.yml`:

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
      - name: Install cargo-deny
        run: cargo install cargo-deny --locked
      - run: make ci
```

- [ ] **Step 2: Write upstream bump workflow**

Create `oxipng-pybind/.github/workflows/upstream-bump.yml`:

```yaml
name: upstream-bump

on:
  workflow_dispatch:
  schedule:
    - cron: "17 9 * * 1"

permissions:
  contents: write
  pull-requests: write

jobs:
  bump:
    name: bump oxipng
    runs-on: ubuntu-latest
    env:
      UV_PYTHON: "3.13"
      GH_TOKEN: ${{ github.token }}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: latest
      - name: Install cargo-deny
        run: cargo install cargo-deny --locked
      - name: Sync dependencies
        run: uv sync --group dev
      - name: Bump upstream
        run: uv run python scripts/bump_upstream.py
      - name: Check for changes
        id: changes
        run: |
          if git diff --quiet; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
          else
            echo "changed=true" >> "$GITHUB_OUTPUT"
          fi
      - name: Run CI before opening PR
        if: steps.changes.outputs.changed == 'true'
        run: make ci
      - name: Create pull request
        if: steps.changes.outputs.changed == 'true'
        id: cpr
        uses: peter-evans/create-pull-request@v6
        with:
          commit-message: "chore: bump upstream oxipng"
          title: "chore: bump upstream oxipng"
          body: |
            Automated upstream oxipng bump.

            Auto-merge is enabled only after required checks pass.
          branch: automation/bump-oxipng
          delete-branch: true
          labels: dependencies, automated
      - name: Enable auto-merge
        if: steps.cpr.outputs.pull-request-number != ''
        run: gh pr merge "${{ steps.cpr.outputs.pull-request-number }}" --auto --squash --delete-branch
```

- [ ] **Step 3: Validate workflow YAML**

Run:

```bash
cd oxipng-pybind && uv run pre-commit run check-yaml --all-files
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml .github/workflows/upstream-bump.yml
git commit -m "ci: add oxipng-pybind workflows"
```

Run the commit commands from inside `oxipng-pybind/`.

---

### Task 7: Final Verification

**Files:**
- Modify only files required by failures from verification commands.

- [ ] **Step 1: Run full local CI**

Run:

```bash
cd oxipng-pybind && make AI=1 ci
```

Expected: PASS. If this fails, use the filtered log and the full `.ci-ai.log` to fix the specific failure.

- [ ] **Step 2: Build and inspect wheel**

Run:

```bash
cd oxipng-pybind && uv run maturin build --release
```

Expected: PASS and a wheel exists under `target/wheels/`.

Run:

```bash
cd oxipng-pybind && python -m zipfile -l target/wheels/*.whl | grep -E 'oxipng\\.(so|pyd|dylib)|oxipng\\.pyi'
```

Expected: output includes the native extension and `oxipng.pyi`.

- [ ] **Step 3: Verify clean supported import from wheel**

Run:

```bash
cd oxipng-pybind && tmpdir="$(mktemp -d)" && python -m venv "$tmpdir/venv" && "$tmpdir/venv/bin/pip" install target/wheels/*.whl pillow && "$tmpdir/venv/bin/python" - <<'PY'
from pathlib import Path
from PIL import Image
from oxipng import PngError, optimize

path = Path("wheel-smoke.png")
Image.new("RGBA", (16, 16), (255, 255, 255, 255)).save(path)
optimize(path, level=6)
with Image.open(path) as image:
    image.verify()
assert issubclass(PngError, Exception)
print("wheel smoke passed")
PY
```

Expected: prints `wheel smoke passed`.

- [ ] **Step 4: Inspect git status**

Run:

```bash
git status --short
```

Expected: only intentional tracked changes remain, or no changes remain after commits.

- [ ] **Step 5: Commit verification fixes**

If Step 1, 2, or 3 required fixes, commit them:

```bash
git add .
git commit -m "fix: pass oxipng-pybind verification"
```

Run the commit commands from inside `oxipng-pybind/`.

If no fixes were needed, do not create an empty commit.

---

## Self-Review Checklist

- Spec coverage:
  - New `oxipng-pybind/` repo folder: Tasks 1-7.
  - Distribution `oxipng-pybind`, import `oxipng`: Tasks 1-2.
  - Supported File optimization API `optimize(path, level=6)`: Task 2.
  - Explicit unsupported broader pyoxipng APIs: Task 4.
  - Make targets and repo polish: Task 3.
  - CI: Task 6.
  - Upstream bump and CI-gated auto-merge: Tasks 5-6.
  - Docs and third-party notices: Task 4.
  - Verification: Task 7.
- Placeholder scan: no TBD/TODO/fill-in-later steps.
- Type consistency:
  - Python public API is `optimize(input, output=None, *, level=2)` in tests, stub, docs, and Rust.
  - Error type is `PngError` in tests, stub, docs, and Rust.
  - Upstream Rust dependency is aliased as `oxi` in `Cargo.toml` and `src/lib.rs`.
