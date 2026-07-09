---
status: complete
---

# AI=1 Make Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `AI=1` flag support to every Makefile in all 8 pd-* repos so agents get a single pass/fail line on success and filtered failure output on error, instead of full verbose CI output.

**Architecture:** A top-level `ifdef AI` block in each Makefile intercepts any target invocation, re-invokes `make <target> AI=` (clearing the flag to avoid recursion), captures all output to `.ci-ai.log`, and on failure pipes the log through `scripts/ai-filter-log.py` which extracts only failure-relevant sections. Normal mode (`AI=` unset) is byte-for-byte unchanged.

**Tech Stack:** GNU Make conditionals, uv PEP 723 inline scripts, Python 3.11+ stdlib (`re`, `sys`, `pathlib`)

---

## File Map

**Created in all 8 repos:**
- `scripts/ai-filter-log.py` — uv PEP 723 inline script; extracts pytest/cargo/ruff/pre-commit failure sections from a log file

**Modified in all 8 repos:**
- `Makefile` — 12 lines prepended (AI block) + `endif` appended
- `.gitignore` — one line added: `.ci-ai.log`

**Three repos need `scripts/` created first:** pd-ocr-labeler, pd-ocr-trainer, pd-png-optimizer

---

## Task 1: Write and validate `scripts/ai-filter-log.py`

Work in `pdomain-book-tools/` — this is the canonical copy; other repos get it verbatim.

**Files:**
- Create: `pdomain-book-tools/scripts/ai-filter-log.py`

- [ ] **Step 1: Create synthetic failing log to drive development**

```bash
cat > /tmp/test-ci-fail.log << 'EOF'
collected 10 items

PASSED tests/test_foo.py::test_ok
FAILED tests/test_foo.py::test_bar - AssertionError

============================= FAILURES =============================
__________________________ test_bar ___________________________

    def test_bar():
>       assert add(1, 1) == 1
E       AssertionError: assert 2 == 1

tests/test_foo.py:5: AssertionError
========================= short test summary info =========================
FAILED tests/test_foo.py::test_bar - AssertionError: assert 2 == 1
================ 1 failed, 9 passed in 0.12s ================
EOF
```

