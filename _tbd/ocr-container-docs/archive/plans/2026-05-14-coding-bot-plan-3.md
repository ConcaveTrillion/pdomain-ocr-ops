---
status: complete
---

# coding-bot Plan 3: Scheduler + Observability (M3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the APScheduler daemon, all `coding-bot scheduler` and
`coding-bot schedule` subcommands, every observability subcommand (`status`,
`ps`, `history`, `inspect`, `tail`, `logs`, `cost`, `pause`/`resume`, `kill`,
`audit`, `doctor`), and the `coding-bot db import-ctask` migration helper.
After this plan the bot can be started, scheduled, and fully observed without
touching the bash scripts.

**Architecture:**
- `src/coding_bot/scheduler/` — daemon, triggers parser, job-firing logic.
- `src/coding_bot/observability/` — one module per subcommand, all read-only
  except pause/resume/kill (which write audit log entries).
- `src/coding_bot/identity.py` — running-user detection + sudo helper.
- All DB models needed (`ScheduleEntry`, `BotPause`, `SlotLock`, `AuditLog`)
  already exist from Plan 1's `db.py`. **No new Alembic migrations needed.**

**Reference spec:** `docs/superpowers/specs/2026-05-14-coding-bot-design.md`
sections 11 (scheduler) and 12 (observability).

---

## File structure after Plan 3

```
src/coding_bot/
├── identity.py                      # NEW: vscode vs claude-bot, sudo helper
├── scheduler/
│   ├── __init__.py                  # NEW
│   ├── daemon.py                    # NEW: APScheduler loop + restart recovery
│   ├── triggers.py                  # NEW: parse "interval:minutes=N" etc.
│   └── cli.py                       # NEW: scheduler start/stop/status/run subcommands
├── observability/
│   ├── __init__.py                  # NEW
│   ├── status.py                    # NEW: top-level dashboard
│   ├── ps.py                        # NEW: list active runs
│   ├── history.py                   # NEW: past runs
│   ├── inspect.py                   # NEW: single run + events
│   ├── tail.py                      # NEW: tail backend stdout file
│   ├── logs.py                      # NEW: scheduler log files
│   ├── cost.py                      # NEW: cost.db query + display
│   ├── pause.py                     # NEW: pause/resume + audit
│   ├── kill.py                      # NEW: kill run + audit
│   ├── audit.py                     # NEW: audit_log query
│   └── doctor.py                    # NEW: env health check
└── cli.py                           # MODIFIED: mount all new sub-apps
tests/
├── unit/
│   ├── test_identity.py             # NEW
│   ├── scheduler/
│   │   ├── __init__.py              # NEW
│   │   ├── test_triggers.py         # NEW
│   │   └── test_daemon.py           # NEW (uses in-memory SQLite + fake jobs)
│   └── observability/
│       ├── __init__.py              # NEW
│       ├── test_status.py           # NEW
│       ├── test_history.py          # NEW
│       ├── test_cost.py             # NEW
│       ├── test_pause.py            # NEW
│       ├── test_kill.py             # NEW
│       ├── test_audit.py            # NEW
│       └── test_doctor.py           # NEW
```

---

## Phase A — Foundation: `identity.py` + `scheduler/triggers.py`

### Task A.1: `identity.py` — running-user detection

**Purpose:** Workflows and observability commands need to know whether they
are running as `vscode` (interactive) or `claude-bot` (scheduled). The
`@audited` decorator uses the actor from `identity.current_user()`.

**Files:**
- Create: `src/coding_bot/identity.py`
- Create: `tests/unit/test_identity.py`

- [ ] **Step 1: Write tests**

`tests/unit/test_identity.py`:

```python
from __future__ import annotations
import os
import pytest
from coding_bot import identity


def test_current_user_returns_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USER", "vscode")
    assert identity.current_user() == "vscode"


def test_current_user_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("USER", raising=False)
    monkeypatch.delenv("LOGNAME", raising=False)
    # Should not raise; returns some string
    user = identity.current_user()
    assert isinstance(user, str)
    assert len(user) > 0


def test_is_bot_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USER", "claude-bot")
    assert identity.is_bot_user() is True


def test_is_not_bot_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USER", "vscode")
    assert identity.is_bot_user() is False
```

- [ ] **Step 2: Verify failures**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/test_identity.py -x 2>&1 | tail -5
```

- [ ] **Step 3: Implement `src/coding_bot/identity.py`**

```python
"""Running-user detection and sudo helpers.

Two known users in this workspace:
  vscode     — CT interactive sessions, pre-commit hooks
  claude-bot — scheduled bot runs in /srv/bot-workspaces/

identity.py is intentionally thin: no subprocess calls except the optional
`sudo -u claude-bot` helper, which callers invoke explicitly.
"""
from __future__ import annotations

import os
import subprocess

_BOT_USER = "claude-bot"


def current_user() -> str:
    """Return the running OS user name."""
    for var in ("USER", "LOGNAME"):
        val = os.environ.get(var, "").strip()
        if val:
            return val
    try:
        import pwd
        return pwd.getpwuid(os.getuid()).pw_name
    except Exception:
        return "unknown"


def is_bot_user() -> bool:
    return current_user() == _BOT_USER


def sudo_as_bot(cmd: list[str]) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    """Run a command as claude-bot via sudo. Raises subprocess.CalledProcessError on failure."""
    return subprocess.run(
        ["sudo", "-u", _BOT_USER, "--"] + cmd,
        check=True,
        capture_output=True,
        text=True,
    )
```

- [ ] **Step 4: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/test_identity.py -v 2>&1 | tail -10
```

- [ ] **Step 5: Commit**

```
feat(identity): add running-user detection
```

---

### Task A.2: `scheduler/triggers.py` — parse trigger specs

**Purpose:** Schedule entries store trigger specs as strings
(`"interval:minutes=30"`, `"cron:hour=3,minute=0"`, `"date:run_at=2026-06-01T03:00:00"`).
This module parses those strings into APScheduler trigger objects.

**Files:**
- Create: `src/coding_bot/scheduler/__init__.py` (empty)
- Create: `src/coding_bot/scheduler/triggers.py`
- Create: `tests/unit/scheduler/__init__.py` (empty)
- Create: `tests/unit/scheduler/test_triggers.py`

- [ ] **Step 1: Write tests**

`tests/unit/scheduler/test_triggers.py`:

```python
from __future__ import annotations
import pytest
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from coding_bot.scheduler.triggers import parse_trigger, TriggerParseError


def test_interval_minutes() -> None:
    t = parse_trigger("interval:minutes=30")
    assert isinstance(t, IntervalTrigger)


def test_interval_hours() -> None:
    t = parse_trigger("interval:hours=2")
    assert isinstance(t, IntervalTrigger)


def test_cron_hourly() -> None:
    t = parse_trigger("cron:hour=3,minute=0")
    assert isinstance(t, CronTrigger)


def test_cron_day_of_week() -> None:
    t = parse_trigger("cron:day_of_week=sun,hour=2,minute=30")
    assert isinstance(t, CronTrigger)


def test_date_oneshot() -> None:
    t = parse_trigger("date:run_at=2026-06-01T03:00:00")
    assert isinstance(t, DateTrigger)


def test_unknown_kind_raises() -> None:
    with pytest.raises(TriggerParseError, match="unknown trigger kind"):
        parse_trigger("weekly:day=mon")


def test_malformed_raises() -> None:
    with pytest.raises(TriggerParseError):
        parse_trigger("interval:minutes=notanumber")
```

- [ ] **Step 2: Verify failures**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/scheduler/test_triggers.py -x 2>&1 | tail -5
```

- [ ] **Step 3: Implement `src/coding_bot/scheduler/triggers.py`**

```python
"""Parse trigger spec strings into APScheduler trigger objects.

Spec format: "<kind>:<key>=<value>[,<key>=<value>...]"

  interval:minutes=30
  interval:hours=2
  cron:hour=3,minute=0
  cron:day_of_week=sun,hour=2,minute=30
  date:run_at=2026-06-01T03:00:00
"""
from __future__ import annotations

import datetime as dt
from typing import Union

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

AnyTrigger = Union[IntervalTrigger, CronTrigger, DateTrigger]


class TriggerParseError(ValueError):
    pass


def parse_trigger(spec: str) -> AnyTrigger:
    """Parse a trigger spec string and return an APScheduler trigger."""
    if ":" not in spec:
        raise TriggerParseError(f"unknown trigger kind: {spec!r}")

    kind, rest = spec.split(":", 1)
    try:
        params = dict(pair.split("=", 1) for pair in rest.split(",") if "=" in pair)
    except ValueError as e:
        raise TriggerParseError(f"malformed trigger spec {spec!r}: {e}") from e

    if kind == "interval":
        try:
            kwargs = {k: int(v) for k, v in params.items()}
        except ValueError as e:
            raise TriggerParseError(f"interval values must be integers: {e}") from e
        return IntervalTrigger(**kwargs)

    if kind == "cron":
        int_keys = {"hour", "minute", "second", "year", "month", "day", "week"}
        kwargs: dict[str, object] = {}
        for k, v in params.items():
            kwargs[k] = int(v) if k in int_keys else v
        return CronTrigger(**kwargs)

    if kind == "date":
        run_at_str = params.get("run_at")
        if not run_at_str:
            raise TriggerParseError(f"date trigger requires run_at=ISO8601: {spec!r}")
        try:
            run_at = dt.datetime.fromisoformat(run_at_str)
        except ValueError as e:
            raise TriggerParseError(f"invalid run_at date {run_at_str!r}: {e}") from e
        return DateTrigger(run_date=run_at)

    raise TriggerParseError(f"unknown trigger kind: {kind!r}")
```

- [ ] **Step 4: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/scheduler/test_triggers.py -v 2>&1 | tail -12
```

- [ ] **Step 5: Commit**

```
feat(scheduler): add trigger spec parser
```

---

## Phase B — Scheduler daemon + `coding-bot scheduler` commands

### Task B.1: `scheduler/daemon.py` — APScheduler daemon

**Purpose:** Wraps APScheduler's `BackgroundScheduler` with a
`SQLAlchemyJobStore` pointed at `state.db`. Handles: start, stop, restart
recovery (resume running workflow_runs), dangling-run reap, and the
per-job `fire_workflow` callback.

**Files:**
- Create: `src/coding_bot/scheduler/daemon.py`
- Create: `tests/unit/scheduler/test_daemon.py`

- [ ] **Step 1: Write tests**

`tests/unit/scheduler/test_daemon.py`:

```python
"""Tests for the scheduler daemon — in-memory DB, no real tmux."""
from __future__ import annotations
import datetime as dt
import pytest
from coding_bot import db
from coding_bot.scheduler.daemon import (
    CodingBotScheduler,
    fire_workflow,
    _is_paused,
    _budget_blocks,
)


def test_scheduler_starts_and_stops(state_db, cost_db):
    sched = CodingBotScheduler()
    sched.start()
    assert sched.running
    sched.stop()
    assert not sched.running


def test_fire_workflow_skips_when_paused(state_db, cost_db, monkeypatch):
    with db.state_session() as session:
        session.add(db.BotPause(
            repo="org/repo", paused_at=dt.datetime.utcnow(),
            paused_by="vscode", reason="test",
        ))
        session.commit()
    fired = []
    monkeypatch.setattr("coding_bot.engine.runner.WorkflowRunner.start",
                        lambda *a, **kw: fired.append(True) or 1)
    fire_workflow("ship-issue", {"repo": "org/repo", "slot": 0}, schedule_entry_id=1)
    assert fired == []


def test_fire_workflow_skips_budget_blocked(state_db, cost_db, monkeypatch):
    monkeypatch.setattr("coding_bot.scheduler.daemon._budget_blocks",
                        lambda backend, plan: True)
    fired = []
    monkeypatch.setattr("coding_bot.engine.runner.WorkflowRunner.start",
                        lambda *a, **kw: fired.append(True) or 1)
    fire_workflow("ship-issue", {"repo": "org/repo", "slot": 0}, schedule_entry_id=1)
    assert fired == []


def test_fire_workflow_runs_when_clear(state_db, cost_db, monkeypatch):
    monkeypatch.setattr("coding_bot.engine.runner.WorkflowRunner.start",
                        lambda *a, **kw: 42)
    # Register a minimal workflow so the runner doesn't complain
    from coding_bot.engine.workflow import REGISTRY, Workflow, workflow as wf_decorator
    if "test-dummy" not in REGISTRY:
        @wf_decorator(name="test-dummy", context_class=dict)
        class _Dummy(Workflow):
            states = ["s"]; initial = "s"; terminal = {"s"}; transitions = []
            def on_enter_s(self, ctx): pass
    fire_workflow("test-dummy", {"repo": "org/repo"}, schedule_entry_id=1)


def test_is_paused_global(state_db, cost_db):
    assert not _is_paused(None)
    with db.state_session() as session:
        session.add(db.BotPause(
            repo=None, paused_at=dt.datetime.utcnow(),
            paused_by="vscode", reason="global pause",
        ))
        session.commit()
    assert _is_paused(None)
    assert _is_paused("org/repo")  # global pause covers all repos


def test_budget_blocks_returns_false_without_budget_rows(state_db, cost_db):
    assert not _budget_blocks("claude", "claude-api-200")
```

