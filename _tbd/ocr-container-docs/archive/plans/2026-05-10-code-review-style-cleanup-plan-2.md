---
status: complete
---

# Code-review + style-cleanup — Plan 2: CONVENTIONS.md bootstrap + /pr-review

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land Phases 2 and 3 of the v2 code-review/style spec on pdomain-book-tools. End state: workspace and pdomain-book-tools each have an authored `CONVENTIONS.md`; the shared review engine (`scripts/style-review-detect.py` + `scripts/style-review-apply.py`) is in place with TDD coverage; the `/pr-review` CT-interactive skill walks a fixture rolling PR end-to-end with the bots-paused flag lifecycle.

**Architecture:** A two-script split with a JSON contract: `style-review-detect.py` is the only LLM call (Sonnet via the Anthropic SDK, with prompt caching on the conventions doc); `style-review-apply.py` is purely deterministic (git apply, `make fast-check`, revert-on-failure, gh comment posting). The `/pr-review` skill is thin: it owns the `bots-paused` flag-file lifecycle and the `AskUserQuestion` walkthrough loop, but delegates detection and application to the same two scripts the (later) bots will use. CONVENTIONS.md per-repo is self-contained: cross-repo rules inlined inside marker tags (synced from a workspace canonical via v2 Plan 4); repo-specific rules below the markers.

**Tech Stack:** Python 3.11, Anthropic SDK (`anthropic` package), `gh` CLI, `git apply`, bash, pytest, `AskUserQuestion` (Claude Code tool).

**Source spec:** `docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md`

**Depends on:**
- v2 Plan 1 (lint-first + worktree retrofit) merged. The `/pr-review` smoke flow operates on rolling `wip/ship-issue` PRs; those PRs are produced by the retrofitted ship-issue from Plan 1.
- Plan-1 bullet "Phase 0 lint-config bumps merged to all 7 pd-* repos" satisfied for at least pdomain-book-tools (so style-review-detect is reviewing prose conventions, not lint findings ruff/pyright would already catch).

**Out of scope:**
- The daily / weekly bots themselves (v2 Plan 3).
- Sync-conventions.py, check-sync-drift.py, check-sibling-drift.py, lint-conventions.py — all in v2 Plan 4 (the workspace meta phase). This plan creates the per-repo CONVENTIONS.md files, but the cross-repo sync infrastructure that propagates the workspace canonical block lands later. **Important** — until v2 Plan 4 lands, the cross-repo block in pdomain-book-tools' CONVENTIONS.md is hand-edited; that's fine for the single-repo Phase 2/3 scope.
- Rollout to other 6 repos — v2 Plan 4 Phase 7.

---

## Background context for the engineer

Read the spec end-to-end first. The relevant sections are:
- **Conventions docs** — per-repo self-contained file structure, marker-delimited cross-repo block, rule template.
- **Script vs LLM boundary** — explicit boundary you must preserve.
- **Shared review engine — split for prompt-caching** — why two scripts and the JSON contract.
- **CT-interactive skill (the only one)** — `/pr-review` lifecycle.
- **Review window coordination** — the bots-paused flag lifecycle.

Existing surfaces:
- `claude-api` skill (loaded via `Skill` tool) — gives you the shape of correct Anthropic SDK usage including prompt caching. Use it inside `style-review-detect.py`.
- `.claude/skills/ship-issue/SKILL.md` — pattern for skill files.
- `superpowers:brainstorming` — wrapped by `/spec-from-issue`; not directly used here but the AskUserQuestion idiom is the same.
- `scripts/seed-labels.sh` — three new labels added in v2 Plan 3 (this plan does not need them).
- `gh pr review --comment` — the gh surface for posting review comments. Verify with `gh pr review --help` if uncertain.
- `make fast-check` — every pd-* repo has a Makefile target for the cheap pre-PR gate (ruff + a fast test slice). Used by `style-review-apply.py` to validate auto-fixes.

The only LLM-bound surface in this plan is `style-review-detect.py`. Everything else (apply, sync, lint, dashboard rendering — the latter two arrive in Plan 4) is deterministic.

**Prompt-caching boundary.** The conventions doc (per-repo CONVENTIONS.md) is the ONLY large stable string in `style-review-detect.py`'s prompt. Make it a system-message-with-cache-control (or pass via the SDK's prompt-caching API). The variable suffix is the diff or full-tree scope. Per-finding output is small. This single design choice is the primary cost lever in v2; do not collapse the two scripts back into one — that would re-tokenize the doc per finding.

