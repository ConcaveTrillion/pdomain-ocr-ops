# repo-setup Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an idempotent `repo-setup` skill that audits and repairs the workspace's repos across label, docs, conventions, and hygiene dimensions, driven by a single canonical repo manifest.

**Architecture:** A new `scripts/workspace-repos.json` manifest becomes the single source of truth for the repo list. `sync-labels.sh` is repointed at it; a new `repo-hygiene-check.sh` covers baseline files; a new `.claude/skills/repo-setup/SKILL.md` orchestrates all four dimension scripts per-repo and reports/repairs drift.

**Tech Stack:** Bash (POSIX-ish, `set -euo pipefail`), `jq`, `gh` CLI, Python 3 (manifest validator), `bats` + `lib.sh` shell-test harness, pytest.

**Spec:** `docs/specs/2026-05-21-repo-setup-skill-design.md`

---

## File Structure

- **Create** `scripts/workspace-repos.json` — canonical repo manifest (name, lang[], status).
- **Create** `scripts/validate-workspace-repos.py` — schema validator for the manifest.
- **Create** `scripts/repo-hygiene-check.sh` — baseline-files audit/repair for one repo.
- **Create** `.claude/skills/repo-setup/SKILL.md` — the orchestration skill.
- **Create** `tests/scripts/test_workspace_repos_manifest.py` — manifest + validator tests.
- **Create** `scripts/tests/test-repo-hygiene-check.sh` — hygiene-script tests (uses `lib.sh`).
- **Modify** `scripts/sync-labels.sh` — read `repos[]` from the manifest, not from canon.
- **Modify** `scripts/sync-labels-canon.json` — remove the `repos[]` key (catalog only).
- **Modify** `scripts/tests/test_sync_labels.bats` — update the canon-shape test for the new layout.

---

## Task 1: Canonical repo manifest + validator

**Files:**
- Create: `scripts/workspace-repos.json`
- Create: `scripts/validate-workspace-repos.py`
- Test: `tests/scripts/test_workspace_repos_manifest.py`

- [ ] **Step 1: Write the failing test**

Create `tests/scripts/test_workspace_repos_manifest.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "scripts" / "workspace-repos.json"
VALIDATOR = REPO_ROOT / "scripts" / "validate-workspace-repos.py"

VALID_LANGS = {"python", "ts", "rust"}
VALID_STATUS = {"active", "retiring", "reference", "spec-only"}


def test_manifest_is_valid_json_array():
    data = json.loads(MANIFEST.read_text())
    assert isinstance(data, list)
    assert len(data) >= 13


def test_every_entry_has_required_fields():
    data = json.loads(MANIFEST.read_text())
    for entry in data:
        assert set(entry) == {"name", "lang", "status"}, entry
        assert isinstance(entry["name"], str) and entry["name"]
        assert isinstance(entry["lang"], list)
        assert all(l in VALID_LANGS for l in entry["lang"]), entry
        assert entry["status"] in VALID_STATUS, entry


def test_repo_names_are_unique():
    data = json.loads(MANIFEST.read_text())
    names = [e["name"] for e in data]
    assert len(names) == len(set(names))


def test_previously_missing_repos_are_present():
    data = json.loads(MANIFEST.read_text())
    names = {e["name"] for e in data}
    for repo in ("pdomain-ocr-training", "pdomain-ocr-simple-gui", "pdomain-ui", "se-llm-skills"):
        assert repo in names


def test_pd_book_tools_is_reference():
    data = json.loads(MANIFEST.read_text())
    bt = next(e for e in data if e["name"] == "pdomain-book-tools")
    assert bt["status"] == "reference"


def test_validator_passes_on_real_manifest():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(MANIFEST)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_validator_rejects_bad_status(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([{"name": "x", "lang": ["python"], "status": "bogus"}]))
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(bad)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "status" in result.stderr.lower()


def test_validator_rejects_duplicate_names(tmp_path):
    bad = tmp_path / "dup.json"
    bad.write_text(json.dumps([
        {"name": "x", "lang": ["python"], "status": "active"},
        {"name": "x", "lang": ["ts"], "status": "active"},
    ]))
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(bad)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "duplicate" in result.stderr.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scripts/test_workspace_repos_manifest.py -v`
Expected: FAIL — `FileNotFoundError` / `JSONDecodeError` (manifest and validator do not exist yet).

- [ ] **Step 3: Create the manifest**

Create `scripts/workspace-repos.json`:

```json
[
  { "name": "pdomain-book-tools",      "lang": ["python"],         "status": "reference" },
  { "name": "pdomain-ocr-cli",         "lang": ["python"],         "status": "active" },
  { "name": "pd-ocr-labeler",     "lang": ["python"],         "status": "active" },
  { "name": "pdomain-ocr-labeler-spa", "lang": ["python", "ts"],   "status": "active" },
  { "name": "pdomain-ocr-ops",         "lang": ["python"],         "status": "active" },
  { "name": "pdomain-ocr-simple-gui",  "lang": ["python", "ts"],   "status": "active" },
  { "name": "pdomain-ocr-synth",       "lang": ["python"],         "status": "active" },
  { "name": "pd-ocr-trainer",     "lang": ["python"],         "status": "retiring" },
  { "name": "pdomain-ocr-training",    "lang": ["python"],         "status": "active" },
  { "name": "pd-png-optimizer",   "lang": ["rust", "python"], "status": "active" },
  { "name": "pdomain-prep-for-pgdp",   "lang": ["python", "ts"],   "status": "active" },
  { "name": "pdomain-ui",              "lang": ["ts"],             "status": "active" },
  { "name": "se-llm-skills",      "lang": ["python"],         "status": "active" },
  { "name": "ocr-container-meta", "lang": [],                 "status": "active" }
]
```

- [ ] **Step 4: Create the validator**

Create `scripts/validate-workspace-repos.py`:

```python
#!/usr/bin/env python3
"""Validate scripts/workspace-repos.json against the manifest schema.

Usage: validate-workspace-repos.py <manifest-path>
Exit 0 if valid; exit 1 with an explanation on stderr otherwise.
"""
import json
import sys
from pathlib import Path

VALID_LANGS = {"python", "ts", "rust"}
VALID_STATUS = {"active", "retiring", "reference", "spec-only"}


def fail(msg: str) -> None:
    print(f"workspace-repos.json: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: validate-workspace-repos.py <manifest-path>")
    path = Path(sys.argv[1])
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"could not read/parse: {exc}")

    if not isinstance(data, list):
        fail("top level must be a JSON array")

    seen: set[str] = set()
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            fail(f"entry {i} is not an object")
        if set(entry) != {"name", "lang", "status"}:
            fail(f"entry {i} must have exactly keys name, lang, status — got {sorted(entry)}")
        name = entry["name"]
        if not isinstance(name, str) or not name:
            fail(f"entry {i} has an invalid name")
        if name in seen:
            fail(f"duplicate repo name: {name}")
        seen.add(name)
        if not isinstance(entry["lang"], list) or any(l not in VALID_LANGS for l in entry["lang"]):
            fail(f"{name}: lang must be a list of {sorted(VALID_LANGS)}")
        if entry["status"] not in VALID_STATUS:
            fail(f"{name}: status must be one of {sorted(VALID_STATUS)}")

    print(f"workspace-repos.json: OK ({len(data)} repos)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/scripts/test_workspace_repos_manifest.py -v`
Expected: PASS — all 8 tests green.

- [ ] **Step 6: Commit**

```bash
git add scripts/workspace-repos.json scripts/validate-workspace-repos.py tests/scripts/test_workspace_repos_manifest.py
git commit -m "feat(scripts): add canonical workspace-repos.json manifest + validator"
```

---

## Task 2: Repoint sync-labels.sh at the manifest

**Files:**
- Modify: `scripts/sync-labels.sh:4-5` (path vars) and `:137-142` (REPOS population)
- Modify: `scripts/sync-labels-canon.json` (remove `repos[]`)
- Test: `scripts/tests/test_sync_labels.bats:14-18`

- [ ] **Step 1: Update the failing test**

Replace the test at `scripts/tests/test_sync_labels.bats:9-18` (the `canon json validates` and `every repo listed in canon.repos` tests) with:

```bash
@test "canon json validates" {
    run jq empty "$CANON"
    [ "$status" -eq 0 ]
}

@test "canon no longer carries a repos[] key" {
    run bash -c "jq -e 'has(\"repos\")' \"$CANON\""
    [ "$status" -ne 0 ]
}

@test "manifest is the repo source and is non-empty" {
    run bash -c "jq -r '.[].name' \"$SCRIPT_DIR/workspace-repos.json\" | wc -l"
    [ "$status" -eq 0 ]
    [ "$output" -gt 0 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats scripts/tests/test_sync_labels.bats`
Expected: FAIL — `canon no longer carries a repos[] key` fails (canon still has `repos[]`); the manifest test passes (Task 1 created it).

