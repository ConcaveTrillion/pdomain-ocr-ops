---
milestone: 11
repo: ConcaveTrillion/ocr-container-meta
status: complete
synced: 2026-05-17
---

# Cost dashboard redesign — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure `cost-dashboard/` into a tabbed shell (Overview / In Progress / Spec Chain / Spend), apply the workspace design language (dark+light tokens), make the kanban comprehensive with frontend filters, and add a milestone-grouped In Progress tab plus a daily-spend 14-day history chart. Output remains a single self-contained HTML file.

**Architecture:** Split `build-cost-dashboard.py` from monolithic-string-template to a template + asset layout. Templates use `{{slot}}` substitution via a 30-line `render.py`. Tokens + primitives live in CSS files inlined into the final HTML. A new `taxonomy.py` reads `scripts/sync-labels-canon.json` (delivered by the taxonomy plan) and exposes lookups for column ordering and chip colors. Two-PR delivery: PR 1 ships the shell + retheme with existing content; PR 2 ships the In Progress tab + restructured panels + kanban filters + daily-spend chart.

**Tech Stack:** Python 3.13, uv, pytest, vanilla JS (no framework), CSS custom properties, gh CLI (existing).

**Depends on:** [2026-05-17-gh-label-taxonomy.md](2026-05-17-gh-label-taxonomy.md) — specifically its Task 1 (canon JSON). Later taxonomy tasks (sync script + repo reconciliation) can run in parallel with this plan.

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Template engine | Custom 30-line `render.py` with `{{slot}}` regex | No Jinja dependency; templates stay reviewable |
| Asset bundling | Inline CSS + JS into final HTML at build time | Keeps output a single-file artifact viewable via `file://` |
| Theme persistence key | `cost-dashboard-theme` in localStorage | Namespaced; won't collide with sibling apps |
| Filter persistence key | `cost-dashboard-kanban-filters` in localStorage | Same namespacing rule |
| Hash routing | `#overview \| #in-progress \| #spec-chain \| #spend` | Standard, no library needed |
| Font strategy | System fonts only (Inter via fallback stack, ui-monospace) | Zero asset bundling; brand fidelity sacrificed for offline reliability |
| Taxonomy import | `taxonomy.py` reads `scripts/sync-labels-canon.json` | Hard-fail with a clear error if missing — taxonomy plan must ship Task 1 first |
| Per-panel failure | Caught in build script, emits `<pre class="panel-error">` block | Dashboard always lands even if one panel crashes |
| Spend history aggregation | Per-day in UTC; bucket by `runs.jsonl` timestamp `[:10]` | Trivial implementation; matches existing `runs_in_window` filtering |
| Test runner | `uv run pytest cost-dashboard/tests/ -v` | Workspace convention (never `python3` directly) |
| Rollback gate | After PR 1 (themed + tabbed shell with same content) | One clear safe point; PR 2 layers new features on |

---

## File structure

| Path | Action | Phase |
|---|---|---|
| `cost-dashboard/render.py` | CREATE | PR 1 |
| `cost-dashboard/taxonomy.py` | CREATE | PR 1 |
| `cost-dashboard/build-cost-dashboard.py` | MODIFY | PR 1 + 2 |
| `cost-dashboard/templates/dashboard.html` | CREATE | PR 1 |
| `cost-dashboard/templates/tabs/{overview,in-progress,spec-chain,spend}.html` | CREATE | PR 1 |
| `cost-dashboard/templates/partials/*.html` | CREATE | PR 2 (most) |
| `cost-dashboard/static/tokens.css` | CREATE | PR 1 |
| `cost-dashboard/static/dashboard.css` | CREATE | PR 1 |
| `cost-dashboard/static/tabs.js` | CREATE | PR 1 + extended in PR 2 |
| `cost-dashboard/tests/test_render.py` | CREATE | PR 1 |
| `cost-dashboard/tests/test_taxonomy.py` | CREATE | PR 1 |
| `cost-dashboard/tests/test_panels.py` | CREATE | PR 2 |
| `cost-dashboard/tests/test_smoke.py` | CREATE | PR 1 |
| `cost-dashboard/tests/fixtures/*` | CREATE | PR 1 (smoke) + PR 2 (panels) |

---

# Phase A — PR 1: scaffolding + retheme

Goal: dashboard renders the **existing content** under the new tab shell with the design language applied. No new In Progress data, no kanban filter logic, no daily-spend chart. Output passes a visual smoke check that the same panels are present and the chrome is the new themed shell.

## Task A1 — `taxonomy.py` loader {#taxonomy-py}

model: sonnet  effort: S  area: cost-dashboard

**Files:**
- Create: `cost-dashboard/taxonomy.py`
- Test: `cost-dashboard/tests/test_taxonomy.py`

Context: Single source of label info for the dashboard. Reads `scripts/sync-labels-canon.json` once at build time and exposes lookups.

- [ ] **Step 1: Write `tests/test_taxonomy.py`**

```python
"""Tests for taxonomy.py — reads sync-labels-canon.json."""
from __future__ import annotations
import json
import pytest
from pathlib import Path

import cost_dashboard_taxonomy as tx  # imported as module path below


def test_load_canon_returns_dict(tmp_path: Path):
    canon = tmp_path / "canon.json"
    canon.write_text(json.dumps({
        "status_order": ["status:backlog"],
        "labels": [{"name": "status:backlog", "color": "ededed",
                    "description": "x", "group": "status"}],
        "chip_colors": {},
        "repos": ["x"], "renames": [], "local_extensions": {},
    }))
    canon_data = tx.load_canon(canon)
    assert canon_data["status_order"] == ["status:backlog"]


def test_column_order_returns_canonical_status_columns(tmp_path):
    canon = tmp_path / "canon.json"
    canon.write_text(json.dumps({
        "status_order": ["status:a", "status:b"],
        "labels": [], "chip_colors": {},
        "repos": [], "renames": [], "local_extensions": {},
    }))
    tx.load_canon(canon)
    assert tx.column_order() == ["unlabeled", "status:a", "status:b"]


def test_chip_color_falls_back_to_default_for_unknown_label(tmp_path):
    canon = tmp_path / "canon.json"
    canon.write_text(json.dumps({
        "status_order": [], "labels": [],
        "chip_colors": {"kind:bug": {"fg": "dc6555", "border": "...", "bg": "..."}},
        "repos": [], "renames": [], "local_extensions": {},
    }))
    tx.load_canon(canon)
    assert tx.chip_color("kind:bug")["fg"] == "dc6555"
    assert tx.chip_color("unknown") is None


def test_missing_canon_file_raises_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="sync-labels-canon.json"):
        tx.load_canon(tmp_path / "nonexistent.json")
```

- [ ] **Step 2: Create `cost-dashboard/taxonomy.py`**