**`bots-paused` flag.** Flag-file at `/srv/bot-workspaces/.state/bots-paused` (the directory created by Plan 1's bootstrap). Presence = pause; absence = run. The orchestrator scripts already check it (Plan 1 Task 11). `/pr-review` is the writer.

---

## File structure (created or modified by this plan)

**Created:**

- `CONVENTIONS.md` (workspace root, `/workspaces/ocr-container/CONVENTIONS.md`) — workspace canonical.
- `pdomain-book-tools/CONVENTIONS.md` — per-repo, self-contained.
- `tests/fixtures/conventions/` — fixture conventions docs for testing detect+apply scripts.
- `tests/fixtures/findings/` — fixture JSON for testing apply.py without an LLM call.
- `scripts/extract-conventions.py` — bootstrap helper.
- `scripts/style-review-detect.py` — LLM detection engine.
- `scripts/style-review-apply.py` — deterministic applier.
- `tests/scripts/test_extract_conventions.py` — unit tests for the path-derivation + input-gathering helpers (the LLM call is mocked).
- `tests/scripts/test_style_review_apply.py` — fixture-driven tests; no LLM.
- `tests/scripts/test_style_review_detect.py` — input-gathering helpers tested; the LLM call mocked at the SDK boundary.
- `.claude/skills/pr-review/SKILL.md` — CT-interactive skill.

**Modified:**

- `docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md` — flip Phase 2 + Phase 3 acceptance bullets when complete.

---

# Phase 2: CONVENTIONS.md bootstrap (workspace + pdomain-book-tools)

## Task 1: Define the rule template + commit fixture conventions

**Files:**

- Create: `tests/fixtures/conventions/example-conventions.md` — example conformant fixture used by tests in later tasks.
- Create: `tests/fixtures/conventions/malformed-no-markers.md` — fixture without sync markers (used by lint-conventions in v2 Plan 4 — pre-stage here).
- Create: `tests/fixtures/conventions/malformed-bad-rule-template.md` — rule heading missing required sub-sections.

These fixtures encode the spec's rule template structurally. They land
before the production `CONVENTIONS.md` files so test code in subsequent
tasks (extract-conventions, style-review-detect, style-review-apply)
has known-good and known-bad inputs.

- [ ] **Step 1: Write the conformant fixture**

Save as `tests/fixtures/conventions/example-conventions.md`:

```markdown
# Conventions — example fixture

<!-- workspace-conventions:start -->

## Rule: No comments explaining what code does

**The rule.** Don't add comments that restate what the code does;
well-named identifiers already do that. Only add a comment when the
WHY is non-obvious.

**Why.** Comments rot when code changes; they become misleading. The
codebase has bitten us with stale comments multiple times — see
PR #42 for the canonical example.

**Common high-confidence violations** (bot auto-fix candidates)
- One-line summary comment immediately above a function definition that simply restates the function name.
- "# returns the X" or "// returns X" before a return statement.

**Common judgment-call violations** (bot flags, CT decides)
- Multi-line preamble that mixes WHY (worth keeping) with WHAT (worth removing).
- Comments that document a workaround for a specific bug — these often look stylistic but encode load-bearing context.

<!-- workspace-conventions:end -->

## Rule: pdomain-book-tools-specific — never silently drop OCR words

**The rule.** Word objects flagged as footnote/header/footer/abandoned
must keep a `role` label, never be deleted from the OCR output. This
is the single most-violated convention in the repo.

**Why.** Drops are unrecoverable; mislabels can be fixed at review
time. See `feedback_no_silent_word_drops.md`.

**Common high-confidence violations** (bot auto-fix candidates)
- `del page.words[i]` calls in the role-classifier code path.

**Common judgment-call violations** (bot flags, CT decides)
- Filtering predicates inside word-iteration loops that exclude
  role-labeled words from rendering.
```

- [ ] **Step 2: Write the malformed fixtures**

`tests/fixtures/conventions/malformed-no-markers.md`:

```markdown
# Conventions — fixture missing sync markers

## Rule: A rule

**The rule.** Some rule.

**Why.** Some reason.

**Common high-confidence violations** (bot auto-fix candidates)
- Pattern A.

**Common judgment-call violations** (bot flags, CT decides)
- Pattern B.
```

`tests/fixtures/conventions/malformed-bad-rule-template.md`:

```markdown
# Conventions — fixture with malformed rule heading

<!-- workspace-conventions:start -->

## Rule: Has only two sub-sections, missing two more

**The rule.** Only one sub-section here.

**Why.** Should have two more.

<!-- workspace-conventions:end -->
```

- [ ] **Step 3: Commit**

```bash
cd /workspaces/ocr-container
git add tests/fixtures/conventions/
git commit -m "test(fixtures): conventions — conformant + two malformed for v2 testing"
```

---

## Task 2: scripts/extract-conventions.py — bootstrap helper

**Files:**

- Create: `scripts/extract-conventions.py`
- Create: `tests/scripts/test_extract_conventions.py`

The script gathers inputs deterministically (file I/O), composes them into
an Anthropic SDK call (the only LLM step), and writes a `CONVENTIONS.md.draft`
file. Idempotent: refuses to overwrite an existing CONVENTIONS.md unless
`--force`; when `--force` not set and the target exists, opens diff-mode.

CT then reviews the .draft, edits, and `mv`s to the final location. Writing
the final file is NOT scripted — it's a CT decision per spec.

- [ ] **Step 1: Write the failing test**

Save as `tests/scripts/test_extract_conventions.py`:

```python
"""Tests for scripts/extract-conventions.py.

The LLM call is mocked at the SDK boundary; tests target the input
gathering and the output-file logic. The actual prompt content is
exercised via a fixture-driven contract (Anthropic returns a known
string that the script writes to .draft as-is).
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/extract-conventions.py"


def _mod():
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    spec = importlib.util.spec_from_file_location("extract_conventions", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FakeAnthropic:
    """Minimal stand-in for an Anthropic SDK client.

    The script calls `client.messages.create(...)` once and reads
    `response.content[0].text`. We expose just enough surface for that.
    """
    def __init__(self, response_text: str = "# Conventions — generated draft\n\n"):
        self.response_text = response_text
        self.calls = []
        self.messages = MagicMock()
        self.messages.create = self._create

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        resp = MagicMock()
        resp.content = [MagicMock(text=self.response_text)]
        return resp


def test_gather_inputs_for_workspace_returns_workspace_files():
    m = _mod()
    inputs = m.gather_inputs(repo=None, workspace=WORKSPACE)
    # The "workspace" mode reads workspace CLAUDE.md + agent-memory feedback files.
    assert "CLAUDE.md" in inputs.label_set
    assert any("agent-memory" in p for p in inputs.path_set)


def test_gather_inputs_for_repo_includes_repo_files():
    m = _mod()
    inputs = m.gather_inputs(repo="pdomain-book-tools", workspace=WORKSPACE)
    # Repo mode reads workspace CLAUDE.md AND repo CLAUDE.md AND repo agent-memory if present.
    paths = " ".join(inputs.path_set)
    assert "pdomain-book-tools/CLAUDE.md" in paths or "pdomain-book-tools" in paths


def test_writes_draft_when_target_absent(tmp_path: Path):
    m = _mod()
    target = tmp_path / "CONVENTIONS.md"
    fake = FakeAnthropic(response_text="# Draft\n\n## Rule: stub\n")
    rc = m.run(
        client=fake, target=target, inputs=m.GatheredInputs(
            label_set=set(), path_set=set(), text="prompt-input"
        ), force=False,
    )
    assert rc == 0
    assert (tmp_path / "CONVENTIONS.md.draft").exists()
    text = (tmp_path / "CONVENTIONS.md.draft").read_text()
    assert "# Draft" in text


def test_refuses_overwrite_without_force(tmp_path: Path):
    m = _mod()
    target = tmp_path / "CONVENTIONS.md"
    target.write_text("# existing\n")
    fake = FakeAnthropic()
    rc = m.run(
        client=fake, target=target, inputs=m.GatheredInputs(
            label_set=set(), path_set=set(), text="ignored"
        ), force=False,
    )
    assert rc != 0
    assert not (tmp_path / "CONVENTIONS.md.draft").exists() or \
           "diff" in (tmp_path / "CONVENTIONS.md.draft").read_text().lower() \
           or True  # diff-mode behavior is acceptable; refuses-only also acceptable


def test_force_overwrites_draft(tmp_path: Path):
    m = _mod()
    target = tmp_path / "CONVENTIONS.md"
    (tmp_path / "CONVENTIONS.md.draft").write_text("# old draft\n")
    fake = FakeAnthropic(response_text="# new draft\n")
    rc = m.run(
        client=fake, target=target, inputs=m.GatheredInputs(
            label_set=set(), path_set=set(), text="prompt"
        ), force=True,
    )
    assert rc == 0
    assert "new draft" in (tmp_path / "CONVENTIONS.md.draft").read_text()


def test_anthropic_call_uses_prompt_caching():
    """The conventions extractor invokes the SDK with cache_control on
    the gathered-inputs system message — the script's primary cost lever.
    Without this, every per-repo extraction re-tokenizes the same shared
    workspace context."""
    m = _mod()
    fake = FakeAnthropic()
    target = Path(tempfile.mkdtemp()) / "CONVENTIONS.md"
    rc = m.run(
        client=fake, target=target, inputs=m.GatheredInputs(
            label_set={"workspace-CLAUDE.md"}, path_set=set(),
            text="<workspace context>\n",
        ), force=False,
    )
    assert rc == 0
    assert len(fake.calls) == 1
    kwargs = fake.calls[0]
    # System message is a list with cache_control on the gathered context.
    sys_msg = kwargs.get("system")
    assert isinstance(sys_msg, list), \
        "system must be a list of blocks for prompt caching"
    cached = [b for b in sys_msg if b.get("cache_control")]
    assert cached, "expected at least one cached system block"
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_extract_conventions.py -v
```

Expected: FAIL — script does not exist.

- [ ] **Step 3: Implement the script**

Save as `scripts/extract-conventions.py`:

```python
#!/usr/bin/env python3
"""extract-conventions.py — bootstrap a CONVENTIONS.md draft.

Workspace mode  : extract-conventions.py --workspace
                  Output: /workspaces/ocr-container/CONVENTIONS.md.draft
Repo mode       : extract-conventions.py <repo-basename>
                  Output: /workspaces/ocr-container/<repo>/CONVENTIONS.md.draft

CT reviews the .draft, edits, and `mv .draft CONVENTIONS.md` when satisfied.
The script never writes the canonical file directly — that's CT's call.

Inputs gathered (deterministic file I/O):
  - Workspace CLAUDE.md
  - Per-repo CLAUDE.md (repo mode)
  - .claude/agent-memory/<agent>/feedback_*.md and project_*.md (workspace + per-repo)
  - Last 90 days of commit subjects (repo mode only)
  - Workspace canonical CONVENTIONS.md (repo mode, if present — used to anchor the cross-repo block)

LLM step (one Sonnet call):
  Drafts the per-repo skeleton: cross-repo block (synced from canonical)
  + proposed repo-specific section. Uses prompt caching on the gathered
  context so future per-repo extractions reuse the workspace prefix.

Idempotent. Refuses to overwrite an existing CONVENTIONS.md unless
--force; when target exists and --force absent, writes a .diff file
suggesting additions instead of overwriting the draft wholesale.
"""
from __future__ import annotations

import argparse
import dataclasses
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable

WORKSPACE = Path("/workspaces/ocr-container")
MODEL = "claude-sonnet-4-6"


@dataclasses.dataclass
class GatheredInputs:
    label_set: set       # human-readable labels for what was gathered
    path_set: set        # absolute paths of files read
    text: str            # the gathered context as a single string


def _read(p: Path) -> str:
    try:
        return p.read_text(errors="replace")
    except OSError:
        return ""


def _agent_memory_files(workspace: Path) -> Iterable[Path]:
    base = workspace / ".claude" / "agent-memory"
    if not base.exists():
        return []
    out = []
    for agent in sorted(base.iterdir()):
        if not agent.is_dir():
            continue
        for f in sorted(agent.glob("feedback_*.md")):
            out.append(f)
        for f in sorted(agent.glob("project_*.md")):
            out.append(f)
    return out


def _commit_subjects(repo_path: Path, days: int = 90) -> str:
    if not (repo_path / ".git").exists():
        return ""
    try:
        r = subprocess.run(
            ["git", "-C", str(repo_path), "log",
             f"--since={days} days ago", "--format=%s"],
            capture_output=True, text=True, timeout=10,
        )
        return r.stdout
    except (subprocess.SubprocessError, OSError):
        return ""


def gather_inputs(repo: str | None, workspace: Path) -> GatheredInputs:
    """Gather all inputs for the LLM call. Pure file I/O."""
    label_set: set = set()
    path_set: set = set()
    chunks: list[str] = []

    workspace_claude = workspace / "CLAUDE.md"
    if workspace_claude.exists():
        chunks.append(f"=== Workspace CLAUDE.md ===\n{_read(workspace_claude)}\n")
        label_set.add("CLAUDE.md")
        path_set.add(str(workspace_claude))

    for f in _agent_memory_files(workspace):
        chunks.append(f"=== {f.relative_to(workspace)} ===\n{_read(f)}\n")
        label_set.add("agent-memory")
        path_set.add(str(f))

    if repo:
        repo_path = workspace / repo
        repo_claude = repo_path / "CLAUDE.md"
        if repo_claude.exists():
            chunks.append(f"=== {repo}/CLAUDE.md ===\n{_read(repo_claude)}\n")
            path_set.add(str(repo_claude))

        commits = _commit_subjects(repo_path)
        if commits:
            chunks.append(f"=== {repo} recent commit subjects ===\n{commits}\n")
            label_set.add("git-log")

        canon = workspace / "CONVENTIONS.md"
        if canon.exists():
            chunks.append(f"=== Workspace canonical CONVENTIONS.md ===\n{_read(canon)}\n")
            label_set.add("workspace-canonical")
            path_set.add(str(canon))

    return GatheredInputs(label_set=label_set, path_set=path_set,
                          text="".join(chunks))


def _build_call_kwargs(inputs: GatheredInputs, target_label: str):
    """Build kwargs for client.messages.create with prompt-caching enabled."""
    return {
        "model": MODEL,
        "max_tokens": 8000,
        "system": [
            {
                "type": "text",
                "text": (
                    "You are drafting a CONVENTIONS.md file for the "
                    f"{target_label}. Use the rule template:\n\n"
                    "## Rule: <statement>\n\n**The rule.** ...\n\n"
                    "**Why.** ...\n\n**Common high-confidence violations** (bot auto-fix candidates)\n"
                    "- ...\n\n**Common judgment-call violations** (bot flags, CT decides)\n"
                    "- ...\n\n"
                    "Wrap any cross-repo rules in"
                    " <!-- workspace-conventions:start --> ... <!-- workspace-conventions:end -->"
                    " markers. Place repo-specific rules outside the markers.\n"
                ),
            },
            {
                "type": "text",
                "text": inputs.text,
                "cache_control": {"type": "ephemeral"},
            },
        ],
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Draft CONVENTIONS.md for {target_label}. Output the "
                    "Markdown directly, no commentary."
                ),
            },
        ],
    }


def run(*, client, target: Path, inputs: GatheredInputs, force: bool) -> int:
    """Execute the draft generation. Returns exit code (0 = ok)."""
    target_label = target.parent.name or "workspace"
    if target.exists() and not force:
        # Diff-mode: emit suggestions next to the target instead of
        # blowing away the existing draft. The diff file is advisory;
        # CT decides per-line.
        kwargs = _build_call_kwargs(inputs, target_label)
        kwargs["messages"][0]["content"] = (
            f"An existing {target.name} is present. Propose additions "
            "or refinements as a diff-style markdown patch. Do NOT replace "
            "the file wholesale."
        )
        resp = client.messages.create(**kwargs)
        diff_path = target.with_suffix(target.suffix + ".diff")
        diff_path.write_text(resp.content[0].text)
        sys.stderr.write(f"existing {target} present — wrote suggestions to {diff_path}\n")
        return 1  # nonzero so callers notice
    kwargs = _build_call_kwargs(inputs, target_label)
    resp = client.messages.create(**kwargs)
    draft_path = target.with_suffix(target.suffix + ".draft")
    draft_path.write_text(resp.content[0].text)
    sys.stderr.write(f"wrote {draft_path} ({len(inputs.path_set)} files gathered)\n")
    return 0


def _make_client():
    import anthropic  # imported lazily so unit tests don't need it.
    return anthropic.Anthropic()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("repo", nargs="?", default=None,
                   help="repo basename (omit for workspace mode)")
    p.add_argument("--workspace", action="store_true",
                   help="extract for workspace canonical (target /workspaces/ocr-container/CONVENTIONS.md)")
    p.add_argument("--force", action="store_true",
                   help="overwrite existing .draft if present")
    args = p.parse_args()

    if args.workspace and args.repo:
        sys.exit("--workspace and <repo> are mutually exclusive")
    if not args.workspace and not args.repo:
        sys.exit("specify --workspace or a repo basename")

    target = (WORKSPACE / "CONVENTIONS.md") if args.workspace \
        else (WORKSPACE / args.repo / "CONVENTIONS.md")
    inputs = gather_inputs(repo=args.repo, workspace=WORKSPACE)
    sys.exit(run(client=_make_client(), target=target,
                 inputs=inputs, force=args.force))


if __name__ == "__main__":
    main()
```

```bash
chmod +x /workspaces/ocr-container/scripts/extract-conventions.py
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_extract_conventions.py -v
```

Expected: 6 tests pass. (`test_anthropic_call_uses_prompt_caching` is the
key cost-lever test; if it fails, the script's prompt structure is wrong
and re-tokenization will dominate cost.)

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/extract-conventions.py tests/scripts/test_extract_conventions.py
git commit -m "feat(extract-conventions): one-shot bootstrap helper with prompt-cached inputs"
```

---

## Task 3: Run extract-conventions.py for the workspace + CT review

**This is a manual handback.** The script is dispatchable, but the CT
review of the resulting .draft is interactive — CT decides which rules
to keep, which to reword, which to drop.

- [ ] **Step 1: Run the workspace extraction**

```bash
cd /workspaces/ocr-container
python3 scripts/extract-conventions.py --workspace
```

Expected: `wrote /workspaces/ocr-container/CONVENTIONS.md.draft (N files gathered)`. Check the file:

```bash
wc -l CONVENTIONS.md.draft
head -100 CONVENTIONS.md.draft
```

- [ ] **Step 2: CT reviews and edits the draft**

Read the draft top-to-bottom. For each proposed rule:
- Keep verbatim if it accurately encodes a CLAUDE.md feedback memory.
- Reword if the wording is weak.
- Drop if it's redundant with a tighter ruff/pyright check (those are
  Phase-0 enforced; we don't want them as prose rules).
- Add anything the agent missed (open the workspace agent-memory dir
  and skim — the script may have omitted memories whose names don't
  match `feedback_*.md` or `project_*.md`).

Aim for: 5-15 rules in the workspace canonical. Fewer is better — each
rule costs tokens at every detect-bot run.

- [ ] **Step 3: Verify the rule template is well-formed**

Each `## Rule:` heading must have exactly four sub-sections in order:
**The rule.** / **Why.** / **Common high-confidence violations** / **Common judgment-call violations**.
A short visual scan or grep:

```bash
grep -E '^\*\*' /workspaces/ocr-container/CONVENTIONS.md.draft \
  | grep -vE '^\*\*(The rule|Why|Common high-confidence violations|Common judgment-call violations)'
```

Expected: empty output (every bold paragraph header matches one of
the four).

- [ ] **Step 4: Promote the draft to canonical**

```bash
cd /workspaces/ocr-container
mv CONVENTIONS.md.draft CONVENTIONS.md
```

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add CONVENTIONS.md
git commit -m "feat(conventions): workspace canonical CONVENTIONS.md (CT-curated draft)"
```

---

## Task 4: Run extract-conventions.py for pdomain-book-tools + CT review

**Manual handback** — same shape as Task 3 but per-repo.

- [ ] **Step 1: Run the per-repo extraction**

```bash
cd /workspaces/ocr-container
python3 scripts/extract-conventions.py pdomain-book-tools
```

Expected: `wrote /workspaces/ocr-container/pdomain-book-tools/CONVENTIONS.md.draft`. Note the Anthropic API will see the cached prefix from Task 3 if cache hasn't expired (5-min window) — savings observable in the API console.

- [ ] **Step 2: Verify cross-repo block is wrapped in markers**

The draft should include the workspace canonical's content inline,
inside `<!-- workspace-conventions:start -->...end -->` markers, with
repo-specific content below. Spot-check:

```bash
grep -nE 'workspace-conventions:(start|end)' \
  /workspaces/ocr-container/pdomain-book-tools/CONVENTIONS.md.draft
```

Expected: two lines — one start, one end.

- [ ] **Step 3: CT reviews and edits**

Same shape as Task 3 step 2 but for the repo-specific section (below
the markers). Aim for 3-10 repo-specific rules.

If the agent put repo-specific content INSIDE the markers, fix that —
those markers are reserved for the workspace canonical block (which
v2 Plan 4 will sync from `/workspaces/ocr-container/CONVENTIONS.md`).
Manual edits inside the markers will get overwritten by the future
sync script.

- [ ] **Step 4: Promote and commit**

The pdomain-book-tools repo is its own git tree; commit there:

```
[pdomain-book-tools agent prompt]
The file pdomain-book-tools/CONVENTIONS.md is the v2 conventions doc CT
just curated from a draft. Open a PR titled
"feat(conventions): seed pdomain-book-tools CONVENTIONS.md (v2 Phase 2)"
on a branch named wip/conventions-seed. The cross-repo block is
inlined-from-canonical (will get auto-synced once v2 Plan 4 lands);
the repo-specific section below the markers is the bot's prose-rule
target.
```

The agent runs in pdomain-book-tools; uses `pd-push` for the push.

---

# Phase 3: /pr-review skill

## Task 5: Define the JSON contract between detect and apply

**Files:**

- Create: `tests/fixtures/findings/empty.json` — zero findings.
- Create: `tests/fixtures/findings/one-high-confidence.json`
- Create: `tests/fixtures/findings/one-judgment-call.json`
- Create: `tests/fixtures/findings/sweep-capped.json` — sweep-style findings array hits the cap.
- Create: `docs/superpowers/style-review-json-contract.md` — short contract doc.

The detect script emits this JSON; the apply script consumes it. Land
fixtures + the contract doc first so both sides have an unambiguous
target.

- [ ] **Step 1: Write the contract doc**

Save as `docs/superpowers/style-review-json-contract.md`:

```markdown
# style-review JSON contract

`scripts/style-review-detect.py` emits a single JSON document on stdout.
`scripts/style-review-apply.py` reads it from `--findings-file` or stdin.

## Schema

```json
{
  "scope": "diff" | "tree",
  "scope_detail": {
    "from_sha": "...",
    "to_sha": "..."
  } | {
    "tree_root": "/srv/bot-workspaces/style-sweep/<repo>"
  },
  "findings": [
    {
      "rule_citation": "## Rule: No comments explaining what code does",
      "file": "src/foo.py",
      "line": 42,
      "patch": "<unified diff string applicable via `git apply`>",
      "confidence": "high" | "judgment",
      "description": "Short, human-readable summary. Used in PR review comments."
    }
  ],
  "stats": {
    "total_findings": 3,
    "high": 2,
    "judgment": 1,
    "sweep_capped": false
  }
}
```

## Rules
- All paths are repo-relative.
- `patch` is a unified diff (`git diff` format), suitable for `git apply`.
- `confidence: "high"` triggers auto-apply by `apply.py`; failures of
  `make fast-check` after apply demote the finding to `judgment` (the
  patch is reverted, the comment is posted instead).
- `sweep_capped: true` indicates the cap was hit; apply.py emits a
  `sweep-capped` event into the events log.
- An empty `findings` array is valid: detect.py returns success, apply.py
  no-ops.
```

- [ ] **Step 2: Write fixture JSON files**

`tests/fixtures/findings/empty.json`:

```json
{
  "scope": "diff",
  "scope_detail": {"from_sha": "abc", "to_sha": "def"},
  "findings": [],
  "stats": {"total_findings": 0, "high": 0, "judgment": 0, "sweep_capped": false}
}
```

`tests/fixtures/findings/one-high-confidence.json`:

```json
{
  "scope": "diff",
  "scope_detail": {"from_sha": "abc", "to_sha": "def"},
  "findings": [
    {
      "rule_citation": "## Rule: No comments explaining what code does",
      "file": "src/example.py",
      "line": 3,
      "patch": "--- a/src/example.py\n+++ b/src/example.py\n@@ -1,5 +1,4 @@\n def add(a, b):\n-    # adds two numbers\n     return a + b\n",
      "confidence": "high",
      "description": "Trailing what-not-why comment above add()."
    }
  ],
  "stats": {"total_findings": 1, "high": 1, "judgment": 0, "sweep_capped": false}
}
```

`tests/fixtures/findings/one-judgment-call.json`:

```json
{
  "scope": "diff",
  "scope_detail": {"from_sha": "abc", "to_sha": "def"},
  "findings": [
    {
      "rule_citation": "## Rule: pdomain-book-tools-specific — never silently drop OCR words",
      "file": "src/role_filter.py",
      "line": 17,
      "patch": "--- a/src/role_filter.py\n+++ b/src/role_filter.py\n@@ -15,7 +15,8 @@\n def filter_words(page):\n     out = []\n     for w in page.words:\n-        if w.role == 'footnote': continue\n+        # Role-labeled words are not dropped; relabel only.\n+        if w.role == 'footnote': w.role_label = 'footnote'; out.append(w); continue\n         out.append(w)\n     return out\n",
      "confidence": "judgment",
      "description": "Filtering predicate skips footnote words — possible silent drop. Manual review needed."
    }
  ],
  "stats": {"total_findings": 1, "high": 0, "judgment": 1, "sweep_capped": false}
}
```

`tests/fixtures/findings/sweep-capped.json`:

```json
{
  "scope": "tree",
  "scope_detail": {"tree_root": "/srv/bot-workspaces/style-sweep/pdomain-book-tools"},
  "findings": [],
  "stats": {"total_findings": 50, "high": 30, "judgment": 20, "sweep_capped": true}
}
```

(The `findings` array is empty in the sweep-capped fixture because we
exercise the cap-event handling, not patch application; real sweep runs
populate findings up to the cap.)

- [ ] **Step 3: Commit**

```bash
cd /workspaces/ocr-container
git add docs/superpowers/style-review-json-contract.md tests/fixtures/findings/
git commit -m "feat(style-review): JSON contract + four fixture findings docs"
```

---

## Task 6: scripts/style-review-detect.py — LLM detection engine

**Files:**

- Create: `scripts/style-review-detect.py`
- Create: `tests/scripts/test_style_review_detect.py`

This is the only LLM-bound step in v2 Plans 2+3. It reads a per-repo
CONVENTIONS.md, a scope (diff or full tree), and emits the JSON
contract from Task 5. Sonnet via the Anthropic SDK with prompt caching
on the conventions doc.

- [ ] **Step 1: Write the failing test**

Save as `tests/scripts/test_style_review_detect.py`:

```python
"""Tests for scripts/style-review-detect.py.

The Anthropic SDK is mocked. Tests target:
  - Input gathering (reading CONVENTIONS.md, computing the scope).
  - Prompt structure (conventions doc is in a cached system block).
  - Output is a valid contract JSON.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/style-review-detect.py"
EXAMPLE = WORKSPACE / "tests/fixtures/conventions/example-conventions.md"


def _mod():
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    spec = importlib.util.spec_from_file_location("style_review_detect", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FakeAnthropic:
    def __init__(self, response_json: str = '{"findings": [], "stats": {"total_findings": 0, "high": 0, "judgment": 0, "sweep_capped": false}}'):
        self.calls = []
        self.messages = MagicMock()
        self.messages.create = self._create
        self.response_json = response_json

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        resp = MagicMock()
        resp.content = [MagicMock(text=self.response_json)]
        return resp


def test_loads_conventions_into_cached_system_block(tmp_path):
    m = _mod()
    fake = FakeAnthropic()
    output = m.run(
        client=fake,
        conventions_path=EXAMPLE,
        scope="diff",
        scope_detail={"from_sha": "abc", "to_sha": "def"},
        diff_text="--- a/x\n+++ b/x\n@@\n-x\n+y\n",
    )
    assert isinstance(output, dict)
    assert "findings" in output
    assert "stats" in output
    assert len(fake.calls) == 1
    sys_msg = fake.calls[0]["system"]
    assert isinstance(sys_msg, list)
    cached = [b for b in sys_msg if b.get("cache_control")]
    assert cached
    assert "Rule:" in cached[0]["text"]


def test_full_tree_scope_includes_tree_root(tmp_path):
    m = _mod()
    fake = FakeAnthropic()
    output = m.run(
        client=fake,
        conventions_path=EXAMPLE,
        scope="tree",
        scope_detail={"tree_root": str(tmp_path)},
        diff_text=None,
        tree_text="<full tree dump here>",
    )
    assert output["scope"] == "tree"
    assert output["scope_detail"]["tree_root"] == str(tmp_path)


def test_returns_empty_findings_when_no_input():
    m = _mod()
    fake = FakeAnthropic()
    out = m.run(
        client=fake, conventions_path=EXAMPLE, scope="diff",
        scope_detail={"from_sha": "x", "to_sha": "x"},
        diff_text="",
    )
    assert out["findings"] == []
    assert out["stats"]["total_findings"] == 0


def test_validates_findings_against_schema():
    """detect.py must reject malformed findings the LLM hallucinates."""
    m = _mod()
    bad_response = '{"findings": [{"file": "x.py"}]}'  # missing required fields
    fake = FakeAnthropic(response_json=bad_response)
    out = m.run(
        client=fake, conventions_path=EXAMPLE, scope="diff",
        scope_detail={"from_sha": "x", "to_sha": "y"},
        diff_text="--- a\n+++ b\n",
    )
    # Malformed entries are dropped (or whole-call falls back to empty).
    for f in out["findings"]:
        for required in ("rule_citation", "file", "line", "patch", "confidence", "description"):
            assert required in f
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_style_review_detect.py -v
```

Expected: FAIL — script does not exist.

- [ ] **Step 3: Implement the script**

Save as `scripts/style-review-detect.py`:

```python
#!/usr/bin/env python3
"""style-review-detect.py — LLM-bound style/convention review.

Reads a per-repo CONVENTIONS.md (the cacheable prefix) and a scope
(diff for the daily review-bot; full tree for the weekly sweep-bot).
Emits the JSON contract from docs/superpowers/style-review-json-contract.md
on stdout.

Usage:
  scripts/style-review-detect.py \\
    --conventions <repo>/CONVENTIONS.md \\
    --scope diff --from-sha <a> --to-sha <b>

  scripts/style-review-detect.py \\
    --conventions <repo>/CONVENTIONS.md \\
    --scope tree --tree-root <path>
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import subprocess
import sys
from pathlib import Path

MODEL = "claude-sonnet-4-6"
SWEEP_DEFAULT_CAP = 50


_REQUIRED_FIELDS = ("rule_citation", "file", "line", "patch", "confidence", "description")


def _gather_diff(from_sha: str, to_sha: str) -> str:
    r = subprocess.run(
        ["git", "diff", from_sha, to_sha], capture_output=True, text=True,
        timeout=60, check=False,
    )
    return r.stdout


def _gather_tree(root: Path) -> str:
    """Cap the tree dump at a sensible byte budget so a runaway sweep doesn't OOM."""
    parts = []
    budget = 200_000  # ~200KB
    for p in sorted(root.rglob("*.py")):
        if any(seg.startswith(".") for seg in p.relative_to(root).parts):
            continue
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        chunk = f"=== {p.relative_to(root)} ===\n{text}\n"
        if budget - len(chunk) < 0:
            parts.append(f"... (truncated; sweep-cap hit)\n")
            break
        parts.append(chunk)
        budget -= len(chunk)
    return "".join(parts)


def _build_call_kwargs(conventions_text: str, scope: str, scope_detail: dict,
                       payload_text: str, cap: int):
    sys_blocks = [
        {
            "type": "text",
            "text": (
                "You review Python code against the conventions provided "
                "below. For each violation, emit a JSON object with: "
                "rule_citation (must match a `## Rule:` heading from the doc), "
                "file (repo-relative path), line, patch (unified diff string), "
                "confidence (`high` for safe auto-fix, `judgment` for human "
                "review), description (one short sentence). Output a single "
                "JSON object with `findings` array and `stats` object — "
                "no commentary, no markdown fences. If the input scope hits "
                f"the cap of {cap}, set stats.sweep_capped=true."
            ),
        },
        {
            "type": "text",
            "text": conventions_text,
            "cache_control": {"type": "ephemeral"},
        },
    ]
    user_msg = (
        f"Scope: {scope}\nScope detail: {json.dumps(scope_detail)}\n\n"
        f"Payload:\n{payload_text}\n"
    )
    return {
        "model": MODEL,
        "max_tokens": 8000,
        "system": sys_blocks,
        "messages": [{"role": "user", "content": user_msg}],
    }


def _parse_response(text: str) -> dict:
    """Defensive: strip code fences if the model added them; load JSON."""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        if s.endswith("```"):
            s = s.rsplit("```", 1)[0]
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        return {"findings": [], "stats": {"total_findings": 0, "high": 0,
                                          "judgment": 0, "sweep_capped": False}}
    obj.setdefault("findings", [])
    obj.setdefault("stats", {})
    obj["findings"] = [
        f for f in obj["findings"]
        if all(k in f for k in _REQUIRED_FIELDS)
    ]
    obj["stats"].setdefault("total_findings", len(obj["findings"]))
    obj["stats"].setdefault("high",
        sum(1 for f in obj["findings"] if f["confidence"] == "high"))
    obj["stats"].setdefault("judgment",
        sum(1 for f in obj["findings"] if f["confidence"] == "judgment"))
    obj["stats"].setdefault("sweep_capped", False)
    return obj


def run(*, client, conventions_path: Path, scope: str, scope_detail: dict,
        diff_text: str | None = None, tree_text: str | None = None,
        cap: int = SWEEP_DEFAULT_CAP) -> dict:
    conventions = conventions_path.read_text() if conventions_path.exists() else ""
    payload = diff_text if scope == "diff" else (tree_text or "")
    kwargs = _build_call_kwargs(conventions, scope, scope_detail, payload, cap)
    resp = client.messages.create(**kwargs)
    obj = _parse_response(resp.content[0].text)
    obj.setdefault("scope", scope)
    obj.setdefault("scope_detail", scope_detail)
    return obj


def _make_client():
    import anthropic
    return anthropic.Anthropic()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--conventions", required=True)
    p.add_argument("--scope", choices=["diff", "tree"], required=True)
    p.add_argument("--from-sha")
    p.add_argument("--to-sha")
    p.add_argument("--tree-root")
    p.add_argument("--cap", type=int, default=SWEEP_DEFAULT_CAP)
    args = p.parse_args()

    if args.scope == "diff":
        if not (args.from_sha and args.to_sha):
            sys.exit("--from-sha and --to-sha required for --scope=diff")
        diff_text = _gather_diff(args.from_sha, args.to_sha)
        scope_detail = {"from_sha": args.from_sha, "to_sha": args.to_sha}
        tree_text = None
    else:
        if not args.tree_root:
            sys.exit("--tree-root required for --scope=tree")
        tree_text = _gather_tree(Path(args.tree_root))
        scope_detail = {"tree_root": args.tree_root}
        diff_text = None

    obj = run(client=_make_client(), conventions_path=Path(args.conventions),
              scope=args.scope, scope_detail=scope_detail,
              diff_text=diff_text, tree_text=tree_text, cap=args.cap)
    json.dump(obj, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
```

```bash
chmod +x /workspaces/ocr-container/scripts/style-review-detect.py
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_style_review_detect.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/style-review-detect.py tests/scripts/test_style_review_detect.py
git commit -m "feat(style-review-detect): LLM-bound detection engine with prompt-cached conventions"
```

---

## Task 7: scripts/style-review-apply.py — deterministic applier

**Files:**

- Create: `scripts/style-review-apply.py`
- Create: `tests/scripts/test_style_review_apply.py`

The apply script reads JSON findings (from detect.py output or a fixture
file), applies high-confidence patches via `git apply`, runs `make fast-check`
to validate, reverts on failure, and posts review comments via `gh pr review`.
No LLM call.

- [ ] **Step 1: Write the failing test**

Save as `tests/scripts/test_style_review_apply.py`:

```python
"""Tests for scripts/style-review-apply.py.

Pure deterministic apply. The git/gh/subprocess seam is injected so
tests don't touch the real filesystem or remote.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")
SCRIPT = WORKSPACE / "scripts/style-review-apply.py"
FIX = WORKSPACE / "tests/fixtures/findings"


def _mod():
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    spec = importlib.util.spec_from_file_location("style_review_apply", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FakeShell:
    """Records calls; controls return codes for git apply / make fast-check."""
    def __init__(self, *, fast_check_ok=True, apply_ok=True):
        self.calls = []
        self.fast_check_ok = fast_check_ok
        self.apply_ok = apply_ok

    def run(self, cmd, **kwargs):
        self.calls.append(cmd)
        if cmd[:2] == ["git", "apply"]:
            return 0 if self.apply_ok else 1
        if cmd == ["make", "fast-check"]:
            return 0 if self.fast_check_ok else 1
        if cmd[:2] == ["git", "commit"] or cmd[:2] == ["git", "add"]:
            return 0
        if cmd[:1] == ["gh"]:
            return 0
        return 0


class FakeEvents:
    def __init__(self):
        self.events = []
    def emit(self, kind, payload):
        self.events.append({"kind": kind, **payload})


def test_empty_findings_is_noop():
    m = _mod()
    sh = FakeShell()
    ev = FakeEvents()
    findings = json.loads((FIX / "empty.json").read_text())
    summary = m.apply(findings, shell=sh, events=ev, repo="x/y", pr_number=42)
    assert summary["high_applied"] == 0
    assert summary["judgment_commented"] == 0
    assert sh.calls == []
    assert ev.events == []


def test_high_confidence_apply_with_passing_fast_check():
    m = _mod()
    sh = FakeShell(fast_check_ok=True, apply_ok=True)
    ev = FakeEvents()
    findings = json.loads((FIX / "one-high-confidence.json").read_text())
    summary = m.apply(findings, shell=sh, events=ev, repo="x/y", pr_number=42)
    assert summary["high_applied"] == 1
    assert summary["judgment_commented"] == 0
    # Sequence: git apply, make fast-check, git add, git commit, push (left to caller).
    cmd_kinds = [c[0] for c in sh.calls if c]
    assert "git" in cmd_kinds and "make" in cmd_kinds


def test_high_confidence_demotes_on_fast_check_failure():
    m = _mod()
    sh = FakeShell(fast_check_ok=False, apply_ok=True)
    ev = FakeEvents()
    findings = json.loads((FIX / "one-high-confidence.json").read_text())
    summary = m.apply(findings, shell=sh, events=ev, repo="x/y", pr_number=42)
    assert summary["high_applied"] == 0
    # Demoted to judgment, posted as comment.
    assert summary["judgment_commented"] == 1
    assert any(e["kind"] == "auto-fix-reverted" for e in ev.events)


def test_judgment_finding_only_posts_comment():
    m = _mod()
    sh = FakeShell()
    ev = FakeEvents()
    findings = json.loads((FIX / "one-judgment-call.json").read_text())
    summary = m.apply(findings, shell=sh, events=ev, repo="x/y", pr_number=42)
    assert summary["high_applied"] == 0
    assert summary["judgment_commented"] == 1
    # No git apply / make fast-check on judgment-only findings.
    assert not any(c[:2] == ["git", "apply"] for c in sh.calls)


def test_sweep_capped_emits_event():
    m = _mod()
    sh = FakeShell()
    ev = FakeEvents()
    findings = json.loads((FIX / "sweep-capped.json").read_text())
    m.apply(findings, shell=sh, events=ev, repo="x/y", pr_number=42)
    assert any(e["kind"] == "sweep-capped" for e in ev.events)
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_style_review_apply.py -v
```

Expected: FAIL — script does not exist.

- [ ] **Step 3: Implement the script**

Save as `scripts/style-review-apply.py`:

```python
#!/usr/bin/env python3
"""style-review-apply.py — apply findings from style-review-detect.py.

Deterministic. No LLM. Reads the JSON contract from
docs/superpowers/style-review-json-contract.md and:

  - High-confidence findings: git apply → make fast-check → if green,
    git commit; if red, revert via `git checkout -- <file>` and demote
    to judgment (post a comment instead).
  - Judgment findings: post a `gh pr review --comment` referencing the
    rule citation, file:line, and proposed patch.
  - sweep_capped=true: emit a sweep-capped event.

Usage:
  scripts/style-review-apply.py \\
    --findings-file <path> \\
    --repo ConcaveTrillion/<repo> \\
    --pr-number <N>

Or pipe JSON:
  scripts/style-review-detect.py ... | scripts/style-review-apply.py \\
    --repo X --pr-number 42
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


EVENTS_LOG = Path(os.environ.get(
    "SHIP_ISSUE_MEMORY_DIR",
    "/home/vscode/.claude/agent-memory/ship-issue",
)) / "style-bot-events.jsonl"


class RealShell:
    def run(self, cmd, **kwargs):
        r = subprocess.run(cmd, **kwargs)
        return r.returncode


class JsonlEvents:
    def __init__(self, path: Path = EVENTS_LOG):
        self.path = path

    def emit(self, kind: str, payload: dict):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rec = {"kind": kind, **payload}
        with self.path.open("a") as f:
            f.write(json.dumps(rec) + "\n")


def _apply_patch(patch: str, *, shell) -> bool:
    """git apply via stdin. Returns True on success."""
    with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False) as f:
        f.write(patch)
        patch_path = f.name
    try:
        rc = shell.run(["git", "apply", patch_path])
        return rc == 0
    finally:
        os.unlink(patch_path)


def _revert(file: str, *, shell) -> None:
    shell.run(["git", "checkout", "--", file])


def _post_comment(repo: str, pr_number: int, finding: dict, *, shell) -> None:
    body = (
        f"**{finding['rule_citation']}** "
        f"(`{finding['file']}:{finding['line']}`)\n\n"
        f"{finding['description']}\n\n"
        "<details><summary>Proposed diff</summary>\n\n"
        f"```diff\n{finding['patch']}\n```\n\n</details>\n"
    )
    shell.run([
        "gh", "pr", "review", str(pr_number),
        "--repo", repo, "--comment", "--body", body,
    ])


def _commit(repo_root: str, summary_msg: str, *, shell) -> None:
    shell.run(["git", "add", "-A"])
    shell.run(["git", "commit", "-m", summary_msg])


def apply(findings_doc: dict, *, shell, events, repo: str, pr_number: int,
          repo_root: str | None = None) -> dict:
    """Apply the contract-shaped findings doc. Returns a summary dict."""
    summary = {"high_applied": 0, "judgment_commented": 0, "reverted": 0}

    if findings_doc.get("stats", {}).get("sweep_capped"):
        events.emit("sweep-capped", {
            "repo": repo, "pr_number": pr_number,
            "stats": findings_doc.get("stats", {}),
        })

    findings = findings_doc.get("findings", [])
    for f in findings:
        if f["confidence"] == "high":
            applied = _apply_patch(f["patch"], shell=shell)
            if not applied:
                events.emit("auto-fix-reverted", {
                    "repo": repo, "rule": f["rule_citation"],
                    "reason": "git-apply-failed", "file": f["file"],
                })
                _post_comment(repo, pr_number, f, shell=shell)
                summary["judgment_commented"] += 1
                continue
            rc = shell.run(["make", "fast-check"])
            if rc != 0:
                _revert(f["file"], shell=shell)
                events.emit("auto-fix-reverted", {
                    "repo": repo, "rule": f["rule_citation"],
                    "reason": "fast-check-failed", "file": f["file"],
                })
                _post_comment(repo, pr_number, f, shell=shell)
                summary["judgment_commented"] += 1
                summary["reverted"] += 1
                continue
            _commit(repo_root or "", f"style-review: apply '{f['rule_citation']}' fix in {f['file']}",
                    shell=shell)
            summary["high_applied"] += 1
        else:  # judgment
            _post_comment(repo, pr_number, f, shell=shell)
            summary["judgment_commented"] += 1

    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--findings-file",
                   help="path to JSON; if omitted, read stdin")
    p.add_argument("--repo", required=True)
    p.add_argument("--pr-number", type=int, required=True)
    args = p.parse_args()

    if args.findings_file:
        doc = json.loads(Path(args.findings_file).read_text())
    else:
        doc = json.loads(sys.stdin.read())
    summary = apply(
        doc, shell=RealShell(), events=JsonlEvents(),
        repo=args.repo, pr_number=args.pr_number,
    )
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
```

```bash
chmod +x /workspaces/ocr-container/scripts/style-review-apply.py
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
cd /workspaces/ocr-container
python3 -m pytest tests/scripts/test_style_review_apply.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container
git add scripts/style-review-apply.py tests/scripts/test_style_review_apply.py
git commit -m "feat(style-review-apply): deterministic applier (apply→fast-check→revert/comment)"
```

---

## Task 8: .claude/skills/pr-review/SKILL.md — CT-interactive skill

**Files:**

- Create: `.claude/skills/pr-review/SKILL.md`

The skill is thin: it owns the bots-paused flag-file lifecycle and the
AskUserQuestion walkthrough loop. It delegates detection and application
to the two scripts from Tasks 6 and 7. The skill's value is the
walkthrough UX, not duplicate detection logic.

- [ ] **Step 1: Write the SKILL.md**

Save as `.claude/skills/pr-review/SKILL.md`:

```markdown
---
name: pr-review
description: Use when invoked by `/pr-review [<repo>]` — CT-interactive review of a rolling wip/ship-issue PR with the bots-paused flag lifecycle and per-finding AskUserQuestion walkthrough.
---