- [ ] **Step 3: Edit sync-labels.sh to read the manifest**

In `scripts/sync-labels.sh`, after the `CANON=` line (`:5`), add:

```bash
MANIFEST="$SCRIPT_DIR/workspace-repos.json"
```

Replace the `REPOS` population block (`:137-142`):

```bash
REPOS=()
if [[ -n "$TARGET_REPO" ]]; then
    REPOS=("$TARGET_REPO")
else
    mapfile -t REPOS < <(jq -r '.repos[]' "$CANON")
fi
```

with:

```bash
REPOS=()
if [[ -n "$TARGET_REPO" ]]; then
    REPOS=("$TARGET_REPO")
elif [[ -r "$MANIFEST" ]]; then
    # Sync labels for every manifest repo except spec-only (not yet bootstrapped).
    mapfile -t REPOS < <(jq -r '.[] | select(.status != "spec-only") | .name' "$MANIFEST")
else
    echo "Manifest not found: $MANIFEST" >&2
    exit 2
fi
```

- [ ] **Step 4: Remove repos[] from the canon file**

In `scripts/sync-labels-canon.json`, delete the `"repos": [ ... ]` key and its array entirely. Keep `labels`, `renames`, and `local_extensions`. Verify it still parses:

Run: `jq empty scripts/sync-labels-canon.json`
Expected: exit 0, no output.

- [ ] **Step 5: Run tests to verify they pass**

Run: `bats scripts/tests/test_sync_labels.bats`
Expected: PASS — all tests green, including the new canon/manifest tests.

Run: `bash scripts/sync-labels.sh --dry-run`
Expected: a `[DRY RUN]` banner followed by one `=== ConcaveTrillion/<repo> ===` block per non-spec-only manifest repo (14 repos).

- [ ] **Step 6: Commit**

```bash
git add scripts/sync-labels.sh scripts/sync-labels-canon.json scripts/tests/test_sync_labels.bats
git commit -m "refactor(scripts): sync-labels reads repo list from workspace-repos.json"
```

---

## Task 3: repo-hygiene-check.sh

**Files:**
- Create: `scripts/repo-hygiene-check.sh`
- Test: `scripts/tests/test-repo-hygiene-check.sh`

- [ ] **Step 1: Write the failing test**

Create `scripts/tests/test-repo-hygiene-check.sh`:

```bash
#!/usr/bin/env bash
# Tests for repo-hygiene-check.sh
set -euo pipefail
source "$(dirname "$0")/lib.sh"

SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/repo-hygiene-check.sh"

test_check_flags_missing_claude_gitignore() {
  local repo; repo="$(setup_test_repo)"
  echo "node_modules/" > "$repo/.gitignore"
  set +e
  out="$("$SCRIPT" "$repo" --check --lang python 2>&1)"; rc=$?
  set -e
  assert_exit 1 "$rc" "--check exits 1 on drift"
  [[ "$out" == *".claude/"* ]] && PASS_COUNT=$((PASS_COUNT+1)) \
    || { echo "  FAIL: expected .claude/ drift line" >&2; FAIL_COUNT=$((FAIL_COUNT+1)); }
  cleanup_test_repo "$repo"
}

test_fix_appends_claude_gitignore() {
  local repo; repo="$(setup_test_repo)"
  echo "node_modules/" > "$repo/.gitignore"
  "$SCRIPT" "$repo" --fix --lang python >/dev/null 2>&1 || true
  grep -qx '.claude/' "$repo/.gitignore" \
    && PASS_COUNT=$((PASS_COUNT+1)) \
    || { echo "  FAIL: .claude/ not appended" >&2; FAIL_COUNT=$((FAIL_COUNT+1)); }
  cleanup_test_repo "$repo"
}

test_fix_is_idempotent() {
  local repo; repo="$(setup_test_repo)"
  printf 'node_modules/\n.claude/\n' > "$repo/.gitignore"
  "$SCRIPT" "$repo" --fix --lang python >/dev/null 2>&1 || true
  local count
  count="$(grep -cx '.claude/' "$repo/.gitignore")"
  assert_exit 1 "$count" "exactly one .claude/ line after fix"
  cleanup_test_repo "$repo"
}

test_check_passes_clean_repo() {
  local repo; repo="$(setup_test_repo)"
  printf 'node_modules/\n.claude/\n' > "$repo/.gitignore"
  touch "$repo/mise.toml"
  mkdir -p "$repo/docs/conventions"
  touch "$repo/docs/conventions/lint-deviations.md"
  printf '[tool.ruff]\n' > "$repo/pyproject.toml"
  set +e
  "$SCRIPT" "$repo" --check --lang python --no-gh >/dev/null 2>&1; rc=$?
  set -e
  assert_exit 0 "$rc" "--check exits 0 on a clean repo"
  cleanup_test_repo "$repo"
}

test_ts_lang_checks_npmrc() {
  local repo; repo="$(setup_test_repo)"
  printf 'node_modules/\n.claude/\n' > "$repo/.gitignore"
  touch "$repo/mise.toml"
  mkdir -p "$repo/docs/conventions"
  touch "$repo/docs/conventions/lint-deviations.md"
  set +e
  out="$("$SCRIPT" "$repo" --check --lang ts --no-gh 2>&1)"; rc=$?
  set -e
  assert_exit 1 "$rc" "ts repo missing .npmrc store-dir is drift"
  [[ "$out" == *".npmrc"* ]] && PASS_COUNT=$((PASS_COUNT+1)) \
    || { echo "  FAIL: expected .npmrc drift line" >&2; FAIL_COUNT=$((FAIL_COUNT+1)); }
  cleanup_test_repo "$repo"
}

run_test test_check_flags_missing_claude_gitignore
run_test test_fix_appends_claude_gitignore
run_test test_fix_is_idempotent
run_test test_check_passes_clean_repo
run_test test_ts_lang_checks_npmrc
summarize_and_exit
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash scripts/tests/test-repo-hygiene-check.sh`
Expected: FAIL — script not found / not executable.

