---
title: pd-* → pdomain-* Phase 2 — Python ecosystem rename
date: 2026-05-26
status: ready
repo: ocr-container-meta
spec: docs/archive/specs/2026-05-26-pd-to-pdomain-rename-design.md
phase: 2
---

# pd-* → pdomain-* Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename every kept `pd-*` Python package, npm package, source-import path, sibling dep specifier, install-script reference, and workflow-secret reference to its `pdomain-*` form, across 10 product repos, with all worktrees passing `make ci AI=1` before any push to `main`.

**Architecture:** One isolated worktree per repo under `<repo>/.claude/worktrees/rename-pdomain` off `main`. Per-worktree: run the existing rename harness (`scripts/rename/apply_rename.py`) → manual sweep of harness-blind surfaces → wire `[tool.uv.sources]` (Python) and `pnpm link` (JS) to **sibling worktrees in this same window**, not to the registry → `make ci AI=1` green → commit on branch `rename/pdomain` (do not merge, do not push). When all 10 product worktrees report green, fast-forward-merge in dep order and push in dep order. The two index repos defer to Phase 3 per spec §5.

**Tech Stack:** uv, hatch-vcs, pnpm, pytest, vitest, basedpyright, ruff. Workspace policy: worktree → local-merge → push; no PRs; no force-pushes; no squash.

**Scope confirmation:** The two index repos (`pdomain-index-pip`, `pdomain-index-npm`) are in Phase 3, not Phase 2 — confirmed against spec §5 line 165–172. They have no `pyproject.toml`, no `make ci`, and Phase 3's index regen is the natural gate for their rename. This plan covers the **10 product repos** that have `make ci`.

**Open-question answers (locked in by this plan):**

1. **Dep-landing order on `main`:** `pdomain-book-tools` first (no pd-* deps). Then in parallel: `pdomain-ocr-ops`, `pdomain-ocr-training`, `pdomain-ocr-synth`, `pdomain-ui` (each depends only on pdomain-book-tools or nothing). Then `pdomain-ocr-cli`, `pdomain-ocr-labeler-spa`, `pdomain-ocr-simple-gui`, `pdomain-prep-for-pgdp` (depend on book-tools + ocr-ops). Then `pdomain-ocr-trainer-spa` last (depends on book-tools + ocr-ops + ocr-training). Verified against each repo's `[project].dependencies` in its `pyproject.toml`.
2. **Sibling-worktree dep resolution:** Each renamed worktree's `[tool.uv.sources]` is rewritten **in-tree on the rename branch** to use `{ path = "<absolute sibling-worktree path>", editable = true }` instead of `{ index = "pdomain-index-pip" }`. This is committed as part of the rename branch. A follow-up cleanup commit in **Phase 3** (after `pdomain-index-pip` exists) flips it back to `{ index = "pdomain-index-pip" }`. JS-side: a Phase-2-only `pnpm link --global` of the `pdomain-ui` rename worktree, replacing the registry-resolved `@concavetrillion/pdomain-ui ^0.2.1`. `scripts/local-dev.sh` is **not used** — its sibling-path resolution is hardcoded to `$WORKSPACE_ROOT/<sibling>` (live checkout) and would point at unrenamed code.
3. **`make ci` gating in mid-rename state:** Each worktree resolves siblings to other Phase-2 worktree paths via in-tree `[tool.uv.sources]` rewrites (Python) and `pnpm link` (JS). No mid-rename worktree depends on the registry; no mid-rename worktree depends on a live checkout. Verified by per-repo CI before cohort gate.
4. **Harness-blind surfaces** (the manual sweep): (a) the `pdomain-ui` codegen wheel-hash JSON (`pdomain-ui/codegen.versions.json`) — the harness will rewrite `pdomain-book-tools` → `pdomain-book-tools` keys, but the SHA256 hashes will not match new wheel filenames; codegen must be re-run to regenerate hashes against rebuilt sibling wheels. (b) the **package directory name itself** (`src/pd_book_tools/` → `src/pdomain_book_tools/`) — the harness rewrites *file contents* but a directory rename is a separate `git mv`. (c) JS source-package directories under `pdomain-ui/src/` if any contain `pd-` in the filename (none confirmed by Explore audit; left as a check, not a task). (d) `.git/config` `remote.origin.url` is **not** rewritten by the harness (excluded per commit 69240e0) — left for Phase 3. (e) any binary asset filenames with `pd[-_]` in the name (none confirmed by Explore audit; left as a check, not a task).
5. **Coordinated-push sequencing:** Push order matches dep order. Each downstream push waits for its upstream push to land on `main`. `pdomain-book-tools` pushes first; only after it lands do `pdomain-ocr-ops`/`pdomain-ocr-training`/`pdomain-ocr-synth`/`pdomain-ui` push (in any order, parallelizable); only after those land do `pdomain-ocr-cli`/`pdomain-ocr-labeler-spa`/`pdomain-ocr-simple-gui`/`pdomain-prep-for-pgdp` push; `pdomain-ocr-trainer-spa` last. This is for hygiene only — CI is already gated at worktree time against sibling worktrees, not `main`, so a downstream push technically works regardless of upstream `main` state; ordered push keeps `main` always-resolvable for an outside observer.
6. **Rollback per worktree** (pre-push): `git worktree remove --force <worktree>` and `git branch -D rename/pdomain` in the live repo. Zero residue. **Post-push:** the rename branch is on `main`; reverting means a fresh rename commit going the other way, same cost as the original. Phase 2 push is the point of no comfortable return — explicit in spec §7.
7. **Pre-1.0 version bumps:** **No version bumps in Phase 2.** Each repo keeps its current version (`pdomain-book-tools 0.14.1` becomes `pdomain-book-tools 0.14.1`). The package name change carries the identity flip; the wheel filename changes as a side effect (`pd_book_tools-0.14.1-py3-none-any.whl` → `pdomain_book_tools-0.14.1-py3-none-any.whl`). Bumping versions is a YAGNI add — the rename window publishes no wheels, and Phase 3 index regen reads GH Release assets whose names already differ. If a real publish needs to bump (e.g., the `pdomain-book-tools 0.0.1` placeholder collides on PyPI), that is a Phase 0 follow-on, not a Phase 2 concern.

