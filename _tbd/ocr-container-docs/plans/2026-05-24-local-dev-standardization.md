---
title: local-dev Makefile standardization implementation plan
date: 2026-05-24
repo: ConcaveTrillion/ocr-container-meta
spec: docs/archive/specs/2026-05-24-local-dev-standardization-design.md
issue: ConcaveTrillion/ocr-container-meta#362
status: active
synced: 2026-05-24
milestone: 17
blocks:
- docs/plans/2026-05-24-update-pd-deps.md
---

# local-dev Makefile standardization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Standardize `local-*` Makefile targets across the 8 pd-* repos with
sibling pd-* deps, with `.venv/.pd-local-mode` marker convention and
per-repo `scripts/local-*.sh` modeled on the existing `scripts/do-release.sh`.

**Architecture:** `pdomain-prep-for-pgdp` becomes the reference; its mature
scripts get extracted into the canonical template. Other 7 repos copy and
adapt. Per-repo target presence is per the matrix in spec §5.2.

**Tech Stack:** bash + GNU make + uv + pnpm (SPAs only).

**Execution shape:** M0 (process doc) and M1 (reference in pdomain-prep-for-pgdp)
ship serially; M2–M8 (per-repo rollouts) can be dispatched in parallel as
one agent per repo. M9 (CLAUDE.md refresh) runs last.

---

## File Structure

**New, per-repo (created in M1, copied/adapted M2–M8):**
- `scripts/local-setup.sh` — clone missing pd-* siblings into the workspace
- `scripts/local-dev.sh` — switch to local-editable; write marker
- `scripts/local-check.sh` — print mode + per-sibling status
- `scripts/local-upgrade-deps.sh` — guard mode, upgrade, restore editable
- `scripts/local-install.sh` — (CLI-publishing repos only) uv tool install with editable siblings
- `scripts/local-uninstall.sh` — (CLI-publishing repos only) uv tool uninstall
- `scripts/local-run.sh` — (CLI/server repos only) run against local-dev workspace

**New, workspace-level (created in M0):**
- `/workspaces/ocr-container/docs/process/local-dev.md` — canonical pattern doc

**Modified, per-repo (M2–M8):**
- `<repo>/Makefile` — add `local-*` targets; add back-compat aliases for renamed legacy targets
- `<repo>/.gitignore` — add `.venv/.pd-local-mode` (Python) or `.pd-local-mode` (pdomain-ui — but pdomain-ui out of scope here)
- `<repo>/CLAUDE.md` — update Commands table

**Modified, workspace-level (M9):**
- `/workspaces/ocr-container/CLAUDE.md` — reference the process doc; mention local-* in workflow guidance

---

## Task 0 — Workspace process doc  {#m0-process-doc}
model: sonnet  effort: S  area: makefile-std

Context: Workspace lacks a canonical reference for the local-dev pattern; agents and humans rediscover it per repo.
Approach: Write docs/process/local-dev.md covering what local-dev is, the marker file, the canonical target set, the per-repo matrix, lifecycle, exceptions, and cross-references.
Verification: test -f /workspaces/ocr-container/docs/process/local-dev.md
Acceptance:
- [ ] docs/process/local-dev.md exists and is committed to ocr-container-meta
- [ ] All 7 sections per the task body are present
- [ ] Linked from CLAUDE.md (handled in Task 9)

**Goal:** Reader can answer "what does `make local-dev` do?", "how does it
interact with `make update-pd-deps`?", "what does the marker file mean?"
without reading any repo's Makefile.

### Step 0.1: Write `docs/process/local-dev.md` {#write-docsprocesslocal-devmd}

**Files:**
- Create: `/workspaces/ocr-container/docs/process/local-dev.md`

- [ ] **Step 1: Draft the doc content**

Sections to include (each 1–3 short paragraphs):
1. **What is local-dev mode** — when sibling pd-* deps resolve from
   `../<sibling>/` editable installs instead of `pdomain-index-pip`/npm.
2. **The marker file** — `.venv/.pd-local-mode` (Python) / `.pd-local-mode`
   (pdomain-ui). Empty file. Presence = local mode.
