# ship-issue interactive runner

A thin script — `scripts/ship-issue-run.sh` — that lets CT invoke a single
ship-issue cycle interactively with the same quality guarantees as the bot:
isolated worktree, correct `--model`/`--effort` from issue labels, wip-branch
integration, and the full claim → work → success/failure lifecycle.

## Problem

The existing orchestrator (`scripts/ship-issue-orchestrator.sh`) runs via
ctask and is designed for unattended multi-run loops. When CT wants to ship
one issue immediately:

- Using `Agent()` directly loses worktree isolation and effort control.
- Manually invoking the orchestrator requires fabricating `--runs 1` and
  waiting for its full throttle + pick cycle, which picks an issue rather
  than shipping a named one.

## Goal

```bash
scripts/ship-issue-run.sh --issue 253 --repo pdomain/pdomain-ocr-labeler-spa
```

Ships issue #253 end-to-end, interactively, with the same path the bot uses:
worktree → `claude -p "/ship-issue"` → success.sh or failure.sh.

## Design

### Reuse, don't rewrite

The script is a thin wrapper. It reuses:

| Existing piece | Role |
|---|---|
| `scripts/bot-workspace-bootstrap.sh` | Create/verify worktree |
| `scripts/ship-issue-preflight.sh` | Validate issue is claimable |
| `scripts/ship-issue-success.sh` | `make ci`, push, PR, label flip |
| `scripts/ship-issue-failure.sh` | Bounce labels, post comment |
| `scripts/ship-issue-escalate.sh` | Model escalation on retry |

It does NOT reuse the orchestrator's pick loop or throttle check — CT already
chose the issue.

### Slot

Interactive runs use slot `--interactive` (or a dedicated high-numbered slot,
e.g. `--slot 99`) so they never collide with ctask bot slots. The worktree is
`/srv/bot-workspaces/ship-issue-interactive/<repo>/` on branch
`wip/ship-issue-interactive`. Push uses the same narrow `push-wip.<repo>.lock`
and pushes to the shared integration branch `wip/ship-issue`.

### Model and effort resolution

```bash
# 1. Fetch labels from GitHub
LABELS=$(gh issue view "$ISSUE" --repo "$REPO" --json labels --jq '[.labels[].name | strings]')

# 2. Extract model label  → claude flag
MODEL=$(echo "$LABELS" | jq -r '.[] | select(startswith("model:")) | ltrimstr("model:")')
MODEL=${MODEL:-sonnet}   # default

# 3. Extract model-effort label → claude flag
EFFORT=$(echo "$LABELS" | jq -r '.[] | select(startswith("model-effort:")) | ltrimstr("model-effort:")')
EFFORT=${EFFORT:-medium}  # default
```

Then pass directly to `claude`:
```bash
claude --model "$MODEL" --effort "$EFFORT" -p "/ship-issue ..."
```

### Claim

Same as the bot: set `status:in-progress`, post a claim comment
`"Claimed by ship-issue-interactive"`. Reuse the pick script's claim logic or
inline the two `gh` calls.

### Retry / escalation

On failure, offer escalation (same ladder as the orchestrator):
`haiku → sonnet → opus → bounce`.  Interactive mode can ask CT:

```
▸ Slice failed. Escalate to sonnet and retry? [y/N]
```

(Or accept `--no-escalate` to skip straight to failure.sh.)

### Paused state

Respect `/srv/bot-workspaces/.state/bots-paused` and
`bots-paused.<repo>`. Print a warning and exit if set — CT should know
the bots are paused before shipping interactive work to the same branch.

## CLI interface

```
scripts/ship-issue-run.sh --issue N --repo owner/repo [--slot N] [--no-escalate]

  --issue N          GitHub issue number (required)
  --repo owner/repo  Full repo slug (required)
  --slot N           Worktree slot (default: interactive)
  --no-escalate      Bounce immediately on failure without retrying at higher model
```

## Success/failure output

Mirror the orchestrator's terminal output style:

```
▸ ship-issue-run: issue #253 (model=haiku, effort=low)
▸ Bootstrapping worktree at /srv/bot-workspaces/ship-issue-interactive/pdomain-ocr-labeler-spa/
▸ Claiming #253 ...
▸ Running claude -p "/ship-issue" ...
▸ Slice exited 0. Running make ci ...
▸ make ci passed. Pushing to wip/ship-issue ...
✔ Issue #253 shipped. PR: https://github.com/...
```

## What this is NOT

- Not a replacement for the ctask orchestrator — that handles scheduling,
  throttling, multi-run loops, and parallel slots.
- Not a new skill invocation path — CT still uses the `ship-issue` skill
  inside the `claude -p` call; this script is the outer harness only.

## Implementation notes

- Run as `vscode` user (CT), not `claude-bot`. The worktree is already
  bot-owned; the `claude` binary runs as vscode (same as ctask does via
  `sudo -u claude-bot ... claude -p` — adjust ownership if needed).
- Stdin should be a tty so `claude -p` progress output renders correctly.
- The script exits with the same code as `claude -p` (0 = shipped,
  non-zero = bounced/failed).
