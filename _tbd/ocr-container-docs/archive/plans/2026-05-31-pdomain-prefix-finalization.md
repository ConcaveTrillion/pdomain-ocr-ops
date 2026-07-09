# pd-* to pdomain-* Finalization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace remaining active `pd-` / `pd_` public names with `pdomain-` / `pdomain_` across the kept pdomain repos, including CLI names, dispatch events, local-dev markers, dataset metadata keys, and Hugging Face model identifiers.

**Architecture:** Execute from upstream dependencies down to downstream apps. Do not add compatibility aliases: this workspace has no external users yet. Skip legacy checkout directories and archived/historical references unless an active kept repo consumes the value at runtime.

**Tech Stack:** Git worktrees or clean repo branches, uv/Python, npm/Node, GitHub Actions YAML, Hugging Face model repo metadata, shell scripts, workspace Makefiles.

---

## Execution status — 2026-05-31 / 2026-06-01

Stages 1–6 complete; all 12 target repos committed and **pushed** to `pdomain/*`
on `main`. **Stage 7 (releases) is SUPERSEDED — folded into the page-split plan**
(`docs/plans/2026-05-31-page-split-book-tools.md`, Plan 1 of 5). See
"Stage 7 status — deferred" below for what shipped standalone vs what rides out
with page-split.

- **Stages 2–5 renames landed** on every repo. The three downstream apps were
  finished this session: `pdomain-ocr-trainer-spa` (`42bfc17`, a prior Codex
  branch verified complete, `make ci` green), `pdomain-ocr-labeler-spa`
  (`81b4b46`, Task 10), `pdomain-ocr-simple-gui` (`c6e341d`, Task 12).
- **Stage 6 cleanup** caught four release-dispatch publishers still emitting the
  old event (`pd-release-published` in `pdomain-book-tools`, `pdomain-ops`,
  `pdomain-ocr-synth`; `pd-npm-publish` in `pdomain-ui`) — these would not have
  triggered index regen. Fixed and folded into each repo's rename commit, plus
  two `.gitignore` local-mode marker leftovers (`pdomain-ops`,
  `pdomain-ocr-simple-gui`). Index listeners confirmed: pip →
  `pdomain-release-published`, npm → `pdomain-npm-publish`.
- **Classified-acceptable residual `pd-` hits** (intentionally kept):
  `pdomain-ocr-labeler-spa/tests/unit/test_m0_acceptance.py` (pins archived M0
  doc text); `pdomain-index-pip/tests/test_dispatch_event_name.py` (negative
  test asserting old name absent); `pdomain-ocr-cli/docs/plans/2026-05-29-…md`
  (historical plan-doc snippets).
- **Known pre-existing red CI, NOT caused by the rename** (carried on `main`
  before this work): `pdomain-ocr-labeler-spa` — 7× `test_release_workflow.py`
  + 1× `test_dockerfile.py` (release-workflow shape drift) + 2× OCR-integration
  (model weights unavailable in env); `pdomain-ocr-simple-gui` — `frontend-build`
  fails against registry `pdomain-ui` 0.2.2 (missing `/hooks` subpath +
  `ShortcutsHelpButton`). Both must be resolved before those two repos release.
- **Follow-up flagged:** `pdomain-ocr-labeler-spa` Task 10 renamed the runtime
  data-root default (`pd-ocr-labeler` → `pdomain-ocr-labeler-spa`), which
  reverses decision D-003 (`specs/17-decisions.md`, left untouched as out of
  scope) and does not auto-migrate any existing on-disk labels. Consistent with
  the plan's "no external users yet"; update/supersede D-003 separately.

---

## Scope

### In Scope

