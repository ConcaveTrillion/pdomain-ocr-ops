# Design: coding-bot — unified workflow runner for ocr-container

**Date:** 2026-05-14
**Status:** Draft — pending review
**Scope:** Replace the workspace's ~50 mixed bash/python bot scripts with one
Python package (`coding-bot`) consolidating orchestration, scheduling, helpers,
and pre-commit hooks. Forward-compatible with multiple LLM backends (Claude
ships in v0.1; Codex and Grok as stubs). Lives in a new sibling repo at
`/workspaces/ocr-container/coding-bot/`. Cost ledger is split into its own
append-only database to support Anthropic's June 2026 API-quota model.

---

## 1. Problem

The workspace has ~50 scripts driving "bot" behavior across the eight pd-*
repos: 4 outer orchestrators (`ship-issue-orchestrator.sh`,
`style-review-orchestrator.sh`, `style-sweep-orchestrator.sh`,
`decompose-spec-auto-orchestrator.sh`), ~10 bash lifecycle scripts
(`ship-issue-success.sh`, `ship-issue-failure.sh`, `ship-issue-escalate.sh`,
`ship-issue-preflight.sh`, `bot-workspace-bootstrap.sh`, `auto-merge-wip-prs.sh`,
…), and ~25 Python helpers (label linting, spec linting, conventions sync,
spec-chain reporting, label arming, triage, cost dashboard, …). Plus `ctask`
(workspace-root Python CLI) for tmux-based scheduling.

Pain points:

1. **Bash↔Python handoffs**: orchestrators (bash) spawn `claude -p` which then
   shells out to Python helpers — Haiku context-switches mid-flow.
2. **Implicit env-var contracts**: `ISSUE`, `REPO`, `MODEL`, `ACCEPTANCE_JSON`,
   `PRE_CLAIM_SHA`, etc., are passed across shell boundaries via env vars; no
   types, no validation, no central definition.
3. **State is scattered**: `tasks.json`, `*.last`, `*.count`, `*.stop`,
   `/srv/bot-workspaces/.state/`, sidecar `*.stats.json` files. Different
   schemas, different write paths.
4. **Cost-attribution is fragile**: ctask injects `--output-format stream-json`
   via shell-string rewriting, parses NDJSON, writes JSON sidecars. Easy to
   miss a code path.
5. **Anthropic's June 2026 split** moves bot traffic to a $200/mo API quota
   (Max plan stays for interactive). Cost tracking is now structurally
   important, not just nice-to-have.
6. **No multi-backend story**: every script bakes in `claude`. CT wants
   coexistence with GPT Codex and Grok subscriptions to spread load across
   plans.

---

## 2. Goals

- **Single Python CLI** (`coding-bot`) replacing all bot-related bash and
  consolidating helpers. Zero bash inside the bot's surface.
- **Workflow-engine architecture** using `transitions` + APScheduler — declared
  state machines, persistent runs, replayable event log.
- **Structural cost separation**: every backend invocation flows through one
  launcher function; cost rows go to a dedicated append-only `cost.db` that
  the dashboard tool reads.
- **Backend abstraction**: Claude, Codex, Grok behind one `CodingBackend`
  protocol. v0.1 ships Claude only; Codex + Grok are stubs.
- **Sibling repo**: `/workspaces/ocr-container/coding-bot/`, distributed via
  `uv tool install`. Cost dashboard is a separate sibling repo.
- **Big-bang migration** on a worktree with a 48–72 hour parallel-run check
  before cutover.

### Non-goals

- Workflow declarative DSL (e.g., YAML state machines). Python classes are the
  authoring surface.
- Full durable-execution semantics à la Temporal. Restart-safety via event log
  + idempotent steps is sufficient.
- A network API or web UI. CLI only; dashboard is a separate tool.
- Backend skill abstraction for v0.1. Skill-driven workflows stay Claude-only;
  Codex/Grok workflows must carry full prompts inline (deferred to v0.2).
- Rewrites of non-bot bash (e.g., `export-models.sh`, `statusline-with-ratelimits.sh`).

---

## 3. Decisions summary

| Topic | Decision |
|---|---|
| Language | Python + Typer + Rich, distributed via `uv tool install` |
| Distribution | v0.1: local-only (`uv tool install --editable /workspaces/ocr-container/coding-bot` for both vscode + claude-bot users). No git remote required. Remote install via `ConcaveTrillion/pd-index` (PEP 503) is the v0.2 path; direct `git+URL` deps are explicitly avoided per workspace memory. |
| Repo home | New sibling `/workspaces/ocr-container/coding-bot/` |
| Migration | Big bang on a worktree; M5 parallel run; M6 cutover |
| Engine | `transitions` + APScheduler + ~200 LOC glue |
| State storage | SQLite, split into **state.db** (operational) and **cost.db** (ledger) |
| Cost ledger | Append-only; SQL triggers reject UPDATE/DELETE on `backend_runs` |
| Backend abstraction | `CodingBackend` Protocol; Claude (v0.1), Codex + Grok stubs |
| Term for backend layer | **`backend`** |
| Detect+apply | Two states in one workflow; style-sweep adds fan-out branch |
| Haiku interaction | Bot owns outer loop (Haiku is subprocess) + observability subcommands |
| Bash residue | Zero bash anywhere in bot surface |
| Locks | All bot-owned locks under `/srv/coding-bot/locks/` |
| Pricing config | Per-user `~/.config/coding-bot/pricing.toml` |
| Alembic | Two trees (`alembic-state/`, `alembic-cost/`) |
| Retention | Manual commands (`coding-bot scheduler prune-logs`, `coding-bot db backup-cost`) |
| AI=1 wrapper | Adopt pd-* Makefile convention; ship `coding-bot/scripts/ai-filter-log.py` |
| Audit log | `audit_log` table in state.db + `coding-bot audit` subcommand |
| Shared state dir | `/srv/coding-bot/`, group `coding-bot`, no per-user fallback |
| Skill files | Stay where they are (`.claude/skills/*/SKILL.md`); workflows drive lifecycle around them |

---

## 4. Architecture overview