3. **The canonical target set** — table of all `local-*` targets with one-line behavior.
4. **Per-repo presence matrix** — copy from spec §5.2.
5. **Mode lifecycle** — diagram: registry → `make local-dev` → local mode →
   `make local-upgrade-deps` → still local mode; `make update-pd-deps`
   auto-flips out and back (link to [#363's process doc](update-pd-deps.md)
   once that lands).
6. **When NOT to use local-dev** — bot workspaces under `/srv/bot-workspaces/`;
   any repo where siblings aren't checked out under `/workspaces/ocr-container/`.
7. **Cross-references** — link to spec, link to `scripts/do-release.sh` as the
   sister pattern, link to `pdomain-prep-for-pgdp/scripts/local-*.sh` as the reference.

- [ ] **Step 2: Commit**

```bash
cd /workspaces/ocr-container
git add docs/process/local-dev.md
git commit -m "docs(process): canonical local-dev pattern (#362)"
```

---

## Task 1 — Reference implementation in pdomain-prep-for-pgdp  {#m1-reference-impl}
model: sonnet  effort: L  area: makefile-std
Blocked-by: #m0-process-doc

Context: pdomain-prep-for-pgdp is the most mature local-dev repo; its scripts become the canonical template for M2–M8.
Approach: In a pdomain-prep-for-pgdp worktree, create scripts/local-{setup,dev,check,upgrade-deps,install,uninstall,run}.sh, wire 7 Make targets + .PHONY + back-compat aliases, add .venv/.pd-local-mode to .gitignore, smoke-test, commit.
Verification: cd pdomain-prep-for-pgdp && make local-dev && make local-check && make ci AI=1
Acceptance:
- [ ] 7 scripts/local-*.sh exist and are executable in pdomain-prep-for-pgdp
- [ ] Makefile has canonical targets + back-compat aliases
- [ ] .gitignore lists .venv/.pd-local-mode
- [ ] make local-upgrade-deps refuses outside local-dev mode
- [ ] make ci AI=1 green

**Goal:** Build the canonical `scripts/local-*.sh` and Make-target additions
in pdomain-prep-for-pgdp. Subsequent per-repo milestones copy from here.

**Working location:** worktree of pdomain-prep-for-pgdp.

### Step 1.1: Create `scripts/local-setup.sh` {#create-scriptslocal-setupsh}

**Files:**
- Create: `pdomain-prep-for-pgdp/scripts/local-setup.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
# scripts/local-setup.sh — clone missing pd-* sibling repos into the workspace.
#
# Idempotent: skips siblings that already exist.
# Does NOT switch the repo into local-dev mode (use `make local-dev` for that).
set -euo pipefail

# Repo-specific: list of sibling pd-* GitHub repo names this repo depends on.
SIBLINGS=(pdomain-book-tools pdomain-ops pdomain-ui)

WORKSPACE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

say() { echo "[local-setup] $*"; }

for sibling in "${SIBLINGS[@]}"; do
  if [[ -d "$WORKSPACE_ROOT/$sibling" ]]; then
    say "✓ $sibling already cloned at $WORKSPACE_ROOT/$sibling"
  else
    say "→ cloning $sibling…"
    gh repo clone "ConcaveTrillion/$sibling" "$WORKSPACE_ROOT/$sibling"
    say "✓ $sibling cloned"
  fi
done

say "done. Run 'make local-dev' to install with editable siblings."
```

- [ ] **Step 2: Make executable**

```bash
chmod +x pdomain-prep-for-pgdp/scripts/local-setup.sh
```

### Step 1.2: Create `scripts/local-dev.sh` {#create-scriptslocal-devsh}

**Files:**
- Create: `pdomain-prep-for-pgdp/scripts/local-dev.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
# scripts/local-dev.sh — switch to local-editable sibling pd-* deps.
#
# Calls local-setup first to ensure siblings are cloned.
# Then installs editable siblings (Python + npm), writes marker.
set -euo pipefail

# Repo-specific: Python siblings + npm siblings.
PY_SIBLINGS=(pdomain-book-tools pdomain-ops)
NPM_SIBLINGS=(pdomain-ui)         # paths relative to ../

WORKSPACE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARKER="$REPO_ROOT/.venv/.pd-local-mode"

say() { echo "[local-dev] $*"; }

# Pre-flight: siblings must exist
make local-setup

# Python: install editable
for s in "${PY_SIBLINGS[@]}"; do
  say "→ installing editable: $s"
  uv pip install --no-deps -e "$WORKSPACE_ROOT/$s"
done

# npm: link (SPAs only)
if [[ -d "$REPO_ROOT/frontend" ]]; then
  for s in "${NPM_SIBLINGS[@]}"; do
    # pdomain-ui needs `make build` for its dist/ to be importable
    if [[ "$s" == "pdomain-ui" ]]; then
      say "→ pre-building pdomain-ui dist/"
      (cd "$WORKSPACE_ROOT/pdomain-ui" && make build)
    fi
    say "→ linking @concavetrillion/$s from $WORKSPACE_ROOT/$s"
    (cd "$REPO_ROOT/frontend" && pnpm link "$WORKSPACE_ROOT/$s")
  done
fi

# Write marker
mkdir -p "$(dirname "$MARKER")"
touch "$MARKER"
say "✓ marker written: $MARKER"

say "✓ local-dev mode active. Run 'make local-check' to verify."
```

- [ ] **Step 2: Make executable**

```bash
chmod +x pdomain-prep-for-pgdp/scripts/local-dev.sh
```

### Step 1.3: Create `scripts/local-check.sh` {#create-scriptslocal-checksh}

**Files:**
- Create: `pdomain-prep-for-pgdp/scripts/local-check.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
# scripts/local-check.sh — print local-dev mode status.
#
# Exit 0 always (informational).
set -euo pipefail

PY_SIBLINGS=(pdomain-book-tools pdomain-ops)
NPM_SIBLINGS=(pdomain-ui)

WORKSPACE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARKER="$REPO_ROOT/.venv/.pd-local-mode"

say() { echo "$*"; }

if [[ -f "$MARKER" ]]; then
  say "MODE: local-dev (marker present at $MARKER)"
else
  say "MODE: registry (no marker)"
fi
say ""

# Python siblings
say "Python siblings:"
for s in "${PY_SIBLINGS[@]}"; do
  loc=$(uv pip show "$s" 2>/dev/null | awk '/^Location:/ {print $2}' || true)
  ver=$(uv pip show "$s" 2>/dev/null | awk '/^Version:/  {print $2}' || true)
  if [[ -z "$loc" ]]; then
    say "  ✗ $s — NOT installed"
  elif [[ "$loc" == *"/$s/"* ]] || [[ "$loc" == *"/$s" ]]; then
    say "  ✓ $s editable from $loc ($ver)"
  else
    say "  → $s registry version $ver (at $loc)"
  fi
done
say ""

# npm siblings (SPA repos)
if [[ -d "$REPO_ROOT/frontend" ]]; then
  say "npm siblings:"
  for s in "${NPM_SIBLINGS[@]}"; do
    pkg_dir="$REPO_ROOT/frontend/node_modules/@concavetrillion/$s"
    if [[ -L "$pkg_dir" ]]; then
      target=$(readlink -f "$pkg_dir")
      say "  ✓ @concavetrillion/$s linked → $target"
    elif [[ -d "$pkg_dir" ]]; then
      ver=$(jq -r .version "$pkg_dir/package.json" 2>/dev/null || echo "unknown")
      say "  → @concavetrillion/$s registry version $ver"
    else
      say "  ✗ @concavetrillion/$s — NOT installed"
    fi
  done
fi
```

- [ ] **Step 2: Make executable**

```bash
chmod +x pdomain-prep-for-pgdp/scripts/local-check.sh
```

### Step 1.4: Create `scripts/local-upgrade-deps.sh` {#create-scriptslocal-upgrade-depssh}

**Files:**
- Create: `pdomain-prep-for-pgdp/scripts/local-upgrade-deps.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
# scripts/local-upgrade-deps.sh — upgrade deps then restore local-editable.
#
# Refuses if not in local-dev mode (use `make upgrade-deps` for registry mode).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARKER="$REPO_ROOT/.venv/.pd-local-mode"

say() { echo "[local-upgrade-deps] $*"; }

if [[ ! -f "$MARKER" ]]; then
  echo "ERROR: not in local-dev mode (no marker at $MARKER)." >&2
  echo "       Run 'make upgrade-deps' instead." >&2
  exit 1
fi

say "→ uv lock --upgrade"
uv lock --upgrade
say "→ uv sync"
uv sync
say "→ uv sync wiped editables; re-running 'make local-dev' to restore"
make local-dev
say "✓ local mode restored after upgrade."
```

- [ ] **Step 2: Make executable**

```bash
chmod +x pdomain-prep-for-pgdp/scripts/local-upgrade-deps.sh
```

### Step 1.5: Create `scripts/local-install.sh` and `scripts/local-uninstall.sh` {#create-scriptslocal-installsh-and-scriptslocal-uni}

**Files:**
- Create: `pdomain-prep-for-pgdp/scripts/local-install.sh`
- Create: `pdomain-prep-for-pgdp/scripts/local-uninstall.sh`

- [ ] **Step 1: Write local-install.sh**

```bash
#!/usr/bin/env bash
# scripts/local-install.sh — install uv tool with editable sibling overrides.
#
# Requires local-dev mode (marker must be present).
set -euo pipefail

TOOL_NAME="pgdp-prep"               # repo-specific
PY_SIBLINGS=(pdomain-book-tools pdomain-ops)
WORKSPACE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARKER="$REPO_ROOT/.venv/.pd-local-mode"

say() { echo "[local-install] $*"; }

if [[ ! -f "$MARKER" ]]; then
  echo "ERROR: not in local-dev mode. Run 'make local-dev' first." >&2
  exit 1
fi

# Build --with-editable args
WITH_ARGS=()
for s in "${PY_SIBLINGS[@]}"; do
  WITH_ARGS+=(--with-editable "$WORKSPACE_ROOT/$s")
done

say "→ uv tool install --editable . ${WITH_ARGS[*]}"
uv tool install --editable . "${WITH_ARGS[@]}" --force

say "✓ $TOOL_NAME installed with editable siblings."
```

- [ ] **Step 2: Write local-uninstall.sh**

```bash
#!/usr/bin/env bash
# scripts/local-uninstall.sh — uninstall the uv tool (siblings + venv untouched).
set -euo pipefail

TOOL_NAME="pgdp-prep"

echo "[local-uninstall] → uv tool uninstall $TOOL_NAME"
uv tool uninstall "$TOOL_NAME" || true
echo "[local-uninstall] ✓ done. Venv + marker unchanged."
```

- [ ] **Step 3: Make executable**

```bash
chmod +x pdomain-prep-for-pgdp/scripts/local-install.sh pdomain-prep-for-pgdp/scripts/local-uninstall.sh
```

### Step 1.6: Create `scripts/local-run.sh` {#create-scriptslocal-runsh}

**Files:**
- Create: `pdomain-prep-for-pgdp/scripts/local-run.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
# scripts/local-run.sh — run repo's CLI/server against the local-dev workspace.
#
# Requires local-dev mode. Delegates to repo-specific `make run` after the guard.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARKER="$REPO_ROOT/.venv/.pd-local-mode"

if [[ ! -f "$MARKER" ]]; then
  echo "ERROR: not in local-dev mode. Run 'make local-dev' first." >&2
  exit 1
fi

# Repo-specific run target
exec make run
```

- [ ] **Step 2: Make executable**

```bash
chmod +x pdomain-prep-for-pgdp/scripts/local-run.sh
```

### Step 1.7: Wire Make targets + back-compat aliases {#wire-make-targets-back-compat-aliases}

**Files:**
- Modify: `pdomain-prep-for-pgdp/Makefile`
- Modify: `pdomain-prep-for-pgdp/.gitignore`

- [ ] **Step 1: Add canonical targets to Makefile**

Insert after the existing `release-major` target (or near the bottom of repo-specific targets):

```makefile
# ─── local-dev workflow (spec #362) ─────────────────────────────────────────

local-setup: ## Clone any missing sibling pd-* repos into the workspace
	@./scripts/local-setup.sh

local-dev: ## Switch to local-dev mode (siblings editable + marker)
	@./scripts/local-dev.sh

local-check: ## Print local-dev mode status + per-sibling resolution
	@./scripts/local-check.sh

local-upgrade-deps: ## Upgrade deps then restore editable siblings (local-mode only)
	@./scripts/local-upgrade-deps.sh

local-install: ## Install uv tool with editable siblings (local-mode only)
	@./scripts/local-install.sh

local-uninstall: ## Uninstall the uv tool (siblings + venv untouched)
	@./scripts/local-uninstall.sh

local-run: ## Run the CLI/server against local-dev workspace (local-mode only)
	@./scripts/local-run.sh
```

- [ ] **Step 2: Add `.PHONY` block**

```makefile
.PHONY: local-setup local-dev local-check local-upgrade-deps \
        local-install local-uninstall local-run
```

- [ ] **Step 3: Add back-compat aliases for legacy target names**

Identify the legacy targets in pdomain-prep-for-pgdp's Makefile (per spec: probably
`dev-local`, `local-setup`, `install-local`, `uninstall-local`,
`check-local-editable`, `upgrade-deps-local`, `run-local`). For each that
existed BEFORE this change, add a deprecation alias:

```makefile
dev-local: ## DEPRECATED: use local-dev
	@echo "warning: 'dev-local' is deprecated; use 'local-dev'"
	@$(MAKE) local-dev

install-local: ## DEPRECATED: use local-install
	@echo "warning: 'install-local' is deprecated; use 'local-install'"
	@$(MAKE) local-install
```

(Add one alias per legacy target.)

- [ ] **Step 4: Update `.gitignore`**

```gitignore
# Local-dev mode marker (spec #362)
.venv/.pd-local-mode
```

- [ ] **Step 5: Update Makefile `help` text**

If the existing `help` target hand-rolls a list of targets, add the new
canonical targets (and mark the aliases DEPRECATED).

### Step 1.8: Smoke-test the reference implementation {#smoke-test-the-reference-implementation}

- [ ] **Step 1: Test `make local-setup` is idempotent**

Run from a clean pdomain-prep-for-pgdp worktree:
```bash
make local-setup
```
Expected: prints `✓ pdomain-book-tools already cloned at …` (etc); exits 0.

- [ ] **Step 2: Test `make local-dev`**

```bash
make local-dev
ls -la .venv/.pd-local-mode
```
Expected: marker file exists.

- [ ] **Step 3: Test `make local-check` reports local mode**

```bash
make local-check
```
Expected: `MODE: local-dev` + per-sibling editable lines with workspace paths.

- [ ] **Step 4: Test `make local-upgrade-deps` runs without errors**

```bash
make local-upgrade-deps
```
Expected: uv lock --upgrade, uv sync, then re-runs local-dev; ends with marker still present.

- [ ] **Step 5: Test refusal when not in local mode**

