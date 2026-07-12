---
title: pdomain-ui configuration and release audit
date: 2026-06-03
repo: pdomain-ui
---

# pdomain-ui

## Summary

- Repo type / packaging: single-package TS/React/Vite component library `@pdomain/pdomain-ui`.
- Package version is `0.5.0` in `package.json` (`package.json:1-4`).
- Publishes by GitHub Release tarball plus dispatch to self-hosted `pdomain-index-npm`.
- `publishConfig.registry` points at `https://pdomain.github.io/pdomain-index-npm/` (`package.json:16-18`).

## Config Files Inspected

- `Makefile`
- `package.json`
- `pnpm-workspace.yaml`
- `.npmrc`
- `mise.toml`
- `codegen.versions.json`
- `.github/workflows/ci.yml`
- `.github/workflows/dep-refresh.yml`
- `.github/workflows/release.yml`
- `scripts/do-release.sh`
- `scripts/update-pdomain-deps.sh`
- `scripts/update_github_actions.py`
- `CHANGELOG.md`
- `README.md`

## Build, Test, And Lint

- `make install` runs `pnpm install --frozen-lockfile` (`Makefile:82-85`).
- `make lint-check` runs format-check plus lint (`Makefile:87-90`).
- `make typecheck`, `make test`, `make build`, `make codegen-check`, and `make theme-check` wrap package scripts (`Makefile:92-114`).
- `make ci` runs install, static-check, unit tests, build, package tests, codegen-check, and theme-check (`Makefile:188-190`).
- Package scripts include `lint`, `typecheck`, `test`, `test:unit`, `test:package`, `build`, `format:check`, `codegen`, `codegen:check`, `codegen:theme-check`, and Storybook (`package.json:181-196`).

## CI

- CI runs on push and PR to `main` (`.github/workflows/ci.yml:21-25`).
- Concurrency cancels stale runs (`.github/workflows/ci.yml:27-29`).
- Jobs: `lint-check`, `typecheck`, sharded `unit-test`, and `build-package` with `pnpm pack` artifact upload (`.github/workflows/ci.yml:40-150`).
- CI intentionally excludes `codegen-check` and `theme-check` because they need self-hosted pip registry/workspace docs (`.github/workflows/ci.yml:14-18`).
- Actions are SHA-pinned, but CI checkout is v4.3.1 while release checkout is v6.0.2 (`.github/workflows/ci.yml:45`, `.github/workflows/release.yml:44`).

## Release And Publish

- `make release-{patch,minor,major}` runs `scripts/do-release.sh` (`Makefile:149-164`).
- Script enforces clean/up-to-date `main`, computes next tag from `v*`, runs local `make ci`, bumps `package.json` using `pnpm version --no-git-tag-version`, commits `package.json`/`pnpm-lock.yaml`, tags, and pushes `main --follow-tags` (`scripts/do-release.sh:36-144`).
- Release workflow triggers on `v*` tag push (`.github/workflows/release.yml:23-25`).
- Release workflow builds/tests/audits/packs tarball with read-only credentials, attests provenance, creates GitHub Release, and dispatches `pdomain-index-npm` (`.github/workflows/release.yml:38-154`).

## Versioning

- npm package version in `package.json` is the package source of truth (`package.json:2-3`).
- Release script derives next version from latest `v*` tag, then writes `package.json` (`scripts/do-release.sh:70-119`).
- Codegen input versions are separate in `codegen.versions.json`: `pdomain-book-tools` `0.14.2`, `pdomain-ops` `0.3.0` (`codegen.versions.json:1-10`), updated by `scripts/update-pdomain-deps.sh`.

## Token And Secret Usage

- No `NPM_TOKEN` or `NODE_AUTH_TOKEN` found; registry publish is via release tarball indexing.
- Release uses `softprops/action-gh-release` under `contents: write` (`.github/workflows/release.yml:125-130`).
- `secrets.PDOMAIN_INDEX_DISPATCH` is used as `GH_TOKEN` for repository dispatch to `pdomain/pdomain-index-npm` (`.github/workflows/release.yml:136-154`).
- `.npmrc` sets scoped registry only (`.npmrc:1-3`).
- Release build uses `persist-credentials:false` to avoid exposing write token to install/build (`.github/workflows/release.yml:183-207`).

## Risks And Drift

- Release workflow does not run `make ci`; it omits `codegen-check` and `theme-check`, relying on local preflight before tag push (`.github/workflows/release.yml:162-166`, `scripts/do-release.sh:102-119`).
- Manual tag pushes can bypass local-only gates.
- `package.json` version can drift from latest tag because release script computes from tags, not the existing package version, and release workflow does not assert tag/package match.
- `scripts/update-pdomain-deps.sh` uses network `curl` to `pdomain-index-pip` and stages generated files, but CI intentionally cannot verify it.
- `Makefile` downloads mise via floating `https://mise.run | sh` (`Makefile:192-198`), unlike the pinned installer pattern in prep.

## Recommended Updates

- Add release-workflow assertion that `package.json` version equals tag.
- Either run `make ci` in release or duplicate `codegen-check`/`theme-check` in a release-safe way.
- Protect releases from manual tag bypass or document that only `make release-*` is valid.
- Pin the mise installer like `pdomain-prep-for-pgdp`.
- Expand action-pin updater to include release-only actions and `pnpm/action-setup`.
