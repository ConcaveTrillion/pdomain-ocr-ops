# ship-issue: wip-branch maintenance, preflight rebase, and per-issue ladders

**Date:** 2026-05-14
**Status:** approved, pending implementation

## Overview

Three related enhancements to the `ship-issue` workflow:

1. **Per-issue escalation ladders** — each issue carries effort labels that determine its starting `(model, effort)` and which escalation ladder to climb.
2. **Preflight rebase** — before handing off to the agent, reset the worktree to `origin/wip/ship-issue` and rebase onto `origin/main`.
3. **Wip-branch maintenance mode** — when `wip/ship-issue` is behind `origin/main`, one slot becomes the maintenance bot: rebase + CI + push, then exit without picking an issue. A DB mutex prevents parallel slots from interfering.
4. **Auto-file blocking issues** — rebase failure or CI failure during maintenance files a `bot:blocks-all` + `bot:fix-wip` issue; those issues are the only thing the bot will pick until resolved, at elevated model/effort.

---

## Label taxonomy additions

Two new labels needed on all `pd-*` repos (matching existing taxonomy):

| Label | Description | Color |
|---|---|---|
| `effort:XL` | Extra-large / opus-only | `#d93f0b` |
| `bot:blocks-all` | Open issue with this label halts all normal bot issue-picking | `#b60205` |

`bot:fix-wip` already exists ("Bot diagnostic: fix broken CI on wip/ship-issue") and is used as the issue-type label on auto-filed issues alongside `bot:blocks-all`.

---

## Escalation ladders

Defined in `coding_bot/engine/policies.py`. Each ladder is a sequence of `(model, effort)` rungs; `ladder.next()` returns the next rung or `None` (bounce).

| Ladder key | Rungs |
|---|---|
| `claude:small` | haiku/low → sonnet/medium → sonnet/high → opus/high |
| `claude:medium` | sonnet/medium → sonnet/high → opus/high |
| `claude:large` | sonnet/high → opus/high |
| `claude:xlarge` | opus/high |
| `claude:blocker` | sonnet/medium → sonnet/high → opus/high |

### Label → ladder mapping (evaluated at picking time)

Priority: `bot:blocks-all` overrides all effort labels.

| Issue labels | Starting `(model, effort)` | `ladder_key` |
|---|---|---|
| `bot:blocks-all` | sonnet / medium | `claude:blocker` |
| `effort:S` | haiku / low | `claude:small` |
| `effort:M` (default if unlabeled) | sonnet / medium | `claude:medium` |
| `effort:L` | sonnet / high | `claude:large` |
| `effort:XL` | opus / high | `claude:xlarge` |

`model:*` and `model-effort:*` labels on an issue override the effort-derived `(model, effort)` when present, but do not change `ladder_key`.

---

## DB schema addition

New table in `state.db` (`coding_bot/db.py`):

```python
class WipRebaseLock(Base):
    __tablename__ = "wip_rebase_lock"
    repo       = Column(Text, primary_key=True)
    slot       = Column(Integer, nullable=False)
    claimed_at = Column(DateTime, nullable=False)
```

**Claim:** `INSERT OR IGNORE` + rowcount check. If rowcount = 0, another slot holds the lock → `throttled`.

**Release:** `DELETE WHERE repo = ?` in:
- `on_enter_wip_updated` (success path)
- `on_enter_bounced` when `ctx.issue is None` (maintenance failure path)

**Crash recovery:** The daemon reaper (`launcher.reap_dangling_runs`) also clears locks older than `max_timeout_secs` on startup.

---

## `ShipIssueContext` additions

```python
ladder_key: str = "claude:medium"   # set by picking; drives escalation lookup
blocker_mode: bool = False           # True when picked issue carries bot:blocks-all
```

---

## Updated state machine

### States

```
# existing
throttle_check, picking, claimed, preflight, slicing, ci_check, pushing,
labeling, shipped, bounced, throttled, no_eligible, escalating

# new
checking_wip, rebasing_wip, ci_check_wip, wip_updated
```

Terminal set: `{shipped, bounced, throttled, no_eligible, wip_updated}`

### Transitions

```python
# throttle_check (changed: ok now goes to checking_wip, not picking)
("ok",            "throttle_check", "checking_wip"),
("throttle",      "throttle_check", "throttled"),

# checking_wip (new)
("wip_current",   "checking_wip",   "picking"),
("wip_behind",    "checking_wip",   "rebasing_wip"),

# picking (unchanged transition names)
("found",         "picking",        "claimed"),
("none_found",    "picking",        "no_eligible"),

# claimed → preflight → slicing (preflight gains a bounce path)
("ready",         "claimed",        "preflight"),
("preflighted",   "preflight",      "slicing"),
("bounce",        "preflight",      "bounced"),
("slice_ok",      "slicing",        "ci_check"),
("escalate",      "slicing",        "escalating"),

# escalating (unchanged)
("retry",         "escalating",     "slicing"),
("bounce",        "escalating",     "bounced"),

# ci_check → pushing (unchanged)
("ci_ok",         "ci_check",       "pushing"),
("ci_fail",       "ci_check",       "escalating"),

# pushing → labeling → shipped (unchanged)
("pushed",        "pushing",        "labeling"),
("bounce",        "pushing",        "bounced"),
("labeled",       "labeling",       "shipped"),

# rebasing_wip (new)
("rebased",       "rebasing_wip",   "ci_check_wip"),
("rebase_failed", "rebasing_wip",   "bounced"),

# ci_check_wip (new)
("ci_ok",         "ci_check_wip",   "wip_updated"),
("ci_fail",       "ci_check_wip",   "bounced"),
```

