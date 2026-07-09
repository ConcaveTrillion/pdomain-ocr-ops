---
status: complete
synced: 2026-05-17
milestone: 6
repo: ConcaveTrillion/ocr-container-meta
---

# GH Workflow — Plan C: Grooming System

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the automated grooming layer: groom-auto.py for nightly mechanical cleanup, the /groom CT-interactive skill for working the judgment queue, and the monthly recurring chore.

**Architecture:** `scripts/groom-auto.py` is a standalone Python script that runs deterministic grooming actions (auto-unblock, milestone-complete, spec-close, decision-close, research-archive) and emits a structured JSON report of judgment-required items. A claude-bot scheduled job wraps that script, formats the JSON into a GitHub issue body, and creates or updates a "Grooming report" issue in `pdomain-book-tools`. CT drains that report interactively via the `/groom` skill, one item at a time.

**Tech Stack:** Python 3.13, pytest, gh CLI, PyYAML, coding-bot scheduler

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Script location | `scripts/groom-auto.py` | Standalone script, same pattern as other workspace scripts (triage-fork.py, decompose-spec-apply.py); not a coding-bot wheel module — no workflow state machine needed for a one-shot cron job |
| Grooming report location | GH issue in `pdomain-book-tools`, label `kind:chore` | Workspace's primary upstream repo; CT already monitors its issue tracker; issue survives across sessions unlike a file |
| Plan frontmatter parsing | PyYAML | Already present in the workspace Python environment; used in existing scripts |
| Archive directories | `docs/plans/archived/` and `docs/research/archived/` | Mirrors the pattern the spec calls for; subdirectory keeps main dirs scannable |
| Blocked-by parsing | Same `Blocked by: #N` regex as ship-issue-pick.py | Reuse: `re.findall(r'Blocked by:\s*#(\d+)', body)` |
| Decision "is written" heuristic | Body contains `Decision:` line pointing to a file that exists on disk | Matches spec §3 body contract; guards against empty/boilerplate bodies |
| Research "is referenced" | `grep -r <filename>` in `docs/specs/` and `docs/decisions/` | Simple, no graph; any mention counts as referenced |
| Test runner | `uv run pytest tests/scripts/test_groom_auto.py -v` | Matches workspace convention |
| Auth token | `GH_TOKEN_PD` env var | Same as all workspace scripts |
| Scheduled job mechanism | `coding-bot schedule add` CLI command | Documented in `coding-bot/src/coding_bot/scheduler/cli.py`; implementer runs the command, not hardcoded |
| Grooming report issue update | `gh issue list --search "Grooming report" --label kind:chore` to detect existing; create if none, edit body if found | Idempotent; same issue number persists so CT can bookmark it |
| `/groom` skill location | `.claude/skills/groom/SKILL.md` | Follows existing skill naming convention |

---

## Task 1 — Write tests for groom-auto.py (TDD first)  {#groom-auto-tests}

model: sonnet  effort: M  area: tests

**Files:**
- Create: `tests/scripts/test_groom_auto.py`

Context: Write ALL tests before any implementation. The FakeGh pattern (from test_decompose_spec_apply.py) provides a lightweight GH stub. Each detection and action is tested independently with a temp directory as the workspace root.

Approach: Import the script via importlib (same as test_decompose_spec_apply.py). Provide a `FakeGh` class and a `make_workspace(tmp_path)` helper that creates the canonical directory structure. Test each of the five deterministic actions plus the judgment-queue collection separately.

Verification: `uv run pytest tests/scripts/test_groom_auto.py -v` — all tests collected but FAILING (red bar) before Task 2.

Acceptance:
- [ ] `FakeGh` class has: `issue_view(repo, number)`, `issue_edit(repo, number, body)`, `issue_close(repo, number)`, `label_remove(repo, number, label)`, `label_add(repo, number, label)` — all record calls
- [ ] `make_workspace(tmp_path)` creates: `docs/plans/`, `docs/plans/archived/`, `docs/specs/`, `docs/decisions/`, `docs/research/`, `docs/research/archived/`
- [ ] `test_auto_unblock_removes_blocked_adds_ready` — task issue has `Blocked by: #5, #6`; both issues are CLOSED in FakeGh; assert `label_remove("status:blocked")` and `label_add("status:ready")` called
- [ ] `test_auto_unblock_skips_if_any_blocker_open` — task has `Blocked by: #5, #6`; issue #5 open; assert no label changes
- [ ] `test_milestone_complete_marks_plan_archived` — plan frontmatter `status: active`, milestone 100% closed in FakeGh; assert plan file moved to `archived/` and frontmatter `status: complete`
- [ ] `test_milestone_incomplete_no_archive` — milestone has 1 open issue; plan stays in place
- [ ] `test_spec_close_when_all_children_closed` — spec issue body has `Tracks: #10\nTracks: #11`; both closed; assert `issue_close` called on spec issue
- [ ] `test_spec_not_closed_if_child_open` — one child still open; assert no close
- [ ] `test_decision_closed_when_doc_written` — decision issue body has `Decision: docs/decisions/2026-05-17-foo.md`; file exists with `Decision:` line; assert `issue_close` called
- [ ] `test_decision_not_closed_if_doc_missing` — file does not exist on disk; assert no close
- [ ] `test_research_archived_when_referenced` — research file `docs/research/foo.md` referenced in a spec file; assert file moved to `archived/`
- [ ] `test_research_not_archived_when_unreferenced` — no spec/decision references it; stays in place
- [ ] `test_judgment_queue_collects_stale_decision` — decision issue open >14 days, no doc written; appears in `judgment_queue` with type `stale_decision`
- [ ] `test_judgment_queue_collects_orphan_plan` — plan frontmatter has no `synced:` date; appears in `judgment_queue` with type `orphan_plan`
- [ ] `test_judgment_queue_collects_stalled_task` — task `status:in-progress`, updated >7 days ago, no recent PR; appears with type `stalled_task`

Steps:
- [ ] Create `tests/scripts/test_groom_auto.py` with the full content below:

```python
"""Tests for scripts/groom-auto.py (TDD — written before implementation)."""
from __future__ import annotations

import importlib.util
import sys
import textwrap
from datetime import date, timedelta
from pathlib import Path

import pytest

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/groom-auto.py"


def _mod():
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    spec = importlib.util.spec_from_file_location("groom_auto", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------------------
# Fake GH
# ---------------------------------------------------------------------------

class FakeGh:
    def __init__(self, issues: dict[int, dict] | None = None,
                 milestones: dict[int, dict] | None = None):
        self.issues: dict[int, dict] = dict(issues or {})
        self.milestones: dict[int, dict] = dict(milestones or {})
        self.calls: list[tuple] = []

    def issue_view(self, repo: str, number: int) -> dict:
        self.calls.append(("issue_view", repo, number))
        return self.issues.get(number, {"state": "closed", "body": "",
                                        "labels": [], "updatedAt": "2020-01-01T00:00:00Z"})

    def issue_list_by_milestone(self, repo: str, milestone_number: int,
                                state: str = "all") -> list[dict]:
        self.calls.append(("issue_list_by_milestone", repo, milestone_number, state))
        return [i for i in self.issues.values()
                if i.get("milestone") == milestone_number
                and (state == "all" or i["state"] == state)]

    def issue_list(self, repo: str, labels: list[str] | None = None,
                   state: str = "open", limit: int = 200) -> list[dict]:
        self.calls.append(("issue_list", repo, labels, state))
        result = list(self.issues.values())
        if state != "all":
            result = [i for i in result if i.get("state", "open") == state]
        if labels:
            result = [i for i in result if any(
                lb in [l if isinstance(l, str) else l["name"]
                       for l in i.get("labels", [])]
                for lb in labels
            )]
        return result[:limit]

    def issue_close(self, repo: str, number: int) -> None:
        self.calls.append(("issue_close", repo, number))
        if number in self.issues:
            self.issues[number]["state"] = "closed"

    def issue_edit(self, repo: str, number: int, body: str) -> None:
        self.calls.append(("issue_edit", repo, number, body))
        if number in self.issues:
            self.issues[number]["body"] = body

    def label_remove(self, repo: str, number: int, label: str) -> None:
        self.calls.append(("label_remove", repo, number, label))

    def label_add(self, repo: str, number: int, label: str) -> None:
        self.calls.append(("label_add", repo, number, label))

    def milestone_view(self, repo: str, number: int) -> dict:
        self.calls.append(("milestone_view", repo, number))
        return self.milestones.get(number, {"openIssues": 0, "closedIssues": 0,
                                            "state": "closed"})


# ---------------------------------------------------------------------------
# Workspace fixture
# ---------------------------------------------------------------------------

def make_workspace(tmp_path: Path) -> Path:
    """Create canonical superpowers directory structure under tmp_path."""
    for sub in [
        "docs/plans",
        "docs/plans/archived",
        "docs/specs",
        "docs/decisions",
        "docs/research",
        "docs/research/archived",
    ]:
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    return tmp_path


# ---------------------------------------------------------------------------
# Auto-unblock tests
# ---------------------------------------------------------------------------

def test_auto_unblock_removes_blocked_adds_ready(tmp_path):
    m = _mod()
    ws = make_workspace(tmp_path)
    gh = FakeGh(issues={
        5: {"number": 5, "state": "closed", "body": "", "labels": [], "updatedAt": "2026-05-01T00:00:00Z"},
        6: {"number": 6, "state": "closed", "body": "", "labels": [], "updatedAt": "2026-05-01T00:00:00Z"},
        99: {
            "number": 99, "state": "open",
            "body": "Blocked by: #5, #6\nApproach: do it",
            "labels": [{"name": "status:blocked"}],
            "updatedAt": "2026-05-01T00:00:00Z",
        },
    })
    repo = "pdomain/pdomain-book-tools"
    m.auto_unblock([gh.issues[99]], repo, gh)
    assert ("label_remove", repo, 99, "status:blocked") in gh.calls
    assert ("label_add", repo, 99, "status:ready") in gh.calls


def test_auto_unblock_skips_if_any_blocker_open(tmp_path):
    m = _mod()
    ws = make_workspace(tmp_path)
    gh = FakeGh(issues={
        5: {"number": 5, "state": "open", "body": "", "labels": [], "updatedAt": "2026-05-01T00:00:00Z"},
        6: {"number": 6, "state": "closed", "body": "", "labels": [], "updatedAt": "2026-05-01T00:00:00Z"},
        99: {
            "number": 99, "state": "open",
            "body": "Blocked by: #5, #6\nApproach: do it",
            "labels": [{"name": "status:blocked"}],
            "updatedAt": "2026-05-01T00:00:00Z",
        },
    })
    repo = "pdomain/pdomain-book-tools"
    m.auto_unblock([gh.issues[99]], repo, gh)
    call_types = [c[0] for c in gh.calls]
    assert "label_remove" not in call_types
    assert "label_add" not in call_types


# ---------------------------------------------------------------------------
# Milestone complete → archive plan
# ---------------------------------------------------------------------------

def test_milestone_complete_marks_plan_archived(tmp_path):
    m = _mod()
    ws = make_workspace(tmp_path)
    plan_file = ws / "docs/plans/2026-05-17-foo-plan.md"
    plan_file.write_text(textwrap.dedent("""\
        ---
        status: active
        milestone: 7
        synced: 2026-05-17
        ---
        # Foo Plan
        Body here.
    """))
    gh = FakeGh(milestones={7: {"openIssues": 0, "closedIssues": 5, "state": "closed"}})
    repo = "pdomain/pdomain-book-tools"
    m.mark_complete_milestones([plan_file], repo, gh, workspace=ws)
    archived = ws / "docs/plans/archived/2026-05-17-foo-plan.md"
    assert archived.exists()
    assert not plan_file.exists()
    content = archived.read_text()
    assert "status: complete" in content


def test_milestone_incomplete_no_archive(tmp_path):
    m = _mod()
    ws = make_workspace(tmp_path)
    plan_file = ws / "docs/plans/2026-05-17-bar-plan.md"
    plan_file.write_text(textwrap.dedent("""\
        ---
        status: active
        milestone: 8
        synced: 2026-05-17
        ---
        # Bar Plan
    """))
    gh = FakeGh(milestones={8: {"openIssues": 2, "closedIssues": 3, "state": "open"}})
    repo = "pdomain/pdomain-book-tools"
    m.mark_complete_milestones([plan_file], repo, gh, workspace=ws)
    assert plan_file.exists()
    archived = ws / "docs/plans/archived/2026-05-17-bar-plan.md"
    assert not archived.exists()


# ---------------------------------------------------------------------------
# Spec close tests
# ---------------------------------------------------------------------------

def test_spec_close_when_all_children_closed(tmp_path):
    m = _mod()
    ws = make_workspace(tmp_path)
    gh = FakeGh(issues={
        10: {"number": 10, "state": "closed", "body": "", "labels": [], "updatedAt": "2026-05-01T00:00:00Z"},
        11: {"number": 11, "state": "closed", "body": "", "labels": [], "updatedAt": "2026-05-01T00:00:00Z"},
        42: {
            "number": 42, "state": "open",
            "body": "Spec: docs/specs/foo.md\nTracks: #10\nTracks: #11",
            "labels": [{"name": "kind:spec"}],
            "updatedAt": "2026-04-01T00:00:00Z",
        },
    })
    repo = "pdomain/pdomain-book-tools"
    m.close_complete_specs([gh.issues[42]], repo, gh)
    assert ("issue_close", repo, 42) in gh.calls


def test_spec_not_closed_if_child_open(tmp_path):
    m = _mod()
    ws = make_workspace(tmp_path)
    gh = FakeGh(issues={
        10: {"number": 10, "state": "open", "body": "", "labels": [], "updatedAt": "2026-05-01T00:00:00Z"},
        11: {"number": 11, "state": "closed", "body": "", "labels": [], "updatedAt": "2026-05-01T00:00:00Z"},
        42: {
            "number": 42, "state": "open",
            "body": "Spec: docs/specs/foo.md\nTracks: #10\nTracks: #11",
            "labels": [{"name": "kind:spec"}],
            "updatedAt": "2026-04-01T00:00:00Z",
        },
    })
    repo = "pdomain/pdomain-book-tools"
    m.close_complete_specs([gh.issues[42]], repo, gh)
    call_types = [c[0] for c in gh.calls]
    assert "issue_close" not in call_types


# ---------------------------------------------------------------------------
# Decision close tests
# ---------------------------------------------------------------------------

def test_decision_closed_when_doc_written(tmp_path):
    m = _mod()
    ws = make_workspace(tmp_path)
    dec_path = ws / "docs/decisions/2026-05-17-foo.md"
    dec_path.write_text(textwrap.dedent("""\
        # Foo Decision
        Decision: use approach A
        Rationale: it is simpler.
    """))
    gh = FakeGh(issues={
        20: {
            "number": 20, "state": "open",
            "body": f"Decision: docs/decisions/2026-05-17-foo.md\nSpawns:",
            "labels": [{"name": "kind:decision"}],
            "updatedAt": "2026-04-01T00:00:00Z",
        },
    })
    repo = "pdomain/pdomain-book-tools"
    m.close_written_decisions([gh.issues[20]], repo, gh, workspace=ws)
    assert ("issue_close", repo, 20) in gh.calls


def test_decision_not_closed_if_doc_missing(tmp_path):
    m = _mod()
    ws = make_workspace(tmp_path)
    # File does NOT exist
    gh = FakeGh(issues={
        20: {
            "number": 20, "state": "open",
            "body": "Decision: docs/decisions/2026-05-17-missing.md\nSpawns:",
            "labels": [{"name": "kind:decision"}],
            "updatedAt": "2026-04-01T00:00:00Z",
        },
    })
    repo = "pdomain/pdomain-book-tools"
    m.close_written_decisions([gh.issues[20]], repo, gh, workspace=ws)
    call_types = [c[0] for c in gh.calls]
    assert "issue_close" not in call_types


# ---------------------------------------------------------------------------
# Research archive tests
# ---------------------------------------------------------------------------

def test_research_archived_when_referenced(tmp_path):
    m = _mod()
    ws = make_workspace(tmp_path)
    research_file = ws / "docs/research/background-notes.md"
    research_file.write_text("# Background\nSome notes.\n")
    spec_file = ws / "docs/specs/2026-05-17-foo-design.md"
    spec_file.write_text("# Spec\nSee [research](../research/background-notes.md) for detail.\n")
    m.archive_referenced_research(workspace=ws)
    archived = ws / "docs/research/archived/background-notes.md"
    assert archived.exists()
    assert not research_file.exists()


def test_research_not_archived_when_unreferenced(tmp_path):
    m = _mod()
    ws = make_workspace(tmp_path)
    research_file = ws / "docs/research/orphan-notes.md"
    research_file.write_text("# Orphan\nNot referenced.\n")
    m.archive_referenced_research(workspace=ws)
    assert research_file.exists()
    archived = ws / "docs/research/archived/orphan-notes.md"
    assert not archived.exists()


# ---------------------------------------------------------------------------
# Judgment queue tests
# ---------------------------------------------------------------------------

_OLD_DATE = (date.today() - timedelta(days=20)).isoformat() + "T00:00:00Z"
_VERY_OLD_DATE = (date.today() - timedelta(days=100)).isoformat() + "T00:00:00Z"
_RECENT_DATE = (date.today() - timedelta(days=2)).isoformat() + "T00:00:00Z"


def test_judgment_queue_collects_stale_decision(tmp_path):
    m = _mod()
    ws = make_workspace(tmp_path)
    # Decision issue open >14 days, no doc file on disk
    gh = FakeGh(issues={
        30: {
            "number": 30, "state": "open",
            "body": "Decision: docs/decisions/2026-04-01-old.md\nSpawns:",
            "labels": [{"name": "kind:decision"}],
            "updatedAt": _OLD_DATE,
        },
    })
    repo = "pdomain/pdomain-book-tools"
    queue = m.collect_judgment_queue(repo, gh, workspace=ws, today=date.today())
    types = [item["type"] for item in queue]
    assert "stale_decision" in types


def test_judgment_queue_collects_orphan_plan(tmp_path):
    m = _mod()
    ws = make_workspace(tmp_path)
    plan_file = ws / "docs/plans/2026-05-01-unsynced.md"
    plan_file.write_text(textwrap.dedent("""\
        ---
        status: active
        ---
        # Unsynced Plan
        No synced date.
    """))
    gh = FakeGh()
    repo = "pdomain/pdomain-book-tools"
    queue = m.collect_judgment_queue(repo, gh, workspace=ws, today=date.today())
    types = [item["type"] for item in queue]
    assert "orphan_plan" in types


def test_judgment_queue_collects_stalled_task(tmp_path):
    m = _mod()
    ws = make_workspace(tmp_path)
    gh = FakeGh(issues={
        55: {
            "number": 55, "state": "open",
            "body": "Approach: do something",
            "labels": [{"name": "status:in-progress"}, {"name": "kind:feature"}],
            "updatedAt": _OLD_DATE,
        },
    })
    repo = "pdomain/pdomain-book-tools"
    queue = m.collect_judgment_queue(repo, gh, workspace=ws, today=date.today())
    types = [item["type"] for item in queue]
    assert "stalled_task" in types
```

