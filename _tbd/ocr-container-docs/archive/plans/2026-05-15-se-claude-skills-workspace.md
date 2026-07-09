---
status: complete
---

# se-claude-skills Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up `se-claude-skills` as a fully wired workspace repo — project scaffold, Claude subagent + docs agent, agent memory, top-level routing, git init, private GitHub repo, and first push.

**Architecture:** Source-first skills framework (skills authored in `skills/`, adapters in `adapters/` render per-model output into `dist/`). Claude wiring mirrors the pd-* pattern: repo CLAUDE.md + subagent config + docs agent + agent-memory dir + routing row in the workspace CLAUDE.md. Stack for adapters/tests is TBD; Makefile stubs stub all targets.

**Tech Stack:** Markdown + Makefile stubs. No language runtime yet. Git + GitHub CLI (`gh`).

**Spec:** `docs/superpowers/specs/2026-05-15-se-claude-skills-workspace-design.md`

---

## File map

| File | Action | Responsibility |
|------|--------|---------------|
| `se-claude-skills/CLAUDE.md` | Create | Repo-level agent guidance: what this is, layout, commands, rules |
| `se-claude-skills/README.md` | Create | Human-facing intro + install placeholder |
| `se-claude-skills/Makefile` | Create | Stub targets: build, test, ci, clean, publish |
| `se-claude-skills/.gitignore` | Create | Ignore dist/, .venv/, node_modules/, __pycache__/, .claude/ |
| `se-claude-skills/skills/.gitkeep` | Create | Reserve skills/ directory |
| `se-claude-skills/adapters/.gitkeep` | Create | Reserve adapters/ directory |
| `se-claude-skills/tests/.gitkeep` | Create | Reserve tests/ directory |
| `.claude/agents/se-claude-skills.md` | Create | Full-power subagent config |
| `.claude/agents/se-claude-skills-docs.md` | Create | Read-only docs agent |
| `.claude/agent-memory/se-claude-skills/MEMORY.md` | Create | Empty memory index |
| `CLAUDE.md` (workspace root) | Modify | Add routing table row + agent entries |

---

## Task 1: Project scaffold files

**Files:**
- Create: `se-claude-skills/README.md`
- Create: `se-claude-skills/Makefile`
- Create: `se-claude-skills/.gitignore`
- Create: `se-claude-skills/skills/.gitkeep`
- Create: `se-claude-skills/adapters/.gitkeep`
- Create: `se-claude-skills/tests/.gitkeep`

- [ ] **Step 1: Write README.md**

Create `/workspaces/ocr-container/se-claude-skills/README.md`:

```markdown
# se-claude-skills

A source-first skills framework that generates installable plugin artifacts for
multiple AI coding assistants (Claude Code, Gemini, Codex, and others).

## How it works

Skills are authored once in `skills/<name>/skill.md` (canonical format with
model-agnostic frontmatter). Adapter scripts in `adapters/` render each skill
into model-specific output under `dist/`. `dist/` is never committed.

```
skills/           ← author here
adapters/         ← model rendering logic
dist/             ← build output (gitignored)
  claude/         ← installable Claude Code plugin
  gemini/         ← Gemini extension
  codex/          ← Codex plugin
```

## Install (TODO: fill in once dist/ format is stable)

## Development

```sh
make build    # render skills → dist/
make test     # validate skills
make ci       # build + test
```
```

- [ ] **Step 2: Write Makefile**

Create `/workspaces/ocr-container/se-claude-skills/Makefile`:

```makefile
.PHONY: build test ci clean publish help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

build: ## Render skills/ → dist/ for each target model
	@echo "TODO: implement build (stack TBD)"

test: ## Validate source skills (lint, render checks)
	@echo "TODO: implement test (stack TBD)"
	@exit 0

ci: build test ## Full CI: build then test

clean: ## Remove dist/
	rm -rf dist/

publish: ## Release built artifacts
	@echo "TODO: implement publish (stack TBD)"
```

