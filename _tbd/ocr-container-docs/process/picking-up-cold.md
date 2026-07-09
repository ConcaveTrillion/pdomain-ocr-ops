# Picking up a session cold

A reusable "I have no current handoff doc, just orient me and pick something useful" prompt for the pd-* workspace. Two parallel versions — Claude and Codex — that mirror the handoff format. Use whenever there is no current `docs/handoff-next-session.md` driving the session.

---

## CLAUDE version

> Paste below into Claude Code when starting a session with no specific brief.

```
I'm picking up the pd-* workspace cold. Orient yourself, find the highest-
leverage unblocked work, and SHIP IT — no "propose before acting". Run
parallel workstreams: dispatch multiple per-repo subagents concurrently
(one Agent block, multiple tool calls), each working in a pre-created
sub-repo worktree that you, the orchestrator, hand them. Do NOT use
`isolation: "worktree"` — the harness worktrees the workspace root, not
the sub-repo. Merge each branch back to its repo's main locally
(merge-commit, never squash) ONLY after CI is green AND a code review
agent has signed off. No `git push`. No `gh pr create`. Local merge only.

DISCOVERY (do this first; don't propose work until done):

1. **Recent handoff.** Read `docs/handoff-next-session.md` if it exists;
   otherwise check the newest file under `docs/handoffs/`. If its "state
   at handoff" block is still current (check dates + verified items), the
   work it lists is the starting point. If stale, note that and re-derive
   from scratch.

2. **Working tree across repos.** For every directory in
   `/workspaces/ocr-container/pd-*`:
   • `git -C <repo> status --short` — surface stray uncommitted work.
   • `git -C <repo> log @{u}..HEAD --oneline` — unpushed local commits.
   • `git -C <repo> worktree list` — non-bot worktrees may hold WIP.
   Surface anything unexpected.

3. **CI status on `main`.** For every pd-* repo:
   `gh run list --repo ConcaveTrillion/<repo> --branch main --limit 1
    --json status,conclusion,name`
   Note which are red and pull the failing job log
   (`gh run view <id> --log-failed`). Categorise: my-fix-now / known-flaky
   / pre-existing-deep / out-of-scope (legacy or other-rotation repos).

4. **Released wheels in pdomain-index-pip.** `gh release list --repo
   ConcaveTrillion/<repo>` for each Python library (pdomain-book-tools,
   pdomain-ops, pdomain-ocr-training, etc.). If a downstream is pinned to an
   editable sibling but the upstream has a published wheel, that's a
   trivial dep-switch win.

5. **Active plans & milestones.**
   • `ls docs/plans/` in each repo — most pd-* repos use
     `docs/plans/<YYYY-MM-DD>-*.md` for active work plans.
   • `gh issue list --repo ConcaveTrillion/ocr-container-meta --state open
      --label kind:tracking --json number,title,milestone` for cross-cut
     workspace tasks.
   • For per-repo work: `gh issue list --repo ConcaveTrillion/<repo>
      --state open --label status:ready --json number,title,milestone`
     (or `status:in-progress`).
   • Per-repo `gh issue list --milestone "<name>" --state open` for
     remaining items in any milestone the handoff or memory references.

6. **Workspace memory.** Read `.claude/memory/MEMORY.md` and any
   relevant `.claude/agent-memory/<repo>/MEMORY.md` files to learn
   recent decisions, blockers, and process gotchas. Treat the memory
   as background context, not authoritative — verify file paths /
   feature names still exist before acting on them.

7. **Stray workspace state.** Look for `/tmp/pd-*` directories
   (worktree leaks). If found, salvage into the correct
   `<repo>/.claude/worktrees/<name>` before any other work.

RANK + DISPATCH (no asking, just go):

After discovery, rank candidates by priority (highest to lowest):
• A red repo whose fix is small and well-specified (test bug, dep
  switch, CI workflow tweak, coverage gap).
• An upstream release that, once published, unblocks N downstream
  items.
• A SEQUENTIAL chain whose head is unblocked (e.g. a milestone issue
  with explicit "blocked by" edges now satisfied).
• A parallel batch of independent unblocked items.
• A research / design issue requiring no code yet (only if nothing
  buildable is ready).

If nothing is unblocked and well-specified, say so plainly and stop —
don't invent work.

Otherwise, pick the top N INDEPENDENT items — items that touch
disjoint repos or disjoint code so they can ship in parallel without
merge conflicts. Size N by the work: 2–4 for chunky items (new
features, multi-file refactors), up to 6–8 for small ones (dep
switches, single-file fixes, doc/CI tweaks). Bias toward more
parallelism when items are clearly small and well-specified. Then run subagent-driven
development:

1. For each picked item, pre-create its worktree from the workspace
   root:
     git -C <repo> worktree add -b <branch> .claude/worktrees/<name> main
   `.claude/` is gitignored so worktree files don't appear in
   `git status`.

2. Dispatch all per-repo subagents in a SINGLE Agent block (multiple
   tool calls in one message) so they run concurrently. For each
   agent:
   • subagent_type = the per-repo agent (`pdomain-book-tools`, etc.)
   • model = "sonnet"
   • NO `isolation` flag — pass the pre-created worktree path in the
     prompt and tell the agent: "work in the worktree
     `<repo>/.claude/worktrees/<name>` you were started in; do not
     create another; do not `gh pr create`; do not `git push`. Commit
     locally and stop."

3. While they run, monitor with TaskList / TaskGet. When each agent
   returns, the orchestrator (not the agent) takes over integration.

4. INTEGRATION GATE — per worktree, in order:
   a. Verify CI conditions locally in that worktree (`make ci AI=1`
      or repo-specific equivalent). pd-* sibling deps must resolve
      from the pdomain-index-pip wheel, NOT an editable `../sibling`.
   b. Dispatch a code-review agent (`subagent_type: "code-review"`
      or repo's reviewer skill, model: "sonnet") against the branch
      diff. Fix anything it flags as a blocker by sending the work
      back to its implementer agent, then re-verify.
   c. Only when (a) green AND (b) sign-off: merge to that repo's
      main locally with merge-commit (no squash):
        git -C <repo> checkout main && git -C <repo> merge --no-ff <branch>
      Then remove worktree + delete branch.
   d. DO NOT push. DO NOT open a PR. Local merge only — CT pushes
      when they're ready.

5. After all parallel workstreams integrate (or report blocked), end
   the iteration with the REPORT block below.

PROCESS RULES (always apply):

• Worktrees MUST live in <repo>/.claude/worktrees/. Pre-create from
  the workspace root, dispatch the per-repo agent pointed at that
  path with NO isolation flag. Tell each agent: "work in the worktree
  you were started in; do not create another."
• Subagents NEVER push and NEVER open PRs. Local commits only. The
  orchestrator merges. CT pushes.
• Verify under CI conditions: pd-* sibling deps resolve from the
  pdomain-index-pip wheel, NOT an editable ../sibling. A local `make ci`
  using an editable overlay (or a Python-version-specific basedpyright
  baseline) is NOT a valid green.
• basedpyright's pre-commit hook auto-prunes .basedpyright/baseline.json
  on every commit, so parallel branches conflict. Per-branch rule:
  `git checkout -- .basedpyright/baseline.json` before committing on a
  chunk branch. Regenerate ONCE at integration with
  `uv run basedpyright <pkg> --writebaseline`.
• Pre-existing test bugs (hardcoded paths, flaky timing tests, e2e
  fixture gaps) surface as deeper failures get past earlier fixes.
  CI moving from "fail at lint" to "fail at tests" is progress —
  read the new failure before assuming regression.
• All Python through `uv run …`; never bare python/python3.
• pnpm9 for every TS/React frontend; never npm. `pnpm install --frozen-lockfile`.
• Git identity per repo: ConcaveTrillion <concavetrillion@gmail.com>.

ROUTING:

A subagent exists per repo (`.claude/agents/<repo>.md`). Three names look
similar — keep them distinct:
• `pd-ocr-labeler` (legacy NiceGUI) vs `pdomain-ocr-labeler-spa` (FastAPI+React
  replacement) vs `pd-ocr-labeler-driver` (Playwright operator).
• `pd-ocr-trainer` (legacy NiceGUI) vs `pdomain-ocr-training` (torch library)
  vs `pdomain-ocr-trainer-spa` (FastAPI+React replacement).
Each has a `<repo>-docs` Haiku sibling for cheap read-only doc lookups —
use those from sibling-repo agents that need cross-repo context.

REPORT:

For each repo you touch: item picked + why, what was built, test/CI
status, worktree path + branch, anything identified but not built. End
with a short "next obvious step if I keep going" so a future session can
chain.
```

