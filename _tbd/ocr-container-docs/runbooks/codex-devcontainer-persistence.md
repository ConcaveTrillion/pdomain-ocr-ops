# Codex Devcontainer Persistence

Codex state must survive dev container rebuilds. The normal path is the Docker
volume mounted at `/home/vscode/.codex`; the backup scripts are insurance for
volume loss, migration, or risky rebuild work.

## What is preserved

`devcontainer.json` mounts the named Docker volume `pd-ocr-codex-config` at
`/home/vscode/.codex`. That directory contains the state worth preserving:

- `auth.json`: login/API auth
- `config.toml`: trusted projects and plugin enablement
- `history.jsonl`: prompt history
- `sessions/`: conversation transcripts
- `plugins/`, `skills/`, `memories/`: installed Codex extensions and memory
- `state_*.sqlite`, `logs_*.sqlite`, `goals_*.sqlite`: UI, logs, and goal state
- `shell_snapshots/`, `models_cache.json`, and logs

Unlike Claude Code, Codex does not currently need a separate `~/.codex.json`
restore step; the useful state is under `~/.codex`.

## Before a risky rebuild

Close Codex terminals first. The backup script refuses to run while Codex is
active because SQLite WAL files may still be changing.

```bash
cd /workspaces/ocr-container
scripts/backup-codex-home.sh
```

The archive is written to `.codex-migration-backups/`, which is gitignored
because it contains auth-bearing state.

## After a rebuild

First check whether the volume worked:

```bash
ls -la ~/.codex/auth.json ~/.codex/config.toml ~/.codex/sessions
codex --version
```

If `~/.codex` is empty or missing expected state, restore the newest backup:

```bash
cd /workspaces/ocr-container
scripts/restore-codex-home.sh
```

Or restore a specific archive:

```bash
scripts/restore-codex-home.sh .codex-migration-backups/codex-home-YYYYMMDDTHHMMSSZ.tgz
```

Then start Codex and confirm that login, history, sessions, plugins, and trusted
project settings are present.

## If sessions look missing after restart

Codex filters the resume picker by current working directory. If you start Codex
from `/workspaces/ocr-container`, sessions created under child repos such as
`/workspaces/ocr-container/se-llm-skills` or
`/workspaces/ocr-container/oxipng-pybind` may not appear in the default picker.

Show every indexed session, including sessions from other working directories:

```bash
codex resume --all
```

Or start from the original working directory before resuming:

```bash
cd /workspaces/ocr-container/se-llm-skills
codex resume
```

Check the on-disk transcript store directly:

```bash
codex doctor
find ~/.codex/sessions -type f -name 'rollout-*.jsonl' | wc -l
```

## If the Docker volume disappears

Do not rebuild repeatedly hoping the old state returns. Check the backup
directory first:

```bash
find /workspaces/ocr-container/.codex-migration-backups -maxdepth 1 -type f -name 'codex-home-*.tgz' | sort
```

Restore the newest usable archive with `scripts/restore-codex-home.sh`.