```bash
rm .venv/.pd-local-mode
make local-upgrade-deps
```
Expected: exit 1 with clear error message; suggests `make upgrade-deps`.

- [ ] **Step 6: Restore local mode for subsequent work**

```bash
make local-dev
```

- [ ] **Step 7: Run full CI**

```bash
make ci AI=1
```
Expected: green. (Codegen-check may fail on pre-existing infrastructure;
acceptable.)

### Step 1.9: Commit the reference {#commit-the-reference}

- [ ] **Step 1: Stage + commit**

```bash
git add scripts/local-*.sh Makefile .gitignore
git commit -m "chore(local-dev): canonical scripts/local-*.sh + Make targets (#362)

Establishes the reference implementation for the workspace-wide local-dev
standardization (spec docs/archive/specs/2026-05-24-local-dev-standardization-design.md).
Other pd-* dependent repos will copy from here in milestones M2–M8.

Targets: local-setup, local-dev, local-check, local-upgrade-deps,
local-install, local-uninstall, local-run. Marker: .venv/.pd-local-mode.
Back-compat aliases preserved for one release cycle.

Closes #362 partially (reference repo only)."
```

---

## Task 2 — pdomain-book-tools  {#m2-pdomain-book-tools}
model: sonnet  effort: M  area: makefile-std
Blocked-by: #m1-reference-impl

Context: pdomain-book-tools is the foundation lib with no siblings; local-dev here means GPU extras active + marker (special case per spec §5.3).
Approach: In a pdomain-book-tools worktree, create 3 scripts (local-dev/check/upgrade-deps) with GPU-extras semantics, wire Make targets + deprecation aliases for dev-local/check-dev-local/upgrade-deps-local, .gitignore marker, smoke-test, commit.
Verification: cd pdomain-book-tools && make local-dev && make local-check && make ci AI=1
Acceptance:
- [ ] 3 local-*.sh scripts in pdomain-book-tools/scripts/
- [ ] Makefile canonical targets + 3 deprecation aliases
- [ ] .venv/.pd-local-mode in .gitignore
- [ ] make ci AI=1 green

**Goal:** Rename `dev-local` → `local-dev` (preserving GPU semantics — NOT
sibling-editable, since pdomain-book-tools has no siblings); add `local-check`
and `local-upgrade-deps`. Per spec §5.3 special case.

### Step 2.1: Create pdomain-book-tools `local-*` scripts {#create-pdomain-book-tools-local-scripts}

**Files:**
- Create: `pdomain-book-tools/scripts/local-dev.sh`
- Create: `pdomain-book-tools/scripts/local-check.sh`
- Create: `pdomain-book-tools/scripts/local-upgrade-deps.sh`

- [ ] **Step 1: Write local-dev.sh (GPU-extras variant)**

```bash
#!/usr/bin/env bash
# scripts/local-dev.sh — toggle pdomain-book-tools into local-dev mode.
#
# pdomain-book-tools is the foundation lib (no siblings); local-dev here means
# "GPU extras active + marker present" per spec §5.3.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARKER="$REPO_ROOT/.venv/.pd-local-mode"

echo "[local-dev] → uv sync --extra gpu"
uv sync --extra gpu

mkdir -p "$(dirname "$MARKER")"
touch "$MARKER"
echo "[local-dev] ✓ GPU extras active; marker written: $MARKER"
```

- [ ] **Step 2: Write local-check.sh**

```bash
#!/usr/bin/env bash
# scripts/local-check.sh — print local-dev (GPU-extras) status.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARKER="$REPO_ROOT/.venv/.pd-local-mode"

if [[ -f "$MARKER" ]]; then
  echo "MODE: local-dev (GPU extras active; marker at $MARKER)"
else
  echo "MODE: registry (no marker; CPU-only base install)"
fi

# Show whether torch is installed and where
TORCH_LOC=$(uv pip show torch 2>/dev/null | awk '/^Location:/ {print $2}' || true)
if [[ -n "$TORCH_LOC" ]]; then
  TORCH_VER=$(uv pip show torch 2>/dev/null | awk '/^Version:/ {print $2}')
  echo "torch:   $TORCH_VER  (at $TORCH_LOC)"
else
  echo "torch:   NOT installed"
fi
```

- [ ] **Step 3: Write local-upgrade-deps.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARKER="$REPO_ROOT/.venv/.pd-local-mode"
if [[ ! -f "$MARKER" ]]; then
  echo "ERROR: not in local-dev mode. Run 'make upgrade-deps' for registry mode." >&2
  exit 1
fi
echo "[local-upgrade-deps] → uv lock --upgrade && uv sync --extra gpu"
uv lock --upgrade
uv sync --extra gpu
echo "[local-upgrade-deps] ✓ done. GPU extras restored."
```

- [ ] **Step 4: chmod +x all three**

```bash
chmod +x pdomain-book-tools/scripts/local-*.sh
```

### Step 2.2: Wire Make targets {#wire-make-targets}

**Files:**
- Modify: `pdomain-book-tools/Makefile`
- Modify: `pdomain-book-tools/.gitignore`

- [ ] **Step 1: Add canonical targets**

```makefile
local-dev: ## Switch to local-dev mode (GPU extras active + marker)
	@./scripts/local-dev.sh

local-check: ## Print local-dev (GPU extras) status
	@./scripts/local-check.sh

local-upgrade-deps: ## Upgrade deps + re-sync GPU extras (local-mode only)
	@./scripts/local-upgrade-deps.sh

.PHONY: local-dev local-check local-upgrade-deps
```

- [ ] **Step 2: Add deprecation alias for legacy `dev-local`**

```makefile
dev-local: ## DEPRECATED: use local-dev
	@echo "warning: 'dev-local' is deprecated; use 'local-dev'"
	@$(MAKE) local-dev

check-dev-local: ## DEPRECATED: use local-check
	@echo "warning: 'check-dev-local' is deprecated; use 'local-check'"
	@$(MAKE) local-check

upgrade-deps-local: ## DEPRECATED: use local-upgrade-deps
	@echo "warning: 'upgrade-deps-local' is deprecated; use 'local-upgrade-deps'"
	@$(MAKE) local-upgrade-deps
