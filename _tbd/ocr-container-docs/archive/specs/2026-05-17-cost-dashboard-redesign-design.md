# Cost dashboard redesign — tabbed shell, In Progress tab, design-language theme

**Date:** 2026-05-17
**Session:** `cost-dashboard-redesign`
**Scope:** Workspace-level. Restructures `cost-dashboard/` and the generated
`cost-dashboard.html` artifact.

**Depends on:** [2026-05-17-gh-label-taxonomy-design.md](2026-05-17-gh-label-taxonomy-design.md)
— this spec uses `scripts/sync-labels-canon.json` as the single source of truth for column
names, chip colors, and filter axes. The taxonomy spec must ship its Slice 1 (canon JSON +
doc) before Slice 2 of this spec can begin.

**Consumes:** [`docs/design-system/DESIGN_LANGUAGE.md`](../../design-system/DESIGN_LANGUAGE.md)
— this dashboard adopts those tokens and primitives.

---

## 1. Goals & non-goals

### Goals

1. Add an **In Progress** tab as a focused, milestone-grouped view of all active work
   (`status:in-progress + status:in-pr`).
2. Restructure the dashboard from one long scroll into a **4-tab shell**: Overview, In Progress,
   Spec Chain, Spend.
3. Adopt the workspace design language (dark default, light toggle, token-based) so the
   dashboard visually matches `pdomain-ocr-labeler-spa` and `pdomain-prep-for-pgdp`.
4. Restructure every panel from raw `<table>` to **card surfaces** using the design system's
   primitives (cards, chips, status pips, accordions).
5. Make the **kanban panel comprehensive**: pull every open issue (not just status-labeled
   ones) into a leading `unlabeled` column, plus add frontend filters for repo / kind / effort
   / title search.
6. Keep the output a single self-contained HTML file viewable via `file://`.
7. Keep `DASHBOARD_SKIP_KANBAN=1` and `DASHBOARD_SKIP_CHAIN=1` graceful-degrade behaviors.

### Non-goals

1. No server-side rendering or web server — the dashboard remains a static HTML artifact
   regenerated on demand by the existing build script.
2. No new data sources beyond what `build-cost-dashboard.py` already loads. The new In
   Progress tab is a reshape of kanban + chain-state data, not a new gh query budget.
3. No font bundling — system fonts only. Inter via system fallback, monospace via
   `ui-monospace`. Branding fidelity is sacrificed for offline reliability.
4. No persistence beyond `localStorage` (theme choice + kanban filter state).
5. No interactive editing or write-back to GH from the dashboard. Read-only artifact.
6. No bundled JS framework. Vanilla JS, ~50 lines total.

---

## 2. Architecture

```
cost-dashboard/
  build-cost-dashboard.py    # entry point; loads data, orchestrates renders, writes final HTML
  render.py                  # NEW — tiny template loader + slot substitutor
  taxonomy.py                # NEW — loads scripts/sync-labels-canon.json; exposes lookup helpers
  spec_chain_data.py         # EXISTING — unchanged
  spec_slug.py               # EXISTING — unchanged
  templates/
    dashboard.html           # shell — slots: {{tab_nav}}, {{tab_panels}}, {{rebase_alerts}}, etc.
    tabs/
      overview.html
      in-progress.html
      spec-chain.html
      spend.html
    partials/
      kpi-tile.html          # one KPI tile
      milestone-group.html   # one milestone group (in-progress tab)
      issue-row.html         # one issue row inside a milestone group
      kanban-card.html       # one kanban issue card
      sessions-row.html      # one row in the sessions table
      run-row.html           # one row in the recent-runs table
      denial-row.html        # one row in the denials table
      source-row.html        # one row in the source-aggregates panel
      spend-day.html         # one day in the 14-day spend history bar chart
  static/
    tokens.css               # :root (dark) + [data-theme=light] custom-property blocks
    dashboard.css            # primitives + layout (cards, chips, tables, tabs, KPI tiles)
    tabs.js                  # tab switching, hash routing, theme toggle, kanban filtering
  tests/
    test_render.py
    test_taxonomy.py
    test_panels.py
    test_smoke.py
    fixtures/
      runs.jsonl
      sidecar.json
      kanban-sample.json
      chain-state.json
```

