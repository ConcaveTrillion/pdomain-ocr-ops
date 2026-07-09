---
status: complete
---

# ship-issue: wip-maintenance + per-issue ladders + preflight rebase — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the ship-issue workflow with per-issue escalation ladders, preflight rebase onto main, and a wip-branch maintenance mode that detects drift, rebases, CI-checks, and auto-files blocking issues on failure.

**Architecture:** Nine sequential tasks — two standalone (git primitive, ladder definitions), one structural scaffolding task, three helper/new-handler tasks, and three update-existing-handler tasks. Each task leaves tests green. The wip maintenance lock uses `coding_bot.locks.exclusive_lock` (flock, already in the codebase) rather than a new DB table — the entire maintenance state chain runs synchronously inside a single `with exclusive_lock(...)` block in `on_enter_checking_wip`, so the lock is automatically released on completion or crash.

**Tech Stack:** Python, `fcntl.flock` via `coding_bot.locks`, `gh` CLI, `git` CLI, `make ci`, pytest + monkeypatch.

> **Spec deviation:** The spec proposed a `WipRebaseLock` SQLAlchemy table. The plan uses `coding_bot.locks.exclusive_lock` (already in the codebase) instead — flock is crash-safe (auto-releases on process death), requires no migration, and fits naturally since the entire maintenance chain runs synchronously.

> **Pre-flight GitHub task (not in code):** Create the `effort:XL` and `bot:blocks-all` labels on all `pd-*` repos before enabling the new picking logic in production. Use: `gh label create "effort:XL" --repo <repo> --description "Extra-large / opus-only" --color d93f0b` and `gh label create "bot:blocks-all" --repo <repo> --description "Open issue halts all normal bot picking" --color b60205`.

**Spec:** `docs/superpowers/specs/2026-05-14-ship-issue-wip-maintenance-design.md`

---

## File map

| File | Change |
|---|---|
| `src/coding_bot/git.py` | Add `is_behind` |
| `src/coding_bot/engine/policies.py` | Add 5 per-issue ladders; update test that asserts exact key count |
| `src/coding_bot/workflows/ship_issue.py` | ShipIssueContext fields; states/transitions/terminal; stub + real `on_enter_checking_wip`; new maintenance handlers; updated preflight/picking/escalating; new helpers |
| `tests/unit/test_git.py` | Add `is_behind` tests |
| `tests/unit/test_policies.py` | Update key-count test; add per-issue ladder tests |
| `tests/workflows/test_ship_issue.py` | Patch new git functions in `_patch_all_externals`; update escalation test |
| `tests/workflows/test_ship_issue_wip.py` | New — integration tests for maintenance path |
| `tests/unit/workflows/test_ship_issue_helpers.py` | New — unit tests for helper functions |

---

## Task 1: git.is_behind primitive

**Files:**
- Modify: `src/coding_bot/git.py`
- Modify: `tests/unit/test_git.py`

- [ ] **Write the failing tests**

Append to `tests/unit/test_git.py`:

```python
def test_is_behind_when_behind(monkeypatch, tmp_path):
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _fail(""))
    assert git.is_behind(tmp_path, branch="origin/wip/ship-issue", ref="origin/main") is True


def test_is_behind_when_current(monkeypatch, tmp_path):
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _ok())
    assert git.is_behind(tmp_path, branch="origin/wip/ship-issue", ref="origin/main") is False
```

- [ ] **Run tests to verify they fail**

```
uv run pytest tests/unit/test_git.py::test_is_behind_when_behind tests/unit/test_git.py::test_is_behind_when_current -v
```

Expected: `AttributeError: module 'coding_bot.git' has no attribute 'is_behind'`

- [ ] **Implement `is_behind` in `src/coding_bot/git.py`**

Add after `reset_hard`:

```python
def is_behind(cwd: Path, *, branch: str, ref: str) -> bool:
    """Return True if branch is missing commits present in ref.

    Uses git merge-base --is-ancestor <ref> <branch>:
      exit 0 = ref IS ancestor of branch (branch is current)
      exit 1 = ref is NOT ancestor of branch (branch is behind)
    """
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ref, branch],
        capture_output=True,
        check=False,
        cwd=cwd,
    )
    return result.returncode != 0
```

- [ ] **Run tests to verify they pass**

```
uv run pytest tests/unit/test_git.py -v
```

Expected: all pass.

- [ ] **Commit**

```bash
git add src/coding_bot/git.py tests/unit/test_git.py
git commit -m "feat(git): add is_behind primitive"
```

---

## Task 2: Per-issue escalation ladders in policies.py

**Files:**
- Modify: `src/coding_bot/engine/policies.py`
- Modify: `tests/unit/test_policies.py`

- [ ] **Update the failing test and add new ones**

In `tests/unit/test_policies.py`, replace `test_ladders_have_three_backends` and add new tests:

```python
def test_ladders_contain_backend_and_per_issue_keys() -> None:
    assert {"claude", "codex", "grok"} <= set(LADDERS.keys())
    assert {"claude:small", "claude:medium", "claude:large", "claude:xlarge", "claude:blocker"} <= set(LADDERS.keys())


def test_claude_small_starts_at_haiku_low() -> None:
    l = LADDERS["claude:small"]
    assert l.rungs[0] == ("haiku", "low")
    assert l.next("sonnet", "high") == ("opus", "high")
    assert l.next("opus", "high") is None


def test_claude_medium_starts_at_sonnet_medium() -> None:
    l = LADDERS["claude:medium"]
    assert l.rungs[0] == ("sonnet", "medium")
    assert l.next("sonnet", "medium") == ("sonnet", "high")
    assert l.next("sonnet", "high") == ("opus", "high")
    assert l.next("opus", "high") is None


def test_claude_large_starts_at_sonnet_high() -> None:
    l = LADDERS["claude:large"]
    assert l.rungs[0] == ("sonnet", "high")
    assert l.next("sonnet", "high") == ("opus", "high")
    assert l.next("opus", "high") is None


def test_claude_xlarge_is_opus_only() -> None:
    l = LADDERS["claude:xlarge"]
    assert l.rungs == (("opus", "high"),)
    assert l.next("opus", "high") is None


def test_claude_blocker_ladder() -> None:
    l = LADDERS["claude:blocker"]
    assert l.rungs[0] == ("sonnet", "medium")
    assert l.next("sonnet", "medium") == ("sonnet", "high")
    assert l.next("sonnet", "high") == ("opus", "high")
    assert l.next("opus", "high") is None
```

- [ ] **Run tests to verify new ones fail**

```
uv run pytest tests/unit/test_policies.py -v
```

Expected: new tests fail with `KeyError`.

- [ ] **Add per-issue ladders to `src/coding_bot/engine/policies.py`**

Replace the `LADDERS` dict (keep existing entries, add five new ones):

```python
LADDERS: dict[str, EscalationLadder] = {
    "claude": EscalationLadder(
        "claude",
        (("haiku", "low"), ("sonnet", "medium"), ("opus", "high")),
    ),
    "codex": EscalationLadder(
        "codex",
        (("gpt-4.1-mini", "low"), ("o4-mini", "medium"), ("gpt-5-codex", "high")),
    ),
    "grok": EscalationLadder(
        "grok",
        (("grok-code-fast-1", "low"), ("grok-4", "medium"), ("grok-4", "high")),
    ),
    "claude:small": EscalationLadder(
        "claude:small",
        (("haiku", "low"), ("sonnet", "medium"), ("sonnet", "high"), ("opus", "high")),
    ),
    "claude:medium": EscalationLadder(
        "claude:medium",
        (("sonnet", "medium"), ("sonnet", "high"), ("opus", "high")),
    ),
    "claude:large": EscalationLadder(
        "claude:large",
        (("sonnet", "high"), ("opus", "high")),
    ),
    "claude:xlarge": EscalationLadder(
        "claude:xlarge",
        (("opus", "high"),),
    ),
    "claude:blocker": EscalationLadder(
        "claude:blocker",
        (("sonnet", "medium"), ("sonnet", "high"), ("opus", "high")),
    ),
}
```

- [ ] **Run tests to verify they pass**

```
uv run pytest tests/unit/test_policies.py -v
```

Expected: all pass.

- [ ] **Commit**

```bash
git add src/coding_bot/engine/policies.py tests/unit/test_policies.py
git commit -m "feat(policies): add per-issue escalation ladders (claude:small/medium/large/xlarge/blocker)"
```

---

## Task 3: ShipIssueContext fields + workflow struct + test scaffolding

**Files:**
- Modify: `src/coding_bot/workflows/ship_issue.py`
- Modify: `tests/workflows/test_ship_issue.py`

This task makes structural changes and installs a stub `on_enter_checking_wip` so existing tests continue to pass. Task 5 replaces the stub with the real implementation.

- [ ] **Add new fields to `ShipIssueContext`**

In `ship_issue.py`, update the `ShipIssueContext` dataclass (add after `terminal`):

```python
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
    ladder_key: str = "claude"      # key into LADDERS; default preserves legacy behaviour
    blocker_mode: bool = False       # True when picked issue carries bot:blocks-all
```

- [ ] **Update `ShipIssueWorkflow.states`**

```python
states: ClassVar[list[str]] = [
    "throttle_check",
    "picking",
    "claimed",
    "preflight",
    "slicing",
    "ci_check",
    "pushing",
    "labeling",
    "shipped",
    "bounced",
    "throttled",
    "no_eligible",
    "escalating",
    "checking_wip",
    "rebasing_wip",
    "ci_check_wip",
    "wip_updated",
]
```

- [ ] **Update `ShipIssueWorkflow.initial` and `terminal`**

`initial` stays `"throttle_check"`.

```python
terminal: ClassVar[set[str]] = {"shipped", "bounced", "throttled", "no_eligible", "wip_updated"}
```

- [ ] **Replace `ShipIssueWorkflow.transitions`**