```

- [ ] **Step 3: Update .gitignore**

```gitignore
.venv/.pd-local-mode
```

### Step 2.3: Smoke test + commit {#smoke-test-commit}

- [ ] **Step 1: Run targets**

```bash
make local-dev
make local-check     # expect: MODE: local-dev + torch present
make local-upgrade-deps
make ci AI=1
```

- [ ] **Step 2: Commit**

```bash
git add scripts/local-*.sh Makefile .gitignore
git commit -m "chore(local-dev): standardize local-* targets (pdomain-book-tools, #362)

GPU-extras-active is pdomain-book-tools's flavor of local-dev (no siblings).
Marker .venv/.pd-local-mode unifies with workspace convention. Back-compat
aliases for dev-local / check-dev-local / upgrade-deps-local."
```

---

## Task 3 — pdomain-ocr-cli  {#m3-pdomain-ocr-cli}
model: sonnet  effort: M  area: makefile-std
Blocked-by: #m1-reference-impl

Context: pdomain-ocr-cli has legacy local-* targets with non-canonical names; needs rename + adopt canonical 7-script set with pdomain-book-tools sibling.
Approach: In a pdomain-ocr-cli worktree, copy 7 scripts from pdomain-prep-for-pgdp, adapt SIBLINGS=(pdomain-book-tools) + TOOL_NAME=pd-ocr, remove SPA frontend branch, wire Make targets + back-compat aliases (dev-local/install-local/uninstall-local/check-local-editable/run-local; drop python-local), .gitignore, smoke, commit.
Verification: cd pdomain-ocr-cli && make local-dev && make local-check && make ci AI=1
Acceptance:
- [ ] 7 local-*.sh in pdomain-ocr-cli/scripts/ adapted to single Python sibling
- [ ] Makefile has canonical targets + 5 deprecation aliases; python-local removed
- [ ] .venv/.pd-local-mode in .gitignore
- [ ] make ci AI=1 green

**Goal:** Rename existing `dev-local`/`local-setup`/`install-local`/etc to
canonical names; copy scripts from pdomain-prep-for-pgdp adapted for pdomain-ocr-cli's
dep set: `pdomain-book-tools` only (Python).

### Step 3.1: Copy + adapt scripts from pdomain-prep-for-pgdp {#copy-adapt-scripts-from-pdomain-prep-for-pgdp}

**Files:**
- Create (copy): `pdomain-ocr-cli/scripts/local-setup.sh`
- Create (copy): `pdomain-ocr-cli/scripts/local-dev.sh`
- Create (copy): `pdomain-ocr-cli/scripts/local-check.sh`
- Create (copy): `pdomain-ocr-cli/scripts/local-upgrade-deps.sh`
- Create (copy): `pdomain-ocr-cli/scripts/local-install.sh`
- Create (copy): `pdomain-ocr-cli/scripts/local-uninstall.sh`
- Create (copy): `pdomain-ocr-cli/scripts/local-run.sh`

- [ ] **Step 1: Copy all 7 scripts from pdomain-prep-for-pgdp**

```bash
for s in setup dev check upgrade-deps install uninstall run; do
  cp ../pdomain-prep-for-pgdp/scripts/local-$s.sh scripts/local-$s.sh
done
chmod +x scripts/local-*.sh
```

- [ ] **Step 2: Adapt SIBLINGS and TOOL_NAME**

In each script, edit the variable declarations:
- `local-setup.sh`: `SIBLINGS=(pdomain-book-tools)` (was `(pdomain-book-tools pdomain-ops pdomain-ui)`)
- `local-dev.sh`: `PY_SIBLINGS=(pdomain-book-tools)`; `NPM_SIBLINGS=()` (no SPA in pdomain-ocr-cli)
- `local-check.sh`: same as local-dev.sh
- `local-install.sh`: `TOOL_NAME="pd-ocr"`; `PY_SIBLINGS=(pdomain-book-tools)`
- `local-uninstall.sh`: `TOOL_NAME="pd-ocr"`
- `local-upgrade-deps.sh`: no changes (no SIBLINGS variable)
- `local-run.sh`: no changes (delegates to `make run`)

- [ ] **Step 3: Remove the SPA-only `frontend` branch from local-dev.sh + local-check.sh**

Since pdomain-ocr-cli has no `frontend/`, simplify by deleting the `if [[ -d "$REPO_ROOT/frontend" ]]` blocks.

### Step 3.2: Wire Make targets + deprecate legacy {#wire-make-targets-deprecate-legacy}

**Files:**
- Modify: `pdomain-ocr-cli/Makefile`
- Modify: `pdomain-ocr-cli/.gitignore`

- [ ] **Step 1: Add canonical targets**

Copy the `# ─── local-dev workflow ──` block from pdomain-prep-for-pgdp's Makefile
into pdomain-ocr-cli's Makefile. Same 7 targets, same `.PHONY` block.

- [ ] **Step 2: Add deprecation aliases for each existing legacy target**

pdomain-ocr-cli currently has: `local-setup`, `dev-local`, `install-local`,
`uninstall-local`, `check-local-editable`, `run-local`, `python-local`.

```makefile
dev-local: ## DEPRECATED: use local-dev
	@echo "warning: 'dev-local' is deprecated; use 'local-dev'"
	@$(MAKE) local-dev

install-local: ## DEPRECATED: use local-install
	@echo "warning: 'install-local' is deprecated; use 'local-install'"
	@$(MAKE) local-install

uninstall-local: ## DEPRECATED: use local-uninstall
	@echo "warning: 'uninstall-local' is deprecated; use 'local-uninstall'"
	@$(MAKE) local-uninstall

check-local-editable: ## DEPRECATED: use local-check
	@echo "warning: 'check-local-editable' is deprecated; use 'local-check'"
	@$(MAKE) local-check

run-local: ## DEPRECATED: use local-run
	@echo "warning: 'run-local' is deprecated; use 'local-run'"
	@$(MAKE) local-run
```

(Note: `local-setup` is already the canonical name — no alias needed if it
existed. `python-local` is NOT in the canonical set per the brainstorm
decision — DELETE the target rather than aliasing.)

- [ ] **Step 3: Update .gitignore**

```gitignore
.venv/.pd-local-mode
```

### Step 3.3: Smoke test + commit {#smoke-test-commit-1}

- [ ] **Step 1: Verify targets work**

```bash
make local-check     # before-local-dev should report registry mode
make local-dev       # installs editable pdomain-book-tools
make local-check     # should report local mode + editable path
make local-upgrade-deps
make ci AI=1
```

- [ ] **Step 2: Commit**

