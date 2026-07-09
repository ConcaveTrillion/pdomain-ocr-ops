---
status: complete
synced: 2026-05-17
milestone: 4
repo: ConcaveTrillion/ocr-container-meta
---

# GH Workflow — Plan B: Skill Prompt Updates

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update all skill prompts and agent definitions to implement the new triage flow, cross-repo convention, decompose-spec --sync idiom, ship-issue two-step context read, and the /groom skill skeleton.

**Architecture:** Each skill and agent file is a self-contained markdown document; edits are surgical text replacements in those files, with no code to compile or test. The patch-brainstorming-skill.sh script is extended with a new idempotent Python patch block that inserts the cross-repo convention block after every plugin update.

**Tech Stack:** Markdown editing, bash (for patch script)

---

## Decisions

| Decision | Choice | Reason |
|---|---|---|
| Triage outcomes for feature-requests | Exactly 2: `kind:spec` or `kind:decision` | Direct-ship shortcut removed per spec §4; size decision moves into spec-from-issue |
| Triage outcomes for bugs/chores | Unchanged — file direct, no triage | Spec §4 non-goals: "No changes to bug or chore flows" |
| Cross-repo recommendation format | Exactly as in spec §10: `Target:`, `Reason:`, `gh issue create` block, `→ Run this?` footer | Consistent format across all skills and agents |
| decompose-spec default mode | `--sync` is new default; `--one-shot` flag preserves old behaviour | Spec §5 replaces one-shot with idempotent sync; backwards compat needed during transition |
| Plan task slug format | `{#slug}` anchor on every `## Task N — Title {#slug}` heading | Required by sync algorithm — stable ID survives title renames |
| ship-issue context read | Two-step: GH issue body for routing/acceptance, then `Plan: path#slug` link for full execution context | Spec §9: "the bot reads the plan section for full context, not just the GH issue title" |
| Brainstorming patch | Detect plugin cache path dynamically (sort by version, take latest), apply idempotently via sentinel string | Plugin version changes; must not double-patch |
| Per-repo agent cross-repo block | Insert after `## Inter-repo awareness` section, before `## Quirks / gotchas` | Natural location: agents already say "don't edit siblings"; the new block says how to surface the gap instead |
| `writing-plans` skill | Not modified in Plan B — it is a plugin-bundled skill, not a local `.claude/skills/` file | Only the patch script can touch plugin skills; Plan B adds the cross-repo convention there via patch-brainstorming-skill.sh extension |
| groom skill | Skeleton only — header, purpose, TODO stub | Plan C will complete the full implementation; Plan B only creates the file |

---

## Task 1 — Update triage skill: remove direct-ship outcome {#triage-two-outcomes}

model: sonnet  effort: S  area: skills

**Files:**
- Modify: `/workspaces/ocr-container/.claude/skills/triage/SKILL.md`

### Steps

- [ ] **1a. Update the frontmatter `description` field** to remove the `tracking-vs-spec` framing and reflect the two-outcome model.

  **Before (line 3):**
  ```
  description: Triage a kind:feature-request issue. Reads the feature-request, decides approve/reject and (if approve) tracking-vs-spec, forks the right child issue, applies triage:* labels, and posts a reasoning comment. Use when CT invokes `/triage <N>`.
  ```

  **After:**
  ```
  description: Triage a kind:feature-request issue. Reads the feature-request, decides approve/reject and (if approve) spec-vs-decision, forks the right child issue, applies triage:* labels, and posts a reasoning comment. Use when CT invokes `/triage <N>`. Bugs and chores are NOT triaged — they file direct.
  ```

- [ ] **1b. Update the opening paragraph** to reflect two outcomes (not three).

  **Before (line 8):**
  ```
  Triage one `kind:feature-request` issue. End state: the parent gets `triage:approved` or `triage:rejected` (and `triage:needs-spec` when applicable), one child issue is forked (tracking or spec), and a reasoning comment is posted on the parent.
  ```

  **After:**
  ```
  Triage one `kind:feature-request` issue. End state: the parent gets `triage:approved` or `triage:rejected`, one child issue is forked (`kind:spec` or `kind:decision`), and a reasoning comment is posted on the parent.

  **Scope:** `kind:feature-request` only. `kind:bug` and `kind:chore` issues are filed direct — do not triage them.
  ```

