# Manual setup for Plan A — workspace foundation

Hand-tracked checklist for the user-only steps in
`docs/plans/2026-05-09-workspace-foundation.md`.

The agent (Claude) cannot do these. After each step, tick the box. When all five
are done, tell Claude **"manual setup complete"** and execution resumes.

> **If this is a fresh Claude session** (e.g., after dev container rebuild),
> point Claude at the plan file and tell it: "Resuming Plan A execution.
> Tasks A1, A2 (agent side), and the Dockerfile commit are done. I'm working
> through MANUAL_SETUP.md now." It can pick up from there.

---

## Status at the time this file was written

- ✓ **Task A1**: pre-flight verification done (Debian 12, gh 2.92, Python 3.13, uv 0.11)
- ✓ **Task A2 (agent side)**: Dockerfile edited + committed (`978f010`)
- ✓ **Home backup created**: `/workspaces/ocr-container/.home-backup-2026-05-09.tgz` (54 MB,
  gitignored). Contains `~/.claude/`, `~/.config/gh/`, `~/.gitconfig`. Cache dirs excluded.
- ⏳ **You are here**: rebuild + steps 1–5 below

**After everything works**, you can delete the backup:
`rm /workspaces/ocr-container/.home-backup-2026-05-09.tgz`

Codex uses the same persistence pattern now: `devcontainer.json` mounts the
`pd-ocr-codex-config` Docker volume at `~/.codex`, and
`docs/runbooks/codex-devcontainer-persistence.md` has the backup/restore flow.
Before risky rebuilds or volume changes, close Codex terminals and run:
`scripts/backup-codex-home.sh`.

---

## ⚠ ON THE NEXT REBUILD ONLY — re-run Steps 3 + 4 once

The PAT secret file at `/run/secrets/gh-token-pd` and the bot's Claude Code
auth at `/home/claude-bot/.claude/` originally lived on tmpfs / the container
layer and **did not survive container rebuilds**. As of `devcontainer.json`
adding the `pd-ocr-secrets` and `pd-ocr-claude-bot-config` named volumes,
both locations now persist across rebuilds — but **the volumes are empty
the first time the container is rebuilt with the new config**.

So the very next rebuild after these volume mounts were added:

1. Re-run **Step 3** (paste the PAT into `/run/secrets/gh-token-pd`).
2. Re-run **Step 4** (`sudo -u claude-bot -i bash` → `claude` → log in).

After that, both persist — future rebuilds keep the PAT file and the bot's
OAuth tokens in their respective Docker volumes. (`setup.sh` also restores
`~/.claude.json` for both users from the in-volume `.claude/backups/` so
the metadata block doesn't force a re-auth.)

---

## Step 1 — Rebuild the dev container (completes Task A2)

VS Code → Command Palette → **"Dev Containers: Rebuild Container"**.
Wait for rebuild to finish. The new image creates `claude-bot` and `claude-dev`.

> **Heads up: rebuild wipes `~/.claude`, `~/.config/gh`, `~/.gitconfig`** (they
> live in the container layer, not the workspace mount). A backup tarball was
> created at `/workspaces/ocr-container/.home-backup-2026-05-09.tgz` (54 MB).
> Restore it **immediately after rebuild, before Step 1's verifications**:
>
> ```bash
> # As vscode in the new container, BEFORE doing anything else:
> cd ~ && tar xzf /workspaces/ocr-container/.home-backup-2026-05-09.tgz
> # Restore correct ownership in case tar extraction left root-owned files
> sudo chown -R vscode:vscode ~/.claude ~/.config/gh ~/.gitconfig 2>/dev/null || true
> ls -la ~/.claude/.credentials.json ~/.config/gh/hosts.yml ~/.gitconfig
> # Expected: all three exist
> ```
>
> Without this restore: Claude Code is logged out, gh is logged out, git
> commits don't have your identity. With it: identical state to pre-rebuild.

**Verify after rebuild (and after the home-dir restore above):**

```bash
# Both users + group exist
getent passwd vscode claude-bot
getent group claude-dev

# Bot's env is correctly stripped
sudo -u claude-bot bash -lc 'whoami; env | grep -E "^(PATH|GH_|GITHUB_)"'
# Expected: claude-bot; PATH includes /workspaces/ocr-container; GH_CONFIG_DIR set;
#           GITHUB_TOKEN unset (no output for that one)

# Bot's git identity is distinct
sudo -u claude-bot git config --global user.name
# Expected: ship-issue-bot
```

If any check fails, the Dockerfile additions didn't apply. Inspect the rebuild log
for errors and re-run rebuild.

- [X] Rebuild completed
- [X] Verification commands above all pass

---

## Step 2 — Create the fine-grained PAT (Task A3)

Open <https://github.com/settings/personal-access-tokens/new>.

| Field | Value |
|---|---|
| Token name | `pd-gh-pd-token` |
| Resource owner | `ConcaveTrillion` |
| Expiration | 90 days |
| Repository access | **Only select repositories** → all 8 `ConcaveTrillion/pd-*` repos |
| Repo permissions | **Contents**: Read and write · **Issues**: Read and write · **Metadata**: Read-only (auto) · **Pull requests**: Read and write |

No Account permissions needed. No Workflows scope. No Administration. No Secrets.

> **Note (2026-05-09):** earlier drafts asked for **Account permissions → Projects: Read and write**. That permission doesn't exist for user-owned PATs (it's an Organization-only scope). The design has been updated to carry workflow status as `status:*` labels instead of a Project board field, so no Projects access is required.

