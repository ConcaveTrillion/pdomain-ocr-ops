---
status: complete
synced: 2026-05-17
milestone: 1
repo: ConcaveTrillion/ocr-container-meta
---

# Workspace chore — rename `pd-index` to `pdomain-index-pip`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename every reference to the existing self-hosted PEP 503 Python index from `pd-index` to `pdomain-index-pip` across the entire `/workspaces/ocr-container/` workspace, in lockstep with a manual rename of the underlying GitHub repository (`ConcaveTrillion/pd-index` → `ConcaveTrillion/pdomain-index-pip`). This pairs with the upcoming new repo `pdomain-index-npm` so the two release indexes share a symmetric naming scheme (`pdomain-index-pip` / `pdomain-index-npm`), per the cross-cut design (`docs/specs/2026-05-16-cross-cut-design.md` §3 "Existing repo rename" + §7 Phase 1 row 1.2).

**Architecture:** The PEP 503 index is hosted on GitHub Pages backed by the `pd-index` repo. Renaming the repo on GitHub changes the Pages URL slug from `https://concavetrillion.github.io/pd-index/simple/` to `https://concavetrillion.github.io/pdomain-index-pip/simple/`. Every `[[tool.uv.index]]` entry, every `repository_dispatch` API call (`/repos/ConcaveTrillion/pd-index/dispatches`), every comment, every workspace anchor (`.gitignore`, agent prompts, memory notes), and every doc reference must be updated. Tasks 1–8 each handle one `pd-*` repo and produce one local commit per repo. Tasks 9–12 sweep the workspace-level artifacts. Task 13 verifies via a final workspace-wide grep.

**Tech stack:** No code change in any pd-* runtime — this is a pure rename chore. Tools: `grep -rn`, `Edit`, `git add`/`git commit`. No test runs required (no behavior change); per-repo CI (`make ci`) does not need to be re-run for a comment/URL rename in `pyproject.toml`'s tool sections because no runtime code or dependency resolution changes — the URL still resolves once Task 0's GitHub rename has landed (GitHub automatically 301-redirects the old URL until the redirect is removed, but the redirect is fragile and should not be relied on).

**Working directory for all commands:** `/workspaces/ocr-container/` (each per-repo task `cd`s into that repo).

---

## Scope, blast radius, and stop-the-world requirement

This is a **workspace-wide chore that touches every `pd-*` repo plus several workspace-level files**. It conflicts with any concurrent in-flight plan that is editing `pyproject.toml`, `.github/workflows/release.yml`, `CLAUDE.md`, `README.md`, or agent prompts in any pd-* repo — every other plan must be paused, and the bots scheduler must be quiesced, before Task 0 fires.

Before starting:

1. Confirm no `wip/ship-issue-*` branches are mid-flight in any pd-* repo. Pause `coding-bot` scheduling:
   ```bash
   coding-bot schedule list
   coding-bot schedule disable <names>   # for any entry that would ship a pd-* repo
   ```
2. Confirm no pr-review session is in flight (no `bot:pr-review-*` labels active).
3. Confirm every pd-* repo has a clean working tree:
   ```bash
   for r in pdomain-book-tools pdomain-ocr-cli pd-ocr-labeler pdomain-ocr-labeler-spa pdomain-ocr-synth pd-ocr-trainer pd-png-optimizer pdomain-prep-for-pgdp; do
     printf '== %s ==\n' "$r"
     git -C "$r" status --short
   done
   ```
   Any non-empty output is a blocker; resolve before proceeding.

Run as a stop-the-world sweep: complete all 13 tasks in one session, push at the end, then re-enable scheduling.

---

## Task 0 — Preflight (manual, by CT) {#preflight-manual-by-ct}

**Why:** The GitHub repo rename has to happen first. Once the repo is renamed, GitHub Pages publishes at the new URL (`https://concavetrillion.github.io/pdomain-index-pip/simple/`) and the old slug returns 404 (or a temporary 301 redirect). Every subsequent task updates references to point at the new URL.

**What:** **CT performs this manually outside of agent automation:**

1. On GitHub, rename `ConcaveTrillion/pd-index` → `ConcaveTrillion/pdomain-index-pip`:
   - Settings → General → Repository name → `pdomain-index-pip` → Rename.
