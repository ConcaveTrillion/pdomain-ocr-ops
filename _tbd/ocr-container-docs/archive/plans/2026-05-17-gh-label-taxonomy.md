---
milestone: 10
repo: ConcaveTrillion/ocr-container-meta
status: complete
synced: 2026-05-17
---

# GH label taxonomy — canonical catalog + sync script + repo reconciliation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lock the workspace label vocabulary as a machine-readable JSON catalog + human-readable markdown doc, ship an idempotent `sync-labels.sh` script that brings every repo to canonical state, and reconcile the drift documented in
[2026-05-17-gh-label-taxonomy-design.md §6](../specs/2026-05-17-gh-label-taxonomy-design.md).

**Architecture:** `scripts/sync-labels-canon.json` is the single source of truth. `docs/label-taxonomy.md` is a hand-curated mirror of the JSON, scoped for human readers. `scripts/sync-labels.sh` is a bash + `jq` + `gh` script that diffs a target repo against canon and applies create / rename / update / (optional) delete operations. The cost-dashboard build script will later consume `sync-labels-canon.json` for column ordering and chip colors.

**Tech Stack:** bash, jq, GitHub CLI (`gh`), JSON. No Python. Runs anywhere `gh auth status` succeeds.

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Canon format | Single JSON file at `scripts/sync-labels-canon.json` | Machine-readable; both bash script and Python dashboard read it |
| Doc location | `docs/label-taxonomy.md` (workspace root, not under `docs/superpowers/`) | Cross-cutting; not a spec, not a plan; lives next to other top-level conventions |
| Rename mechanism | `gh label edit <old> --name <new>` | Preserves history and issue associations |
| Delete safety | `--delete-orphans` opt-in, requires `--yes` or confirmation | Destructive op; default behavior must be safe |
| Token source | `$GH_TOKEN` env, fallback `/run/secrets/gh-token-pd` | Matches existing pattern in `cost-dashboard/build-cost-dashboard.py` |
| Repo list | Read from canon JSON `repos:` array | Single source of truth; adding a new repo = edit JSON |
| Repo-local extensions | Listed in canon JSON `local_extensions:` per repo | Script preserves them on `--delete-orphans` |
| Test repo | Use `pdomain-book-tools` for end-to-end verification | Has the cleanest current label state; easy to spot diffs |

---

## File structure

| Path | Action | Purpose |
|---|---|---|
| `scripts/sync-labels-canon.json` | CREATE | Canonical label catalog (JSON) |
| `scripts/sync-labels.sh` | CREATE | Idempotent sync script (bash) |
| `scripts/tests/test_sync_labels.bats` | CREATE | Smoke tests using `bats` shell test framework |
| `docs/label-taxonomy.md` | CREATE | Human-readable reference doc |

No existing files modified. The downstream dashboard work modifies `cost-dashboard/` files; that lives in the dashboard plan, not this one.

---

## Task 1 — Write canonical JSON catalog {#canon-json}

model: sonnet  effort: M  area: scripts

**Files:**
- Create: `scripts/sync-labels-canon.json`

Context: This is the source of truth referenced by every later task in this plan and by the dashboard plan. Schema needs to support: per-label name + color + description + group; renames (stale → canon); per-repo local extensions; ordered status column for kanban consumers.

Approach: Hand-write the JSON from spec §3, §4, §5, §6. No code generation; the file is short enough (~200 lines) to be readable and reviewable line-by-line.

- [ ] **Step 1: Sketch the JSON schema in a comment in your scratch space**

The shape must support these consumers:
- `sync-labels.sh` needs: `labels[]` (name, color, description, repos_required), `renames[]` (old, new), `repos[]`, `local_extensions{repo: [names]}`.
- Cost dashboard needs: `status_order[]` (kanban column ordering), `chip_colors{label: {fg, bg, border}}`.

- [ ] **Step 2: Write `scripts/sync-labels-canon.json`**

