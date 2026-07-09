# Workspace GH label taxonomy — canonical definition + cross-repo sync

**Date:** 2026-05-17
**Session:** `gh-label-taxonomy`
**Scope:** Workspace-wide. Covers all 9 GitHub repos under `ConcaveTrillion/*` that track work
(8 `pd-*` repos + `ocr-container-meta`). Reconciles drift observed today and locks the canonical
label vocabulary used by the `/triage`, `/spec-from-issue`, `/decompose-spec`, and `/ship-issue`
skills and by the cost dashboard.

Related: [2026-05-17-superpowers-gh-workflow-integration-design.md](2026-05-17-superpowers-gh-workflow-integration-design.md)
(workflow this taxonomy describes) and the cost-dashboard redesign spec dated the same day
(consumer of this taxonomy).

---

## 1. Goals & non-goals

### Goals

1. Define one canonical label vocabulary for the workspace, covering the full
   feature-request → triage → spec → plan/decompose → task → ship lifecycle.
2. Document each label's name, meaning, color, mutually-exclusive group, and which
   skill/automation produces or consumes it.
3. Provide an idempotent `scripts/sync-labels.sh` that brings every repo to the canonical
   state — creates missing labels, renames drifted labels, optionally deletes orphans.
4. Capture repo-local label extensions (`hifi:P*` in labeler-spa, `backend:*` in
   png-optimizer) so they coexist with the canon without being treated as drift.
5. Give the cost dashboard a single source of truth for column names, chip colors, and
   filter axes.

### Non-goals

1. No new lifecycle stages — this is documentation + reconciliation of what already
   exists in practice.
2. No GitHub Projects board integration — `status:*` labels remain the kanban dimension.
3. No automatic relabeling of historical issues. Sync touches the *label catalog* per repo,
   not the labels applied to specific issues.
4. No changes to `triage:*`, `kind:*`, `effort:*` semantics observed today — only naming
   alignment and gap-filling.
5. No deprecation of `bot:*` workflow labels — those are governed by the bot orchestrator
   and out of scope here.

---

## 2. The five-stage lifecycle

Every piece of work moves through five stages. Skills drive transitions; labels mark state.

| # | Stage | Entry skill | Output | Label markers |
|---|---|---|---|---|
| 1 | Request | filed by CT or agent | `kind:feature-request` issue | `kind:feature-request` (no `status:*` yet) |
| 2 | Triage | `/triage <N>` | child `kind:spec` or `kind:feature/bug/chore` or closed | `triage:*` on parent; `status:backlog` on child |
| 3 | Spec | `/spec-from-issue <N>` | spec doc + draft PR + milestone | `kind:spec`, `status:in-progress` while drafting |
| 4 | Plan / decompose | `/decompose-spec --sync` | child task issues attached to milestone | child issues land with `status:backlog` |
| 5 | Task / ship | `/ship-issue` | PR + merge | `status:ready → in-progress → in-pr → done` |

Bugs and chores enter at stage 4 directly (`kind:bug` / `kind:chore` filed by CT or by a
skill, with no preceding feature-request or spec). The label taxonomy covers both paths.

---

## 3. Canonical axes

### 3.1 `kind:*` — what is this issue? (mutually exclusive)

| Label | Meaning | Color | Skills that produce |
|---|---|---|---|
| `kind:feature-request` | Untriaged request; the entry point | `#5d9fdf` (ocr-blue) | filed by user/agent |
| `kind:spec` | Design issue with a spec doc | `#a888d4` (gt-purple) | `/triage` (when approved → spec) |
| `kind:decision` | Architectural decision record; no implementation | `#d6925a` (accent) | `/triage` (when architectural) |
| `kind:feature` | Buildable feature task | `#5fbf6a` (exact-green) | `/decompose-spec`, direct file |
| `kind:bug` | Defect | `#dc6555` (mismatch-red) | direct file |
| `kind:chore` | Maintenance / infra task | `#7a7a85` (ink3-grey) | `/decompose-spec`, direct file |
| `kind:tracking` | Parent issue collecting children; no work of its own | `#e8a83a` (fuzzy-amber) | manual; `/triage` (when `triage:needs-tracking`) |

Exactly one `kind:*` label per issue. Required.

### 3.2 `status:*` — kanban position (mutually exclusive; defines column order)

| Label | Meaning | Column color | Set by |
|---|---|---|---|
| *(none)* | Unlabeled — needs `/triage` or status assignment | `bgSunk` with `mismatch` left border | n/a |
| `status:backlog` | Accepted, not started | `bgPage` | `/triage`, `/decompose-spec` |
| `status:ready` | Claimed/queued for next session | tint `#5fbf6a1a` | CT (arm for ship-issue) |
| `status:in-progress` | Actively being worked | tint `#e8a83a1a` | `/ship-issue` |
| `status:in-pr` | PR open, awaiting merge | tint `#5d9fdf1a` | `/ship-issue`, bot-merge skills |
| `status:done` | Merged, closed satisfactorily | tint `#5fbf6a1a` (lighter) | merge skill / CT |
| `status:archived` | Closed without delivery (cancelled, superseded) | tint `#7a7a8533` | CT |
| `status:blocked` | Waiting on external dep or decision | tint `#dc65551a` | CT, ship-issue (bounce) |
| `status:bounced` | ship-issue cycle failed; needs human triage | tint `#dc6555` + left border `#e99695` | `/ship-issue` |

