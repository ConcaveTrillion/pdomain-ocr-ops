---
status: active
synced: 2026-05-17
milestone: 8
repo: ConcaveTrillion/ocr-container-meta
---

# GH Workflow — Plan A: Pipeline Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the script layer for the unified GH Issues workflow: ship-issue-pick.py (blocker-aware eligibility), decompose-spec-sync.py (idempotent plan→GH sync), plan frontmatter schema, kind:decision label and issue template.

**Architecture:** `scripts/ship-issue-pick.py` is a pure-Python module loaded by the ship-issue skill via `importlib`; its `is_eligible` and `parse_closing_keywords` functions are tested by pre-existing TDD tests and must match those exact signatures. `scripts/decompose-spec-sync.py` replaces the one-shot decompose flow with an idempotent diff loop keyed on `{#slug}` anchors in plan headings; it is exercised by a new TDD test file following the FakeGh pattern already established by `test_decompose_spec_apply.py`. Label seeding and the issue template are wired into existing mechanisms (`coding-bot/src/coding_bot/helpers/label_seed.py` and `pdomain-book-tools/.github/ISSUE_TEMPLATE/`).

**Tech Stack:** Python 3.13, pytest, gh CLI, PyYAML (for frontmatter), uv

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| `is_eligible` signature | `(issue, gh=None, virtually_closed=frozenset()) -> (bool, str)` | Locked by existing tests in `test_ship_issue_pick.py` |
| `parse_closing_keywords` signature | `(text: str) -> set[int]` | Locked by existing tests |
| Blocker header format | `Blocked-by: #N` (hyphenated, singular, no space before `#`) | Locked by test fixtures; matches decompose-spec-apply.py convention |
| Slug identity for sync | `{#slug}` anchor in `## Task N — Title {#slug}` headings | Survives title renames; anchor is stable across plan edits |
| Plan frontmatter keys | `status`, `synced`, `milestone`, `superseded-by` | Matches spec §6; `synced` and `milestone` written by decompose-spec-sync.py; `status` managed by groom |
| Decision label | `kind:decision` | Matches `kind:` family convention in label_seed.py |
| writing-plans frontmatter | Convention-only change (plugin skill, not local) | `writing-plans` lives at `/home/vscode/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/writing-plans/SKILL.md` — a plugin file that gets overwritten on update. Convention is documented in this repo; the patch-brainstorming-skill.sh pattern is the precedent but NOT used here (frontmatter is just a new convention, not a behavior patch). |
| Issue template location | `pdomain-book-tools/.github/ISSUE_TEMPLATE/decision.md` | pdomain-book-tools is the reference repo for workspace-level conventions; other repos copy via the same mechanism as other templates |
| Test runner | `uv run pytest tests/scripts/ -v` from workspace root | Matches existing test infrastructure |
| GH calls in scripts | `subprocess.run(["gh", ...], ...)` | Consistent with all existing workspace scripts |
| Scripts loadable as modules | No `if __name__ == "__main__"` guard around top-level definitions | Required by `importlib.util.spec_from_file_location` pattern used in tests |

---

## Task 1 — ship-issue-pick.py {#ship-issue-pick}

model: sonnet  effort: M  area: scripts

**Files:**
- Create: `scripts/ship-issue-pick.py`
- Test: `tests/scripts/test_ship_issue_pick.py` (pre-existing — must pass)

Context: The TDD tests already exist and define the full contract. The script must be a loadable module (importlib pattern), executable, print `ship-issue` in `--help`, and export `is_eligible` + `parse_closing_keywords`.

Approach: Write the script with a real `argparse` help section, then implement the two functions exactly as the tests require. `is_eligible` checks labels first (fast path), then parses `Blocked-by:` lines and optionally resolves each blocker's state via the `gh` seam, short-circuiting on `virtually_closed`. `parse_closing_keywords` uses a single regex over GitHub's documented closing keyword set.

- [ ] **Step 1: Verify the pre-existing test file exists and review it**

Run: `uv run pytest tests/scripts/test_ship_issue_pick.py -v --collect-only 2>&1 | head -40`
Expected: collection fails with `ModuleNotFoundError` or `FileNotFoundError` for `ship-issue-pick.py` (the script does not exist yet).

- [ ] **Step 2: Create `scripts/ship-issue-pick.py`**

