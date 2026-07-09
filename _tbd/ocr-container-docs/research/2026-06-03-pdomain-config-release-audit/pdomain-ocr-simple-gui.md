---
title: pdomain-ocr-simple-gui configuration and release audit
date: 2026-06-03
repo: pdomain-ocr-simple-gui
---

# pdomain-ocr-simple-gui

## Summary

- Repo type / packaging: Python FastAPI plus React/Vite GUI.
- Uses `hatchling` plus `hatch-vcs`; console script `pdomain-ocr-simple-gui` (`pyproject.toml:1-7`, `:28-29`).
- Frontend is a private package versioned `0.1.0` (`frontend/package.json:1-5`).
- Publish model: GitHub Release wheel/sdist assets plus `pdomain-index-pip` dispatch. No PyPI upload found.

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
- `CHANGELOG.md`
- `README.md`
- No Dockerfile or release runbook found.

## Build, Test, And Lint

- Build: `frontend-build` then `uv build` (`Makefile:189-190`).
- `make ci` includes setup, pre-commit, lint/typecheck, frontend build/test/lint/format/knip, behavior coverage, smoke, and `e2e-fast` (`Makefile:192-194`).
- Frontend scripts are Vite, Vitest, ESLint, Prettier, and Knip (`frontend/package.json:6-17`).

## CI

- PR-only CI on `main`.
- Single Ubuntu job.
- Python 3.11, Node 24, pnpm 11, uv `0.11.16`.
- Installs Playwright Chromium, then runs `make ci` (`.github/workflows/ci.yml:3-33`).
- Weekly dep-refresh opens/auto-merges PRs using `github.token` (`.github/workflows/dep-refresh.yml:29-71`).

## Release And Publish

- Release targets call `scripts/do-release.sh`.
- Shared script requires clean/synced `main`, computes next `vN.N.N`, runs `make ci-slow`, tags, pushes, and dispatches release workflow (`Makefile:260-274`, `scripts/release-common.sh:14-152`).
- Release workflow is publish-only by design: builds artifacts, creates GitHub Release, then dispatches `pdomain-index-pip` (`.github/workflows/release.yml:22-86`).

## Versioning

- Python package version is tag-derived via `hatch-vcs` (`pyproject.toml:64-65`).
- Release script computes the next stable tag (`scripts/release-common.sh:127-152`).
- Frontend package has independent private version `0.1.0`; it is not the release source of truth.

## Token And Secret Usage

- `GH_TOKEN=${{ github.token }}` for GitHub Release creation (`.github/workflows/release.yml:57-71`).
- `secrets.PDOMAIN_INDEX_DISPATCH` for index dispatch (`.github/workflows/release.yml:73-86`).
- Dep-refresh uses `github.token` (`.github/workflows/dep-refresh.yml:31-32`, `:70-71`).
- Local release requires authenticated `gh`.

## Risks And Drift

- No release runbook, unlike `pdomain-ocr-labeler-spa`.
- `CHANGELOG.md` is stale: it says version was confirmed as `0.1.0a0` in `pyproject.toml`, but `pyproject.toml` is now dynamic (`CHANGELOG.md:91-99`, `pyproject.toml:5-8`).
- `CHANGELOG.md` says publish was blocked pending index workflow, but `release.yml` now publishes and dispatches (`CHANGELOG.md:99-106`, `.github/workflows/release.yml:57-86`).
- Release workflow skips GitHub-side tests and relies on local preflight only (`.github/workflows/release.yml:22-25`).

## Recommended Updates

- Add a release runbook.
- Update changelog/release-prep notes for tag-based dynamic versioning and active index dispatch.
- Add a lightweight release CI job before publish, or document the local-only verification policy prominently.