```python
transitions: ClassVar[list[tuple[str, str, str]]] = [
    # throttle_check
    ("ok",            "throttle_check", "checking_wip"),
    ("throttle",      "throttle_check", "throttled"),
    # checking_wip
    ("wip_current",   "checking_wip",   "picking"),
    ("wip_behind",    "checking_wip",   "rebasing_wip"),
    ("throttle",      "checking_wip",   "throttled"),
    # picking
    ("found",         "picking",        "claimed"),
    ("none_found",    "picking",        "no_eligible"),
    # claimed
    ("ready",         "claimed",        "preflight"),
    # preflight (bounce path added)
    ("preflighted",   "preflight",      "slicing"),
    ("bounce",        "preflight",      "bounced"),
    # slicing
    ("slice_ok",      "slicing",        "ci_check"),
    ("escalate",      "slicing",        "escalating"),
    # escalating
    ("retry",         "escalating",     "slicing"),
    ("bounce",        "escalating",     "bounced"),
    # ci_check
    ("ci_ok",         "ci_check",       "pushing"),
    ("ci_fail",       "ci_check",       "escalating"),
    # pushing
    ("pushed",        "pushing",        "labeling"),
    ("bounce",        "pushing",        "bounced"),
    # labeling
    ("labeled",       "labeling",       "shipped"),
    # rebasing_wip
    ("rebased",       "rebasing_wip",   "ci_check_wip"),
    ("rebase_failed", "rebasing_wip",   "bounced"),
    # ci_check_wip
    ("ci_ok",         "ci_check_wip",   "wip_updated"),
    ("ci_fail",       "ci_check_wip",   "bounced"),
]
```

- [ ] **Add stub `on_enter_checking_wip` (to be replaced in Task 5)**

Add after `on_enter_throttle_check`:

```python
def on_enter_checking_wip(self, ctx: ShipIssueContext) -> None:
    self.wip_current()  # type: ignore[attr-defined]
```

- [ ] **Update `_patch_all_externals` in `tests/workflows/test_ship_issue.py`**

Add two new monkeypatches inside `_patch_all_externals`, after the existing git patches:

```python
monkeypatch.setattr(git, "is_behind", lambda *a, **kw: False)
monkeypatch.setattr(git, "reset_hard", _noop)
```

- [ ] **Run existing tests to verify they still pass**

```
uv run pytest tests/workflows/test_ship_issue.py -v
```

Expected: all 5 tests pass.

- [ ] **Commit**

```bash
git add src/coding_bot/workflows/ship_issue.py tests/workflows/test_ship_issue.py
git commit -m "feat(ship-issue): add wip-maintenance states/transitions, ladder_key field, checking_wip stub"
```

---

## Task 4: Helper functions

**Files:**
- Modify: `src/coding_bot/workflows/ship_issue.py`
- Create: `tests/unit/workflows/test_ship_issue_helpers.py`

Three module-level helpers used by new and updated state handlers.

- [ ] **Write the failing tests**

Create `tests/unit/workflows/__init__.py` (empty) if it doesn't exist, then create `tests/unit/workflows/test_ship_issue_helpers.py`:

```python
from __future__ import annotations

from unittest.mock import patch

from coding_bot.workflows.ship_issue import (
    ShipIssueContext,
    _file_blocking_issue,
    _issue_model_effort,
    _wip_lock_path,
)


def test_wip_lock_path_slugifies_slash() -> None:
    p = _wip_lock_path("org/myrepo")
    assert p.name == "wip-rebase-org_myrepo.lock"


def test_issue_model_effort_effort_s() -> None:
    issue: dict = {"labels": [{"name": "effort:S"}, {"name": "bot:ship-issue-ready"}]}
    assert _issue_model_effort(issue) == ("haiku", "low", "claude:small")


def test_issue_model_effort_effort_m() -> None:
    issue: dict = {"labels": [{"name": "effort:M"}]}
    assert _issue_model_effort(issue) == ("sonnet", "medium", "claude:medium")


def test_issue_model_effort_effort_l() -> None:
    issue: dict = {"labels": [{"name": "effort:L"}]}
    assert _issue_model_effort(issue) == ("sonnet", "high", "claude:large")


def test_issue_model_effort_effort_xl() -> None:
    issue: dict = {"labels": [{"name": "effort:XL"}]}
    assert _issue_model_effort(issue) == ("opus", "high", "claude:xlarge")


def test_issue_model_effort_default_when_no_effort_label() -> None:
    issue: dict = {"labels": [{"name": "bot:ship-issue-ready"}]}
    assert _issue_model_effort(issue) == ("sonnet", "medium", "claude:medium")


def test_file_blocking_issue_calls_issue_create() -> None:
    ctx = ShipIssueContext(repo="org/repo", slot=1)
    with patch("coding_bot.workflows.ship_issue.gh") as mock_gh:
        _file_blocking_issue(ctx, reason="rebase failed")
    mock_gh.issue_create.assert_called_once()
    kwargs = mock_gh.issue_create.call_args.kwargs
    assert kwargs["title"] == "[bot:blocks-all] rebase failed"
    assert "bot:blocks-all" in kwargs["labels"]
    assert "bot:fix-wip" in kwargs["labels"]
    assert "bot:ship-issue-ready" in kwargs["labels"]
    assert "status:ready" in kwargs["labels"]


def test_file_blocking_issue_includes_ci_excerpt() -> None:
    ctx = ShipIssueContext(repo="org/repo", slot=1, ci_failure_excerpt="FAILED: test_foo")
    with patch("coding_bot.workflows.ship_issue.gh") as mock_gh:
        _file_blocking_issue(ctx, reason="ci failed")
    body = mock_gh.issue_create.call_args.kwargs["body"]
    assert "FAILED: test_foo" in body
```

- [ ] **Run tests to verify they fail**

```
uv run pytest tests/unit/workflows/test_ship_issue_helpers.py -v
```

Expected: `ImportError` or `AttributeError` for the three helper functions.

- [ ] **Add helpers to `src/coding_bot/workflows/ship_issue.py`**

Add `from coding_bot import locks` to the imports block.

Add after the `_INTEGRATION_BRANCH` constant:

```python
_LOCKS_DIR = Path("/srv/coding-bot/locks")

_EFFORT_LABEL_MAP: dict[str, tuple[str, str, str]] = {
    "effort:S":  ("haiku",  "low",    "claude:small"),
    "effort:M":  ("sonnet", "medium", "claude:medium"),
    "effort:L":  ("sonnet", "high",   "claude:large"),
    "effort:XL": ("opus",   "high",   "claude:xlarge"),
}
_DEFAULT_MODEL_EFFORT_LADDER = ("sonnet", "medium", "claude:medium")


def _wip_lock_path(repo: str) -> Path:
    return _LOCKS_DIR / f"wip-rebase-{repo.replace('/', '_')}.lock"


def _issue_model_effort(issue: dict[str, object]) -> tuple[str, str, str]:
    names = _label_names(issue)
    for label, triple in _EFFORT_LABEL_MAP.items():
        if label in names:
            return triple
    return _DEFAULT_MODEL_EFFORT_LADDER


def _file_blocking_issue(ctx: ShipIssueContext, *, reason: str) -> None:
    body = (
        f"ship-issue slot {ctx.slot} hit a blocking failure.\n\n"
        f"**Reason:** {reason}\n\n"
    )
    if ctx.ci_failure_excerpt:
        body += f"**CI excerpt:**\n```\n{ctx.ci_failure_excerpt}\n```\n"
    gh.issue_create(
        ctx.repo,
        title=f"[bot:blocks-all] {reason}",
        body=body,
        labels=["bot:blocks-all", "bot:fix-wip", "bot:ship-issue-ready", "status:ready"],
    )
```

- [ ] **Run tests to verify they pass**

```
uv run pytest tests/unit/workflows/test_ship_issue_helpers.py -v
```

Expected: all pass.

- [ ] **Run full test suite to confirm no regressions**

```
uv run pytest -x -q
```

- [ ] **Commit**

```bash
git add src/coding_bot/workflows/ship_issue.py tests/unit/workflows/
git commit -m "feat(ship-issue): add _wip_lock_path, _issue_model_effort, _file_blocking_issue helpers"
```

---

## Task 5: on_enter_checking_wip (real implementation)

**Files:**
- Modify: `src/coding_bot/workflows/ship_issue.py`
- Create: `tests/workflows/test_ship_issue_wip.py`

Replaces the stub from Task 3.

- [ ] **Write the failing tests**

Create `tests/workflows/test_ship_issue_wip.py`:

```python
"""Integration tests for the wip-maintenance path of ship-issue."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from coding_bot import db, gh, git, launcher
from coding_bot.engine.runner import WorkflowRunner
from coding_bot.locks import LockBusy
from coding_bot.workflows import ship_issue
from coding_bot.workflows.ship_issue import ShipIssueContext
from tests.workflows.conftest import FakeLaunchResult


def _noop(*a: Any, **kw: Any) -> None:
    return None


def _patch_wip_externals(
    monkeypatch: pytest.MonkeyPatch,
    *,
    is_behind: bool,
    lock_busy: bool = False,
    rebase_fails: bool = False,
    ci_passed: bool = True,
) -> None:
    monkeypatch.setattr(ship_issue, "_over_throttle_limit", lambda ctx: False)
    monkeypatch.setattr(git, "fetch", _noop)
    monkeypatch.setattr(git, "is_behind", lambda *a, **kw: is_behind)
    monkeypatch.setattr(git, "reset_hard", _noop)
    monkeypatch.setattr(git, "push", _noop)

    if rebase_fails:
        def _conflict(*a, **kw): raise git.GitConflict("CONFLICT")
        monkeypatch.setattr(git, "rebase", _conflict)
    else:
        monkeypatch.setattr(git, "rebase", _noop)

    from coding_bot.helpers.ci_check import CiResult
    monkeypatch.setattr(
        ship_issue,
        "run_make_ci",
        lambda cwd, **kw: CiResult(passed=ci_passed, excerpt="" if ci_passed else "FAILED", log_path=cwd / ".ci-ai.log"),
    )

    if lock_busy:
        class _BusyCtx:
            def __enter__(self): raise LockBusy("busy")
            def __exit__(self, *a): pass

        monkeypatch.setattr("coding_bot.workflows.ship_issue.locks.exclusive_lock", lambda *a, **kw: _BusyCtx())

    monkeypatch.setattr(gh, "issue_list", lambda *a, **kw: [])
    monkeypatch.setattr(gh, "issue_create", lambda *a, **kw: (999, "https://github.com/org/repo/issues/999"))


def test_checking_wip_current_proceeds_to_no_eligible(
    state_db: Path, cost_db: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When wip is current, workflow passes through checking_wip and picks normally."""
    _patch_wip_externals(monkeypatch, is_behind=False)

    ctx = ShipIssueContext(repo="org/myrepo", slot=1)
    WorkflowRunner().start("ship-issue", ctx, triggered_by="test")

    assert ctx.terminal == "no_eligible"


def test_checking_wip_behind_and_ci_ok_reaches_wip_updated(
    state_db: Path, cost_db: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When wip is behind and rebase+CI succeed, terminal is wip_updated."""
    _patch_wip_externals(monkeypatch, is_behind=True, ci_passed=True)

    ctx = ShipIssueContext(repo="org/myrepo", slot=1)
    WorkflowRunner().start("ship-issue", ctx, triggered_by="test")

    assert ctx.terminal == "wip_updated"


def test_checking_wip_behind_lock_busy_throttles(
    state_db: Path, cost_db: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When wip is behind but lock is held, workflow ends in throttled."""
    _patch_wip_externals(monkeypatch, is_behind=True, lock_busy=True)

    ctx = ShipIssueContext(repo="org/myrepo", slot=1)
    WorkflowRunner().start("ship-issue", ctx, triggered_by="test")

    assert ctx.terminal == "throttled"
```

