---
status: complete
---

# coding-bot Plan 2: Workflows (M2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the `gh.py` and `git.py` helpers, then implement and test all four
workflows (`ship-issue`, `style-review`, `style-sweep`, `decompose-spec-auto`)
using the engine built in Plan 1. Also add the `helpers/ci_check.py` module
used by `ship-issue`. Each workflow is tested with `FakeLauncher` scripted
results driving every reachable terminal state.

**Architecture:** Every new file lives under
`src/coding_bot/{workflows,helpers}/`. Workflow state machines declare
transitions and implement `on_enter_*` handlers that call `gh.py`, `git.py`,
`helpers/ci_check.py`, and `launcher.run_backend()`. Tests live in
`tests/workflows/`. No new DB migrations needed — Plan 1's schema covers
everything.

**Reference spec:** `docs/superpowers/specs/2026-05-14-coding-bot-design.md`
sections 9, 13.1 (ci_check only).

**Source reference:** Existing scripts being ported:
- `scripts/ship-issue-{orchestrator,pick,success,failure,escalate,preflight,throttle-check}.sh/.py`
- `scripts/style-review-{orchestrator,detect,apply}.sh/.py`
- `scripts/style-sweep-orchestrator.sh`
- `scripts/decompose-spec-{auto-orchestrator,plan,apply}.sh/.py`

---

## File structure after Plan 2

```
src/coding_bot/
├── gh.py                            # NEW: gh CLI wrapper
├── git.py                           # NEW: git plumbing wrapper
├── helpers/
│   ├── __init__.py                  # NEW
│   └── ci_check.py                  # NEW: run_make_ci + excerpt helper
├── workflows/
│   ├── __init__.py                  # NEW
│   ├── ship_issue.py                # NEW: ShipIssue state machine
│   ├── style_review.py              # NEW: StyleReview state machine
│   ├── style_sweep.py               # NEW: StyleSweep state machine
│   └── decompose_spec_auto.py       # NEW: DecomposeSpecAuto state machine
└── cli.py                           # MODIFIED: register workflow subcommands
tests/
├── unit/
│   ├── test_gh.py                   # NEW
│   └── test_git.py                  # NEW
└── workflows/
    ├── __init__.py                  # NEW
    ├── conftest.py                  # NEW: FakeLauncher fixture
    ├── test_ship_issue.py           # NEW
    ├── test_style_review.py         # NEW
    ├── test_style_sweep.py          # NEW
    └── test_decompose_spec_auto.py  # NEW
```

---

## Phase A — Helpers: `gh.py`, `git.py`, `helpers/ci_check.py`

### Task A.1: `gh.py` — GitHub CLI wrapper

**What it wraps:** All `gh` CLI calls currently scattered across
`ship-issue-pick.py` (`gh issue list`, `gh issue edit`, `gh pr create`,
`gh pr view`, `gh issue comment`), `style-review-orchestrator.sh`
(`gh pr review`), and `decompose-spec-apply.py` (`gh issue create`,
`gh api milestone`).

**Files:**
- Create: `src/coding_bot/gh.py`
- Create: `tests/unit/test_gh.py`

- [ ] **Step 1: Write tests (TDD first)**

`tests/unit/test_gh.py`:

```python
"""Unit tests for gh.py — all gh CLI calls are monkeypatched."""
from __future__ import annotations
import json
import pytest
from unittest.mock import patch, MagicMock
from coding_bot import gh


def _make_run(returncode: int, stdout: str, stderr: str = "") -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def test_issue_list_returns_parsed_json(monkeypatch: pytest.MonkeyPatch) -> None:
    issues = [{"number": 1, "title": "Fix bug", "labels": []}]
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _make_run(0, json.dumps(issues)))
    result = gh.issue_list("org/repo", labels=["status:ready"], limit=10)
    assert result == issues


def test_issue_edit_adds_label(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _make_run(0, ""))
    gh.issue_edit("org/repo", 42, add_labels=["status:in-progress"])


def test_issue_comment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _make_run(0, ""))
    gh.issue_comment("org/repo", 42, "Claimed by ship-issue-0")


def test_issue_create_returns_number(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **kw: _make_run(0, json.dumps({"number": 99, "url": "https://..."})),
    )
    number, url = gh.issue_create("org/repo", title="New issue", body="body")
    assert number == 99


def test_pr_create_returns_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **kw: _make_run(0, json.dumps({"url": "https://github.com/pr/1"})),
    )
    url = gh.pr_create("org/repo", title="Fix", body="", base="main", head="wip/ship-issue")
    assert "pr/1" in url


def test_pr_review_comment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _make_run(0, ""))
    gh.pr_review_comment("org/repo", pr_number=7, body="style comment", event="COMMENT")


def test_gh_error_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "subprocess.run", lambda *a, **kw: _make_run(1, "", "error: not found")
    )
    with pytest.raises(gh.GhError, match="not found"):
        gh.issue_list("org/repo", labels=[], limit=10)


def test_milestone_create_returns_number(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **kw: _make_run(0, json.dumps({"number": 3, "title": "spec: foo"})),
    )
    number = gh.milestone_create("org/repo", title="spec: foo", description="")
    assert number == 3
```

- [ ] **Step 2: Verify failures**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/test_gh.py -x 2>&1 | tail -5
```

Expected: `ModuleNotFoundError` or `ImportError` (file doesn't exist yet).

- [ ] **Step 3: Implement `src/coding_bot/gh.py`**

```python
"""Thin wrapper around the `gh` CLI.

Every call is a simple subprocess.run. No retry logic here — callers handle
errors via GhError. All JSON payloads are parsed before returning.
"""
from __future__ import annotations

import json
import subprocess
from typing import Any


class GhError(RuntimeError):
    pass


def _run(args: list[str], *, json_output: bool = True) -> Any:
    cmd = ["gh"] + args
    if json_output:
        cmd += ["--json", ""]   # caller sets actual fields; overridden per call
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise GhError(result.stderr.strip() or result.stdout.strip())
    if json_output and result.stdout.strip():
        return json.loads(result.stdout)
    return result.stdout