- [ ] **Step 2: Run against it before writing the script to confirm failure**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
echo "placeholder" > scripts/ai-filter-log.py
uv run scripts/ai-filter-log.py /tmp/test-ci-fail.log
# Expected: some output (placeholder) — we'll verify correct output after writing
```

- [ ] **Step 3: Write the script**

```python
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Extract failure-relevant sections from a captured make CI log."""
import re
import sys
from pathlib import Path

MAX_OUTPUT_LINES = 300
FALLBACK_TAIL_LINES = 50


def extract_pytest_sections(text: str) -> list[str]:
    sections = []
    for header in ("FAILURES", "ERRORS", "short test summary info"):
        pattern = rf"(={3,} {re.escape(header)} ={3,}.*?)(?=\n={3,}|\Z)"
        m = re.search(pattern, text, re.DOTALL)
        if m:
            sections.append(m.group(1).rstrip())
    return sections


def extract_cargo_failures(text: str) -> list[str]:
    m = re.search(r"(failures:\n\n.*?)(?=\ntest result:|\Z)", text, re.DOTALL)
    return [m.group(1).rstrip()] if m else []


def extract_ruff_lines(text: str) -> list[str]:
    lines = [ln for ln in text.splitlines() if re.match(r".+:\d+:\d+: [A-Z]\d+", ln)]
    return ["\n".join(lines)] if lines else []


def extract_pre_commit_failures(text: str) -> list[str]:
    m = re.search(r"(Failed.*?)(?=\n-{10,}|\Z)", text, re.DOTALL)
    return [m.group(1).rstrip()] if m else []


def extract_error_lines(text: str) -> list[str]:
    """Catch-all: error: lines (mypy, tsc, build errors) with 3-line context."""
    lines = text.splitlines()
    error_re = re.compile(r"error:", re.IGNORECASE)
    hits = [i for i, ln in enumerate(lines) if error_re.search(ln)]
    if not hits:
        return []
    seen: set[int] = set()
    out: list[str] = []
    for i in hits:
        for j in range(max(0, i - 3), min(len(lines), i + 4)):
            if j not in seen:
                out.append(lines[j])
                seen.add(j)
    return ["\n".join(out)]


def fallback_tail(text: str) -> list[str]:
    lines = text.splitlines()
    return ["\n".join(lines[-FALLBACK_TAIL_LINES:])]


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: ai-filter-log.py <logfile>", file=sys.stderr)
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"log not found: {path}", file=sys.stderr)
        sys.exit(1)

    text = path.read_text(errors="replace")

    extractors = [
        extract_pytest_sections,
        extract_cargo_failures,
        extract_ruff_lines,
        extract_pre_commit_failures,
        extract_error_lines,
    ]

    found: list[str] = []
    for extractor in extractors:
        found.extend(extractor(text))

    if not found:
        found = fallback_tail(text)

    output = "\n\n".join(found)
    output_lines = output.splitlines()
    if len(output_lines) > MAX_OUTPUT_LINES:
        output_lines = output_lines[:MAX_OUTPUT_LINES]
        output_lines.append(f"... (truncated to {MAX_OUTPUT_LINES} lines; see full log)")

    print("\n".join(output_lines))


if __name__ == "__main__":
    main()
```

Save to `pdomain-book-tools/scripts/ai-filter-log.py`.

- [ ] **Step 4: Test against pytest failure log — verify only failures are extracted**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
uv run scripts/ai-filter-log.py /tmp/test-ci-fail.log
```

Expected output contains the `=== FAILURES ===` block and `=== short test summary info ===` block, but NOT the `PASSED` lines or `collected 10 items`.

- [ ] **Step 5: Test against a cargo failure log**

```bash
cat > /tmp/test-cargo-fail.log << 'EOF'
running 3 tests
test tests::test_ok ... ok
test tests::test_bad ... FAILED

failures:

---- tests::test_bad stdout ----
thread 'tests::test_bad' panicked at 'assertion failed: 1 == 2'

failures:
    tests::test_bad

test result: FAILED. 1 failed; 2 passed
EOF

uv run scripts/ai-filter-log.py /tmp/test-cargo-fail.log
```

Expected: shows only the `failures:` block, not the `running 3 tests` or `test_ok` lines.

- [ ] **Step 6: Test fallback with a plain build error log**

```bash
cat > /tmp/test-build-fail.log << 'EOF'
Compiling pd_foo v0.1.0
   Compiling pd_bar v0.1.0
src/lib.rs:10:5: error: cannot find value `x` in this scope
   Compiling pd_baz v0.1.0
EOF

uv run scripts/ai-filter-log.py /tmp/test-build-fail.log
```

Expected: shows the `error:` line plus 3 lines of context around it.

- [ ] **Step 7: Test fallback tail (log with no recognisable patterns)**

```bash
cat > /tmp/test-unknown-fail.log << 'EOF'
$(python3 -c "print('\n'.join(f'line {i}' for i in range(1, 80)))")
EOF
# Easier: just use printf
printf '%s\n' $(seq 1 80 | xargs -I{} echo "line {}") > /tmp/test-unknown-fail.log
uv run scripts/ai-filter-log.py /tmp/test-unknown-fail.log
```

Expected: last 50 lines of the log (lines 31–80).

- [ ] **Step 8: Commit the script in pdomain-book-tools**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
git add scripts/ai-filter-log.py
git commit -m "feat: add ai-filter-log.py — extract failure sections from CI log"
```

---

## Task 2: Apply AI=1 wrapper to `pdomain-book-tools`

**Files:**
- Modify: `pdomain-book-tools/Makefile` (prepend AI block, append endif)
- Modify: `pdomain-book-tools/.gitignore` (add `.ci-ai.log`)

- [ ] **Step 1: Prepend the AI block to the Makefile**

The current first line is `.PHONY: install setup ...`. Add these lines BEFORE it:

```makefile
AI ?=
LOG := .ci-ai.log

ifdef AI
_goals := $(or $(MAKECMDGOALS),ci)
.PHONY: $(_goals)
$(_goals):
	@rm -f $(LOG)
	@$(MAKE) --no-print-directory AI= $@ > $(LOG) 2>&1 \
		&& echo "✅ $@ passed (log: $(LOG))" \
		|| (echo "❌ $@ failed:"; uv run scripts/ai-filter-log.py $(LOG); echo "(full log: $(LOG))"; exit 1)

else
```

Use the Edit tool: `old_string` = the current first line (`.PHONY: install setup ...`), `new_string` = the block above followed by the current first line.

- [ ] **Step 2: Append `endif` to the Makefile**

Add to the very end of the file (after the last line):

```makefile

endif
```

Use the Edit tool: `old_string` = the current last line of the file, `new_string` = that line + `\n\nendif`.

- [ ] **Step 3: Add `.ci-ai.log` to `.gitignore`**

Find the section in `.gitignore` that has other generated/temp file entries and add:
```
.ci-ai.log
```

- [ ] **Step 4: Smoke test — dry run verifies Makefile parses**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
make -n ci AI=1 2>&1 | head -5
```

Expected: output shows something like `rm -f .ci-ai.log` and a recursive make call. No `Makefile:N: *** missing separator` errors.

- [ ] **Step 5: Smoke test — fast target through the AI wrapper**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
make help AI=1
```

Expected: `✅ help passed (log: .ci-ai.log)` and `.ci-ai.log` created containing the help output.

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/pdomain-book-tools
git add Makefile .gitignore
git commit -m "feat: add AI=1 make output capture"
```

---

## Task 3: Apply AI=1 wrapper to `pdomain-ocr-cli`

**Files:**
- Modify: `pdomain-ocr-cli/Makefile`
- Modify: `pdomain-ocr-cli/.gitignore`
- Create: `pdomain-ocr-cli/scripts/ai-filter-log.py`

- [ ] **Step 1: Copy the filter script**

```bash
cp /workspaces/ocr-container/pdomain-book-tools/scripts/ai-filter-log.py \
   /workspaces/ocr-container/pdomain-ocr-cli/scripts/ai-filter-log.py
```

- [ ] **Step 2: Prepend the AI block to the Makefile**

Current first line: `.PHONY: setup refresh-version install ...`

Add before it:

```makefile
AI ?=
LOG := .ci-ai.log

ifdef AI
_goals := $(or $(MAKECMDGOALS),ci)
.PHONY: $(_goals)
$(_goals):
	@rm -f $(LOG)
	@$(MAKE) --no-print-directory AI= $@ > $(LOG) 2>&1 \
		&& echo "✅ $@ passed (log: $(LOG))" \
		|| (echo "❌ $@ failed:"; uv run scripts/ai-filter-log.py $(LOG); echo "(full log: $(LOG))"; exit 1)

else
```

- [ ] **Step 3: Append `endif` to the Makefile**

Add to end of file:
```makefile

endif
```

- [ ] **Step 4: Add `.ci-ai.log` to `.gitignore`**

```
.ci-ai.log
```

- [ ] **Step 5: Smoke test**

```bash
cd /workspaces/ocr-container/pdomain-ocr-cli
make -n ci AI=1 2>&1 | head -5
make help AI=1
```

Expected: no parse errors; `✅ help passed (log: .ci-ai.log)`.

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-cli
git add Makefile .gitignore scripts/ai-filter-log.py
git commit -m "feat: add AI=1 make output capture"
```

---

## Task 4: Apply AI=1 wrapper to `pd-ocr-labeler`

**Files:**
- Modify: `pd-ocr-labeler/Makefile`
- Modify: `pd-ocr-labeler/.gitignore`
- Create: `pd-ocr-labeler/scripts/` (new dir) + `pd-ocr-labeler/scripts/ai-filter-log.py`

- [ ] **Step 1: Create scripts/ dir and copy filter script**

```bash
mkdir -p /workspaces/ocr-container/pd-ocr-labeler/scripts
cp /workspaces/ocr-container/pdomain-book-tools/scripts/ai-filter-log.py \
   /workspaces/ocr-container/pd-ocr-labeler/scripts/ai-filter-log.py
```

- [ ] **Step 2: Prepend the AI block to the Makefile**

Current first line starts: `.PHONY: help setup install ...`

Add before it:

```makefile
AI ?=
LOG := .ci-ai.log

ifdef AI
_goals := $(or $(MAKECMDGOALS),ci)
.PHONY: $(_goals)
$(_goals):
	@rm -f $(LOG)
	@$(MAKE) --no-print-directory AI= $@ > $(LOG) 2>&1 \
		&& echo "✅ $@ passed (log: $(LOG))" \
		|| (echo "❌ $@ failed:"; uv run scripts/ai-filter-log.py $(LOG); echo "(full log: $(LOG))"; exit 1)

else
```

- [ ] **Step 3: Append `endif` to the Makefile**

```makefile

endif
```

- [ ] **Step 4: Add `.ci-ai.log` to `.gitignore`**

```
.ci-ai.log
```

- [ ] **Step 5: Smoke test**

```bash
cd /workspaces/ocr-container/pd-ocr-labeler
make -n ci AI=1 2>&1 | head -5
make help AI=1
```

Expected: no parse errors; `✅ help passed (log: .ci-ai.log)`.

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/pd-ocr-labeler
git add Makefile .gitignore scripts/ai-filter-log.py
git commit -m "feat: add AI=1 make output capture"
```

---

## Task 5: Apply AI=1 wrapper to `pdomain-ocr-labeler-spa`

**Files:**
- Modify: `pdomain-ocr-labeler-spa/Makefile`
- Modify: `pdomain-ocr-labeler-spa/.gitignore`
- Create: `pdomain-ocr-labeler-spa/scripts/ai-filter-log.py`

- [ ] **Step 1: Copy the filter script**

```bash
cp /workspaces/ocr-container/pdomain-book-tools/scripts/ai-filter-log.py \
   /workspaces/ocr-container/pdomain-ocr-labeler-spa/scripts/ai-filter-log.py
```

- [ ] **Step 2: Prepend the AI block to the Makefile**

Current first line starts: `.PHONY: help setup refresh-version ...`

Add before it:

```makefile
AI ?=
LOG := .ci-ai.log

ifdef AI
_goals := $(or $(MAKECMDGOALS),ci)
.PHONY: $(_goals)
$(_goals):
	@rm -f $(LOG)
	@$(MAKE) --no-print-directory AI= $@ > $(LOG) 2>&1 \
		&& echo "✅ $@ passed (log: $(LOG))" \
		|| (echo "❌ $@ failed:"; uv run scripts/ai-filter-log.py $(LOG); echo "(full log: $(LOG))"; exit 1)

else
```

- [ ] **Step 3: Append `endif` to the Makefile**

```makefile

endif
```

- [ ] **Step 4: Add `.ci-ai.log` to `.gitignore`**

```
.ci-ai.log
```

- [ ] **Step 5: Smoke test**

```bash
cd /workspaces/ocr-container/pdomain-ocr-labeler-spa
make -n ci AI=1 2>&1 | head -5
make help AI=1
```

Expected: no parse errors; `✅ help passed (log: .ci-ai.log)`.

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-labeler-spa
git add Makefile .gitignore scripts/ai-filter-log.py
git commit -m "feat: add AI=1 make output capture"
```

---

## Task 6: Apply AI=1 wrapper to `pdomain-ocr-synth`

**Files:**
- Modify: `pdomain-ocr-synth/Makefile`
- Modify: `pdomain-ocr-synth/.gitignore`
- Create: `pdomain-ocr-synth/scripts/ai-filter-log.py`

- [ ] **Step 1: Copy the filter script**

```bash
cp /workspaces/ocr-container/pdomain-book-tools/scripts/ai-filter-log.py \
   /workspaces/ocr-container/pdomain-ocr-synth/scripts/ai-filter-log.py
```

- [ ] **Step 2: Prepend the AI block to the Makefile**

Current first line starts: `.PHONY: setup install uninstall ...`

Add before it:

```makefile
AI ?=
LOG := .ci-ai.log

ifdef AI
_goals := $(or $(MAKECMDGOALS),ci)
.PHONY: $(_goals)
$(_goals):
	@rm -f $(LOG)
	@$(MAKE) --no-print-directory AI= $@ > $(LOG) 2>&1 \
		&& echo "✅ $@ passed (log: $(LOG))" \
		|| (echo "❌ $@ failed:"; uv run scripts/ai-filter-log.py $(LOG); echo "(full log: $(LOG))"; exit 1)

else
```

- [ ] **Step 3: Append `endif` to the Makefile**

```makefile

endif
```

- [ ] **Step 4: Add `.ci-ai.log` to `.gitignore`**

```
.ci-ai.log
```

- [ ] **Step 5: Smoke test**

```bash
cd /workspaces/ocr-container/pdomain-ocr-synth
make -n ci AI=1 2>&1 | head -5
make help AI=1
```

Expected: no parse errors; `✅ help passed (log: .ci-ai.log)`.

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-synth
git add Makefile .gitignore scripts/ai-filter-log.py
git commit -m "feat: add AI=1 make output capture"
```

---

## Task 7: Apply AI=1 wrapper to `pd-ocr-trainer`

**Files:**
- Modify: `pd-ocr-trainer/Makefile`
- Modify: `pd-ocr-trainer/.gitignore`
- Create: `pd-ocr-trainer/scripts/` (new dir) + `pd-ocr-trainer/scripts/ai-filter-log.py`

- [ ] **Step 1: Create scripts/ dir and copy filter script**

```bash
mkdir -p /workspaces/ocr-container/pd-ocr-trainer/scripts
cp /workspaces/ocr-container/pdomain-book-tools/scripts/ai-filter-log.py \
   /workspaces/ocr-container/pd-ocr-trainer/scripts/ai-filter-log.py
```

- [ ] **Step 2: Prepend the AI block to the Makefile**

Current first line starts: `.PHONY: install setup reset ...`

Add before it:

```makefile
AI ?=
LOG := .ci-ai.log

ifdef AI
_goals := $(or $(MAKECMDGOALS),ci)
.PHONY: $(_goals)
$(_goals):
	@rm -f $(LOG)
	@$(MAKE) --no-print-directory AI= $@ > $(LOG) 2>&1 \
		&& echo "✅ $@ passed (log: $(LOG))" \
		|| (echo "❌ $@ failed:"; uv run scripts/ai-filter-log.py $(LOG); echo "(full log: $(LOG))"; exit 1)

else
```

- [ ] **Step 3: Append `endif` to the Makefile**

```makefile

endif
```

- [ ] **Step 4: Add `.ci-ai.log` to `.gitignore`**

```
.ci-ai.log
```

- [ ] **Step 5: Smoke test**

```bash
cd /workspaces/ocr-container/pd-ocr-trainer
make -n ci AI=1 2>&1 | head -5
make help AI=1
```

Expected: no parse errors; `✅ help passed (log: .ci-ai.log)`.

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/pd-ocr-trainer
git add Makefile .gitignore scripts/ai-filter-log.py
git commit -m "feat: add AI=1 make output capture"
```

---

## Task 8: Apply AI=1 wrapper to `pd-png-optimizer`

**Files:**
- Modify: `pd-png-optimizer/Makefile`
- Modify: `pd-png-optimizer/.gitignore`
- Create: `pd-png-optimizer/scripts/` (new dir) + `pd-png-optimizer/scripts/ai-filter-log.py`

- [ ] **Step 1: Create scripts/ dir and copy filter script**

```bash
mkdir -p /workspaces/ocr-container/pd-png-optimizer/scripts
cp /workspaces/ocr-container/pdomain-book-tools/scripts/ai-filter-log.py \
   /workspaces/ocr-container/pd-png-optimizer/scripts/ai-filter-log.py
```

- [ ] **Step 2: Prepend the AI block to the Makefile**

Current first line starts: `.PHONY: help setup-rust install ...`

Add before it:

```makefile
AI ?=
LOG := .ci-ai.log

ifdef AI
_goals := $(or $(MAKECMDGOALS),ci)
.PHONY: $(_goals)
$(_goals):
	@rm -f $(LOG)
	@$(MAKE) --no-print-directory AI= $@ > $(LOG) 2>&1 \
		&& echo "✅ $@ passed (log: $(LOG))" \
		|| (echo "❌ $@ failed:"; uv run scripts/ai-filter-log.py $(LOG); echo "(full log: $(LOG))"; exit 1)

else
```

- [ ] **Step 3: Append `endif` to the Makefile**

```makefile

endif
```

- [ ] **Step 4: Add `.ci-ai.log` to `.gitignore`**

```
.ci-ai.log
```

- [ ] **Step 5: Smoke test**

```bash
cd /workspaces/ocr-container/pd-png-optimizer
make -n ci AI=1 2>&1 | head -5
make help AI=1
```

Expected: no parse errors; `✅ help passed (log: .ci-ai.log)`.

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/pd-png-optimizer
git add Makefile .gitignore scripts/ai-filter-log.py
git commit -m "feat: add AI=1 make output capture"
```

---

## Task 9: Apply AI=1 wrapper to `pdomain-prep-for-pgdp`

**Files:**
- Modify: `pdomain-prep-for-pgdp/Makefile`
- Modify: `pdomain-prep-for-pgdp/.gitignore`
- Create: `pdomain-prep-for-pgdp/scripts/ai-filter-log.py`

- [ ] **Step 1: Copy the filter script**

```bash
cp /workspaces/ocr-container/pdomain-book-tools/scripts/ai-filter-log.py \
   /workspaces/ocr-container/pdomain-prep-for-pgdp/scripts/ai-filter-log.py
```

- [ ] **Step 2: Prepend the AI block to the Makefile**

Current first line starts: `.PHONY: help setup refresh-version install ...`

Add before it:

```makefile
AI ?=
LOG := .ci-ai.log

ifdef AI
_goals := $(or $(MAKECMDGOALS),ci)
.PHONY: $(_goals)
$(_goals):
	@rm -f $(LOG)
	@$(MAKE) --no-print-directory AI= $@ > $(LOG) 2>&1 \
		&& echo "✅ $@ passed (log: $(LOG))" \
		|| (echo "❌ $@ failed:"; uv run scripts/ai-filter-log.py $(LOG); echo "(full log: $(LOG))"; exit 1)

else
```

- [ ] **Step 3: Append `endif` to the Makefile**

```makefile

endif
```

- [ ] **Step 4: Add `.ci-ai.log` to `.gitignore`**

```
.ci-ai.log
```

- [ ] **Step 5: Smoke test**

```bash
cd /workspaces/ocr-container/pdomain-prep-for-pgdp
make -n ci AI=1 2>&1 | head -5
make help AI=1
```

Expected: no parse errors; `✅ help passed (log: .ci-ai.log)`.

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/pdomain-prep-for-pgdp
git add Makefile .gitignore scripts/ai-filter-log.py
git commit -m "feat: add AI=1 make output capture"
```

---

## Self-review notes

- All 8 repos covered ✓
- 3 repos that need `scripts/` created (pd-ocr-labeler, pd-ocr-trainer, pd-png-optimizer) have `mkdir -p` in their tasks ✓
- Filter script tested against pytest, cargo, build-error, and unknown-pattern logs ✓
- Smoke test in every task verifies both Makefile parsing (`make -n`) and end-to-end wrapper (`make help AI=1`) ✓
- `AI=` explicitly cleared in recursive call to prevent double-log-write ✓
- Script uses `uv run` per workspace convention ✓
- `.ci-ai.log` added to `.gitignore` in every repo ✓