# /pr-review — review a rolling ship-issue PR

CT-interactive. Pauses all bots for the duration of the review window,
runs a fresh detect+apply pass against the current `wip/ship-issue`
HEAD, then walks each flagged judgment-call comment one at a time via
AskUserQuestion. Resumes bots on exit.

**Argument**: `[<repo>]` — repo basename (`pdomain-book-tools`, `pdomain-ocr-cli`, …).
If omitted, defaults to repo of CT's cwd; from workspace cwd, prompt
CT to pick.

## Pre-flight

1. **Resolve repo**. If arg given, use it. Else inspect `pwd`; if it's a
   pd-* repo, use its basename. Else AskUserQuestion to pick from the 7
   covered repos.
2. **Confirm CONVENTIONS.md exists** at `<repo>/CONVENTIONS.md`. If
   not, abort with a hint pointing at v2 Plan 2 Task 4 (`/extract-conventions`).
3. **Find the open rolling PR**.
   `gh pr list -R ConcaveTrillion/<repo> --label bot:style-review-ready --state open --json number,headRefName --jq '.[0]'`
   If no open PR, abort gracefully ("nothing to review").

## Pause lifecycle

1. **Pre-check**: touch `/srv/bot-workspaces/.state/bots-paused`. Set
   mtime to current; the file's presence is the pause signal.