- [ ] **Step 2: Verify failures**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/scheduler/test_daemon.py -x 2>&1 | tail -5
```

- [ ] **Step 3: Implement `src/coding_bot/scheduler/daemon.py`**

```python
"""APScheduler daemon for coding-bot.

One singleton scheduler per process. Job store points at state.db so jobs
survive restarts. Each job fires fire_workflow(...) which guards against
pauses, budget breaches, and in-flight duplicate runs.
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Any

import sqlalchemy as sa
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from coding_bot import db
from coding_bot.engine.runner import WorkflowRunner

logger = logging.getLogger(__name__)

_MAX_WORKERS = 4
_MISFIRE_GRACE = 600  # seconds


class CodingBotScheduler:
    """Thin wrapper around BackgroundScheduler with our DB wiring."""

    def __init__(self) -> None:
        engine = db.get_state_engine()
        jobstore = SQLAlchemyJobStore(engine=engine)
        executor = ThreadPoolExecutor(max_workers=_MAX_WORKERS)
        self._apscheduler = BackgroundScheduler(
            jobstores={"default": jobstore},
            executors={"default": executor},
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": _MISFIRE_GRACE,
            },
        )

    def start(self) -> None:
        self._apscheduler.start()
        _recover_running_workflows()
        _reap_dangling_backend_runs()

    def stop(self) -> None:
        self._apscheduler.shutdown(wait=False)

    def restart(self) -> None:
        self.stop()
        self.start()

    @property
    def running(self) -> bool:
        return self._apscheduler.running

    @property
    def apscheduler(self) -> BackgroundScheduler:
        return self._apscheduler


def fire_workflow(
    workflow_name: str,
    context_preset: dict[str, Any],
    schedule_entry_id: int,
) -> None:
    """Job callback: guard checks → start or resume workflow."""
    repo = context_preset.get("repo")

    # Resume if already running
    run_id = _find_active_run(workflow_name, repo)
    if run_id is not None:
        logger.info("resuming run %d for %s/%s", run_id, workflow_name, repo)
        WorkflowRunner().resume(run_id)
        return

    if _is_paused(repo):
        logger.info("skipped %s/%s: paused", workflow_name, repo)
        return

    backend = context_preset.get("backend", "claude")
    plan = context_preset.get("plan", "unknown")
    if _budget_blocks(backend, plan):
        logger.info("skipped %s/%s: budget blocked", workflow_name, repo)
        return

    logger.info("starting %s for %s (schedule:%d)", workflow_name, repo, schedule_entry_id)
    WorkflowRunner().start(
        workflow_name,
        context_preset,
        triggered_by=f"schedule:{schedule_entry_id}",
    )


def _find_active_run(workflow_name: str, repo: str | None) -> int | None:
    with db.state_session() as session:
        stmt = (
            sa.select(db.WorkflowRun.id)
            .where(db.WorkflowRun.workflow_name == workflow_name)
            .where(db.WorkflowRun.status == "running")
        )
        if repo:
            stmt = stmt.where(db.WorkflowRun.repo == repo)
        row = session.execute(stmt).first()
    return row[0] if row else None


def _is_paused(repo: str | None) -> bool:
    """True if there is a global pause OR a pause for this specific repo."""
    with db.state_session() as session:
        # Global pause
        global_pause = session.execute(
            sa.select(db.BotPause.id).where(db.BotPause.repo.is_(None))
        ).first()
        if global_pause:
            return True
        if repo is None:
            return False
        repo_pause = session.execute(
            sa.select(db.BotPause.id).where(db.BotPause.repo == repo)
        ).first()
        return repo_pause is not None


def _budget_blocks(backend: str, plan: str) -> bool:
    """True if any active Budget row would be breached (action=pause-schedules)."""
    with db.cost_session() as session:
        budgets = session.execute(
            sa.select(db.Budget)
            .where(db.Budget.backend == backend)
            .where(db.Budget.action_at_breach == "pause-schedules")
        ).scalars().all()
    for budget in budgets:
        if _current_spend_exceeds(budget):
            return True
    return False


def _current_spend_exceeds(budget: db.Budget) -> bool:
    now = dt.datetime.utcnow()
    if budget.window == "daily":
        window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif budget.window == "weekly":
        window_start = now - dt.timedelta(days=now.weekday())
        window_start = window_start.replace(hour=0, minute=0, second=0, microsecond=0)
    else:  # monthly
        window_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    with db.cost_session() as session:
        spend = session.execute(
            sa.select(sa.func.coalesce(sa.func.sum(db.BackendRun.cost_usd), 0.0))
            .where(db.BackendRun.backend == budget.backend)
            .where(db.BackendRun.started_at >= window_start)
        ).scalar_one()
    return float(spend) >= budget.limit_usd


def _recover_running_workflows() -> None:
    """On daemon start: re-enqueue any runs left in status=running."""
    with db.state_session() as session:
        runs = session.execute(
            sa.select(db.WorkflowRun).where(db.WorkflowRun.status == "running")
        ).scalars().all()
        run_ids = [r.id for r in runs]
    for run_id in run_ids:
        logger.info("recovering run %d", run_id)
        try:
            WorkflowRunner().resume(run_id)
        except Exception as exc:
            logger.error("recovery of run %d failed: %s", run_id, exc)


def _reap_dangling_backend_runs(max_timeout_secs: int = 6300) -> None:
    """Close cost.db rows that started but never finished (2× timeout ago)."""
    cutoff = dt.datetime.utcnow() - dt.timedelta(seconds=2 * max_timeout_secs)
    with db.cost_session() as session:
        dangling = session.execute(
            sa.select(db.BackendRun)
            .where(db.BackendRun.ended_at.is_(None))
            .where(db.BackendRun.started_at < cutoff)
        ).scalars().all()
        for row in dangling:
            row.ended_at = dt.datetime.utcnow()
            row.exit_code = -1
            row.is_error = True
        if dangling:
            session.commit()
            logger.warning("reaped %d dangling backend_run rows", len(dangling))
```

- [ ] **Step 4: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/scheduler/test_daemon.py -v 2>&1 | tail -15
```

- [ ] **Step 5: Commit**

```
feat(scheduler): add APScheduler daemon with pause/budget guards
```

---

### Task B.2: `scheduler/cli.py` — `coding-bot scheduler` subcommands

**Purpose:** `coding-bot scheduler start|stop|status|restart|run` and
`coding-bot schedule add|list|disable|remove`.

**Files:**
- Create: `src/coding_bot/scheduler/cli.py`

- [ ] **Step 1: Implement `src/coding_bot/scheduler/cli.py`**

```python
"""CLI subcommands for the scheduler daemon and schedule management."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Annotated, Optional