---

## File structure

Touched in every per-repo worktree (created/modified):

- `pyproject.toml` — `[project].name`, `[project].dependencies`, `[tool.uv.sources]`
- `src/pd_<x>/` → `src/pdomain_<x>/` — directory rename via `git mv`
- `src/**/*.py`, `tests/**/*.py` — import paths
- `Makefile` — any package-name references
- `.github/workflows/*.yml` — dispatch targets and workflow-secret name
- `install.sh` (where present) — wheel name strings, simple-index URLs
- `README.md`, `CLAUDE.md`, `CONVENTIONS.md` — narrative prose
- `frontend/package.json` (SPA repos only) — `@concavetrillion/pdomain-ui` → `@pdomain/pdomain-ui` in `dependencies`
- `frontend/src/**/*.{ts,tsx}` (SPA repos only) — import paths `from '@concavetrillion/pdomain-ui'`

Touched only in `pdomain-ui`:

- `package.json` — `name` field flips to `@pdomain/pdomain-ui`
- `codegen.versions.json` — sibling-package keys flip; SHA256 hashes regenerated
- `src/**/*.ts` — internal references

Touched only in repos with sibling Python deps (everything except `pdomain-book-tools` and `pdomain-ocr-synth` and `pdomain-ui`):

- `[tool.uv.sources]` rewrites — index → path (mid-rename); will be re-flipped to index in Phase 3.

---

## Per-repo task template

Tasks 2 through 11 below are 10 instantiations of one template, one per kept product repo. The template body is identical structurally; only repo-specific data (path, sibling deps, JS-side presence) differs. Tasks 2–4 are written out in full. Tasks 5–11 list only the repo-specific overrides; the body of each is a copy of the Task 4 template with the overrides applied.

This is intentional. Each task is one full subagent-friendly unit of work — sized so one fresh implementation agent can pick it up cold from the plan, do it end-to-end in one isolated worktree, and return a worktree path + branch + green CI summary. Per writing-plans, repeating the body keeps each task readable out of order.

---

## Task 1: Verify harness + workspace preflight

**Files:**
- Read-only audit: `scripts/rename/apply_rename.py`, `scripts/rename/rename-manifest.json`, `scripts/rename/tests/`

- [ ] **Step 1: Confirm harness is committed and tests are green**

```bash
cd /workspaces/ocr-container
git log --oneline scripts/rename/ | head -5
uv run pytest scripts/rename/tests/ -v
```

Expected: 25/25 tests pass. Commits 828f784…69240e0 visible in log.

- [ ] **Step 2: Confirm working tree is clean across all 10 kept repos**

```bash
for repo in pdomain-book-tools pdomain-ocr-ops pdomain-ui pdomain-ocr-cli pdomain-ocr-synth pdomain-ocr-training pdomain-ocr-labeler-spa pdomain-ocr-trainer-spa pdomain-ocr-simple-gui pdomain-prep-for-pgdp; do
  echo "=== $repo ==="
  git -C "/workspaces/ocr-container/$repo" status --short
done
```

Expected: every repo prints just `=== <name> ===` with no file lines. Any uncommitted work must be resolved before starting Phase 2 (per workspace policy step 1).

- [ ] **Step 3: Confirm each repo's `main` is up to date with `origin/main`**

```bash
for repo in pdomain-book-tools pdomain-ocr-ops pdomain-ui pdomain-ocr-cli pdomain-ocr-synth pdomain-ocr-training pdomain-ocr-labeler-spa pdomain-ocr-trainer-spa pdomain-ocr-simple-gui pdomain-prep-for-pgdp; do
  cd "/workspaces/ocr-container/$repo"
  git fetch origin main --quiet
  ahead=$(git rev-list --count main..origin/main)
  behind=$(git rev-list --count origin/main..main)
  echo "$repo: ahead=$ahead behind=$behind"
done
```

Expected: every line shows `ahead=0 behind=0`. If any repo is ahead/behind, resolve before continuing.

- [ ] **Step 4: Smoke-test harness on one repo (dry-run)**

```bash
cd /workspaces/ocr-container
uv run python scripts/rename/apply_rename.py \
  --scope=/workspaces/ocr-container/pdomain-book-tools \
  --manifest=/workspaces/ocr-container/scripts/rename/rename-manifest.json \
  --report=/tmp/changes-bt-dryrun.json \
  --dry-run
cat /tmp/changes-bt-dryrun.json | jq '.summary'
```