- [ ] **Run tests to verify they fail**

```
uv run pytest tests/workflows/test_ship_issue_wip.py -v
```

Expected: `test_checking_wip_behind_*` tests fail because the stub always calls `wip_current()`.

- [ ] **Replace stub with real `on_enter_checking_wip`**

In `src/coding_bot/workflows/ship_issue.py`, replace the stub:

```python
def on_enter_checking_wip(self, ctx: ShipIssueContext) -> None:
    worktree = get_paths("ship-issue", ctx.repo, slot=ctx.slot).worktree
    ctx.worktree = worktree
    git.fetch(worktree)
    if not git.is_behind(worktree, branch="origin/wip/ship-issue", ref="origin/main"):
        self.wip_current()  # type: ignore[attr-defined]
        return
    lock_path = _wip_lock_path(ctx.repo)
    try:
        with locks.exclusive_lock(lock_path, blocking=False):
            self.wip_behind()  # type: ignore[attr-defined]
            # all maintenance states (rebasing_wip → ci_check_wip → wip_updated) run
            # synchronously inside this block; lock releases automatically on exit
    except locks.LockBusy:
        self.throttle()  # type: ignore[attr-defined]
```

- [ ] **Run the new tests to verify they pass**

```
uv run pytest tests/workflows/test_ship_issue_wip.py -v
```

Expected: all 3 tests pass.

- [ ] **Run full suite**

```
uv run pytest -x -q
```

- [ ] **Commit**

```bash
git add src/coding_bot/workflows/ship_issue.py tests/workflows/test_ship_issue_wip.py
git commit -m "feat(ship-issue): implement on_enter_checking_wip with flock-based slot exclusion"
```

---

## Task 6: Maintenance state handlers (rebasing_wip, ci_check_wip, wip_updated)

**Files:**
- Modify: `src/coding_bot/workflows/ship_issue.py`
- Modify: `tests/workflows/test_ship_issue_wip.py`

- [ ] **Write the failing tests**

Add to `tests/workflows/test_ship_issue_wip.py`:

```python
def test_rebase_failure_files_blocking_issue_and_bounces(
    state_db: Path, cost_db: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Rebase failure in rebasing_wip files a bot:blocks-all issue and bounces."""
    filed: list[dict] = []

    def _capture_issue_create(repo, *, title, body, labels=None, **kw):
        filed.append({"title": title, "labels": labels or []})
        return (999, "https://github.com/org/repo/issues/999")

    _patch_wip_externals(monkeypatch, is_behind=True, rebase_fails=True)
    monkeypatch.setattr(gh, "issue_create", _capture_issue_create)

    ctx = ShipIssueContext(repo="org/myrepo", slot=1)
    WorkflowRunner().start("ship-issue", ctx, triggered_by="test")

    assert ctx.terminal == "bounced"
    assert len(filed) == 1
    assert "bot:blocks-all" in filed[0]["labels"]
    assert "bot:fix-wip" in filed[0]["labels"]


def test_ci_failure_files_blocking_issue_and_bounces(
    state_db: Path, cost_db: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """CI failure in ci_check_wip files a bot:blocks-all issue and bounces."""
    filed: list[dict] = []

    def _capture_issue_create(repo, *, title, body, labels=None, **kw):
        filed.append({"title": title, "labels": labels or []})
        return (999, "https://github.com/org/repo/issues/999")

    _patch_wip_externals(monkeypatch, is_behind=True, ci_passed=False)
    monkeypatch.setattr(gh, "issue_create", _capture_issue_create)

    ctx = ShipIssueContext(repo="org/myrepo", slot=1)
    WorkflowRunner().start("ship-issue", ctx, triggered_by="test")

    assert ctx.terminal == "bounced"
    assert len(filed) == 1
    assert "bot:blocks-all" in filed[0]["labels"]
```

- [ ] **Run tests to verify they fail**

```
uv run pytest tests/workflows/test_ship_issue_wip.py::test_rebase_failure_files_blocking_issue_and_bounces tests/workflows/test_ship_issue_wip.py::test_ci_failure_files_blocking_issue_and_bounces -v
```

Expected: both fail — `AttributeError` for missing handler methods.

- [ ] **Implement the three new handlers in `ship_issue.py`**

Add after `on_enter_checking_wip`:

```python
def on_enter_rebasing_wip(self, ctx: ShipIssueContext) -> None:
    assert ctx.worktree is not None
    try:
        git.fetch(ctx.worktree)
        git.reset_hard(ctx.worktree, ref="origin/wip/ship-issue")
        git.rebase(ctx.worktree, onto="origin/main")
        git.push(
            ctx.worktree,
            remote="origin",
            refspec="wip/ship-issue:wip/ship-issue",
            force_with_lease=True,
        )
    except (git.GitConflict, git.GitError):
        _file_blocking_issue(ctx, reason="wip/ship-issue rebase onto origin/main failed")
        self.rebase_failed()  # type: ignore[attr-defined]
        return
    self.rebased()  # type: ignore[attr-defined]

def on_enter_ci_check_wip(self, ctx: ShipIssueContext) -> None:
    assert ctx.worktree is not None
    ci_result = run_make_ci(ctx.worktree)
    if ci_result.passed:
        self.ci_ok()  # type: ignore[attr-defined]
    else:
        ctx.ci_failure_log_path = ci_result.log_path
        ctx.ci_failure_excerpt = ci_result.excerpt
        _file_blocking_issue(ctx, reason="CI failed on wip/ship-issue after rebase")
        self.ci_fail()  # type: ignore[attr-defined]

def on_enter_wip_updated(self, ctx: ShipIssueContext) -> None:
    ctx.terminal = "wip_updated"
```

- [ ] **Run the new tests to verify they pass**

```
uv run pytest tests/workflows/test_ship_issue_wip.py -v
```

Expected: all 5 tests pass.

- [ ] **Run full suite**

```
uv run pytest -x -q
```

- [ ] **Commit**

```bash
git add src/coding_bot/workflows/ship_issue.py tests/workflows/test_ship_issue_wip.py
git commit -m "feat(ship-issue): implement rebasing_wip, ci_check_wip, wip_updated handlers"
```

---

## Task 7: on_enter_preflight update (reset + rebase onto main)

**Files:**
- Modify: `src/coding_bot/workflows/ship_issue.py`
- Modify: `tests/workflows/test_ship_issue.py`

`ctx.worktree` is now set in `on_enter_checking_wip` (Task 5), so preflight no longer sets it.

- [ ] **Write the failing test**

Add to `tests/workflows/test_ship_issue.py`:

```python
def test_preflight_rebase_conflict_bounces_and_files_issue(
    state_db: Path, cost_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preflight rebase failure bounces the workflow and files a bot:blocks-all issue."""
    rebase_calls: list[str] = []
    filed: list[dict] = []

    def fake_rebase(cwd, onto):
        rebase_calls.append(onto)
        if onto == "origin/main":
            raise git.GitConflict("CONFLICT")

    def capture_issue_create(repo, *, title, body, labels=None, **kw):
        filed.append({"title": title, "labels": labels or []})
        return (999, "https://github.com/org/repo/issues/999")

    _patch_all_externals(monkeypatch, issue_list_return=[_FAKE_ISSUE])
    monkeypatch.setattr(git, "rebase", fake_rebase)
    monkeypatch.setattr(gh, "issue_create", capture_issue_create)

    ctx = ShipIssueContext(repo="org/myrepo", slot=1)
    WorkflowRunner().start("ship-issue", ctx, triggered_by="test")

    assert ctx.terminal == "bounced"
    assert len(filed) == 1
    assert "bot:blocks-all" in filed[0]["labels"]
```

- [ ] **Run test to verify it fails**

```
uv run pytest tests/workflows/test_ship_issue.py::test_preflight_rebase_conflict_bounces_and_files_issue -v
```

Expected: FAIL — preflight currently doesn't rebase onto main, so no conflict is raised.

- [ ] **Update `on_enter_preflight` in `ship_issue.py`**

```python
def on_enter_preflight(self, ctx: ShipIssueContext) -> None:
    assert ctx.worktree is not None  # set by on_enter_checking_wip
    git.fetch(ctx.worktree)
    ctx.pre_claim_sha = git.rev_parse(ctx.worktree, "HEAD")
    try:
        git.reset_hard(ctx.worktree, ref="origin/wip/ship-issue")
        git.rebase(ctx.worktree, onto="origin/main")
    except (git.GitConflict, git.GitError):
        _file_blocking_issue(
            ctx, reason="preflight: wip/ship-issue rebase onto origin/main failed"
        )
        self.bounce()  # type: ignore[attr-defined]
        return
    self.preflighted()  # type: ignore[attr-defined]
```

- [ ] **Run new test to verify it passes**

```
uv run pytest tests/workflows/test_ship_issue.py::test_preflight_rebase_conflict_bounces_and_files_issue -v
```

- [ ] **Run full suite**

```
uv run pytest -x -q
```

- [ ] **Commit**

```bash
git add src/coding_bot/workflows/ship_issue.py tests/workflows/test_ship_issue.py
git commit -m "feat(ship-issue): preflight now resets to origin/wip/ship-issue and rebases onto origin/main"
```

---

## Task 8: on_enter_picking update (blocker priority + effort → ladder)

**Files:**
- Modify: `src/coding_bot/workflows/ship_issue.py`
- Modify: `tests/workflows/test_ship_issue.py`

- [ ] **Write the failing tests**

Add to `tests/workflows/test_ship_issue.py`:

```python
_FAKE_BLOCKER_ISSUE = {
    "number": 99,
    "title": "[bot:blocks-all] rebase failed",
    "body": "",
    "labels": [
        {"name": "bot:blocks-all"},
        {"name": "bot:ship-issue-ready"},
        {"name": "status:ready"},
    ],
    "state": "OPEN",
}

_FAKE_EFFORT_M_ISSUE = {
    "number": 77,
    "title": "A medium issue",
    "body": "",
    "labels": [
        {"name": "bot:ship-issue-ready"},
        {"name": "effort:M"},
    ],
    "state": "OPEN",
}


def test_blocker_issue_picked_first_with_sonnet_medium(
    state_db: Path, cost_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """bot:blocks-all issues are picked before normal issues and set blocker ladder."""
    # Return blocker when queried with bot:blocks-all, nothing when queried with bot:ship-issue-ready
    def fake_issue_list(repo, *, labels, **kw):
        if "bot:blocks-all" in labels:
            return [_FAKE_BLOCKER_ISSUE]
        return []

    _patch_all_externals(monkeypatch)
    monkeypatch.setattr(gh, "issue_list", fake_issue_list)

    ctx = ShipIssueContext(repo="org/myrepo", slot=1)
    WorkflowRunner().start("ship-issue", ctx, triggered_by="test")

    assert ctx.issue == 99
    assert ctx.model == "sonnet"
    assert ctx.effort == "medium"
    assert ctx.ladder_key == "claude:blocker"
    assert ctx.blocker_mode is True


def test_effort_label_sets_ladder_key(
    state_db: Path, cost_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """effort:M label on a picked issue sets (sonnet, medium, claude:medium)."""
    def fake_issue_list(repo, *, labels, **kw):
        if "bot:blocks-all" in labels:
            return []
        return [_FAKE_EFFORT_M_ISSUE]

    _patch_all_externals(monkeypatch)
    monkeypatch.setattr(gh, "issue_list", fake_issue_list)

    ctx = ShipIssueContext(repo="org/myrepo", slot=1)
    WorkflowRunner().start("ship-issue", ctx, triggered_by="test")

    assert ctx.issue == 77
    assert ctx.model == "sonnet"
    assert ctx.effort == "medium"
    assert ctx.ladder_key == "claude:medium"
    assert ctx.blocker_mode is False


def test_no_eligible_when_only_blocker_is_in_progress(
    state_db: Path, cost_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bot:blocks-all issue that's in-progress is skipped; if nothing else, no_eligible."""
    in_progress_blocker = {**_FAKE_BLOCKER_ISSUE, "labels": [
        {"name": "bot:blocks-all"},
        {"name": "status:in-progress"},
    ]}

    def fake_issue_list(repo, *, labels, **kw):
        if "bot:blocks-all" in labels:
            return [in_progress_blocker]
        return []

    _patch_all_externals(monkeypatch)
    monkeypatch.setattr(gh, "issue_list", fake_issue_list)

    ctx = ShipIssueContext(repo="org/myrepo", slot=1)
    WorkflowRunner().start("ship-issue", ctx, triggered_by="test")

    assert ctx.terminal == "no_eligible"
```

- [ ] **Run tests to verify they fail**

```
uv run pytest tests/workflows/test_ship_issue.py::test_blocker_issue_picked_first_with_sonnet_medium tests/workflows/test_ship_issue.py::test_effort_label_sets_ladder_key tests/workflows/test_ship_issue.py::test_no_eligible_when_only_blocker_is_in_progress -v
```

- [ ] **Add `_pick_blocker_issue` helper to `ship_issue.py`**

Add after `_pick_eligible_issue`:

```python
def _pick_blocker_issue(ctx: ShipIssueContext) -> dict[str, object] | None:
    issues = gh.issue_list(ctx.repo, labels=["bot:blocks-all"])
    for issue in issues:
        names = _label_names(issue)
        if "status:in-progress" in names or "status:in-pr" in names:
            continue
        return issue
    return None
```

- [ ] **Update `_pick_eligible_issue` to skip bot:blocks-all issues**

In `_pick_eligible_issue`, add inside the for loop after the `status:in-pr` check:

```python
        if "bot:blocks-all" in names:
            continue
```

- [ ] **Replace `on_enter_picking` in `ship_issue.py`**

```python
def on_enter_picking(self, ctx: ShipIssueContext) -> None:
    # Blocker issues take absolute priority over normal issue-picking
    blocker = _pick_blocker_issue(ctx)
    if blocker is not None:
        ctx.issue = int(blocker["number"])  # type: ignore[call-overload]
        ctx.model, ctx.effort, ctx.ladder_key = "sonnet", "medium", "claude:blocker"
        ctx.blocker_mode = True
        gh.issue_edit(ctx.repo, ctx.issue, add_labels=["status:in-progress"])
        gh.issue_comment(ctx.repo, ctx.issue, f"Claimed by ship-issue-{ctx.slot} (blocker mode)")
        self.found()  # type: ignore[attr-defined]
        return

    issue = _pick_eligible_issue(ctx)
    if issue is None:
        self.none_found()  # type: ignore[attr-defined]
        return
    ctx.issue = int(issue["number"])  # type: ignore[call-overload]
    model, effort, ladder_key = _issue_model_effort(issue)
    ctx.model, ctx.effort, ctx.ladder_key = model, effort, ladder_key
    gh.issue_edit(
        ctx.repo,
        ctx.issue,
        add_labels=["status:in-progress"],
        remove_labels=["status:ready"],
    )
    gh.issue_comment(ctx.repo, ctx.issue, f"Claimed by ship-issue-{ctx.slot}")
    self.found()  # type: ignore[attr-defined]
```

- [ ] **Fix `_patch_all_externals` to route `issue_list` calls correctly**

In `tests/workflows/test_ship_issue.py`, the existing `_patch_all_externals` sets `gh.issue_list` to return `issue_list_return` for all calls. Now that picking calls `issue_list` twice (once for `bot:blocks-all`, once for `bot:ship-issue-ready`), the mock needs updating:

```python
def fake_issue_list(repo, *, labels, **kw):
    if "bot:blocks-all" in labels:
        return []  # no blockers in standard tests
    return issue_list_return

monkeypatch.setattr(gh, "issue_list", fake_issue_list)
```

Replace the existing `monkeypatch.setattr(gh, "issue_list", lambda *a, **kw: issue_list_return)` with the above.

- [ ] **Run all new and existing tests**

```
uv run pytest tests/workflows/test_ship_issue.py -v
```

Expected: all pass.

- [ ] **Run full suite**

```
uv run pytest -x -q
```

- [ ] **Commit**

```bash
git add src/coding_bot/workflows/ship_issue.py tests/workflows/test_ship_issue.py
git commit -m "feat(ship-issue): picking now routes bot:blocks-all first; effort labels set ladder_key"
```

---

## Task 9: on_enter_escalating update (use ladder_key)

**Files:**
- Modify: `src/coding_bot/workflows/ship_issue.py`
- Modify: `tests/workflows/test_ship_issue.py`

Also removes the hardcoded `escalation_attempt >= 2` guard — the ladder's own exhaustion is the only stop signal.

- [ ] **Write the failing test**

Add to `tests/workflows/test_ship_issue.py`:

```python
def test_escalation_uses_ladder_key_not_backend(
    state_db: Path, cost_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When ladder_key is claude:medium, escalation follows sonnet/medium → sonnet/high → opus/high."""
    calls = _patch_all_externals(
        monkeypatch,
        issue_list_return=[_FAKE_EFFORT_M_ISSUE],
        slice_results=[
            FakeLaunchResult(exit_code=1),  # fail at sonnet/medium
            FakeLaunchResult(exit_code=1),  # fail at sonnet/high
            FakeLaunchResult(exit_code=0),  # succeed at opus/high
        ],
    )

    def fake_issue_list(repo, *, labels, **kw):
        if "bot:blocks-all" in labels:
            return []
        return [_FAKE_EFFORT_M_ISSUE]

    monkeypatch.setattr(gh, "issue_list", fake_issue_list)

    ctx = ShipIssueContext(repo="org/myrepo", slot=1)
    WorkflowRunner().start("ship-issue", ctx, triggered_by="test")

    assert ctx.terminal == "shipped"
    assert ctx.model == "opus"
    assert ctx.effort == "high"
    assert len(calls) == 3
```

- [ ] **Run test to verify it fails**

```
uv run pytest tests/workflows/test_ship_issue.py::test_escalation_uses_ladder_key_not_backend -v
```

Expected: FAIL — currently `on_enter_escalating` uses `LADDERS.get(ctx.backend)` and the `>= 2` guard would stop it before the third attempt.

- [ ] **Update `on_enter_escalating` in `ship_issue.py`**

```python
def on_enter_escalating(self, ctx: ShipIssueContext) -> None:
    ladder = LADDERS.get(ctx.ladder_key) or LADDERS.get(ctx.backend)
    if ladder is None:
        self.bounce()  # type: ignore[attr-defined]
        return
    next_rung = ladder.next(ctx.model, ctx.effort)
    if next_rung is None:
        self.bounce()  # type: ignore[attr-defined]
        return
    ctx.model, ctx.effort = next_rung
    ctx.escalation_attempt += 1
    self.retry()  # type: ignore[attr-defined]
```

Also add to imports: `from coding_bot.engine.policies import LADDERS`

- [ ] **Update `test_max_escalations_bounces` assertion**

With the updated `on_enter_escalating` and default `ladder_key = "claude"` (3-rung ladder: haiku/low → sonnet/medium → opus/high), the test context starts at haiku/low:
- Fail → escalate to sonnet/medium (attempt=1)
- Fail → escalate to opus/high (attempt=2)
- Fail → ladder exhausted → bounce

So `ctx.escalation_attempt == 2` still holds. No change needed to the assertion.

However, the test issues have no `effort:*` label, so `_issue_model_effort` returns `("sonnet", "medium", "claude:medium")` — and ctx.model starts as haiku/low from ShipIssueContext defaults, but picking now SETS model/effort/ladder_key. The test uses `_FAKE_ISSUE` which has no effort label, so picking sets `("sonnet", "medium", "claude:medium")`.

With `claude:medium` (sonnet/medium → sonnet/high → opus/high):
- Start: sonnet/medium, attempt=0
- Fail → sonnet/high (attempt=1)
- Fail → opus/high (attempt=2)
- Fail → ladder exhausted → bounce

So `ctx.escalation_attempt == 2` still holds. No change needed.

- [ ] **Run all tests**

```
uv run pytest -x -q
```

Expected: all pass.

- [ ] **Commit**

```bash
git add src/coding_bot/workflows/ship_issue.py tests/workflows/test_ship_issue.py
git commit -m "feat(ship-issue): escalating now uses ctx.ladder_key; removes hardcoded attempt>=2 guard"
```

---

## Final verification

- [ ] **Run the full test suite**

```
uv run pytest -v
```

Expected: all tests pass, no failures.

- [ ] **Run ruff and mypy**

```
uv run ruff check src/ tests/
uv run mypy src/
```

Expected: no errors. Fix any that appear before considering the work done.

- [ ] **Commit any lint fixes**

```bash
git add -u
git commit -m "fix: ruff/mypy cleanup after wip-maintenance implementation"
```