```
                    ┌─────────────────┐
                    │  APScheduler    │   in-process daemon (tmux session)
                    │  (state.db jobs)│
                    └────────┬────────┘
                             │ fires
                             ▼
                    ┌─────────────────┐
                    │ WorkflowRunner  │   hydrate ctx from state.db,
                    │  (engine)       │   drive transitions.Machine
                    └────────┬────────┘
                             │ on_enter_*
                             ▼
                    ┌─────────────────┐
                    │ Workflow class  │   ShipIssue, StyleReview, StyleSweep,
                    │ (state machine) │   DecomposeSpecAuto
                    └────────┬────────┘
                             │ launcher.run_backend(...)
                             ▼
                    ┌─────────────────┐
                    │   launcher      │   the ONE function that spawns
                    │                 │   `claude -p`/`codex`/`grok`
                    └────────┬────────┘
                             │ stream-json / JSON / JSON
                             ▼
                    ┌─────────────────┐
                    │ Backend         │   ClaudeBackend, CodexBackend (stub),
                    │ (build + parse) │   GrokBackend (stub)
                    └────────┬────────┘
                             │ writes
              ┌──────────────┼──────────────┐
              ▼                              ▼
      ┌─────────────┐                ┌─────────────┐
      │  state.db   │                │  cost.db    │
      │ (mutable)   │                │ (append-only)│
      └─────────────┘                └─────────────┘
              ▲                              ▲
              │ read                         │ read
      ┌─────────────┐                ┌─────────────┐
      │ coding-bot  │                │cost-dashboard│
      │  observability               │  (separate   │
      │ subcommands │                │   repo)     │
      └─────────────┘                └─────────────┘
```

---

## 5. Repo layout

```
coding-bot/
├── pyproject.toml             # [project.scripts] coding-bot = "coding_bot.cli:app"
├── README.md
├── CLAUDE.md                  # subagent guidance
├── CONVENTIONS.md
├── Makefile                   # AI=1 wrapper + ci/test/lint/format/install
├── mise.toml
├── .github/workflows/ci.yml
├── alembic-state/             # state.db migrations
│   └── versions/
├── alembic-cost/              # cost.db migrations
│   └── versions/
├── scripts/
│   └── ai-filter-log.py       # PEP-723 single-file (lifted from pdomain-book-tools)
├── src/coding_bot/
│   ├── __init__.py
│   ├── cli.py                 # Typer root, wires sub-apps
│   ├── config.py              # paths (XDG-ish + /srv), env vars
│   ├── db.py                  # SQLAlchemy engines for state.db + cost.db
│   ├── launcher.py            # the ONE backend launcher
│   ├── identity.py            # vscode vs claude-bot user, sudo helpers
│   ├── locks.py               # fcntl.flock wrappers
│   ├── gh.py                  # gh CLI wrapper (issue, label, PR)
│   ├── git.py                 # git plumbing (rev-parse, push, rebase, worktree)
│   ├── audit.py               # @audited decorator, audit_log writer
│   ├── engine/                # ~500 LOC
│   │   ├── workflow.py        # @workflow decorator + Workflow base
│   │   ├── runner.py          # start/resume/step, event persistence
│   │   ├── events.py          # WorkflowEvent dataclass + SQLAlchemy mapping
│   │   └── policies.py        # EscalationLadder, TimeoutPolicy
│   ├── backends/              # backend abstraction
│   │   ├── base.py            # CodingBackend Protocol + AgentRunStats
│   │   ├── claude.py          # v0.1 implementation
│   │   ├── codex.py           # stub (NotImplementedError)
│   │   └── grok.py            # stub (NotImplementedError)
│   ├── workflows/             # one file per workflow
│   │   ├── ship_issue.py
│   │   ├── style_review.py
│   │   ├── style_sweep.py
│   │   └── decompose_spec_auto.py
│   ├── scheduler/
│   │   ├── cli.py             # schedule add/list/start/stop/run/disable
│   │   ├── daemon.py          # APScheduler BackgroundScheduler + jobstore
│   │   └── triggers.py        # parse "interval:minutes=N" / "cron:..."
│   ├── observability/
│   │   ├── status.py
│   │   ├── ps.py
│   │   ├── history.py
│   │   ├── inspect.py
│   │   ├── tail.py
│   │   ├── logs.py
│   │   ├── cost.py
│   │   ├── pause.py
│   │   ├── kill.py
│   │   ├── audit.py
│   │   └── doctor.py
│   ├── helpers/               # ex-Python scripts as modules + subcommands
│   │   ├── spec_lint.py
│   │   ├── spec_index.py
│   │   ├── spec_chain.py
│   │   ├── spec_plan.py
│   │   ├── label_lint.py
│   │   ├── label_seed.py
│   │   ├── label_arm.py
│   │   ├── conventions.py
│   │   ├── ci_check.py        # run_make_ci with AI=1 + ai-filter-log
│   │   ├── triage.py
│   │   ├── wip_pr.py
│   │   ├── bot_workspace.py   # bootstrap
│   │   ├── protections.py
│   │   └── patches.py         # apply_with_revert
│   └── hooks/                 # pre-commit-shaped entry points
│       ├── trailing_todos.py
│       ├── spec_lint.py       # calls helpers.spec_lint module
│       ├── conventions_lint.py
│       └── issue_labels_lint.py
└── tests/
    ├── unit/                  # engine, db, launcher, gh, git, locks
    ├── workflows/             # state machines with fake launcher + gh + git
    └── integration/           # against a real test repo
```

---

## 6. Storage

### 6.1 Two databases

| File | Purpose | Mutability | Owner |
|---|---|---|---|
| `/srv/coding-bot/state.db` | Workflow runs, events, scheduler jobs, locks, pauses, audit | Mutable; prunable | coding-bot (write); observability (read) |
| `/srv/coding-bot/cost.db` | Backend invocation ledger, billing periods, budgets | **Append-only** (UPDATE/DELETE rejected by SQL trigger except for the one post-run update); never pruned | launcher (insert + once-update); dashboard (read); coding-bot cost subcommand (read) |

Both in WAL mode for safe concurrent reads. Both group-owned (`root:coding-bot`,
660). Cross-DB queries via `ATTACH` (cost.db attaches state.db read-only).

### 6.2 state.db schema (operational)