- Active repos under `/workspaces/ocr-container/pdomain-*`.
- Active source, tests, Makefiles, install scripts, workflows, README/CLAUDE docs, and non-archived process docs.
- Public identifiers:
  - `pd-ocr` -> `pdomain-ocr`
  - `pd-ocr-labeler-ui` -> `pdomain-ocr-labeler-ui`
  - `pd-ocr-trainer-ui` -> `pdomain-ocr-trainer-ui`
  - `pd-release-published` -> `pdomain-release-published`
  - `pd-npm-publish` -> `pdomain-npm-publish`
  - `.pd-local-mode` -> `.pdomain-local-mode`
  - `.pd-dev-local` -> `.pdomain-dev-local`
  - `PD_DEV_LOCAL` -> `PDOMAIN_DEV_LOCAL`
  - `update-pd-deps` -> `update-pdomain-deps`
  - `CT2534/pd-ocr-models` -> `pdomain/pdomain-ocr-models`
  - `pd-ml-models` -> `pdomain-ml-models`
  - `pd-ocr-*` metadata keys -> `pdomain-ocr-*`
  - `doctr-pd-labeled` -> `doctr-pdomain-labeled`

### Out Of Scope

- Legacy checkout directories:
  - `/workspaces/ocr-container/pd-ocr-labeler`
  - `/workspaces/ocr-container/pd-ocr-trainer`
  - `/workspaces/ocr-container/pd-png-optimizer`
- Archived docs and historical research unless an active test imports them:
  - `docs/archive/**`
  - `specs/**`
  - `docs/research/**`
- Negative tests that intentionally mention old names to assert rejection, as long as the test name/comment makes that intent explicit.

### No Compatibility Policy

Do not keep old aliases for commands, events, marker files, config dirs, or metadata keys. Rename and update every active consumer in the same dependency stage.

---

## Dependency Order

1. External model/data identity.
2. Foundation libraries: `pdomain-book-tools`, `pdomain-ui`, `pdomain-ops`.
3. Index infrastructure: `pdomain-index-pip`, `pdomain-index-npm`.
4. Core OCR producers/consumers: `pdomain-ocr-cli`, `pdomain-ocr-training`, `pdomain-ocr-synth`.
5. Downstream apps: `pdomain-ocr-labeler-spa`, `pdomain-ocr-trainer-spa`, `pdomain-ocr-simple-gui`, `pdomain-prep-for-pgdp`.
6. Workspace-wide cleanup and release.

---

## Global Preflight

- [ ] **Step 1: Confirm each target repo state.**

Run:

```bash
for repo in \
  pdomain-book-tools \
  pdomain-ui \
  pdomain-ops \
  pdomain-index-pip \
  pdomain-index-npm \
  pdomain-ocr-cli \
  pdomain-ocr-training \
  pdomain-ocr-synth \
  pdomain-ocr-labeler-spa \
  pdomain-ocr-trainer-spa \
  pdomain-ocr-simple-gui \
  pdomain-prep-for-pgdp
do
  echo "== $repo =="
  git -C "/workspaces/ocr-container/$repo" status --short --branch
done
```

Expected: each repo is on `main`, clean or only has unrelated user changes explicitly accepted before the stage begins.

- [ ] **Step 2: Create a tracking issue or checklist doc for old-to-new identifiers.**

Modify: `docs/plans/2026-05-31-pdomain-prefix-finalization.md`

Add a dated note under this plan with any identifier decisions discovered during execution. Keep this plan as the single source for the rollout.

- [ ] **Step 3: Capture the baseline search.**

Run:

```bash
rg -n \
  --glob '!**/.git/**' \
  --glob '!**/node_modules/**' \
  --glob '!**/.venv/**' \
  --glob '!**/dist/**' \
  --glob '!**/_site/**' \
  --glob '!**/docs/archive/**' \
  --glob '!**/specs/**' \
  --glob '!**/docs/research/**' \
  'pd-|pd_' /workspaces/ocr-container/pdomain-* \
  > /tmp/pdomain-prefix-baseline.txt
wc -l /tmp/pdomain-prefix-baseline.txt
```

