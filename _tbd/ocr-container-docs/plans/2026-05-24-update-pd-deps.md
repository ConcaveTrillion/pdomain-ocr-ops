---
title: update-pd-deps generalized sibling-dep refresh implementation plan
date: 2026-05-24
repo: ConcaveTrillion/ocr-container-meta
spec: docs/archive/specs/2026-05-24-update-pd-deps-design.md
issue: ConcaveTrillion/ocr-container-meta#363
status: active
synced: 2026-05-24
milestone: 18
blocked_by:
- docs/plans/2026-05-24-local-dev-standardization.md
---

# `update-pd-deps` generalized sibling-dep refresh — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `make update-pd-deps` target to the 9 pd-* repos that consume
sibling pd-* deps; each call bumps every sibling (Python + npm) to its
current registry latest, auto-flips around local-dev mode if active, and
leaves the diff staged for human review.

**Architecture:** Per-repo `scripts/update-pd-deps.sh` modeled on
`scripts/do-release.sh`. Queries `pdomain-index-pip` and `pdomain-index-npm` HTTP
endpoints for "latest". Wires `pdomain-index-npm` into 5 npm-consuming repos
as a prerequisite step.

**Tech Stack:** bash + curl/jq + uv + pnpm.

**BLOCKED BY:** `docs/plans/2026-05-24-local-dev-standardization.md` —
this plan's auto-flip logic uses the marker convention + `make local-dev`
target from #362. Do NOT start M2 (the reference implementation) until
#362's M1–M8 have landed.

**Execution shape:** M1 (npm-registry wiring, 5 repos) can run in parallel
once #362 ships. M2 (reference in pdomain-prep-for-pgdp) ships next. M3–M9
(per-repo rollouts) are parallel-dispatch-friendly.

---

## File Structure

**New, per-repo:**
- `<repo>/scripts/update-pd-deps.sh` — the canonical algorithm

**New, npm-consuming repos (5):**
- `<repo>/frontend/.npmrc` (SPAs) or `<repo>/.npmrc` (pdomain-ui) — `@concavetrillion`
  scope registry pointing at pdomain-index-npm

**Modified, per-repo:**
- `<repo>/Makefile` — add `update-pd-deps` target; convert legacy
  `upgrade-pdomain-book-tools` to deprecation alias
- `<repo>/CLAUDE.md` — Commands table entry

**Modified, workspace-level:**
- `/workspaces/ocr-container/docs/process/update-pd-deps.md` — process doc (created in M0)
- `/workspaces/ocr-container/CLAUDE.md` — reference the process doc (M10)

---

## Task 0 — Workspace process doc  {#m0-process-doc}
model: sonnet  effort: S  area: update-pd-deps

Context: Workspace needs a canonical reference for what update-pd-deps does and how it interacts with local-dev mode.
Approach: Write docs/process/update-pd-deps.md per spec — 8 sections (what/source/local-dev interaction/matrix/pdomain-ui special case/human review/index lag/xrefs).
Verification: test -f /workspaces/ocr-container/docs/process/update-pd-deps.md
Acceptance:
- [ ] docs/process/update-pd-deps.md exists and is committed
- [ ] All 8 sections per the task body are present
- [ ] Linked from CLAUDE.md (handled in Task 10)

**Goal:** Doc explaining what `update-pd-deps` does, how it interacts with
`local-dev`, and the human-review expectations.

### Step 0.1: Write `docs/process/update-pd-deps.md`

**Files:**
- Create: `/workspaces/ocr-container/docs/process/update-pd-deps.md`

- [ ] **Step 1: Draft content (8 short sections)**

1. **What it does** — bumps every sibling pd-* dep (Python + npm) to current
   registry latest; leaves diff staged; does NOT commit.
2. **Source of truth** — `pdomain-index-pip` for Python wheels; `pdomain-index-npm` for
   `@concavetrillion/*` packages. Not GitHub releases (which can lead the
   index by hours).
3. **Local-dev interaction** — if marker `.venv/.pd-local-mode` is present,
   the target auto-flips out of local-dev mode, bumps, flips back. Loud
   per-step messaging.
4. **Per-repo presence** — table from spec §5.2: 9 repos have the target;
   pdomain-book-tools, pdomain-ocr-synth, pd-png-optimizer don't (no pd-* deps).
5. **pdomain-ui special case** — edits `codegen.versions.json` instead of
   pyproject.toml; triggers `make codegen` after the bump.
6. **Human review expectations** — always run `make ci` and review the diff
   before committing. Pre-1.0 pd-* repos may have breaking changes; the
   target doesn't guard against them.
7. **What if pdomain-index-pip lags GitHub?** — the index publishes via the
   release-workflow; if a release was just tagged, the index may not have
   it yet. Re-run after the workflow completes.
8. **Cross-references** — link to spec, link to [local-dev process doc](local-dev.md),
   link to `scripts/update-pd-deps.sh` as the reference.

- [ ] **Step 2: Commit**

```bash
cd /workspaces/ocr-container
git add docs/process/update-pd-deps.md
git commit -m "docs(process): canonical update-pd-deps pattern (#363)"
```

---

