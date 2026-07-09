---
title: dep-refresh GitHub Action — implementation plan
date: 2026-05-31
repo: ConcaveTrillion/ocr-container-meta
spec: docs/specs/2026-05-31-dep-refresh-github-action-design.md
status: active
---

# dep-refresh GitHub Action — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automated weekly refresh of GitHub Actions SHA pins and all Python/npm deps across 12 pdomain repos, landing as auto-merging PRs when CI passes.

**Architecture:** Central `dispatch-dep-refresh.yml` in `ocr-container-meta` sends `repository_dispatch` to each repo. Each repo owns an identical `dep-refresh.yml` + `scripts/update_github_actions.py`. `repo-hygiene-check.sh` detects drift from the pdomain-book-tools reference. Sequence: prerequisite → reference impl → propagate (parallel) → GitHub setup → orchestrator → hygiene checks → smoke test.

**Tech Stack:** GitHub Actions, Python 3.12, uv, pnpm/npm, gh CLI, bash.

---

## File Structure

**New — per repo (×12):**
- `<repo>/scripts/update_github_actions.py` — pdomain action-pin refresher (identical across all repos)
- `<repo>/.github/workflows/dep-refresh.yml` — self-contained dep-refresh workflow (identical across all repos)

**New — pdomain-book-tools only (reference + tests):**
- `pdomain-book-tools/scripts/__init__.py` — makes scripts/ importable
- `pdomain-book-tools/tests/test_update_github_actions.py` — unit tests

**New — orchestrator:**
- `ocr-container-meta/.github/workflows/dispatch-dep-refresh.yml`

**Modified:**
- `pdomain-index-npm/Makefile` — add `upgrade-deps` target (prerequisite)
- `scripts/repo-hygiene-check.sh` — add drift checks
- `scripts/tests/test-repo-hygiene-check.sh` — extend tests

---

## Task 1: Add `upgrade-deps` to `pdomain-index-npm`

**Files:**
- Modify: `pdomain-index-npm/Makefile`

`pdomain-index-npm` has no `upgrade-deps` target; the dep-refresh workflow calls `make upgrade-deps` unconditionally. This is the only blocking prerequisite.

- [ ] **Step 1: Open the Makefile and locate the `.PHONY` line**

```bash
grep -n 'PHONY\|upgrade' /workspaces/ocr-container/pdomain-index-npm/Makefile | head -10
```

- [ ] **Step 2: Add the target**

Add to the `.PHONY` list and insert the target after existing targets:

```makefile
upgrade-deps: ## Upgrade npm dependencies
	npm update

.PHONY: upgrade-deps
```

- [ ] **Step 3: Verify**

```bash
cd /workspaces/ocr-container/pdomain-index-npm
make upgrade-deps
```

Expected: `npm update` runs cleanly. `package-lock.json` may show minor version bumps — that is correct behaviour.

- [ ] **Step 4: Commit**

```bash
git -C /workspaces/ocr-container/pdomain-index-npm add Makefile
git -C /workspaces/ocr-container/pdomain-index-npm commit -m "chore: add upgrade-deps Make target"
```

---

## Task 2: `update_github_actions.py` — pdomain variant + tests (pdomain-book-tools)

The pdomain variant is derived from `oxipng-pybind/scripts/update_github_actions.py` with Rust-specific handling removed. Write tests first (TDD), then the script.

**Files:**
- Create: `pdomain-book-tools/scripts/__init__.py`
- Create: `pdomain-book-tools/tests/test_update_github_actions.py`
- Create: `pdomain-book-tools/scripts/update_github_actions.py`

### Step 2.1: Create `scripts/__init__.py`

- [ ] **Step 1: Create the file**

```bash
touch /workspaces/ocr-container/pdomain-book-tools/scripts/__init__.py
```

This makes `scripts/` importable as a package in pytest (mirrors `pdomain-index-pip/scripts/__init__.py`).

### Step 2.2: Write failing tests