Expected: large nonzero count. Save the output path in the execution notes; do not commit `/tmp` output.

---

## Stage 1: External Model And Dataset Identity

### Task 1: Rename Hugging Face model identity

**Repos affected later:** `pdomain-book-tools`, `pdomain-ocr-cli`, `pdomain-ops`, `pdomain-ocr-labeler-spa`, `pdomain-prep-for-pgdp`.

- [x] **Step 1: Create or rename the HF model repository.**

Target: `pdomain/pdomain-ocr-models`

Move/copy the current model files from `CT2534/pd-ocr-models` into the new repo. Preserve the internal layout unless intentionally renamed in Step 2:

```text
detection/pd-all-detection-model-finetuned.pt
recognition/pd-all-recognition-model-finetuned.pt
```

- [x] **Step 2: Decide whether model filenames also rename.**

Preferred final names:

```text
detection/pdomain-all-detection-model-finetuned.pt
recognition/pdomain-all-recognition-model-finetuned.pt
```

If files are renamed, every downstream default must change in the same stage. Since there are no external users, do not support both old and new filenames.

- [x] **Step 3: Verify anonymous/public download works.**

Run a direct download or `huggingface_hub` probe from a clean shell.

Expected: no authentication required for the model files used by the apps.

**Execution note, 2026-05-31:** User transferred `CT2534/pd-ocr-models` to `pdomain/pdomain-ocr-models`. Ran `scripts/rename-hf-ocr-model-files.py --apply` to rename every `pd-all-*` OCR detection/recognition file to `pdomain-all-*`, including dated checkpoints and sidecars. Verification:

```text
old_count 0
new_count 15
200 detection/pdomain-all-detection-model-finetuned.pt
200 recognition/pdomain-all-recognition-model-finetuned.pt
404 detection/pd-all-detection-model-finetuned.pt
404 recognition/pd-all-recognition-model-finetuned.pt
```

`pdomain/PP-DocLayout_plus-L` was also transferred, but this rollout leaves its active OCR-tooling references unchanged unless a later code search finds a runtime consumer that must move.

---

## Stage 2: Foundation Libraries

### Task 2: `pdomain-book-tools`

**Primary role:** Shared Python foundation. Must land before Python consumers.

**Likely files:**

- `pdomain_book_tools/hf/models.py`
- `pdomain_book_tools/hf/__init__.py`
- `pdomain_book_tools/image_processing/formats.py`
- `pdomain_book_tools/layout/registry.py`
- `pdomain_book_tools/licenses.py`
- `scripts/check_dev_local.py`
- `scripts/write_dev_local_marker.py`
- `scripts/local-*.sh`
- `Makefile`
- `tests/**`
- active docs/CLAUDE/README/CHANGELOG

- [x] **Step 1: Rename HF defaults.**

Change:

```text
CT2534/pd-ocr-models -> pdomain/pdomain-ocr-models
detection/pd-all-detection-model-finetuned.pt -> detection/pdomain-all-detection-model-finetuned.pt
recognition/pd-all-recognition-model-finetuned.pt -> recognition/pdomain-all-recognition-model-finetuned.pt
```

**Execution note, 2026-05-31:** Landed locally in `pdomain-book-tools` commit `ba7f730` (`rename: use pdomain OCR model defaults`). Verified with focused HF-default test and `make ci`:

```text
2163 passed, 1 skipped, 5 xfailed
Required test coverage of 87.0% reached. Total coverage: 90.15%
Successfully built dist/pdomain_book_tools-0.15.3.dev8+g71a0daa18.d20260531-py3-none-any.whl
```

- [ ] **Step 2: Rename local-dev markers and env vars.**

Change:

```text
.pd-local-mode -> .pdomain-local-mode
.pd-dev-local -> .pdomain-dev-local
PD_DEV_LOCAL -> PDOMAIN_DEV_LOCAL
```

Do not read the old marker names after this change.