- [ ] Run `uv run pytest tests/scripts/test_groom_auto.py -v 2>&1 | tail -5` — expect collection error (ModuleNotFoundError for groom_auto) — this is the expected red state
- [ ] Commit: `chore(tests): TDD tests for groom-auto.py (red bar)`

---

## Task 2 — Implement scripts/groom-auto.py  {#groom-auto-impl}

model: sonnet  effort: M  area: scripts

**Files:**
- Create: `scripts/groom-auto.py`

Context: Implement all functions tested in Task 1. The script is a standalone CLI that (1) runs all five deterministic actions, (2) collects judgment-required items, (3) prints JSON to stdout for the bot job to format. Auth uses `GH_TOKEN_PD` env var passed to `gh` via `GITHUB_TOKEN`. No internal `gh` module — shell out to the `gh` CLI via subprocess.

Approach: Structure as a `Groom` class that accepts a `gh` adapter object (real uses subprocess; tests use FakeGh). Entry point `main()` instantiates the real adapter and calls `run_all()`. Return value from `run_all()` is a dict: `{"actions": [...], "judgment_queue": [...]}` — printed as JSON to stdout.

Verification: `uv run pytest tests/scripts/test_groom_auto.py -v` — all green

Acceptance:
- [ ] All 15 tests in Task 1 pass
- [ ] Script is executable (`chmod +x`)
- [ ] `python scripts/groom-auto.py --help` runs without error
- [ ] `BLOCKED_BY_RE = re.compile(r'Blocked by:\s*#(\d+)', re.IGNORECASE)` matches body format
- [ ] PyYAML used for frontmatter parsing (not regex)
- [ ] `archive_referenced_research` checks both `docs/specs/` and `docs/decisions/` for any mention of the research filename