## Task 1 — Wire `pdomain-index-npm` in 5 npm-consuming repos  {#m1-wire-npm-registry}
model: sonnet  effort: M  area: update-pd-deps

Context: npm-side dep resolution currently has no scope override; the 5 npm-consuming repos (4 SPAs + pdomain-ui) need an .npmrc pointing the @concavetrillion scope at pdomain-index-npm before update-pd-deps can fetch npm versions.
Approach: For each of the 5 repos, create .npmrc (frontend/.npmrc for SPAs, repo-root .npmrc for pdomain-ui) with @concavetrillion:registry=https://concavetrillion.github.io/pdomain-index-npm/, commit per repo. Parallel-dispatch one agent per repo.
Verification: for r in pdomain-ocr-simple-gui pdomain-ocr-labeler-spa pdomain-ocr-trainer-spa pdomain-prep-for-pgdp; do test -f $r/frontend/.npmrc; done && test -f pdomain-ui/.npmrc
Acceptance:
- [ ] 4 SPAs each have frontend/.npmrc with @concavetrillion scope registry
- [ ] pdomain-ui has root-level .npmrc with the same
- [ ] All 5 commits land on each repo's main

**Goal:** Add `.npmrc` per-repo so npm-side dep resolution uses the workspace
self-hosted registry. Prerequisite for the npm portion of `update-pd-deps`.

**Repos:** pdomain-ocr-simple-gui, pdomain-ocr-labeler-spa, pdomain-ocr-trainer-spa,
pdomain-prep-for-pgdp (`.npmrc` in `frontend/`), pdomain-ui (`.npmrc` in repo root).

**Dispatch shape:** parallel — one agent per repo.

### Step 1.1: pdomain-ocr-simple-gui — wire `.npmrc`

**Files:**
- Create: `pdomain-ocr-simple-gui/frontend/.npmrc`

- [ ] **Step 1: Write the .npmrc**

```ini
# scoped registry for @concavetrillion/* (pd-* npm packages)
@concavetrillion:registry=https://concavetrillion.github.io/pdomain-index-npm/
```

- [ ] **Step 2: Verify resolution still works**

```bash
cd pdomain-ocr-simple-gui/frontend
pnpm install
```
Expected: install completes; no changes to package.json or pnpm-lock.yaml versions.

- [ ] **Step 3: Commit**

```bash
cd pdomain-ocr-simple-gui
git add frontend/.npmrc
git commit -m "chore(npm): wire pdomain-index-npm scoped registry (#363 prereq)"
```

### Step 1.2: pdomain-ocr-labeler-spa — wire `.npmrc`

Identical to 1.1. Path: `pdomain-ocr-labeler-spa/frontend/.npmrc`.

### Step 1.3: pdomain-ocr-trainer-spa — wire `.npmrc`

Identical. Path: `pdomain-ocr-trainer-spa/frontend/.npmrc`.

### Step 1.4: pdomain-prep-for-pgdp — wire `.npmrc`

Identical. Path: `pdomain-prep-for-pgdp/frontend/.npmrc`.

### Step 1.5: pdomain-ui — wire `.npmrc`

**Files:**
- Create: `pdomain-ui/.npmrc`

- [ ] **Step 1: Append to existing .npmrc** (pdomain-ui already has a `store-dir` line)

```ini
# scoped registry for @concavetrillion/* (pd-* npm packages)
@concavetrillion:registry=https://concavetrillion.github.io/pdomain-index-npm/
```

- [ ] **Step 2: Verify**

```bash
cd pdomain-ui
pnpm install
```

- [ ] **Step 3: Commit**

```bash
git add .npmrc
git commit -m "chore(npm): wire pdomain-index-npm scoped registry (#363 prereq)"
```

---

## Task 2 — Reference implementation in pdomain-prep-for-pgdp  {#m2-reference-impl}
model: sonnet  effort: L  area: update-pd-deps
Blocked-by: #m1-wire-npm-registry

Context: pdomain-prep-for-pgdp is the reference repo; its update-pd-deps.sh becomes the canonical template that M3–M9 copy from.
Approach: In a pdomain-prep-for-pgdp worktree, create scripts/update-pd-deps.sh querying pdomain-index-pip + pdomain-index-npm for latest, auto-flipping around local-dev marker, leaving diff staged. Wire Makefile target, deprecate upgrade-pdomain-book-tools, smoke-test, commit.
Verification: cd pdomain-prep-for-pgdp && make update-pd-deps && git diff --cached --quiet || echo "diff staged"
Acceptance:
- [ ] scripts/update-pd-deps.sh exists and is executable
- [ ] Makefile has update-pd-deps target + upgrade-pdomain-book-tools deprecation alias
- [ ] Auto-flip around local-dev marker works
- [ ] make ci AI=1 green


**Goal:** Build the canonical `scripts/update-pd-deps.sh` in pdomain-prep-for-pgdp,
covering Python (pdomain-book-tools, pdomain-ops) + npm (@concavetrillion/pdomain-ui).
Subsequent repos copy from here.

### Step 2.1: Create `scripts/update-pd-deps.sh`

