# Workspace GH label taxonomy

The canonical label vocabulary used across all `ConcaveTrillion/*` repos. Machine-readable form: [`scripts/sync-labels-canon.json`](../scripts/sync-labels-canon.json). Full rationale: [the design spec](../archive/specs/2026-05-17-gh-label-taxonomy-design.md).

---

## Canonical axes

### `kind:*` — what is this issue? (mutually exclusive)

| Label | Meaning | Color | Skills that produce |
|---|---|---|---|
| `kind:feature-request` | Untriaged request; the entry point | `#5d9fdf` (ocr-blue) | filed by user/agent |
| `kind:spec` | Design issue with a spec doc | `#a888d4` (gt-purple) | `/triage` (when approved → spec) |
| `kind:decision` | Architectural decision record; no implementation | `#d6925a` (accent) | `/triage` (when architectural) |
| `kind:feature` | Buildable feature task | `#5fbf6a` (exact-green) | `/decompose-spec`, direct file |
| `kind:bug` | Defect | `#dc6555` (mismatch-red) | direct file |
| `kind:chore` | Maintenance / infra task | `#7a7a85` (ink3-grey) | `/decompose-spec`, direct file |
| `kind:tracking` | Parent issue collecting children; no work of its own | `#e8a83a` (fuzzy-amber) | manual; `/triage` (when `triage:needs-tracking`) |

Exactly one `kind:*` label per issue. Required.

### `status:*` — kanban position (mutually exclusive; defines column order)

| Label | Meaning | Column color | Set by |
|---|---|---|---|
| *(none)* | Unlabeled — needs `/triage` or status assignment | `bgSunk` with `mismatch` left border | n/a |
| `status:backlog` | Accepted, not started | `bgPage` | `/triage`, `/decompose-spec` |
| `status:ready` | Claimed/queued for next session | tint `#5fbf6a1a` | CT (arm for ship-issue) |
| `status:in-progress` | Actively being worked | tint `#e8a83a1a` | `/ship-issue` |
| `status:in-pr` | PR open, awaiting merge | tint `#5d9fdf1a` | `/ship-issue`, bot-merge skills |
| `status:done` | Merged, closed satisfactorily | tint `#5fbf6a1a` (lighter) | merge skill / CT |
| `status:archived` | Closed without delivery (cancelled, superseded) | tint `#7a7a8533` | CT |
| `status:blocked` | Waiting on external dep or decision | tint `#dc65551a` | CT, ship-issue (bounce) |
| `status:bounced` | ship-issue cycle failed; needs human triage | tint `#dc6555` + left border `#e99695` | `/ship-issue` |

`status:in-review` (currently only in `pd-png-optimizer`) is **renamed to `status:in-pr`** for
workspace consistency. Both states are open issues with an open PR.

A `kind:tracking` parent never has a `status:*` label — its rollup status is implicit (open
when any child is open).

### `triage:*` — outcome of `/triage` on a feature-request

| Label | Meaning |
|---|---|
| `triage:approved` | Moved forward; child issue of `kind:feature/bug/chore` filed |
| `triage:needs-spec` | Approved as requiring design; `kind:spec` child filed |
| `triage:needs-tracking` | Needs a tracking parent first |
| `triage:tracking` | Is a tracking parent issue |
| `triage:rejected` | Closed by triage decision |
| `triage:proposed-by-agent` | Child auto-proposed by an agent; needs human confirm |

Applied to feature-request issues (and sometimes children) by the `/triage` skill.
`triage:rejected` issues are hidden from the cost dashboard by default.

### `effort:*` — planning estimate (mutually exclusive)

| Label | Meaning |
|---|---|
| `effort:S` | Under a session |
| `effort:M` | One full session |
| `effort:L` | Multiple sessions |
| `effort:XL` | Spec-sized; should not be a task — decompose first |

Set by `/decompose-spec` and `/spec-from-issue` based on plan-task complexity.

---

## Cross-cutting axes

### `model:*` — which Claude model is right for this work

`model:haiku`, `model:sonnet`, `model:opus`. Set by `/decompose-spec` and `/spec-from-issue`.

### `model-effort:*` — compute budget within the chosen model

`model-effort:low`, `:medium`, `:high`, `:xhigh`, `:max`. Set alongside `model:*`.

### `priority:*` — `priority:low`, `:medium`, `:high`

Optional. Set by CT when needed.

### `area:*` — `area:ci | deps | docs | refactor | tests`

Optional. Set when an issue is meaningfully scoped to one area.

### `recurring:*` — `recurring:weekly | monthly | quarterly`

Marks recurring chore issues that re-fire on cadence.

### `bot:*` — workflow gating

Out of scope for this doc; governed by the bot orchestrator. Informational names:
- `bot:ship-issue-ready` — armed for ship-issue pickup
- `bot:merge-ready` — child of a wip branch ready to merge
- `bot:style-fixed-by-agent`, `bot:style-review-ready`, `bot:style-sweep-ready` — style flow gates
- `bot:blocks-all` — global pause
- `bot:fix-wip` — agent should clean up wip branch
- `bot:paused` — repo-level pause

---

## Repo-local extensions (allowed, not drift)

Some repos have extra labels that serve repo-specific workflows. These coexist with the
canon and are explicitly allowed:

| Repo | Local labels | Purpose |
|---|---|---|
| `pdomain-ocr-labeler-spa` | `hifi:P1 \| hifi:P2 \| hifi:P3 \| hifi:P4 \| hifi:P5` | Hi-fi design priority levels for the FastAPI+React rebuild |
| `pd-png-optimizer` | `backend:claude \| backend:codex \| backend:grok` | Multi-AI-backend planning for the Rust core |

`sync-labels.sh` does not touch these. If a repo adopts a new local extension, document it here.

---

## See also

- [`scripts/sync-labels-canon.json`](../scripts/sync-labels-canon.json) — machine-readable canonical label catalog
- [`docs/archive/specs/2026-05-17-gh-label-taxonomy-design.md`](../archive/specs/2026-05-17-gh-label-taxonomy-design.md) — full rationale, drift reconciliation plan, and `sync-labels.sh` design
