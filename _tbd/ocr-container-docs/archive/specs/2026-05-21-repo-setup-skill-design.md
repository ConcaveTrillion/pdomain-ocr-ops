# repo-setup skill — design

**Date:** 2026-05-21
**Status:** Approved (brainstorm) — pending implementation plan

## 1. Problem

The `ocr-container` workspace has 12+ repos that are supposed to share a
common shape: a `kind:*`/`status:*`/`triage:*`/`effort:*` GH label taxonomy,
a standard `docs/` folder template, synced workspace `CONVENTIONS.md` /
`CLAUDE.md` process blocks, and baseline hygiene files (`.gitignore` with a
`.claude/` entry, `mise.toml`, `docs/conventions/lint-deviations.md`).

The pieces to enforce this already exist as scripts — `sync-labels.sh`,
`scaffold-docs.sh`, `sync-workspace-blocks.py` — but:

- Each script keeps **its own repo list**, which drifts. The label-sync
  canon (`sync-labels-canon.json` `.repos[]`) was missing `pdomain-ocr-training`,
  `pdomain-ocr-simple-gui`, `pdomain-ui`, and `se-llm-skills` — so those three repos
  never received the `kind:*` taxonomy at all (discovered 2026-05-21 while
  filing per-repo lint-deviation chores).
- There is no single entry point that audits a repo across all dimensions
  and reports/repairs drift.

## 2. Goal

A single idempotent **`repo-setup`** skill that audits the workspace repos
across four dimensions and applies safe fixes. Safe to run any time;
re-running only changes what has drifted.

Non-goals: bootstrapping a brand-new repo from scratch (`git init`, remote
creation). The workspace's 12 repos already exist; new-repo creation is rare
and out of scope for this skill.

## 3. Single source of truth — `scripts/workspace-repos.json`

A new manifest, the one place a repo is declared:

```json
[
  { "name": "pdomain-book-tools",      "lang": ["python"],         "status": "reference" },
  { "name": "pdomain-ocr-cli",         "lang": ["python"],         "status": "active" },
  { "name": "pd-ocr-labeler",     "lang": ["python"],         "status": "active" },
  { "name": "pdomain-ocr-labeler-spa", "lang": ["python", "ts"],   "status": "active" },
  { "name": "pdomain-ops",         "lang": ["python"],         "status": "active" },
  { "name": "pdomain-ocr-simple-gui",  "lang": ["python", "ts"],   "status": "active" },
  { "name": "pdomain-ocr-synth",       "lang": ["python"],         "status": "active" },
  { "name": "pd-ocr-trainer",     "lang": ["python"],         "status": "retiring" },
  { "name": "pdomain-ocr-training",    "lang": ["python"],         "status": "active" },
  { "name": "pd-png-optimizer",   "lang": ["rust", "python"], "status": "active" },
  { "name": "pdomain-prep-for-pgdp",   "lang": ["python", "ts"],   "status": "active" },
  { "name": "pdomain-ui",              "lang": ["ts"],             "status": "active" },
  { "name": "se-llm-skills",      "lang": ["python"],         "status": "active" },
  { "name": "ocr-container-meta", "lang": [],                 "status": "active" }
]
```

Field semantics:

- `lang` — **array**; a repo can be multi-language. FastAPI+React SPAs are
  `["python", "ts"]`; `pd-png-optimizer` is `["rust", "python"]` (PyO3
  facade). A repo "has a frontend" iff `"ts"` is in `lang` — no separate
  `has_frontend` field.