import sqlalchemy as sa
import typer
from rich.console import Console
from rich.table import Table

from coding_bot import db
from coding_bot.scheduler.daemon import CodingBotScheduler
from coding_bot.scheduler.triggers import parse_trigger, TriggerParseError

console = Console()
app = typer.Typer(help="Scheduler daemon control and schedule management.")
schedule_app = typer.Typer(help="Manage schedule entries.")
app.add_typer(schedule_app, name="schedule")

_TMUX_SESSION = "coding-bot-scheduler"
_PID_FILE = "/srv/coding-bot/locks/scheduler.pid"


@app.command("run")
def cmd_run() -> None:
    """Run the scheduler in the foreground (called inside tmux by 'start')."""
    sched = CodingBotScheduler()
    sched.start()
    console.print("[green]Scheduler started.[/green] Press Ctrl-C to stop.")
    try:
        import time
        while True:
            time.sleep(5)
    except (KeyboardInterrupt, SystemExit):
        sched.stop()


@app.command("start")
def cmd_start() -> None:
    """Detach the scheduler into a tmux session."""
    r = subprocess.run(
        ["tmux", "new-session", "-d", "-s", _TMUX_SESSION,
         "coding-bot", "scheduler", "run"],
        capture_output=True, text=True,
    )
    if r.returncode != 0 and "duplicate session" not in r.stderr:
        console.print(f"[red]tmux error:[/red] {r.stderr.strip()}")
        raise typer.Exit(1)
    console.print(f"[green]Scheduler started in tmux session '{_TMUX_SESSION}'.[/green]")


@app.command("stop")
def cmd_stop() -> None:
    """Stop the scheduler tmux session."""
    subprocess.run(["tmux", "kill-session", "-t", _TMUX_SESSION],
                   capture_output=True)
    console.print("[yellow]Scheduler stopped.[/yellow]")


@app.command("restart")
def cmd_restart() -> None:
    """Stop then start the scheduler."""
    cmd_stop()
    cmd_start()


@app.command("status")
def cmd_scheduler_status() -> None:
    """Show whether the scheduler tmux session is alive."""
    r = subprocess.run(
        ["tmux", "list-sessions", "-F", "#{session_name}"],
        capture_output=True, text=True,
    )
    sessions = r.stdout.splitlines()
    if _TMUX_SESSION in sessions:
        console.print(f"[green]✓ Scheduler is running[/green] (tmux:{_TMUX_SESSION})")
    else:
        console.print("[red]✗ Scheduler is not running[/red]")


# ─── coding-bot schedule ─────────────────────────────────────────────────────

@schedule_app.command("add")
def cmd_schedule_add(
    name: str = typer.Argument(..., help="Unique name for this entry"),
    workflow: str = typer.Option(..., "--workflow", "-w"),
    trigger: str = typer.Option(..., "--trigger", "-t",
                                help='e.g. "interval:minutes=30"'),
    context: Optional[str] = typer.Option(None, "--context",
                                          help="key=val,key2=val2 context preset"),
) -> None:
    """Add a new schedule entry."""
    try:
        _trig = parse_trigger(trigger)
    except TriggerParseError as e:
        console.print(f"[red]Invalid trigger:[/red] {e}")
        raise typer.Exit(1)

    ctx_dict: dict[str, object] = {}
    if context:
        for pair in context.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                ctx_dict[k.strip()] = _coerce(v.strip())

    with db.state_session() as session:
        entry = db.ScheduleEntry(
            name=name,
            workflow_name=workflow,
            trigger_spec=trigger,
            context_preset_json=json.dumps(ctx_dict),
            disabled=False,
            apscheduler_job_id=None,
        )
        session.add(entry)
        session.commit()
        console.print(f"[green]Added schedule entry '{name}' (id={entry.id}).[/green]")


@schedule_app.command("list")
def cmd_schedule_list() -> None:
    """List all schedule entries."""
    with db.state_session() as session:
        entries = session.execute(sa.select(db.ScheduleEntry)).scalars().all()
    if not entries:
        console.print("No schedule entries.")
        return
    table = Table(show_header=True)
    table.add_column("ID"); table.add_column("Name"); table.add_column("Workflow")
    table.add_column("Trigger"); table.add_column("Disabled")
    for e in entries:
        table.add_row(str(e.id), e.name, e.workflow_name, e.trigger_spec,
                      "yes" if e.disabled else "no")
    console.print(table)


@schedule_app.command("disable")
def cmd_schedule_disable(entry_id: int = typer.Argument(...)) -> None:
    """Disable a schedule entry by ID."""
    with db.state_session() as session:
        entry = session.get(db.ScheduleEntry, entry_id)
        if entry is None:
            console.print(f"[red]No entry with id {entry_id}[/red]")
            raise typer.Exit(1)
        entry.disabled = True
        session.commit()
    console.print(f"[yellow]Entry {entry_id} disabled.[/yellow]")


@schedule_app.command("remove")
def cmd_schedule_remove(entry_id: int = typer.Argument(...)) -> None:
    """Remove a schedule entry by ID."""
    with db.state_session() as session:
        entry = session.get(db.ScheduleEntry, entry_id)
        if entry is None:
            console.print(f"[red]No entry with id {entry_id}[/red]")
            raise typer.Exit(1)
        session.delete(entry)
        session.commit()
    console.print(f"[red]Entry {entry_id} removed.[/red]")


def _coerce(v: str) -> object:
    if v.isdigit():
        return int(v)
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    return v
```

- [ ] **Step 2: Mount sub-app in `cli.py`**

```python
# in cli.py
from coding_bot.scheduler.cli import app as scheduler_app
app.add_typer(scheduler_app, name="scheduler")
# and re-export schedule_app for the top-level `coding-bot schedule` command:
from coding_bot.scheduler.cli import schedule_app
app.add_typer(schedule_app, name="schedule")
```

- [ ] **Step 3: Smoke-test**

```bash
cd /workspaces/ocr-container/coding-bot
uv run coding-bot scheduler --help
uv run coding-bot schedule --help
```

- [ ] **Step 4: Commit**

```
feat(scheduler): add CLI subcommands (start/stop/status/run + schedule add/list/disable/remove)
```

---

## Phase C — Observability

### Task C.1: Core query helpers in `observability/__init__.py`

**Purpose:** Several commands share the same DB query patterns. Extract them
here so each command module stays thin.

**Files:**
- Create: `src/coding_bot/observability/__init__.py`

```python
"""Shared query helpers for observability subcommands."""
from __future__ import annotations

