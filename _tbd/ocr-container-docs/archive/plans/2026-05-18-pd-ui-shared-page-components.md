---
title: "pdomain-ui shared page components + prefs model alignment"
created: 2026-05-18
repo: ConcaveTrillion/ocr-container-meta
milestone: ~
status: complete
---

# pdomain-ui shared page components + prefs model alignment

Extracts reusable layout components and the common UIPrefs model from pdomain-ocr-simple-gui
into their canonical homes (pdomain-ui and pdomain-ocr-ops), so pdomain-ocr-labeler-spa and
pdomain-prep-for-pgdp can consume them without re-implementing.

## Background

pdomain-ocr-simple-gui was built first and contains patterns that every pd-* SPA will need:
- A `UIPrefsSubset` Pydantic model for persisting AppShell UI prefs (theme/density/fontScale)
- A two-panel page viewer layout (toolbar + image canvas + text editor)
- A "recent jobs" table with status chips
- A job-config dialog shell (source path, project name, output dir, save/cancel)

pdomain-ocr-ops already owns `CommonUIPrefs` (theme/density) — fontScale just needs adding.
The layout components belong in pdomain-ui alongside `PageImageCanvas` and `AppShell`.

## Tasks

### Group A — Prefs model alignment (small)

{#prefs-ops}
**A1 (S) #249: pdomain-ocr-ops — add `font_scale` to `CommonUIPrefs`, ensure public export**

- Add `font_scale: float = 1.0` to `pd_ocr_ops.suite.types.CommonUIPrefs`
- Validate it's exported from `pd_ocr_ops.suite` public surface
- Update any existing tests that compare full `CommonUIPrefs` serialization
- TDD: test round-trips `font_scale` through `LocalFilePrefs`

{#prefs-gui}
**A2 (S) #250: pdomain-ocr-simple-gui — replace `UIPrefsSubset` with imported `CommonUIPrefs`**

- Remove `UIPrefsSubset` model from `src/pd_ocr_simple_gui/models.py`
- Change `AppPrefs.ui_prefs` field type from `UIPrefsSubset | None` to
  `CommonUIPrefs | None` (imported from `pd_ocr_ops.suite`)
- Update any tests that reference `UIPrefsSubset`
- Blocked-by: A1

### Group B — Shared page components in pdomain-ui (medium)

{#page-split-view}
**B1 (M) #251: pdomain-ui — `PageSplitView` layout component**

Two-panel document viewer layout extracted from pdomain-ocr-simple-gui's `PageViewPage`.

Props API:
```tsx
<PageSplitView
  toolbar={ReactNode}   // full-width toolbar row (nav + actions)
  canvas={ReactNode}    // left panel — image canvas
  editor={ReactNode}    // right panel — text / editor
/>
```

CSS: `.page-split-view`, `.page-split-view__toolbar`, `.page-split-view__panels`,
`.page-split-view__canvas-panel`, `.page-split-view__editor-panel` added to
`theme/primitives.css`.

Export from `@concavetrillion/pdomain-ui/primitives`.

{#base-job-config-dialog}
**B2 (M) #252: pdomain-ui — `BaseJobConfigDialog` slot-based dialog**

Common shell for job-start dialogs shared across OCR apps.

Props:
```tsx
<BaseJobConfigDialog
  open={boolean}
  title={string}
  description={string}
  sourcePath={string}
  onClose={() => void}
  onSubmit={(base: BaseJobConfig) => Promise<void>}
  submitLabel={string}          // default "Run →"
  validationError={string|null} // lifted error display
>
  {/* App-specific fields inserted here */}
</BaseJobConfigDialog>
```

`BaseJobConfig`: `{ projectName: string; outputDir: string }`.

Handles: project-name input, output-dir input, error banner, submit/cancel buttons,
loading state on submit. App-specific fields (engine, language, options) go in `children`.

Export from `@concavetrillion/pdomain-ui/primitives`.

{#shared-table-css}
**B3 (S) #253: pdomain-ui — shared jobs-table CSS in `primitives.css`**

Promote `.recent-projects__*` CSS from pdomain-ocr-simple-gui's `app.css` to pdomain-ui's
`theme/primitives.css` as generic `.jobs-table`, `.jobs-table__row`, `.jobs-table__th`,
`.jobs-table__name`, `.jobs-table__date`, `.jobs-table__status` classes.

No component — CSS-only, apps use the classes directly in their markup.

### Group C — pdomain-ocr-simple-gui migration

{#migrate-page-view}
**C1 (M) #254: pdomain-ocr-simple-gui — migrate `PageViewPage` to `PageSplitView`**

Replace the inline `.page-view-page__*` CSS and layout structure in `PageViewPage.tsx`
with `<PageSplitView>` from pdomain-ui. Remove the `.page-view-page__*` blocks from `app.css`.
Blocked-by: B1

{#migrate-recent-list}
**C2 (S) #255: pdomain-ocr-simple-gui — migrate `RecentProjectsList` to shared table CSS**

Replace `.recent-projects__*` classes in `RecentProjectsList.tsx` + `app.css` with
the shared `.jobs-table*` classes from pdomain-ui.
Blocked-by: B3

{#migrate-job-config}
**C3 (M) #256: pdomain-ocr-simple-gui — migrate `JobConfigDialog` to `BaseJobConfigDialog`**

Replace the dialog shell in `JobConfigDialog.tsx` with `<BaseJobConfigDialog>`.
App-specific fields (engine select, language, save_json, combined_txt) become children.
Remove the now-redundant `job-config-dialog__*` CSS from `app.css`.
Blocked-by: B2
