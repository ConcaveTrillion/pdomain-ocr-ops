# pdomain Release And Index Dispatch Policy

## Agent Index

- Use this doc when changing pdomain release workflows, index dispatch secrets,
  release runbooks, or GitHub Actions policy.
- Python packages publish GitHub Release assets and notify `pdomain-index-pip`;
  `pdomain-ui` publishes GitHub Release tarballs and notifies `pdomain-index-npm`.
- `PDOMAIN_INDEX_DISPATCH` requires Contents write on the target index repo for
  repository dispatch.

## Release Channels

Python package repos publish wheels and sdists as GitHub Release assets. The self-hosted `pdomain-index-pip` Pages site indexes those assets. These repos do not use PyPI, `TWINE_USERNAME`, `TWINE_PASSWORD`, or PyPI trusted publishing.

The `pdomain-ui` package publishes a GitHub Release tarball. The self-hosted `pdomain-index-npm` Pages site indexes that tarball. It does not use `NPM_TOKEN` or `NODE_AUTH_TOKEN` for registry publishing.

The index repos publish tooling releases as GitHub Releases and regenerate GitHub Pages. Their repo metadata versions may stay `0.0.0`; their release version is the git tag.

## Release Triggers

Python package repos use local release scripts as the only supported publish path:

```bash
make release-patch
make release-minor
make release-major
```

Those scripts run local preflight checks, create an annotated `vX.Y.Z` tag, push `main` and the tag, then dispatch `.github/workflows/release.yml` with the tag input.

`pdomain-ui` uses tag-push release because the package version in `package.json` is committed by its release script before tagging. The release workflow must assert that `package.json` version equals the pushed tag.

## Dispatch Secret

Publisher repos notify index repos with `secrets.PDOMAIN_INDEX_DISPATCH`.

Use a fine-grained GitHub PAT with:

- Resource owner: `pdomain`
- Repository access: only the target index repo, either `pdomain-index-pip` or `pdomain-index-npm`
- Repository permissions:
  - Contents: Write
  - Metadata: Read-only
  - Actions: Read-only
  - Administration: No access
  - Pull requests: No access
  - Issues: No access
- Endpoint required: `POST /repos/pdomain/<index-repo>/dispatches`

If the secret is absent or the dispatch fails, release workflows must warn and continue. The index repo scheduled regen is the fallback.

## GitHub Actions Policy

All workflow `uses:` entries must be pinned to immutable commit SHAs with adjacent version comments.

Allowed third-party actions:

- `astral-sh/setup-uv`, until the workspace standardizes a first-party shell install path for uv.

Avoid these actions when a shell or first-party equivalent exists:

- `softprops/action-gh-release`; use `gh release create`.
- `pnpm/action-setup`; use `actions/setup-node` plus pinned Corepack activation.
- `jdx/mise-action`; use explicit setup steps unless the workflow documents mise-only behavior.
- `actions/github-script`; use `gh` CLI for GitHub API operations unless JavaScript execution is required.

Each repo's `scripts/update_github_actions.py` must fail if any workflow has an unmanaged `uses:` entry.
