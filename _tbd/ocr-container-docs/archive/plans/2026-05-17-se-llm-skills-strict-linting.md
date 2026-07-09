---
status: complete
synced: 2026-05-17
milestone: 1
repo: ConcaveTrillion/se-llm-skills
---

# se-llm-skills — strict linting rollout (infrastructure additions + exclude-list drawdown)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans`. This repo is structurally **different** from other pd-* rollouts: most strict-linting tooling is ALREADY IN PLACE. The real gap is missing infrastructure (no pre-commit, no CI) + 11 source files in `extend-exclude` that should be linted long-term.

**Reference:**
- Survey: `/workspaces/ocr-container/docs/research/2026-05-17-se-llm-skills-strict-linting-survey.md` (commit `e420c07`)
- Decision doc: [`docs/decisions/2026-05-17-strict-linting.md`](../decisions/2026-05-17-strict-linting.md)
- Canonical Python pattern memory: `/home/vscode/.claude/projects/-workspaces-ocr-container/memory/project_strict_linting_canonical_pattern.md`
- Project memory: `/home/vscode/.claude/projects/-workspaces-ocr-container/memory/project_se_llm_skills_ahead_of_pd.md`

**Working directory:** `/workspaces/ocr-container/se-llm-skills/`

---

## What's ALREADY in place (do NOT redo)

- Full canonical ruff rule set selected (ANN, S, C4, PERF, TC, TID, PT, RET, PL, D, BLE, TRY, LOG, G, etc.)
- basedpyright at `typeCheckingMode = "recommended"` + `failOnWarnings = true` (STRICTEST setting; pdomain-book-tools deferred this)
- `filterwarnings = ["error"]` in pytest
- 209 passing tests

Tasks 1-2 (basedpyright migration), 3 (remove isort/pylint), 6 (ruff expansion), 7 (pytest hardening), 8 (basedpyright recommended): **ALL ALREADY DONE.** Do NOT re-execute these.

---

## Suppression policy

Verbatim from [pdomain-book-tools plan §Suppression policy](2026-05-17-pdomain-book-tools-strict-linting-rollout.md). Same 7 rules; ~90 min per task max.

---

## Task 1: Add `.editorconfig` + `.gitlint` {#add-editorconfig-gitlint}

- [ ] `cat /workspaces/ocr-container/pdomain-book-tools/.editorconfig > .editorconfig`
- [ ] `cat /workspaces/ocr-container/pdomain-book-tools/.gitlint > .gitlint`
- [ ] Add `"gitlint>=0.19.1",` to dev deps (use existing dep-group structure). `uv sync`.
- [ ] Commit:
```
chore: add canonical .editorconfig and .gitlint

Workspace-canonical files per docs/decisions/2026-05-17-strict-linting.md.
Mirror pdomain-book-tools f809701 content verbatim.
```

---

## Task 2: Add `.pre-commit-config.yaml` (full canonical) {#add-pre-commit-configyaml-full-canonical}

This repo currently has NO pre-commit infrastructure. Add the full canonical set.