```python
"""Load workspace label taxonomy from scripts/sync-labels-canon.json.

This module is the dashboard's single source of truth for:
- Kanban column ordering (status_order).
- Per-label chip colors (chip_colors).
- The full canonical labels list (labels).

The JSON file is written and maintained by the gh-label-taxonomy plan;
this module just reads it.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

_canon: dict[str, Any] | None = None


def load_canon(path: Path | None = None) -> dict[str, Any]:
    """Load canon JSON. Caches the result. Call once at build time."""
    global _canon
    if path is None:
        path = Path(__file__).resolve().parents[1] / "scripts" / "sync-labels-canon.json"
    if not path.exists():
        raise FileNotFoundError(
            f"sync-labels-canon.json not found at {path}. "
            "The cost dashboard requires the gh-label-taxonomy plan's "
            "Task 1 (canon JSON) to ship first."
        )
    _canon = json.loads(path.read_text())
    return _canon


def column_order() -> list[str]:
    """Kanban column ordering. Returns 'unlabeled' first, then canon status order."""
    if _canon is None:
        raise RuntimeError("Call load_canon() before column_order()")
    return ["unlabeled"] + list(_canon["status_order"])


def chip_color(label: str) -> dict[str, str] | None:
    """Return {fg, border, bg} for a label, or None if not in chip_colors."""
    if _canon is None:
        raise RuntimeError("Call load_canon() before chip_color()")
    return _canon.get("chip_colors", {}).get(label)
```

- [ ] **Step 3: Adjust test import path**

Tests import as `cost_dashboard_taxonomy`. Add a `cost-dashboard/conftest.py` that prepends the directory:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import taxonomy as cost_dashboard_taxonomy  # noqa: E402,F401
sys.modules["cost_dashboard_taxonomy"] = cost_dashboard_taxonomy
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest cost-dashboard/tests/test_taxonomy.py -v`
Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add cost-dashboard/taxonomy.py cost-dashboard/conftest.py cost-dashboard/tests/test_taxonomy.py
git commit -m "feat(dashboard): add taxonomy loader for canon JSON

Reads scripts/sync-labels-canon.json (from the gh-label-taxonomy plan)
and exposes column_order() + chip_color() for the dashboard. Hard-fails
with a clear message if the canon file is missing."
```

---

## Task A2 — `render.py` template loader {#render-py}

model: sonnet  effort: S  area: cost-dashboard

**Files:**
- Create: `cost-dashboard/render.py`
- Test: `cost-dashboard/tests/test_render.py`

Context: 30-line template engine. No Jinja. `{{slot}}` placeholders, `{{slot_html}}` for raw HTML, anything else gets HTML-escaped.

- [ ] **Step 1: Write `tests/test_render.py`**

```python
"""Tests for render.py — minimal {{slot}} template substitution."""
from __future__ import annotations
import pytest
from pathlib import Path
import render


def test_simple_substitution():
    out = render.render("Hello {{name}}!", name="world")
    assert out == "Hello world!"


def test_html_escaped_by_default():
    out = render.render("{{x}}", x="<script>alert(1)</script>")
    assert "&lt;script&gt;" in out
    assert "<script>" not in out


def test_slot_with_html_suffix_passes_through_raw():
    out = render.render("{{body_html}}", body_html="<b>bold</b>")
    assert out == "<b>bold</b>"


def test_missing_slot_raises_keyerror_loudly():
    with pytest.raises(KeyError, match="missing"):
        render.render("{{missing}}", other="value")


def test_load_template_reads_file(tmp_path: Path):
    p = tmp_path / "x.html"
    p.write_text("hi {{n}}")
    out = render.load_template(p)
    assert out == "hi {{n}}"
```

- [ ] **Step 2: Create `cost-dashboard/render.py`**

```python
"""Tiny template engine: {{slot}} substitution, no Jinja.

Convention: any slot name ending in `_html` is treated as raw HTML
(no escaping). All other slots are HTML-escaped. Unbound slots raise
KeyError loudly so the caller knows to add a try/except panel-error
wrapper if it wants soft failure.
"""
from __future__ import annotations
import html
import re
from pathlib import Path

_SLOT_RE = re.compile(r"\{\{(\w+)\}\}")


def load_template(path: Path) -> str:
    return path.read_text()


def render(template: str, **slots: object) -> str:
    def sub(m: re.Match[str]) -> str:
        name = m.group(1)
        if name not in slots:
            raise KeyError(f"missing slot {name!r} in render() call")
        val = slots[name]
        if name.endswith("_html"):
            return str(val)
        return html.escape(str(val))
    return _SLOT_RE.sub(sub, template)
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest cost-dashboard/tests/test_render.py -v`
Expected: 5 tests pass.

- [ ] **Step 4: Commit**

```bash
git add cost-dashboard/render.py cost-dashboard/tests/test_render.py
git commit -m "feat(dashboard): add minimal {{slot}} template engine

30-line render.py — no Jinja dependency. Slots ending in _html pass
through raw; others are HTML-escaped. Unbound slots raise KeyError."
```

---

## Task A3 — Extract tokens.css + dashboard.css from the design language {#extract-css}

model: sonnet  effort: M  area: cost-dashboard

**Files:**
- Create: `cost-dashboard/static/tokens.css`
- Create: `cost-dashboard/static/dashboard.css`

Context: Port the dual-theme CSS variable blocks from `docs/design-system/DESIGN_LANGUAGE.md` §"Theme implementation" into `tokens.css`, then write the dashboard's component CSS using only those tokens.

- [ ] **Step 1: Create `static/tokens.css` with full dual-theme block**

```css
/* tokens.css — workspace design-language tokens.
 * Mirrors docs/design-system/DESIGN_LANGUAGE.md. Dark default, light via
 * [data-theme="light"]. */

:root {
  /* Surfaces */
  --bg-page: #0c0c10;
  --bg-surface: #15151b;
  --bg-raised: #1d1d24;
  --bg-sunk: #08080c;

  /* Borders */
  --border-1: #222229;
  --border-2: #2f2f38;
  --border-3: #3f3f49;

  /* Text */
  --ink-1: #f0f0f2;
  --ink-2: #b0b0b8;
  --ink-3: #7a7a85;
  --ink-4: #4e4e58;

  /* Accent */
  --accent: #d6925a;
  --accent-ink: #1a0f08;

  /* Status */
  --exact: #5fbf6a;
  --fuzzy: #e8a83a;
  --mismatch: #dc6555;
  --ocr: #5d9fdf;
  --gt: #a888d4;

  /* Layers */
  --block: #a89074;
  --para: #7fb56a;
  --line: #d088a8;
  --word: #6e9cdf;
}

[data-theme="light"] {
  --bg-page: #f6f4ef;
  --bg-surface: #ffffff;
  --bg-raised: #ecebe5;
  --bg-sunk: #f0eee7;
  --border-1: #d8d4c8;
  --border-2: #c2bdaf;
  --border-3: #a39e8d;
  --ink-1: #1a1810;
  --ink-2: #4a4538;
  --ink-3: #7c7665;
  --ink-4: #b0aa95;
  --accent: #b85a2e;
  --accent-ink: #ffffff;
  --exact: #2d8c3a;
  --fuzzy: #b87b1f;
  --mismatch: #b13d32;
  --ocr: #2d6fb5;
  --gt: #6e4ea5;
  --block: #7a5e3a;
  --para: #4d8a3a;
  --line: #a8527a;
  --word: #3d6bb8;
}
```

