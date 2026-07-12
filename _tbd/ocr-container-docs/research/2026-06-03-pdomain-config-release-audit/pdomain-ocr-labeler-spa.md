---
title: pdomain-ocr-labeler-spa configuration and release audit
date: 2026-06-03
repo: pdomain-ocr-labeler-spa
---

# pdomain-ocr-labeler-spa

## Summary

- Repo type / packaging: Python FastAPI app plus bundled React/Vite SPA.
- Wheel-only release path.
- Python package uses dynamic versioning via `hatch-vcs` (`pyproject.toml:1-7`, `:83-90`).
- Frontend package is private and separately versioned `0.0.0` (`frontend/package.json:1-5`).

## Config Files Inspected

- `Makefile`
- `pyproject.toml`
- `frontend/package.json`
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- `.github/workflows/dep-refresh.yml`
- `scripts/do-release.sh`
- `scripts/release-common.sh`
- `scripts/update-pdomain-deps.sh`
- `docs/runbooks/release.md`
- `CHANGELOG.md`
- `Dockerfile`
- `mise.toml`

## Build, Test, And Lint

- Frontend build copies `frontend/dist` into the package static directory (`Makefile:239-246`).
- Lint runs ruff, basedpyright, eslint, and tsc (`Makefile:296-310`).
- Tests include backend, integration, e2e, and behavior coverage (`Makefile:321-337`).
- Release build is `uv build --wheel` only (`Makefile:396-402`).
- `ci-slow` is `ci build` (`Makefile:432-434`).

## CI

- PR-only CI on `main`.
- Split jobs: lint, backend test, frontend test, e2e, wheel build, and OpenAPI drift.
- Actions are SHA-pinned; Node 24, pnpm 11, uv `0.11.16` (`.github/workflows/ci.yml:21-180`).
- E2E is non-blocking with `continue-on-error: true` (`.github/workflows/ci.yml:103-107`).
- Weekly dep-refresh mirrors the shared pdomain pattern (`.github/workflows/dep-refresh.yml:29-71`).

## Release And Publish

- Release targets push an annotated tag and dispatch `release.yml` (`Makefile:501-511`, `scripts/release-common.sh:33-117`).
- Release workflow runs `release-ci` with `make ci-slow`, then `publish` builds with `make build`, creates a GitHub Release, and dispatches `pdomain-index-pip` with repo/tag payload (`.github/workflows/release.yml:22-108`).
- No PyPI upload found.

## Versioning

- Python version comes from git tags via `hatch-vcs`.
- Next `vN.N.N` is computed from stable tags in `scripts/release-common.sh:127-152`.
- `make refresh-version` reinstalls editable package (`Makefile:47-56`).
- Docker builds bypass VCS by replacing `dynamic = ["version"]` with `ARG VERSION`, defaulting to `0.0.0+docker` (`Dockerfile:49-73`).

## Token And Secret Usage

- `GH_TOKEN=${{ github.token }}` for release creation (`.github/workflows/release.yml:79-93`).
- `secrets.PDOMAIN_INDEX_DISPATCH` for index dispatch (`.github/workflows/release.yml:95-108`).
- Dep-refresh uses `github.token` (`.github/workflows/dep-refresh.yml:31-32`, `:70-71`).
- Release runbook requires local `gh` write auth (`docs/runbooks/release.md:10-15`).

## Risks And Drift

- Release docs say publish attaches `dist/*.whl` and `dist/*.tar.gz` (`docs/runbooks/release.md:118-121`), but `make build` is wheel-only (`Makefile:396-402`).
- Release runbook line refs are stale relative to the current Makefile.
- Changelog dependency notes lag current metadata: changelog says `pdomain-ops>=0.7.0`, while `pyproject.toml` says `>=0.7.1` (`CHANGELOG.md:25-29`, `pyproject.toml:34-38`).
- Docker comments say CI passes a real tag via `--build-arg VERSION`, but local `docker-build` does not pass it, so Docker defaults to `0.0.0+docker` (`Dockerfile:49-53`, `Makefile:476-477`).

## Recommended Updates

- Fix release runbook artifact claims and line refs.
- Align changelog dependency floors with `pyproject.toml`.
- Decide whether Docker image version should be wired through `DOCKER_TAG` or git tag.
- Make E2E blocking once flakiness is resolved.
