---
status: complete
---

# Feature-request lifecycle — Phase 1: skills + labels + migration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land Phase 1 of the feature-request → spec → child-issues lifecycle. End state: `/triage`, `/spec-from-issue`, and `/decompose-spec` skills exist, their helpers have unit tests, the `claude-ok` → `bot:ship-issue-ready` rename is applied workspace-wide, and the new label families are seeded across all 8 pd-* repos. The skills are validated end-to-end against pdomain-book-tools. Ship-issue v1 still works exactly as before.

**Architecture:** Each skill follows the existing `ship-issue` pattern: `.claude/skills/<name>/SKILL.md` is interactive orchestration prose; mechanical work lives in `scripts/<name>-*.py` helpers with `tests/scripts/test_<name>_*.py` unit coverage. The `claude-ok` rename is one commit per surface (migration script, hook, pick script, failure script, file-legacy script, doc sweep) so failures bisect cleanly. The label rename runs against all 8 repos in one idempotent shell script. Milestone creation in `/decompose-spec` uses a small deterministic slug helper at `scripts/spec_slug.py` reusable by the chain-state report in Plan 2.

**Tech Stack:** Python 3.11 (helpers), Bash (migration + orchestration glue), `gh` CLI (GitHub mutations), `pytest`/`unittest` for tests, existing `lint-spec.py` for spec validation.

**Source spec:** `docs/superpowers/specs/2026-05-10-feature-request-spec-decomposition-design.md`

**Out of scope (Phase 2+):** backfill validation on real specs, chain-state report generator, dashboard panel, rollout to remaining 7 repos, dashboard refresh design.

---

## Background context for the engineer

You are landing the v1 of a workflow that turns ideas into shipped code:

```
[CT files issue]              [/skill]                        [ship-issue ships]

kind:feature-request   ──/triage N──►   triage:approved/rejected
                                       + forks ONE child:
                                       (a) tracking issue
                                                ──[CT arms bot:ship-issue-ready]──►
                                                ────────────► ship-issue ─► PR
                                       OR
                                       (b) spec issue
                                           ──/spec-from-issue──►
                                           docs/specs/file.md + spec PR
                                                ──/decompose-spec──►
                                                N child issues + milestone
                                                ──[CT arms bot:ship-issue-ready]──► ship-issue ─► PR
```

Existing surfaces you will modify or use:

- `scripts/seed-labels.sh` — one-shot per-repo label seeding. Add new entries.
- `scripts/ship-issue-pick.py` — bot's pick-and-claim script. Filters on `claude-ok`; rename to `bot:ship-issue-ready`.
- `scripts/ship-issue-failure.sh` — bounces issues. Strips `claude-ok`; rename.
- `scripts/file-legacy-migration-issues.py` — narrow legacy-spec helper. Has one `claude-ok` literal; rename.
- `.claude/hooks/bash-command-guard.py` — bot guardrail. `_claude_ok_check` enforces the mutation gate; rename to `_bot_ship_issue_check` and update label string.
- `.claude/skills/ship-issue/SKILL.md` — existing skill, not modified. Reference only (pattern to copy).
- `tests/scripts/test_ship_issue_pick.py` — existing unit-test pattern (importlib-based loader, pytest-style asserts). Copy for new tests.
- `tests/test_bash_command_guard.py` — existing hook test (subprocess-based). Pattern reference for any guard test changes.

The 8 repos are: `pdomain-book-tools`, `pdomain-ocr-cli`, `pd-ocr-labeler`, `pdomain-ocr-labeler-spa`, `pdomain-ocr-synth`, `pd-ocr-trainer`, `pd-png-optimizer`, `pdomain-prep-for-pgdp`. The same `REPOS` tuple is used in `scripts/build-cost-dashboard.py:25-28` — keep both lists in sync.

`gh` auth in this workspace runs through `GH_TOKEN_PD` (read from `/run/secrets/gh-token-pd`). Every script that calls `gh` must set this env explicitly, the same way `ship-issue-pick.py:96-105` does.

---

## File structure (created by this plan)

**Created — Python helpers:**

- `scripts/spec_slug.py` — pure helper: `derive_slug(issue_title) -> str`. Used by `/decompose-spec` and (in Plan 2) the chain-state report.
- `scripts/triage-fork.py` — fork a child tracking-or-spec issue from a feature-request. Idempotent.
- `scripts/spec-from-issue-finalize.py` — given a spec file path and the spec issue number, open a draft PR and edit the issue body to add `Spec:`.
- `scripts/decompose-spec-plan.py` — read a spec file and propose children as JSON.
- `scripts/decompose-spec-apply.py` — file confirmed children + create+attach the milestone.

**Created — Bash:**

- `scripts/migrate-claude-ok-to-bot-label.sh` — one-shot workspace-wide label rename + open-issue migration + old-label deletion.

**Created — skills:**

- `.claude/skills/triage/SKILL.md`
- `.claude/skills/spec-from-issue/SKILL.md`
- `.claude/skills/decompose-spec/SKILL.md`

**Created — tests:**

- `tests/scripts/test_spec_slug.py`
- `tests/scripts/test_triage_fork.py`
- `tests/scripts/test_spec_from_issue_finalize.py`
- `tests/scripts/test_decompose_spec_plan.py`
- `tests/scripts/test_decompose_spec_apply.py`

**Created — test helpers:**

- `tests/fakes/fake_gh.py` — drop-in `gh` shim recording calls + serving canned responses. Used by integration smoke in Task 17 and reusable for Plan 2.
- `tests/fakes/__init__.py` — empty package marker.

**Modified:**

- `scripts/seed-labels.sh` — replace `claude-ok` row; append new label rows.
- `scripts/ship-issue-pick.py` — three label-string surface changes.
- `scripts/ship-issue-failure.sh` — one label-string surface change.
- `scripts/file-legacy-migration-issues.py` — one label-string surface change.
- `.claude/hooks/bash-command-guard.py` — rename `_claude_ok_check` → `_bot_ship_issue_check`; update label string.
- Various docs (CLAUDE.md, plans, READMEs) — sweep for `claude-ok` mentions.

---

## Pre-flight: verify clean starting state

Before Task 1, confirm the working tree is clean of unrelated changes that would muddle the per-task commit history. The four files already showing as modified at session start (`statusline-with-ratelimits.sh`, `test_statusline_with_ratelimits.py`, the two `agent-memory/pdomain-book-tools/` files) are unrelated and should be committed or stashed first.

```bash
cd /workspaces/ocr-container
git status --porcelain
```