2. Confirm GitHub Pages is serving at the new URL:
   ```bash
   curl -sI https://concavetrillion.github.io/pdomain-index-pip/simple/ | head -3
   ```
   Expected: `HTTP/2 200`.
3. Update the local checkout's remote and directory name:
   ```bash
   cd /workspaces/ocr-container/pd-index
   git remote set-url origin git@github.com:ConcaveTrillion/pdomain-index-pip.git
   cd /workspaces/ocr-container
   mv pd-index pdomain-index-pip
   ```
4. Confirm the workspace now contains a `pdomain-index-pip/` directory and the old `pd-index/` is gone.

**Verification:** `ls /workspaces/ocr-container/ | grep '^pd-index'` returns exactly `pdomain-index-pip` (no `pd-index`).

**Acceptance:** GitHub repo renamed, Pages URL live at new slug, local checkout moved and re-pointed at the new remote. Only after this step is complete should the per-repo tasks below begin.

> The remaining tasks (1–13) edit *references* to the index — they do not touch the index repo itself except for one workspace-level rename of the `pd-index/` directory (already done in step 3 above). The `pdomain-index-pip/` repo's own internal files (its `regen.yml` workflow, README, etc.) are part of the sweep too and are covered under Task 11 (workspace-level files within the renamed directory).

---

## Task 1 — `pdomain-book-tools`: rename references {#pdomain-book-tools-rename-references}

**Why:** `pdomain-book-tools/.github/workflows/release.yml` pings `pd-index` via `repository_dispatch` after a release; comments and the URL slug must point at the new repo name.

**Files:** every file under `/workspaces/ocr-container/pdomain-book-tools/` that mentions `pd-index`.

- [ ] **Step 1 — find:**
  ```bash
  cd /workspaces/ocr-container/pdomain-book-tools
  grep -rn "pd-index" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules
  ```
  Note every hit. Common locations: `pyproject.toml` (`[[tool.uv.index]]` URL and `tool.uv.sources` reference), `.github/workflows/release.yml` (URL + comments + `/repos/ConcaveTrillion/pd-index/dispatches`), `CLAUDE.md`, `README.md`, `scripts/do-release.sh`, `Makefile`.

- [ ] **Step 2 — edit:** Replace every `pd-index` with `pdomain-index-pip` in the located files. Two URL forms to handle:
  - `https://concavetrillion.github.io/pd-index/...` → `https://concavetrillion.github.io/pdomain-index-pip/...`
  - `ConcaveTrillion/pd-index` (in `gh api -X POST /repos/...` calls and prose) → `ConcaveTrillion/pdomain-index-pip`
  - `name = "pd-index"` / `{ index = "pd-index" }` in `pyproject.toml` → `pdomain-index-pip`
  - Prose references in comments → `pdomain-index-pip`

  Skip any reference where the literal `pdomain-index-npm` already exists adjacent — that's the new sibling repo and must stay as-is.

- [ ] **Step 3 — verify (second grep):**
  ```bash
  grep -rn "pd-index[^-]" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules
  grep -rn "pd-index$" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules
  ```
  Expected: zero matches. Any survivor is either a missed rename (fix it) or a reference to `pdomain-index-npm` that the second pattern (`pd-index$`) won't match anyway.

- [ ] **Step 4 — commit:**
  ```bash
  cd /workspaces/ocr-container/pdomain-book-tools
  git add -p   # review every hunk
  git commit -m "chore: rename pd-index index URL to pdomain-index-pip

Renames every reference to the self-hosted PEP 503 index from
pd-index to pdomain-index-pip, in lockstep with the GitHub repo rename
(ConcaveTrillion/pd-index -> ConcaveTrillion/pdomain-index-pip). Pairs
with the upcoming pdomain-index-npm sibling repo per cross-cut design
docs/specs/2026-05-16-cross-cut-design.md s3."
  ```

**Acceptance:** Per-repo grep is clean; one local commit on `main`.

---

## Task 2 — `pdomain-ocr-cli`: rename references {#pdomain-ocr-cli-rename-references}

Same procedure as Task 1, executed in `/workspaces/ocr-container/pdomain-ocr-cli/`.