- [ ] **Step 2: Create `static/dashboard.css` with the primitives**

Implement: `body`, `.dash-tabs`, `.dash-tab`, `.dash-tab.active`, `.dash-tab .count`, `.card`, `.card-head`, `.card-title`, `.kpi-tile`, `.chip`, `.chip.*` color variants, `.kanban`, `.kanban .card`, `.kanban .col-*`, `.bots-paused-banner`, `.triage`, `.outcome.recovered/escalated/abandoned`, `.btn`, `.btn.icon`, table primitives (`.tbl`).

Use the mockup CSS we wrote during brainstorming (`/workspaces/ocr-container/.superpowers/brainstorm/897356-1779023033/content/spend-tab.html`) as the starting reference — copy the relevant classes verbatim and adapt as needed.

Length target: ~400 lines. Keep selectors flat.

- [ ] **Step 3: Visually compare in browser**

Run: `python3 -m http.server -d cost-dashboard/static 8765` and open `http://localhost:8765/` in a browser. Verify CSS files load without 404. (No HTML to render yet; just a syntax sanity check.)

Kill the server: `Ctrl-C`.

- [ ] **Step 4: Commit**

```bash
git add cost-dashboard/static/tokens.css cost-dashboard/static/dashboard.css
git commit -m "feat(dashboard): extract design-language tokens + dashboard primitives

tokens.css ports the dual-theme CSS variable block verbatim from
docs/design-system/DESIGN_LANGUAGE.md. dashboard.css contains the
primitives (cards, chips, tabs, tables, KPI tiles, banners) that the
restyled panels will use."
```

---

## Task A4 — Tab shell + tabs.js {#tab-shell}

model: sonnet  effort: M  area: cost-dashboard

**Files:**
- Create: `cost-dashboard/templates/dashboard.html`
- Create: `cost-dashboard/templates/tabs/{overview,in-progress,spec-chain,spend}.html`
- Create: `cost-dashboard/static/tabs.js`

- [ ] **Step 1: Create `templates/dashboard.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ship-issue cost dashboard</title>
<style>{{tokens_css_html}}
{{dashboard_css_html}}</style>
</head>
<body>
<header class="dash-header">
  <span class="dash-title">ship-issue cost dashboard</span>
  <span class="dash-meta mono">Generated {{generated_at}}</span>
  <button id="theme-toggle" class="btn icon" title="Toggle theme">☾</button>
</header>
{{rebase_alerts_html}}
<nav class="dash-tabs">
  <a class="dash-tab" data-tab="overview" href="#overview">Overview</a>
  <a class="dash-tab" data-tab="in-progress" href="#in-progress">In Progress <span class="count">{{in_progress_count}}</span></a>
  <a class="dash-tab" data-tab="spec-chain" href="#spec-chain">Spec Chain</a>
  <a class="dash-tab" data-tab="spend" href="#spend">Spend</a>
</nav>
<main class="dash-body">
  <section class="tab-panel" data-tab="overview">{{overview_html}}</section>
  <section class="tab-panel" data-tab="in-progress">{{in_progress_html}}</section>
  <section class="tab-panel" data-tab="spec-chain">{{spec_chain_html}}</section>
  <section class="tab-panel" data-tab="spend">{{spend_html}}</section>
</main>
<script>{{tabs_js_html}}</script>
</body>
</html>
```

- [ ] **Step 2: Create `static/tabs.js`**

```js
(function() {
  const STORAGE_KEY = "cost-dashboard-theme";
  const html = document.documentElement;

  // Theme boot.
  const stored = localStorage.getItem(STORAGE_KEY);
  const initial = stored || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  html.setAttribute("data-theme", initial);

  const toggleBtn = document.getElementById("theme-toggle");
  if (toggleBtn) {
    toggleBtn.textContent = initial === "dark" ? "☾" : "☀";
    toggleBtn.addEventListener("click", () => {
      const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
      html.setAttribute("data-theme", next);
      localStorage.setItem(STORAGE_KEY, next);
      toggleBtn.textContent = next === "dark" ? "☾" : "☀";
    });
  }

  // Tab routing.
  function activate(name) {
    document.querySelectorAll(".dash-tab").forEach(t => {
      t.classList.toggle("active", t.dataset.tab === name);
    });
    document.querySelectorAll(".tab-panel").forEach(p => {
      p.classList.toggle("active", p.dataset.tab === name);
    });
  }

  function fromHash() {
    const h = (location.hash || "#overview").slice(1);
    const known = ["overview", "in-progress", "spec-chain", "spend"];
    return known.includes(h) ? h : "overview";
  }

  activate(fromHash());
  window.addEventListener("hashchange", () => activate(fromHash()));
})();
```

- [ ] **Step 3: Create empty tab fragments**

Each of `templates/tabs/{overview,in-progress,spec-chain,spend}.html` starts as a stub that the build script will fill. For PR 1, write placeholder slot markers:

`overview.html`:
```html
{{rebase_alerts_html}}
<section class="card">
  <h2 class="card-title">Plan window usage</h2>
  {{plan_block_html}}
</section>
<section class="card">
  <h2 class="card-title">Needs triage</h2>
  {{bounced_triage_html}}
</section>
```

`in-progress.html` (PR 1 placeholder):
```html
<section class="card"><p class="empty">Coming in PR 2.</p></section>
```

`spec-chain.html` and `spend.html` get analogous placeholder card containers with slot markers for every existing panel.

- [ ] **Step 4: Add `.tab-panel { display: none; } .tab-panel.active { display: block; }` to dashboard.css**

Edit `cost-dashboard/static/dashboard.css` and append.

- [ ] **Step 5: Commit**

```bash
git add cost-dashboard/templates/ cost-dashboard/static/tabs.js cost-dashboard/static/dashboard.css
git commit -m "feat(dashboard): tab shell HTML + JS

dashboard.html shell with 4 tab panels and slot markers. tabs.js handles
hash routing + theme toggle + localStorage persistence. Tab fragments
stubbed for PR 1 (existing panels move into Overview/Spec-Chain/Spend;
In Progress is a placeholder for PR 2)."
```

---

## Task A5 — Rewire `build-cost-dashboard.py` to use templates {#rewire-build}

model: sonnet  effort: L  area: cost-dashboard

**Files:**
- Modify: `cost-dashboard/build-cost-dashboard.py`

Context: Pull existing panels out of the monolithic `HTML_TEMPLATE` string and route them through templates. Output must contain the same panels as before — only chrome and styling differ.

- [ ] **Step 1: Add imports + load canon at top of `main()`**

