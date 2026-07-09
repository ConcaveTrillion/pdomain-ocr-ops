# Design: pdomain-prep-for-pgdp Bot Wiring + Issue Taxonomy

**Date:** 2026-05-11  
**Scope:** Enroll pdomain-prep-for-pgdp in the ship-issue/style-review/style-sweep/decompose-spec bot
suite; sync cross-repo label gaps; file the full roadmap issue set so bots can
schedule delivery.

---

## 1. Goal

pdomain-prep-for-pgdp has no bot tasks in ctask and its two open GitHub issues are
unlabeled. The roadmap (docs/08-roadmap.md) carries M2 queued slices and M3–M6
milestones that are not yet tracked as GitHub issues. This design closes all
three gaps so the standard bot automation loop applies to pdomain-prep-for-pgdp.

---

## 2. Label sync (cross-repo)

Three repos are enrolled in ship-issue/decompose-spec. Each has label gaps:

| Label                 | pdomain-book-tools | pdomain-ocr-labeler-spa | pdomain-prep-for-pgdp |
|-----------------------|:---:|:---:|:---:|
| `bot:ship-issue-ready`| **missing** | ✓ | ✓ |
| `status:ready`        | ✓ | **missing** | **missing** |
| `status:in-progress`  | ✓ | **missing** | **missing** |
| `status:bounced`      | — | — | — (adding now) |
| `kind:feature-request`| **missing** | ✓ | ✓ |

**Actions per repo:**

