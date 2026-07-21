---
Status: active
Owner: CT
Created: 2026-07-15
Last verified: 2026-07-15
Kind: process
Level: I1
---

# Issues

## Agent Index

- **Kind:** process
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-15
- **Read when:** filing a bug / defect / investigation report, or looking up an
  open issue's status, evidence, or resolution.
- **Search terms:** issues folder, bug report, defect report, issue template,
  issue lifecycle, kind issue.

## Purpose

`docs/issues/` is the canonical tracker for bounded work: bugs, regressions,
investigations, features, chores, and documentation work. GitHub Issues is not
authoritative for this repository. Each report is an evidence-bearing docgraph
node, so work remains retrievable, reviewable, and versioned with the code.

## Convention

- **Location:** `docs/issues/`
- **Filename:** `YYYY-MM-DD-short-slug.md` (creation date + a terse kebab slug).
- **Metadata:** YAML frontmatter **and** a matching `## Agent Index` block. Keep
  frontmatter `Status:` and Agent Index `Status:` identical — a mismatch trips a
  `field_conflict` (→ `status-reconciler`).
  - `Kind: issue`
  - `Level:` informational scope — `I1` repo-wide, `I2` narrow/local.
  - `Status:` governed lifecycle, **not** the issue's open/closed state (see below).
  - `Issue type:` one of `Bug`, `Regression`, `Investigation`, `Feature`,
    `Chore`, or `Docs`.
  - `Priority:` one of `P0`, `P1`, `P2`, or `P3`, from urgent to low.
  - `Area:` a stable repository component or `Cross-cutting`.
  - `Triage:` one of `Accepted`, `Needs evidence`, or `Deferred` while the issue
    is open. Rejected or duplicate work uses the matching `Resolution` value.
  - `Parent`, `Children`, `Blocked by`, and `Blocks:` relative Markdown links,
    or `None`. Keep each dependency direction consistent in both reports.
- **Issue state vs governed status:** the docgraph lifecycle is
  `draft → active → implemented → retired`. Express the *issue's* resolution state
  as a separate **`Resolution:`** line in the Agent Index (`Open` / `Resolved` /
  `Won't fix` / `Duplicate`) and a final `## Resolution` section. Map the governed
  `Status:`:
  - **Open** → `Status: active`.
  - **Resolved / Won't fix / Duplicate** → `Status: retired`, routed through
    `doc-retirer`, with the resolving commit/spec linked in `## Resolution`.
  - A `Won't fix` or `Duplicate` decision changes `Resolution` immediately;
    it cannot remain an open triage state.
- **Index it (no orphans):** add every issue to the open or resolved list in
  this README. This is the sole issue index. Context docs link here or to a
  specific issue only when the work changes current state or durable intent.
- **Stage + reindex:** under `mode = "git"` a new doc is invisible until
  `git add`ed; stage it, then `docgraph reindex` and `docgraph check --strict` the
  same turn (a new `dangling` blocks completion).
- **Template:** copy `TEMPLATE.md` in this folder. It is index-excluded (a
  top-of-file `<!-- docgraph: ignore -->` marker), so **do not markdown-link to
  it** from a governed doc — the link would dangle. Refer to it by path / inline
  code.

## Recommended structure

Every issue contains Summary, Outcome / acceptance criteria, Evidence /
motivation, Dependencies, Next steps, and Resolution. Bugs and regressions also
record environment, reproduction, ranked root-cause hypotheses, defects to fix,
and what is not broken.

Lead with the **smallest decisive evidence** and separate **observation** from
**hypothesis**. Bugs and regressions always include a **What is NOT broken**
section.

## Open issues

- *None yet.*

## Resolved issues

- *None yet.*