```python
class WorkflowRun(Base):
    id: int
    workflow_name: str               # "ship-issue", "style-review", ...
    status: str                      # "running" | "terminal" | "errored"
    terminal_state: str | None       # "shipped" | "bounced" | "throttled" | ...
    context_json: str                # current ctx snapshot
    repo: str | None
    slot: int | None
    triggered_by: str                # "schedule:<id>" | "cli:<user>" | "resume"
    started_at: datetime
    ended_at: datetime | None
    parent_run_id: int | None        # for resumed runs
    schedule_job_id: str | None

class WorkflowEvent(Base):
    id: int
    run_id: int                      # FK → WorkflowRun
    seq: int                         # 1-based ordinal
    state: str                       # state entered
    from_state: str | None
    trigger: str | None              # transition name
    ctx_snapshot_json: str
    started_at: datetime
    ended_at: datetime | None
    error: str | None
    backend_run_id: int | None       # cross-DB soft FK to cost.db.backend_runs

class BotPause(Base):
    id: int
    repo: str | None                 # NULL = global
    paused_at: datetime
    paused_by: str
    reason: str | None
    # unique partial index: (repo) where repo IS NOT NULL; one global allowed

class SlotLock(Base):
    id: int
    workflow_name: str
    repo: str
    slot: int
    pid: int
    held_since: datetime
    lock_path: str                   # /srv/coding-bot/locks/slot.<wf>.<repo>.<N>

class ScheduleEntry(Base):
    id: int
    name: str                        # human-friendly
    workflow_name: str
    trigger_spec: str                # "interval:minutes=30" | "cron:hour=3"
    context_preset_json: str         # default ctx (repo, slot, model, effort)
    disabled: bool
    apscheduler_job_id: str          # FK to APScheduler's own table

class AuditLog(Base):
    id: int
    timestamp: datetime
    actor: str                       # os user
    action: str                      # "pause" | "schedule.add" | "kill" | "budget.update" | ...
    target: str | None               # repo, schedule_id, run_id, etc.
    payload_json: str

# plus APScheduler's apscheduler_jobs (managed by SQLAlchemyJobStore)
```

### 6.3 cost.db schema (ledger)

```python
class BackendRun(Base):
    id: int
    backend: str                     # "claude" | "codex" | "grok"
    plan: str                        # "claude-api-200" | "codex-plus" | "supergrok" | "unknown"
    task_label: str                  # "ship-issue.pdomain-book-tools.slot2"
    workflow_name: str | None        # denormalized
    workflow_run_id: int | None      # soft pointer to state.db
    repo: str | None
    slot: int | None
    model: str
    effort: str | None
    started_at: datetime
    ended_at: datetime
    duration_ms: int
    exit_code: int
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    cost_usd: float
    num_turns: int | None
    is_error: bool
    api_key_hash: str | None         # last-4 + sha (no secret)
    stdout_path: str                 # /srv/coding-bot/backend-runs/<date>/<id>.ndjson
    text_path: str                   # /srv/coding-bot/backend-runs/<date>/<id>.txt

class BillingPeriod(Base):
    id: int
    backend: str
    plan: str
    start_date: date
    end_date: date
    limit_usd: float
    notes: str | None

class Budget(Base):
    id: int
    name: str                        # "claude-monthly-api-cap"
    backend: str
    plan: str
    limit_usd: float
    window: str                      # "monthly" | "weekly" | "daily"
    warn_at_pct: float
    action_at_breach: str            # "pause-schedules" | "warn-only"
```

Append-only triggers:

```sql
CREATE TRIGGER backend_runs_no_delete BEFORE DELETE ON backend_runs
BEGIN SELECT RAISE(ABORT, 'cost.db: backend_runs is append-only'); END;

CREATE TRIGGER backend_runs_no_update_after_close
BEFORE UPDATE ON backend_runs
WHEN OLD.ended_at IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'cost.db: row closed'); END;
```

The launcher INSERTs at start (started_at only), UPDATEs once at end (closes
the row). After that, the row is immutable.

### 6.4 Filesystem layout

```
/srv/coding-bot/                          # root:coding-bot 2770 (setgid)
├── state.db (+ -wal, -shm)
├── cost.db  (+ -wal, -shm)
├── locks/
│   ├── scheduler.pid
│   ├── slot.<workflow>.<repo>.<N>
│   └── push-wip.<repo>
├── backend-runs/<YYYY-MM-DD>/<run_id>.{ndjson,txt}
├── logs/
│   ├── scheduler/<job>-<ts>.log
│   └── audit/                            # optional overflow if audit_log table grows
└── tmp/                                  # launcher scratch (cleaned on scheduler start)

~/.config/coding-bot/                     # per-user, 700
├── keys.toml                             # 600, API keys + plans
├── pricing.toml                          # vendor prices for cost computation
└── retention.toml                        # optional override of prune defaults

/srv/bot-workspaces/                      # workspace topology, unchanged
└── <workflow>/<repo>/slot<N>/
```

### 6.5 Backups + retention

Manual commands; no built-in periodic jobs.

```bash
coding-bot db backup-cost [--out /srv/coding-bot/backups/cost-2026-05-14.db]
coding-bot db prune-state [--before 2026-02-01]
coding-bot scheduler prune-logs [--older-than 14d]
```

Operators set up `cron`/`systemd-timer` externally if they want automation.
`retention.toml` only configures the manual commands' default thresholds; it
does not enable any periodic execution.

---

## 7. Backend abstraction

### 7.1 Protocol

```python
# coding_bot/backends/base.py
@dataclass
class AgentRunStats:
    model: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    cost_usd: float | None
    num_turns: int | None
    is_error: bool
    duration_ms: int
    text: str
    models_used: list[str]

class CodingBackend(Protocol):
    name: str
    def build_command(self, prompt: str, model: str, effort: str,
                      cwd: Path) -> list[str]: ...
    def parse_run(self, raw_stdout: str) -> AgentRunStats: ...
    def supported_models(self) -> list[str]: ...
    def default_plan(self) -> str: ...
```

### 7.2 v0.1 registry

```python
BACKENDS = {
    "claude": ClaudeBackend(),       # implemented
    "codex":  CodexBackend(),        # raises NotImplementedError on build_command
    "grok":   GrokBackend(),         # raises NotImplementedError on build_command
}
```

### 7.3 Resolution layers (per workflow run)

1. CLI override: `--backend codex`
2. Issue label: `backend:claude` / `backend:codex` / `backend:grok`
3. Workflow default: `Workflow.default_backend = "claude"`

