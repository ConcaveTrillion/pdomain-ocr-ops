---
Status: active
Owner: CT
Created: 2026-08-08
Last verified: 2026-08-08
Kind: issue
Level: I1
---

# Weekly dep-refresh cannot auto-land in this repo

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-08-08
- **Resolution:** Open
- **Issue type:** Bug
- **Priority:** P1
- **Area:** Cross-cutting
- **Triage:** Accepted
- **Affected version:** `pdomain-ops` v0.11.2 (commit `aacc127`)
- **Parent:** None
- **Children:** None
- **Blocked by:** None
- **Blocks:** None
- **Read when:** investigating why a pull request to `master` will not merge,
  why `dep-refresh` PRs pile up, or before editing branch protection,
  `.github/workflows/ci.yml`, or `.github/workflows/dep-refresh.yml`.
- **Search terms:** dep-refresh, auto-merge, branch protection, required
  status checks, pd-ocr-ops CI, delete_branch_on_merge, stray branches,
  admin bypass, gh pr merge --auto.
- **Relates to:** design at `pdomain-ui:docs/specs/2026-07-16-dep-refresh-auto-land-design.md`
  (different repo; not a governed link in this graph).

## Summary

The weekly `dep-refresh` workflow runs correctly and produces correct
dependency updates, but two independent defects stop any pull request to
`master` — dep-refresh or otherwise — from landing itself, and they compound.
Master branch protection requires three status contexts that this repo's CI
no longer produces (a naming leftover from the `pd-ocr-ops` → `pdomain-ops`
rename), so every PR sits with required checks stuck "expected" forever.
Separately, `dep-refresh` creates a fresh dated branch each run with no
cleanup, so failed weeks accumulate as stray branches and open PRs. The
sibling repo `pdomain-ui` diagnosed the same shape of failure and designed a
fix; this report adapts that design to what is actually broken here.

## Outcome / acceptance criteria

- Master branch protection's required status contexts match check names this
  repo's `ci` workflow actually produces, so a green PR can merge without an
  admin bypass.
- `dep-refresh` reuses a single `dep-refresh` branch (force-pushed from a
  fresh `master` each run) instead of a new dated branch per run, and opens a
  PR only when no open one already exists for it.
- `delete_branch_on_merge` is `true` on this repo, so a merged `dep-refresh`
  branch is deleted automatically.
- A green weekly refresh merges and cleans up its branch with no human
  action; a red refresh leaves exactly one open PR and one branch for the
  next run to reuse, not a new pair.

## Evidence / motivation

Lead observation: no pull request has merged into `pdomain-ops` master since
`#79` on 2026-05-23. Every PR opened since, including all three open
`dep-refresh` PRs, shows required checks permanently pending.

### Defect A — required status contexts name a workflow that no longer exists

```console
$ gh api repos/pdomain/pdomain-ops/branches/master/protection --jq '.required_status_checks.contexts'
["pd-ocr-ops CI (3.11)","pd-ocr-ops CI (3.12)","pd-ocr-ops CI (3.13)"]
```

`.github/workflows/ci.yml` is named `ci` and its jobs are `pre-commit`,
`lint`, `typecheck`, `test` (matrix `py3.11`/`py3.12`/`py3.13`), and `build`.
Checking the actual check-runs on open PR `#87`'s head commit confirms
nothing produces the required names:

```console
$ gh api repos/pdomain/pdomain-ops/commits/<head-sha>/check-runs --jq '.check_runs[] | .name'
test / py3.13
test / py3.11
test / py3.12
lint
pre-commit
build
typecheck
```

`pd-ocr-ops CI (3.11/3.12/3.13)` never appears. The names are a leftover
from before this repo was renamed from `pd-ocr-ops` to `pdomain-ops`. With
`enforce_admins: false` confirmed on the branch, the three required
contexts stay "expected" indefinitely for every PR, green or not, and
nothing but an admin bypass can land a change.

