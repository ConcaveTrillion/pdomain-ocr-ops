# `pd-*` → `pdomain-*` workspace-wide rename + org migration

**Date:** 2026-05-26
**Status:** Design — awaiting CT review before implementation planning
**Owner:** CT (ConcaveTrillion)

---

## 1. Goals & Non-Goals

### Goals

- Rename every workspace artifact whose identity begins with `pd-` (or `pd_`, or `PD_`) to the `pdomain-` / `pdomain_` / `PDOMAIN_` form, in a single coordinated cutover.
- Migrate all renamed repos from the personal `ConcaveTrillion/*` namespace to a freshly-claimed `pdomain/*` GitHub organization.
- Migrate the npm publisher identity from `@concavetrillion/*` to a freshly-claimed `@pdomain` npm scope.
- Land all renames before any package is published to PyPI under a `pdomain-*` name (other than the foundation library — see §3), so no PyPI name is wasted on an abandoned identity.
- Keep historical `pd-*` releases reachable for archaeology (GitHub auto-redirects + `pdomain-index-pip` republishes old wheels under new names for installability).
- Preserve cross-repo dep resolution end-to-end after cutover (`make ci` green in every repo, every install script still works).

### Non-Goals

- The workspace root directory `/workspaces/ocr-container/` is **not** renamed.
- The `ocr-container-meta` GH meta-tracker repo is **not** renamed (its content, however, is updated — see §4.N).
- `coding-bot/` and `stay-awake/` are **not** renamed; neither is a `pd-*` project.
- No compatibility shim or deprecation window. Old `pd-*` package names stop receiving new versions at cutover; existing installs keep working from cached wheels.
- No general PyPI publish flow in this spec. Only `pdomain-book-tools` is reserved on PyPI as part of this work; reservation + real-publish for the other repos is deferred (see §9 — Open Follow-ups).

---

## 2. Context

The workspace currently uses the `pd-` prefix on all 12 product repos plus 2 self-hosted index repos, where `pd` stands for "public domain" (the project family processes public-domain book scans for Project Gutenberg / Distributed Proofreaders workflows).

The prefix has accumulated three friction points that compound when planning external publishing:

1. **`pd-` collides with the pandas convention** (`import pandas as pd`). For an external first-time reader on PyPI, `pip install pdomain-ocr-cli` reads as a pandas plugin. Internal users understand the intent, but it's a branding mismatch when the project goes public.
2. **`pd` (bare) is already taken on PyPI** by an unrelated package; this doesn't block `pd-*` names individually, but it does fragment the namespace surface.
3. **No org identity.** All repos live under the personal `ConcaveTrillion/*` namespace. As the project family stabilizes around a coherent identity, an org is the right home.

Replacement prefix `pdomain-` was selected after weighing `cc0-` (license-claim implications), `pgdp-` (third-party-org affiliation implication), `ct-` (org-name-scoped, anonymous), and "no prefix / brand name" (loss of visual grouping). `pdomain-` is unambiguously "public domain," makes no third-party identity claim, and all relevant names are free on PyPI, npm, and GitHub.

Availability verified 2026-05-26:

- `github.com/pdomain` — 404 (available)
- `@pdomain` npm scope — 404 (available)
- All 12 `pdomain-*` PyPI names — 404 (available)

---

## 3. Decisions Made

Traceable record of resolved questions from brainstorming.