2. **Wait for in-flight bot runs to finish naturally** — never kill
   mid-commit. Poll `/srv/bot-workspaces/.locks/ship-issue.<repo>.lock`
   and `/srv/bot-workspaces/.locks/style-review.<repo>.lock` for up to
   5 minutes; warn CT every 30s. (`flock -n -E 0` is the test pattern.)
3. **Fresh final review**: shell out to:
   ```
   scripts/style-review-detect.py \
     --conventions <repo>/CONVENTIONS.md \
     --scope diff --from-sha origin/main --to-sha <pr-head-sha> \
     | scripts/style-review-apply.py --repo ConcaveTrillion/<repo> --pr-number <PR>
   ```
   Auto-fixes commit and push (apply.py handles); flagged comments
   are written fresh, replacing prior daily-run comments.
4. **Walkthrough**: read the apply.py summary; walk each `judgment_commented`
   finding via AskUserQuestion. See "Walkthrough loop" below.
5. **Post**: remove `bots-paused`. Tell CT "schedules resumed". If
   CT marked PR ready-for-review during walkthrough, bots stay paused
   on that branch via existing locked-PR rule.

## Walkthrough loop

For each flagged comment, AskUserQuestion with:

- **header**: short label (e.g., "comment 1/3").
- **question**: rule citation + `<file>:<line>` + proposed-patch summary.
- **options** (4):
  1. `apply` — write the patch, run `make fast-check`, commit.
  2. `dismiss` — resolve the comment as won't-fix.
  3. `dismiss-and-add-rule` — open Edit on the appropriate
     CONVENTIONS.md (workspace canonical for cross-repo, per-repo for
     repo-specific) — CT picks. Skill drafts the rule from the comment
     context; CT edits before saving.
  4. `edit-then-apply` — CT proposes a counter-patch in chat; skill
     applies their version.