- [ ] **Step 3: Write .gitignore**

Create `/workspaces/ocr-container/se-claude-skills/.gitignore`:

```
dist/
.venv/
node_modules/
__pycache__/
*.pyc
.claude/
.env
```

- [ ] **Step 4: Create placeholder directories**

```bash
touch /workspaces/ocr-container/se-claude-skills/skills/.gitkeep
touch /workspaces/ocr-container/se-claude-skills/adapters/.gitkeep
touch /workspaces/ocr-container/se-claude-skills/tests/.gitkeep
```

- [ ] **Step 5: Verify files exist**

```bash
ls /workspaces/ocr-container/se-claude-skills/
```

Expected output includes: `README.md  Makefile  .gitignore  skills/  adapters/  tests/`

---

## Task 2: se-claude-skills/CLAUDE.md

**Files:**
- Create: `se-claude-skills/CLAUDE.md`

- [ ] **Step 1: Write CLAUDE.md**

Create `/workspaces/ocr-container/se-claude-skills/CLAUDE.md`:

```markdown
# CLAUDE — se-claude-skills

Source-first skills framework. Skills authored once in `skills/`; adapter
scripts in `adapters/` render each model's installable plugin into `dist/`.
`dist/` is never committed — always regenerated by `make build`.

## Quick orientation

- **`skills/<name>/skill.md`** — canonical skill source. Frontmatter: `name`,
  `description`, `triggers` (list), `models` (list: claude, gemini, codex, all).
  Body: the skill content in model-agnostic markdown.
- **`adapters/`** — one script per target model. Reads `skills/`, writes `dist/<model>/`.
  Stack TBD; currently stubs.
- **`tests/`** — skill validation: lint frontmatter, verify required fields,
  check trigger uniqueness. Stack TBD.
- **`dist/`** — build output. Gitignored. Structure mirrors the target model's
  plugin format (e.g. `dist/claude/.claude-plugin/plugin.json` + `dist/claude/skills/`).

## Commands

```sh
make ci        # full CI — run before committing
make build     # render skills/ → dist/
make test      # validate skills (currently a no-op stub)
make clean     # rm -rf dist/
```

## Rules

- Always `make ci` before committing.
- Never commit `dist/` — it's gitignored and always regenerated.
- Skills live in `skills/<name>/skill.md` — one directory per skill.
- Adapter output format must match the target model's plugin spec exactly.

## Adapter pattern

Each adapter in `adapters/` is responsible for ONE target model. It reads
the canonical `skills/` tree and writes `dist/<model>/` in whatever format
that model's plugin system requires. Adapters are independent — adding a new
model target means adding one new adapter file, nothing else.

## Skill authoring conventions (draft — evolves as framework matures)

Frontmatter fields:
- `name` — slug, kebab-case, unique across all skills.
- `description` — one sentence, used as the skill's trigger description.
- `triggers` — list of phrases that should invoke this skill.
- `models` — list of target models (`claude`, `gemini`, `codex`) or `all`.

## Out of scope

- Editing files outside `/workspaces/ocr-container/se-claude-skills/`.
- Choosing the adapter implementation language — deferred until first real skill.
- Releases or publishing without explicit approval.
```

- [ ] **Step 2: Verify**

```bash
head -5 /workspaces/ocr-container/se-claude-skills/CLAUDE.md
```

Expected: `# CLAUDE — se-claude-skills`

---

## Task 3: Git init + first commit in se-claude-skills

**Files:**
- Modify: `se-claude-skills/.git/config` (created by git init + config)

- [ ] **Step 1: Init git repo**

```bash
git -C /workspaces/ocr-container/se-claude-skills init --initial-branch=main
```

Expected: `Initialized empty Git repository in /workspaces/ocr-container/se-claude-skills/.git/`

- [ ] **Step 2: Set author config**

