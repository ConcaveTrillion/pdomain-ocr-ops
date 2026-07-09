# pd→pdomain rename — Phase 0+1 prep — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the prerequisites for the workspace-wide `pd-*` → `pdomain-*` rename: claim the `pdomain` GitHub org, claim the `@pdomain` npm scope, reserve `pdomain-book-tools` on PyPI with a 0.0.1 placeholder, and build a tested rename harness (`scripts/rename/apply_rename.py`) driven by a single source-of-truth manifest. No production repo content is changed in this plan — that starts in Phase 2.

**Architecture:** Two strictly-independent tracks. Track A (identity claims) is short and mostly manual web-UI work plus a placeholder PyPI publish from a scratch project at `scripts/pypi-placeholder/pdomain-book-tools/`. Track B (rename harness) is a small Python tool at `scripts/rename/` with its own uv environment and pytest-based tests; the manifest at `scripts/rename/rename-manifest.json` is the canonical mapping for every later phase.

**Tech Stack:** Python 3.12 + uv for the harness; pytest for harness tests; `gh` CLI for identity-claim verification; `uv build` + `uv publish` for the PyPI placeholder.

**Spec:** [`docs/archive/specs/2026-05-26-pd-to-pdomain-rename-design.md`](../archive/specs/2026-05-26-pd-to-pdomain-rename-design.md), §3 Phase 0, §4 Phase 1.

---

## File Structure

Files created by this plan (all at workspace root `/workspaces/ocr-container/`):

```
scripts/
  pypi-placeholder/
    pdomain-book-tools/
      pyproject.toml          # PyPI placeholder metadata
      README.md               # one-paragraph project description + GH link
      src/
        pdomain_book_tools/
          __init__.py         # stub module so wheel builds
  rename/
    pyproject.toml            # uv env for harness + pytest
    rename-manifest.json      # canonical pd→pdomain mapping (all categories)
    apply_rename.py           # the harness
    tests/
      conftest.py             # pytest fixture: a temp fake-repo tree
      test_manifest.py        # load + schema validation
      test_string_replace.py  # content rewriting
      test_file_rename.py     # rename pd-suite.json → pdomain-suite.json
      test_dir_rename.py      # rename src/pd_x/ → src/pdomain_x/
      test_dry_run.py         # --dry-run produces no FS changes
      test_idempotent.py      # second run is a no-op
      test_exclude_paths.py   # archive/, .git/, node_modules/ untouched
      fixtures/
        sample_repo/          # a tiny tree with all the categories
```

**Responsibilities (one per file):**

- `rename-manifest.json` — the only source of truth for mappings. Categorized into `string_replacements`, `file_renames`, `dir_renames`, `exclude_paths`. Every later phase reads from this.
- `apply_rename.py` — a CLI that loads the manifest, walks one scoped tree, and applies the mappings; supports `--dry-run`, writes `changes.json` audit report. Pure file I/O; no git operations.
- One test file per behavior. Fixtures provide reproducible sample trees.
- Placeholder package — minimal but PyPI-compliant: real metadata, README linking to anticipated GH repo, stub Python module so the wheel builds.

---

## Pre-flight (one-time, ~3 min)

- [ ] **Confirm working tree is clean enough to start.**

Run: `git -C /workspaces/ocr-container status --short`

Expected: shows the spec commit just made (`docs/archive/specs/2026-05-26-pd-to-pdomain-rename-design.md`) and pre-existing M/?? entries unrelated to this work. No conflicting uncommitted edits in `scripts/` or `docs/plans/` (those paths are clean).

If there are conflicting uncommitted edits at `scripts/` or `docs/plans/`, stop and surface them to CT before continuing.

- [ ] **Confirm `gh` CLI is logged in as ConcaveTrillion.**

Run: `gh auth status`

Expected: `Logged in to github.com account ConcaveTrillion (...)`. If not, stop and ask CT to run `gh auth login`.

- [ ] **Confirm `uv` is available.**

Run: `uv --version`

Expected: a version string (any reasonably recent version is fine; the workspace is bootstrapped with mise so `uv` should be on PATH).

---

## Track A — Identity claims (manual + verification)

### Task 1: Claim `pdomain` GitHub organization

**Files:** none (manual web action + verification).

- [ ] **Step 1: Open the GH org-creation page in browser.**

URL: `https://github.com/account/organizations/new`

Plan: select the **Free** plan; name `pdomain`; billing email `concavetrillion@gmail.com`; type "Personal" account. Submit.

This is a manual web-UI step. Agent cannot perform it. Pause and ask CT to confirm "org claimed" before continuing.

- [ ] **Step 2: Verify the org exists.**

Run: `gh api orgs/pdomain --jq '.login + " | created=" + .created_at'`

Expected: `pdomain | created=<recent-ISO-timestamp>`. If 404, the claim didn't go through — return to Step 1.

- [ ] **Step 3: Confirm CT is owner.**

Run: `gh api orgs/pdomain/memberships/ConcaveTrillion --jq '.role + " | " + .state'`

Expected: `admin | active`.

- [ ] **Step 4: Commit a placeholder note (no actual file change yet).**

This task creates no files. Skip the commit step; record completion in the task list only.

---

### Task 2: Claim `@pdomain` npm organization

**Files:** none (manual web action + verification).

- [ ] **Step 1: Open the npm org-creation page in browser.**

URL: `https://www.npmjs.com/org/create`

Plan: org name `pdomain` (this creates the `@pdomain` scope); choose the **Free** plan ($0/month, public packages only — fine, the workspace has no private npm packages today). Submit.

Manual web step. Pause and ask CT to confirm.

- [ ] **Step 2: Verify the scope is taken under CT's npm account.**

Run: `curl -sI https://www.npmjs.com/~pdomain | head -1`

Expected: `HTTP/2 200`. If 404, the claim didn't go through.

- [ ] **Step 3: Verify scope is reachable for future publishes.**

Run: `curl -s -o /dev/null -w '%{http_code}\n' https://registry.npmjs.org/@pdomain%2ftest`

Expected: `404` (no package yet, but the scope resolves — registry returns 404 not 401/403 for "scope not found").

---

### Task 3: Create the `pdomain-book-tools` PyPI placeholder project tree

**Files:**
- Create: `scripts/pypi-placeholder/pdomain-book-tools/pyproject.toml`
- Create: `scripts/pypi-placeholder/pdomain-book-tools/README.md`
- Create: `scripts/pypi-placeholder/pdomain-book-tools/src/pdomain_book_tools/__init__.py`

- [ ] **Step 1: Create the directory structure.**

Run:
```bash
mkdir -p /workspaces/ocr-container/scripts/pypi-placeholder/pdomain-book-tools/src/pdomain_book_tools
```

Expected: no output. `ls /workspaces/ocr-container/scripts/pypi-placeholder/pdomain-book-tools/src/pdomain_book_tools/` succeeds and is empty.

- [ ] **Step 2: Write `pyproject.toml`.**

