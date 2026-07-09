---
title: dep-refresh GitHub Action — automated weekly dep and actions-pin refresh
date: 2026-05-31
status: ready-for-review
---

# dep-refresh GitHub Action

## 1. Context

The ten active pdomain-* repos each carry two categories of dependency that
drift over time:

- **GitHub Actions pins** — SHA-pinned refs like
  `actions/checkout@<sha>  # v4` that must be refreshed to pick up upstream
  security patches and new features.
- **Python and npm deps** — `uv.lock` and `pnpm-lock.yaml` that fall behind
  as PyPI and npm publish new versions.

Today both are refreshed manually. The `oxipng-pybind` repo already has a
local `scripts/update_github_actions.py` that resolves the latest SHA for a
managed set of actions; the pdomain repos have nothing equivalent. Each repo
has a `make upgrade-deps` target (`uv lock --upgrade`) for Python deps, and
the four SPA repos have a `frontend/` directory with npm deps that also need
periodic updates.

This spec describes a scheduled GitHub Action that automates both refreshes
weekly, lands each as a PR with auto-merge armed, and keeps all per-repo
copies of the shared script in sync via `repo-hygiene-check.sh`.

## 2. Goals

- **Automated weekly refresh** of GitHub Actions SHA pins and all Python/npm
  deps across all ten active pdomain-* repos.
- **Per-repo PRs** — one PR per repo per run, auto-merged when CI passes.
- **Per-repo workflows** — each repo owns its `dep-refresh.yml`; no runtime
  cross-repo file fetching.
- **Manual override** — `workflow_dispatch` on the orchestrator to target one
  repo or all repos on demand.
- **Drift detection** — `repo-hygiene-check.sh` flags repos where
  `scripts/update_github_actions.py` or `.github/workflows/dep-refresh.yml`
  has diverged from the reference repo.

## 3. Non-goals

- Bumping pd-* sibling deps only (`update-pd-deps`) — this spec uses the
  broader `make upgrade-deps` (`uv lock --upgrade`) which covers all deps
  including siblings.
- Retiring repos (`pd-ocr-labeler`, `pd-ocr-trainer`) — excluded from the
  repo list entirely.
- `oxipng-pybind` / `pd-png-optimizer` — `pd-` prefix repos; out of scope
  for this spec.
