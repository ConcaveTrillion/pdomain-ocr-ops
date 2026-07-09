# se-claude-skills Workspace Design

**Date:** 2026-05-15
**Status:** Approved

## 1. What We're Building

A Claude Code workspace setup (the "pd-* pattern") for `se-claude-skills` — a source-first skills framework that generates installable plugin artifacts for multiple AI coding assistants (Claude Code, Gemini, Codex, GPT 5.5+).

The framework follows an **Approach B** (source-first with build step) model: skills are authored once in a canonical format under `skills/`, adapter scripts in `adapters/` render model-specific output into `dist/`, and `dist/` is never committed.

## 2. Directory Layout

```
se-claude-skills/
├── CLAUDE.md                  # repo guidance for Claude
├── README.md
├── Makefile                   # build / test / publish targets (stubs until stack chosen)
├── .gitignore
│
├── skills/                    # source skills (canonical, model-agnostic)
│   └── <skill-name>/
│       └── skill.md           # frontmatter: name, description, triggers, models
│
├── adapters/                  # per-model rendering rules / output templates
│   ├── claude.py (or .sh)     # stack TBD
│   ├── gemini.py
│   └── codex.py
│
├── tests/                     # skill validation (lint, render checks)
│
└── dist/                      # build output — gitignored
    ├── claude/                # installable Claude Code plugin
    │   ├── .claude-plugin/plugin.json
    │   ├── skills/
    │   └── CLAUDE.md
    ├── gemini/
    └── codex/
```

`skills/` is the single authoring surface. `adapters/` knows how to render each model's plugin format. `dist/` is always a `make build` output, never committed.

## 3. Claude Workspace Wiring

Five artifacts mirror the pd-* pattern:

### 3a. `se-claude-skills/CLAUDE.md`
Repo-level guidance: what this repo is, the `skills/` → `dist/` build flow, standard Makefile targets, adapter pattern, skill authoring conventions, out-of-scope boundaries.

### 3b. `.claude/agents/se-claude-skills.md`
Full-power subagent. Frontmatter: `name: se-claude-skills`, trigger description matching "se-claude-skills", "cross-model skills framework", "skill authoring for se-claude-skills", "skills plugin generator", or anything under `/workspaces/ocr-container/se-claude-skills/`, `memory: project`. Body: identity + repo path pre-flight check, what the repo is, stack layout, read-first files, standard workflow, out-of-scope.

### 3c. `.claude/agents/se-claude-skills-docs.md`
Read-only Haiku doc-lookup agent. Scoped to `se-claude-skills/` markdown (README, CLAUDE.md, docs/). Returns one-sentence answer + verbatim `path:line` quotes, or `Not found in se-claude-skills docs.` Tools: `Read`, `Glob`, `Grep` only.

### 3d. `.claude/agent-memory/se-claude-skills/MEMORY.md`
Empty index to start. The subagent fills it as it works.

### 3e. Top-level `CLAUDE.md`
New row in the routing table:

| `se-claude-skills/` | Skills framework: source-first, generates model-specific plugin artifacts. |

Plus routing section trigger entry for both agents.

## 4. Initial Project Scaffold

Thin by design — structure without stack commitment:

- **`README.md`** — one-paragraph description, install placeholder.
- **`.gitignore`** — `dist/`, `.venv/`, `node_modules/`, `__pycache__/`, `.claude/`.
- **`Makefile`** — stub targets (`build`, `test`, `ci`, `clean`, `publish`). `ci` calls `build` then `test`. Bodies are `@echo "TODO: ..."` until the stack is decided.
- **`skills/.gitkeep`**, **`adapters/.gitkeep`**, **`tests/.gitkeep`** — reserve directories.

No `pyproject.toml` or `package.json` yet. Stack decision deferred.

## 5. Git + GitHub Setup

- `git init` in `se-claude-skills/`; default branch `main`.
- `.git/config` author: `CT <concavetrillion@gmail.com>` (same as peer pd-* repos).
- Remote `origin`: `git@github.com:ConcaveTrillion/se-claude-skills.git`.
- First commit: scaffold + `CLAUDE.md` + `.gitignore`. Message: `chore: initial scaffold`.
- Create **private** GitHub repo `ConcaveTrillion/se-claude-skills` via `gh repo create`.
- Push `main`.

Workspace-level `.claude/agents/` and agent-memory files go in a separate commit to the **ocr-container** repo, not inside `se-claude-skills`.

## 6. Error Handling / Edge Cases

- `.gitignore` includes `.claude/` to prevent agent-memory leakage into the repo tree (same pattern as all pd-* repos).
- Agent pre-flight check in subagent prompt: abort if `cwd` is not `se-claude-skills/`.
- `dist/` is gitignored to prevent accidentally committing build output.

## 7. Testing

No tests until the stack is chosen. The stub `make test` target exits 0 immediately so `make ci` passes on first run.

## 8. Out of Scope

- Choosing the build-system language (Python vs bash vs Node) — deferred.
- Writing any actual skills — deferred.
- Adapter implementations — deferred.
- `-docs` agent will be thin until docs exist; that's expected.

## 9. Open Questions

None blocking implementation.
