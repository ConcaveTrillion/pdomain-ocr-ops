---
title: Org-wide GitHub Actions SHA-pinning enforcement
date: 2026-06-01
repo: ConcaveTrillion/ocr-container-meta
status: active
blocked_on: oxipng-pybind dtolnay/rust-toolchain conversion + CT-supplied upstream SHA
---

# Org-wide SHA-pinning enforcement — remediation plan

**Goal:** Turn on `sha_pinning_required` for the `pdomain` org so every GitHub
Actions workflow must reference actions by full-length commit SHA, blocking
mutable tag/branch refs (e.g. `@v4`) from being silently hijacked.

**Status:** Held on 2026-06-01. The fork-PR approval half of the same hardening
pass is already shipped (see below); SHA-pinning enforcement is deferred because
enabling it now would red-CI `oxipng-pybind` until its workflows are converted.

---

## Context — what's already done

On 2026-06-01 the fork-PR approval hardening was applied across all 16 public
repos: org-level `fork-pr-contributor-approval` set to `all_external_contributors`
for the 13 `pdomain` org repos (cascades), plus per-repo for the 3 public
`ConcaveTrillion`-user repos (`tools`, `pd-ocr-labeler`, `pd-ocr-trainer`).
Outside-collaborator PRs now require maintainer approval before any workflow runs.

SHA-pinning enforcement is the remaining piece of that pass.

## Current state

- Org `sha_pinning_required` is **`false`** (`gh api orgs/pdomain/actions/permissions`).
- **12 of 13 `pdomain` org repos are already 100% SHA-pinned** — enabling
  enforcement is a no-op for them.
- **`oxipng-pybind` is the only blocker:** `dtolnay/rust-toolchain@1.95.0`
  appears in **10 places across 6 workflow files**:
  - `.github/workflows/ci.yml` — lines 26, 43, 53, 66, 85
  - `.github/workflows/wheels.yml` — lines 211, 278
  - `.github/workflows/api-matrix.yml` — line 40
  - `.github/workflows/dependency-health.yml` — line 28
  - `.github/workflows/upstream-bump.yml` — line 26

## Why it's not a simple "repin"

1. **`dtolnay/rust-toolchain` uses the git ref as the toolchain selector.**
   `@1.95.0` means "install Rust 1.95.0". SHA-pinning it requires pinning to the
   action's commit SHA **and** moving the version into a `with:` input:

   ```yaml
   - uses: dtolnay/rust-toolchain@<full-40-char-sha>  # rust-toolchain, pins 1.95.0
     with:
       toolchain: 1.95.0
       # preserve any existing components:/targets: inputs on each call site
   ```

2. **The upstream SHA cannot be fetched in-session.** The workspace
   owner-allowlist guard (`bash-command-guard.py`) blocks all `gh`/`git`/`curl`
   reads of non-`ConcaveTrillion` orgs, so `dtolnay/rust-toolchain`'s commit SHA
   must be supplied by CT (route the external lookup through CT).

## Remediation steps

- [ ] **Obtain the `dtolnay/rust-toolchain` commit SHA** to pin to (CT-supplied —
      allowlist blocks in-session lookup). Capture the SHA + the human-readable
      tag/date it corresponds to for the inline comment.
- [ ] **Convert `oxipng-pybind`'s 6 workflow files** (delegate to the
      `oxipng-pybind` agent, worktree-isolated): replace each
      `dtolnay/rust-toolchain@1.95.0` with `@<sha>` + `with: { toolchain: 1.95.0 }`,
      preserving any existing `with:` inputs (components/targets) at each call site.
- [ ] **Verify `oxipng-pybind` CI is green** (`make ci`) in the worktree, then
      land via the workspace rebase → ff-merge flow and push.
- [ ] **Enable org-wide enforcement.** Set `sha_pinning_required=true` on
      `orgs/pdomain/actions/permissions` (confirm the exact PUT endpoint/body at
      execution — it may be a dedicated sub-resource rather than the main
      permissions PUT; do not clobber `enabled_repositories`/`allowed_actions`).
- [ ] **Verify:** org GET shows `sha_pinning_required: true`, and a fresh CI run
      on `oxipng-pybind` (and one already-pinned repo) passes.

## Acceptance criteria

- `gh api orgs/pdomain/actions/permissions` → `"sha_pinning_required": true`.
- `oxipng-pybind` workflows reference `dtolnay/rust-toolchain` by SHA with a
  `toolchain:` input, and its CI is green.
- No other `pdomain` org repo regressed (they were already pinned).

## Related

- `docs/plans/2026-05-31-dep-refresh-github-action.md` — automated weekly refresh
  of existing Actions SHA pins + deps. Complementary: that plan keeps pins fresh;
  this plan enforces that they exist. Once enforcement is on, the dep-refresh
  bot's PRs must keep producing SHA-pinned diffs (it already does).
- Fork-PR approval hardening (shipped 2026-06-01) — the other half of this pass.