Path: `/workspaces/ocr-container/scripts/pypi-placeholder/pdomain-book-tools/pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pdomain-book-tools"
version = "0.0.1"
description = "Public-domain book-scan OCR + layout-analysis library — placeholder reservation; first real release lands soon"
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [{ name = "ConcaveTrillion", email = "concavetrillion@gmail.com" }]
classifiers = [
    "Development Status :: 1 - Planning",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Image Recognition",
    "Topic :: Text Processing",
]

[project.urls]
Homepage = "https://github.com/pdomain/pdomain-book-tools"
Repository = "https://github.com/pdomain/pdomain-book-tools"

[tool.hatch.build.targets.wheel]
packages = ["src/pdomain_book_tools"]
```

- [ ] **Step 3: Write `README.md`.**

Path: `/workspaces/ocr-container/scripts/pypi-placeholder/pdomain-book-tools/README.md`

```markdown
# pdomain-book-tools

Foundation Python library for public-domain book scans: OCR (Tesseract +
DocTR), layout analysis, image processing.

**This is a placeholder release** (0.0.1) reserving the PyPI name while the
project is being migrated from its previous identity. The first real
release will land at a forthcoming `0.1.x` version.

Project home: <https://github.com/pdomain/pdomain-book-tools>

Maintainer: ConcaveTrillion <concavetrillion@gmail.com>
```

- [ ] **Step 4: Write the stub module.**

Path: `/workspaces/ocr-container/scripts/pypi-placeholder/pdomain-book-tools/src/pdomain_book_tools/__init__.py`

```python
__version__ = "0.0.1"
```

- [ ] **Step 5: Commit the placeholder project tree.**

Run:
```bash
cd /workspaces/ocr-container && \
git add scripts/pypi-placeholder/pdomain-book-tools/ && \
git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com commit -m "$(cat <<'EOF'
chore: add pdomain-book-tools 0.0.1 PyPI placeholder source

Reservation-only stub for the pdomain-book-tools PyPI name. Real package
content lives elsewhere; this scratch tree only exists to build a
PEP-541-compliant placeholder wheel and document exactly what was
published.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

Expected: `1 file changed` or similar; commit lands on `main`.

---

### Task 4: Build the placeholder wheel

**Files:** generated (not committed): `scripts/pypi-placeholder/pdomain-book-tools/dist/`

- [ ] **Step 1: Build sdist + wheel with uv.**

Run:
```bash
cd /workspaces/ocr-container/scripts/pypi-placeholder/pdomain-book-tools && \
uv build
```

Expected: prints `Building source distribution...` and `Building wheel...` lines; `dist/pdomain_book_tools-0.0.1.tar.gz` and `dist/pdomain_book_tools-0.0.1-py3-none-any.whl` exist.

- [ ] **Step 2: Verify wheel metadata.**

Run:
```bash
cd /workspaces/ocr-container/scripts/pypi-placeholder/pdomain-book-tools && \
unzip -p dist/pdomain_book_tools-0.0.1-py3-none-any.whl '**/METADATA' | head -20
```

Expected: shows `Name: pdomain-book-tools`, `Version: 0.0.1`, `Author-email: ConcaveTrillion <concavetrillion@gmail.com>`, `Home-page` or `Project-URL: Homepage, https://github.com/pdomain/pdomain-book-tools`, classifier `Development Status :: 1 - Planning`.