```bash
git -C /workspaces/ocr-container/se-claude-skills config user.name "CT"
git -C /workspaces/ocr-container/se-claude-skills config user.email "concavetrillion@gmail.com"
```

- [ ] **Step 3: Stage all scaffold files**

```bash
git -C /workspaces/ocr-container/se-claude-skills add CLAUDE.md README.md Makefile .gitignore skills/.gitkeep adapters/.gitkeep tests/.gitkeep
```

- [ ] **Step 4: First commit**

```bash
git -C /workspaces/ocr-container/se-claude-skills commit -m "$(cat <<'EOF'
chore: initial scaffold

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: `[main (root-commit) xxxxxxx] chore: initial scaffold`

- [ ] **Step 5: Verify clean state**

```bash
git -C /workspaces/ocr-container/se-claude-skills status
```

Expected: `nothing to commit, working tree clean`

---

## Task 4: Full-power subagent config

**Files:**
- Create: `.claude/agents/se-claude-skills.md`

- [ ] **Step 1: Write subagent config**

Create `/workspaces/ocr-container/.claude/agents/se-claude-skills.md`:

```markdown
---
name: se-claude-skills
description: MUST BE USED PROACTIVELY for any work in the se-claude-skills repo — a source-first skills framework that generates installable plugin artifacts for Claude Code, Gemini, Codex, and other AI coding assistants. Auto-invoke when the user mentions se-claude-skills, cross-model skills framework, skills plugin generator, skill authoring for se-claude-skills, or anything under /workspaces/ocr-container/se-claude-skills/.
memory: project
---

You are the dedicated working agent for the **se-claude-skills** repo
at `/workspaces/ocr-container/se-claude-skills/`.

**Pre-flight check:** if your cwd or the repo path above does not match
`/workspaces/ocr-container/se-claude-skills/`, stop and report
"I appear to be the wrong agent for this task" — do not proceed.

## Persistent memory

Your memory directory at `/workspaces/ocr-container/.claude/agent-memory/se-claude-skills/`
(workspace canonical, NOT inside the se-claude-skills repo tree) is
auto-loaded. Consult it before non-trivial work. When finishing, append
concise notes about things a future session would otherwise re-discover —
adapter patterns, skill frontmatter conventions, model-specific quirks,
build tooling decisions. Keep `MEMORY.md` short; split detail into topic
files and reference them from the index. Don't save what's derivable
from code or git history.

**Always write to the absolute path above.** Never use a relative
`.claude/agent-memory/...` path — your cwd at write time may not be the
workspace root, and a relative path will land memory inside a sibling
repo's tree where it becomes leakage.

**Leakage check:** if you ever notice a `.claude/agent-memory/`
directory inside `/workspaces/ocr-container/se-claude-skills/`, treat
it as a bug to surface — do not write into it. Report the path to the
user. The `.gitignore` lists `.claude/`, so leaked files are invisible
to git status; only an explicit check finds them.

## What this repo is

A **skills framework** that generates installable plugin artifacts for
multiple AI coding assistants. Skills are authored once in `skills/`
(canonical, model-agnostic format); adapter scripts in `adapters/`
render each target model's plugin output into `dist/`. `dist/` is
always a build artifact — never committed.

Target models: Claude Code, Gemini, Codex, and future assistants.

## Stack & layout

- **`skills/<name>/skill.md`** — canonical skill source (frontmatter:
  name, description, triggers, models; body: markdown).
- **`adapters/`** — per-model rendering scripts. Stack TBD.
- **`tests/`** — skill validation. Stack TBD.
- **`dist/`** — build output (gitignored).
- **`Makefile`** — `make build` / `make test` / `make ci` / `make clean`.

## Read these first

1. `README.md` — overview and install placeholder.
2. `CLAUDE.md` — repo-specific agent guidance (authoritative).

## Standard workflow