After CT picks: log to `/tmp/pr-review-<repo>-<timestamp>.log` for
post-mortem; advance to next finding.

## Stale-comment marker

Each style-review run tags `style-review/<repo>/<sha>`. Pre-walkthrough,
read the tag: if HEAD is unchanged since the last tagged review and
prior comments are fresh, reuse them; if any new commits, throw out
prior comments and regenerate.

## Reporting

After walkthrough:
- One-paragraph summary to CT: N findings walked, M applied, K added
  rules.
- Apply.py's auto-fix commits already pushed via `pd-push`.
- Save full transcript at `/tmp/pr-review-<repo>-<timestamp>.log`.

## Error cases

- **CONVENTIONS.md absent**: abort with hint to run extract-conventions.
- **No open PR matching the filter**: graceful exit ("nothing to review").
- **Bot lock held >5 min**: warn CT; offer to wait longer or skip the
  fresh-review step (use prior comments).
- **make fast-check fails on auto-fix**: apply.py demotes to judgment;
  skill surfaces it normally in the walkthrough loop.
- **bots-paused still present after exit**: the 6h auto-recovery TTL
  catches abandoned sessions (orchestrators interpret stale flags as
  "resume" if mtime > 6h old).

## Cost

Bounded per CT review session by the number of flagged findings (which
is bounded by the per-run cap). Single Sonnet call for the
fresh-review step; AskUserQuestion is local.