- [ ] **1c. Replace the "Decision tree" block in step 3** (the three-outcome heuristic) with the two-outcome tree from spec §4.

  **Before (the entire step 3 content):**
  ```
  3. **Read the body and decide classification.**

     Decision tree (matches the spec's sizing heuristic, subject to iteration):
     - **Reject** if duplicate of an existing issue, or out of scope, or scoped to a different repo. Look for dups: `gh issue list --repo "$REPO" --search "<keywords>" --json number,title`.
     - **Approve, ship-direct** if the work is one focused change: estimated effort ≤ S, ≤ 2 files, no new public API. Output kind: `tracking`.
     - **Approve, needs-spec** otherwise. Output kind: `spec`.
  ```

  **After:**
  ```
  3. **Read the body and decide classification.**

     Decision tree:
     - **Reject** if duplicate of an existing issue, out of scope, or clearly owned by a different repo. Look for dups: `gh issue list --repo "$REPO" --search "<keywords>" --json number,title`. For a different-repo feature, emit a cross-repo recommendation block (see spec §10 format) and reject the current issue.
     - **Approve, kind:decision** if the feature-request is architectural: it affects multiple repos simultaneously, or it implies a fundamental choice between approaches that must be resolved before any implementation can begin. Output kind: `decision`.
     - **Approve, kind:spec** for all other approved feature-requests, regardless of size. The size/effort decision happens inside `/spec-from-issue`. Output kind: `spec`.

     There is no "ship-direct" outcome for feature-requests. Every approved feature goes through at least a spec.
  ```

- [ ] **1d. Update step 4 (body composition)** — remove tracking-child instructions, keep spec/decision language.

  **Before (step 4 first paragraph):**
  ```
  4. **Compose the child-issue title and body.**

     Tracking children should have a one-sentence body summarizing what they do, plus an `Acceptance:` checklist that ship-issue can pick up. Spec children should have a body that names the feature and the open design questions; do NOT write the spec itself here — that's `/spec-from-issue`'s job.
  ```

  **After:**
  ```
  4. **Compose the child-issue title and body.**

     - **Spec child:** body names the feature and the open design questions. Do NOT write the spec itself here — that's `/spec-from-issue`'s job.
     - **Decision child:** body names what must be decided and why. Include 2-4 bullet points framing the key tradeoffs. Format: `Decision: (pending)` as first line so `/groom` can detect it.
  ```

- [ ] **1e. Update step 5 (labels)** — remove tracking-child row, add decision-child row.

  **Before (step 5 content):**
  ```
  5. **Determine target labels for the child.**

     - Tracking child: `kind:<bug|chore|feature>`, `effort:<S|M|L>`, `model:<haiku|sonnet|opus>`, `model-effort:<low|medium|high|xhigh|max>`, `status:backlog`. Do NOT add `bot:ship-issue-ready` — CT arms it via `scripts/arm-issue.py <repo> <N>` after the parent spec PR is merged (see `arm_issue_gate.md` in workspace-scripts memory).
     - Spec child: `kind:spec`, `effort:<S|M|L>`, `status:backlog`. Spec children don't need model labels (the work is `/spec-from-issue`, not `/ship-issue`).
  ```

  **After:**
  ```
  5. **Determine target labels for the child.**

     - Spec child: `kind:spec`, `effort:<S|M|L>`, `status:backlog`. No model labels — the work is `/spec-from-issue`, not `/ship-issue`.
     - Decision child: `kind:decision`, `status:backlog`. No effort or model labels — CT writes the decision doc, not a bot.
  ```

- [ ] **1f. Update the `triage-fork.py` call in step 6** — remove `--output tracking` as a valid option, update `--kind` choices.

  **Before (the triage-fork.py call block):**
  ```
     ```bash
     /workspaces/ocr-container/scripts/triage-fork.py \
       --repo "$REPO" --parent <N> \
       --kind <bug|chore|feature|spec> --output <tracking|spec> \
       --title "<title>" \
       --body-file /tmp/triage-<N>-body.md \
       --label kind:<x> --label effort:<x> [--label model:<x> --label model-effort:<x>] \
       --label status:backlog \
       --apply-skill-labels
     ```

     `--apply-skill-labels` does three things in one call:
     - Applies `triage:approved` + `triage:needs-spec` (or `triage:needs-tracking`) to the **parent**.
     - Applies `kind:<kind>` + `triage:proposed-by-agent` + `status:backlog` to the **child**.
     - Posts a linking/decision comment on the **parent** (mirrors today's manual format).
  ```

  **After:**
  ```
     ```bash
     /workspaces/ocr-container/scripts/triage-fork.py \
       --repo "$REPO" --parent <N> \
       --kind <spec|decision> --output <spec|decision> \
       --title "<title>" \
       --body-file /tmp/triage-<N>-body.md \
       --label kind:<spec|decision> --label effort:<x> \
       --label status:backlog \
       --apply-skill-labels
     ```

     `--apply-skill-labels` does three things in one call:
     - Applies `triage:approved` + `triage:needs-spec` (for spec child) or `triage:needs-decision` (for decision child) to the **parent**.
     - Applies `kind:<kind>` + `triage:proposed-by-agent` + `status:backlog` to the **child**.
     - Posts a linking/decision comment on the **parent**.
  ```

