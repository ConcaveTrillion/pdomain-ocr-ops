---
status: complete
---

# Code-review + style-cleanup — Plan 4: Workspace meta scripts + 6-repo rollout

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land Phases 6 and 7 of the v2 code-review/style spec. End state: four new workspace-meta scripts (`sync-conventions`, `check-sync-drift`, `check-sibling-drift`, `lint-conventions`) keep the cross-repo conventions block consistent across all repos with CONVENTIONS.md; two new dashboard panels surface sync-drift and sibling-drift; Phase 2/3/4/5 work from earlier plans is rolled out to the remaining 6 published pd-* repos (pd-png-optimizer skipped per spec Open Q #4).

**Architecture:** Phase 6 follows the spec's deterministic-vs-LLM split: byte-level sync-drift detection runs on every dashboard refresh (no token cost); sibling-drift comparison runs once per week with one Sonnet call (cents per week). Sync application is deterministic (regenerate marker block, commit, pd-push). The pre-commit `lint-conventions.py` checks rule-template structure and marker integrity, plus delegates to `check-sync-drift.py` to reject manual edits inside the cross-repo block. Phase 7 is per-repo bootstrap-then-arm: each repo gets a CONVENTIONS.md (via the existing extract-conventions.py from v2 Plan 2), the labels seeded (existing seed-labels.sh), the recurring:weekly chore filed, and ctask entries scheduled. CT reviews each draft before promotion.

**Tech Stack:** Python 3.11, Anthropic SDK (sibling-drift only), `gh` CLI, `pd-push`, pytest, ctask.

**Source spec:** `docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md`

**Depends on:**
- v2 Plan 1 (worktree retrofit) — done.
- v2 Plan 2 (CONVENTIONS.md bootstrap + /pr-review + detect+apply) — done. Workspace canonical CONVENTIONS.md exists; pdomain-book-tools CONVENTIONS.md exists.
- v2 Plan 3 (daily review-bot + weekly sweep-bot on pdomain-book-tools) — done. Both bots running cleanly for ≥1 week.

**Out of scope:**
- pd-png-optimizer. The repo's Rust core has different toolchain (cargo fmt, cargo clippy); style-sweep on Rust is deferred to a future iteration. The Python facade could in principle still get the lint-first work from v2 Plan 1, but in this plan we treat pd-png-optimizer as fully out of scope to avoid splitting it across plans.
- Future-bot calibration loops (read-only `/check-convention-drift` proposing demotions). Spec Open Q #3 leans read-only; no implementation.
- Cost ceiling per repo (Open Q #5). No v2 mechanism.
- Workspace-tooling repo for the canonical CONVENTIONS.md (Open Q #2). The canonical lives at `/workspaces/ocr-container/CONVENTIONS.md` from Plan 2; this plan does NOT relocate it. CT's queued task #2 ("Decide on the workspace meta repo for canonical CONVENTIONS.md") is independent — if CT later moves to `ConcaveTrillion/ocr-container-meta`, sync-conventions.py needs a one-line `WORKSPACE_CANON` path update. Document this as a known follow-up.

---

## Background context for the engineer

Read the spec sections **Conventions docs**, **Script vs LLM boundary**, and **Scripts (deterministic and one-shot LLM)** before starting. The four scripts in Phase 6 each have a section in the spec that defines their inputs, outputs, and idempotence requirements; mirror those exactly.

**Existing surfaces:**

- `scripts/extract-conventions.py` (v2 Plan 2) — bootstrap helper.
- `scripts/style-review-detect.py` / `scripts/style-review-apply.py` (v2 Plan 2).
- `scripts/style-review-orchestrator.sh` / `scripts/style-sweep-orchestrator.sh` (v2 Plan 3).
- `scripts/seed-labels.sh` (lifecycle Plan 1 + Plan 2 Phase-0 update + v2 Plan 3 update).
- `scripts/build-cost-dashboard.py` — already extended by lifecycle Plan 2 Task 7 (chain-state panel) and v2 Plan 3 Task 6 (style-bot-events panel). This plan adds two more.
- `pd-push` — workspace push helper.
- `/workspaces/ocr-container/CONVENTIONS.md` — workspace canonical (Plan 2 Task 3).
- `/workspaces/ocr-container/pdomain-book-tools/CONVENTIONS.md` — first per-repo (Plan 2 Task 4).

**Coordination notes:**
- Lifecycle Plan 2 Phase 5 (rollout of lifecycle skills to 6 repos) and v2 Plan 4 Phase 7 (rollout of CONVENTIONS.md + bots to 6 repos) cover the same 6 repos. Per the lifecycle Plan 2 amendment ("Coordination with v2 work"): run lifecycle Phase 5 first, then v2 Plan 4 Phase 7.
- Spec Open Q #4 (Rust on style-sweep): pd-png-optimizer skipped throughout. The published 6 repos are: pdomain-ocr-cli, pd-ocr-labeler, pdomain-ocr-labeler-spa, pdomain-ocr-synth, pd-ocr-trainer, pdomain-prep-for-pgdp.

**Marker-block contract:**

Every per-repo `CONVENTIONS.md` contains a marker-delimited block that
must byte-match the workspace canonical when regenerated:

```markdown
<!-- workspace-conventions:start -->
<contents identical to /workspaces/ocr-container/CONVENTIONS.md
 inside the same start/end markers there>
<!-- workspace-conventions:end -->
```

The repo-specific section follows below the markers and is freely
editable; only the marker block is sync-managed.

The workspace canonical itself does NOT have its own start/end markers.
The sync algorithm is: read the workspace file, take everything (or
take everything between `<!-- workspace-conventions:start -->` and
`<!-- workspace-conventions:end -->` if those markers exist in the
canonical too — handy for future-proofing). For v1 of sync, treat the
entire workspace canonical content as the synced block, wrapped in
markers when written into the per-repo file.

**Wait — that contradicts the spec.** Re-read spec lines 96-102: the
workspace canonical is what CT edits at the workspace root; the per-repo
file has marker-delimited block regenerated from the canonical. Two
options:
1. Workspace canonical is "the whole content"; sync wraps it in markers when writing.
2. Workspace canonical contains its own markers; sync extracts that block.

For implementation simplicity and reduced risk of including unrelated
workspace text (Plan 2 Task 3 wrote the workspace canonical directly,
no markers), go with **option 2**: the workspace canonical also uses
`<!-- workspace-conventions:start -->...end -->` markers around the
synced block. Anything outside those markers in the workspace canonical
is workspace-only context (not synced). This means CT's promotion of
the Plan 2 Task 3 draft to canonical must include adding markers if
they aren't there. This task plan flags that explicitly in Task 1.

---

## File structure (created or modified by this plan)

**Created:**

- `scripts/sync-conventions.py`
- `scripts/check-sync-drift.py`
- `scripts/check-sibling-drift.py`
- `scripts/lint-conventions.py`
- `tests/scripts/test_sync_conventions.py`
- `tests/scripts/test_check_sync_drift.py`
- `tests/scripts/test_check_sibling_drift.py`
- `tests/scripts/test_lint_conventions.py`
- `tests/fixtures/conventions/canonical-with-markers.md`
- `<repo>/CONVENTIONS.md` for each of pdomain-ocr-cli, pd-ocr-labeler, pdomain-ocr-labeler-spa, pdomain-ocr-synth, pd-ocr-trainer, pdomain-prep-for-pgdp (per-repo PRs).
- One `recurring:weekly` chore issue per the same 6 repos (`gh issue create`).

**Modified:**

- `/workspaces/ocr-container/CONVENTIONS.md` — add `<!-- workspace-conventions:start --> ... end -->` markers around the synced block (one-time fixup).
- `pdomain-book-tools/CONVENTIONS.md` — verify markers are correct after sync-conventions.py first runs.
- `scripts/build-cost-dashboard.py` — add `sync-drift` and `sibling-drift` panels.
- `tests/scripts/test_build_cost_dashboard.py` — extend.
- `.pre-commit-config.yaml` (workspace + each pd-* repo touched) — add `lint-conventions` hook.
- `Makefile` (workspace) — add `make sync-conventions` target.
- `ctask` config — add per-repo daily/weekly entries; add hourly `check-sibling-drift` (or weekly per cost preference).
- `docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md` — flip Status: Draft → Active when fully landed.

---

# Phase 6: Workspace meta scripts + dashboard panels

## Task 1: Add markers to the workspace canonical CONVENTIONS.md

**This is a one-time fixup before sync-conventions.py can run.** The
workspace canonical written in Plan 2 Task 3 may not have the
`<!-- workspace-conventions:start --> ... end -->` markers explicitly.
Adding them establishes which content is shared vs workspace-only.

- [ ] **Step 1: Inspect the canonical**

```bash
grep -n 'workspace-conventions:' /workspaces/ocr-container/CONVENTIONS.md \
  || echo "no markers — need to add them"
```

- [ ] **Step 2: Decide which content is shared**

Re-read `/workspaces/ocr-container/CONVENTIONS.md`. Decide which `## Rule:`
sections are workspace-wide (all pd-* repos) vs workspace-only (e.g.,
rules about workspace tooling that don't apply to per-repo code).

For most rules, the answer is "shared". Add markers:

```markdown
# Workspace conventions

(any preamble — workspace-only context, not synced)

<!-- workspace-conventions:start -->

## Rule: <first shared rule>
... (content)

## Rule: <second shared rule>
... (content)

(other shared rules)

<!-- workspace-conventions:end -->

(any trailing workspace-only sections — workspace-tooling rules,
references, footnotes — not synced)
```

- [ ] **Step 3: Commit the markers**

```bash
cd /workspaces/ocr-container
git add CONVENTIONS.md
git commit -m "feat(conventions): add workspace-conventions:start/end markers"
```

---

## Task 2: scripts/sync-conventions.py — propagate the canonical

**Files:**

- Create: `scripts/sync-conventions.py`
- Create: `tests/scripts/test_sync_conventions.py`
- Create: `tests/fixtures/conventions/canonical-with-markers.md` — fixture used by tests.

The script reads the workspace canonical's marker block, regenerates each
pd-* repo's marker block to match, commits if changed, and `pd-push`es.
Idempotent on no-change (skips repos whose block already matches).

- [ ] **Step 1: Write the fixture**

Save as `tests/fixtures/conventions/canonical-with-markers.md`:

```markdown
# Workspace conventions

Preamble (not synced).

<!-- workspace-conventions:start -->

## Rule: Don't restate code in comments

**The rule.** Don't write what-comments. Only write why-comments.

**Why.** Comments rot.

**Common high-confidence violations** (bot auto-fix candidates)
- One-line summary above a function definition.

**Common judgment-call violations** (bot flags, CT decides)
- Multi-line preamble mixing why with what.

<!-- workspace-conventions:end -->

Footnotes (not synced).
```

- [ ] **Step 2: Write the failing tests**

Save as `tests/scripts/test_sync_conventions.py`:

```python
"""Tests for scripts/sync-conventions.py."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/sync-conventions.py"
FIX = WORKSPACE / "tests/fixtures/conventions/canonical-with-markers.md"


def _mod():
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    spec = importlib.util.spec_from_file_location("sync_conventions", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_extract_block_from_canonical():
    m = _mod()
    block = m.extract_synced_block(FIX.read_text())
    assert "## Rule: Don't restate code in comments" in block
    assert "Preamble" not in block
    assert "Footnotes" not in block
    # The block does NOT include the start/end markers themselves;
    # those are added when wrapped into a per-repo file.
    assert "workspace-conventions:start" not in block
    assert "workspace-conventions:end" not in block


def test_regenerate_block_in_per_repo_file_replaces_existing():
    m = _mod()
    canonical = FIX.read_text()
    block = m.extract_synced_block(canonical)
    repo_existing = (
        "<!-- workspace-conventions:start -->\n"
        "OLD CONTENT\n"
        "<!-- workspace-conventions:end -->\n\n"
        "## Repo-specific rule\n"
    )
    new = m.regenerate_per_repo(repo_existing, block)
    assert "OLD CONTENT" not in new
    assert "Don't restate code in comments" in new
    assert "## Repo-specific rule" in new


def test_regenerate_is_idempotent():
    m = _mod()
    canonical = FIX.read_text()
    block = m.extract_synced_block(canonical)
    seed = m.regenerate_per_repo("", block)
    again = m.regenerate_per_repo(seed, block)
    assert seed == again


def test_regenerate_preserves_repo_specific_section_below_markers():
    m = _mod()
    block = m.extract_synced_block(FIX.read_text())
    repo_existing = (
        "<!-- workspace-conventions:start -->\n"
        "anything\n"
        "<!-- workspace-conventions:end -->\n\n"
        "## Rule: pdomain-book-tools-specific — never silently drop OCR words\n\n"
        "**The rule.** Don't drop. **Why.** Memory.\n"
    )
    new = m.regenerate_per_repo(repo_existing, block)
    assert "pdomain-book-tools-specific — never silently drop OCR words" in new
    assert "Don't drop" in new


def test_regenerate_creates_block_if_repo_file_lacks_markers():
    """A first-bootstrap per-repo CONVENTIONS.md without markers gets the
    block prepended; the existing repo content stays as the
    repo-specific section."""
    m = _mod()
    block = m.extract_synced_block(FIX.read_text())
    repo_existing = "## Rule: existing-repo-rule\n\n**The rule.** X\n"
    new = m.regenerate_per_repo(repo_existing, block)
    assert "<!-- workspace-conventions:start -->" in new
    assert "<!-- workspace-conventions:end -->" in new
    assert "existing-repo-rule" in new
```

- [ ] **Step 3: Run tests — confirm they fail**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_sync_conventions.py -v
```

Expected: FAIL.

- [ ] **Step 4: Implement the script**

Save as `scripts/sync-conventions.py`:

```python
#!/usr/bin/env python3
"""sync-conventions.py — propagate workspace canonical to each pd-* repo.

Reads /workspaces/ocr-container/CONVENTIONS.md (workspace canonical),
extracts the marker-delimited shared block, and regenerates each pd-*
repo's marker block to match. If the block changed, commits and
pd-pushes.

Idempotent: skips repos whose block already byte-matches.

Usage:
  scripts/sync-conventions.py                       # apply to all pd-* repos
  scripts/sync-conventions.py --confirm             # prompt-before-push
  scripts/sync-conventions.py --allow-branch=foo    # only branch-foo (otherwise default branch only)
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
WORKSPACE_CANON = WORKSPACE / "CONVENTIONS.md"
START = "<!-- workspace-conventions:start -->"
END = "<!-- workspace-conventions:end -->"

# Repos covered. pd-png-optimizer excluded per spec Open Q #4.
REPOS = (
    "pdomain-book-tools", "pdomain-ocr-cli", "pd-ocr-labeler", "pdomain-ocr-labeler-spa",
    "pdomain-ocr-synth", "pd-ocr-trainer", "pdomain-prep-for-pgdp",
)


def extract_synced_block(canonical_text: str) -> str:
    """Return the content between the start/end markers, stripped of the markers themselves."""
    if START not in canonical_text:
        raise ValueError(
            f"workspace canonical lacks {START}; run Plan-4 Task 1 fixup first"
        )
    s = canonical_text.index(START) + len(START)
    e = canonical_text.index(END)
    return canonical_text[s:e].strip("\n")


def regenerate_per_repo(repo_text: str, synced_block: str) -> str:
    """Regenerate the per-repo CONVENTIONS.md so its marker block matches the canonical."""
    new_block = f"{START}\n\n{synced_block}\n\n{END}"
    if START in repo_text and END in repo_text:
        # Replace existing block.
        before, _, rest = repo_text.partition(START)
        _, _, after = rest.partition(END)
        before = before.rstrip("\n")
        after = after.lstrip("\n")
        if before:
            return f"{before}\n\n{new_block}\n\n{after}"
        return f"{new_block}\n\n{after}"
    # No existing block: prepend the block, treating existing content as
    # the repo-specific section.
    if not repo_text.strip():
        return f"{new_block}\n"
    return f"{new_block}\n\n{repo_text.lstrip()}"


def _branch_name(repo_path: Path) -> str:
    r = subprocess.run(
        ["git", "-C", str(repo_path), "symbolic-ref", "--short", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    return r.stdout.strip()


def _default_branch(repo_path: Path) -> str:
    r = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "origin/HEAD"],
        capture_output=True, text=True, check=False,
    )
    return r.stdout.strip().split("/", 1)[-1] if r.returncode == 0 else "main"


def sync_one_repo(repo: str, *, synced_block: str, allow_branch: str | None,
                  confirm: bool) -> str:
    repo_path = WORKSPACE / repo
    target = repo_path / "CONVENTIONS.md"
    if not target.exists():
        return f"{repo}: SKIP (no CONVENTIONS.md yet)"

    current = target.read_text()
    new = regenerate_per_repo(current, synced_block)
    if current == new:
        return f"{repo}: ✓ already in sync"

    branch = _branch_name(repo_path)
    default = _default_branch(repo_path)
    if branch != default and (allow_branch is None or branch != allow_branch):
        return f"{repo}: SKIP (on branch {branch}; pass --allow-branch={branch})"

    if confirm:
        sys.stderr.write(f"{repo}: changes ready. Push? [y/N] ")
        if input().strip().lower() != "y":
            return f"{repo}: SKIP (user declined)"

    target.write_text(new)
    workspace_sha = subprocess.run(
        ["git", "-C", str(WORKSPACE), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    subprocess.run(["git", "-C", str(repo_path), "add", "CONVENTIONS.md"], check=True)
    subprocess.run(
        ["git", "-C", str(repo_path), "commit", "-m",
         f"chore: sync cross-repo conventions to {workspace_sha}"],
        check=True,
    )
    subprocess.run(
        [str(WORKSPACE / "pd-push")], cwd=str(repo_path), check=True,
    )
    return f"{repo}: ✓ synced + pushed"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--confirm", action="store_true",
                   help="prompt before pushing each repo")
    p.add_argument("--allow-branch", default=None,
                   help="permit pushing this non-default branch")
    p.add_argument("--repos", nargs="+", default=list(REPOS))
    args = p.parse_args()

    # Set bots-paused for the duration so sync-conventions doesn't
    # interleave with a bot run.
    pause = Path("/srv/bot-workspaces/.state/bots-paused")
    pause_existed = pause.exists()
    if not pause_existed:
        pause.parent.mkdir(parents=True, exist_ok=True)
        pause.touch()

    try:
        canonical = WORKSPACE_CANON.read_text()
        block = extract_synced_block(canonical)
        for repo in args.repos:
            print(sync_one_repo(repo, synced_block=block,
                                allow_branch=args.allow_branch,
                                confirm=args.confirm))
    finally:
        if not pause_existed:
            try:
                pause.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    main()
```

```bash
chmod +x /workspaces/ocr-container/scripts/sync-conventions.py
```

- [ ] **Step 5: Run tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_sync_conventions.py -v
```

Expected: 5 tests pass.

- [ ] **Step 6: Add `make sync-conventions` target**

Edit the workspace `Makefile`. If a Makefile exists, add a target:

```makefile
.PHONY: sync-conventions
sync-conventions:
	python3 scripts/sync-conventions.py
```

If no workspace Makefile, skip this step (tests still cover the script).

- [ ] **Step 7: Smoke-run against pdomain-book-tools (which already has CONVENTIONS.md)**

```bash
cd /workspaces/ocr-container
python3 scripts/sync-conventions.py --repos pdomain-book-tools
```

Expected: either `✓ already in sync` (markers consistent) or
`✓ synced + pushed` (markers needed updating). If it pushes, inspect
the resulting commit on pdomain-book-tools.

- [ ] **Step 8: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/sync-conventions.py tests/scripts/test_sync_conventions.py \
        tests/fixtures/conventions/canonical-with-markers.md Makefile 2>/dev/null || true
git commit -m "feat(sync-conventions): propagate workspace canonical to per-repo blocks"
```

---

## Task 3: scripts/check-sync-drift.py — dashboard input

**Files:**

- Create: `scripts/check-sync-drift.py`
- Create: `tests/scripts/test_check_sync_drift.py`

Reads each pd-* repo's CONVENTIONS.md (via `gh api repos/.../contents/`),
extracts the marker block, byte-compares against a fresh regeneration
from the workspace canonical, and writes `sync-drift.json`. No LLM,
no commits, no pushes — just observation.

- [ ] **Step 1: Write the failing tests**

Save as `tests/scripts/test_check_sync_drift.py`:

```python
"""Tests for scripts/check-sync-drift.py."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/check-sync-drift.py"


def _mod():
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    spec = importlib.util.spec_from_file_location("check_sync_drift", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FakeGh:
    def __init__(self, files: dict):
        # files: {repo_basename: file_text}
        self.files = dict(files)

    def fetch_conventions(self, repo: str) -> str | None:
        basename = repo.rsplit("/", 1)[-1]
        return self.files.get(basename)


def test_reports_in_sync_when_block_matches(tmp_path):
    m = _mod()
    block = "<!-- workspace-conventions:start -->\nA\n<!-- workspace-conventions:end -->"
    canonical_text = f"# canon\n\n{block}\n"
    repo_text = f"{block}\n\n## Repo: rule\n"
    gh = FakeGh({"pdomain-book-tools": repo_text})
    result = m.check_repos(["pdomain-book-tools"], canonical_text=canonical_text, gh=gh)
    assert result["pdomain-book-tools"]["status"] == "in-sync"


def test_reports_drift_when_block_diverges():
    m = _mod()
    canonical_text = ("# canon\n\n"
        "<!-- workspace-conventions:start -->\nNEW\n<!-- workspace-conventions:end -->\n")
    repo_text = ("<!-- workspace-conventions:start -->\nOLD\n<!-- workspace-conventions:end -->\n")
    gh = FakeGh({"pdomain-book-tools": repo_text})
    result = m.check_repos(["pdomain-book-tools"], canonical_text=canonical_text, gh=gh)
    assert result["pdomain-book-tools"]["status"] == "drifted"
    assert "OLD" in result["pdomain-book-tools"]["actual_block"]
    assert "NEW" in result["pdomain-book-tools"]["expected_block"]


def test_reports_missing_when_no_repo_file():
    m = _mod()
    canonical_text = ("<!-- workspace-conventions:start -->\nx\n<!-- workspace-conventions:end -->")
    gh = FakeGh({})  # no file for pdomain-book-tools
    result = m.check_repos(["pdomain-book-tools"], canonical_text=canonical_text, gh=gh)
    assert result["pdomain-book-tools"]["status"] == "missing"


def test_writes_json_output(tmp_path):
    m = _mod()
    out = tmp_path / "sync-drift.json"
    canonical_text = ("<!-- workspace-conventions:start -->\nA\n<!-- workspace-conventions:end -->")
    gh = FakeGh({"pdomain-ocr-cli": canonical_text})  # in sync
    m.write_report(["pdomain-ocr-cli"], canonical_text=canonical_text, gh=gh, out=out)
    obj = json.loads(out.read_text())
    assert "pdomain-ocr-cli" in obj
```

- [ ] **Step 2: Implement the script**

Save as `scripts/check-sync-drift.py`:

```python
#!/usr/bin/env python3
"""check-sync-drift.py — observe per-repo sync drift; write JSON for dashboard.

For each pd-* repo, fetches CONVENTIONS.md via `gh api`, extracts the
marker block, byte-compares against a fresh extract from the workspace
canonical. Writes $SHIP_ISSUE_MEMORY_DIR/sync-drift.json.

Idempotent. Cheap. No LLM. Safe to call from every dashboard refresh.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
WORKSPACE_CANON = WORKSPACE / "CONVENTIONS.md"
START = "<!-- workspace-conventions:start -->"
END = "<!-- workspace-conventions:end -->"
DEFAULT_OUT = Path(os.environ.get(
    "SHIP_ISSUE_MEMORY_DIR",
    "/home/vscode/.claude/agent-memory/ship-issue",
)) / "sync-drift.json"

REPOS = (
    "pdomain-book-tools", "pdomain-ocr-cli", "pd-ocr-labeler", "pdomain-ocr-labeler-spa",
    "pdomain-ocr-synth", "pd-ocr-trainer", "pdomain-prep-for-pgdp",
)


def _extract_block(text: str) -> str | None:
    if START not in text or END not in text:
        return None
    s = text.index(START) + len(START)
    e = text.index(END)
    return text[s:e].strip("\n")


class GhApi:
    def fetch_conventions(self, repo: str) -> str | None:
        try:
            r = subprocess.run(
                ["gh", "api", f"/repos/{repo}/contents/CONVENTIONS.md",
                 "--jq", ".content"],
                capture_output=True, text=True, check=True, timeout=30,
            )
            import base64
            return base64.b64decode(r.stdout.strip()).decode("utf-8", errors="replace")
        except subprocess.CalledProcessError:
            return None


def check_repos(basenames: list[str], *, canonical_text: str, gh) -> dict:
    canon_block = _extract_block(canonical_text) or ""
    out: dict = {}
    for basename in basenames:
        repo_full = f"ConcaveTrillion/{basename}"
        repo_text = gh.fetch_conventions(repo_full)
        if repo_text is None:
            out[basename] = {"status": "missing"}
            continue
        repo_block = _extract_block(repo_text)
        if repo_block is None:
            out[basename] = {"status": "no-markers", "actual_block": None,
                             "expected_block": canon_block}
            continue
        if repo_block == canon_block:
            out[basename] = {"status": "in-sync"}
        else:
            out[basename] = {
                "status": "drifted",
                "actual_block": repo_block,
                "expected_block": canon_block,
            }
    return out


def write_report(basenames, *, canonical_text, gh, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    obj = check_repos(basenames, canonical_text=canonical_text, gh=gh)
    out.write_text(json.dumps(obj, indent=2))
    return obj


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repos", nargs="+", default=list(REPOS))
    p.add_argument("--out", default=str(DEFAULT_OUT))
    args = p.parse_args()

    write_report(
        args.repos, canonical_text=WORKSPACE_CANON.read_text(),
        gh=GhApi(), out=Path(args.out),
    )


if __name__ == "__main__":
    main()
```

```bash
chmod +x /workspaces/ocr-container/scripts/check-sync-drift.py
```

- [ ] **Step 3: Run tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_check_sync_drift.py -v
```

Expected: 4 tests pass.

- [ ] **Step 4: Smoke-run**

```bash
SHIP_ISSUE_MEMORY_DIR=/tmp/sm /workspaces/ocr-container/scripts/check-sync-drift.py
cat /tmp/sm/sync-drift.json
```

Expected: a JSON object with one key per pd-* repo. pdomain-book-tools may
report `in-sync` or `drifted` depending on the previous task's run;
the other six repos report `missing` (rollout in Phase 7).

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/check-sync-drift.py tests/scripts/test_check_sync_drift.py
git commit -m "feat(check-sync-drift): byte-compare per-repo marker block to canonical"
```

---

## Task 4: scripts/check-sibling-drift.py — weekly LLM compare

**Files:**

- Create: `scripts/check-sibling-drift.py`
- Create: `tests/scripts/test_check_sibling_drift.py`

Pulls each repo's *Repo-specific* section (the part below the marker
block), feeds them to one Sonnet call, and writes
`sibling-drift.json` with candidate-consolidation pairs.

- [ ] **Step 1: Write the failing tests**

Save as `tests/scripts/test_check_sibling_drift.py`:

```python
"""Tests for scripts/check-sibling-drift.py."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/check-sibling-drift.py"


def _mod():
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    spec = importlib.util.spec_from_file_location("check_sibling_drift", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FakeAnthropic:
    def __init__(self, response_json: str = '{"pairs": []}'):
        self.calls = []
        self.messages = MagicMock()
        self.messages.create = self._create
        self.response_json = response_json

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        resp = MagicMock()
        resp.content = [MagicMock(text=self.response_json)]
        return resp


def test_extract_repo_specific_section_from_text():
    m = _mod()
    text = (
        "<!-- workspace-conventions:start -->\nshared\n<!-- workspace-conventions:end -->\n\n"
        "## Rule: repo-specific A\n\n**The rule.** A\n"
    )
    out = m.extract_repo_specific(text)
    assert "repo-specific A" in out
    assert "shared" not in out


def test_compare_calls_anthropic_once_with_all_repos():
    m = _mod()
    fake = FakeAnthropic(response_json='{"pairs": [{"repo_a": "x", "repo_b": "y", "rule_a": "...", "rule_b": "...", "concern": "naming"}]}')
    sections = {
        "pdomain-book-tools": "## Rule: foo\n",
        "pdomain-ocr-cli": "## Rule: bar\n",
    }
    out = m.compare(client=fake, sections=sections)
    assert len(fake.calls) == 1
    assert "pairs" in out


def test_returns_empty_pairs_when_no_overlap_found():
    m = _mod()
    fake = FakeAnthropic(response_json='{"pairs": []}')
    out = m.compare(client=fake, sections={"a": "...", "b": "..."})
    assert out["pairs"] == []
```

- [ ] **Step 2: Implement the script**

Save as `scripts/check-sibling-drift.py`:

```python
#!/usr/bin/env python3
"""check-sibling-drift.py — weekly cross-repo conventions comparison.

One Sonnet call per week. Reads each pd-* repo's CONVENTIONS.md
Repo-specific section (below the markers), asks the LLM for pairs of
rules across repos that overlap in concern but differ in wording.
Writes $SHIP_ISSUE_MEMORY_DIR/sibling-drift.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
END = "<!-- workspace-conventions:end -->"
DEFAULT_OUT = Path(os.environ.get(
    "SHIP_ISSUE_MEMORY_DIR",
    "/home/vscode/.claude/agent-memory/ship-issue",
)) / "sibling-drift.json"
MODEL = "claude-sonnet-4-6"

REPOS = (
    "pdomain-book-tools", "pdomain-ocr-cli", "pd-ocr-labeler", "pdomain-ocr-labeler-spa",
    "pdomain-ocr-synth", "pd-ocr-trainer", "pdomain-prep-for-pgdp",
)


def extract_repo_specific(text: str) -> str:
    """Return everything after the workspace-conventions:end marker, or the whole text if no marker."""
    if END not in text:
        return text
    return text.split(END, 1)[1].lstrip("\n")


def _gather_sections(repos: list[str]) -> dict:
    out: dict = {}
    for r in repos:
        target = WORKSPACE / r / "CONVENTIONS.md"
        if not target.exists():
            continue
        section = extract_repo_specific(target.read_text()).strip()
        if section:
            out[r] = section
    return out


def compare(*, client, sections: dict) -> dict:
    """One Sonnet call. Returns {"pairs": [...]}."""
    if not sections or len(sections) < 2:
        return {"pairs": []}
    body = "\n\n".join(
        f"=== {repo} ===\n{section}" for repo, section in sorted(sections.items())
    )
    resp = client.messages.create(
        model=MODEL, max_tokens=4000,
        system=[{
            "type": "text",
            "text": (
                "You compare repo-specific conventions across sibling Python "
                "repos. Return JSON with a `pairs` array; each pair has "
                "repo_a, repo_b, rule_a (the rule statement), rule_b, "
                "concern (one or two words: naming/style/error-handling/etc). "
                "Include a pair only if the two rules ADDRESS the same "
                "concern but are worded differently in a way that would "
                "be confusing to a developer who works in both repos. "
                "Skip pairs that are merely different rules about "
                "different concerns. Output JSON only, no commentary."
            ),
        }],
        messages=[{"role": "user", "content": body}],
    )
    s = resp.content[0].text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1]
        if s.endswith("```"):
            s = s.rsplit("```", 1)[0]
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return {"pairs": []}


def _make_client():
    import anthropic
    return anthropic.Anthropic()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(DEFAULT_OUT))
    p.add_argument("--repos", nargs="+", default=list(REPOS))
    args = p.parse_args()

    sections = _gather_sections(args.repos)
    out = compare(client=_make_client(), sections=sections)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
```

```bash
chmod +x /workspaces/ocr-container/scripts/check-sibling-drift.py
```

- [ ] **Step 3: Run tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_check_sibling_drift.py -v
```

Expected: 3 tests pass.

- [ ] **Step 4: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/check-sibling-drift.py tests/scripts/test_check_sibling_drift.py
git commit -m "feat(check-sibling-drift): weekly LLM cross-repo compare → sibling-drift.json"
```

---

## Task 5: scripts/lint-conventions.py — pre-commit format check

**Files:**

- Create: `scripts/lint-conventions.py`
- Create: `tests/scripts/test_lint_conventions.py`

The hook runs at workspace pre-commit + each pd-* repo pre-commit. It
verifies:
1. Each `## Rule:` heading has the four expected sub-sections.
2. Marker integrity (in per-repo files, the start/end markers are present and well-formed).
3. The cross-repo block in a per-repo file matches the canonical (delegates to check-sync-drift's logic).

- [ ] **Step 1: Write the failing tests**

Save as `tests/scripts/test_lint_conventions.py`:

```python
"""Tests for scripts/lint-conventions.py."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/lint-conventions.py"
FIX = WORKSPACE / "tests/fixtures/conventions"


def _run(*args):
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        capture_output=True, text=True,
    )


def test_passes_on_canonical_with_markers():
    r = _run(str(FIX / "canonical-with-markers.md"))
    assert r.returncode == 0, r.stderr


def test_fails_on_missing_markers_in_per_repo_mode():
    r = _run("--per-repo", str(FIX / "malformed-no-markers.md"))
    assert r.returncode != 0
    assert "marker" in (r.stderr + r.stdout).lower()


def test_passes_on_no_markers_in_workspace_mode():
    """A workspace-canonical file that lacks markers is allowed (markers
    are only required in per-repo files; workspace-canon may use them
    optionally to scope the synced block)."""
    r = _run("--workspace", str(FIX / "malformed-no-markers.md"))
    # Workspace mode only checks rule template, not markers.
    # That fixture happens to have valid rule headings, so it passes.
    assert r.returncode == 0, r.stderr


def test_fails_on_malformed_rule_template():
    r = _run(str(FIX / "malformed-bad-rule-template.md"))
    assert r.returncode != 0
    assert "rule" in (r.stderr + r.stdout).lower()
```

- [ ] **Step 2: Implement the script**

Save as `scripts/lint-conventions.py`:

```python
#!/usr/bin/env python3
"""lint-conventions.py — pre-commit format check on CONVENTIONS.md.

Modes:
  default        : auto-detect (per-repo if file is named exactly
                   "CONVENTIONS.md" inside a pd-*/, workspace if it's
                   /workspaces/ocr-container/CONVENTIONS.md)
  --per-repo     : strict per-repo checks (markers required)
  --workspace    : workspace-canonical checks (markers optional)

Per-rule heading format:
  ## Rule: <statement>

  **The rule.** ...

  **Why.** ...

  **Common high-confidence violations** (bot auto-fix candidates)
  - ...

  **Common judgment-call violations** (bot flags, CT decides)
  - ...
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
START = "<!-- workspace-conventions:start -->"
END = "<!-- workspace-conventions:end -->"

_RULE_HEADER = re.compile(r"^## Rule: ", re.MULTILINE)
_REQUIRED_BLOCKS = (
    re.compile(r"\*\*The rule\.\*\*"),
    re.compile(r"\*\*Why\.\*\*"),
    re.compile(r"\*\*Common high-confidence violations\*\*"),
    re.compile(r"\*\*Common judgment-call violations\*\*"),
)


def _extract_rules(text: str) -> list[tuple[int, str]]:
    """Return (line_number, body) for each rule in the file."""
    out = []
    matches = list(_RULE_HEADER.finditer(text))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        line = text[: m.start()].count("\n") + 1
        out.append((line, text[start:end]))
    return out


def check_rule_template(text: str, *, label: str) -> list[str]:
    errors = []
    for line, body in _extract_rules(text):
        for rx in _REQUIRED_BLOCKS:
            if not rx.search(body):
                errors.append(
                    f"{label}:{line}: rule missing sub-section matching {rx.pattern}"
                )
                break  # one error per rule is enough
    return errors


def check_markers(text: str, *, label: str) -> list[str]:
    errors = []
    if START not in text:
        errors.append(f"{label}: missing {START}")
    if END not in text:
        errors.append(f"{label}: missing {END}")
    if START in text and END in text:
        if text.index(END) < text.index(START):
            errors.append(f"{label}: markers out of order (end before start)")
    return errors


def auto_mode_for(path: Path) -> str:
    """Decide per-repo vs workspace based on path."""
    try:
        rel = path.resolve().relative_to(WORKSPACE.resolve())
    except ValueError:
        return "workspace"
    parts = rel.parts
    if len(parts) >= 2 and parts[0].startswith("pd-") and parts[-1] == "CONVENTIONS.md":
        return "per-repo"
    return "workspace"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("paths", nargs="+")
    p.add_argument("--per-repo", action="store_true")
    p.add_argument("--workspace", action="store_true")
    args = p.parse_args()

    if args.per_repo and args.workspace:
        sys.exit("--per-repo and --workspace are exclusive")

    rc = 0
    for path_str in args.paths:
        path = Path(path_str)
        text = path.read_text()
        mode = "per-repo" if args.per_repo else \
               "workspace" if args.workspace else \
               auto_mode_for(path)
        errors = check_rule_template(text, label=str(path))
        if mode == "per-repo":
            errors += check_markers(text, label=str(path))
        for e in errors:
            sys.stderr.write(e + "\n")
        if errors:
            rc = 1
    sys.exit(rc)


if __name__ == "__main__":
    main()
```

```bash
chmod +x /workspaces/ocr-container/scripts/lint-conventions.py
```

- [ ] **Step 3: Run tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_lint_conventions.py -v
```

Expected: 4 tests pass.

- [ ] **Step 4: Wire into workspace pre-commit**

Edit `/workspaces/ocr-container/.pre-commit-config.yaml`. Append a
local hook:

```yaml
- repo: local
  hooks:
    - id: lint-conventions
      name: lint CONVENTIONS.md
      description: Verify rule-template structure + marker integrity in CONVENTIONS.md files.
      entry: python3 scripts/lint-conventions.py
      language: system
      files: '(?:^|/)CONVENTIONS\.md$'
```

- [ ] **Step 5: Smoke-test**

```bash
cd /workspaces/ocr-container
pre-commit run lint-conventions --all-files
```

Expected: passes (workspace canonical + pdomain-book-tools per-repo are
both well-formed at this stage).

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/lint-conventions.py tests/scripts/test_lint_conventions.py \
        .pre-commit-config.yaml
git commit -m "feat(lint-conventions): pre-commit format check (rule template + markers)"
```

---

## Task 6: Add sync-drift + sibling-drift dashboard panels

**Files:**

- Modify: `scripts/build-cost-dashboard.py` — add two `render_*_panel` functions and two placeholders.
- Modify: `tests/scripts/test_build_cost_dashboard.py` — extend tests.

Both panels are deterministic JSON-to-HTML renderers — no LLM in the
dashboard build itself.

- [ ] **Step 1: Write the failing tests**

Add to `tests/scripts/test_build_cost_dashboard.py`:

```python
def test_sync_drift_panel_renders_in_sync_repos():
    import sys
    sys.path.insert(0, "/workspaces/ocr-container/scripts")
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_cost_dashboard",
        "/workspaces/ocr-container/scripts/build-cost-dashboard.py",
    )
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    drift = {"pdomain-book-tools": {"status": "in-sync"},
             "pdomain-ocr-cli": {"status": "drifted",
                            "actual_block": "OLD",
                            "expected_block": "NEW"}}
    html = m.render_sync_drift_panel(drift)
    assert "pdomain-book-tools" in html
    assert "in-sync" in html
    assert "pdomain-ocr-cli" in html
    assert "drifted" in html or "drift" in html.lower()


def test_sync_drift_panel_empty_state():
    import sys
    sys.path.insert(0, "/workspaces/ocr-container/scripts")
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_cost_dashboard",
        "/workspaces/ocr-container/scripts/build-cost-dashboard.py",
    )
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    html = m.render_sync_drift_panel({})
    assert "no" in html.lower() or "empty" in html.lower()


def test_sibling_drift_panel_lists_pairs():
    import sys
    sys.path.insert(0, "/workspaces/ocr-container/scripts")
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_cost_dashboard",
        "/workspaces/ocr-container/scripts/build-cost-dashboard.py",
    )
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    pairs = {"pairs": [
        {"repo_a": "pdomain-ocr-cli", "repo_b": "pdomain-ocr-synth",
         "rule_a": "no print()", "rule_b": "no print()",
         "concern": "logging"},
    ]}
    html = m.render_sibling_drift_panel(pairs)
    assert "pdomain-ocr-cli" in html
    assert "pdomain-ocr-synth" in html
    assert "logging" in html
```

- [ ] **Step 2: Implement the renderers**

Edit `scripts/build-cost-dashboard.py`. Add two functions next to the
existing `render_chain_state_panel` and `render_style_bot_events_panel`:

```python
def render_sync_drift_panel(drift: dict) -> str:
    if not drift:
        return "<p class='sync-drift empty'>No sync-drift data yet.</p>"
    rows = ["<table class='sync-drift'><tr><th>Repo</th><th>Status</th><th>Diff</th></tr>"]
    for repo in sorted(drift):
        d = drift[repo]
        status = d.get("status", "unknown")
        cls = {"in-sync": "ok", "drifted": "warn",
               "missing": "warn", "no-markers": "warn"}.get(status, "")
        diff_cell = ""
        if status == "drifted":
            actual = (d.get("actual_block", "") or "")[:80].replace("\n", "↵ ")
            expected = (d.get("expected_block", "") or "")[:80].replace("\n", "↵ ")
            diff_cell = f"<code>actual:</code> {actual}<br/><code>canon:</code> {expected}"
        rows.append(f"<tr class='{cls}'><th>{repo}</th><td>{status}</td><td>{diff_cell}</td></tr>")
    rows.append("</table>")
    return "".join(rows)


def render_sibling_drift_panel(doc: dict) -> str:
    pairs = (doc or {}).get("pairs", [])
    if not pairs:
        return "<p class='sibling-drift empty'>No sibling-drift candidates this week.</p>"
    rows = ["<table class='sibling-drift'>"
            "<tr><th>Concern</th><th>Repo A</th><th>Rule A</th><th>Repo B</th><th>Rule B</th></tr>"]
    for p in pairs:
        rows.append(
            f"<tr><td>{p.get('concern','')}</td>"
            f"<td>{p.get('repo_a','')}</td><td>{p.get('rule_a','')[:80]}</td>"
            f"<td>{p.get('repo_b','')}</td><td>{p.get('rule_b','')[:80]}</td></tr>"
        )
    rows.append("</table>")
    return "".join(rows)
```

Add helpers at the bottom:

```python
def _load_sync_drift() -> dict:
    p = Path(os.environ.get("SHIP_ISSUE_MEMORY_DIR",
        "/home/vscode/.claude/agent-memory/ship-issue")) / "sync-drift.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _load_sibling_drift() -> dict:
    p = Path(os.environ.get("SHIP_ISSUE_MEMORY_DIR",
        "/home/vscode/.claude/agent-memory/ship-issue")) / "sibling-drift.json"
    return json.loads(p.read_text()) if p.exists() else {}
```

In the HTML template, add two placeholders: `{sync_drift_panel}` and
`{sibling_drift_panel}`. Add CSS for `.sync-drift .ok`, `.sync-drift .warn`,
`.sibling-drift`.

In `main()`'s `.format(...)` call, add:
```python
sync_drift_panel=render_sync_drift_panel(_load_sync_drift()),
sibling_drift_panel=render_sibling_drift_panel(_load_sibling_drift()),
```

- [ ] **Step 3: Run tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_build_cost_dashboard.py -v
```

Expected: all tests pass (including 3 new ones).

- [ ] **Step 4: Smoke-render the dashboard**

```bash
SHIP_ISSUE_MEMORY_DIR=/tmp/sm \
  /workspaces/ocr-container/scripts/check-sync-drift.py
SHIP_ISSUE_MEMORY_DIR=/tmp/sm DASHBOARD_SKIP_KANBAN=1 DASHBOARD_SKIP_CHAIN=1 \
  python3 /workspaces/ocr-container/scripts/build-cost-dashboard.py
ls -la /tmp/sm/cost-dashboard.html
```

Expected: dashboard renders; sync-drift panel shows real data.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/build-cost-dashboard.py tests/scripts/test_build_cost_dashboard.py
git commit -m "feat(dashboard): add sync-drift + sibling-drift panels"
```

---

## Task 7: Schedule sync-drift + sibling-drift in ctask

**Files:**

- Modify: ctask config.

- [ ] **Step 1: Add sync-drift hourly entry**

Mirroring the existing dashboard refresh:

```bash
/workspaces/ocr-container/ctask add \
  --name check-sync-drift \
  --cmd "python3 /workspaces/ocr-container/scripts/check-sync-drift.py" \
  --schedule "50 * * * *"
```

(50 past the hour, just before the dashboard's :55 spec-chain run from
lifecycle Plan 2 Task 8 and the dashboard's top-of-hour refresh.)

- [ ] **Step 2: Add sibling-drift weekly entry**

Once a week:

```bash
/workspaces/ocr-container/ctask add \
  --name check-sibling-drift \
  --cmd "python3 /workspaces/ocr-container/scripts/check-sibling-drift.py" \
  --schedule "30 5 * * 0"
```

(Sundays at 05:30 UTC, after the daily review-bot's 03:00 run.)

- [ ] **Step 3: Smoke-fire each once**

```bash
/workspaces/ocr-container/ctask run check-sync-drift
/workspaces/ocr-container/ctask run check-sibling-drift
```

- [ ] **Step 4: Commit ctask config**

```bash
cd /workspaces/ocr-container
git add <ctask-config-file>
git commit -m "chore(ctask): schedule sync-drift hourly + sibling-drift weekly"
```

---

# Phase 7: Rollout to remaining 6 published repos

This phase is mostly a CT-driven manual handback. For each of the 6
published repos (pd-png-optimizer skipped), CT:
1. Runs `extract-conventions.py <repo>` to get a draft.
2. Reviews + edits + promotes to `<repo>/CONVENTIONS.md`.
3. Confirms the lifecycle skills work on the repo (lifecycle Plan 2 Phase 5 prerequisite).
4. Arms the daily + weekly bots via ctask + label.

The repo agents do the bulk of the file-level work; the parent session
coordinates.

## Task 8: Pre-flight — confirm lifecycle Plan 2 Phase 5 done first

**Manual handback** — verify CT has run lifecycle Plan 2 Phase 5
(rolled out the lifecycle skills to the same 6 repos) BEFORE starting
v2 Plan 4 Phase 7. Per the lifecycle Plan 2 amendment ("Coordination
with v2 work"): Phase 5 first, then this.

- [ ] **Step 1: Verify**

For each of the 6 repos, confirm:
- The seed-labels.sh has been run (check for `kind:feature-request` etc.).
- At least one feature-request has been driven through the lifecycle (smoke validation).

```bash
for r in pdomain-ocr-cli pd-ocr-labeler pdomain-ocr-labeler-spa \
         pdomain-ocr-synth pd-ocr-trainer pdomain-prep-for-pgdp; do
  echo "=== $r ==="
  gh label list -R "ConcaveTrillion/$r" --limit 200 --json name \
    --jq '.[] | select(.name | test("kind:feature-request|bot:ship-issue-ready"))'
done
```

If any repo is missing labels, run lifecycle Plan 2 Phase 5 for that
repo first.

---

## Task 9: Bootstrap CONVENTIONS.md on each repo

**Manual handback** — CT runs each per-repo extraction, reviews the
draft, promotes to canonical.

- [ ] **Step 1: For each repo `R` in {pdomain-ocr-cli, pd-ocr-labeler, pdomain-ocr-labeler-spa, pdomain-ocr-synth, pd-ocr-trainer, pdomain-prep-for-pgdp}**

  - [ ] Run extraction:
    ```bash
    cd /workspaces/ocr-container
    python3 scripts/extract-conventions.py "$R"
    ```
  - [ ] Inspect the draft at `<R>/CONVENTIONS.md.draft`.
  - [ ] Review + edit (5-15 minutes per repo). Drop redundant rules; keep the marker block intact (will be sync-managed).
  - [ ] Promote: `mv $R/CONVENTIONS.md.draft $R/CONVENTIONS.md`.
  - [ ] Open a per-repo PR via the per-repo agent:
    ```
    [<R> agent prompt]
    Open a PR titled "feat(conventions): seed CONVENTIONS.md (v2 Phase 7)"
    on branch wip/conventions-seed for the just-promoted CONVENTIONS.md.
    Include lint-conventions.py validation in the pre-commit hook chain.
    pd-push.
    ```
  - [ ] Wait for the PR to merge (CT's call).

- [ ] **Step 2: After all 6 repos have CONVENTIONS.md, verify sync**

```bash
cd /workspaces/ocr-container
python3 scripts/sync-conventions.py
```

Expected: `✓ already in sync` for repos whose marker block was
correctly inlined by extract-conventions; `✓ synced + pushed` for any
that had drift to fix.

- [ ] **Step 3: Verify sync-drift panel shows all six in-sync**

```bash
SHIP_ISSUE_MEMORY_DIR=/tmp/sm /workspaces/ocr-container/scripts/check-sync-drift.py
cat /tmp/sm/sync-drift.json
```

Expected: all 7 covered repos report `in-sync`.

---

## Task 10: Arm the daily + weekly bots on each repo

**Manual handback** — for each of the 6 repos, CT:
1. Schedules the daily review-bot ctask entry (mirroring v2 Plan 3 Task 5).
2. Files the recurring:weekly chore issue (mirroring v2 Plan 3 Task 8).
3. Schedules the weekly sweep-bot ctask entry (mirroring v2 Plan 3 Task 9).

- [ ] **Step 1: For each repo `R`**

  - [ ] Schedule daily review:
    ```bash
    /workspaces/ocr-container/ctask add \
      --name "style-review-$R" \
      --cmd "sudo -u claude-bot env WORKSPACE_ROOT=/workspaces/ocr-container /workspaces/ocr-container/scripts/style-review-orchestrator.sh --repo ConcaveTrillion/$R" \
      --schedule "0 3 * * *"
    ```
  - [ ] File recurring weekly chore:
    ```bash
    gh issue create -R "ConcaveTrillion/$R" \
      --title "Weekly style-sweep" \
      --body "Recurring weekly chore. \`bot:style-sweep-ready\` enables the bot." \
      --label "kind:chore,recurring:weekly,bot:style-sweep-ready,status:ready"
    ```
  - [ ] Schedule weekly sweep:
    ```bash
    /workspaces/ocr-container/ctask add \
      --name "style-sweep-$R" \
      --cmd "sudo -u claude-bot env WORKSPACE_ROOT=/workspaces/ocr-container /workspaces/ocr-container/scripts/style-sweep-orchestrator.sh --repo ConcaveTrillion/$R" \
      --schedule "0 4 * * 0"
    ```

- [ ] **Step 2: After all 6 repos armed, smoke-fire each**

For each repo, run the daily and the weekly orchestrator once
manually as a smoke test:

```bash
for r in pdomain-ocr-cli pd-ocr-labeler pdomain-ocr-labeler-spa \
         pdomain-ocr-synth pd-ocr-trainer pdomain-prep-for-pgdp; do
  echo "=== $r ==="
  sudo -u claude-bot env WORKSPACE_ROOT=/workspaces/ocr-container \
    /workspaces/ocr-container/scripts/style-review-orchestrator.sh \
    --repo "ConcaveTrillion/$r"
done
```

Expected: each one runs cleanly. Some may no-op ("no commits since last
review tag") — that's fine on first arm.

---

## Task 11: Mark v2 spec acceptance bullets + flip Status to Active

This is the final task of v2.

- [ ] **Step 1: Edit the spec**

Open
`docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md`.
Tick the remaining acceptance bullets:

```markdown
- [x] `scripts/lint-conventions.py` exists; pre-commit catches malformed `CONVENTIONS.md` fixtures
- [x] `scripts/sync-conventions.py` correctly identifies no-change and applies changes idempotently
- [x] `scripts/check-sync-drift.py` writes `sync-drift.json`; "Sync drift" dashboard panel renders
- [x] `scripts/check-sibling-drift.py` runs weekly via ctask; writes `sibling-drift.json`; "Sibling drift" dashboard panel renders
- [x] Three new labels (`bot:style-review-ready`, `bot:style-sweep-ready`, `bot:style-fixed-by-agent`) seeded across all 7 repos
- [x] Phase 7 rollout: `CONVENTIONS.md` exists in all 7 pd-* repos; ctask entries scheduled per repo
```

(Re-check the all-7-repos label bullet from v2 Plan 3 Task 11; if it
was reduced to "pdomain-book-tools", restore the original wording now that
all 7 are seeded.)

- [ ] **Step 2: Flip Status: Draft → Active**

Find:
```markdown
> **Status**: Draft
```

Replace with:
```markdown
> **Status**: Active
```

Bump `> **Last updated**:` to today's date.

- [ ] **Step 3: Lint + commit**

```bash
cd /workspaces/ocr-container
python3 scripts/lint-spec.py docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md
git add docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md
git commit -m "spec(code-review-style): mark Active after v2 Plan 4 land"
```

---

## Done — what comes next

With this plan landed, the v2 code-review/style story is fully live
across all 7 covered pd-* repos:

- Workspace canonical CONVENTIONS.md drives a marker-delimited cross-repo block on each per-repo file.
- `sync-conventions.py` propagates updates from the canonical.
- `check-sync-drift.py` + `check-sibling-drift.py` surface drift on the dashboard.
- Daily + weekly bots run on every repo with active CONVENTIONS.md.
- `/pr-review` is the single CT-interactive surface for reviewing.

**Future work (out of all four v2 plans):**

- pd-png-optimizer story (its Rust core needs `cargo fmt` + `cargo clippy` integration; deferred to v3 per Open Q #4).
- Per-rule auto-fix calibration (read-only proposal of demoting noisy `auto-fix-reverted` rules — Open Q #3).
- Cost ceiling per repo (`cost-throttled` event kind — Open Q #5).
- Workspace-tooling repo for the canonical CONVENTIONS.md (move to `ConcaveTrillion/ocr-container-meta` if CT decides per Open Q #2 / queued task #2).
- Future-bot integrations (the `bot:` label namespace continues to scale — see v1 Future state hooks).

**Plan-4 task summary:**
- Tasks 1-7 are dispatchable to subagents (deterministic scripts + dashboard panels).
- Tasks 8-10 are CT-driven manual handbacks (per-repo bootstrap + arm).
- Task 11 marks the spec Active.
