# docs/ folder template — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Roll out the workspace-standard `docs/` folder layout (9 active + archive twin) to all 13 repos in `/workspaces/ocr-container/` via two idempotent bash scripts, a canonical `docs/README.md` template, and a per-repo `CLAUDE.md` block.

**Architecture:** Two scripts under `scripts/` — `scaffold-docs.sh` for the fresh structure, `migrate-docs.sh` for moving existing content — share a `lib.sh` of test helpers and a single template file. Both scripts are TDD'd with plain-bash test runners that use tmpdir-isolated, `git init`-ed fixtures. Rollout is sequential: empty-docs pilot (`pdomain-ocr-cli`) → small-migration pilot (`pdomain-book-tools`) → workspace root (biggest content, most ambiguous) → parallel fan-out to the remaining 10 repos.

**Tech Stack:** Bash 5+, `git`, POSIX coreutils (`mktemp`, `mkdir`, `diff`, `find`). No external test framework — tests are plain shell scripts with assertion helpers; run via `bash scripts/tests/test-*.sh`.

**Spec:** `/workspaces/ocr-container/docs/specs/2026-05-19-docs-folder-template-design.md`

---

## File Structure

Files created:
- `scripts/scaffold-docs.sh` — idempotent structure creator (create / `--check` / `--force` modes)
- `scripts/migrate-docs.sh` — two-pass migrator (Pass 1 scripted, Pass 2 dry-run / `--apply`)
- `scripts/templates/docs-readme.md` — canonical README written verbatim by scaffold
- `scripts/tests/lib.sh` — shared assertion + fixture helpers
- `scripts/tests/test-scaffold-docs.sh` — TDD tests for scaffold
- `scripts/tests/test-migrate-docs.sh` — TDD tests for migrate

Files modified per repo during rollout:
- `<repo>/CLAUDE.md` — append spec §4 superpowers-redirect block

Folders deleted post-migration (where present):
- `<repo>/docs/superpowers/`, plus per-repo legacy folders flagged by Pass 2

---

## Milestone A — `scripts/scaffold-docs.sh`

### Task A1: Test harness + first failing test (active folders)

**Files:**
- Create: `scripts/tests/lib.sh`
- Create: `scripts/tests/test-scaffold-docs.sh`
- Create: `scripts/scaffold-docs.sh`

- [ ] **Step 1: Write shared test helpers**

Create `scripts/tests/lib.sh`:

```bash
#!/usr/bin/env bash
# Shared test helpers for scripts/tests/*.sh. Source from a test script:
#   source "$(dirname "$0")/lib.sh"
set -euo pipefail

FAIL_COUNT=0
PASS_COUNT=0
CURRENT_TEST=""

setup_test_repo() {
  local repo
  repo="$(mktemp -d -t pd-docs-test.XXXXXX)"
  ( cd "$repo" && git init -q && git config user.email t@t && git config user.name t )
  echo "$repo"
}

cleanup_test_repo() {
  local repo="$1"
  [[ -n "$repo" && -d "$repo" && "$repo" =~ /pd-docs-test\. ]] && rm -rf "$repo"
}

assert_dir() {
  local d="$1"; local msg="${2:-dir exists: $d}"
  if [[ -d "$d" ]]; then PASS_COUNT=$((PASS_COUNT+1))
  else echo "  FAIL [$CURRENT_TEST]: $msg" >&2; FAIL_COUNT=$((FAIL_COUNT+1)); fi
}

assert_file() {
  local f="$1"; local msg="${2:-file exists: $f}"
  if [[ -f "$f" ]]; then PASS_COUNT=$((PASS_COUNT+1))
  else echo "  FAIL [$CURRENT_TEST]: $msg" >&2; FAIL_COUNT=$((FAIL_COUNT+1)); fi
}

assert_no_file() {
  local f="$1"; local msg="${2:-file should not exist: $f}"
  if [[ ! -e "$f" ]]; then PASS_COUNT=$((PASS_COUNT+1))
  else echo "  FAIL [$CURRENT_TEST]: $msg" >&2; FAIL_COUNT=$((FAIL_COUNT+1)); fi
}

assert_exit() {
  local expected="$1"; local actual="$2"; local msg="${3:-exit code $expected}"
  if [[ "$expected" == "$actual" ]]; then PASS_COUNT=$((PASS_COUNT+1))
  else echo "  FAIL [$CURRENT_TEST]: $msg (got $actual)" >&2; FAIL_COUNT=$((FAIL_COUNT+1)); fi
}

assert_files_equal() {
  local a="$1"; local b="$2"; local msg="${3:-files equal: $a vs $b}"
  if diff -q "$a" "$b" > /dev/null 2>&1; then PASS_COUNT=$((PASS_COUNT+1))
  else echo "  FAIL [$CURRENT_TEST]: $msg" >&2; FAIL_COUNT=$((FAIL_COUNT+1)); fi
}

run_test() {
  CURRENT_TEST="$1"; shift
  echo "RUN: $CURRENT_TEST"
  "$@"
}

summarize_and_exit() {
  echo
  echo "Tests: $((PASS_COUNT+FAIL_COUNT)). Passed: $PASS_COUNT. Failed: $FAIL_COUNT."
  [[ "$FAIL_COUNT" -gt 0 ]] && exit 1
  exit 0
}
```

- [ ] **Step 2: Write the first failing test**

Create `scripts/tests/test-scaffold-docs.sh`:

```bash
#!/usr/bin/env bash
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/lib.sh"

SCAFFOLD="$HERE/../scaffold-docs.sh"
ACTIVE_FOLDERS=(architecture decisions plans process research runbooks specs templates usage)

test_creates_active_folders() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null
  for f in "${ACTIVE_FOLDERS[@]}"; do
    assert_dir "$repo/docs/$f"
  done
  cleanup_test_repo "$repo"
}

run_test test_creates_active_folders
summarize_and_exit
```

- [ ] **Step 3: Run test, observe failure**

```bash
chmod +x scripts/tests/test-scaffold-docs.sh
bash scripts/tests/test-scaffold-docs.sh
```

Expected: error — `scaffold-docs.sh: No such file or directory`.

- [ ] **Step 4: Write minimal scaffold-docs.sh**

Create `scripts/scaffold-docs.sh`:

```bash
#!/usr/bin/env bash
# scaffold-docs.sh — create the workspace-standard docs/ folder structure.
# See: docs/specs/2026-05-19-docs-folder-template-design.md
set -euo pipefail

REPO="${1:?usage: scaffold-docs.sh <repo-path> [--check|--force]}"
ACTIVE="architecture decisions plans process research runbooks specs templates usage"

mkdir -p "$REPO/docs"
for f in $ACTIVE; do mkdir -p "$REPO/docs/$f"; done
```

```bash
chmod +x scripts/scaffold-docs.sh
```

- [ ] **Step 5: Run test, observe pass**

```bash
bash scripts/tests/test-scaffold-docs.sh
```

Expected: `Tests: 9. Passed: 9. Failed: 0.`

- [ ] **Step 6: Commit**

```bash
git add scripts/tests/lib.sh scripts/tests/test-scaffold-docs.sh scripts/scaffold-docs.sh
git commit -m "feat(scaffold-docs): create nine active folders"
```

---

### Task A2: Archive twin folders

**Files:**
- Modify: `scripts/tests/test-scaffold-docs.sh`
- Modify: `scripts/scaffold-docs.sh`

- [ ] **Step 1: Add failing test for archive folders**

In `scripts/tests/test-scaffold-docs.sh`, add this function above `run_test test_creates_active_folders`:

```bash
test_creates_archive_folders() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null
  for f in "${ACTIVE_FOLDERS[@]}"; do
    assert_dir "$repo/docs/archive/$f"
  done
  cleanup_test_repo "$repo"
}
```

Add this line above `summarize_and_exit`:

```bash
run_test test_creates_archive_folders
```

- [ ] **Step 2: Run, observe failure**

```bash
bash scripts/tests/test-scaffold-docs.sh
```

Expected: 9 failures on `docs/archive/<name>`.

- [ ] **Step 3: Implement archive mkdir**

In `scripts/scaffold-docs.sh`, add after the existing `for f in $ACTIVE` loop:

```bash
for f in $ACTIVE; do mkdir -p "$REPO/docs/archive/$f"; done
```

- [ ] **Step 4: Run, observe pass**

```bash
bash scripts/tests/test-scaffold-docs.sh
```

Expected: `Failed: 0.` (cumulative passed: 18.)

- [ ] **Step 5: Commit**

```bash
git add scripts/tests/test-scaffold-docs.sh scripts/scaffold-docs.sh
git commit -m "feat(scaffold-docs): create archive twin folders"
```

---

### Task A3: `.gitkeep` markers in empty folders

**Files:**
- Modify: `scripts/tests/test-scaffold-docs.sh`
- Modify: `scripts/scaffold-docs.sh`

- [ ] **Step 1: Add failing test for `.gitkeep`**

In `scripts/tests/test-scaffold-docs.sh`, add this function above the existing `run_test` calls:

```bash
test_creates_gitkeep_in_empty_folders() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null
  for f in "${ACTIVE_FOLDERS[@]}"; do
    assert_file "$repo/docs/$f/.gitkeep"
    assert_file "$repo/docs/archive/$f/.gitkeep"
  done
  cleanup_test_repo "$repo"
}

test_no_gitkeep_in_populated_folder() {
  local repo; repo="$(setup_test_repo)"
  mkdir -p "$repo/docs/specs"
  echo "real content" > "$repo/docs/specs/foo.md"
  bash "$SCAFFOLD" "$repo" > /dev/null
  assert_no_file "$repo/docs/specs/.gitkeep" "populated folder should not get .gitkeep"
  cleanup_test_repo "$repo"
}

test_removes_stale_gitkeep_when_folder_populated() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null
  # Add real content next to the .gitkeep scaffold created.
  echo "real content" > "$repo/docs/specs/foo.md"
  bash "$SCAFFOLD" "$repo" > /dev/null
  assert_no_file "$repo/docs/specs/.gitkeep" "stale .gitkeep should be removed when folder has content"
  cleanup_test_repo "$repo"
}
```

Add above `summarize_and_exit`:

```bash
run_test test_creates_gitkeep_in_empty_folders
run_test test_no_gitkeep_in_populated_folder
run_test test_removes_stale_gitkeep_when_folder_populated
```

- [ ] **Step 2: Run, observe failure**

```bash
bash scripts/tests/test-scaffold-docs.sh
```

Expected: 18 `.gitkeep` failures in `test_creates_gitkeep_in_empty_folders`, plus failure in `test_removes_stale_gitkeep_when_folder_populated`. `test_no_gitkeep_in_populated_folder` passes coincidentally (no `.gitkeep` logic yet).

- [ ] **Step 3: Implement `.gitkeep` logic (add + remove-when-stale)**

In `scripts/scaffold-docs.sh`, add after both mkdir loops:

```bash
ensure_gitkeep() {
  local dir="$1"
  [[ ! -d "$dir" ]] && return
  local has_keep=0
  local has_other=0
  while IFS= read -r e; do
    [[ -z "$e" ]] && continue
    if [[ "$e" == ".gitkeep" ]]; then has_keep=1; else has_other=1; fi
  done <<< "$(ls -A "$dir" 2>/dev/null)"
  if [[ "$has_other" == "0" && "$has_keep" == "0" ]]; then
    touch "$dir/.gitkeep"               # empty folder — add marker
  elif [[ "$has_other" == "1" && "$has_keep" == "1" ]]; then
    rm "$dir/.gitkeep"                  # populated folder — drop stale marker
  fi
}

for f in $ACTIVE; do
  ensure_gitkeep "$REPO/docs/$f"
  ensure_gitkeep "$REPO/docs/archive/$f"
done
```

- [ ] **Step 4: Run, observe pass**

```bash
bash scripts/tests/test-scaffold-docs.sh
```

Expected: `Failed: 0.` (cumulative passed: 38.)

- [ ] **Step 5: Commit**

```bash
git add scripts/tests/test-scaffold-docs.sh scripts/scaffold-docs.sh
git commit -m "feat(scaffold-docs): manage .gitkeep (add when empty, remove when stale)"
```

---

### Task A4: Write `docs/README.md` from template

**Files:**
- Create: `scripts/templates/docs-readme.md`
- Modify: `scripts/tests/test-scaffold-docs.sh`
- Modify: `scripts/scaffold-docs.sh`

- [ ] **Step 1: Create the canonical README template**

Create `scripts/templates/docs-readme.md` with **exactly** this content (workspace-standard, byte-identical across all repos):

```markdown
# docs/

How documentation is organized in this repo.

| Folder | Purpose | Use when |
|---|---|---|
| `architecture/` | Durable reference — how the system works today. | Capturing current shape (modules, data flow, contracts, current-state diagrams). |
| `archive/` | Cold storage. Mirrors the nine active folders. | A doc is no longer in force (shipped, superseded, abandoned). |
| `decisions/` | ADRs — dated, append-only "we chose X because Y." | Recording a specific design choice with context, alternatives, consequences. |
| `plans/` | Active execution — what order to make a spec real. | Sequencing work for an approved spec. |
| `process/` | Cross-cutting workflow conventions (verification rules, merge strategy, release process). | Capturing how the team works, not what the system does. |
| `research/` | Investigation in progress. Messy by design. | Exploring before committing to a design. |
| `runbooks/` | Operational reference — something is broken or being operated. | An on-call or ops task needs a recipe. |
| `specs/` | Aspirational, pre-implementation design. | Describing what to build, before code. |
| `templates/` | Issue, spec, plan, ADR boilerplate. | Adding a starter template for a new doc type. |
| `usage/` | Downstream reference — how to consume this app/tool/library. | A user or integrator needs to know how to use it. |

Empty folders are intentional and tracked via `.gitkeep`.

Active docs map to GitHub issues — see this repo's issue tracker for status.
This layout is workspace-standard; see
`/workspaces/ocr-container/docs/README.md` for the master.
```

- [ ] **Step 2: Add failing test for README**

Add to `scripts/tests/test-scaffold-docs.sh`:

```bash
TEMPLATE="$HERE/../templates/docs-readme.md"

test_writes_readme_from_template() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null
  assert_file "$repo/docs/README.md"
  assert_files_equal "$repo/docs/README.md" "$TEMPLATE"
  cleanup_test_repo "$repo"
}

test_preserves_existing_readme() {
  local repo; repo="$(setup_test_repo)"
  mkdir -p "$repo/docs"
  echo "custom README content" > "$repo/docs/README.md"
  bash "$SCAFFOLD" "$repo" > /dev/null
  local actual; actual="$(cat "$repo/docs/README.md")"
  if [[ "$actual" == "custom README content" ]]; then PASS_COUNT=$((PASS_COUNT+1))
  else echo "  FAIL [$CURRENT_TEST]: existing README was overwritten" >&2; FAIL_COUNT=$((FAIL_COUNT+1)); fi
  cleanup_test_repo "$repo"
}
```