```json
{
  "version": "1.0",
  "generated_from": "docs/superpowers/specs/2026-05-17-gh-label-taxonomy-design.md",
  "repos": [
    "pdomain-book-tools", "pdomain-ocr-cli", "pd-ocr-labeler", "pdomain-ocr-labeler-spa",
    "pdomain-ocr-synth", "pd-ocr-trainer", "pd-png-optimizer", "pdomain-prep-for-pgdp",
    "ocr-container-meta"
  ],
  "renames": [
    {"old": "status:in-review", "new": "status:in-pr", "repos": ["pd-png-optimizer"]}
  ],
  "local_extensions": {
    "pdomain-ocr-labeler-spa": ["hifi:P1", "hifi:P2", "hifi:P3", "hifi:P4", "hifi:P5"],
    "pd-png-optimizer": ["backend:claude", "backend:codex", "backend:grok"]
  },
  "status_order": [
    "status:backlog", "status:ready", "status:in-progress",
    "status:in-pr", "status:done", "status:archived",
    "status:blocked", "status:bounced"
  ],
  "labels": [
    {"name": "kind:feature-request", "color": "5d9fdf", "description": "Untriaged request; entry point", "group": "kind"},
    {"name": "kind:spec",            "color": "a888d4", "description": "Design issue with a spec doc",   "group": "kind"},
    {"name": "kind:decision",        "color": "d6925a", "description": "Architectural decision record",  "group": "kind"},
    {"name": "kind:feature",         "color": "5fbf6a", "description": "Buildable feature task",         "group": "kind"},
    {"name": "kind:bug",             "color": "dc6555", "description": "Defect",                          "group": "kind"},
    {"name": "kind:chore",           "color": "7a7a85", "description": "Maintenance / infra task",       "group": "kind"},
    {"name": "kind:tracking",        "color": "e8a83a", "description": "Parent issue collecting children","group": "kind"},

    {"name": "status:backlog",       "color": "ededed", "description": "Accepted, not started",          "group": "status"},
    {"name": "status:ready",         "color": "c5e1c5", "description": "Claimed/queued",                 "group": "status"},
    {"name": "status:in-progress",   "color": "fbeac1", "description": "Actively being worked",          "group": "status"},
    {"name": "status:in-pr",         "color": "c5def5", "description": "PR open, awaiting merge",        "group": "status"},
    {"name": "status:done",          "color": "9be79b", "description": "Merged, closed satisfactorily",  "group": "status"},
    {"name": "status:archived",      "color": "d4d4d4", "description": "Closed without delivery",        "group": "status"},
    {"name": "status:blocked",       "color": "f5c5c5", "description": "Waiting on external dependency", "group": "status"},
    {"name": "status:bounced",       "color": "e99695", "description": "ship-issue failed; needs triage","group": "status"},

    {"name": "triage:approved",        "color": "0e8a16", "description": "Moved forward",                "group": "triage"},
    {"name": "triage:needs-spec",      "color": "1d76db", "description": "Needs design (kind:spec)",     "group": "triage"},
    {"name": "triage:needs-tracking",  "color": "0052cc", "description": "Needs tracking parent",        "group": "triage"},
    {"name": "triage:tracking",        "color": "5319e7", "description": "Is a tracking parent",         "group": "triage"},
    {"name": "triage:rejected",        "color": "b60205", "description": "Closed by triage",             "group": "triage"},
    {"name": "triage:proposed-by-agent","color": "fbca04","description": "Auto-proposed; needs confirm", "group": "triage"},

    {"name": "effort:S",  "color": "c2e0c6", "description": "Under a session",     "group": "effort"},
    {"name": "effort:M",  "color": "fbca04", "description": "One full session",    "group": "effort"},
    {"name": "effort:L",  "color": "d93f0b", "description": "Multiple sessions",   "group": "effort"},
    {"name": "effort:XL", "color": "5319e7", "description": "Spec-sized",          "group": "effort"},

    {"name": "model:haiku",  "color": "c5def5", "description": "Right model: Haiku",  "group": "model"},
    {"name": "model:sonnet", "color": "0052cc", "description": "Right model: Sonnet", "group": "model"},
    {"name": "model:opus",   "color": "5319e7", "description": "Right model: Opus",   "group": "model"},

    {"name": "model-effort:low",    "color": "c5def5", "description": "Compute budget: low",    "group": "model-effort"},
    {"name": "model-effort:medium", "color": "1d76db", "description": "Compute budget: medium", "group": "model-effort"},
    {"name": "model-effort:high",   "color": "0052cc", "description": "Compute budget: high",   "group": "model-effort"},
    {"name": "model-effort:xhigh",  "color": "3713c4", "description": "Compute budget: xhigh",  "group": "model-effort"},
    {"name": "model-effort:max",    "color": "5319e7", "description": "Compute budget: max",    "group": "model-effort"},

    {"name": "priority:low",    "color": "ededed", "description": "Low priority",    "group": "priority"},
    {"name": "priority:medium", "color": "fbca04", "description": "Medium priority", "group": "priority"},
    {"name": "priority:high",   "color": "d93f0b", "description": "High priority",   "group": "priority"},

    {"name": "area:ci",       "color": "7a7a85", "description": "CI / build infrastructure", "group": "area"},
    {"name": "area:deps",     "color": "7a7a85", "description": "Dependencies",              "group": "area"},
    {"name": "area:docs",     "color": "7a7a85", "description": "Documentation",             "group": "area"},
    {"name": "area:refactor", "color": "7a7a85", "description": "Refactoring",               "group": "area"},
    {"name": "area:tests",    "color": "7a7a85", "description": "Test infrastructure",       "group": "area"},

    {"name": "recurring:weekly",    "color": "c5def5", "description": "Recurring weekly",    "group": "recurring"},
    {"name": "recurring:monthly",   "color": "c5def5", "description": "Recurring monthly",   "group": "recurring"},
    {"name": "recurring:quarterly", "color": "c5def5", "description": "Recurring quarterly", "group": "recurring"}
  ],
  "chip_colors": {
    "kind:feature":     {"fg": "5fbf6a", "border": "5fbf6a55", "bg": "5fbf6a1a"},
    "kind:bug":         {"fg": "dc6555", "border": "dc655555", "bg": "dc65551a"},
    "kind:chore":       {"fg": "7a7a85", "border": "7a7a8555", "bg": "7a7a851a"},
    "kind:spec":        {"fg": "a888d4", "border": "a888d455", "bg": "a888d41a"},
    "kind:decision":    {"fg": "d6925a", "border": "d6925a55", "bg": "d6925a1a"},
    "kind:tracking":    {"fg": "e8a83a", "border": "e8a83a55", "bg": "e8a83a1a"},
    "kind:feature-request": {"fg": "5d9fdf", "border": "5d9fdf55", "bg": "5d9fdf1a"},
    "effort:S":         {"fg": "5fbf6a", "border": "5fbf6a55", "bg": "5fbf6a1a"},
    "effort:M":         {"fg": "e8a83a", "border": "e8a83a55", "bg": "e8a83a1a"},
    "effort:L":         {"fg": "dc6555", "border": "dc655555", "bg": "dc65551a"},
    "effort:XL":        {"fg": "a888d4", "border": "a888d455", "bg": "a888d41a"},
    "model:haiku":      {"fg": "a888d4", "border": "a888d455", "bg": "a888d41a"},
    "model:sonnet":     {"fg": "5d9fdf", "border": "5d9fdf55", "bg": "5d9fdf1a"},
    "model:opus":       {"fg": "d6925a", "border": "d6925a55", "bg": "d6925a1a"}
  }
}
```

