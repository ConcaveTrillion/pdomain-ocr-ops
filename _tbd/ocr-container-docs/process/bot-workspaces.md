# Bot workspaces

Per-bot isolated git worktrees under `/srv/bot-workspaces/`, owned by
`claude-bot`. CT's interactive checkouts at
`/workspaces/ocr-container/<repo>/` stay pristine; bots write to their
own subtree.

## Topology

    /srv/bot-workspaces/
      .locks/                         # flock files
      .state/                         # state flags (e.g., bots-paused)
      ship-issue-0/<repo>/            # slot 0 worktree, branch wip/ship-issue-0
      ship-issue-1/<repo>/            # slot 1 worktree, branch wip/ship-issue-1
      ship-issue-N/<repo>/            # slot N worktree, branch wip/ship-issue-N
      style-review/<repo>/            # worktree on wip/ship-issue (integration)
      style-sweep/<repo>/             # worktree on wip/style-sweep
      ...

Each slot N has its own working branch `wip/ship-issue-N`. All slots push
to the shared integration branch `wip/ship-issue` (one rolling PR). The
integration branch is the PR base; slot branches are ephemeral per-slot
accumulators rebased at push time.

    wip/ship-issue-0  ──┐
    wip/ship-issue-1  ──┼─► wip/ship-issue  (integration branch, one PR)
    wip/ship-issue-N  ──┘

A single `.git/` directory lives under CT's main checkout; the bot
worktrees share its object DB via `git worktree add`. One worktree per
(bot, repo) — added lazily by `scripts/bot-workspace-bootstrap.sh`.

## Lock model

| Lock | Held by | Duration | Purpose |
|------|---------|----------|---------|
| `ship-issue-N.<repo>.lock` | slot N orchestrator | full run | prevent two invocations of same slot |
| `push-wip.<repo>.lock` | success.sh (any slot), style-review | push window ~10s | serialize commits to integration branch |
| `style-review.<repo>.lock` | style-review orchestrator | full run | prevent duplicate style-review runs |

The old `wip-branch.<repo>.lock` (held for the full 20-min ship-issue
run) is gone. CI runs are fully lock-free; only the push window is
serialized. This means style-review no longer blocks behind a 20-min
TDD cycle.

## Slot identity

Each slot's claim comment reads `"Claimed by ship-issue-N"`. The
race-check in `ship-issue-pick.py` reads recent comments: if a competing
lower-numbered slot claimed the same issue within 60s, the higher slot
backs off (un-claims and tries the next issue). Lower slot number wins
ties.

## Branch-contention coordination

Git allows only one worktree per branch. Each slot has a unique branch
(`wip/ship-issue-N`), so there is no per-slot contention. The
integration branch `wip/ship-issue` is only ever updated via
`git push origin WIP_BRANCH:wip/ship-issue --force-with-lease` inside the
narrow `push-wip.<repo>.lock`.

style-sweep uses a different branch (`wip/style-sweep`), so no
contention with ship-issue at all.

## Permissions

`/srv/bot-workspaces/` is owned `claude-bot:claude-bot`, mode 0755.
CT's vscode user can read everything but not write — explicit
permission boundary that keeps CT's interactive sessions from
accidentally writing into bot trees.

## Setup

`scripts/bot-workspace-bootstrap.sh <bot> <repo>` is idempotent:
creates the topology if missing, adds the worktree if missing, leaves
existing worktrees alone. Safe to call from every orchestrator startup.

For N-slot ship-issue:

```bash
scripts/bot-workspace-bootstrap.sh ship-issue-0 pdomain-prep-for-pgdp
scripts/bot-workspace-bootstrap.sh ship-issue-1 pdomain-prep-for-pgdp
```

Each call creates the worktree on the matching `wip/ship-issue-N` branch
and ensures the `push-wip.<repo>.lock` file exists.

## Why a single .git/

Disk efficiency. Three worktrees × N repos × ~100MB pack data each
would balloon. `git worktree add` shares the object DB — only the
HEAD/index/working tree are duplicated, which is small.

## ctask scheduling

Each slot is a separate ctask entry:

```
ship-issue-orchestrator.sh --repo pdomain/pdomain-prep-for-pgdp --slot 0 --runs 3
ship-issue-orchestrator.sh --repo pdomain/pdomain-prep-for-pgdp --slot 1 --runs 3
```

Default slot is 0; `--slot` can be omitted for single-slot operation.

## Operational notes (live README)

Hands-on operational notes — file ownership gotchas, flock recovery, the
workspace-rc lessons — live at `/srv/bot-workspaces/README.md` (outside the
git tree because it's bot-owned). Refresh that file when running into new
edge cases; refresh this design doc only when topology changes.