```bash
git add scripts/local-*.sh Makefile .gitignore
git commit -m "chore(local-dev): standardize local-* targets (pdomain-ocr-cli, #362)

Adopt canonical local-* set + scripts from pdomain-prep-for-pgdp reference.
Back-compat aliases for dev-local / install-local / uninstall-local /
check-local-editable / run-local. Drop python-local (not in canonical set)."
```

---

## Task 4 — pdomain-ops  {#m4-pdomain-ops}
model: sonnet  effort: S  area: makefile-std
Blocked-by: #m1-reference-impl

Context: pdomain-ops is a lib (no install/run targets); needs canonical 4-script set with pdomain-book-tools sibling.
Approach: In a pdomain-ops worktree, copy 4 scripts (setup/dev/check/upgrade-deps) from pdomain-prep-for-pgdp, adapt SIBLINGS=(pdomain-book-tools), remove frontend branch, wire 4 Make targets + .PHONY, .gitignore, smoke, commit.
Verification: cd pdomain-ops && make local-dev && make local-check && make ci AI=1
Acceptance:
- [ ] 4 local-*.sh in pdomain-ops/scripts/
- [ ] Makefile has 4 canonical targets
- [ ] .venv/.pd-local-mode in .gitignore
- [ ] make ci AI=1 green

**Goal:** Add `local-setup`, `local-dev`, `local-check`, `local-upgrade-deps`
from scratch (lib pattern — no install/run targets). Single sibling: `pdomain-book-tools`.

### Step 4.1: Copy + adapt 4 scripts {#copy-adapt-4-scripts}

**Files:**
- Create: `pdomain-ops/scripts/local-{setup,dev,check,upgrade-deps}.sh`

- [ ] **Step 1: Copy from pdomain-prep-for-pgdp**

```bash
cd pdomain-ops
for s in setup dev check upgrade-deps; do
  cp ../pdomain-prep-for-pgdp/scripts/local-$s.sh scripts/local-$s.sh
done
chmod +x scripts/local-*.sh
```

- [ ] **Step 2: Adapt**

- `local-setup.sh`: `SIBLINGS=(pdomain-book-tools)`
- `local-dev.sh`: `PY_SIBLINGS=(pdomain-book-tools)`; `NPM_SIBLINGS=()`; remove frontend branch
- `local-check.sh`: same; remove frontend branch
- `local-upgrade-deps.sh`: no changes

### Step 4.2: Wire Makefile + .gitignore {#wire-makefile-gitignore}

**Files:**
- Modify: `pdomain-ops/Makefile`
- Modify: `pdomain-ops/.gitignore`

- [ ] **Step 1: Add 4 targets + .PHONY**

```makefile
local-setup: ## Clone any missing sibling pd-* repos into the workspace
	@./scripts/local-setup.sh

local-dev: ## Switch to local-dev mode (siblings editable + marker)
	@./scripts/local-dev.sh

local-check: ## Print local-dev mode status + per-sibling resolution
	@./scripts/local-check.sh

local-upgrade-deps: ## Upgrade deps then restore editable siblings (local-mode only)
	@./scripts/local-upgrade-deps.sh

.PHONY: local-setup local-dev local-check local-upgrade-deps
```

- [ ] **Step 2: .gitignore**

```gitignore
.venv/.pd-local-mode
```

### Step 4.3: Smoke + commit {#smoke-commit}

- [ ] **Step 1: Test**

```bash
make local-dev
make local-check
make ci AI=1
```

- [ ] **Step 2: Commit**

```bash
git add scripts/local-*.sh Makefile .gitignore
git commit -m "chore(local-dev): add local-* targets (pdomain-ops, #362)"
```

---

## Task 5 — pdomain-ocr-training  {#m5-pdomain-ocr-training}
model: sonnet  effort: S  area: makefile-std
Blocked-by: #m1-reference-impl

Context: pdomain-ocr-training is a lib (no install/run); needs canonical 4-script set with pdomain-book-tools sibling. Mirrors Task 4.
Approach: In a pdomain-ocr-training worktree, copy 4 scripts from pdomain-prep-for-pgdp, adapt SIBLINGS=(pdomain-book-tools), remove frontend branch, wire 4 Make targets, .gitignore, smoke, commit.
Verification: cd pdomain-ocr-training && make local-dev && make local-check && make ci AI=1
Acceptance:
- [ ] 4 local-*.sh in pdomain-ocr-training/scripts/
- [ ] Makefile has 4 canonical targets
- [ ] .venv/.pd-local-mode in .gitignore
- [ ] make ci AI=1 green

**Goal:** Add `local-setup`, `local-dev`, `local-check`, `local-upgrade-deps`
(lib pattern, single sibling `pdomain-book-tools`). Same structure as M4.

### Step 5.1: Copy + adapt 4 scripts {#copy-adapt-4-scripts-1}

**Files:**
- Create: `pdomain-ocr-training/scripts/local-{setup,dev,check,upgrade-deps}.sh`

- [ ] **Step 1: Copy from pdomain-prep-for-pgdp**

```bash
cd pdomain-ocr-training
for s in setup dev check upgrade-deps; do
  cp ../pdomain-prep-for-pgdp/scripts/local-$s.sh scripts/local-$s.sh
done
chmod +x scripts/local-*.sh
```

- [ ] **Step 2: Adapt the sibling lists**

- `local-setup.sh`: `SIBLINGS=(pdomain-book-tools)`
- `local-dev.sh`: `PY_SIBLINGS=(pdomain-book-tools)`; `NPM_SIBLINGS=()`; delete the `if [[ -d "$REPO_ROOT/frontend" ]]` block
- `local-check.sh`: same as local-dev (single sibling, no frontend)
- `local-upgrade-deps.sh`: no changes

### Step 5.2: Wire Makefile + .gitignore {#wire-makefile-gitignore-1}

**Files:**
- Modify: `pdomain-ocr-training/Makefile`
- Modify: `pdomain-ocr-training/.gitignore`

- [ ] **Step 1: Add 4 targets + .PHONY**

```makefile
local-setup: ## Clone any missing sibling pd-* repos into the workspace
	@./scripts/local-setup.sh

local-dev: ## Switch to local-dev mode (siblings editable + marker)
	@./scripts/local-dev.sh

local-check: ## Print local-dev mode status + per-sibling resolution
	@./scripts/local-check.sh

local-upgrade-deps: ## Upgrade deps then restore editable siblings (local-mode only)
	@./scripts/local-upgrade-deps.sh

.PHONY: local-setup local-dev local-check local-upgrade-deps
```