- `status` — one of:
  - `active` — full audit + fix.
  - `reference` — `pdomain-book-tools`; the canonical implementation, audit
    skipped (it defines the standard).
  - `retiring` — `pd-ocr-trainer`; warn-only, no fixes (being deleted per
    spec #267).
  - `spec-only` — repo declared but not yet bootstrapped; skipped with a
    note. (Currently none — `pdomain-ui` is bootstrapped.)

`sync-labels.sh` and the skill both read `repos[]` from this manifest
instead of their own copies. `sync-labels-canon.json` retains **only** the
label catalog (`labels[]`, `renames[]`, `local_extensions{}`); its `repos[]`
key is removed. `scaffold-docs.sh` and `sync-workspace-blocks.py` already
operate per-repo-path — the skill drives the loop over the manifest for
them.

## 4. The skill — `.claude/skills/repo-setup/SKILL.md`

Invocation:

- `/repo-setup` — audit every manifest repo.
- `/repo-setup <repo>` — audit one repo (basename, no org prefix).
- `--check` (default) — report drift only, no writes.
- `--fix` — apply safe fixes.

Behavior per repo (skipping `reference`, warn-only for `retiring`):
run the four dimension checks, accumulate a drift table, and — under
`--fix` — apply the safe fixes. Large script output is delegated to a
subagent; only a per-repo pass/drift summary returns to the parent context
(matches `workspace-cleanup` / `check-ci-failures` conventions).

### Dimensions

| Dimension | Tool wrapped | Auto-fix under `--fix`? |
|-----------|--------------|-------------------------|
| Label taxonomy | `sync-labels.sh --repo <name>` | yes |
| `docs/` template | `scaffold-docs.sh <path>` (`--check` / create) | yes |
| CONVENTIONS / process blocks | `sync-workspace-blocks.py` | yes |
| Repo hygiene | new `repo-hygiene-check.sh <path>` | partial (see §5) |

## 5. New script — `scripts/repo-hygiene-check.sh`

`repo-hygiene-check.sh <repo-path> [--check|--fix] [--lang <l>,<l>]`

Lang-agnostic checks (all repos):

- `.gitignore` contains a `.claude/` entry — **auto-fix**: append it.
- `mise.toml` present — **check-only** (contents are repo-specific; report
  if absent).
- `docs/conventions/lint-deviations.md` present — **check-only** (presence
  only; content work is tracked by the per-repo lint-deviation chores filed
  2026-05-21, not this skill).
- GH `allow_squash_merge=false` — **check-only**, no auto-fix (a one-time
  `gh api` repo-settings write, already applied workspace-wide 2026-05-11;
  flagged only if it has regressed).

Lang-additive checks (applied once per `lang` entry):

- `python` — `[tool.ruff]` present in `pyproject.toml`.
- `ts` — `.npmrc` contains a `store-dir=~/...` line (pnpm store location).
- `rust` — clippy config present (`[lints.clippy]` in `Cargo.toml` or a
  `clippy.toml`).

A `["python","ts"]` repo runs both the Python and the TS lang checks.

## 6. Data flow

```
/repo-setup [<repo>] [--check|--fix]
        │
        ├── read scripts/workspace-repos.json  ← single source of truth
        │
        └── for each in-scope repo:
              ├── sync-labels.sh --repo <name> [--dry-run]
              ├── scaffold-docs.sh <path> [--check]
              ├── sync-workspace-blocks.py [--check] <path>
              └── repo-hygiene-check.sh <path> [--check|--fix] --lang …
                     │
                     └── per-repo drift summary → parent context
```

## 7. Error handling

- Manifest missing/malformed → skill aborts with a clear message before
  touching any repo.
- A repo dir absent on disk but present in the manifest → reported as an
  error row; the loop continues to other repos.
- `gh` unauthenticated → label + merge-setting checks degrade to
  report-only (mirrors `sync-labels.sh`'s existing fallback); other
  dimensions still run.
- Any single dimension failing for a repo does not abort the run — it is
  recorded and the loop continues, exit code non-zero at the end.

## 8. Testing

- `repo-hygiene-check.sh` — fixture repo dirs under `tmp` exercising each
  pass/fail/fix path; assert `--check` is read-only and `--fix` is
  idempotent (second run is a no-op).
- Manifest schema — a small validator (lang values ∈ enum, status ∈ enum,
  name unique).
- `sync-labels.sh` reading `repos[]` from the new manifest — assert it
  errors cleanly if the manifest is absent, and that `--repo` still works
  standalone.
- Skill-level: a `--check` dry run against the real workspace must make no
  writes (verified via `git status` before/after).

## 9. Open questions

None blocking. Future (not this skill): a `new-repo` bootstrap mode could
be added later as a separate invocation path if the workspace ever creates
repos frequently.