- [ ] **Step 3: Create repo-hygiene-check.sh**

Create `scripts/repo-hygiene-check.sh`:

```bash
#!/usr/bin/env bash
# repo-hygiene-check.sh — audit/repair baseline hygiene files for one repo.
set -euo pipefail

usage() {
  cat <<EOF
repo-hygiene-check.sh <repo-path> [--check|--fix] [--lang l,l,...] [--no-gh]

  --check   Report drift only (default). Exit 1 if any drift found.
  --fix     Apply safe fixes (currently: append .claude/ to .gitignore).
  --lang    Comma-separated languages (python,ts,rust) — drives lang checks.
  --no-gh   Skip the GitHub merge-setting check (for offline tests).
EOF
}

REPO="${1:-}"
[[ -z "$REPO" || "$REPO" == "--help" || "$REPO" == "-h" ]] && { usage; exit 2; }
shift

MODE="--check"
LANGS=""
USE_GH=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) MODE="--check" ;;
    --fix)   MODE="--fix" ;;
    --lang)  shift; LANGS="$1" ;;
    --no-gh) USE_GH=0 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

[[ -d "$REPO" ]] || { echo "Not a directory: $REPO" >&2; exit 2; }

DRIFT=0
drift() { echo "  DRIFT: $1"; DRIFT=1; }
ok()    { echo "  ok: $1"; }

# --- lang-agnostic: .gitignore has a .claude/ entry -----------------------
GITIGNORE="$REPO/.gitignore"
if [[ -f "$GITIGNORE" ]] && grep -qx '.claude/' "$GITIGNORE"; then
  ok ".gitignore has .claude/"
else
  if [[ "$MODE" == "--fix" ]]; then
    printf '.claude/\n' >> "$GITIGNORE"
    echo "  fixed: appended .claude/ to .gitignore"
  else
    drift ".gitignore missing .claude/ entry"
  fi
fi

# --- lang-agnostic: check-only presence checks ----------------------------
[[ -f "$REPO/mise.toml" ]] && ok "mise.toml present" || drift "mise.toml absent"
if [[ -f "$REPO/docs/conventions/lint-deviations.md" ]]; then
  ok "docs/conventions/lint-deviations.md present"
else
  drift "docs/conventions/lint-deviations.md absent"
fi

# --- lang-agnostic: GH merge setting (check-only) -------------------------
if [[ "$USE_GH" -eq 1 ]] && command -v gh >/dev/null 2>&1; then
  slug="ConcaveTrillion/$(basename "$REPO")"
  squash="$(gh api "repos/$slug" --jq '.allow_squash_merge' 2>/dev/null || echo "")"
  if [[ "$squash" == "true" ]]; then
    drift "$slug allow_squash_merge=true (should be false)"
  elif [[ "$squash" == "false" ]]; then
    ok "allow_squash_merge=false"
  fi
fi

# --- lang-additive checks -------------------------------------------------
IFS=',' read -ra LANG_ARR <<< "$LANGS"
for lang in "${LANG_ARR[@]}"; do
  case "$lang" in
    python)
      if [[ -f "$REPO/pyproject.toml" ]] && grep -q '\[tool\.ruff' "$REPO/pyproject.toml"; then
        ok "pyproject.toml has [tool.ruff]"
      else
        drift "pyproject.toml missing [tool.ruff]"
      fi
      ;;
    ts)
      if [[ -f "$REPO/.npmrc" ]] && grep -q '^store-dir=' "$REPO/.npmrc"; then
        ok ".npmrc has store-dir"
      else
        drift ".npmrc missing store-dir= line"
      fi
      ;;
    rust)
      if grep -rqs '\[lints\.clippy\]' "$REPO/Cargo.toml" 2>/dev/null \
         || [[ -f "$REPO/clippy.toml" ]]; then
        ok "clippy config present"
      else
        drift "no clippy config (Cargo.toml [lints.clippy] or clippy.toml)"
      fi
      ;;
    "" ) ;;
    *) echo "  (unknown lang '$lang' — skipped)" ;;
  esac
done

[[ "$DRIFT" -eq 1 && "$MODE" == "--check" ]] && exit 1
exit 0
```