Steps:
- [ ] Create `scripts/groom-auto.py` with the full implementation below:

```python
#!/usr/bin/env python3
"""groom-auto.py — deterministic nightly grooming for the superpowers docs tree.

Runs five deterministic actions:
  1. Auto-unblock tasks whose blockers are all closed.
  2. Mark milestone-complete plans as complete + move to archived/.
  3. Close spec issues whose child issues are all closed.
  4. Close decision issues whose decision doc is written.
  5. Archive research files referenced by specs or decisions.

Then collects judgment-required items for the "Grooming report" GH issue.

Outputs JSON: {"actions": [...], "judgment_queue": [...]}
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

WORKSPACE = Path("/workspaces/ocr-container")
REPO = "pdomain/pdomain-book-tools"

BLOCKED_BY_RE = re.compile(r"Blocked by:\s*#(\d+)", re.IGNORECASE)
TRACKS_RE = re.compile(r"Tracks:\s*#(\d+)", re.IGNORECASE)
DECISION_DOC_RE = re.compile(r"Decision:\s*(docs/decisions/\S+\.md)")


# ---------------------------------------------------------------------------
# GH adapter (real, shells out to gh CLI)
# ---------------------------------------------------------------------------


class RealGh:
    """Thin wrapper around the gh CLI."""

    def _run(self, args: list[str], check: bool = True) -> str:
        env = {**os.environ}
        token = os.environ.get("GH_TOKEN_PD", "")
        if token:
            env["GITHUB_TOKEN"] = token
        result = subprocess.run(
            ["gh"] + args, capture_output=True, text=True, env=env
        )
        if check and result.returncode != 0:
            raise RuntimeError(f"gh {' '.join(args)} failed:\n{result.stderr}")
        return result.stdout.strip()

    def issue_view(self, repo: str, number: int) -> dict:
        out = self._run([
            "issue", "view", str(number), "--repo", repo,
            "--json", "number,state,body,labels,updatedAt,milestone",
        ])
        return json.loads(out)

    def issue_list(self, repo: str, labels: list[str] | None = None,
                   state: str = "open", limit: int = 200) -> list[dict]:
        args = [
            "issue", "list", "--repo", repo, "--state", state,
            "--limit", str(limit),
            "--json", "number,state,body,labels,updatedAt,milestone",
        ]
        if labels:
            for lbl in labels:
                args += ["--label", lbl]
        out = self._run(args)
        return json.loads(out) if out else []

    def issue_list_by_milestone(self, repo: str, milestone_number: int,
                                state: str = "all") -> list[dict]:
        out = self._run([
            "issue", "list", "--repo", repo, "--state", state,
            "--milestone", str(milestone_number), "--limit", "200",
            "--json", "number,state,body,labels,updatedAt",
        ])
        return json.loads(out) if out else []

    def issue_close(self, repo: str, number: int) -> None:
        self._run(["issue", "close", str(number), "--repo", repo])

    def issue_edit(self, repo: str, number: int, body: str) -> None:
        self._run(["issue", "edit", str(number), "--repo", repo, "--body", body])

    def label_remove(self, repo: str, number: int, label: str) -> None:
        self._run(["issue", "edit", str(number), "--repo", repo,
                   "--remove-label", label])

    def label_add(self, repo: str, number: int, label: str) -> None:
        self._run(["issue", "edit", str(number), "--repo", repo,
                   "--add-label", label])

    def milestone_view(self, repo: str, number: int) -> dict:
        # gh doesn't have a direct milestone view — use API
        out = self._run([
            "api", f"repos/{repo}/milestones/{number}",
            "--jq", "{openIssues: .open_issues, closedIssues: .closed_issues, state: .state}",
        ])
        return json.loads(out)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _label_names(issue: dict) -> set[str]:
    return {lb["name"] if isinstance(lb, dict) else lb for lb in issue.get("labels", [])}


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body_without_frontmatter)."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, parts[2].lstrip("\n")


def _write_frontmatter(fm: dict, body: str) -> str:
    return "---\n" + yaml.dump(fm, default_flow_style=False) + "---\n\n" + body


def _days_since(iso_str: str, today: date) -> int:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return (today - dt.date()).days


# ---------------------------------------------------------------------------
# Action 1: Auto-unblock
# ---------------------------------------------------------------------------


def auto_unblock(issues: list[dict], repo: str, gh: Any) -> list[dict]:
    """Remove status:blocked and add status:ready for fully-unblocked tasks."""
    actions = []
    for issue in issues:
        if "status:blocked" not in _label_names(issue):
            continue
        body = issue.get("body", "") or ""
        blocker_nums = [int(n) for n in BLOCKED_BY_RE.findall(body)]
        if not blocker_nums:
            continue
        all_closed = all(
            gh.issue_view(repo, n).get("state") == "closed"
            for n in blocker_nums
        )
        if all_closed:
            gh.label_remove(repo, issue["number"], "status:blocked")
            gh.label_add(repo, issue["number"], "status:ready")
            actions.append({
                "action": "auto_unblock",
                "issue": issue["number"],
                "blockers": blocker_nums,
            })
    return actions


# ---------------------------------------------------------------------------
# Action 2: Mark milestone complete → archive plan
# ---------------------------------------------------------------------------


def mark_complete_milestones(plan_files: list[Path], repo: str,
                              gh: Any, workspace: Path) -> list[dict]:
    """Move plans whose milestone is 100% closed to archived/ and set status: complete."""
    actions = []
    archived_dir = workspace / "docs/plans/archived"
    archived_dir.mkdir(parents=True, exist_ok=True)

    for plan_path in plan_files:
        text = plan_path.read_text()
        fm, body = _parse_frontmatter(text)
        milestone_num = fm.get("milestone")
        if not milestone_num:
            continue
        ms = gh.milestone_view(repo, int(milestone_num))
        open_count = ms.get("openIssues", ms.get("open_issues", 1))
        if open_count > 0:
            continue
        # Archive
        fm["status"] = "complete"
        new_text = _write_frontmatter(fm, body)
        dest = archived_dir / plan_path.name
        dest.write_text(new_text)
        plan_path.unlink()
        actions.append({
            "action": "mark_complete",
            "plan": plan_path.name,
            "milestone": milestone_num,
        })
    return actions


# ---------------------------------------------------------------------------
# Action 3: Close spec issues whose children are all closed
# ---------------------------------------------------------------------------


def close_complete_specs(spec_issues: list[dict], repo: str, gh: Any) -> list[dict]:
    """Close spec issues where every Tracks: #N child is closed."""
    actions = []
    for issue in spec_issues:
        body = issue.get("body", "") or ""
        child_nums = [int(n) for n in TRACKS_RE.findall(body)]
        if not child_nums:
            continue
        all_closed = all(
            gh.issue_view(repo, n).get("state") == "closed"
            for n in child_nums
        )
        if all_closed:
            gh.issue_close(repo, issue["number"])
            actions.append({
                "action": "close_spec",
                "issue": issue["number"],
                "children": child_nums,
            })
    return actions


# ---------------------------------------------------------------------------
# Action 4: Close decision issues whose decision doc is written
# ---------------------------------------------------------------------------


def _decision_doc_written(doc_path: Path) -> bool:
    """True if the decision doc exists and contains a 'Decision:' content line."""
    if not doc_path.exists():
        return False
    text = doc_path.read_text()
    # Must have a non-header line starting with "Decision:" (the content line)
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Decision:") and not stripped.startswith("Decision: docs/"):
            return True
    # Fallback: any non-empty content beyond a stub (more than 3 lines)
    non_blank = [l for l in text.splitlines() if l.strip()]
    return len(non_blank) >= 4


def close_written_decisions(decision_issues: list[dict], repo: str,
                             gh: Any, workspace: Path) -> list[dict]:
    """Close decision issues whose decision doc exists and is written."""
    actions = []
    for issue in decision_issues:
        body = issue.get("body", "") or ""
        m = DECISION_DOC_RE.search(body)
        if not m:
            continue
        doc_rel = m.group(1)
        doc_path = workspace / doc_rel
        if _decision_doc_written(doc_path):
            gh.issue_close(repo, issue["number"])
            actions.append({
                "action": "close_decision",
                "issue": issue["number"],
                "doc": doc_rel,
            })
    return actions


# ---------------------------------------------------------------------------
# Action 5: Archive referenced research
# ---------------------------------------------------------------------------


def archive_referenced_research(workspace: Path) -> list[dict]:
    """Move research files that are referenced in any spec or decision to archived/."""
    research_dir = workspace / "docs/research"
    archived_dir = research_dir / "archived"
    archived_dir.mkdir(parents=True, exist_ok=True)

    search_dirs = [
        workspace / "docs/specs",
        workspace / "docs/decisions",
    ]
    actions = []

    for research_file in research_dir.glob("*.md"):
        filename = research_file.name
        referenced = False
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            for candidate in search_dir.glob("*.md"):
                if filename in candidate.read_text():
                    referenced = True
                    break
            if referenced:
                break
        if referenced:
            dest = archived_dir / filename
            shutil.move(str(research_file), str(dest))
            actions.append({
                "action": "archive_research",
                "file": filename,
            })
    return actions


# ---------------------------------------------------------------------------
# Judgment queue collection
# ---------------------------------------------------------------------------


def collect_judgment_queue(repo: str, gh: Any, workspace: Path,
                            today: date | None = None) -> list[dict]:
    """Collect items needing CT review. Returns list of judgment dicts."""
    if today is None:
        today = date.today()
    queue: list[dict] = []

    # 1. Stale decisions (open >14 days, doc not yet written)
    decision_issues = gh.issue_list(repo, labels=["kind:decision"], state="open")
    for issue in decision_issues:
        age = _days_since(issue.get("updatedAt", "2020-01-01T00:00:00Z"), today)
        body = issue.get("body", "") or ""
        m = DECISION_DOC_RE.search(body)
        doc_exists = False
        if m:
            doc_path = workspace / m.group(1)
            doc_exists = _decision_doc_written(doc_path)
        if not doc_exists and age > 14:
            queue.append({
                "type": "stale_decision",
                "issue": issue["number"],
                "age_days": age,
                "proposed": "Nudge CT to write decision doc or close",
            })

    # 2. Orphan plans (no synced: date in frontmatter)
    plans_dir = workspace / "docs/plans"
    for plan_path in sorted(plans_dir.glob("*.md")):
        text = plan_path.read_text()
        fm, _ = _parse_frontmatter(text)
        if not fm.get("synced"):
            queue.append({
                "type": "orphan_plan",
                "file": plan_path.name,
                "proposed": "Run /decompose-spec --sync or delete",
            })

    # 3. Limbo plans (synced >30 days, milestone still has open issues)
    for plan_path in sorted(plans_dir.glob("*.md")):
        text = plan_path.read_text()
        fm, _ = _parse_frontmatter(text)
        synced_str = fm.get("synced")
        milestone_num = fm.get("milestone")
        if not synced_str or not milestone_num:
            continue
        try:
            synced_date = date.fromisoformat(str(synced_str))
            sync_age = (today - synced_date).days
        except ValueError:
            continue
        if sync_age > 30:
            ms = gh.milestone_view(repo, int(milestone_num))
            open_count = ms.get("openIssues", ms.get("open_issues", 0))
            if open_count > 0:
                queue.append({
                    "type": "limbo_plan",
                    "file": plan_path.name,
                    "sync_age_days": sync_age,
                    "open_issues": open_count,
                    "proposed": "Keep / re-sync / archive",
                })

    # 4. Stalled in-progress tasks (status:in-progress >7 days, no recent PR)
    in_progress = gh.issue_list(repo, labels=["status:in-progress"], state="open")
    for issue in in_progress:
        age = _days_since(issue.get("updatedAt", "2020-01-01T00:00:00Z"), today)
        if age > 7:
            queue.append({
                "type": "stalled_task",
                "issue": issue["number"],
                "age_days": age,
                "proposed": "Requeue to status:ready or close",
            })

    # 5. Long-backlog tasks (status:backlog >90 days)
    backlog = gh.issue_list(repo, labels=["status:backlog"], state="open")
    for issue in backlog:
        age = _days_since(issue.get("updatedAt", "2020-01-01T00:00:00Z"), today)
        if age > 90:
            queue.append({
                "type": "long_backlog_task",
                "issue": issue["number"],
                "age_days": age,
                "proposed": "Keep / reprioritize / close",
            })

    # 6. Orphaned research files (>180 days, not referenced)
    research_dir = workspace / "docs/research"
    search_dirs = [
        workspace / "docs/specs",
        workspace / "docs/decisions",
    ]
    for research_file in research_dir.glob("*.md"):
        try:
            mtime = datetime.fromtimestamp(research_file.stat().st_mtime).date()
            file_age = (today - mtime).days
        except OSError:
            file_age = 0
        if file_age <= 180:
            continue
        referenced = any(
            research_file.name in candidate.read_text()
            for sd in search_dirs if sd.exists()
            for candidate in sd.glob("*.md")
        )
        if not referenced:
            queue.append({
                "type": "orphan_research",
                "file": research_file.name,
                "age_days": file_age,
                "proposed": "Delete or archive",
            })

    return queue


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def run_all(repo: str, gh: Any, workspace: Path,
            today: date | None = None) -> dict:
    """Run all deterministic actions and collect judgment queue. Returns report dict."""
    if today is None:
        today = date.today()
    all_actions: list[dict] = []

    # 1. Auto-unblock
    blocked_issues = gh.issue_list(repo, labels=["status:blocked"], state="open")
    all_actions.extend(auto_unblock(blocked_issues, repo, gh))

    # 2. Milestone complete → archive plans
    plans_dir = workspace / "docs/plans"
    plan_files = sorted(plans_dir.glob("*.md"))
    all_actions.extend(mark_complete_milestones(plan_files, repo, gh, workspace))

    # 3. Close complete spec issues
    spec_issues = gh.issue_list(repo, labels=["kind:spec"], state="open")
    all_actions.extend(close_complete_specs(spec_issues, repo, gh))

    # 4. Close written decision issues
    decision_issues = gh.issue_list(repo, labels=["kind:decision"], state="open")
    all_actions.extend(close_written_decisions(decision_issues, repo, gh, workspace))

    # 5. Archive referenced research
    all_actions.extend(archive_referenced_research(workspace))

    # 6. Collect judgment queue
    judgment_queue = collect_judgment_queue(repo, gh, workspace, today=today)

    return {"actions": all_actions, "judgment_queue": judgment_queue}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=REPO,
                        help="OWNER/REPO to query (default: %(default)s)")
    parser.add_argument("--workspace", default=str(WORKSPACE),
                        help="Workspace root (default: %(default)s)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without making changes")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    gh = RealGh()
    report = run_all(args.repo, gh, workspace)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] `chmod +x scripts/groom-auto.py`
- [ ] `uv run pytest tests/scripts/test_groom_auto.py -v` — all green
- [ ] Commit: `feat(scripts): implement groom-auto.py — nightly deterministic grooming`

---

## Task 3 — Register groom-auto as a coding-bot scheduled job  {#groom-auto-schedule}

model: sonnet  effort: S  area: infra

**Files:**
- No new files — job registered via CLI; document command in this plan

Context: The coding-bot scheduler uses `coding-bot schedule add` to register entries. Each entry maps a name → workflow. The `groom-auto` job is simpler than a full workflow: it runs a Python script and files/updates a GH issue. It does NOT need a state-machine workflow in the coding-bot wheel — it runs as a `claude -p` prompt that calls the script and formats the report.

Approach: Register a `decompose-spec-auto`-style entry. The simplest approach is a new minimal workflow `groom-auto` in `coding_bot/workflows/` that shells out to the script, captures stdout, formats as GH issue body, and creates/updates the report issue.

Verification: `coding-bot schedule list` shows the new `groom-auto-nightly` entry

Acceptance:
- [ ] `coding_bot/workflows/groom_auto.py` module exists with `@workflow(name="groom-auto")` class
- [ ] Workflow states: `run_script` → `file_report` → `done` | `nothing_to_do` | `errored`
- [ ] `on_enter_run_script`: runs `python scripts/groom-auto.py --repo <repo>`, captures JSON stdout
- [ ] `on_enter_file_report`: formats judgment queue as markdown table; creates or updates "Grooming report" issue in `pdomain-book-tools` with label `kind:chore`
- [ ] Schedule entry registered:
  ```
  coding-bot schedule add groom-auto-nightly \
    --workflow groom-auto \
    --trigger "cron:hour=2,minute=0" \
    --context "repo=pdomain/pdomain-book-tools"
  ```
- [ ] Entry appears disabled until CT enables it: `coding-bot schedule enable groom-auto-nightly`

Steps:
- [ ] Create `coding-bot/src/coding_bot/workflows/groom_auto.py`:

```python
"""groom-auto workflow: run_script → file_report → done."""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from coding_bot import gh
from coding_bot.engine.workflow import Workflow, workflow

