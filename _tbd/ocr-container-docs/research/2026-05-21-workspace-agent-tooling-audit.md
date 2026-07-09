# Workspace agent tooling audit (2026-05-21)

Status: research and recommendations only. No config changes were applied.

Scope: `/workspaces/ocr-container`, root Claude/Codex setup, workspace
automation, multi-repo workflow, and current external tooling that could improve
the loop.

## Summary

The workspace already has a strong agent operating model:

- root instructions define a multi-repo workflow, required skill usage,
  subagent routing, worktree isolation, TDD, verification, and local commits
  without unsolicited pushes;
- Claude Code has a root statusline, session hooks, pre-tool guards,
  pre-compact snapshots, session-end cost reporting, and per-repo agents;
- the devcontainer persists Claude, Codex, GitHub CLI, model, Playwright,
  torch, Hugging Face, uv, pip, and pre-commit caches in named volumes;
- the `claude-bot` user and `pd-push` wrapper give unattended work a narrower
  GitHub write path than the interactive user;
- workspace cleanup tooling already exists and is safer than ad hoc branch and
  worktree pruning.

The highest leverage improvements are not replacing this system. They are:

1. add reliable notifications for idle or permission-blocked agents;
2. fix stale root tests so workspace gates can be trusted;
3. standardize cross-tool config sync for Claude, Codex, Gemini, Cursor, and
   other tools;
4. improve issue/branch visibility for multi-repo triage;
5. keep new orchestration layers behind trials so they do not bypass the
   existing worktree and guardrail model.

## Local findings

### Workspace state

`python3 scripts/workspace_cleanup_scan.py --ai` reported:

- workspace root: dirty, 13 files changed;
- `coding-bot`: dirty, branch `feature/workspace-sync-all`, no upstream;
- `pdomain-ocr-trainer-spa`: clean, but no upstream;
- `pdomain-ui`: dirty;
- `se-eval-corpus`: dirty;
- no abandoned agent worktrees;
- multiple merged local branches in `coding-bot` and `pdomain-prep-for-pgdp` are
  cleanup candidates;
- one recent `se-llm-skills` branch was flagged as merged and deletable, but it
  was updated recently enough that it should be reviewed before pruning.

Recommendation: run the existing cleanup process before adding more workflow
tools. Start with:

```bash
python3 scripts/workspace_cleanup_scan.py --ai
python3 scripts/workspace_prune.py --branches --worktrees
```

Only add `--apply` after reviewing the dry-run output.

### Root workflow instructions

The root `CLAUDE.md` is doing useful work. It explicitly requires:

- checking dirty state before coding;
- reading repo guidance and docs;
- checking issue status and in-flight work;
- consulting agent memory;
- using an Explore subagent for non-trivial code location;
- worktree isolation for implementation agents;
- focused verification plus `make ci`;
- local commits without unsolicited pushes.

This is the right level of ceremony for a multi-repo OCR workspace with active
agents. The risk is not lack of process. The risk is that the process is partly
Claude-specific and must be kept synchronized for Codex and other agents.

Recommendation: keep `CLAUDE.md` authoritative, but generate/sync tool-specific
pointers and config rather than manually maintaining parallel guidance.

### Claude Code setup

Root `.claude/settings.json` includes:

- statusline command: `scripts/statusline-with-ratelimits.sh`;
- broad interactive command allowances;
- `PreToolUse` hooks for Bash and Read routed through
  `.claude/hooks/bash-command-guard.py`;
- `SessionStart`, `SessionEnd`, and `PreCompact` hooks.

The important observation: the permission allowlist is broad, so the real safety
boundary is the hook layer, not the JSON allowlist. That is fine if hook tests
stay healthy.

Fresh verification:

```bash
pytest -q tests/scripts/test_bash_command_guard.py \
  tests/scripts/test_statusline_with_ratelimits.py \
  tests/scripts/test_sync_workspace_blocks.py
```

Result: 60 passed.

### Stale root test

Adding `tests/scripts/test_no_trailing_todos.py` to the focused root test run
failed. The test still points at:

```python
HOOK = WORKSPACE / "scripts/no-trailing-todos.sh"
```

but root `.pre-commit-config.yaml` now uses:

```yaml
entry: coding-bot hook trailing-todos
```

