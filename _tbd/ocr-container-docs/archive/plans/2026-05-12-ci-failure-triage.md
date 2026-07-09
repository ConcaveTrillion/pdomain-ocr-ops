---
status: complete
---

# CI Failure Triage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `make ci` fails after a TDD slice, automatically detect pre-existing (unrelated) test failures, classify and size each one with sonnet, file bug issues, wire `Blocked-by:` onto the bounced issue, and re-arm it so the next bot run picks it up once the blockers are fixed.

**Architecture:** A new Python script `ship-issue-triage-ci-failure.py` runs inside the success.sh CI-failure block, before `failure.sh` resets git. It stashes the bot's work, reruns failing tests at the pre-claim SHA to identify which failures pre-existed, calls `claude -p` (sonnet, effort:low, max-turns:1) per pre-existing failure for classification + sizing, deduplicates against open issues, files each as a `kind:bug` issue, appends `Blocked-by:` to the bounced issue body, and exits with a JSON summary. `success.sh` reads the summary and, if all failures are pre-existing, re-arms the bounced issue after `failure.sh` has finished bouncing it.

**Tech Stack:** Python 3, `gh` CLI, `git`, `uv run pytest`, `claude` CLI, bash

---

## File Map

| File | Change |
|------|--------|
| `scripts/ship-issue-triage-ci-failure.py` | **Create** — full triage script |
| `scripts/ship-issue-success.sh` | **Modify** — call triage before failure.sh; re-arm after |
| `tests/test_triage_ci_failure.py` | **Create** — unit tests for the parser and classifier |

---

### Task 1: CI log parser + pre-existing detector

**Files:**
- Create: `scripts/ship-issue-triage-ci-failure.py`

- [ ] **Step 1: Write failing unit tests for the log parser**

Create `tests/test_triage_ci_failure.py`:

```python
"""Unit tests for ship-issue-triage-ci-failure helpers."""
import textwrap
import importlib.util, sys
from pathlib import Path

def load_triage():
    spec = importlib.util.spec_from_file_location(
        "triage",
        Path(__file__).parent.parent / "scripts/ship-issue-triage-ci-failure.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

triage = load_triage()


CI_LOG = textwrap.dedent("""\
    FAILED tests/unit/api/test_static_mounts.py::test_image_cache_blocks_path_traversal[../etc/passwd]
    FAILED tests/unit/api/test_static_mounts.py::test_image_cache_blocks_path_traversal[../../etc/passwd]
    FAILED tests/unit/models/test_models.py::test_matchstatus_values
    =================== 3 failed, 751 passed in 3.04s ===================
""")

EXCERPT_LOG = textwrap.dedent("""\
    _ test_image_cache_blocks_path_traversal[../etc/passwd] _
    key = '../etc/passwd'
        r = client.get(f"/image-cache/{key}")
    >   assert r.status_code == 404
    E   assert 200 == 404
    tests/unit/api/test_static_mounts.py:110: AssertionError
    FAILED tests/unit/api/test_static_mounts.py::test_image_cache_blocks_path_traversal[../etc/passwd]
    FAILED tests/unit/models/test_models.py::test_matchstatus_values
    =================== 2 failed in 1.0s ===================
""")


def test_parse_failing_tests_returns_unique_files():
    results = triage.parse_failing_tests(CI_LOG)
    ids = [r.test_id for r in results]
    assert "tests/unit/api/test_static_mounts.py::test_image_cache_blocks_path_traversal[../etc/passwd]" in ids
    assert "tests/unit/models/test_models.py::test_matchstatus_values" in ids


def test_parse_failing_tests_deduplicates_by_file():
    results = triage.parse_failing_tests(CI_LOG)
    # Both path-traversal variants share one file; only one FailingTest per unique test_id
    test_ids = [r.test_id for r in results]
    assert len(test_ids) == len(set(test_ids))


def test_extract_excerpt_finds_failure_block():
    excerpt = triage.extract_excerpt(
        EXCERPT_LOG,
        "tests/unit/api/test_static_mounts.py::test_image_cache_blocks_path_traversal[../etc/passwd]",
    )
    assert "assert 200 == 404" in excerpt
    assert "AssertionError" in excerpt


def test_parse_failing_tests_cap():
    many = "\n".join(
        f"FAILED tests/unit/test_foo.py::test_{i}" for i in range(20)
    ) + "\n20 failed in 1s\n"
    results = triage.parse_failing_tests(many)
    assert len(results) <= triage.MAX_BUGS_TO_FILE


def test_classify_output_parsing():
    raw = "model: sonnet\nmodel-effort: medium\nfix-kind: logic-bug\ntitle: fix broken guard\ndescription: The guard never fires."
    result = triage.parse_classify_output(raw)
    assert result.model == "sonnet"
    assert result.model_effort == "medium"
    assert result.fix_kind == "logic-bug"
    assert "guard" in result.title


def test_classify_output_defaults_on_bad_parse():
    result = triage.parse_classify_output("garbage output here")
    assert result.model in {"haiku", "sonnet", "opus"}
    assert result.model_effort in {"low", "medium", "high"}


def test_build_blocked_by_appends_new():
    body = "Some issue body.\n\nBlocked-by: #10\n"
    new_body = triage.add_blocked_by(body, [20, 30])
    assert "Blocked-by: #10, #20, #30" in new_body


def test_build_blocked_by_creates_when_missing():
    body = "Some issue body with no blocked-by."
    new_body = triage.add_blocked_by(body, [42])
    assert "Blocked-by: #42" in new_body


def test_build_blocked_by_no_duplicates():
    body = "Blocked-by: #10\n"
    new_body = triage.add_blocked_by(body, [10, 11])
    assert new_body.count("Blocked-by:") == 1
    assert "#10" in new_body
    assert "#11" in new_body
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
cd /workspaces/ocr-container
uv run pytest tests/test_triage_ci_failure.py -v 2>&1 | tail -20
```