| Decision | Choice | Rationale |
|---|---|---|
| Replacement prefix | `pdomain-` | Unambiguous public-domain signal; no license-claim or third-party-affiliation baggage; all relevant names available |
| Transition strategy | Clean cutover (no compat shim) | Workspace is internal; ~zero external consumers today; shim machinery not worth its cost |
| Old wheels in `pdomain-index-pip` | Republished under new names in `pdomain-index-pip` | Keeps `pdomain-*` installs resolvable post-cutover; old simple-index URL GH-redirects |
| GH org migration | Folded in | Claiming `pdomain` GH org is free and unblocks future identity work; doing it concurrently saves a second churn cycle |
| npm scope migration | Folded in: `@pdomain` scope | Mirrors GH org identity |
| npm package naming inside scope | `@pdomain/pdomain-<x>` (keep prefix in package name) | Cross-registry character-for-character uniformity with PyPI names; mild departure from npm idiom (which would normally use `@pdomain/<x>`) |
| `~/.local/share/pd-suite/` + `PD_*` env vars | Renamed | Identity consistency; one-shot migration helper handles user state |
| `ocr-container` workspace root directory | Not renamed | Workspace name is generic, not `pd-*` |
| `ocr-container-meta` GH tracker | Repo not renamed; content updated | Name reads as "OCR container meta" generically; only narrative content references `pd-*` |
| PAT/secret rotation (`PD_INDEX_DISPATCH_TOKEN`) | Deferred to Phase 6 | Bot is currently disabled; release.yml's dispatch step is already coded as non-fatal (15-min cron safety net); no urgency |
| Per-repo dispatch secrets | Replaced by one org-level secret at `pdomain/.github` | Org migration unlocks this; one-time setup, never touch again |
| PyPI reservation scope | Only `pdomain-book-tools` reserved at Phase 0 | Other repos not ready for public; risk on the other 11 names explicitly accepted by CT |

---

## 4. Touchpoint Inventory

Grouped by surface. Each category will become one or more tasks in the implementation plan.

**A. GitHub repos (14 renames).** `pdomain-book-tools`, `pdomain-ocr-cli`, `pd-ocr-labeler`, `pdomain-ocr-labeler-spa`, `pdomain-ocr-synth`, `pd-ocr-trainer`, `pdomain-ocr-training`, `pd-png-optimizer`, `pdomain-prep-for-pgdp`, `pdomain-ops`, `pdomain-ocr-simple-gui`, `pdomain-ui`, `pdomain-index-pip`, `pdomain-index-npm` → `pdomain-*`. GitHub auto-redirects old URLs; existing clones keep working via the redirect.

**B. Python package names (12 `pyproject.toml`s).** `[project].name` flips. Every sibling dep specifier (`pdomain-book-tools >=0.10,<0.11` etc.) flips in lockstep. `[tool.uv.sources]` blocks pointing at sibling worktrees flip. Hatch-vcs configuration is unaffected.

**C. Python import paths.** `pd_book_tools` → `pdomain_book_tools`, etc. — every `from pd_*` / `import pd_*` across all 12 repos. Pure find/replace, gated on tests green per repo. Source-package directory renames included (`src/pd_book_tools/` → `src/pdomain_book_tools/`).

**D. npm packages.** `@concavetrillion/pdomain-ui` → `@pdomain/pdomain-ui` (scope changes from `@concavetrillion` to `@pdomain` *and* package name keeps the `pdomain-` prefix). Every consumer's `package.json` deps + every `import ... from '@concavetrillion/pdomain-ui'` flips.

**E. Self-hosted indexes.**
- `pdomain-index-pip` → `pdomain-index-pip`. Pages URL flips to `https://pdomain.github.io/pdomain-index-pip/simple/` (post-transfer to org). Index regenerates from the renamed wheels. Old wheels at the old Pages URL stop being maintained; existing pin-by-hash installs keep working from GH Release assets.
- `pdomain-index-npm` → `pdomain-index-npm`. `.npmrc` registry pointers flip in every consuming repo.

**F. Suite plumbing (pdomain-ops).**
- `~/.local/share/pd-suite/` → `~/.local/share/pdomain-suite/` (platformdirs path).
- `pd-suite.json` → `pdomain-suite.json` manifest filename.
- `PD_SUITE_MODE` → `PDOMAIN_SUITE_MODE` env var.
- `PD_GPU_BACKEND` → `PDOMAIN_GPU_BACKEND` env var.
- Already-installed desktop shortcuts on CT's workstation are stale post-cutover; one-time migration helper (`pdomain-ops migrate-suite-state`) copies state and re-installs shortcuts.

**G. Install scripts.** `pdomain-ocr-cli/install.sh` and `pdomain-prep-for-pgdp/install.sh` carry wheel names + simple-index URLs + the `--with 'pdomain-book-tools @ git+...'` stopgap (if still present at rename time). All three flip. Script filenames stay (`install.sh`).

**H. GitHub Actions workflows.** Every `release.yml` references the repo's old name in `gh api repos/ConcaveTrillion/pdomain-index-pip/dispatches` calls and workflow display names. Secret name `PD_INDEX_DISPATCH_TOKEN` → `PDOMAIN_INDEX_DISPATCH_TOKEN` (the rotation itself is deferred to Phase 6; the in-workflow secret reference is updated during Phase 2).