def issue_list(repo: str, *, labels: list[str], limit: int = 50) -> list[dict]:
    label_args = []
    for lbl in labels:
        label_args += ["--label", lbl]
    result = subprocess.run(
        ["gh", "issue", "list", "--repo", repo, "--limit", str(limit),
         "--json", "number,title,body,labels,assignees,milestone,state"]
        + label_args,
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise GhError(result.stderr.strip())
    return json.loads(result.stdout) if result.stdout.strip() else []


def issue_edit(
    repo: str,
    number: int,
    *,
    add_labels: list[str] | None = None,
    remove_labels: list[str] | None = None,
) -> None:
    args = ["gh", "issue", "edit", str(number), "--repo", repo]
    for lbl in add_labels or []:
        args += ["--add-label", lbl]
    for lbl in remove_labels or []:
        args += ["--remove-label", lbl]
    r = subprocess.run(args, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise GhError(r.stderr.strip())


def issue_comment(repo: str, number: int, body: str) -> None:
    r = subprocess.run(
        ["gh", "issue", "comment", str(number), "--repo", repo, "--body", body],
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0:
        raise GhError(r.stderr.strip())


def issue_create(repo: str, *, title: str, body: str, labels: list[str] | None = None,
                 milestone: int | None = None) -> tuple[int, str]:
    args = ["gh", "issue", "create", "--repo", repo,
            "--title", title, "--body", body, "--json", "number,url"]
    for lbl in labels or []:
        args += ["--label", lbl]
    if milestone is not None:
        args += ["--milestone", str(milestone)]
    r = subprocess.run(args, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise GhError(r.stderr.strip())
    data = json.loads(r.stdout)
    return data["number"], data["url"]


def pr_create(
    repo: str, *, title: str, body: str, base: str, head: str,
    draft: bool = False,
) -> str:
    args = ["gh", "pr", "create", "--repo", repo,
            "--title", title, "--body", body, "--base", base, "--head", head,
            "--json", "url"]
    if draft:
        args.append("--draft")
    r = subprocess.run(args, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise GhError(r.stderr.strip())
    return json.loads(r.stdout)["url"]


def pr_view(repo: str, pr_number: int | str) -> dict:
    r = subprocess.run(
        ["gh", "pr", "view", str(pr_number), "--repo", repo,
         "--json", "number,url,state,headRefName,baseRefName,title"],
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0:
        raise GhError(r.stderr.strip())
    return json.loads(r.stdout)


def pr_review_comment(repo: str, pr_number: int, *, body: str,
                      event: str = "COMMENT") -> None:
    r = subprocess.run(
        ["gh", "pr", "review", str(pr_number), "--repo", repo,
         "--body", body, f"--{event.lower()}"],
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0:
        raise GhError(r.stderr.strip())


def milestone_create(repo: str, *, title: str, description: str) -> int:
    r = subprocess.run(
        ["gh", "api", f"repos/{repo}/milestones",
         "--method", "POST",
         "--field", f"title={title}",
         "--field", f"description={description}",
         "--jq", "{number, title}"],
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0:
        raise GhError(r.stderr.strip())
    return json.loads(r.stdout)["number"]
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/test_gh.py -v 2>&1 | tail -15
```

- [ ] **Step 5: Commit**

```
feat(gh): add gh CLI wrapper
```

---

### Task A.2: `git.py` — git plumbing wrapper

**What it wraps:** All `git` calls in `ship-issue-success.sh`
(`git rev-parse HEAD`, `git rebase`, `git push`, `git reset --hard`,
`git add -A`, `git commit`) and `bot-workspace-bootstrap.sh`
(`git fetch`, `git worktree add`).

**Files:**
- Create: `src/coding_bot/git.py`
- Create: `tests/unit/test_git.py`

- [ ] **Step 1: Write tests**

`tests/unit/test_git.py`:

```python
"""Unit tests for git.py — all subprocess.run calls monkeypatched."""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from pathlib import Path
from coding_bot import git


def _ok(stdout: str = "") -> MagicMock:
    m = MagicMock(); m.returncode = 0; m.stdout = stdout; m.stderr = ""
    return m


def _fail(stderr: str = "error") -> MagicMock:
    m = MagicMock(); m.returncode = 1; m.stdout = ""; m.stderr = stderr
    return m


def test_rev_parse(monkeypatch, tmp_path):
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _ok("abc1234\n"))
    assert git.rev_parse(tmp_path, "HEAD") == "abc1234"


def test_push_force_with_lease(monkeypatch, tmp_path):
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _ok())
    git.push(tmp_path, remote="origin", refspec="wip/ship-issue-0:wip/ship-issue-0",
             force_with_lease=True)


def test_rebase_onto(monkeypatch, tmp_path):
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _ok())
    git.rebase(tmp_path, onto="origin/wip/ship-issue")


def test_rebase_conflict_raises(monkeypatch, tmp_path):
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _fail("CONFLICT"))
    with pytest.raises(git.GitConflict):
        git.rebase(tmp_path, onto="origin/wip/ship-issue")


def test_reset_hard(monkeypatch, tmp_path):
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _ok())
    git.reset_hard(tmp_path, ref="HEAD")


def test_add_all_and_commit(monkeypatch, tmp_path):
    calls = []
    def fake_run(args, **kw):
        calls.append(args)
        return _ok()
    monkeypatch.setattr("subprocess.run", fake_run)
    git.add_all(tmp_path)
    git.commit(tmp_path, message="fix: fmt")
    assert any("add" in str(c) for c in calls)
    assert any("commit" in str(c) for c in calls)


def test_fetch(monkeypatch, tmp_path):
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _ok())
    git.fetch(tmp_path, remote="origin")


def test_error_raises_git_error(monkeypatch, tmp_path):
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _fail("fatal: not a repo"))
    with pytest.raises(git.GitError, match="not a repo"):
        git.rev_parse(tmp_path, "HEAD")
```

- [ ] **Step 2: Verify failures**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/test_git.py -x 2>&1 | tail -5
```

- [ ] **Step 3: Implement `src/coding_bot/git.py`**

```python
"""Thin wrapper around the `git` binary.

All git plumbing called by workflows lives here so tests can monkeypatch
subprocess.run in one place.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    pass


class GitConflict(GitError):
    """Raised when a rebase or merge hits a conflict."""


def _run(args: list[str], cwd: Path) -> str:
    r = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, check=False)
    if r.returncode != 0:
        msg = r.stderr.strip() or r.stdout.strip()
        raise GitError(msg)
    return r.stdout.strip()


def rev_parse(cwd: Path, ref: str) -> str:
    return _run(["git", "rev-parse", "--short", ref], cwd)


def fetch(cwd: Path, remote: str = "origin") -> None:
    _run(["git", "fetch", remote], cwd)


def rebase(cwd: Path, onto: str) -> None:
    try:
        _run(["git", "rebase", onto], cwd)
    except GitError as e:
        if "CONFLICT" in str(e) or "conflict" in str(e).lower():
            _run(["git", "rebase", "--abort"], cwd)
            raise GitConflict(str(e)) from e
        raise


def push(
    cwd: Path,
    remote: str,
    refspec: str,
    *,
    force_with_lease: bool = False,
    ff_only: bool = False,
) -> None:
    args = ["git", "push", remote, refspec]
    if force_with_lease:
        args.append("--force-with-lease")
    if ff_only:
        args.append("--ff-only")
    _run(args, cwd)


def reset_hard(cwd: Path, ref: str) -> None:
    _run(["git", "reset", "--hard", ref], cwd)


def add_all(cwd: Path) -> None:
    _run(["git", "add", "-A"], cwd)


def commit(cwd: Path, message: str) -> None:
    _run(["git", "commit", "-m", message], cwd)


def diff_stat(cwd: Path, base: str = "HEAD") -> str:
    r = subprocess.run(
        ["git", "diff", "--stat", base],
        cwd=str(cwd), capture_output=True, text=True, check=False,
    )
    return r.stdout.strip()
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/test_git.py -v 2>&1 | tail -15
```

- [ ] **Step 5: Commit**

```
feat(git): add git plumbing wrapper
```

---

### Task A.3: `helpers/ci_check.py` — run `make ci` and extract excerpt

**Purpose:** Every workflow that calls `make ci` in a pd-* repo goes through
this helper. It captures the filtered failure excerpt from `ai-filter-log.py`
(≤300 lines) into the workflow's ctx rather than the full log, which keeps
tokens manageable when workflows inspect failure context.

**Files:**
- Create: `src/coding_bot/helpers/__init__.py` (empty)
- Create: `src/coding_bot/helpers/ci_check.py`

- [ ] **Step 1: Write tests**

`tests/unit/test_ci_check.py`:

```python
from __future__ import annotations
import subprocess
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from coding_bot.helpers import ci_check


def _ok() -> MagicMock:
    m = MagicMock(); m.returncode = 0; m.stdout = "✅ ci passed (log: .ci-ai.log)"
    m.stderr = ""; return m


def _fail(stdout: str) -> MagicMock:
    m = MagicMock(); m.returncode = 1; m.stdout = stdout; m.stderr = ""; return m


def test_run_make_ci_success(monkeypatch, tmp_path):
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _ok())
    result = ci_check.run_make_ci(tmp_path)
    assert result.passed is True
    assert result.excerpt == ""


def test_run_make_ci_failure_captures_excerpt(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **kw: _fail("❌ ci failed:\nE   AssertionError\n(full log: .ci-ai.log)")
    )
    result = ci_check.run_make_ci(tmp_path)
    assert result.passed is False
    assert "AssertionError" in result.excerpt


def test_run_make_ci_returns_log_path(monkeypatch, tmp_path):
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _ok())
    result = ci_check.run_make_ci(tmp_path)
    assert result.log_path == tmp_path / ".ci-ai.log"
```

- [ ] **Step 2: Implement `src/coding_bot/helpers/ci_check.py`**

```python
"""Run `make ci AI=1` in a pd-* repo and extract the failure excerpt.

The excerpt is ≤300 lines — the same filtered view ai-filter-log.py produces.
Workflows store the excerpt in ctx.ci_failure_excerpt (for quick read) and
the full log path in ctx.ci_failure_log_path (for inspect drill-down).
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CiResult:
    passed: bool
    excerpt: str
    log_path: Path
    raw_stdout: str = field(default="", repr=False)


def run_make_ci(cwd: Path, *, timeout: int = 900) -> CiResult:
    """Run `make ci AI=1` and return a structured result."""
    log_path = cwd / ".ci-ai.log"
    r = subprocess.run(
        ["make", "ci", "AI=1"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    passed = r.returncode == 0
    excerpt = ""
    if not passed:
        # AI=1 wrapper prints: "❌ target failed:\n<excerpt>\n(full log: …)"
        # Extract everything between the first "❌" line and the "(full log:…)" line.
        lines = r.stdout.splitlines()
        capture = False
        captured: list[str] = []
        for line in lines:
            if line.startswith("❌"):
                capture = True
                continue
            if capture and line.startswith("(full log:"):
                break
            if capture:
                captured.append(line)
        excerpt = "\n".join(captured[:300])
    return CiResult(passed=passed, excerpt=excerpt, log_path=log_path, raw_stdout=r.stdout)
```

- [ ] **Step 3: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/test_ci_check.py -v 2>&1 | tail -10
```

- [ ] **Step 4: Commit**

```
feat(helpers): add ci_check.run_make_ci helper
```

---

## Phase B — Workflow: `ship-issue`

### Task B.1: Context + state machine skeleton

**States (from spec §9.1):**
```
throttle_check → picking → claimed → preflight → slicing →
ci_check → pushing → labeling → shipped
```
Plus loop: `escalating ← slicing|ci_check` (retry then escalate or bounce).
Terminal: `shipped`, `bounced`, `throttled`, `no_eligible`.

- [ ] **Step 1: Write workflow test (happy path + terminal states)**

`tests/workflows/conftest.py`:

```python
"""Shared fixtures for workflow tests."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import pytest
from coding_bot.backends.base import AgentRunStats


@dataclass
class FakeLaunchResult:
    run_id: int = 1
    exit_code: int = 0
    duration_ms: int = 100
    text: str = "done"
    timed_out: bool = False


class FakeLauncher:
    """Scripted launcher for workflow tests.

    Script a queue of results; each call to run_backend pops from the front.
    Record all calls so tests can assert on them.
    """

    def __init__(self, results: list[FakeLaunchResult] | None = None) -> None:
        self._queue: list[FakeLaunchResult] = list(results or [])
        self.calls: list[dict[str, Any]] = []

    def run_backend(self, **kwargs: Any) -> FakeLaunchResult:
        self.calls.append(kwargs)
        if not self._queue:
            return FakeLaunchResult()
        return self._queue.pop(0)

    def push(self, result: FakeLaunchResult) -> None:
        self._queue.append(result)
```

`tests/workflows/test_ship_issue.py`:

```python
"""State-machine tests for ship_issue workflow.

All external calls (gh, git, launcher, ci_check) are monkeypatched.
Tests drive every reachable terminal state.
"""
from __future__ import annotations
from pathlib import Path
import pytest
from coding_bot.workflows.ship_issue import ShipIssue, ShipIssueContext
from coding_bot.engine.runner import WorkflowRunner
from coding_bot import gh, git
from coding_bot.helpers import ci_check
from .conftest import FakeLauncher, FakeLaunchResult


def _make_ctx(**overrides) -> ShipIssueContext:
    base = dict(repo="org/repo", slot=0, backend="claude", model="haiku",
                effort="low")
    return ShipIssueContext(**(base | overrides))


# ─── throttle_check ──────────────────────────────────────────────────────────

def test_throttle_check_passes_through(state_db, cost_db, monkeypatch, tmp_path):
    """No open backend_run rows → proceeds to picking."""
    _patch_happy_path(monkeypatch, tmp_path)
    ctx = _make_ctx()
    runner = WorkflowRunner()
    run_id = runner.start("ship-issue", ctx, triggered_by="test")
    assert ctx.terminal == "shipped"


def test_throttle_check_blocks(state_db, cost_db, monkeypatch, tmp_path):
    """Pending cost rows exceed threshold → throttled."""
    monkeypatch.setattr("coding_bot.workflows.ship_issue._over_throttle_limit",
                        lambda ctx: True)
    ctx = _make_ctx()
    runner = WorkflowRunner()
    runner.start("ship-issue", ctx, triggered_by="test")
    assert ctx.terminal == "throttled"


# ─── no eligible issue ───────────────────────────────────────────────────────

def test_no_eligible_issue(state_db, cost_db, monkeypatch):
    monkeypatch.setattr("coding_bot.gh.issue_list", lambda *a, **kw: [])
    ctx = _make_ctx()
    runner = WorkflowRunner()
    runner.start("ship-issue", ctx, triggered_by="test")
    assert ctx.terminal == "no_eligible"


# ─── slice fails → escalates → ships ─────────────────────────────────────────

def test_escalation_then_ship(state_db, cost_db, monkeypatch, tmp_path):
    """First slice attempt exits 1, escalates model, second succeeds."""
    _patch_happy_path(monkeypatch, tmp_path,
                      slice_results=[FakeLaunchResult(exit_code=1, text="failure"),
                                     FakeLaunchResult(exit_code=0, text="ok")])
    ctx = _make_ctx()
    runner = WorkflowRunner()
    runner.start("ship-issue", ctx, triggered_by="test")
    assert ctx.terminal == "shipped"
    assert ctx.escalation_attempt == 1


# ─── ci_check fails → bounces ────────────────────────────────────────────────

def test_ci_failure_bounces(state_db, cost_db, monkeypatch, tmp_path):
    _patch_happy_path(monkeypatch, tmp_path,
                      ci_pass=False, max_escalations=0)
    ctx = _make_ctx()
    runner = WorkflowRunner()
    runner.start("ship-issue", ctx, triggered_by="test")
    assert ctx.terminal == "bounced"


# ─── helpers ─────────────────────────────────────────────────────────────────

def _patch_happy_path(monkeypatch, tmp_path, *,
                      slice_results=None, ci_pass=True, max_escalations=2):
    issue = {"number": 7, "title": "Fix thing", "body": "Spec: none\nAcceptance: - pass",
             "labels": [{"name": "status:ready"}]}
    monkeypatch.setattr("coding_bot.gh.issue_list", lambda *a, **kw: [issue])
    monkeypatch.setattr("coding_bot.gh.issue_edit", lambda *a, **kw: None)
    monkeypatch.setattr("coding_bot.gh.issue_comment", lambda *a, **kw: None)
    monkeypatch.setattr("coding_bot.gh.pr_create", lambda *a, **kw: "https://gh/pr/1")
    monkeypatch.setattr("coding_bot.gh.pr_view", lambda *a, **kw: {"url": "https://gh/pr/1"})
    monkeypatch.setattr("coding_bot.git.rev_parse", lambda *a, **kw: "abc1234")
    monkeypatch.setattr("coding_bot.git.fetch", lambda *a, **kw: None)
    monkeypatch.setattr("coding_bot.git.rebase", lambda *a, **kw: None)
    monkeypatch.setattr("coding_bot.git.push", lambda *a, **kw: None)
    monkeypatch.setattr("coding_bot.git.add_all", lambda *a, **kw: None)
    monkeypatch.setattr("coding_bot.git.commit", lambda *a, **kw: None)
    ci_result = ci_check.CiResult(passed=ci_pass, excerpt="", log_path=tmp_path / ".log")
    monkeypatch.setattr("coding_bot.helpers.ci_check.run_make_ci", lambda *a, **kw: ci_result)
    monkeypatch.setattr("coding_bot.workflows.ship_issue._worktree_path",
                        lambda ctx: tmp_path)
    if slice_results:
        results_iter = iter(slice_results)
        monkeypatch.setattr("coding_bot.launcher.run_backend",
                            lambda **kw: next(results_iter))
```

- [ ] **Step 2: Verify failures (import errors expected)**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/workflows/test_ship_issue.py -x 2>&1 | tail -5
```

- [ ] **Step 3: Create `src/coding_bot/workflows/__init__.py`** (empty)

- [ ] **Step 4: Implement `src/coding_bot/workflows/ship_issue.py`**

Port the logic from `scripts/ship-issue-pick.py` (eligibility check, claim,
race-check), `scripts/ship-issue-throttle-check.sh` (budget guard),
`scripts/ship-issue-preflight.sh` (worktree setup, pre_claim_sha capture),
`scripts/ship-issue-success.sh` (ci, push, PR create/update),
`scripts/ship-issue-failure.sh` (reset, label swap),
`scripts/ship-issue-escalate.sh` (model escalation ladder).

```python
"""ship-issue workflow.

State machine mirroring the ship-issue bash/python scripts. All external
calls (gh, git, ci_check, launcher) are injected so tests can monkeypatch.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from coding_bot import gh, git, launcher
from coding_bot.engine.workflow import Workflow, workflow
from coding_bot.engine.policies import LADDERS
from coding_bot.helpers.ci_check import run_make_ci


@dataclass
class ShipIssueContext:
    repo: str
    slot: int
    backend: str = "claude"
    model: str = "haiku"
    effort: str = "low"
    issue: int | None = None
    pre_claim_sha: str | None = None
    worktree: Path | None = None
    slice_exit: int | None = None
    pr_url: str | None = None
    escalation_attempt: int = 0
    ci_failure_log_path: Path | None = None
    ci_failure_excerpt: str | None = None
    terminal: str = ""


_THROTTLE_PENDING_LIMIT = 3       # max concurrent backend runs before blocking
_RACE_CHECK_WAIT_SECS = 2         # wait before checking for competing claims
_SLICE_PROMPT = "/ship-issue"
_INTEGRATION_BRANCH = "wip/ship-issue"
_MAX_ESCALATIONS = 2


def _over_throttle_limit(ctx: ShipIssueContext) -> bool:
    """Check cost.db for pending (no ended_at) rows for this backend."""
    from coding_bot import db
    import sqlalchemy as sa
    with db.cost_session() as session:
        count = session.execute(
            sa.select(sa.func.count()).select_from(db.BackendRun)
            .where(db.BackendRun.ended_at.is_(None))
            .where(db.BackendRun.backend == ctx.backend)
        ).scalar_one()
    return count >= _THROTTLE_PENDING_LIMIT


def _pick_eligible_issue(ctx: ShipIssueContext) -> dict | None:
    """Return the highest-priority eligible issue, or None."""
    issues = gh.issue_list(ctx.repo, labels=["status:ready"], limit=50)
    issues = [i for i in issues if _is_eligible(i)]
    if not issues:
        return None
    # sort by priority label (p0 > p1 > p2 > unprioritized)
    return sorted(issues, key=_priority_rank)[0]


def _is_eligible(issue: dict) -> bool:
    label_names = {lb["name"] for lb in issue.get("labels", [])}
    if "bot:ship-issue-ready" not in label_names:
        return False
    if "status:blocked" in label_names:
        return False
    if "status:in-progress" in label_names:
        return False
    if "status:in-pr" in label_names:
        return False
    return True


def _priority_rank(issue: dict) -> int:
    label_names = {lb["name"] for lb in issue.get("labels", [])}
    for rank, lbl in enumerate(["priority:p0", "priority:p1", "priority:p2"]):
        if lbl in label_names:
            return rank
    return 99


def _worktree_path(ctx: ShipIssueContext) -> Path:
    repo_name = ctx.repo.split("/")[-1]
    return Path(f"/srv/bot-workspaces/ship-issue-{ctx.slot}/{repo_name}")


def _wip_branch(ctx: ShipIssueContext) -> str:
    return f"wip/ship-issue-{ctx.slot}"


def _build_slice_prompt(ctx: ShipIssueContext) -> str:
    return _SLICE_PROMPT


@workflow(name="ship-issue", context_class=ShipIssueContext)
class ShipIssue(Workflow):
    states = [
        "throttle_check", "picking", "claimed", "preflight",
        "slicing", "escalating", "ci_check", "pushing", "labeling",
        "shipped", "bounced", "throttled", "no_eligible",
    ]
    initial = "throttle_check"
    terminal = {"shipped", "bounced", "throttled", "no_eligible"}
    transitions = [
        ("ok",          "throttle_check", "picking"),
        ("throttle",    "throttle_check", "throttled"),
        ("found",       "picking",        "claimed"),
        ("none_found",  "picking",        "no_eligible"),
        ("ready",       "claimed",        "preflight"),
        ("preflighted", "preflight",      "slicing"),
        ("slice_ok",    "slicing",        "ci_check"),
        ("escalate",    "slicing",        "escalating"),
        ("retry",       "escalating",     "slicing"),
        ("bounce",      "escalating",     "bounced"),
        ("ci_ok",       "ci_check",       "pushing"),
        ("ci_fail",     "ci_check",       "escalating"),
        ("pushed",      "pushing",        "labeling"),
        ("labeled",     "labeling",       "shipped"),
        ("bounce",      "pushing",        "bounced"),
    ]

    def on_enter_throttle_check(self, ctx: ShipIssueContext) -> None:
        if _over_throttle_limit(ctx):
            self.throttle()
        else:
            self.ok()

    def on_enter_picking(self, ctx: ShipIssueContext) -> None:
        issue = _pick_eligible_issue(ctx)
        if issue is None:
            self.none_found()
            return
        ctx.issue = issue["number"]
        # Claim: add status:in-progress, remove status:ready
        gh.issue_edit(ctx.repo, ctx.issue,
                      add_labels=["status:in-progress"],
                      remove_labels=["status:ready"])
        gh.issue_comment(ctx.repo, ctx.issue,
                         f"Claimed by ship-issue-{ctx.slot}")
        # Race check
        time.sleep(_RACE_CHECK_WAIT_SECS)
        self.found()

    def on_enter_claimed(self, ctx: ShipIssueContext) -> None:
        self.ready()

    def on_enter_preflight(self, ctx: ShipIssueContext) -> None:
        worktree = _worktree_path(ctx)
        git.fetch(worktree)
        ctx.pre_claim_sha = git.rev_parse(worktree, "HEAD")
        ctx.worktree = worktree
        self.preflighted()

    def on_enter_slicing(self, ctx: ShipIssueContext) -> None:
        assert ctx.worktree is not None
        result = launcher.run_backend(
            backend=ctx.backend,
            prompt=_build_slice_prompt(ctx),
            model=ctx.model,
            effort=ctx.effort,
            cwd=ctx.worktree,
            task_label=f"ship-issue.{ctx.repo}.slot{ctx.slot}",
            repo=ctx.repo,
            slot=ctx.slot,
        )
        ctx.slice_exit = result.exit_code
        if result.exit_code == 0:
            self.slice_ok()
        else:
            self.escalate()

    def on_enter_escalating(self, ctx: ShipIssueContext) -> None:
        if ctx.escalation_attempt >= _MAX_ESCALATIONS:
            self.bounce()
            return
        ladder = LADDERS.get(ctx.backend, [])
        current_idx = next(
            (i for i, (m, e) in enumerate(ladder)
             if m == ctx.model and e == ctx.effort),
            None
        )
        if current_idx is None or current_idx + 1 >= len(ladder):
            self.bounce()
            return
        ctx.model, ctx.effort = ladder[current_idx + 1]
        ctx.escalation_attempt += 1
        self.retry()

    def on_enter_ci_check(self, ctx: ShipIssueContext) -> None:
        assert ctx.worktree is not None
        result = run_make_ci(ctx.worktree)
        if result.passed:
            self.ci_ok()
        else:
            ctx.ci_failure_excerpt = result.excerpt
            ctx.ci_failure_log_path = result.log_path
            self.ci_fail()

    def on_enter_pushing(self, ctx: ShipIssueContext) -> None:
        assert ctx.worktree is not None
        wip = _wip_branch(ctx)
        try:
            git.fetch(ctx.worktree)
            git.rebase(ctx.worktree, onto=f"origin/{_INTEGRATION_BRANCH}")
            git.push(ctx.worktree, remote="origin",
                     refspec=f"{wip}:{_INTEGRATION_BRANCH}",
                     force_with_lease=True)
        except Exception:
            self.bounce()
            return
        # Create or update rolling PR
        try:
            ctx.pr_url = gh.pr_create(
                ctx.repo, title="wip: ship-issue rolling PR",
                body="", base="main", head=_INTEGRATION_BRANCH, draft=True
            )
        except gh.GhError:
            pr = gh.pr_view(ctx.repo, "wip/ship-issue")
            ctx.pr_url = pr.get("url", "")
        self.pushed()

    def on_enter_labeling(self, ctx: ShipIssueContext) -> None:
        if ctx.issue:
            gh.issue_edit(ctx.repo, ctx.issue,
                          add_labels=["status:in-pr"],
                          remove_labels=["status:in-progress"])
        self.labeled()

    def on_enter_shipped(self, ctx: ShipIssueContext) -> None:
        ctx.terminal = "shipped"

    def on_enter_bounced(self, ctx: ShipIssueContext) -> None:
        if ctx.issue:
            gh.issue_edit(ctx.repo, ctx.issue,
                          add_labels=["status:ready"],
                          remove_labels=["status:in-progress"])
        ctx.terminal = "bounced"

    def on_enter_throttled(self, ctx: ShipIssueContext) -> None:
        ctx.terminal = "throttled"

    def on_enter_no_eligible(self, ctx: ShipIssueContext) -> None:
        ctx.terminal = "no_eligible"
```

- [ ] **Step 5: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/workflows/test_ship_issue.py -v 2>&1 | tail -20
```

- [ ] **Step 6: Commit**

```
feat(workflows): add ship-issue state machine
```

---

## Phase C — Workflow: `style-review`

### Task C.1: `style-review` state machine

**States (spec §9.2):**
```
read_tag → compute_diff → detecting → applying → commenting →
advancing_tag → done
```
Terminal: `done`, `no_diff`, `errored`.

- [ ] **Step 1: Write tests**

`tests/workflows/test_style_review.py`:

```python
"""State-machine tests for style_review workflow."""
from __future__ import annotations
from pathlib import Path
import pytest
from coding_bot.workflows.style_review import StyleReview, StyleReviewContext
from coding_bot.engine.runner import WorkflowRunner
from coding_bot import gh, git


def _make_ctx(**kw) -> StyleReviewContext:
    return StyleReviewContext(repo="org/repo", pr_number=5,
                              worktree=Path("/tmp/sr"), **kw)


def test_no_diff_terminal(state_db, cost_db, monkeypatch):
    monkeypatch.setattr("coding_bot.git.diff_stat", lambda *a, **kw: "")
    monkeypatch.setattr("coding_bot.workflows.style_review._read_tag", lambda *a: "abc")
    ctx = _make_ctx()
    runner = WorkflowRunner()
    runner.start("style-review", ctx, triggered_by="test")
    assert ctx.terminal == "no_diff"


def test_happy_path(state_db, cost_db, monkeypatch, tmp_path):
    monkeypatch.setattr("coding_bot.git.diff_stat", lambda *a, **kw: "1 file changed")
    monkeypatch.setattr("coding_bot.workflows.style_review._read_tag", lambda *a: "abc")
    monkeypatch.setattr("coding_bot.workflows.style_review._write_tag", lambda *a: None)
    import json
    fake_findings = json.dumps({
        "high_confidence": [{"file": "a.py", "patch": "s/foo/bar/"}],
        "comments": []
    })
    monkeypatch.setattr("coding_bot.launcher.run_backend",
                        lambda **kw: type("R", (), {"exit_code": 0, "text": fake_findings,
                                                    "run_id": 1, "timed_out": False})())
    monkeypatch.setattr("coding_bot.workflows.style_review._apply_patches",
                        lambda *a, **kw: True)
    monkeypatch.setattr("coding_bot.gh.pr_review_comment", lambda *a, **kw: None)
    ctx = _make_ctx()
    runner = WorkflowRunner()
    runner.start("style-review", ctx, triggered_by="test")
    assert ctx.terminal == "done"
```

- [ ] **Step 2: Verify failures**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/workflows/test_style_review.py -x 2>&1 | tail -5
```

- [ ] **Step 3: Implement `src/coding_bot/workflows/style_review.py`**

Port logic from `scripts/style-review-{orchestrator,detect,apply}.sh/.py`.
Tag file is `style-review/<repo>.tag` (a SHA stored in `/srv/coding-bot/`).
Detect call sends unified diff to the backend; apply call patches files and
runs `make ci` with revert-on-failure per batch.

Key functions to port:
- `_read_tag(repo, pr_number)` — reads the tag SHA from state dir
- `_write_tag(repo, pr_number, sha)` — updates the tag
- `_compute_diff(worktree, base_sha)` — `git diff <tag>..HEAD`
- `_apply_patches(worktree, patches, ci_fn)` — deterministic apply + ci + revert

Full implementation follows the same pattern as `ship_issue.py` — state
handlers call helpers, transitions happen via `self.<trigger>()`.

- [ ] **Step 4: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/workflows/test_style_review.py -v 2>&1 | tail -15
```

- [ ] **Step 5: Commit**

```
feat(workflows): add style-review state machine
```

---

## Phase D — Workflow: `style-sweep`

### Task D.1: `style-sweep` state machine

**States (spec §9.3):**
```
reset_branch → scoping → detecting → applying → opening_pr → done
         ↓ (fan-out branch, v0.1 feature-flagged off)
     partitioning → fan_out_detecting
```
Terminal: `done`, `no_findings`, `errored`.
Fan-out feature flag: `ctx.fan_out_enabled = False` in v0.1 — the
`partitioning` and `fan_out_detecting` states are present but the
`scoping → partitioning` transition is never taken.

- [ ] **Step 1: Write tests**

`tests/workflows/test_style_sweep.py`:

```python
"""State-machine tests for style_sweep workflow."""
from __future__ import annotations
from pathlib import Path
import pytest
from coding_bot.workflows.style_sweep import StyleSweep, StyleSweepContext
from coding_bot.engine.runner import WorkflowRunner


def _make_ctx(**kw) -> StyleSweepContext:
    return StyleSweepContext(repo="org/repo", worktree=Path("/tmp/ss"), **kw)


def test_no_findings_terminal(state_db, cost_db, monkeypatch):
    monkeypatch.setattr("coding_bot.git.reset_hard", lambda *a, **kw: None)
    monkeypatch.setattr("coding_bot.git.fetch", lambda *a, **kw: None)
    monkeypatch.setattr("coding_bot.git.diff_stat", lambda *a, **kw: "")
    monkeypatch.setattr("coding_bot.launcher.run_backend",
                        lambda **kw: type("R", (), {"exit_code": 0,
                                                    "text": '{"high_confidence":[],"comments":[]}',
                                                    "run_id": 1, "timed_out": False})())
    ctx = _make_ctx()
    runner = WorkflowRunner()
    runner.start("style-sweep", ctx, triggered_by="test")
    assert ctx.terminal == "no_findings"


def test_happy_path_opens_pr(state_db, cost_db, monkeypatch, tmp_path):
    import json
    monkeypatch.setattr("coding_bot.git.reset_hard", lambda *a, **kw: None)
    monkeypatch.setattr("coding_bot.git.fetch", lambda *a, **kw: None)
    monkeypatch.setattr("coding_bot.git.diff_stat", lambda *a, **kw: "1 file changed")
    monkeypatch.setattr("coding_bot.launcher.run_backend",
                        lambda **kw: type("R", (), {
                            "exit_code": 0,
                            "text": json.dumps({"high_confidence": [{"file": "a.py",
                                                                      "patch": ""}],
                                                "comments": []}),
                            "run_id": 1, "timed_out": False
                        })())
    monkeypatch.setattr("coding_bot.workflows.style_sweep._apply_findings",
                        lambda *a, **kw: True)
    monkeypatch.setattr("coding_bot.gh.pr_create", lambda *a, **kw: "https://gh/pr/2")
    ctx = _make_ctx()
    runner = WorkflowRunner()
    runner.start("style-sweep", ctx, triggered_by="test")
    assert ctx.terminal == "done"
    assert ctx.pr_url == "https://gh/pr/2"
```

- [ ] **Step 2: Verify failures**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/workflows/test_style_sweep.py -x 2>&1 | tail -5
```

- [ ] **Step 3: Implement `src/coding_bot/workflows/style_sweep.py`**

Port from `scripts/style-sweep-orchestrator.sh`. Reuse `_apply_patches` from
`style_review` at the module level (import and call directly — the apply
logic is identical). The `fan_out_detecting` and `partitioning` states are
present in the state machine but the `scoping` handler only takes the
single-shot path when `ctx.fan_out_enabled is False`.

- [ ] **Step 4: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/workflows/test_style_sweep.py -v 2>&1 | tail -15
```

- [ ] **Step 5: Commit**

```
feat(workflows): add style-sweep state machine (fan-out feature-flagged off)
```

---

## Phase E — Workflow: `decompose-spec-auto`

### Task E.1: `decompose-spec-auto` state machine

**States (spec §9.4):**
```
find_next_spec → extract_spec_path → planning → applying → done
```
Terminal: `done`, `nothing_to_do`, `errored`.

The planning step calls `coding_bot.helpers.spec_plan.propose_children(...)`
(a thin Python wrapper around the existing `decompose-spec-plan.py` logic —
see Task E.2). It only calls `launcher.run_backend` when the helper needs
LLM assistance (i.e., it's a Python-first planner with an LLM fallback, not
a pure LLM call).

- [ ] **Step 1: Write tests**

`tests/workflows/test_decompose_spec_auto.py`:

```python
"""State-machine tests for decompose_spec_auto workflow."""
from __future__ import annotations
import pytest
from pathlib import Path
from coding_bot.workflows.decompose_spec_auto import (
    DecomposeSpecAuto, DecomposeSpecAutoContext
)
from coding_bot.engine.runner import WorkflowRunner


def _make_ctx(**kw) -> DecomposeSpecAutoContext:
    return DecomposeSpecAutoContext(repo="org/repo", **kw)


def test_nothing_to_do(state_db, cost_db, monkeypatch):
    monkeypatch.setattr("coding_bot.workflows.decompose_spec_auto._find_next_spec_issue",
                        lambda repo: None)
    ctx = _make_ctx()
    runner = WorkflowRunner()
    runner.start("decompose-spec-auto", ctx, triggered_by="test")
    assert ctx.terminal == "nothing_to_do"


def test_happy_path(state_db, cost_db, monkeypatch):
    spec_issue = {"number": 10, "title": "spec: geometry",
                  "body": "Spec: docs/specs/08-geometry.md\n"}
    monkeypatch.setattr(
        "coding_bot.workflows.decompose_spec_auto._find_next_spec_issue",
        lambda repo: spec_issue,
    )
    monkeypatch.setattr(
        "coding_bot.helpers.spec_plan.propose_children",
        lambda *a, **kw: [{"title": "Add repr", "body": ""}],
    )
    monkeypatch.setattr("coding_bot.gh.issue_create",
                        lambda *a, **kw: (11, "https://gh/issue/11"))
    monkeypatch.setattr("coding_bot.gh.milestone_create",
                        lambda *a, **kw: 3)
    ctx = _make_ctx()
    runner = WorkflowRunner()
    runner.start("decompose-spec-auto", ctx, triggered_by="test")
    assert ctx.terminal == "done"
    assert ctx.children_created == [11]
```

- [ ] **Step 2: Verify failures**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/workflows/test_decompose_spec_auto.py -x 2>&1 | tail -5
```

- [ ] **Step 3: Add `helpers/spec_plan.py` stub**

```python
"""Propose child issues for a spec — Python-first, LLM fallback.

v0.1: thin wrapper calling the existing decompose-spec-plan.py logic as a
subprocess. Full port (Python module) in Plan 4.
"""
from __future__ import annotations
import json
import subprocess
from pathlib import Path


def propose_children(spec_path: Path, repo: str) -> list[dict]:
    """Return a list of {'title': ..., 'body': ...} dicts for child issues."""
    r = subprocess.run(
        ["uv", "run", "/workspaces/ocr-container/scripts/decompose-spec-plan.py",
         str(spec_path), "--repo", repo, "--output-json"],
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0 or not r.stdout.strip():
        return []
    return json.loads(r.stdout)
```

- [ ] **Step 4: Implement `src/coding_bot/workflows/decompose_spec_auto.py`**

Port from `scripts/decompose-spec-auto-orchestrator.sh` and
`scripts/decompose-spec-{plan,apply}.py`. The `planning` state calls
`helpers.spec_plan.propose_children`; `applying` iterates the children and
calls `gh.issue_create` + `gh.milestone_create`.

- [ ] **Step 5: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/workflows/test_decompose_spec_auto.py -v 2>&1 | tail -15
```

- [ ] **Step 6: Commit**

```
feat(workflows): add decompose-spec-auto state machine
```

---

## Phase F — CLI wiring + final CI

### Task F.1: Register workflow subcommands in `cli.py`

Add `coding-bot ship-issue run --repo R --slot N` and peers so workflows
can be triggered manually without the scheduler.

- [ ] **Step 1: Add subcommand stubs to `cli.py`**

```python
# in cli.py, after existing subcommands:
@app.command("ship-issue")
def cmd_ship_issue(
    repo: str = typer.Option(..., help="org/repo"),
    slot: int = typer.Option(0, help="slot number"),
    backend: str = typer.Option("claude"),
    model: str = typer.Option("haiku"),
) -> None:
    """Run one ship-issue cycle."""
    from coding_bot.engine.runner import WorkflowRunner
    from coding_bot.workflows.ship_issue import ShipIssueContext
    ctx = ShipIssueContext(repo=repo, slot=slot, backend=backend, model=model)
    runner = WorkflowRunner()
    run_id = runner.start("ship-issue", ctx, triggered_by=f"cli:{os.getenv('USER','?')}")
    rich.print(f"run {run_id}: {ctx.terminal}")
```

Add similar thin commands for `style-review`, `style-sweep`, `decompose-spec-auto`.

- [ ] **Step 2: Verify import works**

```bash
cd /workspaces/ocr-container/coding-bot
uv run coding-bot --help 2>&1 | grep -E "ship-issue|style-review|style-sweep|decompose"
```

- [ ] **Step 3: Commit**

```
feat(cli): wire workflow subcommands (ship-issue, style-review, style-sweep, decompose-spec-auto)
```

---

### Task F.2: Full `make ci` + tag

- [ ] **Step 1: Run full CI**

```bash
cd /workspaces/ocr-container/coding-bot
make ci AI=1
```

Expected: `✅ ci passed`.

- [ ] **Step 2: Tag v0.2-m2**

```bash
cd /workspaces/ocr-container/coding-bot
git tag v0.2-m2
```

- [ ] **Step 3: Print final state**

```bash
cd /workspaces/ocr-container/coding-bot
git log --oneline | head -10
git tag
uv run coding-bot version
```

---

## Acceptance criteria

1. `make ci AI=1` exits 0 — all unit + workflow tests pass, ruff + mypy clean.
2. Every workflow reaches every terminal state in tests (`shipped`, `bounced`,
   `throttled`, `no_eligible` for ship-issue; `done`, `no_diff` for
   style-review; `done`, `no_findings` for style-sweep; `done`,
   `nothing_to_do` for decompose-spec-auto).
3. `coding-bot ship-issue --help` prints without error.
4. Tag `v0.2-m2` exists.
5. No bash scripts were modified — this plan only adds Python.