- Auto-committing or force-pushing to `main` — all changes land via PR.
- Replacing the `update-pd-deps` plan (#363) — that plan's per-repo
  `make update-pd-deps` target is narrower and orthogonal to this spec.

## 4. Architecture

Two layers — no central orchestrator:

### 4.1 Per-repo workflow

`.github/workflows/dep-refresh.yml` in each of the twelve pdomain repos.

- Triggered by `schedule` (weekly cron, Sunday 02:00 UTC) and by
  `workflow_dispatch` for on-demand runs against a single repo.
- Fully self-contained — uses only `GITHUB_TOKEN`, no cross-repo auth,
  no central dispatcher, no PAT.
- Identical across all repos; repo-specific behaviour comes from the
  Makefile targets and presence/absence of `frontend/package.json`.
- All twelve repos fire independently on the same cron. To refresh a
  single repo on demand, use `workflow_dispatch` on that repo directly.

### 4.2 Per-repo action-pin script

`scripts/update_github_actions.py` in each pdomain repo.

- Copied from the oxipng-pybind reference with Rust-specific handling
  removed and a pdomain-relevant managed-actions list.
- Per-repo copy — no runtime fetch from a central location.
- `repo-hygiene-check.sh` detects drift against the reference repo.

## 5. Active repo list

| Repo | Has frontend/ | Has root package.json | Notes |
|---|---|---|---|
| pdomain-book-tools | — | — | |
| pdomain-ocr-cli | — | — | |
| pdomain-ops | — | — | |
| pdomain-ocr-training | — | — | |
| pdomain-ocr-synth | — | — | |
| pdomain-ui | — | ✓ (pnpm) | |
| pdomain-ocr-simple-gui | ✓ | — | |
| pdomain-ocr-labeler-spa | ✓ | — | |
| pdomain-ocr-trainer-spa | ✓ | — | |
| pdomain-prep-for-pgdp | ✓ | — | |
| pdomain-index-pip | — | — | |
| pdomain-index-npm | — | ✓ (npm, not pnpm) | needs `upgrade-deps` Makefile target added |

## 6. Cadence model

Each repo runs its own weekly cron independently. To refresh a single
repo on demand, use `workflow_dispatch` directly on that repo. No
central orchestrator — each repo is fully autonomous.

## 7. Per-repo dep-refresh workflow

```yaml
name: dep-refresh

on:
  schedule:
    - cron: '0 2 * * 0'   # Sunday 02:00 UTC
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<sha>  # pinned — updated by this workflow itself

      - uses: astral-sh/setup-uv@<sha>
        with:
          version: "0.11.16"

      - name: Set up Python
        run: uv python install 3.12

      - name: Set up pnpm or npm (repos with a package.json)
        if: hashFiles('frontend/package.json') != '' || hashFiles('package.json') != ''
        run: corepack enable

      - name: Refresh GitHub Actions SHA pins
        run: uv run python scripts/update_github_actions.py
        env:
          GH_TOKEN: ${{ github.token }}

      - name: Upgrade all Python deps
        run: make upgrade-deps

      - name: Upgrade frontend npm deps (SPA repos)
        if: hashFiles('frontend/package.json') != ''
        run: pnpm update --dir frontend

      - name: Upgrade root npm deps
        if: hashFiles('package.json') != '' && hashFiles('frontend/package.json') == ''
        run: |
          # pdomain-ui uses pnpm; pdomain-index-npm uses npm
          if [ -f pnpm-lock.yaml ]; then pnpm update; else npm update; fi

      - name: Check for changes
        id: changes
        run: |
          git diff --quiet && echo "changed=false" >> "$GITHUB_OUTPUT" \
            || echo "changed=true" >> "$GITHUB_OUTPUT"

      - name: Create branch, commit, and open PR
        if: steps.changes.outputs.changed == 'true'
        run: |
          BRANCH="dep-refresh/$(date +%Y-%m-%d)"
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git checkout -b "$BRANCH"
          git add -A
          git commit -m "chore: weekly dep refresh (actions pins + all deps)"
          git push origin "$BRANCH"
          gh pr create \
            --title "chore: weekly dep refresh" \
            --body "$(printf 'Automated weekly refresh:\n- GitHub Actions SHA pins\n- Python deps (uv lock --upgrade)\n- npm deps (pnpm update)\n\nAuto-merge armed — will merge when CI passes.')" \
            --base main \
            --head "$BRANCH" \
            --label dep-refresh
          gh pr merge --auto --rebase
        env:
          GH_TOKEN: ${{ github.token }}
```

## 9. `update_github_actions.py` — pdomain variant

The script is copied from `oxipng-pybind/scripts/update_github_actions.py`
with two changes:

1. **Remove Rust-specific handling** — no `dtolnay/rust-toolchain`,
   `taiki-e/install-action`, `PyO3/maturin-action`, or stable Rust
   toolchain resolution.
2. **Replace `MANAGED_ACTIONS`** with the pdomain-relevant set:

```python
MANAGED_ACTIONS = (
    "actions/checkout",
    "astral-sh/setup-uv",
    "actions/setup-python",
    "actions/upload-artifact",
    "actions/download-artifact",
    "peter-evans/create-pull-request",
)
```

SHA resolution logic is unchanged: fetch latest release via `gh api`, dereference
annotated tags to the commit SHA, write `@<sha>  # vX.Y.Z` inline.

Actions not in `MANAGED_ACTIONS` that appear in workflow files are left
unchanged. Actions in `MANAGED_ACTIONS` not found in any workflow file are
silently skipped.

## 10. Branch protection and auto-merge safety

**Repo setting:** "Allow auto-merge" enabled on each pdomain repo.

**Gate:** `dep-refresh.yml` is the only workflow that calls
`gh pr merge --auto --rebase`. Style-review and other bot workflows do not.
Interactive work never creates PRs (worktree → ff path per workspace
policy). So in practice only dep-refresh PRs ever have auto-merge armed.

**Branch protection rule on `main` (each pdomain repo):**
- Required status checks: the repo's existing CI jobs (pre-commit, lint,
  typecheck, test, build — whichever apply).