**I. Workspace `.claude/` infrastructure.**
- `.claude/agents/pd-*.md` (24 files: 12 full-power + 12 `-docs`) → `pdomain-*.md`. Every agent's `description` field + internal repo-path references update.
- `.claude/agent-memory/pd-*/` (12 directories) → `pdomain-*/`. Memory file contents pass for `pd_*` / `pd-*` strings.
- Skills `ship-slice-pd-*` (12 skills) → `ship-slice-pdomain-*`.
- Workspace `CLAUDE.md` routing tables (the big repo-list table + agent-routing section) flip.
- Per-repo `CLAUDE.md`, `CONVENTIONS.md`, `README.md` — narrative prose pass.

**J. Workspace-root tooling.**
- `scripts/repo-hygiene-check.sh`, `scripts/workspace-repos.json` (the canonical manifest), `pdomain-index-pip/scripts/regen_index.py` — references to repo names flip.
- `coding-bot/` schedule entries that reference repo paths (`/workspaces/ocr-container/pd-*/`) flip.
- `/srv/bot-workspaces/` directory naming for bot worktrees: let them regenerate on next bot run (cheaper than filesystem renames for ephemeral state).

**K. Workspace-root docs.** Already-existing workspace `docs/` tree in full: `architecture/`, `decisions/`, `plans/` (active), `process/` (notably `local-dev.md`, `update-pd-deps.md`, `bot-workspaces.md`, `picking-up-cold.md`), `research/`, `runbooks/`, `specs/` (active), `templates/`, `usage/`. Plus workspace-root `CLAUDE.md`, `MANUAL_SETUP.md`, `docs/README.md`, `.gitignore`, `.devcontainer/devcontainer.json`. Archive subfolders (`docs/archive/**`) left alone as frozen history.

**L. Memory (user-level).** `/home/vscode/.claude/projects/-workspaces-ocr-container/memory/MEMORY.md` index + ~20 entry files cite `pd-*`. One-pass update; old `pd-*` names become historical references where they appear in dated decision text.

**M. `ocr-container-meta` content** (repo name unchanged). Open cross-cut issue bodies (any `repos/ConcaveTrillion/pd-foo` URLs, prose `pdomain-book-tools`, install snippets), milestone titles of the form `spec: <plan-basename> (#N)` where the plan-basename contains `pd-*`, and any repo-identifying labels. Pass: `gh issue list --repo ConcaveTrillion/ocr-container-meta --state open --json number,title,body` → grep `pd[-_]` → edit each.

**N. Out-of-scope confirmed.** Workspace root directory name, `ocr-container-meta` repo name (content updated per §4.M), `coding-bot`, `stay-awake`, GH personal-access tokens (only the PAT's resource-allowlist entry shifts, and that's deferred).

---

## 5. Phased Execution

| Phase | Scope | Human-only steps |
|---|---|---|
| 0 | Claim identities (GH org, npm scope, PyPI placeholder for `pdomain-book-tools`) | Claim GH org + npm scope (~5 min web UI); reserve PyPI placeholder (one-shot publish) |
| 1 | Inventory manifest + dry-run harness | none |
| 2 | Python ecosystem rename (12 repos, in worktrees, coordinated push) | CT approves each repo's diff |
| 3 | GH repo renames (14 — all product + index) + index regen | none |
| 4 | Suite plumbing + state migration (pdomain-ops) | CT runs `migrate-suite-state` once |
| 4.5 | Transfer all repos `ConcaveTrillion/pdomain-*` → `pdomain/pdomain-*` (single owner-only move) | none (`gh repo transfer` is scripted) |
| 5 | Org-level dispatch secret + workflow alignment + coding-bot path flips | none if deferring PAT/secret; one-shot PAT-paste loop if doing it now (recommend defer) |
| 6 | Long tail: docs, memory, agents, meta-tracker issues, install-script GH URLs; **[deferrable]** PAT/secret swap | PAT allowlist edit + PAT paste step, when CT chooses |

### Phase 0 — Claim identities

