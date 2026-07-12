---
title: pdomain-ocr-trainer-spa configuration and release audit
date: 2026-06-03
repo: pdomain-ocr-trainer-spa
---

# pdomain-ocr-trainer-spa

## Summary

- Repo type / packaging: Python FastAPI package with bundled React/Vite frontend.
- Uses `hatchling` plus `hatch-vcs`; CLI `pdomain-ocr-trainer-ui`.
- Frontend package is private with independent version `0.1.0` (`pyproject.toml:5`, `frontend/package.json:1`).
- Highest-risk finding: committed absolute local `pdomain-ops` uv source likely breaks CI/release on GitHub runners (`pyproject.toml:66`).

## Config Files Inspected

- `pyproject.toml`
- `Makefile`
- `frontend/package.json`
- `Dockerfile`
- `mise.toml`
- `.github/workflows/ci.yml`
- `.github/workflows/dep-refresh.yml`
- `.github/workflows/nightly.yml`
- `.github/workflows/release.yml`
- Release scripts
- Install scripts

## Build, Test, And Lint

- `make ci` runs setup, Python lint/typecheck/test, frontend install/typecheck/test/format-check/lint/knip.
- `make ci-full` adds frontend build, Playwright e2e, and wheel.
- `make ci-slow` aliases `ci-full`.
- `make build` builds frontend then runs `uv build --wheel` (`Makefile:187`).

## CI

- PR-only CI on `main`.
- Ubuntu 22.04.
- SHA-pinned checkout/setup-node/setup-uv.
- Node 24.
- Corepack prepares `pnpm@latest`.
- Runs `make ci` (`.github/workflows/ci.yml:13`).

## Release And Publish

- Local release driver follows the shared tag-based `vX.Y.Z` flow.
- Release workflow installs Playwright, runs `make ci-slow`, builds a wheel, creates GitHub Release, and dispatches `pdomain-index-pip` with `client_payload[repo]=pdomain-ocr-trainer-spa` (`.github/workflows/release.yml:45`).
- No PyPI or npm publish found.

## Versioning

- Package metadata is VCS-tag dynamic.
- Served app/env version imports hard-coded `_version.__version__ = "0.1.0a0"` (`src/pdomain_ocr_trainer_spa/_version.py:1`).
- No `CHANGELOG.md` found.

## Token And Secret Usage

- Workflow `github.token` for releases and dep-refresh.
- `secrets.PDOMAIN_INDEX_DISPATCH` for index dispatch.
- Runtime HF token config uses `PD_OCR_TRAINER_SPA_HF_TOKEN_PATH`, not `HF_TOKEN`, for backend HF dataset preview/publish paths (`src/pdomain_ocr_trainer_spa/settings.py:46`, `src/pdomain_ocr_trainer_spa/api/sources.py:42`).

## Risks And Drift

- Release/CI likely broken by `[tool.uv.sources] pdomain-ops = { path = "/workspaces/ocr-container/pdomain-ops", editable = true }`, an absolute local path not present on GitHub runners (`pyproject.toml:66`).
- Dockerfile repeats that path-source assumption and has stale `pdomain-ocr-ops` wording (`Dockerfile:22`).
- `uv.lock` records `pdomain-ops` as editable local.
- Docker uses `ghcr.io/astral-sh/uv:latest` and downloads nvm by curl, so container builds are not reproducible (`Dockerfile:8`).
- Nightly uses `actions/github-script` with `draft: true` for issues, which is not a normal Issues API field (`.github/workflows/nightly.yml:31`).
- Action updater does not manage `pnpm/action-setup`, `jdx/mise-action`, or `actions/github-script`.

## Recommended Updates

- Remove the absolute local `pdomain-ops` source from committed release config, or gate it to local-dev only.
- Regenerate lockfile against registry sources for CI/release.
- Wire `_version.py` to VCS/package metadata.
- Pin Docker uv image and nvm/source versions by digest/checksum, or remove Dockerfile if unused.
- Add a changelog.
- Fix nightly issue creation.