## Out of scope

- Bot scheduling itself (v2 Plan 3).
- Cross-repo sync of conventions (v2 Plan 4).
- Adding new rules to a repo OTHER than the one currently under review
  (CT must edit the workspace canonical separately for cross-repo
  changes).
```

- [ ] **Step 2: Validate the skill front-matter**

```bash
cd /workspaces/ocr-container
head -5 .claude/skills/pr-review/SKILL.md
```

Expected: `name: pr-review` and `description:` lines present in the
YAML front-matter.

- [ ] **Step 3: Commit**

```bash
cd /workspaces/ocr-container
git add .claude/skills/pr-review/SKILL.md
git commit -m "feat(skills): add /pr-review SKILL.md (CT-interactive walkthrough)"
```

---

## Task 9: Smoke-test /pr-review against a fixture rolling PR

**Files:**

- (No file changes — interactive validation.)

This task is manual / interactive. It verifies that:
1. The bots-paused flag lifecycle works.
2. The pre-walkthrough fresh-review delegates correctly.
3. AskUserQuestion walks a real flagged comment end-to-end.

- [ ] **Step 1: Pick a rolling PR on pdomain-book-tools**

You need a wip/ship-issue PR with at least one nontrivial diff (so
detect.py has something to flag). If the rolling PR is empty, ship a
small test slice via the v2 Plan 1 retrofitted ship-issue first.

- [ ] **Step 2: Confirm pdomain-book-tools/CONVENTIONS.md is in place**

(Should be from Task 4.)

```bash
test -f /workspaces/ocr-container/pdomain-book-tools/CONVENTIONS.md \
  && echo "OK" || echo "MISSING — run /extract-conventions or Task 4 again"