### Build pipeline

`build-cost-dashboard.main()`:

1. Load `taxonomy.py.canon()` once. Drives column order, chip color maps, filter chips.
2. Load all data sources (runs.jsonl, sidecar, kanban, chain states, drift files, claude
   sessions, rebase alerts, style-bot events, permission denials, sync-drift, sibling-drift).
   No new data sources vs. today.
3. For each tab, render its template fragment by calling per-panel renderers that emit
   token-styled HTML from the partials.
4. Render `dashboard.html` with the tab fragments substituted in, plus inlined contents of
   `static/tokens.css`, `static/dashboard.css`, `static/tabs.js` (so the artifact is
   single-file portable).
5. Write to `$SHIP_ISSUE_MEMORY_DIR/cost-dashboard.html` (location unchanged).

### Template engine

`render.py` is ~30 lines. `load_template(name)` reads from `templates/`. `render(tpl, **slots)`
does a single regex pass: `{{slot_name}}` is replaced by `slots["slot_name"]` (HTML-escaped
unless the slot key ends in `_html`). Unbound slots raise `KeyError` loudly; the caller wraps
each panel in a `try/except` that emits a visible `<pre class="panel-error">` block so the
dashboard always lands.

No Jinja, no Mako, no f-string brace-hell. Re-readable by a human five lines at a time.

---

## 3. Tab shell

### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│ ship-issue cost dashboard       Generated 2026-05-17T15:00:00Z    ☀☾  │
├────────────────────────────────────────────────────────────────────────┤
│ [Bots paused — rebase conflict in pd-png-optimizer]   (red banner)     │
├────────────────────────────────────────────────────────────────────────┤
│ Overview   In Progress (7)   Spec Chain   Spend                        │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  (active tab content)                                                  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

- **Header bar:** title, generated-at timestamp (`ink3 mono`), theme toggle (sun/moon glyph,
  `.icon` button at right). `bgPage` background, `border1` bottom.
- **Rebase-alerts banner:** appears above the tab nav when any `bots-paused.*` flag file
  exists. Workspace-wide alert, not a tab.
- **Tab nav:** underline tabs per design language. Active tab gets `accent` 2-px underline +
  `ink1` label. Count badge in `accent + '33'` background (`accent` text) for tabs that carry
  a count.
- **Tab body:** standard 16-px padding, cards stack vertically with 14-px gap.

### Hash routing

URL hash drives the active tab:
- `#overview` (default) — Overview
- `#in-progress` — In Progress
- `#spec-chain` — Spec Chain
- `#spend` — Spend

`tabs.js` listens for `hashchange` and on initial load. Clicking a tab updates the hash;
back/forward navigation works.

### Theme toggle

`tabs.js` boot logic:

```js
const stored = localStorage.getItem('cost-dashboard-theme');
const initial = stored || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
document.documentElement.setAttribute('data-theme', initial);
```

Toggle button flips `data-theme` and writes `localStorage.setItem('cost-dashboard-theme',
next)`. Storage key namespaced to not collide with sister apps on the same origin.

First-paint flash: tolerated. `:root` is dark; if user prefers light, brief flash before JS
runs. Acceptable per design doc ("Theme swap: instant, no fade — flicker is worse").

---

## 4. Overview tab (`#overview`)

The default tab — "is anything wrong / what's the load."

### Layout — three rows, full width

**Row 1 — KPI strip** (4 tiles, grid)
- `Plan usage (5h)` — large `mono` % + small mini-bar; sidecar-age chip
- `Plan usage (7d)` — same
- `API cost, last 30d` — `$X.XX` in 24-px Inter / 700
- `Runs, last 30d` — count

Each tile is `bgSurface` + `border1` + 5-px radius. Uses `partials/kpi-tile.html`.

**Row 2 — Bounced triage card** (full-width)
- Header: "Needs triage"
- Body: if `kanban.status:bounced` is empty for all repos → "All clear" in `--exact` green,
  centered. Otherwise, one row per repo with bounced issues; repo name in `mismatch`,
  issue links inline. Ports today's `render_bounced_triage_panel` to token styling.

