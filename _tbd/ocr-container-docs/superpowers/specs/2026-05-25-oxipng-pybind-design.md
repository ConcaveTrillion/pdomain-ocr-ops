# oxipng-pybind Design

Date: 2026-05-25

## Summary

Create a new sibling repo folder, `oxipng-pybind/`, containing a focused Python
wrapper around the upstream Rust `oxipng` library. The package is intended to
cover file-based optimization need first, not to be a full replacement
for `pyoxipng`.

The published distribution name is `oxipng-pybind`, but the import module is
`oxipng` so file-based callers can continue to use:

```python
from oxipng import optimize

optimize(path, level=6)
```

The repo should otherwise have full sibling-repo polish: Make targets,
documentation, CI, dependency/license checks, and an automated upstream bump
workflow.

## Goals

- Build a Python extension wrapper around `https://github.com/oxipng/oxipng`
  using Rust, PyO3, and maturin.
- Support the file optimization API surface used today:
  `from oxipng import optimize` and `optimize(path, level=6)`.
- Expose a narrow, explicit public API:
  `optimize(input, output=None, *, level=2)` and `PngError`.
- Track upstream `oxipng` releases automatically.
- Allow automated merge of upstream bump PRs only after CI passes the supported
  API-surface tests.
- Match the development ergonomics and repository conventions of sibling
  `pd-*` repos where applicable.

## Non-Goals

- No full `pyoxipng` compatibility in the initial implementation.
- No `optimize_from_memory`.
- No `RawImage`.
- No row-filter, interlace, strip, or deflater option classes.
- No standalone CLI.
- No sibling `pd-*` local-dev or `update-pd-deps` targets, because this package
  has no sibling `pd-*` dependencies.

## Public API

The extension module is imported as `oxipng`.

```python
from oxipng import PngError, optimize

optimize(input, output=None, *, level=2)
```

`input` accepts `str`, `bytes`, or `os.PathLike`.

`output` accepts `str`, `bytes`, `os.PathLike`, or `None`. When `output` is
`None`, optimization happens in place, matching the existing `pyoxipng`
behavior file-based callers rely on.

`level` must be an integer from `0` through `6`, passed to
`oxipng::Options::from_preset`.

Unsupported keyword arguments raise `TypeError`. Invalid levels raise
`ValueError`. PNG optimization failures raised by the Rust library are mapped
to `PngError`.

## Architecture

`oxipng-pybind/` is a standalone Rust/Python project.

Expected layout:

```text
oxipng-pybind/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── upstream-bump.yml
├── docs/
│   ├── README.md
│   ├── process/
│   │   └── upstream-bumps.md
│   └── usage/
│       └── file-optimization.md
├── src/
│   └── lib.rs
├── tests/
├── Cargo.toml
├── Cargo.lock
├── Makefile
├── README.md
├── THIRD_PARTY_NOTICES.md
├── pyproject.toml
└── uv.lock
```

The Rust extension crate exposes a Python module named `oxipng`. To avoid name
confusion with the Rust dependency, the implementation should alias the
dependency internally:

```rust
use ::oxipng as oxi;
```

The Rust dependency should follow upstream library-use guidance by disabling
the binary feature:

```toml
oxipng = { version = "...", default-features = false, features = ["parallel", "zopfli"] }
```

If upstream feature names change, the bump workflow and CI should surface that
as a failed bump PR rather than merging an unverified update.

## Packaging

Use `maturin` as the build backend, following `pd-png-optimizer`'s wrapper
pattern but without a custom Rust core or Python facade package.

The package identity is:

- Distribution: `oxipng-pybind`
- Import module: `oxipng`
- Initial versioning policy: mirror upstream `oxipng` where practical, so
  `oxipng-pybind 10.1.1` wraps `oxipng 10.1.1`.

If exact version mirroring causes packaging friction, the implementation plan
may switch to independent wrapper versioning only if it also records the
wrapped upstream version in code, docs, and bump automation.

## Make Targets

The repo should provide the standard local development targets that apply to a
small Rust/Python wrapper:

- `make setup`: sync dependencies, build editable maturin extension, install
  hooks.