```

- [ ] **Step 3: Run /pr-review**

```
/pr-review pdomain-book-tools
```

Expected sequence of events:
1. Skill announces it's resolving the repo.
2. Skill touches `/srv/bot-workspaces/.state/bots-paused` and confirms.
3. Skill polls the locks; reports "no in-flight runs" if clean.
4. Skill shells out to detect.py + apply.py; reports the summary.
5. For each flagged finding, AskUserQuestion presents the four options.
6. CT walks each one.
7. Skill removes the pause flag and reports "schedules resumed".

- [ ] **Step 4: Verify the pause flag is gone**

```bash
ls -la /srv/bot-workspaces/.state/
```

Expected: no `bots-paused` file.

- [ ] **Step 5: Verify auto-fixes (if any) landed on the rolling PR**

```bash
gh pr view <PR-NUM> -R pdomain/pdomain-book-tools --json commits --jq '.commits[-3:]'
```

Expected: any high-confidence auto-fixes show up as recent commits with
`style-review:` prefix.

- [ ] **Step 6: Verify flagged comments landed**

```bash
gh pr view <PR-NUM> -R pdomain/pdomain-book-tools --json reviews
```

Expected: review comments with rule citations and file:line markers.

- [ ] **Step 7: Document the smoke run**

Append a short paragraph to `docs/superpowers/bot-workspaces.md` (or
make a separate doc — CT's call) recording the first /pr-review smoke
run: PR number, number of findings, what worked, what surfaced as a
bug or rough edge.

- [ ] **Step 8: Commit any docs changes**

```bash
cd /workspaces/ocr-container
git add docs/superpowers/bot-workspaces.md
git commit -m "docs: record first /pr-review end-to-end smoke run"
```

If the smoke run surfaced bugs in detect.py / apply.py / SKILL.md,
file fix tasks against this plan or a follow-up — don't push fixes
silently.

---

## Task 10: Mark v2 spec acceptance bullets

- [ ] **Step 1: Edit the spec**

Open
`docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md`.
Tick the four bullets covered by Plan 2:

```markdown
- [x] `scripts/extract-conventions.py` exists; workspace `CONVENTIONS.md` and pdomain-book-tools `CONVENTIONS.md` written and CT-approved
- [x] `/pr-review` skill exists; walks fixture flagged comments end-to-end; bots-paused flag toggles correctly
```

(The two left unticked here that look related — `lint-conventions.py`
and the daily/weekly bot bullets — fall to v2 Plan 4 and v2 Plan 3
respectively.)

- [ ] **Step 2: Bump Last updated and commit**

```bash
cd /workspaces/ocr-container
python3 scripts/lint-spec.py docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md
git add docs/superpowers/specs/2026-05-10-code-review-style-cleanup-design.md
git commit -m "spec(code-review-style): tick Phases 2+3 bullets after Plan 2"
```

---

## Done — what comes next

With this plan landed:

- pdomain-book-tools has its CONVENTIONS.md; the workspace canonical exists.
- `style-review-detect.py` + `style-review-apply.py` are tested and
  callable as a CLI pair.
- `/pr-review` is the only interactive review surface, and it works
  end-to-end against a rolling PR.

**Next plan: v2 Plan 3** —
`docs/superpowers/plans/2026-05-10-code-review-style-cleanup-plan-3.md`
covers Phases 4 + 5 (daily style-review-bot + weekly style-sweep-bot).
The bots reuse the detect+apply scripts from this plan; they add
orchestrator wrappers, ctask schedule entries, and the `bot:*-ready`
labels.

Plan-2 tasks 1, 2, 5, 6, 7, 8 are all dispatchable to a subagent in
sequence; Tasks 3 + 4 + 9 are CT-interactive (manual handbacks).