Expected: JSON `summary` block with non-zero `files_modified` count. Inspect a sample entry — every old→new must appear in `rename-manifest.json` (no surprise mappings).

- [ ] **Step 5: Commit nothing in Task 1**

Task 1 is read-only. No commit.

---

## Task 2: Rename pdomain-book-tools (foundation — no pd-* deps)

**Files:**
- Create: `/workspaces/ocr-container/pdomain-book-tools/.claude/worktrees/rename-pdomain/` (worktree off `main`)
- Modify: every file under that worktree the harness identifies
- Branch: `rename/pdomain` (created in step 1)
- Reports: `changes-pdomain-book-tools.json` (in the worktree)

**Repo specifics:**
- No sibling pd-* deps. No `[tool.uv.sources]` rewrites needed.
- No JS frontend. `pnpm link` not needed.
- `src/pd_book_tools/` is the package directory.
- This repo is the upstream of every other repo. It is the unique pre-cohort task — every other repo's worktree depends on this worktree existing on disk.

- [ ] **Step 1: Create the rename worktree off main**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
git fetch origin main --quiet
git worktree add .claude/worktrees/rename-pdomain -b rename/pdomain origin/main
```

Expected: worktree directory `pdomain-book-tools/.claude/worktrees/rename-pdomain/` exists; `git -C .claude/worktrees/rename-pdomain branch --show-current` prints `rename/pdomain`.

- [ ] **Step 2: Run the harness against the worktree**

```bash
cd /workspaces/ocr-container/pdomain-book-tools/.claude/worktrees/rename-pdomain
uv run --directory /workspaces/ocr-container python /workspaces/ocr-container/scripts/rename/apply_rename.py \
  --scope=/workspaces/ocr-container/pdomain-book-tools/.claude/worktrees/rename-pdomain \
  --manifest=/workspaces/ocr-container/scripts/rename/rename-manifest.json \
  --report=./changes-pdomain-book-tools.json
```

Expected: non-zero exit code 0; `changes-pdomain-book-tools.json` written; `git status --short` shows many `M`-marked files. The package directory `src/pd_book_tools/` is **not** renamed by the harness (the harness rewrites file *contents*, not directory names).

- [ ] **Step 3: Rename the package directory**

```bash
cd /workspaces/ocr-container/pdomain-book-tools/.claude/worktrees/rename-pdomain
git mv src/pd_book_tools src/pdomain_book_tools
```

Expected: `git status` shows `R  src/pd_book_tools/... -> src/pdomain_book_tools/...` for every file under the directory.

- [ ] **Step 4: Manual sweep of harness-blind surfaces**

```bash
cd /workspaces/ocr-container/pdomain-book-tools/.claude/worktrees/rename-pdomain
grep -rn 'pd[-_]book[-_]tools' \
  --exclude-dir='.git' --exclude-dir='.venv' --exclude-dir='node_modules' \
  --exclude-dir='__pycache__' --exclude-dir='dist' --exclude-dir='build' \
  --exclude-dir='docs/archive' \
  --exclude='*.lock' --exclude='changes-*.json' \
  . | grep -v '# pre-rename:' | grep -v 'historical:'
```

Expected: empty output, OR only deliberate historical references (which must carry a `# pre-rename:` or `historical:` marker comment — add markers in-line if any survive that should be preserved).

- [ ] **Step 5: Run `make ci AI=1` in the worktree**

```bash
cd /workspaces/ocr-container/pdomain-book-tools/.claude/worktrees/rename-pdomain
make ci AI=1 2>&1 | tee .ci-ai.log | tail -50
```

Expected: trailing `✅ CI pipeline complete!`. Final pytest line shows 100% pass.

- [ ] **Step 6: Commit on rename branch**

```bash
cd /workspaces/ocr-container/pdomain-book-tools/.claude/worktrees/rename-pdomain
rm changes-pdomain-book-tools.json  # audit report stays out of the commit
git add -A
git commit -m "rename: pdomain-book-tools → pdomain-book-tools (Phase 2)

Per spec docs/archive/specs/2026-05-26-pd-to-pdomain-rename-design.md §5.
Harness: scripts/rename/apply_rename.py + rename-manifest.json.
make ci AI=1 green in this worktree."
```

Expected: commit lands on `rename/pdomain`. **Do not merge. Do not push.**

- [ ] **Step 7: Report worktree path + branch + CI status**

The subagent (or executor) records: worktree path `pdomain-book-tools/.claude/worktrees/rename-pdomain`, branch `rename/pdomain`, CI green. This is the artifact every Task 3+ depends on.

---

## Task 3: Rename pdomain-ocr-synth (no pd-* deps, parallelizable with Tasks 4–6)

**Files:** worktree at `/workspaces/ocr-container/pdomain-ocr-synth/.claude/worktrees/rename-pdomain/`. Branch `rename/pdomain`. Report `changes-pdomain-ocr-synth.json`.

**Repo specifics:**
- No sibling pd-* deps. No `[tool.uv.sources]` rewrites.
- No JS frontend.
- Package directory: `src/pd_ocr_synth/`.

- [ ] **Step 1: Create the rename worktree off main**

```bash
cd /workspaces/ocr-container/pdomain-ocr-synth
git fetch origin main --quiet
git worktree add .claude/worktrees/rename-pdomain -b rename/pdomain origin/main
```

- [ ] **Step 2: Run the harness against the worktree**