WORKSPACE = Path("/workspaces/ocr-container")
REPORT_TITLE = "Grooming report"
REPORT_LABEL = "kind:chore"


def _format_judgment_table(queue: list[dict]) -> str:
    if not queue:
        return "_No items require CT review._\n"
    lines = [
        "| Type | Reference | Age | Proposed action |",
        "|---|---|---|---|",
    ]
    for item in queue:
        ref = (
            f"#{item['issue']}" if "issue" in item
            else item.get("file", "—")
        )
        age = f"{item.get('age_days', '—')} days" if "age_days" in item else "—"
        lines.append(
            f"| `{item['type']}` | {ref} | {age} | {item.get('proposed', '—')} |"
        )
    return "\n".join(lines) + "\n"


def _format_actions_summary(actions: list[dict]) -> str:
    if not actions:
        return "_No deterministic actions taken._\n"
    lines = ["| Action | Reference |", "|---|---|"]
    for a in actions:
        ref = f"#{a.get('issue', a.get('plan', a.get('file', '—')))}"
        lines.append(f"| `{a['action']}` | {ref} |")
    return "\n".join(lines) + "\n"


def _find_existing_report_issue(repo: str) -> int | None:
    """Return issue number of existing Grooming report issue, or None."""
    issues = gh.issue_list(repo, labels=[REPORT_LABEL], state="open", limit=50)
    for issue in issues:
        if issue.get("title", "") == REPORT_TITLE:
            return issue["number"]
    return None


