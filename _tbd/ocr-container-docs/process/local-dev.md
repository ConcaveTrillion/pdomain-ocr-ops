# Local-dev mode for sibling pd-* deps

Canonical pattern for iterating on a pd-* repo with one or more sibling
pd-* dependencies resolved from the workspace checkout (`/workspaces/ocr-container/<sibling>/`)
instead of the registry (`pdomain-index-pip` / `pdomain-index-npm`). See
[spec #362](../archive/specs/2026-05-24-local-dev-standardization-design.md).

## What is local-dev mode

When a repo is in local-dev mode, its sibling pd-* deps resolve from
editable installs of the workspace checkouts:

- **Python siblings** — `uv pip install --no-deps -e ../<sibling>` so
  imports hit the sibling's source tree, not the registry wheel.
- **npm siblings** — `pnpm link ../<sibling>` so `@concavetrillion/<sibling>`
  resolves to the workspace checkout's built `dist/`.

The opposite of local-dev mode is **registry mode**: every dep resolves from
the published index, regardless of what's in the workspace. Registry mode is
the default after a fresh `uv sync` or `pnpm install`.

### Three resolution modes

There are three ways a repo can resolve its pd-* siblings:

1. **registry** (default) — published wheels from `pdomain-index-pip` /
   `pdomain-index-npm`.
2. **local-dev** (marker-gated, persistent) — editable workspace checkouts,
   for active cross-repo iteration. This document.
3. **git-main validation** (`make ci-against-main`, transient) — resolve
   Python siblings from each one's latest GitHub `main` (committed but
   unpublished), run the release preflight, then revert. For catching
   "sibling main will break me once released" before a release. Leaves no
   committed churn and is **not** a persistent mode. Python siblings only
   (npm stays on the registry). See
   [`ci-against-main.md`](ci-against-main.md).

## The marker file

A repo is in local-dev mode iff a marker file exists:

- Python repos: `.venv/.pdomain-local-mode`
- pdomain-ui (TS-only, no .venv): `.pdomain-local-mode`

The marker is an empty file written by `make local-dev` and removed (implicitly,
by `uv sync` wiping the venv) on flips back to registry mode. Tools and humans
check it via `make local-check` rather than inspecting the venv directly.

## The canonical target set

| Target | Behavior |
|---|---|
| `make local-setup` | Clone any missing sibling pd-* repos into `/workspaces/ocr-container/`. Idempotent. |
| `make local-dev` | Install editable Python siblings; link npm siblings; write the marker. |
| `make local-check` | Print current mode + per-sibling resolution paths. Exit 0 always. |
| `make local-upgrade-deps` | Refuse if not in local-dev mode; else `uv lock --upgrade && uv sync && make local-dev` (restoring editables that sync wiped). |
| `make local-install` | (CLI-publishing repos only) `uv tool install --editable . --with-editable ../<sibling>` for each Python sibling. |
| `make local-uninstall` | (CLI-publishing repos only) `uv tool uninstall <name>`. Venv + marker untouched. |
| `make local-run` | (CLI/server repos only) refuse outside local-dev mode; else `make run`. |
| `make ci-against-main` | (git-main validation, not local-dev) refuse in local-dev mode; flip Python siblings to GitHub `main`, lock + run the preflight, then revert. See [`ci-against-main.md`](ci-against-main.md). |

## Per-repo presence matrix

From spec §5.2:

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

`pdomain-book-tools` is the foundation lib (no siblings); its local-dev variant
means "GPU extras active + marker present" rather than sibling-editable.

The three leaves — `pdomain-ocr-synth`, `pd-png-optimizer`, `pdomain-ui` — have no pd-*
deps and so have no local-dev targets today. Add them later only if a
local-mode concern arises.

## Mode lifecycle

    registry mode  ──make local-dev──>  local-dev mode
         ^                                    │
         │                                    │
         │                                    ├─ make local-upgrade-deps ─> still local-dev
         │                                    │  (uv lock --upgrade; uv sync wipes editables;
         │                                    │   then re-runs local-dev to restore them)
         │                                    │
         └─ make update-pd-deps ──────────────┘
            (auto-flips out, bumps siblings to registry latest, flips back)

`make update-pd-deps` (spec [#363](../archive/specs/2026-05-24-update-pd-deps-design.md)
/ [plan](../plans/2026-05-24-update-pd-deps.md)) detects the marker, flips out
of local-dev mode to do its registry bump, then flips back. The human sees a
diff staged for review and ends in the same mode they started in.

## When NOT to use local-dev

- **Bot workspaces under `/srv/bot-workspaces/`** — bots always resolve from
  the registry so their results are reproducible from a clean checkout. See
  [bot-workspaces.md](bot-workspaces.md).
- **Any repo where siblings are not checked out under
  `/workspaces/ocr-container/<sibling>/`** — local-setup will clone them, but
  outside the workspace topology the relative-path assumptions in the scripts
  do not hold.

## Cross-references

- Spec: [docs/archive/specs/2026-05-24-local-dev-standardization-design.md](../archive/specs/2026-05-24-local-dev-standardization-design.md)
- Sister pattern (release): `<repo>/scripts/do-release.sh` in any pd-* repo
- Reference implementation (after #362 M1 lands): `pdomain-prep-for-pgdp/scripts/local-*.sh`
- Companion process: [update-pd-deps.md](update-pd-deps.md) (created by spec #363)