**Row 3 — In-progress summary card** (full-width)
- Header: "Currently in progress"
- Body: total count + per-repo chip list (`repo-chip + count`).
- "View all →" link at right, `accent` color, target `#in-progress`.

---

## 5. In Progress tab (`#in-progress`)

The new feature. Milestone-first grouping.

### Data scope

All open issues across the 9 repos where `status ∈ {in-progress, in-pr, in-review}`.
The third (`status:in-review`) only matters during the taxonomy-spec migration window; it
gets renamed to `in-pr` once Slice 3 of the taxonomy spec lands. Hidden if `triage:rejected`.
Tab count badge = total such issues.

### Layout — milestone-grouped cards

Each milestone group is a `bgSurface` card (`border1`, 6-px radius, 14-px padding):

**Header row:**
- Milestone title in `mono` (`spec: <slug> (#N)` if present, else "Unassigned")
- Repo chip on the right (taxonomy color `ink3` on `bgRaised`)
- Progress bar (`--exact` fill) + `closed/total` text, right-aligned

**Children:** one row per issue (`partials/issue-row.html`):
- Issue number in `mono ink3`, linked to GH
- Title in `ink1`, truncated by CSS at container width
- Right-aligned chip group:
  - `effort:S/M/L/XL` chip (color from taxonomy: `--fuzzy` amber tint)
  - `kind:*` chip (color from taxonomy)
  - `model:*` chip (color: opus=accent, sonnet=ocr, haiku=gt)
  - `triage:*` indicator dot if non-default (e.g., `triage:proposed-by-agent` → small accent dot)
  - `priority:*` indicator (priority:high → leading `mismatch` dot before title)

### Ordering

1. **Unassigned group first** (no parent milestone). These need attention; they slipped out
   of a milestone or never landed in one.
2. Then milestone groups by **progress descending** (closest-to-done first).
3. Within a group, issues by **number ascending**.

### Empty state

"No work in progress." in `ink3`, centered, 60-vh min-height. Reads as good news.

### Data path

- Filter `kanban_data` (already loaded by `build-cost-dashboard.py`) to status union.
- Join each issue to its parent milestone using `RepoChainState.feature_requests[].spec_issues[].milestone`.
  Match by milestone number.
- Compute progress: GH milestone `closed_issues / (open_issues + closed_issues)`.
- Orphans: issues whose milestone is `None` or unknown → "Unassigned" group.

---

## 6. Spec Chain tab (`#spec-chain`)

Cross-repo work-board + chain-state + style-bot events + drift, all on one tab.

### Section 6a — Kanban (revised)

**Data change:** `load_kanban_data()` now keeps **every open issue**, not just status-labeled
ones. Columns derive from the canon:

```
unlabeled | backlog | ready | in-progress | in-pr | done | archived | blocked | bounced
```

`unlabeled` is a leading column for issues with no `status:*` label. Tinted `bgSunk` with a
`mismatch`-alpha left border.

**Filter bar** (sticky above the kanban inside the tab body, `bgSurface` card):

- **Repo toggles** — pill buttons, one per repo + ocr-container-meta. Click toggles
  `data-active` attr; CSS hides rows for inactive repos.
- **Kind toggles** — chips per `kind:*` from taxonomy.
- **Effort toggles** — `S | M | L | XL` chips.
- **Title search** — single mono `<input>`, focus-ring `accent`. Live filter, case-insensitive
  substring against `data-title`.
- **Reset link** — far right, `ink3`, underline on hover.
- **Result count chip** — "Showing 47 / 152" updates live.

**Filter state persisted** to `localStorage.cost-dashboard-kanban-filters` as a single JSON
blob. Survives regeneration as long as the dashboard is reopened in the same browser.

**Filter logic:** all client-side in `tabs.js`. Each card emitted with `data-repo`, `data-kind`,
`data-effort`, `data-title` attributes. JS adds/removes `.hidden` class.

### Section 6b — Chain state

Card with the existing `RepoChainState` table per repo:
- Repo · Untriaged count · Specs in progress count · Top FR link.
- Token-styled table — `bgRaised` header, `border1` rows. Counts in `mono`. Links in `accent`.

