---
title: pdomain CI workflows and Makefile audit
date: 2026-05-31
scope: all 12 active pdomain repos
---

# pdomain CI Workflows and Makefile Audit

Scope: all 12 active pdomain repos — `pdomain-book-tools`, `pdomain-ocr-cli`,
`pdomain-ops`, `pdomain-ocr-training`, `pdomain-ocr-synth`, `pdomain-ui`,
`pdomain-ocr-simple-gui`, `pdomain-ocr-labeler-spa`, `pdomain-ocr-trainer-spa`,
`pdomain-prep-for-pgdp`, `pdomain-index-pip`, `pdomain-index-npm`.

---

## 1. Workflow inventory

Every repo has the same four workflow files as of 2026-05-31:

| Workflow | Purpose | Trigger |
|---|---|---|
| `ci.yml` | PR gate | `pull_request` → `main` |
| `dep-refresh.yml` | Weekly dep + SHA-pin maintenance | `schedule` (Sun 02:00 UTC) + `workflow_dispatch` |
| `release.yml` | Publish GitHub Release + notify pd-index | `workflow_dispatch` only |
| `regen.yml` | Rebuild + deploy GitHub Pages index | `schedule` + `repository_dispatch` + `workflow_call` |

`regen.yml` exists only in `pdomain-index-pip` and `pdomain-index-npm` — the two
self-hosted registry repos. All other 10 repos have just the first three.

---

## 2. CI workflow structure by repo

### 2a. Job structure

| Repo | CI jobs | Matrix |
|---|---|---|
| pdomain-book-tools | pre-commit, lint, typecheck, test, build, layout-fork | test: 3.11 / 3.12 / 3.13 |
| pdomain-ocr-cli | ci | 3.11 / 3.12 / 3.13 |
| pdomain-ops | pre-commit, lint, typecheck, test, build | 3.11 / 3.12 / 3.13 |
| pdomain-ocr-training | ci | 3.11 / 3.12 / 3.13 |
| pdomain-ocr-synth | ci | none (3.13 only) |
| pdomain-ui | lint-check, typecheck, unit-test, build-package | unit-test: 4 Vitest shards |
| pdomain-ocr-simple-gui | ci | none (3.11 only) |
| pdomain-ocr-labeler-spa | lint, test-backend, test-frontend, test-e2e, build-wheel, openapi-drift | none |
| pdomain-ocr-trainer-spa | ci | none (3.13 only) |
| pdomain-prep-for-pgdp | ci | none (3.13 only) |
| pdomain-index-pip | static-check, test | none |
| pdomain-index-npm | static-check, test | none |

### 2b. CI trigger coverage

All 12 repos trigger CI only on `pull_request` targeting `main`. Only `pdomain-ui` also
triggers on `push: main`. This means direct ff-only merges (the workspace's canonical
merge model — worktree → rebase → ff push) receive no CI in GitHub for 11 of 12 repos.

### 2c. Concurrency groups

| Repo | Concurrency group | cancel-in-progress |
|---|---|---|
| pdomain-ui | `ci-${{ github.ref }}` | true |
| pdomain-ocr-labeler-spa | `ci-${{ github.ref }}` | true |
| pdomain-index-npm (regen.yml only) | `pdomain-index-npm-pages` | false |
| all others | none | — |

Ten repos have no concurrency group — stale PR runs are not cancelled on force-push.

### 2d. Caching

| Repo | Cache used |
|---|---|
| pdomain-ops, pdomain-ocr-training | `actions/cache` on `~/.cache/uv` keyed on pyproject.toml |
| pdomain-ui (release.yml only) | pnpm cache via `actions/setup-node cache: pnpm` |
| pdomain-prep-for-pgdp (release.yml only) | pnpm cache via `actions/setup-node cache: pnpm` |
| all others | none |

Most repos re-install all deps cold on every CI run. uv's warmup is fast but pnpm
installs on SPAs (~30 s) add real latency per PR.

