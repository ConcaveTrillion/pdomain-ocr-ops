---
title: pd-* → pdomain-* Phase 3 — GH repo renames + index regen + dep flip-back
date: 2026-05-26
status: ready
repo: ocr-container-meta
spec: docs/archive/specs/2026-05-26-pd-to-pdomain-rename-design.md
phase: 3
---

# pd-* → pdomain-* Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the 9 kept product GH repos and 2 index GH repos from `pd-*` → `pdomain-*` under `ConcaveTrillion/`, regenerate the self-hosted Python and npm indices against the new names, flip every Phase-2 sibling-path dep specifier back to a registry pointer, and smoke-install end-to-end — all while GitHub Actions remains disabled per the Phase-4.5 directive.

**Architecture:**

1. Rename product GH repos (9) → rename index GH repos (2) — both groups are pure `gh repo rename` calls; GH preserves old-name redirects automatically.
2. Run the existing rename harness against the two index repo local checkouts (out of Phase 2 scope because they have no `make ci` to gate against). Commit + push to each renamed remote.
3. Regenerate both indices **locally** (no Actions): `python regen_index.py` writes wheel HTML into the `_site/` tree, push to `gh-pages` so GitHub Pages serves new content.
4. In each consumer worktree, flip `[tool.uv.sources]` Python entries from `{ path = … }` back to `{ index = "pdomain-index-pip" }` (the registry pointer). On the JS side, flip `pnpm link --global` → registry `@pdomain/pdomain-ui`. One small commit per repo, pushed to `main`.
5. Restore `pdomain-prep-for-pgdp/frontend/tests/pdUiPin.test.ts` semver guard (was relaxed in Phase 2 to accept `file:` deps).
6. Smoke gate: `uv tool install pdomain-ocr-cli --extra-index-url https://concavetrillion.github.io/pdomain-index-pip/simple/` on a throwaway venv resolves and runs `--help`.

**Tech Stack:** gh CLI, uv, hatch-vcs, pnpm, the existing rename harness (`scripts/rename/apply_rename.py`). No Makefile/CI changes; this is a pure-rename + regen phase.

**User override (Actions stays disabled until Phase 4.5):**