- [ ] **Step 4: Make it executable and run the test to verify it passes**

Run:
```bash
chmod +x scripts/repo-hygiene-check.sh
bash scripts/tests/test-repo-hygiene-check.sh
```
Expected: PASS — `Tests: N. Passed: N. Failed: 0.`

- [ ] **Step 5: Commit**

```bash
git add scripts/repo-hygiene-check.sh scripts/tests/test-repo-hygiene-check.sh
git commit -m "feat(scripts): add repo-hygiene-check.sh baseline-files auditor"
```

---

## Task 4: The repo-setup skill

**Files:**
- Create: `.claude/skills/repo-setup/SKILL.md`

- [ ] **Step 1: Create the skill definition**

Create `.claude/skills/repo-setup/SKILL.md`:

````markdown
---
name: repo-setup
description: Idempotent audit-and-repair for the ocr-container workspace repos — checks GH label taxonomy, the docs/ folder template, synced CONVENTIONS/process blocks, and baseline hygiene files against the canonical workspace-repos.json manifest. Use when CT invokes `/repo-setup [<repo>] [--check|--fix]`, or when onboarding a repo to workspace standards.
---

# repo-setup

Audits the workspace repos against four dimensions and (optionally) repairs
drift. Safe to re-run — idempotent.

## Invocation

- `/repo-setup` — audit every repo in the manifest.
- `/repo-setup <repo>` — audit one repo (basename, no org prefix).
- `--check` (default) — report drift only, no writes.
- `--fix` — apply safe fixes.

## Source of truth

`scripts/workspace-repos.json` — the canonical repo list. Each entry has
`name`, `lang` (array of `python`/`ts`/`rust`), and `status`
(`active`/`retiring`/`reference`/`spec-only`). Never hand-edit a repo list
anywhere else.

## Procedure

1. **Validate the manifest** — run
   `uv run python scripts/validate-workspace-repos.py scripts/workspace-repos.json`.
   Abort on non-zero exit.

2. **Resolve scope** — if `<repo>` was given, that one repo; else every
   manifest entry. For each repo determine the action by `status`:
   - `reference` — **skip** (pdomain-book-tools defines the standard).
   - `retiring` — **warn-only**: run checks, never apply fixes.
   - `spec-only` — **skip** with a note (repo not bootstrapped).
   - `active` — full audit; apply fixes under `--fix`.

3. **Per repo, run the four dimension checks.** Delegate the script runs to
   a subagent so raw output stays out of the parent context — collect only
   the pass/drift summary.

   | Dimension | `--check` command | `--fix` command |
   |-----------|-------------------|-----------------|
   | Labels | `bash scripts/sync-labels.sh --repo <name> --dry-run` | `bash scripts/sync-labels.sh --repo <name>` |
   | docs/ template | `bash scripts/scaffold-docs.sh <path> --check` | `bash scripts/scaffold-docs.sh <path>` |
   | CONVENTIONS/blocks | `uv run python scripts/sync-workspace-blocks.py --check <path>` | `uv run python scripts/sync-workspace-blocks.py <path>` |
   | Hygiene | `bash scripts/repo-hygiene-check.sh <path> --check --lang <langs>` | `bash scripts/repo-hygiene-check.sh <path> --fix --lang <langs>` |

   `<path>` is `/workspaces/ocr-container/<name>`. `<langs>` is the comma-joined
   `lang` array from the manifest.

   > Confirm the exact `sync-workspace-blocks.py` CLI (`--check` flag, path
   > argument) by reading the script before first use; adjust the commands
   > above if its interface differs.