- [ ] **Step 2: Create `tests/test_update_github_actions.py`**

```python
"""Tests for scripts/update_github_actions.py (pdomain action-pin refresher)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts import update_github_actions as uga


def _runner(responses: dict[str, object]):
    """Return a fake gh runner that returns canned JSON responses."""
    def run(command: list[str]) -> subprocess.CompletedProcess[str]:
        endpoint = command[2]  # gh api <endpoint>
        return subprocess.CompletedProcess(
            command, 0, stdout=json.dumps(responses[endpoint]), stderr=""
        )
    return run


def test_gh_json_parses_response() -> None:
    runner = _runner({"repos/actions/checkout/releases/latest": {"tag_name": "v4.2.2"}})
    result = uga.gh_json("repos/actions/checkout/releases/latest", runner=runner)
    assert result == {"tag_name": "v4.2.2"}


def test_latest_release_lightweight_tag() -> None:
    sha = "a" * 40
    runner = _runner(
        {
            "repos/actions/checkout/releases/latest": {"tag_name": "v4.2.2"},
            "repos/actions/checkout/git/ref/tags/v4.2.2": {
                "object": {"sha": sha, "type": "commit"}
            },
        }
    )
    release = uga.latest_release("actions/checkout", runner=runner)
    assert release == uga.ActionRelease(tag="v4.2.2", sha=sha)


def test_latest_release_annotated_tag() -> None:
    tag_sha = "b" * 40
    commit_sha = "c" * 40
    runner = _runner(
        {
            "repos/astral-sh/setup-uv/releases/latest": {"tag_name": "v8.1.0"},
            "repos/astral-sh/setup-uv/git/ref/tags/v8.1.0": {
                "object": {"sha": tag_sha, "type": "tag"}
            },
            f"repos/astral-sh/setup-uv/git/tags/{tag_sha}": {
                "object": {"sha": commit_sha}
            },
        }
    )
    release = uga.latest_release("astral-sh/setup-uv", runner=runner)
    assert release == uga.ActionRelease(tag="v8.1.0", sha=commit_sha)


def test_update_workflow_refs_rewrites_sha(tmp_path: Path) -> None:
    wf = tmp_path / "ci.yml"
    old_sha = "o" * 40
    wf.write_text(f"steps:\n  - uses: actions/checkout@{old_sha}  # v4\n")
    new_sha = "n" * 40
    releases = {"actions/checkout": uga.ActionRelease(tag="v4.2.2", sha=new_sha)}
    changed = uga.update_workflow_refs(wf, releases=releases)
    assert changed is True
    assert new_sha in wf.read_text()
    assert old_sha not in wf.read_text()


def test_update_workflow_refs_no_change(tmp_path: Path) -> None:
    sha = "a" * 40
    wf = tmp_path / "ci.yml"
    wf.write_text(f"steps:\n  - uses: actions/checkout@{sha}  # v4\n")
    releases = {"actions/checkout": uga.ActionRelease(tag="v4.2.2", sha=sha)}
    changed = uga.update_workflow_refs(wf, releases=releases)
    assert changed is False


def test_update_workflow_refs_ignores_unmanaged(tmp_path: Path) -> None:
    wf = tmp_path / "ci.yml"
    original = "steps:\n  - uses: some-org/unknown-action@deadbeef\n"
    wf.write_text(original)
    changed = uga.update_workflow_refs(wf, releases={})
    assert changed is False
    assert wf.read_text() == original


def test_update_github_actions_returns_changed_paths(tmp_path: Path) -> None:
    wf_dir = tmp_path
    old_sha = "o" * 40
    new_sha = "n" * 40
    (wf_dir / "ci.yml").write_text(
        f"steps:\n  - uses: actions/checkout@{old_sha}  # v4\n"
    )
    (wf_dir / "release.yml").write_text("steps:\n  - run: echo hello\n")

    # Build a runner that responds to every MANAGED_ACTIONS release query
    responses: dict[str, object] = {
        "repos/actions/checkout/releases/latest": {"tag_name": "v4.2.2"},
        "repos/actions/checkout/git/ref/tags/v4.2.2": {
            "object": {"sha": new_sha, "type": "commit"}
        },
    }
    for action in uga.MANAGED_ACTIONS:
        if action == "actions/checkout":
            continue
        responses[f"repos/{action}/releases/latest"] = {"tag_name": "v1.0.0"}
        responses[f"repos/{action}/git/ref/tags/v1.0.0"] = {
            "object": {"sha": "x" * 40, "type": "commit"}
        }

    changed = uga.update_github_actions(workflow_dir=wf_dir, runner=_runner(responses))
    assert len(changed) == 1
    assert changed[0] == wf_dir / "ci.yml"
```