Save the `github_pat_…` token in your password manager / keyring.

**Verify the token works** (don't echo it; just confirm it can list issues):

```bash
GH_TOKEN="<paste-token-here>" gh issue list -R pdomain/pdomain-book-tools --limit 1
```

Expected: either an issue listing or "no open issues" — both indicate the token is valid.
A 401/403 means the PAT is misconfigured.

- [ ] PAT created
- [ ] Token verified working

---

## Step 3 — Install token at `/run/secrets/gh-token-pd` (Task A4)

In a vscode-user shell, with the token in `$PAT`:

```bash
PAT='github_pat_paste_here'   # paste your token; this stays in shell history but not in workspace
sudo mkdir -p /run/secrets
printf '%s' "$PAT" | sudo install -m 0440 -o root -g claude-dev /dev/stdin /run/secrets/gh-token-pd
unset PAT   # clear from shell var
```

**Verify:**

```bash
ls -l /run/secrets/gh-token-pd
# Expected: -r--r----- 1 root claude-dev <size>

# Both users can read it
cat /run/secrets/gh-token-pd | head -c 4              # Expected: gith
sudo -u claude-bot cat /run/secrets/gh-token-pd | head -c 4   # Expected: gith
```

- [X] Token file installed at correct path/perms
- [X] Both vscode and claude-bot can read it

---

## Step 4 — Log claude-bot into Claude Code (Task A5)

The bot needs its own Claude Code auth. Same Anthropic account as your normal sessions
(no extra subscription needed).

```bash
sudo -u claude-bot -i bash
```

Inside the bot shell:

```bash
claude
```

Follow the browser auth flow. Send a tiny test prompt (e.g., "say hi") to confirm
the session works, then `/exit`. Then `exit` to leave the bot shell.

**Verify the bot's auth is persisted:**

```bash
sudo -u claude-bot ls -la /home/claude-bot/.claude/ 2>&1 | head -10
# Expected: at least an auth or credentials file
```

- [X] Bot logged in successfully
- [X] Bot's `~/.claude/` has auth state

---

## Step 5 — Apply workspace permissions (Task A6)

```bash
sudo chgrp -R claude-dev /workspaces/ocr-container
sudo chmod -R g+rwX /workspaces/ocr-container
sudo find /workspaces/ocr-container -type d -exec chmod g+s {} \;
```

**Verify:**

```bash
ls -ld /workspaces/ocr-container /workspaces/ocr-container/pdomain-book-tools 2>/dev/null
# Expected: group is claude-dev; mode shows group rwxs (the s = setgid)

# Bot can write a test file in the workspace
sudo -u claude-bot bash -lc 'touch /workspaces/ocr-container/pdomain-book-tools/.bot-write-test && echo OK'
# Expected: OK
rm -f /workspaces/ocr-container/pdomain-book-tools/.bot-write-test
```

- [X] Workspace tree has group `claude-dev` with setgid on dirs
- [X] Bot can write to workspace

---

## Done — resume execution

When all five steps are checked, return to Claude and say:

> **"manual setup complete"**

Claude will verify the post-conditions of A2, A4, A6 and resume from Task A7 onward.
Most remaining tasks (A7–A35) are scriptable and run via subagents. Two more sudo
moments remain at the end:

- **Task A36** — apply lockdown (chown enforcement paths back to vscode:vscode)
- **Task A37** — run final acceptance suite (some sub-checks need bot identity)

Both will surface as quick prompts when reached.