`status:in-review` (currently only in `pd-png-optimizer`) is **renamed to `status:in-pr`** for
workspace consistency. Both states are open issues with an open PR.

A `kind:tracking` parent never has a `status:*` label — its rollup status is implicit (open
when any child is open).

### 3.3 `triage:*` — outcome of `/triage` on a feature-request

| Label | Meaning |
|---|---|
| `triage:approved` | Moved forward; child issue of `kind:feature/bug/chore` filed |
| `triage:needs-spec` | Approved as requiring design; `kind:spec` child filed |
| `triage:needs-tracking` | Needs a tracking parent first |
| `triage:tracking` | Is a tracking parent issue |
| `triage:rejected` | Closed by triage decision |
| `triage:proposed-by-agent` | Child auto-proposed by an agent; needs human confirm |

Applied to feature-request issues (and sometimes children) by the `/triage` skill.
`triage:rejected` issues are hidden from the cost dashboard by default.

### 3.4 `effort:*` — planning estimate (mutually exclusive)

| Label | Meaning |
|---|---|
| `effort:S` | Under a session |
| `effort:M` | One full session |
| `effort:L` | Multiple sessions |
| `effort:XL` | Spec-sized; should not be a task — decompose first |

Set by `/decompose-spec` and `/spec-from-issue` based on plan-task complexity.

---

## 4. Cross-cutting axes

### 4.1 `model:*` — which Claude model is right for this work

`model:haiku`, `model:sonnet`, `model:opus`. Set by `/decompose-spec` and `/spec-from-issue`.

### 4.2 `model-effort:*` — compute budget within the chosen model

`model-effort:low`, `:medium`, `:high`, `:xhigh`, `:max`. Set alongside `model:*`.

### 4.3 `priority:*` — `priority:low`, `:medium`, `:high`

Optional. Set by CT when needed.

### 4.4 `area:*` — `area:ci | deps | docs | refactor | tests`

Optional. Set when an issue is meaningfully scoped to one area.

### 4.5 `recurring:*` — `recurring:weekly | monthly | quarterly`

Marks recurring chore issues that re-fire on cadence.

### 4.6 `bot:*` — workflow gating

Out of scope for this spec; governed by the bot orchestrator. The names listed here are
informational only:
- `bot:ship-issue-ready` — armed for ship-issue pickup
- `bot:merge-ready` — child of a wip branch ready to merge
- `bot:style-fixed-by-agent`, `bot:style-review-ready`, `bot:style-sweep-ready` — style flow gates
- `bot:blocks-all` — global pause
- `bot:fix-wip` — agent should clean up wip branch
- `bot:paused` — repo-level pause

---

## 5. Repo-local extensions (allowed, not drift)

Some repos have extra labels that serve repo-specific workflows. These coexist with the
canon and are explicitly allowed:

| Repo | Local labels | Purpose |
|---|---|---|
| `pdomain-ocr-labeler-spa` | `hifi:P1 \| hifi:P2 \| hifi:P3 \| hifi:P4 \| hifi:P5` | Hi-fi design priority levels for the FastAPI+React rebuild |
| `pd-png-optimizer` | `backend:claude \| backend:codex \| backend:grok` | Multi-AI-backend planning for the Rust core |

`sync-labels.sh` does not touch these. If a repo adopts a new local extension, document it
here.

---

## 6. Drift reconciliation plan

Verified by running `gh label list --repo ConcaveTrillion/<repo>` on every repo
on 2026-05-17. The following changes bring each repo to canonical state.

| Repo | Action | Label change |
|---|---|---|
| `pdomain-book-tools` | DELETE | `test-label-123` (stale test artifact) |
| `pdomain-book-tools` | CREATE | `status:in-pr`, `kind:decision`, `kind:tracking` |
| `pdomain-ocr-cli` | CREATE | `status:in-pr`, `kind:decision`, `kind:tracking` |
| `pd-ocr-labeler` | CREATE | `status:in-pr`, `kind:decision`, `kind:tracking` |
| `pdomain-ocr-labeler-spa` | (already has `status:in-pr`) | CREATE `kind:decision`, `kind:tracking` |
| `pdomain-ocr-synth` | CREATE | `status:in-pr`, `kind:decision`, `kind:tracking` |
| `pd-ocr-trainer` | CREATE | `status:in-pr`, `kind:decision`, `kind:tracking` |
| `pd-png-optimizer` | RENAME | `status:in-review` → `status:in-pr` |
| `pd-png-optimizer` | CREATE | `status:ready`, `status:done`, `priority:low/medium/high`, `triage:needs-spec`, `triage:needs-tracking`, `triage:tracking`, `triage:proposed-by-agent`, `effort:XL`, `model-effort:max`, `model-effort:xhigh`, `recurring:quarterly`, `recurring:weekly`, `kind:feature-request` |
| `pdomain-prep-for-pgdp` | CREATE | `kind:decision`, `kind:tracking` |
| `ocr-container-meta` | CREATE | `status:bounced`, `status:in-pr`, `status:archived`, `kind:decision`, `kind:tracking`, `priority:low/medium/high`, `effort:M`, `effort:XL`, `area:ci/deps/docs/refactor/tests` |

