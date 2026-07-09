---
status: complete
---

# Plan A — Workspace Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the workspace-level scaffolding for the GitHub-Issues + ship-issue system: two-user dev container, scoped PAT, hooks, all `scripts/` glue, `pd-push`, settings.json policy, telemetry pipeline, ship-issue + fixing-specs skills. After this plan ships, the workspace is ready to migrate any individual repo (Plan B / C).

**Architecture:** Single shared dev container with two Linux users — `vscode` (interactive, full gh auth) and `claude-bot` (unattended, scoped `GH_TOKEN_PD` only). Procedural ship-issue logic is in workspace scripts (`scripts/`); the agent skill is a thin orchestrator. Enforcement files (`scripts/`, `.claude/hooks/`, etc.) are owned `vscode:vscode` and immutable to the bot. PAT scope + branch protection on `main` + `bash-command-guard.py` hook + `pd-push` wrapper form the security boundary.

**Tech Stack:**
- Python 3.11+ (most scripts), bash (simple shell glue)
- GitHub CLI (`gh`) with fine-grained PAT
- Pre-commit framework
- Claude Code SessionEnd / PreToolUse hooks

**Scope of this plan:**
- Workspace infra ONLY. No repo migration. No issue creation. No first ship-issue run.
- After this plan: Plan B (pilot pdomain-prep-for-pgdp) becomes executable.

**Reference spec:** `docs/superpowers/specs/2026-05-09-github-issues-projects-design.md`

---

## File Structure

This plan creates the following workspace-level files:

```
/workspaces/ocr-container/
  pd-push                                            (bash; only push wrapper)
  .devcontainer/Dockerfile                           (modified: add bot user, group, sudoers)
  .claude/
    hooks/
      bash-command-guard.py                          (Python; PreToolUse)
      ship-issue-report.py                           (Python; SessionEnd)
      claude-pricing.json                            (config)
    skills/
      ship-issue/SKILL.md                            (orchestrator)
      fixing-specs/SKILL.md                          (5 procedures)
    settings.json                                    (modified: permissions allow/deny + hook registration)
    agent-memory/ship-issue/.gitignore               (covers JSONL + HTML)
  scripts/
    ship-issue-throttle-check.sh
    ship-issue-pick.py
    ship-issue-success.sh
    ship-issue-failure.sh
    ship-issue-orchestrator.sh
    seed-labels.sh                                  (seeds all label families incl. status:*)
    lint-spec.py
    build-spec-index.py
    file-legacy-migration-issues.py
    migrate-legacy-spec-auto.py
    build-cost-dashboard.py
    statusline-with-ratelimits.sh
    tooling-change-guard.sh
    verify-protections.sh
  tests/scripts/                                     (pytest tests for all Python scripts)
```

Tests live in `tests/scripts/` (workspace-level, separate from per-repo test trees).

---

## Phase 1 — Pre-flight verification

### Task A1: Confirm environment

**Files:**
- Read: `/etc/os-release`, `/workspaces/ocr-container/.devcontainer/Dockerfile`

- [ ] **Step 1: Verify in dev container**

Run: `cat /etc/os-release | grep -E '^(NAME|VERSION_ID)='`
Expected: shows the dev container OS (Debian/Ubuntu/etc.)

- [ ] **Step 2: Verify gh CLI installed**

Run: `gh --version`
Expected: `gh version 2.x.x ...`

- [ ] **Step 3: Verify Python 3.11+ available**

Run: `python3 --version`
Expected: `Python 3.11.x` or higher.

- [ ] **Step 4: Verify uv available (used in many tests)**

Run: `uv --version`
Expected: `uv 0.x.x ...`. If missing: `curl -LsSf https://astral.sh/uv/install.sh | sh`.

- [ ] **Step 5: Verify pytest installed at workspace level**

Run: `uv pip install pytest --system 2>&1 | tail -3`
Expected: pytest installs or already-installed message.

- [ ] **Step 6: Note current users on the system**

