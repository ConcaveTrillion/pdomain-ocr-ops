---
title: pdomain-ocr-cli configuration and release audit
date: 2026-06-03
repo: pdomain-ocr-cli
---

# pdomain-ocr-cli

## Summary

- Repo type / packaging: Python CLI wheel using `hatchling` plus `hatch-vcs`.
- Console script: `pdomain-ocr` (`pyproject.toml:1-7`, `:32-33`).
- Version source: git tags; no static version field (`pyproject.toml:64-65`).
- Publish model: GitHub Release assets plus `pdomain-index-pip` dispatch; no PyPI upload found.

## Config Files Inspected

- `Makefile`
- `pyproject.toml`
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- `.github/workflows/dep-refresh.yml`
- `scripts/do-release.sh`
- `scripts/release-common.sh`
- `scripts/update-pdomain-deps.sh`
- `DEVELOPMENT.md`
- `README.md`
- No Dockerfile or changelog found.

## Build, Test, And Lint

- `make setup`
- `make format-check`
- `make typecheck`
- `make coverage`
- `make installer-test`
- `make build`
- `make wheel-smoke`
- Main CI target surface: `Makefile:188-198`.
- Slow release gate: `make ci-slow` (`Makefile:200-207`).
- Build: `uv build` (`Makefile:151-153`).

## CI

- PR-only CI on `main`.
- Python matrix: `3.11`, `3.12`, `3.13`.
- SHA-pinned `actions/checkout@de0fac...`, `astral-sh/setup-uv@0880...`, uv `0.11.16`.
- CI checks out `pdomain/pdomain-ops` at `2d01f1...` and symlinks `../pdomain-ops` (`.github/workflows/ci.yml:3-39`).
- Weekly dep-refresh updates action SHAs, uv, Python deps, and opens/auto-merges a PR with `github.token` (`.github/workflows/dep-refresh.yml:29-71`).

## Release And Publish

- `make release-{patch,minor,major}` delegates to `scripts/do-release.sh` (`Makefile:222-237`).
- Shared script fetches tags, requires clean/synced `main`, runs `make ci-slow`, creates annotated `vN.N.N`, pushes branch and tag, then dispatches `release.yml -f tag=...` (`scripts/release-common.sh:33-117`).
- Release workflow has `release-ci` and `publish`; publish creates GitHub Release assets from `dist/*.whl dist/*.tar.gz` and dispatches `pdomain-index-pip` (`.github/workflows/release.yml:22-110`).

## Versioning

- Authoritative version is latest git tag via `hatch-vcs`.
- Bump script computes next `vN.N.N` from existing stable tags (`scripts/release-common.sh:127-152`).
- `make refresh-version` reinstalls editable package so `hatch-vcs` re-derives version (`Makefile:44-48`).

## Token And Secret Usage

- `GH_TOKEN=${{ github.token }}` for release creation (`.github/workflows/release.yml:81-95`).
- `secrets.PDOMAIN_INDEX_DISPATCH` for repository dispatch to `pdomain-index-pip` (`.github/workflows/release.yml:97-110`).
- Dep-refresh uses `GH_TOKEN=${{ github.token }}` (`.github/workflows/dep-refresh.yml:31-32`, `:70-71`).
- Local release requires authenticated `gh`.

## Risks And Drift

- `DEVELOPMENT.md` says `pdomain-ops` is not published/path-sourced and release is blocked (`DEVELOPMENT.md:142-158`), but `pyproject.toml` now points `pdomain-ops` at `pdomain-index-pip` (`pyproject.toml:60-62`).
- `DEVELOPMENT.md` says release targets only create a local tag and require manual push (`DEVELOPMENT.md:167-174`), but the script pushes and dispatches automatically (`scripts/release-common.sh:111-117`).
- `scripts/update-pdomain-deps.sh` only refreshes `pdomain-book-tools`, not `pdomain-ops`, although both are runtime deps (`scripts/update-pdomain-deps.sh:15-18`, `pyproject.toml:16-18`).
- No changelog or release notes file exists.

## Recommended Updates

- Update `DEVELOPMENT.md` release and dependency sections.
- Add `pdomain-ops` to `scripts/update-pdomain-deps.sh`.
- Add a minimal changelog or release-notes convention.
- Consider removing the unused `pdomain-ops` checkout from release workflow if index resolution is now authoritative.