import datetime as dt
from typing import Sequence

import sqlalchemy as sa

from coding_bot import db


def recent_runs(
    *,
    limit: int = 20,
    since: dt.datetime | None = None,
    workflow_name: str | None = None,
    terminal_state: str | None = None,
    repo: str | None = None,
) -> Sequence[db.WorkflowRun]:
    stmt = sa.select(db.WorkflowRun).order_by(db.WorkflowRun.started_at.desc())
    if since:
        stmt = stmt.where(db.WorkflowRun.started_at >= since)
    if workflow_name:
        stmt = stmt.where(db.WorkflowRun.workflow_name == workflow_name)
    if terminal_state:
        stmt = stmt.where(db.WorkflowRun.terminal_state == terminal_state)
    if repo:
        stmt = stmt.where(db.WorkflowRun.repo == repo)
    stmt = stmt.limit(limit)
    with db.state_session() as session:
        return session.execute(stmt).scalars().all()


def active_runs() -> Sequence[db.WorkflowRun]:
    with db.state_session() as session:
        return (
            session.execute(
                sa.select(db.WorkflowRun).where(db.WorkflowRun.status == "running")
            )
            .scalars()
            .all()
        )


def parse_since(since_str: str) -> dt.datetime:
    """Parse strings like '24h', '7d', '30m' into a UTC datetime."""
    now = dt.datetime.utcnow()
    unit = since_str[-1]
    value = int(since_str[:-1])
    if unit == "m":
        return now - dt.timedelta(minutes=value)
    if unit == "h":
        return now - dt.timedelta(hours=value)
    if unit == "d":
        return now - dt.timedelta(days=value)
    raise ValueError(f"unrecognised since format: {since_str!r}")
```

- [ ] **Commit:** `feat(observability): add shared query helpers`

---

### Task C.2: `status`, `ps`, `history`, `inspect`

**Files:**
- Create: `src/coding_bot/observability/status.py`
- Create: `src/coding_bot/observability/ps.py`
- Create: `src/coding_bot/observability/history.py`
- Create: `src/coding_bot/observability/inspect.py`
- Create: `tests/unit/observability/__init__.py` (empty)
- Create: `tests/unit/observability/test_status.py`
- Create: `tests/unit/observability/test_history.py`

- [ ] **Step 1: Write tests**

`tests/unit/observability/test_status.py`:

```python
from __future__ import annotations
import datetime as dt
import pytest
from coding_bot import db
from coding_bot.observability import status


def test_status_empty(state_db, cost_db, capsys):
    status.print_status()
    out = capsys.readouterr().out
    assert "active" in out.lower() or "0" in out


def test_status_shows_active_run(state_db, cost_db, capsys):
    with db.state_session() as session:
        session.add(db.WorkflowRun(
            workflow_name="ship-issue", status="running",
            terminal_state=None, context_json="{}",
            repo="org/repo", slot=0, triggered_by="test",
            started_at=dt.datetime.utcnow(),
        ))
        session.commit()
    status.print_status()
    out = capsys.readouterr().out
    assert "ship-issue" in out
```

`tests/unit/observability/test_history.py`:

```python
from __future__ import annotations
import datetime as dt
import pytest
from coding_bot import db
from coding_bot.observability import history


def test_history_empty(state_db, cost_db, capsys):
    history.print_history(limit=10)
    capsys.readouterr()  # should not raise


def test_history_shows_terminal_run(state_db, cost_db, capsys):
    with db.state_session() as session:
        session.add(db.WorkflowRun(
            workflow_name="style-review", status="terminal",
            terminal_state="done", context_json="{}",
            repo="org/repo", slot=None, triggered_by="test",
            started_at=dt.datetime.utcnow(),
            ended_at=dt.datetime.utcnow(),
        ))
        session.commit()
    history.print_history(limit=5)
    out = capsys.readouterr().out
    assert "style-review" in out
    assert "done" in out
```

- [ ] **Step 2: Implement `status.py`**

```python
"""Top-level status dashboard."""
from __future__ import annotations
from rich.console import Console
from rich.table import Table
from coding_bot.observability import active_runs, recent_runs

console = Console()


def print_status(*, json_mode: bool = False) -> None:
    active = active_runs()
    console.print(f"[bold]Active runs:[/bold] {len(active)}")
    if not active:
        console.print("  (none)")
        return
    table = Table(show_header=True)
    table.add_column("Run ID"); table.add_column("Workflow")
    table.add_column("Repo"); table.add_column("Slot"); table.add_column("Started")
    for run in active:
        table.add_row(str(run.id), run.workflow_name, run.repo or "-",
                      str(run.slot) if run.slot is not None else "-",
                      run.started_at.isoformat(timespec="seconds"))
    console.print(table)
```

- [ ] **Step 3: Implement `ps.py`**

Thin: `print_ps(workflow=None, repo=None)` — queries `active_runs()` with
optional filters, prints a rich table identical to `status.py`'s active block
but with an extra "Triggered by" column.

- [ ] **Step 4: Implement `history.py`**

```python
"""Past run history."""
from __future__ import annotations
import datetime as dt
from rich.console import Console
from rich.table import Table
from coding_bot.observability import recent_runs, parse_since

console = Console()


def print_history(
    *,
    limit: int = 20,
    since: str | None = None,
    workflow_name: str | None = None,
    terminal_state: str | None = None,
) -> None:
    since_dt = parse_since(since) if since else None
    runs = recent_runs(limit=limit, since=since_dt, workflow_name=workflow_name,
                       terminal_state=terminal_state)
    if not runs:
        console.print("No runs found.")
        return
    table = Table(show_header=True)
    table.add_column("ID"); table.add_column("Workflow"); table.add_column("Repo")
    table.add_column("Terminal"); table.add_column("Started"); table.add_column("Duration")
    for run in runs:
        dur = ""
        if run.ended_at and run.started_at:
            secs = int((run.ended_at - run.started_at).total_seconds())
            dur = f"{secs}s"
        table.add_row(str(run.id), run.workflow_name, run.repo or "-",
                      run.terminal_state or run.status,
                      run.started_at.isoformat(timespec="seconds"), dur)
    console.print(table)
```

- [ ] **Step 5: Implement `inspect.py`**

`print_inspect(run_id, show_events=False)` — fetches `WorkflowRun` + its
`WorkflowEvent` rows + linked `BackendRun` rows from cost.db. Prints a summary
plus an events timeline table when `show_events=True`.

- [ ] **Step 6: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/observability/ -v 2>&1 | tail -15
```

- [ ] **Step 7: Commit**

```
feat(observability): add status, ps, history, inspect
```

---

### Task C.3: `tail`, `logs`, `cost`, `audit`