Run: `getent passwd | grep -E '(vscode|claude)' || echo "no claude-bot yet"`
Expected: `vscode` exists; `claude-bot` does not yet exist (we'll add it).

This task is verification only. No commit.

---

## Phase 2 — Two-user dev container

### Task A2: Add `claude-bot` user and `claude-dev` group to Dockerfile

**Files:**
- Modify: `/workspaces/ocr-container/.devcontainer/Dockerfile`

- [ ] **Step 1: Read existing Dockerfile**

Run: `cat .devcontainer/Dockerfile`
Note the user-creation section (likely creates `vscode` already).

- [ ] **Step 2: Add user/group provisioning at the end of the Dockerfile**

Append:

```dockerfile
# === ship-issue: claude-bot user and claude-dev group ===
# Used for unattended `claude -p` runs. Has no gh auth and a distinct git identity.
RUN groupadd -r claude-dev && \
    usermod -aG claude-dev vscode && \
    useradd -m -s /bin/bash -G claude-dev claude-bot && \
    echo 'umask 002' >> /home/vscode/.bashrc && \
    echo 'umask 002' >> /home/claude-bot/.bashrc

# Bot's stripped env (no token in env at login; secrets file is sourced as needed)
RUN echo 'export PATH="/workspaces/ocr-container:$PATH"' \
      >> /home/claude-bot/.bashrc && \
    echo 'export GH_CONFIG_DIR="$HOME/.config/gh-empty"' \
      >> /home/claude-bot/.bashrc && \
    echo 'unset GITHUB_TOKEN' \
      >> /home/claude-bot/.bashrc && \
    mkdir -p /home/claude-bot/.config/gh-empty && \
    chown -R claude-bot:claude-bot /home/claude-bot/.config

# Bot's git identity (distinct from vscode for audit clarity)
RUN su - claude-bot -c 'git config --global user.name  "ship-issue-bot"' && \
    su - claude-bot -c 'git config --global user.email "ship-issue-bot@concavetrillion.local"' && \
    su - claude-bot -c 'git config --global init.defaultBranch main' && \
    su - claude-bot -c 'git config --global pull.rebase true'

# Allow vscode to sudo to claude-bot WITHOUT password (for ctask schedules)
RUN echo 'vscode ALL=(claude-bot) NOPASSWD: ALL' > /etc/sudoers.d/claude-bot && \
    chmod 440 /etc/sudoers.d/claude-bot

# vscode also gets PATH addition for pd-push
RUN echo 'export PATH="/workspaces/ocr-container:$PATH"' \
      >> /home/vscode/.bashrc
```

- [ ] **Step 3: Rebuild dev container**

Action: In VS Code, run command "Dev Containers: Rebuild Container" — or equivalent for your environment.

(Cannot automate from inside the container; the user runs this.)

- [ ] **Step 4: After rebuild, verify both users exist**

Run: `getent passwd vscode claude-bot && getent group claude-dev`
Expected: both users listed; `claude-dev` group has both as members.

- [ ] **Step 5: Verify sudo path works (no password)**

Run: `sudo -u claude-bot bash -lc 'whoami && env | grep -E "PATH|GH_"'`
Expected: outputs `claude-bot`; PATH includes `/workspaces/ocr-container`; `GH_CONFIG_DIR` set.

- [ ] **Step 6: Commit Dockerfile change**

```bash
git add .devcontainer/Dockerfile
git commit -m "feat(devcontainer): add claude-bot user + claude-dev group for unattended runs

Two-user model: vscode (interactive, full gh auth) + claude-bot (unattended,
scoped GH_TOKEN_PD only, distinct git identity, no SSH keys). Passwordless
sudo from vscode to claude-bot for ctask schedule entries."
```

---

## Phase 3 — PAT creation + secrets file

### Task A3: User creates fine-grained PAT

**Files:** none (manual external step)

- [ ] **Step 1: Tell the user what to do**

The agent cannot create the PAT itself. Print this to the user and pause:

```
Please create a fine-grained PAT at:
  https://github.com/settings/personal-access-tokens/new

Token name:        pd-gh-pd-token
Resource owner:    ConcaveTrillion
Expiration:        90 days
Repository access: Only select repositories → all 8 ConcaveTrillion/pd-* repos
Repository permissions:
  Contents:           Read and write
  Issues:             Read and write
  Metadata:           Read-only (auto-included)
  Pull requests:      Read and write

(No Account permissions. No Workflows. No Administration.)

After creating, save the token (starts with `github_pat_…`).
Paste it here when ready.
```

Pause for user to provide the token.

- [ ] **Step 2: Verify the token works**

With the token in `$PAT` for this step (do NOT echo it):

Run: `GH_TOKEN="$PAT" gh issue list -R pdomain/pdomain-book-tools --limit 1 2>&1 | head -3`
Expected: either an issue listing or "no open issues" — both indicate the token is valid for this repo.

If the call returns 401/403, the PAT is misconfigured. Walk the user through fixing it.

This task has no commit. The token does not go into git.

### Task A4: Install token at `/run/secrets/gh-token-pd`

**Files:**
- Create: `/run/secrets/gh-token-pd` (mode 0440, owner root, group claude-dev)

- [ ] **Step 1: Create the secrets directory if missing**

Run: `sudo mkdir -p /run/secrets`

- [ ] **Step 2: Install the token file**

With the token in `$PAT`:

Run: `printf '%s' "$PAT" | sudo install -m 0440 -o root -g claude-dev /dev/stdin /run/secrets/gh-token-pd`

- [ ] **Step 3: Verify perms**

Run: `ls -l /run/secrets/gh-token-pd`
Expected: `-r--r----- 1 root claude-dev <size> ... gh-token-pd`

- [ ] **Step 4: Verify both users can read it**

Run: `cat /run/secrets/gh-token-pd | head -c 4` (as vscode)
Expected: `gith` (first 4 chars of `github_pat_...`)

Run: `sudo -u claude-bot cat /run/secrets/gh-token-pd | head -c 4`
Expected: same.

- [ ] **Step 5: Verify `vscode` doesn't accidentally use this token automatically**

Run: `gh auth status`
Expected: still shows the user's primary `gho_***` token from `~/.config/gh/`. The PAT is separate; `gh` doesn't pick it up unless `GH_TOKEN` env var is set.

This task has no commit. `/run/secrets/` is outside the workspace.

### Task A5: Bot's first-time Claude Code login

**Files:** none (per-user state in `~claude-bot/.claude/`)

- [ ] **Step 1: Open a shell as claude-bot**

Run: `sudo -u claude-bot -i bash`
You're now claude-bot.

- [ ] **Step 2: Run claude interactively, complete browser auth flow**

Run: `claude`
Follow the prompts. You'll be asked to open a URL in a browser, sign in to your Anthropic account, and paste a verification code back. Same Anthropic account as your vscode-user Claude.

- [ ] **Step 3: Verify session works**

Inside the Claude session, send a small test prompt: `Just say "hello".` Confirm response.
Then `/exit`.

- [ ] **Step 4: Confirm bot's `~/.claude/` state is persisted**

Run: `ls -la /home/claude-bot/.claude/`
Expected: at least an `auth` or `credentials` file exists.

- [ ] **Step 5: Exit bot shell**

Run: `exit`
You're back as vscode.

This task has no commit. Per-user state isn't in workspace.

---

## Phase 4 — Workspace permissions setup

### Task A6: Bulk chgrp + setgid

**Files:** entire `/workspaces/ocr-container/` tree.

- [ ] **Step 1: Verify current ownership**

Run: `ls -ld /workspaces/ocr-container/`
Note the current group.

- [ ] **Step 2: Apply group + permissions**

Run:
```bash
sudo chgrp -R claude-dev /workspaces/ocr-container
sudo chmod -R g+rwX /workspaces/ocr-container
sudo find /workspaces/ocr-container -type d -exec chmod g+s {} \;
```

- [ ] **Step 3: Verify a sample directory**

Run: `ls -ld /workspaces/ocr-container /workspaces/ocr-container/pdomain-book-tools 2>/dev/null`
Expected: group is `claude-dev`; mode shows group `rwxs` (the `s` is setgid).

- [ ] **Step 4: Verify bot can write a file in the workspace**

Run: `sudo -u claude-bot bash -lc 'touch /workspaces/ocr-container/pdomain-book-tools/.bot-write-test && echo OK'`
Expected: `OK`. New file's group is `claude-dev` (setgid inheritance).

Then clean up:
```bash
rm /workspaces/ocr-container/pdomain-book-tools/.bot-write-test
```

This task has no commit (filesystem state, not in git).

### Task A7: Lockdown — chown enforcement paths back to vscode:vscode

**Files:** `.claude/hooks`, `.claude/settings.json`, `.claude/skills`, `.claude/agents`, `pd-push` (after later tasks create it), `scripts/`, `.devcontainer/`.

This task is run AFTER all enforcement files are created (deferred to Task A60). For now, just verify no enforcement paths exist yet that would be miscategorized.

- [ ] **Step 1: Note the deferred lockdown step**

Print: `Lockdown deferred to Task A60 after all enforcement files are written.`

(No-op for this position. The lockdown step is at the end of the plan after everything is in place.)

---

## Phase 5 — `pd-push` wrapper

### Task A8: Write pd-push test

**Files:**
- Create: `tests/scripts/test_pd_push.py`

- [ ] **Step 1: Create test fixture**

```python
# tests/scripts/test_pd_push.py
"""Tests for pd-push wrapper.

pd-push must:
- allow `pd-push wip/ship-issue` (and `pd-push wip/ship-issue --force-with-lease`)
- reject pushes to any other branch
- reject `--force` (only `--force-with-lease` allowed)
- exit nonzero on rejection
"""
import os
import subprocess
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
PD_PUSH = WORKSPACE / "pd-push"


def run(args, env=None, cwd=None):
    """Run pd-push and return (rc, stdout, stderr)."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    result = subprocess.run(
        [str(PD_PUSH), *args],
        capture_output=True, text=True, env=full_env, cwd=cwd,
    )
    return result.returncode, result.stdout, result.stderr


def test_pd_push_exists_and_executable():
    assert PD_PUSH.exists(), f"{PD_PUSH} must exist"
    assert os.access(PD_PUSH, os.X_OK), f"{PD_PUSH} must be executable"


def test_rejects_main():
    rc, _, err = run(["main"])
    assert rc != 0
    assert "wip/ship-issue" in err.lower() or "refused" in err.lower()


def test_rejects_master():
    rc, _, err = run(["master"])
    assert rc != 0


def test_rejects_arbitrary_branch():
    rc, _, err = run(["feature-x"])
    assert rc != 0


def test_rejects_force_flag():
    rc, _, err = run(["wip/ship-issue", "--force"])
    assert rc != 0
    assert "--force-with-lease" in err.lower() or "refused" in err.lower()


def test_accepts_force_with_lease():
    """Wrapper validates args; we don't actually push (network)."""
    rc, _, err = run(["wip/ship-issue", "--force-with-lease", "--dry-run"])
    # --dry-run is a real git push flag; the wrapper should accept the args
    # and let git handle the no-op. RC depends on whether wip/ship-issue exists.
    # Either RC=0 (push succeeded as no-op) or git error (branch missing) — but NOT
    # the wrapper's argument-rejection error.
    assert "wrapper:refused" not in err.lower(), f"wrapper rejected valid args: {err!r}"
```

- [ ] **Step 2: Run test (must fail because pd-push doesn't exist yet)**

Run: `cd /workspaces/ocr-container && uv run pytest tests/scripts/test_pd_push.py -v 2>&1 | tail -20`
Expected: tests fail with "pd-push must exist" or similar.

- [ ] **Step 3: Commit the test**

```bash
git add tests/scripts/test_pd_push.py
git commit -m "test: add pd-push wrapper tests (red)"
```

### Task A9: Implement pd-push

**Files:**
- Create: `/workspaces/ocr-container/pd-push`

- [ ] **Step 1: Write pd-push**

```bash
#!/usr/bin/env bash
# pd-push — constrained git-push wrapper for ship-issue.
# Allows ONLY: pushing to wip/ship-issue, optionally with --force-with-lease.
# Refuses: pushes to main/master/any-other-branch; bare --force.
#
# Authenticates via GH_TOKEN_PD (read from /run/secrets/gh-token-pd if not in env).

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "pd-push wrapper:refused — usage: pd-push <branch> [--force-with-lease] [git-push-flags...]" >&2
  exit 64
fi

BRANCH="$1"
shift

if [[ "$BRANCH" != "wip/ship-issue" ]]; then
  echo "pd-push wrapper:refused — only wip/ship-issue is permitted; got: $BRANCH" >&2
  exit 65
fi

# Inspect remaining flags for --force (without -with-lease)
for arg in "$@"; do
  if [[ "$arg" == "--force" || "$arg" == "-f" ]]; then
    echo "pd-push wrapper:refused — bare --force is not allowed; use --force-with-lease" >&2
    exit 66
  fi
done

# Set GH_TOKEN_PD if not already in env
if [[ -z "${GH_TOKEN_PD:-}" ]] && [[ -r /run/secrets/gh-token-pd ]]; then
  GH_TOKEN_PD="$(cat /run/secrets/gh-token-pd)"
  export GH_TOKEN_PD
fi

# Configure git credential helper to use GH_TOKEN_PD for HTTPS pushes
# (This works because GitHub HTTPS push accepts a PAT as password with any username.)
GIT_ASKPASS_TMP="$(mktemp)"
trap 'rm -f "$GIT_ASKPASS_TMP"' EXIT
cat > "$GIT_ASKPASS_TMP" <<EOF
#!/bin/sh
case "\$1" in
  Username*) echo "x-access-token" ;;
  Password*) echo "$GH_TOKEN_PD" ;;
esac
EOF
chmod +x "$GIT_ASKPASS_TMP"

GIT_ASKPASS="$GIT_ASKPASS_TMP" exec git push origin "$BRANCH" "$@"
```

- [ ] **Step 2: Make executable**

Run: `chmod +x /workspaces/ocr-container/pd-push`

- [ ] **Step 3: Run tests, verify all pass**

Run: `cd /workspaces/ocr-container && uv run pytest tests/scripts/test_pd_push.py -v 2>&1 | tail -20`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add pd-push
git commit -m "feat(pd-push): add constrained git-push wrapper

Allows pushing only to wip/ship-issue. Rejects bare --force (only
--force-with-lease permitted). Authenticates via GH_TOKEN_PD from
/run/secrets/gh-token-pd via temporary GIT_ASKPASS helper."
```

---

## Phase 6 — `bash-command-guard.py` hook

### Task A10: Define the rule schema and write tests

**Files:**
- Create: `tests/scripts/test_bash_command_guard.py`

- [ ] **Step 1: Write tests for each rule category**

```python
# tests/scripts/test_bash_command_guard.py
"""Tests for bash-command-guard.py PreToolUse hook.

Each test sends a JSON payload to the hook on stdin and checks the
permissionDecision in the JSON output.
"""
import json
import subprocess
from pathlib import Path

HOOK = Path("/workspaces/ocr-container/.claude/hooks/bash-command-guard.py")


def call_hook(command: str) -> dict:
    """Send a tool_input.command to the hook; return parsed output."""
    payload = json.dumps({"tool_input": {"command": command}})
    result = subprocess.run(
        ["python3", str(HOOK)],
        input=payload, capture_output=True, text=True,
    )
    if result.returncode != 0:
        # Hook may exit nonzero for fatal errors; treat as deny-loudly
        return {"raw": result.stdout, "stderr": result.stderr, "rc": result.returncode}
    if not result.stdout.strip():
        # Empty output = allow
        return {"decision": "allow"}
    parsed = json.loads(result.stdout)
    return parsed


def assert_denied(command: str, reason_substr: str = ""):
    out = call_hook(command)
    decision = out.get("hookSpecificOutput", {}).get("permissionDecision")
    assert decision == "deny", f"expected deny for {command!r}, got {out!r}"
    reason = out.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
    if reason_substr:
        assert reason_substr.lower() in reason.lower(), \
            f"expected reason to contain {reason_substr!r}, got {reason!r}"


def assert_allowed(command: str):
    out = call_hook(command)
    decision = out.get("hookSpecificOutput", {}).get("permissionDecision")
    # Either no decision (allow) or explicit "allow"
    assert decision != "deny", f"expected allow for {command!r}, got denied: {out!r}"


# === Bare gh / git push denials ===

def test_deny_bare_git_push():
    assert_denied("git push origin main", "pd-push")

def test_deny_bare_git_push_force():
    assert_denied("git push -f origin main", "pd-push")

def test_allow_pd_push():
    assert_allowed("pd-push wip/ship-issue --force-with-lease")

# === gh subcommand denials ===

def test_deny_gh_repo_delete():
    assert_denied("gh repo delete pdomain/pdomain-book-tools", "denied")

def test_deny_gh_workflow_run():
    assert_denied("gh workflow run deploy.yml", "denied")

def test_deny_gh_secret_set():
    assert_denied("gh secret set MY_SECRET", "denied")

def test_deny_gh_pr_create_without_draft():
    assert_denied("gh pr create --title 'foo' --body 'bar'", "draft")

def test_allow_gh_pr_create_with_draft():
    assert_allowed("gh pr create --draft --title 'foo' --body 'bar'")

def test_deny_gh_pr_ready():
    assert_denied("gh pr ready 42", "ready")

def test_allow_gh_issue_list():
    assert_allowed("gh issue list -R pdomain/pdomain-book-tools")

def test_allow_gh_issue_view():
    assert_allowed("gh issue view 42 -R pdomain/pdomain-book-tools")

# claude-ok mutation gate. Mocked via env: CLAUDE_OK_LABEL_CHECK=skip skips the lookup.
# The real check uses gh issue view to fetch labels; we don't test the network path here.

# === Novel package additions ===

def test_deny_uv_add():
    assert_denied("uv add networkx", "uv sync")

def test_allow_uv_sync():
    assert_allowed("uv sync")

def test_deny_pip_install_novel():
    assert_denied("pip install some-package", "uv sync")

def test_allow_pip_install_requirements():
    assert_allowed("pip install -r requirements.txt")

def test_allow_pip_install_editable():
    assert_allowed("pip install -e .")

def test_deny_pnpm_add():
    assert_denied("pnpm add lodash", "approval")

def test_allow_pnpm_install():
    assert_allowed("pnpm install")

def test_deny_cargo_add():
    assert_denied("cargo add tokio", "Cargo.toml")

def test_allow_cargo_build():
    assert_allowed("cargo build --release")

# === Token / credential exfil ===

def test_deny_echo_gh_token():
    assert_denied("echo $GH_TOKEN", "exfiltration")

def test_deny_cat_gh_config():
    assert_denied("cat ~/.config/gh/hosts.yml", "Credential")

def test_deny_redirect_to_gh_config():
    assert_denied("echo foo > ~/.config/gh/hosts.yml", "Credential")

# === Direct API calls ===

def test_deny_curl_github_api():
    assert_denied("curl https://api.github.com/repos/foo/bar", "GitHub")

def test_deny_wget_github_api():
    assert_denied("wget https://api.github.com/repos/foo/bar", "GitHub")

# === Idiomatic shell that should NOT be denied ===

def test_allow_for_loop():
    assert_allowed("for f in *.py; do python -m py_compile \"$f\"; done")

def test_allow_pipe_chain():
    assert_allowed("git log --oneline | head -10")

def test_allow_compound_with_grep():
    assert_allowed("ls | grep test")

def test_allow_make_ci():
    assert_allowed("make ci")

def test_allow_pytest_with_args():
    assert_allowed("pytest -x --picked")
```

- [ ] **Step 2: Run tests (must fail because hook doesn't exist yet)**

Run: `uv run pytest tests/scripts/test_bash_command_guard.py -v 2>&1 | tail -30`
Expected: all tests fail (hook missing).

- [ ] **Step 3: Commit tests**

```bash
git add tests/scripts/test_bash_command_guard.py
git commit -m "test: add bash-command-guard hook tests (red)"
```

### Task A11: Implement bash-command-guard.py

**Files:**
- Create: `.claude/hooks/bash-command-guard.py`

- [ ] **Step 1: Write the hook**

```python
#!/usr/bin/env python3
"""PreToolUse hook for the Bash tool.

Reads tool_input.command from stdin JSON; emits a deny decision for known
bypass patterns. Used as the unified enforcement point for gh/git/package
constraints in the workspace.

Returns:
- exit 0 with empty stdout: implicit allow
- exit 0 with JSON {"hookSpecificOutput": {"permissionDecision": "deny",
                    "permissionDecisionReason": "..."}}: explicit deny
"""
from __future__ import annotations
import json
import re
import sys


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def allow() -> None:
    sys.exit(0)


# Each rule is (regex, reason).
# Order matters: first match wins.
RULES: list[tuple[re.Pattern, str]] = [
    # === gh constraints (replaces pd-gh wrapper) ===
    (re.compile(r"\bgh\s+repo\s+(delete|archive|rename|edit)\b"),
        "Destructive `gh repo` operations are denied."),
    (re.compile(r"\bgh\s+workflow\s+(run|enable|disable)\b"),
        "`gh workflow` operations are denied (PAT lacks Workflows scope)."),
    (re.compile(r"\bgh\s+secret\b"),
        "`gh secret` operations are denied (PAT lacks Administration)."),
    (re.compile(r"\bgh\s+pr\s+ready\b"),
        "Marking PRs ready-for-review is reserved for the human."),
    # gh pr create requires --draft
    (re.compile(r"\bgh\s+pr\s+create\b(?!.*--draft)"),
        "`gh pr create` MUST include --draft (only the human marks ready-for-review)."),
    # bare gh api admin paths
    (re.compile(r"\bgh\s+api\s+\S*admin\b"),
        "`gh api` admin endpoints are denied."),

    # === git push (must use pd-push) ===
    (re.compile(r"\bgit\s+push\b"),
        "Use pd-push for pushing (push only to wip/ship-issue is permitted)."),

    # === Token exfiltration patterns ===
    (re.compile(r"(echo|printf|cat)\s+[^|;]*\$\{?GH_TOKEN"),
        "Token exfiltration pattern: GH_TOKEN."),
    (re.compile(r"(echo|printf|cat)\s+[^|;]*\$\{?GITHUB_TOKEN"),
        "Token exfiltration pattern: GITHUB_TOKEN."),
    (re.compile(r"\benv\s*\|\s*grep\s+\S*TOKEN"),
        "Token-grep is suspicious; denied."),

    # === Credential file access ===
    (re.compile(r"~/\.config/gh"),
        "Credential file access denied."),
    (re.compile(r"~/\.gitconfig\b"),
        "Credential file access denied."),
    (re.compile(r"~/\.netrc\b"),
        "Credential file access denied."),
    (re.compile(r"~/\.ssh\b"),
        "SSH credential access denied."),

    # === Direct api.github.com ===
    (re.compile(r"\b(curl|wget|http|httpie?)\s+\S*api\.github\.com"),
        "Direct GitHub API calls are denied; use scripts that proxy via GH_TOKEN_PD."),
    (re.compile(r"\b(curl|wget)\s+\S*github\.com/.*\.(git|zip)"),
        "Direct GitHub downloads via curl/wget denied."),

    # === Novel package additions outside lockfile ===
    (re.compile(r"\buv\s+add\b"),
        "Use `uv sync`; `uv add` modifies pyproject and needs human approval."),
    (re.compile(r"\buv\s+pip\s+install\b(?!.*(--group|-r |--requirement))"),
        "Use `uv sync`; `uv pip install <novel>` is denied."),
    (re.compile(r"\bpip\s+install\b(?!.*(-r |--requirement|-e |\\.))"),
        "Use `uv sync`; only `pip install -r ...` or `pip install -e .` allowed."),
    (re.compile(r"\bpnpm\s+add\b"),
        "Use `pnpm install`; `pnpm add` needs explicit approval."),
    (re.compile(r"\bnpm\s+install\s+\S+(?!\S*(--save-dev|--package-lock-only))"),
        "Use `npm ci` / `pnpm install`; novel `npm install <pkg>` needs approval."),
    (re.compile(r"\bcargo\s+add\b"),
        "Use Cargo.toml + cargo build; `cargo add` denied."),

    # === Privilege escalation ===
    (re.compile(r"\bsudo\b"),
        "sudo is denied to the bot; vscode-only operation."),
    (re.compile(r"\bchmod\s+777\b"),
        "chmod 777 denied."),
]


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # No useful payload — allow (Claude Code will retry or surface the error)
        allow()

    cmd = data.get("tool_input", {}).get("command", "")
    if not cmd:
        allow()

    for pattern, reason in RULES:
        if pattern.search(cmd):
            deny(f"bash-command-guard: {reason}")

    # claude-ok mutation gate for `gh issue {close,comment,edit,reopen}`
    # This is the same logic as the old pd-gh-issue-guard.py, adapted for bare gh.
    issue_mutation = re.search(
        r"\bgh\s+issue\s+(close|comment|edit|reopen)\s+(\S+)",
        cmd,
    )
    if issue_mutation:
        # Try to extract --repo
        repo_match = re.search(r"(?:--repo|-R)\s+(\S+)", cmd)
        issue_num = issue_mutation.group(2)
        if not repo_match:
            deny(f"bash-command-guard: gh issue {issue_mutation.group(1)} requires --repo")
        repo = repo_match.group(1)
        # Verify the issue has claude-ok
        import os
        import subprocess
        env = os.environ.copy()
        # Use GH_TOKEN_PD if available for the lookup
        token_path = "/run/secrets/gh-token-pd"
        if os.path.isfile(token_path):
            try:
                with open(token_path) as f:
                    env["GH_TOKEN"] = f.read().strip()
            except OSError:
                pass
        try:
            result = subprocess.run(
                ["gh", "issue", "view", issue_num, "--repo", repo, "--json", "labels"],
                capture_output=True, text=True, env=env, timeout=10,
            )
            if result.returncode != 0:
                deny(f"bash-command-guard: could not fetch issue #{issue_num} labels: {result.stderr.strip()}")
            labels = [lbl["name"] for lbl in json.loads(result.stdout).get("labels", [])]
            if "claude-ok" not in labels:
                deny(
                    f"bash-command-guard: issue #{issue_num} in {repo} lacks the 'claude-ok' label. "
                    f"Add the label to permit modification. Current labels: {labels or ['(none)']}"
                )
        except subprocess.TimeoutExpired:
            deny("bash-command-guard: claude-ok lookup timed out")

    allow()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make executable**

Run: `chmod +x .claude/hooks/bash-command-guard.py`

- [ ] **Step 3: Run tests, verify all pass**

Run: `uv run pytest tests/scripts/test_bash_command_guard.py -v 2>&1 | tail -30`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add .claude/hooks/bash-command-guard.py
git commit -m "feat(hooks): add bash-command-guard PreToolUse hook

Unified enforcement of gh/git/package constraints. Replaces the previous
pd-gh-issue-guard.py + pd-gh wrapper allowlist with a single hook script.

Rules: bare git push, gh pr create without --draft, gh pr ready, gh issue
mutations without claude-ok label, gh repo delete/workflow/secret, novel
package adds (uv add/pip install <novel>/pnpm add/cargo add), credential
file access, token exfiltration patterns, direct api.github.com calls."
```

### Task A12: Replace existing pd-gh-issue-guard.py

**Files:**
- Delete: `.claude/hooks/pd-gh-issue-guard.py` (its rules are now in bash-command-guard)

- [ ] **Step 1: Verify the existing hook is now obsolete**

Run: `cat .claude/hooks/pd-gh-issue-guard.py | head -5`
Note: this hook was specific to `pd-gh issue` commands. The new bash-command-guard handles `gh issue` mutations directly with the same claude-ok semantics.

- [ ] **Step 2: Remove pd-gh-issue-guard.py**

Run: `git rm .claude/hooks/pd-gh-issue-guard.py`

- [ ] **Step 3: Commit**

```bash
git commit -m "refactor(hooks): remove pd-gh-issue-guard.py (subsumed by bash-command-guard)

The claude-ok mutation gate now applies to bare gh issue commands inside
the unified bash-command-guard.py. This eliminates the wrapper-and-hook
duplication."
```

---

## Phase 7 — settings.json policy

### Task A13: Update `.claude/settings.json` permissions

**Files:**
- Modify: `.claude/settings.json`

- [ ] **Step 1: Read current settings**

Run: `cat .claude/settings.json | head -80`
Note the existing `permissions` block (if any) and `hooks` block.

- [ ] **Step 2: Update permissions to broad allow + bypass-deny**

Open `.claude/settings.json`. Replace or set the `permissions` block:

```json
{
  "permissions": {
    "allow": [
      "Bash(pd-push:*)",
      "Bash(gh:*)",
      "Bash(git:*)",

      "Bash(uv:*)",
      "Bash(uvx:*)",
      "Bash(pytest:*)",
      "Bash(python:*)",
      "Bash(python3:*)",
      "Bash(pip:*)",
      "Bash(ruff:*)",
      "Bash(mypy:*)",
      "Bash(pre-commit:*)",
      "Bash(pnpm:*)",
      "Bash(npm:*)",
      "Bash(npx:*)",
      "Bash(node:*)",
      "Bash(yarn:*)",
      "Bash(vite:*)",
      "Bash(tsc:*)",
      "Bash(eslint:*)",
      "Bash(prettier:*)",
      "Bash(playwright:*)",
      "Bash(cargo:*)",
      "Bash(maturin:*)",
      "Bash(rustc:*)",
      "Bash(make:*)",
      "Bash(./scripts/:*)",
      "Bash(scripts/:*)",
      "Bash(./bin/:*)",
      "Bash(bash scripts/:*)",
      "Bash(sh scripts/:*)",

      "Bash(for *)",
      "Bash(while *)",
      "Bash(if *)",
      "Bash(case *)",
      "Bash(bash -c *)",
      "Bash(sh -c *)",
      "Bash(env *)",
      "Bash(cd *)",
      "Bash(* | *)",
      "Bash(* && *)",
      "Bash(* || *)",
      "Bash(* ; *)",

      "Bash(grep:*)", "Bash(rg:*)", "Bash(find:*)", "Bash(ls:*)",
      "Bash(cat:*)", "Bash(head:*)", "Bash(tail:*)", "Bash(wc:*)",
      "Bash(awk:*)", "Bash(sed:*)", "Bash(jq:*)", "Bash(yq:*)",
      "Bash(tr:*)", "Bash(sort:*)", "Bash(uniq:*)", "Bash(cut:*)",
      "Bash(xargs:*)", "Bash(tee:*)", "Bash(diff:*)",
      "Bash(mkdir:*)", "Bash(touch:*)", "Bash(cp:*)", "Bash(mv:*)",
      "Bash(chmod:*)", "Bash(stat:*)", "Bash(file:*)",
      "Bash(echo:*)", "Bash(printf:*)", "Bash(date:*)", "Bash(true)",
      "Bash(pwd)", "Bash(env)", "Bash(which:*)", "Bash(type:*)",

      "Read",
      "Edit",
      "Write",
      "Glob",
      "Grep"
    ],
    "deny": [
      "Bash(git push:*)",
      "Bash(*api.github.com*)",
      "Bash(curl*github.com*)",
      "Bash(wget*github.com*)",
      "Bash(*GH_TOKEN*)",
      "Bash(*GITHUB_TOKEN*)",
      "Bash(*~/.config/gh*)",
      "Bash(*~/.gitconfig*)",
      "Bash(*~/.netrc*)",
      "Bash(*~/.ssh*)",
      "Bash(rm -rf /*)",
      "Bash(rm -rf ~*)",
      "Bash(sudo:*)",
      "Bash(chown:*)",
      "Bash(chmod 777:*)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": ".claude/hooks/bash-command-guard.py" }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          { "type": "command", "command": ".claude/hooks/ship-issue-report.py" }
        ]
      }
    ]
  }
}
```

(If the existing settings.json has other top-level keys like `model`, preserve them.)

- [ ] **Step 3: Validate JSON**

Run: `python3 -m json.tool < .claude/settings.json > /dev/null && echo OK`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add .claude/settings.json
git commit -m "feat(settings): broad permissions allow + bypass deny + register hooks

Allow patterns explicitly include shell idioms (for/while/if/case/bash -c,
pipes, chains) so compound commands don't prompt. Deny patterns cover
known bypass paths (bare git push, api.github.com calls, credential file
access, env-var manipulation of GH_TOKEN*).

bash-command-guard.py registered as PreToolUse hook on Bash; settings is
the fast path, the hook is the real enforcement.
ship-issue-report.py registered as SessionEnd hook (will be created in
later task)."
```