In `build-cost-dashboard.py`:
```python
import render
import taxonomy
# ...
def main():
    taxonomy.load_canon()  # Fails fast if canon missing.
    ...
```

- [ ] **Step 2: Replace `HTML_TEMPLATE` formatting with template renders**

Remove the giant `HTML_TEMPLATE = """..."""` literal. Replace the final `html = HTML_TEMPLATE.format(...)` call with:

```python
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"

# Render each tab fragment.
overview_html = render.render(
    render.load_template(templates_dir / "tabs" / "overview.html"),
    plan_block_html=render_plan_block(sidecar, runs),
    bounced_triage_html=render_bounced_triage_panel(kanban_data),
    rebase_alerts_html=render_rebase_alerts_panel(_load_rebase_alerts()),
)
spec_chain_html = render.render(
    render.load_template(templates_dir / "tabs" / "spec-chain.html"),
    kanban_html=render_kanban_panel(kanban_data),
    chain_state_html=render_chain_state_panel(chain_states),
    style_bot_events_html=render_style_bot_events_panel(_load_events()),
    sync_drift_html=render_sync_drift_panel(_load_sync_drift()),
    sibling_drift_html=render_sibling_drift_panel(_load_sibling_drift()),
)
spend_html = render.render(
    render.load_template(templates_dir / "tabs" / "spend.html"),
    claude_sessions_html=render_claude_sessions_panel(claude_sessions),
    runs_table_html=render_runs_table(runs, session_pct_5h, session_pct_7d),
    source_aggregates_html=render_source_aggregates(runs),
    total_cost_30d=f"${total_cost_30d:.2f}",
    n_runs_30d=str(len(runs_30d)),
    denials_html=render_denials_table(denials),
)
in_progress_html = "<section class='card'><p class='empty'>Coming in PR 2.</p></section>"
in_progress_count = "0"

# Compute in_progress_count: filter kanban_data to status:in-progress
# union with status:in-pr (when present) and count.
in_progress_count = str(_count_in_progress(kanban_data))

html_out = render.render(
    render.load_template(templates_dir / "dashboard.html"),
    tokens_css_html=(static_dir / "tokens.css").read_text(),
    dashboard_css_html=(static_dir / "dashboard.css").read_text(),
    tabs_js_html=(static_dir / "tabs.js").read_text(),
    generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    rebase_alerts_html=render_rebase_alerts_panel(_load_rebase_alerts()),
    overview_html=overview_html,
    in_progress_html=in_progress_html,
    in_progress_count=in_progress_count,
    spec_chain_html=spec_chain_html,
    spend_html=spend_html,
)
```

- [ ] **Step 3: Add `_count_in_progress` helper**

```python
def _count_in_progress(kanban_data: dict[str, dict[str, list[dict]]]) -> int:
    total = 0
    for repo_data in kanban_data.values():
        total += len(repo_data.get("status:in-progress", []))
        total += len(repo_data.get("status:in-pr", []))
    return total
```

- [ ] **Step 4: Wrap each `render.render` call in per-panel try/except**

```python
def safe_render(name: str, fn, **kwargs):
    try:
        return fn(**kwargs)
    except Exception as exc:
        return f"<pre class='panel-error'>panel '{name}' failed: {html.escape(str(exc))}</pre>"
```

Wrap every panel-renderer call (`render_plan_block`, `render_kanban_panel`, etc.) in this. Add `<style>.panel-error { color: var(--mismatch); background: var(--bg-sunk); padding: 12px; }</style>` to `dashboard.css`.

- [ ] **Step 5: Run the existing build end-to-end with DASHBOARD_SKIP_KANBAN=1**

Run:
```bash
SHIP_ISSUE_MEMORY_DIR=/tmp/test-dash DASHBOARD_SKIP_KANBAN=1 DASHBOARD_SKIP_CHAIN=1 \
  uv run python cost-dashboard/build-cost-dashboard.py
```
Expected: `Wrote /tmp/test-dash/cost-dashboard.html`. Open the file in a browser; verify the new tab chrome shows, all 4 tabs are clickable, theme toggle works.

- [ ] **Step 6: Commit**

```bash
git add cost-dashboard/build-cost-dashboard.py
git commit -m "refactor(dashboard): split monolithic HTML_TEMPLATE into templates

build-cost-dashboard.py is now a data-loading orchestrator. The shell
HTML lives in templates/dashboard.html; each tab is a templates/tabs/*.html
fragment filled by the existing panel renderers. Per-panel failures are
caught and emit a visible panel-error block; the dashboard always lands."
```

---

## Task A6 — Smoke test {#smoke-test}

model: sonnet  effort: S  area: tests

**Files:**
- Create: `cost-dashboard/tests/test_smoke.py`
- Create: `cost-dashboard/tests/fixtures/runs.jsonl`
- Create: `cost-dashboard/tests/fixtures/sidecar.json`

Context: End-to-end test verifying the new shell renders all 4 tabs from synthetic data.

- [ ] **Step 1: Create fixtures**

`runs.jsonl` — 5 synthetic runs:
```jsonl
{"timestamp": "2026-05-15T10:00:00Z", "session_id": "s1", "source": "interactive", "models_used": ["claude-sonnet-4-6"], "efforts_used": ["medium"], "tokens_in": 1000, "tokens_out": 500, "cache_read_tokens": 0, "cache_creation_tokens": 0, "api_cost_usd": 0.05}
{"timestamp": "2026-05-16T11:00:00Z", "session_id": "s2", "source": "ship-issue-pdomain-book-tools", "models_used": ["claude-sonnet-4-6"], "efforts_used": ["medium"], "tokens_in": 2000, "tokens_out": 800, "cache_read_tokens": 100, "cache_creation_tokens": 50, "api_cost_usd": 0.12}
{"timestamp": "2026-05-17T09:00:00Z", "session_id": "s3", "source": "interactive", "models_used": ["claude-opus-4-7"], "efforts_used": ["high"], "tokens_in": 5000, "tokens_out": 2000, "cache_read_tokens": 200, "cache_creation_tokens": 100, "api_cost_usd": 0.45}
{"timestamp": "2026-05-17T10:00:00Z", "session_id": "s4", "source": "style-sweep", "models_used": ["claude-haiku-4-5"], "efforts_used": ["low"], "tokens_in": 500, "tokens_out": 100, "cache_read_tokens": 0, "cache_creation_tokens": 0, "api_cost_usd": 0.01}
{"timestamp": "2026-05-17T12:00:00Z", "session_id": "s5", "source": "interactive", "models_used": ["claude-sonnet-4-6"], "efforts_used": ["medium"], "tokens_in": 1500, "tokens_out": 600, "cache_read_tokens": 0, "cache_creation_tokens": 0, "api_cost_usd": 0.08}
```

`sidecar.json`:
```json
{"five_hour": {"used_percentage": 32, "resets_at": "14:00 EDT"},
 "seven_day": {"used_percentage": 68, "resets_at": "Sun 21:00 EDT"}}
```