- [ ] **Step 1 — find:** `cd /workspaces/ocr-container/pdomain-ocr-cli && grep -rn "pd-index" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules`
- [ ] **Step 2 — edit:** Replace per the rules in Task 1 Step 2. Known hits include `pyproject.toml` (`[[tool.uv.index]]` name + URL + `tool.uv.sources` `pdomain-book-tools = { index = "pd-index" }`), `.github/workflows/release.yml`, `README.md`.
- [ ] **Step 3 — verify:** Re-grep; expected zero matches for `pd-index` that aren't `pdomain-index-pip` or `pdomain-index-npm`.
- [ ] **Step 4 — commit:** Use the canonical message from Task 1.

**Acceptance:** Clean per-repo grep, one commit on `main`.

---

## Task 3 — `pd-ocr-labeler`: rename references {#pd-ocr-labeler-rename-references}

Same procedure as Task 1, executed in `/workspaces/ocr-container/pd-ocr-labeler/`.

- [ ] **Step 1 — find:** `cd /workspaces/ocr-container/pd-ocr-labeler && grep -rn "pd-index" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules`
- [ ] **Step 2 — edit:** Replace per Task 1's rules. Check `pyproject.toml`, `.github/workflows/`, `CLAUDE.md`, `README.md`.
- [ ] **Step 3 — verify:** Re-grep clean.
- [ ] **Step 4 — commit:** Canonical message from Task 1.

**Acceptance:** Clean per-repo grep, one commit on `main`.

---

## Task 4 — `pdomain-ocr-labeler-spa`: rename references {#pdomain-ocr-labeler-spa-rename-references}

Same procedure as Task 1, executed in `/workspaces/ocr-container/pdomain-ocr-labeler-spa/`.

- [ ] **Step 1 — find:** `cd /workspaces/ocr-container/pdomain-ocr-labeler-spa && grep -rn "pd-index" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules --exclude-dir=frontend/node_modules`
- [ ] **Step 2 — edit:** Replace per Task 1's rules. Check `pyproject.toml`, `.github/workflows/`, `CLAUDE.md`, `README.md`, `docs/` (multiple plan / spec files reference the index).
- [ ] **Step 3 — verify:** Re-grep clean.
- [ ] **Step 4 — commit:** Canonical message from Task 1.

**Acceptance:** Clean per-repo grep, one commit on `main`.

---

## Task 5 — `pdomain-ocr-synth`: rename references {#pdomain-ocr-synth-rename-references}

Same procedure as Task 1, executed in `/workspaces/ocr-container/pdomain-ocr-synth/`.

- [ ] **Step 1 — find:** `cd /workspaces/ocr-container/pdomain-ocr-synth && grep -rn "pd-index" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules`
- [ ] **Step 2 — edit:** Replace per Task 1's rules.
- [ ] **Step 3 — verify:** Re-grep clean.
- [ ] **Step 4 — commit:** Canonical message from Task 1.

**Acceptance:** Clean per-repo grep, one commit on `main`.

---

## Task 6 — `pd-ocr-trainer`: rename references {#pd-ocr-trainer-rename-references}

Same procedure as Task 1, executed in `/workspaces/ocr-container/pd-ocr-trainer/`.

- [ ] **Step 1 — find:** `cd /workspaces/ocr-container/pd-ocr-trainer && grep -rn "pd-index" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules`
- [ ] **Step 2 — edit:** Replace per Task 1's rules.
- [ ] **Step 3 — verify:** Re-grep clean.
- [ ] **Step 4 — commit:** Canonical message from Task 1.

**Acceptance:** Clean per-repo grep, one commit on `main`.

---

## Task 7 — `pd-png-optimizer`: rename references {#pd-png-optimizer-rename-references}

Same procedure as Task 1, executed in `/workspaces/ocr-container/pd-png-optimizer/`.

- [ ] **Step 1 — find:** `cd /workspaces/ocr-container/pd-png-optimizer && grep -rn "pd-index" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules --exclude-dir=target`
- [ ] **Step 2 — edit:** Replace per Task 1's rules. (Rust repo — may also have references in `Cargo.toml` comments or `scripts/`.)
- [ ] **Step 3 — verify:** Re-grep clean.
- [ ] **Step 4 — commit:** Canonical message from Task 1.

**Acceptance:** Clean per-repo grep, one commit on `main`.

---

## Task 8 — `pdomain-prep-for-pgdp`: rename references {#pdomain-prep-for-pgdp-rename-references}

