# Overnight strict-linting rollout — status (2026-05-17)

> **For CT when you wake up.** This is the punch-list of what landed overnight. Every commit is local — nothing pushed. Every `make ci AI=1` was green when the agent finished.

**Reference decision doc:** [`docs/decisions/2026-05-17-strict-linting.md`](../decisions/2026-05-17-strict-linting.md).
**Reference canonical pattern (live, evolving):** `/home/vscode/.claude/projects/-workspaces-ocr-container/memory/project_strict_linting_canonical_pattern.md` — captures pdomain-book-tools final state PLUS the addenda + divergences discovered during the 9 downstream rollouts.

## Per-repo status

| # | Repo | Tip SHA | Commits | Status | Notes |
|---|------|---------|---------|--------|-------|
| 1 | pdomain-book-tools | `f809701` | 8 | ✅ canonical | Established canonical pattern; `failOnWarnings` DEFERRED via `--level error` (CuPy/cv2/DocTR ~4k stub warnings) |
| 2 | pdomain-ops | `546dc79` | 7 | ✅ canonical mirror | Greenfield; first follower; `dict[str, Any]` annotations + BLE001 per-file-ignores for GPU optional-import code |
| 3 | pdomain-ocr-cli | `a17a6b8` | 7 | ✅ canonical mirror | 100% branch coverage PRESERVED (no floor drop needed!); only 7 noqa added; ⚠️ refactored `_update_check.py` to avoid `reportConstantRedefinition` |
| 4 | pdomain-ocr-synth | `0ea3320` | 7 | ✅ canonical mirror | src-layout; largest batch-1 repo (65+62 files); ⚠️ **added 2 bulk global suppressions** (`reportMissingTypeArgument = "none"` + `reportConstantRedefinition = "none"`) covering 62 of 83 stub errors — review whether to back out and refactor |
| 5 | pdomain-prep-for-pgdp | `dc876d7` | 12 | ✅ Python + TS | 7 Python + 5 TS commits + bonus D102 fix; knip baseline 15 advisory findings |
| 6 | pdomain-ocr-labeler-spa | `3bf9523` | 13 | ✅ Python + TS | Largest single rollout (87+123 Python + 219 TS); TS-1 split into 1a/1b (`exactOptionalPropertyTypes` was hardest flag); jsx-a11y had 9 high-volume rules demoted to warn |
| 7 | pd-png-optimizer | `a56a827` | 8 | ✅ Python + Rust | **`failOnWarnings = true` ENABLED** (deliberate deviation — no stub-noise deps); cargo deny baseline clean; ⚠️ needed hand-written `_native.pyi` PyO3 stub |
| 8 | pd-ocr-labeler | `32a731c` | 2 | ✅ minimal scope | Legacy NiceGUI being replaced; only `.editorconfig` + gitleaks + uv-lock-check per decision doc |
| 9 | pd-ocr-trainer | `545df570` | 2 | ✅ minimal scope | Will be rewritten into SPA ecosystem; minimal scope only |
| 10 | se-llm-skills | `4633c8c` | 5 | ✅ infrastructure | Most strict-linting tooling already present (ahead of pd-* on `failOnWarnings = true` from day 1); added pre-commit + CI + cov-branch + began exclude-list drawdown |

**Total: ~71 commits across 10 repos, all local, all green.**

Not touched (intentional): `pdomain-index-pip` (pending rename from `pd-index`), `pdomain-index-npm` (doesn't exist yet), `pdomain-ui` (doesn't exist yet).

## Decisions that need your call

Two items worth surfacing before any of these get pushed:

### 1. pdomain-ocr-synth global suppressions — too broad?

Agent added these to pdomain-ocr-synth's `[tool.basedpyright]`:
```toml
reportMissingTypeArgument = "none"
reportConstantRedefinition = "none"
```
to cover 62 of 83 stub errors at scale. **pdomain-ocr-cli's agent took the opposite path** for `reportConstantRedefinition`: refactored the offending site with an intermediate variable. The bulk approach is faster but disables real correctness checks for FUTURE code, not just legacy. Decision: keep, refactor, or scope tighter via `executionEnvironments`.

### 2. pdomain-ocr-labeler-spa jsx-a11y rule demotions

Agent demoted 9 high-volume jsx-a11y rules to `warn` rather than fix all 219 files' findings inline. pdomain-prep-for-pgdp's agent went the opposite way: 8 inline suppressions at the violation sites. For a 219-file SPA, demotion is probably the right call but worth confirming the workspace pattern.

