# pd-ocr-trainer retirement — design

**Date:** 2026-05-21
**Status:** Approved design — pending implementation plan
**Scope:** Cross-cut (three repos: `pd-ocr-trainer`, `pdomain-ocr-trainer-spa`, new `pdomain-ocr-training`)

## Goal

Retire the legacy NiceGUI `pd-ocr-trainer` repo. Its function is replaced by a
FastAPI + React/Vite SPA (`pdomain-ocr-trainer-spa`) built on the workspace-standard
`pdomain-ui` + `pdomain-ops` stack, with the torch/DocTR training code extracted into a
new peer package so the heavy ML dependency stays contained.

## Background

- `pd-ocr-trainer` is a working NiceGUI app: profile selector, dataset kanban
  board, detection/recognition config cards, training controls, and a live
  training-output log. Non-UI subsystems: `train_detect.py`, `train_recog.py`,
  `dataset_store.py` (`ExportManager`), `utils.py`.
- `pdomain-ocr-trainer-spa` exists but is **spec-only — zero code**. Its 18 specs
  (M0–M9) predate the workspace decision to standardize SPAs on `pdomain-ui` +
  `pdomain-ops`. They explicitly reject `pdomain-ui` (D-004: shadcn/ui + Tailwind) and
  assume `pd-ocr-trainer` keeps existing (D-T1: call its training code by
  subprocess). Both assumptions are now stale.

Because the existing specs conflict with the target architecture, the trainer
SPA gets a **full re-spec** modeled on the shipped `pdomain-ocr-labeler-spa`.

## Target architecture — three repos

| Repo | Role |
|------|------|
| **`pdomain-ocr-training`** *(new peer package)* | Ops-style library. Owns `train_detect`, `train_recog`, `dataset_store`/`ExportManager`, `utils`, vocab. `torch` + DocTR deps live **only here**. Ships an `ITrainingRunner` Protocol + a `LocalTrainingRunner` implementation, mirroring how `pdomain-ops` ships `StageDispatcher`/`LongJobRunner`. |
| **`pdomain-ocr-trainer-spa`** *(full re-spec)* | Thin FastAPI + React/Vite app. Depends on `pdomain-ops` (suite plumbing, GPU dispatch) + `pdomain-ocr-training` (runner Protocol) + `pdomain-ui` (frontend). Its own code never imports `torch` — it drives the runner Protocol. |
| **`pd-ocr-trainer`** *(legacy)* | Deleted once the SPA reaches core parity. |

The other SPA backends (`pdomain-ocr-simple-gui`, `pdomain-prep-for-pgdp`,
`pdomain-ocr-labeler-spa`) stay torch-free — they never depend on `pdomain-ocr-training`.

## Component inventory & migration mapping

Legacy `pd-ocr-trainer` decomposes into two halves.

### Non-UI → `pdomain-ocr-training`

| Legacy file | Destination |
|---|---|
| `train_detect.py`, `train_recog.py` | `pdomain-ocr-training`, wrapped behind the `ITrainingRunner` Protocol |
| `dataset_store.py` (`ExportManager`) | `pdomain-ocr-training` — dataset/profile/disk-layout logic |
| `utils.py` (`EarlyStopper`, plotting) | `pdomain-ocr-training` |

Existing tests move with their modules. The on-disk dataset layout
(`ml-training/<profile>/{detection,recognition}/`, `ml-validation/...`,
`matched-ocr/`, `dist/`) is unchanged.

### UI (NiceGUI → React/pdomain-ui in `pdomain-ocr-trainer-spa`)

| Legacy NiceGUI element | pdomain-ui mapping |
|---|---|
| App header/banner | `AppShell` + `TopNav` + `LauncherSlot` / `useSuiteSiblings` |
| Profile selector | `Select` primitive + a profiles store |
| Detection / Recognition config cards | `Card` + `Accordion` (expandable help) + `Field`/`FieldRow` + `Select` |
| Training control buttons | `Button` primitives |
| Training run / progress | `Progress` + `JobStatusPip` + `useLongJob` (SSE) |
| Live training-output log | **Gap** — built in the SPA (see below) |
| Dataset kanban (drag-drop columns) | **Gap** — built in the SPA (see below) |

## pdomain-ui gaps

`pdomain-ui` covers roughly 80% of the trainer UI off the shelf. Two components are
missing and used only by the trainer today:

1. **DnD kanban board** — the dataset-assignment UI (`dnd-kit`).
2. **Live-log / streaming-text viewer** — the training-output panel
   (`useLongJob` supplies SSE state but there is no log-viewer component).

**Decision:** build both **in `pdomain-ocr-trainer-spa` first**. Promote to `pdomain-ui`
later only if another app needs them — a log viewer plausibly will, a kanban
probably will not. Do not pre-generalize into `pdomain-ui` now (YAGNI).

## Retirement sequence

1. **Re-spec `pdomain-ocr-trainer-spa`** — full rewrite of its 18 specs targeting
   `pdomain-ui` + `pdomain-ops` + `pdomain-ocr-training`, modeled on shipped
   `pdomain-ocr-labeler-spa`.
2. **Scaffold `pdomain-ocr-training`** — spec the new peer package; move the four
   non-UI modules (with tests) out of `pd-ocr-trainer`.
3. **Build the SPA to core parity** — milestone-by-milestone. Core parity = the
   working NiceGUI feature set (profiles, dual kanban, detection + recognition
   config, live training log, training runs).
4. **Parity acceptance → delete `pd-ocr-trainer`** — remove the repo, retire its
   subagent (`pd-ocr-trainer` / `pd-ocr-trainer-docs`), and update the workspace
   `CLAUDE.md` project table and routing section.

## Deferred scope

The legacy `pd-ocr-trainer` HF-datasets roadmap (`docs/architecture/datasets.md`,
`docs/plans/roadmap.md`) and the glyph-feature-classifier specs
(`glyph-feature-classifier.md`, `glyph-annotation-eval-slicing.md`) were never
implemented. They are **carried forward** into `pdomain-ocr-trainer-spa` as
post-core-parity milestones so the design intent survives the repo deletion.
They are out of scope for the core-parity work.

## Plan artifacts

A single **cross-cut plan** in `ConcaveTrillion/ocr-container-meta` tracks the
whole retirement: `pdomain-ocr-training` extraction, `pdomain-ocr-trainer-spa` re-spec and
build, and `pd-ocr-trainer` deletion. This keeps the retirement visible as one
effort rather than scattered per-repo issues.

## Decisions

- **D-1** Training code → new peer package `pdomain-ocr-training`, not `pdomain-ops`
  (keeps torch out of every SPA backend) and not the SPA itself.
- **D-2** `pdomain-ocr-training` follows the ops-style pattern: `ITrainingRunner`
  Protocol + `LocalTrainingRunner` implementation.
- **D-3** `pdomain-ocr-trainer-spa` gets a full re-spec; the existing 18 specs are
  superseded.
- **D-4** Kanban + log-viewer components built in the SPA, not pre-promoted to
  `pdomain-ui`.
- **D-5** Core parity before deletion; HF-datasets + glyph-classifier roadmaps
  deferred as later milestones.
- **D-6** One cross-cut plan in `ocr-container-meta`.