**Files:**
- Create: `src/coding_bot/observability/tail.py`
- Create: `src/coding_bot/observability/logs.py`
- Create: `src/coding_bot/observability/cost.py`
- Create: `src/coding_bot/observability/audit.py`
- Create: `tests/unit/observability/test_cost.py`
- Create: `tests/unit/observability/test_audit.py`

- [ ] **Step 1: Write cost + audit tests**

`tests/unit/observability/test_cost.py`:

```python
from __future__ import annotations
import datetime as dt
import pytest
from coding_bot import db
from coding_bot.observability import cost


def test_cost_summary_empty(state_db, cost_db, capsys):
    cost.print_cost(since_str="7d")
    capsys.readouterr()  # should not raise


def test_cost_shows_rows(state_db, cost_db, capsys):
    now = dt.datetime.utcnow()
    with db.cost_session() as session:
        session.add(db.BackendRun(
            backend="claude", plan="claude-api-200",
            task_label="ship-issue.org/repo.slot0",
            workflow_name="ship-issue", repo="org/repo", slot=0,
            model="claude-haiku-4-5", effort="low",
            started_at=now, ended_at=now, duration_ms=500,
            exit_code=0, input_tokens=100, output_tokens=50,
            cache_creation_tokens=0, cache_read_tokens=0,
            cost_usd=0.002, num_turns=1, is_error=False,
            stdout_path="/dev/null", text_path="/dev/null",
        ))
        session.commit()
    cost.print_cost(since_str="1d")
    out = capsys.readouterr().out
    assert "0.002" in out or "claude" in out
```

`tests/unit/observability/test_audit.py`:

```python
from __future__ import annotations
import datetime as dt
import pytest
from coding_bot import db
from coding_bot.observability import audit as audit_obs


def test_audit_empty(state_db, cost_db, capsys):
    audit_obs.print_audit(limit=10)
    capsys.readouterr()


def test_audit_shows_entry(state_db, cost_db, capsys):
    with db.state_session() as session:
        session.add(db.AuditLog(
            timestamp=dt.datetime.utcnow(), actor="vscode",
            action="pause", target="org/repo", payload_json="{}",
        ))
        session.commit()
    audit_obs.print_audit(limit=5)
    out = capsys.readouterr().out
    assert "pause" in out
```

- [ ] **Step 2: Implement `tail.py`**

`print_tail(run_id_or_workflow)` — finds the latest `BackendRun.stdout_path`
for the run (or most-recent run for a workflow name), opens the `.ndjson` file,
and streams it. Falls back gracefully if the file doesn't exist.

- [ ] **Step 3: Implement `logs.py`**

`print_logs(run_id)` — shows the filtered text output (`text_path`) for a
backend run. Accepts `--json` to dump the `.ndjson` instead.

- [ ] **Step 4: Implement `cost.py`**

```python
"""Cost query and display."""
from __future__ import annotations
import datetime as dt
import sqlalchemy as sa
from rich.console import Console
from rich.table import Table
from coding_bot import db
from coding_bot.observability import parse_since

console = Console()


def print_cost(
    *,
    since_str: str = "7d",
    group_by: str = "backend",
) -> None:
    since_dt = parse_since(since_str)
    with db.cost_session() as session:
        rows = session.execute(
            sa.select(db.BackendRun)
            .where(db.BackendRun.started_at >= since_dt)
            .order_by(db.BackendRun.started_at.desc())
        ).scalars().all()
    if not rows:
        console.print(f"No cost rows since {since_dt.isoformat(timespec='seconds')}.")
        return
    total = sum(r.cost_usd for r in rows if r.cost_usd)
    table = Table(show_header=True, title=f"Cost since {since_str} — total ${total:.4f}")
    table.add_column("Backend"); table.add_column("Model"); table.add_column("Task")
    table.add_column("Input tok"); table.add_column("Output tok"); table.add_column("Cost USD")
    for row in rows[:50]:
        table.add_row(
            row.backend, row.model, row.task_label,
            str(row.input_tokens), str(row.output_tokens),
            f"${row.cost_usd:.4f}" if row.cost_usd else "-",
        )
    console.print(table)
```

- [ ] **Step 5: Implement `audit.py`**

```python
"""Audit log display."""
from __future__ import annotations
import sqlalchemy as sa
from rich.console import Console
from rich.table import Table
from coding_bot import db

console = Console()


def print_audit(*, limit: int = 50, actor: str | None = None,
                action: str | None = None) -> None:
    stmt = sa.select(db.AuditLog).order_by(db.AuditLog.timestamp.desc()).limit(limit)
    if actor:
        stmt = stmt.where(db.AuditLog.actor == actor)
    if action:
        stmt = stmt.where(db.AuditLog.action == action)
    with db.state_session() as session:
        entries = session.execute(stmt).scalars().all()
    if not entries:
        console.print("No audit entries found.")
        return
    table = Table(show_header=True)
    table.add_column("Time"); table.add_column("Actor")
    table.add_column("Action"); table.add_column("Target")
    for e in entries:
        table.add_row(e.timestamp.isoformat(timespec="seconds"),
                      e.actor, e.action, e.target or "-")
    console.print(table)
```

- [ ] **Step 6: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/observability/test_cost.py tests/unit/observability/test_audit.py -v 2>&1 | tail -12
```

- [ ] **Step 7: Commit**

```
feat(observability): add tail, logs, cost, audit
```

---

### Task C.4: `pause`, `kill`, `doctor`

**Files:**
- Create: `src/coding_bot/observability/pause.py`
- Create: `src/coding_bot/observability/kill.py`
- Create: `src/coding_bot/observability/doctor.py`
- Create: `tests/unit/observability/test_pause.py`
- Create: `tests/unit/observability/test_kill.py`
- Create: `tests/unit/observability/test_doctor.py`

- [ ] **Step 1: Write pause tests**

`tests/unit/observability/test_pause.py`:

```python
from __future__ import annotations
import datetime as dt
import sqlalchemy as sa
import pytest
from coding_bot import db
from coding_bot.observability import pause


def test_pause_repo(state_db, cost_db):
    pause.pause_repo("org/repo", actor="vscode", reason="testing")
    with db.state_session() as session:
        rows = session.execute(sa.select(db.BotPause)).scalars().all()
    assert len(rows) == 1
    assert rows[0].repo == "org/repo"


def test_resume_removes_pause(state_db, cost_db):
    pause.pause_repo("org/repo", actor="vscode", reason="x")
    pause.resume_repo("org/repo", actor="vscode")
    with db.state_session() as session:
        rows = session.execute(sa.select(db.BotPause)).scalars().all()
    assert len(rows) == 0


