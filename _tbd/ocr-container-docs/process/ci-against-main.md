# `make ci-against-main` — git-main pre-release validation

Transiently validate a pd-* repo against its sibling pd-* dependencies'
**latest committed `main`** (not the published release, not local editable
checkouts), then revert. This is the third dependency-resolution mode; see
the [three modes](local-dev.md#three-resolution-modes) overview.

## Why

Registry mode validates against what's *published*; local-dev validates
against *uncommitted local drift*. Neither answers the pre-release question:
**"will a sibling's `main` break me once it's released?"** `ci-against-main`
locks each sibling to its current `main` SHA, runs the release preflight, and
reports — so integration breaks surface before a tag is cut, reproducibly.

## What it does

1. Refuses if the repo is in **local-dev mode** (`.venv/.pdomain-local-mode`)
   or if `pyproject.toml`/`uv.lock` have uncommitted changes (it restores
   them by backup, so they must be clean vs `HEAD`).
2. Backs up `pyproject.toml` + `uv.lock`.
3. Flips each pd-* `[tool.uv.sources]` entry from
   `{ index = "pdomain-index-pip" }` to
   `{ git = "https://github.com/pdomain/<sibling>.git", branch = "main" }`.
4. `uv lock` (captures each sibling's **current `main` SHA** → reproducible
   for the run) + `uv sync`.
5. Runs the preflight — `make ci-slow` by default.
6. **Always restores** `pyproject.toml`/`uv.lock` and re-syncs registry deps
   via an `EXIT` trap (on success, failure, or Ctrl-C), preserving the
   preflight's exit code. Zero committed churn.

## Scope: Python siblings only

npm siblings (`@pdomain/pdomain-ui`) are **out of scope**: `pdomain-ui` is a
built library whose git install requires a `dist`/`prepare` build path, which
was deferred by decision (2026-06-06). During `ci-against-main` the SPA still
builds against the **registry** npm `pdomain-ui` — unchanged.

## Usage

```sh
make ci-against-main                       # flip siblings → main, run `make ci-slow`, revert
PREFLIGHT="make test" make ci-against-main # faster smoke (skips slow gates)
VALIDATE_AGAINST_MAIN=1 make release-patch # run it as a pre-tag gate before releasing
```

`PREFLIGHT` overrides the command run against sibling main (default
`make ci-slow`). `VALIDATE_AGAINST_MAIN=1` makes `do-release.sh` run
`ci-against-main` before its normal published-deps preflight — off by default,
because a release should still validate against the deps it will actually ship.

## Configuration

Each repo's `scripts/ci-against-main.sh` sets `OWNER="pdomain"` and a
`PY_SIBLINGS=(...)` array matching that repo's `[tool.uv.sources]`. The
transform itself lives in `scripts/git_main_sources.py` (pure, unit-tested in
`tests/test_git_main_sources.py`).

## Rollout

Present in every pd-* Python repo that has pd-* siblings:

| Repo | `PY_SIBLINGS` |
|---|---|
| `pdomain-ops` | `pdomain-book-tools` |
| `pdomain-ocr-cli` | `pdomain-book-tools pdomain-ops` |
| `pdomain-ocr-training` | `pdomain-book-tools` |
| `pdomain-prep-for-pgdp` | `pdomain-book-tools pdomain-ops` |
| `pdomain-ocr-simple-gui` | `pdomain-book-tools pdomain-ops` |
| `pdomain-ocr-labeler-spa` | `pdomain-book-tools pdomain-ops` |
| `pdomain-ocr-trainer-spa` | `pdomain-book-tools pdomain-ops pdomain-ocr-training` |

`pdomain-ocr-synth` and `pdomain-book-tools` have no pd-* siblings, so they do
not carry the target.

## Caveat — worktree preflight

`make ci-slow` can fail inside a git worktree because `pre-commit install`
refuses when `core.hooksPath` is set (inherited by worktrees). When validating
from a worktree, use `PREFLIGHT="make test"` or run the preflight from the
canonical checkout.