```python
#!/usr/bin/env python3
"""ship-issue-pick.py — eligibility predicate and closing-keyword parser.

Used by the ship-issue skill and coding-bot to select the next issue to work on.
Can be run standalone:
  python3 scripts/ship-issue-pick.py --help
  python3 scripts/ship-issue-pick.py --repo pdomain/pdomain-book-tools

Functions exported for importlib use:
  is_eligible(issue, gh=None, virtually_closed=frozenset()) -> (bool, str)
  parse_closing_keywords(text) -> set[int]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import Any


# ---------------------------------------------------------------------------
# GH seam — thin wrapper used in production; tests inject FakeGhForPick
# ---------------------------------------------------------------------------

class _RealGh:
    """Production gh CLI wrapper for blocker state lookups."""

    def issue_view_state(self, repo: str, number: int) -> str:
        """Return 'OPEN' or 'CLOSED' for the given issue number."""
        result = subprocess.run(
            ["gh", "issue", "view", str(number), "--repo", repo, "--json", "state"],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(result.stdout)
        return data["state"]  # 'OPEN' or 'CLOSED'


# ---------------------------------------------------------------------------
# Blocked-by parsing
# ---------------------------------------------------------------------------

_BLOCKED_BY_RE = re.compile(
    r"^Blocked-by:\s*(.+)$",
    re.MULTILINE | re.IGNORECASE,
)
_ISSUE_REF_RE = re.compile(r"#(\d+)")


def _parse_blocked_by(body: str) -> set[int]:
    """Return set of issue numbers from all 'Blocked-by: #N, #M' lines in body."""
    numbers: set[int] = set()
    for match in _BLOCKED_BY_RE.finditer(body or ""):
        for ref in _ISSUE_REF_RE.finditer(match.group(1)):
            numbers.add(int(ref.group(1)))
    return numbers


# ---------------------------------------------------------------------------
# Closing-keyword parser
# ---------------------------------------------------------------------------

_CLOSING_KEYWORDS_RE = re.compile(
    r"(?<![/\w])(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)",
    re.IGNORECASE,
)


def parse_closing_keywords(text: str) -> set[int]:
    """Return set of issue numbers referenced by GitHub closing keywords in text.

    Recognises: close, closes, closed, fix, fixes, fixed, resolve, resolves, resolved.
    Ignores cross-repo references (owner/repo#N) because they contain a slash before #.
    """
    return {int(m.group(1)) for m in _CLOSING_KEYWORDS_RE.finditer(text)}


# ---------------------------------------------------------------------------
# Eligibility predicate
# ---------------------------------------------------------------------------

_INELIGIBLE_KIND_LABELS = frozenset()  # all kinds allowed; filtered by required labels
_REQUIRED_LABELS = frozenset({"bot:ship-issue-ready", "status:ready"})
_BLOCKING_STATUS_LABELS = frozenset({"status:blocked", "status:in-progress", "status:in-review"})
# model-effort values that require human oversight (skip for bot)
_SKIP_MODEL_EFFORT = frozenset({"xhigh"})
_SKIP_MODEL = frozenset({"model:opus"})


def is_eligible(
    issue: dict[str, Any],
    gh: Any = None,
    virtually_closed: frozenset[int] = frozenset(),
) -> tuple[bool, str]:
    """Return (eligible, reason) for a GH issue dict.

    Args:
        issue: GH issue JSON dict with keys: number, labels (list of {name: str}), body.
        gh: object with issue_view_state(repo, number) -> 'OPEN'|'CLOSED'.
            If None, a _RealGh() is constructed on first need (only when blockers exist
            and are not all virtually_closed).
        virtually_closed: set of issue numbers considered closed even if GH says OPEN
            (e.g., closed by a commit in an open PR in the current session).

    Returns:
        (True, "") if eligible.
        (False, "<human-readable reason>") if not eligible.
    """
    label_names = {lbl["name"] for lbl in issue.get("labels", [])}

    # Must have bot:ship-issue-ready
    if "bot:ship-issue-ready" not in label_names:
        return False, "missing label bot:ship-issue-ready"

    # Must have status:ready
    if "status:ready" not in label_names:
        return False, "missing label status:ready — issue is not in status:ready"

    # Must not have a blocking status label
    blocking = label_names & _BLOCKING_STATUS_LABELS
    if blocking:
        label = next(iter(blocking))
        return False, f"issue has blocking status label: {label}"

    # Skip if model-effort:xhigh (requires Opus / human oversight)
    if label_names & {f"model-effort:{e}" for e in _SKIP_MODEL_EFFORT}:
        bad = next(iter(label_names & {f"model-effort:{e}" for e in _SKIP_MODEL_EFFORT}))
        return False, f"skipping {bad} issue — requires opus-level effort or human review"

    # Skip if model:opus directly labelled
    if _SKIP_MODEL & label_names:
        return False, "skipping model:opus issue — requires human review"

    # Check Blocked-by: headers
    body = issue.get("body") or ""
    blocker_numbers = _parse_blocked_by(body)
    if blocker_numbers:
        # Short-circuit: all virtually closed → no gh call needed
        remaining = blocker_numbers - set(virtually_closed)
        if remaining:
            _gh = gh if gh is not None else _RealGh()
            open_blockers = [
                n for n in sorted(remaining)
                if _gh.issue_view_state("", n) != "CLOSED"
            ]
            if open_blockers:
                refs = ", ".join(f"#{n}" for n in open_blockers)
                return False, f"blocked by open issue(s): {refs}"

    return True, ""


# ---------------------------------------------------------------------------
# CLI — list eligible issues
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ship-issue-pick",
        description=(
            "Pick the next eligible issue for the ship-issue bot.\n"
            "Prints the first eligible issue number to stdout, or exits non-zero if none."
        ),
    )
    p.add_argument("--repo", default="pdomain/pdomain-book-tools",
                   help="GitHub repo (owner/name). Default: pdomain/pdomain-book-tools")
    p.add_argument("--limit", type=int, default=50,
                   help="Max issues to scan. Default: 50")
    p.add_argument("--json", action="store_true", dest="json_output",
                   help="Print full eligible issue JSON instead of just the number")
    p.add_argument("--dry-run", action="store_true",
                   help="Print eligibility table without selecting")
    return p


def _list_issues(repo: str, limit: int) -> list[dict[str, Any]]:
    result = subprocess.run(
        [
            "gh", "issue", "list",
            "--repo", repo,
            "--label", "bot:ship-issue-ready",
            "--state", "open",
            "--limit", str(limit),
            "--json", "number,title,labels,body,milestone",
        ],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    gh = _RealGh()
    issues = _list_issues(args.repo, args.limit)

    rows: list[tuple[dict, bool, str]] = []
    for issue in issues:
        ok, reason = is_eligible(issue, gh=gh)
        rows.append((issue, ok, reason))

    if args.dry_run:
        for issue, ok, reason in rows:
            status = "ELIGIBLE" if ok else f"SKIP: {reason}"
            print(f"  #{issue['number']:5d}  {status}  {issue.get('title', '')[:60]}")
        return 0

    for issue, ok, reason in rows:
        if ok:
            if args.json_output:
                print(json.dumps(issue, indent=2))
            else:
                print(issue["number"])
            return 0

    print("No eligible issues found.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Make the script executable**

```bash
chmod +x /workspaces/ocr-container/scripts/ship-issue-pick.py
```

- [ ] **Step 4: Run the full test suite against the script**

Run: `uv run pytest tests/scripts/test_ship_issue_pick.py -v 2>&1`
Expected: all tests PASS (17 tests).

Look for any failures in:
- `test_script_exists` — checks file exists and is executable
- `test_help_works` — checks `--help` exits 0 and contains "ship-issue"
- `test_eligibility_predicate` — checks label logic including xhigh rejection
- `test_skips_when_blocker_open` — checks FakeGh integration
- `test_virtually_closed_short_circuits_gh_call` — checks ExplodingGh is never called
- `test_parse_closing_keywords_*` — checks regex variants

Fix any failures before proceeding.

- [ ] **Step 5: Commit**

```bash
git add scripts/ship-issue-pick.py
git commit -m "feat(scripts): add ship-issue-pick.py — blocker-aware eligibility predicate