```bash
cd /workspaces/ocr-container/pdomain-ocr-synth/.claude/worktrees/rename-pdomain
uv run --directory /workspaces/ocr-container python /workspaces/ocr-container/scripts/rename/apply_rename.py \
  --scope=/workspaces/ocr-container/pdomain-ocr-synth/.claude/worktrees/rename-pdomain \
  --manifest=/workspaces/ocr-container/scripts/rename/rename-manifest.json \
  --report=./changes-pdomain-ocr-synth.json
```

- [ ] **Step 3: Rename the package directory**

```bash
cd /workspaces/ocr-container/pdomain-ocr-synth/.claude/worktrees/rename-pdomain
git mv src/pd_ocr_synth src/pdomain_ocr_synth
```

- [ ] **Step 4: Manual sweep**

```bash
cd /workspaces/ocr-container/pdomain-ocr-synth/.claude/worktrees/rename-pdomain
grep -rn 'pd[-_]' \
  --exclude-dir='.git' --exclude-dir='.venv' --exclude-dir='node_modules' \
  --exclude-dir='__pycache__' --exclude-dir='dist' --exclude-dir='build' \
  --exclude-dir='docs/archive' \
  --exclude='*.lock' --exclude='changes-*.json' \
  . | grep -v '# pre-rename:' | grep -v 'historical:'
```

Expected: empty or deliberate-only matches.

- [ ] **Step 5: Run `make ci AI=1`**

```bash
cd /workspaces/ocr-container/pdomain-ocr-synth/.claude/worktrees/rename-pdomain
make ci AI=1 2>&1 | tee .ci-ai.log | tail -50
```

Expected: green.

- [ ] **Step 6: Commit on rename branch**

```bash
cd /workspaces/ocr-container/pdomain-ocr-synth/.claude/worktrees/rename-pdomain
rm changes-pdomain-ocr-synth.json
git add -A
git commit -m "rename: pdomain-ocr-synth → pdomain-ocr-synth (Phase 2)

Per spec docs/archive/specs/2026-05-26-pd-to-pdomain-rename-design.md §5.
make ci AI=1 green."
```

- [ ] **Step 7: Report**

Record: worktree path, branch, CI green.

---

## Task 4: Rename pdomain-ocr-ops (depends on pdomain-book-tools)

**Files:** worktree at `/workspaces/ocr-container/pdomain-ocr-ops/.claude/worktrees/rename-pdomain/`. Branch `rename/pdomain`. Report `changes-pdomain-ocr-ops.json`.

**Repo specifics:**
- One sibling Python dep: `pdomain-book-tools`. The harness rewrites the `[project].dependencies` entry from `pdomain-book-tools >= 0.14.1` to `pdomain-book-tools >= 0.14.1` and the `[tool.uv.sources]` entry from `pdomain-book-tools = { index = "pdomain-index-pip" }` to `pdomain-book-tools = { index = "pdomain-index-pip" }`. The post-harness `[tool.uv.sources]` points at a not-yet-existing index — Step 4 rewrites it to a path source for the duration of Phase 2.
- No JS frontend.
- Package directory: `src/pd_ocr_ops/`.

**Pre-condition:** Task 2 (pdomain-book-tools) committed on its rename worktree at `/workspaces/ocr-container/pdomain-book-tools/.claude/worktrees/rename-pdomain/`.

- [ ] **Step 1: Create the rename worktree off main**

```bash
cd /workspaces/ocr-container/pdomain-ocr-ops
git fetch origin main --quiet
git worktree add .claude/worktrees/rename-pdomain -b rename/pdomain origin/main
```

- [ ] **Step 2: Run the harness against the worktree**

```bash
cd /workspaces/ocr-container/pdomain-ocr-ops/.claude/worktrees/rename-pdomain
uv run --directory /workspaces/ocr-container python /workspaces/ocr-container/scripts/rename/apply_rename.py \
  --scope=/workspaces/ocr-container/pdomain-ocr-ops/.claude/worktrees/rename-pdomain \
  --manifest=/workspaces/ocr-container/scripts/rename/rename-manifest.json \
  --report=./changes-pdomain-ocr-ops.json
```

- [ ] **Step 3: Rename the package directory**

```bash
cd /workspaces/ocr-container/pdomain-ocr-ops/.claude/worktrees/rename-pdomain
git mv src/pd_ocr_ops src/pdomain_ocr_ops
```

- [ ] **Step 4: Wire `[tool.uv.sources]` to sibling worktree (path source)**

Edit `/workspaces/ocr-container/pdomain-ocr-ops/.claude/worktrees/rename-pdomain/pyproject.toml`. Locate the `[tool.uv.sources]` block. The harness left it as:

```toml
[tool.uv.sources]
pdomain-book-tools = { index = "pdomain-index-pip" }
```

Replace with:

```toml
[tool.uv.sources]
pdomain-book-tools = { path = "/workspaces/ocr-container/pdomain-book-tools/.claude/worktrees/rename-pdomain", editable = true }
```

Run `uv lock` to refresh the lockfile against the path source:

```bash
cd /workspaces/ocr-container/pdomain-ocr-ops/.claude/worktrees/rename-pdomain
uv lock
```

Expected: `uv.lock` updated; no resolution errors. `pdomain-book-tools` resolves to the sibling worktree path.

- [ ] **Step 5: Manual sweep**