### Defect B — dated branches and PRs accumulate with no cleanup

```console
$ gh api repos/pdomain/pdomain-ops/branches?per_page=100 --jq '.[].name' | grep dep-refresh
dep-refresh/2026-06-21-27896543113
dep-refresh/2026-06-28-28313702493
dep-refresh/2026-07-05-28731581958
dep-refresh/2026-07-12-29181320446
dep-refresh/2026-07-19-29674848893
dep-refresh/2026-07-26-30189638743
dep-refresh/2026-08-02-30734276004
```

Seven stray `dep-refresh` branches on origin, three of them with open PRs:

```console
$ gh pr list --repo pdomain/pdomain-ops --search "dep-refresh" --state all --json number,createdAt,state,headRefName
#87  OPEN    2026-08-02
#86  OPEN    2026-07-26
#85  OPEN    2026-07-19
#84  CLOSED  2026-07-12
#83  CLOSED  2026-07-12
#82  CLOSED  2026-06-28
#81  CLOSED  2026-06-21
```

`.github/workflows/dep-refresh.yml` builds
`BRANCH="dep-refresh/$(date +%Y-%m-%d)-$GITHUB_RUN_ID"` — a new branch name
every run — and:

```console
$ gh api repos/pdomain/pdomain-ops --jq '.delete_branch_on_merge'
false
```

Nothing ever deletes a stale branch or supersedes a stale PR, so failed
weeks pile up independently of defect A. (Checking the three open PRs'
checks shows each has at least one genuine `pre-commit` or `lint` failure of
its own — `pre-commit` fails on all three, `lint` fails on `#86` and `#87` —
so these particular PRs are not simply "green but stuck"; defect B would
still leave them unmerged and un-cleaned-up even after defect A is fixed,
until a refresh lands clean.)

## Dependencies

- None to start Defect A or Defect B individually; see rollout note under
  Next steps for the order the fix must land in.

## Next steps

1. Follow the design at
   `pdomain-ui:docs/specs/2026-07-16-dep-refresh-auto-land-design.md`,
   section B ("One reusable branch") and section C ("Enable delete-on-merge"),
   applied to this repo: replace the dated branch in
   `.github/workflows/dep-refresh.yml` with one reusable `dep-refresh` branch
   force-pushed from a fresh `master` each run, open a PR only when no open
   one exists for it, re-arm `gh pr merge --auto --rebase`, and set
   `delete_branch_on_merge: true` on `pdomain/pdomain-ops`.
2. Additionally, specific to this repo: correct master branch protection's
   required status contexts from `pd-ocr-ops CI (3.11/3.12/3.13)` to names
   this repo's `ci` workflow actually produces (for example the `pre-commit`,
   `lint`, `typecheck`, `test / py3.11`, `test / py3.12`, `test / py3.13`,
   and `build` check names already observed on open PRs). Fixing branch
   churn alone will not make PRs land here while this defect stands.
3. Rollout order, per the spec's rollout note: a change to required checks
   cannot satisfy its own new gate, so the PR that corrects the required
   contexts needs an admin bypass to land (the owner has admin;
   `enforce_admins` is off here too). After that PR lands, subsequent PRs —
   including dep-refresh — gate on the real checks.
4. Close out the seven stray branches and three open dep-refresh PRs
   (`#85`, `#86`, `#87`) once a clean refresh can land under the fixed
   branch, or fold that cleanup into whichever PR implements Next step 1.

## Environment / versions

```text
pdomain-ops v0.11.2 (commit aacc127), branch master
.github/workflows/ci.yml (job id "ci"; jobs: pre-commit, lint, typecheck, test [3.11/3.12/3.13 matrix], build)
.github/workflows/dep-refresh.yml (schedule: Sunday 02:00 UTC; workflow_dispatch)
GitHub API observations taken 2026-08-08 via gh CLI against pdomain/pdomain-ops
```