- [ ] **Step 2: Write `tests/test_smoke.py`**

```python
"""End-to-end smoke: build the dashboard from fixtures and inspect the HTML."""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path
import shutil
import pytest


FIXTURES = Path(__file__).parent / "fixtures"
COST_DASHBOARD = Path(__file__).resolve().parents[1]


def test_dashboard_builds_with_fixtures(tmp_path: Path, monkeypatch):
    # Stage fixtures.
    mem = tmp_path / "memory"
    mem.mkdir()
    shutil.copy(FIXTURES / "runs.jsonl", mem / "run-reports.jsonl")
    sidecar = tmp_path / "sidecar.json"
    shutil.copy(FIXTURES / "sidecar.json", sidecar)

    env = os.environ.copy()
    env["SHIP_ISSUE_MEMORY_DIR"] = str(mem)
    env["RATE_LIMITS_SIDECAR"] = str(sidecar)
    env["DASHBOARD_SKIP_KANBAN"] = "1"
    env["DASHBOARD_SKIP_CHAIN"] = "1"

    result = subprocess.run(
        [sys.executable, str(COST_DASHBOARD / "build-cost-dashboard.py")],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr

    html = (mem / "cost-dashboard.html").read_text()
    # All 4 tab anchors present.
    for tab in ["overview", "in-progress", "spec-chain", "spend"]:
        assert f'data-tab="{tab}"' in html, f"tab {tab} missing"
    # Theme toggle script ran (look for data-theme attribute somewhere).
    assert "data-theme" in html
    # tokens.css inlined (look for accent token).
    assert "--accent" in html
    # tabs.js inlined.
    assert "STORAGE_KEY" in html or "cost-dashboard-theme" in html
```

- [ ] **Step 3: Run the smoke test**

Run: `uv run pytest cost-dashboard/tests/test_smoke.py -v`
Expected: 1 test passes.

- [ ] **Step 4: Commit**

```bash
git add cost-dashboard/tests/test_smoke.py cost-dashboard/tests/fixtures/
git commit -m "test(dashboard): end-to-end smoke for templated build

Builds the dashboard from synthetic runs.jsonl + sidecar.json fixtures
with DASHBOARD_SKIP_KANBAN=1, then asserts all 4 tab IDs are present,
tokens.css is inlined, and the theme toggle script wired up."
```

---

## Task A7 — Push & open PR 1 {#pr1-merge}

model: sonnet  effort: S  area: workflow

- [ ] **Step 1: Verify all PR 1 tests pass**

Run: `uv run pytest cost-dashboard/tests/ -v`
Expected: every test passes (taxonomy, render, smoke).

- [ ] **Step 2: Push branch and open PR**

```bash
git push -u origin <branch-name>
gh pr create --title "feat(dashboard): tabbed shell + design-language retheme (PR 1/2)" \
  --body "$(cat <<'EOF'
## Summary
- New 4-tab shell: Overview / In Progress / Spec Chain / Spend
- Dual-theme design language (dark default + light toggle, localStorage)
- Templates extracted from monolithic HTML_TEMPLATE string
- taxonomy.py reads scripts/sync-labels-canon.json (canon JSON)
- Per-panel failure caught + isolated; dashboard always lands

## Rollback boundary
This is the rollback gate. If PR 2 ships features that need to be reverted,
this PR can stay merged: dashboard renders the same content as today, just
themed + tabbed.

## Test plan
- [ ] uv run pytest cost-dashboard/tests/ passes
- [ ] Open the generated cost-dashboard.html locally; verify 4 tabs work
- [ ] Toggle theme; verify dark→light flip and localStorage persistence
- [ ] Confirm DASHBOARD_SKIP_KANBAN=1 still works

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

PR 1 lands → tag as rollback boundary.

---

# Phase B — PR 2: In Progress tab + restructured panels + kanban filters + spend history

## Task B1 — Card-surface partials for existing panels {#card-partials}

model: sonnet  effort: L  area: cost-dashboard

**Files:**
- Create: `cost-dashboard/templates/partials/{kpi-tile,sessions-row,run-row,denial-row,source-row}.html`
- Modify: `cost-dashboard/build-cost-dashboard.py` (refactor panel renderers to emit card surfaces using partials)

Context: Today's panels emit raw `<table>` HTML. Restructure each to render through partials that use design-language card surfaces.

For each partial:

- [ ] **Step 1: Write `kpi-tile.html`**

```html
<div class="kpi-tile">
  <div class="lbl">{{label}}</div>
  <div class="val">{{value}}</div>
  <div class="delta {{delta_class}}">{{delta_text}}</div>
</div>
```

- [ ] **Step 2: Write `sessions-row.html`, `run-row.html`, `denial-row.html`, `source-row.html`**

Use the same structure as the spend-tab mockup (`spend-tab.html` from the brainstorm browser). Each partial produces one row's worth of HTML.

- [ ] **Step 3: Refactor `render_runs_table`, `render_claude_sessions_panel`, etc.**

Each becomes a loop over data rows, calling `render.render(load_template(partial), **row_data)`. The wrapping `<table>` becomes a `<div class="card">` with header.

- [ ] **Step 4: Run smoke test + visual check**

```bash
uv run pytest cost-dashboard/tests/test_smoke.py -v
SHIP_ISSUE_MEMORY_DIR=/tmp/test-dash DASHBOARD_SKIP_KANBAN=1 DASHBOARD_SKIP_CHAIN=1 \
  uv run python cost-dashboard/build-cost-dashboard.py
```

Open the output. Confirm Spend tab shows the new KPI strip + source aggregates as chip-pill rows + sessions/runs/denials as restyled tables.

- [ ] **Step 5: Commit**

```bash
git add cost-dashboard/templates/partials/ cost-dashboard/build-cost-dashboard.py
git commit -m "refactor(dashboard): emit panels as card surfaces via partials

Sessions, runs, denials, source-aggregates, KPI tiles all use design-
language card surfaces with token-styled chips and pips. No table HTML
escapes into the output."
```

---

## Task B2 — Build the In Progress tab {#in-progress-tab}

model: sonnet  effort: M  area: cost-dashboard

**Files:**
- Create: `cost-dashboard/templates/partials/{milestone-group,issue-row}.html`
- Modify: `cost-dashboard/build-cost-dashboard.py` (add `render_in_progress_panel`)
- Modify: `cost-dashboard/templates/tabs/in-progress.html`

Context: Implement the milestone-grouped In Progress view per spec §5.

- [ ] **Step 1: Write `partials/milestone-group.html`**

```html
<section class="card milestone-group">
  <header class="milestone-head">
    <span class="ms-title mono">{{title}}</span>
    <span class="repo-chip">{{repo}}</span>
    <span class="ms-progress">
      <span class="ms-bar"><span class="ms-bar-fill" style="width: {{progress_pct}}%"></span></span>
      <span class="mono">{{progress_text}}</span>
    </span>
  </header>
  <div class="milestone-children">{{children_html}}</div>