- [ ] **Step 3: Add `dist/` to gitignore for this directory (don't commit built artifacts).**

Edit `/workspaces/ocr-container/.gitignore` — add this stanza at the end:

```
# Generated PyPI placeholder builds (commit source only, not dist)
scripts/pypi-placeholder/*/dist/
```

Run:
```bash
cd /workspaces/ocr-container && \
git add .gitignore && \
git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com commit -m "$(cat <<'EOF'
chore(gitignore): exclude PyPI placeholder dist artifacts

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

Expected: clean commit.

---

### Task 5: Set up PyPI account 2FA + API token

**Files:** none (manual; secret token NEVER lands in any file).

- [ ] **Step 1: If CT doesn't already have a PyPI account, create one.**

URL: `https://pypi.org/account/register/`

Username: `ConcaveTrillion` (or whatever CT prefers). Email: `concavetrillion@gmail.com`. Set a password kept only in CT's password manager.

If account already exists, log in instead.

- [ ] **Step 2: Enable 2FA on the PyPI account.**

URL: `https://pypi.org/manage/account/two-factor/`

Required since 2024 — without 2FA, publishing is blocked. Use either a TOTP app or a hardware key. Store recovery codes in CT's password manager.

- [ ] **Step 3: Create a scoped API token for the placeholder upload.**

URL: `https://pypi.org/manage/account/token/`

Token name: `pdomain-book-tools-placeholder-0.0.1`
Scope: **"Entire account (all projects)"** — required because this is the FIRST upload for `pdomain-book-tools`; PyPI doesn't yet know the project exists, so a project-scoped token can't be created. After this publish, this token gets deleted and any future re-publish uses a project-scoped token.

Copy the token (starts with `pypi-`). Paste once into a transient shell variable in the next task. Do NOT commit it anywhere.

- [ ] **Step 4: Pause and confirm with CT.**

Agent prompt to CT: "Token created? Reply 'ready' and the next task will publish."

---

### Task 6: Publish the placeholder wheel to PyPI

**Files:** none modified.

- [ ] **Step 1: Set the token into a transient shell variable.**

Run (in a shell the agent does NOT echo to logs):
```bash
read -s UV_PUBLISH_TOKEN
# CT pastes the pypi-... token here, hits enter
export UV_PUBLISH_TOKEN
```

Expected: variable set; not visible in scrollback.

- [ ] **Step 2: Publish.**

Run:
```bash
cd /workspaces/ocr-container/scripts/pypi-placeholder/pdomain-book-tools && \
uv publish dist/*
```

Expected: `Publishing... pdomain_book_tools-0.0.1-py3-none-any.whl` and `...-0.0.1.tar.gz`; `Uploaded` confirmation for each.

- [ ] **Step 3: Clear the token from the shell.**

Run: `unset UV_PUBLISH_TOKEN`

- [ ] **Step 4: Delete the token from PyPI (it's served its purpose).**

URL: `https://pypi.org/manage/account/token/`

Find the `pdomain-book-tools-placeholder-0.0.1` token, click "Remove token". A scoped per-project token can be created later when needed.

---

### Task 7: Verify the PyPI placeholder is live

**Files:** none modified.

- [ ] **Step 1: Query PyPI's JSON API.**

Run:
```bash
curl -s https://pypi.org/pypi/pdomain-book-tools/json | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['info']['version'], '|', d['info']['author'], '|', d['info']['classifiers'][:2])"
```

Expected: `0.0.1 | ConcaveTrillion | ['Development Status :: 1 - Planning', 'Intended Audience :: Developers']`.

- [ ] **Step 2: Install the placeholder into a throwaway env to confirm wheel is valid.**

Run:
```bash
cd /tmp && \
uv venv .pdomain-smoke-venv && \
source .pdomain-smoke-venv/bin/activate && \
uv pip install pdomain-book-tools && \
python -c "import pdomain_book_tools; print(pdomain_book_tools.__version__)" && \
deactivate && \
rm -rf .pdomain-smoke-venv
```

Expected: `0.0.1` printed; clean teardown.

- [ ] **Step 3: Mark Track A complete.**

No file changes. Record completion in the task list.

---

## Track B — Rename harness

### Task 8: Set up the harness Python project

**Files:**
- Create: `scripts/rename/pyproject.toml`
- Create: `scripts/rename/apply_rename.py` (empty placeholder)
- Create: `scripts/rename/tests/__init__.py` (empty)
- Create: `scripts/rename/tests/conftest.py`

- [ ] **Step 1: Make the directory tree.**

Run:
```bash
mkdir -p /workspaces/ocr-container/scripts/rename/tests
```

- [ ] **Step 2: Write `pyproject.toml`.**

Path: `/workspaces/ocr-container/scripts/rename/pyproject.toml`

```toml
[project]
name = "pd-rename-harness"
version = "0.0.1"
description = "Workspace-local harness for the pd-* → pdomain-* rename"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
dev = ["pytest>=8.0", "pytest-xdist>=3.5"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Create empty `apply_rename.py` and test scaffolding.**

Path: `/workspaces/ocr-container/scripts/rename/apply_rename.py`

```python
"""Workspace-local rename harness: pd-* → pdomain-*.

Reads `rename-manifest.json`, walks a scoped tree, applies mappings.
"""
```

Path: `/workspaces/ocr-container/scripts/rename/tests/__init__.py` — empty file.

Path: `/workspaces/ocr-container/scripts/rename/tests/conftest.py`

```python
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest


@pytest.fixture
def sample_tree(tmp_path: Path) -> Path:
    """A tiny fake-repo tree exercising every rename category."""
    root = tmp_path / "sample_repo"
    (root / "src" / "pd_book_tools").mkdir(parents=True)
    (root / "src" / "pd_book_tools" / "__init__.py").write_text(
        "from pd_book_tools.core import thing\n"
        "__version__ = '0.10.0'\n"
    )
    (root / "src" / "pd_book_tools" / "core.py").write_text(
        "# pdomain-book-tools core module\n"
        "thing = 1\n"
    )
    (root / "pyproject.toml").write_text(
        '[project]\nname = "pdomain-book-tools"\n'
        'dependencies = ["pdomain-ocr-ops>=0.1"]\n'
    )
    (root / "pd-suite.json").write_text('{"mode": "PD_SUITE_MODE"}\n')
    (root / "README.md").write_text("# pdomain-book-tools\n\nSee pdomain-ocr-cli too.\n")
    (root / "archive").mkdir()
    (root / "archive" / "old.md").write_text("# pdomain-book-tools (frozen)\n")
    return root


@pytest.fixture
def minimal_manifest(tmp_path: Path) -> Path:
    """A minimal manifest covering one entry of each category."""
    manifest = {
        "version": 1,
        "string_replacements": [
            {"old": "pd_book_tools", "new": "pdomain_book_tools"},
            {"old": "pdomain-book-tools", "new": "pdomain-book-tools"},
            {"old": "pdomain-ocr-ops", "new": "pdomain-ocr-ops"},
            {"old": "pdomain-ocr-cli", "new": "pdomain-ocr-cli"},
            {"old": "PD_SUITE_MODE", "new": "PDOMAIN_SUITE_MODE"},
        ],
        "file_renames": [
            {"old": "pd-suite.json", "new": "pdomain-suite.json"},
        ],
        "dir_renames": [
            {"old": "src/pd_book_tools", "new": "src/pdomain_book_tools"},
        ],
        "exclude_paths": [
            "archive/**",
            ".git/**",
            "**/__pycache__/**",
            "**/.venv/**",
            "**/node_modules/**",
        ],
    }
    path = tmp_path / "rename-manifest.json"
    path.write_text(json.dumps(manifest, indent=2))
    return path
```

- [ ] **Step 4: Sync uv environment.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv sync --group dev
```

Expected: creates `.venv/` and installs pytest. No errors.

- [ ] **Step 5: Add `scripts/rename/.venv/` and `scripts/rename/__pycache__/` to gitignore.**

Edit `/workspaces/ocr-container/.gitignore` — append:

```
# Rename harness local env
scripts/rename/.venv/
scripts/rename/**/__pycache__/
```

- [ ] **Step 6: Commit scaffolding.**

Run:
```bash
cd /workspaces/ocr-container && \
git add scripts/rename/pyproject.toml scripts/rename/apply_rename.py scripts/rename/tests/__init__.py scripts/rename/tests/conftest.py .gitignore && \
git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com commit -m "$(cat <<'EOF'
chore(rename): scaffold pd→pdomain rename harness

Empty harness + uv project + pytest conftest with fake-repo fixture.
Logic + manifest land in the next tasks.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Write the canonical rename-manifest.json

**Files:**
- Create: `scripts/rename/rename-manifest.json`

This is the single source of truth for every later phase. Entries derived directly from the spec's §4 inventory and Appendix.

- [ ] **Step 1: Write the manifest.**

Path: `/workspaces/ocr-container/scripts/rename/rename-manifest.json`

```json
{
  "version": 1,
  "description": "Canonical pd-* → pdomain-* mappings. Source of truth for apply_rename.py. See docs/archive/specs/2026-05-26-pd-to-pdomain-rename-design.md.",
  "string_replacements": [
    {"old": "pd_book_tools", "new": "pdomain_book_tools"},
    {"old": "pd_ocr_cli", "new": "pdomain_ocr_cli"},
    {"old": "pd_ocr_labeler_spa", "new": "pdomain_ocr_labeler_spa"},
    {"old": "pd_ocr_labeler", "new": "pdomain_ocr_labeler"},
    {"old": "pd_ocr_synth", "new": "pdomain_ocr_synth"},
    {"old": "pd_ocr_trainer_spa", "new": "pdomain_ocr_trainer_spa"},
    {"old": "pd_ocr_trainer", "new": "pdomain_ocr_trainer"},
    {"old": "pd_ocr_training", "new": "pdomain_ocr_training"},
    {"old": "pd_ocr_ops", "new": "pdomain_ocr_ops"},
    {"old": "pd_ocr_simple_gui", "new": "pdomain_ocr_simple_gui"},
    {"old": "pd_png_optimizer", "new": "pdomain_png_optimizer"},
    {"old": "pd_prep_for_pgdp", "new": "pdomain_prep_for_pgdp"},
    {"old": "pd_ui", "new": "pdomain_ui"},
    {"old": "pdomain-book-tools", "new": "pdomain-book-tools"},
    {"old": "pdomain-ocr-cli", "new": "pdomain-ocr-cli"},
    {"old": "pdomain-ocr-labeler-spa", "new": "pdomain-ocr-labeler-spa"},
    {"old": "pd-ocr-labeler", "new": "pdomain-ocr-labeler"},
    {"old": "pdomain-ocr-synth", "new": "pdomain-ocr-synth"},
    {"old": "pdomain-ocr-trainer-spa", "new": "pdomain-ocr-trainer-spa"},
    {"old": "pd-ocr-trainer", "new": "pdomain-ocr-trainer"},
    {"old": "pdomain-ocr-training", "new": "pdomain-ocr-training"},
    {"old": "pdomain-ocr-ops", "new": "pdomain-ocr-ops"},
    {"old": "pdomain-ocr-simple-gui", "new": "pdomain-ocr-simple-gui"},
    {"old": "pd-png-optimizer", "new": "pdomain-png-optimizer"},
    {"old": "pdomain-prep-for-pgdp", "new": "pdomain-prep-for-pgdp"},
    {"old": "pdomain-ui", "new": "pdomain-ui"},
    {"old": "pdomain-index-pip", "new": "pdomain-index-pip"},
    {"old": "pdomain-index-npm", "new": "pdomain-index-npm"},
    {"old": "@concavetrillion/pdomain-ui", "new": "@pdomain/pdomain-ui"},
    {"old": "@concavetrillion/", "new": "@pdomain/"},
    {"old": "pd-suite", "new": "pdomain-suite"},
    {"old": "PD_SUITE_MODE", "new": "PDOMAIN_SUITE_MODE"},
    {"old": "PD_GPU_BACKEND", "new": "PDOMAIN_GPU_BACKEND"},
    {"old": "PD_INDEX_DISPATCH_TOKEN", "new": "PDOMAIN_INDEX_DISPATCH_TOKEN"},
    {"old": "ship-slice-pd-", "new": "ship-slice-pdomain-"},
    {"old": "concavetrillion.github.io", "new": "pdomain.github.io"},
    {"old": "ConcaveTrillion/pd-", "new": "pdomain/pdomain-"}
  ],
  "file_renames": [
    {"old": "pd-suite.json", "new": "pdomain-suite.json"}
  ],
  "dir_renames": [
    {"old": "src/pd_book_tools", "new": "src/pdomain_book_tools"},
    {"old": "src/pd_ocr_cli", "new": "src/pdomain_ocr_cli"},
    {"old": "src/pd_ocr_labeler_spa", "new": "src/pdomain_ocr_labeler_spa"},
    {"old": "src/pd_ocr_labeler", "new": "src/pdomain_ocr_labeler"},
    {"old": "src/pd_ocr_synth", "new": "src/pdomain_ocr_synth"},
    {"old": "src/pd_ocr_trainer_spa", "new": "src/pdomain_ocr_trainer_spa"},
    {"old": "src/pd_ocr_trainer", "new": "src/pdomain_ocr_trainer"},
    {"old": "src/pd_ocr_training", "new": "src/pdomain_ocr_training"},
    {"old": "src/pd_ocr_ops", "new": "src/pdomain_ocr_ops"},
    {"old": "src/pd_ocr_simple_gui", "new": "src/pdomain_ocr_simple_gui"},
    {"old": "src/pd_png_optimizer", "new": "src/pdomain_png_optimizer"},
    {"old": "src/pd_prep_for_pgdp", "new": "src/pdomain_prep_for_pgdp"},
    {"old": "src/pd_ui", "new": "src/pdomain_ui"},
    {"old": "python/pd_book_tools", "new": "python/pdomain_book_tools"},
    {"old": "python/pd_png_optimizer", "new": "python/pdomain_png_optimizer"},
    {"old": "crates/pd_png_optimizer", "new": "crates/pdomain_png_optimizer"}
  ],
  "exclude_paths": [
    ".git/**",
    ".venv/**",
    "**/.venv/**",
    "**/node_modules/**",
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/dist/**",
    "**/build/**",
    "**/htmlcov/**",
    "**/.coverage*",
    "**/*.lock",
    "docs/archive/**",
    "**/archive/**",
    "**/.ci-ai.log"
  ]
}
```

**Note on ordering:** within `string_replacements`, longer prefixes appear before shorter ones (e.g. `pd_ocr_labeler_spa` before `pd_ocr_labeler`) so substring overlap doesn't collapse longer names into the shorter rename. The harness applies replacements in list order; this ordering matters.

**Note on `@concavetrillion/` general entry:** it appears AFTER the specific `@concavetrillion/pdomain-ui` entry. If the specific case is already rewritten to `@pdomain/pdomain-ui` by the time the general entry runs, the general entry produces no false rewrites because the string `@concavetrillion/` no longer appears.

- [ ] **Step 2: Commit.**

Run:
```bash
cd /workspaces/ocr-container && \
git add scripts/rename/rename-manifest.json && \
git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com commit -m "$(cat <<'EOF'
feat(rename): canonical rename-manifest.json (single source of truth)

All pd-* → pdomain-* mappings for the workspace rename, ordered so
longer prefixes resolve before shorter ones to avoid substring overlap.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Test — manifest loads and validates

**Files:**
- Create: `scripts/rename/tests/test_manifest.py`

- [ ] **Step 1: Write the failing test.**

Path: `/workspaces/ocr-container/scripts/rename/tests/test_manifest.py`

```python
from __future__ import annotations

from pathlib import Path

import pytest

import apply_rename


def test_load_manifest_returns_dict_with_required_keys(minimal_manifest: Path) -> None:
    manifest = apply_rename.load_manifest(minimal_manifest)
    assert manifest["version"] == 1
    assert isinstance(manifest["string_replacements"], list)
    assert isinstance(manifest["file_renames"], list)
    assert isinstance(manifest["dir_renames"], list)
    assert isinstance(manifest["exclude_paths"], list)


def test_load_manifest_raises_on_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        apply_rename.load_manifest(tmp_path / "does-not-exist.json")


def test_load_manifest_raises_on_wrong_version(tmp_path: Path) -> None:
    bad = tmp_path / "manifest.json"
    bad.write_text('{"version": 99, "string_replacements": [], "file_renames": [], "dir_renames": [], "exclude_paths": []}')
    with pytest.raises(ValueError, match="version"):
        apply_rename.load_manifest(bad)
```

- [ ] **Step 2: Run test, verify it fails.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run pytest tests/test_manifest.py -v
```

Expected: 3 errors with `AttributeError: module 'apply_rename' has no attribute 'load_manifest'` (or similar).

- [ ] **Step 3: Implement `load_manifest`.**

Edit `/workspaces/ocr-container/scripts/rename/apply_rename.py` — replace its content with:

```python
"""Workspace-local rename harness: pd-* → pdomain-*.

Reads `rename-manifest.json`, walks a scoped tree, applies mappings.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SUPPORTED_VERSION = 1


def load_manifest(path: Path) -> dict[str, Any]:
    """Load and validate the rename manifest."""
    data = json.loads(Path(path).read_text())
    if data.get("version") != SUPPORTED_VERSION:
        raise ValueError(
            f"unsupported manifest version: got {data.get('version')!r}, "
            f"expected {SUPPORTED_VERSION}"
        )
    for key in ("string_replacements", "file_renames", "dir_renames", "exclude_paths"):
        if key not in data:
            raise ValueError(f"manifest missing required key: {key!r}")
    return data
```

- [ ] **Step 4: Run test, verify it passes.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run pytest tests/test_manifest.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit.**

Run:
```bash
cd /workspaces/ocr-container && \
git add scripts/rename/apply_rename.py scripts/rename/tests/test_manifest.py && \
git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com commit -m "$(cat <<'EOF'
feat(rename): load_manifest with version + key validation

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: Test — exclude-path matching

**Files:**
- Create: `scripts/rename/tests/test_exclude_paths.py`

- [ ] **Step 1: Write the failing test.**

Path: `/workspaces/ocr-container/scripts/rename/tests/test_exclude_paths.py`

```python
from __future__ import annotations

from pathlib import Path

import apply_rename


def test_is_excluded_matches_glob() -> None:
    patterns = ["archive/**", ".git/**", "**/__pycache__/**"]
    assert apply_rename.is_excluded(Path("archive/old.md"), patterns) is True
    assert apply_rename.is_excluded(Path("archive/sub/old.md"), patterns) is True
    assert apply_rename.is_excluded(Path(".git/HEAD"), patterns) is True
    assert apply_rename.is_excluded(Path("src/pkg/__pycache__/foo.pyc"), patterns) is True


def test_is_excluded_misses_non_matches() -> None:
    patterns = ["archive/**"]
    assert apply_rename.is_excluded(Path("src/pkg/code.py"), patterns) is False
    assert apply_rename.is_excluded(Path("README.md"), patterns) is False


def test_is_excluded_empty_patterns_means_none_excluded() -> None:
    assert apply_rename.is_excluded(Path("anything"), []) is False
```

- [ ] **Step 2: Run test, verify it fails.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run pytest tests/test_exclude_paths.py -v
```

Expected: 3 errors with `AttributeError: ... no attribute 'is_excluded'`.

- [ ] **Step 3: Implement `is_excluded`.**

Append to `/workspaces/ocr-container/scripts/rename/apply_rename.py`:

```python
import fnmatch


def is_excluded(relative_path: Path, exclude_patterns: list[str]) -> bool:
    """True if `relative_path` matches any glob in `exclude_patterns`.

    Patterns follow fnmatch semantics with `**` meaning "any number of path
    segments." `archive/**` matches `archive/old.md` and `archive/sub/old.md`.
    """
    posix = relative_path.as_posix()
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(posix, pattern):
            return True
        # `archive/**` should also match the parent itself ("archive/old.md")
        # — fnmatch handles `**` as any-chars-including-slash, which works for
        # `**/foo` and `foo/**` cases via the wildcard.
    return False
```

- [ ] **Step 4: Run test, verify it passes.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run pytest tests/test_exclude_paths.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit.**

Run:
```bash
cd /workspaces/ocr-container && \
git add scripts/rename/apply_rename.py scripts/rename/tests/test_exclude_paths.py && \
git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com commit -m "$(cat <<'EOF'
feat(rename): is_excluded glob matcher with fnmatch

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: Test — string replacement in file contents

**Files:**
- Create: `scripts/rename/tests/test_string_replace.py`

- [ ] **Step 1: Write the failing test.**

Path: `/workspaces/ocr-container/scripts/rename/tests/test_string_replace.py`

```python
from __future__ import annotations

from pathlib import Path

import apply_rename


def test_rewrite_content_applies_all_replacements_in_order(sample_tree: Path, minimal_manifest: Path) -> None:
    manifest = apply_rename.load_manifest(minimal_manifest)
    target = sample_tree / "pyproject.toml"
    original = target.read_text()
    assert "pdomain-book-tools" in original
    assert "pdomain-ocr-ops" in original

    changed = apply_rename.rewrite_content(original, manifest["string_replacements"])

    assert "pdomain-book-tools" not in changed
    assert "pdomain-ocr-ops" not in changed
    assert "pdomain-book-tools" in changed
    assert "pdomain-ocr-ops" in changed


def test_rewrite_content_handles_env_var_form(sample_tree: Path, minimal_manifest: Path) -> None:
    manifest = apply_rename.load_manifest(minimal_manifest)
    target = sample_tree / "pd-suite.json"
    changed = apply_rename.rewrite_content(target.read_text(), manifest["string_replacements"])
    assert "PD_SUITE_MODE" not in changed
    assert "PDOMAIN_SUITE_MODE" in changed


def test_rewrite_content_returns_input_unchanged_when_no_matches() -> None:
    text = "nothing to rename here\n"
    replacements = [{"old": "pdomain-book-tools", "new": "pdomain-book-tools"}]
    assert apply_rename.rewrite_content(text, replacements) == text
```

- [ ] **Step 2: Run test, verify it fails.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run pytest tests/test_string_replace.py -v
```

Expected: 3 errors with `AttributeError: ... no attribute 'rewrite_content'`.

- [ ] **Step 3: Implement `rewrite_content`.**

Append to `/workspaces/ocr-container/scripts/rename/apply_rename.py`:

```python
def rewrite_content(text: str, replacements: list[dict[str, str]]) -> str:
    """Apply each {old, new} string replacement in order.

    Replacements are pure substring substitutions. Order matters: longer
    prefixes must appear before shorter ones in the manifest to avoid
    overlap collisions.
    """
    for entry in replacements:
        text = text.replace(entry["old"], entry["new"])
    return text
```

- [ ] **Step 4: Run test, verify it passes.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run pytest tests/test_string_replace.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit.**

Run:
```bash
cd /workspaces/ocr-container && \
git add scripts/rename/apply_rename.py scripts/rename/tests/test_string_replace.py && \
git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com commit -m "$(cat <<'EOF'
feat(rename): rewrite_content applies string replacements in order

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 13: Test — file rename (e.g. pd-suite.json → pdomain-suite.json)

**Files:**
- Create: `scripts/rename/tests/test_file_rename.py`

- [ ] **Step 1: Write the failing test.**

Path: `/workspaces/ocr-container/scripts/rename/tests/test_file_rename.py`

```python
from __future__ import annotations

from pathlib import Path

import apply_rename


def test_apply_file_renames_moves_matching_basenames(sample_tree: Path, minimal_manifest: Path) -> None:
    manifest = apply_rename.load_manifest(minimal_manifest)
    assert (sample_tree / "pd-suite.json").exists()
    assert not (sample_tree / "pdomain-suite.json").exists()

    moves = apply_rename.apply_file_renames(
        sample_tree, manifest["file_renames"], manifest["exclude_paths"]
    )

    assert not (sample_tree / "pd-suite.json").exists()
    assert (sample_tree / "pdomain-suite.json").exists()
    assert {"old": "pd-suite.json", "new": "pdomain-suite.json"} in moves


def test_apply_file_renames_skips_excluded_paths(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    (root / "archive").mkdir(parents=True)
    (root / "archive" / "pd-suite.json").write_text("{}")
    (root / "pd-suite.json").write_text("{}")

    file_renames = [{"old": "pd-suite.json", "new": "pdomain-suite.json"}]
    excludes = ["archive/**"]

    apply_rename.apply_file_renames(root, file_renames, excludes)

    assert (root / "archive" / "pd-suite.json").exists()  # excluded, untouched
    assert not (root / "pd-suite.json").exists()
    assert (root / "pdomain-suite.json").exists()


def test_apply_file_renames_no_op_when_no_matches(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    (root / "other.json").write_text("{}")

    moves = apply_rename.apply_file_renames(
        root, [{"old": "pd-suite.json", "new": "pdomain-suite.json"}], []
    )

    assert moves == []
    assert (root / "other.json").exists()
```

- [ ] **Step 2: Run test, verify it fails.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run pytest tests/test_file_rename.py -v
```

Expected: 3 errors with `AttributeError: ... no attribute 'apply_file_renames'`.

- [ ] **Step 3: Implement `apply_file_renames`.**

Append to `/workspaces/ocr-container/scripts/rename/apply_rename.py`:

```python
def apply_file_renames(
    root: Path,
    file_renames: list[dict[str, str]],
    exclude_patterns: list[str],
) -> list[dict[str, str]]:
    """Rename files in `root` whose basename matches a `file_renames` entry.

    Returns the list of moves actually performed (the {old, new} entry from
    the manifest), one per file moved. Skips files under any excluded path.
    """
    by_basename = {entry["old"]: entry["new"] for entry in file_renames}
    moves: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if is_excluded(rel, exclude_patterns):
            continue
        if path.name in by_basename:
            new_path = path.with_name(by_basename[path.name])
            path.rename(new_path)
            moves.append({"old": path.name, "new": new_path.name})
    return moves
```

- [ ] **Step 4: Run test, verify it passes.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run pytest tests/test_file_rename.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit.**

Run:
```bash
cd /workspaces/ocr-container && \
git add scripts/rename/apply_rename.py scripts/rename/tests/test_file_rename.py && \
git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com commit -m "$(cat <<'EOF'
feat(rename): apply_file_renames moves matching basenames

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 14: Test — directory rename (e.g. src/pd_book_tools/ → src/pdomain_book_tools/)

**Files:**
- Create: `scripts/rename/tests/test_dir_rename.py`

- [ ] **Step 1: Write the failing test.**

Path: `/workspaces/ocr-container/scripts/rename/tests/test_dir_rename.py`

```python
from __future__ import annotations

from pathlib import Path

import apply_rename


def test_apply_dir_renames_moves_matching_directories(sample_tree: Path, minimal_manifest: Path) -> None:
    manifest = apply_rename.load_manifest(minimal_manifest)
    assert (sample_tree / "src" / "pd_book_tools").is_dir()
    assert not (sample_tree / "src" / "pdomain_book_tools").exists()

    moves = apply_rename.apply_dir_renames(sample_tree, manifest["dir_renames"])

    assert not (sample_tree / "src" / "pd_book_tools").exists()
    assert (sample_tree / "src" / "pdomain_book_tools" / "__init__.py").exists()
    assert (sample_tree / "src" / "pdomain_book_tools" / "core.py").exists()
    assert {"old": "src/pd_book_tools", "new": "src/pdomain_book_tools"} in moves


def test_apply_dir_renames_no_op_when_target_absent(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    (root / "src" / "other_pkg").mkdir(parents=True)

    moves = apply_rename.apply_dir_renames(
        root, [{"old": "src/pd_book_tools", "new": "src/pdomain_book_tools"}]
    )

    assert moves == []
    assert (root / "src" / "other_pkg").exists()
```

- [ ] **Step 2: Run test, verify it fails.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run pytest tests/test_dir_rename.py -v
```

Expected: 2 errors with `AttributeError: ... no attribute 'apply_dir_renames'`.

- [ ] **Step 3: Implement `apply_dir_renames`.**

Append to `/workspaces/ocr-container/scripts/rename/apply_rename.py`:

```python
def apply_dir_renames(
    root: Path,
    dir_renames: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Rename directories under `root` matching `dir_renames` entries.

    Each entry's `old`/`new` is a path relative to `root`. Only entries
    whose `old` directory exists are acted on; others are silently skipped.
    Returns the list of moves performed.
    """
    moves: list[dict[str, str]] = []
    for entry in dir_renames:
        old_dir = root / entry["old"]
        new_dir = root / entry["new"]
        if old_dir.is_dir():
            new_dir.parent.mkdir(parents=True, exist_ok=True)
            old_dir.rename(new_dir)
            moves.append(entry)
    return moves
```

- [ ] **Step 4: Run test, verify it passes.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run pytest tests/test_dir_rename.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit.**

Run:
```bash
cd /workspaces/ocr-container && \
git add scripts/rename/apply_rename.py scripts/rename/tests/test_dir_rename.py && \
git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com commit -m "$(cat <<'EOF'
feat(rename): apply_dir_renames moves matching directories

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 15: Test — full-tree rewrite (content + files + dirs in one pass)

**Files:**
- Create: `scripts/rename/tests/test_rewrite_tree.py`

- [ ] **Step 1: Write the failing test.**

Path: `/workspaces/ocr-container/scripts/rename/tests/test_rewrite_tree.py`

```python
from __future__ import annotations

import json
from pathlib import Path

import apply_rename


def test_rewrite_tree_rewrites_contents_and_renames_files_and_dirs(sample_tree: Path, minimal_manifest: Path) -> None:
    report = apply_rename.rewrite_tree(sample_tree, minimal_manifest, dry_run=False)

    # Dir renamed
    assert (sample_tree / "src" / "pdomain_book_tools" / "__init__.py").exists()
    # File renamed
    assert (sample_tree / "pdomain-suite.json").exists()
    assert not (sample_tree / "pd-suite.json").exists()
    # Content rewritten in the renamed file
    assert "PDOMAIN_SUITE_MODE" in (sample_tree / "pdomain-suite.json").read_text()
    # Content rewritten in pyproject.toml
    py = (sample_tree / "pyproject.toml").read_text()
    assert "pdomain-book-tools" in py
    assert "pdomain-book-tools" not in py
    # Content rewritten in moved module
    init = (sample_tree / "src" / "pdomain_book_tools" / "__init__.py").read_text()
    assert "from pdomain_book_tools.core" in init
    # Archive untouched
    assert (sample_tree / "archive" / "old.md").read_text() == "# pdomain-book-tools (frozen)\n"

    # Report shape
    assert report["files_rewritten"] >= 3  # pyproject, init, core, pdomain-suite.json, README
    assert {"old": "src/pd_book_tools", "new": "src/pdomain_book_tools"} in report["dir_renames"]
    assert {"old": "pd-suite.json", "new": "pdomain-suite.json"} in report["file_renames"]


def test_rewrite_tree_dry_run_leaves_tree_untouched(sample_tree: Path, minimal_manifest: Path) -> None:
    before_snapshot = sorted(p.relative_to(sample_tree).as_posix() for p in sample_tree.rglob("*"))
    before_content = (sample_tree / "pyproject.toml").read_text()

    report = apply_rename.rewrite_tree(sample_tree, minimal_manifest, dry_run=True)

    after_snapshot = sorted(p.relative_to(sample_tree).as_posix() for p in sample_tree.rglob("*"))
    assert before_snapshot == after_snapshot
    assert (sample_tree / "pyproject.toml").read_text() == before_content
    # But the report still shows what would change
    assert report["files_rewritten"] >= 3
```

- [ ] **Step 2: Run test, verify it fails.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run pytest tests/test_rewrite_tree.py -v
```

Expected: 2 errors with `AttributeError: ... no attribute 'rewrite_tree'`.

- [ ] **Step 3: Implement `rewrite_tree`.**

Append to `/workspaces/ocr-container/scripts/rename/apply_rename.py`:

```python
def rewrite_tree(
    root: Path,
    manifest_path: Path,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    """Apply the full rename to a tree.

    Order matters:
        1. Rewrite file CONTENTS first (while paths still match `pd_*` names).
        2. Rename files (basename swaps).
        3. Rename directories (path swaps).

    Doing it in the opposite order would either miss content rewrites (if the
    file moved before its content was visited) or apply content rewrites to
    paths that haven't been computed yet.
    """
    manifest = load_manifest(manifest_path)
    excludes = manifest["exclude_paths"]
    replacements = manifest["string_replacements"]
    report: dict[str, Any] = {
        "files_rewritten": 0,
        "file_renames": [],
        "dir_renames": [],
        "dry_run": dry_run,
    }

    # 1. Rewrite contents.
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if is_excluded(rel, excludes):
            continue
        try:
            original = path.read_text()
        except UnicodeDecodeError:
            continue  # skip binaries
        new_content = rewrite_content(original, replacements)
        if new_content != original:
            report["files_rewritten"] += 1
            if not dry_run:
                path.write_text(new_content)

    # 2. File renames.
    if dry_run:
        # Predict file renames without performing them.
        by_basename = {e["old"]: e["new"] for e in manifest["file_renames"]}
        for path in sorted(root.rglob("*")):
            if path.is_file() and not is_excluded(path.relative_to(root), excludes):
                if path.name in by_basename:
                    report["file_renames"].append({"old": path.name, "new": by_basename[path.name]})
    else:
        report["file_renames"] = apply_file_renames(root, manifest["file_renames"], excludes)

    # 3. Dir renames.
    if dry_run:
        for entry in manifest["dir_renames"]:
            if (root / entry["old"]).is_dir():
                report["dir_renames"].append(entry)
    else:
        report["dir_renames"] = apply_dir_renames(root, manifest["dir_renames"])

    return report
```

- [ ] **Step 4: Run test, verify it passes.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run pytest tests/test_rewrite_tree.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit.**

Run:
```bash
cd /workspaces/ocr-container && \
git add scripts/rename/apply_rename.py scripts/rename/tests/test_rewrite_tree.py && \
git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com commit -m "$(cat <<'EOF'
feat(rename): rewrite_tree orchestrates content + file + dir renames

Order: rewrite contents first (paths still match pd_*), then file basenames,
then directories. Dry-run predicts without performing.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 16: Test — idempotency (second run is a no-op)

**Files:**
- Create: `scripts/rename/tests/test_idempotent.py`

- [ ] **Step 1: Write the failing test.**

Path: `/workspaces/ocr-container/scripts/rename/tests/test_idempotent.py`

```python
from __future__ import annotations

from pathlib import Path

import apply_rename


def test_second_run_is_no_op(sample_tree: Path, minimal_manifest: Path) -> None:
    first = apply_rename.rewrite_tree(sample_tree, minimal_manifest, dry_run=False)
    assert first["files_rewritten"] >= 1
    assert first["file_renames"] != [] or first["dir_renames"] != []

    second = apply_rename.rewrite_tree(sample_tree, minimal_manifest, dry_run=False)
    assert second["files_rewritten"] == 0
    assert second["file_renames"] == []
    assert second["dir_renames"] == []
```

- [ ] **Step 2: Run test, verify it passes already.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run pytest tests/test_idempotent.py -v
```

Expected: 1 passed — idempotency falls out of correct implementation; if it fails it surfaces a bug in `rewrite_tree`'s ordering or in the manifest's overlap-handling. If it does fail, debug `rewrite_tree` before continuing.

- [ ] **Step 3: Commit (the test is the deliverable here).**

Run:
```bash
cd /workspaces/ocr-container && \
git add scripts/rename/tests/test_idempotent.py && \
git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com commit -m "$(cat <<'EOF'
test(rename): assert rewrite_tree is idempotent (second run is no-op)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 17: CLI wiring (`--scope`, `--dry-run`, writes `changes.json`)

**Files:**
- Create: `scripts/rename/tests/test_cli.py`

- [ ] **Step 1: Write the failing test.**

Path: `/workspaces/ocr-container/scripts/rename/tests/test_cli.py`

```python
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import apply_rename


def test_main_dry_run_writes_changes_json(sample_tree: Path, minimal_manifest: Path, tmp_path: Path) -> None:
    out = tmp_path / "changes.json"
    exit_code = apply_rename.main([
        "--scope", str(sample_tree),
        "--manifest", str(minimal_manifest),
        "--dry-run",
        "--report", str(out),
    ])
    assert exit_code == 0
    assert out.exists()
    report = json.loads(out.read_text())
    assert report["dry_run"] is True
    assert report["files_rewritten"] >= 1
    # Tree untouched
    assert (sample_tree / "pd-suite.json").exists()
    assert not (sample_tree / "pdomain-suite.json").exists()


def test_main_apply_modifies_tree_and_reports(sample_tree: Path, minimal_manifest: Path, tmp_path: Path) -> None:
    out = tmp_path / "changes.json"
    exit_code = apply_rename.main([
        "--scope", str(sample_tree),
        "--manifest", str(minimal_manifest),
        "--report", str(out),
    ])
    assert exit_code == 0
    report = json.loads(out.read_text())
    assert report["dry_run"] is False
    assert (sample_tree / "pdomain-suite.json").exists()
    assert not (sample_tree / "pd-suite.json").exists()
```

- [ ] **Step 2: Run test, verify it fails.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run pytest tests/test_cli.py -v
```

Expected: 2 errors with `AttributeError: ... no attribute 'main'`.

- [ ] **Step 3: Implement `main`.**

Append to `/workspaces/ocr-container/scripts/rename/apply_rename.py`:

```python
import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="apply_rename",
        description="Apply pd-* → pdomain-* rename to a scoped tree.",
    )
    parser.add_argument(
        "--scope",
        required=True,
        type=Path,
        help="Path to the tree to rename (a single repo's working directory).",
    )
    parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="Path to rename-manifest.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Predict changes without writing them.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("changes.json"),
        help="Where to write the JSON audit report (default: ./changes.json).",
    )
    args = parser.parse_args(argv)
    report = rewrite_tree(args.scope, args.manifest, dry_run=args.dry_run)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test, verify it passes.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run pytest tests/test_cli.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Run the full test suite to confirm nothing regressed.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run pytest -v
```

Expected: all tests passed (likely 15-17 total across the test files).

- [ ] **Step 6: Commit.**

Run:
```bash
cd /workspaces/ocr-container && \
git add scripts/rename/apply_rename.py scripts/rename/tests/test_cli.py && \
git -c user.name=ConcaveTrillion -c user.email=concavetrillion@gmail.com commit -m "$(cat <<'EOF'
feat(rename): CLI entrypoint with --scope, --dry-run, --report

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 18: Smoke-test against a real pd-* worktree

This is the Phase 1 acceptance gate from the spec. Verifies the harness behaves correctly against an actual repo, not just synthetic fixtures.

**Files:** none modified in workspace tree; a throwaway worktree is created and discarded.

- [ ] **Step 1: Create a throwaway worktree off pd-png-optimizer's main.**

`pd-png-optimizer` is chosen because it's the smallest pd-* repo (Rust core + thin Python facade), so the harness output is easy to eyeball.

Run:
```bash
cd /workspaces/ocr-container/pd-png-optimizer && \
git worktree add .claude/worktrees/rename-smoke main
```

Expected: creates `pd-png-optimizer/.claude/worktrees/rename-smoke/` checked out at `main`.

- [ ] **Step 2: Run the harness in dry-run against the worktree.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run python apply_rename.py \
  --scope /workspaces/ocr-container/pd-png-optimizer/.claude/worktrees/rename-smoke \
  --manifest /workspaces/ocr-container/scripts/rename/rename-manifest.json \
  --dry-run \
  --report /tmp/rename-smoke-dry.json && \
python3 -c "import json; r=json.load(open('/tmp/rename-smoke-dry.json')); print('dry_run:', r['dry_run']); print('files_rewritten:', r['files_rewritten']); print('file_renames:', len(r['file_renames'])); print('dir_renames:', r['dir_renames'])"
```

Expected:
- `dry_run: True`
- `files_rewritten: N` where N > 0 and < ~100 (sanity range — pd-png-optimizer has on order of dozens of `pd-*` references)
- `dir_renames` includes at least `{"old": "src/pd_png_optimizer", "new": "src/pdomain_png_optimizer"}` (since the repo has a Python facade module at that path).
- The worktree's `git -C ... status --short` is empty (dry-run touched nothing).

If `files_rewritten` is zero, something is wrong (likely the manifest excludes the worktree path). Pause and investigate.

- [ ] **Step 3: Run the harness for real against the worktree.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run python apply_rename.py \
  --scope /workspaces/ocr-container/pd-png-optimizer/.claude/worktrees/rename-smoke \
  --manifest /workspaces/ocr-container/scripts/rename/rename-manifest.json \
  --report /tmp/rename-smoke-real.json && \
diff /tmp/rename-smoke-dry.json /tmp/rename-smoke-real.json | head -5
```

Expected: the diff between dry and real reports differs only in the `dry_run` field — same counts, same lists. (The diff command will show `< "dry_run": true,` vs `> "dry_run": false,` and nothing else.)

- [ ] **Step 4: Spot-check the worktree.**

Run:
```bash
cd /workspaces/ocr-container/pd-png-optimizer/.claude/worktrees/rename-smoke && \
git status --short | head -30 && \
echo "---" && \
grep -rn 'pd[-_]' . \
  --include='*.py' --include='*.toml' --include='*.md' --include='*.rs' --include='*.yml' \
  --exclude-dir='.git' --exclude-dir='target' --exclude-dir='.venv' --exclude-dir='archive' \
  2>/dev/null | head -20
```

Expected:
- `git status --short` is non-empty: shows modifications to pyproject.toml, README, workflows, and (if pd-png-optimizer has a Python facade dir matching one of the manifest's `dir_renames` patterns) a directory move surfaced as deletes-of-old + additions-of-new.
- The grep returns zero or near-zero results. Any remaining `pd[-_]` matches indicate either: (a) a manifest gap to fill before Phase 2, or (b) intentional historical/archive prose. Note remaining matches in `/tmp/rename-smoke-residuals.txt` for review with CT before proceeding to Phase 2 planning.

- [ ] **Step 5: Confirm idempotency on the real worktree.**

Run:
```bash
cd /workspaces/ocr-container/scripts/rename && \
uv run python apply_rename.py \
  --scope /workspaces/ocr-container/pd-png-optimizer/.claude/worktrees/rename-smoke \
  --manifest /workspaces/ocr-container/scripts/rename/rename-manifest.json \
  --report /tmp/rename-smoke-second.json && \
python3 -c "import json; r=json.load(open('/tmp/rename-smoke-second.json')); print('files_rewritten:', r['files_rewritten']); print('file_renames:', r['file_renames']); print('dir_renames:', r['dir_renames'])"
```

Expected: `files_rewritten: 0`, `file_renames: []`, `dir_renames: []`. The harness reads its own output as already-renamed and does nothing.

- [ ] **Step 6: Tear down the throwaway worktree.**

Run:
```bash
cd /workspaces/ocr-container/pd-png-optimizer && \
git worktree remove --force .claude/worktrees/rename-smoke
```

Expected: clean removal. `git worktree list` does not include the rename-smoke path.

- [ ] **Step 7: No commit on this task** — the smoke test is a behavior check, not a code change. Mark the task complete in the task list.

---

## Phase 0+1 acceptance criteria (from spec §6)

After all tasks above are checked, verify the spec-defined gates pass:

- [ ] **Phase 0 gates:**
  - `gh api orgs/pdomain --jq .login` returns `pdomain`.
  - `curl -sI https://www.npmjs.com/~pdomain | head -1` returns `HTTP/2 200`.
  - `pip index versions pdomain-book-tools` (or `curl https://pypi.org/pypi/pdomain-book-tools/json | jq .info.version`) shows `0.0.1`.

- [ ] **Phase 1 gates:**
  - `uv run pytest` in `scripts/rename/` is fully green.
  - `apply_rename.py --dry-run --scope=<a pd-* repo>` produces a `changes.json` with deterministic content (re-running yields byte-identical output).
  - Re-running `apply_rename.py` against an already-renamed tree is a no-op (`files_rewritten: 0`).

If any gate fails, surface it to CT before moving to Phase 2 planning.