**Files:**
- Create: `pdomain-prep-for-pgdp/scripts/update-pd-deps.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
# scripts/update-pd-deps.sh — bump every pd-* sibling dep to registry latest.
#
# - Python: queries https://concavetrillion.github.io/pdomain-index-pip/simple/<pkg>/
# - npm:    queries https://concavetrillion.github.io/pdomain-index-npm/@concavetrillion/<pkg>
#
# Auto-flips out of local-dev mode if marker present; bumps; restores.
# Leaves diff staged for human review — does NOT commit.
set -euo pipefail

# ─── Repo-specific configuration ──────────────────────────────────────
PY_DEPS=(pdomain-book-tools pdomain-ops)
NPM_DEPS=(pdomain-ui)                       # @concavetrillion/<pkg>
PYPROJECT="pyproject.toml"
FRONTEND_PACKAGE_JSON="frontend/package.json"
HAS_FRONTEND=true
# Set CODEGEN_JSON= for pdomain-ui only (not applicable here)
CODEGEN_JSON=""
HAS_LOCAL_DEV=true                     # whether this repo supports local-dev mode
# ──────────────────────────────────────────────────────────────────────

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARKER="$REPO_ROOT/.venv/.pd-local-mode"
PIP_INDEX_BASE="https://concavetrillion.github.io/pdomain-index-pip/simple"
NPM_INDEX_BASE="https://concavetrillion.github.io/pdomain-index-npm"

say() { echo "[update-pd-deps] $*"; }
loud() { echo; echo "============================================"; echo "$*"; echo "============================================"; echo; }

# Set up exit trap to restore local-dev if we flip out
FLIPPED=false
restore_if_flipped() {
  if [[ "$FLIPPED" == "true" ]]; then
    loud "→ ERROR before restore. Run 'make local-dev' to restore local mode manually."
  fi
}
trap restore_if_flipped EXIT

# ─── Step 1: Detect local-dev mode (skip if repo doesn't support) ──
if [[ "$HAS_LOCAL_DEV" == "true" ]] && [[ -f "$MARKER" ]]; then
  loud "⚠️  You're in local-dev mode. update-pd-deps requires registry mode."
  cat <<EOF
I will:
  (1) flip out of local-dev (uninstall editable siblings)
  (2) bump pd-* deps from pdomain-index-pip / pdomain-index-npm
  (3) restore local-dev (re-install siblings editable)

EOF
  if [[ "${FORCE:-}" != "1" ]]; then
    read -r -p "Continue? [y/N] " ans
    [[ "$ans" == "y" || "$ans" == "Y" ]] || { say "abort."; exit 1; }
  fi

  # Flip out
  for s in "${PY_DEPS[@]}"; do
    say "→ uv pip uninstall $s"
    uv pip uninstall "$s" || true
  done
  if [[ "$HAS_FRONTEND" == "true" ]]; then
    for s in "${NPM_DEPS[@]}"; do
      say "→ pnpm unlink @concavetrillion/$s"
      (cd "$REPO_ROOT/frontend" && pnpm unlink "@concavetrillion/$s" 2>/dev/null) || true
    done
  fi
  rm -f "$MARKER"
  FLIPPED=true
  loud "✓ flipped to registry mode."
fi

# ─── Step 2: Resolve latest versions ──────────────────────────────────
declare -A PY_LATEST NPM_LATEST

latest_pip() {
  local pkg=$1
  # GET simple-index, extract highest semver from filename ".../<pkg>-X.Y.Z-*"
  curl -fsSL "$PIP_INDEX_BASE/$pkg/" \
    | grep -oE "${pkg}-[0-9]+\.[0-9]+\.[0-9]+[^.-]*" \
    | sed "s/^${pkg}-//" \
    | sort -V | tail -1
}

latest_npm() {
  local pkg=$1
  curl -fsSL "$NPM_INDEX_BASE/@concavetrillion/$pkg" \
    | jq -r '."dist-tags".latest'
}

say "→ querying pdomain-index-pip for Python deps…"
for p in "${PY_DEPS[@]}"; do
  PY_LATEST[$p]=$(latest_pip "$p")
  say "  $p latest: ${PY_LATEST[$p]}"
done

if [[ "$HAS_FRONTEND" == "true" ]]; then
  say "→ querying pdomain-index-npm for npm deps…"
  for p in "${NPM_DEPS[@]}"; do
    NPM_LATEST[$p]=$(latest_npm "$p")
    say "  @concavetrillion/$p latest: ${NPM_LATEST[$p]}"
  done
fi

# ─── Step 3: Bump pyproject.toml ──────────────────────────────────────
say "→ bumping $PYPROJECT"
for p in "${PY_DEPS[@]}"; do
  new=${PY_LATEST[$p]}
  # In-place: replace `"<pkg>>=X.Y.Z"` with `"<pkg>>=<new>"`
  python3 -c "
import re, sys
from pathlib import Path
p = Path('$PYPROJECT')
t = p.read_text()
pat = re.compile(r'(\"$p)>=([0-9.]+[^\"]*)(\")')
new = pat.sub(rf'\1>=$new\3', t)
p.write_text(new)
"
done

# ─── Step 4: Bump frontend/package.json ───────────────────────────────
if [[ "$HAS_FRONTEND" == "true" ]]; then
  say "→ bumping $FRONTEND_PACKAGE_JSON"
  for p in "${NPM_DEPS[@]}"; do
    new=${NPM_LATEST[$p]}
    (cd "$REPO_ROOT/frontend" && \
      jq --arg new "$new" \
         '(.dependencies["@concavetrillion/'"$p"'"] // empty) |= "^"+$new
          | (.peerDependencies["@concavetrillion/'"$p"'"] // empty) |= "^"+$new' \
         package.json > package.json.tmp && mv package.json.tmp package.json)
  done
fi

# ─── Step 5: Bump codegen.versions.json (pdomain-ui only) ─────────────────
if [[ -n "$CODEGEN_JSON" ]] && [[ -f "$CODEGEN_JSON" ]]; then
  say "→ bumping $CODEGEN_JSON"
  for p in "${PY_DEPS[@]}"; do
    new=${PY_LATEST[$p]}
    jq --arg new "$new" --arg p "$p" '.[$p] = $new' \
       "$CODEGEN_JSON" > "$CODEGEN_JSON.tmp" && mv "$CODEGEN_JSON.tmp" "$CODEGEN_JSON"
  done
  # pdomain-ui requires codegen re-run after version bump
  say "→ make codegen (regenerate generated TS types)"
  make codegen
fi

# ─── Step 6: Re-lock + sync ──────────────────────────────────────────
say "→ uv lock && uv sync"
uv lock
uv sync

if [[ "$HAS_FRONTEND" == "true" ]]; then
  say "→ pnpm install"
  (cd "$REPO_ROOT/frontend" && pnpm install)
fi

# ─── Step 7: Print summary ───────────────────────────────────────────
loud "Bump summary:"
for p in "${PY_DEPS[@]}"; do
  echo "  $p → ${PY_LATEST[$p]}"
done
if [[ "$HAS_FRONTEND" == "true" ]]; then
  for p in "${NPM_DEPS[@]}"; do
    echo "  @concavetrillion/$p → ${NPM_LATEST[$p]}"
  done
fi

# ─── Step 8: Restore local-dev if we flipped ─────────────────────────
if [[ "$FLIPPED" == "true" ]]; then
  loud "→ restoring local-dev mode (make local-dev)"
  make local-dev
  FLIPPED=false        # disable the trap's error message
  loud "✓ local-dev restored."
fi

# ─── Step 9: Remind user to review ───────────────────────────────────
loud "✓ done. Review the diff with 'git diff' and run 'make ci' before committing."
```