- [ ] **Step 3: Validate JSON is well-formed**

Run: `jq empty scripts/sync-labels-canon.json`
Expected: silent success (exit 0). Any syntax error → fix and re-run.

- [ ] **Step 4: Spot-check canonical label count matches spec §3 + §4**

Run: `jq '.labels | length' scripts/sync-labels-canon.json`
Expected: `40` (7 kind + 8 status + 6 triage + 4 effort + 3 model + 5 model-effort + 3 priority + 5 area + 3 recurring) — adjust if you count differently and the JSON is right.

- [ ] **Step 5: Commit**

```bash
git add scripts/sync-labels-canon.json
git commit -m "feat(labels): add canonical workspace label JSON catalog

Source of truth for sync-labels.sh and the cost dashboard. Mirrors
docs/superpowers/specs/2026-05-17-gh-label-taxonomy-design.md §3-§6."
```

---

## Task 2 — Write human-readable `docs/label-taxonomy.md` {#taxonomy-doc}

model: sonnet  effort: S  area: docs

**Files:**
- Create: `docs/label-taxonomy.md`

Context: This is the short reference doc that humans read; the long-form rationale is in the spec. It mirrors the spec's tables but is kept lean so it can live at workspace-root level and be linked from CLAUDE.md.

Approach: Pull §3, §4, §5 tables verbatim from the spec, add a one-paragraph intro pointing back at the spec for rationale, add a "See also" footer linking to `scripts/sync-labels-canon.json` and the spec.