### 2e. SHA pinning consistency

All repos SHA-pin every action with inline version comments. All have
`scripts/update_github_actions.py` (added 2026-05-31) and `dep-refresh.yml` to keep
pins current weekly. This is uniform and mature across all 12.

---

## 3. Most advanced CI workflows

Ranked by depth of validation and engineering sophistication.

### Tier 1 — most advanced

**pdomain-ocr-labeler-spa**
- Build-once reuse: SPA dist is built once in `test-frontend`, uploaded as a
  run artifact, then downloaded by `test-e2e`, `build-wheel`, and `openapi-drift` —
  no double-building.
- `openapi-drift` job: regenerates `openapi.json` + `types.ts` and fails the PR if
  they diverge from what is committed. Enforces full-stack type discipline automatically.
- `build-wheel` job: asserts `static/index.html` is present inside the wheel zip via
  `python -m zipfile -l` — catches the "empty SPA wheel" failure mode before release.
- SPA artifact retained for 7 days (vs 1 day elsewhere) for post-merge debugging.
- `test-e2e` is soft (`continue-on-error: true`) with a documented pending fix.

**pdomain-ui**
- 4-way Vitest test sharding: `unit-test` matrix `1/4 2/4 3/4 4/4` with `fail-fast: false`.
- `release.yml` uses SLSA provenance attestation (`actions/attest-build-provenance`,
  `id-token: write`, `attestations: write`) — the only repo in the workspace with
  supply-chain provenance on published artifacts.
- Strictest release security: `persist-credentials: false` on build job, zero default
  workflow permissions, `publish` job gets `contents: write` only.
- `codegen-check` and `theme-check` excluded from GitHub CI with documented rationale
  (self-hosted index unavailable on GitHub runners).

**pdomain-book-tools**
- 6 parallel jobs including an informational `layout-fork` job that checks drift against
  the upstream HuggingFace PP-DocLayout model — never fails CI but surfaces drift
  continuously.
- Full 3-Python matrix (3.11/3.12/3.13) on the test job with `fail-fast: false`.
- `release.yml` patches `failOnWarnings = true` → `false` before running `ci-slow`,
  implementing a two-tier typecheck gate (dev: warnings as errors; release: errors only).

### Tier 2 — mature and comprehensive

**pdomain-ocr-cli**
- 100% test coverage enforced on both fast (`COV_FAIL_UNDER=100`) and slow
  (`COV_FAIL_UNDER_SLOW=100`) suites.
- `wheel-smoke` target verifies the built wheel installs and runs `pd-ocr --version` in
  isolated temp venvs on 3.11, 3.12, and 3.13.
- `check-release-deps` target fails if any path-sourced sibling dep is present in
  `pyproject.toml`, preventing accidental publication of development-mode wheels.
- `release-ci` and `publish` jobs both check out the tagged commit with
  `persist-credentials: false` and `fetch-depth: 0`.

**pdomain-ocr-simple-gui**
- 4-tier E2E pyramid: `test` (unit, `-n auto`), `e2e-fast` (fake dispatcher + chromium,
  in `make ci`), `e2e-browser` (full Playwright), `e2e-real-ocr` (GPU, opt-in only).
- `behavior-coverage` Make target cross-references declared behavior IDs against cited
  test IDs, enforcing the behavior-E2E coverage matrix. Included in `make ci`.
- pnpm-workspace.yaml mutation guard in `frontend-install`: snapshots, diffs, and
  restores after `pnpm install` to catch unauthorized `allowBuilds:` drift.

**pdomain-ocr-trainer-spa**
- `nightly.yml` with a `jdx/mise-action` and `actions/github-script` that auto-files a
  draft GH Issue titled `[nightly] slow tests failed <date>` with label
  `nightly-failure` — no manual monitoring needed for overnight failures.
- `doctor` Make target prints full environment diagnostics: Python version, Node
  presence, CUDA/MPS torch status, HF token presence.
