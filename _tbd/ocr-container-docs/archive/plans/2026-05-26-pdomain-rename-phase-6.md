# Phase 6 — pd-* → pdomain-* code-ref + URL-owner flip

> **For agentic workers:** Self-contained prompt. Read the whole file before starting.

## Context

Phase 5 (`docs/plans/2026-05-26-pdomain-rename-phase-5.md`) finished the
prose / dirs / agents / memory / slash-commands / hooks rename for the 12
active `pd-* → pdomain-*` repos. Final workspace-wide grep dropped
**4677 → 290** active-name hits. Remaining hits are in **code**, **test
fixtures**, **devcontainer bootstrap**, and **skill markdown** — outside
Phase 5's prose scope.

Phase 4.5 (`docs/handoff-next-session.md`) **also transferred the GH org**:
`ConcaveTrillion/pdomain-X` → `pdomain/pdomain-X`. That means many of the
remaining hits are **doubly stale**: both the owner AND the repo name need
flipping (e.g. `ConcaveTrillion/pd-book-tools` → `pdomain/pdomain-book-tools`).
GH redirects keep things working, but the references are stale.

## Active set (12 repos — flip)

`book-tools`, `index-npm`, `index-pip`, `ocr-cli`, `ocr-labeler-spa`,
`ocr-ops`, `ocr-simple-gui`, `ocr-synth`, `ocr-trainer-spa`, `ocr-training`,
`prep-for-pgdp`, `ui`.

## Retired set (3 repos — DO NOT flip)

`pd-png-optimizer`, `pd-ocr-trainer`, `pd-ocr-labeler`. Names stay.

## Owner mapping

- `ConcaveTrillion/pd-<active>` → `pdomain/pdomain-<active>` (when in a URL)
- `ConcaveTrillion/pd-<retired>` → unchanged
- `ConcaveTrillion/ocr-container-meta` → unchanged (workspace meta stays in CT)

## Goal

Drop the workspace-wide active-name grep from ~290 → as close to 0 as is
safe. Acceptable leftovers are historical references in `docs/archive/`,
`scripts/rename/**` (the rename machinery itself), this plan, and Phase 5
plan files.

## Acceptance grep

```bash
cd /workspaces/ocr-container
rg -c --hidden -g '!.git' \
  -e 'pd-book-tools' -e 'pd-index-npm' -e 'pd-index-pip' \
  -e 'pd-ocr-cli' -e 'pd-ocr-labeler-spa' -e 'pd-ocr-ops' \
  -e 'pd-ocr-simple-gui' -e 'pd-ocr-synth' -e 'pd-ocr-trainer-spa' \
  -e 'pd-ocr-training' -e 'pd-prep-for-pgdp' -e 'pd-ui' \
  | awk -F: '{n+=$NF} END {print n+0}'
```

Phase 5 final: **290**. Phase 6 target: **≤ 80** (rename machinery +
archived plans only).

---

## Wave A — Devcontainer bootstrap (highest-impact, blocks cold start)

**Files:**
- `.devcontainer/setup.sh`
- `.devcontainer/Dockerfile`

These clone the repos at devcontainer start. Currently they reference
`https://github.com/ConcaveTrillion/pd-book-tools.git` etc. — both owner
AND name stale. GH redirects work today but break if redirects ever drop.

- [ ] **A.1** In `.devcontainer/setup.sh`, for each of the 12 active repos:
  - Change `pd-<active>` → `pdomain-<active>` (the local dir name).
  - Change the URL `https://github.com/ConcaveTrillion/pd-<active>.git` →
    `https://github.com/pdomain/pdomain-<active>.git`.
- [ ] **A.2** Same flip in `.devcontainer/Dockerfile` comment refs.
- [ ] **A.3** Verify the script's `clone_if_missing` works against the new
  URL — `bash -n .devcontainer/setup.sh` for syntax; spot-check one URL
  with `gh repo view pdomain/pdomain-book-tools`.
- [ ] **A.4** Commit: `rename(phase6): flip devcontainer bootstrap to pdomain/* URLs`.

---

## Wave B — Live workspace scripts

**Files (rough hit counts):**
- `scripts/ship-issue-pick.py` (3) — hardcoded `--repo` default.
- `scripts/groom-auto.py` (1) — hardcoded `REPO` constant.
- `scripts/decompose-spec-sync.py` (1) — example in docstring.
- `scripts/eval-spec-model.py` (1) — example in argparse help.
- `scripts/ocr_to_txt.py` (9) — docstring instructions to `pip install pd-book-tools`.
- `scripts/migrate-claude-ok-to-bot-label.sh` (5) — hardcoded repo list.
- `scripts/sync-labels-canon.json` (1) — repo list.
- `scripts/patch-brainstorming-skill.sh` (1) — path ref.
- `cost-dashboard/build-cost-dashboard.py` (3) — repo list.
- `plan-00-overview.json` (3) — needs inspection (workspace root JSON).

For each:
- Active repo refs (path or `ConcaveTrillion/pd-<active>` URL): flip both
  owner AND name.
- Retired repo refs: leave alone.

`scripts/ocr_to_txt.py` is special — it documents `pip install
pd-book-tools` for end users. The package on PyPI / pd-index is now
`pdomain-book-tools` (per Phase 4.5). Confirm package name on
`pdomain/pdomain-index-pip` before flipping the install instructions.

