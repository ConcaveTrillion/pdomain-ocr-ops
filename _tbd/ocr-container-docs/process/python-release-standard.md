# Python Release Standard

Workspace Python packages use the same release contract unless a repo documents
an exception.

## Local Entry Points

- `make release-patch`, `make release-minor`, and `make release-major` delegate
  to `_do-release BUMP=...`.
- `_do-release` runs `scripts/do-release.sh`.
- `scripts/do-release.sh` sets repo-local config and delegates to
  `scripts/release-common.sh`.
- `scripts/release-common.sh` is intentionally byte-identical across repos.

## Release Gate

The release path has two gates:

- Local gate: `scripts/release-common.sh` runs `make ci-slow` before creating a
  tag. `FORCE=1` skips repo-state guards only; it does not skip `ci-slow`.
- GitHub gate: `.github/workflows/release.yml` runs a `release-ci` job before
  `publish`.

`ci-slow` must include artifact build coverage. It can alias `ci` only when
`ci` already builds the package artifacts.

## Workflow Triggers

- `.github/workflows/ci.yml` is for pull requests only.
- `.github/workflows/release.yml` is `workflow_dispatch` only and requires a
  `tag` input.
- Release tag pushes do not trigger workflows directly. The local release helper
  pushes the exact branch and exact tag, then dispatches `release.yml` with the
  tag input.

## Release Publishing

- Release workflows build via `make build`.
- Release workflows publish with `gh release create`.
- Release workflows notify `pdomain/pdomain-index-pip` using the
  `PDOMAIN_INDEX_DISPATCH` secret, event `pd-release-published`, and payload
  fields `repo` and `tag`.
- If dispatch fails or the secret is missing, the warning should say the index
  catches up via daily cron.

## Action Pinning

All external actions must be pinned to a full commit SHA with a version comment.
Update the SHA and version comment together after checking the upstream release
tag.

## Audit Commands

```bash
rg -n '^  push:' */.github/workflows
rg -n 'uses: [^@]+@(v[0-9]|main|master)' */.github/workflows
for d in pd-ocr-labeler pd-ocr-trainer pd-png-optimizer pdomain-*; do
  [ -f "$d/scripts/release-common.sh" ] || continue
  cmp -s pdomain-ops/scripts/release-common.sh "$d/scripts/release-common.sh" || echo "$d differs"
done
```