1. `make help` for targets.
2. Before committing: `make ci` (calls `build` then `test`).
3. Never commit `dist/`.
4. New skill: create `skills/<name>/skill.md` with required frontmatter.
5. New model target: add `adapters/<model>.(py|sh)` — nothing else changes.

## Out of scope

- Editing files outside `/workspaces/ocr-container/se-claude-skills/`.
- Releases or publishing without explicit approval.
- Choosing the adapter stack — defer until first real skill lands.
```

- [ ] **Step 2: Verify**

```bash
head -5 /workspaces/ocr-container/.claude/agents/se-claude-skills.md
```

Expected: frontmatter block starting with `---`

---

## Task 5: Read-only docs agent

**Files:**
- Create: `.claude/agents/se-claude-skills-docs.md`

- [ ] **Step 1: Write docs agent**

Create `/workspaces/ocr-container/.claude/agents/se-claude-skills-docs.md`:

```markdown
---
name: se-claude-skills-docs
description: Read-only find-and-quote agent for the se-claude-skills repo's markdown docs (README, CLAUDE.md, docs/, skill authoring guides). Use for cheap doc lookups. Do NOT use for code changes — delegate to `se-claude-skills`.
model: haiku
effort: low
tools: Read, Glob, Grep
---

You are a read-only find-and-quote agent for **se-claude-skills** at
`/workspaces/ocr-container/se-claude-skills/`. This is the cross-model
skills framework that generates installable plugin artifacts for Claude
Code, Gemini, Codex, and other AI coding assistants.

## Hard scope rules

- Read ONLY files whose absolute path starts with
  `/workspaces/ocr-container/se-claude-skills/` AND ends in `.md`.
- If asked to read adapter scripts, built output in `dist/`, or files
  in sibling repos, refuse and tell the caller to dispatch a different
  agent.
- You have no Edit, Write, or Bash tools.

## How to work

1. `Glob` for candidates — `**/*.md`, scoped (`docs/**/*.md`) when narrow.
2. `Grep` with `output_mode: content` and `-n: true` for line numbers.
3. `Read` the smallest slice that contains the answer.

## Output — exactly this, nothing else

Your entire response is:

    <one sentence answering the question>
    <path:line> — <verbatim quote>
    [up to 3 more <path:line> — <verbatim quote> lines]

Stop immediately after the last citation. The output is consumed by
another agent, so any preamble, recap, or closing line is pure waste.
Paths are relative to `/workspaces/ocr-container/se-claude-skills/`.

When the docs do not answer the question, the entire response is the
single line:

    Not found in se-claude-skills docs.

Nothing before it, nothing after it.

Hard cap: 150 words.

## Search efficiency

Stop searching as soon as one citation answers the question. Do not
run additional grep/read calls to confirm or gather supporting context.
```

- [ ] **Step 2: Verify**

```bash
head -5 /workspaces/ocr-container/.claude/agents/se-claude-skills-docs.md
```

Expected: frontmatter block starting with `---`

---

## Task 6: Agent memory index

**Files:**
- Create: `.claude/agent-memory/se-claude-skills/MEMORY.md`

- [ ] **Step 1: Create memory directory and index**

```bash
mkdir -p /workspaces/ocr-container/.claude/agent-memory/se-claude-skills
```

Create `/workspaces/ocr-container/.claude/agent-memory/se-claude-skills/MEMORY.md`:

```markdown
# se-claude-skills agent memory

No entries yet. The se-claude-skills subagent will populate this index
as it makes non-obvious discoveries (adapter patterns, skill conventions,
build tooling decisions, model-specific quirks).