- [ ] **Step 2: .gitignore**

```gitignore
.venv/.pd-local-mode
```

### Step 5.3: Smoke + commit {#smoke-commit-1}

- [ ] **Step 1: Test**

```bash
make local-dev
make local-check
make ci AI=1
```

- [ ] **Step 2: Commit**

```bash
git add scripts/local-*.sh Makefile .gitignore
git commit -m "chore(local-dev): add local-* targets (pdomain-ocr-training, #362)"
```

---

## Task 6 — pdomain-ocr-simple-gui  {#m6-pdomain-ocr-simple-gui}
model: sonnet  effort: M  area: makefile-std
Blocked-by: #m1-reference-impl

Context: pdomain-ocr-simple-gui is a SPA (Python + frontend); needs 5-script set (no install/uninstall — not a uv tool).
Approach: In a pdomain-ocr-simple-gui worktree, copy 5 scripts (setup/dev/check/upgrade-deps/run) from pdomain-prep-for-pgdp, adapt PY_SIBLINGS=(pdomain-book-tools pdomain-ops) + NPM_SIBLINGS=(pdomain-ui), keep frontend branch, wire 5 Make targets, .gitignore, smoke, commit.
Verification: cd pdomain-ocr-simple-gui && make local-dev && make local-check && make ci AI=1
Acceptance:
- [ ] 5 local-*.sh in pdomain-ocr-simple-gui/scripts/
- [ ] Makefile has 5 canonical targets
- [ ] .venv/.pd-local-mode in .gitignore
- [ ] make ci AI=1 green

**Goal:** Add 5 targets (setup, dev, check, upgrade-deps, run — no
install/uninstall, not a uv tool). SPA pattern: Python siblings
`pdomain-book-tools, pdomain-ops` + npm sibling `pdomain-ui`.

### Step 6.1: Copy + adapt 5 scripts {#copy-adapt-5-scripts}

**Files:**
- Create: `pdomain-ocr-simple-gui/scripts/local-{setup,dev,check,upgrade-deps,run}.sh`

- [ ] **Step 1: Copy**

```bash
cd pdomain-ocr-simple-gui
for s in setup dev check upgrade-deps run; do
  cp ../pdomain-prep-for-pgdp/scripts/local-$s.sh scripts/local-$s.sh
done
chmod +x scripts/local-*.sh
```

- [ ] **Step 2: Adapt**

- `local-setup.sh`: `SIBLINGS=(pdomain-book-tools pdomain-ops pdomain-ui)`
- `local-dev.sh`: `PY_SIBLINGS=(pdomain-book-tools pdomain-ops)`; `NPM_SIBLINGS=(pdomain-ui)`; keep frontend branch
- `local-check.sh`: same; keep frontend branch
- `local-upgrade-deps.sh`: no changes
- `local-run.sh`: no changes

### Step 6.2: Wire Make targets + .gitignore {#wire-make-targets-gitignore}

- [ ] **Step 1: Add 5 targets + .PHONY**

```makefile
local-setup: ## Clone any missing sibling pd-* repos
	@./scripts/local-setup.sh
local-dev: ## Switch to local-dev mode (siblings editable + marker)
	@./scripts/local-dev.sh
local-check: ## Print local-dev mode status
	@./scripts/local-check.sh
local-upgrade-deps: ## Upgrade deps then restore editable siblings
	@./scripts/local-upgrade-deps.sh
local-run: ## Run the SPA against local-dev workspace
	@./scripts/local-run.sh

.PHONY: local-setup local-dev local-check local-upgrade-deps local-run
```

- [ ] **Step 2: .gitignore**

```gitignore
.venv/.pd-local-mode
```

### Step 6.3: Smoke + commit {#smoke-commit-2}

- [ ] **Step 1: Test**

```bash
make local-dev       # should install editable + link pdomain-ui
make local-check     # should report local mode + pdomain-ui linked
make ci AI=1
```

- [ ] **Step 2: Commit**

```bash
git add scripts/local-*.sh Makefile .gitignore
git commit -m "chore(local-dev): add local-* targets (pdomain-ocr-simple-gui, #362)"
```

---

## Task 7 — pdomain-ocr-labeler-spa  {#m7-pdomain-ocr-labeler-spa}
model: sonnet  effort: M  area: makefile-std
Blocked-by: #m1-reference-impl

Context: pdomain-ocr-labeler-spa is a SPA; needs 5-script set with pdomain-book-tools (Python) + pdomain-ui (npm).
Approach: In a pdomain-ocr-labeler-spa worktree, copy 5 scripts from pdomain-prep-for-pgdp, adapt PY_SIBLINGS=(pdomain-book-tools) + NPM_SIBLINGS=(pdomain-ui), wire 5 Make targets, .gitignore, smoke, commit.
Verification: cd pdomain-ocr-labeler-spa && make local-dev && make local-check && make ci AI=1
Acceptance:
- [ ] 5 local-*.sh in pdomain-ocr-labeler-spa/scripts/
- [ ] Makefile has 5 canonical targets
- [ ] .venv/.pd-local-mode in .gitignore
- [ ] make ci AI=1 green

**Goal:** Add 5 targets, SPA pattern. Python sibling: `pdomain-book-tools` only;
npm sibling: `pdomain-ui`.

### Step 7.1: Copy + adapt 5 scripts (per M6 shape) {#copy-adapt-5-scripts-per-m6-shape}