---

## Phase 8 — Telemetry pipeline

### Task A14: claude-pricing.json

**Files:**
- Create: `.claude/hooks/claude-pricing.json`

- [ ] **Step 1: Write the rates file**

```json
{
  "api_rates": {
    "claude-opus-4-7":    {"input_per_m": 15.00, "output_per_m": 75.00},
    "claude-sonnet-4-6":  {"input_per_m":  3.00, "output_per_m": 15.00},
    "claude-haiku-4-5":   {"input_per_m":  0.80, "output_per_m":  4.00}
  },
  "_note": "Plan-% comes from the statusline sidecar at dashboard render time, not from this file. This file only carries API-billing rates. Update when Anthropic publishes new pricing."
}
```

- [ ] **Step 2: Validate JSON**

Run: `python3 -m json.tool < .claude/hooks/claude-pricing.json > /dev/null && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .claude/hooks/claude-pricing.json
git commit -m "feat(telemetry): add claude-pricing.json with current API rates"
```

### Task A15: Create agent-memory directory + .gitignore

**Files:**
- Create: `.claude/agent-memory/ship-issue/.gitignore`

- [ ] **Step 1: Create directory**

Run: `mkdir -p .claude/agent-memory/ship-issue`

- [ ] **Step 2: Write .gitignore**

```gitignore
# All telemetry artifacts are local-only; do not commit
*
!.gitignore
```

- [ ] **Step 3: Commit**

```bash
git add .claude/agent-memory/ship-issue/.gitignore
git commit -m "feat(telemetry): add agent-memory/ship-issue dir with gitignore

This directory holds run-reports.jsonl, permission-denials.jsonl, and
cost-dashboard.html — all generated locally and never committed."
```

### Task A16: Test for ship-issue-report.py

**Files:**
- Create: `tests/scripts/test_ship_issue_report.py`

- [ ] **Step 1: Write tests**

```python
# tests/scripts/test_ship_issue_report.py
"""Tests for ship-issue-report.py SessionEnd hook.

Tests are fixture-driven: feed the hook a synthetic .jsonl transcript and
verify it parses tokens correctly and writes the expected JSONL record.
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
HOOK = WORKSPACE / ".claude/hooks/ship-issue-report.py"


def make_transcript(messages: list[dict]) -> str:
    """Write a fake .jsonl transcript and return its path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w")
    for msg in messages:
        tmp.write(json.dumps(msg) + "\n")
    tmp.close()
    return tmp.name


def call_hook(transcript_path: str, session_id: str = "test-session") -> dict:
    payload = json.dumps({
        "transcript_path": transcript_path,
        "session_id": session_id,
    })
    env = os.environ.copy()
    # Direct output to a temp memory dir so we don't pollute the real one
    tmpdir = tempfile.mkdtemp()
    env["SHIP_ISSUE_MEMORY_DIR"] = tmpdir
    result = subprocess.run(
        ["python3", str(HOOK)],
        input=payload, capture_output=True, text=True, env=env,
    )
    return {"rc": result.returncode, "memory_dir": tmpdir,
            "stdout": result.stdout, "stderr": result.stderr}


def test_parses_token_counts():
    transcript = make_transcript([
        {"role": "user", "content": "hi"},
        {"role": "assistant", "model": "claude-opus-4-7",
         "usage": {"input_tokens": 100, "output_tokens": 50}},
        {"role": "assistant", "model": "claude-haiku-4-5",
         "usage": {"input_tokens": 200, "output_tokens": 80}},
    ])
    out = call_hook(transcript)
    assert out["rc"] == 0, out["stderr"]
    log = Path(out["memory_dir"]) / "run-reports.jsonl"
    assert log.exists(), f"expected {log} to exist"
    record = json.loads(log.read_text().strip())
    assert record["tokens_in"] == 300  # 100+200
    assert record["tokens_out"] == 130  # 50+80


def test_computes_api_cost():
    transcript = make_transcript([
        {"role": "assistant", "model": "claude-opus-4-7",
         "usage": {"input_tokens": 1_000_000, "output_tokens": 1_000_000}},
    ])
    out = call_hook(transcript)
    assert out["rc"] == 0, out["stderr"]
    record = json.loads((Path(out["memory_dir"]) / "run-reports.jsonl").read_text().strip())
    # 1M input × $15 + 1M output × $75 = $90
    assert abs(record["api_cost_usd"] - 90.00) < 0.01


def test_handles_empty_transcript():
    transcript = make_transcript([])
    out = call_hook(transcript)
    assert out["rc"] == 0
    record = json.loads((Path(out["memory_dir"]) / "run-reports.jsonl").read_text().strip())
    assert record["tokens_in"] == 0
    assert record["tokens_out"] == 0
    assert record["api_cost_usd"] == 0.0


def test_scans_permission_denials():
    transcript = make_transcript([
        {"role": "tool_use", "name": "Bash", "input": {"command": "git push origin main"},
         "permission_decision": "deny",
         "permission_decision_reason": "bash-command-guard: Use pd-push for pushing"},
        {"role": "tool_use", "name": "Bash", "input": {"command": "pd-push wip/ship-issue"}},
    ])
    out = call_hook(transcript)
    denials = Path(out["memory_dir"]) / "permission-denials.jsonl"
    assert denials.exists()
    record = json.loads(denials.read_text().strip())
    assert "git push" in record["denied_command"]
    assert record["correction_outcome"] in ("recovered", "escalated", "abandoned")
```

- [ ] **Step 2: Run tests (red)**

Run: `uv run pytest tests/scripts/test_ship_issue_report.py -v 2>&1 | tail -20`
Expected: all fail (hook missing).

- [ ] **Step 3: Commit**

```bash
git add tests/scripts/test_ship_issue_report.py
git commit -m "test: add ship-issue-report SessionEnd hook tests (red)"
```

### Task A17: Implement ship-issue-report.py

**Files:**
- Create: `.claude/hooks/ship-issue-report.py`

- [ ] **Step 1: Write the hook**

