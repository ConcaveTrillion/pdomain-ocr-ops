# labeler-spa: header → workspace-toolbar realignment

- **Date:** 2026-06-14
- **Repos:** `pdomain-ocr-labeler-spa` (primary), `pdomain-ui` (upstream primitives)
- **Status:** approved design; implementation plan to follow

## Problem

`pdomain-ocr-labeler-spa` already mounts the pdomain-ui `AppShell`, but its
`header` slot is loaded with document/page-scoped controls that pdomain-ui's
design reserves for the **app body**, not chrome. The local `HeaderBar`
currently injects:

| In header today | What it is | Correct home |
|---|---|---|
| `PageActionsCompact` (actionsSlot) | Save, Export, Reload/Rematch OCR, Undo/Redo, OCR-config trigger, overflow (rotate CW/CCW/180, auto-rotate-all, save-project, bulk-glyphs, rotation badge) | In-body workspace toolbar |
| Theme chips (Dark/Light/System) | Site-wide theme radio | SettingsModal Appearance panel (pdomain-ui owns theme via UIPrefs) |
| Metrics strip | exact/fuzzy/mismatch/validated/glyph counts | Workspace status |
| `ProjectNavigationControls` (navSlot) | Prev / page input / Next / Go | Workspace toolbar |
| `QuickSearch` (searchSlot) | ⌘K worklist filter | Drawer worklist header |

pdomain-ui's documented header layout is chrome-only:
`[icon] [name] [spacer] [headerActions] [LauncherSlot] [SettingsSlot ⚙]`
(`pdomain-ui` shared-settings-modal design). The documented convention for an
in-app document toolbar is the `StageToolbar` primitive
(`leftSlot`/`centerSlot`/`rightSlot`), used elsewhere as `FileToolbar` /
`CropToolbar`.

## End-state layout

Two cleanly separated bars (full-width workspace toolbar band, the approved
layout):

```
┌─ AppShell header (chrome only) ───────────────────────┐
│ [icon] Labeler   ·project/path·       [⚙] [launcher]   │
├─ StudioShell header zone: WorkspaceToolbar (StageToolbar) ─┤
│ ‹ 12/240 › Go │ Save Export OCR↻ ⤺⤻ ⟳ ⋯ │ ✓18 ~4 ✗2  │
├────┬───────────────┬──────────────────────┬───────────┤
│rail│ drawer        │       canvas         │   right   │
│    │ [⌘K search]   │                      │           │
│    │ worklist      │                      │           │
└────┴───────────────┴──────────────────────┴───────────┘
```

- **AppShell header → chrome only.** `[icon] [app name] [project path
  breadcrumb] [spacer] [LauncherSlot] [SettingsSlot ⚙]`. No document-scoped
  controls. Theme chips removed; theme now lives in the ⚙ SettingsModal
  Appearance panel.
- **Workspace `StageToolbar` band** — full width, top of `StudioShell`
  (project route only, so it appears exactly when today's nav/actions do).
  `leftSlot` = page navigation, `centerSlot` = page actions,
  `rightSlot` = metrics status.
- **⌘K search** → Drawer worklist header (it filters the worklist, which lives
  in the drawer). ⌘K focus behavior preserved.

## Component boundaries

- `HeaderBar.tsx` slims to chrome. Loses navSlot / searchSlot / actionsSlot /
  metrics / theme-chips wiring.
- New `WorkspaceToolbar.tsx` wraps pdomain-ui `StageToolbar`; composes nav
  (left), page actions (center), metrics (right). Mounted in `StudioShell`'s
  existing header zone.
- `PageActionsCompact`, `ProjectNavigationControls`, the metrics strip, and
  `QuickSearch` move to their new homes **unchanged in behavior** — only their
  mount point changes. Each unit keeps one clear purpose and a stable testid
  surface, so it can be relocated without touching its internals.

## What lands in pdomain-ui (upstream — gates the rest)

Promote generic, reusable toolbar mechanics out of labeler-spa's local
`PageActionsCompact` into pdomain-ui primitives **only if they don't already
exist in pdomain-ui code** (the relevant pdomain-ui docs are specs, so the
upstream agent must verify code-vs-spec first):

- overflow **DropdownMenu**
- **ButtonGroup** (with separators)
- **IconButton** (icon-only button)

**Decision rule the upstream agent applies per control:** generic toolbar
mechanic → pdomain-ui; labeler domain logic (rotation-badge revert, OCR-config
trigger, bulk-glyph dialog) → stays local. If pdomain-ui already provides these
in code, this slice is a no-op and the pdomain-ui release is skipped.

If a release is needed, it follows the workspace flow (worktree → `make ci`
→ rebase → ff-merge → publish to `pdomain-index-npm`), and labeler-spa bumps to
the new version via `make update-pd-deps` before consuming it.

## Hard constraints

- **D-014 testid preservation.** Every moved control keeps its exact
  `data-testid`; only the mount point changes. The Playwright driver depends on
  these.
- **Theme-chip testids relocate.** `theme-chips`, `theme-chip-dark`,
  `theme-chip-light`, `theme-chip-system` are SPA-new (not legacy-labeler), so
  moving them into the Appearance panel is permitted under D-014's "new
  elements get new testids" clause — but the driver contract and
  `HeaderBar.test.tsx` must be updated and the move recorded as a new decision
  (D-0xx) in `specs/17-decisions.md`. This is surfaced, not silent.
- **Stale docs updated.** `docs/architecture/03-frontend.md` (header contents)
  and `docs/architecture/24-shell-layout.md` (zone layout) describe the
  pre-AppShell layout and are corrected to match the end state.

## Testing

- Each moved component's existing unit test follows it: re-point the render
  harness, assert testids unchanged.
- `HeaderBar.test.tsx` asserts chrome-only (no nav/search/actions/metrics/theme
  testids present in the header).
- New `WorkspaceToolbar.test.tsx` covers slot composition and that all
  page-action testids render in the band.
- Playwright e2e: every page-action testid is reachable in the body; the header
  carries none of them; ⌘K still focuses the (relocated) search; theme is
  changeable via the SettingsModal Appearance panel. Tests must not skip when
  the frontend isn't built (per workspace SPA contract conventions).
- `make ci AI=1` green in every worktree before merge.

## Execution methodology

Upstream-first, then scaffold, then parallel content slices — chosen because
`App.tsx` and `HeaderBar.tsx` are chokepoints; firing every slice at once would
guarantee merge conflicts.

1. **Upstream gate — pdomain-ui primitives.** Add/confirm DropdownMenu /
   ButtonGroup / IconButton; release if needed. labeler-spa bumps to consume.
2. **Scaffold slice (labeler-spa).** Chrome-only `HeaderBar` + empty
   `WorkspaceToolbar` band mounted in `StudioShell` + slot rewiring in
   `App.tsx` + a Drawer worklist-header slot. Establishes stable, non-
   overlapping insertion points.
3. **Parallel content slices (labeler-spa), disjoint file ownership:**
   - page-actions → toolbar `centerSlot`
   - nav → toolbar `leftSlot`
   - metrics → toolbar `rightSlot`
   - ⌘K search → drawer worklist header
   - theme → SettingsModal Appearance panel

Each slice runs in its own worktree under `<repo>/.claude/worktrees/<slug>`.
The orchestrator owns integration: rebase onto local `main`, `git merge
--ff-only` sequentially (no merge commits, no squash). **An Opus review
subagent audits each finished worktree** — correctness, deferred items,
inconsistency, testid integrity — before its merge. No GitHub PRs (workspace
rule). Push only on explicit authorization.