- `make develop`: run `maturin develop`.
- `make test`: run Rust tests and pytest.
- `make lint`: run cargo clippy, ruff, and markdown lint where configured.
- `make lint-fix`: apply automatic lint fixes where safe.
- `make format`: run cargo fmt and ruff format, then re-check.
- `make format-check`: check formatting without writes.
- `make typecheck`: run basedpyright over Python stubs and tests.
- `make rust-deny`: run cargo-deny.
- `make build` / `make wheel`: build release wheel artifacts.
- `make clean`, `make reset`, and `make upgrade-deps`.
- `make ci`: run the full local CI sequence.

The Makefile should include the sibling `AI=1` log-filter wrapper if the local
repo pattern still uses it when implementation starts.

## CI

`.github/workflows/ci.yml` runs on pushes to `main` and pull requests targeting
`main`.

The CI job runs `make ci` and must cover:

- Rust compilation and tests.
- Python import tests.
- Supported API behavior.
- Linting and formatting checks.
- Type checking.
- Cargo dependency/license/advisory checks.
- Wheel build.

CI should pin or constrain tool versions only where the sibling repos already
do so for reproducibility.

## Upstream Bump Automation

`.github/workflows/upstream-bump.yml` runs on a schedule and by manual
dispatch.

The workflow checks the latest upstream `oxipng` version, updates:

- `Cargo.toml`
- `Cargo.lock`
- `pyproject.toml` package version when version mirroring is active
- any explicit upstream version marker in docs or code

It then opens a pull request.

Auto-merge is allowed for PRs created by this workflow after all required CI
checks pass. The workflow should not push directly to `main`.

Repository branch protection and GitHub auto-merge settings may need to be
enabled outside the repo. The workflow should document those requirements in
`docs/process/upstream-bumps.md`.

## Tests

Tests must make the supported API contract explicit.

Required pytest coverage:

- `from oxipng import optimize`
- `from oxipng import PngError`
- Optimize a generated fixture PNG in place with `level=6`.
- Optimize a generated fixture PNG to a separate output path.
- Verify optimized output is still a readable PNG, preferably with Pillow.
- Invalid `level` values raise `ValueError`.
- Unsupported kwargs raise `TypeError`.
- Corrupt or non-PNG input raises `PngError`.

Rust-side tests should cover any option/path translation that can be tested
without relying solely on Python integration tests.

The tests are the auto-merge gate. If upstream changes break the supported
surface, the bump PR must remain unmerged until the wrapper is fixed.

## Documentation

`README.md` should include:

- What the package is and why it exists.
- The file optimization compatibility goal.
- Installation instructions.
- Supported API examples.
- Explicit unsupported `pyoxipng` APIs.
- Development commands.
- Upstream tracking policy.

`docs/usage/file-optimization.md` should show the exact file optimization use case:

```python
from oxipng import optimize

optimize(path, level=6)
```

`docs/process/upstream-bumps.md` should explain the scheduled bump workflow,
the CI/auto-merge gate, and the required GitHub repository settings.

`THIRD_PARTY_NOTICES.md` should attribute upstream `oxipng` and any relevant
transitive license notices required by the selected dependency tooling.

## Risks

Maturin module naming needs care because the Python extension module and Rust
dependency are both named `oxipng`. The implementation should alias the Rust
dependency as `oxi`.

Upstream `oxipng` library API changes may require wrapper code changes during a
bump. CI must treat that as a failed automated PR, not as a reason to weaken
tests.

GitHub auto-merge cannot be guaranteed by workflow code alone. Branch
protection and auto-merge settings must permit workflow-created PRs to merge
after required checks pass.

## Acceptance Criteria

- `oxipng-pybind/` exists as a standalone repo folder.
- `make ci` passes locally.
- GitHub CI runs `make ci`.
- The package can be imported as `oxipng`.
- file optimization usage works: `optimize(path, level=6)`.
- Unsupported public APIs are documented as unsupported.
- Upstream bump workflow opens PRs and is configured for CI-gated auto-merge.
- The repo contains README, docs, tests, Makefile, and third-party notices at
  sibling-repo quality.