Add above `summarize_and_exit`:

```bash
run_test test_writes_readme_from_template
run_test test_preserves_existing_readme
```

- [ ] **Step 3: Run, observe failure**

Expected: README missing in first test; second test passes coincidentally (no overwrite logic yet).

- [ ] **Step 4: Implement README write**

In `scripts/scaffold-docs.sh`, replace the shebang/header block to capture script dir, and add README write after the `.gitkeep` loop:

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REPO="${1:?usage: scaffold-docs.sh <repo-path> [--check|--force]}"
ACTIVE="architecture decisions plans process research runbooks specs templates usage"
TEMPLATE="$SCRIPT_DIR/templates/docs-readme.md"
```

At the end (after the `.gitkeep` loop), add:

```bash
README="$REPO/docs/README.md"
if [[ ! -f "$README" ]]; then
  cp "$TEMPLATE" "$README"
fi
```

- [ ] **Step 5: Run, observe pass**

```bash
bash scripts/tests/test-scaffold-docs.sh
```

Expected: `Failed: 0.` (cumulative passed: 41.)

- [ ] **Step 6: Commit**

```bash
git add scripts/templates/docs-readme.md scripts/tests/test-scaffold-docs.sh scripts/scaffold-docs.sh
git commit -m "feat(scaffold-docs): write canonical docs/README.md from template"
```

---

### Task A5: `--check` mode

**Files:**
- Modify: `scripts/tests/test-scaffold-docs.sh`
- Modify: `scripts/scaffold-docs.sh`

- [ ] **Step 1: Add failing test for --check**

Add to `scripts/tests/test-scaffold-docs.sh`:

```bash
test_check_passes_on_complete_structure() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null
  local rc=0
  bash "$SCAFFOLD" "$repo" --check > /dev/null || rc=$?
  assert_exit 0 "$rc" "--check should exit 0 on complete structure"
  cleanup_test_repo "$repo"
}

test_check_fails_on_missing_folder() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null
  rm -rf "$repo/docs/specs"
  local rc=0
  bash "$SCAFFOLD" "$repo" --check > /dev/null 2>&1 || rc=$?
  assert_exit 1 "$rc" "--check should exit 1 when a folder is missing"
  cleanup_test_repo "$repo"
}
```

Add above `summarize_and_exit`:

```bash
run_test test_check_passes_on_complete_structure
run_test test_check_fails_on_missing_folder
```

- [ ] **Step 2: Run, observe failure**

Expected: `--check` is ignored today; current script exits 0 regardless and *re-creates* the missing folder. The "fails on missing folder" test will fail.

- [ ] **Step 3: Implement `--check` mode**

Rewrite `scripts/scaffold-docs.sh` to branch on mode:

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REPO="${1:?usage: scaffold-docs.sh <repo-path> [--check|--force]}"
MODE="${2:-create}"
ACTIVE="architecture decisions plans process research runbooks specs templates usage"
TEMPLATE="$SCRIPT_DIR/templates/docs-readme.md"

FAIL=0

ensure_dir() {
  local d="$1"
  if [[ ! -d "$d" ]]; then
    if [[ "$MODE" == "--check" ]]; then echo "MISSING: $d"; FAIL=1
    else mkdir -p "$d"; fi
  fi
}

ensure_gitkeep() {
  local dir="$1"
  [[ ! -d "$dir" ]] && return
  local has_keep=0 has_other=0
  while IFS= read -r e; do
    [[ -z "$e" ]] && continue
    if [[ "$e" == ".gitkeep" ]]; then has_keep=1; else has_other=1; fi
  done <<< "$(ls -A "$dir" 2>/dev/null)"
  if [[ "$has_other" == "0" && "$has_keep" == "0" ]]; then
    if [[ "$MODE" == "--check" ]]; then echo "MISSING: $dir/.gitkeep"; FAIL=1
    else touch "$dir/.gitkeep"; fi
  elif [[ "$has_other" == "1" && "$has_keep" == "1" ]]; then
    if [[ "$MODE" == "--check" ]]; then echo "STALE: $dir/.gitkeep"; FAIL=1
    else rm "$dir/.gitkeep"; fi
  fi
}

ensure_dir "$REPO/docs"
for f in $ACTIVE; do
  ensure_dir "$REPO/docs/$f"
  ensure_gitkeep "$REPO/docs/$f"
  ensure_dir "$REPO/docs/archive/$f"
  ensure_gitkeep "$REPO/docs/archive/$f"
done

README="$REPO/docs/README.md"
if [[ ! -f "$README" ]]; then
  if [[ "$MODE" == "--check" ]]; then echo "MISSING: $README"; FAIL=1
  else cp "$TEMPLATE" "$README"; fi
fi

[[ "$FAIL" == "1" ]] && exit 1
exit 0
```

- [ ] **Step 4: Run, observe pass**

```bash
bash scripts/tests/test-scaffold-docs.sh
```

Expected: `Failed: 0.` (cumulative passed: 43.)

- [ ] **Step 5: Commit**

```bash
git add scripts/tests/test-scaffold-docs.sh scripts/scaffold-docs.sh
git commit -m "feat(scaffold-docs): add --check mode for drift detection"
```

---

### Task A6: `--force` mode + idempotency

**Files:**
- Modify: `scripts/tests/test-scaffold-docs.sh`
- Modify: `scripts/scaffold-docs.sh`

- [ ] **Step 1: Add failing tests for --force and idempotency**

Add to `scripts/tests/test-scaffold-docs.sh`:

```bash
test_force_overwrites_readme() {
  local repo; repo="$(setup_test_repo)"
  mkdir -p "$repo/docs"
  echo "stale README content" > "$repo/docs/README.md"
  bash "$SCAFFOLD" "$repo" --force > /dev/null
  assert_files_equal "$repo/docs/README.md" "$TEMPLATE"
  cleanup_test_repo "$repo"
}

test_idempotent_double_run() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null
  local rc=0
  bash "$SCAFFOLD" "$repo" > /dev/null || rc=$?
  assert_exit 0 "$rc" "second run should exit 0"
  # No duplicates: each folder still has exactly one .gitkeep.
  for f in "${ACTIVE_FOLDERS[@]}"; do
    local count
    count="$(find "$repo/docs/$f" -maxdepth 1 -name '.gitkeep' | wc -l)"
    if [[ "$count" == "1" ]]; then PASS_COUNT=$((PASS_COUNT+1))
    else echo "  FAIL [$CURRENT_TEST]: $f has $count .gitkeep files" >&2; FAIL_COUNT=$((FAIL_COUNT+1)); fi
  done
  cleanup_test_repo "$repo"
}
```

Add above `summarize_and_exit`:

```bash
run_test test_force_overwrites_readme
run_test test_idempotent_double_run
```

- [ ] **Step 2: Run, observe failure**

Expected: `--force` doesn't overwrite (current script skips when file exists). Idempotency passes coincidentally.

- [ ] **Step 3: Implement `--force`**

In `scripts/scaffold-docs.sh`, replace the README block with:

```bash
README="$REPO/docs/README.md"
if [[ ! -f "$README" || "$MODE" == "--force" ]]; then
  if [[ "$MODE" == "--check" ]]; then echo "MISSING: $README"; FAIL=1
  else cp "$TEMPLATE" "$README"; fi
fi
```

- [ ] **Step 4: Run, observe pass**

```bash
bash scripts/tests/test-scaffold-docs.sh
```

