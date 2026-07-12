---
title: pdomain-index-pip configuration and release audit
date: 2026-06-03
repo: pdomain-index-pip
---

# pdomain-index-pip

## Summary

- Repo type / packaging: Python/uv tooling repo for a static PEP 503 simple index.
- Not a distributable package; `[tool.uv] package = false`; metadata version fixed at `0.0.0` (`pyproject.toml:1-19`).
- Publish model: tooling releases are empty GitHub Releases; indexed packages are GitHub Release assets from publisher repos.

## Config Files Inspected

- `pyproject.toml`
- `uv.lock`
- `Makefile`
- `.github/workflows/ci.yml`
- `.github/workflows/dep-refresh.yml`
- `.github/workflows/regen.yml`
- `.github/workflows/release.yml`
- `scripts/regen_index.py`
- `scripts/release-common.sh`
- `scripts/do-release.sh`
- `scripts/update_github_actions.py`
- `README.md`
- `CONVENTIONS.md`

## Build, Test, And Lint

- `make setup`
- `make format`
- `make lint-check`
- `make typecheck`
- `make test`
- `make actionlint`
- `make shell-check`
- `make docs-check`
- `make static-check`
- `make ci`
- `make regen`
- `make build`
- `make smoke-regen`
- Main Makefile surface: `Makefile:26-121`.

## CI

- PR-only CI on `main` (`.github/workflows/ci.yml:3-29`).
- SHA-pinned `actions/checkout` and `astral-sh/setup-uv`.
- Runs `make static-check` and `make test`.

## Release And Publish

- Local `make release-{patch,minor,major}` runs `scripts/do-release.sh`; `RELEASE_PREFLIGHT="make ci"` (`scripts/do-release.sh:4-5`).
- Common release script creates and pushes a tag, then dispatches release workflow (`scripts/release-common.sh:25-115`).
- Release workflow creates an empty GitHub Release for the repo-code tag, then calls `regen.yml` to refresh Pages (`.github/workflows/release.yml:63-89`).
- Indexed package versions come from release asset filenames and GitHub Release assets, not this repo's package metadata (`scripts/regen_index.py:167-224`).

## Versioning

- Repo-code releases are tag-only. Local latest tag observed by reviewer: `v0.1.0`.
- `pyproject.toml` version remains `0.0.0`.
- `RELEASE_VERSION_SOURCE` defaults to `tags` (`scripts/release-common.sh:10-13`, `:59-65`).

## Token And Secret Usage

- Regen uses `secrets.GITHUB_TOKEN` as `GH_TOKEN` for public release reads (`.github/workflows/regen.yml:63-66`).
- Docs say no PAT is needed for public reads (`.github/workflows/regen.yml:17-18`, `README.md:35-47`).
- Release uses `secrets.GITHUB_TOKEN` for `gh release create` (`.github/workflows/release.yml:70-79`).
- External publisher repos need a fine-grained PAT to dispatch `pdomain-release-published` (`README.md:46`).

## Risks And Drift

- No changelog or release notes file exists; release notes are GitHub-generated only.
- `README.md` still says "Once GitHub Pages is enabled" (`README.md:7-13`), while workflows assume Pages deployment is active.
- Regen repo allowlist is hard-coded (`scripts/regen_index.py:32-42`), so new Python publishers require a code change.
- Release workflow produces no wheel/sdist by design, but the GitHub Release can be confused with package publication.

## Recommended Updates

- Clarify that Pages is expected to be enabled now, or separate setup instructions from normal operations.
- Document required dispatch PAT permissions.
- Add a changelog or explicitly declare GitHub Release notes canonical.
- Tie `REPOS` allowlist maintenance to new package release checklists.