In v0.1 the picker rejects `backend:codex` / `backend:grok` with a clear error.

### 7.4 Model + effort mapping

`MODEL_MAP[backend][label_value]` translates generic labels (`sonnet`, `opus`)
into backend-specific model names. Avoids encoding model names into
workflows. Lives in `coding_bot/backends/__init__.py`, versioned with code.

### 7.5 Escalation ladders

Per backend, keyed by `(model, effort)`:

```python
LADDERS = {
    "claude": [("haiku","low"), ("sonnet","medium"), ("opus","high")],
    "codex":  [("gpt-4.1-mini","low"), ("o4-mini","medium"), ("gpt-5-codex","high")],
    "grok":   [("grok-code-fast-1","low"), ("grok-4","medium"), ("grok-4","high")],
}
```

`LADDERS[backend].next(model, effort)` returns the next rung or None.

### 7.6 CLI surface verification (M1 spike)

`build_command` and `parse_run` for codex and grok need to be verified against
the actual binaries' surfaces before they leave stub status. Will happen as a
short spike before workflows use them in v0.2.

---

## 8. Workflow engine

### 8.1 Authoring surface

```python
@workflow(name="ship-issue", context=ShipIssueContext)
class ShipIssue:
    states = [...]                   # state names
    initial = "throttle_check"
    terminal = {"shipped", "bounced", "throttled", "no_eligible"}
    transitions = [
        # (trigger,    source,    dest)
        ("ok",         "throttle_check", "picking"),
        ...
    ]

    def on_enter_<state>(self, ctx) -> None:
        # do the work for this state; call self.<trigger>() to transition
```

The `@workflow` decorator wraps the class with a `transitions.Machine` and
registers it in a global registry.

### 8.2 Runner contract

```python
class WorkflowRunner:
    def start(self, workflow_name: str, context: dict,
              triggered_by: str) -> RunId: ...
    def resume(self, run_id: RunId) -> None: ...
    def step(self, run_id: RunId) -> WorkflowEvent: ...
```

Every state entry writes a `WorkflowEvent` row before the `on_enter_*` body
runs. A SIGKILL mid-step leaves an event with no `ended_at`; on `resume` the
runner re-enters that state. **Step handlers must be idempotent or check for
prior completion** (same property current bash needs).

### 8.3 Dependency injection

The runner takes a `launcher` argument. Production wiring uses the real
launcher; tests pass `FakeLauncher` with scripted results.

### 8.4 Policies

Each workflow declares a `WorkflowPolicy` (timeouts, escalation ladder
reference, retry counts, slot count, fan-out threshold). Defaults can be
overridden per schedule entry.

---

## 9. The four workflows

### 9.1 `ship-issue`

**States:** `throttle_check → picking → claimed → preflight → slicing →
ci_check → pushing → labeling → shipped` plus `escalating ← slicing|ci_check`
loop and terminal states `bounced`, `throttled`, `no_eligible`.

**Context:**

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
```

**Consolidates:**

- `ship-issue-orchestrator.sh`
- `ship-issue-preflight.sh`
- `ship-issue-pick.py`
- `ship-issue-success.sh`
- `ship-issue-failure.sh`
- `ship-issue-escalate.sh`
- `ship-issue-throttle-check.sh`
- `ship-issue-file-broken-ci.py`
- `ship-issue-triage-ci-failure.py`
- `ship-issue-cleanup-bounced.py`
- `arm-issue.py`
- rolling-PR pieces of `merge-wip-ship-issue-pr.sh`

**Behaviors preserved:**

- 1h45m slice timeout (recent orchestrator fix)
- `make ci` failure on integration branch → reset `status:in-pr` to
  `status:ready`
- Pre-commit auto-format fixup commits before push
- Bot unblocking after fix-wip ships to integration branch
- Stale fix-wip claim recovery

### 9.2 `style-review` (per-PR)

**States:** `read_tag → compute_diff → detecting → applying → commenting →
advancing_tag → done` plus terminal `no_diff`, `errored`.

**Pattern:** one LLM detect call producing JSON findings (high-confidence
patches + judgment comments); deterministic Python apply with per-batch
`make ci` revert-on-failure; PR review comments for judgment findings; tag
advances at end.

**Consolidates:** `style-review-orchestrator.sh`,
`style-review-detect.py`, `style-review-apply.py`.

### 9.3 `style-sweep` (tree-wide, weekly)

**States:** `reset_branch → scoping → detecting → applying → opening_pr → done`
plus `partitioning → fan_out_detecting` branch from `scoping`, and terminals
`no_findings`, `errored`.

**Fan-out trigger:** `scoping` measures diff/tree size. If under
`fan_out_threshold_tokens` (default ~80% of backend context), proceeds to
single-shot `detecting`. Otherwise: `partitioning` buckets by directory (or
rule category — pinned during M2 spike), `fan_out_detecting` spawns N parallel
backend calls (capped at 3 concurrent), findings aggregate into `ctx.findings`,
`applying` proceeds unchanged. Feature-flagged off in v0.1; lit up when
context-window pressure measurably appears.

**Consolidates:** `style-sweep-orchestrator.sh` and reuses the apply logic from
style-review at the module level.

### 9.4 `decompose-spec-auto`

**States:** `find_next_spec → extract_spec_path → planning → applying → done`
plus terminal `nothing_to_do`, `errored`.

**Planning step:** calls `coding_bot.helpers.spec_plan.propose_children(...)`
in-process; only spawns claude via launcher for the `/decompose-spec-auto`
skill if/when the helper logic needs LLM assistance for hard cases. Apply step
creates milestone + child issues via `gh.py`.

**Consolidates:** `decompose-spec-auto-orchestrator.sh`,
`decompose-spec-plan.py`, `decompose-spec-apply.py`. Reuses `spec_slug.py` and
`spec_chain_data.py` as helper modules.

### 9.5 Workflows NOT in v0.1

- `pr-review`: stays as a CT-interactive skill (`/pr-review`).
- `fixing-specs`: CT-interactive walkthrough; stays as skill.
- `triage`: CT-interactive; helpers move into `coding_bot.helpers.triage`
  for reuse.
- `auto-merge-wip-prs`: stays a helper subcommand
  (`coding-bot wip-pr auto-merge`); becomes a 5th workflow only if state
  complexity grows.
- `check-ci-failures`: helper subcommand only (`coding-bot ci check`).

---

## 10. Launcher

### 10.1 Contract

```python
def run_backend(
    *,
    backend: str,
    prompt: str,
    model: str,
    effort: str,
    cwd: Path,
    task_label: str,
    workflow_run_id: int | None = None,
    workflow_event_id: int | None = None,
    repo: str | None = None,
    slot: int | None = None,
    timeout: int = 6300,             # 1h45m
    env: dict | None = None,
    api_key_profile: str | None = None,
) -> LaunchResult:
    ...