- [ ] **Step 3: Rename generic suite wording.**

Change active prose/comments:

```text
pd-* -> pdomain-*
pd-ocr-labeler -> pdomain-ocr-labeler-spa, unless explicitly referring to skipped legacy repo
pd-ocr-trainer -> pdomain-ocr-training or pdomain-ocr-trainer-spa, based on context
```

- [ ] **Step 4: Run focused searches.**

Run:

```bash
cd /workspaces/ocr-container/pdomain-book-tools
rg -n 'pd-|pd_|PD_DEV_LOCAL|pd-ocr-models|pd-all|\.pd-' .
```

Expected: only explicit legacy or negative-test references remain.

- [ ] **Step 5: Verify.**

Run:

```bash
make ci
git diff --check
```

Expected: both pass.

- [ ] **Step 6: Commit.**

```bash
git add -A
git commit -m "rename: use pdomain prefix across book tools"
```

### Task 3: `pdomain-ui`

**Primary role:** Shared frontend package for downstream SPAs.

**Likely files:**

- `package.json`
- `Makefile`
- `scripts/update-pd-deps.sh`
- `README.md`
- `CLAUDE.md`
- `CHANGELOG.md`
- `src/**`
- `docs/usage/**`
- `tests/codegen/fetch.test.ts`

- [ ] **Step 1: Rename dependency-refresh command.**

Change:

```text
scripts/update-pd-deps.sh -> scripts/update-pdomain-deps.sh
make update-pd-deps -> make update-pdomain-deps
```

Do not keep the old Make target.

- [ ] **Step 2: Rename generic suite wording.**

Change active prose/comments:

```text
pd-* -> pdomain-*
pd-prep -> pdomain-prep, if it is not a literal old path
pd-index -> pdomain-index-pip or pdomain-index-npm, based on context
```

- [ ] **Step 3: Update tests that accept old index names.**

In `tests/codegen/fetch.test.ts`, remove acceptance of old `pd-index` / `concavetrillion.*pd-index` strings unless the test is explicitly validating rejection.

- [ ] **Step 4: Verify.**

Run:

```bash
npm test
make ci
git diff --check
```

Expected: all pass.

- [ ] **Step 5: Commit.**

```bash
git add -A
git commit -m "rename: use pdomain prefix across ui package"
```

### Task 4: `pdomain-ops`

**Primary role:** Shared operational library and local suite launcher.

**Likely files:**

- `Makefile`
- `scripts/update-pd-deps.sh`
- `scripts/local-*.sh`
- `pdomain_ops/**`
- `tests/suite/**`
- `README.md`
- `CLAUDE.md`

- [ ] **Step 1: Rename dependency-refresh command and scripts.**

Change `update-pd-deps` to `update-pdomain-deps` everywhere.

- [ ] **Step 2: Rename local-dev markers.**

Change `.pd-local-mode` and `.pd-dev-local` to `.pdomain-local-mode` and `.pdomain-dev-local`.

- [ ] **Step 3: Rename test app IDs.**

Examples:

```text
pd-test-app -> pdomain-test-app
pd-app-a -> pdomain-app-a
pd-app-b -> pdomain-app-b
```

- [ ] **Step 4: Rename HF/model references.**

Change `CT2534/pd-ocr-models` and `pd-ml-models` if present.

- [ ] **Step 5: Verify.**

Run:

```bash
make ci
git diff --check
```

Expected: both pass.

- [ ] **Step 6: Commit.**

```bash
git add -A
git commit -m "rename: use pdomain prefix across ops"
```

---

## Stage 3: Index Infrastructure

### Task 5: `pdomain-index-pip`

**Primary role:** PEP 503 index for Python release assets.

- [ ] **Step 1: Rename dispatch event.**

Change:

```text
pd-release-published -> pdomain-release-published
```

Touch:

- `.github/workflows/regen.yml`
- `README.md`
- workflow tests, if present