- [ ] **Step 1: Copy 5 scripts to pdomain-ocr-labeler-spa/scripts/**

- [ ] **Step 2: Adapt**

- `local-setup.sh`: `SIBLINGS=(pdomain-book-tools pdomain-ui)`
- `local-dev.sh`: `PY_SIBLINGS=(pdomain-book-tools)`; `NPM_SIBLINGS=(pdomain-ui)`
- `local-check.sh`: same as local-dev
- others: no changes

### Step 7.2: Wire Makefile + .gitignore + smoke + commit (per M6) {#wire-makefile-gitignore-smoke-commit-per-m6}

```bash
git commit -m "chore(local-dev): add local-* targets (pdomain-ocr-labeler-spa, #362)"
```

---

## Task 8 — pdomain-ocr-trainer-spa  {#m8-pdomain-ocr-trainer-spa}
model: sonnet  effort: M  area: makefile-std
Blocked-by: #m1-reference-impl

Context: pdomain-ocr-trainer-spa is a SPA with 3 Python siblings + pdomain-ui (npm); 5-script set.
Approach: In a pdomain-ocr-trainer-spa worktree, copy 5 scripts from pdomain-prep-for-pgdp, adapt PY_SIBLINGS=(pdomain-book-tools pdomain-ops pdomain-ocr-training) + NPM_SIBLINGS=(pdomain-ui), wire 5 Make targets, .gitignore, smoke, commit.
Verification: cd pdomain-ocr-trainer-spa && make local-dev && make local-check && make ci AI=1
Acceptance:
- [ ] 5 local-*.sh in pdomain-ocr-trainer-spa/scripts/
- [ ] Makefile has 5 canonical targets
- [ ] .venv/.pd-local-mode in .gitignore
- [ ] make ci AI=1 green

**Goal:** Add 5 targets, SPA pattern. Python siblings:
`pdomain-book-tools, pdomain-ops, pdomain-ocr-training`; npm sibling: `pdomain-ui`.

### Step 8.1: Copy + adapt 5 scripts (per M6 shape) {#copy-adapt-5-scripts-per-m6-shape-1}

- [ ] **Step 1: Copy 5 scripts**

- [ ] **Step 2: Adapt**

- `local-setup.sh`: `SIBLINGS=(pdomain-book-tools pdomain-ops pdomain-ocr-training pdomain-ui)`
- `local-dev.sh`: `PY_SIBLINGS=(pdomain-book-tools pdomain-ops pdomain-ocr-training)`; `NPM_SIBLINGS=(pdomain-ui)`
- `local-check.sh`: same
- others: no changes

### Step 8.2: Wire Makefile + .gitignore + smoke + commit (per M6) {#wire-makefile-gitignore-smoke-commit-per-m6-1}

```bash
git commit -m "chore(local-dev): add local-* targets (pdomain-ocr-trainer-spa, #362)"
```

---

## Task 9 — Workspace CLAUDE.md refresh  {#m9-claude-md-refresh}
model: sonnet  effort: S  area: makefile-std
Blocked-by: #m2-pdomain-book-tools, #m3-pdomain-ocr-cli, #m4-pdomain-ops, #m5-pdomain-ocr-training, #m6-pdomain-ocr-simple-gui, #m7-pdomain-ocr-labeler-spa, #m8-pdomain-ocr-trainer-spa

Context: Workspace and per-repo CLAUDE.md docs need to reference the canonical local-* targets and the process doc; runs after all per-repo rollouts.
Approach: Update /workspaces/ocr-container/CLAUDE.md with a Local-dev workflow subsection; for each of the 8 dependent repos, add local-* rows to the Commands table in <repo>/CLAUDE.md; commit per repo.
Verification: grep -q 'make local-dev' /workspaces/ocr-container/CLAUDE.md
Acceptance:
- [ ] Workspace CLAUDE.md has Local-dev workflow subsection
- [ ] Each of the 8 repos' CLAUDE.md Commands table includes the assigned local-* targets
- [ ] Per-repo commits land on each repo's main

**Goal:** Update workspace and per-repo CLAUDE.md docs to mention the
canonical `local-*` target set and the process doc.

### Step 9.1: Update workspace CLAUDE.md {#update-workspace-claudemd}

**Files:**
- Modify: `/workspaces/ocr-container/CLAUDE.md`

- [ ] **Step 1: Add a "Local-dev workflow" subsection in the Before-coding section**

Just after the existing "Routing" section, add:

```markdown
## Local-dev workflow

When iterating on sibling pd-* deps together (e.g. fixing a bug in
pdomain-book-tools and exercising it in pdomain-prep-for-pgdp), use the canonical
`local-*` Make targets in any repo with sibling pd-* deps. See
[`docs/process/local-dev.md`](docs/process/local-dev.md) for the full
pattern. Quick reference:

- `make local-setup` — clone any missing siblings
- `make local-dev` — switch to local-editable mode (writes `.venv/.pd-local-mode` marker)
- `make local-check` — print current mode + per-sibling resolution
- `make local-upgrade-deps` — upgrade then restore editable siblings
- `make local-install` / `local-uninstall` / `local-run` — repo-specific extras

Bot workspaces under `/srv/bot-workspaces/` do NOT use local-dev mode —
they always resolve from the registry.
```

- [ ] **Step 2: Commit**

```bash
cd /workspaces/ocr-container
git add CLAUDE.md
git commit -m "docs(workspace): document local-* canonical targets (#362)"
```

### Step 9.2: Per-repo CLAUDE.md "Commands" table refresh {#per-repo-claudemd-commands-table-refresh}

For each of the 8 repos that gained local-* targets (M2–M8 above), add the
new targets to the Commands table in the repo's CLAUDE.md.

- [ ] **Step 1: For each repo, edit `<repo>/CLAUDE.md` Commands table**

Add rows like:
```markdown
| `make local-dev` | switch to local-dev mode (siblings editable) |
| `make local-check` | print local-dev mode status |
```

(Repo-specific: only add the targets that repo actually has.)

- [ ] **Step 2: Commit per repo**

```bash
git -C <repo> add CLAUDE.md
git -C <repo> commit -m "docs(claude): document local-* targets (#362)"
```

---

## Final acceptance

- [ ] Every repo in the spec §5.2 matrix has its assigned `local-*` targets.
- [ ] Every dependent repo has `.venv/.pd-local-mode` in `.gitignore`.
- [ ] `make local-dev && make local-check` works correctly in each repo.
- [ ] `make local-upgrade-deps` refuses outside local-dev mode in each repo.
- [ ] `make ci` is green in each repo.
- [ ] Process doc `docs/process/local-dev.md` exists and is committed.
- [ ] Workspace CLAUDE.md references the process doc.
- [ ] Per-repo CLAUDE.md Commands tables include the new targets.
- [ ] Deprecation aliases for legacy target names are in place.
- [ ] GH issue ConcaveTrillion/ocr-container-meta#362 is closed.

## Out-of-scope (handled by separate plan)

- `make update-pd-deps` per spec #363 — depends on this plan landing
  at least M1–M8 (canonical `local-*` + marker convention in all 8 repos).
  See [docs/plans/2026-05-24-update-pd-deps.md](2026-05-24-update-pd-deps.md).
- Removing deprecation aliases — follow-up commit after one release cycle.
- `local-*` for the 3 leaves (pdomain-ocr-synth, pd-png-optimizer, pdomain-ui) — not
  needed today; add later if a local-mode concern arises.