</section>
```

- [ ] **Step 2: Write `partials/issue-row.html`**

```html
<a class="issue-row" href="{{url}}">
  <span class="issue-num mono">#{{number}}</span>
  <span class="issue-title">{{title}}</span>
  <span class="issue-chips">{{chips_html}}</span>
</a>
```

- [ ] **Step 3: Add `render_in_progress_panel` to `build-cost-dashboard.py`**

```python
def render_in_progress_panel(kanban_data, chain_states):
    """Milestone-grouped view of status:in-progress + status:in-pr + status:in-review."""
    in_progress_statuses = ("status:in-progress", "status:in-pr", "status:in-review")
    # Build issue list with milestone joins.
    issues = []
    for repo, cols in kanban_data.items():
        for status in in_progress_statuses:
            for issue in cols.get(status, []):
                if "triage:rejected" in issue.get("labels", []):
                    continue
                issues.append({"repo": repo, **issue})

    # Group by milestone using chain_states.
    milestone_by_issue: dict[tuple[str, int], dict] = {}
    for state in chain_states:
        repo_base = state.repo.split("/")[-1]
        for fr in state.feature_requests:
            for spec in fr.spec_issues:
                if spec.milestone:
                    milestone_by_issue[(repo_base, fr.number)] = spec.milestone

    groups: dict[str, dict] = {"__unassigned__": {"title": "Unassigned",
                                                   "progress_pct": 0, "issues": []}}
    for issue in issues:
        ms = milestone_by_issue.get((issue["repo"], issue["number"]))
        key = ms.title if ms else "__unassigned__"
        if key not in groups:
            closed = ms.closed_issues if ms else 0
            total = (ms.closed_issues + ms.open_issues) if ms else 0
            pct = int(100 * closed / total) if total else 0
            groups[key] = {"title": ms.title, "repo": issue["repo"],
                           "progress_pct": pct, "progress_text": f"{closed}/{total}",
                           "issues": []}
        groups[key]["issues"].append(issue)

    # Order: unassigned first, then by progress desc, then by milestone title.
    ordered = [groups.pop("__unassigned__")] if groups.get("__unassigned__", {}).get("issues") else []
    ordered += sorted(groups.values(),
                      key=lambda g: (-g["progress_pct"], g["title"]))

    if not ordered:
        return "<section class='card'><p class='empty centered'>No work in progress.</p></section>"

    # Render.
    fragments = []
    for group in ordered:
        children = "".join(_render_issue_row(i) for i in sorted(group["issues"], key=lambda x: x["number"]))
        fragments.append(render.render(
            render.load_template(templates_dir / "partials" / "milestone-group.html"),
            title=group["title"], repo=group.get("repo", ""),
            progress_pct=str(group["progress_pct"]),
            progress_text=group.get("progress_text", ""),
            children_html=children,
        ))
    return "".join(fragments)
```

(Where `_render_issue_row` is a helper that builds the chip list and substitutes into `issue-row.html`.)

- [ ] **Step 4: Update `templates/tabs/in-progress.html`**

```html
{{in_progress_panel_html}}
```

And wire it in `main()`:
```python
in_progress_html = safe_render("in-progress",
    render_in_progress_panel, kanban_data=kanban_data, chain_states=chain_states)
```

- [ ] **Step 5: Run smoke test against real kanban data**

```bash
SHIP_ISSUE_MEMORY_DIR=/tmp/test-dash \
  uv run python cost-dashboard/build-cost-dashboard.py
```

Open the result; switch to `#in-progress`. Confirm milestone groups render and issues link to GH.

- [ ] **Step 6: Commit**

```bash
git add cost-dashboard/templates/ cost-dashboard/build-cost-dashboard.py
git commit -m "feat(dashboard): build In Progress tab with milestone grouping

Pulls status:in-progress + status:in-pr + status:in-review issues across
all repos, joins to milestones via spec_chain_data, groups by milestone
with progress bar. Unassigned milestones surface first; otherwise sorted
by progress desc. Hides triage:rejected. Empty state when no work flows."
```

---

## Task B3 — Comprehensive kanban + filter bar {#kanban-filters}

model: sonnet  effort: L  area: cost-dashboard

**Files:**
- Modify: `cost-dashboard/build-cost-dashboard.py` (`load_kanban_data`, `render_kanban_panel`)
- Modify: `cost-dashboard/static/tabs.js` (filter logic)
- Modify: `cost-dashboard/static/dashboard.css` (filter bar styles)
- Modify: `cost-dashboard/templates/tabs/spec-chain.html`

- [ ] **Step 1: Change `load_kanban_data` to keep all open issues**

Today it drops issues without a `status:*` label. Change so unlabeled issues land in an `"unlabeled"` column. Use `taxonomy.column_order()` to drive column iteration.

```python
def load_kanban_data(repos):
    if os.environ.get("DASHBOARD_SKIP_KANBAN") == "1":
        return {}
    columns = taxonomy.column_order()
    # ... (same gh issue fetch) ...
    out[repo] = {col: [] for col in columns}
    for issue in json.loads(result.stdout):
        names = {l["name"] for l in issue.get("labels", [])}
        target = "unlabeled"
        for col in columns:
            if col != "unlabeled" and col in names:
                target = col
                break
        out[repo][target].append({
            "number": issue["number"], "title": issue["title"],
            "labels": sorted(names),
        })
    return out
```

- [ ] **Step 2: Update `render_kanban_panel` to emit data-attributes for filters**

Each card gets:
```python
f'<a class="card" data-repo="{repo}" data-kind="{kind}" data-effort="{effort}" '
f'data-title="{title.lower()}" href="...">#{n} {title}<span class="meta">...</span></a>'
```

- [ ] **Step 3: Add the filter bar HTML**

In `templates/tabs/spec-chain.html`, prepend before the kanban section:

```html
<section class="card filter-bar">
  <div class="filter-group" data-axis="repo">
    <span class="label">Repo</span>
    {{repo_chips_html}}
  </div>
  <div class="filter-group" data-axis="kind">
    <span class="label">Kind</span>
    {{kind_chips_html}}
  </div>
  <div class="filter-group" data-axis="effort">
    <span class="label">Effort</span>
    {{effort_chips_html}}
  </div>
  <input class="filter-search mono" placeholder="Title search…"/>
  <button class="filter-reset btn">Reset</button>
  <span class="filter-count">Showing <span class="filter-shown">0</span>/<span class="filter-total">0</span></span>
</section>
```

- [ ] **Step 4: Generate chip HTML in Python**

```python
def _filter_chips(axis: str, values: list[str]) -> str:
    return "".join(
        f'<button class="chip filter-chip" data-axis="{axis}" data-value="{v}" data-active="1">{v}</button>'
        for v in values
    )
```

