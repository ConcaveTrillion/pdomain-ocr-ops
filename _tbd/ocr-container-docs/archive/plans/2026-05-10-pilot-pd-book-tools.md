---
status: complete
---

# Plan B — Pilot pdomain-book-tools

> **Status**: Active
> **Last updated**: 2026-05-10

## TL;DR

Onboard `pdomain-book-tools` (the foundation library) to the workspace machinery built in Plan A: label discipline, the 9-section spec template, GitHub-issue-driven backlog, and `/ship-issue` end-to-end. Foundation-first piloting: any rough edges shake out where they matter most before downstream repos onboard.

## Context

Plan A built workspace-level scaffolding (hooks, `pd-push`, `bash-command-guard`, `lint-spec`, `seed-labels`, ship-issue scripts, two skills, lockdown). Plan A did not modify any pd-* repo. Plan B is the first pd-* onboarding.

`pdomain-book-tools` was chosen over `pdomain-prep-for-pgdp` (the original Plan A target) because it is the foundation everyone else depends on; getting ship-issue working there exercises the highest-stakes path first.

## Constraints

- **Spec discipline is opt-in via `.specrc:legacy`** — existing docs aren't required to conform on day one. Migration is incremental (Procedure 1 mechanical, Procedure 4 splitting).
- **No breaking changes during the pilot** — pdomain-book-tools is depended on by 6 downstream repos. Pilot work is documentation, label hygiene, test coverage, and small bug fixes only. No API rewrites.
- **Delegate in-repo code/spec changes to the `pdomain-book-tools` agent** — workspace-level glue (label seeding, lint-spec runs from workspace root) is fine here; anything writing files inside `pdomain-book-tools/` goes through the agent per CLAUDE.md routing.
- **Bot-only pilot** — every issue worked by `/ship-issue` must be reviewed via the resulting draft PR before merge. No fast-merge.

## Decision

Seven phases, each landing on a green acceptance check. Stop and reassess between phases.

### Phase B1 — Workspace prep (≈15 min)

- [ ] Run `scripts/seed-labels.sh pdomain/pdomain-book-tools`
- [ ] Verify: `gh label list -R pdomain/pdomain-book-tools` shows all 26 workspace labels (kind/effort/model/model-effort/recurring/status/bot/triage)

### Phase B2 — Spec discipline skeleton (≈1 hour)

Existing pdomain-book-tools docs map roughly to:

| Source | Target |
|---|---|
| `docs/architecture/*.md` (5 files) | `docs/specs/0X-*.md` (decisions) |
| `docs/planning/*-spec.md` (3 files) | `docs/specs/0X-*.md` (specs) |
| `docs/review/{bugs-*,refactors}.md` | GitHub issues (kind:bug / kind:chore) |
| `docs/ROADMAP.md` items | GitHub issues (kind:feature) |
| `TEST_COVERAGE_WORKPLAN.md` items | GitHub issues (kind:chore + bot:ship-issue-ready) |

- [ ] Create `pdomain-book-tools/docs/specs/` (delegate to pdomain-book-tools agent)
- [ ] Move (or copy + delete) the 8 spec-shaped docs into `docs/specs/` with sequence-number prefixes
- [ ] Run `python3 scripts/lint-spec.py --seed-legacy pdomain-book-tools/docs/specs` to populate `.specrc:legacy`
- [ ] Commit (in pdomain-book-tools)

### Phase B3 — Mechanical spec migration (≈1 hour)

For each spec on `.specrc:legacy`:

- [ ] Run `python3 scripts/migrate-legacy-spec-auto.py <path>` (Procedure 1)
- [ ] Run `python3 scripts/lint-spec.py <path>` and confirm all 6 rules pass
- [ ] Remove from `.specrc:legacy`

Some specs may still be over the 800-line cap → those get a chore issue for human-required Procedure 4 splitting (Phase B4).

- [ ] Commit (in pdomain-book-tools)

### Phase B4 — Backlog issue creation (≈2 hours)

- [ ] Walk `docs/ROADMAP.md` → file each item as `kind:feature` issue with effort/model labels (start without `bot:ship-issue-ready`; user arms it manually after triage)
- [ ] Walk `TEST_COVERAGE_WORKPLAN.md` → file each line item as `kind:chore` issue with `effort:S` + `model:haiku` + `model-effort:low` + `bot:ship-issue-ready` (these are mechanical)
- [ ] Walk `docs/review/bugs-*.md` → file as `kind:bug` issues
- [ ] Walk `docs/review/refactors.md` → file as `kind:chore` issues
- [ ] User triages: add `status:ready` to whichever issues they want piloted first