```bash
cd /workspaces/ocr-container/pdomain-ocr-ops/.claude/worktrees/rename-pdomain
grep -rn 'pd[-_]' \
  --exclude-dir='.git' --exclude-dir='.venv' --exclude-dir='node_modules' \
  --exclude-dir='__pycache__' --exclude-dir='dist' --exclude-dir='build' \
  --exclude-dir='docs/archive' \
  --exclude='*.lock' --exclude='changes-*.json' \
  . | grep -v '# pre-rename:' | grep -v 'historical:'
```

Expected: empty or deliberate-only matches.

- [ ] **Step 6: Run `make ci AI=1`**

```bash
cd /workspaces/ocr-container/pdomain-ocr-ops/.claude/worktrees/rename-pdomain
make ci AI=1 2>&1 | tee .ci-ai.log | tail -50
```

Expected: green. Verify in the log that `pdomain-book-tools` resolves from the path source (look for the install line referencing the sibling worktree).

- [ ] **Step 7: Commit on rename branch**

```bash
cd /workspaces/ocr-container/pdomain-ocr-ops/.claude/worktrees/rename-pdomain
rm changes-pdomain-ocr-ops.json
git add -A
git commit -m "rename: pdomain-ocr-ops → pdomain-ocr-ops (Phase 2)

Per spec docs/archive/specs/2026-05-26-pd-to-pdomain-rename-design.md §5.
[tool.uv.sources] points at Phase-2 sibling worktree for pdomain-book-tools;
will be flipped to { index = \"pdomain-index-pip\" } in Phase 3 cleanup.
make ci AI=1 green."
```

- [ ] **Step 8: Report**

Record: worktree path, branch, CI green.

---

## Task 5: Rename pdomain-ocr-training (depends on pdomain-book-tools)

Body identical to Task 4. Overrides:

- Repo: `pdomain-ocr-training`. Worktree: `/workspaces/ocr-container/pdomain-ocr-training/.claude/worktrees/rename-pdomain/`.
- Sibling deps: `pdomain-book-tools` only.
- Package directory: `src/pd_ocr_training/` → `src/pdomain_ocr_training/`.
- Step 4 path-source block — exactly one line, same form as Task 4 step 4.
- Pre-condition: Task 2 worktree exists on disk.
- Parallelizable with Tasks 3, 4, 6.

---

## Task 6: Rename pdomain-ui (no Python pd-* deps; codegen against book-tools + ocr-ops wheels)

**Files:** worktree at `/workspaces/ocr-container/pdomain-ui/.claude/worktrees/rename-pdomain/`. Branch `rename/pdomain`. Report `changes-pdomain-ui.json`.

**Repo specifics:**
- No `[project]` dependencies (TypeScript-only library — `pyproject.toml` exists for codegen tooling).
- Has `package.json` — `name` flips from `@concavetrillion/pdomain-ui` to `@pdomain/pdomain-ui`.
- `codegen.versions.json` keys flip (`pdomain-book-tools` → `pdomain-book-tools`, `pdomain-ocr-ops` → `pdomain-ocr-ops`) but the SHA256 hashes will be **wrong** until codegen runs against rebuilt sibling wheels.
- Pre-condition: Tasks 2 (pdomain-book-tools) and 4 (pdomain-ocr-ops) committed on their rename worktrees.

- [ ] **Step 1: Create the rename worktree off main**

```bash
cd /workspaces/ocr-container/pdomain-ui
git fetch origin main --quiet
git worktree add .claude/worktrees/rename-pdomain -b rename/pdomain origin/main
```

- [ ] **Step 2: Run the harness**

```bash
cd /workspaces/ocr-container/pdomain-ui/.claude/worktrees/rename-pdomain
uv run --directory /workspaces/ocr-container python /workspaces/ocr-container/scripts/rename/apply_rename.py \
  --scope=/workspaces/ocr-container/pdomain-ui/.claude/worktrees/rename-pdomain \
  --manifest=/workspaces/ocr-container/scripts/rename/rename-manifest.json \
  --report=./changes-pdomain-ui.json
```

- [ ] **Step 3: Build sibling wheels (book-tools + ocr-ops) for codegen**

```bash
cd /workspaces/ocr-container/pdomain-book-tools/.claude/worktrees/rename-pdomain
make build  # writes dist/pdomain_book_tools-0.14.1-py3-none-any.whl
cd /workspaces/ocr-container/pdomain-ocr-ops/.claude/worktrees/rename-pdomain
make build  # writes dist/pdomain_ocr_ops-0.2.2-py3-none-any.whl
```

Expected: each `dist/` contains a `pdomain_*` wheel.

- [ ] **Step 4: Re-run codegen against rebuilt wheels and refresh SHA256s**

In `codegen.versions.json`, the harness rewrote keys but left old hashes. The wheel filenames have changed (`pd_*` → `pdomain_*`). The codegen scripts (per Explore: `pdomain-ui/package.json` lines 185–186) read this file to pin which wheels to install. Re-run codegen:

```bash
cd /workspaces/ocr-container/pdomain-ui/.claude/worktrees/rename-pdomain
pnpm install
# Update codegen.versions.json wheel filenames + SHA256 by hand from the rebuilt wheels:
sha256sum /workspaces/ocr-container/pdomain-book-tools/.claude/worktrees/rename-pdomain/dist/pdomain_book_tools-*.whl
sha256sum /workspaces/ocr-container/pdomain-ocr-ops/.claude/worktrees/rename-pdomain/dist/pdomain_ocr_ops-*.whl
```