Expected: `Failed: 0.` (cumulative passed: 54.)

- [ ] **Step 5: Commit**

```bash
git add scripts/tests/test-scaffold-docs.sh scripts/scaffold-docs.sh
git commit -m "feat(scaffold-docs): add --force mode + lock in idempotency"
```

---

## Milestone B — `scripts/migrate-docs.sh`

### Task B1: Test harness + Pass 1 (`docs/superpowers/plans/` → `docs/plans/`)

**Files:**
- Create: `scripts/tests/test-migrate-docs.sh`
- Create: `scripts/migrate-docs.sh`

- [ ] **Step 1: Write failing test for first Pass-1 move**

Create `scripts/tests/test-migrate-docs.sh`:

```bash
#!/usr/bin/env bash
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/lib.sh"

MIGRATE="$HERE/../migrate-docs.sh"
SCAFFOLD="$HERE/../scaffold-docs.sh"

stage_legacy_file() {
  # Args: repo subdir filename content
  local repo="$1" sub="$2" name="$3" content="$4"
  mkdir -p "$repo/docs/$sub"
  echo "$content" > "$repo/docs/$sub/$name"
  ( cd "$repo" && git add . && git commit -q -m "stage" )
}

test_pass1_moves_superpowers_plans() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null
  ( cd "$repo" && git add . && git commit -q -m "scaffold" )
  stage_legacy_file "$repo" "superpowers/plans" "P1.md" "plan one"
  bash "$MIGRATE" "$repo" --pass 1 > /dev/null
  assert_file "$repo/docs/plans/P1.md"
  assert_no_file "$repo/docs/superpowers/plans/P1.md"
  cleanup_test_repo "$repo"
}

run_test test_pass1_moves_superpowers_plans
summarize_and_exit
```

```bash
chmod +x scripts/tests/test-migrate-docs.sh
```

- [ ] **Step 2: Run, observe failure**

```bash
bash scripts/tests/test-migrate-docs.sh
```

Expected: error — `migrate-docs.sh: No such file or directory`.

- [ ] **Step 3: Write minimal migrate-docs.sh**

Create `scripts/migrate-docs.sh`:

```bash
#!/usr/bin/env bash
# migrate-docs.sh — migrate existing docs/ content into the workspace-standard layout.
# See: docs/specs/2026-05-19-docs-folder-template-design.md
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REPO="${1:?usage: migrate-docs.sh <repo-path> [--pass 1|2] [--apply <report-file>]}"
shift || true

PASS=""
APPLY=""
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --pass) PASS="$2"; shift 2 ;;
    --apply) APPLY="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Pass 1: well-known scripted moves.
pass1_move_dir() {
  local src="$REPO/docs/$1"
  local dst="$REPO/docs/$2"
  [[ -d "$src" ]] || return 0
  mkdir -p "$dst"
  ( cd "$REPO" && find "docs/$1" -maxdepth 1 -type f -name '*.md' | while read -r f; do
      local base; base="$(basename "$f")"
      git mv -k "$f" "docs/$2/$base"
    done )
}

if [[ "$PASS" == "1" ]]; then
  pass1_move_dir "superpowers/plans" "plans"
fi
```

```bash
chmod +x scripts/migrate-docs.sh
```

- [ ] **Step 4: Run, observe pass**

```bash
bash scripts/tests/test-migrate-docs.sh
```

Expected: `Tests: 2. Passed: 2. Failed: 0.`

- [ ] **Step 5: Commit**

```bash
git add scripts/tests/test-migrate-docs.sh scripts/migrate-docs.sh
git commit -m "feat(migrate-docs): pass 1 moves superpowers/plans to plans"
```

---

### Task B2: Pass 1 — remaining well-known moves

**Files:**
- Modify: `scripts/tests/test-migrate-docs.sh`
- Modify: `scripts/migrate-docs.sh`

- [ ] **Step 1: Add failing tests for the four remaining well-known moves**

In `scripts/tests/test-migrate-docs.sh`, add (above `summarize_and_exit`):

```bash
test_pass1_moves_superpowers_specs() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null
  ( cd "$repo" && git add . && git commit -q -m "scaffold" )
  stage_legacy_file "$repo" "superpowers/specs" "S1.md" "spec one"
  bash "$MIGRATE" "$repo" --pass 1 > /dev/null
  assert_file "$repo/docs/specs/S1.md"
  assert_no_file "$repo/docs/superpowers/specs/S1.md"
  cleanup_test_repo "$repo"
}

test_pass1_moves_superpowers_research() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null
  ( cd "$repo" && git add . && git commit -q -m "scaffold" )
  stage_legacy_file "$repo" "superpowers/research" "R1.md" "research one"
  bash "$MIGRATE" "$repo" --pass 1 > /dev/null
  assert_file "$repo/docs/research/R1.md"
  cleanup_test_repo "$repo"
}

test_pass1_moves_superpowers_decisions() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null
  ( cd "$repo" && git add . && git commit -q -m "scaffold" )
  stage_legacy_file "$repo" "superpowers/decisions" "D1.md" "decision one"
  bash "$MIGRATE" "$repo" --pass 1 > /dev/null
  assert_file "$repo/docs/decisions/D1.md"
  cleanup_test_repo "$repo"
}

test_pass1_moves_superpowers_reminders_to_runbooks() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null
  ( cd "$repo" && git add . && git commit -q -m "scaffold" )
  stage_legacy_file "$repo" "superpowers/reminders" "Rem1.md" "reminder one"
  bash "$MIGRATE" "$repo" --pass 1 > /dev/null
  assert_file "$repo/docs/runbooks/Rem1.md"
  cleanup_test_repo "$repo"
}
```

Add above `summarize_and_exit`:

```bash
run_test test_pass1_moves_superpowers_specs
run_test test_pass1_moves_superpowers_research
run_test test_pass1_moves_superpowers_decisions
run_test test_pass1_moves_superpowers_reminders_to_runbooks
```

- [ ] **Step 2: Run, observe failure**

Expected: 4 failures (only `plans` is migrated so far).

- [ ] **Step 3: Add the four remaining well-known moves**

In `scripts/migrate-docs.sh`, replace the `if [[ "$PASS" == "1" ]]; then ...` block with:

```bash
if [[ "$PASS" == "1" ]]; then
  pass1_move_dir "superpowers/plans"     "plans"
  pass1_move_dir "superpowers/specs"     "specs"
  pass1_move_dir "superpowers/research"  "research"
  pass1_move_dir "superpowers/decisions" "decisions"
  pass1_move_dir "superpowers/reminders" "runbooks"
fi
```

- [ ] **Step 4: Run, observe pass**

```bash
bash scripts/tests/test-migrate-docs.sh
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/tests/test-migrate-docs.sh scripts/migrate-docs.sh
git commit -m "feat(migrate-docs): pass 1 handles all five well-known moves"
```

---

### Task B3: Pass 1 — empty-legacy-dir cleanup + `.gitkeep` top-up

**Files:**
- Modify: `scripts/tests/test-migrate-docs.sh`
- Modify: `scripts/migrate-docs.sh`

- [ ] **Step 1: Add failing tests for cleanup**

In `scripts/tests/test-migrate-docs.sh`, add:

```bash
test_pass1_removes_empty_legacy_superpowers_dir() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null
  ( cd "$repo" && git add . && git commit -q -m "scaffold" )
  stage_legacy_file "$repo" "superpowers/plans" "P1.md" "p"
  bash "$MIGRATE" "$repo" --pass 1 > /dev/null
  assert_no_file "$repo/docs/superpowers/plans"
  assert_no_file "$repo/docs/superpowers"
  cleanup_test_repo "$repo"
}

test_pass1_does_not_remove_dir_with_unknown_subdir() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null
  ( cd "$repo" && git add . && git commit -q -m "scaffold" )
  stage_legacy_file "$repo" "superpowers/odd-subdir" "X.md" "x"
  bash "$MIGRATE" "$repo" --pass 1 > /dev/null
  assert_dir "$repo/docs/superpowers"  # still has odd-subdir/X.md
  cleanup_test_repo "$repo"
}

test_pass1_removes_stale_gitkeep_from_newly_populated_folder() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null  # creates docs/plans/.gitkeep
  ( cd "$repo" && git add . && git commit -q -m "scaffold" )
  stage_legacy_file "$repo" "superpowers/plans" "P1.md" "p"
  bash "$MIGRATE" "$repo" --pass 1 > /dev/null
  assert_file "$repo/docs/plans/P1.md" "migrated file present"
  assert_no_file "$repo/docs/plans/.gitkeep" "stale .gitkeep removed after migration"
  cleanup_test_repo "$repo"
}
```

Add above `summarize_and_exit`:

```bash
run_test test_pass1_removes_empty_legacy_superpowers_dir
run_test test_pass1_does_not_remove_dir_with_unknown_subdir
run_test test_pass1_removes_stale_gitkeep_from_newly_populated_folder
```

- [ ] **Step 2: Run, observe failure**

Expected: legacy `docs/superpowers/` directories stick around.

- [ ] **Step 3: Implement cleanup**

In `scripts/migrate-docs.sh`, add a helper above `pass1_move_dir`:

```bash
remove_if_empty() {
  local d="$REPO/$1"
  [[ -d "$d" ]] && find "$d" -type d -empty -delete 2>/dev/null || true
}
```

After the five `pass1_move_dir` calls (still inside the `if [[ "$PASS" == "1" ]]` block), add:

```bash
  remove_if_empty "docs/superpowers/plans"
  remove_if_empty "docs/superpowers/specs"
  remove_if_empty "docs/superpowers/research"
  remove_if_empty "docs/superpowers/decisions"
  remove_if_empty "docs/superpowers/reminders"
  remove_if_empty "docs/superpowers"
  # Top up the scaffold to drop stale .gitkeep from folders that just
  # received migrated content (and add .gitkeep to any now-empty folder).
  bash "$SCRIPT_DIR/scaffold-docs.sh" "$REPO" > /dev/null
```

- [ ] **Step 4: Run, observe pass**

```bash
bash scripts/tests/test-migrate-docs.sh
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/tests/test-migrate-docs.sh scripts/migrate-docs.sh
git commit -m "feat(migrate-docs): pass 1 cleans up empty legacy dirs"
```

---

### Task B4: Pass 2 — dry-run report

**Files:**
- Modify: `scripts/tests/test-migrate-docs.sh`
- Modify: `scripts/migrate-docs.sh`

- [ ] **Step 1: Add failing test for Pass-2 dry-run**

In `scripts/tests/test-migrate-docs.sh`, add:

```bash
test_pass2_reports_known_legacy_folders() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null
  stage_legacy_file "$repo" "planning"     "Old1.md" "planning"
  stage_legacy_file "$repo" "audit"        "Aud1.md" "audit"
  stage_legacy_file "$repo" "review-notes" "Rev1.md" "review-notes"
  stage_legacy_file "$repo" "roadmap"      "Road1.md" "roadmap"
  stage_legacy_file "$repo" "milestones"   "M1.md"   "milestones"
  stage_legacy_file "$repo" "futures"      "F1.md"   "futures"
  stage_legacy_file "$repo" "design-brief" "DB1.md"  "design-brief"

  local out; out="$(bash "$MIGRATE" "$repo" --pass 2 2>/dev/null)"

  # Each known-legacy folder must produce one row.
  local n; n="$(echo "$out" | grep -cE '^docs/(planning|audit|review-notes|roadmap|milestones|futures|design-brief)/' || true)"
  if [[ "$n" == "7" ]]; then PASS_COUNT=$((PASS_COUNT+1))
  else echo "  FAIL [$CURRENT_TEST]: expected 7 report rows, got $n" >&2; FAIL_COUNT=$((FAIL_COUNT+1)); fi

  cleanup_test_repo "$repo"
}
```

Add above `summarize_and_exit`:

```bash
run_test test_pass2_reports_known_legacy_folders
```

- [ ] **Step 2: Run, observe failure**

Expected: failure — Pass 2 not implemented.

- [ ] **Step 3: Implement Pass-2 report**

In `scripts/migrate-docs.sh`, add a function above the `if [[ "$PASS" == "1" ]]` block:

```bash
suggest_dst() {
  # Heuristic mapping for known-legacy folders. Outputs the suggested dest dir.
  case "$1" in
    planning|roadmap|milestones)        echo "docs/plans" ;;
    futures|design-brief)               echo "docs/specs" ;;
    audit)                              echo "docs/archive/architecture" ;;
    review|review-notes)                echo "docs/archive/research" ;;
    superpowers)                        echo "docs/archive/architecture" ;;
    *)                                  echo "docs/archive/architecture" ;;
  esac
}

pass2_report() {
  local known_legacy="planning audit review review-notes roadmap milestones futures design-brief"
  for legacy in $known_legacy; do
    [[ -d "$REPO/docs/$legacy" ]] || continue
    local dst; dst="$(suggest_dst "$legacy")"
    ( cd "$REPO" && find "docs/$legacy" -type f -name '*.md' | while read -r f; do
        local base; base="$(basename "$f")"
        printf '%s\t%s/%s\t%s\n' "$f" "$dst" "$base" "legacy-$legacy"
      done )
  done

  # Also report stray top-level docs/superpowers/*.md (one level deep).
  if [[ -d "$REPO/docs/superpowers" ]]; then
    ( cd "$REPO" && find "docs/superpowers" -maxdepth 1 -type f -name '*.md' | while read -r f; do
        local base; base="$(basename "$f")"
        printf '%s\t%s/%s\t%s\n' "$f" "docs/archive/architecture" "$base" "legacy-superpowers-loose"
      done )
  fi
}

if [[ "$PASS" == "2" && -z "$APPLY" ]]; then
  pass2_report
fi
```

- [ ] **Step 4: Run, observe pass**

```bash
bash scripts/tests/test-migrate-docs.sh
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/tests/test-migrate-docs.sh scripts/migrate-docs.sh
git commit -m "feat(migrate-docs): pass 2 dry-run report for ambiguous content"
```

---

### Task B5: Pass 2 — `--apply` mode

**Files:**
- Modify: `scripts/tests/test-migrate-docs.sh`
- Modify: `scripts/migrate-docs.sh`

- [ ] **Step 1: Add failing test for --apply**

In `scripts/tests/test-migrate-docs.sh`, add:

```bash
test_pass2_apply_moves_per_report() {
  local repo; repo="$(setup_test_repo)"
  bash "$SCAFFOLD" "$repo" > /dev/null
  stage_legacy_file "$repo" "planning" "Old1.md" "planning"
  local report; report="$(mktemp)"
  bash "$MIGRATE" "$repo" --pass 2 > "$report"
  bash "$MIGRATE" "$repo" --pass 2 --apply "$report" > /dev/null
  assert_file "$repo/docs/plans/Old1.md"
  assert_no_file "$repo/docs/planning/Old1.md"
  rm -f "$report"
  cleanup_test_repo "$repo"
}
```

