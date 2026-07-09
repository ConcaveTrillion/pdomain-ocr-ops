# Decisions — strict linting + type-check stack (2026-05-17)

**Status:** approved; rollout not yet started.
**Source research:** [`docs/research/2026-05-17-strict-linting-stack.md`](../research/2026-05-17-strict-linting-stack.md)
**Workspace scope:** all 12 repos (8 existing pd-* + 3 incoming pd-* + se-llm-skills).
**Goal:** strictest sound lint + type-check feedback at commit time so LLM coding agents iterate against high-signal errors locally before diffs land.

---

## Summary

| Area | Decision |
|---|---|
| Python type checker | basedpyright 1.39.4 @ `typeCheckingMode = "recommended"` + `failOnWarnings = true` |
| Python ruff rules | Full expansion: `ANN S C4 PERF TC TID PT RET PL D BLE TRY LOG G` on top of current baseline |
| Python ruff `D` (docstrings) | Enable globally + per-file-ignores for `tests/**`, `**/_*.py`, `**/__init__.py`, `**/migrations/**` |
| Python pytest | `filterwarnings = ["error"]` with case-by-case `ignore::...` for known noisy third-party deps; `--cov-branch` enabled in `addopts` to gate branch coverage on `except` paths |
| TS compiler flags | All 5 strict additions: `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `noPropertyAccessFromIndexSignature`, `useUnknownInCatchVariables` |
| typescript-eslint preset | `strictTypeChecked` + `stylisticTypeChecked` with `parserOptions.projectService: true` |
| `@typescript-eslint/no-explicit-any` | `error` in src/, `off` in test files |
| TS dead-code detection | `knip 6.x` in CI only, non-blocking (`\|\| true`) until each frontend baseline is clean |
| TS linter | ESLint 9.x (NOT 10) until react-hooks + jsx-a11y publish ESLint-10-compatible peer ranges. Biome rejected — can't run type-aware rules or react-hooks/jsx-a11y. |
| Commit-message lint | `gitlint v0.19.1` in every repo's pre-commit |
| Dependency updates | Renovate self-hosted via GitHub Action (free regardless of repo visibility; no vendor lock-in) |
| Rust supply chain | `cargo deny check` + `deny.toml` in pd-png-optimizer; license allowlist MIT/Apache-2.0/BSD/ISC/Zlib |
| Secret detection | `gitleaks v8.24.2` in every repo (pre-commit + CI) |
| `.editorconfig` | Canonical file in every repo root |
| isort + pylint | Remove from dev deps everywhere (ruff `I` and `PL` rules subsume both) |
| Pre-commit framework | `pre-commit` (pre-commit.com) is the umbrella for both Python AND JS/TS hooks via `language: system` entries. No husky / simple-git-hooks. |
| Rollout order | **pdomain-book-tools first** (foundation library; sets canonical pattern for consumers to mirror), then the rest |
| pd-ocr-labeler (legacy NiceGUI) | **Minimal scope** — gitleaks + uv-lock-check only; everything else deferred until deprecation completes |
| pd-ocr-trainer | **Minimal scope** — same as pd-ocr-labeler. Treat as legacy-bound-for-replacement; the trainer will be rewritten into the SPA ecosystem (future project), and the full linting stack should land WITH that rewrite, not before it. |

---

## Python stack

### Type checker — basedpyright @ recommended

**Decision:** Replace pyright with `basedpyright 1.39.4` at `typeCheckingMode = "recommended"` with `failOnWarnings = true` in every Python repo.

**Why this over vanilla pyright:**
- `"recommended"` mode in basedpyright is stricter than `--strict` in vanilla pyright. It checks unannotated functions by default; vanilla pyright skips them unless `reportMissingParameterType` is wired up explicitly.
- 97.8% typing-spec conformance vs vanilla pyright's lower number (and mypy's 58.3%).
- Pyright-style inline error messages — actionable for LLM iteration loops.
- Bundles its own Node runtime via `nodejs-wheel`, so `uv add --dev basedpyright` works without a separate `npm install`.

**Why this over mypy:**
- mypy's `--strict` mode skips unannotated functions unless you also pass `--check-untyped-defs`.
- mypy + basedpyright running both is confusing for LLMs when the tools disagree. Pick one; basedpyright is stricter.

**Why this over `ty` (astral's new checker):**
- `ty 0.0.32` is in beta (May 2026) with 53.2% typing-spec conformance. Significant false-negative rate makes it unsuitable as a strictness gate.
- Revisit when ty hits 1.0 and conformance reaches ~90%.

**Migration knob:** If a repo can't meet `"recommended"` immediately, use `executionEnvironments` to set `tests/` at `"standard"` and `src/` at `"recommended"`. Pick one and hold it; don't let test files drift forever.

**`failOnWarnings = true` criterion (addendum, 2026-05-17 rollout):** The decision doc originally treated deferral as universal. pd-png-optimizer proved `failOnWarnings = true` is achievable from day one on a clean-slate repo (4 src files, 0 prior suppressions, no GPU/stub-noise deps) — landed directly with 4 global suppressions driven by argparse.Namespace and C-extension kwargs. Decision criterion for downstream:

- **Attempt `failOnWarnings = true` directly** if: small codebase + no untyped third-party stub debt (no CuPy/cv2/DocTR/PyTorch) + clean baseline.
- **Defer via `--level error` pattern** (comment out `failOnWarnings = true` + pass `--level error` to pre-commit hook and Makefile target) if: large codebase OR untyped stub-heavy deps. This is what pdomain-book-tools uses.

**`reportMissingTypeArgument` — hand-fix, not global suppression (addendum, 2026-05-17 rollout):** `dict` → `dict[str, Any]`, `list` → `list[T]`, `tuple` → `tuple[T, ...]` throughout. pdomain-ocr-synth initially added `reportMissingTypeArgument = "none"` as a global basedpyright suppression but reverted it per CT decision — bulk-suppressing globally disables a real correctness check for all future code. Triage per-site or fix in bulk via search-and-replace, but do not disable the rule globally.

### Ruff — full proposed rule set

**Decision:** Adopt the full expanded `[tool.ruff.lint] select` from the research doc PLUS four extra groups (`BLE TRY LOG G`) chosen to roll the workspace's `docs/python-coding-guidelines.md` into tools wherever syntactically possible:

```toml
select = [
  "E", "W", "F", "I", "N",                # current baseline
  "B", "SIM", "UP", "RUF", "ERA", "T20",  # current baseline
  "ANN", "S", "C4", "PERF", "TC", "TID",  # new (research doc)
  "PT", "RET", "PL", "D",                 # new (research doc)
  "BLE", "TRY", "LOG", "G",               # new (guidelines-driven, added 2026-05-17 audit)
]
```

**Why all of them:**
- `ANN` forces function-signature annotations — direct LLM-correctness win, makes downstream type errors deterministic.
- `S` (bandit) catches `assert` in non-test code, hardcoded credentials, broad exception swallow.
- `TC` moves type-only imports into `TYPE_CHECKING` blocks, reducing import-time cost.
- `PT` enforces pytest conventions (parametrize, fixture, raises patterns) — relevant since every repo uses pytest.
- `RET` catches inconsistent return paths.
- `PERF` catches anti-patterns like materializing lists where iterators suffice.
- `PL` subsumes ~90% of pylint at 50× speed (so pylint goes away — see "removed tools" below).
- `D` enforces docstrings on public API.
- **`BLE` (flake8-blind-except)** — catches `except Exception:` and `except BaseException:` without re-raise / specific handling. Directly enforces guidelines #1, #3, #4, and the syntactic portion of #5/#16/#20 from `docs/python-coding-guidelines.md`.
- **`TRY` (tryceratops)** — exception-handling best practices. `TRY400` enforces `logging.exception(...)` over `logging.error(...)` in `except` blocks (guideline #16); `TRY002` bans raising vanilla `Exception`; `TRY004` prefers `TypeError` for type checks; `TRY200`/`TRY201` enforce `raise X from Y`.
- **`LOG` (flake8-logging)** + **`G` (flake8-logging-format)** — proper f-string/format usage in `log.*` calls, lazy formatting, etc. Supports guidelines #16 and #17 indirectly.

**Rejected (single tools subsumed by ruff):** standalone isort, standalone pydocstyle, standalone flake8, standalone black.

**Per-repo overrides (carry forward existing ones):**
- `pdomain-prep-for-pgdp`, `pdomain-ocr-labeler-spa`: keep `"B008"` and `"UP042"` in `ignore` (FastAPI `Depends()` pattern).
- `pd-png-optimizer`: `target-version = "py39"` (multi-Python facade).
- `pd-ocr-labeler` (legacy): see "repo-specific" section.

### D (docstring) scope

**Decision:** Enable `D` globally with `[tool.ruff.lint.per-file-ignores]`:

```toml
"tests/**/*.py" = ["S101", "S105", "S106", "S311", "T201", "ANN", "D"]
"**/_*.py" = ["D"]                   # private modules exempt
"**/__init__.py" = ["D104", "F401", "TC"]
"**/migrations/**/*.py" = ["D"]
"scripts/**/*.py" = ["T201", "D"]    # CLI scripts use print()
```

Use `# noqa: D102` / `# noqa: D103` on individual trivial getters / properties where a docstring is noise.