- `ci-full` / `ci-slow` targets include `e2e` (Playwright) + `build` in the
  pre-release gate; the PR `ci` target intentionally excludes these for speed.

### Tier 3 — solid standard pattern

`pdomain-ops`, `pdomain-ocr-training`, `pdomain-ocr-synth`, `pdomain-prep-for-pgdp`,
`pdomain-ocr-trainer-spa`: single-job `ci` with matrix or single Python version.
Correct SHA pinning, minimal permissions, standard `do-release.sh` dispatch pattern.

### Index repos

**pdomain-index-pip / pdomain-index-npm** — structurally different from the library
and SPA repos. Their `regen.yml` is the most event-driven workflow in the workspace:

```
repository_dispatch pd-release-published / pd-npm-publish
    → immediate index rebuild (real-time)
daily schedule
    → safety-net rebuild
workflow_call from release.yml
    → rebuild after this repo's own release
workflow_dispatch
    → manual trigger
```

The `regen.yml` concurrency group `pages` / `cancel-in-progress: false` is the correct
GitHub Pages pattern — queues deploys, never kills an in-flight one.

---

## 4. Most useful patterns (worth copying / standardising)

### 4a. AI=1 Makefile log-capture shim

Present in all Python repos. Intercepts every Make goal when `AI=1` is set,
tees output to `.ci-ai.log`, prints `✅ passed` or filtered failure lines via
`scripts/ai-filter-log.py`. Enables agent-driven CI with a clean signal.

```makefile
ifdef AI
%:
    @$(MAKE) $@ 2>&1 | tee .ci-ai.log; ...
else
# normal targets
endif
```

### 4b. dep-refresh automation

Now in all 12 repos (2026-05-31). One workflow covers:
- GitHub Actions SHA pin refresh (`scripts/update_github_actions.py`)
- Python lockfile (`uv lock --upgrade`)
- npm/pnpm deps (conditional on `frontend/package.json` or root `package.json`)

Auto-merges via `gh pr merge --auto --rebase` when CI passes. Prevents the most common
cause of security drift (stale action SHAs) with zero manual effort.

### 4c. do-release.sh + dispatch-only release.yml

Local `scripts/do-release.sh` enforces:
1. Clean repo state (no uncommitted changes, on `main`)
2. `make ci-slow` as pre-flight
3. Semver bump + annotated tag
4. Push main + tag
5. `gh workflow run release.yml` with the tag input

The GitHub workflow then re-validates at the pinned tag before publishing. Two
independent gates. No risk of tagging a broken state.

### 4d. pd-index dispatch with graceful fallback

In every `release.yml`:

```yaml
- name: Notify pd-index
  run: |
    gh api -X POST /repos/pdomain/pdomain-index-pip/dispatches \
      -f event_type=pd-release-published || echo "::warning::index dispatch skipped"
  env:
    GH_TOKEN: ${{ secrets.PDOMAIN_INDEX_DISPATCH }}
```

Non-fatal if secret absent — the index's daily cron is the fallback. New forks or
repos without the secret never break the release pipeline.

### 4e. Build-once artifact reuse (pdomain-ocr-labeler-spa)

SPA build happens in one job, artifact uploaded, reused by three downstream jobs.
Eliminates `pnpm install + vite build` repetition on every CI run that needs the SPA.

### 4f. openapi-drift gate (labeler-spa, prep-for-pgdp)

After building the SPA, regenerate `openapi.json` and `types.gen.ts`, then:

```bash
git diff --exit-code frontend/src/api/types.ts frontend/openapi.json
```

Fails the PR if the generated types drifted from what is committed. Enforces
full-stack API contract discipline without a separate codegen CI step.

### 4g. SLSA provenance attestation (pdomain-ui)

```yaml
- uses: actions/attest-build-provenance@...
```

Only repo in the workspace with cryptographic build provenance. Worth propagating
to the other SPA repos and library wheels over time.

---

## 5. Differences and inconsistencies