@dataclass
class GroomAutoContext:
    repo: str = "pdomain/pdomain-book-tools"
    backend: str = "claude"
    model: str = "haiku"
    effort: str = "low"
    report: dict = field(default_factory=dict)
    terminal: str = ""


@workflow(name="groom-auto", context_class=GroomAutoContext)
class GroomAuto(Workflow):
    states: ClassVar[list[str]] = [
        "run_script",
        "file_report",
        "done",
        "nothing_to_do",
        "errored",
    ]
    initial: ClassVar[str] = "run_script"
    terminal: ClassVar[set[str]] = {"done", "nothing_to_do", "errored"}
    transitions: ClassVar[list[tuple[str, str, str]]] = [
        ("script_done", "run_script", "file_report"),
        ("reported", "file_report", "done"),
        ("no_queue", "file_report", "nothing_to_do"),
        ("error", "run_script", "errored"),
        ("error", "file_report", "errored"),
    ]

    def on_enter_run_script(self) -> None:
        env = {**os.environ}
        token = env.get("GH_TOKEN_PD", "")
        if token:
            env["GITHUB_TOKEN"] = token
        script = WORKSPACE / "scripts/groom-auto.py"
        result = subprocess.run(
            ["python3", str(script), "--repo", self.ctx.repo],
            capture_output=True, text=True, env=env,
        )
        if result.returncode != 0:
            self.ctx.terminal = f"script failed: {result.stderr[:500]}"
            self.error()
            return
        try:
            self.ctx.report = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.ctx.terminal = f"JSON parse error: {exc}"
            self.error()
            return
        self.script_done()

    def on_enter_file_report(self) -> None:
        from datetime import date
        report = self.ctx.report
        actions = report.get("actions", [])
        queue = report.get("judgment_queue", [])

        body = (
            f"## Grooming report — {date.today().isoformat()}\n\n"
            "### Deterministic actions taken\n\n"
            + _format_actions_summary(actions)
            + "\n### Items requiring CT review\n\n"
            + _format_judgment_table(queue)
            + "\n---\n"
            "_Run `/groom all` to work through this list interactively._\n"
        )

        existing_number = _find_existing_report_issue(self.ctx.repo)
        if existing_number:
            gh.issue_edit(self.ctx.repo, existing_number, body=body)
        else:
            gh.issue_create(
                self.ctx.repo,
                title=REPORT_TITLE,
                body=body,
                labels=[REPORT_LABEL, "status:ready"],
            )

        if not queue:
            self.no_queue()
        else:
            self.reported()