## Evidence — reproduction & diagnosis

### 1. Required contexts do not match any produced check name

```console
$ gh api repos/pdomain/pdomain-ops/branches/master/protection --jq '.required_status_checks.contexts'
["pd-ocr-ops CI (3.11)","pd-ocr-ops CI (3.12)","pd-ocr-ops CI (3.13)"]
```

Compare against `.github/workflows/ci.yml`'s job names (`pre-commit`,
`lint`, `typecheck`, `test / py<version>`, `build`) and the check-runs
actually posted to a live PR head commit (`#87`, shown above under Defect
A) — no overlap. Every PR's required checks stay pending indefinitely.

### 2. No PR has merged since the rename-era contexts went stale

```console
$ gh pr list --repo pdomain/pdomain-ops --state merged --limit 5 --json number,title,mergedAt
[{"number":79,"title":"chore: drop reportMissingTypeStubs ignores; pin pd-book-tools >=0.14.0","mergedAt":"2026-05-23T00:28:49Z"}]
```

Only one merge is on record and it predates the current run of stuck PRs
(`#81`–`#87`), consistent with the required-context gap blocking every PR
opened since, not just `dep-refresh` PRs.

### 3. Branch and PR counts for defect B

Seven stray `dep-refresh/*` branches and three open `dep-refresh` PRs
(`#85`, `#86`, `#87`), shown in full under Defect B above, with
`delete_branch_on_merge: false` confirmed on the repo.

## Root-cause hypotheses (ranked)

1. **(Confirmed) Stale required-context names from the `pd-ocr-ops` →
   `pdomain-ops` rename.** Branch protection was never updated when the CI
   workflow was renamed and restructured; the three required contexts name a
   workflow shape (`pd-ocr-ops CI (3.x)`) that no longer exists, so
   `strict`-mode required checks stay "expected" forever regardless of
   whether the PR is actually green. This is the more serious of the two
   defects because it blocks all PRs to master, not only dep-refresh.
2. **(Confirmed) No branch or PR reuse in dep-refresh.yml.** The dated
   branch name plus `delete_branch_on_merge: false` guarantees a new stray
   branch (and, if changes exist, a new open PR) every week a refresh runs,
   with nothing to consolidate or clean them up. Independent of defect A;
   compounds with it because even a hypothetically green dep-refresh PR
   would still leave a growing pile of superseded branches and PRs behind
   it.

## Defects to fix

1. **Master branch protection required status contexts name a nonexistent
   workflow** (`pd-ocr-ops CI (3.11/3.12/3.13)` vs. the `ci` workflow's
   `pre-commit` / `lint` / `typecheck` / `test / py3.1x` / `build`).
   (Primary — blocks all merges to master.)
2. **`dep-refresh.yml` creates a new dated branch every run with no
   consolidation, and `delete_branch_on_merge` is `false`** — nothing
   supersedes or cleans up a prior week's branch or PR.

## What is NOT broken (to scope the fix)

- **The dep-refresh workflow's dependency-update logic itself.** It runs on
  schedule, correctly refreshes GitHub Actions SHA pins and Python/npm
  dependencies, and produces real, mergeable-shape diffs. The problem is
  landing the resulting PRs, not generating them.
- **The individual CI jobs.** `pre-commit`, `lint`, `typecheck`, `test`, and
  `build` all run and report pass/fail correctly per PR (see the check-run
  listings for `#85`–`#87` above); they are simply never consulted by branch
  protection because their names don't match the required contexts.
- **`enforce_admins`.** Already `false`, so the rollout path (admin bypass
  for the PR that fixes the required contexts) is available without a
  settings change.
- **The `dep-refresh` workflow's auto-merge arming.** `gh pr merge --auto
  --rebase` is already called at the end of a successful refresh run; it has
  nothing to act on because the required checks never resolve.

## Resolution

*Open.* When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit link here, move the README pointer, and route the
retirement through `doc-retirer`.