- [ ] `cat /workspaces/ocr-container/pdomain-book-tools/.pre-commit-config.yaml > .pre-commit-config.yaml`
- [ ] Edit:
  - Replace `pd_book_tools` → the actual python package directory name for se-llm-skills (verify with `ls`; if it's at `src/se_llm_skills/`, use `src/se_llm_skills`; else use the discovered path).
  - In the basedpyright local hook: adjust `entry:` and `files:` accordingly.
  - NOTE: basedpyright config already has `failOnWarnings = true` per discovery. The local-hook entry can use just `uv run basedpyright <path>` (NO `--level error` — we WANT warnings to fail since failOnWarnings=true is already on).
- [ ] Add `"pre-commit>=4.2.0",` to dev deps if missing.
- [ ] `uv sync`. Install: `uv run pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg`.
- [ ] `uv run pre-commit run --all-files 2>&1 | tail -60`. Fix any new findings. No `--no-verify`.
- [ ] Commit:
```
chore(precommit): add canonical hooks (gitleaks + check-* + uv-lock-check + basedpyright + gitlint)

Mirrors pdomain-book-tools f809701 canonical pattern. First pre-commit
infrastructure in this repo:
- pre-commit-update (auto-rev bumper)
- pre-commit-hooks v6.0.0 (trailing/EOF/yaml/json/toml/large-files
  (maxkb=1000)/debug/merge)
- gitleaks v8.30.1
- ruff-pre-commit v0.15.13 (I-fix → general-fix → format)
- markdownlint-cli2 v0.22.1
- local uv-lock-check + basedpyright (failOnWarnings=true already on
  per existing config — no --level error in hook entry)
- gitlint v0.19.1 (commit-msg stage)

Per docs/decisions/2026-05-17-strict-linting.md.
```

---

## Task 3: Add `--cov-branch` + coverage floor {#add-cov-branch-coverage-floor}

- [ ] Check current pytest config: `grep -A20 "\[tool.pytest" pyproject.toml`.
- [ ] Add to `[tool.pytest.ini_options]` `addopts` (extend, don't overwrite):
  - `--cov-branch`
  - `--cov-report=term-missing:skip-covered`
  - `--cov-report=html`
- [ ] Measure current coverage: `uv run pytest --cov-branch 2>&1 | tail -10`. Note the number.
- [ ] In `[tool.coverage.report]` add `fail_under = <NN>` where NN is **2 percentage points below the measured number** (small ratchet buffer). Comment with a TODO to raise as branch-coverage gaps close.
- [ ] `make ci AI=1` (if Makefile exists; else `uv run pytest`) must pass.
- [ ] Commit:
```
test(pytest): add --cov-branch + initial fail_under floor

Mirrors pdomain-book-tools f809701 canonical pattern. --cov-branch
measures branch coverage; fail_under = <NN> pins the post-branch
coverage floor with a 2pp ratchet buffer.

Per docs/decisions/2026-05-17-strict-linting.md.
```

---

## Task 4: Add GitHub Actions CI workflow {#add-github-actions-ci-workflow}

- [ ] Create `.github/workflows/ci.yml` matching the pattern other pd-* repos use. Reference pdomain-prep-for-pgdp's `.github/workflows/ci.yml` for the lean single-job pattern.
- [ ] Basic structure:
```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - name: Run make ci
        run: make ci AI=1
```
- [ ] Verify Makefile has `ci:` target (per survey it should). If not, add a minimal one wiring `pre-commit-check` + `test` + (any existing) `build`.
- [ ] Commit (locally only — pushing the workflow is a separate human decision):
```
chore(ci): add GitHub Actions workflow running make ci AI=1

Lean single-job pattern matching pdomain-prep-for-pgdp. First CI for
this repo. Triggers on push + PR to main.

Per docs/decisions/2026-05-17-strict-linting.md.
```

---

## Task 5: Phased exclude-list drawdown (start) {#phased-exclude-list-drawdown-start}

Per survey: 11 files (including 1,040-LOC `classify_hunks.py`) are in `[tool.ruff] extend-exclude` and basedpyright `exclude`. These ship verbatim into Claude plugin artifacts, so they should be linted long-term.

**For this rollout commit: remove 2-3 LOW-RISK files from extend-exclude.** Fix what surfaces. Pick files that are likely clean: small utility scripts, recently-touched files. Save the 1,040-LOC `classify_hunks.py` for a dedicated commit (or defer entirely if scope explodes).

- [ ] List current excludes: `grep -A20 "extend-exclude\|^exclude" pyproject.toml`.
- [ ] Pick 2-3 files (smallest first; recently-touched are likely cleanest).
- [ ] Remove them from `extend-exclude` (and basedpyright `exclude` if separately listed).
- [ ] Run `uv run ruff check <files>` and `uv run basedpyright <files>`. Triage. STOP at 60 min for this task; the larger files can wait.
- [ ] Commit:
```
chore(lint): begin exclude-list drawdown — bring <files> under canonical lint

Per docs/research/2026-05-17-se-llm-skills-strict-linting-survey.md.
Removes <files> from extend-exclude; <H> noqa/pyright-ignore added
inline with comments where narrowing wasn't viable.

Remaining exclude-list backlog: <N> files including classify_hunks.py
(1,040 LOC, dedicated commit forthcoming).

Per docs/decisions/2026-05-17-strict-linting.md.
```

---

## Self-review checklist

- [ ] 5 commits land (editorconfig+gitlint, pre-commit, cov-branch+floor, CI workflow, exclude-list step).
- [ ] No `--no-verify`.
- [ ] `make ci AI=1` (or `uv run pre-commit run --all-files && uv run pytest`) green.
- [ ] `.editorconfig`, `.gitlint`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml` all present.
- [ ] failOnWarnings = true remains true (pre-existing — do not change).
- [ ] extend-exclude list shrunk by 2-3 files.

## Notes for the agent

- This is the SHORTEST rollout (5 commits) because most tooling pre-existed. Don't redo what's already done.
- The plan's "exclude-list drawdown" (Task 5) is partial — finishing it (all 11 files including classify_hunks.py) is follow-up work that should land in subsequent commits, not this rollout.
- If a task overruns ~90 min, STOP and report.
- Final report: "5 commits landed; final SHA: <X>; CI workflow created (not pushed); coverage floor pinned at <NN>%; <N> files removed from exclude (<M> remain including classify_hunks.py); <flagged divergences from canonical>".
