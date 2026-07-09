# Updating sibling pd-* deps

Canonical pattern for bumping a pd-* repo's sibling pd-* dependencies (both
Python wheels via `pdomain-index-pip` and npm packages via `pdomain-index-npm`) to
their current registry latest. See [spec #363](../archive/specs/2026-05-24-update-pd-deps-design.md).

## What it does

`make update-pd-deps` queries the workspace self-hosted indexes for each
sibling pd-* dep's latest version, edits `pyproject.toml` /
`package.json` / `codegen.versions.json` accordingly, runs `uv lock` (or
`pnpm install`, or `make codegen`) to refresh resolution, and **leaves the
diff staged** for human review. It never commits — that's deliberate so the
reviewer can decide whether the bump is safe to land.

## Source of truth

- Python wheels: `pdomain-index-pip` (PEP 503 simple index hosted on GitHub Pages
  at `ConcaveTrillion/pdomain-index-pip`).
- `@concavetrillion/*` npm packages: `pdomain-index-npm` (Verdaccio-style static
  registry at `ConcaveTrillion/pdomain-index-npm`, GitHub Pages).

NOT GitHub Releases — releases can lead the index by several hours while
the release-workflow rebuilds/republishes the index. If a release was just
tagged, re-run `make update-pd-deps` once the workflow completes.

## Local-dev interaction

If the repo is in local-dev mode (marker `.venv/.pd-local-mode` present per
[local-dev.md](local-dev.md)), `make update-pd-deps`:

1. Detects the marker; auto-flips OUT of local-dev mode.
2. Performs the registry bump (resolution against the published versions).
3. Auto-flips BACK into local-dev mode (`make local-dev` restores editables).

Loud per-step messaging makes the flip visible. The human ends in the same
mode they started in, with a staged diff to review.

## Per-repo presence matrix

From spec §5.2: 9 repos have the target.

| Repo | Has update-pd-deps |
|---|---|
| pdomain-book-tools | — (no pd-* deps; foundation lib) |
| pdomain-ocr-cli | ✓ (pdomain-book-tools) |
| pdomain-ops | ✓ (pdomain-book-tools) |
| pdomain-ocr-training | ✓ (pdomain-book-tools) |
| pdomain-ocr-simple-gui | ✓ (pdomain-book-tools, pdomain-ops, pdomain-ui) |
| pdomain-ocr-labeler-spa | ✓ (pdomain-book-tools, pdomain-ui) |
| pdomain-ocr-trainer-spa | ✓ (pdomain-book-tools, pdomain-ops, pdomain-ocr-training, pdomain-ui) |
| pdomain-prep-for-pgdp | ✓ (pdomain-book-tools, pdomain-ops, pdomain-ui) — reference impl |
| pdomain-ui | ✓ (special case: edits codegen.versions.json) |
| pdomain-ocr-synth | — (no pd-* deps today) |
| pd-png-optimizer | — (no pd-* deps) |

## pdomain-ui special case

`pdomain-ui` doesn't import sibling pd-* code at runtime — it consumes
`pdomain-book-tools` only as a **codegen input** for generated TypeScript types
(model schemas → `frontend/src/codegen/`). Therefore its `update-pd-deps`:

1. Edits `codegen.versions.json` to bump the `pdomain-book-tools` version.
2. Runs `make codegen` to regenerate `frontend/src/codegen/`.
3. Leaves the bumped json + regenerated codegen staged for review.

There is no pyproject or package.json bump in pdomain-ui's variant.

## Human review expectations

Always run `make ci` before committing the bumped diff. Pre-1.0 pd-* repos
do not guarantee semver — breaking changes can arrive at any minor or patch
bump. `update-pd-deps` does not guard against them; the human reviewer must.

If `make ci` fails after the bump, the typical fixes are:

- Adjust call sites to match a renamed API.
- Pin an upper bound on the dep until the breaking change is resolved.
- Roll back the bump (`git restore -SW pyproject.toml uv.lock`) if not ready.

## What if pdomain-index-pip lags GitHub?

The release-workflow publishes wheels into the index via a GitHub Pages
deploy. If you tag a release and run `make update-pd-deps` within minutes,
the index may not have the new version yet. Re-run after the workflow
completes (typically 1–3 minutes).

## Cross-references

- Spec: [docs/archive/specs/2026-05-24-update-pd-deps-design.md](../archive/specs/2026-05-24-update-pd-deps-design.md)
- Local-dev companion: [local-dev.md](local-dev.md)
- Reference implementation (after #363 M2 lands): `pdomain-prep-for-pgdp/scripts/update-pd-deps.sh`
- Release index repos: `ConcaveTrillion/pdomain-index-pip`, `ConcaveTrillion/pdomain-index-npm`