### 5a. Python version in dep-refresh.yml

All repos use `uv python install 3.12` in `dep-refresh.yml` but their CI runs on
3.11, 3.12, or 3.13 depending on the repo. The lockfile upgrade runs on a different
Python than CI validates against. Low risk for pure lockfile upgrades but worth aligning.

**Recommendation:** change `dep-refresh.yml` to use whatever `UV_PYTHON` the repo's
`ci.yml` uses.

### 5b. uv version pinning inconsistency

| Workflow | uv version |
|---|---|
| `ci.yml` in most repos | `version: latest` (floating) |
| `dep-refresh.yml` all repos | `version: "0.11.16"` (pinned) |
| `release.yml` all repos | `version: "0.11.16"` (pinned) |
| `ci.yml` in pdomain-ops, pdomain-ocr-training | no explicit version |

Release and dep-refresh pin uv; PR CI floats. A uv update could silently change
resolver behaviour between a PR and its release.

**Recommendation:** pin uv in `ci.yml` across all repos. dep-refresh keeps it
current automatically.

### 5c. pnpm setup method

| Repo | CI method | Release method |
|---|---|---|
| pdomain-ui | `corepack enable` (floating latest) | `pnpm/action-setup@... version: "11"` |
| pdomain-ocr-labeler-spa | `pnpm/action-setup@... version: 11` | same |
| pdomain-prep-for-pgdp | `corepack prepare pnpm@11.3.0` (pinned) | `pnpm/action-setup@... version: "11"` |
| pdomain-ocr-trainer-spa | `corepack enable` | `pnpm/action-setup@...` |
| pdomain-ocr-simple-gui | `pnpm/action-setup@...` (in ci.yml) | same |

No repo uses the same method across all three workflows. Three different approaches
(corepack float, corepack pin, action-setup) on the same repo is common.

**Recommendation:** standardise on `pnpm/action-setup` with a pinned version in all
workflows. Add `pnpm/action-setup` to `MANAGED_ACTIONS` in `update_github_actions.py`.

### 5d. Makefile deprecated alias density

The following deprecated aliases exist in multiple repos — printed warnings but still
functional:

| Deprecated target | Canonical replacement | Repos |
|---|---|---|
| `dev-local` | `local-dev` | most Python repos |
| `upgrade-pdomain-book-tools` | `update-pd-deps` | pdomain-ocr-cli, pdomain-prep-for-pgdp |
| `upgrade-deps-local` | `local-upgrade-deps` | pdomain-ocr-labeler-spa, others |
| `install-local` | `local-install` | pdomain-ocr-cli, pdomain-prep-for-pgdp |
| `uninstall-local` | `local-uninstall` | same |
| `check-local-editable` | `local-check` | same |
| `run-local` | `local-run` | same |
| `reset-venv` | `reset` | several repos |
| `format-check` | `lint-check` | pdomain-ops and others |
| `test-verbose` | `test` (identical) | pdomain-book-tools, pdomain-ocr-synth |

### 5e. `ci-slow` is a no-op alias in most repos

In pdomain-book-tools, pdomain-ops, pdomain-ocr-training, pdomain-ocr-synth,
pdomain-index-pip, pdomain-index-npm: `ci-slow` is declared as an alias for `ci`
with a comment "reserved for slower checks if added later."

The release.yml calls `make ci-slow` in `release-ci`, implying a stricter gate.
Currently it provides no extra validation beyond `make ci`.

**Exception:** pdomain-ocr-cli has a genuine `ci-slow` (includes `coverage-slow`
with `--run-slow`). pdomain-ocr-simple-gui and pdomain-ocr-labeler-spa have
`ci-slow` that adds `build` + E2E. pdomain-ocr-trainer-spa's `ci-slow` aliases
`ci-full` which includes `e2e` and `build`.

---

## 6. Legacy items flagged for cleanup

### 6a. Deprecated Make aliases — safe to remove after one more release cycle