- [ ] **1g. Update Constraints section** — remove the "Approve, ship-direct" constraint, keep the rest.

  **Before:**
  ```
  - **Approving a sprawling idea as `tracking` because it "feels small"** — when in doubt, use `spec` and let `/decompose-spec` size it later.
  ```

  **After:**
  ```
  - **Approving a feature-request as a direct tracking issue** — every approved feature goes through a spec. No exceptions. Size is determined inside `/spec-from-issue`.
  ```

- [ ] **1h. Update Anti-patterns section** — replace the ship-direct anti-pattern with the no-direct-ship rule, and fix the `triage:needs-spec` anti-pattern.

  **Before (last two anti-patterns):**
  ```
  - Approving a sprawling idea as `tracking` because it "feels small" — when in doubt, use `spec` and let `/decompose-spec` size it later.
  - Forgetting `triage:needs-spec` on spec-output children — the chain-state report keys on it.
  - Filing the child against a different repo — v1 is per-repo locality only.
  ```

  **After:**
  ```
  - Approving a feature-request as a direct tracking issue — there is no direct-ship shortcut for feature-requests in this workflow. Every feature needs a spec.
  - Forgetting `triage:needs-spec` on spec children or `triage:needs-decision` on decision children — the chain-state report keys on these labels.
  - Filing the child against a different repo — v1 is per-repo locality only. If a feature belongs in a sibling repo, emit a cross-repo recommendation and reject the current issue.
  ```

- [ ] **1i. Commit the triage skill change.**

  ```bash
  cd /workspaces/ocr-container
  git add .claude/skills/triage/SKILL.md
  git commit -m "skill(triage): two-outcome model — remove direct-ship shortcut for feature-requests"
  ```

---

## Task 2 — Update spec-from-issue: add cross-repo recommendation convention {#spec-from-issue-cross-repo}

model: sonnet  effort: S  area: skills

**Files:**
- Modify: `/workspaces/ocr-container/.claude/skills/spec-from-issue/SKILL.md`

### Steps

- [ ] **2a. Add a new step 2b after the brainstorm step**, documenting when and how to emit cross-repo recommendations while writing the spec.

  Insert the following block immediately after step 2 ("Brainstorm the design") and before step 3 ("Pick the spec file path"). The inserted text becomes the new step 2b; renumber subsequent steps accordingly (step 3 becomes step 3, step 4 becomes step 4, etc. — renumbering is not strictly required in markdown prose, but the new content must be clearly inserted between steps 2 and 3).

  **Content to insert (between step 2 and step 3):**
  ```
  2b. **Emit cross-repo recommendations (if any).**

      While brainstorming or writing the spec, you will sometimes identify a gap
      that belongs in a sibling repo rather than the one you are speccing. Do NOT
      file or edit issues in that sibling repo. Instead, emit a formatted
      recommendation block for CT to review:

      ```
      Cross-repo recommendation
        Target: <repo>  (e.g. pdomain-book-tools)
        Reason: <one sentence — what's missing and why it belongs there>
        gh issue create -R ConcaveTrillion/<repo> \
          -l kind:feature-request -l status:backlog \
          --title "<title>" \
          --body "Tracks: (none yet)\nContext: Discovered while writing spec for #<N>\n\n<body>"
        → Run this? CT can edit before executing.
      ```

      Emit one block per gap, immediately when identified. Do NOT wait until the spec
      is finished. After emitting, continue writing the spec — CT decides whether to
      run the command and when.

      **Applies when:** the spec reveals a missing upstream capability in `pdomain-book-tools`,
      a shared contract that must change in a sibling repo, or a data-flow dependency
      that must be built elsewhere first.
  ```

- [ ] **2b. Add a cross-repo Anti-pattern** at the end of the Anti-patterns section.

  **Append to the Anti-patterns section:**
  ```
  - Filing or editing issues in a sibling repo directly — emit the formatted cross-repo recommendation block and let CT decide. Per-repo locality is a hard constraint.
  ```

- [ ] **2c. Commit the spec-from-issue skill change.**

  ```bash
  cd /workspaces/ocr-container
  git add .claude/skills/spec-from-issue/SKILL.md
  git commit -m "skill(spec-from-issue): add cross-repo recommendation convention (spec §10)"
  ```

---

## Task 3 — Update decompose-spec: --sync as default, --one-shot for backwards compat, {#slug} requirement {#decompose-spec-sync}

model: sonnet  effort: M  area: skills

**Files:**
- Modify: `/workspaces/ocr-container/.claude/skills/decompose-spec/SKILL.md`

### Steps

- [ ] **3a. Replace frontmatter description** to reflect the new default invocation.

  **Before (line 3):**
  ```
  description: Read a spec markdown file, propose child issues, present them to CT for review, then file the confirmed children + create a per-spec milestone. Use when CT invokes `/decompose-spec <path> [--output=tracking|feature-requests|mixed] [--backfill]`.
  ```

  **After:**
  ```
  description: Idempotent plan→GH sync — reads a plan doc, diffs plan tasks against existing GH issues, and creates/updates/reopens/closes to keep them in sync. Primary mode: `/decompose-spec --sync <plan-path>` (can be re-run whenever the plan changes). Legacy one-shot mode: `/decompose-spec --one-shot <path> [--output=tracking|feature-requests|mixed] [--backfill]`. Use when CT invokes either form.
  ```