Add above `summarize_and_exit`:

```bash
run_test test_pass2_apply_moves_per_report
```

- [ ] **Step 2: Run, observe failure**

Expected: `--apply` is currently ignored; files aren't moved.

- [ ] **Step 3: Implement --apply**

In `scripts/migrate-docs.sh`, add this function:

```bash
pass2_apply() {
  local report="$1"
  [[ -f "$report" ]] || { echo "report file not found: $report" >&2; exit 2; }
  while IFS=$'\t' read -r src dst _reason; do
    [[ -z "$src" || -z "$dst" ]] && continue
    mkdir -p "$REPO/$(dirname "$dst")"
    ( cd "$REPO" && git mv -k "$src" "$dst" )
  done < "$report"
  # Clean up any directories now empty.
  ( cd "$REPO" && find docs -type d -empty -delete 2>/dev/null || true )
  # Top up the scaffold so stale .gitkeep gets removed from newly-populated
  # destination folders (and missing .gitkeep added to any now-empty folder).
  bash "$SCRIPT_DIR/scaffold-docs.sh" "$REPO" > /dev/null
}

if [[ "$PASS" == "2" && -n "$APPLY" ]]; then
  pass2_apply "$APPLY"
fi
```

- [ ] **Step 4: Run, observe pass**

```bash
bash scripts/tests/test-migrate-docs.sh
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/tests/test-migrate-docs.sh scripts/migrate-docs.sh
git commit -m "feat(migrate-docs): pass 2 --apply executes approved moves"
```

---

## Milestone C — Pilot rollout: `pdomain-ocr-cli` (scaffold-only, no migration)

### Task C1: Run scaffold against `pdomain-ocr-cli`

**Files:**
- Affected: `pdomain-ocr-cli/docs/` (new structure)

- [ ] **Step 1: Confirm current state**

```bash
cd /workspaces/ocr-container/pdomain-ocr-cli
ls -la docs/
```

Expected: `docs/` exists, empty.

- [ ] **Step 2: Run scaffold**

```bash
bash /workspaces/ocr-container/scripts/scaffold-docs.sh /workspaces/ocr-container/pdomain-ocr-cli
```

- [ ] **Step 3: Verify with --check**

```bash
bash /workspaces/ocr-container/scripts/scaffold-docs.sh /workspaces/ocr-container/pdomain-ocr-cli --check
```

Expected: exit 0, no output.

- [ ] **Step 4: Inspect tree**

```bash
ls -la /workspaces/ocr-container/pdomain-ocr-cli/docs/
find /workspaces/ocr-container/pdomain-ocr-cli/docs -name .gitkeep | wc -l
```

Expected: 9 active + 1 archive dir at top; 18 `.gitkeep` files total; `docs/README.md` byte-identical to `scripts/templates/docs-readme.md`.

- [ ] **Step 5: Commit in pdomain-ocr-cli**

```bash
cd /workspaces/ocr-container/pdomain-ocr-cli
git add docs/
git commit -m "docs: scaffold workspace-standard docs/ layout

Empty pilot rollout. No content migration needed.
Ref: ocr-container/docs/specs/2026-05-19-docs-folder-template-design.md"
```

---

### Task C2: Append `CLAUDE.md` block to `pdomain-ocr-cli`

**Files:**
- Modify: `pdomain-ocr-cli/CLAUDE.md`

- [ ] **Step 1: Open the file and find the last `## ` section**

```bash
cd /workspaces/ocr-container/pdomain-ocr-cli
cat CLAUDE.md | tail -40
```

Identify a safe insertion point (end of file or just before any trailing footer).

- [ ] **Step 2: Append the spec §4 block verbatim**

Append to `pdomain-ocr-cli/CLAUDE.md`:

```markdown

## docs/ folder

This repo follows the workspace docs/ template — see `docs/README.md`. Active
folders: `architecture/`, `decisions/`, `plans/`, `process/`, `research/`,
`runbooks/`, `specs/`, `templates/`, `usage/`, plus parallel `archive/`
subfolders.

**Superpowers redirect.** When a superpowers skill (e.g. `brainstorming`,
`writing-plans`) instructs you to save to `docs/superpowers/specs/<file>.md`
or `docs/superpowers/plans/<file>.md`, save to `docs/specs/<file>.md` or
`docs/plans/<file>.md` instead. There is no `docs/superpowers/` subdirectory
in this repo.
```

- [ ] **Step 3: Verify CLAUDE.md still renders cleanly**

```bash
cd /workspaces/ocr-container/pdomain-ocr-cli
head -5 CLAUDE.md
tail -20 CLAUDE.md
```

- [ ] **Step 4: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-cli
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md superpowers-redirect block"
```

---

## Milestone D — Migration pilot: `pdomain-book-tools`

### Task D1: Pre-migration snapshot

**Files:**
- Affected: `pdomain-book-tools/docs/`

- [ ] **Step 1: Inventory existing content**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
ls -la docs/
find docs -type f -name '*.md' | sort
```

Expected: `docs/review/`, `docs/specs/`, `docs/README.md`. Record file list.

- [ ] **Step 2: Run scaffold first (creates new folders alongside existing)**

```bash
bash /workspaces/ocr-container/scripts/scaffold-docs.sh /workspaces/ocr-container/pdomain-book-tools
```

Note: existing `docs/specs/` is preserved (already correctly named). Existing `docs/README.md` is preserved (will be updated by hand later if needed).

- [ ] **Step 3: Run Pass 1 (no-op for this repo — no docs/superpowers/)**

```bash
bash /workspaces/ocr-container/scripts/migrate-docs.sh /workspaces/ocr-container/pdomain-book-tools --pass 1
```

Expected: silent / no-op.

- [ ] **Step 4: Run Pass 2 dry-run**

```bash
bash /workspaces/ocr-container/scripts/migrate-docs.sh /workspaces/ocr-container/pdomain-book-tools --pass 2 > /tmp/pdomain-book-tools-migrate.tsv
cat /tmp/pdomain-book-tools-migrate.tsv
```

Expected: each `docs/review/*.md` listed with suggested dest `docs/archive/research/<name>` and reason `legacy-review`.

- [ ] **Step 5: Apply Pass 2 (after visual confirmation of the report)**

```bash
bash /workspaces/ocr-container/scripts/migrate-docs.sh /workspaces/ocr-container/pdomain-book-tools --pass 2 --apply /tmp/pdomain-book-tools-migrate.tsv
```

- [ ] **Step 6: Verify final state with --check**

```bash
bash /workspaces/ocr-container/scripts/scaffold-docs.sh /workspaces/ocr-container/pdomain-book-tools --check
```

Expected: exit 0.

- [ ] **Step 7: Commit in pdomain-book-tools**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
git status
git add docs/
git commit -m "docs: migrate to workspace-standard layout

