# Handoff — Behavior-Driven E2E pilot (pdomain-ocr-simple-gui)

Paste the block below into a fresh Claude Code session (started in
`/workspaces/ocr-container`) to execute the plan. Everything it needs is
referenced by absolute path.

---

```
We are executing a pre-written implementation plan. Do NOT redesign — the
design and plan are already approved. Read these three source-of-truth docs
first, in order, then begin:

1. METHODOLOGY (workspace, reusable):
   /workspaces/ocr-container/docs/process/behavior-e2e-capture.md
2. TEMPLATES:
   /workspaces/ocr-container/docs/templates/behavior-unit-spec.md
   /workspaces/ocr-container/docs/templates/behavior-flows.md
3. THE PLAN TO EXECUTE (per-task, TDD, checkboxes):
   /workspaces/ocr-container/pdomain-ocr-simple-gui/docs/plans/2026-05-29-behavior-e2e-pilot.md

GOAL: stand up behavior-driven E2E in pdomain-ocr-simple-gui (the Web/GUI
pilot) — per-screen behavior specs with split observable-output + backend
assertions, two test tiers (A: fake dispatcher in CI; B: real OCR engine on
the GPU, opt-in), and an ID-traceable generated coverage gate. The existing
tests/e2e/ Playwright + fake-dispatcher harness, testids, make targets and
CI already exist; the plan's "What already exists" section lists them — do
not rebuild them.

CURRENT STATE (as of 2026-05-29):
- Design + plan + templates are written and self-reviewed. NOTHING is
  implemented yet. Everything is UNCOMMITTED on branch tests/audit-reorg.
- No behavior records, no coverage script, no Tier-B harness yet.

USE THE SKILL: invoke superpowers:executing-plans (or
superpowers:subagent-driven-development) and work the plan task-by-task,
checking boxes as you go.

EXECUTION APPROACH (recommended hybrid):
- M0–M2 and M8 are fully concrete infra → do these first. Per workspace
  rules, make code edits via the `pdomain-ocr-simple-gui` agent with
  isolation:"worktree" (or set up one worktree yourself under
  pdomain-ocr-simple-gui/.claude/worktrees/<slug> and work there).
- M3–M7 are INTERVIEW-GATED: they require the maintainer (CT) live. For
  each screen: agent inventories + drafts proposed behavior records, then
  CT confirms/corrects intent, edge cases, and known regressions before
  any test is written. Do NOT invent behavior — ask CT.

HARD CONSTRAINTS (from /workspaces/ocr-container/CLAUDE.md + memory):
- NEVER open GitHub PRs (no `gh pr create`). Interactive merge workflow is
  worktree → make ci AI=1 → local merge --no-ff into main → push only when
  CT authorizes. pd-* repos disallow squash.
- Per-task commits ON THE WORKTREE BRANCH are expected (the plan has commit
  steps). Do NOT push or merge to main without CT's explicit OK.
- Always `uv run …` (never bare python3). Use Read (never cat/tail).
- Deliver complete, working features — no stubs / deferred parts / silent
  scope-downs. Verify by RUNNING (make e2e-fast / make ci), not just green
  unit tests.
- Tier B uses the LOCAL GPU. If CT pastes sensor output or names a CPU core
  ≥90°C, pause CPU-heavy work (gh/git/reads/edits stay fine).
- Follow the workspace "Before coding" checklist in CLAUDE.md (git status
  first, read repo CLAUDE.md/CONVENTIONS.md, Explore before broad reads).

START HERE:
1. `git -C /workspaces/ocr-container/pdomain-ocr-simple-gui status --short`
   — surface any stray state before building.
2. Read the three docs above.
3. Set up the worktree, then begin Plan Milestone 0 (scaffold) → M1
   (coverage script + gate) → M2 (Tier-B harness).
4. Pause and interview CT before starting M3 (HomePage).
```

---

## Notes for CT (not part of the prompt)

- The plan flags two things to confirm during execution: the exact sidecar
  filename (assumed `page_0000.json` — verify against `storage.py`) and the
  exact `data-testid` keys (verify against `frontend/src/lib/testids.ts`).
- If you want the plan's tasks tracked as GH issues, run
  `/decompose-spec --sync pdomain-ocr-simple-gui/docs/plans/2026-05-29-behavior-e2e-pilot.md`
  (per-repo plan → simple-gui's own tracker).
- Memory entry `behavior-e2e-methodology` records this initiative for future
  sessions.