- [ ] **Step 1: Create `docs/label-taxonomy.md`**

Use the exact tables from `docs/superpowers/specs/2026-05-17-gh-label-taxonomy-design.md` §3 (canonical axes) and §4 (cross-cutting axes) and §5 (repo-local extensions). Open with:

```markdown
# Workspace GH label taxonomy

The canonical label vocabulary used across all `ConcaveTrillion/*` repos. Machine-readable form: [`scripts/sync-labels-canon.json`](../scripts/sync-labels-canon.json). Full rationale: [the design spec](superpowers/specs/2026-05-17-gh-label-taxonomy-design.md).
```

- [ ] **Step 2: Verify references resolve**

Run: `grep -E '\(\.\.?/' docs/label-taxonomy.md | while read line; do echo "$line"; done`
Eyeball: every relative link points to a file that exists.

- [ ] **Step 3: Commit**

```bash
git add docs/label-taxonomy.md
git commit -m "docs(labels): add human-readable taxonomy reference

Short reference doc; pairs with scripts/sync-labels-canon.json (machine
form) and docs/superpowers/specs/2026-05-17-gh-label-taxonomy-design.md
(rationale)."
```

---

## Task 3 — Bats smoke test scaffolding {#bats-scaffold}

model: sonnet  effort: S  area: tests

**Files:**
- Create: `scripts/tests/test_sync_labels.bats`

Context: We want a thin test layer that catches obvious script regressions without standing up a fake GH server. The plan is: test the *parsing and diffing* logic with `--dry-run` against a stubbed gh response.

Approach: Use `bats-core` (already standard in many ops repos; install via `apt-get` or `mise` if not present). Use bash function override to stub `gh` for tests.

- [ ] **Step 1: Confirm bats is available**

Run: `command -v bats || echo MISSING`
Expected: prints `/usr/bin/bats` or similar. If `MISSING`, install with `sudo apt-get install -y bats` (debian/ubuntu) and retry.

- [ ] **Step 2: Create `scripts/tests/test_sync_labels.bats`**

```bash
#!/usr/bin/env bats

setup() {
    BATS_TEST_DIRNAME="${BATS_TEST_DIRNAME:-$(dirname "$BATS_TEST_FILENAME")}"
    SCRIPT_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    CANON="$SCRIPT_DIR/sync-labels-canon.json"
}

@test "canon json validates" {
    run jq empty "$CANON"
    [ "$status" -eq 0 ]
}

@test "every repo listed in canon.repos has a corresponding labels entry shape" {
    run bash -c "jq -r '.repos[]' \"$CANON\" | wc -l"
    [ "$status" -eq 0 ]
    [ "$output" -gt 0 ]
}

@test "script exists and is executable" {
    [ -x "$SCRIPT_DIR/sync-labels.sh" ]
}

@test "script --help prints usage" {
    run "$SCRIPT_DIR/sync-labels.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ "sync-labels" ]]
}

@test "script --dry-run with --repo nonexistent fails cleanly" {
    run "$SCRIPT_DIR/sync-labels.sh" --dry-run --repo not-a-real-repo-xyz
    [ "$status" -ne 0 ]
}
```

- [ ] **Step 3: Run the test suite (it should fail until Task 4 lands the script)**

Run: `bats scripts/tests/test_sync_labels.bats`
Expected: 5 tests, 3 pass (canon validation, repos count) but `script exists` and `--help` fail because the script isn't written yet.

- [ ] **Step 4: Commit**

```bash
git add scripts/tests/test_sync_labels.bats
git commit -m "test(labels): scaffold bats smoke tests for sync-labels

Tests for canon JSON validity and script presence. Script-execution
tests fail until sync-labels.sh lands in the next task."
```

---

## Task 4 — Implement `sync-labels.sh` {#sync-script}

model: sonnet  effort: L  area: scripts

**Files:**
- Create: `scripts/sync-labels.sh`

Context: The actual reconciliation tool. Reads canon JSON, lists labels per repo via `gh`, diffs, applies changes. Must be idempotent and safe by default.

Approach: One bash file. Use `jq` for JSON parsing. Use `gh label list --json name,color,description` for current state. Apply changes via `gh label create | edit | delete`. Renames run before creates so that a renamed label doesn't get a duplicate.

- [ ] **Step 1: Create `scripts/sync-labels.sh` with arg parsing and help**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANON="$SCRIPT_DIR/sync-labels-canon.json"

ORG="ConcaveTrillion"
DRY_RUN=0
DELETE_ORPHANS=0
ASSUME_YES=0
TARGET_REPO=""

usage() {
    cat <<EOF
sync-labels — reconcile GH label catalog against the canonical taxonomy.

Usage: sync-labels.sh [OPTIONS]

Options:
  --dry-run            Show planned changes without applying.
  --repo <name>        Operate on one repo only (basename, no org prefix).
  --delete-orphans     Delete labels not in canon and not in local-extensions.
                       Requires --yes or interactive confirmation per repo.
  --yes                Auto-confirm destructive operations.
  --help               Show this message.

Canon: $CANON
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1 ;;
        --repo) shift; TARGET_REPO="$1" ;;
        --delete-orphans) DELETE_ORPHANS=1 ;;
        --yes) ASSUME_YES=1 ;;
        --help|-h) usage; exit 0 ;;
        *) echo "Unknown arg: $1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done

# Token: prefer GH_TOKEN env, fallback to mounted secret.
if [[ -z "${GH_TOKEN:-}" ]] && [[ -r /run/secrets/gh-token-pd ]]; then
    export GH_TOKEN="$(cat /run/secrets/gh-token-pd)"
fi
if ! gh auth status >/dev/null 2>&1; then
    echo "gh CLI not authenticated. Set GH_TOKEN or run 'gh auth login'." >&2
    DRY_RUN=1
fi
```

- [ ] **Step 2: Add the per-repo sync function**

Append to the script:

```bash
sync_repo() {
    local repo="$1"
    local full="$ORG/$repo"
    local created=0 updated=0 renamed=0 deleted=0 skipped=0

    # Fetch current labels.
    local current
    if ! current=$(gh label list --repo "$full" --json name,color,description --limit 200 2>/dev/null); then
        echo "  ✗ Could not list labels on $full" >&2
        return 1
    fi

    # Process renames first.
    while IFS=$'\t' read -r old new; do
        if echo "$current" | jq -e --arg n "$old" '.[] | select(.name == $n)' >/dev/null; then
            if [[ "$DRY_RUN" -eq 1 ]]; then
                echo "  ⤳ rename '$old' → '$new'"
            else
                gh label edit "$old" --repo "$full" --name "$new" >/dev/null
                echo "  ⤳ renamed '$old' → '$new'"
            fi
            renamed=$((renamed+1))
        fi
    done < <(jq -r --arg r "$repo" '.renames[] | select(.repos | index($r)) | "\(.old)\t\(.new)"' "$CANON")

    # Refresh current after renames.
    if [[ "$DRY_RUN" -eq 0 ]] && [[ "$renamed" -gt 0 ]]; then
        current=$(gh label list --repo "$full" --json name,color,description --limit 200)
    fi

    # Process creates + updates.
    while IFS=$'\t' read -r name color description; do
        local existing
        existing=$(echo "$current" | jq -r --arg n "$name" '.[] | select(.name == $n)')
        if [[ -z "$existing" ]]; then
            if [[ "$DRY_RUN" -eq 1 ]]; then
                echo "  + create '$name' (#$color)"
            else
                gh label create "$name" --repo "$full" --color "$color" --description "$description" >/dev/null
                echo "  + created '$name'"
            fi
            created=$((created+1))
        else
            local cur_color cur_desc
            cur_color=$(echo "$existing" | jq -r .color)
            cur_desc=$(echo "$existing" | jq -r .description)
            if [[ "$cur_color" != "$color" ]] || [[ "$cur_desc" != "$description" ]]; then
                if [[ "$DRY_RUN" -eq 1 ]]; then
                    echo "  ~ update '$name' (color/desc drift)"
                else
                    gh label edit "$name" --repo "$full" --color "$color" --description "$description" >/dev/null
                    echo "  ~ updated '$name'"
                fi
                updated=$((updated+1))
            fi
        fi
    done < <(jq -r '.labels[] | "\(.name)\t\(.color)\t\(.description)"' "$CANON")

    # Optional: delete orphans.
    if [[ "$DELETE_ORPHANS" -eq 1 ]]; then
        local canon_names locals
        canon_names=$(jq -r '.labels[].name' "$CANON")
        locals=$(jq -r --arg r "$repo" '.local_extensions[$r] // [] | .[]' "$CANON")
        while IFS= read -r name; do
            if ! echo "$canon_names" | grep -qx "$name" && ! echo "$locals" | grep -qx "$name"; then
                if [[ "$ASSUME_YES" -eq 0 ]]; then
                    read -r -p "  Delete orphan '$name' on $repo? [y/N] " ans
                    [[ "$ans" =~ ^[Yy]$ ]] || { skipped=$((skipped+1)); continue; }
                fi
                if [[ "$DRY_RUN" -eq 1 ]]; then
                    echo "  - delete '$name' (orphan)"
                else
                    gh label delete "$name" --repo "$full" --yes >/dev/null
                    echo "  - deleted '$name'"
                fi
                deleted=$((deleted+1))
            fi
        done < <(echo "$current" | jq -r '.[].name')
    fi

    echo "  Summary $repo: created $created · updated $updated · renamed $renamed · deleted $deleted · skipped $skipped"
}
```

- [ ] **Step 3: Add the driver loop**

Append:

```bash
REPOS=()
if [[ -n "$TARGET_REPO" ]]; then
    REPOS=("$TARGET_REPO")
else
    mapfile -t REPOS < <(jq -r '.repos[]' "$CANON")
fi

[[ "$DRY_RUN" -eq 1 ]] && echo "[DRY RUN — no changes will be made]"

for repo in "${REPOS[@]}"; do
    echo
    echo "=== $ORG/$repo ==="
    sync_repo "$repo" || echo "  (continuing despite errors on $repo)"
done

echo
echo "Done."
```

- [ ] **Step 4: Make executable and verify syntax**

Run: `chmod +x scripts/sync-labels.sh && bash -n scripts/sync-labels.sh`
Expected: silent (no syntax errors). Any error → fix and re-run.

- [ ] **Step 5: Test --help works**

Run: `scripts/sync-labels.sh --help`
Expected: prints the usage block, exits 0.

- [ ] **Step 6: Run the bats smoke tests again**

Run: `bats scripts/tests/test_sync_labels.bats`
Expected: all 5 tests pass.

- [ ] **Step 7: Commit**

```bash
git add scripts/sync-labels.sh
git commit -m "feat(labels): add sync-labels.sh idempotent reconciler

Diffs each repo's label catalog against scripts/sync-labels-canon.json.
Supports --dry-run, --repo <name>, --delete-orphans (with --yes for
non-interactive). Renames run before creates so renamed labels are not
duplicated. Token pulled from GH_TOKEN env or /run/secrets/gh-token-pd."
```

---

## Task 5 — Dry-run sync across all 9 repos {#dry-run}

model: sonnet  effort: S  area: scripts

**Files:** (no file changes — verification step)

Context: Before applying anything, see the planned changes for every repo and confirm they match the drift table in spec §6.

- [ ] **Step 1: Run dry-run for the full workspace**

Run: `scripts/sync-labels.sh --dry-run 2>&1 | tee /tmp/sync-labels-dryrun.log`
Expected: per-repo output showing planned creates/renames/updates. Read through and confirm:
- `pd-png-optimizer` shows `⤳ rename 'status:in-review' → 'status:in-pr'` plus several creates.
- Every other repo shows creates for `status:in-pr`, `kind:decision`, `kind:tracking`.
- `pdomain-ocr-labeler-spa` does NOT plan to delete `hifi:P*` labels.
- `pd-png-optimizer` does NOT plan to delete `backend:*` labels.

- [ ] **Step 2: Investigate any surprises**

If the dry-run plans changes that don't match spec §6, the canon JSON is wrong. Fix the JSON and re-run Step 1.

- [ ] **Step 3: No commit needed for this verification task**

---

## Task 6 — Apply sync (non-destructive pass) {#apply-creates}

model: sonnet  effort: S  area: scripts

**Files:** (no file changes — applies live GH state)

Context: Run the actual sync. Skip `--delete-orphans` on this pass; just create + rename + update.

- [ ] **Step 1: Verify gh auth**

Run: `gh auth status`
Expected: "Logged in as ..." for github.com. If not authenticated, set `GH_TOKEN` or run `gh auth login` first.

- [ ] **Step 2: Apply across all repos**

Run: `scripts/sync-labels.sh 2>&1 | tee /tmp/sync-labels-apply.log`
Expected: per-repo summaries with `created N · updated M · renamed K · deleted 0 · skipped 0`. Errors on any repo log as `✗ ...` and the script continues.

- [ ] **Step 3: Re-run to confirm idempotency**

Run: `scripts/sync-labels.sh 2>&1 | tail -20`
Expected: every repo shows `created 0 · updated 0 · renamed 0 · deleted 0 · skipped 0`. If any repo still has changes, the previous pass failed for that repo — re-run with `--repo <name>` and investigate.

- [ ] **Step 4: Verify in GH UI**

Spot check 2 repos:
- `gh label list --repo ConcaveTrillion/pd-png-optimizer | grep -E 'status:(in-pr|in-review|done|ready)'`
  Expected: `status:in-pr`, `status:done`, `status:ready` present; `status:in-review` absent.
- `gh label list --repo pdomain/pdomain-book-tools | grep -E 'kind:(decision|tracking)'`
  Expected: both labels present.

- [ ] **Step 5: No commit (live-state change only)**

---

## Task 7 — Delete orphans pass (gated) {#delete-orphans}

model: sonnet  effort: S  area: scripts

**Files:** (no file changes — applies live GH state)

Context: Now clean up labels not in canon. The only known orphan from spec §6 is `test-label-123` in `pdomain-book-tools`. Run with confirmation to be safe.

- [ ] **Step 1: Dry-run with --delete-orphans first**

Run: `scripts/sync-labels.sh --dry-run --delete-orphans 2>&1 | grep delete`
Expected: a small list. The only expected orphan is `pdomain-book-tools/test-label-123`. If anything else appears, STOP and investigate — it might be an in-flight label that just hasn't been added to canon yet.

- [ ] **Step 2: Apply orphan deletion interactively**

Run: `scripts/sync-labels.sh --delete-orphans`
Expected: prompts for each orphan; answer `y` only for those confirmed in Step 1.

- [ ] **Step 3: Confirm idempotency**

Run: `scripts/sync-labels.sh --dry-run --delete-orphans 2>&1 | grep -c delete`
Expected: `0`.

- [ ] **Step 4: No commit needed**

---

## Self-review checklist

- [ ] Canon JSON validates as JSON
- [ ] Every label in spec §3 + §4 appears in `labels[]`
- [ ] Every rename in spec §6 appears in `renames[]`
- [ ] `hifi:P*` and `backend:*` listed in `local_extensions`
- [ ] sync-labels.sh `--dry-run` matches spec §6 drift table
- [ ] sync-labels.sh re-run after apply shows zero changes (idempotent)
- [ ] `test-label-123` deleted from pdomain-book-tools
- [ ] `status:in-review` no longer exists in any repo
- [ ] `docs/label-taxonomy.md` references resolve

When all checked, this plan is done.