- Scaffold 9 active + archive twin folders.
- Move docs/review/* to docs/archive/research/*.
Ref: ocr-container/docs/specs/2026-05-19-docs-folder-template-design.md"
```

---

### Task D2: Append `CLAUDE.md` block to `pdomain-book-tools`

- [ ] **Step 1: Append the spec §4 block** (verbatim from Task C2 Step 2) to `pdomain-book-tools/CLAUDE.md`.

- [ ] **Step 2: Verify and commit**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md superpowers-redirect block"
```

---

## Milestone E — Workspace root migration

Workspace root has the highest content volume: 17 plans, 14 specs, decisions, research, reminders, plus 7 loose `docs/superpowers/*.md` files and 4 loose top-level docs (`doc-cleanup-plan.md`, `label-taxonomy.md`, `python-coding-guidelines.md`, `update-post.md`, plus `Screenshot from 2026-05-16 21-31-32.png`) and a `design-system/` folder.

### Task E1: Scaffold + Pass 1 on workspace root

**Files:**
- Affected: `/workspaces/ocr-container/docs/`

- [ ] **Step 1: Snapshot**

```bash
cd /workspaces/ocr-container
ls -la docs/
find docs/superpowers -type f -name '*.md' | sort > /tmp/workspace-superpowers-pre.txt
wc -l /tmp/workspace-superpowers-pre.txt
```

- [ ] **Step 2: Scaffold** (preserves the existing `docs/specs/` and `docs/plans/` we created earlier in this work)

```bash
bash scripts/scaffold-docs.sh .
```

- [ ] **Step 3: Pass 1**

```bash
bash scripts/migrate-docs.sh . --pass 1
```

Expected: `docs/superpowers/plans/*.md` → `docs/plans/`, `docs/superpowers/specs/*.md` → `docs/specs/`, `docs/superpowers/research/*.md` → `docs/research/`, `docs/superpowers/decisions/*.md` → `docs/decisions/`, `docs/superpowers/reminders/*.md` → `docs/runbooks/`. Subfolders of `docs/superpowers/` removed once empty.

- [ ] **Step 4: Verify**

```bash
ls docs/plans/ | wc -l
ls docs/specs/ | wc -l
ls docs/research/ | wc -l
ls docs/decisions/ | wc -l
ls docs/runbooks/ | wc -l
[[ -d docs/superpowers ]] && echo "REMAINING: docs/superpowers still present (loose files)" || echo "OK"
```

Expected: plans ≥ 17, specs ≥ 14 + 1 (this design doc), research ≥ 2, decisions ≥ 1, runbooks ≥ 2. `docs/superpowers/` may still exist if it still contains the 7 loose top-level `.md` files.

- [ ] **Step 5: Commit Pass 1**

```bash
git add docs/
git status
git commit -m "docs(workspace): pass 1 migration — superpowers/{plans,specs,research,decisions,reminders}"
```

---

### Task E2: Pass 2 dry-run + hand-curation + apply

**Files:**
- Affected: `/workspaces/ocr-container/docs/`

- [ ] **Step 1: Generate Pass 2 report**

```bash
cd /workspaces/ocr-container
bash scripts/migrate-docs.sh . --pass 2 > /tmp/workspace-pass2.tsv
cat /tmp/workspace-pass2.tsv
```

Expected rows: 7 entries for loose `docs/superpowers/*.md` files (handoffs, bot-workspaces, ship-issue-interactive, style-review-json-contract, se-ebook-isolated-sessions, spec-chain-status, 2x handoff files), each suggested to `docs/archive/architecture/`.

- [ ] **Step 2: Hand-curate the report**

Open `/tmp/workspace-pass2.tsv` in an editor. Change the suggested destination per the spec §6 Pass-2 guidance:

| Source | Better destination | Reason |
|---|---|---|
| `docs/superpowers/handoff-2026-05-17-cross-cut.md` | `docs/archive/research/handoff-2026-05-17-cross-cut.md` | ephemeral handoff |
| `docs/superpowers/handoff-2026-05-16-cross-cut.md` | `docs/archive/research/handoff-2026-05-16-cross-cut.md` | ephemeral handoff |
| `docs/superpowers/ship-issue-interactive.md` | `docs/process/ship-issue-interactive.md` | workflow doc |
| `docs/superpowers/bot-workspaces.md` | `docs/process/bot-workspaces.md` | workflow doc |
| `docs/superpowers/se-ebook-isolated-sessions.md` | `docs/process/se-ebook-isolated-sessions.md` | workflow doc |
| `docs/superpowers/style-review-json-contract.md` | `docs/architecture/style-review-json-contract.md` | durable reference |
| `docs/superpowers/spec-chain-status.md` | `docs/archive/research/spec-chain-status.md` | one-time status |

Save the edited report.

- [ ] **Step 3: Apply**

```bash
bash scripts/migrate-docs.sh . --pass 2 --apply /tmp/workspace-pass2.tsv
```

- [ ] **Step 4: Hand-migrate the four loose top-level workspace docs**

These are not in any known-legacy folder, so they were not in the Pass-2 report. Move by judgment:

```bash
cd /workspaces/ocr-container
git mv docs/doc-cleanup-plan.md docs/archive/plans/doc-cleanup-plan.md      # superseded by this work
git mv docs/label-taxonomy.md docs/architecture/label-taxonomy.md            # durable reference
git mv docs/python-coding-guidelines.md docs/process/python-coding-guidelines.md  # cross-cutting convention
git mv docs/update-post.md docs/archive/research/update-post.md              # one-time content
# Screenshot: move under research (likely a session-time grab):
git mv "docs/Screenshot from 2026-05-16 21-31-32.png" docs/archive/research/screenshot-2026-05-16-21-31-32.png
```

- [ ] **Step 5: Decide on `docs/design-system/`**

Inspect contents:

```bash
ls -la docs/design-system/
```

Move to `docs/architecture/design-system/` (it's durable reference) or `docs/archive/architecture/design-system/` if no longer in force. Default — move to active:

```bash
git mv docs/design-system docs/architecture/design-system
```

- [ ] **Step 6: Verify with --check**

```bash
bash scripts/scaffold-docs.sh . --check
```

Expected: exit 0.

- [ ] **Step 7: Verify `docs/superpowers/` is gone**

```bash
ls docs/ | grep -v archive | sort
[[ -d docs/superpowers ]] && echo "FAIL: superpowers still present" || echo "OK: superpowers removed"
```

- [ ] **Step 8: Commit Pass 2 + hand-curated moves**

```bash
git add docs/
git commit -m "docs(workspace): pass 2 migration — hand-curated loose docs

- handoff-*, spec-chain-status, screenshot → archive/research
- ship-issue-interactive, bot-workspaces, se-ebook-isolated-sessions,
  python-coding-guidelines → process
- style-review-json-contract, label-taxonomy, design-system → architecture
- doc-cleanup-plan, update-post → archive
- docs/superpowers/ directory removed"
```

---

### Task E3: Workspace `CLAUDE.md` block

**Files:**
- Modify: `/workspaces/ocr-container/CLAUDE.md`

- [ ] **Step 1: Append the spec §4 block** (verbatim from Task C2 Step 2).

- [ ] **Step 2: Commit**

```bash
cd /workspaces/ocr-container
git add CLAUDE.md
git commit -m "docs: add workspace CLAUDE.md superpowers-redirect block"
```

---

## Milestone F — Fan-out to the remaining 10 repos

Remaining: `pd-ocr-labeler`, `pdomain-ocr-labeler-spa`, `pdomain-ocr-ops`, `pdomain-ocr-simple-gui`, `pdomain-ocr-synth`, `pd-ocr-trainer`, `pd-png-optimizer`, `pdomain-prep-for-pgdp`, `pdomain-ui`, `se-llm-skills`.

### Task F1: Per-repo scaffold + migrate + CLAUDE.md, batched

**Files (per repo):**
- Affected: `<repo>/docs/`, `<repo>/CLAUDE.md`

Run the same sequence on each repo. Repos `pdomain-ocr-ops` and `pdomain-ui` have no existing `docs/` — pure scaffold. The rest have some existing content; use Pass 1 + Pass 2.

- [ ] **Step 1: For each repo in `pdomain-ocr-ops pdomain-ui pdomain-ocr-simple-gui`, run scaffold and commit**

```bash
for repo in pdomain-ocr-ops pdomain-ui pdomain-ocr-simple-gui; do
  bash /workspaces/ocr-container/scripts/scaffold-docs.sh /workspaces/ocr-container/$repo
  bash /workspaces/ocr-container/scripts/scaffold-docs.sh /workspaces/ocr-container/$repo --check
  ( cd /workspaces/ocr-container/$repo && git add docs/ && git commit -m "docs: scaffold workspace-standard docs/ layout" )
done
```

- [ ] **Step 2: For each repo with existing content, scaffold + Pass 1 + Pass 2 dry-run**

For each of `pd-ocr-labeler pdomain-ocr-labeler-spa pdomain-ocr-synth pd-ocr-trainer pd-png-optimizer pdomain-prep-for-pgdp se-llm-skills`:

```bash
REPO=pd-ocr-labeler  # change per iteration
bash /workspaces/ocr-container/scripts/scaffold-docs.sh /workspaces/ocr-container/$REPO
bash /workspaces/ocr-container/scripts/migrate-docs.sh /workspaces/ocr-container/$REPO --pass 1
bash /workspaces/ocr-container/scripts/migrate-docs.sh /workspaces/ocr-container/$REPO --pass 2 > /tmp/$REPO-pass2.tsv
cat /tmp/$REPO-pass2.tsv
# Review and edit /tmp/$REPO-pass2.tsv as needed.
bash /workspaces/ocr-container/scripts/migrate-docs.sh /workspaces/ocr-container/$REPO --pass 2 --apply /tmp/$REPO-pass2.tsv
bash /workspaces/ocr-container/scripts/scaffold-docs.sh /workspaces/ocr-container/$REPO --check
( cd /workspaces/ocr-container/$REPO && git add docs/ && git commit -m "docs: migrate to workspace-standard layout" )
```

Hand-curated per-repo expectations (from spec §6 / Pass 2 suggestions):

| Repo | Likely hand-edits in the report |
|---|---|
| `pd-ocr-labeler` | `docs/planning/*` → `docs/plans/` (active) or `docs/archive/plans/` (stale). `docs/review/*` + `docs/review-notes/*` → `docs/archive/research/`. `docs/usage/*` and `docs/architecture/*` → no-op. |
| `pdomain-ocr-labeler-spa` | `docs/architecture/*` no-op; `docs/archive/*` may need to be re-categorized into mirrored subfolders. |
| `pdomain-ocr-synth` | `docs/roadmap/*` → `docs/plans/` (most likely active) or `docs/archive/plans/`. `docs/specs/*` no-op. |
| `pd-ocr-trainer` | `docs/review/*` → `docs/archive/research/`. `docs/specs/*` no-op. |
| `pd-png-optimizer` | `docs/milestones/*` → `docs/plans/` or `docs/archive/plans/`. `docs/research/*` and `docs/specs/*` no-op. |
| `pdomain-prep-for-pgdp` | `docs/audit/*` → `docs/archive/architecture/`. `docs/design-brief/*` → `docs/specs/` (or `docs/archive/specs/`). `docs/futures/*` → `docs/specs/`. `docs/archive/*` already exists — re-categorize into mirrored subfolders. `docs/architecture/*` and `docs/specs/*` no-op. |
| `se-llm-skills` | `docs/superpowers/*` handled by Pass 1. `docs/diagnostics/*` → `docs/archive/research/` (or `docs/research/` if active). |

- [ ] **Step 3: Append `CLAUDE.md` block to every repo**

For each of the 10 remaining repos:

```bash
REPO=pd-ocr-labeler  # change per iteration
cat >> /workspaces/ocr-container/$REPO/CLAUDE.md << 'EOF'

## docs/ folder

This repo follows the workspace docs/ template — see `docs/README.md`. Active
folders: `architecture/`, `decisions/`, `plans/`, `process/`, `research/`,
`runbooks/`, `specs/`, `templates/`, `usage/`, plus parallel `archive/`
subfolders.

**Superpowers redirect.** When a superpowers skill (e.g. `brainstorming`,
`writing-plans`) instructs you to save to `docs/superpowers/specs/<file>.md`
or `docs/superpowers/plans/<file>.md`, save to `docs/specs/<file>.md` or
`docs/plans/<file>.md` instead. There is no `docs/superpowers/` subdirectory
in this repo.
EOF
( cd /workspaces/ocr-container/$REPO && git add CLAUDE.md && git commit -m "docs: add CLAUDE.md superpowers-redirect block" )
```

- [ ] **Step 4: Final workspace-wide verification**

```bash
for repo in pdomain-book-tools pdomain-ocr-cli pd-ocr-labeler pdomain-ocr-labeler-spa pdomain-ocr-ops \
            pdomain-ocr-simple-gui pdomain-ocr-synth pd-ocr-trainer pd-png-optimizer \
            pdomain-prep-for-pgdp pdomain-ui se-llm-skills; do
  echo "=== $repo ==="
  bash /workspaces/ocr-container/scripts/scaffold-docs.sh /workspaces/ocr-container/$repo --check
done
bash /workspaces/ocr-container/scripts/scaffold-docs.sh /workspaces/ocr-container --check
```

Expected: every repo exits 0.

---

## Open follow-ups (deferred, not in this plan)

- **F1. Issue-reconnection sweep.** After all 13 repos are migrated, run a `gh search` pass for `docs/superpowers/` in issue bodies and update via `gh issue edit`. Tracked separately.
- **F2. Pre-commit hook.** Add `scaffold-docs.sh --check` as a pre-commit hook per repo so drift is caught early.
- **F3. Upstream PR to superpowers.** Propose configurable `paths.{specs,plans}` so future repos drop the per-repo CLAUDE.md instruction.

---

## Self-Review

**1. Spec coverage:**

- §1 schema (9 active + archive) → Task A1, A2 (folders); A3 (.gitkeep); A4 (README).
- §2 `.gitkeep` convention → Task A3.
- §3 README template → Task A4 (template file content embedded verbatim).
- §4 CLAUDE.md addition → Task C2 (template), F1 (applied to all 10 remaining repos), D2 (pdomain-book-tools), E3 (workspace). All 13 repos covered.
- §5 scaffold-docs.sh (create, --check, --force) → Tasks A1–A6.
- §6 migration (Pass 1 scripted, Pass 2 dry-run + --apply) → Tasks B1–B5.
- §7 issue-reconnection → Open follow-ups (correctly deferred per spec).
- §8 rollout order (`pdomain-ocr-cli` pilot → `pdomain-book-tools` → workspace → fan-out) → Milestones C, D, E, F in that order.
- §9 open follow-ups → captured.

**2. Placeholder scan:** No "TBD", "TODO", or "fill in details." Each task has exact code, exact commands, expected output. Per-repo loops in Task F1 use a `REPO=` variable that the operator updates per iteration — explicit, not a placeholder.

**3. Type consistency:** Bash function names (`ensure_dir`, `ensure_gitkeep`, `pass1_move_dir`, `suggest_dst`, `pass2_report`, `pass2_apply`, `remove_if_empty`) are used consistently across tasks. The `ACTIVE_FOLDERS` array and `ACTIVE` string variable are the same nine names everywhere.

**4. FastAPI + SPA check:** N/A. This plan produces bash scripts and content moves only — no FastAPI backend, no React/Vite SPA.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-19-docs-folder-template.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Which approach?