### Phase B5 — First ship-issue cycle (≈1 hour, observation-heavy)

- [ ] Pick the smallest `status:ready` + `bot:ship-issue-ready` issue (likely a TEST_COVERAGE chore)
- [ ] As `claude-bot`: `scripts/ship-issue-orchestrator.sh --repo pdomain/pdomain-book-tools --runs 1`
- [ ] Observe the full cycle: throttle → pick → claim comment → claude -p → success.sh / failure.sh
- [ ] Review the resulting draft PR
- [ ] Document any rough edges in `pdomain-book-tools/CLAUDE.md` and/or workspace memory

### Phase B6 — Multi-cycle stress (≈half-day)

- [ ] Add `bot:ship-issue-ready` to 3-5 more issues spanning kind:bug / kind:chore / kind:feature
- [ ] `--runs 5`
- [ ] Confirm: orchestrator handles success, failure (intentional or organic), and throttle correctly
- [ ] Triage the resulting draft PRs and merge what looks good

### Phase B7 — Pilot debrief

- [ ] Append a section to `docs/superpowers/plans/STATUS.md` with: success rate, known issues, script tweaks made
- [ ] If any workspace script changed during the pilot: tag those commits `[pilot-feedback]` for traceability
- [ ] Decision point: which pd-* repo to onboard next, or pause and harden?

## Contract / Acceptance

Plan B is complete when:

- [ ] All 26 workspace labels exist on `pdomain/pdomain-book-tools`
- [ ] `pdomain-book-tools/docs/specs/` exists with at least 8 specs (any combination of conforming + legacy-allowlisted)
- [ ] `python3 scripts/lint-spec.py pdomain-book-tools/docs/specs/*.md` passes (legacy allowlisted ones warn but don't fail)
- [ ] At least 5 issues filed on `pdomain/pdomain-book-tools` with the workspace label families
- [ ] At least one ship-issue cycle completed end-to-end with a draft PR opened against `wip/ship-issue`
- [ ] At least 3 ship-issue cycles total (B6) with mixed outcomes (success + failure paths exercised)
- [ ] Pilot debrief committed

## Trade-offs considered

| Approach | Pro | Con |
|---|---|---|
| Foundation-first (chosen) | Highest-stakes early; rough edges shake out where they matter | One bad change ripples to 6 repos |
| Pilot a leaf repo (`pdomain-prep-for-pgdp`) | Lower blast radius | Leaf-repo lessons may not generalize back to foundation |
| Skip pilot, onboard all repos in parallel | Fast | One bug in scripts blocks all 7 simultaneously |
| Spec migration in one big bang | Conceptually clean | Days of doc work before any value |
| `.specrc:legacy` allowlist (chosen) | Non-blocking; spec discipline grows incrementally | Tech debt is visible but not forced |

## Consequences

- pdomain-book-tools becomes the canonical example of the workspace pattern. Other agents will reference its docs/specs structure when onboarding their own repos.
- Any workspace script changes during the pilot must be backward-compatible (we have no other onboarded repo yet to break, but Plan A specs must keep passing).
- The `[pilot-feedback]` commit tag becomes a search index for "what we learned in the pilot" when onboarding the second pd-* repo.

## Open questions

- Should `TEST_COVERAGE_WORKPLAN.md` be deleted after issue migration, or kept as a tracking summary? (Lean: keep as a summary index pointing at issues.)
- Should `docs/ROADMAP.md` continue to exist as a curated narrative alongside issues? (Lean: yes — issues are individual; ROADMAP is the story.)
- Does the pilot need its own throttle-check threshold (lower than the default 7-day) so we notice unmerged work faster? (Lean: try default first.)

## References

- `docs/superpowers/plans/2026-05-09-workspace-foundation.md` (Plan A)
- `docs/superpowers/specs/2026-05-09-github-issues-projects-design.md` (parent spec)
- `docs/superpowers/plans/STATUS.md` (rolling status)
- `pdomain-book-tools/CLAUDE.md` (foundation library description)