## Workspace-canonical addenda discovered (already in canonical-pattern memory)

These weren't in the original decision doc but emerged during rollout — relevant if you write another rollout plan later:

- **`.markdownlint-cli2.jsonc` is required** alongside the markdownlint-cli2 pre-commit hook. The hook silently uses defaults without it.
- **gitlint 72-char title limit clips template commit messages** — several pdomain-book-tools-template titles in the canonical plan needed shortening. Future plan templates should respect 72 chars in commit titles.
- **`reportMissingTypeArgument`** is workspace-wide pattern — `dict` / `list` / `tuple` without type args trigger it at recommended mode.
- **cargo-deny 0.19 format change** — removed `unlicensed`/`copyleft`/`deny` keys. Decision doc's `deny.toml` template needs updating.
- **License allowlist needs `Unicode-3.0`** for `unicode-ident` transitive Rust dep.
- **PyO3 facades need hand-written `_native.pyi`** for basedpyright recommended-mode cleanliness.
- **`strictTypeChecked` ESLint preset must be scoped to `src/**/*.{ts,tsx}`** via `.map((c) => ({ ...c, files: [...] }))` — naively spreading the preset tries to type-check `postcss.config.js` etc.
- **failOnWarnings=true criterion:** small codebase + no untyped third-party stub debt + clean baseline → attempt directly. Otherwise defer via `--level error`.

## Plan docs added (this overnight)

All under `/workspaces/ocr-container/docs/plans/`:
- `2026-05-17-pdomain-ops-strict-linting.md`
- `2026-05-17-pdomain-ocr-cli-strict-linting.md`
- `2026-05-17-pdomain-ocr-synth-strict-linting.md`
- `2026-05-17-pdomain-prep-for-pgdp-strict-linting.md`
- `2026-05-17-pdomain-ocr-labeler-spa-strict-linting.md`
- `2026-05-17-pd-png-optimizer-strict-linting.md`
- `2026-05-17-se-llm-skills-strict-linting.md`
- `2026-05-17-legacy-minimal-scope-strict-linting.md`

Survey doc:
- `/workspaces/ocr-container/docs/research/2026-05-17-se-llm-skills-strict-linting-survey.md`

## Memory updates

In `/home/vscode/.claude/projects/-workspaces-ocr-container/memory/`:
- `project_strict_linting_canonical_pattern.md` — pattern + addenda + divergences (the live reference for any future rollout work).
- `project_se_llm_skills_ahead_of_pd.md` — notes that se-llm-skills is more advanced than pd-* on strict-linting (gap is coverage scope + missing CI infra, not tooling selection).

## Suggested next steps when you wake up

1. **Review each repo's tip commit visually** (`cd <repo> && git log --oneline -10`) to confirm nothing weird.
2. **Decide on the two judgment calls** above (pdomain-ocr-synth global suppressions; pdomain-ocr-labeler-spa jsx-a11y demotions).
3. **Push when ready** — nothing has been pushed; all commits are local. Suggested order: pdomain-book-tools first (foundation), then everything else can go in any order since they don't share state.
4. **Open follow-up issues** if you want any deferred backlog tracked:
   - pdomain-ocr-synth: 55+ deferred ANN/D per-file-ignores (cleanup commit later).
   - pdomain-ocr-labeler-spa: TS-1b's `exactOptionalPropertyTypes` test-file relaxations could be tightened later.
   - pdomain-prep-for-pgdp & pdomain-ocr-labeler-spa: knip baseline ~15-30 findings each, non-blocking; flip blocking once cleaned.
   - se-llm-skills: 15 exclude-list entries still deferred (including 1,040-LOC `classify_hunks.py`).
5. **Decision doc updates** — capture the workspace-canonical addenda (markdownlint-cli2.jsonc, cargo-deny 0.19 format, Unicode-3.0, PyO3 _native.pyi, strictTypeChecked scoping) into the decision doc proper so future rollouts don't re-discover.

## What did NOT land

- Nothing was pushed.
- No PRs opened.
- No follow-up issues filed.
- Pd-ui / pdomain-index-npm / pdomain-index-pip remain untouched (they don't exist yet or are out of scope).
- Decision doc itself was not edited (the addenda live in memory only — see suggested next step 5).