Use this to fill `repo_chips_html` (from `REPOS`), `kind_chips_html` (from canon kinds), `effort_chips_html` (`["S", "M", "L", "XL"]`).

- [ ] **Step 5: Add filter logic to `tabs.js`**

```js
// --- Kanban filters ---
const FILTER_KEY = "cost-dashboard-kanban-filters";

function loadFilters() {
  try {
    return JSON.parse(localStorage.getItem(FILTER_KEY) || "{}");
  } catch { return {}; }
}

function saveFilters(state) {
  localStorage.setItem(FILTER_KEY, JSON.stringify(state));
}

function applyFilters() {
  const state = loadFilters();
  const search = (state.search || "").toLowerCase();
  const cards = document.querySelectorAll(".kanban .card");
  let shown = 0;
  cards.forEach(card => {
    const repo = card.dataset.repo;
    const kind = card.dataset.kind;
    const effort = card.dataset.effort;
    const title = card.dataset.title || "";
    const visible =
      (!state.repo || state.repo[repo] !== false) &&
      (!state.kind || state.kind[kind] !== false) &&
      (!state.effort || state.effort[effort] !== false) &&
      (!search || title.includes(search));
    card.classList.toggle("hidden", !visible);
    if (visible) shown++;
  });
  document.querySelector(".filter-shown").textContent = shown;
  document.querySelector(".filter-total").textContent = cards.length;
  // Sync chip data-active states.
  document.querySelectorAll(".filter-chip").forEach(chip => {
    const axis = chip.dataset.axis;
    const val = chip.dataset.value;
    const active = !state[axis] || state[axis][val] !== false;
    chip.dataset.active = active ? "1" : "0";
  });
}

document.querySelectorAll(".filter-chip").forEach(chip => {
  chip.addEventListener("click", () => {
    const state = loadFilters();
    const axis = chip.dataset.axis;
    const val = chip.dataset.value;
    state[axis] = state[axis] || {};
    state[axis][val] = state[axis][val] === false ? true : false;
    saveFilters(state);
    applyFilters();
  });
});

const searchInput = document.querySelector(".filter-search");
if (searchInput) {
  const saved = loadFilters();
  searchInput.value = saved.search || "";
  searchInput.addEventListener("input", () => {
    const state = loadFilters();
    state.search = searchInput.value;
    saveFilters(state);
    applyFilters();
  });
}

document.querySelector(".filter-reset")?.addEventListener("click", () => {
  saveFilters({});
  if (searchInput) searchInput.value = "";
  applyFilters();
});

applyFilters();
```

- [ ] **Step 6: CSS for filter bar and `.hidden`**

Append to `dashboard.css`:

```css
.filter-bar { display: flex; flex-wrap: wrap; gap: 14px; align-items: center;
  padding: 10px 14px; }
.filter-group { display: flex; gap: 4px; align-items: center; }
.filter-group .label { font-size: 9.5px; }
.filter-chip[data-active="0"] { opacity: 0.4; }
.filter-search { background: var(--bg-sunk); border: 1px solid var(--border-2);
  color: var(--ink-1); padding: 4px 8px; border-radius: 4px; font-family: ui-monospace, monospace;
  font-size: 11px; min-width: 200px; }
.filter-search:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 2px rgba(214,146,90,0.25); }
.filter-reset { font-size: 10px; color: var(--ink-3); background: none; border: none;
  cursor: pointer; text-decoration: underline; }
.filter-count { margin-left: auto; font-size: 10.5px; color: var(--ink-3);
  font-family: ui-monospace, monospace; }
.kanban .card.hidden { display: none; }
```

- [ ] **Step 7: Run smoke + click through filters in browser**

```bash
SHIP_ISSUE_MEMORY_DIR=/tmp/test-dash \
  uv run python cost-dashboard/build-cost-dashboard.py
```

Open output. Switch to Spec Chain tab. Toggle a repo chip → cards in that repo's row should disappear. Type in search → cards not matching hide. Reload page → filter state restored.

- [ ] **Step 8: Commit**

```bash
git add cost-dashboard/
git commit -m "feat(dashboard): comprehensive kanban with frontend filters

load_kanban_data now keeps every open issue (unlabeled lands in new
leading 'unlabeled' column). Columns ordered from taxonomy canon. Filter
bar above the kanban: repo chips, kind chips, effort chips, title search,
reset link, live count. State persisted to localStorage. All filtering
is client-side."
```

---

## Task B4 — Daily-spend 14-day history chart {#spend-history}

model: sonnet  effort: M  area: cost-dashboard

**Files:**
- Create: `cost-dashboard/templates/partials/spend-day.html`
- Modify: `cost-dashboard/build-cost-dashboard.py` (add `aggregate_daily_cost` + `render_spend_history_panel`)
- Modify: `cost-dashboard/templates/tabs/spend.html`

- [ ] **Step 1: Add `aggregate_daily_cost` function**

```python
def aggregate_daily_cost(runs: list[dict], days: int = 14) -> list[dict]:
    """Aggregate runs by UTC date for the last `days` days.

    Returns one row per day (oldest first) with {date, interactive, bot, unknown, total}.
    """
    from collections import defaultdict
    today = datetime.now(timezone.utc).date()
    by_day = defaultdict(lambda: {"interactive": 0.0, "bot": 0.0, "unknown": 0.0})
    for r in runs:
        try:
            dt = datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        d = dt.date()
        if (today - d).days >= days or d > today:
            continue
        src = r.get("source") or "unknown"
        bucket = "interactive" if src == "interactive" else (
            "unknown" if src == "unknown" else "bot")
        by_day[d][bucket] += r.get("api_cost_usd", 0) or 0
    out = []
    for offset in range(days - 1, -1, -1):
        d = today - timedelta(days=offset)
        row = by_day.get(d, {"interactive": 0.0, "bot": 0.0, "unknown": 0.0})
        total = row["interactive"] + row["bot"] + row["unknown"]
        out.append({
            "date": d.strftime("%m-%d %a"),
            **{k: v for k, v in row.items()},
            "total": total,
        })
    return out
```

- [ ] **Step 2: Write `partials/spend-day.html`**

```html
<div class="day">
  <span class="date mono">{{date}}</span>
  <div class="bar">
    <div class="interactive" style="width: {{interactive_pct}}%"></div>
    <div class="bot" style="width: {{bot_pct}}%"></div>
    <div class="unknown" style="width: {{unknown_pct}}%"></div>
  </div>
  <span class="total mono">${{total}}</span>
</div>
```

- [ ] **Step 3: Add `render_spend_history_panel`**