Expected: `ERROR` or `ModuleNotFoundError` (script doesn't exist yet).

- [ ] **Step 3: Create the script skeleton with data types and parsers**

Create `scripts/ship-issue-triage-ci-failure.py`:

```python
#!/usr/bin/env python3
"""ship-issue-triage-ci-failure.py — auto-triage pre-existing CI failures.

Called by ship-issue-success.sh after make ci fails, before failure.sh resets
git. Detects pre-existing (unrelated) test failures, classifies + sizes each
via sonnet, deduplicates against open issues, files bug issues, appends
Blocked-by: lines to the bounced issue body, and optionally re-arms it.

Args:
  --repo OWNER/REPO
  --issue N           bounced issue number
  --pre-claim-sha SHA
  --ci-log PATH
  --repo-dir PATH     (defaults to cwd)

Stdout: JSON {"filed": [issue_numbers], "rearm": bool}
Stderr: human-readable progress
Exit 0 always (failures are logged, not raised — bouncing happens in failure.sh).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

MAX_BUGS_TO_FILE = 5

_FAILED_RE = re.compile(r"^FAILED\s+([\w/.\[\]-]+(?:::[^\s\[\]]+(?:\[.*?\])?)?)", re.MULTILINE)
_BLOCKED_BY_RE = re.compile(r"^(Blocked-by:\s*)(.+)$", re.MULTILINE)

VALID_MODELS = {"haiku", "sonnet", "opus"}
VALID_EFFORTS = {"low", "medium", "high", "xhigh", "max"}

FIX_KINDS = {"test-wrong", "logic-bug", "missing-impl", "type-error", "infra"}


@dataclass
class FailingTest:
    test_id: str        # full pytest node id
    excerpt: str = ""   # failure text extracted from CI log
    is_preexisting: bool = False


@dataclass
class SizingResult:
    model: str = "sonnet"
    model_effort: str = "medium"
    fix_kind: str = "logic-bug"
    title: str = ""
    description: str = ""


# ── Parsers ──────────────────────────────────────────────────────────────────

def parse_failing_tests(ci_log: str) -> list[FailingTest]:
    """Extract unique failing test IDs from a pytest CI log, capped at MAX_BUGS_TO_FILE."""
    seen: set[str] = set()
    results: list[FailingTest] = []
    for m in _FAILED_RE.finditer(ci_log):
        test_id = m.group(1).strip()
        if test_id in seen:
            continue
        seen.add(test_id)
        excerpt = extract_excerpt(ci_log, test_id)
        results.append(FailingTest(test_id=test_id, excerpt=excerpt))
        if len(results) >= MAX_BUGS_TO_FILE:
            break
    return results


def extract_excerpt(ci_log: str, test_id: str) -> str:
    """Return up to 40 lines of failure output for the given test_id."""
    # Find the separator line just before the test output
    safe_id = re.escape(test_id.split("[")[0])
    pattern = re.compile(
        r"_{3,}\s+" + safe_id + r".*?_{3,}(.*?)(?=_{3,}|\Z)",
        re.DOTALL,
    )
    m = pattern.search(ci_log)
    if not m:
        # fallback: grab 20 lines after first FAILED mention
        idx = ci_log.find(f"FAILED {test_id}")
        if idx == -1:
            return ""
        chunk = ci_log[max(0, idx - 500) : idx + 500]
        return "\n".join(chunk.splitlines()[:40])
    lines = m.group(1).strip().splitlines()
    return "\n".join(lines[:40])


def parse_classify_output(raw: str) -> SizingResult:
    """Parse the structured two-to-five line output from the sonnet sizing call."""
    result = SizingResult()
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("model:"):
            val = line.split(":", 1)[1].strip()
            if val in VALID_MODELS:
                result.model = val
        elif line.startswith("model-effort:"):
            val = line.split(":", 1)[1].strip()
            if val in VALID_EFFORTS:
                result.model_effort = val
        elif line.startswith("fix-kind:"):
            val = line.split(":", 1)[1].strip()
            if val in FIX_KINDS:
                result.fix_kind = val
        elif line.startswith("title:"):
            result.title = line.split(":", 1)[1].strip()
        elif line.startswith("description:"):
            result.description = line.split(":", 1)[1].strip()
    # defaults on parse failure
    if not result.title:
        result.title = "fix pre-existing test failure"
    return result


def add_blocked_by(body: str, new_issue_numbers: list[int]) -> str:
    """Append new_issue_numbers to an existing Blocked-by: line or create one."""
    m = _BLOCKED_BY_RE.search(body)
    if m:
        # parse existing numbers
        existing = {int(n) for n in re.findall(r"#(\d+)", m.group(2))}
        merged = sorted(existing | set(new_issue_numbers))
        refs = ", ".join(f"#{n}" for n in merged)
        return _BLOCKED_BY_RE.sub(f"Blocked-by: {refs}", body, count=1)
    # no existing Blocked-by — append before the last blank line or at end
    refs = ", ".join(f"#{n}" for n in sorted(new_issue_numbers))
    return body.rstrip() + f"\n\nBlocked-by: {refs}\n"
```

- [ ] **Step 4: Run parser tests — should pass now**

```bash
cd /workspaces/ocr-container
uv run pytest tests/test_triage_ci_failure.py::test_parse_failing_tests_returns_unique_files \
  tests/test_triage_ci_failure.py::test_parse_failing_tests_deduplicates_by_file \
  tests/test_triage_ci_failure.py::test_extract_excerpt_finds_failure_block \
  tests/test_triage_ci_failure.py::test_parse_failing_tests_cap \
  tests/test_triage_ci_failure.py::test_classify_output_parsing \
  tests/test_triage_ci_failure.py::test_classify_output_defaults_on_bad_parse \
  tests/test_triage_ci_failure.py::test_build_blocked_by_appends_new \
  tests/test_triage_ci_failure.py::test_build_blocked_by_creates_when_missing \
  tests/test_triage_ci_failure.py::test_build_blocked_by_no_duplicates \
  -v 2>&1 | tail -20
```

Expected: all 9 pass.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/ship-issue-triage-ci-failure.py tests/test_triage_ci_failure.py
git commit -m "feat(triage): CI failure parser, classifier types, Blocked-by helper"
```

---

### Task 2: Pre-existing failure detector (git stash + re-run)

**Files:**
- Modify: `scripts/ship-issue-triage-ci-failure.py` — add `detect_preexisting()`

- [ ] **Step 1: Add `detect_preexisting` to the script**

Append after `add_blocked_by`:

```python
# ── Pre-existing detector ─────────────────────────────────────────────────────

def detect_preexisting(
    failing: list[FailingTest],
    pre_claim_sha: str,
    repo_dir: str,
) -> list[FailingTest]:
    """Run failing tests at pre_claim_sha; mark those that also fail there as pre-existing.

    Uses git stash -u / git checkout / git stash pop. Leaves git state unclean
    on failure — success.sh calls failure.sh afterwards which does git reset --hard.
    """
    if not failing:
        return failing

    test_ids = [t.test_id for t in failing]
    sys.stderr.write(f"triage: checking {len(test_ids)} failing tests at {pre_claim_sha[:12]}...\n")

    # Stash bot's uncommitted work (including untracked files).
    stashed = False
    stash_result = subprocess.run(
        ["git", "-C", repo_dir, "stash", "-u", "--include-untracked"],
        capture_output=True, text=True,
    )
    if stash_result.returncode == 0 and "No local changes" not in stash_result.stdout:
        stashed = True

    try:
        # Detach at pre-claim SHA.
        subprocess.run(
            ["git", "-C", repo_dir, "checkout", "--detach", pre_claim_sha],
            capture_output=True, check=True,
        )

        # Run only the specific failing tests.
        proc = subprocess.run(
            ["uv", "run", "pytest", *test_ids, "--tb=no", "-q", "--no-header"],
            capture_output=True, text=True,
            cwd=repo_dir,
        )
        output = proc.stdout + proc.stderr

        # Parse which tests failed at pre-claim SHA.
        failed_at_base: set[str] = set()
        for m in _FAILED_RE.finditer(output):
            failed_at_base.add(m.group(1).strip())

        for t in failing:
            # Match by base test id (strip parametrize suffix for comparison)
            base_id = t.test_id.split("[")[0]
            t.is_preexisting = any(
                f.split("[")[0] == base_id for f in failed_at_base
            )
            status = "PRE-EXISTING" if t.is_preexisting else "bot-introduced"
            sys.stderr.write(f"  {status}: {t.test_id}\n")
    except Exception as exc:
        sys.stderr.write(f"triage: detect_preexisting error ({exc}); treating all as bot-introduced\n")
    finally:
        if stashed:
            subprocess.run(
                ["git", "-C", repo_dir, "stash", "pop"],
                capture_output=True,
            )

    return failing
```

- [ ] **Step 2: Run existing tests — must still pass**

```bash
cd /workspaces/ocr-container
uv run pytest tests/test_triage_ci_failure.py -v 2>&1 | tail -10
```

Expected: all 9 pass (new function has no tests yet; no regressions).

- [ ] **Step 3: Commit**

```bash
git add scripts/ship-issue-triage-ci-failure.py
git commit -m "feat(triage): detect pre-existing failures via stash+checkout+rerun"
```

---

### Task 3: Sonnet classifier call

**Files:**
- Modify: `scripts/ship-issue-triage-ci-failure.py` — add `classify_failure()`

- [ ] **Step 1: Add `classify_failure` after `detect_preexisting`**

```python
# ── Sonnet classifier ─────────────────────────────────────────────────────────

_CLASSIFY_PROMPT = """\
You are sizing and classifying a pre-existing test failure for an automated bug-filing bot.

Failing test: {test_id}
Failure output (up to 40 lines):
{excerpt}

Classify the fix:

fix-kind options:
- test-wrong     — the test itself is wrong (bad expectation, wrong encoding, stale fixture)
- logic-bug      — source code has incorrect logic
- missing-impl   — a function/method is not yet implemented (NotImplementedError or missing)
- type-error     — type annotation mismatch or wrong type passed
- infra          — missing fixture, env var, or test-infrastructure issue

Sizing:
- haiku / low    — trivially localized: one-liner, obvious typo, single constant
- sonnet / medium — a few callsites, needs moderate reasoning
- sonnet / high  — security-sensitive, cross-cutting, or subtle invariant
- opus / high    — deep architectural reasoning required

Reply with ONLY these five lines, no other text:
model: <haiku|sonnet|opus>
model-effort: <low|medium|high>
fix-kind: <test-wrong|logic-bug|missing-impl|type-error|infra>
title: <imperative phrase, ≤72 chars, no "fix:" prefix>
description: <one sentence explaining the root cause and fix>
"""


def classify_failure(test: FailingTest) -> SizingResult:
    """Call sonnet (effort:low, max-turns:1) to size and classify a pre-existing failure."""
    prompt = _CLASSIFY_PROMPT.format(
        test_id=test.test_id,
        excerpt=test.excerpt[:2000] if test.excerpt else "(no excerpt available)",
    )

    gh_secret = "/run/secrets/gh-token-pd"
    env = os.environ.copy()
    # Strip bot PAT — claude doesn't need it.
    env.pop("GH_TOKEN", None)
    # Ensure claude binary is on PATH.
    env["PATH"] = f"/home/claude-bot/.local/bin:{env.get('PATH', '')}"

    result = subprocess.run(
        ["claude", "-p", prompt,
         "--model", "sonnet",
         "--effort", "low",
         "--max-turns", "1"],
        capture_output=True, text=True,
        env=env,
        timeout=120,
    )
    raw = result.stdout.strip()
    sys.stderr.write(f"triage: sonnet classify for {test.test_id.split('::')[-1][:50]}:\n  {raw[:120]}\n")
    return parse_classify_output(raw)
```

- [ ] **Step 2: Run existing tests — must still pass**

```bash
cd /workspaces/ocr-container
uv run pytest tests/test_triage_ci_failure.py -v 2>&1 | tail -10
```

Expected: all 9 pass.

- [ ] **Step 3: Commit**

```bash
git add scripts/ship-issue-triage-ci-failure.py
git commit -m "feat(triage): sonnet classify_failure call with structured prompt"
```

---

### Task 4: Dedup check + issue filer

**Files:**
- Modify: `scripts/ship-issue-triage-ci-failure.py` — add `find_duplicate()` and `file_bug_issue()`

- [ ] **Step 1: Add gh helpers after `classify_failure`**

```python
# ── GH helpers ───────────────────────────────────────────────────────────────

def _gh(args: list[str]) -> subprocess.CompletedProcess:
    """Run a gh command with GH_TOKEN from /run/secrets/gh-token-pd."""
    env = os.environ.copy()
    gh_secret = "/run/secrets/gh-token-pd"
    if Path(gh_secret).is_file():
        env["GH_TOKEN"] = Path(gh_secret).read_text().strip()
    return subprocess.run(["gh", *args], capture_output=True, text=True, env=env)


def find_duplicate(repo: str, test_id: str) -> int | None:
    """Return open bug issue number if one exists for this test, else None.

    Searches by the short test function name (after last '::'). A match
    requires the title to contain that name to avoid false positives on
    short words.
    """
    short = test_id.split("::")[-1].split("[")[0][:60]
    r = _gh([
        "issue", "list", "--repo", repo, "--state", "open",
        "--label", "kind:bug",
        "--search", short,
        "--json", "number,title",
        "--limit", "10",
    ])
    if r.returncode != 0:
        return None
    items = json.loads(r.stdout or "[]")
    for item in items:
        if short.lower() in item["title"].lower():
            return int(item["number"])
    return None


def file_bug_issue(
    repo: str,
    test: FailingTest,
    sizing: SizingResult,
    blocked_issue: int,
) -> int | None:
    """Create a new kind:bug issue. Returns the new issue number or None on failure."""
    short_test = test.test_id.split("::")[-1]
    title = sizing.title or f"fix pre-existing failure: {short_test[:60]}"

    # Prefix title with fix-kind hint for humans.
    kind_prefix = {
        "test-wrong": "fix(tests):",
        "logic-bug": "fix:",
        "missing-impl": "chore:",
        "type-error": "fix:",
        "infra": "chore(infra):",
    }.get(sizing.fix_kind, "fix:")
    full_title = f"{kind_prefix} {title}"

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    body = f"""\
Pre-existing test failure detected by ship-issue while working on #{blocked_issue}.

**Test:** `{test.test_id}`

**Root cause:** {sizing.description or '(see failure excerpt)'}

## Acceptance
- [ ] `uv run pytest "{test.test_id}" -v` exits 0
- [ ] `make ci` exits 0 with this fix applied

**Failure excerpt:**
```
{test.excerpt[:800] if test.excerpt else '(not captured)'}
```

*Auto-filed by ship-issue triage on {today}.*
"""

    labels = [
        "kind:bug",
        f"model:{sizing.model}",
        f"model-effort:{sizing.model_effort}",
        "status:ready",
        "bot:ship-issue-ready",
    ]
    r = _gh([
        "issue", "create",
        "--repo", repo,
        "--title", full_title,
        "--body", body,
        "--label", ",".join(labels),
    ])
    if r.returncode != 0:
        sys.stderr.write(f"triage: gh issue create failed: {r.stderr[:200]}\n")
        return None

    # gh issue create prints the URL; extract number from the last path segment.
    url = r.stdout.strip()
    try:
        return int(url.rstrip("/").split("/")[-1])
    except ValueError:
        sys.stderr.write(f"triage: could not parse issue number from URL: {url}\n")
        return None
```

- [ ] **Step 2: Run tests — still passing**

```bash
cd /workspaces/ocr-container
uv run pytest tests/test_triage_ci_failure.py -v 2>&1 | tail -10
```

Expected: all 9 pass.

- [ ] **Step 3: Commit**

```bash
git add scripts/ship-issue-triage-ci-failure.py
git commit -m "feat(triage): dedup check and bug issue filer"
```

---

### Task 5: Blocked-by updater + main()

**Files:**
- Modify: `scripts/ship-issue-triage-ci-failure.py` — add `update_blocked_by_on_issue()` and `main()`

- [ ] **Step 1: Add `update_blocked_by_on_issue` and `main` at end of script**

```python
# ── Blocked-by updater ────────────────────────────────────────────────────────

def update_blocked_by_on_issue(repo: str, issue: int, new_blockers: list[int]) -> None:
    """Append Blocked-by: #N lines to the bounced issue body."""
    r = _gh(["issue", "view", str(issue), "--repo", repo, "--json", "body"])
    if r.returncode != 0:
        sys.stderr.write(f"triage: could not fetch body of #{issue}\n")
        return
    current_body = json.loads(r.stdout).get("body", "") or ""
    new_body = add_blocked_by(current_body, new_blockers)
    edit = _gh([
        "issue", "edit", str(issue), "--repo", repo,
        "--body", new_body,
    ])
    if edit.returncode != 0:
        sys.stderr.write(f"triage: could not update body of #{issue}: {edit.stderr[:200]}\n")
    else:
        refs = ", ".join(f"#{n}" for n in sorted(new_blockers))
        sys.stderr.write(f"triage: added Blocked-by {refs} to #{issue}\n")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--pre-claim-sha", required=True)
    parser.add_argument("--ci-log", required=True)
    parser.add_argument("--repo-dir", default=".")
    args = parser.parse_args()

    ci_log = Path(args.ci_log).read_text(errors="replace")

    # 1. Parse failing tests.
    failing = parse_failing_tests(ci_log)
    if not failing:
        sys.stderr.write("triage: no FAILED lines found in CI log; nothing to triage\n")
        print(json.dumps({"filed": [], "rearm": False}))
        return

    sys.stderr.write(f"triage: {len(failing)} unique failing test(s) found\n")

    # 2. Detect which are pre-existing.
    failing = detect_preexisting(failing, args.pre_claim_sha, args.repo_dir)
    preexisting = [t for t in failing if t.is_preexisting]
    bot_introduced = [t for t in failing if not t.is_preexisting]

    if not preexisting:
        sys.stderr.write("triage: all failures are bot-introduced; no bugs to file\n")
        print(json.dumps({"filed": [], "rearm": False}))
        return

    sys.stderr.write(
        f"triage: {len(preexisting)} pre-existing, {len(bot_introduced)} bot-introduced\n"
    )

    # 3. Classify + file each pre-existing failure.
    filed: list[int] = []
    for test in preexisting:
        # Dedup.
        existing = find_duplicate(args.repo, test.test_id)
        if existing is not None:
            sys.stderr.write(f"triage: duplicate found for {test.test_id}: #{existing}; skipping\n")
            filed.append(existing)
            continue

        # Size + classify via sonnet.
        sizing = classify_failure(test)

        # File the bug issue.
        new_number = file_bug_issue(args.repo, test, sizing, args.issue)
        if new_number:
            sys.stderr.write(f"triage: filed bug #{new_number} for {test.test_id}\n")
            filed.append(new_number)

    if not filed:
        sys.stderr.write("triage: no bug issues filed (all duplicates or errors)\n")
        print(json.dumps({"filed": [], "rearm": False}))
        return

    # 4. Update bounced issue with Blocked-by lines.
    update_blocked_by_on_issue(args.repo, args.issue, filed)

    # 5. Rearm only if ALL failures are pre-existing (bot introduced nothing new).
    rearm = len(bot_introduced) == 0
    sys.stderr.write(
        f"triage: done — filed={filed}, rearm={rearm}\n"
    )
    print(json.dumps({"filed": filed, "rearm": rearm}))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make executable**

```bash
chmod +x /workspaces/ocr-container/scripts/ship-issue-triage-ci-failure.py
```

- [ ] **Step 3: Run all tests**

```bash
cd /workspaces/ocr-container
uv run pytest tests/test_triage_ci_failure.py -v 2>&1 | tail -15
```

Expected: all 9 pass.

- [ ] **Step 4: Commit**

```bash
git add scripts/ship-issue-triage-ci-failure.py
git commit -m "feat(triage): Blocked-by updater and main() entry point"
```

---

### Task 6: Wire into ship-issue-success.sh

**Files:**
- Modify: `scripts/ship-issue-success.sh:60-66`

- [ ] **Step 1: Replace the CI failure block**

Current block (lines 60–66):
```bash
if [[ "$_CI_PASSED" -eq 0 ]]; then
  CI_TAIL="$(tail -50 "$CI_LOG")"
  echo "✗ make ci failed after self-correction; bouncing issue" >&2
  "$WORKSPACE/scripts/ship-issue-failure.sh" "$ISSUE" "$REPO" "$PRE_SHA" \
    "make ci failed: $CI_TAIL"
  exit 1
fi
```

Replace with:
```bash
if [[ "$_CI_PASSED" -eq 0 ]]; then
  CI_TAIL="$(tail -50 "$CI_LOG")"
  echo "✗ make ci failed after self-correction; triaging failures..." >&2

  # Triage BEFORE failure.sh resets git (need working tree to stash + rerun).
  TRIAGE_JSON="$("$WORKSPACE/scripts/ship-issue-triage-ci-failure.py" \
    --repo "$REPO" --issue "$ISSUE" \
    --pre-claim-sha "$PRE_SHA" \
    --ci-log "$CI_LOG" \
    --repo-dir "$(pwd)" 2>/tmp/triage-stderr-$ISSUE.txt)" || TRIAGE_JSON='{"filed":[],"rearm":false}'
  cat /tmp/triage-stderr-$ISSUE.txt >&2
  rm -f /tmp/triage-stderr-$ISSUE.txt

  TRIAGE_REARM="$(echo "$TRIAGE_JSON" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin).get("rearm",False))' \
    2>/dev/null || echo False)"

  # failure.sh: reset git, set status:bounced, remove bot:ship-issue-ready.
  "$WORKSPACE/scripts/ship-issue-failure.sh" "$ISSUE" "$REPO" "$PRE_SHA" \
    "make ci failed: $CI_TAIL"

  # Re-arm if ALL failures were pre-existing (filed as blocker bugs above).
  if [[ "$TRIAGE_REARM" == "True" || "$TRIAGE_REARM" == "true" ]]; then
    echo "▸ All CI failures were pre-existing; re-arming #$ISSUE with Blocked-by" >&2
    gh issue edit "$ISSUE" -R "$REPO" \
      --remove-label "status:bounced" \
      --add-label "status:ready" \
      --add-label "bot:ship-issue-ready" \
      || echo "WARN: could not re-arm #$ISSUE" >&2
  fi

  exit 1
fi
```

- [ ] **Step 2: Verify success.sh parses cleanly**

```bash
bash -n /workspaces/ocr-container/scripts/ship-issue-success.sh && echo "syntax OK"
```

Expected: `syntax OK`

- [ ] **Step 3: Commit**

```bash
git add scripts/ship-issue-success.sh
git commit -m "feat(triage): wire triage script into success.sh CI failure block"
```

---

### Task 7: Smoke-test with real bounce data

This task verifies the script end-to-end using the known-bounced pdomain-ocr-labeler-spa path-traversal failure as a fixture (without actually filing issues).

- [ ] **Step 1: Run the parser against a synthetic CI log matching the known bounce**

```bash
cd /workspaces/ocr-container
python3 - <<'EOF'
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("t", "scripts/ship-issue-triage-ci-failure.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

log = """
FAILED tests/unit/api/test_static_mounts.py::test_image_cache_blocks_path_traversal[../etc/passwd]
FAILED tests/unit/api/test_static_mounts.py::test_image_cache_blocks_path_traversal[../../etc/passwd]
FAILED tests/unit/api/test_static_mounts.py::test_image_cache_blocks_path_traversal[subdir/../../escape.png]
=================== 3 failed, 751 passed in 3.04s ===================
"""

failing = mod.parse_failing_tests(log)
print(f"Found {len(failing)} unique test(s):")
for t in failing:
    print(f"  {t.test_id}")

sizing_raw = "model: haiku\nmodel-effort: low\nfix-kind: test-wrong\ntitle: use percent-encoded dots in path traversal tests\ndescription: httpx normalises literal .. before sending; use %2e%2e instead."
sizing = mod.parse_classify_output(sizing_raw)
print(f"Sizing: {sizing.model}/{sizing.model_effort} fix-kind={sizing.fix_kind}")

body = "Tracks: #6\nSpec: docs/specs/foo.md\nBlocked-by: #10\n"
new_body = mod.add_blocked_by(body, [42, 43])
print(f"Updated body:\n{new_body}")
assert "Blocked-by: #10, #42, #43" in new_body
print("All assertions passed.")
EOF
```

Expected output:
```
Found 3 unique test(s):
  tests/unit/api/test_static_mounts.py::test_image_cache_blocks_path_traversal[../etc/passwd]
  tests/unit/api/test_static_mounts.py::test_image_cache_blocks_path_traversal[../../etc/passwd]
  tests/unit/api/test_static_mounts.py::test_image_cache_blocks_path_traversal[subdir/../../escape.png]
Sizing: haiku/low fix-kind=test-wrong
Updated body:
Tracks: #6
Spec: docs/specs/foo.md
Blocked-by: #10, #42, #43

All assertions passed.
```

- [ ] **Step 2: Run full test suite**

```bash
cd /workspaces/ocr-container
uv run pytest tests/test_triage_ci_failure.py -v 2>&1 | tail -15
```

Expected: all 9 pass.

- [ ] **Step 3: Commit (if any fixups needed)**

```bash
git add -p  # stage only actual fixes
git commit -m "fix(triage): smoke-test corrections"
```

---

## Verification after all tasks

1. `uv run pytest tests/test_triage_ci_failure.py -v` → 9 passed
2. `bash -n scripts/ship-issue-triage-ci-failure.py` → syntax OK (Python)
3. `bash -n scripts/ship-issue-success.sh` → syntax OK
4. Next real bounce on a repo with a pre-existing failure → bug issue filed, bounced issue re-armed with `Blocked-by:`, CI failures identified as `PRE-EXISTING` in the log
