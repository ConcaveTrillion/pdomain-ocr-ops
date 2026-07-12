---
title: pdomain-book-tools configuration and release audit
date: 2026-06-03
repo: pdomain-book-tools
---

# pdomain-book-tools

## Summary

- Repo type / packaging: Python package, `hatchling` plus `hatch-vcs`; package name `pdomain-book-tools`; dynamic version from VCS tags; Python `>=3.11,<3.14` in `pyproject.toml:1-17`.
- Publish model: GitHub Release assets plus `pdomain-index-pip` dispatch. No PyPI publish workflow found.
- Primary version source: git tags via `hatch-vcs` (`pyproject.toml:80-86`). Local latest tag observed by reviewer: `v0.18.0`.

## Config Files Inspected

- `pyproject.toml`
- `uv.lock`
- `Makefile`
- `.github/workflows/ci.yml`
- `.github/workflows/dep-refresh.yml`
- `.github/workflows/release.yml`
- `scripts/release-common.sh`
- `scripts/do-release.sh`
- `README.md`
- `CHANGELOG.md`
- `.pre-commit-config.yaml`
- `.gitignore`
- `pdomain_book_tools/__init__.py`

## Build, Test, And Lint

- `make setup`
- `make test`
- `make lint-check`
- `make typecheck`
- `make build`
- `make ci`
- `make ci-slow`
- Main Makefile surfaces: `Makefile:67-99`, `Makefile:166-209`.
- CI runs `pre-commit` with `basedpyright` skipped (`.github/workflows/ci.yml:29-31`).

## CI

- PR-only CI on `main` (`.github/workflows/ci.yml:3-110`).
- SHA-pinned actions include `actions/checkout` v6.0.2 and `astral-sh/setup-uv` v8.1.0.
- Test matrix covers Python `3.11`, `3.12`, and `3.13`.
- CI installs `tesseract-ocr`.

## Release And Publish

- Local release targets `make release-{patch,minor,major}` call `scripts/do-release.sh`.
- Shared release script fetches tags, requires clean `main`, computes next `vX.Y.Z`, runs `make ci-slow`, creates an annotated tag, pushes `main` and the tag, then dispatches `release.yml` (`Makefile:242-318`, `scripts/release-common.sh:33-118`).
- GitHub release workflow builds wheel and sdist, then creates a GitHub Release with `dist/*.whl` and `dist/*.tar.gz` attached (`.github/workflows/release.yml:52-90`).
- No PyPI upload is configured.

## Versioning

- Source of truth is git tags through `hatch-vcs` (`pyproject.toml:80-86`).
- Runtime import uses generated `_version.py` with fallback to installed metadata or `0.0.0+unknown` (`pdomain_book_tools/__init__.py:19-35`).
- `_version.py` is ignored and not tracked (`.gitignore:12-13`).

## Token And Secret Usage

- Release uses `github.token` as `GH_TOKEN` for `gh release create` (`.github/workflows/release.yml:75-89`).
- Optional cross-repo dispatch uses `secrets.PDOMAIN_INDEX_DISPATCH` to post `pdomain-release-published` to `pdomain-index-pip` (`.github/workflows/release.yml:91-104`).
- Dep refresh uses `github.token` for action-pin refresh and PR creation (`.github/workflows/dep-refresh.yml:29-32`, `:53-71`).

## Risks And Drift

- README install examples imply `pip install pdomain-book-tools`, but no PyPI publish exists. Availability depends on GitHub Release assets and the self-hosted pip index unless the package is published elsewhere.
- `CHANGELOG.md` is stale: latest changelog release is `v0.14.1`, while local latest tag is `v0.18.0` (`CHANGELOG.md:24`).
- Release CI mutates `pyproject.toml` to relax `failOnWarnings` before `make ci-slow` (`.github/workflows/release.yml:40-50`), so release gates differ from normal PR/local gates.
- Dep-refresh is broad and template-like; it may run npm/frontend upgrade branches if matching files appear (`.github/workflows/dep-refresh.yml:25-44`).

## Recommended Updates

- Document whether GitHub Releases plus `pdomain-index-pip` or PyPI is the intended install channel.
- Update changelog through current tags or explicitly switch to GitHub-generated notes as canonical.
- Make release CI's typecheck policy match normal CI, or document why warnings are tolerated during release.
- Document `PDOMAIN_INDEX_DISPATCH` required permissions.