- **pdomain-book-tools:** add `bot:ship-issue-ready` (#0e8a16 "Bot-eligibility gate —
  ship-issue may modify this issue") and `kind:feature-request` (#c5def5 "Idea
  pre-triage; will fork a tracking or spec issue") and `status:bounced`.
- **pdomain-ocr-labeler-spa:** add `status:ready` (#0e8a16 "Workflow: queued for
  ship-issue (with bot:ship-issue-ready) or you"), `status:in-progress` (#fbca04
  "Workflow: currently being worked on"), `status:bounced`.
- **pdomain-prep-for-pgdp:** add `status:ready`, `status:in-progress`, `status:bounced`.

`status:bounced` color and description: #e4e669 "Workflow: bot could not ship —
needs human triage".

All via `gh label create --repo <owner/repo> --name <name> --color <hex>
--description <desc> --force`.

---

## 3. ctask wiring

Five new tasks. All follow the pattern of existing entries (sudo -u claude-bot,
env -u GH_TOKEN, orchestrator script).

| Task name | Interval (s) | Script | Extra args |
|---|---|---|---|
| `ship-issue-pdomain-prep-for-pgdp` | 1800 | `ship-issue-orchestrator.sh` | `--repo pdomain/pdomain-prep-for-pgdp --runs 1` |
| `style-review-pdomain-prep-for-pgdp` | 86400 | `style-review-orchestrator.sh` | `--repo pdomain/pdomain-prep-for-pgdp` |
| `style-sweep-pdomain-prep-for-pgdp` | 604800 | `style-sweep-orchestrator.sh` | `--repo pdomain/pdomain-prep-for-pgdp` |
| `decompose-spec-pdomain-prep-for-pgdp` | 604800 | `decompose-spec-auto-orchestrator.sh` | `--repo pdomain/pdomain-prep-for-pgdp --model sonnet` |
| `decompose-spec-pdomain-book-tools` | 604800 | `decompose-spec-auto-orchestrator.sh` | `--repo pdomain/pdomain-book-tools --model sonnet` |

Each: `ctask add <name> --interval <secs> --dir /workspaces/ocr-container --prompt "sudo -u claude-bot bash -c 'env -u GH_TOKEN /workspaces/ocr-container/scripts/<script> <args>'"` then `ctask start <name>`.

---

## 4. Issue taxonomy

The workspace uses a 3-level hierarchy; no `kind:plan` layer:

```
kind:feature-request  →  triage skill  →  kind:spec or kind:feature (tracking)
kind:spec             →  /spec-from-issue + decompose-spec bot  →  kind:feature issues (milestone)
kind:feature          →  ship-issue bot  →  merged
kind:chore            →  ship-issue bot  →  merged
```

GitHub milestones serve as the plan-level grouping unit (created by decompose-spec).
`kind:plan` is explicitly out of scope.

All new issues start `status:backlog`. An issue becomes bot-eligible only when CT
manually applies `status:ready` + `bot:ship-issue-ready`.

---

## 5. Issue filing plan — pdomain-prep-for-pgdp

### 5a. Triage existing open issues (gh issue edit)

| # | Title | Labels to add |
|---|---|---|
| 1 | Tighten requires-python upper bound to <3.14 | `kind:chore` `effort:S` `model:haiku` `model-effort:low` `status:backlog` |
| 2 | Use oxipng (via pyoxipng) for PNG optimization | `kind:feature` `effort:M` `model:sonnet` `model-effort:medium` `status:backlog` |

### 5b. New — M2 carry-forward queued slices (kind:feature)

| Title | Labels |
|---|---|
| Pipeline: bounded deferred-write executor (Q8) | `kind:feature` `effort:M` `model:sonnet` `model-effort:medium` `status:backlog` |
| Pipeline: ResolvedPageConfig plumbing into stage runner | `kind:feature` `effort:M` `model:sonnet` `model-effort:medium` `status:backlog` |
| Pipeline: `?async=true` flag on stage run route | `kind:feature` `effort:S` `model:sonnet` `model-effort:low` `status:backlog` |
| Pipeline: real impls for `blank_proof_synth` + `auto_detect_attrs` | `kind:feature` `effort:S` `model:sonnet` `model-effort:medium` `status:backlog` |

Body for each includes a Spec: pointer to `docs/specs/pipeline-task-model.md`
and the relevant roadmap section from `docs/08-roadmap.md §M2`.

### 5c. New — Milestones needing spec first (kind:spec)

No `bot:ship-issue-ready` at filing time; CT adds it after writing the spec via
`/spec-from-issue`.

| Title | Labels |
|---|---|
| Spec: M3 workbench artifact viewer + stage controls panel | `kind:spec` `model:sonnet` `model-effort:high` `status:backlog` |
| Spec: M4 lazy migration of existing projects + disk-cost UI | `kind:spec` `model:sonnet` `model-effort:medium` `status:backlog` |
| Spec: M5 project-level fan-out + `awaiting_review` gate | `kind:spec` `model:sonnet` `model-effort:high` `status:backlog` |
| Spec: undo/soft-delete strategy for word-delete editor (P1 #9a) | `kind:spec` `model:sonnet` `model-effort:medium` `status:backlog` |
| Spec: Konva rotate/flip (P2 #10) | `kind:spec` `model:sonnet` `model-effort:medium` `status:backlog` |
| Spec: search across pages (P2 #13) | `kind:spec` `model:sonnet` `model-effort:high` `status:backlog` |

Body for each includes a Spec-file: line pointing to where the spec will live
once written, and a summary drawn from the roadmap description.

### 5d. New — Well-defined cleanup (kind:chore)

| Title | Labels |
|---|---|
| M6: remove `batch_*` job types, `LocalBackend`, `process_page_cpu` monolith | `kind:chore` `effort:M` `model:sonnet` `model-effort:medium` `status:backlog` |
| P2 #13a: remaining shadcn/ui Radix primitive swaps (Tabs, Select, Popover, Tooltip) | `kind:chore` `effort:S` `model:haiku` `model-effort:low` `status:backlog` |

---

## 6. Execution — 5 parallel agents

All agents are independent; none share state. Label sync and issue filing can run
simultaneously because all issues land as `status:backlog` (which already exists
on the repo).

| Agent | Responsibility |
|---|---|
| **A — Label sync** | `gh label create --force` for all gaps across 3 repos |
| **B — ctask wiring** | `ctask add` + `ctask start` for all 5 new tasks |
| **C — Triage existing** | `gh issue edit` on #1 and #2 only |
| **D — M2 feature issues** | `gh issue create` for 4 kind:feature issues (§5b) |
| **E — Spec + chore issues** | `gh issue create` for 6 kind:spec + 2 kind:chore issues (§5c–d) |

---

## 7. Out of scope

- `kind:plan` issue type — milestones serve this role.
- Bot enrollment for pdomain-ocr-cli, pd-ocr-labeler, pdomain-ocr-synth, pd-ocr-trainer,
  pd-png-optimizer — not requested; revisit when those repos need automation.
- Promoting any issue to `status:ready` — CT does this manually.
- Writing spec documents — CT uses `/spec-from-issue` interactively after filing.