```

### 10.2 Steps

1. Resolve backend in registry; reject unknown.
2. Resolve model via `MODEL_MAP[backend]` if caller passed a generic label.
3. Pre-flight budget check: query `cost.db.backend_runs` for current period
   spend; abort with `BudgetExceeded` if breach action is `pause-schedules`.
4. **INSERT** pre-run row in `cost.db` (`started_at` only) — assigns
   `backend_run_id`. Crash before completion still leaves a row.
5. Build argv via `backend.build_command(prompt, model, effort, cwd)`.
6. Resolve API key from `~/.config/coding-bot/keys.toml`; set env;
   record profile name + sha-of-key in row.
7. Spawn subprocess; capture stdout/stderr to
   `/srv/coding-bot/backend-runs/<date>/<id>.ndjson` with `timeout=`.
8. Parse via `backend.parse_run(raw)` → `AgentRunStats`.
9. **UPDATE** cost.db row with stats (the only allowed update; trigger
   enforces).
10. Write parsed text to `<id>.txt`.
11. Return `LaunchResult`.

### 10.3 Cost source per backend

| Field | Claude | Codex | Grok |
|---|---|---|---|
| tokens (input/output) | stream-json assistant events | JSON usage block | JSON usage block |
| cache_* tokens | stream-json cache fields | — (0) | — (0) |
| `cost_usd` | `result.total_cost_usd` | computed via `pricing.toml` | computed via `pricing.toml` |
| `num_turns` | `result.num_turns` | message count | message count |

### 10.4 Timeout handling

- Default 6300 s (1h45m).
- On timeout: kill, `timed_out=True`, partial stdout best-effort parsed,
  `exit_code=-9`, `is_error=True`, cost row still closed with whatever tokens
  were consumed.

### 10.5 Crash safety

- Pre-run insert means any SIGKILL leaves a `started_at`-only row.
- `coding-bot db reap-dangling-runs` finds rows older than 2× max timeout with
  no `ended_at`, closes them with `is_error=True, exit_code=-1`.
- Same idea for `workflow_events` in state.db.

### 10.6 Interactive bypass: structural

There is **no API** for "run a backend but don't record cost." If anything
spawns `claude` outside `run_backend`, it never appears in cost.db.
Interactive CT sessions in the IDE never go through coding-bot, so they're
structurally excluded. `coding-bot ship-issue run --issue 253` typed by a
human DOES go through the launcher and IS counted — `triggered_by="cli:vscode"`
distinguishes it for dashboards.

### 10.7 Config files

```toml
# ~/.config/coding-bot/keys.toml
[profiles.bot-claude]
backend = "claude"
api_key = "sk-ant-..."
plan = "claude-api-200"

# ~/.config/coding-bot/pricing.toml
[claude.sonnet]
input_per_mtok = 3.00
output_per_mtok = 15.00
cache_write_per_mtok = 3.75
cache_read_per_mtok = 0.30
```

Pricing per-user (each user keeps it updated for their own visibility).

---

## 11. Scheduler

### 11.1 Process model

APScheduler runs in-process inside a `coding-bot scheduler run` daemon,
launched via `coding-bot scheduler start` which detaches it into a tmux
session `coding-bot-scheduler`. SQLAlchemy jobstore points at `state.db`.

```
coding-bot scheduler start          # tmux-detached
coding-bot scheduler stop           # SIGTERM, graceful
coding-bot scheduler status
coding-bot scheduler restart
coding-bot scheduler run            # foreground (what `start` runs inside tmux)
```

PID lock at `/srv/coding-bot/locks/scheduler.pid` prevents multiple instances.

### 11.2 Schedule entries

```bash
coding-bot schedule add ship-issue-pdomain-book-tools \
    --workflow ship-issue \
    --trigger "interval:minutes=30" \
    --context repo=pdomain/pdomain-book-tools,slot=2
```

Stored in `state.db.schedule_entries` (display metadata) plus
`apscheduler_jobs` (APScheduler internal).

Triggers:
- `interval:minutes=N` | `interval:hours=N`
- `cron:hour=N,minute=N,day_of_week=...`
- `date:run_at=ISO8601` (one-shot)

### 11.3 Firing a job

```python
def fire_workflow(workflow_name, context_preset, schedule_entry_id):
    in_flight = find_active_run(workflow_name, **context_preset)
    if in_flight:
        runner.resume(in_flight.id); return
    if is_paused(context_preset.get("repo")):
        log_skipped(reason="paused"); return
    if budget_blocks(backend, plan):
        log_skipped(reason="budget"); return
    runner.start(workflow_name, context_preset,
                 triggered_by=f"schedule:{schedule_entry_id}")