---

## State handler behaviour

### `on_enter_throttle_check`

Added check: if `WipRebaseLock` row exists for `ctx.repo` (held by another slot) → `self.throttle()`.

### `on_enter_checking_wip`

```
git.fetch(worktree)
behind = git.is_behind(worktree, branch="origin/wip/ship-issue", ref="origin/main")
if behind:
    claim WipRebaseLock (INSERT OR IGNORE)
    if claim failed → self.throttle()
    else → self.wip_behind()
else:
    self.wip_current()
```

### `on_enter_picking` (changed)

Before the existing eligible-issue loop:

```
blockers = gh.issue_list(repo, labels=["bot:blocks-all"])
open_blockers = [i for i in blockers if not {in-progress, in-pr} ∩ labels(i)]
if open_blockers:
    pick open_blockers[0]
    ctx.model, ctx.effort = "sonnet", "medium"
    ctx.ladder_key = "claude:blocker"
    ctx.blocker_mode = True
    → self.found()
```

Normal picking follows if no blockers. Effort label → `(model, effort, ladder_key)` resolved from table above.

### `on_enter_preflight` (changed)

```
worktree = get_paths("ship-issue", ctx.repo, slot=ctx.slot).worktree
ctx.worktree = worktree
git.fetch(worktree)
ctx.pre_claim_sha = git.rev_parse(worktree, "HEAD")
try:
    git.reset_hard(worktree, ref="origin/wip/ship-issue")
    git.rebase(worktree, onto="origin/main")
except git.GitConflict:
    _file_blocking_issue(ctx, reason="preflight rebase failed")
    self.bounce()
    return
self.preflighted()
```

### `on_enter_escalating` (changed)

```python
ladder = LADDERS.get(ctx.ladder_key) or LADDERS.get(ctx.backend)
```

### `on_enter_rebasing_wip` (new)

```
try:
    git.fetch(worktree)
    git.reset_hard(worktree, ref="origin/wip/ship-issue")
    git.rebase(worktree, onto="origin/main")
    git.push(worktree, remote="origin",
             refspec="wip/ship-issue:wip/ship-issue", force_with_lease=True)
except (git.GitConflict, Exception):
    _file_blocking_issue(ctx, reason="wip rebase failed")
    self.rebase_failed()
    return
self.rebased()
```

### `on_enter_ci_check_wip` (new)

Same as `on_enter_ci_check` but on failure calls `_file_blocking_issue` before `self.ci_fail()`.

### `on_enter_wip_updated` (new terminal)

```
_release_wip_lock(ctx)
ctx.terminal = "wip_updated"
```

### `on_enter_bounced` (changed)

If `ctx.issue is None` (maintenance path): call `_release_wip_lock(ctx)`.
Existing issue-label cleanup runs only when `ctx.issue is not None` (unchanged).

---

## `_file_blocking_issue` helper

```python
def _file_blocking_issue(ctx: ShipIssueContext, *, reason: str) -> None:
    body = f"ship-issue slot {ctx.slot} hit a blocking failure.\n\n**Reason:** {reason}\n\n"
    if ctx.ci_failure_excerpt:
        body += f"**CI excerpt:**\n```\n{ctx.ci_failure_excerpt}\n```\n"
    gh.issue_create(
        ctx.repo,
        title=f"[bot:blocks-all] {reason}",
        body=body,
        labels=["bot:blocks-all", "bot:fix-wip", "bot:ship-issue-ready", "status:ready"],
    )
```

The filed issue carries `bot:ship-issue-ready` so normal picking eligibility rules apply; `bot:blocks-all` ensures it jumps the queue.

---

## `git.py` additions

Two new primitives needed:

- `git.reset_hard(worktree, ref)` — `git reset --hard <ref>`
- `git.is_behind(worktree, branch, ref)` — `git merge-base --is-ancestor <branch> <ref>` (exit code 0 = up-to-date, 1 = behind)

---

## Testing

- Unit tests for new `checking_wip`, `rebasing_wip`, `ci_check_wip` handlers (mock git + gh)
- Unit test: `on_enter_picking` picks `bot:blocks-all` issue before normal issues, sets correct `(model, effort, ladder_key)`
- Unit test: `on_enter_picking` returns `none_found` when only `bot:blocks-all` issue is in-progress
- Unit test: `WipRebaseLock` claim races (second INSERT returns rowcount=0 → throttled)
- Unit test: `on_enter_bounced` releases lock when `ctx.issue is None`
- Unit test: `on_enter_preflight` bounces + files issue on rebase conflict
- Integration: full `wip_updated` happy path (checking_wip → rebasing_wip → ci_check_wip → wip_updated)