Edit `codegen.versions.json`: replace the `sha256` keys (filenames) and values with the just-computed hashes.

Then point codegen at the local wheel via env override (the codegen script supports `PD_UI_CODEGEN_WHEEL_DIR` or similar — confirm in `pdomain-ui/scripts/codegen-fetch.mjs` at implementation time; if no env override exists, copy the wheels into a known fetch path first):

```bash
cd /workspaces/ocr-container/pdomain-ui/.claude/worktrees/rename-pdomain
pnpm run codegen
```

Expected: `src/types/generated/` regenerated. `pnpm run codegen:check` exits 0.

- [ ] **Step 5: Manual sweep**

```bash
cd /workspaces/ocr-container/pdomain-ui/.claude/worktrees/rename-pdomain
grep -rn 'pd[-_]' \
  --exclude-dir='.git' --exclude-dir='.venv' --exclude-dir='node_modules' \
  --exclude-dir='__pycache__' --exclude-dir='dist' --exclude-dir='build' \
  --exclude-dir='docs/archive' --exclude-dir='src/types/generated' \
  --exclude='*.lock' --exclude='changes-*.json' \
  . | grep -v '# pre-rename:' | grep -v 'historical:'
```

Expected: empty or deliberate-only matches.

- [ ] **Step 6: Run `make ci AI=1`**

```bash
cd /workspaces/ocr-container/pdomain-ui/.claude/worktrees/rename-pdomain
make ci AI=1 2>&1 | tee .ci-ai.log | tail -50
```

Expected: green. Includes `codegen-check`.

- [ ] **Step 7: Build + globally link the renamed package for downstream consumers**

```bash
cd /workspaces/ocr-container/pdomain-ui/.claude/worktrees/rename-pdomain
pnpm run build
pnpm link --global
```

Expected: `pnpm ls --global` shows `@pdomain/pdomain-ui` resolving to this worktree.

- [ ] **Step 8: Commit on rename branch**

```bash
cd /workspaces/ocr-container/pdomain-ui/.claude/worktrees/rename-pdomain
rm changes-pdomain-ui.json
git add -A
git commit -m "rename: @concavetrillion/pdomain-ui → @pdomain/pdomain-ui (Phase 2)

Per spec docs/archive/specs/2026-05-26-pd-to-pdomain-rename-design.md §5.
codegen.versions.json refreshed against rebuilt sibling pdomain-* wheels.
make ci AI=1 green."
```

- [ ] **Step 9: Report**

Record: worktree path, branch, CI green, pnpm-global-link status.

---

## Task 7: Rename pdomain-ocr-cli (depends on pdomain-book-tools)

Body identical to Task 4. Overrides:

- Repo: `pdomain-ocr-cli`. Worktree: `/workspaces/ocr-container/pdomain-ocr-cli/.claude/worktrees/rename-pdomain/`.
- Sibling deps: `pdomain-book-tools`.
- Package directory: `src/pd_ocr_cli/` → `src/pdomain_ocr_cli/`.
- Has `install.sh` — verify harness rewrote wheel-name strings and simple-index URL in it. Manual sweep step must inspect `install.sh` explicitly.
- No JS frontend.
- Pre-condition: Task 2 worktree exists.
- Parallelizable with Tasks 8, 9, 10.

---

## Task 8: Rename pdomain-ocr-labeler-spa (depends on pdomain-book-tools + pdomain-ui [JS])

Body extends Task 4 with JS-side work. Overrides:

- Repo: `pdomain-ocr-labeler-spa`. Worktree: `/workspaces/ocr-container/pdomain-ocr-labeler-spa/.claude/worktrees/rename-pdomain/`.
- Python sibling deps: `pdomain-book-tools`.
- Package directory: `src/pd_ocr_labeler_spa/` → `src/pdomain_ocr_labeler_spa/`.
- JS frontend: `frontend/`. Harness rewrites `package.json` `@concavetrillion/pdomain-ui` → `@pdomain/pdomain-ui` and TS imports.
- Pre-condition: Tasks 2 (book-tools) and 6 (pdomain-ui pnpm-link-global) both committed.
- **Extra step between harness-run and CI:** in the worktree's `frontend/`:

```bash
cd /workspaces/ocr-container/pdomain-ocr-labeler-spa/.claude/worktrees/rename-pdomain/frontend
pnpm install
pnpm link --global @pdomain/pdomain-ui
```

Expected: `node_modules/@pdomain/pdomain-ui` is a symlink into the pdomain-ui rename worktree. Verify with `ls -la node_modules/@pdomain/`.

- Parallelizable with Tasks 7, 9, 10.

---

## Task 9: Rename pdomain-ocr-simple-gui (depends on pdomain-book-tools + pdomain-ocr-ops + pdomain-ui [JS])

Body extends Task 4 with two Python siblings and JS-side work. Overrides:

- Repo: `pdomain-ocr-simple-gui`. Worktree: `/workspaces/ocr-container/pdomain-ocr-simple-gui/.claude/worktrees/rename-pdomain/`.
- Python sibling deps: `pdomain-book-tools`, `pdomain-ocr-ops`. Step 4 path-source block has two entries.
- Package directory: `src/pd_ocr_simple_gui/` → `src/pdomain_ocr_simple_gui/`.
- JS frontend: `frontend/`. Same `pnpm link --global @pdomain/pdomain-ui` step as Task 8.
- Pre-condition: Tasks 2 (book-tools), 4 (ocr-ops), 6 (pdomain-ui).
- Parallelizable with Tasks 7, 8, 10.