These exist across repos, print deprecation warnings, and delegate to canonical targets.
Once all CLAUDE.md and agent prompt references are updated they can be deleted:

- `dev-local` → `local-dev`
- `upgrade-pdomain-book-tools` → `update-pd-deps`
- `upgrade-deps-local` → `local-upgrade-deps`
- `install-local`, `uninstall-local`, `check-local-editable`, `run-local` → `local-*`
- `reset-venv` → `reset`
- `format-check` (where it is a pure alias) → `lint-check`

### 6b. `_require_peer_book_tools` in pdomain-prep-for-pgdp Makefile

A helper defined at the top of the Makefile but not called by any visible target.
Leftover from before the `local-*` script delegation pattern. Safe to delete.

### 6c. `test-verbose` duplicating `test`

In pdomain-book-tools and pdomain-ocr-synth, `test-verbose` is documented separately
but runs the identical `pytest -n auto -v -ra` command. Not deprecated, but a dead
alias. Remove or differentiate.

### 6d. `PEER_BOOK_TOOLS_PATH` / `PEER_BOOK_TOOLS_REPO` vars in pdomain-prep-for-pgdp

Defined at the top of the Makefile, used by `_require_peer_book_tools`. Since that
helper is not called anywhere, these vars are dead. Remove with it.

### 6e. Hardcoded `pdomain` org links in pdomain-index-npm landing page

`regen.yml` writes a GitHub org URL pointing to `https://github.com/pdomain` in the
generated landing page. The actual org is `pdomain` (confirmed — all repos are under
the `pdomain` GitHub org), so this is correct. However, it conflicts with references
in other workflow files using `pdomain/pdomain-index-pip` that some audit notes flagged
as `ConcaveTrillion`. Those workflow references are also correct (`pdomain/` org).

**No action needed** — the `pdomain/` org references are accurate.

---

## 7. Coverage of `make ci` across repos

What `make ci` actually covers per repo:

| Repo | pre-commit | lint | typecheck | test | build | E2E | coverage | other |
|---|---|---|---|---|---|---|---|---|
| pdomain-book-tools | ✓ | ✓ | ✓ | ✓ (xdist) | ✓ | — | — | layout-fork-info |
| pdomain-ocr-cli | ✓ | ✓ | ✓ | ✓ (100%) | ✓ | — | 100% enforced | installer-test, wheel-smoke |
| pdomain-ops | ✓ | ✓ | ✓ | ✓ (xdist) | — | — | — | — |
| pdomain-ocr-training | ✓ | ✓ | ✓ | ✓ (xdist) | — | — | — | — |
| pdomain-ocr-synth | ✓ | ✓ | ✓ | ✓ (xdist) | ✓ | — | — | — |
| pdomain-ui | — | ✓ | ✓ | ✓ (vitest) | ✓ | — | — | codegen-check, theme-check |
| pdomain-ocr-simple-gui | ✓ | ✓ | ✓ | ✓ (xdist) | — | — | — | behavior-coverage, e2e-fast, frontend-* |
| pdomain-ocr-labeler-spa | ✓ | ✓ | ✓ | ✓ (xdist) | — | partial (e2e soft) | — | openapi-export, frontend-*, knip |
| pdomain-ocr-trainer-spa | — | ✓ | ✓ | ✓ (xdist) | — | — | — | frontend-*, knip |
| pdomain-prep-for-pgdp | ✓ | ✓ | ✓ | ✓ (xdist) | — | — | — | openapi-export, frontend-*, knip |
| pdomain-index-pip | ✓ | ✓ | — | ✓ | — | — | — | actionlint, shell-check |
| pdomain-index-npm | ✓ | ✓ | ✓ | ✓ | — | — | — | actionlint, shell-check |

Notable: `pdomain-index-pip` and `pdomain-index-npm` include `actionlint` and
`shellcheck` in `make ci` — no other repo does. Worth propagating to repos that
ship workflow files.

---

## 8. Makefile richness ranking