def test_global_pause(state_db, cost_db):
    pause.pause_repo(None, actor="vscode", reason="global")
    with db.state_session() as session:
        rows = session.execute(sa.select(db.BotPause)
                               .where(db.BotPause.repo.is_(None))).scalars().all()
    assert len(rows) == 1
```

- [ ] **Step 2: Write kill tests**

`tests/unit/observability/test_kill.py`:

```python
from __future__ import annotations
import datetime as dt
import sqlalchemy as sa
import pytest
from coding_bot import db
from coding_bot.observability import kill


def test_kill_run(state_db, cost_db):
    with db.state_session() as session:
        run = db.WorkflowRun(
            workflow_name="ship-issue", status="running",
            terminal_state=None, context_json="{}",
            repo="org/repo", slot=0, triggered_by="test",
            started_at=dt.datetime.utcnow(),
        )
        session.add(run)
        session.commit()
        run_id = run.id
    kill.kill_run(run_id, actor="vscode")
    with db.state_session() as session:
        r = session.get(db.WorkflowRun, run_id)
    assert r is not None
    assert r.status == "errored"
```

- [ ] **Step 3: Implement `pause.py`**

```python
"""Pause/resume bot execution with audit log entries."""
from __future__ import annotations
import datetime as dt
import sqlalchemy as sa
from coding_bot import db


def pause_repo(repo: str | None, *, actor: str, reason: str | None = None) -> None:
    with db.state_session() as session:
        session.add(db.BotPause(
            repo=repo, paused_at=dt.datetime.utcnow(),
            paused_by=actor, reason=reason,
        ))
        session.add(db.AuditLog(
            timestamp=dt.datetime.utcnow(), actor=actor,
            action="pause", target=repo or "(global)",
            payload_json=f'{{"reason": {reason!r}}}',
        ))
        session.commit()


def resume_repo(repo: str | None, *, actor: str) -> None:
    with db.state_session() as session:
        stmt = sa.select(db.BotPause)
        if repo is None:
            stmt = stmt.where(db.BotPause.repo.is_(None))
        else:
            stmt = stmt.where(db.BotPause.repo == repo)
        rows = session.execute(stmt).scalars().all()
        for row in rows:
            session.delete(row)
        session.add(db.AuditLog(
            timestamp=dt.datetime.utcnow(), actor=actor,
            action="resume", target=repo or "(global)",
            payload_json="{}",
        ))
        session.commit()
```

- [ ] **Step 4: Implement `kill.py`**

```python
"""Kill a running workflow run."""
from __future__ import annotations
import datetime as dt
import sqlalchemy as sa
from coding_bot import db


def kill_run(run_id: int, *, actor: str) -> None:
    with db.state_session() as session:
        run = session.get(db.WorkflowRun, run_id)
        if run is None:
            raise ValueError(f"no run with id {run_id}")
        run.status = "errored"
        run.ended_at = dt.datetime.utcnow()
        session.add(db.AuditLog(
            timestamp=dt.datetime.utcnow(), actor=actor,
            action="kill", target=str(run_id), payload_json="{}",
        ))
        session.commit()


def kill_all(*, workflow_name: str | None = None, actor: str) -> int:
    with db.state_session() as session:
        stmt = sa.select(db.WorkflowRun).where(db.WorkflowRun.status == "running")
        if workflow_name:
            stmt = stmt.where(db.WorkflowRun.workflow_name == workflow_name)
        runs = session.execute(stmt).scalars().all()
        now = dt.datetime.utcnow()
        for run in runs:
            run.status = "errored"
            run.ended_at = now
        session.add(db.AuditLog(
            timestamp=now, actor=actor, action="kill-all",
            target=workflow_name or "(all)",
            payload_json=f'{{"count": {len(runs)}}}',
        ))
        session.commit()
    return len(runs)
```

- [ ] **Step 5: Implement `doctor.py`**

Checks (exit nonzero with numbered remediation list on any failure):
1. `uv` on PATH
2. `coding-bot` on PATH with expected version
3. System binaries: `claude`, `gh`, `git`, `tmux`, `make`, `flock`
4. `/srv/coding-bot/` exists, owned `root:coding-bot`, mode 2770, writable
5. `~/.config/coding-bot/keys.toml` exists and is mode 600
6. `state.db` + `cost.db` at Alembic head (`alembic current`)
7. APScheduler tmux session alive (warn, not error)

```python
"""coding-bot doctor — environment health check."""
from __future__ import annotations
import os
import shutil
import subprocess
import stat
from pathlib import Path
from rich.console import Console

console = Console()