- [ ] **3b. Rewrite the opening paragraph** to describe the new primary mode first, with the legacy mode second.

  **Before:**
  ```
  # decompose-spec

  Decompose one spec file into N child issues, all attached to a per-spec GitHub milestone. End state: each new child has `Tracks: #<spec-issue>` + `Spec: <path>` body lines, the milestone titled `spec: <slug> (#<spec-issue>)` exists in the target repo, and every child is assigned to it.
  ```

  **After:**
  ```
  # decompose-spec

  **Primary mode (`--sync`):** Idempotent plan→GH sync. Reads a plan doc, diffs its tasks against existing GH milestone issues, and creates/updates/reopens/closes to keep them current. Safe to re-run whenever the plan changes. This is the expected everyday invocation.

  **Legacy mode (`--one-shot`):** One-shot decomposition from a spec file into N child issues. Preserved for transition; prefer `--sync` for all new work.

  End state (both modes): child issues have `Tracks: #<spec-issue>` + `Plan: <path>#<slug>` body lines, the milestone `spec: <slug> (#<spec-issue>)` exists in the target repo, and every child is assigned to it.
  ```

- [ ] **3c. Replace the Required arguments section** to document both invocation forms and the new `{#slug}` anchor requirement.

  **Replace the entire "## Required arguments" section with:**
  ```
  ## Required arguments

  ### --sync mode (primary)

  ```
  /decompose-spec --sync <plan-path>
    (or)
  /decompose-spec --sync <spec-issue-N>
  ```

  - `<plan-path>` — a `docs/plans/YYYY-MM-DD-slug.md` file.
  - `<spec-issue-N>` — GH issue number; the skill resolves the `Plan:` link from the issue body.
  - `--dry-run` — preview changes without writing.

  **Required plan task format for `--sync` to work:**

  Every task in the plan doc MUST use this heading format:

  ```markdown
  ## Task N — <title>  {#task-slug}
  model: <haiku|sonnet|opus>  effort: <S|M|L>  area: <tag>

  Context: ...
  Approach: ...
  Blocked by: #other-task-slug   (use slug, not GH number — sync resolves it)
  Verification: <command>
  Acceptance:
  - [ ] ...
  ```

  The `{#slug}` anchor is the **stable identity key** — the sync algorithm uses it to
  match plan tasks to GH issues. A task that lacks a `{#slug}` anchor cannot be synced
  and will be skipped with a warning. The slug must be unique within the plan doc,
  lowercase, and use only `a-z`, `0-9`, and `-`.

  ### --one-shot mode (legacy, use for transition only)

  ```
  /decompose-spec --one-shot <path> [--output=tracking|feature-requests|mixed] [--backfill] [--diff]
  ```

  - `<path>` — the spec markdown file.
  - `--output=<tracking|feature-requests|mixed>` — child kind axis. Default: `tracking`.
  - `--backfill` — required if the spec has no `> **Spec-Issue**:` header.
  - `--diff` — file only children that don't already exist (rerun after partial failure).
  ```

- [ ] **3d. Insert a new "## --sync workflow" section** before the existing "## Workflow" section (rename existing "## Workflow" to "## --one-shot workflow" to distinguish them).

  **Insert the following new section before "## Workflow":**
  ```
  ## --sync workflow

  ### Algorithm

  1. **Read plan doc** — extract ordered task list by `## Task N — <title> {#slug}` headings.
     Warn and skip any task missing a `{#slug}` anchor.
  2. **Resolve spec issue** — read plan frontmatter for `milestone: N`; if absent, search
     for an open `kind:spec` issue whose body contains `Plan: <this-plan-path>`.
  3. **Query GH milestone** — `gh issue list --milestone "spec: <slug> (#M)"` to get all
     open + closed issues assigned to it.
  4. **Diff by task slug:**
     - Task in plan, no GH issue → **CREATE** issue with summary card body (see body contract).
     - Task in plan, GH issue exists, body differs → **UPDATE** issue body.
     - Task in plan, GH issue was closed → **REOPEN** with comment `restored from plan update YYYY-MM-DD`.
     - GH issue exists, task removed from plan → **CLOSE** with comment `removed from plan YYYY-MM-DD`.
  5. **Resolve blockers** — for each `Blocked by: #task-slug` in plan, look up the
     corresponding GH issue number and write `Blocked by: #N` in the child issue body.
  6. **Ensure spec GH issue exists** — if none, create it with `Spec:` and `Plan:` body lines.
  7. **Update plan frontmatter:**
     ```yaml
     synced: YYYY-MM-DD
     milestone: N
     ```

  ### Task issue body (generated by --sync)

  ```
  Approach: <one sentence from plan task>
  Blocked by: #N, #M   (resolved GH numbers)
  Plan: docs/plans/YYYY-MM-DD-slug.md#task-slug
  Verification: <command>
  Tracks: #<spec-issue>
  Acceptance:
  - [ ] ...
  - [ ] ...
  ```

  The full Context + detailed Approach lives in the plan doc section.
  ship-issue reads the `Plan:` link to fetch that execution context.

  ### CT confirmation

  Present a diff table before applying:

  ```
  Action  Title                      Notes
  CREATE  Task 2 — Add bbox extract  new task in plan
  UPDATE  Task 1 — Schema def        body differs (Approach line changed)
  CLOSE   Task 4 — Old export path   removed from plan
  ```

  Wait for CT confirmation. Then apply with:

  ```bash
  /workspaces/ocr-container/scripts/decompose-spec-sync.py \
    --plan <plan-path> --repo "$REPO"
  ```

  ### Cross-repo tasks

  If a plan task's `area:` tag or body references a different repo, emit a
  cross-repo recommendation block for CT (do not file in the sibling repo directly):

  ```
  Cross-repo recommendation
    Target: <repo>
    Reason: <one sentence>
    gh issue create -R ConcaveTrillion/<repo> \
      -l kind:feature-request -l status:backlog \
      --title "<title>" \
      --body "Tracks: (none yet)\nContext: Decomposed from plan <path>\n\n<body>"
    → Run this? CT can edit before executing.
  ```
  ```

- [ ] **3e. Rename the existing "## Workflow" section** to "## --one-shot workflow" to disambiguate.

  **Before:**
  ```
  ## Workflow

  ### Stage 1 — propose
  ```

  **After:**
  ```
  ## --one-shot workflow

  ### Stage 1 — propose
  ```

- [ ] **3f. Update Constraints section** — add the `{#slug}` requirement and the sync-is-default note.

  **Append to the Constraints section (after the existing bullets):**
  ```
  - **`{#slug}` anchor required for `--sync`.** Any task heading that lacks `{#slug}` is skipped with a warning; the skip is reported in the diff table. Remind CT to add anchors to plan headings before syncing.
  - **`--sync` is the preferred mode for all new work.** Use `--one-shot` only when migrating a legacy spec that was decomposed before this feature shipped.
  ```

- [ ] **3g. Update Anti-patterns section** — add sync-specific anti-patterns.

  **Append to the Anti-patterns section:**
  ```
  - Running `--one-shot` against a plan that already has synced children — use `--sync` instead to diff rather than duplicate.
  - Editing GH issue bodies that were generated by `--sync` directly — the next sync run will detect the body change as drift and may overwrite it. If the plan changed, update the plan first, then re-sync.
  - Omitting `{#slug}` anchors in new plan tasks — a task without a slug cannot be tracked across renames and will be orphaned on the next sync.
  ```

- [ ] **3h. Commit the decompose-spec skill change.**

  ```bash
  cd /workspaces/ocr-container
  git add .claude/skills/decompose-spec/SKILL.md
  git commit -m "skill(decompose-spec): --sync as primary mode, --one-shot for legacy, {#slug} anchor requirement"
  ```

---

## Task 4 — Update ship-issue: two-step context read {#ship-issue-two-step-context}

model: sonnet  effort: S  area: skills

**Files:**
- Modify: `/workspaces/ocr-container/.claude/skills/ship-issue/SKILL.md`

### Steps

- [ ] **4a. Update step 1** (currently "If SPEC_PATH is non-empty: Read it") to describe the two-step context read.

  **Before (step 1):**
  ```
  1. If `SPEC_PATH` is non-empty: Read it (use the `Read` tool, not bash `cat`).
  ```

  **After:**
  ```
  1. **Two-step context read.**

     **Step 1 — GH issue body (routing and acceptance).**

     Read `ISSUE_JSON` to get routing metadata (labels, blockers, milestone) and acceptance criteria.
     The body follows the task card contract:

     ```
     Approach: <one sentence>
     Blocked by: #N, #M
     Plan: docs/plans/YYYY-MM-DD-slug.md#task-slug
     Verification: <command>
     Tracks: #<spec-issue>
     Acceptance:
     - [ ] ...
     ```

     Extract the `Plan:` line. If it is present, proceed to Step 2.

     **Step 2 — Plan doc section (full execution context).**

     If the issue body contains a `Plan: <path>#<slug>` line, read the referenced plan file
     and locate the section whose heading anchor matches `{#<slug>}`. That section contains
     the full Context, detailed Approach, and Verification that the GH card summarizes.
     Use the plan section as the authoritative execution context for the TDD slice.

     ```bash
     # Resolve the plan path (workspace-relative)
     PLAN_PATH=$(cat "$ISSUE_JSON" | python3 -c "
     import sys, re, json
     body = json.load(sys.stdin)['body']
     m = re.search(r'^Plan: (.+?)#(.+)$', body, re.MULTILINE)
     if m: print('/workspaces/ocr-container/' + m.group(1))
     ")
     PLAN_SLUG=$(cat "$ISSUE_JSON" | python3 -c "
     import sys, re, json
     body = json.load(sys.stdin)['body']
     m = re.search(r'^Plan: .+?#(.+)$', body, re.MULTILINE)
     if m: print(m.group(1))
     ")
     ```

     Then use the `Read` tool on `$PLAN_PATH`, search for the heading `{#$PLAN_SLUG}`, and
     read that task's full section (Context through Acceptance).

     **If no `Plan:` line is present:** the issue predates the plan-doc convention, or it is
     a `bot:fix-wip` issue. Use the issue body alone. Do NOT fail or bounce — proceed with
     whatever context is available.

     **If `SPEC_PATH` is also non-empty:** Read it as well. SPEC_PATH is a legacy field from
     before the plan-doc convention; both sources are additive context.
  ```

- [ ] **4b. Add a note to the Constraints section** about the Plan: link and what the bot does NOT require.

  **Append to the Constraints section (after the existing bullets):**
  ```
  - **GH issue body need not contain full context.** The task card is intentionally lean (Approach: one sentence, Acceptance bullets). Full execution detail lives in the plan doc section. The bot is expected to read both — never bounce because "the issue body doesn't have enough detail" without first checking the `Plan:` link.
  - **Do not call `gh` to fetch the plan doc.** The plan doc is a local file in the repo tree; use the `Read` tool with the resolved path. The `Plan:` path is always workspace-relative (`docs/plans/...`).
  ```

- [ ] **4c. Commit the ship-issue skill change.**

  ```bash
  cd /workspaces/ocr-container
  git add .claude/skills/ship-issue/SKILL.md
  git commit -m "skill(ship-issue): two-step context read — GH card for routing, Plan: link for full execution context"
  ```

---

## Task 5 — Add cross-repo recommendation block to all 8 pd-* agent prompts {#agent-cross-repo-blocks}

model: sonnet  effort: M  area: agents

**Files (all 8 to modify):**
- `/workspaces/ocr-container/.claude/agents/pdomain-book-tools.md`
- `/workspaces/ocr-container/.claude/agents/pdomain-ocr-cli.md`
- `/workspaces/ocr-container/.claude/agents/pd-ocr-labeler.md`
- `/workspaces/ocr-container/.claude/agents/pdomain-ocr-labeler-spa.md`
- `/workspaces/ocr-container/.claude/agents/pdomain-ocr-synth.md`
- `/workspaces/ocr-container/.claude/agents/pd-ocr-trainer.md`
- `/workspaces/ocr-container/.claude/agents/pd-png-optimizer.md`
- `/workspaces/ocr-container/.claude/agents/pdomain-prep-for-pgdp.md`

### Cross-repo block to insert

The following block is inserted at the **end of the `## Inter-repo awareness` section** in each agent file, immediately before the blank line that separates it from `## Quirks / gotchas` (or `## Out of scope` if Quirks is absent). Insert verbatim — do not paraphrase.

```markdown
- **Cross-repo gaps: emit a recommendation, do not file autonomously.** If mid-task
  you discover a missing capability in a sibling repo, do NOT create or edit issues in
  that repo directly. Instead, emit this block and continue your primary task:

  ```
  Cross-repo recommendation
    Target: <repo>  (e.g. pdomain-book-tools)
    Reason: <one sentence — what's missing and why it belongs there>
    gh issue create -R ConcaveTrillion/<repo> \
      -l kind:feature-request -l status:backlog \
      --title "<title>" \
      --body "Tracks: (none yet)\nContext: Discovered while working on <this-repo>#<issue-N>\n\n<body>"
    → Run this? CT can edit before executing.
  ```

  CT reviews and runs (or edits) the command. The skill does not wait — continue your
  primary task immediately after emitting the block.
```

### Steps

- [ ] **5a. Edit pdomain-book-tools.md** — insert cross-repo block at end of `## Inter-repo awareness`.

  The current section ends with:
  ```
  - You may **read** sibling pd-* repos under `/workspaces/ocr-container/`
    to understand how an API is used, but **do not edit** them — surface
    the cross-repo work to the caller or hand it to that repo's agent.
  ```

  Append the cross-repo block immediately after that bullet (before the blank line leading into `## Quirks / gotchas`).

- [ ] **5b. Edit pdomain-ocr-cli.md** — locate `## Inter-repo awareness`, append cross-repo block at end.

- [ ] **5c. Edit pd-ocr-labeler.md** — locate `## Inter-repo awareness`, append cross-repo block at end.

- [ ] **5d. Edit pdomain-ocr-labeler-spa.md** — locate `## Inter-repo awareness`, append cross-repo block at end.

  Note: this agent has a long `## Inter-repo awareness` section with multiple sub-bullets. Append after the last bullet in that section (the `pdomain-book-tools` bullet that says "Don't reach into it; route shared OCR/layout concerns to that agent").

- [ ] **5e. Edit pdomain-ocr-synth.md** — locate `## Inter-repo awareness`, append cross-repo block at end.

- [ ] **5f. Edit pd-ocr-trainer.md** — locate `## Inter-repo awareness`, append cross-repo block at end.

- [ ] **5g. Edit pd-png-optimizer.md** — locate `## Inter-repo awareness`, append cross-repo block at end.

- [ ] **5h. Edit pdomain-prep-for-pgdp.md** — locate `## Inter-repo awareness`, append cross-repo block at end.

  Note: this agent's section ends with "You may **read** sibling pd-* repos but **do not edit** them." Append after that line.

- [ ] **5i. Commit all agent changes together.**

  ```bash
  cd /workspaces/ocr-container
  git add .claude/agents/pdomain-book-tools.md \
           .claude/agents/pdomain-ocr-cli.md \
           .claude/agents/pd-ocr-labeler.md \
           .claude/agents/pdomain-ocr-labeler-spa.md \
           .claude/agents/pdomain-ocr-synth.md \
           .claude/agents/pd-ocr-trainer.md \
           .claude/agents/pd-png-optimizer.md \
           .claude/agents/pdomain-prep-for-pgdp.md
  git commit -m "agents(all pd-*): add cross-repo recommendation convention block (spec §10)"
  ```

---

## Task 6 — Extend patch-brainstorming-skill.sh with cross-repo convention patch {#patch-brainstorming-cross-repo}

model: sonnet  effort: S  area: scripts

**Files:**
- Modify: `/workspaces/ocr-container/scripts/patch-brainstorming-skill.sh`

### Steps

- [ ] **6a. Understand the existing patch structure.** The script currently:
  1. Locates the latest plugin cache version of the brainstorming SKILL.md dynamically.
  2. Checks for a sentinel string (`sub-agent (breadth: medium)`) to bail if already patched.
  3. Runs an inline Python script that does two `str.replace` calls.

  The new patch must:
  - Use a DIFFERENT sentinel string (the existing one guards the explore-first patch; a second sentinel guards the cross-repo patch).
  - Be idempotent independently — re-running the script must not double-patch either block.
  - Insert the cross-repo convention block into the brainstorming skill's checklist, specifically into the "When to emit" or "Checklist" section if one exists; otherwise append to the end of the skill file.

- [ ] **6b. Add the cross-repo patch block.** Extend the script after the existing `python3` heredoc with a second sentinel check and a second Python patch:

  **Replace the closing lines of the script (after `PYEOF`):**

  Current ending:
  ```bash
  open(path, "w").write(text)
  print("Done.")
  PYEOF
  ```

  New ending (modify the existing PYEOF to include the cross-repo patch in the same Python script, and change the sentinel logic):

  The simplest approach: change the existing sentinel check at the top of the script to only guard the explore-first patch, then add a SEPARATE sentinel check below the first `python3` block for the cross-repo patch. Specifically, extend the script after the first `PYEOF` with:

  ```bash
  # --- Cross-repo recommendation patch (idempotent) ---
  if grep -q "Cross-repo recommendation" "$SKILL"; then
    echo "Cross-repo patch already applied — skipping."
  else
    python3 - "$SKILL" <<'PYEOF2'
  import sys, textwrap
  path = sys.argv[1]
  text = open(path).read()

  CROSS_REPO_BLOCK = textwrap.dedent("""
  ## Cross-repo recommendations

  When brainstorming identifies a gap in a sibling repo (a missing upstream capability,
  a shared contract that must change elsewhere, or a data-flow dependency that must be
  built in a different project), do NOT file or edit issues in that repo. Instead, emit
  this block for CT to review, then continue the brainstorming session:

  ```
  Cross-repo recommendation
    Target: <repo>  (e.g. pdomain-book-tools)
    Reason: <one sentence — what's missing and why it belongs there>
    gh issue create -R ConcaveTrillion/<repo> \\
      -l kind:feature-request -l status:backlog \\
      --title "<title>" \\
      --body "Tracks: (none yet)\\nContext: <where this was discovered>\\n\\n<body>"
    → Run this? CT can edit before executing.
  ```

  Emit one block per gap, immediately when identified. CT decides whether to run it and when.
  """).strip()

  # Append before the last heading or at the end of the file
  if "## Anti-patterns" in text:
      text = text.replace(
          "## Anti-patterns",
          CROSS_REPO_BLOCK + "\n\n## Anti-patterns",
          1,
      )
  else:
      text = text.rstrip() + "\n\n" + CROSS_REPO_BLOCK + "\n"

  open(path, "w").write(text)
  print("Cross-repo patch done.")
  PYEOF2
  fi
  ```

- [ ] **6c. Verify the script is syntactically valid.**

  ```bash
  bash -n /workspaces/ocr-container/scripts/patch-brainstorming-skill.sh
  echo "Syntax OK: $?"
  ```

- [ ] **6d. Commit the patch script change.**

  ```bash
  cd /workspaces/ocr-container
  git add scripts/patch-brainstorming-skill.sh
  git commit -m "scripts(patch-brainstorming-skill): add cross-repo recommendation convention patch"
  ```

---

## Task 7 — Create groom skill skeleton {#groom-skill-skeleton}

model: sonnet  effort: S  area: skills

**Files:**
- Create: `/workspaces/ocr-container/.claude/skills/groom/SKILL.md`

### Steps

- [ ] **7a. Create the directory and write the skeleton file.**

  ```bash
  mkdir -p /workspaces/ocr-container/.claude/skills/groom
  ```

  Write `/workspaces/ocr-container/.claude/skills/groom/SKILL.md` with the following content:

  ```markdown
  ---
  name: groom
  description: CT-interactive grooming of the superpowers artifact backlog. Works through the queued grooming report one item at a time (decisions, specs, plans, tasks, research). Use when CT invokes `/groom [decisions|specs|plans|tasks|research|all]`. TODO: full implementation in Plan C.
  ---

  # groom

  > **Status:** Skeleton — full implementation is in Plan C
  > (`docs/plans/2026-05-17-gh-workflow-plan-c-groom.md`).
  > Do not invoke this skill until Plan C ships.

  ## Purpose

  `/groom` walks through the queued "Grooming report" GH issue one item at a time,
  presenting each flagged item to CT with a suggested action. CT decides: keep /
  update / archive / delete. The interaction pattern mirrors `/triage`.

  ### Invocation forms

  ```
  /groom decisions   — work through stale/orphan decision items
  /groom specs       — work through orphan spec items
  /groom plans       — work through limbo/stale plan items
  /groom tasks       — work through stalled task items
  /groom research    — work through orphan research files
  /groom all         — work through all queued items in order
  ```

  ## Grooming item types (from spec §7)

  Each item type has a signal, a proposed action, and a CT decision set:

  | Signal | Type | Proposed action |
  |---|---|---|
  | Decision issue open, no decision doc written, >14 days | stale | Nudge CT |
  | Spec issue open, no plan doc linked, >30 days | orphan | Write plan or close |
  | Plan `synced:` >30 days, milestone <100% stalled | limbo | Keep / update / archive |
  | Plan no `synced:` date (never decomposed) | orphan | Decompose or delete |
  | Task `status:in-progress` >7 days, no recent PR activity | stalled | Requeue or close |
  | Task `status:backlog` >90 days | limbo | Keep / reprioritize / close |
  | Task `Plan:` link points to removed section | drift | Re-sync |
  | Research file >180 days, not referenced anywhere | orphan | Delete or archive |
  | Decision doc — all spawned specs fully shipped | complete | Archive doc |
  | Decision doc — no spawned specs, >30 days | no-op decision | CT confirms intent |

  ## TODO — Plan C will implement

  - [ ] Read the "Grooming report" GH issue (filed by `groom-auto` nightly job)
  - [ ] For each queued item: present signal, proposed action, CT decision choices
  - [ ] Apply CT decision: keep (no-op), update (edit issue/file), archive (move file + close issue), delete (delete file + close issue)
  - [ ] Mark item resolved in the Grooming report
  - [ ] After all items: summarize actions taken
  - [ ] `--dry-run` mode: show what would be done without acting
  ```

- [ ] **7b. Commit the groom skill skeleton.**

  ```bash
  cd /workspaces/ocr-container
  git add .claude/skills/groom/SKILL.md
  git commit -m "skill(groom): add skeleton — full implementation deferred to Plan C"
  ```

---

## Verification

After all tasks are committed:

- [ ] Run `ls /workspaces/ocr-container/.claude/skills/` — confirm `groom/` directory exists.
- [ ] Run `head -5 /workspaces/ocr-container/.claude/skills/triage/SKILL.md` — confirm description mentions "spec-vs-decision".
- [ ] Run `grep -c "Cross-repo recommendation" /workspaces/ocr-container/.claude/skills/spec-from-issue/SKILL.md` — expect ≥ 1.
- [ ] Run `grep -c "\-\-sync" /workspaces/ocr-container/.claude/skills/decompose-spec/SKILL.md` — expect ≥ 3.
- [ ] Run `grep -c "Plan:" /workspaces/ocr-container/.claude/skills/ship-issue/SKILL.md` — expect ≥ 2.
- [ ] Run `grep -c "Cross-repo recommendation" /workspaces/ocr-container/.claude/agents/pdomain-book-tools.md` — expect 1.
- [ ] Run `bash -n /workspaces/ocr-container/scripts/patch-brainstorming-skill.sh` — expect exit 0.
- [ ] Run `git log --oneline -7` — expect 7 commits matching the commit messages above.
