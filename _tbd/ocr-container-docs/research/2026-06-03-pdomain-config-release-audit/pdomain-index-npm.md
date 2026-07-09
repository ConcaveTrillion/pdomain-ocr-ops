---
title: pdomain-index-npm configuration and release audit
date: 2026-06-03
repo: pdomain-index-npm
---

# pdomain-index-npm

## Summary

- Repo type / packaging: private Node/TypeScript tooling repo for a static npm registry.
- `package.json` is `private: true`, version fixed at `0.0.0`, Node `>=20` (`package.json:1-15`).
- Publish model: the repo releases its tooling as tag-only GitHub Releases, while indexed npm packages are release tarballs from publisher repos.

## Config Files Inspected

- `package.json`
- `package-lock.json`
- `Makefile`
- `tsconfig.json`
- `eslint.config.js`
- `.github/workflows/ci.yml`
- `.github/workflows/dep-refresh.yml`
- `.github/workflows/regen.yml`
- `.github/workflows/release.yml`
- `scripts/regen-index.ts`
- `scripts/registry-layout.ts`
- `scripts/actionlint.ts`
- `scripts/release-common.sh`
- `scripts/do-release.sh`
- `README.md`
- `docs/REGISTRY_FORMAT.md`

## Build, Test, And Lint

- npm scripts include `build`, `typecheck`, `lint`, `format:check`, `actionlint`, `shell:check`, `static-check`, `ci`, `regen-index`, `smoke`, and `test` (`package.json:16-28`).
- Make aliases cover the same commands (`Makefile:12-48`) plus regen and smoke (`Makefile:67-74`).

## CI

- PR-only CI on `main` (`.github/workflows/ci.yml:3-38`).
- Node 24.
- SHA-pinned `actions/checkout` v6.0.2 and `actions/setup-node` v6.4.0.
- Jobs run `make static-check` and `make test`.

## Release And Publish

- `make release-{patch,minor,major}` creates tags from git tag history, not `package.json` (`Makefile:50-65`, `scripts/release-common.sh:33-118`).
- Release workflow creates an empty GitHub Release for the tooling tag, then calls `regen.yml` to deploy Pages (`.github/workflows/release.yml:64-90`).
- Indexed npm package versions are taken from publisher tarball `package.json` fields (`scripts/regen-index.ts:387-413`).
- Static registry dist-tags are computed from semver (`scripts/regen-index.ts:416-466`).

## Versioning

- Repo-code releases are tag-only. Local latest tag observed by reviewer: `v0.1.0`.
- `package.json` version remains `0.0.0` and is not bumped.
- Publisher package versions are independent from this repo's tooling version.

## Token And Secret Usage

- Regen uses `secrets.GITHUB_TOKEN` / `GITHUB_TOKEN` for GitHub API release scans (`.github/workflows/regen.yml:42-45`, `scripts/regen-index.ts:582`).
- Release uses `secrets.GITHUB_TOKEN` for `gh release create` (`.github/workflows/release.yml:71-80`).
- Dep-refresh uses `github.token` (`.github/workflows/dep-refresh.yml:29-32`, `:53-71`).
- Publisher repos need a token capable of `repository_dispatch` to send `pdomain-npm-publish`; this is documented in `README.md:43-53`.

## Risks And Drift

- No changelog or release notes file exists for this repo; GitHub-generated notes appear to be canonical.
- `scripts/release-common.sh` comment says "Python repos" even though this is Node tooling (`scripts/release-common.sh:2`).
- Registry allowlist currently indexes only `pdomain/pdomain-ui` (`scripts/regen-index.ts:12-15`), so new npm publishers require a code change.
- Release creates no package artifact. That is correct for tooling releases, but it can look like a publish gap without documentation.

## Recommended Updates

- Add release-process notes clarifying tag-only tooling releases versus publisher package releases.
- Document exact publisher PAT permissions required for `repository_dispatch`.
- Update the stale "Python repos" script comment.
- Add a small changelog or state that GitHub-generated notes are canonical.