```python
#!/usr/bin/env python3
"""SessionEnd hook for ship-issue.

Parses the session transcript for token counts and permission denials,
appends to local JSONL files, optionally posts a brief shipped marker
on the issue, and regenerates the cost dashboard.
"""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def memory_dir() -> Path:
    """Allow tests to override via env var."""
    return Path(os.environ.get(
        "SHIP_ISSUE_MEMORY_DIR",
        "/workspaces/ocr-container/.claude/agent-memory/ship-issue",
    ))


def pricing_path() -> Path:
    return Path("/workspaces/ocr-container/.claude/hooks/claude-pricing.json")


def load_pricing() -> dict:
    try:
        return json.loads(pricing_path().read_text())
    except (OSError, json.JSONDecodeError):
        return {"api_rates": {}}


def parse_transcript(path: Path) -> tuple[dict, list[dict]]:
    """Return (token_summary, denial_events)."""
    tokens = {}  # model -> {"input": N, "output": N}
    denials = []
    pending_denial = None

    if not path.exists():
        return tokens, denials

    for line_no, line in enumerate(path.read_text().splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Token counting
        if msg.get("role") == "assistant" and "usage" in msg:
            model = msg.get("model", "unknown")
            usage = msg["usage"]
            entry = tokens.setdefault(model, {"input": 0, "output": 0})
            entry["input"] += usage.get("input_tokens", 0)
            entry["output"] += usage.get("output_tokens", 0)

        # Denial events
        if msg.get("role") == "tool_use":
            decision = msg.get("permission_decision")
            if decision == "deny":
                pending_denial = {
                    "denied_command": msg.get("input", {}).get("command", ""),
                    "reason": msg.get("permission_decision_reason", ""),
                    "tool": msg.get("name", ""),
                    "line_no": line_no,
                    "corrections": [],
                }
                denials.append(pending_denial)
            elif pending_denial is not None and len(pending_denial["corrections"]) < 3:
                # Subsequent tool calls become corrections
                pending_denial["corrections"].append({
                    "command": msg.get("input", {}).get("command", ""),
                    "outcome": "another_denial" if decision == "deny" else "ok",
                })

    # Classify each denial's correction_outcome
    for d in denials:
        corrections = d["corrections"]
        if not corrections:
            d["correction_outcome"] = "abandoned"
        elif any(c["outcome"] == "another_denial" for c in corrections):
            d["correction_outcome"] = "escalated"
        else:
            d["correction_outcome"] = "recovered"

    return tokens, denials


def compute_cost(tokens: dict, pricing: dict) -> float:
    rates = pricing.get("api_rates", {})
    total = 0.0
    for model, counts in tokens.items():
        rate = rates.get(model)
        if not rate:
            continue
        total += counts["input"] * rate["input_per_m"] / 1_000_000
        total += counts["output"] * rate["output_per_m"] / 1_000_000
    return total


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        data = {}

    transcript_path = data.get("transcript_path", "")
    session_id = data.get("session_id", "")

    if not transcript_path:
        sys.exit(0)  # Nothing to do

    tokens, denials = parse_transcript(Path(transcript_path))
    pricing = load_pricing()
    cost = compute_cost(tokens, pricing)

    total_in = sum(t["input"] for t in tokens.values())
    total_out = sum(t["output"] for t in tokens.values())

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "tokens_in": total_in,
        "tokens_out": total_out,
        "tokens_by_model": tokens,
        "api_cost_usd": round(cost, 4),
    }

    mdir = memory_dir()
    append_jsonl(mdir / "run-reports.jsonl", record)

    for d in denials:
        denial_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "denied_command": d["denied_command"],
            "reason": d["reason"],
            "corrections": d["corrections"],
            "correction_outcome": d["correction_outcome"],
        }
        append_jsonl(mdir / "permission-denials.jsonl", denial_record)

    # Best-effort dashboard rebuild — never fail the hook on dashboard errors
    try:
        import subprocess
        subprocess.run(
            ["python3", "/workspaces/ocr-container/scripts/build-cost-dashboard.py"],
            timeout=30, check=False,
        )
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make executable**

Run: `chmod +x .claude/hooks/ship-issue-report.py`

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/scripts/test_ship_issue_report.py -v 2>&1 | tail -20`
Expected: all pass (some may skip dashboard rebuild gracefully if the dashboard script doesn't exist yet).

- [ ] **Step 4: Commit**

```bash
git add .claude/hooks/ship-issue-report.py
git commit -m "feat(hooks): add ship-issue-report SessionEnd hook

Parses session transcript for token counts and permission denials,
appends to run-reports.jsonl and permission-denials.jsonl, computes API
cost from claude-pricing.json, classifies denial corrections as
recovered/escalated/abandoned, and best-effort triggers dashboard rebuild."
```

### Task A18: Test for statusline-with-ratelimits.sh

**Files:**
- Create: `tests/scripts/test_statusline_with_ratelimits.py`

- [ ] **Step 1: Write tests**

```python
# tests/scripts/test_statusline_with_ratelimits.py
"""Test statusline-with-ratelimits.sh writes the sidecar correctly."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/statusline-with-ratelimits.sh"


def call(input_payload: dict, sidecar_path: str | None = None) -> tuple[int, str, str]:
    env = os.environ.copy()
    if sidecar_path:
        env["RATE_LIMITS_SIDECAR"] = sidecar_path
    result = subprocess.run(
        [str(SCRIPT)],
        input=json.dumps(input_payload),
        capture_output=True, text=True, env=env,
    )
    return result.returncode, result.stdout, result.stderr


def test_writes_sidecar():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        sidecar = f.name
    payload = {
        "rate_limits": {
            "five_hour": {"used_percentage": 14.3, "resets_at": "2026-05-09T22:00:00Z"},
            "seven_day": {"used_percentage": 42.1, "resets_at": "2026-05-16T18:00:00Z"},
        },
        "transcript_path": "/tmp/foo.jsonl",
    }
    rc, _, _ = call(payload, sidecar)
    assert rc == 0
    written = json.loads(Path(sidecar).read_text())
    assert written["five_hour"]["used_percentage"] == 14.3
    assert written["seven_day"]["used_percentage"] == 42.1


def test_handles_missing_rate_limits():
    """If stdin has no rate_limits, sidecar should not error."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        sidecar = f.name
    Path(sidecar).unlink()  # ensure absent
    payload = {"transcript_path": "/tmp/foo.jsonl"}
    rc, _, _ = call(payload, sidecar)
    assert rc == 0


def test_emits_statusline_text():
    """Script should also emit the statusline text on stdout."""
    payload = {
        "rate_limits": {
            "five_hour": {"used_percentage": 14.3, "resets_at": "2026-05-09T22:00:00Z"},
        },
        "transcript_path": "/tmp/foo.jsonl",
    }
    rc, stdout, _ = call(payload, "/tmp/dummy-sidecar.json")
    assert rc == 0
    assert "14" in stdout or "%" in stdout  # some indication of rate-limit info
```

- [ ] **Step 2: Run tests (red)**

Run: `uv run pytest tests/scripts/test_statusline_with_ratelimits.py -v 2>&1 | tail -10`
Expected: fail (script missing).

- [ ] **Step 3: Commit**

```bash
git add tests/scripts/test_statusline_with_ratelimits.py
git commit -m "test: add statusline-with-ratelimits tests (red)"
```

### Task A19: Implement statusline-with-ratelimits.sh

**Files:**
- Create: `scripts/statusline-with-ratelimits.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
# statusline-with-ratelimits.sh
# Reads Claude Code's statusline JSON from stdin, writes rate-limit values
# to a sidecar file, and emits the statusline text on stdout.
#
# Sidecar path defaults to /tmp/claude-rate-limits.json (mode 0644).
# Override via env var RATE_LIMITS_SIDECAR for testing.

set -euo pipefail

SIDECAR="${RATE_LIMITS_SIDECAR:-/tmp/claude-rate-limits.json}"

# Read stdin once
INPUT="$(cat)"

# Extract rate_limits block (if present) and write to sidecar
RATE_LIMITS_JSON="$(echo "$INPUT" | jq -c '.rate_limits // empty' 2>/dev/null || true)"
if [[ -n "$RATE_LIMITS_JSON" ]]; then
  # Write sidecar with mode 0644 so claude-bot can also read it
  echo "$RATE_LIMITS_JSON" > "$SIDECAR.tmp"
  chmod 0644 "$SIDECAR.tmp"
  mv "$SIDECAR.tmp" "$SIDECAR"
fi

# Emit a simple statusline text on stdout
FIVE_H="$(echo "$INPUT" | jq -r '.rate_limits.five_hour.used_percentage // "?"' 2>/dev/null || echo "?")"
SEVEN_D="$(echo "$INPUT" | jq -r '.rate_limits.seven_day.used_percentage // "?"' 2>/dev/null || echo "?")"
DIR="$(echo "$INPUT" | jq -r '.cwd // "?"' 2>/dev/null || echo "?")"

printf '%s | 5h: %s%% | 7d: %s%%\n' "$DIR" "$FIVE_H" "$SEVEN_D"
```

- [ ] **Step 2: Make executable**

Run: `chmod +x scripts/statusline-with-ratelimits.sh`

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/scripts/test_statusline_with_ratelimits.py -v 2>&1 | tail -10`
Expected: all pass.

- [ ] **Step 4: Wire into settings.json**

Open `.claude/settings.json`. Add (or update if present) the `statusLine` block at top level:

```json
{
  "statusLine": {
    "command": "scripts/statusline-with-ratelimits.sh"
  }
}
```

- [ ] **Step 5: Validate JSON**

Run: `python3 -m json.tool < .claude/settings.json > /dev/null && echo OK`

- [ ] **Step 6: Commit**

```bash
git add scripts/statusline-with-ratelimits.sh .claude/settings.json
git commit -m "feat(telemetry): add statusline that captures rate_limits sidecar

Writes /tmp/claude-rate-limits.json on every render of an interactive
session, capturing five_hour and seven_day used_percentage. Mode 0644 so
claude-bot can read. Stdout still serves a normal statusline text."
```

### Task A20: Test for build-cost-dashboard.py

**Files:**
- Create: `tests/scripts/test_build_cost_dashboard.py`

- [ ] **Step 1: Write tests**

```python
# tests/scripts/test_build_cost_dashboard.py
"""Tests for build-cost-dashboard.py."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/build-cost-dashboard.py"


def setup_fixture(runs: list[dict], denials: list[dict] = None,
                  sidecar: dict | None = None) -> str:
    """Create a temp memory dir with the given fixtures; return its path."""
    tmpdir = tempfile.mkdtemp()
    runs_path = Path(tmpdir) / "run-reports.jsonl"
    runs_path.write_text("\n".join(json.dumps(r) for r in runs) + ("\n" if runs else ""))
    if denials:
        denials_path = Path(tmpdir) / "permission-denials.jsonl"
        denials_path.write_text("\n".join(json.dumps(d) for d in denials) + "\n")
    return tmpdir


def call(memory_dir: str, sidecar_path: str | None = None) -> tuple[int, Path]:
    env = os.environ.copy()
    env["SHIP_ISSUE_MEMORY_DIR"] = memory_dir
    # Skip the gh-driven kanban panel so tests don't depend on a live network
    env["DASHBOARD_SKIP_KANBAN"] = "1"
    if sidecar_path:
        env["RATE_LIMITS_SIDECAR"] = sidecar_path
    result = subprocess.run(
        ["python3", str(SCRIPT)],
        capture_output=True, text=True, env=env,
    )
    return result.returncode, Path(memory_dir) / "cost-dashboard.html"


def test_generates_html_with_no_runs():
    mdir = setup_fixture([])
    rc, html_path = call(mdir)
    assert rc == 0
    assert html_path.exists()
    content = html_path.read_text()
    assert "<html" in content.lower()
    assert "ship-issue" in content.lower()


def test_html_includes_session_costs():
    runs = [
        {"timestamp": "2026-05-09T18:00:00Z", "session_id": "s1",
         "tokens_in": 100000, "tokens_out": 50000, "api_cost_usd": 4.21,
         "tokens_by_model": {"claude-opus-4-7": {"input": 100000, "output": 50000}}},
        {"timestamp": "2026-05-09T19:00:00Z", "session_id": "s2",
         "tokens_in": 5000, "tokens_out": 2000, "api_cost_usd": 0.08,
         "tokens_by_model": {"claude-haiku-4-5": {"input": 5000, "output": 2000}}},
    ]
    mdir = setup_fixture(runs)
    rc, html_path = call(mdir)
    assert rc == 0
    content = html_path.read_text()
    assert "4.21" in content
    assert "0.08" in content


def test_html_shows_plan_pct_when_sidecar_present():
    runs = [
        {"timestamp": "2026-05-09T18:00:00Z", "session_id": "s1",
         "tokens_in": 100000, "tokens_out": 50000, "api_cost_usd": 4.21,
         "tokens_by_model": {"claude-opus-4-7": {"input": 100000, "output": 50000}}},
    ]
    mdir = setup_fixture(runs)
    sidecar = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    sidecar.write(json.dumps({
        "five_hour": {"used_percentage": 14.3, "resets_at": "2026-05-09T22:00:00Z"},
        "seven_day": {"used_percentage": 42.1, "resets_at": "2026-05-16T18:00:00Z"},
    }).encode())
    sidecar.close()
    rc, html_path = call(mdir, sidecar.name)
    assert rc == 0
    content = html_path.read_text()
    assert "14.3" in content or "14" in content
    assert "approximate" in content.lower()  # Per-session % is flagged approximate


def test_html_shows_denials_panel():
    runs = [
        {"timestamp": "2026-05-09T18:00:00Z", "session_id": "s1",
         "tokens_in": 100000, "tokens_out": 50000, "api_cost_usd": 4.21,
         "tokens_by_model": {}},
    ]
    denials = [
        {"timestamp": "2026-05-09T18:01:00Z", "session_id": "s1",
         "denied_command": "git push origin main", "reason": "Use pd-push",
         "corrections": [{"command": "pd-push wip/ship-issue", "outcome": "ok"}],
         "correction_outcome": "recovered"},
    ]
    mdir = setup_fixture(runs, denials)
    rc, html_path = call(mdir)
    assert rc == 0
    content = html_path.read_text()
    assert "git push" in content
    assert "recovered" in content.lower()


def test_kanban_section_renders_placeholder_when_skipped():
    """With DASHBOARD_SKIP_KANBAN=1 the panel still renders a placeholder
    rather than failing or omitting the section heading."""
    mdir = setup_fixture([])
    rc, html_path = call(mdir)
    assert rc == 0
    content = html_path.read_text()
    assert "Work board" in content
    assert "Kanban data unavailable" in content
```

- [ ] **Step 2: Run tests (red)**

Run: `uv run pytest tests/scripts/test_build_cost_dashboard.py -v 2>&1 | tail -10`
Expected: fail (script missing).

- [ ] **Step 3: Commit**

```bash
git add tests/scripts/test_build_cost_dashboard.py
git commit -m "test: add cost-dashboard tests (red)"
```

### Task A21: Implement build-cost-dashboard.py

**Files:**
- Create: `scripts/build-cost-dashboard.py`

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Generate cost-dashboard.html from run-reports.jsonl + sidecar + gh issue lists.

Reads:
- $SHIP_ISSUE_MEMORY_DIR/run-reports.jsonl
- $SHIP_ISSUE_MEMORY_DIR/permission-denials.jsonl  (optional)
- $RATE_LIMITS_SIDECAR (default /tmp/claude-rate-limits.json)  (optional)
- gh issue list per pd-* repo for the kanban panel  (skipped if gh unavailable)

Writes:
- $SHIP_ISSUE_MEMORY_DIR/cost-dashboard.html

Env:
- DASHBOARD_SKIP_KANBAN=1   skip the gh-driven kanban panel (e.g., in tests)
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPOS = (
    "pdomain-book-tools", "pdomain-ocr-cli", "pd-ocr-labeler", "pdomain-ocr-labeler-spa",
    "pdomain-ocr-synth", "pd-ocr-trainer", "pd-png-optimizer", "pdomain-prep-for-pgdp",
)
KANBAN_COLUMNS = ("status:backlog", "status:ready", "status:in-progress",
                  "status:done", "status:blocked")


def memory_dir() -> Path:
    return Path(os.environ.get(
        "SHIP_ISSUE_MEMORY_DIR",
        "/workspaces/ocr-container/.claude/agent-memory/ship-issue",
    ))


def sidecar_path() -> Path:
    return Path(os.environ.get(
        "RATE_LIMITS_SIDECAR", "/tmp/claude-rate-limits.json"))


def load_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def load_sidecar() -> dict | None:
    p = sidecar_path()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        data["_mtime"] = p.stat().st_mtime
        return data
    except (OSError, json.JSONDecodeError):
        return None


def runs_in_window(runs: list[dict], hours: float) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out = []
    for r in runs:
        try:
            ts = datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
            if ts >= cutoff:
                out.append(r)
        except (KeyError, ValueError):
            continue
    return out


def compute_per_session_pct(runs: list[dict], window_pct: float, window_hours: float) -> dict:
    """Approximate per-session plan-% using rate-based attribution.

    rate = sum(window-tokens) / window_pct
    session_pct = session.tokens_total × (1 / rate) = session.tokens × window_pct / sum(tokens)
    """
    window_runs = runs_in_window(runs, window_hours)
    total_tokens = sum(r.get("tokens_in", 0) + r.get("tokens_out", 0) for r in window_runs)
    if total_tokens == 0 or window_pct == 0:
        return {}
    return {
        r["session_id"]: round(
            (r.get("tokens_in", 0) + r.get("tokens_out", 0)) * window_pct / total_tokens, 3
        )
        for r in window_runs
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ship-issue cost dashboard</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       background: #fafafa; color: #222; max-width: 1100px; margin: 2em auto; padding: 0 1em; }}
h1, h2 {{ font-weight: 600; border-bottom: 1px solid #ddd; padding-bottom: .3em; }}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.92em; }}
th, td {{ padding: 6px 10px; text-align: left; border-bottom: 1px solid #eee; }}
th {{ background: #f0f0f0; }}
.flag {{ color: #888; font-size: 0.85em; }}
.recovered {{ color: #2a7; }} .escalated {{ color: #d22; font-weight: 600; }} .abandoned {{ color: #a82; }}
.kpi {{ display: inline-block; margin-right: 2em; }}
.kpi-value {{ font-size: 1.6em; font-weight: 600; }}
.kpi-label {{ color: #666; font-size: 0.85em; }}
.kanban {{ font-size: 0.85em; }}
.kanban td {{ vertical-align: top; min-width: 120px; }}
.kanban .col-backlog    {{ background: #fafafa; }}
.kanban .col-ready      {{ background: #e8f5e9; }}
.kanban .col-in-progress{{ background: #fff8e1; }}
.kanban .col-done       {{ background: #f1f8e9; }}
.kanban .col-blocked    {{ background: #ffebee; }}
.kanban .card {{ display: block; padding: 3px 6px; margin: 3px 0;
                 background: #fff; border: 1px solid #ddd; border-radius: 3px;
                 text-decoration: none; color: #222; }}
.kanban .card:hover {{ border-color: #888; }}
.kanban .card .meta {{ color: #888; font-size: 0.85em; }}
</style>
</head>
<body>
<h1>ship-issue cost dashboard</h1>
<p class="flag">Generated {now}</p>

<h2>Plan window usage</h2>
{plan_block}

<h2>Work board (cross-repo)</h2>
{kanban_panel}

<h2>Recent runs (last 50)</h2>
{runs_table}

<h2>Aggregates</h2>
<div class="kpi"><span class="kpi-value">${total_cost_30d:.2f}</span><br>
  <span class="kpi-label">API cost, last 30d</span></div>
<div class="kpi"><span class="kpi-value">{n_runs_30d}</span><br>
  <span class="kpi-label">Runs, last 30d</span></div>

<h2>Permission denials (last 50)</h2>
{denials_table}

</body>
</html>
"""


def render_plan_block(sidecar: dict | None, runs: list[dict]) -> str:
    if not sidecar:
        return "<p class='flag'>No sidecar yet — run an interactive Claude session to populate /tmp/claude-rate-limits.json.</p>"

    five_h = sidecar.get("five_hour", {}).get("used_percentage", "?")
    seven_d = sidecar.get("seven_day", {}).get("used_percentage", "?")
    five_h_resets = sidecar.get("five_hour", {}).get("resets_at", "?")
    seven_d_resets = sidecar.get("seven_day", {}).get("resets_at", "?")

    mtime = sidecar.get("_mtime", 0)
    age_min = int((datetime.now(timezone.utc).timestamp() - mtime) / 60) if mtime else "?"

    return f"""
<p>
  <strong>5h window:</strong> {five_h}% used (resets {five_h_resets})
  <span class="flag">| sidecar age: {age_min} min</span><br>
  <strong>7d window:</strong> {seven_d}% used (resets {seven_d_resets})
</p>
"""


def render_runs_table(runs: list[dict], session_pct_5h: dict, session_pct_7d: dict) -> str:
    rows = []
    rows.append("<tr><th>Time</th><th>Session</th><th>Tokens</th>"
                "<th>Cost</th><th>≈ 5h%</th><th>≈ 7d%</th></tr>")
    for r in reversed(runs[-50:]):
        ts = r.get("timestamp", "?")[:19].replace("T", " ")
        sid = r.get("session_id", "?")[:10]
        tokens = r.get("tokens_in", 0) + r.get("tokens_out", 0)
        cost = r.get("api_cost_usd", 0)
        p5 = session_pct_5h.get(r.get("session_id", ""), "")
        p7 = session_pct_7d.get(r.get("session_id", ""), "")
        rows.append(f"<tr><td>{ts}</td><td>{sid}</td><td>{tokens:,}</td>"
                    f"<td>${cost:.2f}</td><td>{p5}</td><td>{p7}</td></tr>")
    table = "<table>" + "".join(rows) + "</table>"
    if session_pct_5h or session_pct_7d:
        table += "<p class='flag'>Per-session plan-% values are <em>approximate</em>, computed from current sidecar rate. For exact attribution, see future-state Sidecar history.</p>"
    return table


def load_kanban_data(repos: tuple[str, ...]) -> dict[str, dict[str, list[dict]]]:
    """Return repo → status_label → [issue, ...] using gh issue list per repo.

    Each issue dict carries: number, title, labels (list of names).
    Falls back to {} on any gh failure so the dashboard still renders.
    """
    if os.environ.get("DASHBOARD_SKIP_KANBAN") == "1":
        return {}
    env = os.environ.copy()
    token_path = "/run/secrets/gh-token-pd"
    if Path(token_path).is_file():
        env["GH_TOKEN"] = Path(token_path).read_text().strip()

    out: dict[str, dict[str, list[dict]]] = {}
    for repo in repos:
        out[repo] = {col: [] for col in KANBAN_COLUMNS}
        try:
            result = subprocess.run(
                ["gh", "issue", "list", "--repo", f"ConcaveTrillion/{repo}",
                 "--state", "open", "--json", "number,title,labels",
                 "--limit", "200"],
                capture_output=True, text=True, env=env, timeout=20,
            )
            if result.returncode != 0:
                continue
            for issue in json.loads(result.stdout):
                names = {l["name"] for l in issue.get("labels", [])}
                # First matching status:* label wins (single-select discipline)
                for col in KANBAN_COLUMNS:
                    if col in names:
                        out[repo][col].append({
                            "number": issue["number"],
                            "title": issue["title"],
                            "labels": sorted(names),
                        })
                        break
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            continue
    return out


def render_kanban_panel(data: dict[str, dict[str, list[dict]]]) -> str:
    if not data:
        return ("<p class='flag'>Kanban data unavailable "
                "(gh CLI not reachable or DASHBOARD_SKIP_KANBAN=1).</p>")
    headers = "".join(
        f"<th>{c.split(':', 1)[1]}</th>" for c in KANBAN_COLUMNS
    )
    rows: list[str] = [f"<tr><th>repo</th>{headers}</tr>"]
    for repo in sorted(data):
        cells = [f"<th>{repo}</th>"]
        for col in KANBAN_COLUMNS:
            issues = data[repo].get(col, [])
            cls = "col-" + col.split(":", 1)[1]
            cards = "".join(
                f'<a class="card" href="https://github.com/ConcaveTrillion/'
                f'{repo}/issues/{i["number"]}">'
                f'#{i["number"]} {i["title"][:60]}'
                f'<span class="meta"> · {_meta(i["labels"])}</span></a>'
                for i in issues
            )
            cells.append(f'<td class="{cls}">{cards or "&nbsp;"}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f'<table class="kanban">{"".join(rows)}</table>'


def _meta(labels: list[str]) -> str:
    """One-line summary of effort + model labels for a kanban card."""
    bits: list[str] = []
    for prefix in ("effort:", "model:", "model-effort:"):
        for l in labels:
            if l.startswith(prefix):
                bits.append(l)
                break
    return " ".join(bits) or "—"


def render_denials_table(denials: list[dict]) -> str:
    if not denials:
        return "<p class='flag'>No permission denials recorded.</p>"
    rows = []
    rows.append("<tr><th>Time</th><th>Command</th><th>Reason</th><th>Outcome</th></tr>")
    for d in reversed(denials[-50:]):
        ts = d.get("timestamp", "?")[:19].replace("T", " ")
        cmd = d.get("denied_command", "")[:80]
        reason = d.get("reason", "")[:80]
        outcome = d.get("correction_outcome", "?")
        rows.append(f"<tr><td>{ts}</td><td><code>{cmd}</code></td>"
                    f"<td>{reason}</td><td class='{outcome}'>{outcome}</td></tr>")
    return "<table>" + "".join(rows) + "</table>"


def main():
    mdir = memory_dir()
    runs = load_jsonl(mdir / "run-reports.jsonl")
    denials = load_jsonl(mdir / "permission-denials.jsonl")
    sidecar = load_sidecar()

    session_pct_5h = {}
    session_pct_7d = {}
    if sidecar:
        five_h_pct = sidecar.get("five_hour", {}).get("used_percentage", 0) or 0
        seven_d_pct = sidecar.get("seven_day", {}).get("used_percentage", 0) or 0
        session_pct_5h = compute_per_session_pct(runs, five_h_pct, 5)
        session_pct_7d = compute_per_session_pct(runs, seven_d_pct, 24 * 7)

    runs_30d = runs_in_window(runs, 24 * 30)
    total_cost_30d = sum(r.get("api_cost_usd", 0) for r in runs_30d)

    kanban_data = load_kanban_data(REPOS)

    html = HTML_TEMPLATE.format(
        now=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        plan_block=render_plan_block(sidecar, runs),
        kanban_panel=render_kanban_panel(kanban_data),
        runs_table=render_runs_table(runs, session_pct_5h, session_pct_7d),
        total_cost_30d=total_cost_30d,
        n_runs_30d=len(runs_30d),
        denials_table=render_denials_table(denials),
    )

    out = mdir / "cost-dashboard.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    sys.stderr.write(f"Wrote {out}\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make executable**

Run: `chmod +x scripts/build-cost-dashboard.py`

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/scripts/test_build_cost_dashboard.py -v 2>&1 | tail -10`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add scripts/build-cost-dashboard.py
git commit -m "feat(dashboard): add build-cost-dashboard.py

Renders cost-dashboard.html from run-reports.jsonl + permission-denials.jsonl
+ sidecar + a cross-repo kanban panel pulled from gh issue list. Shows
per-session approximate plan-% (rate-based attribution), plan window usage,
work-board kanban (5 status:* columns × 8 pd-* repos with clickable cards),
recent runs table, denials panel with recovered/escalated/abandoned
classification. Kanban falls back to a 'data unavailable' note if gh isn't
reachable or DASHBOARD_SKIP_KANBAN=1 is set (used in unit tests)."
```

---

## Phase 9 — ship-issue scripts

### Task A22: Tests for ship-issue-throttle-check.sh

**Files:**
- Create: `tests/scripts/test_ship_issue_throttle_check.py`

- [ ] **Step 1: Write tests**

```python
# tests/scripts/test_ship_issue_throttle_check.py
"""Tests for ship-issue-throttle-check.sh."""
import os
import subprocess
import tempfile
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/ship-issue-throttle-check.sh"


def setup_repo(commits_age_days: list[int]) -> Path:
    """Create a temp git repo with main + wip/ship-issue having commits at given ages."""
    repo = Path(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    # Initial commit on main
    (repo / "README.md").write_text("test\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init", "--date", "2026-04-01T00:00:00"],
                   cwd=repo, check=True, env={**os.environ,
                       "GIT_AUTHOR_DATE": "2026-04-01T00:00:00",
                       "GIT_COMMITTER_DATE": "2026-04-01T00:00:00"})
    # Create wip/ship-issue with each commit at the requested age
    subprocess.run(["git", "checkout", "-b", "wip/ship-issue"], cwd=repo, check=True, capture_output=True)
    from datetime import datetime, timedelta, timezone
    for i, days in enumerate(commits_age_days):
        date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        (repo / f"file{i}.txt").write_text(f"line {i}\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", f"slice {i}"], cwd=repo, check=True,
                       env={**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date})
    return repo


def call(repo: Path, max_age_days: int = 7) -> tuple[int, str, str]:
    env = os.environ.copy()
    env["MAX_UNMERGED_AGE_DAYS"] = str(max_age_days)
    result = subprocess.run(
        [str(SCRIPT)],
        cwd=repo, capture_output=True, text=True, env=env,
    )
    return result.returncode, result.stdout, result.stderr


def test_no_branch_no_throttle():
    """If wip/ship-issue doesn't exist, exit 0 (nothing to throttle)."""
    repo = Path(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@e"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "README.md").write_text("test\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True)
    rc, _, _ = call(repo)
    assert rc == 0


def test_recent_commits_no_throttle():
    """Commits 1 day old: not throttled."""
    repo = setup_repo([1])
    rc, _, _ = call(repo)
    assert rc == 0


def test_old_commit_throttles():
    """Oldest unmerged commit > 7 days: throttle."""
    repo = setup_repo([1, 5, 10])  # oldest is 10 days
    rc, _, err = call(repo)
    assert rc != 0
    assert "7 day" in err.lower() or "old" in err.lower() or "throttle" in err.lower()


def test_configurable_threshold():
    """MAX_UNMERGED_AGE_DAYS overrides the 7-day default."""
    repo = setup_repo([1, 5, 10])  # oldest is 10 days
    rc, _, _ = call(repo, max_age_days=15)  # threshold raised to 15
    assert rc == 0
```

- [ ] **Step 2: Run tests (red)**

Run: `uv run pytest tests/scripts/test_ship_issue_throttle_check.py -v 2>&1 | tail -10`
Expected: fail (script missing).

- [ ] **Step 3: Commit**

```bash
git add tests/scripts/test_ship_issue_throttle_check.py
git commit -m "test: add ship-issue throttle-check tests (red)"
```

### Task A23: Implement ship-issue-throttle-check.sh

**Files:**
- Create: `scripts/ship-issue-throttle-check.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
# ship-issue-throttle-check.sh
# Exits non-zero (with reason on stderr) if the oldest unmerged commit on
# wip/ship-issue is older than MAX_UNMERGED_AGE_DAYS (default 7).
#
# Run from inside any git repo. If wip/ship-issue doesn't exist or has no
# commits ahead of main, exits 0.

set -euo pipefail

MAX_AGE_DAYS="${MAX_UNMERGED_AGE_DAYS:-7}"

# Ensure we're in a git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
  echo "throttle: not in a git repo" >&2
  exit 0
fi

# Check if wip/ship-issue exists
if ! git rev-parse --verify wip/ship-issue > /dev/null 2>&1; then
  exit 0
fi

# Find main branch (could be main or master)
MAIN_REF=""
for ref in main master; do
  if git rev-parse --verify "$ref" > /dev/null 2>&1; then
    MAIN_REF="$ref"
    break
  fi
done
if [[ -z "$MAIN_REF" ]]; then
  echo "throttle: cannot find main or master" >&2
  exit 0
fi

# Get oldest unmerged commit's committer date in seconds-since-epoch
OLDEST_TS="$(git log wip/ship-issue --not "$MAIN_REF" --reverse --format=%ct | head -1 || true)"
if [[ -z "$OLDEST_TS" ]]; then
  # No commits ahead of main
  exit 0
fi

NOW="$(date +%s)"
AGE_SEC=$(( NOW - OLDEST_TS ))
AGE_DAYS=$(( AGE_SEC / 86400 ))

if [[ $AGE_DAYS -gt $MAX_AGE_DAYS ]]; then
  OLDEST_DATE="$(date -u -d "@$OLDEST_TS" +"%Y-%m-%d %H:%M UTC" 2>/dev/null || date -u -r "$OLDEST_TS" +"%Y-%m-%d %H:%M UTC")"
  echo "throttle: wip/ship-issue has unreviewed commits older than $MAX_AGE_DAYS days" >&2
  echo "  oldest unmerged: $OLDEST_DATE ($AGE_DAYS days ago)" >&2
  echo "  Merge or close the draft PR before continuing." >&2
  exit 1
fi

exit 0
```

- [ ] **Step 2: Make executable**

Run: `chmod +x scripts/ship-issue-throttle-check.sh`

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/scripts/test_ship_issue_throttle_check.py -v 2>&1 | tail -10`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add scripts/ship-issue-throttle-check.sh
git commit -m "feat(ship-issue): add throttle-check script

Exits nonzero if oldest unmerged commit on wip/ship-issue is older than
MAX_UNMERGED_AGE_DAYS (default 7). Used as the first step of every
ship-issue run to refuse new claims when human attention has lapsed."
```

### Task A24: Stub for ship-issue-pick.py (with documented contract)

**Files:**
- Create: `tests/scripts/test_ship_issue_pick.py`
- Create: `scripts/ship-issue-pick.py`

ship-issue-pick uses `gh issue list` with label filters (no Project API). For v1 we ship the script structure with mockable IO; integration testing against a real repo happens in Plan B.

- [ ] **Step 1: Write a basic structure test**

```python
# tests/scripts/test_ship_issue_pick.py
"""Tests for ship-issue-pick.py.

This script does gh API work; full integration test is in Plan B.
Here we test:
- Script exists and is executable
- --help prints usage
- Eligibility predicate logic (unit-testable)
"""
import os
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/ship-issue-pick.py"


def test_script_exists():
    assert SCRIPT.exists()
    assert os.access(SCRIPT, os.X_OK)


def test_help_works():
    result = subprocess.run(
        ["python3", str(SCRIPT), "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "ship-issue" in result.stdout.lower()


def _eligible_fixture():
    return {
        "number": 42,
        "labels": [
            {"name": "kind:feature"}, {"name": "claude-ok"},
            {"name": "model:haiku"}, {"name": "model-effort:low"},
            {"name": "effort:S"}, {"name": "status:ready"},
        ],
        "authorAssociation": "OWNER",
        "body": "## Context\n\nFoo.\n\n## Spec\n\nSpec: docs/specs/foo.md#decision\n",
    }


def test_eligibility_predicate():
    """Import the module and test the eligibility check directly."""
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("ship_issue_pick", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Eligible issue
    issue = _eligible_fixture()
    ok, reason = mod.is_eligible(issue)
    assert ok, f"expected eligible, got: {reason}"

    # Missing status:ready (label query may not have caught this if labels changed)
    issue_no_status = {**issue, "labels": [l for l in issue["labels"] if l["name"] != "status:ready"]}
    ok, reason = mod.is_eligible(issue_no_status)
    assert not ok
    assert "status:ready" in reason.lower()

    # Wrong status (e.g. blocked added after query)
    issue_blocked = {**issue, "labels": issue["labels"] + [{"name": "status:blocked"}]}
    ok, reason = mod.is_eligible(issue_blocked)
    assert not ok
    assert "status" in reason.lower()

    # Non-OWNER author
    issue2 = {**issue, "authorAssociation": "NONE"}
    ok, reason = mod.is_eligible(issue2)
    assert not ok
    assert "author" in reason.lower()

    # Missing claude-ok
    issue3 = {**issue, "labels": [l for l in issue["labels"] if l["name"] != "claude-ok"]}
    ok, reason = mod.is_eligible(issue3)
    assert not ok
    assert "claude-ok" in reason.lower()

    # xhigh requires opus
    issue4 = {**issue, "labels": [
        {"name": "kind:feature"}, {"name": "claude-ok"},
        {"name": "model:haiku"}, {"name": "model-effort:xhigh"},
        {"name": "effort:S"}, {"name": "status:ready"},
    ]}
    ok, reason = mod.is_eligible(issue4)
    assert not ok
    assert "xhigh" in reason.lower() or "opus" in reason.lower()

    # Bug exempt from Spec: requirement
    issue5 = {**issue, "labels": [
        {"name": "kind:bug"}, {"name": "claude-ok"},
        {"name": "model:haiku"}, {"name": "model-effort:low"},
        {"name": "effort:S"}, {"name": "status:ready"},
    ], "body": "## Repro\n\n1. foo\n\n## Expected\n\nbar\n"}
    ok, reason = mod.is_eligible(issue5)
    assert ok, f"bug should be eligible without Spec: line, got: {reason}"
```

- [ ] **Step 2: Write the script**

```python
#!/usr/bin/env python3
"""ship-issue-pick: query, validate, claim the next eligible issue.

Lists open issues with `status:ready` AND `claude-ok` labels, validates
eligibility per spec rules, picks the lowest-numbered eligible one, swaps
its status label `status:ready` → `status:in-progress`, posts the claim
comment, and prints one stdout line for the caller to consume:

    ISSUE=42 REPO=pdomain/pdomain-prep-for-pgdp \\
    MODEL=haiku MODEL_EFFORT=low KIND=feature \\
    SPEC_PATH=docs/specs/02-backend.md#decision \\
    ACCEPTANCE_JSON=/tmp/ship-issue-acceptance-42.json \\
    PRE_CLAIM_SHA=<sha>

Or "NONE" if no eligible issue is found.

Requires: gh CLI auth (GH_TOKEN_PD or equivalent), git in a repo dir.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


REQUIRED_LABEL_FAMILIES = {"kind", "model", "model-effort"}
ALLOWED_KINDS = {"feature", "bug", "spec", "chore"}
ALLOWED_MODELS = {"haiku", "sonnet", "opus"}
ALLOWED_MODEL_EFFORTS = {"low", "medium", "high", "xhigh", "max"}
TRUSTED_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}


def is_eligible(issue: dict) -> tuple[bool, str]:
    """Return (eligible, reason). Reason explains why if not eligible.

    Defensive re-check after the gh-issue-list label filter; status labels
    are convention-enforced single-select, so we verify exactly one status:*
    is present and it's status:ready.
    """
    label_names = {l["name"] for l in issue.get("labels", [])}

    status_labels = sorted(n for n in label_names if n.startswith("status:"))
    if not status_labels:
        return False, "missing status:ready label"
    if len(status_labels) > 1:
        return False, f"multiple status:* labels (single-select violation): {status_labels}"
    if status_labels[0] != "status:ready":
        return False, f"status is {status_labels[0]!r}, not status:ready"

    if "claude-ok" not in label_names:
        return False, "missing claude-ok label"

    aa = issue.get("authorAssociation", "")
    if aa not in TRUSTED_ASSOCIATIONS:
        return False, f"authorAssociation {aa!r} not trusted"

    by_family = {}
    for name in label_names:
        if ":" in name:
            family, value = name.split(":", 1)
            by_family.setdefault(family, []).append(value)

    for fam in REQUIRED_LABEL_FAMILIES:
        if fam not in by_family:
            return False, f"missing {fam}: label"
        if len(by_family[fam]) > 1:
            return False, f"multiple {fam}: labels: {by_family[fam]}"

    kind = by_family["kind"][0]
    if kind not in ALLOWED_KINDS:
        return False, f"unknown kind: {kind}"

    model = by_family["model"][0]
    if model not in ALLOWED_MODELS:
        return False, f"unknown model: {model}"

    me = by_family["model-effort"][0]
    if me not in ALLOWED_MODEL_EFFORTS:
        return False, f"unknown model-effort: {me}"

    if me == "xhigh" and model != "opus":
        return False, "model-effort:xhigh requires model:opus"

    body = issue.get("body", "") or ""
    has_spec = bool(re.search(r"^Spec:\s*\S", body, re.MULTILINE))
    if not has_spec and kind not in {"bug", "chore", "spec"}:
        return False, f"kind:{kind} body must contain a 'Spec:' line"

    return True, "eligible"


def gh_api(args: list[str]) -> dict | list:
    """Run gh and parse JSON output."""
    env = os.environ.copy()
    token_path = "/run/secrets/gh-token-pd"
    if Path(token_path).is_file():
        env["GH_TOKEN"] = Path(token_path).read_text().strip()
    result = subprocess.run(["gh", *args], capture_output=True, text=True, env=env)
    if result.returncode != 0:
        sys.stderr.write(f"gh failed: {result.stderr}\n")
        sys.exit(2)
    return json.loads(result.stdout)


def list_ready_issues(repo: str) -> list[dict]:
    """Open issues with both status:ready AND claude-ok, sorted by number."""
    issues = gh_api([
        "issue", "list", "--repo", repo, "--state", "open",
        "--label", "status:ready", "--label", "claude-ok",
        "--json", "number,title,labels,author,authorAssociation,body",
        "--limit", "100",
    ])
    return sorted(issues, key=lambda i: i["number"])


def post_skip_comment(repo: str, number: int, reason: str) -> None:
    subprocess.run(
        ["gh", "issue", "comment", str(number), "--repo", repo,
         "--body", f"ship-issue: skipped — {reason}"],
        capture_output=True,
    )


def claim_issue(repo: str, number: int,
                model: str, model_effort: str, spec_path: str,
                acceptance: list[str], pre_claim_sha: str) -> None:
    """Swap status:ready → status:in-progress; post claim comment.

    Single-select discipline: remove status:ready before adding
    status:in-progress in one `gh issue edit` call.
    """
    subprocess.run(
        ["gh", "issue", "edit", str(number), "--repo", repo,
         "--remove-label", "status:ready",
         "--add-label", "status:in-progress"],
        check=True, capture_output=True,
    )

    acceptance_text = "\n".join(f"- [ ] {a}" for a in acceptance) if acceptance else "(none)"
    body = (
        f"Claimed by ship-issue.\n\n"
        f"- Model: `{model}` / effort: `{model_effort}`\n"
        f"- Spec: `{spec_path or '(none)'}`\n"
        f"- Pre-claim SHA: `{pre_claim_sha}`\n\n"
        f"Acceptance:\n{acceptance_text}\n"
    )
    subprocess.run(
        ["gh", "issue", "comment", str(number), "--repo", repo, "--body", body],
        check=True, capture_output=True,
    )


def extract_spec_path(body: str) -> str:
    m = re.search(r"^Spec:\s*(\S.*?)\s*$", body, re.MULTILINE)
    return m.group(1).strip() if m else ""


def extract_acceptance(body: str) -> list[str]:
    """Find checkbox items under '## Acceptance' or 'Acceptance:'."""
    m = re.search(r"(?:^##\s*Acceptance|Acceptance:)\s*\n(.*?)(?=\n##|\Z)",
                  body, re.MULTILINE | re.DOTALL)
    if not m:
        return []
    return [
        line[5:].strip()
        for line in m.group(1).splitlines()
        if line.strip().startswith("- [ ]")
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Pick + claim the next eligible ship-issue work item."
    )
    parser.add_argument("--repo", required=True, help="ConcaveTrillion/<repo>")
    args = parser.parse_args()

    repo = args.repo

    # Capture pre-claim SHA before doing anything that mutates branch
    pre_claim_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    # Rebase wip/ship-issue onto origin/main BEFORE claiming
    # (per spec: rebase failure leaves no half-claimed issue)
    rebase_result = subprocess.run(
        ["bash", "-c",
         "git fetch origin && "
         "git checkout wip/ship-issue 2>/dev/null || git checkout -b wip/ship-issue origin/main && "
         "git rebase origin/main"],
        capture_output=True, text=True,
    )
    if rebase_result.returncode != 0:
        subprocess.run(["git", "rebase", "--abort"], capture_output=True)
        sys.stderr.write("rebase failed; will not claim. Resolve manually.\n")
        print("NONE")
        sys.exit(0)

    candidates = list_ready_issues(repo)

    for issue in candidates:
        ok, reason = is_eligible(issue)
        if ok:
            kind = next(l["name"].split(":", 1)[1] for l in issue["labels"] if l["name"].startswith("kind:"))
            model = next(l["name"].split(":", 1)[1] for l in issue["labels"] if l["name"].startswith("model:"))
            me = next(l["name"].split(":", 1)[1] for l in issue["labels"] if l["name"].startswith("model-effort:"))
            spec = extract_spec_path(issue.get("body", "") or "")
            acceptance = extract_acceptance(issue.get("body", "") or "")
            claim_issue(repo, issue["number"], model, me, spec,
                        acceptance, pre_claim_sha)
            acc_path = f"/tmp/ship-issue-acceptance-{issue['number']}.json"
            with open(acc_path, "w") as f:
                json.dump(acceptance, f)
            print(
                f"ISSUE={issue['number']} REPO={repo} "
                f"MODEL={model} MODEL_EFFORT={me} KIND={kind} "
                f"SPEC_PATH={spec or ''} ACCEPTANCE_JSON={acc_path} "
                f"PRE_CLAIM_SHA={pre_claim_sha}"
            )
            return

        # Skip silently if claude-ok missing; otherwise post comment
        if "claude-ok" in {l["name"] for l in issue.get("labels", [])}:
            post_skip_comment(repo, issue["number"], reason)

    print("NONE")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Make executable**

Run: `chmod +x scripts/ship-issue-pick.py`

- [ ] **Step 4: Run unit tests**

Run: `uv run pytest tests/scripts/test_ship_issue_pick.py -v 2>&1 | tail -10`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/ship-issue-pick.py tests/scripts/test_ship_issue_pick.py
git commit -m "feat(ship-issue): add pick.py — query, validate, claim

Lists open issues with status:ready + claude-ok via gh issue list, validates
eligibility per spec rules, picks lowest-numbered, claims (status:ready →
status:in-progress label swap + claim comment), and emits parameters for the
caller. Rebase-before-claim ordering ensures a rebase failure leaves no
half-claimed issue.

Unit tests cover the eligibility predicate. Full integration test against
a real repo lives in Plan B."
```

### Task A25: ship-issue-success.sh

**Files:**
- Create: `scripts/ship-issue-success.sh`

(Minimal tests for this script — it's mostly a sequence of git/gh calls. Plan B integration-tests it end-to-end.)

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
# ship-issue-success.sh — run when an issue's TDD slice completes successfully.
#
# 1. make ci   (full CI gate before push)
# 2. pd-push wip/ship-issue
# 3. gh pr create --draft (or gh pr edit body if PR exists and is draft)
#
# On make ci failure: invokes ship-issue-failure.sh and exits nonzero.
#
# Args: $1=ISSUE_NUMBER  $2=REPO  $3=PRE_CLAIM_SHA

set -euo pipefail

ISSUE="${1:?usage: ship-issue-success.sh ISSUE_NUMBER REPO PRE_CLAIM_SHA}"
REPO="${2:?missing REPO}"
PRE_SHA="${3:?missing PRE_CLAIM_SHA}"

WORKSPACE="${WORKSPACE_ROOT:-/workspaces/ocr-container}"

# Step 1: make ci
echo "▸ Running make ci..." >&2
CI_LOG="$(mktemp)"
trap 'rm -f "$CI_LOG"' EXIT
if ! make ci 2>&1 | tee "$CI_LOG" >&2; then
  CI_TAIL="$(tail -50 "$CI_LOG")"
  echo "✗ make ci failed; bouncing issue" >&2
  "$WORKSPACE/scripts/ship-issue-failure.sh" "$ISSUE" "$REPO" "$PRE_SHA" \
    "make ci failed: $CI_TAIL"
  exit 1
fi

# Step 2: push via pd-push
echo "▸ Pushing wip/ship-issue..." >&2
"$WORKSPACE/pd-push" wip/ship-issue --force-with-lease

# Step 3: open or update draft PR
echo "▸ Updating draft PR..." >&2

# Check if a draft PR for wip/ship-issue exists
PR_JSON="$(gh pr list -R "$REPO" --head wip/ship-issue --json number,isDraft --limit 1 || echo '[]')"
PR_NUMBER="$(echo "$PR_JSON" | python3 -c 'import json,sys; arr=json.load(sys.stdin); print(arr[0]["number"] if arr else "")')"
PR_IS_DRAFT="$(echo "$PR_JSON" | python3 -c 'import json,sys; arr=json.load(sys.stdin); print(arr[0]["isDraft"] if arr else "false")')"

# Build PR body (append-section style)
SECTION="$(cat <<EOF

---

### Issue #$ISSUE — $(date -u +"%Y-%m-%d %H:%M UTC")

Closes #$ISSUE
EOF
)"

if [[ -z "$PR_NUMBER" ]]; then
  # Create new draft PR
  gh pr create -R "$REPO" --draft \
    --title "ship-issue: rolling work" \
    --body "Auto-managed by ship-issue. Each successful run appends a section.$SECTION" \
    || { echo "✗ pr create failed" >&2; exit 1; }
  echo "✓ Created draft PR" >&2
elif [[ "$PR_IS_DRAFT" == "True" || "$PR_IS_DRAFT" == "true" ]]; then
  # Append to existing draft body
  CURRENT_BODY="$(gh pr view "$PR_NUMBER" -R "$REPO" --json body -q .body)"
  printf '%s%s' "$CURRENT_BODY" "$SECTION" | gh pr edit "$PR_NUMBER" -R "$REPO" --body-file -
  echo "✓ Updated draft PR #$PR_NUMBER" >&2
else
  # PR is no longer draft — locked. Don't touch.
  echo "ℹ PR #$PR_NUMBER is no longer draft; not modified" >&2
fi

echo "✓ ship-issue-success completed for #$ISSUE" >&2
```

- [ ] **Step 2: Make executable**

Run: `chmod +x scripts/ship-issue-success.sh`

- [ ] **Step 3: Smoke test (no real push possible without test repo)**

Run: `bash -c 'scripts/ship-issue-success.sh 2>&1 | head -5; true'`
Expected: prints usage error (no args). Exit code can be anything; we just want the script to be executable and parseable.

- [ ] **Step 4: Commit**

```bash
git add scripts/ship-issue-success.sh
git commit -m "feat(ship-issue): add success.sh — make ci + push + draft PR

Run when an issue's TDD slice completes. Runs full CI before push; on
CI failure, invokes ship-issue-failure.sh with the CI tail. On success,
pushes via pd-push, then either opens a new draft PR for wip/ship-issue
or appends a section to an existing draft. Treats non-draft PR as locked."
```

### Task A26: ship-issue-failure.sh

**Files:**
- Create: `scripts/ship-issue-failure.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
# ship-issue-failure.sh — bounce an issue when its slice cannot complete.
#
# 1. git reset --hard <pre-claim-sha>  (drops any commits made during the slice)
# 2. Swap status:in-progress → status:backlog (single-select discipline)
# 3. Strip claude-ok label
# 4. Post bounce comment with reason and pre-claim SHA
#
# Args: $1=ISSUE_NUMBER  $2=REPO  $3=PRE_CLAIM_SHA  $4=REASON

set -euo pipefail

ISSUE="${1:?usage: ship-issue-failure.sh ISSUE_NUMBER REPO PRE_CLAIM_SHA REASON}"
REPO="${2:?missing REPO}"
PRE_SHA="${3:?missing PRE_CLAIM_SHA}"
REASON="${4:-(no reason given)}"

# Step 1: reset
echo "▸ Resetting wip/ship-issue to pre-claim SHA $PRE_SHA" >&2
git reset --hard "$PRE_SHA" 2>&1 | tail -3 >&2 || true

# Step 2: swap status:in-progress → status:backlog (and strip claude-ok in the same call)
gh issue edit "$ISSUE" -R "$REPO" \
  --remove-label "status:in-progress" \
  --add-label    "status:backlog" \
  --remove-label "claude-ok" \
  2>&1 | tail -3 >&2 || true

# Step 3: bounce comment
gh issue comment "$ISSUE" -R "$REPO" --body "$(cat <<EOF
ship-issue: bounced.

**Reason:** $REASON

**Pre-claim SHA:** \`$PRE_SHA\` (work is recoverable from reflog if you want it)

The issue has been moved to \`status:backlog\` and \`claude-ok\` removed; re-add \`claude-ok\` and swap \`status:backlog\` → \`status:ready\` to retry.
EOF
)"

echo "✓ ship-issue-failure completed for #$ISSUE" >&2
```

- [ ] **Step 2: Make executable**

Run: `chmod +x scripts/ship-issue-failure.sh`

- [ ] **Step 3: Commit**

```bash
git add scripts/ship-issue-failure.sh
git commit -m "feat(ship-issue): add failure.sh — bounce issue cleanly

git reset --hard to pre-claim SHA, swap status:in-progress → status:backlog,
strip claude-ok label, post bounce comment with reason + recovery SHA. Used
both directly when a slice can't complete and indirectly by success.sh
when make ci fails."
```

### Task A27: ship-issue-orchestrator.sh

**Files:**
- Create: `scripts/ship-issue-orchestrator.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
# ship-issue-orchestrator.sh — outer loop for ship-issue.
#
# Wraps a number of issue cycles: throttle-check, pick, work (delegated
# to claude -p), success/failure handling.
#
# Usage: ship-issue-orchestrator.sh --repo ConcaveTrillion/<repo> [--runs N]

set -euo pipefail

REPO=""
RUNS=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --runs) RUNS="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 64 ;;
  esac
done

if [[ -z "$REPO" ]]; then
  echo "usage: ship-issue-orchestrator.sh --repo <owner/repo> [--runs N]" >&2
  exit 64
fi

WORKSPACE="${WORKSPACE_ROOT:-/workspaces/ocr-container}"

for ((i=1; i<=RUNS; i++)); do
  echo "═══ Run $i/$RUNS ═══" >&2

  if ! "$WORKSPACE/scripts/ship-issue-throttle-check.sh"; then
    echo "▸ Throttled; stopping" >&2
    break
  fi

  PICKED="$("$WORKSPACE/scripts/ship-issue-pick.py" --repo "$REPO" 2>&1 | tail -1)"
  if [[ "$PICKED" == "NONE" ]]; then
    echo "▸ No eligible issues" >&2
    break
  fi

  # Source the structured params (ISSUE=42 REPO=... etc.)
  eval "$PICKED"

  # Hand off to claude -p with the issue context
  echo "▸ Working issue #$ISSUE..." >&2
  if claude -p "/ship-issue-work $ISSUE $REPO $MODEL $MODEL_EFFORT $KIND $SPEC_PATH $ACCEPTANCE_JSON $PRE_CLAIM_SHA"; then
    "$WORKSPACE/scripts/ship-issue-success.sh" "$ISSUE" "$REPO" "$PRE_CLAIM_SHA" \
      || echo "✗ success.sh failed" >&2
  else
    "$WORKSPACE/scripts/ship-issue-failure.sh" "$ISSUE" "$REPO" "$PRE_CLAIM_SHA" \
      "TDD slice did not complete (claude -p returned nonzero)"
  fi
done

echo "═══ Orchestrator finished ═══" >&2
```

- [ ] **Step 2: Make executable + commit**

```bash
chmod +x scripts/ship-issue-orchestrator.sh
git add scripts/ship-issue-orchestrator.sh
git commit -m "feat(ship-issue): add orchestrator.sh outer loop

Wraps throttle-check + pick + claude -p (the TDD slice) + success/failure.
Used by ctask schedules and for --runs N batch runs."
```

---

## Phase 10 — Other workspace scripts

### Task A28: seed-labels.sh

**Files:**
- Create: `scripts/seed-labels.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
# seed-labels.sh REPO — idempotently create the standard label set on a repo.
#
# Run as: scripts/seed-labels.sh pdomain/pdomain-prep-for-pgdp

set -euo pipefail

REPO="${1:?usage: seed-labels.sh OWNER/REPO}"

# (label, color, description)
LABELS=(
  "kind:feature|0e8a16|New slice of planned work"
  "kind:bug|d73a4a|Reproducible incorrect behavior"
  "kind:spec|c5def5|Design/decision needed before code"
  "kind:chore|fef2c0|Deps, CI, refactor, doc cleanup"

  "effort:S|c2e0c6|Small / mechanical (haiku-suitable)"
  "effort:M|fbca04|Medium / standard (sonnet-suitable)"
  "effort:L|d93f0b|Large / architectural (opus-suitable)"

  "model:haiku|fef2c0|Recommend Claude Haiku"
  "model:sonnet|fbca04|Recommend Claude Sonnet"
  "model:opus|d93f0b|Recommend Claude Opus"

  "model-effort:low|d4c5f9|effort=low"
  "model-effort:medium|c5def5|effort=medium"
  "model-effort:high|bfd4f2|effort=high"
  "model-effort:xhigh|0052cc|effort=xhigh (Opus only)"
  "model-effort:max|003366|effort=max"

  "recurring:weekly|c2e0c6|Recurring chore, weekly cadence"
  "recurring:monthly|fef2c0|Recurring chore, monthly cadence"
  "recurring:quarterly|fbca04|Recurring chore, quarterly cadence"

  # status:* — workflow state. Single-select by convention; tooling that
  # transitions state must remove existing status:* labels before adding new one.
  "status:backlog|ededed|Workflow: not yet ready to work on"
  "status:ready|0e8a16|Workflow: queued for ship-issue (with claude-ok) or you"
  "status:in-progress|fbca04|Workflow: currently being worked on"
  "status:done|c2e0c6|Workflow: shipped (auto-applied by ship-issue on close)"
  "status:blocked|d93f0b|Workflow: blocked on external dependency or decision"

  "claude-ok|0e8a16|Mutation gate — agent may modify this issue"
  "triage:tracking|d4c5f9|Internal tracking issue for an external user report"
)

for entry in "${LABELS[@]}"; do
  IFS='|' read -r name color desc <<< "$entry"
  if gh label list -R "$REPO" --limit 200 --json name | grep -q "\"$name\""; then
    echo "  ✓ $name (exists)"
  else
    gh label create "$name" -R "$REPO" --color "$color" --description "$desc" \
      && echo "  + $name"
  fi
done

echo "Done. To create per-repo area:* labels, edit this script or use gh manually."
```

- [ ] **Step 2: Make executable + commit**

```bash
chmod +x scripts/seed-labels.sh
git add scripts/seed-labels.sh
git commit -m "feat(scripts): add seed-labels.sh (idempotent label seeding)"
```

### Task A29: (removed — see design pivot)

The original Task A29 (`seed-project.py`) created per-repo Project boards with
a Status field. The 2026-05-09 design pivot replaced Project-board status with
a `status:*` label family because user-owned PATs have no Projects scope.
`seed-labels.sh` (Task A28) now seeds the status labels directly, and no
Project board is created. Skip this task; downstream task numbers are kept
stable for traceability.

### Task A30: lint-spec.py

**Files:**
- Create: `tests/scripts/test_lint_spec.py`
- Create: `scripts/lint-spec.py`

- [ ] **Step 1: Write tests**

```python
# tests/scripts/test_lint_spec.py
"""Tests for lint-spec.py."""
import os
import subprocess
import tempfile
from pathlib import Path
from textwrap import dedent

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/lint-spec.py"


def write_spec(content: str, name: str = "test.md") -> Path:
    tmpdir = Path(tempfile.mkdtemp())
    path = tmpdir / name
    path.write_text(dedent(content).lstrip())
    return path


def lint(path: Path, extra_args: list[str] = None) -> tuple[int, str, str]:
    args = ["python3", str(SCRIPT), str(path)] + (extra_args or [])
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


CONFORMING_SPEC = """\
    # Test spec

    > **Status**: Active
    > **Last updated**: 2026-05-09

    ## TL;DR

    Two sentences.

    ## Context

    Why.

    ## Constraints

    - none

    ## Decision

    The design.

    ## Contract / Acceptance

    - [ ] one
    - [ ] two

    ## Trade-offs considered

    | A | B |
    |---|---|

    ## Consequences

    Whatever.

    ## Open questions

    None.

    ## References

    None.
"""


def test_conforming_spec_passes():
    spec = write_spec(CONFORMING_SPEC)
    rc, _, _ = lint(spec)
    assert rc == 0


def test_missing_heading_fails():
    bad = CONFORMING_SPEC.replace("## Trade-offs considered\n", "")
    spec = write_spec(bad)
    rc, _, err = lint(spec)
    assert rc != 0
    assert "Trade-offs" in err or "missing" in err.lower()


def test_no_status_header_fails():
    bad = CONFORMING_SPEC.replace("> **Status**: Active\n", "")
    spec = write_spec(bad)
    rc, _, err = lint(spec)
    assert rc != 0
    assert "status" in err.lower()


def test_missing_last_updated_fails():
    bad = CONFORMING_SPEC.replace("> **Last updated**: 2026-05-09\n", "")
    spec = write_spec(bad)
    rc, _, err = lint(spec)
    assert rc != 0


def test_seed_legacy_writes_specrc():
    """--seed-legacy mode walks docs/specs/ and writes .specrc:legacy."""
    tmpdir = Path(tempfile.mkdtemp())
    specs = tmpdir / "docs" / "specs"
    specs.mkdir(parents=True)
    (specs / "01-conforming.md").write_text(dedent(CONFORMING_SPEC).lstrip())
    bad = CONFORMING_SPEC.replace("## Trade-offs considered\n", "")
    (specs / "02-legacy.md").write_text(dedent(bad).lstrip())

    rc, _, _ = lint(specs, extra_args=["--seed-legacy"])
    assert rc == 0
    rc_path = specs / ".specrc"
    assert rc_path.exists()
    content = rc_path.read_text()
    assert "02-legacy.md" in content
    assert "01-conforming.md" not in content
```

- [ ] **Step 2: Run tests (red)**

Run: `uv run pytest tests/scripts/test_lint_spec.py -v 2>&1 | tail -10`
Expected: fail.

- [ ] **Step 3: Commit tests**

```bash
git add tests/scripts/test_lint_spec.py
git commit -m "test: add lint-spec tests (red)"
```

### Task A31: Implement lint-spec.py

**Files:**
- Create: `scripts/lint-spec.py`

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""lint-spec.py — validate spec files against the 9-section template.

Rules:
1. All 9 required ## headings present (gated by .specrc:legacy allowlist)
2. Status blockquote present and valid
3. Last updated date present
4. File length within .specrc cap (default 800 lines)
5. TL;DR ≤ 6 lines (warn-only by default)
6. Anchor stability: existing ## headings cannot be renamed/removed (always enforced)

Usage:
    lint-spec.py <file>...                    # lint specific files
    lint-spec.py --seed-legacy <docs/specs>   # populate .specrc:legacy
    lint-spec.py --no-legacy <file>           # ignore .specrc:legacy
"""
from __future__ import annotations
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REQUIRED_HEADINGS = [
    "TL;DR",
    "Context",
    "Constraints",
    "Decision",
    "Contract / Acceptance",
    "Trade-offs considered",
    "Consequences",
    "Open questions",
    "References",
]

DEFAULT_CAP_LINES = 800


def parse_specrc(specs_dir: Path) -> dict:
    rc = specs_dir / ".specrc"
    if not rc.exists():
        return {"legacy": [], "cap_lines": {}}
    legacy = []
    cap_lines = {}
    section = None
    for line in rc.read_text().splitlines():
        stripped = line.strip()
        if stripped == "legacy:":
            section = "legacy"
            continue
        if stripped == "cap_lines:":
            section = "cap_lines"
            continue
        if section == "legacy" and stripped.startswith("- "):
            legacy.append(stripped[2:])
        elif section == "cap_lines" and ":" in stripped:
            k, v = stripped.split(":", 1)
            try:
                cap_lines[k.strip()] = int(v.strip())
            except ValueError:
                pass
    return {"legacy": legacy, "cap_lines": cap_lines}


def check_status_header(content: str) -> str | None:
    if re.search(r"^>\s*\*\*Status\*\*:\s*(Draft|Active|Locked|Superseded)",
                 content, re.MULTILINE):
        return None
    return "missing or invalid Status header (expected `> **Status**: Draft|Active|Locked|Superseded by ...`)"


def check_last_updated(content: str) -> str | None:
    if re.search(r"^>\s*\*\*Last updated\*\*:\s*\d{4}-\d{2}-\d{2}",
                 content, re.MULTILINE):
        return None
    return "missing or invalid Last updated header"


def check_required_headings(content: str) -> list[str]:
    missing = []
    for h in REQUIRED_HEADINGS:
        # Match ## followed by the heading; allow trailing whitespace
        pattern = rf"^##\s+{re.escape(h)}\s*$"
        if not re.search(pattern, content, re.MULTILINE):
            missing.append(h)
    return missing


def check_length_cap(path: Path, content: str, cap_overrides: dict) -> str | None:
    n = content.count("\n") + 1
    cap = cap_overrides.get(path.name, cap_overrides.get("default", DEFAULT_CAP_LINES))
    if n > cap:
        return f"length {n} exceeds cap {cap} (consider splitting via fixing-specs Procedure 4)"
    return None


def check_tldr_brevity(content: str) -> str | None:
    m = re.search(r"^##\s*TL;DR\s*\n(.*?)(?=\n##|\Z)",
                  content, re.MULTILINE | re.DOTALL)
    if not m:
        return None
    body = m.group(1).strip()
    if not body:
        return "TL;DR section is empty"
    n_lines = len([l for l in body.splitlines() if l.strip()])
    if n_lines > 6:
        return f"TL;DR has {n_lines} non-empty lines (>6); trim it"
    return None


def check_anchor_stability(path: Path, content: str) -> str | None:
    """Compare current ## headings to HEAD's version of this file.

    Pass if no HEAD version exists (file is new).
    Fail if any ## heading present in HEAD is missing in current.
    """
    try:
        head_content = subprocess.run(
            ["git", "show", f"HEAD:{path}"],
            capture_output=True, text=True, cwd=path.parent,
        ).stdout
    except Exception:
        return None
    if not head_content:
        return None
    current_headings = set(re.findall(r"^##\s+(.+?)\s*$", content, re.MULTILINE))
    head_headings = set(re.findall(r"^##\s+(.+?)\s*$", head_content, re.MULTILINE))
    missing = head_headings - current_headings
    if missing:
        return (f"anchor stability violation — heading(s) present at HEAD but missing now: "
                f"{sorted(missing)}. Renaming breaks Spec: pointers in issues. "
                f"Restore the heading or split the spec via fixing-specs Procedure 4.")
    return None


def lint_file(path: Path, specrc: dict, no_legacy: bool = False) -> list[str]:
    if not path.exists():
        return [f"file not found: {path}"]
    content = path.read_text()
    errors = []

    # Rule 1: required headings (legacy-skippable)
    is_legacy = path.name in specrc.get("legacy", [])
    if is_legacy and not no_legacy:
        # Legacy spec — skip required heading check; print warning
        sys.stderr.write(f"WARN: {path.name} is in .specrc:legacy; Rule 1 skipped\n")
    else:
        missing = check_required_headings(content)
        if missing:
            errors.append(f"Rule 1: missing required heading(s): {missing}")

    # Rule 2: status header
    err = check_status_header(content)
    if err:
        errors.append(f"Rule 2: {err}")

    # Rule 3: last updated
    err = check_last_updated(content)
    if err:
        errors.append(f"Rule 3: {err}")

    # Rule 4: length cap
    err = check_length_cap(path, content, specrc.get("cap_lines", {}))
    if err:
        errors.append(f"Rule 4: {err}")

    # Rule 5: TL;DR brevity
    err = check_tldr_brevity(content)
    if err:
        sys.stderr.write(f"WARN ({path.name}): Rule 5: {err}\n")

    # Rule 6: anchor stability (always)
    err = check_anchor_stability(path, content)
    if err:
        errors.append(f"Rule 6: {err}")

    return errors


def seed_legacy(specs_dir: Path) -> None:
    rc_path = specs_dir / ".specrc"
    legacy = []
    for p in sorted(specs_dir.glob("*.md")):
        if p.name.startswith("_"):
            continue
        content = p.read_text()
        # Heuristic: if Rule 1 fails, mark as legacy
        if check_required_headings(content):
            legacy.append(p.name)

    body = "# Spec lint config (auto-generated by lint-spec.py --seed-legacy)\n\n"
    body += "legacy:\n"
    if legacy:
        body += "\n".join(f"  - {n}" for n in legacy) + "\n"
    body += "\ncap_lines:\n  default: 800\n"
    rc_path.write_text(body)
    print(f"Wrote {rc_path} with {len(legacy)} legacy spec(s)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="file(s) or directory")
    parser.add_argument("--no-legacy", action="store_true")
    parser.add_argument("--seed-legacy", action="store_true")
    args = parser.parse_args()

    if args.seed_legacy:
        for d in args.paths:
            p = Path(d)
            if p.is_file():
                p = p.parent
            seed_legacy(p)
        sys.exit(0)

    rc = 0
    for path_str in args.paths:
        path = Path(path_str)
        if path.is_dir():
            files = list(path.glob("*.md"))
        else:
            files = [path]
        for f in files:
            if f.name.startswith("_"):
                continue
            specs_dir = f.parent
            specrc = parse_specrc(specs_dir)
            errors = lint_file(f, specrc, no_legacy=args.no_legacy)
            if errors:
                rc = 1
                for e in errors:
                    sys.stderr.write(f"{f}: {e}\n")
    sys.exit(rc)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make executable**

Run: `chmod +x scripts/lint-spec.py`

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/scripts/test_lint_spec.py -v 2>&1 | tail -10`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add scripts/lint-spec.py
git commit -m "feat(scripts): add lint-spec.py (6-rule spec validator)

Implements all 6 rules from the spec design: required headings (legacy-
skippable), status header, last updated, length cap, TL;DR brevity, and
anchor stability (always enforced).

Supports --seed-legacy mode for initial allowlist population, and
--no-legacy for migration verification."
```

### Task A32: build-spec-index.py + file-legacy-migration-issues.py + migrate-legacy-spec-auto.py

These three scripts are smaller. Bundle them into one task.

**Files:**
- Create: `scripts/build-spec-index.py`
- Create: `scripts/file-legacy-migration-issues.py`
- Create: `scripts/migrate-legacy-spec-auto.py`

- [ ] **Step 1: build-spec-index.py**

```python
#!/usr/bin/env python3
"""build-spec-index.py — generate a workspace-level spec index.

Walks all pd-*/docs/specs/*.md files, extracts Status + TL;DR, writes
~/spec-index.html (or path from --out).
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path
from textwrap import dedent

WORKSPACE = Path("/workspaces/ocr-container")


def parse_spec(path: Path) -> dict:
    content = path.read_text()
    status = re.search(r"^>\s*\*\*Status\*\*:\s*(\S.*?)\s*$", content, re.MULTILINE)
    tldr_match = re.search(r"^##\s*TL;DR\s*\n(.*?)(?=\n##|\Z)",
                           content, re.MULTILINE | re.DOTALL)
    tldr = tldr_match.group(1).strip()[:200] if tldr_match else ""
    return {"status": status.group(1) if status else "(no status)", "tldr": tldr}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(Path.home() / "spec-index.html"))
    args = parser.parse_args()

    rows = []
    for spec_dir in sorted(WORKSPACE.glob("pd-*/docs/specs")):
        for spec in sorted(spec_dir.glob("*.md")):
            if spec.name.startswith("_"):
                continue
            try:
                meta = parse_spec(spec)
            except Exception:
                continue
            rel = spec.relative_to(WORKSPACE)
            rows.append((str(rel), meta["status"], meta["tldr"]))

    html = dedent(f"""\
        <!DOCTYPE html>
        <html><head><meta charset="UTF-8"><title>Spec index</title>
        <style>
        body {{ font-family: -apple-system, "Segoe UI", sans-serif;
               max-width: 1200px; margin: 2em auto; padding: 0 1em; }}
        table {{ border-collapse: collapse; width: 100%; font-size: 0.9em; }}
        th, td {{ padding: 6px 10px; border-bottom: 1px solid #eee; }}
        th {{ background: #f0f0f0; text-align: left; }}
        .Active {{ color: #2a7; font-weight: 600; }}
        .Draft {{ color: #888; }}
        .Locked {{ color: #28b; }}
        </style></head><body>
        <h1>Spec index ({len(rows)} specs)</h1>
        <table>
        <tr><th>Path</th><th>Status</th><th>TL;DR</th></tr>
        """)
    for path, status, tldr in rows:
        css = status.split()[0] if status else ""
        html += f"<tr><td><code>{path}</code></td><td class='{css}'>{status}</td>" \
                f"<td>{tldr}</td></tr>\n"
    html += "</table></body></html>\n"

    out = Path(args.out)
    out.write_text(html)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: migrate-legacy-spec-auto.py (mechanical Procedure 1)**

```python
#!/usr/bin/env python3
"""migrate-legacy-spec-auto.py — apply Procedure 1 mechanically.

Inserts missing required headings as `_(none)_` placeholders, sets
Status header if missing, sets Last updated to today.
"""
from __future__ import annotations
import argparse
import re
import sys
from datetime import date
from pathlib import Path

REQUIRED_HEADINGS = [
    "TL;DR", "Context", "Constraints", "Decision",
    "Contract / Acceptance", "Trade-offs considered",
    "Consequences", "Open questions", "References",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    content = path.read_text()
    today = date.today().isoformat()

    # Status header (insert at top if missing)
    if not re.search(r"^>\s*\*\*Status\*\*:", content, re.MULTILINE):
        content = (f"> **Status**: Active\n"
                   f"> **Last updated**: {today}\n\n") + content
    elif not re.search(r"^>\s*\*\*Last updated\*\*:", content, re.MULTILINE):
        content = re.sub(
            r"(>\s*\*\*Status\*\*:.*\n)",
            rf"\1> **Last updated**: {today}\n",
            content, count=1,
        )

    # Add missing required headings at the end (placeholder bodies)
    for h in REQUIRED_HEADINGS:
        if not re.search(rf"^##\s+{re.escape(h)}\s*$", content, re.MULTILINE):
            content += f"\n## {h}\n\n_(none)_\n"

    path.write_text(content)
    print(f"Migrated {path} (mechanical Procedure 1)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: file-legacy-migration-issues.py**

```python
#!/usr/bin/env python3
"""file-legacy-migration-issues.py — fan out chore issues per legacy spec.

For each path listed in <REPO>/docs/specs/.specrc:legacy:
- run scripts/lint-spec.py --no-legacy to capture failing rules
- classify auto-runnable vs human-required
- file a chore issue with appropriate labels (claude-ok if auto-runnable)
"""
from __future__ import annotations
import argparse
import re
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_path", help="local repo path (where docs/specs/.specrc lives)")
    parser.add_argument("--repo", required=True, help="OWNER/REPO for gh")
    parser.add_argument("--auto-only", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    repo_path = Path(args.repo_path)
    specrc = repo_path / "docs/specs/.specrc"
    if not specrc.exists():
        sys.stderr.write(f"No .specrc at {specrc}\n")
        sys.exit(2)

    # Parse legacy list
    legacy = []
    in_legacy = False
    for line in specrc.read_text().splitlines():
        stripped = line.strip()
        if stripped == "legacy:":
            in_legacy = True
            continue
        if in_legacy and stripped.startswith("- "):
            legacy.append(stripped[2:])
        elif in_legacy and stripped and not stripped.startswith("-"):
            in_legacy = False

    print(f"Found {len(legacy)} legacy spec(s)")

    for spec_name in legacy:
        spec_path = repo_path / "docs/specs" / spec_name
        if not spec_path.exists():
            print(f"  ⚠ {spec_name} not found; skipping")
            continue

        # Lint with --no-legacy to capture failures
        result = subprocess.run(
            ["python3", str(WORKSPACE / "scripts/lint-spec.py"),
             "--no-legacy", str(spec_path)],
            capture_output=True, text=True,
        )
        failures = result.stderr.strip()

        n_lines = spec_path.read_text().count("\n") + 1
        # Classification: if Rule 4 fails (length cap), human-required
        is_human = "Rule 4:" in failures
        classification = "human-required" if is_human else "auto-runnable"

        if args.auto_only and is_human:
            print(f"  → skip {spec_name} (human-required)")
            continue
        if not args.auto_only and not args.all:
            print(f"  → skip {spec_name} (use --auto-only or --all)")
            continue

        # Build the issue body
        body = (
            f"## Routine\n\n"
            f"Migrate this legacy spec to the standard 9-section template.\n\n"
            f"Spec: docs/specs/{spec_name}\n"
            f"Current size: {n_lines} lines\n"
            f"Classification: {classification}\n"
            f"Lint failures (from `scripts/lint-spec.py --no-legacy`):\n```\n{failures}\n```\n\n"
            f"## Procedure\n\n"
            f"Invoke the `fixing-specs` skill. "
            f"Apply Procedure {'4' if is_human else '1'} as classified above.\n\n"
            f"## Acceptance\n\n"
            f"- [ ] All 9 required headings present\n"
            f"- [ ] Status header set\n"
            f"- [ ] Last updated set to today\n"
            f"- [ ] If split: forwarding stub at original path; references updated\n"
            f"- [ ] `scripts/lint-spec.py --no-legacy` passes for the spec\n"
            f"- [ ] Spec path removed from docs/specs/.specrc:legacy\n\n"
            f"## When done\n\n"
            f"Close this issue. The spec is no longer legacy.\n"
        )

        labels = ["kind:chore", "area:docs"]
        if is_human:
            labels.extend(["effort:M", "model:sonnet", "model-effort:medium"])
        else:
            labels.extend(["effort:S", "model:haiku", "model-effort:low", "claude-ok"])

        gh_args = [
            "gh", "issue", "create", "-R", args.repo,
            "--title", f"Migrate legacy spec: docs/specs/{spec_name}",
            "--body", body,
        ]
        for lbl in labels:
            gh_args.extend(["--label", lbl])

        result = subprocess.run(gh_args, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✓ {classification}: filed for {spec_name}")
        else:
            print(f"  ✗ failed: {result.stderr.strip()}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Make all executable + commit**

```bash
chmod +x scripts/build-spec-index.py scripts/migrate-legacy-spec-auto.py scripts/file-legacy-migration-issues.py
git add scripts/build-spec-index.py scripts/migrate-legacy-spec-auto.py scripts/file-legacy-migration-issues.py
git commit -m "feat(scripts): add build-spec-index, migrate-legacy-spec-auto, file-legacy-migration-issues

- build-spec-index: generates workspace-level HTML index of all specs
- migrate-legacy-spec-auto: mechanical Procedure 1 migration
- file-legacy-migration-issues: fan-out chore creator with auto-vs-human
  classification (claude-ok applied only on auto-runnable)"
```

### Task A33: tooling-change-guard.sh + verify-protections.sh

**Files:**
- Create: `scripts/tooling-change-guard.sh`
- Create: `scripts/verify-protections.sh`

- [ ] **Step 1: tooling-change-guard.sh**

```bash
#!/usr/bin/env bash
# tooling-change-guard.sh — pre-commit hook
# Rejects commits modifying enforcement paths unless the commit message
# contains [tooling-change-approved].
#
# Run as a pre-commit hook with files=^(<enforcement paths>) filter.

set -euo pipefail

PROTECTED_PATTERNS=(
  "^\.claude/hooks/"
  "^\.claude/settings\.json"
  "^\.claude/skills/"
  "^\.claude/agents/"
  "^pd-push$"
  "^scripts/"
  "^\.devcontainer/"
)

# Get staged files
STAGED="$(git diff --cached --name-only)"
TOUCHED_PROTECTED=""
for f in $STAGED; do
  for pat in "${PROTECTED_PATTERNS[@]}"; do
    if [[ "$f" =~ $pat ]]; then
      TOUCHED_PROTECTED+="$f"$'\n'
      break
    fi
  done
done

if [[ -z "$TOUCHED_PROTECTED" ]]; then
  exit 0  # nothing protected staged
fi

# Check the commit message (passed by pre-commit framework via $1, or use COMMIT_EDITMSG)
COMMIT_MSG_FILE="${1:-.git/COMMIT_EDITMSG}"
if [[ ! -f "$COMMIT_MSG_FILE" ]]; then
  COMMIT_MSG=""
else
  COMMIT_MSG="$(cat "$COMMIT_MSG_FILE")"
fi

if [[ "$COMMIT_MSG" == *"[tooling-change-approved]"* ]]; then
  echo "tooling-change-guard: marker present, allowing"
  exit 0
fi

echo "tooling-change-guard: ERROR — staged commit modifies enforcement paths:" >&2
echo "$TOUCHED_PROTECTED" | sed 's/^/  - /' >&2
echo "" >&2
echo "Add the marker '[tooling-change-approved]' to the commit message" >&2
echo "if this is intentional. Otherwise revert the staged enforcement-path changes." >&2
exit 1
```

- [ ] **Step 2: verify-protections.sh**

```bash
#!/usr/bin/env bash
# verify-protections.sh — confirm claude-bot cannot modify enforcement files.
#
# Usage: bash scripts/verify-protections.sh
# Must be run as vscode (the script sudos to claude-bot for the test).

set -euo pipefail

PATHS=(
  ".claude/hooks/bash-command-guard.py"
  ".claude/settings.json"
  "pd-push"
  "scripts/lint-spec.py"
  "scripts/ship-issue-pick.py"
)

WORKSPACE="${WORKSPACE_ROOT:-/workspaces/ocr-container}"
cd "$WORKSPACE"

FAILURES=0

for p in "${PATHS[@]}"; do
  if [[ ! -e "$p" ]]; then
    echo "  ⚠ $p does not exist; skipping"
    continue
  fi
  # Try writing as claude-bot — should fail (EPERM)
  if sudo -u claude-bot bash -lc "echo test >> '$WORKSPACE/$p'" 2>/dev/null; then
    echo "  ✗ FAIL: claude-bot was able to write to $p (security gap)"
    # Roll back the test write
    sudo bash -c "head -n -1 '$p' > /tmp/restore.tmp && mv /tmp/restore.tmp '$p'" || true
    FAILURES=$((FAILURES + 1))
  else
    echo "  ✓ $p — claude-bot correctly denied write"
  fi
done

# Also verify claude-bot CAN execute pd-push and bash-command-guard
if sudo -u claude-bot bash -lc "test -x '$WORKSPACE/pd-push'"; then
  echo "  ✓ pd-push — claude-bot can execute"
else
  echo "  ✗ FAIL: claude-bot cannot execute pd-push"
  FAILURES=$((FAILURES + 1))
fi

if [[ $FAILURES -eq 0 ]]; then
  echo ""
  echo "All protection checks passed."
  exit 0
else
  echo ""
  echo "$FAILURES check(s) failed. Re-run the lockdown step (Task A60)."
  exit 1
fi
```

- [ ] **Step 3: Make executable + commit**

```bash
chmod +x scripts/tooling-change-guard.sh scripts/verify-protections.sh
git add scripts/tooling-change-guard.sh scripts/verify-protections.sh
git commit -m "feat(scripts): add tooling-change-guard + verify-protections

- tooling-change-guard.sh: pre-commit hook rejecting unmarked enforcement
  path changes (requires [tooling-change-approved] in commit message)
- verify-protections.sh: end-to-end test that claude-bot cannot modify
  enforcement files; runs after lockdown (Task A60)."
```

---

## Phase 11 — ship-issue and fixing-specs skills

### Task A34: ship-issue skill

**Files:**
- Create: `.claude/skills/ship-issue/SKILL.md`

- [ ] **Step 1: Write the skill**

````markdown
---
name: ship-issue
description: Ship one issue end-to-end (claim, TDD slice, commit, success/fail). Use when the user invokes `/ship-issue` or when ctask schedules an unattended run. Delegates procedural work to `scripts/ship-issue-*`; agent only does the TDD slice itself.
---

# ship-issue

Ship one eligible issue end-to-end. The agent's job is to write the failing tests, implement the slice, and verify with `make fast-check`. Procedural glue is in workspace scripts.

## Required arguments

The skill is invoked from `scripts/ship-issue-orchestrator.sh`, which provides:

```
ISSUE=<num> REPO=<owner/repo> MODEL=<haiku|sonnet|opus>
MODEL_EFFORT=<low|medium|high|xhigh|max> KIND=<feature|bug|spec|chore>
SPEC_PATH=<path-or-empty> ACCEPTANCE_JSON=/tmp/...
PRE_CLAIM_SHA=<sha>
```

## Workflow

1. If `SPEC_PATH` is non-empty: Read it (use the `Read` tool, not bash `cat`).

2. Read the acceptance criteria from `ACCEPTANCE_JSON` (a JSON array of strings).

3. For each acceptance bullet, run a TDD slice:
   - Write a failing test that asserts the behavior described by the bullet.
   - Run the test (`uv run pytest ...` or repo-equivalent). Confirm it fails for the right reason.
   - Implement the smallest code change that makes the test pass.
   - Run the test. Confirm it passes.
   - Run `make fast-check` to verify lint + types + impacted tests still pass.
   - If `make fast-check` fails: revert the last commit, debug, retry.
   - When green: `git commit -m "issue #$ISSUE: <slice>"`. The final slice's commit body adds `Closes #$ISSUE`.

4. After all acceptance bullets are green:
   - Verify locally: all tests pass, all bullets are checked.
   - Exit with status 0. The orchestrator runs `scripts/ship-issue-success.sh` next, which runs `make ci` and pushes.

5. If any bullet cannot be completed (test stays failing after multiple attempts; the spec is wrong; the slice depends on something unimplemented):
   - Exit with status 1, with a one-paragraph reason on stderr.
   - The orchestrator runs `scripts/ship-issue-failure.sh` to bounce the issue.

## Constraints

- **Do not modify enforcement files** (`.claude/hooks/`, `.claude/settings.json`, `scripts/`, `pd-push`, `.devcontainer/`). They are read-only to the bot user; attempted writes will fail. If you need a tooling change, file a separate `kind:chore` issue.
- **Do not push or create PRs.** That's `ship-issue-success.sh`'s job.
- **Do not run `gh pr create` or `git push` directly.** Use `pd-push` only via `ship-issue-success.sh`.
- **Do not add new dependencies** (`uv add`, `pnpm add`, `cargo add`). The hook will deny these. If the slice genuinely needs a new dep, bounce with that as the reason.
- **Acceptance bullets are the contract.** Don't expand scope. If the spec section says "out of scope: X," respect it.

## Anti-patterns

- Skipping `make fast-check` between commits — small breakages compound.
- Implementing without a failing test first — TDD discipline is the slice's quality gate.
- Editing acceptance criteria mid-slice — that's renegotiating the contract; bounce instead.
- Asking the user to approve changes — this is unattended; if you need approval, bounce.
````

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/ship-issue/SKILL.md
git commit -m "feat(skills): add ship-issue thin orchestrator skill

~80-line skill that delegates procedural steps to scripts/. Agent's job
is the TDD slice itself; everything else is in scripts/ship-issue-*.

Documents constraints (no enforcement-file mods, no direct pushes, no
novel deps) and anti-patterns."
```

### Task A35: fixing-specs skill

**Files:**
- Create: `.claude/skills/fixing-specs/SKILL.md`

- [ ] **Step 1: Write the skill**

````markdown
---
name: fixing-specs
description: Use when a pre-commit lint-spec failure blocks a commit, or when a spec has grown past 800 lines and needs splitting. Walks through 5 fix procedures including spec splitting with reference repair.
---

# Fixing specs

## Decision tree

1. Read the lint failure output. Identify which rule(s) failed.
2. For each failure, follow the matching procedure below.
3. Re-run `scripts/lint-spec.py <file>` to verify before committing.

## Procedure 1 — Missing required heading (Rule 1)

The 9 required headings are: TL;DR, Context, Constraints, Decision, Contract / Acceptance, Trade-offs considered, Consequences, Open questions, References.

If a section genuinely has no content yet, leave the heading and write `_(none)_` underneath. Do not omit the heading.

For mechanical migration (placeholder insertion + Status + Last updated), use:

```bash
python3 /workspaces/ocr-container/scripts/migrate-legacy-spec-auto.py <path>
```

## Procedure 2 — Heading renamed or removed (Rule 6)

Renaming is forbidden. The heading must be restored to its previous name.

If the rename was intentional because the spec is being restructured, that is a SPLIT, not a rename. Go to Procedure 4.

To find what the heading was at HEAD:

```bash
git show HEAD:docs/specs/<file>.md | grep '^##'
```

## Procedure 3 — TL;DR too long (Rule 5, warning)

Trim TL;DR to 2-4 sentences. The full context belongs in `## Context`. TL;DR is a "decide whether to keep reading" hook, not a summary.

## Procedure 4 — Spec too long (Rule 4) → SPLIT

The spec must be split. This is the high-risk path because it can break `Spec:` references in issues, code, and other specs.

### Step 4.1 — Identify split axes

Group `## Decision` subsections. Common axes: by component (routes / storage / model), by milestone (M2-decisions / M3-decisions), by concern (data-model / API / lifecycle).

### Step 4.2 — Plan new file names

Original: `02-backend.md`
Split: `02a-backend-routes.md`, `02b-backend-storage.md`, `02c-backend-model.md`

The original becomes a forwarding stub.

### Step 4.3 — Find all references

```bash
grep -rn 'docs/specs/02-backend\.md' \
  --include='*.md' --include='*.py' --include='*.ts' \
  /workspaces/ocr-container

# Plus open issues
gh issue list -R <repo> --search "02-backend.md"
```

### Step 4.4 — Create new spec files

Each new file has all 9 required headings. Add `Split from: 02-backend.md` in References.

### Step 4.5 — Replace original with forwarding stub

```markdown
# Backend (split)

> **Status**: Superseded by 02a-backend-routes.md, 02b-backend-storage.md, 02c-backend-model.md
> **Last updated**: YYYY-MM-DD

This spec was split on YYYY-MM-DD. See:
- Routes → [02a-backend-routes.md](02a-backend-routes.md)
- Storage → [02b-backend-storage.md](02b-backend-storage.md)
- Model → [02c-backend-model.md](02c-backend-model.md)

## TL;DR
_Split into three files; see above._
## Context
_Split into three files; see above._
## Constraints
_Split into three files; see above._
## Decision
_Split into three files; see above._
## Contract / Acceptance
_Split into three files; see above._
## Trade-offs considered
_Split into three files; see above._
## Consequences
_Split into three files; see above._
## Open questions
_Split into three files; see above._
## References
- 02a-backend-routes.md
- 02b-backend-storage.md
- 02c-backend-model.md
```

The forwarding stub keeps every existing `Spec:` pointer working.

### Step 4.6 — Update high-value references (optional)

For issues whose `Spec:` lines pointed at specific subsections that moved, update them. Code-comment references too. The stub catches everything else.

### Step 4.7 — Verify

```bash
scripts/lint-spec.py docs/specs/02a-backend-routes.md \
                     docs/specs/02b-backend-storage.md \
                     docs/specs/02c-backend-model.md \
                     docs/specs/02-backend.md
git add docs/specs/02*.md
git commit -m "spec: split 02-backend.md into routes/storage/model"
```

## Procedure 5 — Removing a spec from the legacy allowlist

After fully migrating a legacy spec to the template:

1. Verify all 9 required headings are present.
2. Run `scripts/lint-spec.py --no-legacy <file>` and confirm Rule 1 passes.
3. Edit `docs/specs/.specrc` and delete the file's line under `legacy:`.
4. Commit both the spec and `.specrc` together.

## Anti-patterns

- Renaming headings to "tidy up" — Rule 6 will reject and `Spec:` references will rot.
- Combining specs by deleting one and merging into another — same anchor-rot problem.
- Skipping the forwarding stub when splitting — older issues will orphan.
- Splitting mid-slice when the slice's purpose isn't a split — file a separate `kind:chore` issue for the split work and bounce the current slice.
````

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/fixing-specs/SKILL.md
git commit -m "feat(skills): add fixing-specs skill (5 procedures)

Walks through: missing heading insert, restore renamed/removed heading,
TL;DR trim, spec split (with reference-repair forwarding-stub pattern),
remove from legacy allowlist."
```

---

## Phase 12 — Lockdown + verification

### Task A36: Apply lockdown — chown enforcement paths

**Files:** ownership change on multiple paths (no file content changes)

- [ ] **Step 1: Apply chown sequence**

Run:
```bash
PROTECTED=(
  .claude/hooks
  .claude/settings.json
  .claude/skills
  .claude/agents
  pd-push
  scripts
  .devcontainer
)
for p in "${PROTECTED[@]}"; do
  if [[ -e "/workspaces/ocr-container/$p" ]]; then
    sudo chown -R vscode:vscode "/workspaces/ocr-container/$p"
    sudo chmod -R go-w "/workspaces/ocr-container/$p"
  fi
done
```

- [ ] **Step 2: Verify ownership**

Run: `ls -ld /workspaces/ocr-container/.claude/hooks /workspaces/ocr-container/pd-push /workspaces/ocr-container/scripts`
Expected: each shows owner `vscode`, group `vscode`, mode without group/other write (`-rw-r--r--` or `drwxr-xr-x`).

- [ ] **Step 3: Run verify-protections.sh**

Run: `scripts/verify-protections.sh`
Expected: every check passes ("All protection checks passed.").

If any check fails, re-run the chown loop and fix.

- [ ] **Step 4: Commit a marker file documenting the lockdown**

(There's no file change to commit; the chown sequence is filesystem state. Document the verification by writing a marker.)

```bash
echo "# Lockdown verified $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  > /workspaces/ocr-container/.claude/.lockdown-verified
git add .claude/.lockdown-verified
git commit -m "chore: lockdown applied — enforcement paths immutable to bot

Verified via scripts/verify-protections.sh. claude-bot cannot modify
.claude/hooks/, .claude/settings.json, pd-push, scripts/, etc."
```

---

## Phase 13 — Final acceptance verification

### Task A37: Run full acceptance suite

This task runs all the workspace-level acceptance checks from the spec. It catches any gaps before declaring Plan A done.

- [ ] **Step 1: PAT scope verification**

Run: `cat /run/secrets/gh-token-pd | head -c 4`
Expected: `gith` (token starts with `github_pat_`).

Run: `GH_TOKEN=$(cat /run/secrets/gh-token-pd) gh issue list -R pdomain/pdomain-book-tools --limit 1 2>&1 | head -3`
Expected: works (issues listed, or empty list).

- [ ] **Step 2: Bot user functional**

Run: `sudo -u claude-bot bash -lc 'whoami; git config user.name; gh auth status 2>&1 | head -2'`
Expected: `claude-bot`; `ship-issue-bot`; "not logged in" (because bot's GH_CONFIG_DIR is empty).

- [ ] **Step 3: Bash command guard fires correctly**

Run: `echo '{"tool_input": {"command": "git push origin main"}}' | python3 .claude/hooks/bash-command-guard.py`
Expected: JSON output with `permissionDecision: deny`.

- [ ] **Step 4: Compound shell idioms NOT denied (acceptance from spec)**

Run: `echo '{"tool_input": {"command": "for f in *.py; do python -m py_compile \"$f\"; done"}}' | python3 .claude/hooks/bash-command-guard.py`
Expected: empty output (allow).

- [ ] **Step 5: pd-push rejects pushes to main**

Run: `pd-push main 2>&1 | head -3`
Expected: stderr message about "wrapper:refused"; exit nonzero.

- [ ] **Step 6: All workspace tests pass**

Run: `cd /workspaces/ocr-container && uv run pytest tests/scripts/ -v 2>&1 | tail -20`
Expected: all tests pass.

- [ ] **Step 7: Cost dashboard renders (with no data)**

Run: `python3 scripts/build-cost-dashboard.py 2>&1`
Expected: writes `.claude/agent-memory/ship-issue/cost-dashboard.html`. Inspect with: `head -20 .claude/agent-memory/ship-issue/cost-dashboard.html` — should be valid HTML.

- [ ] **Step 8: Lint-spec validates a synthetic conforming spec**

Run:
```bash
mkdir -p /tmp/lint-test
cat > /tmp/lint-test/test.md <<'EOF'
# Test

> **Status**: Active
> **Last updated**: 2026-05-09

## TL;DR
Two sentences.
## Context
Why.
## Constraints
- none
## Decision
The design.
## Contract / Acceptance
- [ ] one
## Trade-offs considered
| A | B |
## Consequences
ok
## Open questions
none
## References
none
EOF
python3 scripts/lint-spec.py /tmp/lint-test/test.md
```
Expected: exit 0, no output.

- [ ] **Step 9: SessionEnd hook fires on a synthetic transcript**

Run:
```bash
cat <<'EOF' > /tmp/synthetic-transcript.jsonl
{"role": "user", "content": "hi"}
{"role": "assistant", "model": "claude-haiku-4-5", "usage": {"input_tokens": 100, "output_tokens": 20}}
EOF
echo '{"transcript_path": "/tmp/synthetic-transcript.jsonl", "session_id": "synth"}' \
  | SHIP_ISSUE_MEMORY_DIR=/tmp/synth-memory python3 .claude/hooks/ship-issue-report.py
cat /tmp/synth-memory/run-reports.jsonl
```
Expected: a JSON record with `tokens_in: 100`, `api_cost_usd > 0`.

- [ ] **Step 10: All checks pass — declare Plan A done**

If all 9 steps above passed: Plan A is complete. Print:

```
✓ Plan A — Workspace Foundation: complete
Next: Plan B — pilot pdomain-prep-for-pgdp
```

Commit a final summary marker:

```bash
echo "Plan A complete: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> docs/superpowers/plans/STATUS.md
git add docs/superpowers/plans/STATUS.md
git commit -m "chore: mark Plan A (workspace foundation) complete

Verified via Task A37 acceptance suite. All 9 acceptance steps passed.
Workspace is ready for Plan B (pilot pdomain-prep-for-pgdp)."
```

---

## End of Plan A

When all tasks are checked, the workspace has:
- Two-user dev container
- Scoped PAT installed in secrets
- Branch protection (configured per repo in Plan B/C, not here)
- Hooks: bash-command-guard.py, ship-issue-report.py
- Settings: comprehensive permissions, registered hooks
- Statusline writing rate-limit sidecar
- All ship-issue scripts: throttle-check, pick, success, failure, orchestrator
- All workspace scripts: seed-labels (incl. status:* family), lint-spec, build-spec-index, file-legacy-migration-issues, migrate-legacy-spec-auto, build-cost-dashboard (with cross-repo kanban panel), statusline, tooling-change-guard, verify-protections
- Skills: ship-issue, fixing-specs
- Cost dashboard generation
- Lockdown verified — enforcement paths immutable to bot

Plan B (pilot pdomain-prep-for-pgdp) is now executable.
