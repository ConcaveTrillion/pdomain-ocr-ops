---
title: pdomain configuration and release audit
date: 2026-06-03
scope: all active pdomain-* repos in /workspaces/ocr-container
---

# pdomain Configuration And Release Audit

This bundle records a parallel review of Makefiles, GitHub Actions, release processes,
version processes, GitHub token/PAT usage, and publish/index assumptions across the
active `pdomain-*` repos in `/workspaces/ocr-container`.

Each repo has its own audit file:

- [GitHub Actions comparison](github-actions-comparison.md)
- [pdomain-book-tools](pdomain-book-tools.md)
- [pdomain-index-npm](pdomain-index-npm.md)
- [pdomain-index-pip](pdomain-index-pip.md)
- [pdomain-ocr-cli](pdomain-ocr-cli.md)
- [pdomain-ocr-labeler-spa](pdomain-ocr-labeler-spa.md)
- [pdomain-ocr-simple-gui](pdomain-ocr-simple-gui.md)
- [pdomain-ocr-synth](pdomain-ocr-synth.md)
- [pdomain-ocr-trainer-spa](pdomain-ocr-trainer-spa.md)
- [pdomain-ocr-training](pdomain-ocr-training.md)
- [pdomain-ops](pdomain-ops.md)
- [pdomain-prep-for-pgdp](pdomain-prep-for-pgdp.md)
- [pdomain-ui](pdomain-ui.md)

## Common Baseline

Most repos now share the same release architecture:

- local `make release-{patch,minor,major}` targets drive release creation;
- release scripts require clean/up-to-date `main`, compute the next semver tag, run a local preflight, create an annotated tag, and push;
- Python repos derive package metadata versions from git tags via `hatch-vcs`;
- Python package artifacts are GitHub Release wheels/sdists indexed by `pdomain-index-pip`, not PyPI;
- npm package publishing is GitHub Release tarball indexing by `pdomain-index-npm`, not npm registry token publishing;
- `secrets.PDOMAIN_INDEX_DISPATCH` is the cross-repo secret used to notify index repos;
- `github.token` / `secrets.GITHUB_TOKEN` is used for same-repo release creation, dep-refresh PRs, and public release reads;
- GitHub Actions are generally SHA-pinned and maintained by `dep-refresh.yml` plus `scripts/update_github_actions.py`.

The outlier is `pdomain-ui`, which is an npm package and uses `package.json` as the
package version source. Its release workflow triggers on `v*` tag push instead of
workflow dispatch.

## Comparison Matrix

| Repo | Package type | Version source | Release trigger | Publish target | Main concern |
|---|---|---|---|---|---|
| `pdomain-book-tools` | Python lib | VCS tag | local script -> dispatch | GitHub Release + pip index | changelog and install-channel drift |
| `pdomain-index-npm` | Node tooling | tag-only repo release | local script -> dispatch | GitHub Release + Pages regen | tag-only release docs and PAT permissions |
| `pdomain-index-pip` | Python tooling | tag-only repo release | local script -> dispatch | GitHub Release + Pages regen | Pages/allowlist docs and PAT permissions |
| `pdomain-ocr-cli` | Python CLI | VCS tag | local script -> dispatch | GitHub Release + pip index | stale `DEVELOPMENT.md`, dep updater misses `pdomain-ops` |
| `pdomain-ocr-labeler-spa` | Python + SPA | VCS tag | local script -> dispatch | GitHub Release + pip index | stale release runbook, Docker version default |
| `pdomain-ocr-simple-gui` | Python + SPA | VCS tag | local script -> dispatch | GitHub Release + pip index | stale changelog, no release runbook |
| `pdomain-ocr-synth` | Python CLI/lib | VCS tag plus hard-coded runtime | local script -> dispatch | GitHub Release + pip index | runtime version drift, no changelog |
| `pdomain-ocr-trainer-spa` | Python + SPA | VCS tag plus hard-coded runtime | local script -> dispatch | GitHub Release + pip index | absolute local `pdomain-ops` source likely breaks CI/release |
| `pdomain-ocr-training` | Python lib/CLI | VCS tag plus hard-coded runtime | local script -> dispatch | GitHub Release + pip index | runtime version drift, action updater misses cache |
| `pdomain-ops` | Python lib | VCS tag | local script -> dispatch | GitHub Release + pip index | PR-only CI, action updater/local-dev marker drift |
| `pdomain-prep-for-pgdp` | Python + SPA | VCS tag | local script -> dispatch | GitHub Release + pip index | stale `DEVELOPMENT.md`, Docker version default |
| `pdomain-ui` | npm package | `package.json` | tag push | GitHub Release + npm index | tag/package assertion and local-only release gates |

## Highest-Priority Updates

1. Fix likely CI/release blocker in `pdomain-ocr-trainer-spa`.
   Remove or local-gate the committed absolute uv source
   `/workspaces/ocr-container/pdomain-ops`, regenerate the lockfile against registry
   sources, and fix the Dockerfile's repeated local-path assumption.