Recommendation: fix this before treating root `pytest` as a reliable workflow
gate. Either update the test to call `coding-bot hook trailing-todos`, or add a
thin compatibility wrapper at `scripts/no-trailing-todos.sh` that delegates to
the canonical hook.

### Scheduling and task runners

There are two overlapping task schedulers:

- `claude-tasks.sh`: older shell scheduler;
- `ctask`: newer Python scheduler with JSON config, stream-json injection,
  cost/usage extraction, and commit tracking.

Recommendation: treat `ctask` as canonical. Archive or deprecate
`claude-tasks.sh` after confirming no scheduled tmux sessions still depend on
the shell format.

### Devcontainer

The devcontainer is a strong foundation:

- persistent Claude, Codex, GitHub CLI, bot Claude auth, and secrets volumes;
- shared caches for uv, pip, pre-commit, Playwright, Hugging Face, torch, and
  model assets;
- Node 24, Python 3.13, uv, GitHub CLI, tmux, ripgrep, CUDA support, and
  separate `claude-bot` user.

Recommendation: add any new notification/orchestration binaries through the
devcontainer or `mise`, not ad hoc install scripts, so rebuilds preserve the
workflow.

## Recommended tooling

### 1. PeonPing

Use case: audible or desktop notification when Claude Code, Codex, or another
agent needs attention.

Fit for this workspace: high. The workspace already has Claude hooks and Codex
terminal profiles. PeonPing supports multiple coding agents and has a Codex
adapter path that expects the runtime under `~/.claude/hooks/peon-ping/`, which
matches the existing Claude-hook-centered layout.

Recommended integration:

- install runtime under the persisted Claude config volume;
- wire Claude Code `Notification` hooks for `permission_prompt` and
  `idle_prompt`;
- wire Codex through its notify hook or adapter path;
- keep messages local-only at first, then decide whether phone notifications are
  needed.

Source: <https://github.com/PeonPing/peon-ping>

### 2. Claude Code Notification hooks

Use case: trigger scripts when Claude needs permission, becomes idle, finishes
elicitation, or sends other notification events.

Fit for this workspace: high. You already use several hook types, but not the
notification hook family. This is the clean place to connect PeonPing, `ntfy`,
Slack, or a local `notify-send` wrapper.

