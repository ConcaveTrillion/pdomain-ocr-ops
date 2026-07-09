---
title: pdomain GitHub Actions comparison
date: 2026-06-03
scope: workflow action usage across active pdomain-* repos
---

# GitHub Actions Comparison

This compares `uses:` entries across the active `pdomain-*` repos. The policy concern
is third-party action usage where another repo already performs the same work with
first-party actions plus shell commands.

The inventory below records the audit-time state. The remediation completed from this
audit removed the avoidable helper actions called out here and added unmanaged-action
verification to every updater script.

## Action Inventory By Repo

| Repo | Actions used |
|---|---|
| `pdomain-book-tools` | `actions/checkout`, `astral-sh/setup-uv` |
| `pdomain-index-npm` | `actions/checkout`, `actions/setup-node`, `actions/configure-pages`, `actions/upload-pages-artifact`, `actions/deploy-pages`, `astral-sh/setup-uv`, local workflow call to `regen.yml` |
| `pdomain-index-pip` | `actions/checkout`, `actions/configure-pages`, `actions/upload-pages-artifact`, `actions/deploy-pages`, `astral-sh/setup-uv`, local workflow call to `regen.yml` |
| `pdomain-ocr-cli` | `actions/checkout`, `astral-sh/setup-uv` |
| `pdomain-ocr-labeler-spa` | `actions/checkout`, `actions/setup-node`, `actions/upload-artifact`, `actions/download-artifact`, `astral-sh/setup-uv`, `pnpm/action-setup` |
| `pdomain-ocr-simple-gui` | `actions/checkout`, `actions/setup-node`, `astral-sh/setup-uv`, `pnpm/action-setup` |
| `pdomain-ocr-synth` | `actions/checkout`, `astral-sh/setup-uv` |
| `pdomain-ocr-trainer-spa` | `actions/checkout`, `actions/setup-node`, `actions/github-script`, `astral-sh/setup-uv`, `jdx/mise-action`, `pnpm/action-setup` |
| `pdomain-ocr-training` | `actions/checkout`, `actions/cache`, `astral-sh/setup-uv` |
| `pdomain-ops` | `actions/checkout`, `actions/cache`, `astral-sh/setup-uv` |
| `pdomain-prep-for-pgdp` | `actions/checkout`, `actions/setup-node`, `astral-sh/setup-uv`, `pnpm/action-setup` |
| `pdomain-ui` | `actions/checkout`, `actions/setup-node`, `actions/upload-artifact`, `actions/download-artifact`, `actions/attest-build-provenance`, `softprops/action-gh-release`, `astral-sh/setup-uv`, `pnpm/action-setup` |

## First-Party Actions With Expected Variation

These are GitHub-owned `actions/*` entries. They still need pin/version maintenance,
but they are not the third-party-action concern.

- `actions/checkout`: used by every repo.
- `actions/setup-node`: used by Node/SPA repos and `pdomain-index-npm`.
- `actions/upload-artifact` / `actions/download-artifact`: used where workflows pass
  built SPA or tarball artifacts between jobs.
- `actions/configure-pages`, `actions/upload-pages-artifact`, `actions/deploy-pages`:
  used only by the index repos for GitHub Pages deployment.
- `actions/cache`: used only by `pdomain-ops` and `pdomain-ocr-training`.
- `actions/attest-build-provenance`: used only by `pdomain-ui` release provenance.
- Local workflow calls to `./.github/workflows/regen.yml`: used only by index repos.

The main first-party drift to fix is version inconsistency, not removal:

- `pdomain-ui` CI still uses `actions/checkout` v4.3.1 and `actions/setup-node` v4.4.0,
  while other repos use checkout v6.0.2 and setup-node v6.4.0.
- Artifact actions differ by repo: `pdomain-ocr-labeler-spa` uses newer
  upload/download SHAs than `pdomain-ui`.

## Third-Party And Avoidable Helper Actions