2. Standardize runtime version derivation.
   `pdomain-ocr-synth`, `pdomain-ocr-trainer-spa`, and `pdomain-ocr-training` have
   hard-coded runtime `__version__` values while package metadata is VCS-tag dynamic.
   Runtime version should come from installed metadata, generated VCS version files,
   or another single source.

3. Decide release trigger policy.
   Most Python repos publish only when the local release script dispatches
   `release.yml`; tag pushes alone do not publish. `pdomain-ui` publishes on tag
   push. Pick one standard or document the difference clearly. If tag pushes should
   publish Python packages, add protected tag triggers. If only local scripts are
   valid, document and enforce that path.

4. Extend action-pin updater coverage.
   Several repos use actions that their updater does not manage, including
   `actions/cache`, `pnpm/action-setup`, `actions/setup-node` variants,
   `jdx/mise-action`, and `actions/github-script`. The updater should include every
   action in workflow files or fail when unmanaged actions are present.

5. Remove avoidable third-party or helper actions where the workspace already has a
   shell or first-party equivalent.
   `pdomain-ui` uses `softprops/action-gh-release`, while the Python repos use
   `gh release create`; `pdomain-ocr-trainer-spa` nightly uses `actions/github-script`,
   while the workspace already uses `gh` for GitHub API operations; several pnpm
   workflows use `pnpm/action-setup`, while `pdomain-prep-for-pgdp` CI and
   `pdomain-ocr-trainer-spa` CI show a Corepack setup path.

6. Document dispatch PAT permissions once and link everywhere.
   Publisher repos use `PDOMAIN_INDEX_DISPATCH` for cross-repo `repository_dispatch`.
   Index repos mention publisher PAT needs, but the exact fine-grained token
   permissions should be centralized and referenced from release docs.

## Documentation And Process Drift

Several repos have docs that describe old release behavior:

- `pdomain-ocr-cli`: `DEVELOPMENT.md` still describes blocked/path-sourced
  `pdomain-ops` and manual tag pushing.
- `pdomain-ocr-labeler-spa`: release runbook says wheel plus sdist, while build is
  wheel-only; line references are stale.
- `pdomain-ocr-simple-gui`: changelog still says publish was blocked pending index
  workflow.
- `pdomain-prep-for-pgdp`: `DEVELOPMENT.md` describes push/tag release CI and
  container publishing that do not exist.
- `pdomain-book-tools`: changelog lags observed local tags.
- Index repos lack changelog/release-note policy docs.

Recommended standard: each repo should either maintain `CHANGELOG.md` and enforce a
release checklist, or explicitly state that GitHub-generated release notes are
canonical.

## CI Trigger And Gate Differences

- `pdomain-ui` runs CI on push and PR to `main` and uses concurrency cancellation.
- Most other repos run CI only on PRs to `main`.
- Dispatch-only Python releases generally re-run `make ci-slow` in the release
  workflow.
- `pdomain-ocr-simple-gui` intentionally publishes without GitHub-side tests and
  relies on local preflight.
- `pdomain-ui` release omits `make ci`, `codegen-check`, and `theme-check`, relying on
  local preflight before tag push.
- `pdomain-ocr-labeler-spa` E2E is currently non-blocking.

Recommended standard: release workflows should assert the artifact-critical invariants
that can be checked in GitHub, even if expensive or registry-dependent checks remain
local-only.

## GitHub Actions Differences

See [GitHub Actions comparison](github-actions-comparison.md) for the full action
inventory and replacement targets. The main policy finding is that the workspace
already has shell-based patterns for several jobs currently handled by third-party
or helper actions:

- replace `softprops/action-gh-release` in `pdomain-ui` with `gh release create`;
- replace `actions/github-script` in `pdomain-ocr-trainer-spa` nightly with
  `gh issue create`;
- replace `pnpm/action-setup` where practical with `actions/setup-node` plus a pinned
  Corepack activation step;
- keep `astral-sh/setup-uv` as an explicit workspace exception unless uv installation
  is standardized another way.

## Version Source Differences

Python repos mostly use VCS tags through `hatch-vcs`, while repo-code releases for the
index repos are tag-only and do not bump `package.json` or `pyproject.toml`.

`pdomain-ui` is different: its package version is `package.json`, and the release
script writes it from the next tag. The release workflow should assert
`package.json` version equals the pushed tag to prevent manual tag drift.

Docker builds in `pdomain-ocr-labeler-spa` and `pdomain-prep-for-pgdp` replace dynamic
VCS versioning with `ARG VERSION` and default to `0.0.0+docker`; local docker build
targets do not currently pass a real version.

## Token And PAT Pattern

No PyPI token, Twine token, `NPM_TOKEN`, or `NODE_AUTH_TOKEN` publish flow was found
in these audits. Publishing is based on GitHub Release assets plus static index
regeneration.

Common token usage:

- `github.token` / `secrets.GITHUB_TOKEN`: same-repo release creation, dep-refresh PRs,
  and public release reads.
- `secrets.PDOMAIN_INDEX_DISPATCH`: cross-repo repository dispatch to
  `pdomain-index-pip` or `pdomain-index-npm`.