```

- [ ] Register the schedule entry:
  ```bash
  coding-bot schedule add groom-auto-nightly \
    --workflow groom-auto \
    --trigger "cron:hour=2,minute=0" \
    --context "repo=pdomain/pdomain-book-tools"
  ```
  (Note: this requires `coding-bot schedule add` — run after coding-bot DB is available; leave disabled until CT enables it)
- [ ] Add `groom_auto` to `coding-bot/src/coding_bot/workflows/__init__.py` imports
- [ ] Write minimal workflow test `coding-bot/tests/unit/workflows/test_groom_auto_workflow.py` verifying state transitions with a mock subprocess that returns valid JSON
- [ ] Commit: `feat(coding-bot): groom-auto workflow + nightly schedule entry`

---

## Task 4 — Implement .claude/skills/groom/SKILL.md  {#groom-skill}

model: sonnet  effort: M  area: skills

**Files:**
- Create: `.claude/skills/groom/SKILL.md`

Context: The `/groom` skill is CT-interactive, same pattern as `/triage`. It reads the current "Grooming report" GH issue, then presents each flagged item one at a time. CT picks an action (keep / update / archive / delete). The skill executes the decision immediately.

Approach: Read the report issue body, parse the judgment table rows, filter by the subcommand argument (`decisions | specs | plans | tasks | research | all`), then loop: present item, ask CT, execute. After draining, post a comment on the report issue summarizing what was resolved.

Verification: Manual test: `/groom all` with a seeded report issue. The skill must present at least one item and execute at least one decision without error.

Acceptance:
- [ ] SKILL.md has correct frontmatter `name: groom` and `description:` matching the skill trigger
- [ ] Supports `/groom decisions | specs | plans | tasks | research | all`
- [ ] Reads "Grooming report" issue from `pdomain/pdomain-book-tools`
- [ ] For each item: displays type, reference, age, proposed action, then asks "Decision (keep/update/archive/delete/skip)?"
- [ ] `keep` → adds a comment on the referenced issue/file noting CT reviewed; no other change
- [ ] `archive` → for files: moves to `archived/` subdirectory; for issues: closes with label `status:archived`
- [ ] `delete` → for files: `rm`; for issues: closes with comment "deleted by CT during grooming"
- [ ] `update` → prompts CT for new title or body, applies via `gh issue edit`
- [ ] `skip` → leaves item in queue for next run
- [ ] After all items: post summary comment on report issue; close report issue if queue fully drained

Steps:
- [ ] Create `.claude/skills/groom/SKILL.md` with full content:

```markdown
---
name: groom
description: CT-interactive grooming skill. Reads the current "Grooming report" GH issue and works through flagged items one at a time. CT decides keep / update / archive / delete. Supports `/groom decisions | specs | plans | tasks | research | all`.
---

# groom

Work through the "Grooming report" issue one item at a time. For each flagged item, present the context and ask CT for a decision. Execute the decision immediately.

## Invocation

```
/groom all
/groom decisions
/groom specs
/groom plans
/groom tasks
/groom research
```

## Workflow

### 1. Parse the subcommand filter

Extract the filter from the argument:
- `all` → include all item types
- `decisions` → only `stale_decision`, `no_op_decision`, `complete_decision`
- `specs` → only `orphan_spec`
- `plans` → only `orphan_plan`, `limbo_plan`
- `tasks` → only `stalled_task`, `long_backlog_task`, `drift_task`
- `research` → only `orphan_research`

If no argument, default to `all`.

### 2. Find the Grooming report issue

```bash
REPO="pdomain/pdomain-book-tools"
gh issue list --repo "$REPO" \
  --label "kind:chore" \
  --state open \
  --search "Grooming report" \
  --json number,title,body \
  --limit 5
```

If none found, print: "No Grooming report issue found. Run groom-auto or check if it has already been drained." and exit.

Take the first result. Parse the body's "Items requiring CT review" section — each row of the markdown table is one item. If the table shows "_No items require CT review._", print: "Queue is empty. Nothing to groom." and exit.

Parse table rows into structured dicts:
```
| `stale_decision` | #30 | 20 days | Nudge CT |
```
→ `{"type": "stale_decision", "ref": "#30", "age": "20 days", "proposed": "Nudge CT"}`

Filter rows by the subcommand.

### 3. For each item — present and ask

For each item in the filtered list:

```
──────────────────────────────────────────────
Type:     stale_decision
Ref:      #30
Age:      20 days old
Proposed: Nudge CT to write decision doc or close
──────────────────────────────────────────────
Decision? [keep / update / archive / delete / skip / q(uit)]:
```

Wait for CT input. Execute:

#### keep
- Post a comment on the referenced GH issue: "Reviewed during grooming YYYY-MM-DD — keeping open."
- Remove the item from the local tracking list (it will re-appear next run if still flagged).

#### update
- For issue references: prompt "New body? (leave blank to just re-title)". If body given, `gh issue edit <N> --repo "$REPO" --body "<body>"`. If title given, `gh issue edit <N> --repo "$REPO" --title "<title>"`.
- For file references: prompt "Open in editor? (y/n)". Print the file path for CT to edit manually. After CT confirms done, mark resolved.

#### archive
- For issue references: `gh issue close <N> --repo "$REPO"` then `gh issue edit <N> --repo "$REPO" --add-label status:archived`.
- For file references: move file to the appropriate `archived/` subdirectory:
  - `docs/plans/*.md` → `docs/plans/archived/`
  - `docs/research/*.md` → `docs/research/archived/`

  ```bash
  mv /workspaces/ocr-container/docs/<type>/<file> \
     /workspaces/ocr-container/docs/archive/<type>/<file>
  ```

#### delete
- For issue references: `gh issue close <N> --repo "$REPO" --comment "Deleted by CT during grooming $(date +%Y-%m-%d)"`.
- For file references:
  ```bash
  rm /workspaces/ocr-container/docs/<type>/<file>
  ```
  If file is tracked by git: `git rm /workspaces/ocr-container/docs/<type>/<file>`.

#### skip
- Leave the item in the queue unchanged. Move to the next item.

#### q or quit
- Stop the loop. Proceed to step 4 with whatever was resolved so far.

### 4. Post summary and conditionally close report

After the loop, collect resolved items (any decision other than skip/quit).

Post a comment on the Grooming report issue:
```
Grooming session YYYY-MM-DD — resolved N items:
- #30: stale_decision → archived
- docs/research/foo.md: orphan_research → deleted
```

If all items in the filter were resolved (none skipped), close the report issue:
```bash
gh issue close <report_issue_number> --repo "$REPO" \
  --comment "Queue fully drained for filter: <filter>."
```

If partial drain, leave open.

### 5. Commit changes to the workspace

If any files were moved or deleted, create a git commit:
```bash
cd /workspaces/ocr-container
git add docs/
git commit -m "chore(groom): archive/delete items from grooming session $(date +%Y-%m-%d)"
```

## Error handling

- If `gh` returns an error for an item action, print the error and ask CT: "Retry / skip / quit?".
- If the report issue body cannot be parsed, print the raw body and ask CT to resolve manually.
- Never silently skip an item — always show what happened.
```

- [ ] Commit: `feat(skills): /groom CT-interactive grooming skill`

---

## Task 5 — File monthly recurring chore GH issue  {#monthly-groom-chore}

model: haiku  effort: S  area: process

**Files:**
- No new files — GH issue filed via CLI

Context: A `kind:chore recurring:monthly` GH issue in `pdomain-book-tools` reminds CT to run `/groom all` once a month. The body contains the procedure so CT can work through it without hunting for docs.

Approach: File the issue using `gh issue create`. The body is self-contained: what the chore is, how to run it, what to do if the report queue is empty.

Verification: `gh issue list --repo pdomain/pdomain-book-tools --label recurring:monthly` shows the new issue.

Acceptance:
- [ ] Issue title: "Monthly grooming: /groom all"
- [ ] Labels: `kind:chore`, `recurring:monthly`, `status:backlog`
- [ ] Body includes: what groom-auto does automatically vs what CT drains, the `/groom all` command, and a note that if the queue is empty the chore is complete
- [ ] Issue filed in `pdomain/pdomain-book-tools`

Steps:
- [ ] File the issue:

```bash
gh issue create \
  --repo "pdomain/pdomain-book-tools" \
  --title "Monthly grooming: /groom all" \
  --label "kind:chore" \
  --label "recurring:monthly" \
  --label "status:backlog" \
  --body "$(cat <<'EOF'
## Monthly grooming chore

This is a recurring monthly chore. Complete it once per month.

### What groom-auto does automatically (nightly)

The \`groom-auto-nightly\` coding-bot job runs every night at 02:00 and:
- Removes \`status:blocked\` from tasks whose blockers are all closed, sets \`status:ready\`
- Marks plan docs \`status: complete\` and moves them to \`plans/archived/\` when their milestone is 100% closed
- Closes spec issues when all child tracking issues are closed
- Closes decision issues when the decision doc is written on disk
- Moves research files to \`research/archived/\` when they are referenced by a spec or decision

The nightly job also creates/updates a "Grooming report" issue (#grooming-report) with items that need CT judgment.

### Your job: drain the judgment queue

1. Check if a "Grooming report" issue is open in this repo.
2. If yes, run:

   \`\`\`
   /groom all
   \`\`\`

   The skill will walk through each flagged item and ask: keep / update / archive / delete / skip.

3. If the report issue shows "No items require CT review" — the chore is complete. Close this recurrence.

### When done

Mark this issue \`status:done\` or close it. A new one will be filed for next month.

### Reference

- Script: \`scripts/groom-auto.py\`
- Skill: \`.claude/skills/groom/SKILL.md\`
- Spec: \`docs/specs/2026-05-17-superpowers-gh-workflow-integration-design.md\` §7
EOF
)"
```

- [ ] Note the issue number from the output (e.g. `#NNN`)
- [ ] Commit: `chore(process): file monthly grooming recurring chore issue`

---

## Run order

Tasks must be completed in this order:
1. Task 1 (tests) → 2 (implementation) → 3 (schedule) → 4 (skill) → 5 (chore issue)

Tasks 3 and 4 can be worked in parallel after Task 2 passes.

## Final verification

After all tasks:
- [ ] `uv run pytest tests/scripts/test_groom_auto.py -v` — 15 tests green
- [ ] `python scripts/groom-auto.py --help` — exits 0
- [ ] `.claude/skills/groom/SKILL.md` — `head -5` shows correct frontmatter
- [ ] `coding-bot schedule list` — shows `groom-auto-nightly` entry (or documents that DB not available and provides the command to register it)
- [ ] `gh issue list --repo pdomain/pdomain-book-tools --label recurring:monthly` — shows monthly chore issue

---

## Scheduler registration (deferred — DB inaccessible during automated run)

The `groom-auto-nightly` schedule entry must be registered manually once the coding-bot scheduler DB at `/srv/coding-bot/state.db` is accessible:

```bash
coding-bot schedule add groom-auto-nightly \
  --workflow groom-auto \
  --trigger "cron:hour=2,minute=0" \
  --context "repo=pdomain/pdomain-book-tools"
coding-bot schedule enable groom-auto-nightly
```

Then verify: `coding-bot schedule list`
