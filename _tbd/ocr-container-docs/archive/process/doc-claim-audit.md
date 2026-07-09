---
name: doc-claim-audit
description: Use when auditing Markdown docs for writing style, factual correctness, stale plan items, broken links, and claims that must be validated against code, tests, config, or official references.
---

# Doc Claim Audit

## Overview

Audit documentation by assigning one Markdown file per agent. Each agent owns
a single file, validates claims against primary evidence, edits only that file,
and reports what changed.

Core rule: docs must describe what is true now. Completed plan items should be
removed or reduced to short historical notes only when the file still needs
them.

## When to Use

Use this when the user asks to:

- Review many docs for correctness or writing style.
- Validate docs against actual code, tests, configs, workflows, lockfiles, or
  upstream libraries.
- Clean active plans by removing completed items.
- Run doc cleanup with parallel subagents.
- Audit stale Markdown after a large implementation.

Do not use this for a single quick typo fix or for a docs task that requires
changing code behavior.

## Setup

1. Read project guidance first:
   - `AGENTS.md`
   - `CLAUDE.md`
   - `CONVENTIONS.md`
   - `CONTRIBUTING.md`
   - Any repo writing-style doc, such as `docs/process/writing-style.md`
2. Use the git-worktree workflow if available or requested.
3. Inventory Markdown files:

   ```bash
   find docs -name '*.md' -type f | sort
   ```

4. Run a lightweight baseline if practical:
   - Prefer repo Make targets.
   - For docs-only work, at least run the repo Markdown lint target or
     pre-commit hook if one exists.

## Agent Dispatch Pattern

Dispatch one worker per Markdown file.

Each worker must have:

- One assigned Markdown file.
- A disjoint write scope.
- Instructions to read repo guidance.
- Instructions to validate claims against primary evidence.
- Permission to edit only its assigned file.
- A final report format.

Use waves if the agent limit is lower than the number of files.

## Worker Prompt Template

```markdown
You are auditing exactly ONE Markdown file in this repo: `<path>`.

Workspace: `<absolute-worktree-path>`.

Project guidance:
- Read `AGENTS.md`, `CLAUDE.md`, `CONVENTIONS.md`, `CONTRIBUTING.md`, and the
  repo writing-style doc before editing.
- Do not change code.
- You are not alone in the codebase. Other agents may edit other docs in
  parallel.
- Do not revert or touch work outside your assigned file.

Task:
1. Examine only `<path>` for writing style, correctness, stale statements,
   broken local links, and claims that need validation.
2. Validate factual claims against actual code, tests, config, workflows,
   lockfiles, scripts, and local docs.
3. For external library or tool claims, prefer local lockfiles, source, and
   config first. Use official web docs only when local evidence is insufficient.
4. If this is a plan, status, or report file, remove items that are already
   complete. Leave only genuinely current work, or reduce completed plans to a
   short pointer to current work.
5. Fix the file in place. You may edit only `<path>`.
6. Do not commit.

Return:
- Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`
- Changed paths
- Key claims checked
- Completed items removed, if any
- Verification run
- Remaining concerns
```

## Evidence Rules

Use primary evidence first:

- Public API claims: source, stubs, tests, README.
- Command claims: `Makefile`, scripts, pyproject, Cargo config, workflows.
- Dependency claims: lockfiles, manifests, audit configs, notice tooling.
- Release claims: workflows, pyproject, packaging tests, release docs.
- Upstream claims: pinned versions and local crate or package metadata first;
  official upstream pages only when needed.
- Hosted-service claims: mark as unproven if they depend on GitHub, PyPI,
  secrets, or settings not visible in the checkout.

## Review And Integration

As agents finish:

1. Read each report.
2. Close completed agent slots before dispatching more.
3. Treat "other docs modified" as expected when each worker stayed in scope.
4. Investigate `NEEDS_CONTEXT` or `BLOCKED` before continuing.
5. After all agents finish, inspect the combined diff.
6. Run repo-level verification:
   - Markdown lint or pre-commit for changed docs.
   - `git diff --check`.
   - Broader tests only when docs changes affect commands, examples, or
     generated docs.

## Common Mistakes

- Giving one agent multiple files.
- Letting agents edit code to make docs true.
- Keeping completed checklist items in active plan docs.
- Validating against memory instead of source files.
- Using unofficial web sources when local or official sources exist.
- Running too many agents without closing completed ones.
- Treating hosted CI, secrets, or PyPI settings as proven from local files.