- [ ] **Step 2: chmod +x**

```bash
chmod +x pdomain-prep-for-pgdp/scripts/update-pd-deps.sh
```

### Step 2.2: Wire Makefile target + deprecate `upgrade-pdomain-book-tools`

**Files:**
- Modify: `pdomain-prep-for-pgdp/Makefile`

- [ ] **Step 1: Add the target**

```makefile
# ─── pd-* sibling dep updates (spec #363) ──────────────────────────────

update-pd-deps: ## Bump all pd-* sibling deps to registry latest (does NOT commit)
	@./scripts/update-pd-deps.sh

.PHONY: update-pd-deps
```

- [ ] **Step 2: Convert legacy `upgrade-pdomain-book-tools` to deprecation alias**

Find the existing `upgrade-pdomain-book-tools` target and replace its recipe:

```makefile
upgrade-pdomain-book-tools: ## DEPRECATED: use update-pd-deps
	@echo "warning: 'upgrade-pdomain-book-tools' is deprecated; use 'update-pd-deps'"
	@$(MAKE) update-pd-deps
```

### Step 2.3: Smoke test the reference

- [ ] **Step 1: Test in registry mode**

Ensure not in local-dev mode:
```bash
rm -f .venv/.pd-local-mode
make update-pd-deps
```
Expected: script queries registries, edits pyproject.toml + frontend/package.json,
re-locks, prints summary, doesn't commit. `git status` shows modified files.

- [ ] **Step 2: Inspect the diff**

```bash
git diff pyproject.toml frontend/package.json
```
Expected: pdomain-book-tools, pdomain-ops, @concavetrillion/pdomain-ui versions all bumped (or "already current" report).

- [ ] **Step 3: Verify `make ci` still passes after the bump**

```bash
make ci AI=1
```
Expected: green.