Rename, not delete-and-recreate: GH preserves issue assignments on rename, so
`status:in-review` issues in `pd-png-optimizer` keep their label.

`status:archived` (`pd-png-optimizer`'s existing label, now canonical) is propagated only
on demand — not every repo needs it day 1.

---

## 7. `sync-labels.sh` design

### 7.1 Location

```
/workspaces/ocr-container/
  scripts/
    sync-labels.sh           # entry point (bash)
    sync-labels-canon.json   # canonical label catalog (the table from §3 + §4 in JSON)
```

`sync-labels-canon.json` is the machine-readable source of truth. The cost dashboard reads
it; this spec's tables are the human-readable mirror, kept in sync by hand.

### 7.2 Behavior

```bash
scripts/sync-labels.sh [--dry-run] [--repo <repo>] [--delete-orphans]
```

For each repo (all 9 by default, or filtered with `--repo`):

1. `gh label list --repo ConcaveTrillion/$repo --json name,color,description` → current state.
2. Diff against `sync-labels-canon.json`:
   - **Create** labels in canon but not in repo (`gh label create`).
   - **Update** color/description if they drift from canon.
   - **Rename** when a known-stale name maps to a canon name (`status:in-review` → `status:in-pr`). Renames listed in a `renames:` block in the JSON.
   - **Leave alone** repo-local extensions from §5.
   - With `--delete-orphans`: delete any label not in canon and not in §5 (after confirm prompt unless `--yes`).
3. Print a per-repo summary: `created N · updated M · renamed K · skipped Q (local) · orphans R`.

### 7.3 Safety

- `--dry-run` is the default if `gh auth status` reports unauthenticated, prevents accidental
  destructive runs.
- `--delete-orphans` requires either `--yes` or interactive confirmation per repo.
- All operations are idempotent. Re-running with no changes prints `nothing to do`.
- Renames preserve label history. Creates set color + description from canon.
- No issue-level operations — the script never touches labels *applied to* issues, only the
  catalog.

### 7.4 Implementation notes

- Bash with `jq`, no Python dependency, runs anywhere `gh` runs.
- Token: prefers `$GH_TOKEN`, falls back to `/run/secrets/gh-token-pd` (matches the cost
  dashboard's existing pattern).
- Runs in <30s for all 9 repos when no changes needed; longer first-run when many creates.

---

## 8. Cost-dashboard interface

The cost dashboard's redesign spec consumes `sync-labels-canon.json`:

- **Kanban columns** ordered from the canon's `status:*` block: `unlabeled | backlog | ready
  | in-progress | in-pr | done | archived | blocked | bounced`.
- **Column tint colors** taken from canon (`tint` field per label).
- **Kanban filter chips** for `kind:*` derived from canon's `kind:*` block.
- **Effort filter chips** derived from canon's `effort:*` block.
- **In Progress tab** filters by the union `status:in-progress + status:in-pr +
  status:in-review` (the last only matters during the migration window).
- **Triage rejected hidden by default**: dashboard filters out issues labeled
  `triage:rejected` unless an explicit "show rejected" toggle is set.

The dashboard's Python code reads `sync-labels-canon.json` once at build time; column
order, chip colors, and filter-chip sets all come from there.

---

## 9. Implementation plan

Three slices, ordered by risk and dependency.

### Slice 1 — write the canonical doc + JSON (no GH changes)

- Write `docs/label-taxonomy.md` (short reference doc; this spec is the long form).
- Write `scripts/sync-labels-canon.json` (machine-readable canon).
- Commit. Verify against today's labels with a one-off `gh label list | diff` check.
- No live label changes yet.

### Slice 2 — write and test `sync-labels.sh` (dry-run only)

- Implement the script per §7.
- Run `--dry-run` against all 9 repos; verify the planned changes match §6's table.
- Iterate until clean.

### Slice 3 — apply the canonical state

- Run `sync-labels.sh` (no `--dry-run`) without `--delete-orphans` first; creates/renames/updates
  only. Verify in GH UI per repo.
- Run again with `--delete-orphans --yes` after confirming no in-flight work uses the orphans.
- Commit any taxonomy adjustments discovered during reconciliation.

After Slice 3 lands, the cost-dashboard redesign spec can rely on the canon being the
single source of truth.

### Future extensions (out of scope here)

- Pre-commit hook on `scripts/sync-labels-canon.json`: regenerate `docs/label-taxonomy.md`
  tables from JSON to keep them in lockstep.
- Issue templates per repo (`.github/ISSUE_TEMPLATE/*.yml`) auto-applying canonical labels at
  filing time.
- `gh-label-drift` script that diffs live state against canon weekly and opens an issue on
  drift.
