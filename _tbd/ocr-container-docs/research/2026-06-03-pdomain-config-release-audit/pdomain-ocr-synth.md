---
title: pdomain-ocr-synth configuration and release audit
date: 2026-06-03
repo: pdomain-ocr-synth
---

# pdomain-ocr-synth

## Summary

- Repo type / packaging: Python `src/` package using `hatchling` plus `hatch-vcs`.
- CLI script: `pdomain-ocr-synth`.
- Package version is dynamic in `pyproject.toml:5`, but runtime `__version__` is hard-coded to `0.0.1` in `src/pdomain_ocr_synth/__init__.py:3`.
- Publish model: GitHub Release assets plus `pdomain-index-pip` dispatch. No PyPI upload found.

## Config Files Inspected

- `pyproject.toml`
- `Makefile`
- `.github/workflows/ci.yml`
- `.github/workflows/dep-refresh.yml`
- `.github/workflows/release.yml`
- `scripts/do-release.sh`
- `scripts/release-common.sh`
- `scripts/update_github_actions.py`
- `docs/specs/10-publishing.md`

## Build, Test, And Lint

- `make setup` runs `uv sync --group all-dev`.
- `make test` runs `uv run pytest -n auto -v -ra`.
- `make lint` uses pre-commit ruff and markdownlint.
- `make typecheck` runs `basedpyright src/pdomain_ocr_synth`.
- `make ci` runs setup, pre-commit, format-check, typecheck, test, and build.
- `make build` runs `uv build` (`Makefile:26`, `Makefile:146`).

## CI

- PR-only CI on `main`.
- SHA-pinned `actions/checkout@de0fac... # v6.0.2` and `astral-sh/setup-uv@088076... # v8.1.0`.
- `UV_PYTHON=3.13`.
- Runs `make ci` (`.github/workflows/ci.yml:3`).

## Release And Publish

- Local `make release-{patch,minor,major}` computes next `vX.Y.Z` from git tags, runs `make ci-slow`, creates an annotated tag, pushes `main` and tag, then dispatches `release.yml` (`scripts/release-common.sh:67`).
- Release workflow builds `dist/*.whl` and `dist/*.tar.gz`, creates a GitHub Release, then repository-dispatches `pdomain/pdomain-index-pip` (`.github/workflows/release.yml:63`).
- No PyPI upload found.

## Versioning

- Build metadata source is VCS tags via `hatch-vcs`.
- Release bump source defaults to tags, not `uv version` (`scripts/release-common.sh:20`).
- Runtime `__version__` is hard-coded and can drift.
- No `CHANGELOG.md` found.

## Token And Secret Usage

- Workflow `GH_TOKEN: ${{ github.token }}` for dep-refresh PRs and releases.
- `secrets.PDOMAIN_INDEX_DISPATCH` for index dispatch (`.github/workflows/release.yml:81`).
- Runtime Hugging Face publishing resolves `--token`, then `HF_TOKEN`, then `~/.cache/huggingface/token` (`src/pdomain_ocr_synth/publish/auth.py:99`).

## Risks And Drift

- Hard-coded runtime `__version__` can diverge from tag-derived package versions.
- No changelog/release notes source besides GitHub `--generate-notes`.
- Dep-refresh auto-merge assumes label `dep-refresh`, branch protection, and `GITHUB_TOKEN` permissions allow PR creation/auto-merge.
- Action updater pins SHAs but does not update adjacent version comments.

## Recommended Updates

- Make runtime `__version__` derive from installed metadata or generated VCS version.
- Add and maintain `CHANGELOG.md`.
- Document that GitHub Releases plus `pdomain-index-pip` are the only publish targets.
- Make action-pin refresh update/check adjacent version comments.