| Action | Repos | Current purpose | Similar process exists without it? | Recommendation |
|---|---|---|---|---|
| `astral-sh/setup-uv` | all Python or dep-refresh workflows | Install/pin uv | Not consistently; all uv workflows use it | Keep for now as a workspace-approved exception, but ensure updater manages it everywhere. |
| `pnpm/action-setup` | `pdomain-ocr-labeler-spa`, `pdomain-ocr-simple-gui`, `pdomain-ocr-trainer-spa`, `pdomain-prep-for-pgdp`, `pdomain-ui` | Install/activate pnpm | Yes. `pdomain-prep-for-pgdp` CI and `pdomain-ocr-trainer-spa` CI use `corepack enable && corepack prepare ... --activate` instead. | Replace with Corepack shell setup where practical, especially in release jobs. |
| `softprops/action-gh-release` | `pdomain-ui` only | Create GitHub Release | Yes. Python repos create releases with `gh release create` shell steps. | Replace with `gh release create` to match the rest of the workspace. |
| `jdx/mise-action` | `pdomain-ocr-trainer-spa` nightly only | Tool setup for nightly slow tests | Mostly yes. Other workflows use `actions/setup-node`, `astral-sh/setup-uv`, Corepack, and Make targets directly. | Remove unless nightly genuinely needs mise-specific behavior; prefer explicit setup steps. |
| `actions/github-script` | `pdomain-ocr-trainer-spa` nightly only | Create a GitHub issue on nightly failure | Yes. Can use `gh issue create` with `GH_TOKEN`, consistent with existing `gh` usage for releases and dispatch. | First-party but avoidable; replace with `gh issue create` shell step. |

## Concrete Replacement Targets

1. `pdomain-ui/.github/workflows/release.yml`
   Replace `softprops/action-gh-release` with a shell step using `gh release create`.
   This matches Python release workflows and removes a third-party release action from
   the only job with write permissions.

2. `pdomain-ocr-trainer-spa/.github/workflows/nightly.yml`
   Replace `actions/github-script` with `gh issue create`. Also remove
   `draft: true`, which is not a normal Issues API field. If mise is only setting up
   Python/Node/uv, replace `jdx/mise-action` with the explicit setup-node/setup-uv
   pattern used in CI.

3. `pnpm/action-setup` consumers
   Standardize on Corepack:

   ```yaml
   - uses: actions/setup-node@<pinned-sha>
     with:
       node-version: "24"
       cache: "pnpm"
   - name: Enable pnpm via corepack
     run: corepack enable && corepack prepare pnpm@<pinned-version> --activate
   ```

   `pdomain-prep-for-pgdp` CI already uses this style with `pnpm@11.3.0`.
   `pdomain-ocr-trainer-spa` CI uses the same shape but currently says
   `pnpm@latest`; pin that version before copying the pattern.

4. Action updater coverage
   If a third-party action remains, it must be included in `scripts/update_github_actions.py`.
   The updater should also fail when a workflow contains an unmanaged `uses:` entry.

## Keep Or Remove Decision Notes

- Keep `astral-sh/setup-uv` unless the workspace decides to install uv by a first-party
  shell path everywhere. It is third-party, but it is the common baseline rather than
  an outlier. This is the only retained third-party setup action intentionally allowed
  by the current policy.
- Keep GitHub-owned Pages actions in index repos. There is no equivalent shell process
  elsewhere in this workspace, and they are first-party.
- Keep `actions/attest-build-provenance` in `pdomain-ui` unless provenance is dropped.
  It is first-party and provides a unique release property.
- Prefer `gh` CLI shell steps for GitHub Release creation, issue creation, and
  repository dispatch because the repos already use `gh` for release and dispatch
  flows.

## Remediation Result

Final workflow policy decisions:

- Removed `softprops/action-gh-release`; `pdomain-ui` now uses `gh release create`.
- Removed `actions/github-script`; trainer nightly now uses `gh issue create`.
- Removed `jdx/mise-action`; trainer nightly now uses explicit uv, Python, Node, and
  pinned Corepack setup.
- Removed `pnpm/action-setup`; pnpm workflows now use `actions/setup-node` followed by
  `corepack enable && corepack prepare pnpm@11.3.0 --activate`.
- Removed `cache: pnpm` from `setup-node` steps that run before Corepack activation, so
  `setup-node` cannot try to call `pnpm` before pnpm exists.
- Retained `astral-sh/setup-uv`, GitHub-owned Pages actions, GitHub-owned cache/artifact
  actions, and `actions/attest-build-provenance`.

Final verification:

- `rg -n "softprops/action-gh-release|pnpm/action-setup|jdx/mise-action|actions/github-script" pdomain-*/.github/workflows`
  found no matches in the remediation worktrees.
- `verify_managed_actions(.github/workflows)` passed in every active `pdomain-*` repo.
- Every active workflow `uses:` entry is managed by the repo's updater or is a local
  workflow call.
