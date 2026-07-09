---
milestone: 9
repo: ConcaveTrillion/ocr-container-meta
status: complete
synced: 2026-05-17
---

# pdomain-ui — new TS/React/Vite shared component library

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the new repo `pdomain-ui` — a TypeScript / React / Vite library that becomes the shared frontend surface for every pd-* end-user SPA (labeler-spa, pgdp-prep, trainer-spa, simple-gui, future proofreader). It owns the canvas, worklist, app shell, design-system primitives, icons, generated types, and Zustand store factories. Phase 1 ships `@concavetrillion/pdomain-ui@0.1.0-alpha` to the self-hosted `pdomain-index-npm` registry.

**Spec reference:** [`docs/superpowers/specs/2026-05-16-cross-cut-design.md`](../specs/2026-05-16-cross-cut-design.md), in particular:
- §4 (component surface, Key API conventions, what pdomain-ui does not include, shared UI prefs)
- §5 (type contract, codegen pipeline, `*Like` reductions, naming)
- §6 (slot / render-prop API for `<PageImageCanvas>`, `<WordList>`, `<AppShell>`, hooks)
- §7 Phase 1 row 1.5 (this plan's scope)
- §8 Frontend impact (deployMode, useStageCall/useLongJob — interfaces only in Phase 1)

**Hard dependencies (sequencing):**

1. **Plan #1 (pdomain-book-tools ReviewMetadata + schemas.emit)** must ship before M4 (codegen) can succeed. Until then, M0–M3 + M5–M7 (scaffold, theme, primitives, icons, ported components against hand-written placeholder types) can run in parallel — but the placeholder types are explicitly thrown away in M4. See spec §7.1 footnote: *"Track 1.5 needs 1.1's schema emitter for codegen; scaffold/Storybook/component porting can start immediately."*
2. **Plan #4 (pdomain-index-npm registry)** must be live before M10 (publish). Build + version + dry-run packaging in M10 can be exercised against a `--dry-run` npm publish before then.
3. **Plan #3 (pdomain-ocr-ops)** is NOT a hard dependency for Phase 1 pdomain-ui — pdomain-ui never imports pdomain-ocr-ops. The suite-prefs + sibling launch hooks (M8) are wired through callback props supplied by the host app; the corresponding HTTP contract lives in pdomain-ocr-ops route helpers, which apps mount. Phase 1 pdomain-ui ships these hooks against fetch URL constants documented in the spec; integration with real backends is Phase 2 work in each consuming app.

**Hard design principles (constraints on every task below):**

- **Deploy-mode-agnostic** (spec §1.4). pdomain-ui never branches on hosted-vs-local. `<AppShell deployMode>` flips wording / hides local-only menu items only. All real mode logic is in pdomain-ocr-ops adapters.
- **No CVA** (spec §4, §2.5b). Variants are CSS class modifiers on design-system primitives (`.btn.primary`, `.chip.tristate`, …). React wrappers compose class names — they do not generate styles.
- **No Tailwind color/theme utilities** (spec §2.5b). Layout utilities only if Tailwind is included; for Phase 1 pdomain-ui itself omits Tailwind entirely — apps may keep it scoped to layout. pdomain-ui's own components are pure CSS-class + token references.
- **No direct lucide-react imports outside `pdomain-ui/icons`** (spec §4, §8 icon strategy). pdomain-ui re-exports a curated subset; apps import only from `@concavetrillion/pdomain-ui/icons`.
- **No singletons** (spec §4). Every store is a factory function returning a fresh Zustand store; apps instantiate per-AppShell.
- **Port-not-copy** for ported components. The labeler-spa implementations of `PageImageCanvas`, `LineCard` / worklist, and `StudioShell` (at `/workspaces/ocr-container/pdomain-ocr-labeler-spa/frontend/src/components/`) are the source-of-truth. Each ported component is restructured under the slot-based API from spec §6 — *not* a verbatim copy. The executing engineer reads the labeler-spa version once, designs the slot surface that subsumes it, then ports.

**Tech stack:**

- Node 20 LTS (managed via mise like the rest of the workspace).
- pnpm 9 (matches the optional `pnpm-workspace.yaml` overlay from spec §3 install model).
- TypeScript 5 strict (`"strict": true`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`).
- Vite 5 library mode (`vite.config.ts` with `build.lib.entry` + per-subpath entry points).
- Vitest 1 + `@testing-library/react` for component tests.
- ESLint flat config + `eslint-plugin-react-hooks`, `eslint-plugin-jsx-a11y`, no Prettier (matches workspace `pdomain-prep-for-pgdp` / labeler-spa conventions; check those before scaffolding).
- Storybook 8 (React + Vite builder).
- Konva + react-konva (for `<PageImageCanvas>`, matching the labeler-spa stack).
- Zustand 4 (store factories).
- Radix UI primitives (scoped to `@radix-ui/react-dialog`, `react-alert-dialog`, `react-popover`, `react-tooltip`, `react-dropdown-menu`, `react-select`, `react-tabs`, `react-toggle-group` per spec §4).
- `react-virtuoso` or `@tanstack/react-virtual` for `<WordList>` virtualization (pick whichever the labeler-spa worklist uses, to keep port mechanical).
- `lucide-react` (curated re-exports only).
- `openapi-typescript` for codegen (consumes JSON Schema → TS types).

**Working directory for all commands:** `/workspaces/ocr-container/pdomain-ui/`

**ConcaveTrillion metadata** (copy from peer pd-* repos; spec §0 memory rule "never invent author/org/URL"):
- `author`: `CT <concavetrillion@gmail.com>`
- `repository`: `https://github.com/pdomain/pdomain-ui.git`
- `license`: `MIT` (match peer repos; verify by reading one peer `LICENSE` before writing)
- `homepage`: `https://github.com/pdomain/pdomain-ui`

---

## Milestone M0: Repo scaffold

Stand up the empty repo skeleton so every subsequent milestone has a place to land. No components yet.

### Task M0.1: Create directory + .gitignore + LICENSE + README stub {#create-directory-gitignore-license-readme-stub}

**Why:** New repo needs file-system identity before `git init`.

**What:** Create `/workspaces/ocr-container/pdomain-ui/` with:

- `.gitignore` — copy from `pdomain-ocr-labeler-spa/.gitignore` (Node + Vite + Vitest + `.codegen/` + `dist/` + `storybook-static/`).
- `LICENSE` — copy verbatim from `pdomain-ocr-labeler-spa/LICENSE` (MIT, ConcaveTrillion).
- `README.md` — minimal: title, one-paragraph mission, "see [`docs/superpowers/specs/2026-05-16-cross-cut-design.md`](...) for design"`.
- `CLAUDE.md` — copy structure from `pdomain-ocr-labeler-spa/CLAUDE.md`; populate with pdomain-ui specifics (TS strict, Vitest, Storybook, codegen-from-pdomain-book-tools).

**TDD steps:** None — pure scaffold.

**Acceptance:** Files exist; `git init` succeeds; `git status` is clean after first add+commit.

### Task M0.2: package.json with ConcaveTrillion metadata {#packagejson-with-concavetrillion-metadata}

**Why:** Drives npm publish, dependency resolution, subpath imports.

**What:** Create `package.json` with:

- `"name": "@concavetrillion/pdomain-ui"`
- `"version": "0.0.0"` (M10 bumps to `0.1.0-alpha`)
- `"type": "module"`
- `"publishConfig": { "registry": "https://concavetrillion.github.io/pdomain-index-npm/" }` (or whatever URL plan #4 settles on)
- `"exports"` map with subpaths: `.`, `./canvas`, `./worklist`, `./shell`, `./primitives`, `./icons`, `./types`, `./stores`, `./theme/tokens.css`, `./theme/primitives.css`, `./testids`. Each maps to a built ESM file with a TS `types` entry.
- `"sideEffects": ["**/*.css"]` so CSS imports survive tree-shaking.
- `"files": ["dist", "theme", "README.md", "LICENSE"]`.
- ConcaveTrillion `author` / `repository` / `homepage` per peer repos.
- `"engines": { "node": ">=20" }`.
- `peerDependencies`: `react` ^18, `react-dom` ^18.
- `dependencies`: konva, react-konva, zustand, `@radix-ui/react-{dialog,alert-dialog,popover,tooltip,dropdown-menu,select,tabs,toggle-group}`, lucide-react, virtualization lib.
- `devDependencies`: typescript, vite, vitest, `@testing-library/react`, `@testing-library/user-event`, jsdom, eslint + plugins, storybook + builder-vite, `openapi-typescript`, `@types/react`, `@types/node`.

**TDD steps:**

- [ ] Vitest test `tests/package.contract.test.ts` asserting:
  - `package.json.name === "@concavetrillion/pdomain-ui"`
  - `package.json.exports` has every subpath in spec §4 module map
  - `package.json.dependencies` does NOT include `class-variance-authority`
  - `package.json.dependencies` does NOT include `tailwindcss`
  - `package.json.peerDependencies` requires React 18

**Acceptance:** Test passes. `npm pack --dry-run` lists `theme/`, `dist/`, README, LICENSE, no source.

### Task M0.3: tsconfig.json (strict) {#tsconfigjson-strict}

**Why:** Strict TS catches the `*Like` reduction breakages spec §5 calls out.

**What:** Create `tsconfig.json` extending `@tsconfig/strictest` (or hand-rolled equivalent) with:

- `"strict": true`
- `"noUncheckedIndexedAccess": true`
- `"exactOptionalPropertyTypes": true`
- `"moduleResolution": "bundler"`
- `"jsx": "react-jsx"`
- `"target": "ES2022"`
- `"paths"` mapping `@/*` → `./src/*` (matches labeler-spa convention).

Plus `tsconfig.build.json` excluding `**/*.test.tsx`, `**/*.test.ts`, `tests/**`, `stories/**`.

**TDD steps:**

- [ ] Vitest test `tests/tsconfig.contract.test.ts` parses `tsconfig.json` and asserts the strict flags above are set.

**Acceptance:** `npx tsc --noEmit` exits 0 against an empty `src/`.

### Task M0.4: Vite library-mode build config {#vite-library-mode-build-config}

**Why:** Library mode produces ESM with proper subpath outputs.

**What:** Create `vite.config.ts` with:

- `build.lib.entry` = an object mapping each subpath (`canvas`, `worklist`, `shell`, `primitives`, `icons`, `types`, `stores`, `testids`, `index`) to its source entry file under `src/`.
- `build.rollupOptions.external`: react, react-dom, react/jsx-runtime, all listed `peerDependencies`, and all `dependencies` (so consumers dedupe).
- `build.cssCodeSplit: true`.
- `plugins`: `@vitejs/plugin-react`, `vite-plugin-dts` (for `.d.ts` generation).

**TDD steps:**

- [ ] Vitest test `tests/build.contract.test.ts` runs `vite build` programmatically against a 2-file fixture in `tests/fixtures/build-smoke/` and asserts `dist/index.js`, `dist/canvas.js`, etc. exist.

**Acceptance:** `pnpm run build` against an empty placeholder `src/index.ts` produces `dist/index.js` + `dist/index.d.ts`.

### Task M0.5: Vitest config {#vitest-config}

**Why:** `make ci` needs `pnpm test` to run.

**What:** Create `vitest.config.ts` with:

- `environment: 'jsdom'`
- `setupFiles: ['tests/setup.ts']` (extends `expect` with `@testing-library/jest-dom`)
- `coverage` config: provider `v8`, thresholds (lines/branches/functions/statements) at 80 for now, raise in M9.

**TDD steps:**

- [ ] Smoke test `tests/setup.smoke.test.ts` renders `<div data-testid="x">ok</div>` and asserts `screen.getByTestId('x').textContent === 'ok'`.

**Acceptance:** `pnpm test` runs the smoke test and exits 0.

### Task M0.6: ESLint flat config {#eslint-flat-config}

**Why:** Workspace convention; pre-commit hook will rely on it.

**What:** Create `eslint.config.js` (flat) with:

- `@typescript-eslint` recommended + strict typed rules.
- `eslint-plugin-react-hooks` (rules-of-hooks + exhaustive-deps).
- `eslint-plugin-jsx-a11y` recommended.
- Custom rule: no direct import from `lucide-react` outside `src/icons/` (use `no-restricted-imports`).
- Custom rule: no import of `class-variance-authority` anywhere (`no-restricted-imports`).

**TDD steps:**

- [ ] Vitest test `tests/eslint.contract.test.ts` programmatically lints two fixture files: (a) `tests/fixtures/lint-bad/lucide-direct.tsx` importing from `lucide-react` — must report the custom rule; (b) `tests/fixtures/lint-bad/cva.ts` importing `class-variance-authority` — must report. A `lint-good/` fixture must pass clean.

**Acceptance:** Test passes; `pnpm run lint` on a fresh repo lints zero source files clean.

### Task M0.7: Makefile + CI gate {#makefile-ci-gate}

**Why:** Matches per-repo `make ci AI=1` convention from CLAUDE.md.

**What:** Create `Makefile` with targets:

- `install` — `pnpm install --frozen-lockfile`
- `lint` — `pnpm run lint`
- `typecheck` — `pnpm run typecheck`
- `test` — `pnpm run test`
- `build` — `pnpm run build`
- `codegen` / `codegen-check` (placeholders; wired in M4)
- `frontend-build` — alias for `build`
- `ci` — `install lint typecheck test build codegen-check` chained; supports `AI=1` mode flag

**TDD steps:** None — Makefile contract verified by running `make ci AI=1` at the end of every later milestone.

**Acceptance:** `make ci AI=1` against the empty scaffold exits 0.

### Task M0.8: First commit + agent definitions {#first-commit-agent-definitions}

**Why:** Workspace CLAUDE.md routing requires `.claude/agents/pdomain-ui.md` + `.claude/agents/pdomain-ui-docs.md` to exist before any sibling agent can dispatch into pdomain-ui.

**What:** Add two agent definition files under workspace `/workspaces/ocr-container/.claude/agents/`:

- `pdomain-ui.md` — full-power agent. Use `pdomain-ocr-labeler-spa.md` as the template; swap repo path, drop NiceGUI-specific bits, add codegen-from-pdomain-book-tools mention.
- `pdomain-ui-docs.md` — Haiku read-only `-docs` sibling. Use `pdomain-ocr-labeler-spa-docs.md` as template.

Update workspace CLAUDE.md routing table to list pdomain-ui among the eight (now nine) repos.

**TDD steps:**

- [ ] Bash check: `test -f .claude/agents/pdomain-ui.md && test -f .claude/agents/pdomain-ui-docs.md`
- [ ] grep CLAUDE.md for `pdomain-ui/` row

**Acceptance:** Workspace `make ci` (if any) passes; routing table includes pdomain-ui.

---

## Milestone M1: Theme migration (design-system → pdomain-ui/theme)

Move `tokens.css` and `primitives.css` from `/workspaces/ocr-container/docs/design-system/` into `pdomain-ui/theme/` as the canonical runtime home. Ship a sync script that mirrors changes back to `docs/design-system/` snapshots, so the workspace-level docs stay aligned with what pdomain-ui actually ships.

### Task M1.1: Copy tokens.css and primitives.css into pdomain-ui/theme/ {#copy-tokenscss-and-primitivescss-into-pd-uitheme}

**Why:** Spec §4 module map and §7.1 row 1.5 — pdomain-ui owns the runtime source-of-truth.

**What:** Create `pdomain-ui/theme/` and copy:

- `docs/design-system/tokens.css` → `pdomain-ui/theme/tokens.css`
- `docs/design-system/primitives.css` → `pdomain-ui/theme/primitives.css`

Do not edit content yet — byte-for-byte copy.

**TDD steps:**

- [ ] Vitest test `tests/theme/snapshot.test.ts` reads both files in `pdomain-ui/theme/` and asserts:
  - `tokens.css` contains `:root {` AND `[data-theme="light"] {` (dual-theme blocks)
  - `primitives.css` contains class selectors `.btn`, `.chip`, `.pip`, `.input`, `.key` (verifies the primitives that wrappers in M2 will use)
- [ ] Vitest test `tests/theme/no-hex-in-primitives.test.ts` asserts `primitives.css` references only `var(--…)` and never raw `#`-hex literals (per spec §4 rule 5).

**Acceptance:** Both tests pass. Files exist.

### Task M1.2: Sync-back script (pdomain-ui → docs/design-system) {#sync-back-script-pdomain-ui-docsdesign-system}

**Why:** Spec §4: "a sync script in pdomain-ui's release updates docs/design-system/ snapshots". Workspace-level docs stay in lockstep with shipping CSS.

**What:** Create `scripts/sync-design-system.mjs` (Node ESM) that:

- Reads `pdomain-ui/theme/tokens.css` and `pdomain-ui/theme/primitives.css`.
- Writes them to `../docs/design-system/tokens.css` and `../docs/design-system/primitives.css` (resolved via `path.resolve(__dirname, '../../docs/design-system')`; aborts with non-zero exit if path doesn't exist).
- Refuses to run if `git status --porcelain ../docs/design-system/` shows uncommitted changes (avoids clobbering in-flight edits in workspace docs); flag `--force` overrides.
- Prints a diff summary of what changed.

Wire as npm script: `"sync:design-system": "node scripts/sync-design-system.mjs"`.

**TDD steps:**

- [ ] Vitest test `tests/theme/sync.test.ts` using `tmp` directory:
  - Sets up a fake workspace layout in tmp: `pdomain-ui/theme/tokens.css` and `docs/design-system/tokens.css` with differing contents.
  - Invokes the sync script via `child_process` with PWD pointed at the tmp pdomain-ui.
  - Asserts the docs/design-system copy now matches pdomain-ui/theme.
- [ ] Test asserts the script exits non-zero when the docs/design-system file has uncommitted git changes and `--force` is not passed.

**Acceptance:** Tests pass. Manual `node scripts/sync-design-system.mjs --dry-run` against the real workspace prints a no-op diff (since M1.1 copied byte-for-byte).

### Task M1.3: Sync-invariant CI gate {#sync-invariant-ci-gate}

**Why:** Prevent drift between pdomain-ui's shipping CSS and workspace docs.

**What:** Add `codegen:theme-check` npm script that runs the sync script in `--check` mode (which exits non-zero if a diff exists). Add to `make ci` chain after `codegen-check`.

**TDD steps:**

- [ ] Vitest test `tests/theme/sync-check.test.ts` asserts:
  - Running `--check` against an in-sync workspace exits 0.
  - Running `--check` after mutating `pdomain-ui/theme/tokens.css` (in a tmp fixture) exits non-zero.

**Acceptance:** `make ci` includes the check; passes when in sync.

### Task M1.4: Export theme CSS via package subpaths {#export-theme-css-via-package-subpaths}

**Why:** Consumers `import '@concavetrillion/pdomain-ui/theme/tokens.css'` at their root layout.

**What:** Verify `package.json.exports` from M0.2 includes:

```json
"./theme/tokens.css": "./theme/tokens.css",
"./theme/primitives.css": "./theme/primitives.css"
```

Update `package.json.files` to include `"theme"`.

**TDD steps:**

- [ ] Extend `tests/package.contract.test.ts` to assert both theme exports exist.
- [ ] `npm pack --dry-run` output verified to include `theme/tokens.css` and `theme/primitives.css`.

**Acceptance:** Tests pass. A test consumer can resolve both CSS subpaths.

---

## Milestone M2: Primitives folder

Thin React wrappers around the design-system CSS classes. Pure className composition — no CVA, no inline styles for variants, no Radix for non-behavior primitives. Radix is layered in only where listed in spec §4.

### Task M2.1: Primitives folder layout + className helper {#primitives-folder-layout-classname-helper}

**Why:** Establish the shape every primitive follows.

**What:** Create `src/primitives/` with:

- `cn.ts` — a tiny `cn(...args: ClassValue[]): string` helper that joins truthy class names. Use `clsx` lib or 10-line hand-roll (do not pull `class-variance-authority`).
- `index.ts` — barrel re-exports.

**TDD steps:**

- [ ] `src/primitives/cn.test.ts` covering: undefined / false / nested arrays / object truthiness collapses correctly.

**Acceptance:** Tests pass.

### Task M2.2: Non-Radix primitives — Button, Input, Textarea, Badge, Chip, StatusPip, KeyCap, Card, Separator, Progress {#non-radix-primitives-button-input-textarea-badge-c}

**Why:** Spec §4 lists these as "just CSS + plain HTML".

**What:** For each primitive, ship a React component file under `src/primitives/<Name>.tsx`. Each:

- Accepts `className?: string` merged via `cn()`.
- Forwards `ref` via `React.forwardRef`.
- Accepts a `variant?: 'primary' | 'ghost' | 'danger' | ...` prop where applicable, which maps 1:1 to a CSS class modifier (e.g., `variant='primary'` → adds `.primary` class to the `.btn` base).
- For Button: `size?: 'sm' | 'md' | 'lg'` → `.btn.sm` / `.btn.md` / `.btn.lg`.
- For StatusPip: `status: 'exact' | 'fuzzy' | 'mismatch' | 'ocr' | 'gt'` → applies `.pip` + inline `color: var(--<status>)` per the README pattern (color-mix at 10%/33% for fill/border).
- Spreads remaining props onto the underlying HTML element.

The labeler-spa `src/components/ui/{Button,Input,Chip,KeyCap,StatusPip}.tsx` files are the source-of-truth for prop shapes — port them, but strip any inline-style variant logic in favor of class modifiers from `primitives.css`.

**TDD steps (per primitive, one test file each):**

- [ ] `src/primitives/Button.test.tsx`: asserts `<Button variant="primary">x</Button>` renders `<button class="btn primary">x</button>`; `size="sm"` adds `.sm`; forwards ref to the underlying `<button>`; `disabled` HTML attribute passes through.
- [ ] Same shape for Input, Textarea, Badge, Chip, KeyCap, Card, Separator, Progress.
- [ ] `src/primitives/StatusPip.test.tsx`: asserts the rendered style attribute includes `color: var(--exact)` for `status='exact'`; asserts `.pip` class present.
- [ ] Cross-cutting test `tests/primitives/no-cva.test.ts` greps `src/primitives/**/*.{ts,tsx}` for the literal string `class-variance-authority` and `cva(` — asserts zero occurrences.

**Acceptance:** All primitive tests pass; `tests/primitives/no-cva.test.ts` proves CVA absent.

### Task M2.3: Radix-layered primitives — Dialog, AlertDialog, Popover, Tooltip, DropdownMenu, Select, Tabs, ToggleGroup, Accordion {#radix-layered-primitives-dialog-alertdialog-popove}

**Why:** Spec §4 lists these as the behavior-heavy set. Accordion can use native `<details>` *or* Radix — pick Radix here for consistent keyboard nav + animation hooks; document the choice in CLAUDE.md.

**What:** For each Radix primitive, ship a thin wrapper file under `src/primitives/<Name>.tsx` that:

- Re-exports the Radix subcomponents (e.g., `Dialog.Root`, `Dialog.Trigger`, `Dialog.Content`).
- Applies design-system classes (`.dialog`, `.popover`, `.tabs`, etc.) to the visual subcomponents.
- Adds no behavior on top of Radix — pdomain-ui is a styling + slot layer.

The labeler-spa `src/components/ui/{dialog,dropdown-menu,tabs,accordion,tooltip}.tsx` files are the source-of-truth for which Radix subcomponents the suite uses.

**TDD steps (per Radix primitive, one test file each):**

- [ ] `src/primitives/Dialog.test.tsx`: asserts clicking Trigger opens Content (basic Radix behavior survives the wrap); asserts the visible Content has the expected design-system class.
- [ ] `src/primitives/Tabs.test.tsx`: asserts arrow-key navigation between triggers works (Radix behavior); asserts the active tab has the `.tabs` active-class modifier.
- [ ] Same shape for AlertDialog, Popover, Tooltip, DropdownMenu, Select, ToggleGroup, Accordion.

**Acceptance:** All Radix wrapper tests pass.

### Task M2.4: Primitives barrel + subpath export {#primitives-barrel-subpath-export}

**Why:** Consumers `import { Button } from '@concavetrillion/pdomain-ui/primitives'`.

**What:**

- `src/primitives/index.ts` re-exports every primitive.
- Verify `package.json.exports['./primitives']` points at `dist/primitives.js`.
- Add `src/primitives/index.ts` to `vite.config.ts` `build.lib.entry.primitives`.

**TDD steps:**

- [ ] `tests/primitives/barrel.test.ts` imports every primitive from `@concavetrillion/pdomain-ui/primitives` (using a path alias resolving to `src/primitives/`) and asserts each is a function/component.

**Acceptance:** Test passes. Build produces `dist/primitives.js` and `dist/primitives.d.ts`.

### Task M2.5: Field + Form helper primitives {#field-form-helper-primitives}

**Why:** Form layouts repeat across labeler-spa and pgdp-prep; centralize.

**What:** Add `src/primitives/Field.tsx` (label + input + error slot wrapper) and `src/primitives/FieldRow.tsx` (horizontal field group). These wrap children with the design-system `.field` / `.field-row` classes from `primitives.css`. Verify both classes exist in `primitives.css` first; if not, add them in M1 follow-up (and re-run M1.2 sync).

**TDD steps:**

- [ ] `src/primitives/Field.test.tsx`: asserts label is associated with input via `htmlFor`/`id`; error slot renders when `error` prop set.

**Acceptance:** Test passes.

---

## Milestone M3: Icons

Curated lucide-react re-exports plus bespoke OCR-domain SVG stubs. Apps never import lucide directly.

### Task M3.1: Curated lucide subset re-export {#curated-lucide-subset-re-export}

**Why:** Spec §4 lists the ~30 chrome icons. Apps must import only from `pdomain-ui/icons`.

**What:** Create `src/icons/lucide.ts`:

```ts
export {
  ChevronDown, ChevronUp, ChevronLeft, ChevronRight,
  X as Close, Search, Settings, Save, FolderOpen,
  Undo, Redo, Plus, Minus, Eye, EyeOff,
  Trash2 as Delete, Copy, Download, Upload,
  RotateCw, RotateCcw, ZoomIn, ZoomOut,
  Check, Info, AlertTriangle,
  PanelLeft, PanelRight, LayoutGrid,
  // ...exact final list lives here
} from 'lucide-react';
```

The labeler-spa `src/components/**` direct lucide imports give the empirical "what's actually used" list — sweep them as the source-of-truth for the initial vetted set; spec §4 lists the baseline.

**TDD steps:**

- [ ] `src/icons/lucide.test.tsx` renders each re-exported icon into a div and asserts the SVG root mounts (smoke test).
- [ ] `tests/icons/no-direct-lucide.test.ts` greps `src/**/*.{ts,tsx}` for `from 'lucide-react'` and asserts the only matching file is `src/icons/lucide.ts`.

**Acceptance:** Tests pass.

### Task M3.2: Bespoke OCR-domain SVG stubs {#bespoke-ocr-domain-svg-stubs}

**Why:** Spec §4 (and §9 deferred items): ship stub SVGs so types + exports exist; finished art lands later.

**What:** Create `src/icons/bespoke/` containing one `<Name>.tsx` per glyph from spec §4:

- `LayerBlock.tsx`, `LayerPara.tsx`, `LayerLine.tsx`, `LayerWord.tsx`
- `ModeSelect.tsx`, `ModeRebox.tsx`, `ModeErase.tsx`, `ModeCharFixer.tsx`
- `MatchStatusExact.tsx`, `MatchStatusFuzzy.tsx`, `MatchStatusMismatch.tsx`

Each component:

- Accepts `size?: number` (default 16), `className?: string`, all other SVG props.
- Renders a minimal placeholder SVG (e.g., a labeled box) using `currentColor` for stroke/fill so design-system tokens can drive color via CSS.
- Includes a `<title>` for accessibility.

Add `src/icons/bespoke/index.ts` barrel.

**TDD steps:**

- [ ] `src/icons/bespoke/index.test.tsx` renders each component, asserts the root is an `<svg>` with the expected `<title>` text, asserts `size` prop drives `width` + `height`.
- [ ] `tests/icons/bespoke.contract.test.ts` asserts the full list of 11 named exports exists.

**Acceptance:** Tests pass.

### Task M3.3: Icons barrel + subpath export {#icons-barrel-subpath-export}

**Why:** Single import surface.

**What:**

- `src/icons/index.ts` re-exports from `./lucide` and `./bespoke`.
- Wire `vite.config.ts` `build.lib.entry.icons = 'src/icons/index.ts'`.

**TDD steps:**

- [ ] `tests/icons/barrel.test.ts` imports a sample of each (one lucide, one bespoke) and asserts they render.

**Acceptance:** Test passes; `dist/icons.js` produced by `pnpm run build`.

---

## Milestone M4: Codegen pipeline

Consume pdomain-book-tools' `schemas.emit` CLI output → produce TypeScript types in `src/types/generated/`. Committed to git. CI gate fails if regen produces a diff. This is the milestone with a hard dep on plan #1.

### Task M4.1: codegen:fetch — install pinned wheels {#codegenfetch-install-pinned-wheels}

**Why:** Spec §5 codegen pipeline: pin the wheel versions consumed.

**What:** Create `scripts/codegen-fetch.mjs` that:

- Reads pinned versions from a new `codegen.versions.json` (committed; bumped manually): `{ "pdomain-book-tools": "x.y.z", "pdomain-ocr-ops": "x.y.z" }`.
- Creates `.codegen/venv/` (gitignored) via `uv venv .codegen/venv`.
- Installs both wheels: `uv pip install --python .codegen/venv pdomain-book-tools==<v> pdomain-ocr-ops==<v>` using the pdomain-index-pip URL from workspace conventions.
- Skips the pdomain-ocr-ops install during the bootstrap phase before plan #3 ships (gate on a `--book-tools-only` flag; default false; will be flipped once #3 lands).

Add npm script: `"codegen:fetch": "node scripts/codegen-fetch.mjs --book-tools-only"`.

**TDD steps:**

- [ ] `tests/codegen/fetch.test.ts` uses tmp dir, mocks `uv` invocations via a shim, asserts the script reads `codegen.versions.json` and forms the correct `uv pip install` command including the pdomain-index-pip URL.

**Acceptance:** Test passes. Manual `node scripts/codegen-fetch.mjs --book-tools-only` creates `.codegen/venv/` with pdomain-book-tools installed.

### Task M4.2: codegen:emit — invoke schemas.emit, write JSON {#codegenemit-invoke-schemasemit-write-json}

**Why:** Capture the raw JSON Schema for diffing in PRs.

**What:** Create `scripts/codegen-emit.mjs` that:

- Runs `.codegen/venv/bin/python -m pd_book_tools.schemas.emit > .codegen/book-tools.schema.json`.
- Runs the equivalent for pdomain-ocr-ops when not gated by `--book-tools-only`.
- Validates the JSON parses; aborts on parse failure.

Add npm script: `"codegen:emit": "node scripts/codegen-emit.mjs --book-tools-only"`.

**TDD steps:**

- [ ] `tests/codegen/emit.test.ts`: with a stub venv where `python -m pd_book_tools.schemas.emit` is replaced by a shell script echoing a known JSON Schema fixture, asserts the script writes `.codegen/book-tools.schema.json` matching the fixture.

**Acceptance:** Test passes. Manual emit produces a JSON file ≥ 10 KB containing keys `Word`, `Block`, `Page`, `ReviewMetadata`, `BoundingBox` (per plan #1).

### Task M4.3: codegen:tsgen — JSON Schema → TypeScript {#codegentsgen-json-schema-typescript}

**Why:** Spec §5: "openapi-typescript -> src/types/generated/{book-tools,suite}.ts".

**What:** Create `scripts/codegen-tsgen.mjs` that:

- Runs `openapi-typescript` against `.codegen/book-tools.schema.json` → `src/types/generated/book-tools.ts`.
- Same for `.codegen/ocr-ops.schema.json` → `src/types/generated/suite.ts` when not gated.
- Prepends an auto-generated header: `// AUTO-GENERATED by scripts/codegen-tsgen.mjs from pdomain-book-tools <version>. DO NOT EDIT.`

`openapi-typescript` expects an OpenAPI document, not raw JSON Schema. Wrap the schemas in a minimal OpenAPI stub (`openapi: 3.1.0`, `info`, `components.schemas`) before invoking; the wrapping logic lives in `scripts/codegen-tsgen.mjs`.

Add npm script: `"codegen:tsgen": "node scripts/codegen-tsgen.mjs --book-tools-only"`.

**TDD steps:**

- [ ] `tests/codegen/tsgen.test.ts`: against a tiny fixture schema (`{Word: {...}}`), runs the script and asserts `src/types/generated/book-tools.ts` exports a `Word` type with the expected shape (use TS compiler API or simple substring assertions on the generated file).
- [ ] Asserts the header comment is present.

**Acceptance:** Test passes.

### Task M4.4: codegen orchestrator + commit policy {#codegen-orchestrator-commit-policy}

**Why:** Single command for engineers; CI invariant for PRs.

**What:**

- Add `"codegen"` npm script chaining `codegen:fetch && codegen:emit && codegen:tsgen`.
- Add `"codegen:check"` script that runs `codegen` then checks `git diff --exit-code src/types/generated/` and exits non-zero on diff.
- Wire `codegen-check` into `make ci`.
- `src/types/generated/` is committed to git; `.codegen/` is gitignored.
- Document in CLAUDE.md: "When bumping pdomain-book-tools or pdomain-ocr-ops in `codegen.versions.json`, run `pnpm codegen` and commit the regenerated `src/types/generated/` in the same PR."

**TDD steps:**

- [ ] `tests/codegen/check.test.ts`: simulates an out-of-sync state by mutating `src/types/generated/book-tools.ts` in a tmp checkout, runs `codegen:check`, asserts non-zero exit.

**Acceptance:** Test passes. `make ci` includes the gate.

### Task M4.5: src/types/index.ts barrel + `*Like` reductions {#srctypesindexts-barrel-like-reductions}

**Why:** Spec §5 says these become one-line `Pick<>` derivations from the generated types.

**What:** Create `src/types/index.ts`:

```ts
export * from './generated/book-tools';
// export * from './generated/suite';  // re-enable once pdomain-ocr-ops codegen lands

import type { Word, Block, Page } from './generated/book-tools';

export type WordLike = Pick<Word,
    'bounding_box' | 'text' | 'ocr_confidence'
  | 'chars' | 'review' | 'matching'
  | 'word_labels' | 'text_style_labels'
>;

export type BlockLike = Pick<Block,
    'category' | 'bounding_box' | 'children' | 'review'
>;

// Lines are blocks: filter by `block.category === 'line'`.
// Same for paragraphs, captions, figures, etc. No separate LineLike.

export type PageLike = Pick<Page,
    'page_index' | 'name' | 'image_url' | 'width' | 'height'
  | 'category' | 'blocks' | 'review'
  | 'parent_page_index' | 'subpage_index' | 'subpage_position'
>;
```

Field names follow spec §5 "Canonical model shape" (rewritten 2026-05-17 to keep `bounding_box`/`ocr_confidence` from pdomain-book-tools instead of the earlier `bbox`/`confidence` drafts; lines are `Block(category=LINE)` rather than a separate `Line` class; `Page` carries `page_index`+`name`+`image_url` rather than a single synthetic `id`). The `WordLike` Pick will fail to compile if pdomain-book-tools' generated `Word` is missing any of the listed fields — that's the codegen contract.

**TDD steps:**

- [ ] `src/types/reductions.test-d.ts` (`.test-d.ts` is `tsd`-style; or use `expect-type`): asserts `WordLike` extends a subset of `Word`'s keys; asserts assigning a full `Word` to `WordLike` typechecks; asserts a `WordLike` missing the `text` field FAILS to typecheck (compile-error expected).
- [ ] If using `vitest`-only, write `src/types/reductions.test.ts` that calls `tsc --noEmit` against fixture files and asserts the expected pass/fail outcomes.

**Acceptance:** Tests pass after a successful `pnpm codegen`.

### Task M4.6: Types subpath export {#types-subpath-export}

**Why:** Consumers `import type { Word, WordLike } from '@concavetrillion/pdomain-ui/types'`.

**What:** Add `vite.config.ts` `build.lib.entry.types = 'src/types/index.ts'`. Verify `package.json.exports['./types']` points at `dist/types.js` + `dist/types.d.ts`.

**TDD steps:**

- [ ] `tests/types/barrel.test.ts` imports `WordLike`, `BlockLike`, `PageLike` from the subpath and asserts they're each defined (TypeScript-level check via `expect-type`).

**Acceptance:** Test passes.

---

## Milestone M5: `<PageImageCanvas>` port (slot-based)

Port the labeler-spa `PageImageCanvas.tsx` into pdomain-ui, restructured under the slot API from spec §6. Layer order is fixed by pdomain-ui; apps fill slots.

### Task M5.1: Canvas slot API + types {#canvas-slot-api-types}

**Why:** Spec §6 declares the canonical surface; component code follows.

**What:** Create `src/canvas/types.ts` with:

- `SlotRenderProps`, `WordSlotProps`, `CanvasProps<TWord, TPage>` (verbatim from spec §6, adjusted only for the actual generated names from M4).
- `CoordContext` shape (page-space ↔ stage-space transforms).
- `SelectionState` shape (set of word ids + anchor id + range mode).
- `ViewportState` (zoom, pan).

These types reference `WordLike` and `PageLike` from `src/types/`.

**Read-only consumers.** `CanvasProps.selection` and `CanvasProps.onSelectionChange` MUST be optional (`selection?:`, `onSelectionChange?:`) so read-only embedders (pdomain-ocr-simple-gui's per-page view) don't have to thread no-op pairs. When `selection` is undefined the canvas treats selection as the empty set; when `onSelectionChange` is undefined, selection-changing user actions are still tracked internally but no callback fires. Selection slot fills (e.g., `<MarqueeSelectLayer>`) MUST tolerate undefined selection state.

**TDD steps:**

- [ ] `src/canvas/types.test-d.ts`: asserts `CanvasProps['children']['overlay']` accepts `(p: WordSlotProps) => ReactNode`; asserts a fixture `MyWord extends WordLike` satisfies the canvas's `TWord` constraint.

**Acceptance:** Tests pass.

### Task M5.2: Hooks — useCanvasCoords, useViewport, useCanvasSelection {#hooks-usecanvascoords-useviewport-usecanvasselecti}

**Why:** Spec §6 hook surface. Components inside slot fills read these via context.

**What:** Implement under `src/canvas/hooks/`:

- `useCanvasCoords()` — returns `CoordContext`; reads from a `CanvasInternalContext`.
- `useViewport()` — returns `ViewportState`.
- `useCanvasSelection()` — returns `SelectionState` + dispatch.
- Each hook throws a clear error when called outside `<PageImageCanvas>`.

Port the labeler-spa hook bodies (likely embedded inside the existing `PageImageCanvas.tsx` or `usePage.ts`) into these dedicated hooks.

**TDD steps:**

- [ ] One test per hook: render a `<PageImageCanvas>` fixture wrapping a child that invokes the hook and asserts the returned shape.
- [ ] One test per hook: render the child OUTSIDE the canvas and assert the thrown error message names the hook.

**Acceptance:** Tests pass.

### Task M5.3: Stage shell + image layer + fixed layer order {#stage-shell-image-layer-fixed-layer-order}

**Why:** Spec §6: `image -> underlay -> overlay -> selection -> tool -> hud`.

**What:** Create `src/canvas/PageImageCanvas.tsx` that:

- Sets up the Konva Stage + Layer scaffolding from labeler-spa's implementation.
- Loads the page image (URL from `page.image_url`).
- Provides `CanvasInternalContext` so hooks resolve.
- Renders children slots in the order: `underlay → overlay → selection → tool → hud`, with the image as the bottom layer.
- Emits selection changes via `onSelectionChange`.

The labeler-spa `src/components/PageImageCanvas.tsx` is the source-of-truth for: pan/zoom math, fit-on-mount, hit-test layering, image loading state, and the Konva-stage perf tuning. Port mechanically; restructure all "labeler-specific overlay logic" as slot fills documented in M5.4 below.

**TDD steps:**

- [ ] `src/canvas/PageImageCanvas.test.tsx`: render with a fixture page + words; asserts the stage mounts; asserts the image element renders at the expected coords given `initialZoom` and `fitOnMount`.
- [ ] Renders with each slot supplied as a unique `<div data-testid="slot-x">`; asserts DOM order (top-to-bottom in the Konva tree) is `underlay → overlay → selection → tool → hud`.
- [ ] Mocks `onSelectionChange`; simulates a click on a word; asserts the callback fires with the expected `SelectionState`.

**Acceptance:** Tests pass.

### Task M5.4: Slot helpers — BBoxLayer, WordHitLayer, MarqueeSelectLayer, RotateTransformerLayer, EraseOverlayLayer, CharRangeLayer {#slot-helpers-bboxlayer-wordhitlayer-marqueeselectl}

**Why:** Spec §4 module map: these are the common overlays pdomain-ui ships so apps don't reinvent them.

**What:** Each helper is a React component that's rendered INSIDE a slot fill by the app:

```tsx
<PageImageCanvas page={page} words={words} selection={sel} onSelectionChange={setSel}>
  {{ overlay: (p) => <BBoxLayer {...p} color="var(--word)" /> }}
</PageImageCanvas>
```

Port these from labeler-spa's `BBoxOverlay.tsx` and related files. Each uses `useCanvasCoords` to project page-space rects into stage-space.

**TDD steps:**

- [ ] One test per helper: render inside a `<PageImageCanvas>` with a fixed fixture; assert the layer renders the expected number of shapes and that each shape's coords match the expected transform.

**Acceptance:** Tests pass.

### Task M5.5: Canvas subpath export {#canvas-subpath-export}

**What:**

- `src/canvas/index.ts` re-exports `PageImageCanvas`, all slot helpers, all hooks, all types.
- `vite.config.ts` `build.lib.entry.canvas = 'src/canvas/index.ts'`.

**TDD steps:**

- [ ] `tests/canvas/barrel.test.ts` imports each export and asserts presence.

**Acceptance:** Test passes; `dist/canvas.js` produced.

---

## Milestone M6: `<WordList>` port (render-prop rows)

Port the labeler-spa worklist into pdomain-ui as `<WordList>` with the render-prop API from spec §6.

### Task M6.1: WordList API types + render-prop signatures {#wordlist-api-types-render-prop-signatures}

**Why:** Spec §6.

**What:** Create `src/worklist/types.ts` with `WordRowProps<TWord>`, `WordListProps<TWord>` per spec §6.

**TDD steps:**

- [ ] `src/worklist/types.test-d.ts`: asserts a custom `TWord extends WordLike` flows through `renderRow` props.

**Acceptance:** Test passes.

### Task M6.2: Virtualized list shell {#virtualized-list-shell}

**Why:** Spec §4 promises virtualization for large word counts.

**What:** Create `src/worklist/WordList.tsx`:

- Uses the same virtualization lib labeler-spa uses (read its `LineCard.tsx` / worklist parent first to pick).
- Owns scroll-to-active behavior, multi-select gestures (shift-click range, ctrl/cmd-click toggle), keyboard navigation (up/down arrows move active; space toggles select).
- Calls `renderRow` for each visible row.
- Renders optional `header`, `footer`, `emptyState` slots.
- Applies optional `filter` and `sortKey` + `reverse` props before virtualization.

Port the labeler-spa worklist's gesture + keyboard handlers verbatim.

**TDD steps:**

- [ ] `src/worklist/WordList.test.tsx`: render with 200 fixture words; assert only a virtualized subset is in the DOM (~20-40).
- [ ] Click on row index 5 with shift held after row index 2 is active: assert `onSelectionChange` is called with the range 2-5.
- [ ] Ctrl/cmd-click toggles a single id.
- [ ] Arrow-down with active=row 5: assert `onActiveChange(row 6's id)`.
- [ ] `sortKey={w => w.confidence}` + `reverse={true}` produces descending order.

**Acceptance:** Tests pass.

### Task M6.3: WordList sibling shells — LineList, PageList {#wordlist-sibling-shells-linelist-pagelist}

**Why:** Spec §4 module map lists "LineList, PageList (same pattern, different shape)".

**What:** Generic-ish shells over the same virtualization machinery. Each accepts its own `*Like` constraint and `renderRow`. For Phase 1 these can be thin clones of `<WordList>` reparameterized over `BlockLike` (e.g., a line-block list, a paragraph-block list, filtered by `category`) / `PageLike`; refactor to share internals later.

**TDD steps:**

- [ ] One render+selection test per list type, mirroring M6.2 at smaller scope.

**Acceptance:** Tests pass.

### Task M6.4: Adapter docs for LineCard {#adapter-docs-for-linecard}

**Why:** In Phase 2 labeler-spa's `LineCard.tsx` becomes the `renderRow` for `<WordList>`. Document the prop-shape expected so the migration is mechanical.

**What:** Add `src/worklist/README.md` documenting:

- The full `WordRowProps<TWord>` surface.
- A worked example showing how to convert an existing LineCard-style component (which takes a Word + handlers as separate props) into a `renderRow`-compatible one.

**TDD steps:** None — docs.

**Acceptance:** README exists and the worked example mirrors labeler-spa's current `LineCard.tsx` props (verify by reading labeler-spa's LineCard ONCE; do not import it).

### Task M6.5: useWorklistFilter, useWorklistSort hooks {#useworklistfilter-useworklistsort-hooks}

**Why:** Spec §4 module map.

**What:** Pure hooks under `src/worklist/hooks/` that wrap common filter / sort predicates and return memoized output. Useful for apps that pass `filter` / `sortKey` to `<WordList>` and want shared filter logic.

**TDD steps:**

- [ ] One test per hook covering basic filter / sort behavior + memoization stability.

**Acceptance:** Tests pass.

### Task M6.6: Status row primitives — StatusPip, ConfidenceBar, MatchStatusChip {#status-row-primitives-statuspip-confidencebar-matc}

**Why:** Spec §4 module map; these are commonly used inside `renderRow` implementations across apps.

**What:**

- `StatusPip` already exists from M2.2 — re-export from worklist barrel.
- `ConfidenceBar` — small visual bar fill component using design-system tokens (`var(--exact)` / `var(--fuzzy)` / `var(--mismatch)` based on threshold). Port from labeler-spa if it exists; otherwise build fresh against `primitives.css`.
- `MatchStatusChip` — renders a `Chip` with `status='exact'|'fuzzy'|'mismatch'|'none'` styling. Port from labeler-spa's match-status chip if present.

**TDD steps:**

- [ ] One render test per component.

**Acceptance:** Tests pass.

### Task M6.7: Worklist subpath export {#worklist-subpath-export}

**What:** Standard barrel + Vite entry + `package.json.exports` for `./worklist`.

**TDD steps:**

- [ ] `tests/worklist/barrel.test.ts` imports each export.

**Acceptance:** Test passes; `dist/worklist.js` produced.

---

## Milestone M7: `<AppShell>` port

Port `StudioShell` from labeler-spa into pdomain-ui as `<AppShell>` with `deployMode`, `launcherSlot`, and UIPrefs context wiring per spec §6 and §8.

### Task M7.1: AppShell props + context types {#appshell-props-context-types}

**Why:** Spec §6 declares the canonical surface.

**What:** Create `src/shell/types.ts` with `AppShellProps` exactly as spec §6. Plus:

- `UIPrefsConfig` — `{ load: () => Promise<UIPrefs>; persistCommon: (p: Partial<UIPrefs['common']>) => Promise<void>; persistApp: (p: Record<string, unknown>) => Promise<void>; }`
- `AppShellContextValue` — exposes `deployMode`, `appId`, `appDisplayName`, `appIconUrl` to descendants.

**TDD steps:**

- [ ] `src/shell/types.test-d.ts`: type smoke tests asserting `deployMode` is optional (defaults to `'local'`) and that the literal `'hosted' | 'local'` union is enforced.

**Acceptance:** Test passes.

### Task M7.2: AppShell grid skeleton {#appshell-grid-skeleton}

**Why:** Spec §6: "header + rail + drawer + main + right panel grid".

**What:** Create `src/shell/AppShell.tsx`:

- CSS grid layout matching labeler-spa's `StudioShell` (header row + rail column + drawer column + main + right panel).
- Slot props (`header`, `rail`, `drawer`, `main`, `rightPanel`) render into the appropriate grid cells.
- Provides `AppShellContext` so descendants can read `deployMode`, `appId`, etc.
- Mounts `<UIPrefsProvider>` (M8) and `<SuiteSiblingsProvider>` (M8) wrapping `main`.

Port the labeler-spa `StudioShell.tsx` layout (CSS grid + breakpoint behavior) verbatim. Replace labeler-specific children with the slot props.

**TDD steps:**

- [ ] `src/shell/AppShell.test.tsx`: render with each slot as a `<div data-testid="slot-x">`; assert each is in the expected grid cell (via `getComputedStyle` or by structural assertion).
- [ ] Render with `deployMode='hosted'`; assert children calling `useAppShell().deployMode` see `'hosted'`.
- [ ] Render with no `deployMode` prop; assert default is `'local'`.

**Acceptance:** Tests pass.

### Task M7.3: LauncherSlot + LauncherTile {#launcherslot-launchertile}

**Why:** Spec §3 sibling discovery, §6 hook surface.

**What:**

- `src/shell/LauncherSlot.tsx` — reads `useSuiteSiblings()` (M8) and renders one `<LauncherTile>` per installed sibling; hides itself when zero siblings.
- `src/shell/LauncherTile.tsx` — accepts `{ sibling: InstalledApp }`; renders icon + display name; on click calls `useSuiteSiblings().launch(sibling.id)` and handles the discriminated `LaunchResult` (open URL in new tab for `'opened'`; show a "requires host config" tooltip for `'requires-host-config'`).

`launcherSlot` prop on `<AppShell>` controls where it appears: `'header'` (default) | `'rail'` | `'off'`.

**TDD steps:**

- [ ] `src/shell/LauncherSlot.test.tsx`: with mocked `useSuiteSiblings` returning `{ siblings: [], loading: false, launch: vi.fn() }`, assert nothing renders.
- [ ] With 2 mock siblings, asserts 2 tiles render with the expected display names + icons.
- [ ] `src/shell/LauncherTile.test.tsx`: click fires `launch(id)`; on `{ kind: 'opened', url }`, asserts `window.open` called with `url`.
- [ ] On `{ kind: 'requires-host-config', siblingId }`, asserts the tile shows a tooltip / banner indicating sibling not reachable.

**Acceptance:** Tests pass.

### Task M7.4: Breadcrumb, TopNav, Drawer, Rail, RightPanel sub-shells {#breadcrumb-topnav-drawer-rail-rightpanel-sub-shell}

**Why:** Spec §4 module map.

**What:** Each is a thin layout primitive consumed in slot fills by apps. Port from labeler-spa's `src/components/shell/{Breadcrumb,Drawer,Rail,RightPanel}.tsx`. Each accepts `children` and applies design-system classes.

**TDD steps:**

- [ ] One render test per sub-shell asserting children placement + design-system class application.

**Acceptance:** Tests pass.

### Task M7.5: Shell subpath export {#shell-subpath-export}

**What:** Barrel + Vite entry + `package.json.exports` for `./shell`.

**TDD steps:**

- [ ] `tests/shell/barrel.test.ts` imports each export.

**Acceptance:** Test passes; `dist/shell.js` produced.

---

## Milestone M8: Hook surface (useSuiteSiblings, useUIPrefs, store factories, GPU dispatch)

Cross-cutting hooks and the Zustand store factories. Where pdomain-ocr-ops adapters aren't wired yet, hooks ship as stubs against the documented HTTP contract; integration is host-app work later.

### Task M8.1: createSelectionStore, createViewportStore, createWorklistStore, createUIPrefsStore {#createselectionstore-createviewportstore-createwor}

**Why:** Spec §4: "Stores are factories, not singletons". Spec §6 lists hook accessors.

**What:** Create `src/stores/` with one file per factory. Each:

- Exports a `create<Name>Store(initial?: Partial<State>)` function returning a Zustand store.
- Defines selectors as separate named exports (or as members on the store) so apps can subscribe granularly.

Port the state shape + reducer logic from labeler-spa's `src/stores/{selection-store,viewport-store,worklist-store,ui-prefs}.ts`. Each labeler-spa store currently exports a singleton — convert each to a factory closure.

**TDD steps:**

- [ ] One test file per store. Each:
  - Creates two independent store instances; asserts mutating one does NOT affect the other (factory isolation).
  - Asserts every documented action (select, unselect, set zoom, set pan, set sort key, etc.) mutates state as expected.

**Acceptance:** Tests pass.

### Task M8.2: useSelection, useViewport, useWorklist context-bound hooks {#useselection-useviewport-useworklist-context-bound}

**Why:** Spec §6 lists these as ambient hooks usable inside an `<AppShell>`.

**What:** Each hook reads from a corresponding React context provider that the AppShell wires. Providers (e.g., `<SelectionStoreProvider value={selectionStore}>`) accept a store instance from the app. The hook returns the store's state + actions via Zustand's `useStore` selector pattern.

**TDD steps:**

- [ ] Each hook: rendered inside the appropriate provider, returns the expected slice; rendered outside, throws a clear error.

**Acceptance:** Tests pass.

### Task M8.3: createUIPrefsStore + UIPrefsProvider + useUIPrefs + useTheme + useDensity + useLayerColor + useStatusColor + useAccentColor {#createuiprefsstore-uiprefsprovider-useuiprefs-uset}

**Why:** Spec §4 cross-cutting concern: shared UI prefs.

**What:**

- `createUIPrefsStore({ load, persistCommon, persistApp })` returns a Zustand store. Constructor wires `load()` on first subscribe; debounce-persists on common/app pref changes.
- `<UIPrefsProvider>` mounts the store; reads `UIPrefsConfig` from `<AppShell>`.
- `useUIPrefs()` → current full UIPrefs object.
- `useTheme()` / `useDensity()` → the corresponding common values.
- `useLayerColor(layer)` reads `prefs.common.layer_colors[layer]` with a token fallback (`var(--word)` / `var(--line)` / `var(--para)` / `var(--block)`).
- `useStatusColor(status)` returns `var(--exact)` / `var(--fuzzy)` / `var(--mismatch)` / `var(--ocr)` / `var(--gt)`.
- `useAccentColor()` returns `{ fg: 'var(--accent-ink)', bg: 'var(--accent)' }`.

These hooks NEVER call fetch directly — the prefs load/persist callbacks supplied to `createUIPrefsStore` do.

Port the labeler-spa `src/stores/ui-prefs.ts` shape; convert from singleton to factory; add the multi-app `common` vs `apps['<app-id>']` split per spec §4 JSON schema.

**TDD steps:**

- [ ] Factory test: creates the store with mock `load` returning a fixture; asserts subsequent `useUIPrefs()` reads return the loaded shape.
- [ ] Mutation test: calling the store's `setTheme('light')` action triggers `persistCommon({ theme: 'light' })`.
- [ ] `useLayerColor('word')` returns the configured custom color when set; falls back to `var(--word)` when unset.

**Acceptance:** Tests pass.

### Task M8.4: useSuiteSiblings + SuiteSiblingsProvider {#usesuitesiblings-suitesiblingsprovider}

**Why:** Spec §6 hook surface; §3 sibling discovery model.

**What:**

- `<SuiteSiblingsProvider value={{ fetchInstalled, postLaunch }}>` — wraps the AppShell; accepts a config object with the two fetch callbacks.
- `useSuiteSiblings()` returns `{ siblings: InstalledApp[]; launch: (id) => Promise<LaunchResult>; loading: boolean }`.
- `siblings` is populated from `fetchInstalled()` (which the host app implements as `GET /api/suite/installed`).
- `launch(id)` calls `postLaunch(id)` (host implements as `POST /api/suite/launch?app=<id>`) and returns the discriminated `LaunchResult`.

Phase 1 ships the hook + provider; the host app wires `fetchInstalled` / `postLaunch` to its own backend's pdomain-ocr-ops-mounted routes (once plan #3 ships). For Phase 1 testing, a mock provider in Storybook proves the integration.

**TDD steps:**

- [ ] Render `useSuiteSiblings` inside a provider with mock `fetchInstalled` returning 2 sibling fixtures; assert the hook returns `{ siblings: [..], loading: false }` after the promise resolves.
- [ ] Call `launch('sibling-1')` with mock `postLaunch` returning `{ kind: 'opened', url: 'http://x' }`; assert the discriminated result is returned.
- [ ] Outside provider: hook throws.

**Acceptance:** Tests pass.

### Task M8.5: useStageCall + useLongJob (interfaces; stub-friendly impls) {#usestagecall-uselongjob-interfaces-stub-friendly-i}

**Why:** Spec §6 hook surface, §8 frontend impact. Even though hosted-mode adapters land later, the hook contract must exist so apps can wire them now.

**What:**

- `useStageCall(stageId, pageId, params)` returns `{ status: 'idle'|'loading'|'success'|'error'|'retry'; result?: StageResult; isWarming: boolean; retryAt?: number }`. Internally `POST`s to `/api/stage/{stageId}` (URL convention from pdomain-ocr-ops); on `503 Retry-After`, schedules a retry, sets `isWarming: true`.
- `useLongJob(jobId)` returns `{ status, progress, events, cancel }`. Uses SSE in hosted mode (when available; feature-detects); falls back to polling `/api/jobs/{jobId}` in local mode.

Both hooks use the `useAppShell().deployMode` value to choose transport but otherwise present the same surface. The URL constants are documented in `src/hooks/transport-contracts.ts` (single source of truth).

**TDD steps:**

- [ ] `useStageCall.test.tsx`: mock fetch returning 503 with `Retry-After: 2`; assert hook transitions to `'retry'` and schedules a retry; mock the retry succeeding; assert final status `'success'`.
- [ ] `useLongJob.test.tsx`: mock polling endpoint returning increasing progress over 3 polls; assert `progress` accumulates; assert `cancel()` posts to `/api/jobs/{id}/cancel`.

**Acceptance:** Tests pass.

### Task M8.6: useCanvasCoords + useSelection + useViewport + useWorklist re-exports from `/canvas` and `/worklist` {#usecanvascoords-useselection-useviewport-useworkli}

**Why:** Spec §6 lists all hooks at top level. Canvas hooks already live in `src/canvas/hooks/`; re-export at top level for spec consistency.

**What:** Update `src/index.ts` top-level barrel to re-export the canvas + worklist + shell + stores hooks under one ambient surface. Apps may either import from subpaths (preferred for tree-shaking) or from the root.

**TDD steps:**

- [ ] `tests/hooks/surface.test.ts` asserts every hook listed in spec §6 is exported by some subpath.

**Acceptance:** Test passes.

### Task M8.7: Stores subpath export {#stores-subpath-export}

**What:** Barrel + Vite entry + `package.json.exports` for `./stores`.

**TDD steps:**

- [ ] `tests/stores/barrel.test.ts` imports each factory.

**Acceptance:** Test passes; `dist/stores.js` produced.

---

## Milestone M9: Storybook setup

One story per component, in both `:root` (dark) and `[data-theme="light"]` modes.

### Task M9.1: Storybook scaffold {#storybook-scaffold}

**Why:** Spec §7.1 row 1.5: "Storybook for component dev loop".

**What:** Run `pnpm dlx storybook@latest init --type react --builder vite --no-yes`. Customize `.storybook/main.ts` and `.storybook/preview.ts`:

- `preview.ts` imports `@concavetrillion/pdomain-ui/theme/tokens.css` and `primitives.css` (via path alias).
- Adds a global toolbar toggle for `data-theme` (dark / light), wiring it to set the attribute on `<html>` in the preview iframe.
- Sets dark as default.

**TDD steps:**

- [ ] `pnpm run storybook --ci --quiet` (or `storybook build`) exits 0 with the scaffold story present.

**Acceptance:** `pnpm run build-storybook` produces `storybook-static/` with at least the default Stories.mdx visible.

### Task M9.2: Primitives stories (Button, Input, Chip, StatusPip, KeyCap, Card, Separator, Progress, Badge, Field) {#primitives-stories-button-input-chip-statuspip-key}

**Why:** Living visual reference.

**What:** One `<Name>.stories.tsx` per primitive under `src/primitives/`. Each shows all variants/sizes/states in a grid. Use `@storybook/test` for interaction stories where applicable (e.g., disabled state, hover state).

**TDD steps:** None per-story; M9.5 covers the cross-cutting story-presence test.

**Acceptance:** `pnpm run build-storybook` exits 0 with each story navigable.

### Task M9.3: Canvas + Worklist + Shell stories {#canvas-worklist-shell-stories}

**Why:** Higher-level components need fixture data; Storybook is the easiest way to exercise them in isolation.

**What:**

- `src/canvas/PageImageCanvas.stories.tsx` — fixture page with 5-10 fixture words; one story per overlay combination (no slots, BBox overlay only, full overlay set).
- `src/worklist/WordList.stories.tsx` — 200-row fixture; stories for default render, custom row, filtered, sorted.
- `src/shell/AppShell.stories.tsx` — full shell with all slots populated; story variant for `deployMode='hosted'` showing local-only affordances hidden.

**TDD steps:** None per-story.

**Acceptance:** Stories render without errors.

### Task M9.4: Icons stories {#icons-stories}

**Why:** Visual catalogue.

**What:** `src/icons/Icons.stories.tsx` renders a grid of every curated lucide + bespoke icon with its name label, in both themes.

**Acceptance:** Story renders.

### Task M9.5: Story-presence CI gate {#story-presence-ci-gate}

**Why:** Catch unprotected components.

**What:** Vitest test `tests/storybook/coverage.test.ts` walks `src/` for every `*.tsx` file with a default-exported React component and asserts a sibling `*.stories.tsx` exists. Exemptions: hooks, types, internal-only utilities (whitelist).

**TDD steps:**

- [ ] Run the test against the current tree; assert it passes.
- [ ] Temporarily delete one story file; assert the test fails identifying the missing story.

**Acceptance:** Test passes; included in `make ci`.

---

## Milestone M10: Publish 0.1.0-alpha to pdomain-index-npm

Build the package, version-bump, publish to the self-hosted registry. Depends on plan #4 (pdomain-index-npm) being live.

### Task M10.1: Verify build output completeness {#verify-build-output-completeness}

**Why:** Before publishing, confirm every subpath in `package.json.exports` resolves to a real `dist/` file.

**What:** Add `tests/release/exports.test.ts` that:

- Reads `package.json.exports`.
- Builds the package (`pnpm run build`).
- Asserts every export target file exists in `dist/`.
- Asserts every export has a matching `.d.ts`.
- Asserts CSS subpaths resolve to files under `theme/`.

**TDD steps:** The test IS the verification.

**Acceptance:** Test passes after `pnpm run build`.

### Task M10.2: Version bump to 0.1.0-alpha {#version-bump-to-010-alpha}

**Why:** First publishable identity.

**What:** `pnpm version 0.1.0-alpha --no-git-tag-version`. Commit `package.json` + `pnpm-lock.yaml` change with message `chore(release): bump to 0.1.0-alpha`.

**TDD steps:**

- [ ] Extend `tests/package.contract.test.ts` to assert `version` matches `/^0\.1\.0-alpha(\.\d+)?$/` (allows `0.1.0-alpha.1`, `.2`, etc.).

**Acceptance:** Test passes.

### Task M10.3: Publish dry-run + smoke install in tmp consumer {#publish-dry-run-smoke-install-in-tmp-consumer}

**Why:** Catch packaging mistakes before the real publish.

**What:**

- Run `pnpm publish --dry-run --registry https://concavetrillion.github.io/pdomain-index-npm/` and verify no warnings about missing files.
- Build a tmp consumer: `mkdir /tmp/pdomain-ui-smoke && cd /tmp/pdomain-ui-smoke && pnpm init && pnpm add file:/workspaces/ocr-container/pdomain-ui`. Write a 5-line `index.ts` importing `Button`, `PageImageCanvas`, `WordList`, `AppShell`, `tokens.css`. Run `pnpm exec tsc --noEmit`. Assert exit 0.

**TDD steps:** Manual; document the smoke procedure in `RELEASE.md`.

**Acceptance:** Both succeed.

### Task M10.4: Publish 0.1.0-alpha {#publish-010-alpha}

**Why:** Ship it.

**What:** `pnpm publish --registry https://concavetrillion.github.io/pdomain-index-npm/` against the real registry from plan #4. Tag the commit (`git tag v0.1.0-alpha`).

**Pre-flight:** Confirm plan #4 ready. If not, M10.4 is BLOCKED — leave M10.1–M10.3 done; revisit when #4 lands.

**TDD steps:** None — publish is one-way.

**Acceptance:** Package visible at the registry; `pnpm add @concavetrillion/pdomain-ui@0.1.0-alpha` from a fresh tmp dir succeeds.

### Task M10.5: Document the release in CHANGELOG.md {#document-the-release-in-changelogmd}

**Why:** Workspace convention.

**What:** Create `CHANGELOG.md` (Keep-a-Changelog format). First entry:

```
## 0.1.0-alpha — YYYY-MM-DD
### Added
- Initial scaffold: TS + Vite library mode + Vitest + ESLint + Storybook
- Theme (tokens.css + primitives.css from workspace docs/design-system/)
- Primitives: Button, Input, Textarea, Badge, Chip, StatusPip, KeyCap, Card, Separator, Progress, Field, Dialog, AlertDialog, Popover, Tooltip, DropdownMenu, Select, Tabs, ToggleGroup, Accordion
- Icons: ~30 curated lucide-react re-exports + 11 bespoke OCR-domain stub SVGs
- Codegen from pdomain-book-tools: src/types/generated/book-tools.ts
- Components: <PageImageCanvas> (slot-based), <WordList> (render-prop rows), <AppShell> (with launcherSlot + deployMode + UIPrefs context)
- Hooks: useCanvasCoords, useSelection, useViewport, useWorklist, useUIPrefs, useTheme, useDensity, useLayerColor, useStatusColor, useAccentColor, useSuiteSiblings, useStageCall, useLongJob
- Stores (factories): createSelectionStore, createViewportStore, createWorklistStore, createUIPrefsStore
- testids constants
- Storybook coverage of every component, in dark + light themes
### Notes
- pdomain-ocr-ops integration deferred to plan #3 + Phase 2; pdomain-ui ships the hook contracts only
- Bespoke OCR-domain icons are stubs; finished art lands later without API change
```

**Acceptance:** File exists.

---

## Follow-up plans (not in scope here)

The following are intentionally NOT covered by this plan; each becomes its own plan when sequenced.

1. **Phase 2.1 — labeler-spa migration to pdomain-ui.** Spec §7.2 rows 2.1–2.6 + 2.5b. Replace labeler-spa's canvas / worklist / shell internals with the pdomain-ui versions; move labeler-specific layer code into slot fills; convert labeler-spa stores from custom reactive to Zustand factories; remove labeler-spa's direct lucide imports + CVA dep; full Playwright driver regression pass. Own plan, owned by the labeler-spa agent.

2. **Phase 2.7 — pgdp-prep migration to pdomain-ui.** Same as above for pgdp-prep. pdomain-ui releases as `0.2.0` after this with any lessons baked in.

3. **Zustand factory spec sketch — store internals across the suite.** Spec §4 cross-cutting hints that `createSelectionStore`, etc., need a documented internal contract (which actions, which selectors, which middleware). This becomes a "pdomain-ui store conventions" spec / plan when the second consumer (pgdp-prep) starts to push back on the M8 shape.

4. **Behavior-heavy components beyond canvas/worklist/shell.** The labeler-spa `WordEditDialog`, `OCRConfigModal`, `ExportDialog`, `HotkeyHelpModal`, `SourceFolderDialog`, `ProjectLoadControls`, `ProjectNavigationControls`, etc., are app-specific in Phase 1. As patterns emerge across two consumers, promote shared ones into pdomain-ui (likely `pdomain-ui/dialogs/` or `pdomain-ui/project/`). Each promotion is its own small plan.

5. **Real ML-domain icon set.** Spec §9 defers bespoke OCR-domain icon art (LayerBlock/Para/Line/Word, ModeSelect/Rebox/Erase/CharFixer, MatchStatus*). A designer / illustrator pass replaces the M3.2 stubs without API change. Own plan, scheduled when a designer is available.

6. **Cross-tab UI prefs sync via SSE.** Spec §4 cross-cutting + §9 deferred: reload-only sync acceptable for Phase 1. Phase 2 ships an SSE channel in pdomain-ocr-ops; pdomain-ui adds a store subscriber. Own plan.

7. **Automated TS-vs-Python schema drift CI gate.** Spec §9: hand-review during PRs sufficient for first months; automate later. Own plan in pdomain-ui CI 0.2.x.

8. **`<JobsDrawer>` shared right-side drawer.** Spec §8 frontend impact: "shared right-side drawer listing active long jobs across the suite. Reads from `useSuiteJobs()` which queries every installed sibling's `/api/jobs?status=active` and merges." Defer to after first hosted-mode adapter in pdomain-ocr-ops lands and the multi-sibling query pattern is concrete.

9. **Split into multiple packages** (`@pd/canvas`, `@pd/shell`, `@pd/primitives`). Spec §9 open question: "Split if bundle gets fat." Revisit after the first labeler-spa migration measures actual bundle impact.

10. **CharRangeLayer per-character glyph selection.** Phase 1 ships the slot-helper stub from spec §4. Once pdomain-book-tools' `CharBBox` is published (commit `f11924d`) and `Word.chars` is wired through codegen, fill in the actual hit-testing + render logic. Own plan.