- [ ] **Step 2: Keep self-release workflow_call unchanged.**

Do not reintroduce self-dispatch. `release.yml` should continue to call `regen.yml` directly.

- [ ] **Step 3: Verify.**

Run:

```bash
make ci
git diff --check
```

Expected: both pass.

- [ ] **Step 4: Commit.**

```bash
git add -A
git commit -m "rename: use pdomain release dispatch event"
```

### Task 6: `pdomain-index-npm`

**Primary role:** Static npm registry for `@pdomain/*`.

- [ ] **Step 1: Rename dispatch event.**

Change:

```text
pd-npm-publish -> pdomain-npm-publish
```

Touch:

- `.github/workflows/regen.yml`
- `README.md`
- `tests/test_workflows.test.ts`

- [ ] **Step 2: Keep self-release workflow_call unchanged.**

Do not reintroduce self-dispatch. `release.yml` should continue to call `regen.yml` directly.

- [ ] **Step 3: Verify.**

Run:

```bash
make ci
git diff --check
```

Expected: both pass.

- [ ] **Step 4: Commit.**

```bash
git add -A
git commit -m "rename: use pdomain npm dispatch event"
```

---

## Stage 4: Core OCR Producers And Consumers

### Task 7: `pdomain-ocr-cli`

**Primary role:** User-facing OCR CLI and HF model consumer.

**Likely files:**

- `pyproject.toml`
- `pdomain_ocr_cli/**`
- `install.sh`
- `install.ps1`
- `scripts/install-uv-tool.sh`
- `scripts/local-*.sh`
- `scripts/update-pd-deps.sh`
- `Makefile`
- `README.md`
- `DEVELOPMENT.md`
- `docs/**`
- `tests/**`
- `.github/workflows/release.yml`

- [ ] **Step 1: Rename console command.**

Change:

```text
pd-ocr -> pdomain-ocr
```

In `pyproject.toml`, the script entry should become:

```toml
pdomain-ocr = "pdomain_ocr_cli.ocr_to_txt:main"
```

- [ ] **Step 2: Rename HF defaults and model filenames.**

Change to `pdomain/pdomain-ocr-models` and `pdomain-all-*` filenames.

- [ ] **Step 3: Rename local-dev markers and update-deps command.**

Change `.pd-local-mode`, `.pd-dev-local`, `PD_DEV_LOCAL`, and `update-pd-deps`.

- [ ] **Step 4: Rename release dispatch event.**

Change publisher notification to:

```text
pdomain-release-published
```

- [ ] **Step 5: Verify.**

Run:

```bash
make ci
make wheel-smoke
git diff --check
```

Expected: all pass.

- [ ] **Step 6: Commit.**

```bash
git add -A
git commit -m "rename: use pdomain prefix across ocr cli"
```

### Task 8: `pdomain-ocr-training`

**Primary role:** Training/data pipeline consumed by trainer SPA and synth.

- [ ] **Step 1: Rename app/model-store constants.**

Change:

```text
pd-ocr-labeler -> pdomain-ocr-labeler-spa
pd-ml-models -> pdomain-ml-models
```

- [ ] **Step 2: Rename local-dev markers and update-deps command.**

Change `.pd-local-mode`, `.pd-dev-local`, `PD_DEV_LOCAL`, and `update-pd-deps`.

- [ ] **Step 3: Rename release dispatch event.**

Change publisher notification to `pdomain-release-published`.

- [ ] **Step 4: Verify.**

Run:

```bash
make ci
git diff --check
```

Expected: both pass.

- [ ] **Step 5: Commit.**

```bash
git add -A
git commit -m "rename: use pdomain prefix across ocr training"
```

### Task 9: `pdomain-ocr-synth`

**Primary role:** Synthetic dataset producer; owns many dataset metadata keys.

- [ ] **Step 1: Rename trainer format strings.**

Change:

```text
pd-ocr-trainer/v1 -> pdomain-ocr-training/v1
```

- [ ] **Step 2: Rename dataset/card metadata keys.**

Change:

```text
pd-ocr-shape -> pdomain-ocr-shape
pd-ocr-source -> pdomain-ocr-source
pd-ocr-recipe-sha -> pdomain-ocr-recipe-sha
pd-ocr-render-tool-version -> pdomain-ocr-render-tool-version
pd-ocr-content-sha -> pdomain-ocr-content-sha
```

- [ ] **Step 3: Rename HF tags and repo examples.**

Change `pd-ocr` tags and sample repos to `pdomain-ocr` equivalents.

- [ ] **Step 4: Rename release dispatch event.**

Change publisher notification to `pdomain-release-published`.

- [ ] **Step 5: Verify.**

Run:

```bash
make ci
git diff --check
```

Expected: both pass.

- [ ] **Step 6: Commit.**

```bash
git add -A
git commit -m "rename: use pdomain prefix across ocr synth"
```

---

## Stage 5: Downstream Apps

### Task 10: `pdomain-ocr-labeler-spa`

**Primary role:** Labeler app; depends on renamed CLI/model/training conventions.

- [ ] **Step 1: Rename console command.**

Change:

```text
pd-ocr-labeler-ui -> pdomain-ocr-labeler-ui
```

Update `pyproject.toml`, Dockerfile, install scripts, docs, tests, and `local-run.sh`.

- [ ] **Step 2: Rename default paths and metadata.**

Change:

```text
pd-ocr-labeler -> pdomain-ocr-labeler-spa
pd-ml-models -> pdomain-ml-models
doctr-pd-labeled -> doctr-pdomain-labeled
```

- [ ] **Step 3: Rename HF defaults and model filenames.**

Use `pdomain/pdomain-ocr-models` and `pdomain-all-*` filenames.

- [ ] **Step 4: Rename local-dev markers and update-deps command.**

Change `.pd-local-mode`, `.pd-dev-local`, `PD_DEV_LOCAL`, and `update-pd-deps`.

- [ ] **Step 5: Rename release dispatch event.**

Change publisher notification to `pdomain-release-published`.

- [ ] **Step 6: Verify.**

Run:

```bash
make ci
git diff --check
```

Expected: backend and frontend checks pass.

- [ ] **Step 7: Commit.**

```bash
git add -A
git commit -m "rename: use pdomain prefix across labeler spa"
```

### Task 11: `pdomain-ocr-trainer-spa`

**Primary role:** Trainer UI app.

- [ ] **Step 1: Rename console command.**

Change:

```text
pd-ocr-trainer-ui -> pdomain-ocr-trainer-ui
```

Update `pyproject.toml`, Dockerfile, install scripts, docs, tests, and `local-run.sh`.

- [ ] **Step 2: Rename training/core references.**

Change:

```text
pd-ocr-trainer -> pdomain-ocr-training or pdomain-ocr-trainer-spa, based on context
pd-ml-ci -> pdomain-ml-ci
```

- [ ] **Step 3: Rename local-dev markers and update-deps command.**

Change `.pd-local-mode`, `.pd-dev-local`, `PD_DEV_LOCAL`, and `update-pd-deps`.

- [ ] **Step 4: Rename release dispatch event.**

Change publisher notification to `pdomain-release-published`.

- [ ] **Step 5: Verify.**

Run:

```bash
make ci
git diff --check
```

Expected: backend and frontend checks pass.

- [ ] **Step 6: Commit.**

```bash
git add -A
git commit -m "rename: use pdomain prefix across trainer spa"
```

### Task 12: `pdomain-ocr-simple-gui`

**Primary role:** GUI wrapper around OCR flow.

- [ ] **Step 1: Update CLI references.**

Change `pd-ocr` references to `pdomain-ocr`.

- [ ] **Step 2: Rename local-dev markers and update-deps command.**