```

`coalesce=True, max_instances=1` per job prevents double-fires.

### 11.4 Concurrency

`ThreadPoolExecutor(max_workers=4)` for cross-job concurrency. Per-slot
exclusion via `SlotLock` flock files.

### 11.5 Missed-fire policy

`misfire_grace_time=600` (10 minutes). Older suppressed with logged event.

### 11.6 Restart recovery

On `scheduler start`:
1. APScheduler resumes triggers from jobstore.
2. For each `workflow_run` in `status="running"`, enqueue a one-shot recovery
   job: `runner.resume(run_id)`.
3. Reap dangling cost.db rows (started_at without ended_at, older than 2× max
   timeout).

### 11.7 Migration from ctask

`coding-bot db import-ctask` (one-shot at cutover):

1. Reads `~/.local/share/claude-tasks/tasks.json`; creates equivalent
   `schedule_entries` rows.
2. Reads `*.stats.json` history; INSERTs `backend_runs` rows
   (`plan="unknown"`, `backend="claude"`).
3. Renames `~/.local/share/claude-tasks/` to
   `~/.local/share/claude-tasks-archived-YYYY-MM-DD/`.

---

## 12. Observability

```bash
coding-bot status [--watch] [--json]      # top dashboard: scheduler + active runs + cost
coding-bot ps [--workflow X] [--repo X]
coding-bot history [--limit N] [--since 24h] [--workflow X] [--terminal-state X]
coding-bot inspect <run-id> [--events] [--replay]
coding-bot tail <run-id> | --workflow X | --task X
coding-bot logs <run-id> [--json]
coding-bot cost [--since 7d] [--group-by backend|task|workflow] [--json]
coding-bot pause [--repo X] [--reason "..."]
coding-bot resume [--repo X]
coding-bot pause status
coding-bot kill <run-id> | --all | --workflow X
coding-bot audit [--limit N] [--actor X] [--action X]
coding-bot scheduler status
coding-bot doctor                          # perms + groups + DBs + sudoers
```

All have `--json` for machine consumption (Haiku-friendly), all support
`--db PATH` for inspecting offline copies, all observability commands are
read-only except `pause`, `resume`, `kill` (which write audit log entries).

`inspect --replay` is a v0.2 feature; v0.1 ships `inspect` showing the event
log + ctx snapshots + linked cost rows.

---

## 13. Helpers + hooks

### 13.1 Helper subcommands

Verb-noun grouping under top-level domains:

```
coding-bot spec {lint, index, chain-report, from-issue-finalize}
coding-bot label {lint, seed, arm, migrate-claude-ok}
coding-bot conventions {extract, sync, lint, check-drift, check-sibling-drift}
coding-bot ci {check, triage}
coding-bot triage {sweep, fork}
coding-bot wip-pr {status, auto-merge, merge}
coding-bot bot-workspace {bootstrap, list}
coding-bot protections verify
coding-bot db {upgrade, backup-cost, prune-state, import-ctask, reap-dangling-runs}
coding-bot agents list
coding-bot budget {add, list, status}
coding-bot setup                           # one-time perms + groups + dir creation
```

Each is **both** a CLI subcommand and an importable module (workflows call the
module functions directly; CLI is for humans and pre-commit).

### 13.2 Pre-commit hooks

```bash
coding-bot hook trailing-todos [files...]
coding-bot hook spec-lint [files...]
coding-bot hook conventions-lint [files...]
coding-bot hook issue-labels-lint
```

pd-* `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: trailing-todos
      entry: coding-bot hook trailing-todos
      language: system
      types: [text]
