# Phase 5 — pd-* → pdomain-* long-tail rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the pd-* → pdomain-* rename by flipping the *local* directories, agent definitions, memory dirs, skills, prose, and user memory to match the already-renamed GitHub repos and packages.

**Architecture:** Mechanical sweep across the interactive workspace at `/workspaces/ocr-container/`. No code-behavior changes — every change is a path/name/prose update. Done in waves so the agent harness (which dispatches by agent name and reads memory by path) stays usable; one session-restart checkpoint in the middle.

**Tech Stack:** bash, git mv, sed, ripgrep (`rg`). No new dependencies.

---

## Decisions locked in by this plan

1. **Local dirs rename.** `/workspaces/ocr-container/pd-<x>/` → `/workspaces/ocr-container/pdomain-<x>/` for the 12 active repos. The 3 retired repos keep their `pd-*` names.
2. **Active set (12 dirs):** `pdomain-book-tools`, `pdomain-index-npm`, `pdomain-index-pip`, `pdomain-ocr-cli`, `pdomain-ocr-labeler-spa`, `pdomain-ocr-ops`, `pdomain-ocr-simple-gui`, `pdomain-ocr-synth`, `pdomain-ocr-trainer-spa`, `pdomain-ocr-training`, `pdomain-prep-for-pgdp`, `pdomain-ui`.
3. **Retired set (3 dirs, stay as pd-*):** `pd-png-optimizer`, `pd-ocr-trainer`, `pd-ocr-labeler`. Their agent defs, memory dirs, and CLAUDE.md prose are **not** renamed.
4. **Out of scope:** `pd-gh` and `pd-push` (single-file executables, not repo dirs — separate naming decision). Bot workspaces under `/srv/bot-workspaces/pd-*/`. PAT/secret swap (Finding #2 — deferred).
5. **Session restart point** is between Wave 3 and Wave 4 so the harness reloads agents/memory/skills against new names.

## Idempotency / acceptance grep

Throughout the plan, the "active-names grep" is:

```bash
rg -n --hidden -g '!.git' \
  -e 'pdomain-book-tools' -e 'pdomain-index-npm' -e 'pdomain-index-pip' \
  -e 'pdomain-ocr-cli' -e 'pdomain-ocr-labeler-spa' -e 'pdomain-ocr-ops' \
  -e 'pdomain-ocr-simple-gui' -e 'pdomain-ocr-synth' -e 'pdomain-ocr-trainer-spa' \
  -e 'pdomain-ocr-training' -e 'pdomain-prep-for-pgdp' -e 'pdomain-ui' \
  /workspaces/ocr-container
```

This must shrink to **only** acceptable leftovers (handoff/changelog notes documenting the rename; quoted strings inside docs that intentionally reference the historical name) by the end of Wave 8.

---

## File / asset map

What changes, where:

- **Filesystem dirs** at workspace root (Wave 1) — `git mv` won't work because each is a separate repo; plain `mv` + update of workspace-level `.gitignore` + `scripts/workspace-repos.json`.
- **Agent definitions** at `.claude/agents/*.md` (Wave 2) — rename file + update internal "Expected repo path", description, tool-list paths.
- **Agent memory** at `.claude/agent-memory/*/` (Wave 3) — rename dir + content sed for path refs.
- **Workspace prose** (Wave 4) — `CLAUDE.md`, `MANUAL_SETUP.md`, `README.md` if present, `docs/` tree.
- **Per-repo prose** (Wave 5) — inside each of the 12 renamed repos: `CLAUDE.md`, `CONVENTIONS.md`, `README.md`, `docs/`. These are *separate git repos*, so each gets its own commit + push.
- **User MEMORY.md** at `/home/vscode/.claude/projects/-workspaces-ocr-container/memory/` (Wave 6).
- **Org-meta issues** (Wave 7) — `ConcaveTrillion/ocr-container-meta` open issue bodies.
- **Phase 3 cleanup** (Wave 8) — gitignored leftover dirs.

---

## Wave 0 — Audit & prep

**Files:**
- Read-only: `scripts/workspace-repos.json`, `.gitignore`, `.claude/agents/`, `.claude/agent-memory/`

- [ ] **Step 0.1: Capture baseline grep count**

```bash
cd /workspaces/ocr-container
rg -c --hidden -g '!.git' \
  -e 'pdomain-book-tools' -e 'pdomain-index-npm' -e 'pdomain-index-pip' \
  -e 'pdomain-ocr-cli' -e 'pdomain-ocr-labeler-spa' -e 'pdomain-ocr-ops' \
  -e 'pdomain-ocr-simple-gui' -e 'pdomain-ocr-synth' -e 'pdomain-ocr-trainer-spa' \
  -e 'pdomain-ocr-training' -e 'pdomain-prep-for-pgdp' -e 'pdomain-ui' \
  | awk -F: '{n+=$NF} END {print "baseline active-name hits:", n}'
```

Record the number in the commit message of the final wave for before/after evidence.

- [ ] **Step 0.2: Resolve ship-slice-pd-* skill registration**

The system-reminder lists per-repo skills (`ship-slice-pdomain-book-tools`, `ship-slice-pdomain-ocr-cli`, ...) but the earlier audit found no on-disk skill directories matching that name. They are likely generated/registered from one source — find it before Wave 1, because Wave 1 may or may not flip them automatically.

```bash
grep -rln 'ship-slice-pd' /workspaces/ocr-container/scripts/ /workspaces/ocr-container/.claude/ \
  ~/.claude/ 2>/dev/null | grep -v history.jsonl | grep -v subagents/
cat /workspaces/ocr-container/scripts/workspace-repos.json | python3 -m json.tool | head -80
```

Acceptance for this step: the executor identifies (a) the file/template that emits the `ship-slice-pd-*` names AND (b) confirms whether flipping `workspace-repos.json` in Step 1.3 cascades, OR (c) records a follow-up step inside Wave 1 to handle the additional source.

Possible outcomes:
- **Auto-generated from `workspace-repos.json`** → Wave 1 Step 1.3 handles them automatically; record this in the wave commit message.
- **Static templates under `.claude/skills/` per repo** → add a Wave 1 sub-step that `git mv`s each `ship-slice-pd-<x>` directory to `ship-slice-pdomain-<x>` and sed-updates contents.
- **Registered elsewhere** (e.g. `coding-bot` manifest) → record the source path and add a targeted update step.

- [ ] **Step 0.3: Confirm no in-flight branches on the 12 active repos**

```bash
for r in pdomain-book-tools pdomain-index-npm pdomain-index-pip pdomain-ocr-cli pdomain-ocr-labeler-spa pdomain-ocr-ops pdomain-ocr-simple-gui pdomain-ocr-synth pdomain-ocr-trainer-spa pdomain-ocr-training pdomain-prep-for-pgdp pdomain-ui; do
  cur=$(git -C "$r" branch --show-current 2>/dev/null)
  ahead=$(git -C "$r" rev-list --count "origin/$cur..$cur" 2>/dev/null || echo "?")
  dirty=$(git -C "$r" status --short 2>/dev/null | wc -l)
  echo "$r: branch=$cur ahead=$ahead dirty=$dirty"
done
```

Expected: every repo `branch=main`, `ahead=0` (we just pushed Phase 5 findings), `dirty=0`. If any are non-clean, surface to CT and STOP — do not proceed.

- [ ] **Step 0.4: Confirm no agent worktrees are live in any of the 12 dirs**

```bash
for r in pdomain-book-tools pdomain-index-npm pdomain-index-pip pdomain-ocr-cli pdomain-ocr-labeler-spa pdomain-ocr-ops pdomain-ocr-simple-gui pdomain-ocr-synth pdomain-ocr-trainer-spa pdomain-ocr-training pdomain-prep-for-pgdp pdomain-ui; do
  wt=$(git -C "$r" worktree list | grep -v "^/workspaces/ocr-container/$r " | grep -v '/srv/bot-workspaces/' || true)
  [ -n "$wt" ] && echo "$r has non-main worktrees:" && echo "$wt"
done
```

Expected: no output. Active worktrees would block the directory rename. If any are reported, ask CT to land/abandon them first.

---

## Wave 1 — Filesystem dir renames + workspace registry

**Files:**
- Modify: `/workspaces/ocr-container/.gitignore`
- Modify: `/workspaces/ocr-container/scripts/workspace-repos.json`
- Move: 12 dirs `pd-<x>/` → `pdomain-<x>/`

**Why this wave first:** Every subsequent path reference in agents/memory/prose targets the new dir name. Doing the dir rename first means later sed passes use real paths.

- [ ] **Step 1.1: Rename the 12 dirs in one batch**

```bash
cd /workspaces/ocr-container
for r in book-tools index-npm index-pip ocr-cli ocr-labeler-spa ocr-ops \
         ocr-simple-gui ocr-synth ocr-trainer-spa ocr-training \
         prep-for-pgdp ui; do
  mv "pd-$r" "pdomain-$r"
done
ls -d pdomain-*
```

Expected: 12 `pdomain-<x>/` directories exist; `pd-<x>/` versions are gone (for the 12 active repos). The 3 retired (`pd-png-optimizer`, `pd-ocr-trainer`, `pd-ocr-labeler`) remain.

- [ ] **Step 1.2: Update workspace `.gitignore` per-repo entries**

In `/workspaces/ocr-container/.gitignore`, replace each `/pd-<x>/` line (12 lines, for the active repos) with `/pdomain-<x>/`. Leave the 3 retired entries unchanged.

Verify:
```bash
git diff .gitignore
grep -E '^/pd|^/pdomain' .gitignore | sort
```

Expected diff: 12 lines changed, retired 3 untouched.

- [ ] **Step 1.3: Update `scripts/workspace-repos.json`**

Find every `pd-<x>` (and any URL containing `pd-<x>`) that maps to one of the 12 renamed repos. Replace with `pdomain-<x>`. The 3 retired entries stay.

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("scripts/workspace-repos.json")
text = p.read_text()
ACTIVE = ["book-tools", "index-npm", "index-pip", "ocr-cli", "ocr-labeler-spa",
          "ocr-ops", "ocr-simple-gui", "ocr-synth", "ocr-trainer-spa",
          "ocr-training", "prep-for-pgdp", "ui"]
for n in ACTIVE:
    text = text.replace(f"pd-{n}", f"pdomain-{n}")
p.write_text(text)
PY
git diff scripts/workspace-repos.json | head -60
```

Verify the diff only flips the 12 active names; the 3 retired names appear unchanged.

- [ ] **Step 1.4: Commit Wave 1 in the workspace meta repo**

```bash
git add .gitignore scripts/workspace-repos.json
# (Renamed dirs are NOT staged here — they live in the .gitignore and
#  are not tracked by the workspace-meta repo. The per-repo git histories
#  are unaffected by the dir rename, since git tracks repo root by .git/.)
git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com \
  commit -m "rename(phase5): flip 12 active pd-* dirs to pdomain-* (+ .gitignore, workspace-repos.json)"
```

- [ ] **Step 1.5: Sanity check that each renamed dir is still a working repo**

```bash
for r in pdomain-book-tools pdomain-index-npm pdomain-index-pip pdomain-ocr-cli \
         pdomain-ocr-labeler-spa pdomain-ocr-ops pdomain-ocr-simple-gui \
         pdomain-ocr-synth pdomain-ocr-trainer-spa pdomain-ocr-training \
         pdomain-prep-for-pgdp pdomain-ui; do
  echo -n "$r: "; git -C "$r" rev-parse --abbrev-ref HEAD
done
```

Expected: every line shows `main` (or whatever branch is checked out). If any fail "not a git repository", the dir rename was incomplete — investigate before continuing.

---

## Wave 2 — Agent definitions

**Files:**
- Rename: 19 of 26 files under `.claude/agents/pd-*.md` → `pdomain-*.md` (skip the 7 retired-repo files: 2 png-optimizer + 2 ocr-trainer + 3 ocr-labeler-incl-driver).
- Modify: same files, internal content (Expected repo path, description, prose).

**Active set to rename (22 files):**

```
pdomain-book-tools.md           pdomain-book-tools-docs.md
pdomain-ocr-cli.md              pdomain-ocr-cli-docs.md
pdomain-ocr-labeler-spa.md      pdomain-ocr-labeler-spa-docs.md
pdomain-ocr-ops.md              pdomain-ocr-ops-docs.md
pdomain-ocr-simple-gui.md
pdomain-ocr-synth.md            pdomain-ocr-synth-docs.md
pdomain-ocr-trainer-spa.md      pdomain-ocr-trainer-spa-docs.md
pdomain-ocr-training.md         pdomain-ocr-training-docs.md
pdomain-prep-for-pgdp.md        pdomain-prep-for-pgdp-docs.md
pdomain-ui.md                   pdomain-ui-docs.md
```

(That's 19 files for 12 active repos: most have both `<name>.md` + `<name>-docs.md`, except `pdomain-ocr-simple-gui.md` which has no `-docs` sibling, and the two index repos `pdomain-index-pip` / `pdomain-index-npm` which have no agents at all. Step 2.1 produces the exact list at runtime.)

**Retired set to leave alone (4 files):**

```
pd-png-optimizer.md        pd-png-optimizer-docs.md
pd-ocr-trainer.md          pd-ocr-trainer-docs.md
pd-ocr-labeler.md          pd-ocr-labeler-docs.md
pd-ocr-labeler-driver.md
```

- [ ] **Step 2.1: Build the rename map**

```bash
cd /workspaces/ocr-container/.claude/agents
ACTIVE="book-tools index-npm index-pip ocr-cli ocr-labeler-spa ocr-ops \
        ocr-simple-gui ocr-synth ocr-trainer-spa ocr-training \
        prep-for-pgdp ui"
for n in $ACTIVE; do
  for suffix in "" "-docs"; do
    f="pd-${n}${suffix}.md"
    [ -f "$f" ] && echo "rename $f -> pdomain-${n}${suffix}.md"
  done
done
```

Confirm the list before executing. There may be no `pd-index-*` agent files (the indices don't have dedicated subagents per CLAUDE.md).

- [ ] **Step 2.2: `git mv` each file**

```bash
cd /workspaces/ocr-container/.claude/agents
for n in $ACTIVE; do
  for suffix in "" "-docs"; do
    f="pd-${n}${suffix}.md"
    [ -f "$f" ] && git mv "$f" "pdomain-${n}${suffix}.md"
  done
done
```

Use `git mv` so the workspace-meta repo records the rename as a rename (preserves blame).

- [ ] **Step 2.3: Sed the file contents**

Each agent definition contains the agent's name, expected repo path, and prose that references the dir. Replace every occurrence of an active `pd-<x>` token (whole-word, hyphen-bounded) with `pdomain-<x>`, but leave references to the retired 3 alone.

```bash
cd /workspaces/ocr-container/.claude/agents
for n in $ACTIVE; do
  # Update every renamed agent file
  for f in pdomain-${n}.md pdomain-${n}-docs.md; do
    [ -f "$f" ] || continue
    sed -i -E "s/\\bpd-${n}\\b/pdomain-${n}/g" "$f"
  done
done
# Also: agent files for OTHER renamed repos may cross-reference the names
# (e.g. pdomain-ui.md may mention pdomain-prep-for-pgdp). Do a global sweep across
# ALL agent files for the active 12:
for n in $ACTIVE; do
  find . -maxdepth 1 -name '*.md' -exec sed -i -E "s/\\bpd-${n}\\b/pdomain-${n}/g" {} +
done
git diff --stat .
```

Expected: each renamed agent file shows content updates; retired agent files may show updates *only* where they referenced an active sibling (e.g. `pd-ocr-labeler.md` mentioning `pdomain-ocr-labeler-spa` should now say `pdomain-ocr-labeler-spa`).

- [ ] **Step 2.4: Per-file acceptance check**

```bash
cd /workspaces/ocr-container/.claude/agents
for n in $ACTIVE; do
  for f in pdomain-${n}.md pdomain-${n}-docs.md; do
    [ -f "$f" ] || continue
    # Should find NO references to the active name in renamed files
    if grep -E "\\bpd-${n}\\b" "$f"; then
      echo "FAIL: $f still references pd-${n}"
    fi
  done
done
```

Expected: no FAIL output.

- [ ] **Step 2.5: Commit Wave 2**

```bash
cd /workspaces/ocr-container
git add .claude/agents/
git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com \
  commit -m "rename(phase5): flip 19 active agent definitions pd-* -> pdomain-*"
```

---

## Wave 3 — Agent memory dirs

**Files:**
- Rename: 10 dirs under `.claude/agent-memory/pd-*/` → `pdomain-*/` (the 12-minus-2 — `pd-index-*` likely have no memory dirs since indices don't have agents).
- Modify: contents inside each renamed dir (linked-memory `[[name]]` references, path refs).

- [ ] **Step 3.1: Build the rename map**

```bash
cd /workspaces/ocr-container/.claude/agent-memory
for n in $ACTIVE; do
  [ -d "pd-${n}" ] && echo "rename pd-${n}/ -> pdomain-${n}/"
done
ls -d pd-*/
```

- [ ] **Step 3.2: `git mv` each dir**

```bash
cd /workspaces/ocr-container/.claude/agent-memory
for n in $ACTIVE; do
  [ -d "pd-${n}" ] && git mv "pd-${n}" "pdomain-${n}"
done
```

- [ ] **Step 3.3: Sed all .md files inside the agent-memory tree**

Sweep for the 12 active names in every `.md` under `.claude/agent-memory/`:

```bash
cd /workspaces/ocr-container/.claude/agent-memory
for n in $ACTIVE; do
  find . -name '*.md' -exec sed -i -E "s/\\bpd-${n}\\b/pdomain-${n}/g" {} +
done
```

This catches cross-repo `[[link]]`s in memory files (e.g. a pdomain-prep-for-pgdp memory file referencing `[[pdomain-ui-handoff-plan-format]]` should now read `[[pdomain-ui-handoff-plan-format]]` if that memory was renamed too).

- [ ] **Step 3.4: Acceptance check per dir**

```bash
cd /workspaces/ocr-container/.claude/agent-memory
for n in $ACTIVE; do
  d="pdomain-${n}"
  [ -d "$d" ] || continue
  hits=$(grep -rE "\\bpd-${n}\\b" "$d" | wc -l)
  [ "$hits" -ne 0 ] && echo "FAIL: $d has $hits active-name hits remaining"
done
```

Expected: no FAIL output.

- [ ] **Step 3.5: Commit Wave 3**

```bash
cd /workspaces/ocr-container
git add .claude/agent-memory/
git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com \
  commit -m "rename(phase5): flip 10 active agent-memory dirs pd-* -> pdomain-*"
```

---

## CHECKPOINT — session restart

After Wave 3, the harness has stale agent / memory pointers. Restart the Claude Code session before continuing.

CT action: **type `/exit` and start a fresh session.** When you resume, the fresh session sees `pdomain-*` agents and memory. Then ask: "continue Phase 5 from Wave 4."

If you forget and continue in the same session, agent dispatches will likely fail or hit stale paths. The prose waves (4–7) do not invoke per-repo agents, so they could in principle proceed in this session — but the restart is the cleaner cutover.

---

## Wave 4 — Workspace-root prose

**Files:**
- Modify: `/workspaces/ocr-container/CLAUDE.md`
- Modify: `/workspaces/ocr-container/MANUAL_SETUP.md`
- Modify: `/workspaces/ocr-container/README.md` (if present)
- Modify: every `.md` under `/workspaces/ocr-container/docs/`

- [ ] **Step 4.1: Sweep**

```bash
cd /workspaces/ocr-container
ACTIVE="book-tools index-npm index-pip ocr-cli ocr-labeler-spa ocr-ops \
        ocr-simple-gui ocr-synth ocr-trainer-spa ocr-training \
        prep-for-pgdp ui"
# Touch only top-level prose + docs/, leave .claude/ alone (already handled
# in Waves 2-3) and skip per-repo CLAUDE.mds (handled in Wave 5).
for n in $ACTIVE; do
  find . -maxdepth 1 -name '*.md' -exec sed -i -E "s/\\bpd-${n}\\b/pdomain-${n}/g" {} +
  find docs -name '*.md' -exec sed -i -E "s/\\bpd-${n}\\b/pdomain-${n}/g" {} +
done
git diff --stat | tail -20
```

- [ ] **Step 4.2: Spot-check known landmarks**

```bash
# CLAUDE.md routing section
grep -nE '\bpd-(book-tools|ocr-cli|ocr-ops|ui)\b' CLAUDE.md
```

Expected: no remaining active-name hits. If hits appear, they're either inside historical-note sections (acceptable — confirm by reading) or the sed missed a non-standard token form.

- [ ] **Step 4.3: Acceptance grep**

```bash
cd /workspaces/ocr-container
hits=$(rg -c --hidden -g '!.git' -g '!.claude/agent-memory' -g '!.claude/agents' \
  -e 'pdomain-book-tools' -e 'pdomain-index-npm' -e 'pdomain-index-pip' \
  -e 'pdomain-ocr-cli' -e 'pdomain-ocr-labeler-spa' -e 'pdomain-ocr-ops' \
  -e 'pdomain-ocr-simple-gui' -e 'pdomain-ocr-synth' -e 'pdomain-ocr-trainer-spa' \
  -e 'pdomain-ocr-training' -e 'pdomain-prep-for-pgdp' -e 'pdomain-ui' \
  -- 'CLAUDE.md' 'MANUAL_SETUP.md' 'README.md' 'docs/**' 2>/dev/null \
  | awk -F: '{n+=$NF} END {print n+0}')
echo "remaining workspace-root prose hits: $hits"
```

Expected: a small number — typically rename-doc historical references in `docs/handoff-next-session.md`, `docs/plans/2026-05-26-pdomain-rename-phase-*.md`, and this plan file. Confirm those are intentional historical references and not new bugs.

- [ ] **Step 4.4: Commit Wave 4**

```bash
cd /workspaces/ocr-container
git add CLAUDE.md MANUAL_SETUP.md README.md docs/
git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com \
  commit -m "rename(phase5): flip active pd-* names in workspace prose (CLAUDE.md, docs/, MANUAL_SETUP.md)"
```

---

## Wave 5 — Per-repo prose (one commit + push per repo)

**Files:** inside each of the 12 renamed repos:
- `CLAUDE.md`, `CONVENTIONS.md`, `README.md`, `docs/**/*.md`

Each repo is its own git history, so each gets its own commit. Push immediately after each commit (per CT default this session: explicit pushes after merge).

- [ ] **Step 5.1: Run per-repo sweep**

```bash
ACTIVE="book-tools index-npm index-pip ocr-cli ocr-labeler-spa ocr-ops \
        ocr-simple-gui ocr-synth ocr-trainer-spa ocr-training \
        prep-for-pgdp ui"
for r in $ACTIVE; do
  path="/workspaces/ocr-container/pdomain-$r"
  cd "$path"
  for n in $ACTIVE; do
    find . -name '*.md' -not -path './.git/*' \
      -exec sed -i -E "s/\\bpd-${n}\\b/pdomain-${n}/g" {} +
  done
  if git status --short | grep -q .; then
    git add -A
    git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com \
      commit -m "docs(rename): flip pd-* refs to pdomain-* in repo prose"
    echo "$r committed"
  else
    echo "$r: no changes"
  fi
done
```

- [ ] **Step 5.2: Push each repo (CT explicit consent assumed for this batch)**

If CT has already authorized push for the rename sweep, push each main:

```bash
for r in $ACTIVE; do
  cd "/workspaces/ocr-container/pdomain-$r"
  git push origin main 2>&1 | tail -3
done
```

Otherwise, stop after commits and report SHAs for CT to approve.

- [ ] **Step 5.3: Acceptance grep per repo**

```bash
for r in $ACTIVE; do
  path="/workspaces/ocr-container/pdomain-$r"
  hits=$(cd "$path" && grep -rE "\\bpd-($(echo $ACTIVE | tr ' ' '|'))\\b" --include='*.md' . 2>/dev/null | wc -l)
  echo "$r: $hits remaining active-name hits"
done
```

Expected: each line shows `0`, except where a repo intentionally documents the historical name (e.g. a `CHANGELOG.md` entry).

---

## Wave 6 — User-level MEMORY.md

**Files:** `/home/vscode/.claude/projects/-workspaces-ocr-container/memory/MEMORY.md` and the individual memory entries it indexes.

- [ ] **Step 6.1: Audit user memory for active-name hits**

```bash
MEM_DIR="/home/vscode/.claude/projects/-workspaces-ocr-container/memory"
ACTIVE="book-tools index-npm index-pip ocr-cli ocr-labeler-spa ocr-ops \
        ocr-simple-gui ocr-synth ocr-trainer-spa ocr-training \
        prep-for-pgdp ui"
for n in $ACTIVE; do
  hits=$(grep -rE "\\bpd-${n}\\b" "$MEM_DIR" 2>/dev/null | wc -l)
  [ "$hits" -gt 0 ] && echo "pd-${n}: $hits hits"
done
```

- [ ] **Step 6.2: Rewrite in place**

```bash
for n in $ACTIVE; do
  find "$MEM_DIR" -name '*.md' -exec sed -i -E "s/\\bpd-${n}\\b/pdomain-${n}/g" {} +
done
```

No commit step — user memory is not git-tracked. Just verify the edits with a follow-up grep showing zero active-name hits.

---

## Wave 7 — ocr-container-meta GH issue body audit

**Files:** open issues at `ConcaveTrillion/ocr-container-meta`.

- [ ] **Step 7.1: Pull open issues**

```bash
gh issue list --repo ConcaveTrillion/ocr-container-meta --state open --limit 200 \
  --json number,title,body \
  > /tmp/ocr-container-meta-open-issues.json
jq '.[] | {n: .number, t: .title}' /tmp/ocr-container-meta-open-issues.json | head -40
```

- [ ] **Step 7.2: Identify issues that need body updates**

```bash
jq -r '.[] | select(.body | test("pd-(book-tools|ocr-(cli|labeler-spa|ops|simple-gui|synth|trainer-spa|training)|prep-for-pgdp|ui|index-(pip|npm))")) | "\(.number)\t\(.title)"' \
  /tmp/ocr-container-meta-open-issues.json
```

Each listed issue's body references an active pd-* name and should be updated.

- [ ] **Step 7.3: Per-issue update (manual review recommended)**

Issue bodies often contain code blocks, URLs, and prose. A blind sed risks corrupting URLs. For each listed issue:

1. `gh issue view N --repo ConcaveTrillion/ocr-container-meta`
2. Decide whether the active-name occurrence is prose (rewrite) or a historical URL/SHA reference (keep).
3. `gh issue edit N --repo ConcaveTrillion/ocr-container-meta --body "$(updated body)"`

CT may prefer to defer this wave — it's slow + judgment-heavy and the live GH repo redirects handle URL references for free.

---

## Wave 8 — Phase 3 sweep cleanup

**Files:**
- Delete: `/workspaces/ocr-container/pdomain-ocr-labeler-spa/src/pd_ocr_labeler_spa/`
- Delete: `/workspaces/ocr-container/pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/`

These are gitignored leftover package dirs from Phase 2's `pd_*` → `pdomain_*` Python-package rename. Safe to remove.

- [ ] **Step 8.1: Confirm both dirs are gitignored**

```bash
git -C /workspaces/ocr-container/pdomain-ocr-labeler-spa check-ignore src/pd_ocr_labeler_spa
git -C /workspaces/ocr-container/pdomain-prep-for-pgdp check-ignore src/pd_prep_for_pgdp
```

Expected: both commands echo the path (indicating they're ignored). If either is *not* ignored, STOP — investigate before deleting.

- [ ] **Step 8.2: Remove**

```bash
rm -rf /workspaces/ocr-container/pdomain-ocr-labeler-spa/src/pd_ocr_labeler_spa
rm -rf /workspaces/ocr-container/pdomain-prep-for-pgdp/src/pd_prep_for_pgdp
```

No commit (the dirs were ignored — `git status` should be unchanged).

---

## Wave 9 — Final acceptance + handoff doc

- [ ] **Step 9.1: Run the workspace-wide active-names grep**

```bash
cd /workspaces/ocr-container
rg -c --hidden -g '!.git' \
  -e 'pdomain-book-tools' -e 'pdomain-index-npm' -e 'pdomain-index-pip' \
  -e 'pdomain-ocr-cli' -e 'pdomain-ocr-labeler-spa' -e 'pdomain-ocr-ops' \
  -e 'pdomain-ocr-simple-gui' -e 'pdomain-ocr-synth' -e 'pdomain-ocr-trainer-spa' \
  -e 'pdomain-ocr-training' -e 'pdomain-prep-for-pgdp' -e 'pdomain-ui' \
  | awk -F: '{n+=$NF} END {print "final active-name hits:", n}'
```

Compare against the Wave-0 baseline. The remaining hits should be **only** historical-note references in:
- `docs/handoff-next-session.md`
- `docs/plans/2026-05-26-pdomain-rename-phase-*.md`
- This plan file itself
- This session's commit messages (already history; nothing to do)

- [ ] **Step 9.2: Update `docs/handoff-next-session.md`**

Add a Phase 5 section mirroring the existing Phase 3/4.5 sections:

- What renamed (12 dirs, 19 agent defs, 10 memory dirs, prose across N files).
- Final main HEAD per repo.
- Baseline → final grep delta.
- Remaining out-of-scope items: `pd-gh` / `pd-push` naming decision, PAT/secret swap (Finding #2), bot-workspace dir renames (`/srv/bot-workspaces/pd-*/`).

- [ ] **Step 9.3: Commit Wave 9 in workspace meta**

```bash
cd /workspaces/ocr-container
git add docs/handoff-next-session.md
git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com \
  commit -m "docs(handoff): record Phase 5 rename sweep (dirs + agents + memory + prose)"
```

- [ ] **Step 9.4: Push workspace meta (if CT consents)**

```bash
git push origin main
```

---

## Acceptance gates (overall)

- Wave 0: clean repos (no in-flight branches, no live worktrees) — confirmed before starting.
- Wave 1: 12 `pdomain-*/` dirs exist; 3 retired `pd-*/` dirs exist; `.gitignore` and `workspace-repos.json` updated.
- Wave 2: 22 agent files renamed; each renamed file passes its own `grep \bpd-${n}\b` check (zero hits).
- Wave 3: 10 memory dirs renamed; cross-link `[[name]]` references updated.
- Wave 4: workspace prose grep reduced to historical-only hits.
- Wave 5: each of 12 repos has a commit + optional push; per-repo acceptance grep clean.
- Wave 6: user MEMORY.md has zero active-name hits.
- Wave 7: open ocr-container-meta issues either updated or explicitly deferred.
- Wave 8: two leftover `pd_*` package dirs gone.
- Wave 9: final grep delta logged in handoff doc; workspace-meta committed.

## Out of scope

Explicit non-goals so the sweep doesn't grow:

- `pd-gh`, `pd-push` (single-file utility scripts — separate decision)
- `/srv/bot-workspaces/pd-*/` (bot workspaces, orthogonal per CLAUDE.md)
- `~/.local/share/pd-suite/` (kept as fallback per Phase 4 migration)
- PAT/secret swap (Finding #2 — needs CT to mint PAT)
- Git tag renames (annotated tags `v*` are untouched — only paths/names change)
- The 3 retired repos (`pd-png-optimizer`, `pd-ocr-trainer`, `pd-ocr-labeler`) and their agents, memory, and prose

## Rollback

If a wave goes wrong before commit, `git checkout -- <paths>` restores. After commit, `git revert <SHA>` works because every wave is a single commit.

The Wave 1 dir rename is the riskiest. Rollback: `mv pdomain-<x> pd-<x>` for each, plus `git checkout -- .gitignore scripts/workspace-repos.json`. No data loss since each repo's `.git/` directory moved intact with its parent.
