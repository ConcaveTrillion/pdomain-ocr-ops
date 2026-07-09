# OCR Labeler · Hi-Fi Design Language

This document distills the visual choices into a reusable system. The app supports **both dark and light modes** — every surface, every component, every state. Token tables below list both values. Apply the token, not the literal color.

## Aesthetic direction

A dense, terminal-adjacent UI inspired by the sister app **pgdp-prep**. The product is a power-user tool used for long sessions; the visual language gets out of the way and reserves color for **meaning** (status, layer kind, action priority).

Three rules:

1. **Color is semantic, not decorative.** Status / layer / accent only. Neutrals carry chrome.
2. **Mono font for everything code-shaped.** OCR text, GT text, coordinates, IDs, keyboard shortcuts.
3. **Subtle borders > shadows.** Both themes gain depth from elevation steps and 1-px borders, not large drop-shadows.

The default theme is **dark**. Light mode must be reachable via a user toggle and respect `prefers-color-scheme`. Persist the choice. All tokens, components, and states must render identically in structure across modes; only color values flip.

## Color tokens

### Surfaces (warm-charcoal scale)

| Token        | Dark       | Light      | Use                                       |
|--------------|------------|------------|-------------------------------------------|
| `bgPage`     | `#0c0c10`  | `#f6f4ef`  | Page background, top header, rail         |
| `bgSurface`  | `#15151b`  | `#ffffff`  | Cards, panels, drawer, right panel        |
| `bgRaised`   | `#1d1d24`  | `#ecebe5`  | Buttons, hover, active rows, breadcrumb chips |
| `bgSunk`     | `#08080c`  | `#f0eee7`  | Inputs, code wells, sunken sections       |

Note: light mode surfaces use a warm cream tint (matches the page-scan aesthetic the app surrounds). Pure white reserved for cards / canvases.

### Borders (3-step)

| Token       | Dark       | Light      | Use                                            |
|-------------|------------|------------|------------------------------------------------|
| `border1`   | `#222229`  | `#d8d4c8`  | Default panel/section divider                  |
| `border2`   | `#2f2f38`  | `#c2bdaf`  | Button border, input border, chip border       |
| `border3`   | `#3f3f49`  | `#a39e8d`  | High-contrast key-cap border, input focus ring |

### Text (4-step)

| Token   | Dark       | Light      | Use                                                 |
|---------|------------|------------|-----------------------------------------------------|
| `ink1`  | `#f0f0f2`  | `#1a1810`  | Primary text, headings, value text                  |
| `ink2`  | `#b0b0b8`  | `#4a4538`  | Secondary text, button label, breadcrumb non-active |
| `ink3`  | `#7a7a85`  | `#7c7665`  | Hints, helper text, micro-labels                    |
| `ink4`  | `#4e4e58`  | `#b0aa95`  | Disabled, ID dim, separator glyphs                  |

### Accent

| Token    | Dark        | Light       | Use                                          |
|----------|-------------|-------------|----------------------------------------------|
| `accent` | `#d6925a`   | `#b85a2e`   | Primary CTAs, active selection on canvas/breadcrumb, focus state, brand mark |
| `accentInk` | `#1a0f08` | `#ffffff`   | Text *on top of* accent backgrounds         |

The dark accent (`#d6925a`) is amber for contrast against charcoal; the light accent (`#b85a2e`) is a deeper terracotta for contrast against cream. Same role, different saturation.

### Status (5)

| Token       | Dark       | Light      | Meaning                          |
|-------------|------------|------------|----------------------------------|
| `exact`     | `#5fbf6a`  | `#2d8c3a`  | OCR == GT                        |
| `fuzzy`     | `#e8a83a`  | `#b87b1f`  | OCR ≈ GT                         |
| `mismatch`  | `#dc6555`  | `#b13d32`  | OCR ≠ GT                         |
| `ocr`       | `#5d9fdf`  | `#2d6fb5`  | OCR with no GT match · style kind|
| `gt`        | `#a888d4`  | `#6e4ea5`  | GT with no OCR match · component kind |

Status chips use a `+ '1a'` (10% alpha) fill of the same color in both modes, with a `+ '55'` (33%) border. The contrast ratio of text on tinted background stays readable in both.

### Layers (4) — canvas + UI chips

| Token   | Dark       | Light      | Used for                |
|---------|------------|------------|-------------------------|
| `block` | `#a89074`  | `#7a5e3a`  | Structural block (taupe)|
| `para`  | `#7fb56a`  | `#4d8a3a`  | Paragraph (green)       |
| `line`  | `#d088a8`  | `#a8527a`  | Line (pink)             |
| `word`  | `#6e9cdf`  | `#3d6bb8`  | Word (blue)             |

On canvas overlays use `mix-blend-mode: multiply` in both modes — the scan stays readable underneath.

## Typography

| Family            | Use                                                          |
|-------------------|--------------------------------------------------------------|
| **Inter** 400–700 | UI body, labels, button text                                 |
| **PGDP custom monospace** (JetBrains Mono as placeholder) | OCR + GT text, IDs (`B2.2.2`, `L7·W1`), coordinates, keyboard shortcuts, file paths, confidence percentages |
| **Times New Roman / serif** | Page-scan content rendering only (replace with actual scan in production) |

### Scale

| Role             | Size  | Weight | Notes                                       |
|------------------|-------|--------|---------------------------------------------|
| Section heading  | 13 px | 700    | "Line 7 · Word 1"                           |
| Body / button    | 12 px | 500    | Default                                     |
| Small button     | 11 px | 500    | `.btn.sm`                                   |
| Helper / hint    | 10 px | 400    | Tertiary lines                              |
| Label (uppercase)| 9.5 px| 700    | Letter-spacing 0.1em, ink3                  |
| Pip / chip       | 10 px | 600    | Status pip, chip                            |
| Key cap          | 9.5 px| 500    | Mono, sunken surface                        |