- [ ] **Step 3: Run — confirm ImportError (script absent)**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
uv run pytest tests/test_update_github_actions.py -v 2>&1 | head -15
```

Expected: `ModuleNotFoundError` for `scripts.update_github_actions`.

### Step 2.3: Write the script

- [ ] **Step 4: Create `scripts/update_github_actions.py`**

```python
#!/usr/bin/env python3
"""Refresh reviewed GitHub Actions refs in workflow files."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github/workflows"
MANAGED_ACTIONS = (
    "actions/checkout",
    "astral-sh/setup-uv",
    "actions/setup-python",
    "actions/upload-artifact",
    "actions/download-artifact",
    "peter-evans/create-pull-request",
)


@dataclass(frozen=True)
class ActionRelease:
    """Latest release tag and immutable commit SHA."""

    tag: str
    sha: str


GhRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def resolve_executable(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise RuntimeError(f"{name} executable not found on PATH")
    return executable


def run_gh(command: list[str]) -> subprocess.CompletedProcess[str]:
    resolved = [resolve_executable(command[0]), *command[1:]]
    return subprocess.run(  # noqa: S603
        resolved, cwd=ROOT, check=True, capture_output=True, text=True
    )


def gh_json(endpoint: str, *, runner: GhRunner = run_gh) -> dict[str, object]:
    result = runner(["gh", "api", endpoint])
    return cast("dict[str, object]", json.loads(result.stdout))


def latest_release(action: str, *, runner: GhRunner = run_gh) -> ActionRelease:
    """Return the latest release tag and target commit SHA for an action."""
    release = gh_json(f"repos/{action}/releases/latest", runner=runner)
    tag = release.get("tag_name")
    if not isinstance(tag, str):
        raise TypeError(f"latest release for {action} did not include tag_name")
    tag_ref = gh_json(f"repos/{action}/git/ref/tags/{tag}", runner=runner)
    raw_object = tag_ref.get("object")
    if not isinstance(raw_object, dict):
        raise TypeError(f"tag ref for {action}@{tag} did not include object")
    tag_object = cast("dict[str, object]", raw_object)
    sha = tag_object.get("sha")
    if tag_object.get("type") == "tag" and isinstance(sha, str):
        tag_payload = gh_json(f"repos/{action}/git/tags/{sha}", runner=runner)
        nested = tag_payload.get("object")
        if not isinstance(nested, dict):
            raise TypeError(f"annotated tag for {action}@{tag} did not include object")
        sha = cast("dict[str, object]", nested).get("sha")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise TypeError(f"tag ref for {action}@{tag} did not resolve to a commit SHA")
    return ActionRelease(tag=tag, sha=sha)


def update_workflow_refs(path: Path, *, releases: dict[str, ActionRelease]) -> bool:
    """Update managed action refs in one workflow file. Returns True if changed."""
    text = path.read_text(encoding="utf-8")
    updated = text
    for action, release in releases.items():
        updated = re.sub(
            rf"(?m)(uses:\s+{re.escape(action)}@)[^\s]+",
            rf"\g<1>{release.sha}",
            updated,
        )
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def update_github_actions(
    *,
    workflow_dir: Path = WORKFLOW_DIR,
    runner: GhRunner = run_gh,
) -> list[Path]:
    """Refresh managed action refs and return changed workflow paths."""
    releases = {a: latest_release(a, runner=runner) for a in MANAGED_ACTIONS}
    return [
        path
        for path in sorted(workflow_dir.glob("*.yml"))
        if update_workflow_refs(path, releases=releases)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    for path in update_github_actions():
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests — all 7 should pass**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
uv run pytest tests/test_update_github_actions.py -v
```

Expected: 7 passed.

- [ ] **Step 6: Run script live against the repo**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
uv run python scripts/update_github_actions.py
```

Expected: prints paths of any workflow files whose SHAs were updated, or no output if already current. Either is correct.

- [ ] **Step 7: Run full CI**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
make ci AI=1
```

Expected: green.

- [ ] **Step 8: Commit**

```bash
git -C /workspaces/ocr-container/pdomain-book-tools \
  add scripts/__init__.py scripts/update_github_actions.py tests/test_update_github_actions.py
git -C /workspaces/ocr-container/pdomain-book-tools \
  commit -m "feat(dep-refresh): add update_github_actions.py + tests"
```

---

## Task 3: `dep-refresh.yml` — reference workflow in pdomain-book-tools

The workflow is written once here with current pinned SHAs (from ci.yml), then
`update_github_actions.py` is run to normalise them. Task 4 copies this
normalised file to all other repos — so all 12 start identical.

**Files:**
- Create: `pdomain-book-tools/.github/workflows/dep-refresh.yml`

- [ ] **Step 1: Read current pinned SHAs from `ci.yml`**

```bash
grep 'uses: actions/checkout@\|uses: astral-sh/setup-uv@' \
  /workspaces/ocr-container/pdomain-book-tools/.github/workflows/ci.yml | head -2
```

Note the two full lines. Use the SHA portion (the 40-char hex after `@`) in the next step.

- [ ] **Step 2: Write `dep-refresh.yml`** (replace `<CHECKOUT_SHA>` and `<SETUPUV_SHA>` with values from step 1)

```yaml
name: dep-refresh

on:
  repository_dispatch:
    types: [dep-refresh]
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<CHECKOUT_SHA>

      - uses: astral-sh/setup-uv@<SETUPUV_SHA>
        with:
          version: "0.11.16"

      - name: Set up Python
        run: uv python install 3.12

      - name: Set up pnpm or npm (repos with a package.json)
        if: hashFiles('frontend/package.json') != '' || hashFiles('package.json') != ''
        run: corepack enable

      - name: Refresh GitHub Actions SHA pins
        run: uv run python scripts/update_github_actions.py
        env:
          GH_TOKEN: ${{ github.token }}

      - name: Upgrade all Python deps
        run: make upgrade-deps

      - name: Upgrade frontend npm deps (SPA repos)
        if: hashFiles('frontend/package.json') != ''
        run: pnpm update --dir frontend

      - name: Upgrade root npm deps
        if: hashFiles('package.json') != '' && hashFiles('frontend/package.json') == ''
        run: |
          if [ -f pnpm-lock.yaml ]; then pnpm update; else npm update; fi

      - name: Check for changes
        id: changes
        run: |
          git diff --quiet \
            && echo "changed=false" >> "$GITHUB_OUTPUT" \
            || echo "changed=true" >> "$GITHUB_OUTPUT"

      - name: Create branch, commit, and open PR
        if: steps.changes.outputs.changed == 'true'
        run: |
          BRANCH="dep-refresh/$(date +%Y-%m-%d)"
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git checkout -b "$BRANCH"
          git add -A
          git commit -m "chore: weekly dep refresh (actions pins + all deps)"
          git push origin "$BRANCH"
          gh pr create \
            --title "chore: weekly dep refresh" \
            --body "$(printf 'Automated weekly refresh:\n- GitHub Actions SHA pins\n- Python deps (uv lock --upgrade)\n- npm deps (pnpm/npm update)\n\nAuto-merge armed — merges when CI passes.')" \
            --base main \
            --head "$BRANCH" \
            --label dep-refresh
          gh pr merge --auto --rebase
        env:
          GH_TOKEN: ${{ github.token }}
```

- [ ] **Step 3: Run `update_github_actions.py` to normalise the SHAs in the new file**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
uv run python scripts/update_github_actions.py
```

Expected: prints `.github/workflows/dep-refresh.yml` (the SHA lines will have been updated to current values). All workflow files now have matching, current SHAs.

- [ ] **Step 4: Validate YAML**

```bash
python3 -c "
import yaml
yaml.safe_load(open('/workspaces/ocr-container/pdomain-book-tools/.github/workflows/dep-refresh.yml'))
print('ok')
"
```

Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git -C /workspaces/ocr-container/pdomain-book-tools \
  add .github/workflows/dep-refresh.yml .github/workflows/ci.yml
git -C /workspaces/ocr-container/pdomain-book-tools \
  commit -m "feat(dep-refresh): add dep-refresh.yml workflow"
```

---

## Task 4: Propagate to remaining 11 repos

Copy the two files from pdomain-book-tools to each of the 11 remaining repos.
The files are identical — `update_github_actions.py` will normalise any SHA
drift on the first real run. Dispatch one subagent per repo in parallel.

**Repos:** `pdomain-ocr-cli`, `pdomain-ops`, `pdomain-ocr-training`,
`pdomain-ocr-synth`, `pdomain-ui`, `pdomain-ocr-simple-gui`,
`pdomain-ocr-labeler-spa`, `pdomain-ocr-trainer-spa`, `pdomain-prep-for-pgdp`,
`pdomain-index-pip`, `pdomain-index-npm`.

Per-repo steps (substitute `<REPO>` with the repo name throughout):

**Files:**
- Create: `<REPO>/scripts/__init__.py` (if absent)
- Create: `<REPO>/scripts/update_github_actions.py`
- Create: `<REPO>/.github/workflows/dep-refresh.yml`

- [ ] **Step 1: Ensure `scripts/__init__.py` exists**

```bash
REPO=<REPO>
touch /workspaces/ocr-container/$REPO/scripts/__init__.py
```

- [ ] **Step 2: Copy both files from the reference**

```bash
SRC=/workspaces/ocr-container/pdomain-book-tools
DEST=/workspaces/ocr-container/<REPO>

cp "$SRC/scripts/update_github_actions.py" "$DEST/scripts/update_github_actions.py"
cp "$SRC/.github/workflows/dep-refresh.yml" "$DEST/.github/workflows/dep-refresh.yml"
```

- [ ] **Step 3: Verify files landed**

```bash
ls /workspaces/ocr-container/<REPO>/scripts/update_github_actions.py
ls /workspaces/ocr-container/<REPO>/.github/workflows/dep-refresh.yml
```

Expected: both paths exist.

- [ ] **Step 4: Run CI**

```bash
cd /workspaces/ocr-container/<REPO>
make ci AI=1
```

Expected: green. The new files add no test surface.

- [ ] **Step 5: Commit**

```bash
git -C /workspaces/ocr-container/<REPO> \
  add scripts/__init__.py scripts/update_github_actions.py \
      .github/workflows/dep-refresh.yml
git -C /workspaces/ocr-container/<REPO> \
  commit -m "feat(dep-refresh): add update_github_actions.py and dep-refresh workflow"
```

---

## Task 5: GitHub repo setup — labels, auto-merge, branch protection

Run once for all 12 repos. No code changes — only GitHub API calls.

```bash
REPOS=(
  pdomain-book-tools pdomain-ocr-cli pdomain-ops pdomain-ocr-training
  pdomain-ocr-synth pdomain-ui pdomain-ocr-simple-gui pdomain-ocr-labeler-spa
  pdomain-ocr-trainer-spa pdomain-prep-for-pgdp pdomain-index-pip pdomain-index-npm
)
```

- [ ] **Step 1: Create `dep-refresh` label in each repo**

```bash
for repo in "${REPOS[@]}"; do
  gh label create dep-refresh \
    --color "0075ca" \
    --description "Automated dependency refresh PR" \
    --repo "ConcaveTrillion/$repo" 2>/dev/null \
    && echo "created: $repo" \
    || echo "already exists (ok): $repo"
done
```

Expected: each repo prints "created" or "already exists (ok)".

- [ ] **Step 2: Enable "Allow auto-merge" on each repo**

```bash
for repo in "${REPOS[@]}"; do
  gh api "repos/ConcaveTrillion/$repo" \
    --method PATCH \
    -f allow_auto_merge=true \
    --silent \
    && echo "auto-merge enabled: $repo"
done
```

Expected: each repo prints the enabled message.

- [ ] **Step 3: Verify required CI status checks on `main`**

```bash
for repo in "${REPOS[@]}"; do
  count=$(gh api "repos/ConcaveTrillion/$repo/branches/main/protection" \
    2>/dev/null \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('required_status_checks',{}).get('contexts',[])))" \
    2>/dev/null || echo "0")
  if [[ "$count" == "0" ]]; then
    echo "WARNING: $repo — no required status checks. Set via GitHub UI: Settings → Branches → main."
  else
    echo "ok ($count checks): $repo"
  fi
done
```

For any repo that shows WARNING: navigate to `github.com/ConcaveTrillion/<repo>/settings/branches`, edit the `main` rule, and add the repo's existing CI job names (visible in `.github/workflows/ci.yml`) as required status checks.

---

## Task 6: Orchestrator workflow in `ocr-container-meta`

**Files:**
- Create: `ocr-container-meta/.github/workflows/dispatch-dep-refresh.yml`

- [ ] **Step 1: Create the workflow**

```yaml
name: dispatch-dep-refresh

on:
  schedule:
    - cron: '0 2 * * 0'   # Sunday 02:00 UTC
  workflow_dispatch:
    inputs:
      repo:
        description: 'Single repo name to refresh (omit for all)'
        required: false

jobs:
  dispatch:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        repo:
          - pdomain-book-tools
          - pdomain-ocr-cli
          - pdomain-ops
          - pdomain-ocr-training
          - pdomain-ocr-synth
          - pdomain-ui
          - pdomain-ocr-simple-gui
          - pdomain-ocr-labeler-spa
          - pdomain-ocr-trainer-spa
          - pdomain-prep-for-pgdp
          - pdomain-index-pip
          - pdomain-index-npm
    steps:
      - name: Dispatch dep-refresh
        if: inputs.repo == '' || inputs.repo == matrix.repo
        run: |
          gh api "repos/ConcaveTrillion/${{ matrix.repo }}/dispatches" \
            --method POST \
            -f event_type=dep-refresh
        env:
          GH_TOKEN: ${{ secrets.DISPATCH_PAT }}
```

- [ ] **Step 2: Validate YAML**

```bash
python3 -c "
import yaml
yaml.safe_load(open('/workspaces/ocr-container/ocr-container-meta/.github/workflows/dispatch-dep-refresh.yml'))
print('ok')
"
```

Expected: `ok`.

- [ ] **Step 3: Create `DISPATCH_PAT` secret**

Create a fine-grained PAT at `github.com/settings/tokens/new` with:
- **Resource owner:** ConcaveTrillion
- **Repository access:** Select the 12 pdomain repos explicitly
- **Permissions:** Actions → Read and write (allows `repository_dispatch`)

Then store it:

```bash
gh secret set DISPATCH_PAT \
  --repo ConcaveTrillion/ocr-container-meta \
  --body "$(cat)"   # paste the token then Ctrl-D
```

- [ ] **Step 4: Commit**

```bash
git -C /workspaces/ocr-container/ocr-container-meta \
  add .github/workflows/dispatch-dep-refresh.yml
git -C /workspaces/ocr-container/ocr-container-meta \
  commit -m "feat(dep-refresh): add dispatch-dep-refresh orchestrator"
```

---

## Task 7: Drift checks in `repo-hygiene-check.sh`

Extend the hygiene check with presence + content-match checks for the two dep-refresh files. The reference is always `pdomain-book-tools`.

**Files:**
- Modify: `scripts/repo-hygiene-check.sh`
- Modify: `scripts/tests/test-repo-hygiene-check.sh`

### Step 7.1: Write the failing test first

- [ ] **Step 1: Append a new test to `test-repo-hygiene-check.sh`**

Open the file and add before the final summary/exit lines:

```bash
# --- dep-refresh presence checks ---
test_dep_refresh_files_flagged_when_absent() {
  local repo
  repo=$(mktemp -d)
  mkdir -p "$repo/.github/workflows"
  result=$(bash "$SCRIPT" "$repo" --check --no-gh 2>&1)
  echo "$result" | grep -q "update_github_actions.py absent" \
    && echo "PASS: missing script flagged" \
    || { echo "FAIL: missing script not flagged"; FAILURES=$((FAILURES+1)); }
  echo "$result" | grep -q "dep-refresh.yml absent" \
    && echo "PASS: missing workflow flagged" \
    || { echo "FAIL: missing workflow not flagged"; FAILURES=$((FAILURES+1)); }
  rm -rf "$repo"
}
test_dep_refresh_files_flagged_when_absent
```

- [ ] **Step 2: Run the test suite — confirm the new tests fail**

```bash
bash /workspaces/ocr-container/scripts/tests/test-repo-hygiene-check.sh 2>&1 | tail -10
```

Expected: the two new assertions fail.

### Step 7.2: Add checks to `repo-hygiene-check.sh`

- [ ] **Step 3: Add the drift block after the existing presence checks section**

Find the line with `[[ -f "$REPO/mise.toml" ]]` and add the following block after the existing presence check group:

```bash
# --- dep-refresh file presence and content drift ---
BOOK_TOOLS_REF="/workspaces/ocr-container/pdomain-book-tools"

_check_dep_refresh_file() {
  local rel_path="$1"
  local full="$REPO/$rel_path"
  local ref="$BOOK_TOOLS_REF/$rel_path"
  if [[ -f "$full" ]]; then
    ok "$rel_path present"
    if [[ -f "$ref" && "$REPO" != "$BOOK_TOOLS_REF" ]]; then
      if diff -q "$full" "$ref" >/dev/null 2>&1; then
        ok "$rel_path matches reference"
      else
        drift "$rel_path differs from pdomain-book-tools reference"
      fi
    fi
  else
    drift "$rel_path absent"
  fi
}

_check_dep_refresh_file "scripts/update_github_actions.py"
_check_dep_refresh_file ".github/workflows/dep-refresh.yml"
```

- [ ] **Step 4: Run the full test suite — all tests should pass**

```bash
bash /workspaces/ocr-container/scripts/tests/test-repo-hygiene-check.sh 2>&1 | tail -15
```

Expected: all tests PASS, exit 0.

- [ ] **Step 5: Smoke-test against pdomain-book-tools**

```bash
bash /workspaces/ocr-container/scripts/repo-hygiene-check.sh \
  /workspaces/ocr-container/pdomain-book-tools --check --no-gh 2>&1 \
  | grep -E 'update_github_actions|dep-refresh'
```

Expected:
```
  ok: scripts/update_github_actions.py present
  ok: .github/workflows/dep-refresh.yml present
```

- [ ] **Step 6: Smoke-test against a repo that doesn't have the files yet (pdomain-ocr-synth before Task 4 runs)**

```bash
bash /workspaces/ocr-container/scripts/repo-hygiene-check.sh \
  /workspaces/ocr-container/pdomain-ocr-synth --check --no-gh 2>&1 \
  | grep -E 'update_github_actions|dep-refresh'
```

Expected:
```
  DRIFT: scripts/update_github_actions.py absent
  DRIFT: .github/workflows/dep-refresh.yml absent
```

- [ ] **Step 7: Commit**

```bash
git add scripts/repo-hygiene-check.sh scripts/tests/test-repo-hygiene-check.sh
git commit -m "feat(dep-refresh): add dep-refresh drift checks to repo-hygiene-check"
```

---

## Task 8: End-to-end smoke test

Verify the full flow before the first scheduled Sunday run.

- [ ] **Step 1: Push all commits to their remotes**

For each repo modified in Tasks 1–4 and for ocr-container-meta:

```bash
for repo in pdomain-index-npm pdomain-book-tools ocr-container-meta; do
  git -C /workspaces/ocr-container/$repo push origin main
done
```

Repeat for each repo from Task 4 that has been committed.

- [ ] **Step 2: Trigger a single-repo dispatch**

```bash
gh workflow run dispatch-dep-refresh.yml \
  --repo ConcaveTrillion/ocr-container-meta \
  -f repo=pdomain-book-tools
```

Expected: workflow queued in ocr-container-meta.

- [ ] **Step 3: Watch for the triggered dep-refresh run (allow ~60s for dispatch)**

```bash
sleep 60
gh run list \
  --repo pdomain/pdomain-book-tools \
  --workflow dep-refresh.yml \
  --limit 3
```

Expected: a run appears with status `in_progress` or `success`.

- [ ] **Step 4: If deps were already current — verify the "no changes" path**

```bash
gh run view \
  --repo pdomain/pdomain-book-tools \
  --workflow dep-refresh.yml \
  $(gh run list --repo pdomain/pdomain-book-tools --workflow dep-refresh.yml --limit 1 --json databaseId --jq '.[0].databaseId')
```

Expected: run succeeds; "Check for changes" step shows `changed=false` and no PR is created — OR a PR is created if deps were out of date.

- [ ] **Step 5: If a PR was created — verify auto-merge is armed**

```bash
gh pr list \
  --repo pdomain/pdomain-book-tools \
  --label dep-refresh \
  --json number,title,autoMergeRequest
```

Expected: PR is present with `autoMergeRequest` non-null (auto-merge is armed).

- [ ] **Step 6: Confirm the PR merges when CI passes**

Watch the PR in the GitHub UI or poll:

```bash
gh pr view \
  --repo pdomain/pdomain-book-tools \
  --json state,mergeStateStatus \
  $(gh pr list --repo pdomain/pdomain-book-tools --label dep-refresh --json number --jq '.[0].number')
```

Once CI passes, state transitions to `MERGED`. Fetch and verify:

```bash
git -C /workspaces/ocr-container/pdomain-book-tools fetch origin
git -C /workspaces/ocr-container/pdomain-book-tools log origin/main -3 --oneline
```

Expected: "chore: weekly dep refresh (actions pins + all deps)" appears at the tip of main.

---

## Final acceptance checklist

- [ ] `pdomain-index-npm` has `upgrade-deps` Makefile target
- [ ] All 12 repos have `scripts/__init__.py`, `scripts/update_github_actions.py`, `.github/workflows/dep-refresh.yml`
- [ ] `dep-refresh` label exists in all 12 repos
- [ ] "Allow auto-merge" enabled in all 12 repos
- [ ] All 12 repos have required CI status checks on `main`
- [ ] `dispatch-dep-refresh.yml` is live in `ocr-container-meta`
- [ ] `DISPATCH_PAT` secret is set in `ocr-container-meta`
- [ ] `repo-hygiene-check.sh` drift checks pass for all 12 repos
- [ ] End-to-end smoke test (Task 8) confirms the run completes and auto-merge fires
