---
title: local-dev Makefile standardization across pd-* repos
date: 2026-05-24
status: ready-for-review
issue: ConcaveTrillion/ocr-container-meta#362
related: [ConcaveTrillion/ocr-container-meta#363]
---

# local-dev Makefile standardization across pd-* repos

## 1. Context

Three pd-* repos (pdomain-book-tools, pdomain-ocr-cli, pdomain-prep-for-pgdp) have organically
accumulated "local-dev" Makefile targets that toggle between registry-installed
and sibling-editable sibling pd-* dependencies. The names and behaviors diverge:
`dev-local`, `local-setup`, `install-local`, `check-dev-local`, `upgrade-deps-local`
all coexist with different semantics across repos. Most other repos with pd-*
sibling deps have no local-dev workflow at all.

The 2026-05-24 Makefile standardization pass aligned the workspace-wide
canonical target set (`format-check`, `release-*`, `upgrade-deps`, `frontend-*`,
etc.). This spec finishes the job for the local-dev surface.

## 2. Goals

- **One canonical `local-*` target set** every pd-* repo with sibling pd-* deps
  exposes the same names with the same behavior.
- **All targets prefixed `local-`** — no more `dev-local` / `local-setup` /
  `install-local` mix-and-match.
- **One marker file convention** — `.venv/.pd-local-mode` (Python repos) /
  `.pd-local-mode` (pdomain-ui) — so any tool can answer "am I in local mode?"
- **Per-repo self-contained scripts** modeled on the existing `scripts/do-release.sh`
  pattern: each repo carries its own copy under `scripts/local-*.sh`.
- **`pdomain-prep-for-pgdp` is the reference implementation** — its mature scripts
  become the canonical templates other repos copy and adapt.
- **Workspace process doc** at `/workspaces/ocr-container/docs/process/local-dev.md`
  documents the canonical pattern and when to use each target.

## 3. Non-goals

- Removing repo-specific extras (e.g. pdomain-ocr-cli's GPU auto-detect in install
  paths). Preserve repo specificity where justified.
- Migrating pdomain-ocr-synth, pd-png-optimizer, pdomain-ui to have local-* targets when
  they have no local-mode concern today. Add later if a real need arises.
- Building a workspace-shared script library — per-repo scripts only, for self-containment.
- Handling the registry/local mode interaction inside `update-pd-deps` —
  that's [spec #363](2026-05-24-update-pd-deps-design.md).

## 4. Architecture

### Two modes, mutually exclusive per repo at any given time

| Mode | Sibling pd-* resolution | Marker present? |
|---|---|---|
| **registry mode** (default) | `pdomain-index-pip` / `pdomain-index-npm` per pyproject pins | no |
| **local-dev mode** | sibling checkouts under `/workspaces/ocr-container/<sibling>/`, installed editable | yes |

### Marker file

- Python repos: empty file at `.venv/.pd-local-mode`
- pdomain-ui (no venv): empty file at `<repo>/.pd-local-mode` (in `.gitignore`)

Presence ↔ local mode. The marker is the single source of truth that
`local-check`, `local-upgrade-deps`'s guard, and `update-pd-deps`'s auto-flip
detection all read.

### Script pattern

Each repo carries its own `scripts/local-*.sh` files. Modeled exactly on
the existing `scripts/do-release.sh`:

- bash, `set -euo pipefail`
- clear logging (function `say() { echo "[local-dev] $*"; }`)
- idempotent where possible
- escape hatches: `FORCE=1`, `DRY_RUN=1` where useful

### Mode interaction (handled in this spec)

- `local-dev` flips mode ON: install editable, write marker, `uv sync`
- `local-upgrade-deps` requires already-in-local-mode (refuses with clear
  error message otherwise): `uv lock --upgrade && uv sync && make local-dev`
  (since `uv sync` would wipe editables)
- `local-check` prints current mode + per-sibling status
- The mode interaction with `update-pd-deps` lives in [spec #363](2026-05-24-update-pd-deps-design.md).

## 5. Detailed behavior

### 5.1 Canonical target set

| Target | What it does |
|---|---|
| `local-setup` | For each sibling pd-* dep declared in pyproject.toml, check `/workspaces/ocr-container/<sibling>/` exists; if not, `gh repo clone ConcaveTrillion/<sibling>`. Prints summary. Idempotent. Does NOT switch to local-dev mode. |
| `local-dev` | Calls `local-setup` first. Then `uv pip install --no-deps -e ../<sibling>` (Python) per sibling; for SPA repos, also `cd frontend && pnpm link <relative-path>` for the npm side. Touch marker. Print summary of what's now editable. |
| `local-check` | Print marker presence + per-sibling: editable from path X or registry version Y. One screen, easy to scan. Exit 0 always (informational). |
| `local-upgrade-deps` | Refuses (exit 1, clear message) if marker absent. Else: `uv lock --upgrade && uv sync && make local-dev` (re-establishes editables that uv sync wiped). |
| `local-install` | (CLI/tool-publishing repos only — pdomain-ocr-cli, pdomain-prep-for-pgdp). `uv tool install --editable . --with-editable ../<sibling>` per sibling. Marker required. |
| `local-uninstall` | (CLI-publishing repos). `uv tool uninstall <tool-name>`. Does NOT touch venv or marker. |
| `local-run` | (CLI/server repos). Marker required (refuse otherwise). Runs the repo's equivalent of `make run` against the local-dev workspace. For SPA repos: build frontend with local pdomain-ui linked then launch the FastAPI server. |

### 5.2 Per-repo target matrix

| Repo | local-setup | local-dev | local-check | local-upgrade-deps | local-install | local-uninstall | local-run |
|---|---|---|---|---|---|---|---|
| pdomain-book-tools | — | ✓ (GPU extras) | ✓ | ✓ | — | — | — |
| pdomain-ocr-cli | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| pdomain-ops | ✓ | ✓ | ✓ | ✓ | — | — | — |
| pdomain-ocr-training | ✓ | ✓ | ✓ | ✓ | — | — | — |
| pdomain-ocr-simple-gui | ✓ | ✓ | ✓ | ✓ | — | — | ✓ |
| pdomain-ocr-labeler-spa | ✓ | ✓ | ✓ | ✓ | — | — | ✓ |
| pdomain-ocr-trainer-spa | ✓ | ✓ | ✓ | ✓ | — | — | ✓ |
| pdomain-prep-for-pgdp | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

8 of 11 repos. Leaves (pdomain-ocr-synth, pd-png-optimizer, pdomain-ui) skip — no
local-mode concern today.

### 5.3 Special case: pdomain-book-tools

pdomain-book-tools is the foundation library — no siblings to make editable. Its
`local-dev` is the existing GPU-extras toggle: `uv sync --extra gpu` + write
marker. `local-check` reports GPU extras active. `local-upgrade-deps`
re-syncs with extras after upgrade. No `local-setup` / `local-install` /
`local-run` (it's a library, no CLI to install or run).

### 5.4 npm side for SPAs

The 4 SPAs (labeler-spa, simple-gui, trainer-spa, prep-for-pgdp) handle BOTH
Python siblings AND `@concavetrillion/pdomain-ui` in `local-dev`:

```bash
# Python side
uv pip install --no-deps -e ../pdomain-book-tools
uv pip install --no-deps -e ../pdomain-ops
# npm side (SPA only)
cd frontend && pnpm link ../../../pdomain-ui
```

`pnpm link` is one-way: pdomain-ui's `src/` changes show up in the SPA's
dev-server reload without a publish/install step. `local-upgrade-deps`
reinstates via `pnpm install` then re-link.

## 6. Implementation plan

Per-repo, in dependency order so reference implementations exist first:

1. **pdomain-prep-for-pgdp** (reference) — rename/consolidate existing `dev-local` /
   `local-setup` / `install-local` / `check-local-editable` / `upgrade-deps-local`
   into the canonical `local-*` set. Write `scripts/local-*.sh` as the
   workspace template implementations. Add deprecation aliases for the old
   target names (one-release back-compat).
2. **pdomain-book-tools** — rename `dev-local` → `local-dev` (preserve GPU semantics);
   add `local-check`, `local-upgrade-deps`. Carry deprecation alias for `dev-local`.
3. **pdomain-ocr-cli** — rename `dev-local`/`local-setup`/`install-local`/`check-local-editable`/
   `run-local`/`upgrade-deps-local` to canonical. Copy scripts from prep-for-pgdp.
   Deprecation aliases.
4. **pdomain-ops, pdomain-ocr-training** (add from scratch, libraries) — copy scripts; add `local-setup`,
   `local-dev`, `local-check`, `local-upgrade-deps`.
5. **pdomain-ocr-simple-gui, pdomain-ocr-labeler-spa, pdomain-ocr-trainer-spa** (add from scratch, SPAs) —
   copy scripts; add full set including `local-run` for the SPA dev-server.
6. **Workspace process doc** — write `/workspaces/ocr-container/docs/process/local-dev.md`
   documenting the pattern, the marker file convention, when to use each target,
   and how the mode interacts with [#363's `update-pd-deps`](2026-05-24-update-pd-deps-design.md).
7. **CLAUDE.md references** — update the workspace and per-repo CLAUDE.md "Commands"
   tables to reflect the canonical target set.

Each step is its own commit (or PR per repo). Deprecation aliases stay until
spec #363 lands (giving callers one cycle to migrate names).

## 7. Migration / Rollout

- **Back-compat strategy:** every renamed target keeps the old name as a
  `.PHONY` alias delegating to the new name, with a `@echo "warning: <old> is
  deprecated, use <new>"` line. Aliases removed in a follow-up after #363 ships.
- **Sibling clone:** `local-setup` should NOT clone aggressively — only if
  the sibling directory is missing. Repos already cloned (the workspace's
  standard state) skip the clone step silently.
- **Marker file on first switch:** if a repo had its venv set up before this
  spec ships, the first `local-dev` invocation writes the marker. No migration
  step needed for existing venvs.

## 8. Risks & alternatives

- **Risk:** `uv sync` after `local-dev` would wipe editable installs because
  it resolves from the lockfile. Mitigation: `local-upgrade-deps` always calls
  `make local-dev` at the end to re-establish editables. Documented loudly.
- **Risk:** SPA `pnpm link` against `../../../pdomain-ui` is fragile if pdomain-ui's
  `dist/` isn't built. Mitigation: `local-dev` for SPAs ends with
  `cd ../pdomain-ui && make build` to ensure the dist exists.
- **Risk:** sibling paths `../<sibling>/` assume the interactive workspace
  layout (`/workspaces/ocr-container/<repo>/`). Bot workspaces under
  `/srv/bot-workspaces/<bot>/<repo>/` would not find siblings via `../`.
  Mitigation: local-dev is interactive-only by design; document that bots
  should not invoke `local-*` targets. Scripts should refuse with a clear
  error if siblings are missing rather than silently failing later.
- **Alternative rejected:** workspace-shared `/workspaces/ocr-container/scripts/`
  considered. Rejected because a checkout of one repo alone would break (script
  reference points outside its tree). Per-repo self-containment wins.
- **Alternative rejected:** all 11 repos get the full set for uniformity (even
  no-op stubs in leaves). Rejected because pointless targets confuse `make help`.

## 9. Open questions

None at design time. All ambiguities resolved in the 2026-05-24 brainstorming
session (transcript at the parent conversation).