- Runtime external-service tokens are separate and app-specific, such as Hugging Face
  token lookup in `pdomain-ocr-synth` and `pdomain-ocr-trainer-spa`.

## Follow-Up Work Queue

1. Fix `pdomain-ocr-trainer-spa` release-source and lockfile issue.
2. Add or centralize `PDOMAIN_INDEX_DISPATCH` PAT permissions docs.
3. Update stale release docs in `pdomain-ocr-cli`, `pdomain-ocr-labeler-spa`,
   `pdomain-ocr-simple-gui`, and `pdomain-prep-for-pgdp`.
4. Standardize runtime version derivation across Python packages.
5. Remove avoidable third-party/helper actions: `softprops/action-gh-release`,
   `actions/github-script`, `jdx/mise-action` if not essential, and
   `pnpm/action-setup` where Corepack is enough.
6. Expand `update_github_actions.py` coverage and add an unmanaged-action check.
7. Decide and document PR-only versus push-to-main CI policy.
8. Decide and document dispatch-only versus tag-push release policy.
9. Add changelog policy/release checklist per repo.
10. Add release artifact assertions where missing, especially tag/package version checks
   in `pdomain-ui` and installer smoke checks in app repos.

## Remediation Status

The implementation plan for this audit is
`docs/superpowers/plans/2026-06-03-pdomain-config-release-remediation.md`.

Execution completed the planned remediation across isolated per-repo worktrees:

- Root policy docs were added in commit `e55b9dc`, including the corrected
  `PDOMAIN_INDEX_DISPATCH` fine-grained PAT policy requiring `Contents: Write`
  on the target index repo for `repository_dispatch`.
- Every repo with `scripts/update_github_actions.py` now fails on unmanaged
  workflow `uses:` entries, and all managed-action verifiers passed against the
  final workflows.
- Avoidable helper actions were removed from active workflows:
  `softprops/action-gh-release`, `pnpm/action-setup`, `jdx/mise-action`, and
  `actions/github-script`.
- All `ci.yml` workflows now run on push and pull request to `main` and use
  canceling CI concurrency.
- `pdomain-ocr-trainer-spa` no longer commits an absolute local `pdomain-ops`
  uv source; its Docker build/install path uses locked registry dependencies.
- Runtime `__version__` values in `pdomain-ocr-synth`,
  `pdomain-ocr-trainer-spa`, and `pdomain-ocr-training` now derive from installed
  package metadata with tested fallback behavior.
- Release workflows now include GitHub-side artifact assertions, and
  `pdomain-ui` asserts the pushed tag matches `package.json`.
- Docker build targets in `pdomain-ocr-labeler-spa` and
  `pdomain-prep-for-pgdp` pass a git-derived `VERSION` build arg.
- Active release docs and source-of-truth specs were updated to remove stale
  tag-push, container-publish, attestation, owner, and blocked-release claims.
- Dependency refresh coverage now includes `pdomain-ops` for `pdomain-ocr-cli`,
  and `pdomain-ops` guards dependency upgrades in local dependency mode.

Final per-repo remediation heads:

| Repo | Final head | Last remediation subject |
|---|---:|---|
| `pdomain-book-tools` | `3c21741fea8a` | `docs: align pdomain release documentation` |
| `pdomain-index-npm` | `f8b5640b6bde` | `docs: align pdomain release documentation` |
| `pdomain-index-pip` | `5bea33d859d4` | `docs: align pdomain release documentation` |
| `pdomain-ocr-cli` | `3aa7d9656792` | `docs: fix stale release workflow notes` |
| `pdomain-ocr-labeler-spa` | `7651a64370f0` | `docs: fix stale release workflow notes` |
| `pdomain-ocr-simple-gui` | `5feead6f104b` | `docs: align pdomain release documentation` |
| `pdomain-ocr-synth` | `a8f5d645705b` | `test: verify runtime version metadata` |
| `pdomain-ocr-trainer-spa` | `b679939ab1df` | `ci: strengthen release workflow assertions` |
| `pdomain-ocr-training` | `81b8e696cd75` | `test: verify runtime version metadata` |
| `pdomain-ops` | `91ad8e384861` | `fix: run dependency updater with project python` |
| `pdomain-prep-for-pgdp` | `d9aa9ca3effa` | `docs: align deployment spec release workflow` |
| `pdomain-ui` | `d8a739524203` | `ci: strengthen release workflow assertions` |

Final verification evidence:

- Forbidden helper-action scan over active workflows found no
  `softprops/action-gh-release`, `pnpm/action-setup`, `jdx/mise-action`, or
  `actions/github-script` entries.
- Local uv source scan over `pyproject.toml` and `uv.lock` found no
  `/workspaces/ocr-container` path sources or editable sources.
- Hard-coded runtime version scan found no stale `0.0.1`, `0.1.0a0`, or `0.2.1`
  assignments in the targeted version repos.
- All twelve `ci.yml` workflows include both `push` and `pull_request` triggers
  for `main` and canceling concurrency.
- `verify_managed_actions(.github/workflows)` passed in all twelve repos.
- Focused version tests passed: synth `5 passed`, training `10 passed`, trainer
  SPA `3 passed`.
