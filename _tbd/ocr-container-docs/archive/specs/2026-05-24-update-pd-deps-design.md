---
title: update-pd-deps generalized sibling-dep refresh for pd-* repos
date: 2026-05-24
status: ready-for-review
issue: ConcaveTrillion/ocr-container-meta#363
related: [ConcaveTrillion/ocr-container-meta#362]
depends_on: [2026-05-24-local-dev-standardization-design.md]
---

# `update-pd-deps`: generalized sibling-dep refresh for pd-* repos

## 1. Context

Two pd-* repos (pdomain-ocr-cli, pdomain-prep-for-pgdp) currently have a
`upgrade-pdomain-book-tools` Make target that pins pdomain-book-tools to its latest
GitHub tag. The target is single-purpose: only one upstream dep, only the
GitHub-tag source of truth.

Most pd-* repos depend on multiple sibling pd-* repos. The full dep DAG:

| Repo | pd-* Python deps | npm @concavetrillion/* deps |
|---|---|---|
| pdomain-ocr-cli | pdomain-book-tools | — |
| pdomain-ops | pdomain-book-tools | — |
| pdomain-ocr-training | pdomain-book-tools | — |
| pdomain-ocr-simple-gui | pdomain-book-tools, pdomain-ops | pdomain-ui |
| pdomain-ocr-labeler-spa | pdomain-book-tools | pdomain-ui |
| pdomain-ocr-trainer-spa | pdomain-book-tools, pdomain-ops, pdomain-ocr-training | pdomain-ui |
| pdomain-prep-for-pgdp | pdomain-book-tools, pdomain-ops | pdomain-ui |
| pdomain-ui | pdomain-book-tools, pdomain-ops (via codegen.versions.json) | — |

We want one `update-pd-deps` target per dependent that bumps all sibling
pd-* deps in a single shot, picking each one's latest version from the
authoritative registry (`pdomain-index-pip` for Python, `pdomain-index-npm` for npm).

## 2. Goals

- **One target per dependent** — `make update-pd-deps` in 9 repos handles
  every pd-* sibling (Python + npm) in one shot.
- **Registry as source of truth** — query `pdomain-index-pip` /
  `pdomain-index-npm` for "latest", not GitHub tags. Matches what `uv pip install`
  and `pnpm install` would resolve.
- **Co-exists cleanly with local-dev mode** — auto-flip out, bump, auto-flip
  back, with loud per-step messaging.
- **Doesn't commit** — leaves the diff for human review per ocr-container-meta#363.
- **Wire `pdomain-index-npm` in all 5 npm-consuming repos** as a prerequisite step.

## 3. Non-goals

- Cross-repo release coordination (e.g. "bump pdomain-book-tools across all 8
  dependents and PR each at once"). Separate concern, separate spec.
- Auto-commit / auto-PR. Manual review wanted.
- Replacing `upgrade-deps` — that workspace-canonical target bumps ALL deps;
  `update-pd-deps` is narrower (just pd-* siblings).
- Adding `update-pd-deps` to pdomain-book-tools, pdomain-ocr-synth, pd-png-optimizer —
  they have no pd-* deps.

## 4. Architecture

### Dependency on spec #362

This spec **depends on [#362](2026-05-24-local-dev-standardization-design.md)**
shipping at least `local-dev` + `local-check` + the marker-file convention in
the 8 repos that have local-dev support. `update-pd-deps` uses the marker to
detect mode and `make local-dev` to restore after flipping.

pdomain-ui is special: it has `update-pd-deps` (it consumes pdomain-book-tools + pdomain-ops
via codegen.versions.json) but has NO local-dev support per #362. For pdomain-ui,
the auto-flip step is a no-op because the marker is never written. See §5.1
step 1's "if marker file convention applies to this repo" qualifier.

Implementation order: #362 ships first in the 8 dependent repos; #363 ships
after.

### Prerequisite: wire `pdomain-index-npm`

Survey finding: NONE of the 4 SPAs or pdomain-ui currently has `.npmrc` pointing
at `pdomain-index-npm`. Without it, npm-side updates have no registry to query.
The first per-repo commit in #363's plan adds:

```
# frontend/.npmrc (SPAs) or .npmrc (pdomain-ui)
@concavetrillion:registry=https://concavetrillion.github.io/pdomain-index-npm/
```

This is a deliverable of this spec (not a separate prerequisite issue).

### Per-repo script pattern

`scripts/update-pd-deps.sh` per repo. Modeled exactly on `scripts/do-release.sh`:
bash, `set -euo pipefail`, clear logging, idempotent. Different dep sets and
different file edits per repo (pyproject.toml vs frontend/package.json vs
codegen.versions.json), but the shared logic — query index, bump, re-lock —
follows the same shape everywhere.

## 5. Detailed behavior

### 5.1 Algorithm

1. **Detect local-dev mode** (skip this step for repos without local-dev
   support — currently only pdomain-ui among the 9 `update-pd-deps` repos).
   Read `.venv/.pd-local-mode`. If present, print a loud warning:

   ```
   ⚠️  update-pd-deps requires registry mode. You're in local-dev.
       I will:
         (1) flip out of local-dev (uninstall editable siblings)
         (2) bump pd-* deps from pdomain-index-pip / pdomain-index-npm
         (3) restore local-dev (re-install siblings editable)
       Continue? [y/N]
   ```

   Bail on N or non-interactive without `FORCE=1`.

2. **(If in local-dev) Flip out.**
   - Python: `uv pip uninstall <each-sibling>` per Python sibling
   - npm: `cd frontend && pnpm unlink <each-sibling>` per npm sibling
   - Remove marker
   - Loud confirmation: `→ Flipped out of local-dev. Siblings will resolve from registry.`

3. **Discover pd-* deps.** Parse:
   - `pyproject.toml` → packages matching `pd-*` in `dependencies` /
     `optional-dependencies` / `dependency-groups.dev`
   - `frontend/package.json` (SPAs) or `package.json` (pdomain-ui) → keys matching
     `@concavetrillion/*` in `dependencies` / `peerDependencies`
   - `codegen.versions.json` (pdomain-ui only) → its pinned `pdomain-book-tools` +
     `pdomain-ops` wheel versions

4. **Resolve "latest" for each.**
   - Python: HTTP GET `https://concavetrillion.github.io/pdomain-index-pip/simple/<pkg>/`
     → parse `<a>` tags → pick highest semver. Cache per-run.
   - npm: HTTP GET `https://concavetrillion.github.io/pdomain-index-npm/@concavetrillion/<pkg>/`
     → parse package metadata `dist-tags.latest`. Cache per-run.

5. **Bump pins in place.**
   - Python: edit `pyproject.toml` `dependencies` line for each pd-* dep
   - npm: edit `package.json` `dependencies` / `peerDependencies` for each
   - pdomain-ui: edit `codegen.versions.json` for its pinned wheel versions

6. **Re-lock + sync.**
   - Python: `uv lock && uv sync` (will pull new versions from pdomain-index-pip)
   - npm: `cd frontend && pnpm install` (will pull new from pdomain-index-npm)
   - pdomain-ui only: after `codegen.versions.json` bump, `make codegen` to
     regenerate `src/types/generated/`

7. **Print summary table.**

   ```
   pdomain-book-tools           0.9.1          → 0.10.0
   pdomain-ops              0.2.2          → 0.2.3
   @concavetrillion/pdomain-ui  0.1.0-alpha.1  → 0.1.0-alpha.2

   (3 bumped, 1 already current)
   ```

8. **(If flipped) Restore local-dev.** `make local-dev`. Loud confirmation:

   ```
   ✓ Restored local-dev mode. Siblings editable again.
   ```

9. **Do NOT commit.** Leaves the diff for review.

### 5.2 Per-repo target presence

| Repo | update-pd-deps? | Python deps touched | npm deps touched | codegen file? |
|---|---|---|---|---|
| pdomain-book-tools | — | — | — | — |
| pdomain-ocr-cli | ✓ | pdomain-book-tools | — | — |
| pdomain-ops | ✓ | pdomain-book-tools | — | — |
| pdomain-ocr-training | ✓ | pdomain-book-tools | — | — |
| pdomain-ocr-simple-gui | ✓ | pdomain-book-tools, pdomain-ops | pdomain-ui | — |
| pdomain-ocr-labeler-spa | ✓ | pdomain-book-tools | pdomain-ui | — |
| pdomain-ocr-trainer-spa | ✓ | pdomain-book-tools, pdomain-ops, pdomain-ocr-training | pdomain-ui | — |
| pdomain-prep-for-pgdp | ✓ | pdomain-book-tools, pdomain-ops | pdomain-ui | — |
| pdomain-ui | ✓ | — | — | codegen.versions.json (pdomain-book-tools, pdomain-ops) |
| pdomain-ocr-synth | — | — | — | — |
| pd-png-optimizer | — | — | — | — |

9 repos get the target. pdomain-ui's variant is special — it edits
`codegen.versions.json` (not pyproject.toml or package.json) and triggers
`make codegen` after the bump.

### 5.3 Deprecation of `upgrade-pdomain-book-tools`

The existing `upgrade-pdomain-book-tools` target in pdomain-ocr-cli and
pdomain-prep-for-pgdp becomes a one-line alias for `update-pd-deps`:

```makefile
upgrade-pdomain-book-tools: ## DEPRECATED: alias for update-pd-deps
	@echo "warning: upgrade-pdomain-book-tools is deprecated; use update-pd-deps"
	@$(MAKE) update-pd-deps
```

Marked DEPRECATED in `make help`. Removed in a follow-up commit after one
release cycle.

## 6. Implementation plan

Sequenced so each step is reviewable independently:

1. **Wire `pdomain-index-npm`** in the 5 npm-consuming repos
   (pdomain-ocr-simple-gui, pdomain-ocr-labeler-spa, pdomain-ocr-trainer-spa,
   pdomain-prep-for-pgdp, pdomain-ui). One commit per repo: add `.npmrc` with the
   scope registry line. Run `pnpm install` to verify resolution still works
   (versions don't change). Per-repo PRs.

2. **Reference implementation in pdomain-prep-for-pgdp.** Build
   `scripts/update-pd-deps.sh` with the canonical algorithm. Wire the Make
   target. Add deprecation alias for `upgrade-pdomain-book-tools`. Test manually:
   `make update-pd-deps` should bump pdomain-book-tools + pdomain-ops + pdomain-ui to
   their current registry latests without committing. Document the
   reference in `/workspaces/ocr-container/docs/process/update-pd-deps.md`.

3. **Propagate to other 8 dependents.** Per-repo: copy
   `scripts/update-pd-deps.sh` from prep-for-pgdp; tailor the dep list +
   file paths; wire the Make target; deprecate `upgrade-pdomain-book-tools` if
   the repo has it. Use parallel agent dispatch (one agent per repo) since
   they're independent.

4. **pdomain-ui variant.** Special-case: edit `codegen.versions.json` instead
   of pyproject.toml; trigger `make codegen` after the bump; verify the
   regenerated TS types are part of the diff.

5. **Workspace process doc.** Write `docs/process/update-pd-deps.md`:
   when to use, how it interacts with `local-dev`, what NOT to do (don't
   commit blindly — review the diff because bumps may include breaking
   changes; for breaking changes, ensure the downstream tests still pass
   with `make ci` before committing).

6. **CLAUDE.md references.** Update workspace and per-repo CLAUDE.md "Commands"
   tables to include `update-pd-deps`. Note the deprecation of
   `upgrade-pdomain-book-tools` where it appears.

## 7. Migration / Rollout

- **Sequencing:** ships AFTER spec [#362](2026-05-24-local-dev-standardization-design.md)
  has landed at least `local-dev` + `local-check` + marker convention in the
  8 dependent repos with local-dev support. The implementation cannot reliably
  auto-flip without these. pdomain-ui (no local-dev) is unblocked once #362 starts.
- **`pdomain-index-npm` go-live:** the registry already exists per workspace
  policy (per CLAUDE.md). Wiring `.npmrc` should be a no-op for current
  resolution (assuming pdomain-index-npm is reachable and has `@concavetrillion/pdomain-ui`
  published). If pdomain-index-npm is empty for any pkg, the per-repo PR catches
  it via `pnpm install` failure — surface and fix before merging.
- **`upgrade-pdomain-book-tools` aliases:** kept for one cycle, then removed.
  Process doc explains the rename. No agent prompts reference the old name
  yet that the orchestrator is aware of, so callsites should be minimal.

## 8. Risks & alternatives

- **Risk:** `pdomain-index-pip` lag behind GitHub releases. If a release was tagged
  but the index hasn't published it yet, `update-pd-deps` reports "already
  current" even though a newer version exists. Mitigation: the user can
  re-run after the release workflow completes; the workspace process doc
  mentions this lag explicitly.
- **Risk:** breaking-change bumps. `update-pd-deps` doesn't run `make ci`
  before completing — it leaves the diff for review precisely because the
  user might need to fix call sites. Mitigation: doc says "always run
  `make ci` before committing the result."
- **Risk:** auto-flip leaves the repo in registry mode if step 8 fails.
  Mitigation: trap an exit handler that prints `→ ERROR: did NOT restore
  local-dev. Run 'make local-dev' to restore manually.`
- **Risk:** the npm-side `pnpm install` may take a long time on first run
  after wiring pdomain-index-npm if the lockfile mismatches. Mitigation: the
  prerequisite step (item 1 above) catches it once per repo.
- **Alternative rejected:** workspace-shared script under
  `/workspaces/ocr-container/scripts/update-pd-deps.sh`. Rejected — same
  reason as #362: a checkout of one repo alone wouldn't work.
- **Alternative rejected:** "latest" = latest GitHub release. Rejected because
  it disagrees with what `uv pip install` actually resolves; registry
  is authoritative.
- **Alternative rejected:** auto-commit. Rejected per ocr-container-meta#363
  body: human review of the diff is the whole point (breaking changes are
  routine in pre-1.0 pd-* repos).

## 9. Open questions

None at design time. All ambiguities resolved in the 2026-05-24 brainstorming
session.