**Convention:** `[tool.ruff.lint.pydocstyle] convention = "google"`. Pick it once at the workspace level; don't let repos drift between google and numpy.

### pytest filterwarnings

**Decision:** `filterwarnings = ["error"]` in every repo, with case-by-case `ignore::DeprecationWarning:torch.*`-style entries for known noisy third-party deps. Also add `--cov-branch` to `addopts` so branch coverage is measured (gates the syntactic portion of guideline #22 — "test the error path, not just happy path").

**Why:** Catches deprecated API usage during LLM iteration. Single highest-leverage line in pytest config. `--cov-branch` flips test-error-path discipline from LLM-judgment to coverage-gate (assuming each repo also enforces a coverage floor; pdomain-ocr-cli already has 100%).

**Migration cost:** `filterwarnings = ["error"]` surfaces every pre-existing warning. Expect 5-30min of cataloguing per established repo. `--cov-branch` may drop measured coverage by 3-8% per repo (uncovered `except` branches surface); pin the new floor at the post-migration number, then ratchet up incrementally. Greenfield repos pay zero cost on both.

---

## TypeScript / React stack

### tsconfig.app.json strict additions

**Decision:** Add all 5 strict flags to every TS frontend's `tsconfig.app.json`:

```jsonc
{
  "compilerOptions": {
    "strict": true,                                  // already on
    "noUncheckedIndexedAccess": true,                // NEW — array/object index returns T | undefined
    "exactOptionalPropertyTypes": true,              // NEW — { foo?: string } excludes { foo: undefined }
    "noImplicitOverride": true,                      // NEW — class overrides must use `override` keyword
    "noPropertyAccessFromIndexSignature": true,      // NEW — obj["key"] required on index sigs
    "useUnknownInCatchVariables": true               // NEW — catch (e) gives e: unknown not any
  }
}
```

**Why all 5 (including the contested noPropertyAccessFromIndexSignature):**
- `noUncheckedIndexedAccess` is the single highest-leverage flag for catching LLM off-by-one and null-dereference patterns.
- `useUnknownInCatchVariables` ends `catch (e: any)` for good.
- `noPropertyAccessFromIndexSignature` is more pedantic but signals intent — `obj["key"]` says "I know this might not exist" vs `obj.key` saying "this is a known property". Worth the friction.

**Migration cost:** 10-50 errors per typical 5k-LOC frontend. Fix path:
1. `tsc --noEmit` with flags on.
2. Use optional chaining (`items[0]?.id`) where TS can't narrow.
3. Non-null assertion with `!` only after a guard, with a comment.

### typescript-eslint preset

**Decision:** Upgrade both frontends from `tseslint.configs.recommended` to:

```js
...tseslint.configs.strictTypeChecked,
...tseslint.configs.stylisticTypeChecked,
```

with `parserOptions.projectService: true` to unlock type-aware rules.

**Why:** The current `recommended` preset silently skips ~30 type-aware rules that catch unsafe assignment, unsafe member access, unsafe call, and unsafe return. Without them, `any` propagation is invisible.

**Performance:** type-checked ESLint adds 3-8 seconds per pre-commit run on a typical 5k-LOC frontend. Acceptable.

**Addendum (2026-05-17 rollout — pdomain-prep-for-pgdp):** `strictTypeChecked` and `stylisticTypeChecked` **must be scoped to `src/**/*.{ts,tsx}`** via `.map()`. Naively spreading the preset array causes ESLint to try type-checking root-level config files (`postcss.config.js`, `vite.config.ts`) which are not in `tsconfig.app.json`'s `include`, producing immediate parse errors. Correct pattern:

```js
...tseslint.configs.strictTypeChecked.map((c) => ({ ...c, files: ["src/**/*.{ts,tsx}"] })),
...tseslint.configs.stylisticTypeChecked.map((c) => ({ ...c, files: ["src/**/*.{ts,tsx}"] })),
```

Apply this scoping in every TS frontend (pdomain-prep-for-pgdp, pdomain-ocr-labeler-spa, pdomain-ui).

### `@typescript-eslint/no-explicit-any`

**Decision:** Flip from `warn` to `error` in src/. Per-file override leaves it `off` in test files (mocks, casts, spy patterns).

**Why:** The single highest-leverage TS rule for LLM correctness. Forces explicit `unknown` or a proper type rather than the silent `any` propagation that makes downstream errors mysterious.

### Dead-code detection — knip

**Decision:** Add `knip 6.x` to CI only (NOT pre-commit) as a non-blocking step (`|| true`) initially; flip to blocking once each frontend's baseline is clean.

**Why non-blocking first:** Knip is genuinely useful but has false positives on dynamic imports, plugin entry points, and Vite-magic patterns. Letting it flag noise without breaking CI for one cycle is the cheap way to baseline.

### Linter — ESLint 9.x

**Decision:** Stay on ESLint 9.x; do NOT upgrade to ESLint 10.

**Why:** As of May 2026, `eslint-plugin-react-hooks` and `eslint-plugin-jsx-a11y` have not published ESLint-10-compatible peer ranges. Move when they do.

**Biome rejected:** Biome v2 added some type-aware rules but cannot run `strict-type-checked` (which requires the TypeScript language service), cannot run `eslint-plugin-react-hooks`, and cannot run `eslint-plugin-jsx-a11y`. For this workspace, Biome's 15× speedup is dwarfed by the rule-coverage regression. Reject.

---

## Cross-cutting infrastructure

### Pre-commit framework

**Decision:** The Python `pre-commit` framework (pre-commit.com) is the umbrella for ALL repos — Python AND JS/TS hooks run inside it via `language: system` entries.

**Why:** Already in use across the workspace. Single tool, single install (`uv run pre-commit install`), consistent UX. No need for husky / simple-git-hooks in any TS repo.

**Addendum (2026-05-17 rollout):** `.markdownlint-cli2.jsonc` is REQUIRED alongside the markdownlint-cli2 pre-commit hook. Without it the hook runs with bare defaults that flag innocuous patterns (e.g. bare URLs, trailing punctuation in headings). Copy pdomain-book-tools' canonical `.markdownlint-cli2.jsonc` verbatim into every repo that includes the hook.

### Commit-message lint — gitlint

**Decision:** Add `gitlint v0.19.1` to every repo's pre-commit:

```yaml
- repo: https://github.com/jorisroovers/gitlint
  rev: v0.19.1
  hooks:
    - id: gitlint
```

With workspace-canonical `.gitlint`:

```ini
[general]
ignore=body-is-missing
max-line-length=100
[title-must-not-contain-word]
words=WIP
[body-max-line-length]
line-length=100
```

**Why gitlint over commitlint:** gitlint is pure Python — installs alongside pre-commit via `uv`. commitlint is Node-only and would require a `package.json` in every Python repo.

**Addendum (2026-05-17 rollout):** The gitlint title limit is **72 chars** (via `[title-max-length] line-length=72`), not the `max-line-length=100` entry in the template above. Several commit-title templates in the canonical pdomain-book-tools plan were 80+ chars and failed gitlint at pre-commit time. Future plan templates must write commit titles at ≤72 chars in the first place; body lines may be up to 100 chars. Use the split-key format that actually landed:

```ini
[general]
ignore=body-is-missing
[title-max-length]
line-length=72
[title-must-not-contain-word]
words=WIP
[body-max-line-length]
line-length=100
```

### Dependency-update bot — Renovate self-hosted

**Decision:** Run Renovate as a self-hosted GitHub Action in a dedicated config repo (e.g. `ConcaveTrillion/pd-renovate-config`). Free regardless of repo visibility; no vendor lock-in.

**Why self-hosted over Renovate Cloud:** Renovate Cloud is also free for the (currently public) ConcaveTrillion repos, but self-hosted gives:
- No dependency on Mend's hosted-tier pricing changing.
- Full control over scheduling and config.
- Logs land in your own GHA history; debuggable.

**Why Renovate over Dependabot:**
- Renovate groups related bumps. A ruff release → **one PR** that bumps `ruff-pre-commit` rev across all 9 Python repos at once. Dependabot creates 9 separate PRs.
- Renovate understands `uv.lock`, `Cargo.lock`, and `package-lock.json` natively.
- `automerge: true` for low-risk updates (pre-commit hook bumps, lint tools) keeps churn low.

**Initial scope of the renovate config:** all 12 repos, with package rules grouping:
- All ruff / ruff-pre-commit bumps → single PR.
- All pre-commit-hooks rev bumps → single PR.
- All eslint / typescript-eslint / prettier bumps → single PR per ecosystem.

### Secret detection — gitleaks

**Decision:** Add `gitleaks v8.24.2` to every repo's `.pre-commit-config.yaml` AND CI:

```yaml
# pre-commit
- repo: https://github.com/gitleaks/gitleaks
  rev: v8.24.2
  hooks:
    - id: gitleaks
```

```yaml
# CI
- name: gitleaks
  uses: gitleaks/gitleaks-action@v2
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Why:** Scans only staged diff (typically <100ms). Catches LLM-generated plausible test credentials before they reach the remote.

### .editorconfig

**Decision:** Add the canonical `.editorconfig` from the research doc to every repo root.

**Why:** Baseline file settings (charset, EOL, indent) editors respect before any formatter runs. Useful for LLM editor environments without format-on-save.

### Rust supply chain — cargo deny

**Decision:** Add `cargo deny check` + `deny.toml` to pd-png-optimizer's CI and Makefile. License allowlist: MIT, Apache-2.0, Apache-2.0-WITH-LLVM-exception, BSD-2-Clause, BSD-3-Clause, ISC, Unlicense, Zlib.

**Why:** Supply-chain security. Adds 10-30s to CI but catches real vulnerability / license drift issues.

**Existing Rust hooks (keep):** `cargo clippy --workspace --all-targets -- -D warnings` and `cargo fmt --check` are already in pre-commit and `make ci`. Don't use `--all-features` — the `extension-module` feature breaks `cargo test` linking on Linux (enabled by maturin only at wheel build time).

**Addendum — license allowlist needs `Unicode-3.0` (2026-05-17 rollout):** `unicode-ident` (transitive Rust dep, pulled in by `proc-macro2`) ships under the `Unicode-3.0` license. Add it to every cargo-deny allowlist alongside the canonical set above, or `cargo deny check` will fail on that crate.

**Addendum — cargo-deny 0.19 format change (2026-05-17 rollout):** cargo-deny 0.19 removed the `unlicensed`, `copyleft`, and `deny` keys from the `[licenses]` table. The `deny.toml` template used in the decision doc (and its source research doc) uses the old key names and will error on current cargo-deny. Use the format that landed in pd-png-optimizer at commit `a56a827` (Task R commit). The relevant `[licenses]` block in the new format uses `allow = [...]` (explicit allowlist) without the removed top-level disposition keys.

### Tools to remove

**Decision:** Remove from dev deps wherever present:
- `isort` (ruff `I` subsumes) — currently in pdomain-book-tools and pd-ocr-trainer.
- `pylint` (ruff `PL` subsumes ~90% at 50× speed) — currently in pdomain-book-tools.

---

## Repo-specific decisions

### pd-ocr-labeler (legacy NiceGUI)

**Decision: minimal scope only.**

Apply:
- `gitleaks` pre-commit + CI hook.
- `uv-lock-check` pre-commit hook.
- `.editorconfig`.

Do NOT apply:
- Ruff rule expansion.
- basedpyright.
- `D` docstring rules (codebase has zero docstrings; investment isn't worth it for a repo being replaced).
- `filterwarnings = ["error"]`.

Keep `fail_under = 0` until the NiceGUI replacement (pdomain-ocr-labeler-spa) fully supersedes it.

### pd-ocr-trainer (will be rewritten)

**Decision: minimal scope only — same treatment as pd-ocr-labeler.**

User intent: pd-ocr-trainer will be rewritten into the SPA ecosystem in a future project. The full linting stack should land WITH that rewrite, not before it.

Until the rewrite ships, apply:
- `gitleaks` pre-commit + CI hook.
- `uv-lock-check` pre-commit hook.
- `.editorconfig`.

Defer:
- setuptools → hatchling migration (was previously flagged as a separate chore commit; now folded into the rewrite project).
- All other linting upgrades.

### pd-png-optimizer

Apply the full canonical stack. Additionally:

**PyO3 facade requires a hand-written `_native.pyi` stub (addendum, 2026-05-17 rollout):** basedpyright recommended + `failOnWarnings = true` floods with C-extension import warnings unless a hand-written `python/pd_png_optimizer/_native.pyi` stub declares every symbol the extension exports. Without it, every call-site produces a warning that the import is untyped. Any future PyO3 repo follows the same pattern.

### All other repos

Apply the full canonical stack per the rollout order below.

---

## Rollout order (revised)

**pdomain-book-tools first** (foundation library; sets canonical patterns for downstream consumers to mirror). Otherwise follow the research doc's ordering, with the deprecated repos handled minimally:

| Order | Repo | Notes |
|---|---|---|
| 1 | **pdomain-book-tools** | Foundation library; most suppressions to add but sets the canonical patterns every other pd-* repo will mirror. Highest-quality precedent first. |
| 2 | pdomain-ops | Greenfield; freshly scaffolded; ideal first follower of the pdomain-book-tools pattern. |
| 3 | pdomain-ocr-cli | Small codebase, 100% coverage floor, already well-linted. |
| 4 | pdomain-ocr-synth | No pre-commit at all today — establish baseline; spec-only state minimizes migration noise. |
| 5 | pdomain-prep-for-pgdp | Actively worked; full stack including frontend (tsconfig + ESLint). |
| 6 | pdomain-ocr-labeler-spa | Similar shape to pgdp-prep; do after pgdp-prep so the frontend patterns are established. |
| 7 | pd-png-optimizer | Add `cargo deny`, expand Python lint rules, add basedpyright to Rust-facade Python. |
| 8 | pdomain-ui (incoming) | Greenfield TS library — apply full TS strict stack from day 1. |
| 9 | pdomain-index-npm (incoming) | Greenfield Node scripts — minimal surface. |
| 10 | pd-ocr-labeler (legacy) | Minimal scope only (gitleaks + uv-lock-check + .editorconfig). |
| 11 | pd-ocr-trainer (legacy) | Minimal scope only; full stack lands with the SPA rewrite (future project). |
| 12 | se-llm-skills | Survey separately. |

**Parallel opportunities:**
- Steps 2-4 (pdomain-ops, pdomain-ocr-cli, pdomain-ocr-synth) are fully independent and can be dispatched as three parallel subagents AFTER step 1 (pdomain-book-tools) lands and the canonical pattern exists.
- Steps 10-11 (the minimal legacy treatments) can be batched into a single PR or single agent task.

---

## What was rejected and why

| Tool | Reason rejected |
|---|---|
| **mypy** | basedpyright is stricter (97.8% vs 58.3% spec conformance), catches unannotated functions mypy skips by default. Running both creates conflicting signals. |
| **ty** (astral's new type checker) | Beta with 53.2% spec conformance; significant false-negative rate. Revisit at 1.0. |
| **pylint** | ruff `PL` covers ~90% of pylint correctness rules at 50× speed; pylint adds CI latency without LLM-feedback value. |
| **Biome** | Can't run `strict-type-checked` (no TS language service), can't run `react-hooks` or `jsx-a11y`. 15× speedup doesn't compensate for rule-coverage regression. |
| **oxlint** | Same limitation as Biome — fast but no type-aware rules. A second JS linter would confuse LLMs about error-source authority. |
| **husky / simple-git-hooks** | Pre-commit framework already handles JS hooks via `language: system`; second hook runner adds complexity. |
| **commitlint** | Node-only; would require `package.json` in every Python repo. Use gitlint instead. |
| **stylelint** | Both frontends are Tailwind-only — zero hand-written CSS. Add only if a frontend migrates to CSS Modules or plain CSS. |
| **Mend Renovate Cloud** | Free for public repos today, but self-hosted GH Action eliminates dependency on Mend's hosted-tier pricing. |
| **Dependabot** | Per-repo PR multiplication is meaningful churn at workspace scale (12 repos sharing lint tools). |
| **isort (standalone)**, **pydocstyle (standalone)**, **flake8**, **black** | All subsumed by ruff. Remove from dev deps wherever present. |
| **depcheck / npm-check-updates** | Superseded by Renovate. |

---

## Follow-up items

1. **Write the per-repo migration plans.** Each repo in the rollout order needs its own plan file at `docs/plans/2026-MM-DD-<repo>-strict-linting.md`. The research doc's "5-commit sequence per Python repo" + "5-commit sequence per frontend" sections give the template.

2. **Create the Renovate config repo.** Once decided which Renovate variant (cloud vs self-hosted GH Action), stand up `ConcaveTrillion/pd-renovate-config` with the workspace-canonical `renovate.json` and the scheduling GH Action workflow.

3. **Workspace-wide canonical configs.** Three files should live somewhere referenced by every repo (e.g. a `pd-meta` config repo or symlinked from each):
   - `.editorconfig`
   - `.gitlint`
   - Renovate package-rules templates

4. **Re-evaluate ESLint 10.** Track `eslint-plugin-react-hooks` and `eslint-plugin-jsx-a11y` for ESLint 10 peer-range bumps. When both ship, plan the ESLint 9 → 10 upgrade across both frontends + pdomain-ui.

5. **Re-evaluate ty.** Astral's type checker is moving fast. When it reaches 1.0 with ≥90% conformance, re-evaluate vs basedpyright.

6. **D rule docstring backlog.** When pdomain-book-tools rolls out `D`, expect a backlog of missing docstrings. Can be addressed incrementally via `# noqa: D102` markers with TODO comments, then cleaned in a focused docstring-pass commit.

7. **Migrate `docs/python-coding-guidelines.md` into a real guidelines + review-checklist pair structured for LLM consumption.** Current state: one 402-line file blending coding patterns with anti-patterns and inline before/after examples. Audit done 2026-05-17 categorized all 22 rules: 9 will be tool-enforced (✅), 8 partially (🟡), 14 require LLM/human review (❌). Target structure for the migration:

   - **`docs/llm-coding-guide-python.md`** — "WRITE CODE LIKE THIS" reference for an LLM authoring code. Organized by category (Exception Handling, Typed API Boundaries, etc.). Each rule annotated with its enforcement status so an LLM knows which violations will auto-fail at commit time. Includes all 22 rules so the doc is the single canonical reference; LLMs can read it for context even on items that will eventually be caught by tools.
   - **`docs/llm-review-checklist-python.md`** — "WHEN REVIEWING A PR, CHECK THESE" focused list of the ~14 items that survive automated tooling. Structured as direct review prompts (e.g. "For every `try/except` block: which specific exception type matches the cause? Does the `except` arm log before re-raising?"). Each entry references the canonical rule in the guide doc.
   - **TS/React equivalents** — currently no `docs/typescript-coding-guidelines.md` exists. Mirror the structure once the Python pair is established; pull from the linting research doc's TS sections + extract patterns from existing pdomain-prep-for-pgdp/pdomain-ocr-labeler-spa frontends.

   Plan + write these docs after the pdomain-book-tools strict-linting migration lands — that migration will surface the practical edge cases (which suppressions are routine, which signal real anti-patterns) needed to calibrate the LLM prompts.