1. Create `pdomain` GitHub organization (free tier). CT becomes sole owner.
2. Create `@pdomain` npm organization. CT becomes sole owner.
3. Reserve `pdomain-book-tools` on PyPI with a 0.0.1 placeholder package:
   - `pyproject.toml` with real metadata (name, version `0.0.1`, description, author = ConcaveTrillion / concavetrillion@gmail.com, `urls.Homepage = https://github.com/pdomain/pdomain-book-tools` — anticipated post-transfer URL, GH-redirect-safe), classifier `Development Status :: 1 - Planning`.
   - One-paragraph README pointing at the GH repo.
   - Empty stub module (`src/pdomain_book_tools/__init__.py` with a comment line) so the wheel builds.
   - Build with `uv build`, publish with `uv publish` using a one-shot PyPI API token (Trusted Publishing setup is overkill for a single placeholder upload; the real-publish follow-on spec will switch to GH OIDC). PyPI account must have 2FA enabled (mandatory as of 2024).

### Phase 1 — Inventory manifest + dry-run harness

1. Hand-write `scripts/rename/rename-manifest.json` at workspace root: every old → new mapping (repos, packages, npm names, env vars, paths, secret names, agent slugs, skill slugs, memory slugs, doc strings). One source of truth driving every later phase.
2. Write `scripts/rename/apply-rename.py` — a repo-scoped harness consuming the manifest that does the find/replace in a single tree at a time, with `--dry-run`, `--scope=<repo>`, and a JSON `changes.json` audit report. No git operations; pure file edits.
3. Smoke-test against `pd-png-optimizer` (smallest tree) on a throwaway worktree. Discard the worktree.

### Phase 2 — Python ecosystem rename

The hard phase. All Python package + import renames land **in one push window** because cross-repo deps mean partial rollouts break `make ci` in downstream repos. Per-repo work happens in isolated worktrees in parallel; pushes coordinate at the end.

Per repo, in dependency order (`pdomain-book-tools` first, then `pdomain-ops` and `pd-png-optimizer`, then `pdomain-ui` Python-side if any, then leaf consumers):