---

## Task 10: Rename pdomain-prep-for-pgdp (depends on pdomain-book-tools + pdomain-ocr-ops + pdomain-ui [JS])

Body extends Task 4 with two Python siblings and JS-side work. Overrides:

- Repo: `pdomain-prep-for-pgdp`. Worktree: `/workspaces/ocr-container/pdomain-prep-for-pgdp/.claude/worktrees/rename-pdomain/`.
- Python sibling deps: `pdomain-book-tools`, `pdomain-ocr-ops`.
- Package directory: `src/pd_prep_for_pgdp/` → `src/pdomain_prep_for_pgdp/`.
- JS frontend: `frontend/`. Same `pnpm link --global @pdomain/pdomain-ui`.
- Has `install.sh` — verify rewrite in manual sweep.
- Pre-condition: Tasks 2 (book-tools), 4 (ocr-ops), 6 (pdomain-ui).
- Parallelizable with Tasks 7, 8, 9.

---

## Task 11: Rename pdomain-ocr-trainer-spa (depends on pdomain-book-tools + pdomain-ocr-ops + pdomain-ocr-training + pdomain-ui [JS])

Body extends Task 4 with three Python siblings and JS-side work. Overrides:

- Repo: `pdomain-ocr-trainer-spa`. Worktree: `/workspaces/ocr-container/pdomain-ocr-trainer-spa/.claude/worktrees/rename-pdomain/`.
- Python sibling deps: `pdomain-book-tools`, `pdomain-ocr-ops`, `pdomain-ocr-training`. Step 4 path-source block has three entries.
- Package directory: `src/pd_ocr_trainer_spa/` → `src/pdomain_ocr_trainer_spa/`.
- JS frontend: `frontend/`. Same `pnpm link --global @pdomain/pdomain-ui`.
- Pre-condition: Tasks 2 (book-tools), 4 (ocr-ops), 5 (ocr-training), 6 (pdomain-ui). This is the most-downstream repo — it runs after every other Phase 2 task is committed on its rename worktree.

---

## Task 12: Cohort gate — verify all 10 worktrees green

**Files:** read-only check across all 10 rename worktrees.

- [ ] **Step 1: Confirm every worktree exists, has the branch, and the last commit is the rename commit**

```bash
for repo in pdomain-book-tools pdomain-ocr-synth pdomain-ocr-ops pdomain-ocr-training pdomain-ui pdomain-ocr-cli pdomain-ocr-labeler-spa pdomain-ocr-simple-gui pdomain-prep-for-pgdp pdomain-ocr-trainer-spa; do
  wt="/workspaces/ocr-container/$repo/.claude/worktrees/rename-pdomain"
  branch=$(git -C "$wt" branch --show-current 2>/dev/null || echo "MISSING")
  last=$(git -C "$wt" log -1 --oneline 2>/dev/null || echo "MISSING")
  echo "$repo: branch=$branch last=$last"
done
```

Expected: every line shows `branch=rename/pdomain` and a commit subject starting with `rename:`.

- [ ] **Step 2: Re-run `make ci AI=1` in every worktree (idempotency + freshness check)**

Run in parallel via subagents (one per repo) or sequentially. Each invocation:

```bash
cd /workspaces/ocr-container/<repo>/.claude/worktrees/rename-pdomain
make ci AI=1 2>&1 | tail -5
```

Expected: every repo prints `✅ CI pipeline complete!`.

- [ ] **Step 3: Cross-repo audit grep**

```bash
for repo in pdomain-book-tools pdomain-ocr-synth pdomain-ocr-ops pdomain-ocr-training pdomain-ui pdomain-ocr-cli pdomain-ocr-labeler-spa pdomain-ocr-simple-gui pdomain-prep-for-pgdp pdomain-ocr-trainer-spa; do
  wt="/workspaces/ocr-container/$repo/.claude/worktrees/rename-pdomain"
  hits=$(grep -rn 'pd[-_]' "$wt/src" "$wt/tests" "$wt/pyproject.toml" 2>/dev/null \
    | grep -v '# pre-rename:' | grep -v 'historical:' \
    | wc -l)
  echo "$repo: residual_pd_refs=$hits"
done
```

Expected: every line shows `residual_pd_refs=0` (excluding deliberate historical markers).

- [ ] **Step 4: Gate decision**

If all 10 worktrees pass Steps 1–3, the cohort is green and Task 13 (coordinated landing) is unblocked. If any single repo fails, the cohort gate fails and **no repo pushes** — the window slips. Fix the failing worktree, re-run Steps 1–3, then proceed.

- [ ] **Step 5: Request explicit push authorization from CT**

Per workspace policy: no pushes without explicit say-so. Surface the cohort status (10 green / N red) and ask CT to authorize the coordinated landing before proceeding to Task 13.

---

## Task 13: Coordinated landing (worktree → local-merge → push, in dep order)

**Pre-condition:** Task 12 passed all checks AND CT has explicitly authorized push.

Per workspace `CLAUDE.md`: worktree → local-merge → push (merge-commit, never squash). For each repo, in dep order:

```bash
# Order:
# Wave 1: pdomain-book-tools, pdomain-ocr-synth (no pd-* deps)
# Wave 2: pdomain-ocr-ops, pdomain-ocr-training, pdomain-ui (book-tools only)
# Wave 3: pdomain-ocr-cli, pdomain-ocr-labeler-spa, pdomain-ocr-simple-gui, pdomain-prep-for-pgdp (book-tools + ocr-ops)
# Wave 4: pdomain-ocr-trainer-spa (book-tools + ocr-ops + ocr-training + ui)
```

- [ ] **Step 1: Wave 1 land (pdomain-book-tools, pdomain-ocr-synth)**

For each repo in Wave 1, sequentially:

```bash
cd /workspaces/ocr-container/<repo>
git checkout main
git merge --no-ff rename/pdomain -m "Merge rename/pdomain into main (Phase 2)"
git push origin main
```

Expected: each push lands on `origin/main`. Verify with `gh repo view ConcaveTrillion/<repo> --json defaultBranchRef`.

- [ ] **Step 2: Wave 2 land (pdomain-ocr-ops, pdomain-ocr-training, pdomain-ui)**

For each repo in Wave 2 (parallelizable across repos, but sequence within each repo):

```bash
cd /workspaces/ocr-container/<repo>
git checkout main
git merge --no-ff rename/pdomain -m "Merge rename/pdomain into main (Phase 2)"
git push origin main
```

- [ ] **Step 3: Wave 3 land (pdomain-ocr-cli, pdomain-ocr-labeler-spa, pdomain-ocr-simple-gui, pdomain-prep-for-pgdp)**

Same pattern.

- [ ] **Step 4: Wave 4 land (pdomain-ocr-trainer-spa)**

Same pattern.

- [ ] **Step 5: Per-repo cleanup**

For each of the 10 repos, after its push lands:

```bash
cd /workspaces/ocr-container/<repo>
git worktree remove --force .claude/worktrees/rename-pdomain
git branch -D rename/pdomain
```

Expected: worktree directory gone; branch removed locally.

- [ ] **Step 6: Sanity check**

```bash
for repo in pdomain-book-tools pdomain-ocr-synth pdomain-ocr-ops pdomain-ocr-training pdomain-ui pdomain-ocr-cli pdomain-ocr-labeler-spa pdomain-ocr-simple-gui pdomain-prep-for-pgdp pdomain-ocr-trainer-spa; do
  cd "/workspaces/ocr-container/$repo"
  echo "$repo: $(git log -1 --oneline)"
done
```

Expected: every repo's `main` tip is a merge commit named `Merge rename/pdomain into main (Phase 2)`.

- [ ] **Step 7: Hand off to Phase 3**

Phase 2 is complete. Phase 3 (GH repo rename + index regen) starts immediately — per spec §7, the gap between Phase 2 push and Phase 3 dispatch should be short to minimize the `pdomain-index-pip dispatch failed` warning window.

---

## Rollback procedure (pre-push)

Per-worktree rollback (any single repo abort before Task 13):

```bash
cd /workspaces/ocr-container/<repo>
git worktree remove --force .claude/worktrees/rename-pdomain
git branch -D rename/pdomain
```

Zero residue. The live checkout at `/workspaces/ocr-container/<repo>/` is untouched (was never modified).

If `pdomain-ui` has been globally linked (Task 6 step 7):

```bash
pnpm unlink --global @pdomain/pdomain-ui  # if applicable
```

Cohort-wide rollback (any single repo fails Task 12):

Run the per-worktree rollback for **every** repo. The cohort is all-or-nothing — partial Phase 2 is not a valid state.

Post-push rollback (Task 13 completed): no clean revert. A fresh rename commit going `pdomain-*` → `pd-*` is the recovery path, same cost as the original. Phase 2 push is the point of no comfortable return — explicit in spec §7.

---

## Out of scope (defer to later phases)

- Phase 3: GH repo renames (`gh repo rename`) for all 14 repos; `pdomain-index-pip` + `pdomain-index-npm` regen; flip `[tool.uv.sources]` path-sources back to `{ index = "pdomain-index-pip" }`; flip `pnpm link --global` to registry `@pdomain/pdomain-ui`.
- Phase 4: `pdomain-ocr-ops migrate-suite-state` runtime + state migration.
- Phase 4.5: org transfer `ConcaveTrillion/pdomain-*` → `pdomain/pdomain-*`.
- Phase 5+: secrets rotation, long-tail docs/agents/memory cleanup.

---

## Summary

13 tasks. 1 preflight (Task 1), 10 per-repo rename tasks (Tasks 2–11), 1 cohort gate (Task 12), 1 coordinated landing (Task 13). Tasks 2–11 are subagent-friendly — each is one full unit of work per repo (worktree + harness + manual sweep + sibling-source wiring + CI + commit), sized so one fresh implementation agent can pick it up cold. Tasks 3, 5, 6 parallelize after Task 2 lands; Tasks 7–10 parallelize after Tasks 2, 4, 6 land; Task 11 is sequential at the end of Wave 3 / start of Wave 4 (single-repo). Task 12 is sequential read-only audit. Task 13 is sequential push waves with the workspace's mandatory CT-authorization gate at the boundary. The plan deliberately repeats the per-repo task body in Tasks 2, 3, 4, 6 (full) and Tasks 5, 7–11 (overrides only) per the writing-plans no-placeholders rule — readable out of order, every task self-contained.