Implements is_eligible(issue, gh=None, virtually_closed=frozenset()) -> (bool, str)
and parse_closing_keywords(text) -> set[int]. All 17 pre-existing TDD tests pass.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2 — TDD tests for decompose-spec-sync.py {#sync-tests}

model: sonnet  effort: M  area: scripts

**Files:**
- Create: `tests/scripts/test_decompose_spec_sync.py`
- Read context: `tests/scripts/test_decompose_spec_apply.py` (FakeGh pattern)

Context: Write the test file FIRST (TDD). The sync script does not exist yet; tests will fail at import. The FakeGh for this test needs: `issue_list`, `issue_create`, `issue_update`, `issue_close`, `issue_reopen`, `milestone_list`, `milestone_create`. Plan frontmatter is read/written with PyYAML.

Approach: Model the FakeGh on the existing pattern from `test_decompose_spec_apply.py`. Tests cover: (1) create issue for new task slug, (2) skip existing matching slug, (3) update body when slug exists but body differs, (4) close issue when task removed from plan, (5) reopen issue when task re-added to plan, (6) frontmatter is updated with `synced:` and `milestone:` after sync, (7) blocker slug resolution writes `Blocked by: #N` in created body.

- [ ] **Step 1: Create `tests/scripts/test_decompose_spec_sync.py`**

```python
"""Tests for scripts/decompose-spec-sync.py.

TDD-first: script does not exist yet. All tests fail at import until Task 3.
Uses the FakeGh pattern established by test_decompose_spec_apply.py.
"""
from __future__ import annotations

import importlib.util
import sys
import textwrap
import tempfile
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/decompose-spec-sync.py"


def _load_module():
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    spec = importlib.util.spec_from_file_location("decompose_spec_sync", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# FakeGh seam
# ---------------------------------------------------------------------------

class FakeGh:
    """Fake GH for decompose-spec-sync tests.

    Tracks calls to verify side-effects without hitting the network.
    """

    def __init__(self, milestone_number: int = 42, existing_issues: list[dict] | None = None):
        self.milestone_number = milestone_number
        self._issues: list[dict] = list(existing_issues or [])
        self._next_issue_number = 300
        # Call log
        self.created_issues: list[dict] = []
        self.updated_issues: list[dict] = []  # list of {number, body}
        self.closed_issues: list[int] = []
        self.reopened_issues: list[int] = []
        self.created_milestones: list[dict] = []

    def milestone_list(self, repo: str) -> list[dict]:
        return [{"number": self.milestone_number, "title": "spec: test-plan (#10)", "state": "open"}]

    def milestone_create(self, repo: str, title: str, description: str = "") -> int:
        n = self.milestone_number
        self.created_milestones.append({"number": n, "title": title})
        return n

    def issue_list(self, repo: str, milestone: int | None = None, state: str = "open",
                   limit: int = 200) -> list[dict]:
        results = list(self._issues)
        if state != "all":
            results = [i for i in results if i.get("state", "OPEN") == state.upper()]
        return results

    def issue_create(self, repo: str, title: str, body: str, labels: list[str],
                     milestone_number: int | None = None) -> int:
        n = self._next_issue_number
        self._next_issue_number += 1
        rec = {"number": n, "title": title, "body": body, "labels": labels,
               "milestone": milestone_number, "state": "OPEN"}
        self._issues.append(rec)
        self.created_issues.append(rec)
        return n

    def issue_update(self, repo: str, number: int, body: str) -> None:
        for issue in self._issues:
            if issue["number"] == number:
                issue["body"] = body
        self.updated_issues.append({"number": number, "body": body})

    def issue_close(self, repo: str, number: int, comment: str = "") -> None:
        for issue in self._issues:
            if issue["number"] == number:
                issue["state"] = "CLOSED"
        self.closed_issues.append(number)

    def issue_reopen(self, repo: str, number: int, comment: str = "") -> None:
        for issue in self._issues:
            if issue["number"] == number:
                issue["state"] = "OPEN"
        self.reopened_issues.append(number)


# ---------------------------------------------------------------------------
# Plan doc helpers
# ---------------------------------------------------------------------------

_PLAN_WITH_TWO_TASKS = textwrap.dedent("""\
    ---
    status: active
    synced: ~
    milestone: ~
    ---

    # Test Plan

    > **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

    **Goal:** Test the sync script.

    **Architecture:** N/A

    **Tech Stack:** Python, pytest

    ---

    ## Task 1 — Schema definition  {#schema-definition}
    model: sonnet  effort: S  area: backend

    Approach: Define the Pydantic schema for the task body.
    Verification: uv run pytest tests/test_schema.py -v
    Acceptance:
    - [ ] Schema validates a valid body
    - [ ] Schema rejects a missing field

    ## Task 2 — Bbox extraction  {#bbox-extraction}
    model: sonnet  effort: M  area: backend

    Approach: Extract bounding boxes from the OCR output.
    Blocked-by: #schema-definition
    Verification: uv run pytest tests/test_bbox.py -v
    Acceptance:
    - [ ] Returns list of BBox objects
""")

_PLAN_ONE_TASK_REMOVED = textwrap.dedent("""\
    ---
    status: active
    synced: ~
    milestone: ~
    ---

    # Test Plan

    > **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

    **Goal:** Test the sync script.

    **Architecture:** N/A

    **Tech Stack:** Python, pytest

    ---

    ## Task 1 — Schema definition  {#schema-definition}
    model: sonnet  effort: S  area: backend

    Approach: Define the Pydantic schema for the task body.
    Verification: uv run pytest tests/test_schema.py -v
    Acceptance:
    - [ ] Schema validates a valid body
""")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_script_exists():
    assert SCRIPT.exists()


def test_creates_issues_for_new_tasks():
    """Two tasks in plan, no existing issues → two issues created."""
    mod = _load_module()
    gh = FakeGh()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(_PLAN_WITH_TWO_TASKS)
        plan_path = Path(f.name)

    try:
        result = mod.sync_plan(
            plan_path=plan_path,
            repo="pdomain/pdomain-book-tools",
            spec_issue_number=10,
            milestone_number=42,
            gh=gh,
            dry_run=True,
        )
        assert result["created"] == 2
        assert result["updated"] == 0
        assert result["closed"] == 0
        # Dry run should NOT actually call gh.issue_create
        assert len(gh.created_issues) == 0
    finally:
        plan_path.unlink()


def test_skips_existing_issue_with_matching_slug():
    """Task already has a GH issue with matching slug in body → no create."""
    mod = _load_module()

    existing = [
        {
            "number": 301,
            "title": "Schema definition",
            "body": "Plan: docs/plans/test.md#schema-definition\nTracks: #10",
            "labels": [{"name": "kind:feature"}],
            "state": "OPEN",
        }
    ]
    gh = FakeGh(existing_issues=existing)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(_PLAN_WITH_TWO_TASKS)
        plan_path = Path(f.name)

    try:
        result = mod.sync_plan(
            plan_path=plan_path,
            repo="pdomain/pdomain-book-tools",
            spec_issue_number=10,
            milestone_number=42,
            gh=gh,
            dry_run=True,
        )
        # Only one new issue (bbox-extraction), schema-definition already exists
        assert result["created"] == 1
        slugs = [t["slug"] for t in result["tasks_created"]]
        assert "bbox-extraction" in slugs
        assert "schema-definition" not in slugs
    finally:
        plan_path.unlink()


def test_updates_body_when_slug_exists_but_body_differs():
    """Task slug matches but body has changed → update recorded."""
    mod = _load_module()

    existing = [
        {
            "number": 301,
            "title": "Schema definition",
            "body": "Plan: docs/plans/test.md#schema-definition\nTracks: #10\nApproach: OLD",
            "labels": [{"name": "kind:feature"}],
            "state": "OPEN",
        }
    ]
    gh = FakeGh(existing_issues=existing)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(_PLAN_WITH_TWO_TASKS)
        plan_path = Path(f.name)

    try:
        result = mod.sync_plan(
            plan_path=plan_path,
            repo="pdomain/pdomain-book-tools",
            spec_issue_number=10,
            milestone_number=42,
            gh=gh,
            dry_run=True,
        )
        assert result["updated"] >= 1
        updated_slugs = [t["slug"] for t in result["tasks_updated"]]
        assert "schema-definition" in updated_slugs
    finally:
        plan_path.unlink()


def test_closes_issue_when_task_removed_from_plan():
    """Issue has slug for a task that no longer exists in plan → close."""
    mod = _load_module()

    existing = [
        {
            "number": 301,
            "title": "Schema definition",
            "body": "Plan: docs/plans/test.md#schema-definition\nTracks: #10",
            "labels": [{"name": "kind:feature"}],
            "state": "OPEN",
        },
        {
            "number": 302,
            "title": "Bbox extraction",
            "body": "Plan: docs/plans/test.md#bbox-extraction\nTracks: #10",
            "labels": [{"name": "kind:feature"}],
            "state": "OPEN",
        },
    ]
    gh = FakeGh(existing_issues=existing)

    # Plan with only one task — bbox-extraction removed
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(_PLAN_ONE_TASK_REMOVED)
        plan_path = Path(f.name)

    try:
        result = mod.sync_plan(
            plan_path=plan_path,
            repo="pdomain/pdomain-book-tools",
            spec_issue_number=10,
            milestone_number=42,
            gh=gh,
            dry_run=True,
        )
        assert result["closed"] == 1
        closed_slugs = [t["slug"] for t in result["tasks_closed"]]
        assert "bbox-extraction" in closed_slugs
    finally:
        plan_path.unlink()


def test_reopens_issue_when_task_readded():
    """Closed issue has slug that reappears in plan → reopen."""
    mod = _load_module()

    existing = [
        {
            "number": 302,
            "title": "Bbox extraction",
            "body": "Plan: docs/plans/test.md#bbox-extraction\nTracks: #10",
            "labels": [{"name": "kind:feature"}],
            "state": "CLOSED",
        },
    ]
    gh = FakeGh(existing_issues=existing)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(_PLAN_WITH_TWO_TASKS)
        plan_path = Path(f.name)

    try:
        result = mod.sync_plan(
            plan_path=plan_path,
            repo="pdomain/pdomain-book-tools",
            spec_issue_number=10,
            milestone_number=42,
            gh=gh,
            dry_run=True,
        )
        assert result["reopened"] == 1
        reopened_slugs = [t["slug"] for t in result["tasks_reopened"]]
        assert "bbox-extraction" in reopened_slugs
    finally:
        plan_path.unlink()


def test_frontmatter_updated_after_live_sync():
    """After a non-dry-run sync, plan frontmatter has synced: YYYY-MM-DD and milestone: N."""
    mod = _load_module()
    gh = FakeGh(milestone_number=42)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(_PLAN_WITH_TWO_TASKS)
        plan_path = Path(f.name)

    try:
        mod.sync_plan(
            plan_path=plan_path,
            repo="pdomain/pdomain-book-tools",
            spec_issue_number=10,
            milestone_number=42,
            gh=gh,
            dry_run=False,
        )
        updated_text = plan_path.read_text()
        assert "synced:" in updated_text
        assert "milestone: 42" in updated_text
        # synced: should be a date (not null)
        import re
        assert re.search(r"synced:\s*\d{4}-\d{2}-\d{2}", updated_text), (
            f"expected synced: YYYY-MM-DD in frontmatter, got:\n{updated_text[:300]}"
        )
    finally:
        plan_path.unlink()


def test_blocker_slug_resolved_to_issue_number():
    """Task has Blocked-by: #schema-definition; created issue body has Blocked by: #301."""
    mod = _load_module()

    # schema-definition already exists as issue #301
    existing = [
        {
            "number": 301,
            "title": "Schema definition",
            "body": "Plan: docs/plans/test.md#schema-definition\nTracks: #10",
            "labels": [{"name": "kind:feature"}],
            "state": "OPEN",
        }
    ]
    gh = FakeGh(existing_issues=existing)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(_PLAN_WITH_TWO_TASKS)
        plan_path = Path(f.name)

    try:
        mod.sync_plan(
            plan_path=plan_path,
            repo="pdomain/pdomain-book-tools",
            spec_issue_number=10,
            milestone_number=42,
            gh=gh,
            dry_run=False,
        )
        # bbox-extraction should have been created with resolved blocker
        assert len(gh.created_issues) == 1
        bbox_issue = gh.created_issues[0]
        assert "Blocked by: #301" in bbox_issue["body"], (
            f"expected 'Blocked by: #301' in body, got:\n{bbox_issue['body']}"
        )
    finally:
        plan_path.unlink()
```

- [ ] **Step 2: Run tests to confirm they fail at import (script missing)**

Run: `uv run pytest tests/scripts/test_decompose_spec_sync.py -v 2>&1 | head -20`
Expected: `test_script_exists` FAILS (file does not exist) or collection error.

- [ ] **Step 3: Commit the test file**

```bash
git add tests/scripts/test_decompose_spec_sync.py
git commit -m "test(scripts): TDD tests for decompose-spec-sync.py

All tests currently fail — script does not exist yet (Plan A Task 3).
FakeGh seam mirrors test_decompose_spec_apply.py pattern.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3 — decompose-spec-sync.py implementation {#sync-impl}

model: sonnet  effort: L  area: scripts

**Files:**
- Create: `scripts/decompose-spec-sync.py`
- Test: `tests/scripts/test_decompose_spec_sync.py` (Task 2 — must pass)

Context: The sync script is the idempotent replacement for the one-shot decompose flow. It parses `## Task N — Title {#slug}` headings from a plan doc, diffs against GH milestone issues by slug (keyed via `Plan: path#slug` line in issue body), and creates/updates/closes/reopens accordingly. Frontmatter is read/written with PyYAML.

Approach: Parse plan headings with a regex. Load existing issues for the milestone from GH (open + closed). Build a slug→issue map from `Plan:` body lines. Diff: new slugs → create; changed body → update; removed slugs → close; closed slugs that reappear → reopen. Return a result dict with counts and task lists for dry-run reporting.

- [ ] **Step 1: Create `scripts/decompose-spec-sync.py`**

```python
#!/usr/bin/env python3
"""decompose-spec-sync.py — idempotent plan→GH milestone sync.

Usage:
  python3 scripts/decompose-spec-sync.py \\
    --plan docs/plans/2026-05-17-foo.md \\
    --repo pdomain/pdomain-book-tools \\
    --spec-issue 43 \\
    [--milestone 99] \\
    [--dry-run]

Algorithm (per spec §5):
  1. Parse plan doc: extract tasks by ## Task N — Title {#slug} headings.
  2. Query GH milestone: fetch open + closed issues.
  3. Build slug→issue map from "Plan: path#slug" body lines.
  4. Diff:
     - slug in plan, no issue    → CREATE
     - slug in plan, issue open, body differs → UPDATE
     - slug in plan, issue closed            → REOPEN
     - slug not in plan, issue open          → CLOSE
  5. Resolve blockers: Blocked-by: #slug → Blocked by: #N in issue body.
  6. Update plan frontmatter: synced: YYYY-MM-DD, milestone: N.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("error: PyYAML not installed. Run: uv pip install pyyaml", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Plan doc parsing
# ---------------------------------------------------------------------------

_TASK_HEADING_RE = re.compile(
    r"^##\s+Task\s+\d+\s+[—\-]+\s+(.+?)\s+\{#([\w-]+)\}",
    re.MULTILINE,
)
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_BLOCKED_BY_SLUG_RE = re.compile(r"^Blocked-by:\s*#([\w-]+)", re.MULTILINE)


def _parse_tasks(plan_text: str) -> list[dict[str, str]]:
    """Return list of {title, slug, section_text} dicts from plan headings."""
    tasks = []
    headings = list(_TASK_HEADING_RE.finditer(plan_text))
    for i, m in enumerate(headings):
        title = m.group(1).strip()
        slug = m.group(2).strip()
        start = m.start()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(plan_text)
        section = plan_text[start:end].strip()
        tasks.append({"title": title, "slug": slug, "section_text": section})
    return tasks


def _read_frontmatter(plan_text: str) -> dict[str, Any]:
    """Return parsed YAML frontmatter dict, or empty dict if none."""
    m = _FRONTMATTER_RE.match(plan_text)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}


def _write_frontmatter(plan_path: Path, updates: dict[str, Any]) -> None:
    """Update YAML frontmatter keys in-place. Adds frontmatter block if missing."""
    text = plan_path.read_text()
    m = _FRONTMATTER_RE.match(text)
    if m:
        fm = yaml.safe_load(m.group(1)) or {}
        fm.update(updates)
        new_fm = yaml.dump(fm, default_flow_style=False).rstrip()
        new_text = f"---\n{new_fm}\n---\n" + text[m.end():]
    else:
        fm = updates
        new_fm = yaml.dump(fm, default_flow_style=False).rstrip()
        new_text = f"---\n{new_fm}\n---\n\n" + text
    plan_path.write_text(new_text)


# ---------------------------------------------------------------------------
# Issue body builder
# ---------------------------------------------------------------------------

def _build_issue_body(
    task: dict[str, str],
    plan_path: Path,
    spec_issue_number: int,
    slug_to_number: dict[str, int],
) -> str:
    """Build the GH issue body for a plan task.

    Resolves Blocked-by: #slug references to Blocked by: #N.
    """
    section = task["section_text"]
    slug = task["slug"]

    # Extract Approach line(s)
    approach_match = re.search(r"^Approach:\s*(.+)$", section, re.MULTILINE)
    approach = approach_match.group(1).strip() if approach_match else "(see plan)"

    # Extract Verification
    verif_match = re.search(r"^Verification:\s*(.+)$", section, re.MULTILINE)
    verification = verif_match.group(1).strip() if verif_match else ""

    # Extract Acceptance block
    acceptance_match = re.search(
        r"^Acceptance:\n((?:- \[.\].*\n?)+)", section, re.MULTILINE
    )
    acceptance = acceptance_match.group(0).strip() if acceptance_match else ""

    # Resolve blocker slugs
    blocker_lines = []
    for bm in _BLOCKED_BY_SLUG_RE.finditer(section):
        blocker_slug = bm.group(1)
        if blocker_slug in slug_to_number:
            blocker_lines.append(f"Blocked by: #{slug_to_number[blocker_slug]}")
        else:
            # Slug not yet created; leave as slug placeholder (will update on next sync)
            blocker_lines.append(f"Blocked by: #{blocker_slug}  <!-- unresolved -->")

    plan_ref = f"docs/plans/{plan_path.name}#{slug}"

    lines = [
        f"Approach: {approach}",
        "",
        f"Plan: {plan_ref}",
        f"Tracks: #{spec_issue_number}",
    ]
    if blocker_lines:
        lines.extend(blocker_lines)
    if verification:
        lines.append(f"Verification: {verification}")
    if acceptance:
        lines.append("")
        lines.append(acceptance)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# GH seam — production implementation
# ---------------------------------------------------------------------------

class _RealGh:
    """Production gh CLI wrapper."""

    def milestone_list(self, repo: str) -> list[dict]:
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/milestones",
             "--jq", "[.[] | {number: .number, title: .title, state: .state}]"],
            capture_output=True, text=True, check=True,
        )
        return json.loads(result.stdout)

    def milestone_create(self, repo: str, title: str, description: str = "") -> int:
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/milestones",
             "--method", "POST",
             "--field", f"title={title}",
             "--field", f"description={description}",
             "--jq", ".number"],
            capture_output=True, text=True, check=True,
        )
        return int(result.stdout.strip())

    def issue_list(self, repo: str, milestone: int | None = None,
                   state: str = "open", limit: int = 200) -> list[dict]:
        cmd = [
            "gh", "issue", "list", "--repo", repo,
            "--state", state,
            "--limit", str(limit),
            "--json", "number,title,body,labels,state,milestone",
        ]
        if milestone is not None:
            cmd += ["--milestone", str(milestone)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    def issue_create(self, repo: str, title: str, body: str, labels: list[str],
                     milestone_number: int | None = None) -> int:
        cmd = [
            "gh", "issue", "create", "--repo", repo,
            "--title", title,
            "--body", body,
        ]
        for label in labels:
            cmd += ["--label", label]
        if milestone_number is not None:
            cmd += ["--milestone", str(milestone_number)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # gh issue create prints the issue URL; extract number from it
        url = result.stdout.strip()
        return int(url.rstrip("/").split("/")[-1])

    def issue_update(self, repo: str, number: int, body: str) -> None:
        subprocess.run(
            ["gh", "issue", "edit", str(number), "--repo", repo, "--body", body],
            capture_output=True, text=True, check=True,
        )

    def issue_close(self, repo: str, number: int, comment: str = "") -> None:
        if comment:
            subprocess.run(
                ["gh", "issue", "comment", str(number), "--repo", repo, "--body", comment],
                capture_output=True, text=True, check=True,
            )
        subprocess.run(
            ["gh", "issue", "close", str(number), "--repo", repo],
            capture_output=True, text=True, check=True,
        )

    def issue_reopen(self, repo: str, number: int, comment: str = "") -> None:
        subprocess.run(
            ["gh", "issue", "reopen", str(number), "--repo", repo],
            capture_output=True, text=True, check=True,
        )
        if comment:
            subprocess.run(
                ["gh", "issue", "comment", str(number), "--repo", repo, "--body", comment],
                capture_output=True, text=True, check=True,
            )


# ---------------------------------------------------------------------------
# Core sync logic
# ---------------------------------------------------------------------------

_PLAN_REF_RE = re.compile(r"Plan:\s*\S+#([\w-]+)")


def _slug_from_body(body: str) -> str | None:
    """Extract task slug from 'Plan: path#slug' body line."""
    m = _PLAN_REF_RE.search(body or "")
    return m.group(1) if m else None


def sync_plan(
    plan_path: Path,
    repo: str,
    spec_issue_number: int,
    milestone_number: int,
    gh: Any = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Idempotently sync plan tasks to GH milestone issues.

    Returns a result dict:
      {created, updated, closed, reopened,
       tasks_created, tasks_updated, tasks_closed, tasks_reopened}

    In dry_run=True mode, no GH writes are made and frontmatter is NOT updated.
    """
    if gh is None:
        gh = _RealGh()

    plan_text = plan_path.read_text()
    tasks = _parse_tasks(plan_text)

    # Fetch all open and closed issues for the milestone
    open_issues = gh.issue_list(repo, milestone=milestone_number, state="open")
    closed_issues = gh.issue_list(repo, milestone=milestone_number, state="closed")
    all_issues = open_issues + closed_issues

    # Build slug → issue map from existing GH issues
    slug_to_issue: dict[str, dict] = {}
    for issue in all_issues:
        slug = _slug_from_body(issue.get("body", ""))
        if slug:
            slug_to_issue[slug] = issue

    # Build slug → GH number map (for blocker resolution)
    slug_to_number: dict[str, int] = {
        slug: issue["number"] for slug, issue in slug_to_issue.items()
    }

    plan_slugs = {t["slug"] for t in tasks}

    result: dict[str, Any] = {
        "created": 0,
        "updated": 0,
        "closed": 0,
        "reopened": 0,
        "tasks_created": [],
        "tasks_updated": [],
        "tasks_closed": [],
        "tasks_reopened": [],
    }

    # Pass 1: for each task in plan, determine action
    for task in tasks:
        slug = task["slug"]
        new_body = _build_issue_body(task, plan_path, spec_issue_number, slug_to_number)

        if slug not in slug_to_issue:
            # CREATE
            result["created"] += 1
            result["tasks_created"].append({"slug": slug, "title": task["title"],
                                             "body": new_body})
            if not dry_run:
                n = gh.issue_create(
                    repo=repo,
                    title=task["title"],
                    body=new_body,
                    labels=["kind:feature", "status:backlog"],
                    milestone_number=milestone_number,
                )
                slug_to_number[slug] = n
        else:
            existing = slug_to_issue[slug]
            if existing.get("state", "OPEN").upper() == "CLOSED":
                # REOPEN
                result["reopened"] += 1
                result["tasks_reopened"].append({"slug": slug, "number": existing["number"]})
                if not dry_run:
                    today = date.today().isoformat()
                    gh.issue_reopen(
                        repo, existing["number"],
                        comment=f"Restored from plan update {today}",
                    )
                    gh.issue_update(repo, existing["number"], body=new_body)
            else:
                # Check if body differs (ignoring whitespace)
                existing_body = (existing.get("body") or "").strip()
                if existing_body != new_body.strip():
                    result["updated"] += 1
                    result["tasks_updated"].append({
                        "slug": slug, "number": existing["number"],
                        "old_body": existing_body, "new_body": new_body,
                    })
                    if not dry_run:
                        gh.issue_update(repo, existing["number"], body=new_body)

    # Pass 2: close issues whose slugs no longer appear in plan
    for slug, issue in slug_to_issue.items():
        if slug not in plan_slugs and issue.get("state", "OPEN").upper() == "OPEN":
            result["closed"] += 1
            result["tasks_closed"].append({"slug": slug, "number": issue["number"]})
            if not dry_run:
                today = date.today().isoformat()
                gh.issue_close(
                    repo, issue["number"],
                    comment=f"Removed from plan {today}",
                )

    # Update frontmatter
    if not dry_run:
        _write_frontmatter(plan_path, {
            "synced": date.today().isoformat(),
            "milestone": milestone_number,
        })

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="decompose-spec-sync",
        description="Idempotently sync a plan doc's tasks to a GH milestone.",
    )
    p.add_argument("--plan", required=True, metavar="PATH",
                   help="Path to the plan markdown file")
    p.add_argument("--repo", required=True,
                   help="GitHub repo (owner/name)")
    p.add_argument("--spec-issue", required=True, type=int, metavar="N",
                   help="Spec GH issue number (used in Tracks: #N body line)")
    p.add_argument("--milestone", required=True, type=int, metavar="N",
                   help="GH milestone number to sync against")
    p.add_argument("--dry-run", action="store_true",
                   help="Print diff without making any GH writes")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"error: plan file not found: {plan_path}", file=sys.stderr)
        return 1

    result = sync_plan(
        plan_path=plan_path,
        repo=args.repo,
        spec_issue_number=args.spec_issue,
        milestone_number=args.milestone,
        gh=None,  # use _RealGh
        dry_run=args.dry_run,
    )

    mode = "[DRY RUN] " if args.dry_run else ""
    print(f"{mode}Sync complete:")
    print(f"  Created:  {result['created']}")
    print(f"  Updated:  {result['updated']}")
    print(f"  Closed:   {result['closed']}")
    print(f"  Reopened: {result['reopened']}")
    if args.dry_run:
        for t in result["tasks_created"]:
            print(f"  + {t['slug']} — {t['title']}")
        for t in result["tasks_updated"]:
            print(f"  ~ {t['slug']} (#{t['number']})")
        for t in result["tasks_closed"]:
            print(f"  - {t['slug']} (#{t['number']})")
        for t in result["tasks_reopened"]:
            print(f"  ^ {t['slug']} (#{t['number']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Make the script executable**

```bash
chmod +x /workspaces/ocr-container/scripts/decompose-spec-sync.py
```

- [ ] **Step 3: Run all sync tests**

Run: `uv run pytest tests/scripts/test_decompose_spec_sync.py -v 2>&1`
Expected: all 7 tests PASS.

Fix any failures (common issues: `yaml` import, frontmatter regex, slug extraction regex).

- [ ] **Step 4: Run the full test suite to check for regressions**

Run: `uv run pytest tests/scripts/ -v 2>&1`
Expected: all tests PASS (ship-issue-pick tests + sync tests, no regressions).

- [ ] **Step 5: Commit**

```bash
git add scripts/decompose-spec-sync.py
git commit -m "feat(scripts): add decompose-spec-sync.py — idempotent plan→GH sync

Implements sync_plan() with create/update/close/reopen diff against GH milestone
issues keyed by {#slug} anchors. Resolves Blocked-by: #slug to issue numbers.
Writes synced: and milestone: to plan YAML frontmatter after live sync.
All 7 TDD tests pass.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4 — kind:decision label and plan frontmatter convention {#decision-label}

model: haiku  effort: S  area: tooling

**Files:**
- Modify: `coding-bot/src/coding_bot/helpers/label_seed.py`
- Modify: `.claude/skills/decompose-spec/SKILL.md` (document `--sync` mode)
- Create: `pdomain-book-tools/.github/ISSUE_TEMPLATE/decision.md`

Context: `kind:decision` is missing from STANDARD_LABELS. The writing-plans skill is a plugin (not local) so plan frontmatter is documented as a convention change only — no plugin edit. The issue template establishes the decision issue body contract from spec §3.

Approach: Add `kind:decision` to the STANDARD_LABELS list in label_seed.py right after `kind:spec`. Create the decision issue template in pdomain-book-tools (the reference repo). Document the `--sync` alias in the decompose-spec SKILL.md.

- [ ] **Step 1: Add `kind:decision` to STANDARD_LABELS in label_seed.py**

In `/workspaces/ocr-container/coding-bot/src/coding_bot/helpers/label_seed.py`, insert after the `kind:spec` entry (line 19):

```python
    {"name": "kind:decision", "color": "0075ca", "description": "Architectural decision record (ADR)"},
```

The modified STANDARD_LABELS block around that insertion point will look like:

```python
    {"name": "kind:feature", "color": "0e8a16", "description": "New slice of planned work"},
    {"name": "kind:bug", "color": "d73a4a", "description": "Reproducible incorrect behavior"},
    {"name": "kind:spec", "color": "c5def5", "description": "Design/decision needed before code"},
    {"name": "kind:decision", "color": "0075ca", "description": "Architectural decision record (ADR)"},
    {"name": "kind:feature-request", "color": "c5def5", "description": "Idea pre-triage"},
```

- [ ] **Step 2: Verify label_seed.py loads cleanly**

Run: `uv run python3 -c "from coding_bot.helpers.label_seed import STANDARD_LABELS; names = [l['name'] for l in STANDARD_LABELS]; assert 'kind:decision' in names, names; print('OK', len(STANDARD_LABELS), 'labels')" 2>&1`

Run from: `/workspaces/ocr-container/coding-bot`
Expected: `OK 52 labels` (or the current count + 1).

- [ ] **Step 3: Create pdomain-book-tools decision issue template**

Create `/workspaces/ocr-container/pdomain-book-tools/.github/ISSUE_TEMPLATE/decision.md`:

```markdown
---
name: Decision
about: Architectural decision record — open while deliberating, close when doc is written
labels: "kind:decision,status:backlog"
---

<!--
Decision issues track architectural choices that affect multiple repos or
require choosing between fundamentally different approaches.
Use /triage to route a feature-request here if needed.
-->

Decision: <!-- docs/decisions/YYYY-MM-DD-slug.md -->
Spawns: <!-- #N, #M — spec issues created from this decision -->
Status: open while deliberating; close when doc is written
```

- [ ] **Step 4: Verify the template is valid YAML front-matter**

Run: `python3 -c "
import re, sys
text = open('/workspaces/ocr-container/pdomain-book-tools/.github/ISSUE_TEMPLATE/decision.md').read()
m = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
assert m, 'no front-matter found'
import yaml
data = yaml.safe_load(m.group(1))
assert data['name'] == 'Decision'
assert 'kind:decision' in data['labels']
print('OK:', data)
"
`
Expected: `OK: {'name': 'Decision', 'about': '...', 'labels': '...'}`

- [ ] **Step 5: Document writing-plans frontmatter convention in decompose-spec SKILL.md**

In `/workspaces/ocr-container/.claude/skills/decompose-spec/SKILL.md`, after the "## Required arguments" section, add a new section:

```markdown
## Plan frontmatter (required for --sync)

Every plan doc must begin with a YAML frontmatter block:

```yaml
---
status: active
synced: ~
milestone: ~
---
```

`decompose-spec --sync` writes `synced:` and `milestone:` after each run.
`status:` is managed by grooming (automated or CT). Optional key: `superseded-by: path`.

**writing-plans is a plugin skill** — the frontmatter block is not enforced by the plugin itself.
When writing a new plan, add the frontmatter manually or ask CT to prepend it.
The patch script (`scripts/patch-brainstorming-skill.sh`) is NOT used for this convention —
frontmatter is a structural addition, not a behavior patch.
```

- [ ] **Step 6: Commit all three changes**

```bash
git add coding-bot/src/coding_bot/helpers/label_seed.py \
        pdomain-book-tools/.github/ISSUE_TEMPLATE/decision.md \
        .claude/skills/decompose-spec/SKILL.md
git commit -m "feat(tooling): add kind:decision label, decision issue template, plan frontmatter docs

- label_seed.py: add kind:decision (color #0075ca) to STANDARD_LABELS
- pdomain-book-tools ISSUE_TEMPLATE: decision.md with body contract from spec §3
- decompose-spec SKILL.md: document plan frontmatter schema and writing-plans
  plugin caveat (convention-only, no patch script needed)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5 — Final integration check {#integration-check}

model: haiku  effort: S  area: scripts

**Files:**
- No new files — verification only

Context: Run the full test suite, check executables, and confirm the plan frontmatter on this plan doc itself is correct.

- [ ] **Step 1: Run the complete scripts test suite**

Run: `uv run pytest tests/scripts/ -v 2>&1`
Expected: all tests PASS (no failures, no errors).

- [ ] **Step 2: Verify both scripts are executable and have correct shebangs**

Run:
```bash
head -1 /workspaces/ocr-container/scripts/ship-issue-pick.py
head -1 /workspaces/ocr-container/scripts/decompose-spec-sync.py
python3 /workspaces/ocr-container/scripts/ship-issue-pick.py --help 2>&1 | grep -i "ship-issue"
python3 /workspaces/ocr-container/scripts/decompose-spec-sync.py --help 2>&1 | grep -i "sync"
```
Expected: both have `#!/usr/bin/env python3` shebangs; `--help` exits 0 with usage text containing "ship-issue" and "sync" respectively.

- [ ] **Step 3: Verify kind:decision is in label_seed.py**

Run from `/workspaces/ocr-container/coding-bot`:
```bash
uv run python3 -c "
from coding_bot.helpers.label_seed import STANDARD_LABELS
d = next(l for l in STANDARD_LABELS if l['name'] == 'kind:decision')
print('kind:decision found:', d)
"
```
Expected: prints the label dict with color `0075ca`.

- [ ] **Step 4: Verify the decision issue template has valid front-matter**

Run:
```bash
python3 -c "
import re, yaml
text = open('/workspaces/ocr-container/pdomain-book-tools/.github/ISSUE_TEMPLATE/decision.md').read()
m = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
data = yaml.safe_load(m.group(1))
assert data['name'] == 'Decision', data
assert 'kind:decision' in data['labels'], data
print('Template OK')
"
```
Expected: `Template OK`

- [ ] **Step 5: Confirm this plan doc's frontmatter is valid**

Run:
```bash
python3 -c "
import re, yaml
text = open('/workspaces/ocr-container/docs/plans/2026-05-17-gh-workflow-plan-a-pipeline.md').read()
m = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
assert m, 'no frontmatter'
data = yaml.safe_load(m.group(1))
assert data['status'] == 'active', data
print('Plan frontmatter OK:', data)
"
```
Expected: `Plan frontmatter OK: {'status': 'active', 'synced': None, 'milestone': None}`

- [ ] **Step 6: Final summary commit (if any loose ends)**

If there are any outstanding uncommitted fixes, commit them:

```bash
git add -p  # stage only what was changed in this task
git commit -m "chore(scripts): integration check fixes for Plan A

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

If nothing to commit, skip this step.