## Component primitives

Same primitives in both modes — token-based, so the swap is automatic. Listed once.

### Buttons

Base — 30 px tall, 12 px x-padding, 6 px radius, `bgRaised` background, `border2` border, `ink1` label. Hover lifts background.

Variants: `.primary` (accent bg + accentInk text), `.ghost` (transparent), `.danger` (mismatch tint), `.icon` (square). Sizes: `.sm` (24 px), default (30 px), `.lg` (34 px).

### Chips

**Static chip** — 20 px tall, 10-px radius pill, `bgRaised` bg, `border2`, `ink2` label.

**Tri-state chip** — 24 px tall, 12-px radius. State controls fill + border:
- **none**: `bgRaised` bg, `ink2` text, `border2`
- **some**: `bgRaised` bg, base text + border, hatched circle
- **all**: 10%-tint of base, full base text + border, filled circle with check

Optional hotkey key-cap trails inside the chip.

### Status pip

18 px tall, 9-px radius. Background `status + '1a'`, text `status`, border `status + '55'`. Leading 5-px dot.

### Inputs

`bgSunk` background, `border2`, 5-px radius. Mono font for code-shaped content. Focus ring: `accent` border + 2-px outer glow.

### Key caps

`bgSunk` bg, `border3` border with extra bottom-pixel for depth. Mono.

### Section headers

Uppercase tracked labels: 9.5 px / 700 / 0.1em tracking / `ink3`.

### Accordion sections

- Container: `bgSunk`, 6-px radius, `border1` border.
- Header row: chevron + uppercase label + helper text + right-aligned hotkey.
- Accent-tagged variants (Rebox = `accent`, Erase = `mismatch`) use a 12%-tinted bg and 33%-alpha colored border.

### Tabs

Underline tabs. Active: `accent` 2-px underline, `ink1` label. Count badge: `accent + '33'` bg when active.

## Spacing

4-px base. Common sequence: 4 / 6 / 8 / 10 / 12 / 14 / 18 / 24 / 32. Inter-section gap = 14 px. Card padding = 12–16 px. Inline button gap = 6 px.

## Radii

3 px (key caps) · 4 px (small pills) · 5 px (inputs, small buttons) · 6 px (buttons, cards, accordions) · 8 px (layout-type cards) · 9 px (status pip) · 12 px (tri-state chip) · 14 px (avatar).

## Elevation pattern

Surfaces step from `bgPage` → `bgSurface` → `bgRaised` → `bgSunk`. Borders trace boundaries. Avoid drop shadows except floating chrome — cap at `0 3px 10px rgba(0,0,0,0.15)` (dark) / `0 3px 10px rgba(60,40,20,0.1)` (light).

## Theme implementation

Use CSS custom properties. One block of variables under `:root` (dark default) and another under `[data-theme="light"]`. Components reference `var(--bg-surface)` etc. Toggle by setting `data-theme` on `<html>`.

```css
:root {
  --bg-page: #0c0c10;
  --bg-surface: #15151b;
  --ink-1: #f0f0f2;
  --accent: #d6925a;
  --accent-ink: #1a0f08;
  /* ...all tokens */
}
[data-theme="light"] {
  --bg-page: #f6f4ef;
  --bg-surface: #ffffff;
  --ink-1: #1a1810;
  --accent: #b85a2e;
  --accent-ink: #ffffff;
  /* ...all tokens */
}
```

Mode logic:
1. On boot: read `localStorage.theme`. If set, use it.
2. Otherwise: match `window.matchMedia('(prefers-color-scheme: light)')`.
3. Toggle persists to localStorage.
4. Expose a toggle in the user-menu (top-right avatar) or in Settings.

## Selection language

How a user reads "what is selected":

1. **Rail TARGET** — colored `B/L/W` cell with 1-px border in the level color.
2. **Canvas highlight** — 2-px accent outline + 10% accent tint.
3. **Breadcrumb terminal** — deepest segment filled 10%-tinted in its kind color.
4. **Drawer row** — accent border around selected hierarchy row.

## Status language

`✓ green` exact · `~ amber` fuzzy · `✗ red` mismatch · `○ blue/purple` unmatched.

## Density toggle

`Density: Cards | Rows` segmented in bulk toolbar. Default Cards. Persist per scope.

## Layer-color usage

Layers are the canvas's domain. Carry into UI only for:
- Indicating depth in a tree (kind chip).
- Indicating "what kind of thing am I editing" in a breadcrumb terminal.
- Style vs component chips (style → `ocr` blue, component → `gt` purple).

Never as decoration.

## Hotkeys

Always show key caps next to affordances. `V/R/A/E` (modes) · `1/2/3` (target) · `J/K` (worklist) · `⌥arrows` (tree walk) · `F/B/X/R/S` (word-detail sections) · `⌘K` (palette) · `⌘ /` or `?` (cheatsheet).

## Motion

- Button hover: 120 ms.
- Tab swap: instant.
- Drawer collapse: 180 ms width.
- Accordion expand: 200 ms height.
- Theme swap: instant (no fade — flicker is worse).

## Asset bundling

PGDP custom monospace bundled locally · Inter system or local · no icon font (unicode + small SVG layout-type glyphs).

## Migration to your codebase

Three steps:

1. Copy the dual `:root` / `[data-theme="light"]` CSS variable block into your token layer.
2. Build the 8 primitives (Button, Chip, ChipState, StatusPip, Input, KeyCap, Accordion, Tab) referencing only the tokens.
3. Compose surfaces. Theme toggle becomes free.