Same procedure as Task 1, executed in `/workspaces/ocr-container/pdomain-prep-for-pgdp/`.

- [ ] **Step 1 — find:** `cd /workspaces/ocr-container/pdomain-prep-for-pgdp && grep -rn "pd-index" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules --exclude-dir=frontend/node_modules`
- [ ] **Step 2 — edit:** Replace per Task 1's rules.
- [ ] **Step 3 — verify:** Re-grep clean.
- [ ] **Step 4 — commit:** Canonical message from Task 1.

**Acceptance:** Clean per-repo grep, one commit on `main`.

---

## Task 9 — Workspace `CLAUDE.md` + `.gitignore` {#workspace-claudemd-gitignore}

**Why:** The workspace-root `CLAUDE.md` documents repo layout and routing; the workspace `.gitignore` has an anchor entry (currently `/pd-index/`) that must move to `/pdomain-index-pip/`.

**Files:**
- Modify: `/workspaces/ocr-container/CLAUDE.md`
- Modify: `/workspaces/ocr-container/.gitignore`

- [ ] **Step 1 — find:**
  ```bash
  grep -n "pd-index" /workspaces/ocr-container/CLAUDE.md /workspaces/ocr-container/.gitignore
  ```

- [ ] **Step 2 — edit:**
  - In `.gitignore`, replace the `/pd-index/` anchor with `/pdomain-index-pip/`. If `/pdomain-index-npm/` is not yet present, this plan does **not** add it (that's the new-repo plan's job).
  - In `CLAUDE.md`, replace any prose `pd-index` reference with `pdomain-index-pip`. Skip if no hits.

- [ ] **Step 3 — verify (second grep):**
  ```bash
  grep -n "pd-index[^-]\|pd-index$" /workspaces/ocr-container/CLAUDE.md /workspaces/ocr-container/.gitignore
  ```
  Expected: zero matches.

- [ ] **Step 4 — commit (workspace-root repo):**
  ```bash
  cd /workspaces/ocr-container
  git add CLAUDE.md .gitignore
  git commit -m "chore: rename pd-index references to pdomain-index-pip (workspace)

Workspace-level rename matching the GitHub repo rename
(ConcaveTrillion/pd-index -> ConcaveTrillion/pdomain-index-pip).
Updates .gitignore anchor and CLAUDE.md prose."
  ```

**Acceptance:** Clean grep on both files; one workspace-root commit.

---

## Task 10 — Sweep `.claude/agents/` agent prompts {#sweep-claudeagents-agent-prompts}

**Why:** Per-repo agent prompts may instruct the agent to publish to or reference the index by name. Stale `pd-index` references would mislead the agent.

**Files:** every `.md` under `/workspaces/ocr-container/.claude/agents/`.

- [ ] **Step 1 — find:**
  ```bash
  grep -rn "pd-index" /workspaces/ocr-container/.claude/agents/
  ```

- [ ] **Step 2 — edit:** Replace every `pd-index` with `pdomain-index-pip` (skip `pdomain-index-npm`). If the grep returns zero matches, mark the task complete with no edit.

- [ ] **Step 3 — verify:**
  ```bash
  grep -rn "pd-index[^-]\|pd-index$" /workspaces/ocr-container/.claude/agents/
  ```
  Expected: zero matches.

- [ ] **Step 4 — commit (workspace-root repo):** If files were modified:
  ```bash
  cd /workspaces/ocr-container
  git add .claude/agents/
  git commit -m "chore: rename pd-index references to pdomain-index-pip (agent prompts)"
  ```
  Skip the commit if no files changed.

**Acceptance:** Clean grep over `.claude/agents/`.

---

## Task 11 — Sweep `.claude/agent-memory/` per-agent notes {#sweep-claudeagent-memory-per-agent-notes}

**Why:** Agent memory files (under `.claude/agent-memory/<agent>/`) record what each agent has learned — including release-strategy notes that name the index repo. Stale memory misleads the agent on subsequent runs.

**Files:** every `.md` under `/workspaces/ocr-container/.claude/agent-memory/`. The initial grep run during planning showed hits in (non-exhaustive): every pd-* agent's `MEMORY.md`, several `release_strategy_self_hosted_index.md` notes, `pdomain-ocr-cli/install_sh_pd_book_tools_pin.md`, `pdomain-ocr-cli/dev_local_install_recipe.md`, `pdomain-book-tools/release_flow.md`.