---

## CODEX version

> Paste below into Codex CLI when starting a session with no specific brief.

```
I'm picking up the pd-* workspace cold at /workspaces/ocr-container.
Orient yourself, find the highest-leverage unblocked work, and propose a
plan BEFORE acting. Each pd-* repo is a separate git checkout. Work one
repo at a time on feature branches; merge-commit (no squash) to main;
commit locally and ask before pushing.

WORKSPACE LAYOUT:
• pdomain-book-tools/      — foundation Python library (every pd-* depends on it)
• pdomain-ocr-cli/         — end-user CLI
• pd-ocr-labeler/     — legacy NiceGUI labeler
• pdomain-ocr-labeler-spa/ — FastAPI+React labeler (replacement)
• pdomain-ops/         — Python ops library (every SPA backend imports)
• pdomain-ocr-simple-gui/  — minimal FastAPI+React OCR app
• pdomain-ocr-synth/       — synthetic training-data generator (spec-only)
• pd-ocr-trainer/     — legacy NiceGUI training suite (retiring)
• pdomain-ocr-trainer-spa/ — FastAPI+React trainer (replacement)
• pdomain-ocr-training/    — torch/DocTR training library
• pd-png-optimizer/   — Rust PNG optimizer
• pdomain-prep-for-pgdp/   — FastAPI+React PGDP-submission app
• pdomain-ui/              — shared TS/React/Vite library
• se-llm-skills/      — source-first skills framework (generates plugin artifacts)
• pdomain-index-pip/       — PEP 503 simple index (workspace-root edits, no agent)
• pdomain-index-npm/       — npm registry (workspace-root edits, no agent)

EACH repo: read its CLAUDE.md first, then use its Makefile.
• Verify with `make ci AI=1` (sub-steps: `make test`, `make lint`, `make format`).
• All Python through `uv run …`; never bare python/python3.
• pnpm9 for every TS/React frontend; never npm.

DISCOVERY (do this first; don't propose work until done):

1. **Recent handoff.** `cat docs/handoff-next-session.md` if it exists;
   otherwise check the newest file under `docs/handoffs/`. If its "state
   at handoff" block is still current (check dates + verified items),
   it's the starting point. If stale, note and re-derive.

2. **Working tree across repos.** For every pd-* directory:
     git -C <repo> status --short
     git -C <repo> log @{u}..HEAD --oneline
     git -C <repo> worktree list
   Surface stray uncommitted work, unpushed commits, non-bot worktrees.

3. **CI status on `main`.** For every pd-* repo:
     gh run list --repo ConcaveTrillion/<repo> --branch main --limit 1 \
       --json status,conclusion,name
   For each red one, pull the failing job log:
     gh run view <run-id> --repo ConcaveTrillion/<repo> --log-failed
   Categorise: my-fix-now / known-flaky / pre-existing-deep / out-of-scope.

4. **Released wheels.** `gh release list --repo ConcaveTrillion/<repo>` for
   each Python library. If a downstream is pinned to `../sibling`
   (editable) but an upstream wheel exists, that's a trivial dep-switch
   win — switch to `{ index = "pdomain-index-pip" }` with a version pin
   following the existing pattern used elsewhere in the workspace.

5. **Active plans & milestones.**
   • `ls <repo>/docs/plans/*.md` — most pd-* repos use dated work plans.
   • `gh issue list --repo ConcaveTrillion/ocr-container-meta --state open \
      --label kind:tracking --json number,title,milestone` — cross-cut tasks.
   • `gh issue list --repo ConcaveTrillion/<repo> --state open \
      --label status:ready --json number,title,milestone` — per-repo work.
   • If the handoff or a plan references a milestone:
       gh issue list --repo ConcaveTrillion/<repo> --milestone "<name>" --state open

6. **Workspace memory.** `.claude/memory/MEMORY.md` (if it exists) plus any
   relevant `.claude/agent-memory/<repo>/MEMORY.md` files document recent
   decisions, blockers, and gotchas. Treat as background context — verify
   file paths / feature names still exist before acting on them.

7. **Stray state.** `ls /tmp/pd-* 2>/dev/null` — worktree leaks; salvage
   any into the correct `<repo>/.claude/worktrees/<name>` before anything
   else.

PROPOSE BEFORE ACTING:

After discovery, list candidate items in priority order with a one-line
justification each, then ask which to pursue. Priority signals
(highest to lowest):
• A red repo whose fix is small and well-specified (test bug, dep switch,
  CI workflow tweak).
• An upstream release that, once published, unblocks N downstream items.
• A SEQUENTIAL chain whose head is unblocked (e.g. a wave in a burn-down
  plan, a milestone issue with explicit "blocked by" edges now satisfied).
• A parallel batch of independent unblocked items.
• A research / design issue requiring no code yet (only if nothing
  buildable is ready).

If nothing is unblocked and well-specified, say so plainly — don't invent
work.

PROCESS RULES (always apply):

• Work in a feature branch per task. Create a worktree at
  `<repo>/.claude/worktrees/<short-name>` (.claude/ is gitignored, so
  worktree files don't show up in git status):
     git -C <repo> worktree add -b fix/<name> .claude/worktrees/<name> main
  Work in that path. After merge, remove worktree + delete branch.
• Local `make ci` is NOT proof CI will pass. Two known traps:
   (a) editable `../sibling` deps — must be `{ index = "pdomain-index-pip" }`
       with a version pin. Cross-repo deps in pyproject.toml resolve
       through the GitHub-Pages-hosted index, not the local checkouts.
   (b) basedpyright baseline column drift across the CI Python matrix.
       If an untyped sibling needs grandfathering for
       `reportMissingTypeStubs`, use a line-level
       `# pyright: ignore[...]` on the import line (column-stable),
       never a baseline entry.
• basedpyright's pre-commit hook auto-prunes .basedpyright/baseline.json.
  On a chunk branch, `git checkout -- .basedpyright/baseline.json` before
  committing. Regenerate the baseline ONCE at integration with
  `uv run basedpyright <pkg> --writebaseline`.
• Pre-existing test bugs surface as deeper failures get past earlier
  ones. CI moving from "fail at lint" to "fail at tests" is progress;
  read the new failure before assuming regression.
• Use `git commit --no-verify` only after independently running
  `uv run ruff format` + `uv run ruff check` + targeted pytest
  (--no-verify skips the pre-commit hook stack).
• Git identity per repo:
     git -C <repo> config user.name ConcaveTrillion
     git -C <repo> config user.email concavetrillion@gmail.com

NOTES ON SIMILAR NAMES (don't conflate):

• pd-ocr-labeler (legacy NiceGUI) vs pdomain-ocr-labeler-spa (FastAPI+React
  replacement). Both touch labeler UI — context will tell you which.
• pd-ocr-trainer (legacy NiceGUI, retiring) vs pdomain-ocr-training (torch
  library) vs pdomain-ocr-trainer-spa (FastAPI+React replacement). Only one
  consumer of pdomain-ocr-training: pdomain-ocr-trainer-spa.

REPORT:

For each repo you touch: item picked + why, what was built, test/CI
status, branch name, anything identified but not built. End with a short
"next obvious step if I keep going" so a future session can chain.
```

---

## When to use this vs. handoff docs

- **Specific current handoff in `docs/handoff-next-session.md`** → use that. It points at known-good items with pre-approved pushes already negotiated.
- **Historical handoff under `docs/handoffs/` that's still relevant** → use it as context, then re-verify dates and current repo state.
- **No handoff, or handoff is stale** → use this cold-start prompt. It rebuilds the picture from scratch and proposes work before acting.

When a session finishes, update `docs/handoff-next-session.md` so the next session can skip the discovery phase.