```

Each developer environment and CI runner installs `coding-bot` via
`uv tool install` (one line in CI workflows; mise.toml bootstrap in dev).

### 13.3 What gets deleted from scripts/ at cutover

`scripts/ship-issue-*.{sh,py}`, `scripts/style-*.{sh,py}`,
`scripts/decompose-spec-*.{sh,py}`, `scripts/lint-*.py`,
`scripts/*-conventions.py`, `scripts/spec_*.py`, `scripts/arm-issue.py`,
`scripts/triage-*.py`, `scripts/auto-merge-wip-prs.sh`,
`scripts/pr-wip-status.sh`, `scripts/merge-wip-ship-issue-pr.sh`,
`scripts/bot-workspace-bootstrap.sh`, `scripts/verify-protections.sh`,
`scripts/no-trailing-todos.sh`, `scripts/seed-labels.sh`,
`scripts/migrate-claude-ok-*.sh`, `scripts/check-ci-failures.sh`.

`scripts/build-cost-dashboard.py` moves to the new `cost-dashboard/` sibling repo.

Kept (out of scope for this rewrite): `scripts/statusline-with-ratelimits.sh`,
`scripts/export-models.sh`, `scripts/upload-models.sh`,
`scripts/patch-brainstorming-skill.sh`. Workspace bash that isn't bot-related.

---

## 14. Identity, worktrees, locks

### 14.1 Users

| User | Role | coding-bot install |
|---|---|---|
| `vscode` | CT interactive, pre-commit hooks | `~vscode/.local/bin/coding-bot` |
| `claude-bot` | Scheduled bot runs in `/srv/bot-workspaces/` | `~claude-bot/.local/bin/coding-bot` |

Both belong to the `coding-bot` group. `/srv/coding-bot/` is owned
`root:coding-bot` with 2770 (setgid).

### 14.2 Scheduler runs as claude-bot

The scheduler tmux session lives in `claude-bot`'s session. All workflows it
fires run as `claude-bot`. Interactive single-shots from `vscode` run as
vscode by default, or `sudo -u claude-bot ...` (or `--as-bot` shortcut) if CT
wants to use the bot's keys + worktree.

### 14.3 Worktree topology (unchanged from `docs/process/bot-workspaces.md`)

```
/srv/bot-workspaces/
└── <workflow>/<repo>/slot<N>/    # detached HEAD, owned claude-bot
```

`coding-bot bot-workspace bootstrap` replaces `bot-workspace-bootstrap.sh`.

### 14.4 Locks (`fcntl.flock`)

```
/srv/coding-bot/locks/scheduler.pid                    # one scheduler
/srv/coding-bot/locks/slot.<workflow>.<repo>.<N>       # per slot
/srv/coding-bot/locks/push-wip.<repo>                  # serialize integration pushes
```

`SlotLock` table in state.db is the audit copy; flock is the source of truth.

### 14.5 Pause flag

`BotPause` row replaces `/srv/bot-workspaces/.state/bots-paused.<repo>`.
Grace period: scheduler checks both DB rows AND legacy flag files for 30 days
post-cutover, then flag-file fallback is dropped.

### 14.6 API key isolation

Per-user `keys.toml` (0600). Launcher reads from the running user's home dir.
Cost row records the actual key's hash + plan.

---

## 15. Makefile AI=1 convention

coding-bot adopts the same pattern as pd-* repos
(see `docs/specs/2026-05-14-ai-make-output-design.md`):

```makefile
AI ?= 1
LOG := .ci-ai.log

ifdef AI
target:
	@rm -f $(LOG)
	@$(MAKE) --no-print-directory AI= $@ > $(LOG) 2>&1 \
		&& echo "✅ $@ passed (log: $(LOG))" \
		|| (echo "❌ $@ failed:"; uv run scripts/ai-filter-log.py $(LOG); echo "(full log: $(LOG))"; exit 1)
else
# normal verbose targets
endif
```

`coding-bot/scripts/ai-filter-log.py` (PEP-723 single-file) extracts
pytest/cargo/ruff failure sections, capped at 300 lines.

**`coding_bot.helpers.ci_check.run_make_ci(...)`** — the function workflows
call to run `make ci` in pd-* repos — invokes with `AI=1` (or relies on the
default), captures the filtered failure excerpt into the workflow event's
`error` field on failure (not the full log), and stores the full log path in
`ctx.ci_failure_log_path` for `coding-bot inspect` drill-down. Big token win.

---

## 16. Packaging and installation

### 16.1 pyproject.toml shape

```toml
[project]
name = "coding-bot"
version = "0.1.0"
description = "Unified workflow runner for ocr-container bot automation"
requires-python = ">=3.12"
authors = [{name = "CT", email = "concavetrillion@gmail.com"}]
dependencies = [
    "typer>=0.12",
    "rich>=13",
    "transitions>=0.9",
    "apscheduler>=3.10,<4",
    "sqlalchemy>=2",
    "alembic>=1.13",
    "pydantic>=2",
    "tomli-w",
    "httpx",                # vendor API reconciliation (v0.2+)
]

[project.scripts]
coding-bot = "coding_bot.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
managed = true
```

`coding-bot` on PATH → `coding_bot.cli:app` (Typer's app callable).

### 16.2 v0.1 install — local-only, no git remote required

The workspace runs entirely on the local filesystem; coding-bot can be
installed without pushing to GitHub. Two local paths:

**A. Editable from local source (recommended for both dev + prod use)**

```bash
# vscode user
uv sync --project /workspaces/ocr-container/coding-bot     # populate .venv
uv tool install --editable /workspaces/ocr-container/coding-bot

# claude-bot user
sudo -u claude-bot bash -lc \
    'uv tool install --editable /workspaces/ocr-container/coding-bot'
```

Edits to `src/coding_bot/` take effect immediately. The same on-disk source
tree is installed for both users; each user gets an isolated venv at
`~/.local/share/uv/tools/coding-bot/`.

This is the **v0.1 default** for both users. Upgrades = pull the repo.

**B. Local wheel build (for pinned installs without editable's live-source coupling)**

```bash
cd /workspaces/ocr-container/coding-bot
uv build                                     # writes dist/coding_bot-0.1.0-py3-none-any.whl
uv tool install dist/coding_bot-0.1.0-py3-none-any.whl
sudo -u claude-bot bash -lc \
    "uv tool install /workspaces/ocr-container/coding-bot/dist/coding_bot-0.1.0-py3-none-any.whl"
```

Useful when you want a stable installed version that won't shift if you edit
the source tree. Reinstall on each version bump.

### 16.3 Optional: remote install via pd-index

A workspace-level decision (memory `project_release_strategy.md`) is to
publish pd-* wheels into `ConcaveTrillion/pd-index` — a self-hosted PEP 503
index on GitHub Pages — instead of using PEP 508 `git+URL` direct deps (those
burn the PyPI bridge). pd-index doesn't exist yet.

If/when coding-bot wants remote distribution (e.g., for pd-* repos' CI to
consume it without checking out the workspace), the path is:

```bash
uv tool install coding-bot --index https://concavetrillion.github.io/pd-index/
```

NOT `--from git+https://github.com/...` — that pattern is explicitly avoided
workspace-wide.

For v0.1 this is deferred. Section 16.5 covers what changes when remote
install lights up.

### 16.4 Prerequisites

`uv` itself must be installed for **both** users (vscode + claude-bot). The
container bootstrap should ensure this; `coding-bot doctor` verifies.
Fallback install: `curl -LsSf https://astral.sh/uv/install.sh | sh`.

System binaries coding-bot shells out to (not Python deps; must be on PATH):

| Binary | Used by |
|---|---|
| `claude` (and `codex`, `grok` later) | launcher |
| `gh` | gh.py wrapper |
| `git` | git.py wrapper |
| `tmux` | scheduler start/stop |
| `make` | ci_check helper |
| `flock` (util-linux) | locks.py |

`coding-bot doctor` reports missing ones with install hints.

### 16.5 CI installation — deferred to v0.2

pd-* repos' CI runners currently invoke `bash scripts/*.sh` and
`python3 scripts/*.py` directly. For v0.1, that does NOT change in CI:

- **Pre-commit hooks invoked by pd-* repos' CI** keep their current shape
  (the bash scripts stay during M0–M6; only at M6 cutover are they deleted
  from the workspace).
- **After M6 cutover, the pre-commit hooks in each pd-* repo point at
  `coding-bot hook X`.** For pd-* CI to run those hooks, coding-bot has to
  be installable in the CI environment.
- v0.1's local-only install (§16.2) doesn't satisfy CI — CI runners can't
  read CT's workspace filesystem.

**Two short-term options at M6:**

1. **Vendor coding-bot into each pd-* repo at CI time** by cloning the
   workspace's coding-bot repo via a CI artifact bridge (HTTPS link to a
   wheel built by a workspace CI workflow). Complicated; deferred.
2. **Keep pre-commit hooks bash for now in CI environments only**, by
   special-casing the entry point. Pre-commit can use different entries
   per environment via separate hook configs; one for local (`coding-bot
   hook X`) and one for CI (`bash scripts/X.sh`). Ugly during overlap.

**Recommended path:** stand up `ConcaveTrillion/pd-index` (the workspace's
already-decided self-hosted PEP 503 index) **before** flipping pd-* CI to
require coding-bot. Until then, pd-* CI keeps the legacy bash entries; only
local dev environments switch to `coding-bot hook`.

This means M6 cutover deletes bash scripts from the workspace `scripts/` but
**each pd-* repo retains its old hook entries (and its own local copies of
the hook scripts if needed) until pd-index lights up.** Cleaner than the
alternatives, slower than ideal.

A future amendment to this spec covers the pd-index integration.

### 16.6 Upgrade

With **editable installs (§16.2A)** there's nothing to upgrade — running
`coding-bot` always reflects the current `src/coding_bot/` source. The
"upgrade" is `git pull` in `/workspaces/ocr-container/coding-bot/` (or
direct edits). If dependencies change in `pyproject.toml`, force a re-resolve:

```bash
uv tool install --reinstall --editable /workspaces/ocr-container/coding-bot
sudo -u claude-bot bash -lc \
    'uv tool install --reinstall --editable /workspaces/ocr-container/coding-bot'
```

With **wheel installs (§16.2B)**, install the new wheel after rebuilding:

```bash
uv build && uv tool install --reinstall dist/coding_bot-0.1.0-py3-none-any.whl
```

`coding-bot db upgrade` runs on every startup (cheap, idempotent): applies
any pending Alembic migrations against state.db and cost.db before the CLI
does anything else. Stale-schema runs are structurally impossible.

### 16.7 Verification (`coding-bot doctor`)

Checks:

- `uv` on running user's PATH.
- `uv tool list` shows `coding-bot` with expected version.
- System binaries present (claude, gh, git, tmux, make, flock).
- `/srv/coding-bot/` ownership (`root:coding-bot`), mode (`2770`),
  writable by running user.
- `~/.config/coding-bot/keys.toml` exists, mode 600, parseable.
- state.db and cost.db at Alembic head.
- Sudoers entry for `vscode → claude-bot` if `--as-bot` is intended.

Exits nonzero with a numbered checklist of remediations on any failure.

### 16.8 Uninstall

```bash
uv tool uninstall coding-bot
```

Removes the venv + `~/.local/bin/coding-bot` symlink only. Data
(`/srv/coding-bot/`, `~/.config/coding-bot/`) is NOT touched — a misclicked
uninstall must not lose cost history. Data removal is a deliberate manual
`rm -rf`.

---

## 17. Migration plan

| Milestone | Days | Scope |
|---|---|---|
| M0 — Bootstrap | 1 | Repo scaffolding (pyproject, Makefile, mise, CLAUDE.md, CONVENTIONS.md, CI). **git init + local `main` branch only — no remote required.** Optionally push to ConcaveTrillion/coding-bot later if/when remote becomes useful (CI integration in v0.2 etc.). Same for cost-dashboard sibling repo. |
| M1 — Engine + storage | 2–4 | Alembic, engine, db, launcher, ClaudeBackend, Codex/Grok stubs; tests |
| M2 — Workflows | 5–7 | Port the four workflows with mocked launcher + gh + git |
| M3 — Scheduler + observability | 8–9 | APScheduler wiring; all observability subcommands; doctor |
| M4 — Helpers + hooks | 10–11 | Port all Python helpers; hook namespace; setup command |
| M5 — Parallel run | 12–14 | Install on both users; `db import-ctask`; mirror ctask schedules on different slots; 48–72h watch |
| M6 — Cutover | 15 | ctask stop + archive; flip pre-commit configs; delete scripts/; update CLAUDE.md across pd-* repos |
| M7 — Stabilize | week 3 | Watch for regressions; ship via coding-bot's own ship-issue workflow |

**Rollback window:** through M5 trivial (just stop coding-bot, ctask is
running); through ~30 days post-M6 possible (re-arm ctask from archive,
revert pre-commit flips); after ~30 days, cost.db data uniqueness makes
rollback lossy.

**ctask retention:** kept installable indefinitely as a read-only viewer of
the archived `~/.local/share/claude-tasks-archived-YYYY-MM-DD/` directory.

### Skill files

`.claude/skills/<name>/SKILL.md` files stay where they are. The launcher
spawns `claude -p "/ship-issue"` and Haiku follows the skill inside the
slice. Workflows drive the lifecycle around the skill; the skill drives the
slice itself.

---

## 18. Test strategy

- **Unit:** engine, db, launcher (FakeBackend), gh wrapper, git wrapper, locks,
  audit decorator.
- **Workflow tests:** each workflow with `FakeLauncher` driving every state
  machine to every terminal state. Tests assert event sequence, cost row
  shape, terminal context.
- **Integration:** scratch GitHub repo, real launcher against `claude` binary
  (gated by `CODING_BOT_INTEGRATION=1` env var to avoid burning tokens in
  routine CI). Run each workflow once per integration suite.
- **Migration test:** `coding-bot db import-ctask` against a fixture
  `~/.local/share/claude-tasks/` tree; assert backend_runs rows match
  expected.
- **Alembic CI step:** `alembic upgrade head` against a temp DB for both
  state.db and cost.db; assert no warnings.
- **AI=1 wrapper:** snapshot test on a deliberately-failing target; assert
  `ai-filter-log.py` extracts the right sections.

---

## 19. Open questions

1. **Codex CLI surface** — `build_command` and `parse_run` for codex and grok
   are sketched against assumed flag names; M1 spike pins them.
2. **Style-sweep partition strategy** — by directory or by rule category. Pin
   during M2 implementation; either works.
3. **Auto-merge-wip-prs as 5th workflow** — currently planned as a helper.
   Convert if state complexity grows (poll/eligible/merge/reset states).
4. **Reconciliation against vendor billing APIs** — currently per-row cost is
   estimate-only. For Anthropic specifically, may want a `coding-bot cost
   reconcile` that pulls authoritative monthly totals via the org API and
   reports drift. v0.2.
5. **inspect --replay** — useful for "did the bot do the right thing given
   that ctx" debugging; v0.2.
6. **Backend skill abstraction** — neutral procedure format that renders to
   Claude/Codex/Grok prompts. v0.2 work; required before non-Claude workflows
   can use existing skills.

---

## 20. References

- `docs/process/bot-workspaces.md` — worktree topology + lock model
- `docs/process/ship-issue-interactive.md` — interactive runner design
- `docs/architecture/style-review-json-contract.md` — JSON contract for
  style-review detect/apply
- `docs/specs/2026-05-14-ai-make-output-design.md` — AI=1 Makefile
  convention
- `ctask` (workspace root) — current scheduler being replaced
- `scripts/ship-issue-*` — current ship-issue lifecycle being replaced
- `scripts/style-*-orchestrator.sh` — current style orchestrators
- `scripts/decompose-spec-auto-orchestrator.sh` — current decompose orchestrator
- transitions library: <https://github.com/pytransitions/transitions>
- APScheduler: <https://apscheduler.readthedocs.io>