Expected: an empty list (or only this plan file, if you've already saved it).

If anything else shows modified or untracked, either commit it on its own branch or stash it before starting Task 1.

---

## Task 1: Build the fake-gh shim

**Why first:** later tests for triage / spec-from-issue / decompose-spec helpers that exercise gh-mutating code paths import or shell-out to this shim. Building it first lets every later test be written against a stable fake.

**Files:**

- Create: `tests/fakes/__init__.py`
- Create: `tests/fakes/fake_gh.py`
- Create: `tests/fakes/test_fake_gh.py`

- [ ] **Step 1: Create the package marker**

```bash
mkdir -p /workspaces/ocr-container/tests/fakes
touch /workspaces/ocr-container/tests/fakes/__init__.py
```

- [ ] **Step 2: Write the failing test for the shim**

Save as `tests/fakes/test_fake_gh.py`:

```python
"""Smoke tests for the fake-gh shim.

The shim is a drop-in replacement for `gh` that records every invocation
to a JSONL log and serves canned JSON responses keyed on argv-prefix.
Used by integration smoke tests in this and later plans.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SHIM = Path(__file__).resolve().parent / "fake_gh.py"


class FakeGhTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.calls_log = Path(self.tmp) / "calls.jsonl"
        self.responses = Path(self.tmp) / "responses.json"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *argv, expect_rc=0):
        env = {
            **os.environ,
            "FAKE_GH_CALLS_LOG": str(self.calls_log),
            "FAKE_GH_RESPONSES_JSON": str(self.responses),
        }
        r = subprocess.run(
            ["python3", str(SHIM), *argv],
            capture_output=True, text=True, env=env, timeout=10,
        )
        self.assertEqual(
            r.returncode, expect_rc,
            f"unexpected rc={r.returncode}; stderr={r.stderr}",
        )
        return r

    def test_records_call_and_returns_default(self):
        r = self._run("issue", "view", "42", "--repo", "x/y")
        self.assertEqual(r.stdout, "")  # default empty stdout
        lines = self.calls_log.read_text().splitlines()
        self.assertEqual(len(lines), 1)
        rec = json.loads(lines[0])
        self.assertEqual(rec["argv"], ["issue", "view", "42", "--repo", "x/y"])

    def test_canned_response_by_prefix(self):
        self.responses.write_text(json.dumps([
            {
                "match_argv_prefix": ["issue", "view"],
                "stdout": json.dumps({"number": 42, "labels": []}),
                "rc": 0,
            },
        ]))
        r = self._run("issue", "view", "42", "--repo", "x/y")
        self.assertEqual(json.loads(r.stdout), {"number": 42, "labels": []})

    def test_canned_response_first_match_wins(self):
        self.responses.write_text(json.dumps([
            {"match_argv_prefix": ["issue", "view"], "stdout": "first", "rc": 0},
            {"match_argv_prefix": ["issue"], "stdout": "second", "rc": 0},
        ]))
        r = self._run("issue", "view", "42")
        self.assertEqual(r.stdout.strip(), "first")

    def test_canned_response_with_nonzero_rc(self):
        self.responses.write_text(json.dumps([
            {"match_argv_prefix": ["api"], "stdout": "", "stderr": "boom", "rc": 4},
        ]))
        r = self._run("api", "/repos/x/y", expect_rc=4)
        self.assertIn("boom", r.stderr)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the test — confirm it fails**

```bash
cd /workspaces/ocr-container
python3 -m unittest tests/fakes/test_fake_gh.py -v
```

Expected: error/failure (shim does not exist yet).

- [ ] **Step 4: Implement the shim**

Save as `tests/fakes/fake_gh.py`:

```python
#!/usr/bin/env python3
"""fake_gh — drop-in `gh` replacement for tests.

Reads optional canned responses from FAKE_GH_RESPONSES_JSON; appends every
invocation to FAKE_GH_CALLS_LOG (JSONL, one record per call). With no
responses configured, returns empty stdout / rc 0.

Responses file format: a JSON list of {match_argv_prefix, stdout, stderr, rc}.
First entry whose match_argv_prefix is a prefix of the actual argv wins.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _load_responses() -> list[dict]:
    p = os.environ.get("FAKE_GH_RESPONSES_JSON")
    if not p or not Path(p).is_file():
        return []
    return json.loads(Path(p).read_text())


def _record_call(argv: list[str]) -> None:
    p = os.environ.get("FAKE_GH_CALLS_LOG")
    if not p:
        return
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps({"argv": argv}) + "\n")


def _match(argv: list[str], responses: list[dict]) -> dict | None:
    for resp in responses:
        prefix = resp.get("match_argv_prefix", [])
        if argv[: len(prefix)] == prefix:
            return resp
    return None


def main() -> int:
    argv = sys.argv[1:]
    _record_call(argv)
    resp = _match(argv, _load_responses())
    if resp is None:
        return 0
    sys.stdout.write(resp.get("stdout", ""))
    sys.stderr.write(resp.get("stderr", ""))
    return int(resp.get("rc", 0))


if __name__ == "__main__":
    sys.exit(main())
```

```bash
chmod +x /workspaces/ocr-container/tests/fakes/fake_gh.py
```

- [ ] **Step 5: Run the test — confirm it passes**

```bash
cd /workspaces/ocr-container
python3 -m unittest tests/fakes/test_fake_gh.py -v
```

Expected: 4 tests pass.

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container
git add tests/fakes/__init__.py tests/fakes/fake_gh.py tests/fakes/test_fake_gh.py
git commit -m "test(fakes): add fake-gh shim for skill helper integration tests"
```

---

## Task 2: Update seed-labels.sh with the new label families

**Why now:** the new labels need to exist on the repo before any skill can reference them. Doing this before the `claude-ok` rename keeps the change one-axis-at-a-time.

**Files:**

- Modify: `scripts/seed-labels.sh`

- [ ] **Step 1: Read the current label list**

```bash
sed -n '10,42p' /workspaces/ocr-container/scripts/seed-labels.sh
```

Expected: the existing `LABELS=(...)` array with `claude-ok|0e8a16|...` on line 40.

- [ ] **Step 2: Replace `claude-ok` row and append new label rows**

Edit `scripts/seed-labels.sh`. Replace the `claude-ok` line with the new `bot:ship-issue-ready` line, and add three new label families before the closing `)`:

```bash
  "claude-ok|0e8a16|Mutation gate — agent may modify this issue"
```

becomes:

```bash
  "bot:ship-issue-ready|0e8a16|Bot-eligibility gate — ship-issue may modify this issue"

  "kind:feature-request|c5def5|Idea pre-triage; will fork a tracking or spec issue"

  "triage:proposed-by-agent|d4c5f9|Reserved for future agent-driven triage proposal"
  "triage:approved|0e8a16|Triage decision: ready to fork a child"
  "triage:rejected|d73a4a|Triage decision: not pursued"
  "triage:needs-spec|fbca04|Triage decision: spec required before child issues"
```

Also update the description on the `status:ready` line so it no longer says "with claude-ok":

```bash
  "status:ready|0e8a16|Workflow: queued for ship-issue (with claude-ok) or you"
```

becomes:

```bash
  "status:ready|0e8a16|Workflow: queued for ship-issue (with bot:ship-issue-ready) or you"
```

- [ ] **Step 3: Smoke-run on a throwaway test repo**

You don't have a test repo. Instead, smoke-test idempotence by re-reading the file shape:

```bash
cd /workspaces/ocr-container
bash -n scripts/seed-labels.sh
grep -c "^  \"" scripts/seed-labels.sh
```

Expected: bash syntax check passes; row count is 5 more than before (claude-ok kept its row → 1 unchanged net; +1 kind:feature-request; +4 triage:*; +0 bot — wait the row count goes from 26 to 30, since claude-ok→bot:ship-issue-ready is a 1:1 substitution and we add 5 new rows). Confirm: `grep -c '^  "' scripts/seed-labels.sh` returns 30 (or 30 plus blank-line padding rows if you formatted with blank separators).

- [ ] **Step 4: Run idempotently against pdomain-book-tools**

```bash
cd /workspaces/ocr-container
scripts/seed-labels.sh pdomain/pdomain-book-tools
```

Expected: existing rows print `✓ … (exists)`; new rows print `+ kind:feature-request`, `+ triage:proposed-by-agent`, etc. The new `bot:ship-issue-ready` is created; `claude-ok` row is also re-printed as `(exists)` because the label still exists on the repo (the migration in Task 3 will delete it).

- [ ] **Step 5: Verify in GitHub**

```bash
gh label list -R pdomain/pdomain-book-tools --limit 200 | grep -E "(bot:|triage:|kind:feature-request|claude-ok)"
```

Expected: `bot:ship-issue-ready`, `kind:feature-request`, four `triage:*` rows, AND the legacy `claude-ok` (still present pre-migration). All present.

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/seed-labels.sh
git commit -m "feat(labels): add bot:ship-issue-ready, kind:feature-request, triage:* to seed-labels.sh"
```

---

## Task 3: Write the migration script

**Files:**

- Create: `scripts/migrate-claude-ok-to-bot-label.sh`

- [ ] **Step 1: Write the script**

Save as `scripts/migrate-claude-ok-to-bot-label.sh`:

```bash
#!/usr/bin/env bash
# migrate-claude-ok-to-bot-label.sh — one-shot workspace-wide rename.
#
# For each pd-* repo:
#   1. Ensure bot:ship-issue-ready label exists.
#   2. For every open or closed issue/PR with claude-ok, add bot:ship-issue-ready.
#   3. Remove claude-ok from those issues/PRs.
#   4. Delete the claude-ok label from the repo.
#
# Idempotent: safe to re-run. Skips repos already migrated.
#
# Usage: scripts/migrate-claude-ok-to-bot-label.sh [--dry-run]

set -euo pipefail

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi

REPOS=(
  pdomain/pdomain-book-tools
  pdomain/pdomain-ocr-cli
  ConcaveTrillion/pd-ocr-labeler
  pdomain/pdomain-ocr-labeler-spa
  pdomain/pdomain-ocr-synth
  ConcaveTrillion/pd-ocr-trainer
  ConcaveTrillion/pd-png-optimizer
  pdomain/pdomain-prep-for-pgdp
)

run() {
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "DRY: $*"
  else
    "$@"
  fi
}

for REPO in "${REPOS[@]}"; do
  echo "=== $REPO ==="

  # Step 1 — ensure new label exists. Idempotent.
  if ! gh label list -R "$REPO" --limit 200 --json name | grep -q '"bot:ship-issue-ready"'; then
    run gh label create "bot:ship-issue-ready" -R "$REPO" \
      --color "0e8a16" \
      --description "Bot-eligibility gate — ship-issue may modify this issue"
  fi

  # Step 2/3 — find every issue/PR carrying claude-ok and migrate it.
  ITEMS=$(gh issue list -R "$REPO" --label claude-ok --state all \
            --limit 500 --json number --jq '.[].number')
  PRS=$(gh pr list -R "$REPO" --label claude-ok --state all \
          --limit 500 --json number --jq '.[].number' || true)
  for N in $ITEMS $PRS; do
    echo "  migrating #$N"
    run gh issue edit "$N" -R "$REPO" \
      --add-label "bot:ship-issue-ready" --remove-label "claude-ok"
  done

  # Step 4 — delete the old label. Idempotent: skips if already gone.
  if gh label list -R "$REPO" --limit 200 --json name | grep -q '"claude-ok"'; then
    run gh label delete "claude-ok" -R "$REPO" --yes
  fi

  echo "  done."
done

echo
echo "All 8 repos migrated."
```

```bash
chmod +x /workspaces/ocr-container/scripts/migrate-claude-ok-to-bot-label.sh
```

- [ ] **Step 2: Smoke-check syntax**

```bash
bash -n /workspaces/ocr-container/scripts/migrate-claude-ok-to-bot-label.sh
```

Expected: no output (clean parse).

- [ ] **Step 3: Dry-run against the workspace**

```bash
cd /workspaces/ocr-container
scripts/migrate-claude-ok-to-bot-label.sh --dry-run
```

Expected: per-repo "DRY: gh ..." lines for any issues currently carrying `claude-ok`. No state changes on GitHub.

- [ ] **Step 4: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/migrate-claude-ok-to-bot-label.sh
git commit -m "feat(migration): scripts/migrate-claude-ok-to-bot-label.sh (idempotent, all 8 repos)"
```

---

## Task 4: Run the migration on all 8 repos

**This is a manual checkpoint, not code.** No tests, no commit. The state change happens on GitHub.

- [ ] **Step 1: Re-run the dry-run and review the planned changes**

```bash
cd /workspaces/ocr-container
scripts/migrate-claude-ok-to-bot-label.sh --dry-run | tee /tmp/migration-plan.log
wc -l /tmp/migration-plan.log
```

Expected: a manageable number of issue migrations (probably ≤ 20 across all 8 repos given current state). Pause and read `/tmp/migration-plan.log` end-to-end before continuing.

- [ ] **Step 2: Run for real**

```bash
cd /workspaces/ocr-container
scripts/migrate-claude-ok-to-bot-label.sh 2>&1 | tee /tmp/migration-real.log
```

Expected: each repo reports 0 or N issues migrated, then "done." `claude-ok` label is deleted from every repo.

- [ ] **Step 3: Verify post-migration state**

```bash
for r in pdomain-book-tools pdomain-ocr-cli pd-ocr-labeler pdomain-ocr-labeler-spa \
         pdomain-ocr-synth pd-ocr-trainer pd-png-optimizer pdomain-prep-for-pgdp; do
  echo "=== $r ==="
  gh label list -R "ConcaveTrillion/$r" --limit 200 \
    | grep -E "claude-ok|bot:ship-issue-ready" || echo "  (only bot:ship-issue-ready, claude-ok gone)"
done
```

Expected: every repo shows `bot:ship-issue-ready` and NO `claude-ok` row.

- [ ] **Step 4: Verify no straggler issues**

```bash
for r in pdomain-book-tools pdomain-ocr-cli pd-ocr-labeler pdomain-ocr-labeler-spa \
         pdomain-ocr-synth pd-ocr-trainer pd-png-optimizer pdomain-prep-for-pgdp; do
  echo "=== $r ==="
  gh issue list -R "ConcaveTrillion/$r" --label claude-ok --state all \
    --json number --jq '.[].number' | head
done
```

Expected: empty output for every repo (no issues still carry `claude-ok`).

If any repo still has issues, re-run the migration on that repo:

```bash
gh issue list -R ConcaveTrillion/<repo> --label claude-ok --state all \
  --json number --jq '.[].number' | while read N; do
  gh issue edit "$N" -R ConcaveTrillion/<repo> \
    --add-label bot:ship-issue-ready --remove-label claude-ok
done
gh label delete claude-ok -R ConcaveTrillion/<repo> --yes
```

---

## Task 5: Rename the bash-command-guard label gate

**Files:**

- Modify: `.claude/hooks/bash-command-guard.py:264-321`
- Modify: `tests/scripts/test_bash_command_guard.py:95` (the gate-comment + any string assertions)

- [ ] **Step 1: Add a failing test for the renamed gate**

The current `tests/scripts/test_bash_command_guard.py` has gate tests around line 95. Find the section that asserts on `claude-ok`, add a parallel test that asserts on `bot:ship-issue-ready` (or update the existing one to use the new name, depending on what's there):

```bash
sed -n '85,140p' /workspaces/ocr-container/tests/scripts/test_bash_command_guard.py
```

For the gate-rename, append a new test class `BotShipIssueLabelGateTests` to `tests/scripts/test_bash_command_guard.py` (do not delete existing tests; mirror the existing pattern for the `claude-ok` gate). The new class should:

1. Stand up a fake gh on PATH (using `tests/fakes/fake_gh.py` — symlinked to a `gh` name in a tmpdir, with `FAKE_GH_RESPONSES_JSON` configured to return `{"labels": [{"name": "bot:ship-issue-ready"}]}` for `gh issue view ... --json labels`).
2. Run the hook with a `gh issue close 42 --repo pdomain/pdomain-book-tools` command. Expect ALLOW.
3. Run the same with the canned response returning `[]` for labels. Expect DENY with `bot:ship-issue-ready` in the reason.

This is a small block. Add it at the end of the test file. Example shape:

```python
class BotShipIssueLabelGateTests(unittest.TestCase):
    """Regression coverage for the renamed _bot_ship_issue_check gate."""

    def _hook_with_fake_gh(self, labels_for_view, command):
        import json as _json
        import os as _os
        import shutil as _shutil
        import subprocess as _sp
        import tempfile as _tf
        from pathlib import Path as _P

        tmp = _tf.mkdtemp()
        self.addCleanup(_shutil.rmtree, tmp, True)
        responses = [{
            "match_argv_prefix": ["issue", "view"],
            "stdout": _json.dumps({"labels": labels_for_view}),
            "rc": 0,
        }]
        responses_path = _P(tmp) / "responses.json"
        responses_path.write_text(_json.dumps(responses))
        gh_dir = _P(tmp) / "bin"
        gh_dir.mkdir()
        shim = _P(__file__).resolve().parent.parent / "fakes" / "fake_gh.py"
        (gh_dir / "gh").symlink_to(shim)
        env = {
            **_os.environ,
            "PATH": f"{gh_dir}:{_os.environ['PATH']}",
            "FAKE_GH_RESPONSES_JSON": str(responses_path),
            "BASH_GUARD_FORCE_BOT": "1",
        }
        payload = {"tool_name": "Bash", "tool_input": {"command": command}}
        return _sp.run(
            ["python3", str(HOOK)],
            input=_json.dumps(payload), capture_output=True, text=True,
            env=env, timeout=10,
        )

    def test_allows_when_label_present(self):
        r = self._hook_with_fake_gh(
            [{"name": "bot:ship-issue-ready"}],
            "gh issue close 42 --repo pdomain/pdomain-book-tools",
        )
        self.assertEqual(_decision(r.stdout), "allow")

    def test_denies_when_label_absent(self):
        r = self._hook_with_fake_gh(
            [{"name": "kind:bug"}],
            "gh issue close 42 --repo pdomain/pdomain-book-tools",
        )
        self.assertEqual(_decision(r.stdout), "deny")
        self.assertIn("bot:ship-issue-ready", r.stdout)
```

- [ ] **Step 2: Run the new tests — confirm they fail**

```bash
cd /workspaces/ocr-container
python3 -m unittest tests.scripts.test_bash_command_guard.BotShipIssueLabelGateTests -v
```

Expected: at least the `test_denies_when_label_absent` test fails because the deny reason still contains `claude-ok`.

- [ ] **Step 3: Apply the rename in the hook**

Open `.claude/hooks/bash-command-guard.py` and change:

- Line 264 comment: `--- claude-ok mutation gate` → `--- bot:ship-issue-ready mutation gate`
- Line ~269 function name: `_claude_ok_check` → `_bot_ship_issue_check`
- Line ~271 docstring: `'claude-ok'` → `'bot:ship-issue-ready'`
- Line ~308 timeout message: `claude-ok lookup timed out` → `bot:ship-issue-ready lookup timed out`
- Line ~315 condition: `if "claude-ok" not in labels:` → `if "bot:ship-issue-ready" not in labels:`
- Line ~317 deny message: `lacks the 'claude-ok' label. Add the label to permit modification.` → `lacks the 'bot:ship-issue-ready' label. Add the label to permit modification.`
- Line ~377 entry-point call: `_claude_ok_check(segments)` → `_bot_ship_issue_check(segments)`

- [ ] **Step 4: Run all hook tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m unittest tests/test_bash_command_guard.py tests/scripts/test_bash_command_guard.py -v
```

Expected: all pre-existing tests still green AND the new `BotShipIssueLabelGateTests` pass.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add .claude/hooks/bash-command-guard.py tests/scripts/test_bash_command_guard.py
git commit -m "refactor(hook): rename _claude_ok_check → _bot_ship_issue_check"
```

---

## Task 6: Rename in ship-issue-pick.py

**Files:**

- Modify: `scripts/ship-issue-pick.py:53,54,57,109,112,284`
- Modify: `tests/scripts/test_ship_issue_pick.py` (fixture label names + assertions)

- [ ] **Step 1: Update the failing-test fixtures to use the new label name**

Open `tests/scripts/test_ship_issue_pick.py`. Replace every `"claude-ok"` literal with `"bot:ship-issue-ready"`. Replace every `"claude-ok"` substring assertion with `"bot:ship-issue-ready"` (or, where the assertion is doing `assert "claude-ok" in reason.lower()`, change to `assert "bot:ship-issue-ready" in reason.lower()`).

- [ ] **Step 2: Run the tests — confirm they fail**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_ship_issue_pick.py -v
```

Expected: failures because `is_eligible` still rejects on missing `claude-ok` while fixtures now provide `bot:ship-issue-ready`.

- [ ] **Step 3: Update ship-issue-pick.py**

Open `scripts/ship-issue-pick.py` and change at these specific locations:

- Line 4 docstring: `status:ready\` AND \`claude-ok\` labels` → `` `status:ready` AND `bot:ship-issue-ready` labels``
- Line 53: `if "claude-ok" not in label_names:` → `if "bot:ship-issue-ready" not in label_names:`
- Line 54: `return False, "missing claude-ok label"` → `return False, "missing bot:ship-issue-ready label"`
- Line 57 comment: `Trust is gated by claude-ok already` → `Trust is gated by bot:ship-issue-ready already`
- Line 109 docstring: `status:ready AND claude-ok` → `status:ready AND bot:ship-issue-ready`
- Line 112: `"--label", "status:ready", "--label", "claude-ok",` → `"--label", "status:ready", "--label", "bot:ship-issue-ready",`
- Line 284: `if "claude-ok" in {l["name"] for l in issue.get("labels", [])}:` → `if "bot:ship-issue-ready" in {l["name"] for l in issue.get("labels", [])}:`

- [ ] **Step 4: Run the tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_ship_issue_pick.py -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/ship-issue-pick.py tests/scripts/test_ship_issue_pick.py
git commit -m "refactor(ship-issue-pick): claude-ok → bot:ship-issue-ready"
```

---

## Task 7: Rename in ship-issue-failure.sh and file-legacy-migration-issues.py

These two surfaces have one literal each; group them in one commit.

**Files:**

- Modify: `scripts/ship-issue-failure.sh:6,24,34`
- Modify: `scripts/file-legacy-migration-issues.py:7,95`

- [ ] **Step 1: Read current state**

```bash
grep -n claude-ok /workspaces/ocr-container/scripts/ship-issue-failure.sh \
                 /workspaces/ocr-container/scripts/file-legacy-migration-issues.py
```

Expected: 5 matches.

- [ ] **Step 2: Update ship-issue-failure.sh**

In `scripts/ship-issue-failure.sh`:

- Line 6 comment: `Strip claude-ok label` → `Strip bot:ship-issue-ready label`
- Line 24 gh-call: `--remove-label "claude-ok"` → `--remove-label "bot:ship-issue-ready"`
- Line 34 user-facing message: `\`status:backlog\` and \`claude-ok\` removed; re-add \`claude-ok\`` → `\`status:backlog\` and \`bot:ship-issue-ready\` removed; re-add \`bot:ship-issue-ready\``

- [ ] **Step 3: Update file-legacy-migration-issues.py**

In `scripts/file-legacy-migration-issues.py`:

- Line 7 docstring: `claude-ok if auto-runnable` → `bot:ship-issue-ready if auto-runnable`
- Line 95 label list: `labels.extend(["effort:S", "model:haiku", "model-effort:low", "claude-ok"])` → `labels.extend(["effort:S", "model:haiku", "model-effort:low", "bot:ship-issue-ready"])`

- [ ] **Step 4: Smoke-check**

```bash
grep -nE "claude-ok" /workspaces/ocr-container/scripts/ship-issue-failure.sh \
                    /workspaces/ocr-container/scripts/file-legacy-migration-issues.py
```

Expected: no output.

```bash
bash -n /workspaces/ocr-container/scripts/ship-issue-failure.sh
python3 -c "import ast; ast.parse(open('/workspaces/ocr-container/scripts/file-legacy-migration-issues.py').read())"
```

Expected: clean parses.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/ship-issue-failure.sh scripts/file-legacy-migration-issues.py
git commit -m "refactor(scripts): claude-ok → bot:ship-issue-ready in failure.sh + legacy-migration"
```

---

## Task 8: Sweep doc references

**Files:**

- Modify: `CLAUDE.md` (workspace) — if any `claude-ok` mention remains.
- Modify: `docs/superpowers/plans/2026-05-09-workspace-foundation.md` — multiple historical mentions (do NOT rewrite; add a note at top of the section explaining the rename).
- Modify: `docs/superpowers/plans/2026-05-10-pilot-pdomain-book-tools.md`, `2026-05-10-pilot-pdomain-book-tools-debrief.md` — these are historical; leave as-is, do NOT rewrite.
- Modify: pd-* repo CLAUDE.md / READMEs — sweep, but only if they mention `claude-ok` operationally (not historically).

- [ ] **Step 1: Find live references**

```bash
cd /workspaces/ocr-container
grep -rln "claude-ok" \
  --exclude-dir=node_modules --exclude-dir=.git \
  --exclude-dir=.claude/agent-memory \
  --include="*.md" --include="*.py" --include="*.sh" \
  | grep -v docs/superpowers/plans \
  | grep -v docs/superpowers/specs/2026-05-09 \
  | grep -v docs/superpowers/specs/2026-05-10
```

Expected: a small list. Historical docs (plans + the older spec) are intentionally excluded — they are records of decisions made before the rename and should not be rewritten.

- [ ] **Step 2: For each remaining file, update operational references**

For each file in the list above, replace `claude-ok` with `bot:ship-issue-ready` where the mention describes current behavior. Leave any explicitly historical mention alone.

If `CLAUDE.md` (workspace root) has any current-behavior mention, update it. Per the routing in `CLAUDE.md`, do NOT delegate this — workspace-level docs are direct edits.

- [ ] **Step 3: For each pd-* repo, sweep current-behavior mentions**

Per `CLAUDE.md`, pd-* file mods normally go through the per-repo agent. **Exception** (matches the spec line ~138 carve-out for skill development): you may make these mechanical text replacements directly because they are surface-level rename mirrors of a workspace-level decision, not domain changes. Each repo gets one commit of its own (so the per-repo CI runs cleanly):

```bash
for r in pdomain-book-tools pdomain-ocr-cli pd-ocr-labeler pdomain-ocr-labeler-spa \
         pdomain-ocr-synth pd-ocr-trainer pd-png-optimizer pdomain-prep-for-pgdp; do
  cd "/workspaces/ocr-container/$r"
  grep -rln "claude-ok" --include="*.md" --include="*.py" --include="*.sh" . \
    | grep -v ".claude/agent-memory" || true
done
```

For each match in each repo, decide: operational (rewrite) or historical (leave). Commit per-repo.

- [ ] **Step 4: Add a forward-pointer in `docs/superpowers/specs/2026-05-09-github-issues-projects-design.md`**

The 2026-05-09 spec is the parent design and refers to `claude-ok` as the gate. Don't rewrite it; add a one-line "superseded by" note near the top, e.g. at the start of the "Future state" section:

```markdown
> **Note (2026-05-10):** the `claude-ok` label was renamed to `bot:ship-issue-ready` in the `bot:` family by [the feature-request lifecycle spec](2026-05-10-feature-request-spec-decomposition-design.md). Mentions below predate the rename.
```

Run lint to confirm the spec still passes:

```bash
python3 /workspaces/ocr-container/scripts/lint-spec.py /workspaces/ocr-container/docs/superpowers/specs/2026-05-09-github-issues-projects-design.md
```

Expected: exit 0.

- [ ] **Step 5: Commit (workspace + per-repo as needed)**

```bash
cd /workspaces/ocr-container
git add -A docs/ CLAUDE.md
git commit -m "docs: sweep claude-ok → bot:ship-issue-ready (operational mentions only)"
```

For each pd-* repo with changes, separately:

```bash
cd /workspaces/ocr-container/<repo>
git add <files>
git commit -m "docs: claude-ok → bot:ship-issue-ready (workspace label rename)"
```

---

## Task 9: Build the spec_slug.py helper

**Files:**

- Create: `scripts/spec_slug.py`
- Create: `tests/scripts/test_spec_slug.py`

- [ ] **Step 1: Write the failing test**

Save as `tests/scripts/test_spec_slug.py`:

```python
"""Tests for scripts/spec_slug.py.

The slug derivation must be deterministic across runs (same input always
produces same output) so that /decompose-spec's milestone-reuse logic
finds existing milestones on rerun. ASCII-safe so GitHub milestone titles
don't get URL-encoded oddly.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/spec_slug.py"


def _mod():
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    spec = importlib.util.spec_from_file_location("spec_slug", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_basic_slug():
    m = _mod()
    assert m.derive_slug("Reorganize page-utils pipeline") == "reorganize-page-utils-pipeline"


def test_strips_kind_marker():
    m = _mod()
    assert m.derive_slug("[spec] Add rotation heuristic") == "add-rotation-heuristic"
    assert m.derive_slug("[chore] Refactor X") == "refactor-x"


def test_truncates_to_40_chars():
    m = _mod()
    long_title = "A " * 50
    s = m.derive_slug(long_title)
    assert len(s) <= 40
    assert not s.endswith("-")


def test_handles_unicode_and_punctuation():
    m = _mod()
    assert m.derive_slug("Foo — Bar / Baz!") == "foo-bar-baz"
    assert m.derive_slug("Café résumé") == "caf-r-sum"


def test_idempotent_on_already_slug():
    m = _mod()
    assert m.derive_slug("foo-bar-baz") == "foo-bar-baz"


def test_empty_title_falls_back_to_unnamed():
    m = _mod()
    assert m.derive_slug("") == "unnamed"
    assert m.derive_slug("!!!") == "unnamed"


def test_milestone_title_format():
    m = _mod()
    assert m.milestone_title("Reorganize pipeline", 12) == "spec: reorganize-pipeline (#12)"
```

- [ ] **Step 2: Run the test — confirm it fails**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_spec_slug.py -v
```

Expected: import error / file not found.

- [ ] **Step 3: Implement the helper**

Save as `scripts/spec_slug.py`:

```python
"""Deterministic slug + milestone-title helper for the spec lifecycle.

Used by:
- scripts/decompose-spec-apply.py (milestone creation, diff-mode reuse)
- scripts/build-spec-chain-report.py (Plan 2 — joins issues to milestones by title)

Slug rules (must be deterministic across runs):
- Lowercase
- Strip a leading [spec|chore|feature|bug] marker if present
- Replace runs of non-[a-z0-9] with single dashes
- Strip leading/trailing dashes
- Truncate to 40 characters, then re-strip trailing dashes
- Empty result falls back to "unnamed"
"""
from __future__ import annotations

import re

_KIND_MARKER = re.compile(r"^\[(spec|chore|feature|bug)\]\s*", re.IGNORECASE)
_NON_SLUG = re.compile(r"[^a-z0-9]+")
_MAX_LEN = 40


def derive_slug(title: str) -> str:
    s = title.lower().strip()
    s = _KIND_MARKER.sub("", s)
    s = _NON_SLUG.sub("-", s)
    s = s.strip("-")
    s = s[:_MAX_LEN].rstrip("-")
    return s or "unnamed"


def milestone_title(issue_title: str, issue_number: int) -> str:
    """Format the canonical milestone title: 'spec: <slug> (#M)'."""
    return f"spec: {derive_slug(issue_title)} (#{issue_number})"
```

- [ ] **Step 4: Run the tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_spec_slug.py -v
```

Expected: 7 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/spec_slug.py tests/scripts/test_spec_slug.py
git commit -m "feat(spec_slug): deterministic slug helper for milestone titles"
```

---

## Task 10: Build triage-fork.py

**Files:**

- Create: `scripts/triage-fork.py`
- Create: `tests/scripts/test_triage_fork.py`

The script forks a child issue from a `kind:feature-request` parent. Inputs: parent issue number, output kind (`tracking` or `spec`), proposed title, body, target labels. Outputs: prints the new issue number on stdout. Idempotent: refuses if a child with `Tracks: #<parent>` already exists in the same repo, unless `--force`.

- [ ] **Step 1: Write the failing tests**

Save as `tests/scripts/test_triage_fork.py`:

```python
"""Tests for scripts/triage-fork.py.

Pure-logic tests use importlib to load the module and exercise functions
that take an injected gh_call seam.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/triage-fork.py"


def _mod():
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    spec = importlib.util.spec_from_file_location("triage_fork", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FakeGh:
    """Minimal fake gh_call: returns canned results for issue-list, captures issue-create."""
    def __init__(self, existing_children=None):
        self.existing_children = existing_children or []
        self.created = []
        self.commented = []

    def issue_list(self, repo, label=None, state="open", limit=200):
        return list(self.existing_children)

    def issue_create(self, repo, title, body, labels):
        n = 100 + len(self.created)
        self.created.append({"number": n, "title": title, "body": body, "labels": labels})
        return n

    def issue_comment(self, repo, number, body):
        self.commented.append({"number": number, "body": body})


def test_existing_child_blocks_unless_force():
    m = _mod()
    gh = FakeGh(existing_children=[{"number": 99, "body": "Tracks: #42\n", "labels": []}])
    decision = m.plan_fork(
        gh, repo="pdomain/pdomain-book-tools", parent=42,
        kind="bug", output="tracking",
        title="Fix X", body="Repro: ...", labels=["kind:bug", "effort:S"],
        force=False,
    )
    assert decision.kind == "skip"
    assert "Tracks: #42" in decision.reason


def test_force_overrides_existing_child():
    m = _mod()
    gh = FakeGh(existing_children=[{"number": 99, "body": "Tracks: #42", "labels": []}])
    decision = m.plan_fork(
        gh, repo="pdomain/pdomain-book-tools", parent=42,
        kind="bug", output="tracking",
        title="Fix X", body="Repro: ...", labels=["kind:bug"],
        force=True,
    )
    assert decision.kind == "create"


def test_creates_tracking_child_with_tracks_line():
    m = _mod()
    gh = FakeGh()
    decision = m.plan_fork(
        gh, repo="pdomain/pdomain-book-tools", parent=42,
        kind="bug", output="tracking",
        title="Fix X", body="Repro: foo", labels=["kind:bug", "effort:S"],
        force=False,
    )
    assert decision.kind == "create"
    new_num = m.execute_fork(gh, decision)
    assert new_num == 100
    assert len(gh.created) == 1
    body = gh.created[0]["body"]
    assert "Tracks: #42" in body
    assert "Repro: foo" in body
    assert "kind:bug" in gh.created[0]["labels"]


def test_creates_spec_child_carries_kind_spec_label():
    m = _mod()
    gh = FakeGh()
    decision = m.plan_fork(
        gh, repo="pdomain/pdomain-book-tools", parent=42,
        kind="spec", output="spec",
        title="Spec: rework Y", body="Y is hard", labels=["kind:spec", "effort:M"],
        force=False,
    )
    new_num = m.execute_fork(gh, decision)
    assert "kind:spec" in gh.created[0]["labels"]
    assert "Tracks: #42" in gh.created[0]["body"]


def test_posts_pointer_comment_on_parent():
    m = _mod()
    gh = FakeGh()
    decision = m.plan_fork(
        gh, repo="pdomain/pdomain-book-tools", parent=42,
        kind="bug", output="tracking",
        title="Fix X", body="Repro", labels=["kind:bug"],
        force=False,
    )
    new_num = m.execute_fork(gh, decision)
    assert any(c["number"] == 42 and f"#{new_num}" in c["body"] for c in gh.commented)
```

- [ ] **Step 2: Run the test — confirm it fails**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_triage_fork.py -v
```

Expected: file not found / import error.

- [ ] **Step 3: Implement triage-fork.py**

Save as `scripts/triage-fork.py`:

```python
#!/usr/bin/env python3
"""triage-fork.py — fork a child issue from a kind:feature-request parent.

Used by the /triage skill after the agent decides classification. The
skill reads the feature-request, decides:
  - approve (with output:tracking) → fork a kind:bug|chore|feature
  - approve (with output:spec)     → fork a kind:spec
  - reject                         → skill posts comment + applies
                                     triage:rejected; this script not
                                     needed in that case

Idempotent on the parent: refuses if a child with `Tracks: #<parent>` is
already open in the same repo, unless --force is passed. The spec calls
this "diff-mode" but for triage there's only one expected child per
parent so refusing is the right behavior.

Usage (called by SKILL.md):

  scripts/triage-fork.py \\
    --repo pdomain/pdomain-book-tools \\
    --parent 42 \\
    --kind bug \\
    --output tracking \\
    --title 'Fix the foo handler' \\
    --body-file /tmp/triage-42-body.md \\
    --label kind:bug --label effort:S \\
    --label model:haiku --label model-effort:low

Prints the new issue number to stdout.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import subprocess
import sys
from pathlib import Path


# --- gh seam ----------------------------------------------------------------

def _gh_env() -> dict:
    env = os.environ.copy()
    token_path = "/run/secrets/gh-token-pd"
    if Path(token_path).is_file():
        env["GH_TOKEN"] = Path(token_path).read_text().strip()
    return env


class GhCli:
    """Real gh-CLI implementation. Tests use FakeGh instead."""

    def issue_list(self, repo, label=None, state="open", limit=200):
        cmd = ["gh", "issue", "list", "--repo", repo, "--state", state,
               "--limit", str(limit), "--json", "number,body,labels"]
        if label:
            cmd += ["--label", label]
        r = subprocess.run(cmd, capture_output=True, text=True, env=_gh_env(),
                           check=True, timeout=30)
        return json.loads(r.stdout)

    def issue_create(self, repo, title, body, labels):
        cmd = ["gh", "issue", "create", "--repo", repo, "--title", title,
               "--body", body]
        for lbl in labels:
            cmd += ["--label", lbl]
        r = subprocess.run(cmd, capture_output=True, text=True, env=_gh_env(),
                           check=True, timeout=30)
        # gh prints the new issue URL; extract the number.
        url = r.stdout.strip().splitlines()[-1]
        return int(url.rstrip("/").rsplit("/", 1)[-1])

    def issue_comment(self, repo, number, body):
        subprocess.run(
            ["gh", "issue", "comment", str(number), "--repo", repo, "--body", body],
            capture_output=True, text=True, env=_gh_env(), check=True, timeout=30,
        )


# --- decision data classes --------------------------------------------------

@dataclasses.dataclass
class ForkDecision:
    kind: str  # "create" or "skip"
    reason: str
    repo: str
    parent: int
    title: str
    body: str
    labels: list[str]


# --- planning ---------------------------------------------------------------

def _existing_child(gh, repo: str, parent: int) -> dict | None:
    needle = f"Tracks: #{parent}"
    for issue in gh.issue_list(repo, state="open"):
        if needle in (issue.get("body") or ""):
            return issue
    return None


def plan_fork(gh, *, repo: str, parent: int, kind: str, output: str,
              title: str, body: str, labels: list[str],
              force: bool) -> ForkDecision:
    """Decide whether to create the child issue. Pure logic; takes injected gh."""
    if not force:
        prior = _existing_child(gh, repo, parent)
        if prior:
            return ForkDecision(
                kind="skip",
                reason=f"existing child #{prior['number']} carries Tracks: #{parent}",
                repo=repo, parent=parent, title=title,
                body=body, labels=labels,
            )

    # Body always carries the Tracks: header. Spec-output children also get
    # an empty Spec: line that /spec-from-issue will fill in.
    augmented_body = f"Tracks: #{parent}\n\n{body.rstrip()}\n"
    if output == "spec":
        augmented_body += "\nSpec: (to be filled by /spec-from-issue)\n"

    return ForkDecision(
        kind="create", reason="ready to fork",
        repo=repo, parent=parent, title=title,
        body=augmented_body, labels=list(labels),
    )


def execute_fork(gh, decision: ForkDecision) -> int:
    """Execute a 'create' decision against gh and post pointer comment."""
    if decision.kind != "create":
        raise ValueError(f"cannot execute non-create decision: {decision.reason}")
    new_num = gh.issue_create(
        decision.repo, decision.title, decision.body, decision.labels,
    )
    gh.issue_comment(
        decision.repo, decision.parent,
        f"Triage forked child #{new_num} (`{', '.join(decision.labels)}`).",
    )
    return new_num


# --- entry point ------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--parent", type=int, required=True)
    p.add_argument("--kind", required=True,
                   choices=["bug", "chore", "feature", "spec"])
    p.add_argument("--output", required=True, choices=["tracking", "spec"])
    p.add_argument("--title", required=True)
    p.add_argument("--body-file", required=True,
                   help="path to a file holding the child-issue body")
    p.add_argument("--label", action="append", default=[],
                   help="label to apply (may repeat)")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    body = Path(args.body_file).read_text()
    gh = GhCli()
    decision = plan_fork(
        gh, repo=args.repo, parent=args.parent,
        kind=args.kind, output=args.output,
        title=args.title, body=body,
        labels=list(args.label), force=args.force,
    )
    if decision.kind == "skip":
        sys.stderr.write(f"triage-fork: skipped — {decision.reason}\n")
        sys.exit(2)
    new_num = execute_fork(gh, decision)
    print(new_num)


if __name__ == "__main__":
    main()
```

```bash
chmod +x /workspaces/ocr-container/scripts/triage-fork.py
```

- [ ] **Step 4: Run the tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_triage_fork.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/triage-fork.py tests/scripts/test_triage_fork.py
git commit -m "feat(triage): scripts/triage-fork.py — idempotent child-issue forking"
```

---

## Task 11: Write the /triage SKILL.md

**Files:**

- Create: `.claude/skills/triage/SKILL.md`

The skill is interactive prose orchestrating the agent through the triage decision and then calling `triage-fork.py`.

- [ ] **Step 1: Write the SKILL.md**

Save as `.claude/skills/triage/SKILL.md`:

````markdown
---
name: triage
description: Triage a kind:feature-request issue. Reads the feature-request, decides approve/reject and (if approve) tracking-vs-spec, forks the right child issue, applies triage:* labels, and posts a reasoning comment. Use when CT invokes `/triage <N>`.
---

# triage

Triage one `kind:feature-request` issue. End state: the parent gets `triage:approved` or `triage:rejected` (and `triage:needs-spec` when applicable), one child issue is forked (tracking or spec), and a reasoning comment is posted on the parent.

## Required arguments

- The user passes the issue number as `/triage <N>`.
- The active repo is the cwd's `git remote get-url origin` (resolves to `ConcaveTrillion/<repo>`).

## Workflow

1. **Resolve repo and load the issue.**

   ```bash
   REPO=$(git remote get-url origin | sed -E 's#.*github\.com[:/](.*)\.git#\1#')
   gh issue view <N> --repo "$REPO" --json number,title,body,labels,author
   ```

2. **Verify it's a fresh feature-request.**
   - Must carry `kind:feature-request`.
   - Must NOT already carry `triage:approved` or `triage:rejected`. If it does and `--force` was not passed, abort with: "already triaged; pass --force to re-triage".

3. **Read the body and decide classification.**

   Decision tree (matches the spec's sizing heuristic, subject to iteration):
   - **Reject** if duplicate of an existing issue, or out of scope, or scoped to a different repo. Look for dups: `gh issue list --repo "$REPO" --search "<keywords>" --json number,title`.
   - **Approve, ship-direct** if the work is one focused change: estimated effort ≤ S, ≤ 2 files, no new public API. Output kind: `tracking`.
   - **Approve, needs-spec** otherwise. Output kind: `spec`.

4. **Compose the child-issue title and body.**

   Tracking children should have a one-sentence body summarizing what they do, plus an `Acceptance:` checklist that ship-issue can pick up. Spec children should have a body that names the feature and the open design questions; do NOT write the spec itself here — that's `/spec-from-issue`'s job.

   Save the body to a tempfile so `triage-fork.py` can read it without quoting headaches:

   ```bash
   cat > /tmp/triage-<N>-body.md <<'EOF'
   <body content here>
   EOF
   ```

5. **Determine target labels for the child.**

   - Tracking child: `kind:<bug|chore|feature>`, `effort:<S|M|L>`, `model:<haiku|sonnet|opus>`, `model-effort:<low|medium|high|xhigh|max>`, `status:backlog`. Do NOT add `bot:ship-issue-ready` — CT arms it manually after review.
   - Spec child: `kind:spec`, `effort:<S|M|L>`, `status:backlog`. Spec children don't need model labels (the work is `/spec-from-issue`, not `/ship-issue`).

6. **Call triage-fork.py.**

   ```bash
   /workspaces/ocr-container/scripts/triage-fork.py \
     --repo "$REPO" --parent <N> \
     --kind <bug|chore|feature|spec> --output <tracking|spec> \
     --title "<title>" \
     --body-file /tmp/triage-<N>-body.md \
     --label kind:<x> --label effort:<x> [--label model:<x> --label model-effort:<x>] \
     --label status:backlog
   ```

   Capture the new issue number from stdout. If exit code is 2, the parent already has a child — surface the message and stop.

7. **Update the parent's labels.**

   ```bash
   gh issue edit <N> --repo "$REPO" \
     --add-label triage:approved \
     [--add-label triage:needs-spec]   # only when output=spec
     --remove-label triage:proposed-by-agent   # if present
   ```

   For rejection (no child fork was made):

   ```bash
   gh issue edit <N> --repo "$REPO" --add-label triage:rejected
   ```

8. **Post the reasoning comment on the parent.**

   ```bash
   gh issue comment <N> --repo "$REPO" --body "<comment>"
   ```

   The comment explains *why* this classification (1-3 sentences). The pointer-comment naming the child is already posted by `triage-fork.py`.

## Constraints

- **Idempotent.** Refuses on a parent that already carries `triage:approved` or `triage:rejected` unless `--force`.
- **Single child per parent.** The forked child carries `Tracks: #<parent>`; `triage-fork.py` enforces no duplicate.
- **No `bot:ship-issue-ready` on the child.** That label is CT's eligibility gate; agents never apply it.
- **No spec writing here.** Spec children are placeholders. The actual spec is written by `/spec-from-issue`.
- **CT-interactive only.** This skill runs in `vscode` user's interactive session. Not invokable by `claude-bot`.

## Anti-patterns

- Triaging from the issue title alone — read the full body and the related code.
- Approving a sprawling idea as `tracking` because it "feels small" — when in doubt, use `spec` and let `/decompose-spec` size it later.
- Forgetting `triage:needs-spec` on spec-output children — the chain-state report keys on it.
- Filing the child against a different repo — v1 is per-repo locality only.
````

- [ ] **Step 2: Quick smoke check**

```bash
cd /workspaces/ocr-container
python3 -c "
from pathlib import Path
md = Path('.claude/skills/triage/SKILL.md').read_text()
assert md.startswith('---'), 'missing frontmatter'
assert 'name: triage' in md
assert 'description:' in md
"
```

Expected: no error.

- [ ] **Step 3: Commit**

```bash
cd /workspaces/ocr-container
git add .claude/skills/triage/SKILL.md
git commit -m "feat(skills): add /triage SKILL.md (CT-interactive feature-request triage)"
```

---

## Task 12: Build spec-from-issue-finalize.py

**Files:**

- Create: `scripts/spec-from-issue-finalize.py`
- Create: `tests/scripts/test_spec_from_issue_finalize.py`

The finalizer takes a written spec file path and the spec issue number, opens a draft PR for the spec file, and edits the spec issue's body to add a `Spec: <path>` line. The brainstorming + actual spec writing happens in the SKILL.md (next task).

- [ ] **Step 1: Write the failing tests**

Save as `tests/scripts/test_spec_from_issue_finalize.py`:

```python
"""Tests for scripts/spec-from-issue-finalize.py."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/spec-from-issue-finalize.py"


def _mod():
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    spec = importlib.util.spec_from_file_location("spec_from_issue_finalize", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FakeGh:
    def __init__(self, issue_body=""):
        self.issue_body = issue_body
        self.body_edits = []

    def issue_view(self, repo, number):
        return {"number": number, "body": self.issue_body, "title": "Spec: foo"}

    def issue_edit_body(self, repo, number, new_body):
        self.body_edits.append({"number": number, "body": new_body})
        self.issue_body = new_body


def test_adds_spec_line_when_missing():
    m = _mod()
    gh = FakeGh(issue_body="Tracks: #42\n\nWrite the spec.\n")
    decision = m.plan_finalize(
        gh, repo="x/y", spec_issue=43,
        spec_path="docs/specs/2026-05-10-foo.md",
        force=False,
    )
    assert decision.kind == "edit"
    new_body = decision.new_body
    assert "Spec: docs/specs/2026-05-10-foo.md" in new_body
    assert "Tracks: #42" in new_body  # original preserved


def test_refuses_when_spec_line_already_present():
    m = _mod()
    gh = FakeGh(issue_body="Tracks: #42\n\nSpec: docs/specs/foo.md\n")
    decision = m.plan_finalize(
        gh, repo="x/y", spec_issue=43,
        spec_path="docs/specs/2026-05-10-foo.md",
        force=False,
    )
    assert decision.kind == "skip"
    assert "Spec:" in decision.reason


def test_force_replaces_existing_spec_line():
    m = _mod()
    gh = FakeGh(issue_body="Tracks: #42\n\nSpec: docs/specs/old.md\n")
    decision = m.plan_finalize(
        gh, repo="x/y", spec_issue=43,
        spec_path="docs/specs/2026-05-10-new.md",
        force=True,
    )
    assert decision.kind == "edit"
    assert "Spec: docs/specs/2026-05-10-new.md" in decision.new_body
    assert "Spec: docs/specs/old.md" not in decision.new_body
```

- [ ] **Step 2: Run the test — confirm it fails**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_spec_from_issue_finalize.py -v
```

Expected: file not found.

- [ ] **Step 3: Implement spec-from-issue-finalize.py**

Save as `scripts/spec-from-issue-finalize.py`:

```python
#!/usr/bin/env python3
"""spec-from-issue-finalize.py — wire a written spec file to its issue.

Called by /spec-from-issue AFTER the agent has used the brainstorming
skill to write the spec file at <spec_path>. This script:

  1. Edits the spec issue body to add `Spec: <path>` (if missing).
  2. Opens a draft PR titled "spec: <issue title>" against main, with the
     issue # in the body so the auto-link works.

Idempotent: refuses if the spec issue body already has a Spec: line,
unless --force.

Usage:
  scripts/spec-from-issue-finalize.py \\
    --repo pdomain/pdomain-book-tools --spec-issue 43 \\
    --spec-path docs/specs/2026-05-10-foo.md
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_SPEC_LINE = re.compile(r"^Spec:\s*\S.*$", re.MULTILINE)


def _gh_env() -> dict:
    env = os.environ.copy()
    token_path = "/run/secrets/gh-token-pd"
    if Path(token_path).is_file():
        env["GH_TOKEN"] = Path(token_path).read_text().strip()
    return env


class GhCli:
    def issue_view(self, repo, number):
        r = subprocess.run(
            ["gh", "issue", "view", str(number), "--repo", repo,
             "--json", "number,body,title"],
            capture_output=True, text=True, env=_gh_env(),
            check=True, timeout=30,
        )
        return json.loads(r.stdout)

    def issue_edit_body(self, repo, number, new_body):
        subprocess.run(
            ["gh", "issue", "edit", str(number), "--repo", repo,
             "--body", new_body],
            capture_output=True, text=True, env=_gh_env(),
            check=True, timeout=30,
        )

    def pr_create_draft(self, repo, title, body, head, base="main"):
        r = subprocess.run(
            ["gh", "pr", "create", "--repo", repo, "--draft",
             "--title", title, "--body", body,
             "--head", head, "--base", base],
            capture_output=True, text=True, env=_gh_env(),
            check=True, timeout=30,
        )
        return r.stdout.strip().splitlines()[-1]


@dataclasses.dataclass
class FinalizeDecision:
    kind: str  # "edit" or "skip"
    reason: str
    new_body: str | None
    issue_title: str | None


def plan_finalize(gh, *, repo: str, spec_issue: int, spec_path: str,
                  force: bool) -> FinalizeDecision:
    issue = gh.issue_view(repo, spec_issue)
    body = issue.get("body") or ""
    title = issue.get("title") or ""

    if _SPEC_LINE.search(body) and not force:
        return FinalizeDecision(
            kind="skip", reason="spec issue body already has a Spec: line",
            new_body=None, issue_title=title,
        )

    if force:
        new_body = _SPEC_LINE.sub(f"Spec: {spec_path}", body, count=1)
        if not _SPEC_LINE.search(new_body):
            new_body = body.rstrip() + f"\n\nSpec: {spec_path}\n"
    else:
        new_body = body.rstrip() + f"\n\nSpec: {spec_path}\n"

    return FinalizeDecision(
        kind="edit", reason="spec wired", new_body=new_body, issue_title=title,
    )


def execute_finalize(gh, *, repo: str, spec_issue: int, decision: FinalizeDecision,
                     spec_path: str, head_branch: str | None) -> str | None:
    """Apply the body edit and open a draft PR if a head branch is given."""
    if decision.kind != "edit":
        return None
    gh.issue_edit_body(repo, spec_issue, decision.new_body)

    if head_branch is None:
        return None
    pr_body = (
        f"Spec for issue #{spec_issue}.\n\n"
        f"Closes #{spec_issue} when merged.\n"
    )
    return gh.pr_create_draft(
        repo, title=f"spec: {decision.issue_title or '(unnamed)'}",
        body=pr_body, head=head_branch, base="main",
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--spec-issue", type=int, required=True)
    p.add_argument("--spec-path", required=True)
    p.add_argument("--head-branch", default=None,
                   help="branch to open draft PR from; if omitted, no PR")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    gh = GhCli()
    decision = plan_finalize(
        gh, repo=args.repo, spec_issue=args.spec_issue,
        spec_path=args.spec_path, force=args.force,
    )
    if decision.kind == "skip":
        sys.stderr.write(f"spec-from-issue-finalize: skipped — {decision.reason}\n")
        sys.exit(2)
    pr_url = execute_finalize(
        gh, repo=args.repo, spec_issue=args.spec_issue,
        decision=decision, spec_path=args.spec_path,
        head_branch=args.head_branch,
    )
    if pr_url:
        print(pr_url)


if __name__ == "__main__":
    main()
```

```bash
chmod +x /workspaces/ocr-container/scripts/spec-from-issue-finalize.py
```

- [ ] **Step 4: Run the tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_spec_from_issue_finalize.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/spec-from-issue-finalize.py tests/scripts/test_spec_from_issue_finalize.py
git commit -m "feat(spec-from-issue): finalize.py wires spec file to its tracking issue"
```

---

## Task 13: Write the /spec-from-issue SKILL.md

**Files:**

- Create: `.claude/skills/spec-from-issue/SKILL.md`

- [ ] **Step 1: Write the SKILL.md**

Save as `.claude/skills/spec-from-issue/SKILL.md`:

````markdown
---
name: spec-from-issue
description: Write a design spec for a kind:spec issue using brainstorming, save the spec file with the standard 9-section template, and wire it back to the spec issue (Spec: body line + draft PR). Use when CT invokes `/spec-from-issue <N>`.
---

# spec-from-issue

Write the spec file for one `kind:spec` issue. End state: a new spec markdown exists under `docs/specs/` (or `docs/superpowers/specs/` for workspace specs), the spec issue body carries `Spec: <path>`, and a draft PR is open against `main`.

## Required arguments

- The user passes the issue number as `/spec-from-issue <N>`.
- Active repo is `git remote get-url origin`.

## Workflow

1. **Load the spec issue.**

   ```bash
   REPO=$(git remote get-url origin | sed -E 's#.*github\.com[:/](.*)\.git#\1#')
   gh issue view <N> --repo "$REPO" --json number,title,body,labels
   ```

   Verify it carries `kind:spec`. Verify body does NOT already have a `Spec: ` line; if it does, abort: "spec already wired; use --force only after confirming with CT".

2. **Brainstorm the design.**

   Invoke the `superpowers:brainstorming` skill scoped to:
   - The spec issue body
   - The `Tracks: #<parent>` parent (read it for context)
   - Recent code under the relevant repo paths

   Brainstorming should converge on a design before any spec text is written. Take notes; do not skip ahead.

3. **Pick the spec file path.**

   - Per-repo specs: `<repo>/docs/specs/YYYY-MM-DD-<topic>-design.md`
   - Workspace specs: `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
   - Convention: lowercase, dash-separated topic; `-design.md` suffix.

4. **Write the spec file using the standard 9-section template.**

   Copy the structure from `scripts/migrate-legacy-spec-auto.py` (REQUIRED_HEADINGS list). The required H2s are: TL;DR, Context, Constraints, Decision, Contract / Acceptance, Trade-offs considered, Consequences, Open questions, References.

   Add the optional header line directly under the H1:

   ```markdown
   # <Spec title>

   > **Status**: Draft
   > **Last updated**: YYYY-MM-DD
   > **Spec-Issue**: ConcaveTrillion/<repo>#<N>
   ```

   The `Spec-Issue:` line is what makes `/decompose-spec` skip backfill mode.

5. **Lint the spec.**

   ```bash
   python3 /workspaces/ocr-container/scripts/lint-spec.py <spec-path>
   ```

   Expected: exit 0. If it fails, follow `superpowers:fixing-specs` Procedure 1-3 to repair before continuing.

6. **Create a branch and commit the spec.**

   ```bash
   BRANCH="spec/$(basename <spec-path> .md)"
   git checkout -b "$BRANCH"
   git add <spec-path>
   git commit -m "spec: <topic> (#<N>)"
   git push -u origin "$BRANCH"
   ```

   For workspace specs the push is to the `ocr-container` repo's main remote (run from `/workspaces/ocr-container`); for per-repo specs the push is to the per-repo remote (run from `/workspaces/ocr-container/<repo>`).

   *Note for the bot user:* this skill is CT-interactive only. The bot is not authorized to push from arbitrary branches; ignore this section if you somehow find yourself executing this skill as `claude-bot` and bounce.

7. **Wire the spec to its issue + open the draft PR.**

   ```bash
   /workspaces/ocr-container/scripts/spec-from-issue-finalize.py \
     --repo "$REPO" --spec-issue <N> \
     --spec-path <spec-path-relative-to-repo-root> \
     --head-branch "$BRANCH"
   ```

   This edits the spec issue body to add `Spec: <path>` and opens a draft PR. Captures the PR URL on stdout.

## Constraints

- **Idempotent on the issue.** Refuses if `Spec: ` is already in the issue body.
- **Lint must pass.** Don't open the PR if `lint-spec.py` rejects.
- **Follow the 9-section template.** Empty section: write `_(none)_` underneath, do not omit the heading.
- **CT-interactive only.** Brainstorming requires user collaboration; the bot user is not authorized to run this skill.

## Anti-patterns

- Skipping `superpowers:brainstorming` and writing the spec from scratch.
- Diverging from the 9-section template "to fit this case".
- Filing the PR as ready-for-review (always `--draft`; `gh pr create --draft` is enforced by the hook).
- Forgetting the `Spec-Issue:` blockquote line — `/decompose-spec` will treat the spec as a backfill candidate.
````

- [ ] **Step 2: Smoke-check the SKILL.md**

```bash
python3 -c "
from pathlib import Path
md = Path('/workspaces/ocr-container/.claude/skills/spec-from-issue/SKILL.md').read_text()
assert md.startswith('---')
assert 'name: spec-from-issue' in md
assert '9-section template' in md
"
```

Expected: no error.

- [ ] **Step 3: Commit**

```bash
cd /workspaces/ocr-container
git add .claude/skills/spec-from-issue/SKILL.md
git commit -m "feat(skills): add /spec-from-issue SKILL.md (brainstorm + write spec + draft PR)"
```

---

## Task 14: Build decompose-spec-plan.py

**Files:**

- Create: `scripts/decompose-spec-plan.py`
- Create: `tests/scripts/test_decompose_spec_plan.py`

The planner reads a spec file, parses for the `Spec-Issue:` blockquote header, and emits a JSON proposal listing children to file. It does not call `gh` (read-only). The agent presents the proposal to CT in the chat; CT edits/confirms; then `decompose-spec-apply.py` (next task) does the writes.

- [ ] **Step 1: Write the failing tests**

Save as `tests/scripts/test_decompose_spec_plan.py`:

```python
"""Tests for scripts/decompose-spec-plan.py."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/decompose-spec-plan.py"


def _mod():
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    spec = importlib.util.spec_from_file_location("decompose_spec_plan", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SPEC_WITH_HEADER = """\
# Foo design

> **Status**: Draft
> **Last updated**: 2026-05-10
> **Spec-Issue**: pdomain/pdomain-book-tools#43

## TL;DR

Three new helpers.

## Decision

### Helper A

Do X.

### Helper B

Do Y.

### Helper C

Do Z.

## Contract / Acceptance

- [ ] Helper A passes its tests
- [ ] Helper B passes its tests
- [ ] Helper C passes its tests
"""

SPEC_WITHOUT_HEADER = SPEC_WITH_HEADER.replace(
    "> **Spec-Issue**: pdomain/pdomain-book-tools#43\n", ""
)


def _write_spec(text: str) -> Path:
    p = Path(tempfile.mkdtemp()) / "spec.md"
    p.write_text(text)
    return p


def test_extracts_spec_issue_when_present():
    m = _mod()
    p = _write_spec(SPEC_WITH_HEADER)
    plan = m.build_plan(p, output="tracking")
    assert plan["spec_issue"] == {"repo": "pdomain/pdomain-book-tools", "number": 43}
    assert plan["backfill"] is False


def test_marks_backfill_when_header_missing():
    m = _mod()
    p = _write_spec(SPEC_WITHOUT_HEADER)
    plan = m.build_plan(p, output="tracking")
    assert plan["backfill"] is True
    assert plan["spec_issue"] is None


def test_proposes_one_child_per_decision_subsection():
    m = _mod()
    p = _write_spec(SPEC_WITH_HEADER)
    plan = m.build_plan(p, output="tracking")
    titles = [c["title"] for c in plan["children"]]
    assert any("Helper A" in t for t in titles)
    assert any("Helper B" in t for t in titles)
    assert any("Helper C" in t for t in titles)


def test_tracking_output_assigns_kind_chore():
    m = _mod()
    p = _write_spec(SPEC_WITH_HEADER)
    plan = m.build_plan(p, output="tracking")
    for c in plan["children"]:
        assert c["kind"] in {"chore", "feature", "bug"}


def test_feature_request_output_uses_kind_feature_request():
    m = _mod()
    p = _write_spec(SPEC_WITH_HEADER)
    plan = m.build_plan(p, output="feature-requests")
    for c in plan["children"]:
        assert c["kind"] == "feature-request"


def test_milestone_title_present_for_non_backfill():
    m = _mod()
    p = _write_spec(SPEC_WITH_HEADER)
    plan = m.build_plan(p, output="tracking")
    assert plan["milestone_title"] == "spec: foo-design (#43)"


def test_milestone_title_omitted_for_backfill_until_issue_filed():
    m = _mod()
    p = _write_spec(SPEC_WITHOUT_HEADER)
    plan = m.build_plan(p, output="tracking")
    assert plan["milestone_title"] is None


def test_plan_round_trips_through_json():
    m = _mod()
    p = _write_spec(SPEC_WITH_HEADER)
    plan = m.build_plan(p, output="tracking")
    s = json.dumps(plan)
    plan2 = json.loads(s)
    assert plan2 == plan
```

- [ ] **Step 2: Run the test — confirm it fails**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_decompose_spec_plan.py -v
```

Expected: file not found.

- [ ] **Step 3: Implement decompose-spec-plan.py**

Save as `scripts/decompose-spec-plan.py`:

```python
#!/usr/bin/env python3
"""decompose-spec-plan.py — read a spec, propose children as JSON.

Stage 1 of /decompose-spec. Pure: no gh calls, no writes. Output is a
JSON document the SKILL.md presents to CT for review/edit. Stage 2
(decompose-spec-apply.py) consumes the (possibly edited) JSON and writes
to GitHub.

Plan shape:

  {
    "spec_path": "docs/specs/2026-05-10-foo.md",
    "spec_issue": {"repo": "pdomain/pdomain-book-tools", "number": 43} | null,
    "backfill": true|false,                 # null spec_issue → backfill mode
    "output": "tracking" | "feature-requests" | "mixed",
    "milestone_title": "spec: foo (#43)" | null,
    "children": [
      {
        "title": "...",
        "body": "...",
        "kind": "chore" | "feature" | "bug" | "spec" | "feature-request",
        "labels": ["kind:chore", "effort:M", ...],
      },
      ...
    ]
  }

The SKILL.md is responsible for the agent's heuristic of "what does each
Decision subsection mean for issue-filing"; the helper just enumerates
the structural sub-headings (### under ## Decision) and fills in
defaults that CT then edits.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Ensure scripts/ is importable so we can pull in spec_slug.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import spec_slug

_HEADER_LINE = re.compile(
    r"^>\s*\*\*Spec-Issue\*\*:\s*([^\s/]+/[^\s#]+)#(\d+)\s*$",
    re.MULTILINE,
)
_DECISION_SECTION = re.compile(
    r"^##\s+Decision\s*$(.*?)(?=^##\s+|\Z)",
    re.MULTILINE | re.DOTALL,
)
_SUBSECTION = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
_H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)

_VALID_OUTPUTS = {"tracking", "feature-requests", "mixed"}


def _parse_spec_issue(content: str) -> dict | None:
    m = _HEADER_LINE.search(content)
    if not m:
        return None
    return {"repo": m.group(1), "number": int(m.group(2))}


def _spec_h1(content: str) -> str:
    m = _H1.search(content)
    return m.group(1).strip() if m else "(unnamed spec)"


def _enumerate_decision_subsections(content: str) -> list[str]:
    m = _DECISION_SECTION.search(content)
    if not m:
        return []
    return [s.strip() for s in _SUBSECTION.findall(m.group(1))]


def _default_kind_for_output(output: str) -> str:
    if output == "feature-requests":
        return "feature-request"
    return "chore"


def _default_labels(kind: str) -> list[str]:
    if kind == "feature-request":
        return ["kind:feature-request", "status:backlog"]
    if kind == "spec":
        return ["kind:spec", "effort:M", "status:backlog"]
    return [f"kind:{kind}", "effort:S", "model:haiku",
            "model-effort:low", "status:backlog"]


def build_plan(spec_path: Path, *, output: str) -> dict:
    if output not in _VALID_OUTPUTS:
        raise ValueError(f"invalid output: {output!r}; allowed: {sorted(_VALID_OUTPUTS)}")

    content = spec_path.read_text()
    spec_issue = _parse_spec_issue(content)
    backfill = spec_issue is None

    h1 = _spec_h1(content)
    subsections = _enumerate_decision_subsections(content)
    if not subsections:
        # Fall back to a single child covering the whole spec.
        subsections = [h1]

    children = []
    for sub in subsections:
        kind = _default_kind_for_output(output)
        children.append({
            "title": sub if output == "feature-requests" else f"{h1}: {sub}",
            "body": (
                f"Source spec: {spec_path}\n\n"
                f"Section: {sub}\n\n"
                "(Edit this body before applying. /decompose-spec is a proposal stage.)\n"
            ),
            "kind": kind,
            "labels": _default_labels(kind),
        })

    if spec_issue is not None:
        milestone_title = spec_slug.milestone_title(h1, spec_issue["number"])
    else:
        milestone_title = None

    return {
        "spec_path": str(spec_path),
        "spec_issue": spec_issue,
        "backfill": backfill,
        "output": output,
        "milestone_title": milestone_title,
        "children": children,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--spec", required=True, help="path to the spec markdown file")
    p.add_argument("--output", default="tracking",
                   choices=sorted(_VALID_OUTPUTS))
    args = p.parse_args()

    plan = build_plan(Path(args.spec), output=args.output)
    json.dump(plan, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
```

```bash
chmod +x /workspaces/ocr-container/scripts/decompose-spec-plan.py
```

- [ ] **Step 4: Run the tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_decompose_spec_plan.py -v
```

Expected: 8 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/decompose-spec-plan.py tests/scripts/test_decompose_spec_plan.py
git commit -m "feat(decompose-spec): plan.py — read spec, propose children + milestone title"
```

---

## Task 15: Build decompose-spec-apply.py (with milestone creation)

**Files:**

- Create: `scripts/decompose-spec-apply.py`
- Create: `tests/scripts/test_decompose_spec_apply.py`

The applier consumes the JSON plan (possibly edited by CT), files children via `gh issue create`, ensures the milestone exists, and assigns each new child to the milestone. Diff-mode: if `--diff` is passed, only file children whose `Tracks: #M` is not already present.

- [ ] **Step 1: Write the failing tests**

Save as `tests/scripts/test_decompose_spec_apply.py`:

```python
"""Tests for scripts/decompose-spec-apply.py."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/decompose-spec-apply.py"


def _mod():
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    spec = importlib.util.spec_from_file_location("decompose_spec_apply", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FakeGh:
    def __init__(self, milestones=None, existing_issues=None):
        self.milestones = list(milestones or [])
        self.existing_issues = list(existing_issues or [])
        self.created_issues = []
        self.created_milestones = []

    def list_milestones(self, repo):
        return list(self.milestones)

    def create_milestone(self, repo, title, description):
        n = 100 + len(self.created_milestones)
        rec = {"number": n, "title": title, "description": description, "state": "open"}
        self.created_milestones.append(rec)
        self.milestones.append(rec)
        return n

    def issue_list(self, repo, label=None, state="open", limit=200):
        return list(self.existing_issues)

    def issue_create(self, repo, title, body, labels, milestone_number=None):
        n = 200 + len(self.created_issues)
        rec = {"number": n, "title": title, "body": body, "labels": labels,
               "milestone": milestone_number}
        self.created_issues.append(rec)
        return n


def _plan(repo="pdomain/pdomain-book-tools", number=43, backfill=False,
          children=None, milestone_title="spec: foo-design (#43)"):
    return {
        "spec_path": "docs/specs/2026-05-10-foo.md",
        "spec_issue": None if backfill else {"repo": repo, "number": number},
        "backfill": backfill,
        "output": "tracking",
        "milestone_title": milestone_title,
        "children": children or [
            {"title": "Foo: A", "body": "Do A", "kind": "chore",
             "labels": ["kind:chore", "effort:S"]},
            {"title": "Foo: B", "body": "Do B", "kind": "chore",
             "labels": ["kind:chore", "effort:S"]},
        ],
    }


def test_creates_milestone_then_files_children():
    m = _mod()
    gh = FakeGh()
    plan = _plan()
    summary = m.apply_plan(gh, plan, dry_run=False)

    assert len(gh.created_milestones) == 1
    assert gh.created_milestones[0]["title"] == "spec: foo-design (#43)"
    assert len(gh.created_issues) == 2
    for issue in gh.created_issues:
        assert issue["milestone"] == 100  # number from FakeGh
        assert "Tracks: #43" in issue["body"]
        assert "Spec: docs/specs/2026-05-10-foo.md" in issue["body"]
    assert summary["children_filed"] == 2


def test_reuses_existing_milestone_by_title():
    m = _mod()
    gh = FakeGh(milestones=[
        {"number": 7, "title": "spec: foo-design (#43)", "state": "open"},
    ])
    plan = _plan()
    m.apply_plan(gh, plan, dry_run=False)

    assert gh.created_milestones == []
    for issue in gh.created_issues:
        assert issue["milestone"] == 7


def test_diff_mode_skips_already_filed_children():
    m = _mod()
    gh = FakeGh(existing_issues=[
        {"number": 99, "title": "Foo: A",
         "body": "Tracks: #43\nSpec: docs/specs/2026-05-10-foo.md\n",
         "labels": []},
    ])
    plan = _plan()
    summary = m.apply_plan(gh, plan, dry_run=False, diff=True)
    assert summary["children_filed"] == 1  # only "Foo: B" filed
    assert all("Foo: B" in i["title"] for i in gh.created_issues)


def test_dry_run_makes_no_writes():
    m = _mod()
    gh = FakeGh()
    plan = _plan()
    summary = m.apply_plan(gh, plan, dry_run=True)
    assert gh.created_milestones == []
    assert gh.created_issues == []
    assert summary["dry_run"] is True
    assert summary["would_create_milestone"] == "spec: foo-design (#43)"
    assert summary["would_file_children"] == 2


def test_backfill_without_milestone_title_skips_milestone():
    m = _mod()
    gh = FakeGh()
    plan = _plan(backfill=True, milestone_title=None)
    plan["children"][0]["body"] = "Source spec: docs/specs/foo.md"  # no Tracks line yet
    summary = m.apply_plan(gh, plan, dry_run=False)
    assert gh.created_milestones == []
    for issue in gh.created_issues:
        assert issue["milestone"] is None


def test_feature_request_output_routes_to_kind_feature_request():
    m = _mod()
    gh = FakeGh()
    plan = _plan()
    plan["output"] = "feature-requests"
    plan["children"] = [
        {"title": "Cluster A", "body": "...", "kind": "feature-request",
         "labels": ["kind:feature-request"]},
    ]
    m.apply_plan(gh, plan, dry_run=False)
    assert "kind:feature-request" in gh.created_issues[0]["labels"]
```

- [ ] **Step 2: Run the test — confirm it fails**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_decompose_spec_apply.py -v
```

Expected: file not found.

- [ ] **Step 3: Implement decompose-spec-apply.py**

Save as `scripts/decompose-spec-apply.py`:

```python
#!/usr/bin/env python3
"""decompose-spec-apply.py — apply a confirmed plan from decompose-spec-plan.

Stage 2 of /decompose-spec. Reads the JSON plan (possibly edited by CT),
ensures the milestone exists in the target repo, and files each child
issue assigned to that milestone. Diff-mode (--diff) skips children that
already exist (matched by Tracks: #<spec_issue> + title).

Usage:
  scripts/decompose-spec-apply.py --plan-json /tmp/plan.json [--diff] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spec_slug  # noqa: E402  re-exported for callers


def _gh_env() -> dict:
    env = os.environ.copy()
    token_path = "/run/secrets/gh-token-pd"
    if Path(token_path).is_file():
        env["GH_TOKEN"] = Path(token_path).read_text().strip()
    return env


class GhCli:
    def list_milestones(self, repo):
        # gh api gives the full milestone list; --json flag is not exposed for milestones.
        r = subprocess.run(
            ["gh", "api", f"/repos/{repo}/milestones?state=all&per_page=200"],
            capture_output=True, text=True, env=_gh_env(),
            check=True, timeout=30,
        )
        return json.loads(r.stdout)

    def create_milestone(self, repo, title, description):
        r = subprocess.run(
            ["gh", "api", "--method", "POST", f"/repos/{repo}/milestones",
             "-f", f"title={title}",
             "-f", f"description={description or ''}"],
            capture_output=True, text=True, env=_gh_env(),
            check=True, timeout=30,
        )
        return int(json.loads(r.stdout)["number"])

    def issue_list(self, repo, label=None, state="open", limit=200):
        cmd = ["gh", "issue", "list", "--repo", repo, "--state", state,
               "--limit", str(limit), "--json", "number,title,body,labels"]
        if label:
            cmd += ["--label", label]
        r = subprocess.run(cmd, capture_output=True, text=True, env=_gh_env(),
                           check=True, timeout=30)
        return json.loads(r.stdout)

    def issue_create(self, repo, title, body, labels, milestone_number=None):
        cmd = ["gh", "issue", "create", "--repo", repo,
               "--title", title, "--body", body]
        for lbl in labels:
            cmd += ["--label", lbl]
        if milestone_number is not None:
            cmd += ["--milestone", str(milestone_number)]
        r = subprocess.run(cmd, capture_output=True, text=True, env=_gh_env(),
                           check=True, timeout=30)
        url = r.stdout.strip().splitlines()[-1]
        return int(url.rstrip("/").rsplit("/", 1)[-1])


def _ensure_milestone(gh, repo, title, description):
    """Return the milestone number, creating it if needed. Idempotent by exact title."""
    for ms in gh.list_milestones(repo):
        if ms.get("title") == title:
            return ms["number"]
    return gh.create_milestone(repo, title, description)


def _augmented_body(plan: dict, child: dict) -> str:
    body = child.get("body", "").rstrip()
    extras: list[str] = []
    if plan.get("spec_issue"):
        extras.append(f"Tracks: #{plan['spec_issue']['number']}")
    extras.append(f"Spec: {plan['spec_path']}")
    return body + "\n\n" + "\n".join(extras) + "\n"


def _is_already_filed(existing_issues: list[dict], child_title: str,
                      tracks_marker: str | None) -> bool:
    for issue in existing_issues:
        if tracks_marker and tracks_marker in (issue.get("body") or ""):
            if issue.get("title") == child_title:
                return True
    return False


def apply_plan(gh, plan: dict, *, dry_run: bool, diff: bool = False) -> dict:
    """Apply a JSON plan against gh. Returns a summary dict for the SKILL."""
    repo = (plan.get("spec_issue") or {}).get("repo")
    children = plan.get("children", [])
    milestone_title = plan.get("milestone_title")

    if dry_run:
        return {
            "dry_run": True,
            "would_create_milestone": milestone_title,
            "would_file_children": len(children),
        }

    if not repo and plan.get("output") in ("tracking", "feature-requests"):
        # Backfill mode WITH no spec issue yet — caller must file the spec
        # issue first (handled in SKILL.md). We accept this in tests by
        # leaving spec_issue None and skipping milestone creation.
        repo = None

    milestone_number = None
    if milestone_title and repo:
        description = f"Spec file: {plan.get('spec_path', '')}\nSpec issue: #{(plan.get('spec_issue') or {}).get('number','?')}"
        milestone_number = _ensure_milestone(gh, repo, milestone_title, description)

    existing = gh.issue_list(repo) if (diff and repo) else []
    tracks_marker = (
        f"Tracks: #{plan['spec_issue']['number']}" if plan.get("spec_issue") else None
    )

    filed = 0
    for child in children:
        if diff and _is_already_filed(existing, child["title"], tracks_marker):
            continue
        body = _augmented_body(plan, child)
        gh.issue_create(
            repo, child["title"], body, child.get("labels", []),
            milestone_number=milestone_number,
        )
        filed += 1

    return {
        "dry_run": False,
        "milestone_number": milestone_number,
        "children_filed": filed,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--plan-json", required=True,
                   help="path to a plan JSON (output of decompose-spec-plan.py, possibly edited)")
    p.add_argument("--diff", action="store_true",
                   help="skip children whose Tracks:+title pair already exists")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    plan = json.loads(Path(args.plan_json).read_text())
    gh = GhCli()
    summary = apply_plan(gh, plan, dry_run=args.dry_run, diff=args.diff)
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
```

```bash
chmod +x /workspaces/ocr-container/scripts/decompose-spec-apply.py
```

- [ ] **Step 4: Run the tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_decompose_spec_apply.py -v
```

Expected: 6 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/decompose-spec-apply.py tests/scripts/test_decompose_spec_apply.py
git commit -m "feat(decompose-spec): apply.py — file children + ensure milestone (idempotent)"
```

---

## Task 16: Write the /decompose-spec SKILL.md

**Files:**

- Create: `.claude/skills/decompose-spec/SKILL.md`

- [ ] **Step 1: Write the SKILL.md**

Save as `.claude/skills/decompose-spec/SKILL.md`:

````markdown
---
name: decompose-spec
description: Read a spec markdown file, propose child issues, present them to CT for review, then file the confirmed children + create a per-spec milestone. Use when CT invokes `/decompose-spec <path> [--output=tracking|feature-requests|mixed] [--backfill]`.
---

# decompose-spec

Decompose one spec file into N child issues, all attached to a per-spec GitHub milestone. End state: each new child has `Tracks: #<spec-issue>` + `Spec: <path>` body lines, the milestone titled `spec: <slug> (#<spec-issue>)` exists in the target repo, and every child is assigned to it.

## Required arguments

- `<path>` — the spec markdown file. Per-repo specs: `<repo>/docs/specs/...`. Workspace specs: `docs/superpowers/specs/...`.
- `--output=<tracking|feature-requests|mixed>` — child kind axis. Default: `tracking`. See spec for guidance.
- `--backfill` — required if the spec has no `> **Spec-Issue**:` header. Creates a retrospective spec issue first.
- `--apply` — actually file. Without this, decompose-spec runs as dry-run.
- `--diff` — file only children that don't already exist (rerun after partial failure or after CT files some manually).

## Workflow

### Stage 1 — propose

1. **Run the planner.**

   ```bash
   /workspaces/ocr-container/scripts/decompose-spec-plan.py \
     --spec <path> --output <output> > /tmp/plan.json
   ```

   The plan JSON has fields: `spec_issue`, `backfill`, `milestone_title`, `children[]`.

2. **Handle backfill if needed.**

   If `plan.backfill == true`:
   - File a retrospective `kind:spec` issue in the target repo. Title: derive from the spec file's H1. Body: `Backfill: pre-existing spec at <path>`. Labels: `kind:spec`, `status:backlog`. Capture the new issue number `M`.
   - Edit the spec markdown to add the blockquote header line below `> **Last updated**:`:
     ```
     > **Spec-Issue**: ConcaveTrillion/<repo>#M
     ```
   - Re-run the planner — `plan.spec_issue` is now populated and `plan.milestone_title` is set.

3. **Present the proposal to CT.**

   Format the children as a table in the chat:

   ```
   #  Title                           Kind     Labels
   1  Foo: Helper A                   chore    effort:S, model:haiku, model-effort:low, status:backlog
   2  Foo: Helper B                   chore    effort:M, model:sonnet, model-effort:medium, status:backlog
   ...
   ```

   For each row, CT can: edit title/body/labels, change kind, drop the row, or add a new row. Update `/tmp/plan.json` in place to reflect CT's edits.

### Stage 2 — apply

4. **Confirm and apply.**

   Show CT the final plan summary:

   ```
   Spec issue: #43 in pdomain/pdomain-book-tools
   Milestone: "spec: foo-design (#43)" (will be created if missing)
   Children to file: 3
   ```

   Wait for CT confirmation. Then:

   ```bash
   /workspaces/ocr-container/scripts/decompose-spec-apply.py \
     --plan-json /tmp/plan.json [--diff]
   ```

   The script ensures the milestone exists, then files each child. Output is a JSON summary with the milestone number and `children_filed` count.

5. **(Optional) re-run dry-mode for verification.**

   ```bash
   gh issue list --repo pdomain/pdomain-book-tools \
     --milestone "spec: foo-design (#43)" --json number,title,labels
   ```

   Expected: every confirmed child appears, attached to the milestone.

## Diff-mode (rerun after partial failure)

If `--apply` failed mid-flight (e.g., `gh` 5xx, network blip), re-run with `--diff`:

```bash
/workspaces/ocr-container/scripts/decompose-spec-apply.py \
  --plan-json /tmp/plan.json --diff
```

The script consults `Tracks: #<spec-issue>` in existing issues' bodies to skip already-filed children. The milestone is reused by exact title match. CT does not need to edit the plan again.

## Constraints

- **Idempotent.** Re-running with `--diff` files only missing children. Milestone reuse is by exact title; do not let CT edit the milestone title between runs.
- **Transactional confirm.** Always present the proposal table to CT before calling apply. Never auto-confirm.
- **Per-repo locality (v1).** All children land in the same repo as the spec issue. Cross-repo workspace specs (under `docs/superpowers/specs/`) are out of scope for v1; if you encounter one, abort and tell CT.
- **No `bot:ship-issue-ready` on children.** CT arms eligibility manually after review.
- **Milestones are scoped to spec-grouping only.** Do not name them anything other than `spec: <slug> (#M)`. Do not add due dates unless CT passes `--due-date YYYY-MM-DD`.

## Anti-patterns

- Filing children without first running the planner — the planner enforces the JSON contract.
- Editing the milestone title between dry-run and apply — that breaks the idempotence by-title.
- Creating multiple milestones for one spec because the slug differed across runs — `spec_slug.derive_slug` is deterministic; if you see this, something is wrong with the spec issue title.
- Skipping the CT confirmation step "to be helpful" — the design treats the proposal table as the contract.
````

- [ ] **Step 2: Smoke-check**

```bash
python3 -c "
from pathlib import Path
md = Path('/workspaces/ocr-container/.claude/skills/decompose-spec/SKILL.md').read_text()
assert md.startswith('---')
assert 'name: decompose-spec' in md
assert 'milestone' in md.lower()
"
```

Expected: no error.

- [ ] **Step 3: Commit**

```bash
cd /workspaces/ocr-container
git add .claude/skills/decompose-spec/SKILL.md
git commit -m "feat(skills): add /decompose-spec SKILL.md (proposal + milestone + apply)"
```

---

## Task 17: End-to-end smoke on pdomain-book-tools

This task is a manual validation pass. No new code; the goal is to drive the new skills against pdomain-book-tools and confirm the full chain works once.

**Prerequisites:** Tasks 1-16 complete and committed. `claude-ok` is gone from all 8 repos. `bot:ship-issue-ready` and the new triage/feature-request labels are present on pdomain-book-tools.

- [ ] **Step 1: File a fresh feature-request manually**

```bash
gh issue create --repo pdomain/pdomain-book-tools \
  --title "Smoke: feature-request lifecycle E2E" \
  --label kind:feature-request --label status:backlog \
  --body "Smoke-test the new triage → spec-from-issue → decompose-spec chain. Free to close once validated."
```

Capture the new issue number as `$FR`.

- [ ] **Step 2: Triage the feature-request as needs-spec**

In a `vscode` Claude session, run:

```
/triage <FR>
```

Expected:
- The skill reads the body, decides `approve, needs-spec`, drafts a spec-issue title and body.
- A new `kind:spec` issue `$SPEC` is filed; its body has `Tracks: #<FR>` and a placeholder `Spec:` line.
- Parent gets `triage:approved` + `triage:needs-spec` labels.
- Parent gets two comments: the reasoning comment + the pointer-to-#$SPEC comment.

Verify via:

```bash
gh issue view <FR> --repo pdomain/pdomain-book-tools --json labels,comments
gh issue view <SPEC> --repo pdomain/pdomain-book-tools --json body,labels
```

- [ ] **Step 3: Write the spec via /spec-from-issue**

```
/spec-from-issue <SPEC>
```

Expected:
- The skill walks brainstorming with you (be brief — this is a smoke test). Then writes the spec to `pdomain-book-tools/docs/specs/2026-05-10-smoke-feature-request-lifecycle-e2e.md` with the 9-section template + `Spec-Issue:` blockquote header.
- `lint-spec.py` passes against the new file.
- The spec issue body now contains `Spec: docs/specs/2026-05-10-smoke-feature-request-lifecycle-e2e.md`.
- A draft PR is open against pdomain-book-tools' `master` (or `main`).

Verify:

```bash
gh issue view <SPEC> --repo pdomain/pdomain-book-tools --json body
gh pr list --repo pdomain/pdomain-book-tools --search "spec: smoke" --draft
```

- [ ] **Step 4: Decompose the spec**

```
/decompose-spec pdomain-book-tools/docs/specs/2026-05-10-smoke-feature-request-lifecycle-e2e.md --output=tracking
```

Expected:
- Planner emits 1+ proposed children (depends on how many `### ` subsections you wrote in `## Decision`).
- Skill presents the proposal table; you confirm with no edits.
- `decompose-spec-apply.py` runs, creates the milestone `spec: smoke-feature-request-lifecycle-e2e (#<SPEC>)`, files each child attached to the milestone.

Verify:

```bash
gh api "/repos/pdomain/pdomain-book-tools/milestones?state=all" \
  --jq '.[] | select(.title | contains("smoke-feature-request-lifecycle-e2e")) | {number, title, open_issues, closed_issues}'

gh issue list --repo pdomain/pdomain-book-tools \
  --milestone "spec: smoke-feature-request-lifecycle-e2e (#<SPEC>)" --json number,title,labels
```

Expected: milestone exists, every filed child shows up under it.

- [ ] **Step 5: Arm one child + confirm ship-issue still picks it up**

Pick the smallest filed child `$CHILD` (likely a kind:chore with effort:S):

```bash
gh issue edit <CHILD> --repo pdomain/pdomain-book-tools \
  --add-label bot:ship-issue-ready --add-label status:ready --remove-label status:backlog
```

Then run ship-issue against pdomain-book-tools (use ctask or the orchestrator). Confirm it claims `<CHILD>` and proceeds normally.

If ship-issue does not claim it because of a missing label or wrong filter, debug — that means Task 6 missed a surface. Roll back the label change and fix the bug rather than working around it.

- [ ] **Step 6: Mark Phase 1 acceptance**

Once Step 5 succeeds, the following spec acceptance criteria are satisfied by Plan 1:

- [x] `seed-labels.sh` adds the new labels to all 8 repos (Task 2)
- [x] `scripts/migrate-claude-ok-to-bot-label.sh` runs successfully workspace-wide (Task 3-4)
- [x] `bash-command-guard.py` `_bot_ship_issue_check` gates on `bot:ship-issue-ready` (Task 5)
- [x] `ship-issue-pick.py` filters on `bot:ship-issue-ready` not `claude-ok` (Task 6)
- [x] `.claude/skills/triage/SKILL.md` + helpers exist and pass unit tests (Tasks 10, 11)
- [x] `.claude/skills/spec-from-issue/SKILL.md` + helpers exist and pass unit tests (Tasks 12, 13)
- [x] `.claude/skills/decompose-spec/SKILL.md` + helpers exist and unit tests pass for both `--output=tracking` and `--output=feature-requests` modes (Tasks 14-16). End-to-end exercise of `--output=tracking` happens in this task; `--output=feature-requests` E2E and `--backfill` dry-run validation are Plan 2 Phase 2.
- [x] `/decompose-spec` creates a `spec: <slug> (#M)` milestone in the target repo and assigns each filed child to it; diff-mode rerun reuses the existing milestone (Task 15 unit tests + this task's Step 4)
- [x] At least one end-to-end pass: file `kind:feature-request`, `/triage`, `/spec-from-issue`, write spec, `/decompose-spec` (verify milestone created with all children attached), arm a child, ship-issue picks it up, PR opens (this task)

The remaining acceptance bullets (chain-state report, dashboard panel, View A milestone column, `--output=feature-requests` end-to-end, `--backfill` against an existing spec) are covered by Plan 2.

- [ ] **Step 7: Cleanup commit**

If the smoke run produced a spec PR + spec issues you want to keep as a real seed, leave them. If the goal was purely to validate, close them:

```bash
# Close the smoke artifacts (do NOT delete the spec markdown — the spec is real; the issues are scratch).
gh issue close <FR>  --repo pdomain/pdomain-book-tools  --comment "Smoke validated; closing."
gh issue close <SPEC> --repo pdomain/pdomain-book-tools --comment "Smoke validated; closing."
gh pr close <PR> --repo pdomain/pdomain-book-tools --delete-branch
# Close children individually or the milestone — whichever is cleaner.
```

The `claude-ok → bot:ship-issue-ready` label rename is permanent regardless.

---

## Done — what comes next

Plan 1 is complete. The new skills are usable workspace-wide, but only pdomain-book-tools has been exercised end-to-end. The remaining acceptance gates from the spec — chain-state markdown, workspace summary, dashboard panel — are Plan 2.

Plan 2 also includes:

- Phase 2: `/decompose-spec --backfill --output=feature-requests` against existing pdomain-book-tools specs to seed the chain on real history.
- Phase 3: `scripts/build-spec-chain-report.py` + dashboard panel.
- Phase 5: rolling out skill *use* (not seeding — that's done in this plan) to the remaining 7 repos.

Phase 4 (dashboard refresh design) is deferred and not in scope for either plan.