- Do **not** re-enable GitHub Actions on any repo this phase (carry-forward item #1 from Phase 2 is deferred). The `pdomain/pdomain-index-pip dispatch failed` warnings emitted by post-Phase-2 release.yml jobs are inert because no workflow runs; the 15-min cron in `regen.yml` also will not fire. **Index regen is run locally** instead, pushing artifacts straight to the `gh-pages` branch of each index repo.
- Smoke-install (step 6) does not require Actions — it pulls wheels from the GH-Pages-served simple-index, which serves static HTML the moment `gh-pages` is pushed.

**Scope confirmation:** Three repos are retired and keep `pd-*` names: `pd-png-optimizer`, `pd-ocr-trainer` (legacy NiceGUI), `pd-ocr-labeler` (legacy NiceGUI). They are **not** renamed in Phase 3 (commit `0f81bca` dropped them from the manifest). 9 product repos + 2 index repos = 11 GH renames total.

**Repos to rename (product, 9):**
`pdomain-book-tools`, `pdomain-ocr-cli`, `pdomain-ocr-labeler-spa`, `pdomain-ocr-ops`, `pdomain-ocr-simple-gui`, `pdomain-ocr-synth`, `pdomain-ocr-trainer-spa`, `pdomain-ocr-training`, `pdomain-prep-for-pgdp`, `pdomain-ui`.

Wait — that's 10. Let me recount: book-tools, ocr-cli, ocr-labeler-spa, ocr-ops, ocr-simple-gui, ocr-synth, ocr-trainer-spa, ocr-training, prep-for-pgdp, ui = **10 product repos**. The Phase-2 "10 kept repos" matches. Total GH renames = 10 + 2 = **12**.

**Repos to rename (index, 2):** `pdomain-index-pip`, `pdomain-index-npm`.

---

## Open-question answers (locked in by this plan)

1. **Rename order:** GH repo renames are atomic per-repo at the GH side and have no cross-repo ordering constraint (redirects work both directions during the transition). However: rename the **index repos last**, after products. The renamed `pdomain-index-pip` repo's `gh-pages` URL becomes `concavetrillion.github.io/pdomain-index-pip/simple/`, which is what consumers will reference after the dep flip-back. Renaming products first means the regen script (still keyed off `pd-*` names until step 2) doesn't see a half-renamed world.

2. **Index regen without Actions:** Run `regen_index.py` from CT's interactive workspace. The script enumerates GH Releases via `gh api` (requires `GH_TOKEN` env or `gh auth status` — already configured for `ConcaveTrillion`). Output writes to `_site/simple/<package>/index.html`. Push to `gh-pages` branch directly. **No workflow_dispatch needed.**

3. **`[tool.uv.sources]` flip-back target:** Spec §3 line 167 keeps the index under `ConcaveTrillion/` until Phase 4.5. So during Phase 3, the dep spec is:

   ```toml
   [tool.uv.sources]
   pdomain-book-tools = { index = "pdomain-index-pip" }
   ```

   And `[[tool.uv.index]]` block:

   ```toml
   [[tool.uv.index]]
   name = "pdomain-index-pip"
   url = "https://concavetrillion.github.io/pdomain-index-pip/simple/"
   ```

   The URL flips to `pdomain.github.io/...` in Phase 4.5, **not Phase 3**. Manifest currently has the post-Phase-4.5 final URL substituted (`pdomain.github.io/pdomain-index-pip`). For Phase 3 we override that one substitution to the intermediate `concavetrillion.github.io/pdomain-index-pip` form (a Phase-3-only patch, reverted in Phase 4.5).

4. **Frontend `@pdomain/pdomain-ui` flip-back:** Each SPA repo currently has either a `file:` dep or a vendored `.tgz` in-tree. Flip to `"@pdomain/pdomain-ui": "^0.2.1"` (matching the pre-Phase-2 `^0.2.1` pin, since no version bump happened) plus an `.npmrc` registry pointer at `https://concavetrillion.github.io/pdomain-index-npm/`. Remove the in-tree `.tgz` artifact in `pdomain-ocr-labeler-spa`.

5. **No Actions ⇒ no CI gate:** Each post-flip-back commit lands on `main` without a CI run. CT performs a per-repo `make ci AI=1` locally before each merge (same gate Phase 2 used; just run by hand here). Per-repo `make ci` is the authoritative gate; the absent workflow run is not.

6. **Index regen artifact verification:** After regen, `curl -s https://concavetrillion.github.io/pdomain-index-pip/simple/ | grep pdomain-book-tools` confirms the HTML lists the new names. Allow ~60 s for GH Pages to propagate after the `gh-pages` push.

7. **Old-name redirect spot-check:** `curl -L -o /dev/null -w "%{url_effective}\n" https://github.com/pdomain/pdomain-book-tools` should resolve to `https://github.com/pdomain/pdomain-book-tools`. GH provides this redirect automatically.

---

## File structure

Touched in Phase 3:

- **Each index repo local checkout** (`pdomain-index-pip/`, `pdomain-index-npm/`):
  - All files matched by the existing rename manifest (string substitutions: `pd-*` → `pdomain-*`, `ConcaveTrillion/pd-*` → `pdomain/pdomain-*` URLs, etc.)
  - `scripts/regen_index.py` — repo list rewritten in place.
  - `_site/` regenerated by running the regen script locally.
  - `gh-pages` branch updated and pushed.

- **Each consumer repo** (10 product repos):
  - `pyproject.toml` — `[tool.uv.sources]` entries: `{ path = … }` → `{ index = "pdomain-index-pip" }`. `[[tool.uv.index]]` URL is set/updated.
  - `frontend/package.json` (SPA repos: pdomain-ocr-labeler-spa, pdomain-ocr-simple-gui, pdomain-ocr-trainer-spa, pdomain-prep-for-pgdp) — `@pdomain/pdomain-ui` dep flipped from `file:` / `.tgz` → `"^0.2.1"`.
  - `frontend/.npmrc` — registry pointer added/verified.
  - `pdomain-ocr-labeler-spa/frontend/` — vendored `pdomain-pdomain-ui-*.tgz` deleted.
  - `pdomain-prep-for-pgdp/frontend/tests/pdUiPin.test.ts` — semver guard restored (reject `file:`).

- **Workspace root:**
  - `scripts/rename/rename-manifest.json` — Phase-3-only override of the Pages URL substitution (apply, run regen, revert override). **Or** simpler: do not re-run the harness against product repos; only run against the two index repos with a Phase-3-only manifest override, then revert. (Product repos are already done in Phase 2.)
  - `docs/handoff-next-session.md` — append Phase 3 done summary.

Not touched:

- Three retired repos (`pd-png-optimizer`, `pd-ocr-trainer`, `pd-ocr-labeler`). They keep `pd-*` names on GH and locally.
- GitHub Actions enablement (deferred to Phase 4.5).
- Any agent-memory / `.claude/agents/` / docs slug renames (Phase 6).

---

## Task 1: Pre-flight — confirm Phase 2 state and Actions-disabled posture

**Files:** read-only

- [ ] **Step 1: Confirm all 10 product repos are on `main` at the Phase 2 merge SHA**

  ```bash
  cd /workspaces/ocr-container
  for r in pdomain-book-tools pdomain-ocr-cli pdomain-ocr-labeler-spa pdomain-ocr-ops \
           pdomain-ocr-simple-gui pdomain-ocr-synth pdomain-ocr-trainer-spa pdomain-ocr-training \
           pdomain-prep-for-pgdp pdomain-ui; do
    echo "=== $r ==="
    git -C "$r" status --short
    git -C "$r" rev-parse --short HEAD
    git -C "$r" log -1 --format="%s"
  done
  ```

  Acceptance: each repo on `main`, clean tree, HEAD matches the Phase 2 merge SHA in the carry-forward table.

- [ ] **Step 2: Confirm Actions are disabled on all 10 product + 2 index repos**

  ```bash
  for r in pdomain-book-tools pdomain-ocr-cli pdomain-ocr-labeler-spa pdomain-ocr-ops \
           pdomain-ocr-simple-gui pdomain-ocr-synth pdomain-ocr-trainer-spa pdomain-ocr-training \
           pdomain-prep-for-pgdp pdomain-ui pdomain-index-pip pdomain-index-npm; do
    echo -n "$r: "
    gh api "/repos/ConcaveTrillion/$r/actions/permissions" --jq .enabled
  done
  ```

  Acceptance: all 12 print `false`.

- [ ] **Step 3: Confirm `gh auth` is logged in as ConcaveTrillion with `repo`+`workflow` scopes**

  ```bash
  gh auth status
  ```

  Acceptance: token has `repo`, `workflow`, `admin:org` (or at least `repo`) scopes for `ConcaveTrillion`.

---

## Task 2: Rename the 10 product GH repos

**Files:** none locally; GH-side mutations only.

- [ ] **Step 1: Rename in alphabetical order (no cross-repo coupling)**

  ```bash
  for old in pdomain-book-tools pdomain-ocr-cli pdomain-ocr-labeler-spa pdomain-ocr-ops \
             pdomain-ocr-simple-gui pdomain-ocr-synth pdomain-ocr-trainer-spa pdomain-ocr-training \
             pdomain-prep-for-pgdp pdomain-ui; do
    new="pdomain-${old#pd-}"
    echo "Renaming $old → $new"
    gh repo rename "$new" --repo "ConcaveTrillion/$old" --yes
  done
  ```

- [ ] **Step 2: Verify new names resolve and old names redirect**

  ```bash
  for new in pdomain-book-tools pdomain-ocr-cli pdomain-ocr-labeler-spa \
             pdomain-ocr-ops pdomain-ocr-simple-gui pdomain-ocr-synth \
             pdomain-ocr-trainer-spa pdomain-ocr-training \
             pdomain-prep-for-pgdp pdomain-ui; do
    echo -n "$new: "
    gh api "/repos/ConcaveTrillion/$new" --jq .full_name
  done
  ```

  Acceptance: each line prints `ConcaveTrillion/pdomain-<x>`.

- [ ] **Step 3: Update each local checkout's `remote.origin.url`** (the harness deliberately excluded `.git/config` per commit `69240e0`)

  ```bash
  for old in pdomain-book-tools pdomain-ocr-cli pdomain-ocr-labeler-spa pdomain-ocr-ops \
             pdomain-ocr-simple-gui pdomain-ocr-synth pdomain-ocr-trainer-spa pdomain-ocr-training \
             pdomain-prep-for-pgdp pdomain-ui; do
    new="pdomain-${old#pd-}"
    git -C "$old" remote set-url origin "https://github.com/ConcaveTrillion/$new.git"
    echo -n "$old → "
    git -C "$old" remote get-url origin
  done
  ```

  Acceptance: every `remote get-url` prints the `pdomain-*` URL. GH redirect would also work transparently, but explicit set-url avoids future audit confusion.

- [ ] **Step 4: Spot-check fetch from the new remote name**

  ```bash
  git -C pdomain-book-tools fetch origin
  git -C pdomain-book-tools status --short
  ```

  Acceptance: fetch succeeds, working tree still clean.

---

## Task 3: Rename the 2 index GH repos + harness their checkouts

**Files:**
- `pdomain-index-pip/**`, `pdomain-index-npm/**` (whole-tree harness pass)
- `scripts/rename/rename-manifest.json` — Phase-3 URL-substitution override (temporary)

- [ ] **Step 1: Rename `pdomain-index-pip` and `pdomain-index-npm` on GH**

  ```bash
  gh repo rename pdomain-index-pip --repo ConcaveTrillion/pdomain-index-pip --yes
  gh repo rename pdomain-index-npm --repo ConcaveTrillion/pdomain-index-npm --yes
  ```

  Acceptance: `gh api /repos/ConcaveTrillion/pdomain-index-pip` returns 200.

- [ ] **Step 2: Update local remotes for both index checkouts**

  ```bash
  git -C pdomain-index-pip remote set-url origin https://github.com/ConcaveTrillion/pdomain-index-pip.git
  git -C pdomain-index-npm remote set-url origin https://github.com/ConcaveTrillion/pdomain-index-npm.git
  ```

- [ ] **Step 3: Apply Phase-3 manifest override**

  The Phase-2 manifest substitutes `concavetrillion.github.io/pdomain-index-pip` → `pdomain.github.io/pdomain-index-pip` (the Phase-4.5 final form). For Phase 3 we need the intermediate form `concavetrillion.github.io/pdomain-index-pip`. Two clean options:

  - **Option A (preferred):** Hand-edit the two index repos after the harness run, undoing only the owner-prefix subs. The harness leaves a deterministic audit trail; `git diff` makes this trivial.
  - **Option B:** Add a temporary manifest entry for Phase 3 only, then revert. Riskier — touches a shared file.

  Picking A.

- [ ] **Step 4: Run the rename harness against each index repo**

  ```bash
  for r in pdomain-index-pip pdomain-index-npm; do
    cd "/workspaces/ocr-container/$r"
    # Worktree off main so we keep main untouched until we're happy
    git checkout -b rename/pdomain
    uv run --directory /workspaces/ocr-container/scripts/rename \
      python apply_rename.py --scope="$r" --apply
    cd /workspaces/ocr-container
  done
  ```

- [ ] **Step 5: Manual sweep — revert any premature Phase-4.5 owner-prefix substitutions**

  ```bash
  for r in pdomain-index-pip pdomain-index-npm; do
    cd "/workspaces/ocr-container/$r"
    # Undo only the Phase-4.5 owner flip; keep all other rename subs
    git grep -lE "pdomain\.github\.io|pdomain/pdomain-" | \
      xargs -r sed -i \
        -e 's|pdomain\.github\.io|concavetrillion.github.io|g' \
        -e 's|pdomain/pdomain-|ConcaveTrillion/pdomain-|g'
    git diff --stat
    cd /workspaces/ocr-container
  done
  ```

  Acceptance: `git diff` on each repo shows the harness rename results minus the Phase-4.5 owner flip.

- [ ] **Step 6: Sanity-check `regen_index.py` (pdomain-index-pip)**

  ```bash
  cd /workspaces/ocr-container/pdomain-index-pip
  grep -nE "ConcaveTrillion|pdomain-|pd-" scripts/regen_index.py | head -20
  ```

  Acceptance: `ORG = "ConcaveTrillion"`, REPOS list contains the 10 `pdomain-*` product names, **no remaining `pd-*` references** in the live config (only in comments/docstrings if any).

- [ ] **Step 7: Commit + merge + push each index repo**

  ```bash
  for r in pdomain-index-pip pdomain-index-npm; do
    cd "/workspaces/ocr-container/$r"
    git add -A
    git commit -m "$(cat <<'EOF'
  chore(rename): harness pd-* → pdomain-* (Phase 3)

  Mirrors Phase 2's content rewrite but for the two index repos that
  defer to Phase 3 per spec §5. Pages URL kept at concavetrillion.github.io
  until Phase 4.5 org transfer.

  Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
    git checkout main
    git merge --no-ff rename/pdomain -m "Merge rename/pdomain → main (Phase 3)"
    git push origin main
    git branch -d rename/pdomain
    cd /workspaces/ocr-container
  done
  ```

  Acceptance: each repo's `main` is one merge commit ahead; pushes succeed; local rename branch deleted.

---

## Task 4: Regenerate both indices (locally, no Actions)

**Files:**
- `pdomain-index-pip/_site/**` regenerated and pushed to `gh-pages`
- `pdomain-index-npm/_site/**` (or equivalent — check structure) regenerated and pushed to `gh-pages`

- [ ] **Step 1: Regenerate the pip index**

  ```bash
  cd /workspaces/ocr-container/pdomain-index-pip
  # Ensure gh CLI is reachable from the regen script
  gh auth status
  uv run python scripts/regen_index.py
  ls _site/simple/ | head -20
  ```

  Acceptance: `_site/simple/` lists `pdomain-book-tools`, `pdomain-ocr-cli`, etc. (matching whatever has GH Release assets). Empty for repos with no releases yet — that's fine.

- [ ] **Step 2: Push the regenerated `_site/` to `gh-pages`**

  ```bash
  cd /workspaces/ocr-container/pdomain-index-pip
  git checkout gh-pages 2>/dev/null || git checkout --orphan gh-pages
  # Replace gh-pages content with the new _site/
  git rm -rf . 2>/dev/null || true
  cp -r _site/* .
  git add -A
  git commit -m "regen index (Phase 3 — pdomain-* names)"
  git push origin gh-pages
  git checkout main
  ```

  *Note:* If the existing repo workflow normally publishes via `peaceiris/actions-gh-pages`, the `gh-pages` branch already exists with its own layout. Adapt to whatever the live branch looks like before committing — investigate first with `git ls-remote --heads origin gh-pages` and `git fetch origin gh-pages && git log origin/gh-pages -1`.

- [ ] **Step 3: Wait for GH Pages to propagate, then verify**

  ```bash
  sleep 60
  curl -sSL https://concavetrillion.github.io/pdomain-index-pip/simple/ | head -40
  curl -sSL https://concavetrillion.github.io/pdomain-index-pip/simple/pdomain-book-tools/ | head -20
  ```

  Acceptance: HTML lists `pdomain-*` packages; package detail page lists wheel filenames matching `pdomain_*-*.whl`.

- [ ] **Step 4: Repeat for the npm index**

  ```bash
  cd /workspaces/ocr-container/pdomain-index-npm
  ls scripts/   # confirm regen entrypoint
  # Run the npm-index regen; structure differs from pip — read scripts/ first
  # to find the right invocation. Then push gh-pages similarly.
  ```

  Acceptance: `curl -sSL https://concavetrillion.github.io/pdomain-index-npm/` lists `@pdomain/pdomain-ui` versions.

- [ ] **Step 5: Cross-redirect spot check**

  ```bash
  curl -L -o /dev/null -w "%{url_effective}\n" \
    https://concavetrillion.github.io/pdomain-index-pip/simple/
  ```

  Acceptance: prints `https://concavetrillion.github.io/pdomain-index-pip/simple/` (GH Pages redirect from old name).

---

## Task 5: Flip `[tool.uv.sources]` and `[[tool.uv.index]]` in each consumer repo

**Files (per repo):** `pyproject.toml`

Repos with Python sibling deps: `pdomain-ocr-cli`, `pdomain-ocr-labeler-spa`, `pdomain-ocr-ops`, `pdomain-ocr-simple-gui`, `pdomain-ocr-trainer-spa`, `pdomain-ocr-training`, `pdomain-prep-for-pgdp`. (`pdomain-book-tools`, `pdomain-ocr-synth`, `pdomain-ui` have no Python sibling deps.)

Note: local checkout dirs still on `pd-*` paths — that's fine, Phase 6 does the local rename. We act on the *contents* of `pyproject.toml` in each pd-* directory.

- [ ] **Step 1 (per repo): Edit `pyproject.toml`**

  Replace each `[tool.uv.sources]` entry of the form:

  ```toml
  pdomain-<sibling> = { path = "/workspaces/ocr-container/pd-<sibling>/.claude/worktrees/rename-pdomain", editable = true }
  ```

  with:

  ```toml
  pdomain-<sibling> = { index = "pdomain-index-pip" }
  ```

  Ensure the `[[tool.uv.index]]` block exists:

  ```toml
  [[tool.uv.index]]
  name = "pdomain-index-pip"
  url = "https://concavetrillion.github.io/pdomain-index-pip/simple/"
  ```

  *Important:* the URL is the **Phase-3 intermediate** form (`concavetrillion.github.io`), not the Phase-4.5 final form.

- [ ] **Step 2 (per repo): `uv sync` and run local CI**

  ```bash
  cd /workspaces/ocr-container/<repo>
  uv sync
  make ci AI=1
  ```

  Acceptance: `uv sync` resolves siblings from the simple-index; `make ci` green. If `uv` can't find a wheel (the upstream repo has no release published with the new name), fall back to `{ path = "../<sibling>" }` (live checkout, since both ends are renamed at the `pyproject` level) and document under "Known gaps" below.

- [ ] **Step 3 (per repo): Commit + merge to `main`, push**

  ```bash
  git checkout -b flip-back/index
  git add pyproject.toml uv.lock
  git commit -m "$(cat <<'EOF'
  chore(rename): flip [tool.uv.sources] from path → pdomain-index-pip

  Phase 3 cleanup. Sibling pd-* deps were pinned to Phase-2 worktree paths
  during the rename window; restore the registry pointer now that the
  pdomain-* wheels are served by the renamed self-hosted index.

  Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
    git checkout main
    git merge --no-ff flip-back/index -m "Merge flip-back/index → main (Phase 3)"
    git push origin main
    git branch -d flip-back/index
  ```

---

## Task 6: Flip frontend `@pdomain/pdomain-ui` deps to registry in each SPA repo

**Files (per SPA repo):** `frontend/package.json`, `frontend/.npmrc`, `frontend/pnpm-lock.yaml`; in `pdomain-ocr-labeler-spa` also delete the vendored `.tgz`.

SPA repos: `pdomain-ocr-labeler-spa`, `pdomain-ocr-simple-gui`, `pdomain-ocr-trainer-spa`, `pdomain-prep-for-pgdp`.

- [ ] **Step 1 (per repo): Edit `frontend/package.json`**

  Replace the `@pdomain/pdomain-ui` dep value with `"^0.2.1"` (matching the pre-Phase-2 pin).

- [ ] **Step 2 (per repo): Ensure `.npmrc` registry pointer**

  ```ini
  @pdomain:registry=https://concavetrillion.github.io/pdomain-index-npm/
  store-dir=~/.local/share/pnpm/store
  ```

  Phase 2 already added `@concavetrillion:` colon-syntax handling (commit `11792bf`); the harness should have rewritten `@concavetrillion:` → `@pdomain:` in `.npmrc`. Verify.

- [ ] **Step 3 (per repo): Delete vendored `.tgz` if present (`pdomain-ocr-labeler-spa` only)**

  ```bash
  cd /workspaces/ocr-container/pdomain-ocr-labeler-spa/frontend
  rm -f pdomain-pdomain-ui-*.tgz pdomain-ui-*.tgz @pdomain-pdomain-ui-*.tgz
  ```

- [ ] **Step 4 (per repo): `pnpm install` + run frontend CI**

  ```bash
  cd /workspaces/ocr-container/<repo>
  pnpm --filter './frontend' install
  make ci AI=1
  ```

  Acceptance: `pnpm` resolves `@pdomain/pdomain-ui@^0.2.1` from the npm index; vitest passes; frontend build green. If the npm index has no `0.2.1` published under the new name yet, `pdomain-ui` needs a `pnpm publish` first — flag as a blocker and pause.

- [ ] **Step 5 (per repo): Commit + merge + push**

  ```bash
  git checkout -b flip-back/frontend
  git add -A
  git commit -m "$(cat <<'EOF'
  chore(rename): flip @pdomain/pdomain-ui dep back to registry

  Phase 3 cleanup. Frontend dep was pinned to a file: / .tgz path during
  the rename window; restore the registry pointer.

  Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
    git checkout main
    git merge --no-ff flip-back/frontend -m "Merge flip-back/frontend → main (Phase 3)"
    git push origin main
    git branch -d flip-back/frontend
  ```

---

## Task 7: Restore `pdUiPin.test.ts` semver guard in pdomain-prep-for-pgdp

**Files:** `pdomain-prep-for-pgdp/frontend/tests/pdUiPin.test.ts`

- [ ] **Step 1: Restore the assertion that rejects `file:` deps**

  Look up the Phase-2 patch that relaxed the guard (`git log -p frontend/tests/pdUiPin.test.ts` since the Phase-2 merge). Revert just the relaxation; keep all other rename-related edits.

- [ ] **Step 2: Run the test**

  ```bash
  cd /workspaces/ocr-container/pdomain-prep-for-pgdp
  pnpm --filter './frontend' test pdUiPin
  ```

  Acceptance: test passes against the now-registry `@pdomain/pdomain-ui` dep, would fail if reverted to `file:`.

- [ ] **Step 3: Commit + merge + push** (same pattern as Task 6 Step 5)

---

## Task 8: Smoke test — fresh install via the regenerated index

**Files:** none (throwaway venv)

- [ ] **Step 1: Build a clean tool venv**

  ```bash
  uv tool install pdomain-ocr-cli \
    --extra-index-url https://concavetrillion.github.io/pdomain-index-pip/simple/ \
    --force
  ```

  Acceptance: resolves `pdomain-ocr-cli` and all `pdomain-*` transitive deps from the simple-index; tool venv installs without falling through to PyPI for `pdomain-*` packages.

- [ ] **Step 2: Run `--help`**

  ```bash
  pdomain-ocr --help 2>&1 | head -20
  ```

  Acceptance: prints usage; entry point resolves and the renamed `pdomain_*` import path loads.

- [ ] **Step 3: Tear down**

  ```bash
  uv tool uninstall pdomain-ocr-cli
  ```

---

## Task 9: Update workspace handoff doc + close out Phase 3

**Files:** `docs/handoff-next-session.md`

- [ ] **Step 1: Append a Phase 3 done section**

  Mirror the Phase 2 carry-forward table. Note explicitly: Actions still disabled. List which carry-forward items from Phase 2 are now resolved (`gh repo rename`, index regen, `[tool.uv.sources]` flip-back, frontend dep flip-back, `pdUiPin.test.ts` restore, vendored `.tgz` cleanup) vs. still open (Actions re-enable → Phase 4.5; package-dir renames → Phase 6).

- [ ] **Step 2: Commit on workspace root**

  ```bash
  cd /workspaces/ocr-container
  git add docs/plans/2026-05-26-pdomain-rename-phase-3.md docs/handoff-next-session.md
  git commit -m "$(cat <<'EOF'
  docs(plans): Phase 3 plan + handoff update — pd-* → pdomain-* renames live

  Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
  ```

---

## Acceptance gates (cohort-wide)

- [ ] All 10 product GH repos return 200 at `https://github.com/ConcaveTrillion/pdomain-<x>`; old `pd-<x>` URLs 301-redirect to new.
- [ ] Both index GH repos return 200 at their new `pdomain-index-*` names.
- [ ] `https://concavetrillion.github.io/pdomain-index-pip/simple/` lists `pdomain-*` packages.
- [ ] `https://concavetrillion.github.io/pdomain-index-npm/` lists `@pdomain/pdomain-ui` versions.
- [ ] No `pyproject.toml` in any consumer has `path = …` for a sibling dep.
- [ ] No `frontend/package.json` in any SPA has `file:` or `.tgz` for `@pdomain/pdomain-ui`.
- [ ] `pdomain-prep-for-pgdp/frontend/tests/pdUiPin.test.ts` rejects `file:` deps.
- [ ] No `.tgz` artifact under any `frontend/`.
- [ ] `uv tool install pdomain-ocr-cli ...` smoke test passes.
- [ ] GitHub Actions remains `enabled=false` on all 12 repos (verify post-flight).

---

## Rollback

Pre-rename (per repo): `gh repo rename pd-<x> --repo ConcaveTrillion/pdomain-<x> --yes` flips the name back; GH retains the redirect either direction.

Pre-index-regen: `git push origin gh-pages --force-with-lease` to the previous tip restores the old simple-index. (CT must approve any force-push.)

Post-flip-back: revert the per-repo flip-back commit; the Phase-2 path-based dep spec still resolves while the sibling worktree exists. Once the worktrees are gone (after Phase 3 cleanup), revert restores `{ index = "pdomain-index-pip" }` — but the renamed repo is now `pdomain-index-pip`, so a rollback past this point requires a fresh path pin, not a clean revert.

After Step 5+ (push of flip-back commits): Phase 3 is the second point of no comfortable return after Phase 2's push. From here, forward through Phases 4–6 is cheaper than reverse.

---

## Known gaps / explicit non-goals

- **Actions re-enable:** deferred to Phase 4.5 per user directive.
- **Package directory renames** (`src/pd_<x>/` → `src/pdomain_<x>/`): Phase 2 did these *inside the rename worktrees*; verify by reading the merged tree on `main`. If any survive, Phase 6 handles. **Add a verification step in Task 1 to check this.**
- **`.claude/agents/`, `.claude/agent-memory/`, skills, docs prose:** Phase 6.
- **Org transfer to `pdomain/`:** Phase 4.5.
- **PAT/secret swap:** Phase 6 (PAT remains scoped to `ConcaveTrillion/*` until then; the GH redirect handles cross-name resolution).
- **`pdomain-ui` codegen wheel hashes:** already regenerated in Phase 2. Phase 3 should not need to touch them; verify nothing slipped.

---

## Notes for the executing agent

- **No PRs.** Workspace policy: worktree → local-merge → push. Same as Phase 2.
- **Identity check.** Each repo's `.git/config` `user.email`/`user.name` should already be set from Phase 2; if not, set repo-locally to `ConcaveTrillion` / `concavetrillion@gmail.com`.
- **Do not delegate the GH rename step to a subagent.** It is a single short `gh repo rename` loop and the failure modes (wrong name, scope error) are easiest to read in the parent's tool output.
- **Index-regen and flip-back tasks can be delegated** per-repo to the matching `pdomain-<x>` (currently still named `pd-<x>`) agent for the file edits — but ONLY after Step 1 of Task 5 has been laid out so the agent has explicit content to apply. The agent should NOT need to read or understand the Phase 3 plan; quote the exact diff in the prompt.
- **No `make ci AI=1` skips.** Even with Actions disabled, local CI is the gate. If `make ci` fails on a repo, do not push that repo's flip-back commit until the failure is resolved.

---