Repos with the most complete and feature-rich Makefiles:

1. **pdomain-ocr-labeler-spa** — Docker targets, full mise integration, pip-audit
   targets, 4-tier E2E (`test`, `e2e`, `exercise-real`, `integration`), all
   `local-frontend-*` variants, `openapi-export`, `behavior-coverage`.

2. **pdomain-ocr-simple-gui** — behavior-coverage gate, 4-tier E2E pyramid,
   `local-frontend-*` variants, `run`/`run-cpu` GPU switching, `openapi-export`,
   pnpm-workspace.yaml mutation guard.

3. **pdomain-prep-for-pgdp** — Docker targets (`docker-build`, `docker-run`),
   `run`/`run-cpu` targets, full `local-*` suite (10 targets), `mise-*` toolchain
   management, `openapi-export`.

4. **pdomain-ocr-trainer-spa** — `doctor` target for environment diagnostics, split
   `dev`/`dev-backend`/`dev-frontend` concurrently managed dev server, mise-trust
   for bot-workspaces, `openapi-export`.

5. **pdomain-book-tools** — 6 layout-fork management targets (with shell-injection
   guards on user-supplied Make vars), GPU auto-detection in `setup`, `sync-gpu`,
   `ci-slow` as genuine additional gate, AI=1 shim.

6. **pdomain-ocr-cli** — `wheel-smoke` across 3 Python versions, `check-release-deps`,
   `installer-test` suite, `coverage`/`coverage-slow` with enforced 100% threshold.

7. **pdomain-ui** — Storybook build/e2e, `codegen`/`codegen-check`/`theme-check`,
   `update-pd-deps` (codegen.versions.json variant), mise integration with fallback.

8. **pdomain-index-pip** — `actionlint`/`shellcheck` (unique in workspace), `smoke-regen`
   safety pattern, `regen` with `OUT` override, distinct `static-check` vs `ci` split.

9. **pdomain-index-npm** — same `static-check` split, TypeScript repo pattern,
   `regen-index` + `smoke`, `release.yml` calls `regen.yml` via workflow_call.

10. **pdomain-ops, pdomain-ocr-training, pdomain-ocr-synth, pdomain-ocr-trainer-spa**
    — standard pattern: setup/lint/typecheck/test/ci/build/release + local-dev suite.

---

## 9. Cross-cutting recommendations

| Priority | Recommendation | Repos affected |
|---|---|---|
| High | Pin uv version in `ci.yml` (match `0.11.16` used in dep-refresh/release) | all 10 Python repos |
| High | Standardise pnpm setup on `pnpm/action-setup` + pinned version; add to MANAGED_ACTIONS | 5 SPA repos |
| High | Add concurrency groups to `ci.yml` (`cancel-in-progress: true`) | 10 repos |
| Medium | Align dep-refresh Python version with each repo's `UV_PYTHON` | all 12 |
| Medium | Remove deprecated Make aliases after one cycle | most repos |
| Medium | Add `actionlint` + `shellcheck` to `make ci` for repos with workflow files | 10 product repos |
| Medium | Make `ci-slow` genuinely slower than `ci` (or remove the distinction) | pdomain-ops, pdomain-ocr-training, pdomain-ocr-synth, pdomain-index-* |
| Low | Add uv/pnpm cache to `ci.yml` for fast PR feedback | all repos |
| Low | Add `push: main` trigger to CI so ff-merge pushes get CI coverage | 11 repos (not pdomain-ui) |
| Low | Remove `test-verbose` dead alias | pdomain-book-tools, pdomain-ocr-synth |
| Future | Propagate SLSA provenance attestation from pdomain-ui to other SPA repos | 4 SPA repos |
| Future | Propagate `nightly.yml` auto-issue-filing pattern from pdomain-ocr-trainer-spa | repos with slow tests |
| Future | Propagate `behavior-coverage` Make target from pdomain-ocr-simple-gui | SPA repos with E2E |