1. Run `apply-rename.py --scope=<repo>` in a worktree.
2. Tree-wide find/replace: `pd_<x>` → `pdomain_<x>` Python identifiers; `pd-<x>` → `pdomain-<x>` package names + dep specifiers; install-script wheel-name strings; workflow `repos/ConcaveTrillion/pd-*` paths.
3. Rename source package directory (`src/pd_book_tools/` → `src/pdomain_book_tools/`).
4. `make ci AI=1` in the worktree. Must go green using **sibling worktrees from the same window** for cross-repo deps (each repo's `[tool.uv.sources]` points at sibling worktrees, not registry).
5. Commit on a `rename/pdomain` branch; do **not** merge yet.

Coordinated push: when all 12 worktrees are CI-green, fast-forward `main` in each repo in dep order, push, then immediately move to Phase 3 (index regen) so the simple-index reflects the new wheel names before any consumer pulls fresh.

### Phase 3 — GH repo renames + index regen

All 14 repos rename in place under `ConcaveTrillion/` (org transfer is Phase 4.5; no intermediate `pdomain/pd-<x>` state).

1. Rename the 12 product repos: `gh repo rename pdomain-<x> --repo ConcaveTrillion/pd-<x>` per repo. GH preserves the redirect from the old name.
2. Rename the 2 index repos: `gh repo rename pdomain-index-pip --repo ConcaveTrillion/pdomain-index-pip` and the npm equivalent.
3. Run the rename harness against the index repos (out of Phase 2 scope because they have no `make ci` to gate against): `apply-rename.py --scope=pdomain-index-pip` and `--scope=pdomain-index-npm`. This rewrites `regen_index.py` to grep GH Releases under the new product-repo names plus any embedded URL strings.
4. Trigger regen. Verify `https://concavetrillion.github.io/pdomain-index-pip/simple/` serves `pdomain-book-tools` etc. (Pages URL owner-prefix flips to `pdomain.github.io` after Phase 4.5.)
5. Update `.npmrc` registry pointer in every consuming repo (already touched in Phase 2's file edits, but verify the URL now reflects `pdomain-index-npm`).
6. Smoke test: a fresh `uv tool install pdomain-ocr-cli --extra-index-url https://concavetrillion.github.io/pdomain-index-pip/simple/` resolves end-to-end.

*Note on Phase 2 → Phase 3 gap:* Phase 2's tree-wide rename updates each `release.yml`'s dispatch target from `ConcaveTrillion/pdomain-index-pip` to `ConcaveTrillion/pdomain-index-pip`. Between Phase 2's push and Phase 3's rename of the index repo, any release triggered would dispatch to a not-yet-existing target and emit `::warning::pdomain-index-pip dispatch failed`. This is the existing release.yml's graceful-degradation path (15-min cron catches up); acceptable. Phase 3 runs immediately after Phase 2's push to keep this window short.

### Phase 4 — Suite plumbing + state migration

Code already renamed in Phase 2; this phase is the runtime / state-migration piece.

Ship a `pdomain-ops migrate-suite-state` one-shot command (or Make target) that:

1. Copies `~/.local/share/pd-suite/` → `~/.local/share/pdomain-suite/` if the destination doesn't exist.
2. Rewrites the manifest filename inside (`pd-suite.json` → `pdomain-suite.json`).
3. Re-installs desktop shortcuts pointing at the new paths.
4. Leaves old `pd-suite/` intact for one release as fallback.

Env-var migration: any developer shell that hardcodes `export PD_SUITE_MODE=...` updates manually. The library reads `PDOMAIN_*` only post-Phase-2; document the cutover in workspace `CLAUDE.md`. Active shell sessions need explicit `unset PD_SUITE_MODE PD_GPU_BACKEND` and re-export of `PDOMAIN_*` equivalents — no inheritance trick covers this.

CT runs the migration on the workspace machine once.

### Phase 4.5 — Org transfer (single owner-only move, no name change)

By this point all 14 repos already carry their final `pdomain-*` names under `ConcaveTrillion/`.

1. `gh repo transfer ConcaveTrillion/pdomain-<x> pdomain` for each of the 14 repos. GH redirects all old URLs to the new owner. Issues / PRs / releases / wiki / workflows carry over.
2. In every active local checkout: `git remote set-url origin https://github.com/pdomain/pdomain-<x>.git`. GH redirect would work transparently, but the explicit set-url makes the new identity sticky and avoids future audit confusion.
3. Update install scripts to point at the post-transfer Pages URL: `https://concavetrillion.github.io/pdomain-index-pip/simple/` → `https://pdomain.github.io/pdomain-index-pip/simple/` in `pdomain-ocr-cli/install.sh`, `pdomain-prep-for-pgdp/install.sh`, and any consumer's `.npmrc`. GH Pages serves both URLs (old emits 301 to new) during a transition window, but pinning to the final form post-transfer avoids accumulating redirect hops.
4. Existing `PD_INDEX_DISPATCH_TOKEN` PAT's resource-allowlist still points at `ConcaveTrillion/pdomain-index-pip`; left alone here, swept in Phase 6.

After Phase 4.5: all repos live at their final paths `pdomain/pdomain-<x>`; install scripts reference the final Pages URLs.

### Phase 5 — Org-level dispatch secret + workflow alignment + bot path flips

1. Create `pdomain/.github` org-level secret `PDOMAIN_INDEX_DISPATCH_TOKEN`. Set its value once (CT pastes PAT). The PAT itself is unchanged; only its resource-allowlist needs the Phase 6 deferrable edit.
2. Update every member repo's `release.yml` to consume the org-level secret name `PDOMAIN_INDEX_DISPATCH_TOKEN` (already done in Phase 2 file edits — verify here that the workflow secret reference matches what's set at the org level).
3. `coding-bot/` schedule-entry repo paths flip.
4. `/srv/bot-workspaces/` directories left to regenerate on next bot run.

### Phase 6 — Long tail

Parallelizable, doesn't block daily work, lands over several days.

- `.claude/agents/pd-*.md` → `pdomain-*.md` (24 files), `description:` fields, path references inside prompts.
- `.claude/agent-memory/pd-*/` (12 dirs) → `pdomain-*/`; one-pass content edit for `pd_*` / `pd-*` strings in memory bodies.
- Skills `ship-slice-pd-*` → `ship-slice-pdomain-*` (12 skills); update `description:` and any hardcoded paths.
- Workspace-root `CLAUDE.md` + per-repo `CLAUDE.md` / `CONVENTIONS.md` / `README.md`.
- Workspace `docs/` tree (active folders only; archive untouched).
- User-level `MEMORY.md` index + ~20 entry files (mark dated decisions as historical when they cite `pd-*` literally; rename slugs).
- `ocr-container-meta` open-issue audit: `gh issue list --state open --json number,title,body` → batch-edit any issue body referencing `pd-*` repos via `gh issue edit`. Same for milestone titles.
- **[deferrable, manual]** PAT/secret swap:
  - Web UI: open `https://github.com/settings/personal-access-tokens`, find the existing dispatch PAT, edit its resource allowlist to `pdomain/pdomain-index-pip` (remove `ConcaveTrillion/pdomain-index-pip`). Save.
  - One-shot scripted loop:
    ```bash
    read -s PAT   # CT pastes once, never echoed
    for repo in pdomain-{book-tools,ocr-cli,ocr-labeler,ocr-labeler-spa,ocr-synth,ocr-trainer,ocr-training,png-optimizer,prep-for-pgdp,ocr-ops,ocr-simple-gui,ui}; do
      gh secret delete PD_INDEX_DISPATCH_TOKEN --repo pdomain/$repo 2>/dev/null
    done
    unset PAT
    ```
  - (Org-level `PDOMAIN_INDEX_DISPATCH_TOKEN` was set in Phase 5; this just removes the now-redundant per-repo secrets.)

---

## 6. Testing & Verification Gates

Each phase has runnable/observable gates. The implementation plan will turn these into per-task acceptance criteria.

### Phase 0 gates
- `gh org view pdomain --json login,createdAt` returns the freshly-created org.
- `curl https://www.npmjs.com/~pdomain` returns the org page under CT's ownership.
- `pip index versions pdomain-book-tools` shows `0.0.1` on PyPI.

### Phase 1 gates
- `python scripts/rename/apply-rename.py --dry-run --scope=pd-png-optimizer` produces a deterministic `changes.json` audit report.
- Audit report's old→new mappings each appear in `rename-manifest.json` (no surprise renames).
- Re-running the harness against the same tree is a no-op (idempotency check).

### Phase 2 gates (per repo, then cohort-wide)
- Per-repo worktree: `make ci AI=1` green with sibling worktrees pinned via `[tool.uv.sources]`.
- Per-repo grep: `grep -r "pd[-_]" src/ tests/ pyproject.toml` returns only intentional matches (comments referencing the rename, archival prose). No live identifiers remain.
- Cohort gate before push: all 12 worktrees report green on the same harness day. If even one fails, no repo pushes — the window slips.
- Post-push sentinel: a fresh `uv pip install pdomain-book-tools` from sibling-worktree source resolves cleanly.

### Phase 3 gates
- `gh repo view pdomain/pdomain-book-tools` (and the other 13) returns 200; `gh repo view pdomain/pdomain-book-tools` redirects to the new name.
- `curl https://concavetrillion.github.io/pdomain-index-pip/simple/` returns the regenerated index HTML listing `pdomain-*` packages (Pages URL owner-prefix flips to `pdomain.github.io` after Phase 4.5).
- Smoke install: `uv tool install pdomain-ocr-cli --extra-index-url https://concavetrillion.github.io/pdomain-index-pip/simple/` on a clean throwaway env resolves and runs `--help`.
- Old simple-index URL GH-redirects (`curl -L`) to the new URL.

### Phase 4 gates
- `pdomain-ops migrate-suite-state` exits 0; `~/.local/share/pdomain-suite/` exists with same JSON content as old dir.
- Launching any `pdomain-*` SPA backend reads prefs from the new path; old path remains intact as fallback.
- `env | grep -E '(^|_)PD_'` empty in fresh shells (or only contains intentional non-pdomain entries).

### Phase 4.5 gates
- `gh repo view pdomain/pdomain-book-tools` returns 200 (final name and owner); `gh repo view pdomain/pdomain-book-tools` redirects to the new owner.
- All 14 expected repos appear in `gh repo list pdomain --limit 50`.
- Each active local checkout's `git remote -v` shows `pdomain/pdomain-<x>` URLs.
- One live test push from a workspace checkout lands in the new owner's repo.

### Phase 5 gates
- Org-level secret `PDOMAIN_INDEX_DISPATCH_TOKEN` exists at `pdomain/.github`: `gh secret list --org pdomain` shows it.
- Every member repo's `release.yml` references the org-level secret name (grep across `.github/workflows/release.yml` in all 14 repos).
- Per-repo `PD_INDEX_DISPATCH_TOKEN` either removed (if Phase 6 PAT swap done) or still present as a no-op (acceptable — dispatch step is non-fatal).
- One fired release workflow on a renamed repo successfully dispatches to `pdomain-index-pip`, or warns non-fatally if PAT step still deferred.
- `coding-bot/` schedule entries reference `pdomain/pdomain-<x>` paths.

### Phase 6 gates
- Workspace `grep -rn 'pd[-_]' .claude/ docs/` returns only deliberate historical references (dated decision text, archive prose).
- Workspace `MEMORY.md` index reads coherently with renamed slugs.
- `gh issue list --repo ConcaveTrillion/ocr-container-meta --state open --search 'pdomain-book-tools OR pdomain-ocr-cli'` returns zero issues (all references updated).
- A fresh `git clone https://github.com/pdomain/pdomain-book-tools` smoke-runs `make ci AI=1` in each repo with zero `pd[-_]` warnings from any tool.

### Cross-cutting acceptance criterion

The rename is "done" only when a fresh developer cloning the workspace with no prior `pd-*` knowledge cannot find any live `pd[-_]` identifier (excluding intentional history references). Audit:

```bash
grep -rn 'pd[-_]' /workspaces/ocr-container \
  --exclude-dir='.git' \
  --exclude-dir='archive' \
  --exclude-dir='node_modules' \
  --exclude-dir='.venv' \
  | grep -v '# pre-rename:' \
  | grep -v 'historical:'
```

Empty output ⇒ done.

---

## 7. Risks & Rollback

### Risk: cross-repo `make ci` breaks mid-cutover (Phase 2)

The Python ecosystem rename is the one phase where partial rollout actively breaks things — `pdomain-ocr-cli` depending on a sibling that still publishes as `pdomain-book-tools` won't resolve.

*Mitigation:* every repo's Phase-2 worktree uses sibling-worktree `[tool.uv.sources]` overrides during local CI. All 12 push in one window. If any single repo's CI red-lines during the window, the window aborts and all worktrees stay un-pushed (no half-state lands in `main`).

*Rollback:* `git branch -D rename/pdomain` per worktree, drop worktrees. Zero residue.

### Risk: index regen fetches stale wheels and serves a broken simple-index page (Phase 3)

`regen_index.py` greps GH Releases under the new repo names. If it runs before all 12 repos have actually pushed renamed releases, the index renders empty or partial.

*Mitigation:* Phase 3 runs *after* Phase 2's coordinated push succeeds. Smoke test (`uv tool install pdomain-ocr-cli ...`) before declaring Phase 3 done.

### Risk: suite-state migration misses files (Phase 4)

`~/.local/share/pd-suite/` likely contains hand-edited prefs, recently-cached state, possibly schema-versioned JSON.

*Mitigation:* `migrate-suite-state` copies (not moves) the old directory; old `pd-suite/` stays intact as fallback for one release cycle. CT removes manually once `pdomain-suite/` is verified good.

### Risk: repo transfer breaks in-flight branches / open PRs (Phase 4.5)

`gh repo transfer` preserves issues, PRs, branches, releases, and Actions — but any local checkout's remote URL still points at `https://github.com/ConcaveTrillion/<repo>.git`. GH redirects, but doesn't rewrite.

*Mitigation:* after transfer, run `git remote set-url origin https://github.com/pdomain/<repo>.git` in every active checkout (workspace + bot worktrees + CT's own machines). One-line script step.

### Risk: external deep-links rot

Old GitHub URLs in third-party docs, blog posts, etc. continue to redirect through GH only as long as the old owner+name pair stays unused.

*Mitigation:* don't reuse `ConcaveTrillion/pd-<x>` names for anything else post-transfer. Discipline-only mitigation; no code change.

### Risk: PyPI placeholder squatting on the 11 unreserved names

Between today and whenever the other `pdomain-*` repos go public, a third party could claim one of those PyPI names.

*Mitigation accepted by CT:* recovery is a PEP 541 dispute. Public GH repo trail under the `pdomain` org makes a successful dispute likely; it is friction, not a blocker. Bulk-reserve the remaining 11 in one afternoon at any time if the risk feels material.

### Risk: PEP 541 challenge against the `pdomain-book-tools` placeholder

A passerby on PyPI could file a PEP 541 dispute against the `0.0.1` placeholder, claiming squatting, during the gap between Phase 0 publish and the first real release.

*Mitigation:* placeholder follows the §3 recipe (real metadata, README linking to public GH repo, `Development Status :: 1 - Planning`, real author identity). PyPI admins evaluating a dispute would see a credible active project. CT must respond to any admin email promptly (PyPI gives the maintainer time to respond before transferring a name); if CT is unreachable, the name could be transferred. Practical guard: enable email notifications on the PyPI account and check monthly. Once the real first release ships, this risk drops to ~zero.

### Rollback strategy (whole spec)

- Phases 0-1 are pure-claim and harness-write — no rollback needed; both are reversible (delete the GH/npm orgs, delete the harness branch).
- Phase 2 rolls back via `git branch -D rename/pdomain` per worktree if it aborts before push. Once pushed, "rolling back" means a new rename PR back to `pd-*` — same cost as the original rename. Phase 2 is the point of no comfortable return.
- Phases 3-6 each roll back individually by reverting the relevant commit; none depend on irreversible global state.

---

## 8. Out of Scope (explicit)

- PyPI publishing for any repo other than `pdomain-book-tools` (placeholder only). Real-publish + reservation for the other 11 names is a follow-on per-repo spec.
- Workspace root directory `/workspaces/ocr-container/` rename.
- `ocr-container-meta` GH meta-tracker repo rename (content is updated; name stays).
- `coding-bot/` and `stay-awake/` projects.
- The `@concavetrillion/` npm scope itself (left intact; just no longer published into).
- Personal-access-token rotation as a whole (only the dispatch-PAT allowlist entry shifts).

---

## 9. Open Follow-ups

These are intentionally not in this spec but should be tracked.

- **Reserve the remaining 11 `pdomain-*` names on PyPI** when each becomes near-public. Reuse the Phase 0 placeholder recipe per repo.
- **Real PyPI publish for `pdomain-book-tools`** (move from `0.0.1` placeholder to real version). Separate spec; extends existing `release.yml` to add `uv publish` via PyPI Trusted Publishing.
- **PAT allowlist edit + per-repo secret cleanup** (the Phase 6 deferrable item) — execute when the bot is re-enabled or instant index regen becomes useful again.
- **Decommission `@concavetrillion/` npm scope** if abandoned long enough — purely a tidying step, no urgency.
- **Decommission old `pdomain-index-pip` / `pdomain-index-npm` Pages URLs** after a holding period (e.g., 6 months). GH redirect keeps working; this is just cleanup.

---

## Appendix: name mapping summary

| Surface | Old | New |
|---|---|---|
| GH org | `ConcaveTrillion` (personal) | `pdomain` (org) |
| npm scope | `@concavetrillion` | `@pdomain` |
| GH repo prefix | `pd-` | `pdomain-` |
| Python package prefix | `pd-` / `pd_` | `pdomain-` / `pdomain_` |
| npm package | `@concavetrillion/pdomain-ui` | `@pdomain/pdomain-ui` |
| Self-hosted PyPI index | `pdomain-index-pip` | `pdomain-index-pip` |
| Self-hosted npm index | `pdomain-index-npm` | `pdomain-index-npm` |
| Suite state dir | `~/.local/share/pd-suite/` | `~/.local/share/pdomain-suite/` |
| Suite manifest | `pd-suite.json` | `pdomain-suite.json` |
| Suite-mode env | `PD_SUITE_MODE` | `PDOMAIN_SUITE_MODE` |
| GPU-backend env | `PD_GPU_BACKEND` | `PDOMAIN_GPU_BACKEND` |
| Dispatch secret | `PD_INDEX_DISPATCH_TOKEN` (per-repo) | `PDOMAIN_INDEX_DISPATCH_TOKEN` (org-level) |
| `.claude/agents/` slugs | `pd-<x>.md`, `pd-<x>-docs.md` | `pdomain-<x>.md`, `pdomain-<x>-docs.md` |
| `.claude/agent-memory/` dirs | `pd-<x>/` | `pdomain-<x>/` |
| Skill slugs | `ship-slice-pd-<x>` | `ship-slice-pdomain-<x>` |
