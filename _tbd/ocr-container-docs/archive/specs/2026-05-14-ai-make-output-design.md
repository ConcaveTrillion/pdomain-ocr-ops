# AI=1 Make Output Design

**Date:** 2026-05-14  
**Status:** Approved  
**Scope:** All 8 pd-* repos

## Problem

`make ci` and other make targets produce high-volume output (pytest `-v -ra`, cargo test, vitest, ruff, pre-commit hooks) that wastes tokens when AI agents run them. Agents only need pass/fail and error details — not the full trace of a passing run.

## Solution

Add `AI=1` support to every Makefile. When set, any make target is silently re-invoked, full output is captured to `.ci-ai.log`, and only a one-line pass or the failing step's full output is printed to stdout.

## Makefile Pattern

Add these lines at the top of every repo's Makefile, then wrap all existing content in the `else` branch:

```makefile
.DEFAULT_GOAL := ci   # set to repo's actual default target
AI ?=
LOG := .ci-ai.log

ifdef AI
# AI mode: intercept any goal, re-invoke without AI, capture output
_goals := $(or $(MAKECMDGOALS),$(.DEFAULT_GOAL))
.PHONY: $(_goals)
$(_goals):
	@rm -f $(LOG)
	@$(MAKE) --no-print-directory AI= $@ > $(LOG) 2>&1 \
		&& echo "✅ $@ passed (log: $(LOG))" \
		|| (echo "❌ $@ failed:"; uv run scripts/ai-filter-log.py $(LOG); echo "(full log: $(LOG))"; exit 1)

else
# Normal mode: all existing targets unchanged

... existing Makefile content ...

endif
```

### How it works

- `AI=1` puts Make into intercept mode before any target definition is evaluated.
- `$(_goals)` matches whatever target(s) were requested on the command line, falling back to `.DEFAULT_GOAL` if none.
- The catch-all re-invokes `make <target> AI=` — the explicit `AI=` clears the flag in the recursive call, which hits the `else` branch and runs normally.
- stdout+stderr of the full recursive make are captured to `.ci-ai.log`.
- On pass: single line `✅ <target> passed (log: .ci-ai.log)`.
- On fail: `❌ <target> failed:` followed by filtered failure output (see below), then the log path.
- Exit code is preserved — nonzero on failure.

### Why `AI=` in the recursive call

GNU Make propagates command-line variables to recursive `$(MAKE)` calls via `MAKEFLAGS`. Without `AI=`, the recursive call would also enter AI mode and double-write the log. The explicit `AI=` overrides this propagation.

## Per-repo `.DEFAULT_GOAL`

| Repo | `.DEFAULT_GOAL` |
|------|----------------|
| pdomain-book-tools | `ci` |
| pdomain-ocr-cli | `ci` |
| pd-ocr-labeler | `ci` |
| pdomain-ocr-labeler-spa | `ci` |
| pdomain-ocr-synth | `ci` |
| pd-ocr-trainer | `ci` |
| pd-png-optimizer | `ci` |
| pdomain-prep-for-pgdp | `ci` |

All repos default to `ci`.

## `.gitignore`

Add to every repo's `.gitignore`:

```
.ci-ai.log
```

The log is overwritten at the start of each run (`rm -f $(LOG)`). No rotation or cleanup needed.

## Agent conventions

- `make ci AI=1` — full CI check; use before committing or opening a PR.
- `make test AI=1` — test-only check after a fix.
- `make lint AI=1`, `make build AI=1`, `make frontend-test AI=1` — individual steps.
- Any make target works; no per-target maintenance required.
- On failure, filtered failure output is already on stdout — no need to `cat .ci-ai.log`. The full log is preserved at `.ci-ai.log` for deeper inspection.
- `AI=` (empty) or omitting the flag: identical to today's behavior.
- `AI=1` is canonical; any non-empty value enables the mode.

## Failure filter: `scripts/ai-filter-log.py`

A uv inline script (PEP 723) copied identically to all 8 repos. Invoked on failure to extract only the relevant portions from `.ci-ai.log`.

```python
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
```

Run as `uv run scripts/ai-filter-log.py <logfile>`. Uses stdlib only (`re`, `sys`, `pathlib`).

### Extraction strategy (tried in order, all matches printed)

| Tool | Strategy |
|------|----------|
| pytest | `=== FAILURES ===` block + `=== ERRORS ===` block + `=== short test summary info ===` block — each delimited by `===` markers |
| cargo test | `failures:` section through `test result:` line |
| ruff | Lines matching `path:line:col:` pattern (already one-per-violation) |
| mypy / tsc | Lines matching `error:` |
| pre-commit | Lines from a `Failed` hook name through the next hook separator |
| fallback | Lines matching `error\|failed\|failure` (case-insensitive) + 3 lines of context, deduped |

Output is capped at 300 lines. If no extractor matches, the last 50 lines of the log are shown (build errors tend to appear at the end).

## What does not change

- The normal (non-AI) code path is byte-for-byte identical to today.
- Exit codes are preserved in both modes.
- Each repo is fully self-contained (filter script is copied, not referenced externally).
- New targets added to any Makefile automatically inherit AI=1 support without any additional work.

## Scope of changes per repo

For each of the 8 repos:
1. Add `AI ?=`, `LOG := .ci-ai.log`, `.DEFAULT_GOAL := ci`, and the `ifdef AI` block at the top.
2. Wrap all existing Makefile content in `else ... endif`.
3. Add `.ci-ai.log` to `.gitignore`.
4. Add `scripts/ai-filter-log.py` (identical content across all repos).

Total: ~12 Makefile lines + 1 gitignore line + the filter script per repo.
