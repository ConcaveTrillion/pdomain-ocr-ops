# Isolated Claude Code sessions for SE ebook projects

SE ebook projects live under `se-llm-skills/test-ebooks/` inside the workspace
tree. Running Claude from there causes two problems:

1. **Parent CLAUDE.md files load** — workspace-level agent routing and
   `se-llm-skills/CLAUDE.md` get injected as context, which is irrelevant noise
   for ebook work.
2. **Memory is shared with the workspace session** — ebook-specific memories
   land in the workspace memory bucket, not their own.

The fix is to clone each ebook to a standalone location outside the workspace
tree and always launch Claude from there.

## How Claude Code scopes things

| Thing | Scope |
|---|---|
| **Memory** | Derived from cwd at session start — different cwd = separate memory bucket |
| **CLAUDE.md loading** | Walks up the directory tree from cwd — standalone clone has no parent files |
| **Plugin / skills** | Global — installed once in `~/.claude/`, active in every session |

## One-time setup

```sh
mkdir -p ~/ebooks
```

## Per ebook — initial clone

```sh
gh repo clone standardebooks/oscar-wilde_the-picture-of-dorian-gray \
  ~/ebooks/oscar-wilde_the-picture-of-dorian-gray

gh repo clone standardebooks/h-g-wells_the-time-machine \
  ~/ebooks/h-g-wells_the-time-machine
```

Add further ebooks following the same `~/ebooks/<author>_<title>` pattern.

## Launching a session

Always `cd` into the standalone clone before running `claude`:

```sh
cd ~/ebooks/oscar-wilde_the-picture-of-dorian-gray && claude
cd ~/ebooks/hg-wells_the-time-machine && claude
```

Each ebook gets its own isolated memory bucket automatically.

## Plugin (one-time install)

The SE skills plugin is global — install once and it is active everywhere:

```sh
# Build dist (gitignored, must be regenerated)
cd /workspaces/ocr-container/se-llm-skills && make build
```

Then inside Claude Code:

```
/plugin install /workspaces/ocr-container/se-llm-skills/dist/claude
```

If you ever uninstall and need to reinstall, repeat the two steps above.

## Result

- Each ebook session has isolated memory.
- No workspace agent-routing noise in context.
- SE skills plugin available in every session.
- The ebook's own `CLAUDE.md` still loads (it's in the repo root — that's wanted).