### Section 6c — Style-bot events (last 7 days)

Card with the per-repo event-kind summary, restyled:
- Repo column on the left.
- Right column: event kinds as inline chips with counts.
- Calibration-relevant kinds (`auto-fix-reverted`, `sweep-capped`, `missing-conventions`,
  `fast-check-prebroken`) styled with `mismatch` color.

### Section 6d — Drift (sync + sibling)

Two-column split (`.split`):
- **Left:** Conventions sync drift card — per-repo status with diff snippets for drifted repos.
- **Right:** Sibling rule overlap card — table of cross-repo rule pairs.

---

## 7. Spend tab (`#spend`)

The full token-cost view.

### Row 1 — KPI strip (4 tiles)

- `API cost · 30d` — `$X.XX`, delta vs prior 30d (red up, green down)
- `Runs · 30d` — count, delta vs prior 30d
- `Avg cost / run` — `$X.XX`, delta
- `Top model · 30d` — `mono` model name + % of runs

### Row 2 — Plan window card

Two progress rings (`<svg>` arcs):
- 5-hour window — fill `accent`; turns `--fuzzy` over 70%, `--mismatch` over 90%.
- 7-day window — same color logic.

Each ring: center % in `mono` 13/700. Right side: label + value + "resets" timestamp in `ET`
(uses existing `_ET = ZoneInfo("America/New_York")` pattern).

### Row 3 — Daily spend history (NEW)

Last 14 days as stacked horizontal bars:
- One row per day (date in `mono ink3`).
- Bar segments: interactive (`--ocr` blue), bot (`--gt` purple), unknown (`ink4`).
- Right-aligned total in `mono ink1`.
- Legend below.

Data: aggregate `runs.jsonl` by date (UTC date of `timestamp`), sum `api_cost_usd` per
source category. New aggregation function `aggregate_daily_cost(runs, days=14)`.

### Row 4 — By source (last 30d)

Restructured from the existing source-aggregates table:
- One row per source, sorted by cost descending (interactive first if present).
- Source as chip pill (`interactive` = `--ocr`, bot ctasks = `--gt`, `unknown` = `ink4`).
- Bar showing share of total cost.
- Run count + tokens on the right.
- Cost in `mono` right-aligned.

### Row 5 — Claude Code sessions (last 100)

Restyled table (existing data). New columns:
- Project becomes a `repo-chip` derived from the existing `project` field.
- Cost column right-aligned, `mono`, `ink1`/600 weight.
- Model column uses chip pills (opus=accent, sonnet=ocr, haiku=gt).

### Row 6 — Recent runs (last 50)

Restyled table (existing data). Source pill column. Model chip column. Cost mono-right.

### Row 7 — Permission denials (last 50)

Restyled table. `outcome` column uses status-pip components:
- `recovered` → `--exact` green pip
- `escalated` → `--mismatch` red pip
- `abandoned` → `--fuzzy` amber pip

---

## 8. Error handling

| Failure mode | Behavior |
|---|---|
| Missing sidecar (`/tmp/claude-rate-limits.json`) | Plan-window card shows "No sidecar yet" in `ink3`. Existing behavior, restyled. |
| `gh` CLI unreachable or `DASHBOARD_SKIP_KANBAN=1` | Kanban card shows "Kanban data unavailable" hint. In Progress tab shows "Kanban data required for this view" (NEW empty state). |
| Spec-chain collection fails for one repo | Write to stderr, skip that repo. Existing behavior. |
| Template slot unbound | `render.py` raises `KeyError`. Build script catches per-panel and emits a `<pre class="panel-error">` block; dashboard always lands. NEW. |
| Drift JSON files missing | Per-panel empty-state messages. Existing behavior. |
| Bad data in a run/session/issue record | Skip the row, continue. Existing behavior in `runs_in_window` etc. extended to all renderers. |
| First paint before theme JS runs | `:root` default = dark. Light-mode users see a one-frame flash. Acceptable per design doc. |
| Filter state corrupted in localStorage | Reset on parse error; log to console. Defaults are "all on." |
| No issues to show in In Progress | "No work in progress." centered empty state. |

No panel failure crashes the whole build. Loud-but-contained.

