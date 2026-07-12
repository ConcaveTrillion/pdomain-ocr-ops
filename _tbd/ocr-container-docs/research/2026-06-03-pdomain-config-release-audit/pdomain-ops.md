---
title: pdomain-ops configuration and release audit
date: 2026-06-03
repo: pdomain-ops
---

# pdomain-ops

## Summary

- Repo type / packaging: Python library package `pdomain-ops`.
- Uses `hatchling` plus `hatch-vcs`; dynamic VCS tag version (`pyproject.toml:1-7`, `:38-42`).
- Publishes release artifacts to GitHub Releases, then notifies self-hosted `pdomain-index-pip`.
- No PyPI publish configured.

## Config Files Inspected

- `Makefile`
- `pyproject.toml`
- `.github/workflows/ci.yml`
- `.github/workflows/dep-refresh.yml`
- `.github/workflows/release.yml`
- `scripts/do-release.sh`
- `scripts/release-common.sh`
- `scripts/update_github_actions.py`
- `scripts/update-pdomain-deps.sh`
- `scripts/local-upgrade-deps.sh`
- `.pre-commit-config.yaml`
- `CHANGELOG.md`
- `README.md`

## Build, Test, And Lint

- `make setup` runs `uv sync --group dev` and pre-commit install (`Makefile:41-43`).
- `make lint-check` runs `ruff format --check` plus `ruff check` (`Makefile:72-74`).
- `make typecheck` runs `basedpyright pdomain_ops --level error` (`Makefile:81-82`).
- `make test` runs `pytest -n auto` (`Makefile:84-85`).
- `make build` runs `uv build` (`Makefile:100-101`).
- `make ci` chains setup, pre-commit, lint, typecheck, and test (`Makefile:90-96`).

## CI

- PR-only CI on `main` (`.github/workflows/ci.yml:3-5`).
- Separate jobs for pre-commit, lint, typecheck, test, and build.
- Test matrix covers Python `3.11`, `3.12`, and `3.13` (`.github/workflows/ci.yml:68-88`).
- Actions are SHA-pinned: checkout v6.0.2, setup-uv v8.1.0, actions/cache v5.0.5 (`.github/workflows/ci.yml:18-25` and similar).

## Release And Publish

- Local `make release-{patch,minor,major}` calls `scripts/do-release.sh` (`Makefile:145-159`).
- Shared release script requires clean/up-to-date `main`, computes next `vX.Y.Z` from tags, runs `make ci-slow`, creates an annotated tag, pushes branch/tag, then triggers `gh workflow run release.yml -f tag=...` (`scripts/release-common.sh:40-124`).
- Release workflow is `workflow_dispatch` only (`.github/workflows/release.yml:7-12`).
- Release workflow checks out the input tag, runs `make ci-slow`, builds `dist/*.whl dist/*.tar.gz`, creates GitHub Release, then dispatches `pdomain-index-pip` (`.github/workflows/release.yml:73-102`).

## Versioning

- Source of truth is git tags via `hatch-vcs` (`pyproject.toml:38-39`).
- No static version file.
- Release script computes next stable tag from existing `v[0-9]*` tags (`scripts/release-common.sh:134-158`).
- Changelog is manual and has `[Unreleased]` plus historical releases.

## Token And Secret Usage

- `github.token` is used for `gh release create` (`.github/workflows/release.yml:73-87`).
- `PDOMAIN_INDEX_DISPATCH` secret is used as `GH_TOKEN` for repository dispatch to `pdomain/pdomain-index-pip` (`.github/workflows/release.yml:89-102`).
- Dep-refresh uses `github.token` for action-pin refresh and PR creation/auto-merge (`.github/workflows/dep-refresh.yml:29-32`, `:53-71`).
- No `NPM_TOKEN`, `NODE_AUTH_TOKEN`, `PYPI`, or `TWINE` references found in root config.

## Risks And Drift

- CI does not run on push to `main`, only PRs (`.github/workflows/ci.yml:3-5`).
- Tag pushes alone do not publish; release depends on local script triggering workflow dispatch.
- `scripts/update_github_actions.py` manages a limited action list and does not include `actions/cache`, though CI uses it.
- `make upgrade-deps` runs `uv lock --upgrade` and `uv sync --group dev` without the local-dev guard that `pdomain-prep-for-pgdp` has (`Makefile:115-120`), so editable sibling installs can be overwritten.
- Legacy `dev-local` writes `.pdomain-dev-local` (`Makefile:103-110`), while newer local scripts appear to use `.pdomain-local-mode`, creating marker drift risk.

## Recommended Updates

- Add push-to-main CI or document PR-only gating.
- Make release workflow also trigger on protected tag push, or clearly enforce local release path.
- Extend action-pin updater to include all actions used.
- Align local-dev marker names and guard `upgrade-deps`.
- Add a release checklist requiring changelog update before tagging.