Change `.pd-local-mode`, `.pd-dev-local`, `PD_DEV_LOCAL`, and `update-pd-deps`.

- [ ] **Step 3: Rename release dispatch event.**

Change publisher notification to `pdomain-release-published`.

- [ ] **Step 4: Verify.**

Run:

```bash
make ci
git diff --check
```

Expected: both pass.

- [ ] **Step 5: Commit.**

```bash
git add -A
git commit -m "rename: use pdomain prefix across simple gui"
```

### Task 13: `pdomain-prep-for-pgdp`

**Primary role:** Downstream app consuming OCR/model/tooling defaults.

- [ ] **Step 1: Update CLI and legacy repo references.**

Change active `pd-ocr` command references to `pdomain-ocr`. Change active `pd-ocr-labeler` / `pd-ocr-trainer` dependency references to their kept `pdomain-*` repo names.

- [ ] **Step 2: Rename model/cache defaults.**

Change `CT2534/pd-ocr-models`, `pd-all-*`, and `pd-ml-models` to the final `pdomain-*` names.

- [ ] **Step 3: Rename local-dev markers and update-deps command.**

Change `.pd-local-mode`, `.pd-dev-local`, `PD_DEV_LOCAL`, and `update-pd-deps`.

- [ ] **Step 4: Rename release dispatch event.**

Change publisher notification to `pdomain-release-published`.

- [ ] **Step 5: Verify.**

Run:

```bash
make ci
git diff --check
```

Expected: both pass.

- [ ] **Step 6: Commit.**

```bash
git add -A
git commit -m "rename: use pdomain prefix across prep for pgdp"
```

---

## Stage 6: Workspace Cleanup

- [ ] **Step 1: Search active surfaces for old names.**

Run:

```bash
rg -n \
  --glob '!**/.git/**' \
  --glob '!**/node_modules/**' \
  --glob '!**/.venv/**' \
  --glob '!**/dist/**' \
  --glob '!**/_site/**' \
  --glob '!**/docs/archive/**' \
  --glob '!**/specs/**' \
  --glob '!**/docs/research/**' \
  'pd-|pd_|PD_DEV_LOCAL|\.pd-' /workspaces/ocr-container/pdomain-*
```

Expected: only explicit skipped legacy references and negative tests remain.

- [ ] **Step 2: Inspect remaining matches manually.**

For each remaining active match, classify it inline:

```text
legacy reference to skipped repo
negative test fixture
archival/historical context
```

If it does not fit one of those, rename it before proceeding.

- [ ] **Step 3: Run repo CI again in dependency order.**

Run each:

```bash
make ci
git diff --check
```

Expected: all pass.

---

## Stage 7 status — DEFERRED into the page-split plan (2026-06-01)

**Superseded.** CT decided to stop the standalone rename-only release train and
let the remaining releases ride out with `docs/plans/2026-05-31-page-split-book-tools.md`
(Plan 1 of 5) and its successor plans, which re-release the same core repos
anyway. The rename code is already merged on `main` in every repo, so each
page-split release will ship the rename for free.

**Released standalone before deferral (3):**

| Repo | Tag | Index |
|---|---|---|
| `pdomain-book-tools` | v0.16.0 | pip index refreshed ✅ |
| `pdomain-ui` | v0.3.0 | npm index NOT refreshed (dispatch token 403 — see infra blockers) |
| `pdomain-ops` | v0.5.0 | pip index refreshed ✅ |

**Deferred — rename on `main`, not yet released (5):** `pdomain-ocr-cli`,
`pdomain-ocr-training`, `pdomain-ocr-synth`, `pdomain-ocr-trainer-spa`,
`pdomain-prep-for-pgdp`. Next minor would be cli v0.8.0, training v0.3.0,
synth v0.1.0, trainer-spa v0.1.0, prep v0.2.0 — but these now release via
page-split, not here.