4. **Report.** Print one drift table for the whole run:

   ```
   repo                 labels   docs    blocks  hygiene
   pdomain-ocr-cli           ok       ok      ok      DRIFT
   pdomain-ui                DRIFT    ok      ok      ok
   ```

   Under `--check`, list each drift line beneath the table. Under `--fix`,
   list what was changed and re-run `--check` to confirm the repo is clean.

5. **Never auto-fix** GH merge settings or `lint-deviations.md` content —
   `repo-hygiene-check.sh` only reports those.

## Notes

- `gh` unauthenticated → label + merge-setting checks degrade to
  report-only; other dimensions still run.
- A manifest repo whose directory is absent on disk → one error row; the
  loop continues.
- `--fix` writes into the interactive checkouts under
  `/workspaces/ocr-container/<repo>/`. It does not commit — review and
  commit per-repo afterwards.
````

- [ ] **Step 2: Verify the skill is discoverable**

Run: `ls .claude/skills/repo-setup/SKILL.md`
Expected: the path prints (file exists).

Confirm the frontmatter `name:` and `description:` are present and the
`description` names the `/repo-setup` trigger — the harness loads skills by
this metadata.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/repo-setup/SKILL.md
git commit -m "feat(skills): add repo-setup audit/repair skill"
```

---

## Task 5: Backfill the four newly-tracked repos

The manifest now includes `pdomain-ocr-training`, `pdomain-ocr-simple-gui`, `pdomain-ui`,
and `se-llm-skills`, which previously had no `kind:*` taxonomy. Run the
label sync to bring them up to canon.

**Files:** none — this task only runs the tool.

- [ ] **Step 1: Dry-run the label sync for the four repos**

Run:
```bash
for r in pdomain-ocr-training pdomain-ocr-simple-gui pdomain-ui se-llm-skills; do
  bash scripts/sync-labels.sh --repo "$r" --dry-run
done
```
Expected: each block lists `+ create` lines for the missing `kind:*`,
`status:*`, `triage:*`, `effort:*` labels. (`kind:chore` already exists on
all four — created 2026-05-21 — so it will not appear.)

- [ ] **Step 2: Apply the label sync**

Run:
```bash
for r in pdomain-ocr-training pdomain-ocr-simple-gui pdomain-ui se-llm-skills; do
  bash scripts/sync-labels.sh --repo "$r"
done
```
Expected: `+ created` lines and a per-repo `Summary` with `created > 0`.

- [ ] **Step 3: Verify with a full audit**

Run: invoke `/repo-setup --check`
Expected: the four backfilled repos show `ok` in the `labels` column.

- [ ] **Step 4: Verify the whole test suite**

Run:
```bash
uv run pytest tests/scripts/test_workspace_repos_manifest.py -v
bats scripts/tests/test_sync_labels.bats
bash scripts/tests/test-repo-hygiene-check.sh
```
Expected: all three suites green.

- [ ] **Step 5: Commit (no-op safety / changelog)**

No files changed by Task 5. If a workspace changelog or process doc tracks
tooling additions, add a one-line entry there and commit; otherwise skip.

---

## Self-Review

- **Spec coverage:** §3 manifest → Task 1; §3 sync-labels repoint + canon
  trim → Task 2; §4 skill → Task 4; §5 `repo-hygiene-check.sh` → Task 3;
  §2 "fixes the canon drift" outcome → Task 5. §6 data flow and §7 error
  handling are realised in the Task 4 skill procedure and the script
  fallbacks. §8 testing → the test files in Tasks 1–3. All covered.
- **Placeholders:** none — every step has concrete code or an exact command.
  The one explicit unknown (the `sync-workspace-blocks.py` CLI) is called
  out as a read-before-use note in Task 4, not left as a silent TODO.
- **Type consistency:** manifest keys `name`/`lang`/`status` and the
  `VALID_LANGS`/`VALID_STATUS` sets are identical across the validator,
  the pytest tests, and the skill doc. `repo-hygiene-check.sh` flags
  (`--check`/`--fix`/`--lang`/`--no-gh`) match between the script, its
  tests, and the skill's command table.
- **FastAPI + SPA check:** not applicable — this plan builds workspace
  tooling (shell scripts + a skill), no FastAPI app or React SPA.