def run_doctor() -> bool:
    """Run all checks; return True if all pass."""
    failures: list[str] = []

    def check(name: str, ok: bool, remedy: str) -> None:
        if ok:
            console.print(f"  [green]✓[/green] {name}")
        else:
            console.print(f"  [red]✗[/red] {name}")
            failures.append(remedy)

    console.print("[bold]coding-bot doctor[/bold]")

    check("uv on PATH", shutil.which("uv") is not None,
          "install uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
    check("coding-bot on PATH", shutil.which("coding-bot") is not None,
          "uv tool install --editable /workspaces/ocr-container/coding-bot")

    for binary in ["claude", "gh", "git", "tmux", "make", "flock"]:
        check(f"{binary} on PATH", shutil.which(binary) is not None,
              f"install {binary}")

    srv = Path("/srv/coding-bot")
    check("/srv/coding-bot exists", srv.is_dir(),
          "sudo mkdir -p /srv/coding-bot && sudo chown root:coding-bot /srv/coding-bot && sudo chmod 2770 /srv/coding-bot")

    keys = Path.home() / ".config" / "coding-bot" / "keys.toml"
    check("keys.toml exists", keys.exists(),
          f"create {keys} with your API keys (chmod 600 afterwards)")
    if keys.exists():
        mode = oct(stat.S_IMODE(keys.stat().st_mode))
        check("keys.toml is 600", mode == "0o600", f"chmod 600 {keys}")

    if failures:
        console.print(f"\n[red]{len(failures)} check(s) failed:[/red]")
        for i, remedy in enumerate(failures, 1):
            console.print(f"  {i}. {remedy}")
        return False

    console.print("\n[green]All checks passed.[/green]")
    return True
```

- [ ] **Step 6: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/observability/ -v 2>&1 | tail -20
```

- [ ] **Step 7: Commit**

```
feat(observability): add pause, kill, doctor
```

---

## Phase D — `coding-bot db import-ctask` + CLI wiring

### Task D.1: `db import-ctask` migration helper

**Purpose:** One-shot migration from ctask's `tasks.json` into `state.db`
`schedule_entries`, and from `*.stats.json` history files into `cost.db`
`backend_runs`.

- [ ] **Step 1: Implement in `cli.py` under the existing `db` sub-app**

```python
@db_app.command("import-ctask")
def cmd_import_ctask(
    tasks_dir: Optional[Path] = typer.Option(None,
        help="Path to tasks dir (default: ~/.local/share/claude-tasks)"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Migrate ctask schedule entries and cost history to coding-bot DBs."""
    from coding_bot.scheduler.cli import _coerce
    import json
    import datetime as dt
    import shutil

    src = tasks_dir or (Path.home() / ".local" / "share" / "claude-tasks")
    tasks_file = src / "tasks.json"
    if not tasks_file.exists():
        console.print(f"[red]{tasks_file} not found[/red]")
        raise typer.Exit(1)

    tasks = json.loads(tasks_file.read_text())
    entries_added = 0
    runs_added = 0

    with db.state_session() as session:
        for task in tasks.get("tasks", []):
            entry = db.ScheduleEntry(
                name=task.get("name", f"ctask-{task['id']}"),
                workflow_name=_guess_workflow(task.get("command", "")),
                trigger_spec=_guess_trigger(task),
                context_preset_json=json.dumps(
                    _extract_context(task.get("command", ""))
                ),
                disabled=not task.get("active", True),
                apscheduler_job_id=None,
            )
            if not dry_run:
                session.add(entry)
            entries_added += 1
        if not dry_run:
            session.commit()

    # Import stats.json cost history
    for stats_file in src.glob("**/*.stats.json"):
        try:
            stats = json.loads(stats_file.read_text())
        except Exception:
            continue
        for row in stats if isinstance(stats, list) else [stats]:
            started = dt.datetime.fromisoformat(row.get("started_at", dt.datetime.utcnow().isoformat()))
            ended = dt.datetime.fromisoformat(row.get("ended_at", started.isoformat()))
            with db.cost_session() as session:
                if not dry_run:
                    session.add(db.BackendRun(
                        backend=row.get("backend", "claude"),
                        plan="unknown",
                        task_label=row.get("task", "ctask-import"),
                        workflow_name=None,
                        repo=row.get("repo"),
                        slot=None,
                        model=row.get("model", "unknown"),
                        effort=None,
                        started_at=started, ended_at=ended,
                        duration_ms=int((ended - started).total_seconds() * 1000),
                        exit_code=row.get("exit_code", 0),
                        input_tokens=row.get("input_tokens", 0),
                        output_tokens=row.get("output_tokens", 0),
                        cache_creation_tokens=0, cache_read_tokens=0,
                        cost_usd=row.get("cost_usd", 0.0),
                        num_turns=row.get("num_turns"),
                        is_error=row.get("is_error", False),
                        stdout_path="/dev/null", text_path="/dev/null",
                    ))
                    session.commit()
            runs_added += 1

    if dry_run:
        console.print(f"[yellow]Dry run:[/yellow] would import {entries_added} entries + {runs_added} runs.")
    else:
        # Archive
        archive = src.parent / f"claude-tasks-archived-{dt.date.today().isoformat()}"
        shutil.move(str(src), str(archive))
        console.print(f"[green]Imported {entries_added} schedule entries + {runs_added} cost rows.[/green]")
        console.print(f"Original ctask dir archived to: {archive}")


def _guess_workflow(command: str) -> str:
    if "ship-issue" in command:
        return "ship-issue"
    if "style-review" in command:
        return "style-review"
    if "style-sweep" in command:
        return "style-sweep"
    if "decompose-spec" in command:
        return "decompose-spec-auto"
    return "unknown"


def _guess_trigger(task: dict) -> str:
    interval = task.get("interval_minutes")
    if interval:
        return f"interval:minutes={interval}"
    return "interval:minutes=30"


def _extract_context(command: str) -> dict[str, object]:
    ctx: dict[str, object] = {}
    for part in command.split():
        if "/" in part and not part.startswith("-"):
            ctx["repo"] = part
        if "--slot" in part:
            try:
                ctx["slot"] = int(command.split("--slot")[1].split()[0])
            except Exception:
                pass
    return ctx
```

- [ ] **Step 2: Mount all new sub-apps in `cli.py`**

```python
# cli.py additions:
from coding_bot.observability.status import print_status
from coding_bot.observability.history import print_history
from coding_bot.observability.ps import print_ps
from coding_bot.observability.inspect import print_inspect
from coding_bot.observability.cost import print_cost
from coding_bot.observability.audit import print_audit
from coding_bot.observability.pause import pause_repo, resume_repo
from coding_bot.observability.kill import kill_run, kill_all
from coding_bot.observability.doctor import run_doctor
# Add @app.command wrappers for each
```

Full wiring: add one thin `@app.command` per subcommand that calls the
matching function with typer-parsed args and exits nonzero on failure.

- [ ] **Step 3: Smoke-test all commands**

```bash
cd /workspaces/ocr-container/coding-bot
uv run coding-bot --help
uv run coding-bot status
uv run coding-bot history --limit 3
uv run coding-bot ps
uv run coding-bot cost --since 1d
uv run coding-bot audit --limit 5
uv run coding-bot doctor
uv run coding-bot schedule list
uv run coding-bot scheduler status
```

- [ ] **Step 4: Commit**

```
feat(cli): wire all observability + scheduler subcommands + db import-ctask
```

---

## Phase E — Final CI + tag

### Task E.1: `make ci` + tag

- [ ] **Step 1: Run full CI**

```bash
cd /workspaces/ocr-container/coding-bot
make ci AI=1
```

Expected: `✅ ci passed`.

- [ ] **Step 2: Tag**

```bash
cd /workspaces/ocr-container/coding-bot
git tag v0.3-m3
```

- [ ] **Step 3: Print summary**

```bash
cd /workspaces/ocr-container/coding-bot
git log --oneline | head -15
uv run coding-bot --help
```

---

## Acceptance criteria

1. `make ci AI=1` exits 0 — all unit tests pass, ruff + mypy clean.
2. `coding-bot scheduler start` works (starts tmux session).
3. `coding-bot schedule add` / `list` round-trips through state.db.
4. `coding-bot status` / `ps` / `history` / `inspect` / `cost` / `audit` all
   print without error against an empty DB.
5. `coding-bot pause --repo org/repo` writes a `BotPause` row and an
   `AuditLog` entry; `coding-bot resume --repo org/repo` deletes it.
6. `coding-bot doctor` exits 0 on a correctly configured machine (nonzero
   with numbered list on misconfigured machines).
7. `coding-bot db import-ctask --dry-run` prints a count without writing.
8. Tag `v0.3-m3` exists.
9. No bash scripts in `scripts/` were modified.