- [ ] **Step 1 — find:**
  ```bash
  grep -rn "pd-index" /workspaces/ocr-container/.claude/agent-memory/ /workspaces/ocr-container/.claude/memory/
  ```

- [ ] **Step 2 — edit:** Replace every `pd-index` with `pdomain-index-pip` (skip `pdomain-index-npm`). Be conservative — these are historical notes, so rewriting text aggressively is fine but do not alter the meaning. For dated note titles that include the literal word `pd-index`, the rename is still correct (the note's subject is now `pdomain-index-pip`).

- [ ] **Step 3 — verify:**
  ```bash
  grep -rn "pd-index[^-]\|pd-index$" /workspaces/ocr-container/.claude/agent-memory/ /workspaces/ocr-container/.claude/memory/
  ```
  Expected: zero matches.

- [ ] **Step 4 — commit (workspace-root repo):**
  ```bash
  cd /workspaces/ocr-container
  git add .claude/agent-memory/ .claude/memory/
  git commit -m "chore: rename pd-index references to pdomain-index-pip (agent memory)"
  ```

**Acceptance:** Clean grep over both memory roots.

---

## Task 12 — Sweep workspace `docs/` and the renamed `pdomain-index-pip/` repo's own internals {#sweep-workspace-docs-and-the-renamed-pdomain-index-pip-}

**Why:** Workspace-level design docs and handoff notes mention `pd-index`. The renamed `pdomain-index-pip/` directory (formerly `pd-index/`) also has its own `README.md`, `.github/workflows/regen.yml`, and any prose referencing the old name that must be updated.

**Files:**
- Every `.md` under `/workspaces/ocr-container/docs/`.
- Every file under `/workspaces/ocr-container/pdomain-index-pip/` (newly renamed) that mentions `pd-index`.

- [ ] **Step 1 — find (workspace docs):**
  ```bash
  grep -rn "pd-index" /workspaces/ocr-container/docs/
  ```
  Known hits include `docs/specs/2026-05-16-cross-cut-design.md`, `docs/superpowers/handoff-2026-05-16-cross-cut.md`, `docs/specs/2026-05-14-coding-bot-design.md`. Plan files in `docs/plans/` may have hits too — this plan itself contains intentional `pd-index` occurrences (the rename-from name) so visually inspect that the rename does not corrupt this plan's prose; the rename rule is "every `pd-index` not in a `pdomain-index-pip` or `pdomain-index-npm` substring **outside this plan file**". Easiest path: hand-edit this plan's references *not at all*, then run the replacement on every other doc.

- [ ] **Step 2 — find (renamed index repo):**
  ```bash
  cd /workspaces/ocr-container/pdomain-index-pip
  grep -rn "pd-index" . --exclude-dir=.git
  ```
  Known: `README.md`, `.github/workflows/regen.yml`.

- [ ] **Step 3 — edit:** Replace `pd-index` with `pdomain-index-pip` in every located file (workspace docs + the renamed index repo's own files). For the renamed repo's `regen.yml`, ensure any `${{ github.repository }}` references are not hard-coded to the old name and that workflow names / display strings reflect the new repo name.

- [ ] **Step 4 — verify:**
  ```bash
  grep -rn "pd-index[^-]\|pd-index$" /workspaces/ocr-container/docs/
  grep -rn "pd-index[^-]\|pd-index$" /workspaces/ocr-container/pdomain-index-pip/ --exclude-dir=.git
  ```
  Expected: zero matches in `docs/`; zero matches in `pdomain-index-pip/`. (This plan file itself is exempt — it intentionally documents the from-name and the to-name; if grep flags it, confirm visually that the remaining hits are exactly the documented-from-name references in this plan, not stale references elsewhere.)

- [ ] **Step 5 — commit (workspace-root repo, for docs):**
  ```bash
  cd /workspaces/ocr-container
  git add docs/
  git commit -m "chore: rename pd-index references to pdomain-index-pip (workspace docs)"
  ```

- [ ] **Step 6 — commit (renamed pdomain-index-pip repo):**
  ```bash
  cd /workspaces/ocr-container/pdomain-index-pip
  git add -A
  git commit -m "chore: rename internal references to pdomain-index-pip

Self-references to the old pd-index repo name updated after the
GitHub repo rename. Pairs with the upcoming pdomain-index-npm sibling
per cross-cut design docs/specs/2026-05-16-cross-cut-design.md s3."
  ```

**Acceptance:** Both greps clean; two commits (one in workspace root, one in pdomain-index-pip).

---

## Task 13 — Workspace-wide verification grep {#workspace-wide-verification-grep}

**Why:** Catch anything missed by the per-task sweeps — a final stop-the-world grep proves the rename is complete.

- [ ] **Step 1 — run the verifier:**
  ```bash
  cd /workspaces/ocr-container
  grep -rn "pd-index[^-]\|pd-index$" . \
    --exclude-dir=.git \
    --exclude-dir=.venv \
    --exclude-dir=node_modules \
    --exclude-dir=target \
    --exclude-dir=frontend/node_modules
  ```
  Expected: zero matches **except** the historical references inside this plan file itself (`docs/plans/2026-05-16-pd-index-rename-to-pip.md`), which document the from-name.

- [ ] **Step 2 — manually triage every reported hit:**
  - If the hit is inside this plan file → ignore (documented from-name).
  - If the hit is `pdomain-index-pip` or `pdomain-index-npm` and was matched by the regex erroneously → re-check the regex (`[^-]` and `$` should be sufficient; if not, narrow further).
  - If the hit is a genuine stale `pd-index` reference → open the file, rename it, and add it to the appropriate per-task commit by amending or filing a small follow-up commit (`chore: catch missed pd-index reference in <path>`).

- [ ] **Step 3 — push:** Once the workspace is clean and all 8 per-repo commits + 4 workspace-root/index commits are recorded, push each repo (workspace root + 8 pd-* repos + pdomain-index-pip = 10 pushes):
  ```bash
  for r in . pdomain-book-tools pdomain-ocr-cli pd-ocr-labeler pdomain-ocr-labeler-spa pdomain-ocr-synth pd-ocr-trainer pd-png-optimizer pdomain-prep-for-pgdp pdomain-index-pip; do
    printf '== %s ==\n' "$r"
    git -C "$r" push origin main
  done
  ```

- [ ] **Step 4 — re-enable scheduling:**
  ```bash
  coding-bot schedule list   # confirm previously-disabled entries are still disabled
  coding-bot schedule enable <name>   # for each entry paused in the preflight
  ```

**Acceptance:** Workspace-wide grep returns no stale `pd-index` references outside this plan file; all 10 repos pushed to `origin/main`; coding-bot scheduling restored.

---

## Self-review checklist (engineer; do this before declaring done)

- [ ] Task 0 was confirmed complete by CT before any per-repo edits began (GitHub repo renamed, Pages live at `pdomain-index-pip/simple/`).
- [ ] Each of Tasks 1–8 produced exactly **one commit per pd-* repo** with the canonical message form `chore: rename pd-index index URL to pdomain-index-pip`.
- [ ] Task 9 produced one workspace-root commit covering `CLAUDE.md` + `.gitignore`.
- [ ] Tasks 10–11 produced zero or one workspace-root commit each (skip-if-no-changes is acceptable).
- [ ] Task 12 produced two commits (workspace `docs/` + `pdomain-index-pip/` internals).
- [ ] Task 13's verifier grep is clean modulo this plan file.
- [ ] Every pyproject.toml `[[tool.uv.index]]` URL hits the new slug `https://concavetrillion.github.io/pdomain-index-pip/simple/`.
- [ ] Every `.github/workflows/release.yml` `gh api -X POST /repos/ConcaveTrillion/...` line targets `pdomain-index-pip`.
- [ ] No squash-merges (per workspace merge strategy memory note `project_merge_strategy.md`).
- [ ] `coding-bot schedule list` shows previously-disabled entries re-enabled.

## Follow-up plans (not in scope here)

1. **New repo `pdomain-index-npm`.** Verdaccio-style npm index hosted on GitHub Pages. Adds a new workspace `.gitignore` anchor (`/pdomain-index-npm/`) and a new entry in workspace `CLAUDE.md`'s repo layout. Tracked separately per cross-cut design §7 Phase 1 row 1.4.
2. **Optional: drop the GitHub redirect.** GitHub auto-redirects renamed repos for a grace period. Once every pd-* repo is on the new URL and at least one release has cycled through, CT can disable the redirect explicitly. Not required for this plan.
