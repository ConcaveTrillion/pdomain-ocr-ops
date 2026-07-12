---
title: pdomain-prep-for-pgdp configuration and release audit
date: 2026-06-03
repo: pdomain-prep-for-pgdp
---

# pdomain-prep-for-pgdp

## Summary

- Repo type / packaging: Python/FastAPI app with bundled React SPA.
- Uses `hatchling` plus `hatch-vcs`; package `pdomain-prep-for-pgdp` has dynamic VCS version (`pyproject.toml:1-7`, `:88-95`).
- Frontend package is private `pgdp-prep-frontend` version `0.0.0` (`frontend/package.json:1-6`).
- Publish model: GitHub Release wheel assets plus `pdomain-index-pip` dispatch. No PyPI upload found.

## Config Files Inspected

- `Makefile`
- `pyproject.toml`
- `frontend/package.json`
- `frontend/.npmrc`
- `.github/workflows/ci.yml`
- `.github/workflows/dep-refresh.yml`
- `.github/workflows/release.yml`
- `Dockerfile`
- `install.sh`
- `install.ps1`
- `scripts/do-release.sh`
- `scripts/release-common.sh`
- `.pre-commit-config.yaml`
- `README.md`
- `DEVELOPMENT.md`
- `CHANGELOG.md`

## Build, Test, And Lint

- Backend `make typecheck` runs `basedpyright` (`Makefile:275-276`).
- `make test` runs `pytest tests/ -v --ignore=tests/e2e -n auto` (`Makefile:289-290`).
- `make build` runs `frontend-build`, then `uv build --wheel` (`Makefile:295-302`).
- Frontend build/test/lint commands wrap pnpm (`Makefile:212-247`).
- Frontend scripts include `build`, `lint`, `format:check`, `test`, `openapi:gen`, and `knip` (`frontend/package.json:6-18`).
- `make ci` chains setup, frontend install, pre-commit, typecheck, OpenAPI export, frontend build, pytest, frontend format/lint/test/knip (`Makefile:311`).

## CI

- PR-only CI on `main` (`.github/workflows/ci.yml:3-5`).
- Single `ci` job uses Python `3.13`, Node `24`, pnpm `11.3.0`, uv `0.11.16`, and sets `CUDA_VISIBLE_DEVICES=""` (`.github/workflows/ci.yml:14-36`).
- Dep-refresh is weekly/manual, updates action pins plus Python and frontend deps, then opens an auto-merge PR (`.github/workflows/dep-refresh.yml:3-71`).

## Release And Publish

- Local `make release-{patch,minor,major}` calls shared release driver (`Makefile:421-435`).
- Release workflow is dispatch-only with tag input (`.github/workflows/release.yml:7-12`).
- Release workflow runs `make ci-slow`, builds wheel artifacts, creates GitHub Release, and dispatches `pdomain-index-pip` with repo/tag payload (`.github/workflows/release.yml:45-108`).
- No PyPI publish found.

## Versioning

- Python version derives from git tags via `hatch-vcs` (`pyproject.toml:88-89`).
- Release script computes next `vX.Y.Z` from tags and does not edit `pyproject.toml` (`scripts/release-common.sh:74-80`, `:134-158`).
- Docker cannot use `.git`, so it replaces dynamic version with `ARG VERSION`, defaulting to `0.0.0+docker` (`Dockerfile:50-70`).
- Local `make docker-build` does not pass `VERSION` (`Makefile:408-409`).

## Token And Secret Usage

- Release uses `github.token` for `gh release create` (`.github/workflows/release.yml:79-93`).
- `secrets.PDOMAIN_INDEX_DISPATCH` is used as `GH_TOKEN` for dispatch to `pdomain/pdomain-index-pip` (`.github/workflows/release.yml:95-108`).
- Dep-refresh uses `github.token` for PR creation/merge (`.github/workflows/dep-refresh.yml:29-32`, `:53-71`).
- Frontend `.npmrc` scopes `@pdomain` to `pdomain-index-npm` (`frontend/.npmrc:1-2`).
- No npm publish token or PyPI token found.

## Risks And Drift

- `DEVELOPMENT.md` still describes release CI as push/tag-based and mentions container build on tag push (`DEVELOPMENT.md:162-172`, `:221-222`), but actual release is `workflow_dispatch` only and no container workflow exists.
- `install.sh` depends on GitHub Releases latest plus attached wheel asset (`install.sh:324-360`), so failed index dispatch is survivable, but missing GitHub release asset is fatal.
- Docker image defaults to `0.0.0+docker` unless caller passes `--build-arg VERSION`; current `make docker-build` does not.
- Action updater likely misses `pnpm/action-setup` and `actions/setup-node` variants used here.

## Recommended Updates

- Update `DEVELOPMENT.md` to match dispatch-only release and no container publishing.
- Pass a real version in `make docker-build`, or document local `0.0.0+docker`.
- Add tag-push release trigger if manual tag pushes should publish.
- Expand action-pin updater coverage.
- Add release checklist for wheel asset verification and installer smoke test.