---

## 9. Testing

`cost-dashboard/tests/` (new) with `uv run pytest cost-dashboard/tests/`:

| Test | What it covers |
|---|---|
| `test_render.py` | `render.load_template`, `render.render` with bound slots; loud `KeyError` on unbound. |
| `test_taxonomy.py` | `taxonomy.load_canon()` returns expected shape; `taxonomy.column_order()`, `taxonomy.chip_color(label)` return canonical values from a fixture canon. |
| `test_panels.py` | Each panel renderer with a tiny fixture: asserts presence of key chips/strings, not full HTML. |
| `test_smoke.py` | E2E: `DASHBOARD_SKIP_KANBAN=1` + fixture `runs.jsonl` + fixture `sidecar.json` → `main()` writes a non-empty HTML containing all 4 tab IDs, the `data-theme` script, and the theme toggle. |

Fixtures (`tests/fixtures/`):
- `runs.jsonl` — 20 synthetic runs across sources/models/dates
- `sidecar.json` — synthetic `five_hour` / `seven_day` blocks
- `kanban-sample.json` — 30 synthetic issues across 3 fake repos covering every status
- `chain-state.json` — pre-baked `RepoChainState` snapshot for the 3 fake repos
- `canon-test.json` — minimal taxonomy canon for taxonomy tests

CI: an existing pre-commit hook runs the smoke test (or, if none today, this spec adds one).

---

## 10. Implementation plan

Two PRs, with an explicit rollback boundary after PR 1.

### PR 1 — Scaffolding + retheme (passes the rollback gate)

Goal: dashboard renders the **existing content** under the new tab shell with the design
language applied. No new In Progress data, no kanban filter logic, no daily-spend chart.

Slices:

1. Add `cost-dashboard/taxonomy.py` reading `scripts/sync-labels-canon.json`. Hard-fail if
   missing — taxonomy spec must land first.
2. Add `render.py` + the template directory structure. Move existing `HTML_TEMPLATE` content
   into `templates/dashboard.html` verbatim (preserves output bit-for-bit, plus tests pass).
3. Extract inline CSS to `static/tokens.css` + `static/dashboard.css`. Inline both into the
   final HTML at build time. Verify visual diff is minimal.
4. Add `templates/tabs/{overview,in-progress,spec-chain,spend}.html`. Move existing panels
   into the appropriate tab fragments. Add `static/tabs.js` with hash routing + theme
   toggle. In Progress tab placeholder reads "Coming in PR 2."
5. Add `cost-dashboard/tests/` with `test_render.py` + `test_smoke.py`. CI green.

PR 1 lands a tabbed, themed dashboard with the same data on a new shell. Rollback target.

### PR 2 — In Progress tab + restructured panels + kanban filters

Goal: deliver the full design.

Slices:

1. Restructure each panel from `<table>`-only to card-surface partials. Add `partials/`
   directory with the 9 partial templates. Existing panel renderers refactored to use them.
2. Build the In Progress tab fully (milestone grouping, issue rows, empty state). Add
   `partials/milestone-group.html` + `partials/issue-row.html`.
3. Make the kanban comprehensive: change `load_kanban_data` to keep all open issues; add
   `unlabeled` column; render columns from canon ordering.
4. Add the kanban filter bar (HTML in spec-chain.html, logic in `tabs.js`). Localstorage
   persistence.
5. Add the daily-spend 14-day history chart (`partials/spend-day.html` + aggregator function).
6. Add `test_panels.py` + `test_taxonomy.py`. Round out coverage.

PR 2 ships the full redesign.

### Cross-PR concerns

- Both PRs gate on the taxonomy spec's Slice 1 (the canon JSON) being present.
- No need to wait on the taxonomy's Slices 2-3 (sync script + repo reconciliation) — the
  dashboard reads from canon regardless of whether repos are fully synced. Stale labels just
  appear in the `unlabeled` column on the kanban, which is the right behavior.
- Both PRs preserve `DASHBOARD_SKIP_KANBAN=1` and `DASHBOARD_SKIP_CHAIN=1` env switches.
- Both PRs produce a single-file HTML output to the same path. No callers update needed.