- No required reviewers — CT is the sole contributor; interactive merges
  go through the worktree → ff path.
- Rebase merge only (squash stays disabled per existing GitHub settings).

**CI failure behaviour:** The PR stays open, auto-merge is armed but does
not fire. CT reviews, closes, or pushes a fix to the branch. No special
workflow handling needed.

**PR label:** `dep-refresh` applied at PR creation, making the queue easy
to scan and filter.

## 11. Drift detection via `repo-hygiene-check.sh`

Two new checks added to `repo-hygiene-check.sh`:

1. `scripts/update_github_actions.py` is present in the repo.
2. Its content matches the canonical reference
   (`pdomain-book-tools/scripts/update_github_actions.py`). Reports
   `DRIFT` if any repo has diverged.

Same check applied to `.github/workflows/dep-refresh.yml`. When the
workflow template changes in the reference repo (pdomain-book-tools),
the hygiene check immediately surfaces which other repos are behind.

The reference repo (`pdomain-book-tools`) is chosen because it is the
foundational Python-only repo — its copies contain no SPA-specific
conditional steps, making it the canonical baseline.

Note: the SPA repos (pdomain-ocr-simple-gui, pdomain-ocr-labeler-spa,
pdomain-ocr-trainer-spa, pdomain-prep-for-pgdp) and pdomain-ui have
identical workflow YAML to the reference — the `hashFiles()` conditionals
handle the npm steps at runtime without any static difference in the file.

## 12. Sequencing

One prerequisite: `pdomain-index-npm` needs an `upgrade-deps` Makefile
target added (step 1 below). All other twelve repos already have it.
This spec is independent of the `update-pd-deps` plan (#363) and the
local-dev standardisation plan (#362).

Note: all twelve repos live under the `pdomain` GitHub org, not
`ConcaveTrillion`. GitHub setup steps (labels, auto-merge, branch
protection) must target `pdomain/<repo>`.

Delivery order within this plan:

1. Add `upgrade-deps` Makefile target to `pdomain-index-npm` (runs `npm update`).
2. Write `scripts/update_github_actions.py` in pdomain-book-tools
   (reference) and propagate to the other eleven repos.
3. Add `.github/workflows/dep-refresh.yml` to all twelve repos (identical
   file with schedule cron; start with pdomain-book-tools, parallel-dispatch
   the rest).
4. Create the `dep-refresh` label in each repo before the first run
   (`gh label create dep-refresh --color 0075ca --repo pdomain/<repo>`).
5. Enable "Allow auto-merge" on each repo (`pdomain/<repo>` settings).
6. Add branch protection rules to each repo if not already present.
7. Add drift checks to `repo-hygiene-check.sh`.
8. Trigger a manual run (`workflow_dispatch`) on one repo to verify end-to-end.

## 13. Risks and alternatives

- **Risk:** `gh pr merge --auto --rebase` requires the "Allow auto-merge"
  repo setting. If the setting is off, the command exits with an error and
  the workflow run turns red — CT sees it immediately. Mitigation: step 4
  above enables it before the first run; the hygiene check can verify the
  setting is on.
- **Risk:** `pnpm update` in a SPA repo may upgrade a package with a
  breaking change, causing CI to fail. Mitigation: this is the intended
  behaviour — CI is the gate; the PR stays open for review.
- **Risk:** `make upgrade-deps` refuses to run in local-dev mode (it checks
  for the marker). In the GitHub Actions runner there is no local-dev marker,
  so this is a non-issue.
- **Alternative rejected:** Composite action in `ocr-container-meta` for the
  `update_github_actions.py` script. Rejected because it creates a live
  cross-repo runtime dependency — a bad commit in the meta repo breaks all
  ten dep-refresh runs simultaneously.
- **Alternative rejected:** Dependabot. Dependabot cannot update SHA-pinned
  actions refs that use the SHA-with-comment pattern this workspace uses.
  It also cannot run `make upgrade-deps` or coordinate across repos.
