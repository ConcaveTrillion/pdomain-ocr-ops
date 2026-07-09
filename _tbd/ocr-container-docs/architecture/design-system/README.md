# ocr-project-prep · Design System

A drop-in design system for power-user OCR / labeling / pipeline tools. Dense, terminal-adjacent, dual-theme (dark default + light). Color is reserved for **meaning** (status · layer · accent), neutrals carry the chrome.

## What's in this folder

| File | What it is |
|---|---|
| **`DESIGN_LANGUAGE.md`** | The canonical spec — read this first. Tokens, type scale, components, motion, hotkeys, mode rules. |
| **`tokens.css`** | All design tokens as CSS custom properties. Two themes: `:root` (dark) and `[data-theme="light"]`. |
| **`primitives.css`** | Every primitive class (`.btn`, `.chip`, `.pip`, `.input`, `.key`, `.stage-cell`, `.tabs`, etc.) — pure CSS, references only tokens. |
| **`ui-kit.html`** + **`ui-kit.jsx`** | The live UI kit — every primitive, every state, both themes, with a theme toggle. Open `ui-kit.html` in a browser to browse it. |

## Quick start (10 seconds)

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">

<link rel="stylesheet" href="tokens.css">
<link rel="stylesheet" href="primitives.css">
```

Then use the classes:

```html
<button class="btn primary">Build package</button>
<span class="pip" style="color:var(--exact);
  background:color-mix(in srgb, var(--exact) 10%, transparent);
  border:1px solid color-mix(in srgb, var(--exact) 33%, transparent);">
  <span class="dot" style="background:var(--exact)"></span>Done
</span>
<input class="input mono" placeholder="scan_0033.tif">
<kbd class="key">⌘</kbd><kbd class="key">K</kbd>
```

Flip themes by setting `data-theme="light"` (or removing it for dark) on `<html>`. See the toggle in `ui-kit.html` for the localStorage + `prefers-color-scheme` recipe.

---

## Prompt to give Claude

Paste this into a new chat after attaching the zip:

> Use the attached design system. The files are:
> - `DESIGN_LANGUAGE.md` — the spec. Read it first.
> - `tokens.css` — token block. Link it on every HTML page you produce.
> - `primitives.css` — primitive classes. Link it after tokens.
> - `ui-kit.html` / `ui-kit.jsx` — the live reference showing every primitive in every state. Open this if you're unsure what something should look like.
>
> Rules:
> 1. **Reference tokens, not literals.** Use `var(--bg-surface)`, `var(--accent)`, `var(--exact)` etc. Never hard-code `#15151b` or `#d6925a`.
> 2. **Color is semantic.** Status → `--exact`/`--fuzzy`/`--mismatch`/`--ocr`/`--gt`. Layer → `--block`/`--para`/`--line`/`--word`. Accent → `--accent` only for primary CTAs, selection, focus, brand mark. Neutrals carry everything else.
> 3. **Mono for code-shaped content.** OCR text, GT text, IDs (`P0033`, `B2·L7·W1`), filenames, timestamps, durations, confidence values, bbox coords, file paths, hotkey caps — all `--mono-font`. UI labels and prose stay in `--ui-font` (Inter).
> 4. **Borders, not shadows.** Depth comes from stepping `--bg-page` → `--bg-surface` → `--bg-raised` → `--bg-sunk` and tracing with 1-px borders. Drop shadows only for floating chrome (use `--shadow-floating`).
> 5. **Both themes always work.** Test with `data-theme="light"` on `<html>` — the design must look intentional in both modes. Only color values flip; structure, density, type sizes stay identical.
> 6. **Use primitive classes from `primitives.css`.** Don't re-invent the button. If you need a variant, extend the class (`.btn.my-variant`) or compose inline-styles referencing tokens — don't write fresh button CSS from scratch.
> 7. **Density.** 12 px body, 13 px headings, 9.5 px tracked uppercase labels. Buttons are 30 px tall by default. Inter-section gap is 14 px. Card padding 12–16 px.
> 8. **Hotkeys are part of the UI.** When you add an action with a hotkey, surface the key cap (`.key`) next to it.
>
> Before writing any new component CSS, check `primitives.css` to see if it already exists.

---

## Token reference cheatsheet

```
Surfaces   --bg-page --bg-surface --bg-raised --bg-sunk
Borders    --border-1 --border-2 --border-3
Text       --ink-1 --ink-2 --ink-3 --ink-4
Accent     --accent --accent-ink
Status     --exact --fuzzy --mismatch --ocr --gt
Layers     --block --para --line --word
Type       --ui-font --mono-font
```

Tinted fills follow the pattern `color-mix(in srgb, var(--TOKEN) 10%, transparent)` for fills and `33%` (or `40%`) for borders. Use these instead of inventing new shades.

## Mode boot

```js
const t = localStorage.getItem('theme')
  || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
document.documentElement.setAttribute('data-theme', t);
```

Persist on toggle. The theme swap is instant — no fade.

## Common patterns

- **Stat tiles**: big mono numeral in tone color (`--exact` for ready, `--fuzzy` for blocking, `--ocr` for in-progress), uppercase label below, mono helper line beneath. Group as one card row with `--border-1` dividers.
- **Banners**: tint card with `status × 8%` background and `status × 35%` border. Status icon at left. Primary action on the right.
- **Filter chips**: neutral `.filter-chip` + `.on` for active (accent 14% fill, accent 45% border, accent text). Count number always mono tabular.
- **Tabs**: underline only. Active tab has 2-px accent underline; count badge gets accent 20% fill when active, `--bg-raised` neutral when not.
- **Selection** reads in 4 concurrent places: rail target chip (layer color), canvas outline (2-px accent + 10% accent tint), breadcrumb terminal (layer color), drawer row border (accent).

Everything else: open `ui-kit.html` and look.