- [ ] **Step 4: Reset the bumps (we're not committing here yet)**

```bash
git restore pyproject.toml frontend/package.json uv.lock frontend/pnpm-lock.yaml
```

- [ ] **Step 5: Test in local-dev mode (auto-flip path)**

```bash
make local-dev
FORCE=1 make update-pd-deps    # FORCE to skip interactive prompt
```
Expected: prints loud warnings at each phase; ends with `local-dev restored` and the diff still present in pyproject.toml / package.json.

- [ ] **Step 6: Cleanup**

```bash
git restore pyproject.toml frontend/package.json uv.lock frontend/pnpm-lock.yaml
```

### Step 2.4: Commit

- [ ] **Step 1: Stage + commit**

```bash
git add scripts/update-pd-deps.sh Makefile
git commit -m "chore(update-pd-deps): canonical script + Make target (#363)

Reference implementation for the workspace-wide update-pd-deps target
(spec docs/archive/specs/2026-05-24-update-pd-deps-design.md). Bumps Python
deps (pdomain-book-tools, pdomain-ops) + npm deps (@concavetrillion/pdomain-ui)
from pdomain-index-pip / pdomain-index-npm. Auto-flips around local-dev mode.
Leaves diff staged for human review.

Deprecates 'upgrade-pdomain-book-tools' (now an alias)."
```

---

## Task 3 — pdomain-ocr-cli  {#m3-pdomain-ocr-cli}
model: sonnet  effort: S  area: update-pd-deps
Blocked-by: #m2-reference-impl

Context: pdomain-ocr-cli has legacy upgrade-pdomain-book-tools target; needs canonical update-pd-deps with single Python sibling.
Approach: In a pdomain-ocr-cli worktree, copy scripts/update-pd-deps.sh from pdomain-prep-for-pgdp, adapt SIBLINGS=(pdomain-book-tools), wire Makefile target + deprecation alias, smoke, commit.
Verification: cd pdomain-ocr-cli && make update-pd-deps && make ci AI=1
Acceptance:
- [ ] scripts/update-pd-deps.sh in pdomain-ocr-cli
- [ ] Makefile has update-pd-deps + upgrade-pdomain-book-tools deprecation
- [ ] make ci AI=1 green


**Goal:** Add `update-pd-deps` (Python only — pdomain-book-tools sole dep).

### Step 3.1: Copy + adapt the script

**Files:**
- Create: `pdomain-ocr-cli/scripts/update-pd-deps.sh`

- [ ] **Step 1: Copy from pdomain-prep-for-pgdp**

```bash
cp ../pdomain-prep-for-pgdp/scripts/update-pd-deps.sh scripts/update-pd-deps.sh
chmod +x scripts/update-pd-deps.sh
```

- [ ] **Step 2: Adapt the config block at the top**

Replace lines under `# ─── Repo-specific configuration ──`:

```bash
PY_DEPS=(pdomain-book-tools)
NPM_DEPS=()
PYPROJECT="pyproject.toml"
FRONTEND_PACKAGE_JSON=""
HAS_FRONTEND=false
CODEGEN_JSON=""
HAS_LOCAL_DEV=true
```

### Step 3.2: Wire Makefile + deprecate legacy

- [ ] **Step 1: Add target**

```makefile
update-pd-deps: ## Bump all pd-* sibling deps to registry latest (does NOT commit)
	@./scripts/update-pd-deps.sh

.PHONY: update-pd-deps
```

- [ ] **Step 2: Convert existing `upgrade-pdomain-book-tools` to alias**

```makefile
upgrade-pdomain-book-tools: ## DEPRECATED: use update-pd-deps
	@echo "warning: 'upgrade-pdomain-book-tools' is deprecated; use 'update-pd-deps'"
	@$(MAKE) update-pd-deps
```

### Step 3.3: Smoke + commit

- [ ] **Step 1: Test**

```bash
rm -f .venv/.pd-local-mode
make update-pd-deps
git diff pyproject.toml
make ci AI=1
git restore pyproject.toml uv.lock
```

- [ ] **Step 2: Commit**

```bash
git add scripts/update-pd-deps.sh Makefile
git commit -m "chore(update-pd-deps): add update-pd-deps target (pdomain-ocr-cli, #363)"
```

---

## Task 4 — pdomain-ops  {#m4-pdomain-ops}
model: sonnet  effort: S  area: update-pd-deps
Blocked-by: #m2-reference-impl

Context: pdomain-ops needs update-pd-deps with single Python sibling; no legacy target to deprecate.
Approach: In a pdomain-ops worktree, copy scripts/update-pd-deps.sh from pdomain-prep-for-pgdp, adapt SIBLINGS=(pdomain-book-tools), wire Makefile target, smoke, commit.
Verification: cd pdomain-ops && make update-pd-deps && make ci AI=1
Acceptance:
- [ ] scripts/update-pd-deps.sh in pdomain-ops
- [ ] Makefile has update-pd-deps target
- [ ] make ci AI=1 green


**Goal:** Add `update-pd-deps` (Python only — pdomain-book-tools sole dep).

### Step 4.1: Copy + adapt script

```bash
cp ../pdomain-prep-for-pgdp/scripts/update-pd-deps.sh scripts/update-pd-deps.sh
chmod +x scripts/update-pd-deps.sh
```

Config:
```bash
PY_DEPS=(pdomain-book-tools)
NPM_DEPS=()
HAS_FRONTEND=false
CODEGEN_JSON=""
HAS_LOCAL_DEV=true
```

### Step 4.2: Wire Makefile target (no legacy to deprecate — pdomain-ops has no upgrade-pdomain-book-tools)

```makefile
update-pd-deps: ## Bump all pd-* sibling deps to registry latest (does NOT commit)
	@./scripts/update-pd-deps.sh

.PHONY: update-pd-deps
```

### Step 4.3: Smoke + commit

```bash
git commit -m "chore(update-pd-deps): add update-pd-deps target (pdomain-ops, #363)"
```

---

## Task 5 — pdomain-ocr-training  {#m5-pdomain-ocr-training}
model: sonnet  effort: S  area: update-pd-deps
Blocked-by: #m2-reference-impl

Context: pdomain-ocr-training needs update-pd-deps with single Python sibling; mirrors Task 4.
Approach: In a pdomain-ocr-training worktree, copy scripts/update-pd-deps.sh, adapt SIBLINGS=(pdomain-book-tools), wire Makefile target, smoke, commit.
Verification: cd pdomain-ocr-training && make update-pd-deps && make ci AI=1
Acceptance:
- [ ] scripts/update-pd-deps.sh in pdomain-ocr-training
- [ ] Makefile has update-pd-deps target
- [ ] make ci AI=1 green


**Goal:** Add `update-pd-deps` (Python only — pdomain-book-tools sole dep). No
legacy `upgrade-pdomain-book-tools` to deprecate.

### Step 5.1: Copy + adapt script

**Files:**
- Create: `pdomain-ocr-training/scripts/update-pd-deps.sh`

- [ ] **Step 1: Copy**

```bash
cp ../pdomain-prep-for-pgdp/scripts/update-pd-deps.sh scripts/update-pd-deps.sh
chmod +x scripts/update-pd-deps.sh
```

- [ ] **Step 2: Adapt config block at top of script**

```bash
PY_DEPS=(pdomain-book-tools)
NPM_DEPS=()
PYPROJECT="pyproject.toml"
FRONTEND_PACKAGE_JSON=""
HAS_FRONTEND=false
CODEGEN_JSON=""
HAS_LOCAL_DEV=true
```

### Step 5.2: Wire Makefile

**Files:**
- Modify: `pdomain-ocr-training/Makefile`

- [ ] **Step 1: Add target**

```makefile
update-pd-deps: ## Bump all pd-* sibling deps to registry latest (does NOT commit)
	@./scripts/update-pd-deps.sh

.PHONY: update-pd-deps
```

### Step 5.3: Smoke + commit

- [ ] **Step 1: Test**

```bash
rm -f .venv/.pd-local-mode
make update-pd-deps
git diff pyproject.toml
make ci AI=1
git restore pyproject.toml uv.lock
```

- [ ] **Step 2: Commit**

```bash
git add scripts/update-pd-deps.sh Makefile
git commit -m "chore(update-pd-deps): add update-pd-deps target (pdomain-ocr-training, #363)"
```

---

## Task 6 — pdomain-ocr-simple-gui  {#m6-pdomain-ocr-simple-gui}
model: sonnet  effort: S  area: update-pd-deps
Blocked-by: #m2-reference-impl

Context: pdomain-ocr-simple-gui is SPA needing update-pd-deps for 2 Python siblings + pdomain-ui (npm).
Approach: In a pdomain-ocr-simple-gui worktree, copy scripts/update-pd-deps.sh, adapt PY_SIBLINGS=(pdomain-book-tools pdomain-ops) + NPM_SIBLINGS=(pdomain-ui), wire Makefile target, smoke, commit.
Verification: cd pdomain-ocr-simple-gui && make update-pd-deps && make ci AI=1
Acceptance:
- [ ] scripts/update-pd-deps.sh in pdomain-ocr-simple-gui
- [ ] Makefile has update-pd-deps target
- [ ] make ci AI=1 green


**Goal:** SPA pattern. Python: pdomain-book-tools, pdomain-ops. npm: pdomain-ui.

### Step 6.1: Copy + adapt script

```bash
cp ../pdomain-prep-for-pgdp/scripts/update-pd-deps.sh scripts/update-pd-deps.sh
chmod +x scripts/update-pd-deps.sh
```

Config:
```bash
PY_DEPS=(pdomain-book-tools pdomain-ops)
NPM_DEPS=(pdomain-ui)
HAS_FRONTEND=true
CODEGEN_JSON=""
HAS_LOCAL_DEV=true
```

### Step 6.2: Wire Makefile (no legacy alias)

```makefile
update-pd-deps: ## Bump all pd-* sibling deps to registry latest (does NOT commit)
	@./scripts/update-pd-deps.sh

.PHONY: update-pd-deps
```

### Step 6.3: Smoke + commit

```bash
git commit -m "chore(update-pd-deps): add update-pd-deps target (pdomain-ocr-simple-gui, #363)"
```

---

## Task 7 — pdomain-ocr-labeler-spa  {#m7-pdomain-ocr-labeler-spa}
model: sonnet  effort: S  area: update-pd-deps
Blocked-by: #m2-reference-impl

Context: pdomain-ocr-labeler-spa is SPA needing update-pd-deps for pdomain-book-tools (Python) + pdomain-ui (npm).
Approach: In a pdomain-ocr-labeler-spa worktree, copy scripts/update-pd-deps.sh, adapt PY_SIBLINGS=(pdomain-book-tools) + NPM_SIBLINGS=(pdomain-ui), wire Makefile target, smoke, commit.
Verification: cd pdomain-ocr-labeler-spa && make update-pd-deps && make ci AI=1
Acceptance:
- [ ] scripts/update-pd-deps.sh in pdomain-ocr-labeler-spa
- [ ] Makefile has update-pd-deps target
- [ ] make ci AI=1 green


**Goal:** Python: pdomain-book-tools. npm: pdomain-ui.

### Step 7.1: Copy + adapt script

```bash
cp ../pdomain-prep-for-pgdp/scripts/update-pd-deps.sh scripts/update-pd-deps.sh
chmod +x scripts/update-pd-deps.sh
```

Config:
```bash
PY_DEPS=(pdomain-book-tools)
NPM_DEPS=(pdomain-ui)
HAS_FRONTEND=true
CODEGEN_JSON=""
HAS_LOCAL_DEV=true
```

### Step 7.2: Wire Makefile + commit (per M6)

```bash
git commit -m "chore(update-pd-deps): add update-pd-deps target (pdomain-ocr-labeler-spa, #363)"
```

---

## Task 8 — pdomain-ocr-trainer-spa  {#m8-pdomain-ocr-trainer-spa}
model: sonnet  effort: S  area: update-pd-deps
Blocked-by: #m2-reference-impl

Context: pdomain-ocr-trainer-spa is SPA needing update-pd-deps for 3 Python siblings + pdomain-ui (npm).
Approach: In a pdomain-ocr-trainer-spa worktree, copy scripts/update-pd-deps.sh, adapt PY_SIBLINGS=(pdomain-book-tools pdomain-ops pdomain-ocr-training) + NPM_SIBLINGS=(pdomain-ui), wire Makefile target, smoke, commit.
Verification: cd pdomain-ocr-trainer-spa && make update-pd-deps && make ci AI=1
Acceptance:
- [ ] scripts/update-pd-deps.sh in pdomain-ocr-trainer-spa
- [ ] Makefile has update-pd-deps target
- [ ] make ci AI=1 green


**Goal:** Python: pdomain-book-tools, pdomain-ops, pdomain-ocr-training. npm: pdomain-ui.

### Step 8.1: Copy + adapt script

```bash
cp ../pdomain-prep-for-pgdp/scripts/update-pd-deps.sh scripts/update-pd-deps.sh
chmod +x scripts/update-pd-deps.sh
```

Config:
```bash
PY_DEPS=(pdomain-book-tools pdomain-ops pdomain-ocr-training)
NPM_DEPS=(pdomain-ui)
HAS_FRONTEND=true
CODEGEN_JSON=""
HAS_LOCAL_DEV=true
```

### Step 8.2: Wire Makefile + commit (per M6)

```bash
git commit -m "chore(update-pd-deps): add update-pd-deps target (pdomain-ocr-trainer-spa, #363)"
```

---

## Task 9 — pdomain-ui (special case — codegen.versions.json)  {#m9-pdomain-ui}
model: sonnet  effort: M  area: update-pd-deps
Blocked-by: #m2-reference-impl

Context: pdomain-ui edits codegen.versions.json (not pyproject.toml) and triggers make codegen after the bump; special-case script.
Approach: In a pdomain-ui worktree, create scripts/update-pd-deps.sh that updates codegen.versions.json from pdomain-index-pip (pdomain-book-tools version), runs make codegen, leaves diff staged. Wire Makefile target, smoke, commit.
Verification: cd pdomain-ui && make update-pd-deps && make ci AI=1
Acceptance:
- [ ] scripts/update-pd-deps.sh in pdomain-ui (codegen.versions.json variant)
- [ ] Makefile has update-pd-deps target
- [ ] make codegen runs after bump; make ci AI=1 green


**Goal:** pdomain-ui consumes pdomain-book-tools + pdomain-ops via `codegen.versions.json`
(pinned wheel versions for the codegen pipeline). No pyproject.toml deps to
bump; no @concavetrillion/* npm deps. The script edits a JSON file and triggers
`make codegen` after the bump.

### Step 9.1: Copy + adapt script

**Files:**
- Create: `pdomain-ui/scripts/update-pd-deps.sh`

- [ ] **Step 1: Copy**

```bash
cp ../pdomain-prep-for-pgdp/scripts/update-pd-deps.sh scripts/update-pd-deps.sh
chmod +x scripts/update-pd-deps.sh
```

- [ ] **Step 2: Adapt config**

```bash
PY_DEPS=(pdomain-book-tools pdomain-ops)
NPM_DEPS=()
PYPROJECT=""                          # no Python deps in pdomain-ui's pyproject
FRONTEND_PACKAGE_JSON=""              # no @concavetrillion/* in package.json
HAS_FRONTEND=false                    # no frontend/ — pdomain-ui IS the frontend
CODEGEN_JSON="codegen.versions.json"  # ← the actual source of truth
HAS_LOCAL_DEV=false                   # pdomain-ui has no local-dev (leaf per #362)
```

- [ ] **Step 3: Guard the empty PYPROJECT case**

In the script, wrap the "bump pyproject" section:
```bash
if [[ -n "$PYPROJECT" ]]; then
  # ... bump pyproject.toml ...
fi
```
(The reference already wraps codegen + frontend; verify the pyproject section
is similarly guarded, or add the guard now.)

### Step 9.2: Wire Makefile (no legacy alias)

**Files:**
- Modify: `pdomain-ui/Makefile`

```makefile
update-pd-deps: ## Bump pd-* codegen pins to registry latest + re-run codegen
	@./scripts/update-pd-deps.sh

.PHONY: update-pd-deps
```

### Step 9.3: Smoke + commit

- [ ] **Step 1: Test**

```bash
make update-pd-deps
git diff codegen.versions.json src/types/generated/
make ci AI=1                   # codegen-check should pass now (deps freshly resolved)
git restore codegen.versions.json src/types/generated/
```

- [ ] **Step 2: Commit**

```bash
git add scripts/update-pd-deps.sh Makefile
git commit -m "chore(update-pd-deps): add update-pd-deps target (pdomain-ui, #363)

Edits codegen.versions.json (pdomain-ui's source of truth for upstream
pdomain-book-tools + pdomain-ops wheel pins) and re-runs make codegen so
generated TS types stay in sync. No PYPROJECT / NPM_DEPS path used."
```

---

## Task 10 — Workspace CLAUDE.md refresh  {#m10-claude-md-refresh}
model: sonnet  effort: S  area: update-pd-deps
Blocked-by: #m3-pdomain-ocr-cli, #m4-pdomain-ops, #m5-pdomain-ocr-training, #m6-pdomain-ocr-simple-gui, #m7-pdomain-ocr-labeler-spa, #m8-pdomain-ocr-trainer-spa, #m9-pdomain-ui

Context: After all per-repo rollouts land, the workspace + per-repo CLAUDE.md docs need to reference update-pd-deps and link the process doc.
Approach: Update /workspaces/ocr-container/CLAUDE.md with an Updating sibling pd-* deps subsection; for each of the 9 dependent repos, add make update-pd-deps to the Commands table in <repo>/CLAUDE.md; commit per repo.
Verification: grep -q 'make update-pd-deps' /workspaces/ocr-container/CLAUDE.md
Acceptance:
- [ ] Workspace CLAUDE.md has Updating sibling pd-* deps subsection
- [ ] Each of the 9 dependent repos' CLAUDE.md Commands table includes make update-pd-deps
- [ ] Per-repo commits land on each repo's main


**Goal:** Document `update-pd-deps` in workspace and per-repo CLAUDE.md.

### Step 10.1: Update workspace CLAUDE.md

**Files:**
- Modify: `/workspaces/ocr-container/CLAUDE.md`

- [ ] **Step 1: Add an `update-pd-deps` subsection (near the local-dev subsection from #362)**

```markdown
## Updating sibling pd-* deps

When you want to pick up newly-released versions of upstream pd-* siblings
without bumping unrelated deps, run `make update-pd-deps` in the affected
repo. See [`docs/process/update-pd-deps.md`](docs/process/update-pd-deps.md)
for the full pattern.

- Queries `pdomain-index-pip` (Python) + `pdomain-index-npm` (npm) for latest versions
- Auto-flips around local-dev mode if active (loud per-step messaging)
- Leaves the diff staged — always run `make ci` and review before committing
  (pre-1.0 pd-* repos may have breaking changes)

Replaces the legacy `upgrade-pdomain-book-tools` (now a deprecation alias).
```

- [ ] **Step 2: Commit**

```bash
cd /workspaces/ocr-container
git add CLAUDE.md
git commit -m "docs(workspace): document update-pd-deps (#363)"
```

### Step 10.2: Per-repo CLAUDE.md Commands table

For each of the 9 repos that gained `update-pd-deps`:

- [ ] **Step 1: Add row to Commands table**

```markdown
| `make update-pd-deps` | bump pd-* sibling deps to registry latest (does NOT commit) |
```

- [ ] **Step 2: For repos with legacy `upgrade-pdomain-book-tools` alias still present, add a deprecation note**

```markdown
| `make upgrade-pdomain-book-tools` | DEPRECATED — use `update-pd-deps` |
```

- [ ] **Step 3: Commit per repo**

```bash
git -C <repo> add CLAUDE.md
git -C <repo> commit -m "docs(claude): document update-pd-deps (#363)"
```

---

## Final acceptance

- [ ] All 5 npm-consuming repos have `.npmrc` with `@concavetrillion` scope registry.
- [ ] All 9 dependent repos have `make update-pd-deps` working.
- [ ] `update-pd-deps` correctly auto-flips around local-dev mode (8 of 9 repos; pdomain-ui skips this path).
- [ ] `update-pd-deps` queries pdomain-index-pip + pdomain-index-npm and prints a clear bump summary.
- [ ] `update-pd-deps` leaves the diff staged — does NOT commit.
- [ ] `make ci` passes after a bump (catches the breaking-change cases).
- [ ] Legacy `upgrade-pdomain-book-tools` is a deprecation alias in pdomain-ocr-cli + pdomain-prep-for-pgdp.
- [ ] Process doc `docs/process/update-pd-deps.md` exists and is committed.
- [ ] Workspace CLAUDE.md references the process doc.
- [ ] Per-repo CLAUDE.md Commands tables include the new target.
- [ ] GH issue ConcaveTrillion/ocr-container-meta#363 is closed.

## Out-of-scope

- Removing the `upgrade-pdomain-book-tools` deprecation aliases — follow-up after
  one release cycle.
- Auto-running `make ci` after the bump — by design, the target leaves the
  diff for human review.
- Cross-repo coordinated bumps (e.g. "bump pdomain-book-tools across all 8
  dependents at once") — separate concern, separate spec.
- Wiring `pdomain-index-npm` in non-pd-* repos — out of scope.