**Still-blocked apps (no rename release yet):** `pdomain-ocr-labeler-spa`,
`pdomain-ocr-simple-gui` — see pre-existing red CI above. simple-gui's frontend
blocker is resolved once it upgrades to `@pdomain/pdomain-ui@0.3.0` (already
exports `/hooks` + `ShortcutsHelpButton`), which needs the npm index refreshed.

### Infra blockers carried forward (must clear before ANY future release)

These are org-migration artifacts surfaced by the release train; they block
releases regardless of which plan triggers them:

1. **GitHub Actions disabled** on `pdomain-ocr-training`, `pdomain-ocr-synth`,
   `pdomain-ocr-labeler-spa`, `pdomain-ocr-trainer-spa`, `pdomain-ocr-simple-gui`,
   `pdomain-prep-for-pgdp`. (Already enabled during the train on book-tools, ui,
   ops, index-pip, index-npm, **cli**.) Enable per repo:
   `gh api --method PUT repos/pdomain/<repo>/actions/permissions --field enabled=true`.
2. **`PD_NPM_DISPATCH_TOKEN` returns 403** — publisher→`pdomain-index-npm`
   dispatch broken (org-rename SSO/scope). Needs CT to rotate/re-authorize the
   token. Workaround: run `pdomain-index-npm` `release.yml` (workflow_call chain
   bypasses the Pages env protection).
3. **`github-pages` environment protection** on `pdomain-index-npm` blocks
   non-`workflow_call` deploys (so manual `regen.yml` dispatch fails).

### Known release-preflight failure to resolve before cli releases

`pdomain-ocr-cli` `make ci-slow` fails one OCR test:
`tests/test_pipeline_integration.py::test_ocr_fixture_corpus_recovers_expected_tokens[rotated_page.png-expected_tokens2]`
— rotated fixture returns empty text (`'\n'`). Root cause NOT yet investigated
(CT deferred it). Prime suspect: the Stage-1 HF model relocation
(`CT2534/pd-ocr-models` → `pdomain/pdomain-ocr-models`, `pd-all-*` →
`pdomain-all-*`). Must be triaged before cli (and possibly prep) release via
page-split.

---

## Stage 7: Release Order (original — see DEFERRED status above)

Release after all commits are pushed and CI is green. Use each repo's existing release Make targets.

1. `pdomain-book-tools`
2. `pdomain-ui`
3. `pdomain-ops`
4. `pdomain-index-pip`
5. `pdomain-index-npm`
6. `pdomain-ocr-cli`
7. `pdomain-ocr-training`
8. `pdomain-ocr-synth`
9. `pdomain-ocr-labeler-spa`
10. `pdomain-ocr-trainer-spa`
11. `pdomain-ocr-simple-gui`
12. `pdomain-prep-for-pgdp`

For each repo:

- [ ] **Step 1: Push main.**
- [ ] **Step 2: Run the requested release target, usually `make release-minor`.**
- [ ] **Step 3: Watch release workflow to success.**
- [ ] **Step 4: Confirm index refresh when applicable.**
- [ ] **Step 5: Confirm downstream install/dependency resolution uses the new `pdomain-*` names.**

---

## Final Acceptance

- [ ] Active workspace search has no unclassified `pd-` / `pd_` hits.
- [ ] HF model defaults point at `pdomain/pdomain-ocr-models`.
- [ ] Python index event is `pdomain-release-published`.
- [ ] npm index event is `pdomain-npm-publish`.
- [ ] CLI commands are `pdomain-ocr`, `pdomain-ocr-labeler-ui`, and `pdomain-ocr-trainer-ui`.
- [ ] Local dev markers are `.pdomain-local-mode` and `.pdomain-dev-local`.
- [ ] Dataset/card metadata keys use `pdomain-ocr-*`.
- [ ] Every target repo has passed `make ci`.
- [ ] Every target repo has been committed, pushed, and released in dependency order.