- [ ] **B.1** Sweep `scripts/*.{py,sh}`, `scripts/*.json`,
  `cost-dashboard/*.py`, and `plan-00-overview.json` (NOT `scripts/rename/`).
  Flip active names + owners.
- [ ] **B.2** Run any tests that cover these scripts:
  ```bash
  cd /workspaces/ocr-container
  uv run pytest tests/scripts/ -k "not rename" -q
  ```
  Expect some failures (test fixtures still use old names) — those are
  Wave C's problem; the script itself must pass syntax checks.
- [ ] **B.3** Commit: `rename(phase6): flip pd-* refs in workspace scripts to pdomain/*`.

---

## Wave C — Test fixtures + workspace-meta tests

**Files (~140 hits):**
- `tests/scripts/test_*.py` — most tests assert on repo names or mock GH
  responses with old names.
- `tests/fixtures/findings/*.json` — finding fixtures.
- `tests/fixtures/conventions/example-conventions.md` — fixture prose.
- `cost-dashboard/tests/fixtures/runs.jsonl` — historical run records.

**Decision per file:**
- If the test fixture is a **frozen historical record** (e.g. a captured
  GH API response from before the rename, or a runs.jsonl with old SHAs),
  **leave it alone** — rewriting history isn't the goal.
- If the test fixture is a **synthetic example** of what current code
  should produce, flip the names.
- If the test asserts current code behavior (e.g. "ship-issue-pick should
  output `pdomain-book-tools`"), flip the assertion.

Recommended approach:
- [ ] **C.1** Run the test suite first to see what's already failing:
  ```bash
  uv run pytest tests/scripts/ -q 2>&1 | tail -40
  ```
  Any test failing *because of the script changes in Wave B* is a Wave-C
  target — flip its fixtures/assertions until it passes again.
- [ ] **C.2** For each failing test, decide: flip names, or update the
  test to match the new behavior. Don't blanket-sed — judgment per file.
- [ ] **C.3** Test fixtures that are pure historical records: leave
  alone, document them in commit message.
- [ ] **C.4** Final acceptance: `uv run pytest tests/ -q` passes.
- [ ] **C.5** Commit: `rename(phase6): align test fixtures + assertions with pdomain/* rename`.

---

## Wave D — Skill markdown + workspace plans

**Files (~25 hits):**
- `.claude/skills/repo-setup/SKILL.md` (3)
- `.claude/skills/decompose-spec-auto/SKILL.md` (3)
- `.claude/skills/spec-from-issue/SKILL.md` (2)
- `.claude/skills/pr-wip-status/SKILL.md` (2)
- `.claude/skills/check-ci-failures/SKILL.md` (2)
- `.claude/skills/workspace-cleanup/SKILL.md` (1)
- `.claude/skills/pr-review/SKILL.md` (1)
- `.claude/skills/groom/SKILL.md` (1)
- `.claude/skills/extract-conventions/SKILL.md` (1)
- `.claude/skills/decompose-spec/SKILL.md` (1)
- `.claude/plans/would-switching-to-justfile-typed-spark.md` (8)
- `.claude/plans/optimized-finding-aurora.md` (2)

Pure prose flips. Skill markdown drives Claude behavior — examples and
descriptions should match current repo names.

- [ ] **D.1** Sweep `.claude/skills/**/*.md` and `.claude/plans/*.md` for
  the 12 active names. Flip.
- [ ] **D.2** Verify no skill SKILL.md has a syntactically broken
  description block (frontmatter must still parse).
- [ ] **D.3** Commit: `rename(phase6): flip pd-* refs in skill docs and workspace plans`.

---

## Wave E — Final acceptance + handoff

- [ ] **E.1** Run the acceptance grep. Remaining hits should be:
  - `scripts/rename/**` (rename machinery — historical names ARE the input)
  - `docs/archive/plans/**` (archived historical plans)
  - `docs/plans/2026-05-26-pdomain-rename-phase-*.md` (these plan files)
  - `docs/handoff-next-session.md` (historical notes)
  - This plan file
- [ ] **E.2** Append a "Phase 6 done" section to
  `docs/handoff-next-session.md` mirroring the Phase 5 section: list each
  wave, baseline → final grep, what was deferred (if anything).
- [ ] **E.3** Commit + push workspace meta `main`.

---

## Out of scope

- `pd-gh`, `pd-push` single-file utility scripts (separate naming decision).
- `/srv/bot-workspaces/pd-*/` bot workspace dir renames.
- PAT/secret swap (Finding #2).
- The 3 retired repos and their references.
- Annotated `v*` git tag renames.
- `scripts/rename/**` machinery (uses historical names as input — correct).

## Notes for the executor

- **Check the working tree first.** `git status --short` may show stale
  modifications from Phase 5 (e.g. `.claude/memory/*.md` were touched but
  not committed). Surface them to CT before piling on top.
- **Each wave is its own commit.** Don't bundle waves — they touch
  unrelated concerns and reviewers want them separable.
- **No PRs.** Per workspace `CLAUDE.md`: interactive sessions never open
  GitHub PRs. Commit locally; push when CT authorizes.
- **No subagents needed.** The work is mechanical sed + targeted file
  reads. Use `Explore` only if a file's contents surprise you.
- **Use `Read`, `Edit`, `Write` directly — no `cat`/`tail`/`sed -i` via
  `Bash` for files you can name (user memory: "Use Read not tail/cat").
  `sed -i` is OK for bulk path-pattern sweeps where there's no specific
  file to Read first.