```python
def render_spend_history_panel(runs: list[dict]) -> str:
    rows = aggregate_daily_cost(runs, days=14)
    if not rows:
        return "<p class='empty'>No spend recorded in the last 14 days.</p>"
    max_total = max((r["total"] for r in rows), default=1) or 1
    fragments = []
    for r in rows:
        scale = 100 / max_total if max_total else 0
        fragments.append(render.render(
            render.load_template(templates_dir / "partials" / "spend-day.html"),
            date=r["date"],
            interactive_pct=f"{r['interactive'] * scale:.1f}",
            bot_pct=f"{r['bot'] * scale:.1f}",
            unknown_pct=f"{r['unknown'] * scale:.1f}",
            total=f"{r['total']:.2f}",
        ))
    legend = (
        '<div class="legend">'
        '<span><span class="dot interactive"></span>Interactive</span>'
        '<span><span class="dot bot"></span>Bots</span>'
        '</div>'
    )
    return f'<div class="spend-history">{"".join(fragments)}{legend}</div>'
```

- [ ] **Step 4: Wire into spend tab**

In `templates/tabs/spend.html`, add a card section:

```html
<section class="card">
  <header class="card-head">
    <span class="card-title">Daily spend · last 14 days</span>
  </header>
  {{spend_history_html}}
</section>
```

And in `main()`:
```python
spend_history_html = safe_render("spend-history", render_spend_history_panel, runs=runs)
```

- [ ] **Step 5: Add CSS for spend-history**

Append to `dashboard.css` (port styles from the brainstorm-mockup `spend-tab.html` `.spend-history` rules verbatim).

- [ ] **Step 6: Run smoke + visual check**

```bash
uv run pytest cost-dashboard/tests/ -v
SHIP_ISSUE_MEMORY_DIR=/tmp/test-dash DASHBOARD_SKIP_KANBAN=1 \
  uv run python cost-dashboard/build-cost-dashboard.py
```

Open output. Switch to Spend tab. Confirm 14 day rows render with stacked bars.

- [ ] **Step 7: Commit**

```bash
git add cost-dashboard/
git commit -m "feat(dashboard): add daily-spend 14-day history chart

Aggregates runs.jsonl by UTC date, splits by source (interactive / bot /
unknown). Renders as 14 stacked horizontal bars on the Spend tab. New
aggregator: aggregate_daily_cost(runs, days=14)."
```

---

## Task B5 — Panel-level tests {#panel-tests}

model: sonnet  effort: M  area: tests

**Files:**
- Create: `cost-dashboard/tests/test_panels.py`
- Create: `cost-dashboard/tests/fixtures/kanban-sample.json`

- [ ] **Step 1: Create `fixtures/kanban-sample.json` — 6-8 issues across 2 fake repos**

```json
{
  "fake-repo-a": {
    "status:in-progress": [
      {"number": 1, "title": "wire keyboard cheatsheet", "labels": ["status:in-progress", "kind:feature", "effort:M", "model:sonnet"]}
    ],
    "status:backlog": [
      {"number": 2, "title": "refactor token loader", "labels": ["status:backlog", "kind:chore", "effort:S"]}
    ],
    "unlabeled": [
      {"number": 3, "title": "investigate flaky test", "labels": []}
    ]
  },
  "fake-repo-b": {
    "status:in-pr": [
      {"number": 10, "title": "fix race condition in adapter", "labels": ["status:in-pr", "kind:bug", "effort:L", "model:opus", "priority:high"]}
    ]
  }
}
```

- [ ] **Step 2: Write `test_panels.py`**

```python
"""Per-panel tests with frozen fixtures."""
from __future__ import annotations
import json
from pathlib import Path
import sys

FIX = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_cost_dashboard as bcd  # noqa: E402
import taxonomy  # noqa: E402

taxonomy.load_canon(Path(__file__).resolve().parents[2] / "scripts" / "sync-labels-canon.json")


def test_render_in_progress_empty_state():
    out = bcd.render_in_progress_panel({}, [])
    assert "No work in progress" in out


def test_render_in_progress_with_unassigned_group():
    kd = json.loads((FIX / "kanban-sample.json").read_text())
    out = bcd.render_in_progress_panel(kd, [])
    assert "Unassigned" in out
    assert "#1" in out
    assert "#10" in out
    assert "wire keyboard cheatsheet" in out


def test_aggregate_daily_cost_returns_14_rows():
    rows = bcd.aggregate_daily_cost([], days=14)
    assert len(rows) == 14
    # All zero when no runs.
    assert all(r["total"] == 0 for r in rows)


def test_aggregate_daily_cost_buckets_by_source():
    today_iso = bcd.datetime.now(bcd.timezone.utc).isoformat()
    runs = [
        {"timestamp": today_iso, "source": "interactive", "api_cost_usd": 1.5},
        {"timestamp": today_iso, "source": "ship-issue-x", "api_cost_usd": 0.5},
    ]
    rows = bcd.aggregate_daily_cost(runs, days=1)
    assert rows[-1]["interactive"] == 1.5
    assert rows[-1]["bot"] == 0.5
    assert rows[-1]["total"] == 2.0


def test_kanban_unlabeled_column_present():
    """Smoke: column_order() includes unlabeled as first column."""
    cols = taxonomy.column_order()
    assert cols[0] == "unlabeled"
```

- [ ] **Step 3: Run all dashboard tests**

Run: `uv run pytest cost-dashboard/tests/ -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add cost-dashboard/tests/
git commit -m "test(dashboard): per-panel coverage for in-progress + spend history

Tests render_in_progress_panel empty state and unassigned-group path;
aggregate_daily_cost bucketing logic; taxonomy column ordering."
```

---

## Task B6 — Open PR 2 {#pr2-merge}

model: sonnet  effort: S  area: workflow

- [ ] **Step 1: Verify all tests pass**

Run: `uv run pytest cost-dashboard/tests/ -v`
Expected: 100% pass.

- [ ] **Step 2: Open PR 2**

```bash
git push -u origin <branch-name>
gh pr create --title "feat(dashboard): In Progress tab + comprehensive kanban + spend history (PR 2/2)" \
  --body "$(cat <<'EOF'
## Summary
- In Progress tab: milestone-grouped view with progress bars
- Kanban: every open issue (not just status-labeled), filter bar (repo/kind/effort/search), localStorage persistence
- Daily spend 14-day history chart on Spend tab
- Existing panels restructured to card surfaces with token-styled chips

## Test plan
- [ ] uv run pytest cost-dashboard/tests/ passes
- [ ] In Progress tab shows milestone groups; click-through works
- [ ] Kanban filters toggle visibility; state persists across reload
- [ ] Spend history chart renders 14 days

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-review checklist

- [ ] Every requirement in spec §3-§9 maps to a task here
- [ ] PR 1 ships a working themed dashboard with the same content as today
- [ ] PR 2 ships In Progress, kanban filters, spend history, card-surface restructure
- [ ] All `uv run pytest cost-dashboard/tests/` invocations pass
- [ ] No backwards-compat shims for the old monolithic HTML_TEMPLATE
- [ ] Output remains a single-file HTML at `$SHIP_ISSUE_MEMORY_DIR/cost-dashboard.html`
- [ ] DASHBOARD_SKIP_KANBAN=1 and DASHBOARD_SKIP_CHAIN=1 still work

When all checked, this plan is done.