Recommended integration:

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "permission_prompt",
        "hooks": [
          {
            "type": "command",
            "command": "/workspaces/ocr-container/scripts/agent-notify.sh permission"
          }
        ]
      },
      {
        "matcher": "idle_prompt",
        "hooks": [
          {
            "type": "command",
            "command": "/workspaces/ocr-container/scripts/agent-notify.sh idle"
          }
        ]
      }
    ]
  }
}
```

Make `agent-notify.sh` route to PeonPing, `ntfy`, or desktop notifications
based on env vars. That keeps `.claude/settings.json` stable.

Source: <https://code.claude.com/docs/en/hooks>

### 3. ntfy

Use case: push notifications to phone or desktop from scripts using plain HTTP.

Fit for this workspace: high if you want notifications away from the terminal.
It is simpler than a full Slack or Telegram control plane and can be used by:

- Claude `Notification` hooks;
- `ctask` completion or failure;
- long `make ci` wrappers;
- cost dashboard threshold alerts;
- stale worktree scan reports.

Recommended integration:

- start with a private, hard-to-guess topic on public `ntfy.sh`;
- move to self-hosted only if you need access control, message history, or no
  public relay dependency;
- never include file paths containing secrets or raw prompt content in the push
  payload.

Source: <https://docs.ntfy.sh/>

### 4. Saddle

Use case: sync AI coding tool configs, skills, agents, commands, and root config
files across tools.

Fit for this workspace: high. You already maintain `CLAUDE.md`, `AGENTS.md`,
per-agent definitions, Codex config, skills, and plugin-derived skills. Drift is
the obvious long-term maintenance problem.

Recommended integration:

- trial Saddle against a copy of the workspace or a small repo first;
- make root `CLAUDE.md` and `CONVENTIONS.md` the source of truth;
- generate or sync pointers for `AGENTS.md`, Codex, Cursor, Gemini, and any
  future tools;
- do not let it overwrite `.claude/settings.local.json` or persisted auth
  volumes.

Source: <https://saddle.sh/>

### 5. Agent Desk or SkillsGate

Use case: visual management of skills and agent configs across multiple tools.

Fit for this workspace: medium. These tools are worth watching because your
workspace already has enough skills and agent definitions that discoverability
will become a problem. They are less urgent than notifications and config sync.

Recommended integration:

- evaluate read-only first;
- require explicit review before any tool rewrites installed skills or
  marketplace entries;
- compare against your existing `se-llm-skills` build/install flow before
  adopting.

Sources:

- <https://agentdesk.sh/>
- <https://skillsgate.ai/>

### 6. gh-dash

Use case: terminal dashboard for GitHub pull requests and issues using GitHub
filters.

Fit for this workspace: high. Plans sync to GitHub issues, milestones carry
spec names, and you routinely need to see the meta repo plus per-repo issue
queues. `gh-dash` can give you a live dashboard without another custom script.

Recommended dashboards:

- `ocr-container-meta`: open issues by milestone, grouped by `status:*`;
- active repo: PRs needing review, draft PRs, assigned issues;
- bot view: issues labeled `claude-ok`, stale `wip/ship-issue*` branches, and
  open tasks by milestone.

Source: <https://dlvhdr.github.io/gh-dash/>

### 7. lazygit

Use case: terminal UI for branch history, staging hunks, rebases, cherry-picks,
and quick inspection.

Fit for this workspace: medium-high. It will help with dirty multi-repo review
and coherent commits, but it must remain subordinate to your push policy.

Recommended integration:

- add lazygit to the devcontainer or `mise`;
- use it for local inspection and staging;
- keep `pd-push` as the only bot push path;
- add a note to root guidance that lazygit is interactive-human tooling, not a
  bot push bypass.

Source: <https://lazygit.dev/>

### 8. Ductor, Agent Deck, or Claude Squad

Use case: manage multiple CLI agents, sometimes with Telegram/Slack channels,
Docker isolation, persistent memory, cron jobs, or conductor-style session
control.

Fit for this workspace: trial only. Your workspace already has:

- tmux-based scheduling;
- per-repo agent definitions;
- worktree isolation policy;
- `claude-bot`;
- cost tracking;
- cleanup scans.

Adding a second orchestration layer could either reduce terminal juggling or
weaken the careful local guardrails.

Recommendation:

- trial one tool at a time in a disposable repo;
- evaluate whether it respects per-repo worktree isolation;
- verify it does not bypass `.claude/hooks/bash-command-guard.py` or `pd-push`;
- prefer the one that can call your existing `ctask`, `workspace_cleanup_scan`,
  and `pd-push` wrappers rather than replacing them.

Sources:

- <https://github.com/PleasePrompto/ductor>
- <https://github.com/asheshgoplani/agent-deck>
- <https://github.com/smtg-ai/claude-squad>

### 9. Codex workflow hardening

Use case: make Codex work more like your Claude setup.

Fit for this workspace: high. The VS Code profile now launches Codex through
`.devcontainer/bin/codex-vscode`, and the devcontainer persists `.codex`. The
missing piece is ensuring Codex receives the same repo guidance and can use
repeatable workspace commands instead of discovering process by reading large
docs.

Recommended changes:

- keep root `AGENTS.md` as a thin pointer to `CLAUDE.md` and `CONVENTIONS.md`;
- create small, composable workspace CLIs for repeated tasks:
  `workspace-status`, `workspace-cleanup-scan`, `workspace-prune-preview`,
  `agent-notify`, `agent-cost-report`;
- save repeated Codex workflows as skills where appropriate;
- do not duplicate the full Claude agent model unless Codex needs it.

OpenAI's current Codex use-case guidance explicitly calls out creating CLIs
that Codex can use and saving repeatable workflows as skills.

Source: <https://developers.openai.com/codex/explore>

### 10. direnv

Use case: per-directory environment loading and unloading.

Fit for this workspace: medium. You already use devcontainer env and `mise`;
`direnv` would help most in sibling repos that need local env toggles, path
adjustments, or repo-specific feature flags.

Recommendation:

- only add if repo-specific env drift is causing pain;
- use checked-in `.envrc.example` plus ignored `.envrc`;
- do not store tokens in `.envrc`;
- keep the devcontainer as the primary toolchain authority.

Source: <https://direnv.com/>

## Adoption plan

### Phase 0 - fix current reliability gaps

1. Fix `tests/scripts/test_no_trailing_todos.py` or restore a compatibility
   wrapper.
2. Run `python3 scripts/workspace_cleanup_scan.py --ai`.
3. Prune confirmed stale branches/worktrees using the existing dry-run-first
   process.
4. Decide whether to archive `claude-tasks.sh` in favor of `ctask`.

### Phase 1 - notification loop

1. Add `scripts/agent-notify.sh`.
2. Wire Claude `Notification` hooks for `permission_prompt` and `idle_prompt`.
3. Install PeonPing in the persisted Claude config volume.
4. Optionally add `ntfy` support behind an env var.
5. Add tests for the notification wrapper that verify it degrades safely when
   PeonPing or `ntfy` are not configured.

### Phase 2 - visibility

1. Install `gh-dash`.
2. Create dashboards for meta issues, active repo PRs, and bot-approved tasks.
3. Install `lazygit` for human local review.
4. Document that lazygit is not a bot push path.

### Phase 3 - cross-tool config sync

1. Trial Saddle read-only.
2. Confirm which files it would manage.
3. Exclude auth, local settings, volatile memory, logs, and generated plugin
   artifacts.
4. If it behaves well, use it to keep Claude/Codex/Gemini/Cursor guidance in
   sync.

### Phase 4 - orchestration trial

1. Trial Ductor, Agent Deck, or Claude Squad in a disposable repo.
2. Score it against:
   - worktree isolation;
   - compatibility with `pd-push`;
   - hook/guard preservation;
   - cost visibility;
   - cleanup story after interrupted sessions.
3. Adopt only if it removes real operational friction that `ctask` cannot
   address.

## Recommendation ranking

| Rank | Tool / change | Priority | Reason |
|---:|---|---|---|
| 1 | Fix stale root TODO test | Immediate | Root verification is currently partially stale. |
| 2 | PeonPing + Claude Notification hooks | Immediate | Solves idle/permission babysitting with minimal disruption. |
| 3 | `ntfy` behind `agent-notify.sh` | High | Gives phone/desktop alerts for agents and long tasks. |
| 4 | `gh-dash` | High | Matches the milestone and issue-heavy workflow. |
| 5 | `ctask` canonicalization | High | Removes duplicate scheduler paths. |
| 6 | Saddle | Medium-high | Reduces cross-tool config drift. |
| 7 | lazygit | Medium | Helps human review/staging but should not affect bot policy. |
| 8 | Agent Desk / SkillsGate | Medium | Useful later for skill discoverability. |
| 9 | Ductor / Agent Deck / Claude Squad | Trial only | Potentially helpful but overlaps existing orchestration. |
| 10 | direnv | Conditional | Useful only if per-repo env drift becomes painful. |

## Sources

Local files inspected:

- `CLAUDE.md`
- `.claude/settings.json`
- `.claude/settings.local.json`
- `.devcontainer/devcontainer.json`
- `.devcontainer/Dockerfile`
- `.vscode/settings.json`
- `.pre-commit-config.yaml`
- `.claude/agents/*.md`
- `.claude/hooks/*.py`
- `scripts/statusline-with-ratelimits.sh`
- `scripts/workspace_cleanup_scan.py`
- `scripts/workspace_prune.py`
- `ctask`
- `claude-tasks.sh`
- `pd-push`

External references:

- PeonPing: <https://github.com/PeonPing/peon-ping>
- Claude Code hooks: <https://code.claude.com/docs/en/hooks>
- Claude Agent SDK hooks: <https://platform.claude.com/docs/en/agent-sdk/hooks>
- Claude Code power user tips: <https://support.claude.com/en/articles/14554000-claude-code-power-user-tips>
- Saddle: <https://saddle.sh/>
- Agent Desk: <https://agentdesk.sh/>
- SkillsGate: <https://skillsgate.ai/>
- gh-dash: <https://dlvhdr.github.io/gh-dash/>
- lazygit: <https://lazygit.dev/>
- ntfy: <https://docs.ntfy.sh/>
- Ductor: <https://github.com/PleasePrompto/ductor>
- Agent Deck: <https://github.com/asheshgoplani/agent-deck>
- Claude Squad: <https://github.com/smtg-ai/claude-squad>
- Codex use cases: <https://developers.openai.com/codex/explore>
- direnv: <https://direnv.com/>