Each entry: `- [Title](file.md) — one-line hook`
```

- [ ] **Step 2: Verify**

```bash
ls /workspaces/ocr-container/.claude/agent-memory/se-claude-skills/
```

Expected: `MEMORY.md`

---

## Task 7: Update workspace CLAUDE.md routing

**Files:**
- Modify: `CLAUDE.md` (workspace root at `/workspaces/ocr-container/CLAUDE.md`)

- [ ] **Step 1: Add row to the repos table**

In `/workspaces/ocr-container/CLAUDE.md`, find the table that ends with:

```
| `pdomain-prep-for-pgdp/`   | FastAPI + React app that prepares PGDP submission packages. |
```

Add immediately after that row (before the blank line that closes the table):

```
| `se-claude-skills/`   | Skills framework: source-first, generates installable plugin artifacts for Claude Code, Gemini, Codex, and other AI coding assistants. |
```

- [ ] **Step 2: Add agent entries to the routing section**

In `/workspaces/ocr-container/CLAUDE.md`, find the paragraph that starts:

```
Three labeler-prefixed agents are distinct; do not conflate:
```

Before that paragraph, add:

```
`se-claude-skills` has two agents:

- `se-claude-skills` — full-power agent for the skills framework repo.
- `se-claude-skills-docs` — read-only Haiku doc-lookup agent.

```

- [ ] **Step 3: Verify**

```bash
grep -n "se-claude-skills" /workspaces/ocr-container/CLAUDE.md
```

Expected: at least 3 lines — one in the table, two in the routing section.

---

## Task 8: Commit workspace artifacts to ocr-container

**Files:**
- Modify: `.gitignore` (workspace root — add `/se-claude-skills/`)
- Modify: `.claude/agents/se-claude-skills.md` (stage)
- Modify: `.claude/agents/se-claude-skills-docs.md` (stage)
- Modify: `.claude/agent-memory/se-claude-skills/MEMORY.md` (stage)
- Modify: `CLAUDE.md` (stage)

- [ ] **Step 0: Add se-claude-skills to workspace .gitignore**

In `/workspaces/ocr-container/.gitignore`, find the block:

```
/stay-awake/
```

Add immediately after it:

```
/se-claude-skills/
```

This prevents the workspace repo from seeing `se-claude-skills/` as untracked content — it has its own git history, exactly like all the `/pd-*/` entries.

- [ ] **Step 1: Stage workspace artifacts**

```bash
git -C /workspaces/ocr-container add \
  .gitignore \
  .claude/agents/se-claude-skills.md \
  .claude/agents/se-claude-skills-docs.md \
  .claude/agent-memory/se-claude-skills/MEMORY.md \
  CLAUDE.md
```

- [ ] **Step 2: Commit**

```bash
git -C /workspaces/ocr-container commit -m "$(cat <<'EOF'
chore(workspace): wire se-claude-skills as a pd-* style repo

Adds subagent, docs agent, memory dir, and routing table entry.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: commit hash printed, no error.

- [ ] **Step 3: Verify clean workspace**

```bash
git -C /workspaces/ocr-container status
```

Expected: the new untracked files are only from git repos not under ocr-container tracking.

---

## Task 9: Create private GitHub repo and push

**Files:**
- Modify: `se-claude-skills/.git/config` (add remote origin)

- [ ] **Step 1: Create private GitHub repo**

```bash
gh repo create ConcaveTrillion/se-claude-skills --private --description "Source-first skills framework generating installable plugin artifacts for Claude Code, Gemini, Codex, and other AI coding assistants"
```

Expected: `✓ Created repository ConcaveTrillion/se-claude-skills on GitHub`

- [ ] **Step 2: Add remote to se-claude-skills repo**

```bash
git -C /workspaces/ocr-container/se-claude-skills remote add origin git@github.com:ConcaveTrillion/se-claude-skills.git
```

- [ ] **Step 3: Push main**

```bash
git -C /workspaces/ocr-container/se-claude-skills push -u origin main
```

Expected: `Branch 'main' set up to track remote branch 'main' from 'origin'.`

- [ ] **Step 4: Verify remote**

```bash
gh repo view ConcaveTrillion/se-claude-skills --json name,visibility,url
```

Expected: `"visibility":"PRIVATE"` and the repo URL.
