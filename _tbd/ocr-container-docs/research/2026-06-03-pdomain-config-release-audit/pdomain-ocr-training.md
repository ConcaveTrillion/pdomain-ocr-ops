---
title: pdomain-ocr-training configuration and release audit
date: 2026-06-03
repo: pdomain-ocr-training
---

# pdomain-ocr-training

## Summary

- Repo type / packaging: Python package, flat `pdomain_ocr_training/`, using `hatchling` plus `hatch-vcs`.
- CLI scripts: `pdomain-ocr-training-detect` and `pdomain-ocr-training-recog`.
- Optional `[train]` extra owns the torch/DocTR stack (`pyproject.toml:5`, `:25`).
- Package version is dynamic, but runtime `__version__` is hard-coded.

## Config Files Inspected

- `pyproject.toml`
- `Makefile`
- `.github/workflows/ci.yml`
- `.github/workflows/dep-refresh.yml`
- `.github/workflows/release.yml`
- Release scripts
- `CHANGELOG.md`

## Build, Test, And Lint

- `make setup` runs `uv sync --group dev`.
- `make lint-check` runs `ruff format --check .` plus `ruff check .`.
- `make typecheck` runs `basedpyright pdomain_ocr_training`.
- `make test` runs `pytest -n auto`.
- `make ci` runs setup, pre-commit, lint-check, format-check, typecheck, and test.
- `make ci-slow` adds `uv build` (`Makefile:55`).

## CI

- PR-only CI on `main`.
- Python matrix: `3.11`, `3.12`, and `3.13`.
- SHA-pinned checkout, setup-uv, and actions/cache.
- Runs `make ci` (`.github/workflows/ci.yml:14`).

## Release And Publish

- Local tag-based release driver.
- Release workflow uses `workflow_dispatch` with `tag`.
- Release CI runs on Python 3.12.
- Publishes wheel/sdist to GitHub Release and dispatches `pdomain-index-pip` (`.github/workflows/release.yml:17`).
- No PyPI upload found.

## Versioning

- Package version is VCS-tag dynamic.
- Runtime `pdomain_ocr_training.__version__` is hard-coded to `0.2.1`; tests assert that exact value (`pdomain_ocr_training/__init__.py:51`).
- Changelog latest released entry is `0.2.1` (`CHANGELOG.md:5`).

## Token And Secret Usage

- `GH_TOKEN: ${{ github.token }}` for release creation and dep-refresh PRs.
- `secrets.PDOMAIN_INDEX_DISPATCH` for index dispatch (`.github/workflows/release.yml:65`).
- Training code references optional Slack tqdm env vars `TQDM_SLACK_TOKEN` and `TQDM_SLACK_CHANNEL`; no workflow secret wiring found.

## Risks And Drift

- Hard-coded runtime version can drift from VCS tag/package version.
- Release workflow tests only Python 3.12, while CI matrix covers 3.11-3.13.
- `actions/cache` is used but not included in `MANAGED_ACTIONS`, so dep-refresh will not update that pinned SHA (`scripts/update_github_actions.py:18`).
- Dep-refresh scripts use networked `curl` to pdomain indexes and assume auto-merge permissions.
- Release notes depend on GitHub-generated notes plus manually maintained changelog, with no enforcement.

## Recommended Updates

- Derive `__version__` from installed metadata or generated VCS file, then adjust tests.
- Add a release checklist enforcing changelog updates.
- Include `actions/cache` in action-pin refresh.
- Decide whether release CI should run the full supported Python matrix or explicitly document Python 3.12 as the release gate.
