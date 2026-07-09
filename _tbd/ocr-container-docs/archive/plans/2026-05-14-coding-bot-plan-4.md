---
status: complete
---

# coding-bot Plan 4: Helpers + Hooks (M4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port all workspace Python/bash helper scripts into `coding_bot.helpers.*` modules, add the `coding-bot hook` namespace, and wire all remaining CLI subcommands (`setup`, `budget`, `agents`, additional `db` commands).

**Architecture:** Fourteen helper modules under `src/coding_bot/helpers/`, four hook entry points under `src/coding_bot/hooks/`, and new CLI sub-apps (`hook`, `budget`, `agents`) + additional `db` and top-level commands. Each helper is both an importable module (for workflows) and a CLI subcommand (for humans and pre-commit).

**Tech Stack:** Python, Typer, Rich, `coding_bot.gh`, `coding_bot.git`, SQLAlchemy.

**Reference spec:** `docs/superpowers/specs/2026-05-14-coding-bot-design.md` sections 13 (helpers + hooks) and 6.5 (db retention commands).

---

## File structure after Plan 4

```
src/coding_bot/
├── helpers/
│   ├── __init__.py               # exists (empty)
│   ├── ci_check.py               # exists ✓
│   ├── spec_plan.py              # exists ✓
│   ├── spec_lint.py              # NEW — port lint-spec.py
│   ├── spec_index.py             # NEW — port build-spec-index.py
│   ├── spec_chain.py             # NEW — port build-spec-chain-report.py + spec_chain_data.py + spec_slug.py
│   ├── label_lint.py             # NEW — port lint-issue-labels.py
│   ├── label_seed.py             # NEW — port seed-labels.sh (bash→Python)
│   ├── label_arm.py              # NEW — port arm-issue.py
│   ├── conventions.py            # NEW — port extract/sync/lint/check-drift/check-sibling-drift
│   ├── triage.py                 # NEW — port triage-sweep.py + triage-fork.py
│   ├── wip_pr.py                 # NEW — port pr-wip-status.sh + auto-merge-wip-prs.sh + merge-wip-ship-issue-pr.sh
│   ├── bot_workspace.py          # NEW — port bot-workspace-bootstrap.sh (bash→Python)
│   ├── protections.py            # NEW — port verify-protections.sh (bash→Python)
│   └── patches.py                # NEW — apply_with_revert (from style-review-apply.py)
├── hooks/
│   ├── __init__.py               # NEW (empty)
│   ├── trailing_todos.py         # NEW — port no-trailing-todos.sh (bash→Python)
│   ├── spec_lint.py              # NEW — thin wrapper calling helpers.spec_lint
│   ├── conventions_lint.py       # NEW — thin wrapper calling helpers.conventions
│   └── issue_labels_lint.py      # NEW — thin wrapper calling helpers.label_lint
└── cli.py                        # MODIFIED — mount hook/budget/agents apps, additional db/setup commands

tests/unit/
├── helpers/
│   ├── __init__.py               # NEW
│   ├── test_spec_lint.py         # NEW
│   ├── test_spec_index.py        # NEW
│   ├── test_spec_chain.py        # NEW
│   ├── test_label_lint.py        # NEW
│   ├── test_label_seed.py        # NEW
│   ├── test_label_arm.py         # NEW
│   ├── test_conventions.py       # NEW
│   ├── test_triage.py            # NEW
│   ├── test_wip_pr.py            # NEW
│   ├── test_bot_workspace.py     # NEW
│   ├── test_protections.py       # NEW
│   └── test_patches.py           # NEW
└── hooks/
    ├── __init__.py               # NEW
    └── test_trailing_todos.py    # NEW
```

---

## Phase A — Spec helpers

### Task A.1: `helpers/spec_lint.py`

Port `scripts/lint-spec.py` as an importable module. Public API:
- `lint_file(path, *, no_legacy=False) -> list[LintError]`
- `parse_specrc(specs_dir) -> dict`
- `LintError` dataclass

**Files:**
- Create: `src/coding_bot/helpers/spec_lint.py`
- Create: `tests/unit/helpers/__init__.py`
- Create: `tests/unit/helpers/test_spec_lint.py`

- [ ] **Step 1: Write the failing tests**

`tests/unit/helpers/test_spec_lint.py`:

```python
from __future__ import annotations
import textwrap
from pathlib import Path
import pytest
from coding_bot.helpers.spec_lint import lint_file, parse_specrc, LintError

VALID_SPEC = textwrap.dedent("""\
    # My spec

    > **Status**: Draft

    > **Last updated**: 2026-05-14

    ## TL;DR
    Short summary.

    ## Context
    Context here.

    ## Constraints
    Constraints here.

    ## Decision
    Decision here.

    ## Contract / Acceptance
    Acceptance here.

    ## Trade-offs considered
    Trade-offs here.

    ## Consequences
    Consequences here.

    ## Open questions
    None.

    ## References
    None.
""")

MISSING_HEADING_SPEC = textwrap.dedent("""\
    # My spec

    > **Status**: Draft

    > **Last updated**: 2026-05-14

    ## TL;DR
    Short.

    ## Context
    ctx.
""")


def test_valid_spec_no_errors(tmp_path: Path) -> None:
    f = tmp_path / "test.md"
    f.write_text(VALID_SPEC)
    errors = lint_file(f)
    assert errors == []


def test_missing_headings_reported(tmp_path: Path) -> None:
    f = tmp_path / "test.md"
    f.write_text(MISSING_HEADING_SPEC)
    errors = lint_file(f)
    assert any("Constraints" in e.message for e in errors)


def test_parse_specrc_empty(tmp_path: Path) -> None:
    cfg = parse_specrc(tmp_path)
    assert cfg["legacy"] == []
    assert cfg["cap_lines"] == {}


def test_parse_specrc_legacy(tmp_path: Path) -> None:
    rc = tmp_path / ".specrc"
    rc.write_text("legacy:\n- old-spec.md\n- another.md\n")
    cfg = parse_specrc(tmp_path)
    assert "old-spec.md" in cfg["legacy"]


def test_file_too_long(tmp_path: Path) -> None:
    long_spec = VALID_SPEC + "\n".join(["line"] * 900)
    f = tmp_path / "big.md"
    f.write_text(long_spec)
    errors = lint_file(f)
    assert any("too long" in e.message.lower() or "exceeds" in e.message.lower() for e in errors)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_spec_lint.py -x 2>&1 | tail -5
```

Expected: `ImportError` or `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/coding_bot/helpers/spec_lint.py`**

```python
"""spec_lint — validate spec files against the 9-section template.

Ported from scripts/lint-spec.py. Importable; no argparse side effects.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REQUIRED_HEADINGS = [
    "TL;DR",
    "Context",
    "Constraints",
    "Decision",
    "Contract / Acceptance",
    "Trade-offs considered",
    "Consequences",
    "Open questions",
    "References",
]
DEFAULT_CAP_LINES = 800


@dataclass
class LintError:
    path: Path
    line: int
    message: str
    level: str = "error"  # "error" | "warning"


def parse_specrc(specs_dir: Path) -> dict:
    """Parse .specrc from specs_dir. Returns {"legacy": [...], "cap_lines": {}}."""
    rc = specs_dir / ".specrc"
    if not rc.exists():
        return {"legacy": [], "cap_lines": {}}
    legacy: list[str] = []
    cap_lines: dict[str, int] = {}
    section = None
    for line in rc.read_text().splitlines():
        stripped = line.strip()
        if stripped == "legacy:":
            section = "legacy"
            continue
        if stripped == "cap_lines:":
            section = "cap_lines"
            continue
        if section == "legacy" and stripped.startswith("- "):
            legacy.append(stripped[2:])
        elif section == "cap_lines" and ":" in stripped:
            k, v = stripped.split(":", 1)
            try:
                cap_lines[k.strip()] = int(v.strip())
            except ValueError:
                pass
    return {"legacy": legacy, "cap_lines": cap_lines}


def lint_file(path: Path, *, no_legacy: bool = False) -> list[LintError]:
    """Lint a single spec file. Returns list of LintError (empty = clean)."""
    errors: list[LintError] = []
    text = path.read_text(errors="replace")
    lines = text.splitlines()

    # Resolve .specrc relative to the file's parent or grandparent docs/specs dir
    specs_dir = path.parent
    specrc = parse_specrc(specs_dir)
    is_legacy = (not no_legacy) and (path.name in specrc["legacy"])

    # 1. Required headings (skip for legacy files)
    if not is_legacy:
        found_headings = set(re.findall(r"^##\s+(.+)$", text, re.MULTILINE))
        for heading in REQUIRED_HEADINGS:
            if heading not in found_headings:
                errors.append(LintError(path, 0, f"Missing required heading: ## {heading}"))

    # 2. Status blockquote
    if not re.search(r"^>\s*\*\*Status\*\*:", text, re.MULTILINE):
        errors.append(LintError(path, 0, "Missing > **Status**: blockquote"))

    # 3. Last updated date
    if not re.search(r"^>\s*\*\*Last updated\*\*:", text, re.MULTILINE):
        errors.append(LintError(path, 0, "Missing > **Last updated**: date", level="warning"))

    # 4. File length cap
    cap = specrc["cap_lines"].get(path.name, DEFAULT_CAP_LINES)
    if len(lines) > cap:
        errors.append(LintError(
            path, len(lines),
            f"File exceeds {cap}-line cap ({len(lines)} lines)",
        ))

    # 5. TL;DR length (warn-only, ≤6 lines)
    tldr = re.search(r"^##\s*TL;DR\s*\n(.*?)(?=\n##|\Z)", text, re.MULTILINE | re.DOTALL)
    if tldr:
        tldr_lines = [l for l in tldr.group(1).splitlines() if l.strip()]
        if len(tldr_lines) > 6:
            errors.append(LintError(path, 0, "TL;DR exceeds 6 lines", level="warning"))

    return errors
```

- [ ] **Step 4: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_spec_lint.py -v 2>&1 | tail -12
```

Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container/coding-bot
git add src/coding_bot/helpers/spec_lint.py tests/unit/helpers/
git commit -m "feat(helpers): add spec_lint module"
```

---

### Task A.2: `helpers/spec_index.py` and `helpers/spec_chain.py`

Port `build-spec-index.py` (HTML index) and consolidate `build-spec-chain-report.py` + `spec_chain_data.py` + `spec_slug.py` into one module.

**Files:**
- Create: `src/coding_bot/helpers/spec_index.py`
- Create: `src/coding_bot/helpers/spec_chain.py`
- Create: `tests/unit/helpers/test_spec_index.py`
- Create: `tests/unit/helpers/test_spec_chain.py`

- [ ] **Step 1: Write tests**

`tests/unit/helpers/test_spec_index.py`:

```python
from __future__ import annotations
import textwrap
from pathlib import Path
from coding_bot.helpers.spec_index import build_html, parse_spec_meta


SAMPLE_SPEC = textwrap.dedent("""\
    # Test spec

    > **Status**: Active

    ## TL;DR
    This is the summary.

    ## Context
    Context here.
""")


def test_parse_spec_meta(tmp_path: Path) -> None:
    f = tmp_path / "spec.md"
    f.write_text(SAMPLE_SPEC)
    meta = parse_spec_meta(f)
    assert meta["status"] == "Active"
    assert "summary" in meta["tldr"].lower()


def test_build_html_produces_table(tmp_path: Path) -> None:
    spec_dir = tmp_path / "pd-test" / "docs" / "specs"
    spec_dir.mkdir(parents=True)
    (spec_dir / "2026-05-01-foo.md").write_text(SAMPLE_SPEC)
    html = build_html(workspace=tmp_path)
    assert "<table" in html
    assert "2026-05-01-foo.md" in html


def test_build_html_empty_workspace(tmp_path: Path) -> None:
    html = build_html(workspace=tmp_path)
    assert "0 specs" in html
```

`tests/unit/helpers/test_spec_chain.py`:

```python
from __future__ import annotations
from coding_bot.helpers.spec_chain import derive_slug, milestone_title


def test_derive_slug_basic() -> None:
    assert derive_slug("Add foobar feature") == "add-foobar-feature"


def test_derive_slug_strips_kind_prefix() -> None:
    assert derive_slug("[spec] My spec title") == "my-spec-title"
    assert derive_slug("spec: My spec title") == "my-spec-title"


def test_derive_slug_truncates_at_40() -> None:
    long = "a" * 50
    result = derive_slug(long)
    assert len(result) <= 40


def test_derive_slug_empty() -> None:
    assert derive_slug("") == "unnamed"


def test_milestone_title() -> None:
    t = milestone_title("Add foobar feature", 42)
    assert t == "spec: add-foobar-feature (#42)"
```

- [ ] **Step 2: Verify failures**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_spec_index.py tests/unit/helpers/test_spec_chain.py -x 2>&1 | tail -5
```

- [ ] **Step 3: Implement `src/coding_bot/helpers/spec_index.py`**

```python
"""spec_index — workspace-level HTML spec index. Ported from build-spec-index.py."""
from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent

WORKSPACE = Path("/workspaces/ocr-container")


def parse_spec_meta(path: Path) -> dict:
    content = path.read_text(errors="replace")
    status_m = re.search(r"^>\s*\*\*Status\*\*:\s*(\S.*?)\s*$", content, re.MULTILINE)
    tldr_m = re.search(r"^##\s*TL;DR\s*\n(.*?)(?=\n##|\Z)", content, re.MULTILINE | re.DOTALL)
    return {
        "status": status_m.group(1) if status_m else "(no status)",
        "tldr": (tldr_m.group(1).strip()[:200] if tldr_m else ""),
    }


def build_html(*, workspace: Path = WORKSPACE) -> str:
    rows: list[tuple[str, str, str]] = []
    for spec_dir in sorted(workspace.glob("pd-*/docs/specs")):
        for spec in sorted(spec_dir.glob("*.md")):
            if spec.name.startswith("_"):
                continue
            try:
                meta = parse_spec_meta(spec)
            except Exception:
                continue
            rel = str(spec.relative_to(workspace))
            rows.append((rel, meta["status"], meta["tldr"]))

    row_html = "\n".join(
        f"<tr><td>{p}</td><td class='{s.split()[0] if s else ''}'>{s}</td><td>{t}</td></tr>"
        for p, s, t in rows
    )
    return dedent(f"""\
        <!DOCTYPE html><html><head><meta charset="UTF-8"><title>Spec index</title>
        <style>body{{font-family:sans-serif;max-width:1200px;margin:2em auto}}
        table{{border-collapse:collapse;width:100%}}
        th,td{{padding:6px 10px;border-bottom:1px solid #eee}}th{{background:#f0f0f0}}
        .Active{{color:#2a7;font-weight:600}}.Draft{{color:#888}}.Locked{{color:#28b}}
        </style></head><body>
        <h1>Spec index ({len(rows)} specs)</h1>
        <table><tr><th>Path</th><th>Status</th><th>TL;DR</th></tr>
        {row_html}
        </table></body></html>""")
```

- [ ] **Step 4: Implement `src/coding_bot/helpers/spec_chain.py`**

```python
"""spec_chain — slug helpers and spec-chain report. Consolidates spec_slug.py + spec_chain_data.py + build-spec-chain-report.py."""
from __future__ import annotations

import re
from pathlib import Path

_KIND_MARKER = re.compile(
    r"^(?:\[(spec|chore|feature|bug)\]|(spec|chore|feature|bug):)\s*",
    re.IGNORECASE,
)
_NON_SLUG = re.compile(r"[^a-z0-9]+")
_MAX_LEN = 40


def derive_slug(title: str) -> str:
    """Deterministic slug for a spec/issue title."""
    s = title.lower().strip()
    s = _KIND_MARKER.sub("", s)
    s = _NON_SLUG.sub("-", s)
    s = s.strip("-")
    s = s[:_MAX_LEN]
    if len(s) == _MAX_LEN:
        last_dash = s.rfind("-")
        if last_dash > 0:
            s = s[:last_dash]
    s = s.strip("-")
    return s or "unnamed"


def milestone_title(issue_title: str, issue_number: int) -> str:
    """Canonical milestone title: 'spec: <slug> (#N)'."""
    return f"spec: {derive_slug(issue_title)} (#{issue_number})"


_TRACKS_RE = re.compile(r"^Tracks:\s*#(\d+)\s*$", re.MULTILINE)
_SPEC_FILE_RE = re.compile(r"^Spec:\s*docs/specs/.+\.md\s*$", re.MULTILINE)


def tracks_parent(body: str | None) -> int | None:
    if not body:
        return None
    m = _TRACKS_RE.search(body)
    return int(m.group(1)) if m else None


def has_spec_file_link(body: str | None) -> bool:
    return bool(body and _SPEC_FILE_RE.search(body))
```

- [ ] **Step 5: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_spec_index.py tests/unit/helpers/test_spec_chain.py -v 2>&1 | tail -12
```

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/coding-bot
git add src/coding_bot/helpers/spec_index.py src/coding_bot/helpers/spec_chain.py tests/unit/helpers/test_spec_index.py tests/unit/helpers/test_spec_chain.py
git commit -m "feat(helpers): add spec_index and spec_chain modules"
```

---

## Phase B — Label helpers

### Task B.1: `helpers/label_lint.py`

Port `scripts/lint-issue-labels.py`. Public API:
- `SINGLE_SELECT_FAMILIES` dict
- `find_violations(issue) -> list[dict]`
- `fix_violations(repo, issue_number, violations, *, dry_run, gh) -> int`

**Files:**
- Create: `src/coding_bot/helpers/label_lint.py`
- Create: `tests/unit/helpers/test_label_lint.py`

- [ ] **Step 1: Write tests**

`tests/unit/helpers/test_label_lint.py`:

```python
from __future__ import annotations
from coding_bot.helpers.label_lint import find_violations, SINGLE_SELECT_FAMILIES


def _make_issue(labels: list[str]) -> dict:
    return {"number": 1, "labels": [{"name": l} for l in labels]}


def test_no_violation_single_status() -> None:
    issue = _make_issue(["status:ready", "kind:feature"])
    assert find_violations(issue) == []


def test_dual_status_is_violation() -> None:
    issue = _make_issue(["status:ready", "status:in-progress"])
    violations = find_violations(issue)
    assert len(violations) == 1
    assert violations[0]["family"] == "status:*"
    assert set(violations[0]["labels"]) == {"status:ready", "status:in-progress"}


def test_dual_kind_is_violation() -> None:
    issue = _make_issue(["kind:bug", "kind:feature"])
    violations = find_violations(issue)
    assert any(v["family"] == "kind:*" for v in violations)


def test_triage_multi_label_ok() -> None:
    issue = _make_issue(["triage:approved", "triage:rejected"])
    # triage:* is intentionally excluded from single-select families
    assert find_violations(issue) == []


def test_families_defined() -> None:
    assert "status:*" in SINGLE_SELECT_FAMILIES
    assert "kind:*" in SINGLE_SELECT_FAMILIES
    assert "effort:*" in SINGLE_SELECT_FAMILIES
```

- [ ] **Step 2: Verify failures**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_label_lint.py -x 2>&1 | tail -5
```

- [ ] **Step 3: Implement `src/coding_bot/helpers/label_lint.py`**

```python
"""label_lint — detect and fix single-select label violations. Ported from lint-issue-labels.py."""
from __future__ import annotations

from typing import Any

SINGLE_SELECT_FAMILIES: dict[str, list[str]] = {
    "status:*": [
        "status:in-progress", "status:in-review", "status:ready",
        "status:blocked", "status:bounced", "status:backlog",
    ],
    "kind:*": [
        "kind:feature-request", "kind:spec", "kind:tracking",
        "kind:chore", "kind:bug", "kind:feature",
    ],
    "effort:*": ["effort:XL", "effort:L", "effort:M", "effort:S"],
    "model:*": ["model:opus", "model:sonnet", "model:haiku"],
    "model-effort:*": ["model-effort:high", "model-effort:medium", "model-effort:low"],
}

_LABEL_TO_FAMILY: dict[str, str] = {
    label: family
    for family, members in SINGLE_SELECT_FAMILIES.items()
    for label in members
}


def find_violations(issue: dict[str, Any]) -> list[dict[str, Any]]:
    """Return violation dicts for an issue. Each: {family, labels, needs_human_review}."""
    label_names = [lbl["name"] for lbl in issue.get("labels", [])]
    by_family: dict[str, list[str]] = {}
    for name in label_names:
        fam = _LABEL_TO_FAMILY.get(name)
        if fam:
            by_family.setdefault(fam, []).append(name)
    violations = []
    for family, present in by_family.items():
        if len(present) > 1:
            members = SINGLE_SELECT_FAMILIES[family]
            needs_review = any(l not in members for l in present)
            violations.append({
                "family": family,
                "labels": present,
                "needs_human_review": needs_review,
            })
    return violations


def resolve_winner(family: str, present_labels: list[str]) -> str:
    """Return the highest-priority label from the family's precedence list."""
    members = SINGLE_SELECT_FAMILIES.get(family, [])
    for member in members:
        if member in present_labels:
            return member
    return present_labels[0]
```

- [ ] **Step 4: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_label_lint.py -v 2>&1 | tail -10
```

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container/coding-bot
git add src/coding_bot/helpers/label_lint.py tests/unit/helpers/test_label_lint.py
git commit -m "feat(helpers): add label_lint module"
```

---

### Task B.2: `helpers/label_seed.py` and `helpers/label_arm.py`

Port `seed-labels.sh` (bash → Python) and `arm-issue.py`.

**Files:**
- Create: `src/coding_bot/helpers/label_seed.py`
- Create: `src/coding_bot/helpers/label_arm.py`
- Create: `tests/unit/helpers/test_label_seed.py`
- Create: `tests/unit/helpers/test_label_arm.py`

- [ ] **Step 1: Write tests**

`tests/unit/helpers/test_label_seed.py`:

```python
from __future__ import annotations
from unittest.mock import MagicMock, call
from coding_bot.helpers.label_seed import STANDARD_LABELS, seed_labels


def test_standard_labels_defined() -> None:
    assert len(STANDARD_LABELS) > 10
    names = [l["name"] for l in STANDARD_LABELS]
    assert "kind:feature" in names
    assert "status:ready" in names
    assert "bot:ship-issue-ready" in names


def test_seed_labels_calls_gh_for_each_label() -> None:
    fake_gh = MagicMock()
    fake_gh.label_create = MagicMock(return_value=None)
    fake_gh.label_list = MagicMock(return_value=[])
    created = seed_labels("org/repo", gh=fake_gh)
    assert created == len(STANDARD_LABELS)


def test_seed_labels_skips_existing() -> None:
    fake_gh = MagicMock()
    existing = [{"name": l["name"]} for l in STANDARD_LABELS]
    fake_gh.label_list = MagicMock(return_value=existing)
    created = seed_labels("org/repo", gh=fake_gh)
    assert created == 0
```

`tests/unit/helpers/test_label_arm.py`:

```python
from __future__ import annotations
from unittest.mock import MagicMock
from coding_bot.helpers.label_arm import arm_issue, ArmError, ArmResult


def _make_gh(issue_state="OPEN", issue_labels=None, pr_list=None):
    gh = MagicMock()
    gh.issue_view = MagicMock(return_value={
        "number": 10, "state": issue_state,
        "labels": [{"name": l} for l in (issue_labels or [])],
        "body": "Tracks: #5\n",
    })
    gh.pr_list = MagicMock(return_value=pr_list or [])
    gh.issue_edit = MagicMock(return_value=None)
    return gh


def test_arm_issue_already_armed() -> None:
    gh = _make_gh(issue_labels=["bot:ship-issue-ready", "status:ready"])
    result = arm_issue("org/repo", 10, gh=gh)
    assert result == ArmResult.ALREADY_ARMED
    gh.issue_edit.assert_not_called()


def test_arm_issue_not_open_raises() -> None:
    gh = _make_gh(issue_state="CLOSED")
    with pytest.raises(ArmError, match="not OPEN"):
        arm_issue("org/repo", 10, gh=gh)


def test_arm_issue_force_skips_gate() -> None:
    gh = _make_gh()
    result = arm_issue("org/repo", 10, gh=gh, force=True)
    assert result == ArmResult.ARMED
    gh.issue_edit.assert_called_once()


import pytest  # noqa: E402 — needed after function defs referencing it
```

- [ ] **Step 2: Verify failures**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_label_seed.py tests/unit/helpers/test_label_arm.py -x 2>&1 | tail -5
```

- [ ] **Step 3: Implement `src/coding_bot/helpers/label_seed.py`**

```python
"""label_seed — idempotently create the standard label set on a repo.

Ported from scripts/seed-labels.sh (bash → Python).
"""
from __future__ import annotations

from typing import Any, Protocol


class GhProtocol(Protocol):
    def label_list(self, repo: str) -> list[dict]: ...
    def label_create(self, repo: str, name: str, color: str, description: str) -> None: ...


STANDARD_LABELS: list[dict[str, str]] = [
    {"name": "kind:feature",          "color": "0e8a16", "description": "New slice of planned work"},
    {"name": "kind:bug",               "color": "d73a4a", "description": "Reproducible incorrect behavior"},
    {"name": "kind:spec",              "color": "c5def5", "description": "Design/decision needed before code"},
    {"name": "kind:feature-request",   "color": "c5def5", "description": "Idea pre-triage"},
    {"name": "kind:chore",             "color": "fef2c0", "description": "Deps, CI, refactor, doc cleanup"},
    {"name": "kind:tracking",          "color": "e4e669", "description": "Child tracking issue"},
    {"name": "effort:S",               "color": "c2e0c6", "description": "Small / mechanical"},
    {"name": "effort:M",               "color": "fbca04", "description": "Medium / standard"},
    {"name": "effort:L",               "color": "d93f0b", "description": "Large / architectural"},
    {"name": "effort:XL",              "color": "b60205", "description": "Very large"},
    {"name": "model:haiku",            "color": "fef2c0", "description": "Recommend Claude Haiku"},
    {"name": "model:sonnet",           "color": "fbca04", "description": "Recommend Claude Sonnet"},
    {"name": "model:opus",             "color": "d93f0b", "description": "Recommend Claude Opus"},
    {"name": "model-effort:low",       "color": "d4c5f9", "description": "effort=low"},
    {"name": "model-effort:medium",    "color": "c5def5", "description": "effort=medium"},
    {"name": "model-effort:high",      "color": "bfd4f2", "description": "effort=high"},
    {"name": "status:ready",           "color": "0e8a16", "description": "Armed for next bot cycle"},
    {"name": "status:in-progress",     "color": "fbca04", "description": "Bot is working on this"},
    {"name": "status:in-review",       "color": "006b75", "description": "PR open, awaiting review"},
    {"name": "status:blocked",         "color": "d93f0b", "description": "Waiting on dependency"},
    {"name": "status:bounced",         "color": "b60205", "description": "Bot failed; needs human"},
    {"name": "status:backlog",         "color": "e4e669", "description": "Not yet scheduled"},
    {"name": "bot:ship-issue-ready",   "color": "0052cc", "description": "Cleared for ship-issue bot"},
    {"name": "bot:merge-ready",        "color": "0e8a16", "description": "CT approved; merge when green"},
    {"name": "bot:paused",             "color": "e4e669", "description": "Bot skips this issue"},
    {"name": "triage:approved",        "color": "0e8a16", "description": "FR approved"},
    {"name": "triage:rejected",        "color": "d73a4a", "description": "FR rejected"},
    {"name": "backend:claude",         "color": "c5def5", "description": "Use Claude backend"},
    {"name": "backend:codex",          "color": "fef2c0", "description": "Use Codex backend"},
    {"name": "backend:grok",           "color": "e4e669", "description": "Use Grok backend"},
]


def seed_labels(repo: str, *, gh: Any) -> int:
    """Idempotently create STANDARD_LABELS on repo. Returns count of labels created."""
    existing = {l["name"] for l in gh.label_list(repo)}
    created = 0
    for label in STANDARD_LABELS:
        if label["name"] not in existing:
            gh.label_create(repo, label["name"], label["color"], label["description"])
            created += 1
    return created
```

- [ ] **Step 4: Implement `src/coding_bot/helpers/label_arm.py`**

```python
"""label_arm — arm a ship-issue issue after verifying the parent spec PR is merged.

Ported from scripts/arm-issue.py.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Any


class ArmResult(Enum):
    ARMED = "armed"
    ALREADY_ARMED = "already_armed"


class ArmError(RuntimeError):
    pass


_TRACKS_RE = re.compile(r"^Tracks:\s*#(\d+)", re.MULTILINE)


def arm_issue(
    repo: str,
    issue_number: int,
    *,
    gh: Any,
    force: bool = False,
    dry_run: bool = False,
) -> ArmResult:
    """Arm issue with bot:ship-issue-ready + status:ready.

    Gate: parent spec PR must be merged unless --force.
    Exit: ArmResult.ALREADY_ARMED if already armed; raises ArmError on gate refusal.
    """
    issue = gh.issue_view(repo, issue_number)

    if issue.get("state", "").upper() != "OPEN":
        raise ArmError(f"Issue #{issue_number} is not OPEN (state={issue.get('state')})")

    label_names = {l["name"] for l in issue.get("labels", [])}
    if "bot:ship-issue-ready" in label_names and "status:ready" in label_names:
        return ArmResult.ALREADY_ARMED

    if not force:
        body = issue.get("body") or ""
        m = _TRACKS_RE.search(body)
        if m:
            spec_num = int(m.group(1))
            _verify_spec_pr_merged(repo, spec_num, gh=gh)

    if not dry_run:
        add = []
        if "bot:ship-issue-ready" not in label_names:
            add.append("bot:ship-issue-ready")
        if "status:ready" not in label_names:
            add.append("status:ready")
        if add:
            gh.issue_edit(repo, issue_number, add_labels=add)

    return ArmResult.ARMED


def _verify_spec_pr_merged(repo: str, spec_issue: int, *, gh: Any) -> None:
    prs = gh.pr_list(repo, search=f"Closes #{spec_issue}", state="all")
    merged = [pr for pr in prs if pr.get("mergedAt")]
    if not merged:
        raise ArmError(
            f"Gate refused: no merged PR found that closes spec issue #{spec_issue}. "
            "Use --force to override."
        )
```

- [ ] **Step 5: Add `label_list` and `label_create` to `coding_bot/gh.py`**

Open `src/coding_bot/gh.py` and add after the existing functions:

```python
def label_list(repo: str) -> list[dict[str, Any]]:
    return json.loads(_run([
        "gh", "label", "list", "--repo", repo,
        "--json", "name,color,description", "--limit", "200",
    ]))


def label_create(repo: str, name: str, color: str, description: str) -> None:
    _run([
        "gh", "label", "create", name, "--repo", repo,
        "--color", color, "--description", description,
        "--force",
    ])


def pr_list(repo: str, search: str, state: str = "all") -> list[dict[str, Any]]:
    return json.loads(_run([
        "gh", "pr", "list", "--repo", repo,
        "--search", search, "--state", state,
        "--json", "number,state,title,headRefName,mergedAt",
    ]))
```

- [ ] **Step 6: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_label_seed.py tests/unit/helpers/test_label_arm.py -v 2>&1 | tail -12
```

- [ ] **Step 7: Commit**

```bash
cd /workspaces/ocr-container/coding-bot
git add src/coding_bot/helpers/label_seed.py src/coding_bot/helpers/label_arm.py tests/unit/helpers/test_label_seed.py tests/unit/helpers/test_label_arm.py src/coding_bot/gh.py
git commit -m "feat(helpers): add label_seed and label_arm modules"
```

---

## Phase C — Conventions helpers

### Task C.1: `helpers/conventions.py`

Consolidate `extract-conventions.py`, `sync-conventions.py`, `lint-conventions.py`, `check-sync-drift.py`, `check-sibling-drift.py` into one module with five functions.

**Files:**
- Create: `src/coding_bot/helpers/conventions.py`
- Create: `tests/unit/helpers/test_conventions.py`

- [ ] **Step 1: Write tests**

`tests/unit/helpers/test_conventions.py`:

```python
from __future__ import annotations
import textwrap
from pathlib import Path
from coding_bot.helpers.conventions import (
    lint_conventions_file,
    ConventionsLintError,
    check_sync_drift,
    RULE_HEADER_RE,
)


VALID_CONVENTIONS = textwrap.dedent("""\
    ## Rule: Always use uv run

    **The rule.** Use `uv run` not `python3` directly.

    **Why.** Ensures the managed venv is used.

    **Common high-confidence violations** (bot auto-fix candidates)
    - Direct `python3` calls

    **Common judgment-call violations** (bot flags, CT decides)
    - `./manage.py` style runners
""")

INVALID_CONVENTIONS = textwrap.dedent("""\
    ## Rule: Some rule

    Missing required sections.
""")


def test_valid_conventions_no_errors(tmp_path: Path) -> None:
    f = tmp_path / "CONVENTIONS.md"
    f.write_text(VALID_CONVENTIONS)
    errors = lint_conventions_file(f)
    assert errors == []


def test_missing_required_blocks(tmp_path: Path) -> None:
    f = tmp_path / "CONVENTIONS.md"
    f.write_text(INVALID_CONVENTIONS)
    errors = lint_conventions_file(f)
    assert len(errors) > 0
    assert any("The rule" in e.message for e in errors)


def test_rule_header_re() -> None:
    assert RULE_HEADER_RE.search("## Rule: Do not squash-merge")


def test_check_sync_drift_no_file(tmp_path: Path) -> None:
    # No CONVENTIONS.md → no drift to check
    drift = check_sync_drift(tmp_path / "CONVENTIONS.md", workspace_conventions=None)
    assert drift == []
```

- [ ] **Step 2: Verify failures**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_conventions.py -x 2>&1 | tail -5
```

- [ ] **Step 3: Implement `src/coding_bot/helpers/conventions.py`**

```python
"""conventions — CONVENTIONS.md lint, sync, and drift checks.

Consolidates extract-conventions.py, sync-conventions.py, lint-conventions.py,
check-sync-drift.py, check-sibling-drift.py.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

WORKSPACE = Path("/workspaces/ocr-container")
RULE_HEADER_RE = re.compile(r"^## Rule: ", re.MULTILINE)
_REQUIRED_BLOCKS = (
    re.compile(r"\*\*The rule\.\*\*"),
    re.compile(r"\*\*Why\.\*\*"),
    re.compile(r"\*\*Common high-confidence violations\*\*"),
    re.compile(r"\*\*Common judgment-call violations\*\*"),
)
_START_MARKER = "<!-- workspace-conventions:start -->"
_END_MARKER = "<!-- workspace-conventions:end -->"


@dataclass
class ConventionsLintError:
    path: Path
    message: str
    rule_heading: str = ""


def lint_conventions_file(path: Path) -> list[ConventionsLintError]:
    """Validate CONVENTIONS.md structure. Returns list of errors (empty = clean)."""
    if not path.exists():
        return []
    text = path.read_text(errors="replace")
    errors: list[ConventionsLintError] = []
    rule_sections = _split_by_rules(text)
    for heading, body in rule_sections:
        for pat in _REQUIRED_BLOCKS:
            if not pat.search(body):
                errors.append(ConventionsLintError(
                    path=path,
                    message=f"Missing '{pat.pattern}' block",
                    rule_heading=heading,
                ))
    return errors


def _split_by_rules(text: str) -> list[tuple[str, str]]:
    """Split conventions text into [(heading, body)] pairs per rule."""
    parts: list[tuple[str, str]] = []
    current_heading = ""
    current_body_lines: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^## Rule: (.+)$", line)
        if m:
            if current_heading:
                parts.append((current_heading, "\n".join(current_body_lines)))
            current_heading = m.group(1)
            current_body_lines = []
        else:
            current_body_lines.append(line)
    if current_heading:
        parts.append((current_heading, "\n".join(current_body_lines)))
    return parts


def check_sync_drift(
    repo_conventions: Path,
    *,
    workspace_conventions: Path | None,
) -> list[str]:
    """Return list of workspace rule headings not present in repo CONVENTIONS.md."""
    if workspace_conventions is None or not workspace_conventions.exists():
        return []
    if not repo_conventions.exists():
        return []
    workspace_rules = _extract_rule_headings(workspace_conventions.read_text())
    repo_rules = _extract_rule_headings(repo_conventions.read_text())
    in_block = _extract_sync_block(workspace_conventions.read_text())
    if not in_block:
        return []
    block_rules = _extract_rule_headings(in_block)
    return [r for r in block_rules if r not in repo_rules]


def _extract_rule_headings(text: str) -> set[str]:
    return set(re.findall(r"^## Rule: (.+)$", text, re.MULTILINE))


def _extract_sync_block(text: str) -> str:
    start = text.find(_START_MARKER)
    end = text.find(_END_MARKER)
    if start == -1 or end == -1:
        return ""
    return text[start + len(_START_MARKER):end]


def check_sibling_drift(repo: Path, workspace: Path = WORKSPACE) -> list[str]:
    """Return list of rule headings in workspace CONVENTIONS.md missing from this repo."""
    ws_conv = workspace / "CONVENTIONS.md"
    repo_conv = repo / "CONVENTIONS.md"
    return check_sync_drift(repo_conv, workspace_conventions=ws_conv)
```

- [ ] **Step 4: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_conventions.py -v 2>&1 | tail -10
```

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container/coding-bot
git add src/coding_bot/helpers/conventions.py tests/unit/helpers/test_conventions.py
git commit -m "feat(helpers): add conventions module"
```

---

## Phase D — Triage and wip-pr helpers

### Task D.1: `helpers/triage.py`

Port `triage-sweep.py` + `triage-fork.py`. Public API:
- `sweep(repo, *, gh) -> list[dict]`  — categorize open issues, return buckets
- `fork_child(repo, parent, kind, title, body, labels, *, gh, output, dry_run) -> int | None`

**Files:**
- Create: `src/coding_bot/helpers/triage.py`
- Create: `tests/unit/helpers/test_triage.py`

- [ ] **Step 1: Write tests**

`tests/unit/helpers/test_triage.py`:

```python
from __future__ import annotations
from unittest.mock import MagicMock
from coding_bot.helpers.triage import sweep, BUCKETS, categorize_issue


def _make_issue(number: int, labels: list[str], body: str = "") -> dict:
    return {
        "number": number,
        "title": f"Issue {number}",
        "body": body,
        "labels": [{"name": l} for l in labels],
        "state": "OPEN",
    }


def test_buckets_defined() -> None:
    assert "untriaged-fr" in BUCKETS
    assert "bot-ready-armed" in BUCKETS


def test_categorize_untriaged_fr() -> None:
    issue = _make_issue(1, ["kind:feature-request"])
    bucket = categorize_issue(issue, all_issues=[issue])
    assert bucket == "untriaged-fr"


def test_categorize_armed() -> None:
    issue = _make_issue(2, ["kind:feature", "status:ready", "bot:ship-issue-ready"])
    bucket = categorize_issue(issue, all_issues=[issue])
    assert bucket == "bot-ready-armed"


def test_categorize_missing_kind() -> None:
    issue = _make_issue(3, ["status:ready"])
    bucket = categorize_issue(issue, all_issues=[issue])
    assert bucket == "missing-kind-label"


def test_sweep_returns_bucketed_list() -> None:
    fake_gh = MagicMock()
    fake_gh.issue_list = MagicMock(return_value=[
        _make_issue(1, ["kind:feature-request"]),
        _make_issue(2, ["kind:feature", "status:ready", "bot:ship-issue-ready"]),
    ])
    results = sweep("org/repo", gh=fake_gh)
    buckets = {r["bucket"] for r in results}
    assert "untriaged-fr" in buckets
    assert "bot-ready-armed" in buckets
```

- [ ] **Step 2: Verify failures**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_triage.py -x 2>&1 | tail -5
```

- [ ] **Step 3: Implement `src/coding_bot/helpers/triage.py`**

```python
"""triage — bulk issue categorization and child-issue forking.

Ported from scripts/triage-sweep.py + scripts/triage-fork.py.
"""
from __future__ import annotations

import re
from typing import Any

_TRACKS_RE = re.compile(r"^Tracks:\s*#(\d+)\s*$", re.MULTILINE)
_SPEC_FILE_RE = re.compile(r"^Spec:\s*docs/specs/.+\.md\s*$", re.MULTILINE)

BUCKETS = [
    "untriaged-fr",
    "approved-needs-spec-no-child",
    "approved-needs-tracking-no-child",
    "spec-missing-tracks-link",
    "spec-missing-spec-file-link",
    "bot-ready-not-armed",
    "bot-ready-armed",
    "missing-kind-label",
    "blocked",
    "triaged-rejected",
    "other",
]

SUGGESTED_ACTIONS: dict[str, str] = {
    "untriaged-fr": "Run `/triage <N>` to approve or reject this feature request",
    "approved-needs-spec-no-child": "Run `/triage <N>` or manually create a kind:spec child with `Tracks: #<N>`",
    "approved-needs-tracking-no-child": "Run `/triage <N>` or create a tracking child with `Tracks: #<N>`",
    "spec-missing-tracks-link": "Add `Tracks: #<FR-number>` as the first line of this spec issue body",
    "spec-missing-spec-file-link": "Run `/spec-from-issue <N>` to generate the spec file",
    "bot-ready-not-armed": "Add `status:ready` label to arm this issue",
    "bot-ready-armed": "Waiting for next ship-issue cycle",
    "missing-kind-label": "Add a `kind:*` label",
    "blocked": "Review blocker",
    "triaged-rejected": "Closed loop — no action required",
    "other": "No action required",
}


def _label_names(issue: dict) -> set[str]:
    return {lbl["name"] for lbl in issue.get("labels", [])}


def _tracks_parent(body: str | None) -> int | None:
    if not body:
        return None
    m = _TRACKS_RE.search(body)
    return int(m.group(1)) if m else None


def _spec_child_exists(fr_num: int, all_issues: list[dict]) -> bool:
    needle = f"Tracks: #{fr_num}"
    return any(
        issue["number"] != fr_num
        and "kind:spec" in _label_names(issue)
        and needle in (issue.get("body") or "")
        for issue in all_issues
    )


def _tracking_child_exists(parent_num: int, all_issues: list[dict]) -> bool:
    needle = f"Tracks: #{parent_num}"
    return any(
        issue["number"] != parent_num
        and needle in (issue.get("body") or "")
        for issue in all_issues
    )


def categorize_issue(issue: dict, *, all_issues: list[dict]) -> str:
    """Return the bucket name for a single issue."""
    labels = _label_names(issue)
    body = issue.get("body") or ""

    if "kind:feature-request" in labels:
        if "triage:rejected" in labels:
            return "triaged-rejected"
        if "triage:approved" not in labels:
            return "untriaged-fr"
        # approved — needs spec or tracking child
        if "output:spec" in labels or not _spec_child_exists(issue["number"], all_issues):
            if not _tracking_child_exists(issue["number"], all_issues):
                return "approved-needs-spec-no-child"
        if not _tracking_child_exists(issue["number"], all_issues):
            return "approved-needs-tracking-no-child"

    if "kind:spec" in labels:
        if not _tracks_parent(body):
            return "spec-missing-tracks-link"
        if not re.search(r"^Spec:\s*", body, re.MULTILINE):
            return "spec-missing-spec-file-link"

    kind_labels = {l for l in labels if l.startswith("kind:")}
    if not kind_labels:
        return "missing-kind-label"

    if "status:blocked" in labels:
        return "blocked"

    if "bot:ship-issue-ready" in labels and "status:ready" in labels:
        return "bot-ready-armed"

    # Has kind but no bot label
    if any(l in labels for l in ("kind:feature", "kind:bug", "kind:chore", "kind:tracking")):
        if "bot:ship-issue-ready" not in labels:
            return "bot-ready-not-armed"

    return "other"


def sweep(repo: str, *, gh: Any, limit: int = 200) -> list[dict]:
    """Categorize all open issues in a repo. Returns list of {number, title, bucket, action}."""
    issues = gh.issue_list(repo, labels=[], limit=limit)
    return [
        {
            "number": issue["number"],
            "title": issue.get("title", ""),
            "bucket": categorize_issue(issue, all_issues=issues),
            "action": SUGGESTED_ACTIONS.get(categorize_issue(issue, all_issues=issues), ""),
        }
        for issue in issues
    ]


def fork_child(
    repo: str,
    parent: int,
    kind: str,
    title: str,
    body: str,
    labels: list[str],
    *,
    gh: Any,
    output: str = "tracking",
    dry_run: bool = False,
) -> int | None:
    """Create a child issue tracking parent. Returns new issue number or None (dry-run)."""
    if dry_run:
        return None
    return gh.issue_create(repo, title=title, body=body, labels=labels)
```

- [ ] **Step 4: Add `issue_create` to `gh.py`**

In `src/coding_bot/gh.py`, add:

```python
def issue_create(
    repo: str,
    *,
    title: str,
    body: str,
    labels: list[str] | None = None,
    milestone: int | None = None,
) -> int:
    cmd = ["gh", "issue", "create", "--repo", repo,
           "--title", title, "--body", body]
    for label in labels or []:
        cmd += ["--label", label]
    if milestone is not None:
        cmd += ["--milestone", str(milestone)]
    result = _run(cmd)
    # gh prints the issue URL; extract the number from the last path component
    return int(result.strip().rstrip("/").split("/")[-1])
```

- [ ] **Step 5: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_triage.py -v 2>&1 | tail -12
```

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/coding-bot
git add src/coding_bot/helpers/triage.py tests/unit/helpers/test_triage.py src/coding_bot/gh.py
git commit -m "feat(helpers): add triage module"
```

---

### Task D.2: `helpers/wip_pr.py`

Port `pr-wip-status.sh` + `auto-merge-wip-prs.sh` + `merge-wip-ship-issue-pr.sh` (all bash → Python). Public API:
- `wip_status(repos, *, gh) -> list[dict]`
- `auto_merge(repos, *, gh, git, dry_run) -> list[str]`
- `merge_pr(repo, pr_number, *, gh, git) -> None`

**Files:**
- Create: `src/coding_bot/helpers/wip_pr.py`
- Create: `tests/unit/helpers/test_wip_pr.py`

- [ ] **Step 1: Write tests**

`tests/unit/helpers/test_wip_pr.py`:

```python
from __future__ import annotations
from unittest.mock import MagicMock
from coding_bot.helpers.wip_pr import wip_status, auto_merge


def _make_pr(number: int, draft: bool, labels: list[str], checks: list[dict]) -> dict:
    return {
        "number": number, "title": f"PR {number}", "isDraft": draft,
        "labels": [{"name": l} for l in labels],
        "statusCheckRollup": checks,
    }


def test_wip_status_returns_list() -> None:
    fake_gh = MagicMock()
    fake_gh.pr_list_open = MagicMock(return_value=[
        _make_pr(1, True, ["bot:merge-ready"], [{"name": "CI", "conclusion": "SUCCESS", "__typename": "CheckRun"}]),
    ])
    fake_gh.compare_branches = MagicMock(return_value={"ahead_by": 3})
    results = wip_status(["org/repo"], gh=fake_gh)
    assert len(results) == 1
    assert results[0]["repo"] == "org/repo"


def test_auto_merge_skips_non_ready_prs() -> None:
    fake_gh = MagicMock()
    fake_gh.pr_list_open = MagicMock(return_value=[
        _make_pr(1, False, ["kind:feature"], []),  # no bot:merge-ready
    ])
    fake_git = MagicMock()
    merged = auto_merge(["org/repo"], gh=fake_gh, git=fake_git, dry_run=True)
    assert merged == []


def test_auto_merge_dry_run_eligible_pr() -> None:
    fake_gh = MagicMock()
    fake_gh.pr_list_open = MagicMock(return_value=[
        _make_pr(5, False, ["bot:merge-ready"], [
            {"name": "CI", "conclusion": "SUCCESS", "__typename": "CheckRun"},
        ]),
    ])
    fake_git = MagicMock()
    merged = auto_merge(["org/repo"], gh=fake_gh, git=fake_git, dry_run=True)
    assert "org/repo#5" in merged
    fake_git.merge_pr.assert_not_called()
```

- [ ] **Step 2: Verify failures**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_wip_pr.py -x 2>&1 | tail -5
```

- [ ] **Step 3: Implement `src/coding_bot/helpers/wip_pr.py`**

```python
"""wip_pr — rolling-PR status, auto-merge, and merge helpers.

Ported from pr-wip-status.sh + auto-merge-wip-prs.sh + merge-wip-ship-issue-pr.sh.
"""
from __future__ import annotations

from typing import Any

_MERGE_READY_LABEL = "bot:merge-ready"
_WIP_BRANCH = "wip/ship-issue"


def wip_status(repos: list[str], *, gh: Any) -> list[dict]:
    """Return PR state + branch ahead-counts for each repo."""
    results = []
    for repo in repos:
        prs = gh.pr_list_open(repo)
        try:
            ahead = gh.compare_branches(repo, base="main", head=_WIP_BRANCH)
        except Exception:
            ahead = {"ahead_by": "error"}
        results.append({
            "repo": repo,
            "prs": [
                {
                    "number": pr["number"],
                    "title": pr["title"],
                    "draft": pr.get("isDraft", False),
                    "labels": [l["name"] for l in pr.get("labels", [])],
                    "ci": _summarize_checks(pr.get("statusCheckRollup") or []),
                }
                for pr in prs
            ],
            "wip_ahead": ahead.get("ahead_by", "?"),
        })
    return results


def _summarize_checks(checks: list[dict]) -> str:
    runs = [c for c in checks if c.get("__typename") == "CheckRun"]
    if not runs:
        return "(no checks)"
    return " ".join(f"{c['name']}:{c.get('conclusion', '?')}" for c in runs)


def _is_merge_eligible(pr: dict) -> bool:
    labels = {l["name"] for l in pr.get("labels", [])}
    if _MERGE_READY_LABEL not in labels:
        return False
    checks = pr.get("statusCheckRollup") or []
    runs = [c for c in checks if c.get("__typename") == "CheckRun"]
    if not runs:
        return False
    return all(c.get("conclusion") in ("SUCCESS", "SKIPPED") for c in runs)


def auto_merge(
    repos: list[str],
    *,
    gh: Any,
    git: Any,
    dry_run: bool = False,
) -> list[str]:
    """Merge all eligible (bot:merge-ready + green CI) rolling PRs.

    Returns list of 'repo#pr_number' strings merged (or would-merge on dry_run).
    """
    merged: list[str] = []
    for repo in repos:
        prs = gh.pr_list_open(repo)
        for pr in prs:
            if _is_merge_eligible(pr):
                key = f"{repo}#{pr['number']}"
                if not dry_run:
                    merge_pr(repo, pr["number"], gh=gh, git=git)
                merged.append(key)
    return merged


def merge_pr(repo: str, pr_number: int, *, gh: Any, git: Any) -> None:
    """Merge a rolling PR: rebase-merge, reset wip branch to main HEAD."""
    gh.pr_merge(repo, pr_number, merge_method="rebase")
    git.fetch(repo)
    git.reset_branch_to_remote(repo, branch=_WIP_BRANCH, target="origin/main")
```

- [ ] **Step 4: Add helpers to `gh.py` and `git.py`**

In `src/coding_bot/gh.py`, add:

```python
def pr_list_open(repo: str) -> list[dict[str, Any]]:
    return json.loads(_run([
        "gh", "pr", "list", "--repo", repo, "--state", "open",
        "--json", "number,title,isDraft,labels,statusCheckRollup",
    ]))


def compare_branches(repo: str, base: str, head: str) -> dict[str, Any]:
    return json.loads(_run([
        "gh", "api", f"repos/{repo}/compare/{base}...{head}",
        "--jq", "{ahead_by: .ahead_by}",
    ]))


def pr_merge(repo: str, pr_number: int, merge_method: str = "rebase") -> None:
    _run(["gh", "pr", "merge", str(pr_number), "--repo", repo,
          f"--{merge_method}"])
```

In `src/coding_bot/git.py`, add:

```python
def reset_branch_to_remote(repo_path: Path, *, branch: str, target: str) -> None:
    _run(["git", "-C", str(repo_path), "checkout", branch])
    _run(["git", "-C", str(repo_path), "reset", "--hard", target])
```

- [ ] **Step 5: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_wip_pr.py -v 2>&1 | tail -12
```

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/coding-bot
git add src/coding_bot/helpers/wip_pr.py tests/unit/helpers/test_wip_pr.py src/coding_bot/gh.py src/coding_bot/git.py
git commit -m "feat(helpers): add wip_pr module"
```

---

## Phase E — Infrastructure helpers

### Task E.1: `helpers/bot_workspace.py` and `helpers/protections.py`

Port `bot-workspace-bootstrap.sh` (bash → Python) and `verify-protections.sh` (bash → Python).

**Files:**
- Create: `src/coding_bot/helpers/bot_workspace.py`
- Create: `src/coding_bot/helpers/protections.py`
- Create: `tests/unit/helpers/test_bot_workspace.py`
- Create: `tests/unit/helpers/test_protections.py`

- [ ] **Step 1: Write tests**

`tests/unit/helpers/test_bot_workspace.py`:

```python
from __future__ import annotations
from pathlib import Path
from coding_bot.helpers.bot_workspace import get_paths, WorkspacePaths


def test_get_paths_ship_issue() -> None:
    paths = get_paths("ship-issue", "pdomain/pdomain-book-tools", slot=2)
    assert isinstance(paths, WorkspacePaths)
    assert "ship-issue" in str(paths.worktree)
    assert "pdomain-book-tools" in str(paths.worktree)
    assert paths.slot == 2


def test_get_paths_branch_name() -> None:
    paths = get_paths("ship-issue", "pdomain/pdomain-book-tools", slot=0)
    assert paths.branch == "wip/ship-issue"


def test_get_paths_style_sweep() -> None:
    paths = get_paths("style-sweep", "pdomain/pdomain-book-tools", slot=0)
    assert "style-sweep" in paths.branch
```

`tests/unit/helpers/test_protections.py`:

```python
from __future__ import annotations
from unittest.mock import MagicMock, patch
from coding_bot.helpers.protections import ProtectionResult, check_all


def test_check_all_returns_list() -> None:
    results = check_all(workspace=None, dry_run=True)
    assert isinstance(results, list)
    # In dry-run mode all checks are skipped; results may be empty
```

- [ ] **Step 2: Verify failures**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_bot_workspace.py tests/unit/helpers/test_protections.py -x 2>&1 | tail -5
```

- [ ] **Step 3: Implement `src/coding_bot/helpers/bot_workspace.py`**

```python
"""bot_workspace — manage /srv/bot-workspaces/ topology.

Ported from scripts/bot-workspace-bootstrap.sh (bash → Python).
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path("/srv/bot-workspaces")
WORKSPACE = Path("/workspaces/ocr-container")

_BRANCH_MAP: dict[str, str] = {
    "ship-issue": "wip/ship-issue",
    "style-review": "wip/ship-issue",
    "style-sweep": "wip/style-sweep",
    "decompose-spec-auto": "wip/decompose-spec-auto",
}
_PATH_TRAVERSAL = re.compile(r"\.\.")


@dataclass
class WorkspacePaths:
    worktree: Path
    branch: str
    slot: int
    repo: str


def get_paths(workflow: str, repo: str, *, slot: int = 0) -> WorkspacePaths:
    """Return canonical paths for a bot worktree (no filesystem side effects)."""
    if _PATH_TRAVERSAL.search(workflow) or _PATH_TRAVERSAL.search(repo):
        raise ValueError(f"Path traversal detected: workflow={workflow!r} repo={repo!r}")
    repo_name = repo.split("/")[-1]
    branch = _BRANCH_MAP.get(workflow, f"wip/{workflow}")
    worktree = _ROOT / workflow / repo_name / f"slot{slot}"
    return WorkspacePaths(worktree=worktree, branch=branch, slot=slot, repo=repo)


def bootstrap(workflow: str, repo: str, *, slot: int = 0) -> WorkspacePaths:
    """Idempotently create the worktree for (workflow, repo, slot)."""
    paths = get_paths(workflow, repo, slot=slot)
    repo_name = repo.split("/")[-1]
    source_repo = WORKSPACE / repo_name

    paths.worktree.parent.mkdir(parents=True, exist_ok=True)
    (_ROOT / ".locks").mkdir(exist_ok=True)
    (_ROOT / ".state").mkdir(exist_ok=True)

    if not paths.worktree.exists():
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(paths.worktree)],
            cwd=str(source_repo), check=True,
        )

    return paths
```

- [ ] **Step 4: Implement `src/coding_bot/helpers/protections.py`**

```python
"""protections — verify claude-bot cannot modify enforcement files.

Ported from scripts/verify-protections.sh (bash → Python).
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

WORKSPACE = Path("/workspaces/ocr-container")

_PROTECTED_PATHS = [
    ".claude/hooks/bash-command-guard.py",
    ".claude/settings.json",
    "pd-push",
    "scripts/lint-spec.py",
    "scripts/ship-issue-pick.py",
]


@dataclass
class ProtectionResult:
    path: str
    protected: bool
    message: str


def check_path(path: str, workspace: Path) -> ProtectionResult:
    """Check that claude-bot cannot write to path. Skips if file not present."""
    full = workspace / path
    if not full.exists():
        return ProtectionResult(path, protected=True, message="(does not exist, skipped)")
    try:
        result = subprocess.run(
            ["sudo", "-u", "claude-bot", "bash", "-lc",
             f"echo test >> '{full}' && head -n -1 '{full}' > /tmp/r.tmp && mv /tmp/r.tmp '{full}'"],
            capture_output=True, timeout=10,
        )
        if result.returncode == 0:
            return ProtectionResult(path, protected=False, message="FAIL: claude-bot could write")
        return ProtectionResult(path, protected=True, message="✓ correctly denied")
    except subprocess.TimeoutExpired:
        return ProtectionResult(path, protected=True, message="✓ (timeout — treated as denied)")


def check_all(workspace: Path | None = None, *, dry_run: bool = False) -> list[ProtectionResult]:
    """Run all protection checks. In dry_run mode, skip sudo calls."""
    ws = workspace or WORKSPACE
    if dry_run:
        return []
    return [check_path(p, ws) for p in _PROTECTED_PATHS]
```

- [ ] **Step 5: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_bot_workspace.py tests/unit/helpers/test_protections.py -v 2>&1 | tail -10
```

- [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/coding-bot
git add src/coding_bot/helpers/bot_workspace.py src/coding_bot/helpers/protections.py tests/unit/helpers/test_bot_workspace.py tests/unit/helpers/test_protections.py
git commit -m "feat(helpers): add bot_workspace and protections modules"
```

---

### Task E.2: `helpers/patches.py`

Extract the `apply_with_revert` pattern from `style-review-apply.py` as a standalone helper for the style-review workflow.

**Files:**
- Create: `src/coding_bot/helpers/patches.py`
- Create: `tests/unit/helpers/test_patches.py`

- [ ] **Step 1: Write tests**

`tests/unit/helpers/test_patches.py`:

```python
from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock
from coding_bot.helpers.patches import apply_patch, PatchResult


def test_apply_patch_success(tmp_path: Path) -> None:
    target = tmp_path / "file.py"
    target.write_text("line1\nline2\n")

    fake_shell = MagicMock()
    fake_shell.run = MagicMock(return_value=0)

    result = apply_patch("fake diff", cwd=tmp_path, shell=fake_shell)
    assert result == PatchResult.APPLIED
    fake_shell.run.assert_called_once()


def test_apply_patch_failure_triggers_revert(tmp_path: Path) -> None:
    fake_shell = MagicMock()
    fake_shell.run = MagicMock(return_value=1)  # git apply fails

    result = apply_patch("bad diff", cwd=tmp_path, shell=fake_shell)
    assert result == PatchResult.REJECTED
```

- [ ] **Step 2: Verify failures**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_patches.py -x 2>&1 | tail -5
```

- [ ] **Step 3: Implement `src/coding_bot/helpers/patches.py`**

```python
"""patches — apply git patches with auto-revert on failure.

Extracted from scripts/style-review-apply.py for use by style-review workflow.
"""
from __future__ import annotations

import subprocess
import tempfile
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


class PatchResult(Enum):
    APPLIED = "applied"
    REJECTED = "rejected"


class ShellProtocol(Protocol):
    def run(self, cmd: list[str], **kwargs: Any) -> int: ...


class RealShell:
    def run(self, cmd: list[str], **kwargs: Any) -> int:
        return subprocess.run(cmd, **kwargs).returncode


def apply_patch(
    patch_text: str,
    *,
    cwd: Path,
    shell: ShellProtocol | None = None,
) -> PatchResult:
    """Write patch_text to a temp file and run `git apply`. Revert on failure."""
    sh = shell or RealShell()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
        f.write(patch_text)
        patch_path = Path(f.name)

    try:
        rc = sh.run(
            ["git", "apply", "--whitespace=fix", str(patch_path)],
            cwd=str(cwd),
            capture_output=True,
        )
        if rc == 0:
            return PatchResult.APPLIED
        # Revert any partial application
        sh.run(["git", "checkout", "--", "."], cwd=str(cwd), capture_output=True)
        return PatchResult.REJECTED
    finally:
        patch_path.unlink(missing_ok=True)
```

- [ ] **Step 4: Run tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/helpers/test_patches.py -v 2>&1 | tail -8
```

- [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container/coding-bot
git add src/coding_bot/helpers/patches.py tests/unit/helpers/test_patches.py
git commit -m "feat(helpers): add patches module"
```

---

## Phase F — Hook namespace

### Task F.1: Hook modules + `coding-bot hook` CLI

Port `no-trailing-todos.sh` (bash → Python) as the first hook. Then add the three thin-wrapper hooks. Wire the `coding-bot hook` sub-app.

**Files:**
- Create: `src/coding_bot/hooks/__init__.py`
- Create: `src/coding_bot/hooks/trailing_todos.py`
- Create: `src/coding_bot/hooks/spec_lint.py`
- Create: `src/coding_bot/hooks/conventions_lint.py`
- Create: `src/coding_bot/hooks/issue_labels_lint.py`
- Create: `tests/unit/hooks/__init__.py`
- Create: `tests/unit/hooks/test_trailing_todos.py`
- Modify: `src/coding_bot/cli.py` — add `hook_app`

- [ ] **Step 1: Write trailing-todos tests**

`tests/unit/hooks/test_trailing_todos.py`:

```python
from __future__ import annotations
from pathlib import Path
from coding_bot.hooks.trailing_todos import check_files, MarkerViolation


def test_no_markers_clean(tmp_path: Path) -> None:
    f = tmp_path / "clean.py"
    f.write_text("def foo():\n    return 1\n")
    assert check_files([f]) == []


def test_paired_todo_ok(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("# TODO #123: fix this\npass\n")
    assert check_files([f]) == []


def test_unpaired_todo_violation(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("# TODO: fix this\npass\n")
    violations = check_files([f])
    assert len(violations) == 1
    assert violations[0].path == f
    assert violations[0].line == 1


def test_paired_date_ok(tmp_path: Path) -> None:
    f = tmp_path / "dated.py"
    f.write_text("# FIXME (2026-05-14): clean up\npass\n")
    assert check_files([f]) == []


def test_fixme_without_pairing(tmp_path: Path) -> None:
    f = tmp_path / "bad2.py"
    f.write_text("# FIXME: clean up\n")
    violations = check_files([f])
    assert len(violations) == 1
```

- [ ] **Step 2: Verify failures**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/hooks/test_trailing_todos.py -x 2>&1 | tail -5
```

- [ ] **Step 3: Implement `src/coding_bot/hooks/__init__.py`** (empty)

```python
```

- [ ] **Step 4: Implement `src/coding_bot/hooks/trailing_todos.py`**

```python
"""trailing_todos hook — reject unpaired TODO/FIXME/XXX markers.

Ported from scripts/no-trailing-todos.sh (bash → Python).
Pairing rule: marker must be followed on the same line by '#<digits>' or '(YYYY-MM-DD)'.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_MARKERS = re.compile(r"\b(TODO|FIXME|XXX)\b")
_PAIRING = re.compile(r"(#[0-9]+|\([0-9]{4}-[0-9]{2}-[0-9]{2}\))")


@dataclass
class MarkerViolation:
    path: Path
    line: int
    text: str


def check_files(paths: list[Path]) -> list[MarkerViolation]:
    """Return violations for unpaired TODO/FIXME/XXX markers across files."""
    violations: list[MarkerViolation] = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for lineno, text in enumerate(lines, start=1):
            if _MARKERS.search(text) and not _PAIRING.search(text):
                violations.append(MarkerViolation(path=path, line=lineno, text=text.strip()))
    return violations
```

- [ ] **Step 5: Implement thin-wrapper hooks**

`src/coding_bot/hooks/spec_lint.py`:

```python
"""spec_lint hook — pre-commit wrapper calling helpers.spec_lint."""
from __future__ import annotations
from pathlib import Path
from coding_bot.helpers.spec_lint import lint_file


def check_files(paths: list[Path]) -> list:
    errors = []
    for p in paths:
        if p.suffix == ".md":
            errors.extend(lint_file(p))
    return errors
```

`src/coding_bot/hooks/conventions_lint.py`:

```python
"""conventions_lint hook — pre-commit wrapper calling helpers.conventions."""
from __future__ import annotations
from pathlib import Path
from coding_bot.helpers.conventions import lint_conventions_file


def check_files(paths: list[Path]) -> list:
    errors = []
    for p in paths:
        if p.name == "CONVENTIONS.md":
            errors.extend(lint_conventions_file(p))
    return errors
```

`src/coding_bot/hooks/issue_labels_lint.py`:

```python
"""issue_labels_lint hook — pre-commit wrapper that lints GitHub issue labels."""
from __future__ import annotations
from coding_bot.helpers.label_lint import find_violations
from coding_bot import gh


def run(repo: str) -> list[dict]:
    issues = gh.issue_list(repo, labels=[], limit=200)
    violations = []
    for issue in issues:
        v = find_violations(issue)
        if v:
            violations.append({"issue": issue["number"], "violations": v})
    return violations
```

- [ ] **Step 6: Wire `hook_app` in `cli.py`**

In `src/coding_bot/cli.py`, after the existing imports and before the last lines, add:

```python
# ─── hook sub-app ────────────────────────────────────────────────────────────
hook_app = typer.Typer(name="hook", help="Pre-commit hook entry points.", no_args_is_help=True)
app.add_typer(hook_app, name="hook")


@hook_app.command("trailing-todos")
def hook_trailing_todos(
    files: list[Path] = typer.Argument(default=None),
) -> None:
    """Reject files with unpaired TODO/FIXME/XXX markers."""
    from coding_bot.hooks.trailing_todos import check_files, MarkerViolation
    if not files:
        raise typer.Exit(0)
    violations = check_files(files)
    for v in violations:
        console.print(f"[red]{v.path}:{v.line}:[/red] unpaired marker — {v.text}")
    raise typer.Exit(1 if violations else 0)


@hook_app.command("spec-lint")
def hook_spec_lint(
    files: list[Path] = typer.Argument(default=None),
) -> None:
    """Lint spec files for required headings and structure."""
    from coding_bot.hooks.spec_lint import check_files
    if not files:
        raise typer.Exit(0)
    errors = check_files(files)
    for e in errors:
        console.print(f"[red]{e.path}:{e.line}:[/red] {e.message}")
    raise typer.Exit(1 if errors else 0)


@hook_app.command("conventions-lint")
def hook_conventions_lint(
    files: list[Path] = typer.Argument(default=None),
) -> None:
    """Lint CONVENTIONS.md files for required rule structure."""
    from coding_bot.hooks.conventions_lint import check_files
    if not files:
        raise typer.Exit(0)
    errors = check_files(files)
    for e in errors:
        console.print(f"[red]{e.path}:[/red] {e.message}")
    raise typer.Exit(1 if errors else 0)


@hook_app.command("issue-labels-lint")
def hook_issue_labels_lint(
    repo: str = typer.Option(..., "--repo", "-r", help="owner/repo"),
) -> None:
    """Lint GitHub issue labels for single-select family violations."""
    from coding_bot.hooks.issue_labels_lint import run
    violations = run(repo)
    for v in violations:
        console.print(f"[red]Issue #{v['issue']}:[/red] {v['violations']}")
    raise typer.Exit(1 if violations else 0)
```

- [ ] **Step 7: Smoke-test hooks CLI**

```bash
cd /workspaces/ocr-container/coding-bot
uv run coding-bot hook --help
uv run coding-bot hook trailing-todos --help
```

- [ ] **Step 8: Run hook tests**

```bash
cd /workspaces/ocr-container/coding-bot
uv run pytest tests/unit/hooks/ -v 2>&1 | tail -12
```

- [ ] **Step 9: Commit**

```bash
cd /workspaces/ocr-container/coding-bot
git add src/coding_bot/hooks/ tests/unit/hooks/ src/coding_bot/cli.py
git commit -m "feat(hooks): add hook namespace + trailing_todos, spec_lint, conventions_lint, issue_labels_lint"
```

---

## Phase G — Additional CLI surface

### Task G.1: Wire helper sub-apps into `cli.py`

Add `spec`, `label`, `conventions`, `triage`, `wip-pr`, `bot-workspace`, `protections` sub-apps plus `coding-bot setup`, `coding-bot budget`, `coding-bot agents`, and the remaining `db` commands.

**Files:**
- Modify: `src/coding_bot/cli.py`

- [ ] **Step 1: Add `spec` sub-app**

In `src/coding_bot/cli.py`, add after `hook_app` wiring:

```python
# ─── spec sub-app ────────────────────────────────────────────────────────────
spec_app = typer.Typer(name="spec", help="Spec lifecycle helpers.", no_args_is_help=True)
app.add_typer(spec_app, name="spec")


@spec_app.command("lint")
def spec_lint_cmd(
    files: list[Path] = typer.Argument(default=None),
    no_legacy: bool = typer.Option(False, "--no-legacy"),
) -> None:
    """Lint spec files against the 9-section template."""
    from coding_bot.helpers.spec_lint import lint_file, LintError
    if not files:
        console.print("[yellow]No files specified.[/yellow]")
        raise typer.Exit(0)
    all_errors: list[LintError] = []
    for f in files:
        all_errors.extend(lint_file(Path(f), no_legacy=no_legacy))
    for e in all_errors:
        level_color = "red" if e.level == "error" else "yellow"
        console.print(f"[{level_color}]{e.path}:{e.line}:[/{level_color}] {e.message}")
    raise typer.Exit(1 if any(e.level == "error" for e in all_errors) else 0)


@spec_app.command("index")
def spec_index_cmd(
    out: Path = typer.Option(Path.home() / "spec-index.html", "--out"),
) -> None:
    """Generate a workspace-level HTML spec index."""
    from coding_bot.helpers.spec_index import build_html
    html = build_html()
    out.write_text(html)
    console.print(f"[green]Spec index written to {out}[/green]")


@spec_app.command("chain-report")
def spec_chain_report_cmd(
    repo: str = typer.Argument(..., help="owner/repo"),
) -> None:
    """Print spec chain state for a repo."""
    from coding_bot.helpers.triage import sweep
    from coding_bot import gh as gh_module
    results = sweep(repo, gh=gh_module)
    for r in results:
        console.print(f"  #{r['number']} [{r['bucket']}] {r['title']}")
```

- [ ] **Step 2: Add `label` sub-app**

```python
# ─── label sub-app ───────────────────────────────────────────────────────────
label_app = typer.Typer(name="label", help="Label management.", no_args_is_help=True)
app.add_typer(label_app, name="label")


@label_app.command("lint")
def label_lint_cmd(
    repos: list[str] = typer.Option([], "--repo", "-r"),
    fix: bool = typer.Option(False, "--fix"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Detect single-select label violations across repos."""
    from coding_bot.helpers.label_lint import find_violations
    from coding_bot import gh as gh_module
    all_violations = 0
    for repo in repos:
        issues = gh_module.issue_list(repo, labels=[], limit=200)
        for issue in issues:
            v = find_violations(issue)
            if v:
                console.print(f"[yellow]{repo}#{issue['number']}:[/yellow] {v}")
                all_violations += len(v)
    raise typer.Exit(1 if all_violations else 0)


@label_app.command("seed")
def label_seed_cmd(
    repo: str = typer.Argument(...),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Idempotently create the standard label set on a repo."""
    from coding_bot.helpers.label_seed import seed_labels
    from coding_bot import gh as gh_module
    if dry_run:
        from coding_bot.helpers.label_seed import STANDARD_LABELS
        console.print(f"[yellow]Dry run:[/yellow] would create up to {len(STANDARD_LABELS)} labels on {repo}")
        return
    created = seed_labels(repo, gh=gh_module)
    console.print(f"[green]Created {created} labels on {repo}.[/green]")


@label_app.command("arm")
def label_arm_cmd(
    repo: str = typer.Argument(...),
    issue: int = typer.Argument(...),
    force: bool = typer.Option(False, "--force"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Arm an issue for ship-issue (adds bot:ship-issue-ready + status:ready)."""
    from coding_bot.helpers.label_arm import arm_issue, ArmResult, ArmError
    from coding_bot import gh as gh_module
    try:
        result = arm_issue(repo, issue, gh=gh_module, force=force, dry_run=dry_run)
    except ArmError as e:
        console.print(f"[red]Arm refused:[/red] {e}")
        raise typer.Exit(3)
    if result == ArmResult.ALREADY_ARMED:
        console.print(f"[yellow]Issue #{issue} already armed.[/yellow]")
    else:
        console.print(f"[green]Issue #{issue} armed.[/green]")
```

- [ ] **Step 3: Add `conventions`, `triage`, `wip-pr` sub-apps**

```python
# ─── conventions sub-app ─────────────────────────────────────────────────────
conventions_app = typer.Typer(name="conventions", help="CONVENTIONS.md helpers.", no_args_is_help=True)
app.add_typer(conventions_app, name="conventions")


@conventions_app.command("lint")
def conventions_lint_cmd(
    files: list[Path] = typer.Argument(default=None),
) -> None:
    """Lint CONVENTIONS.md files for required structure."""
    from coding_bot.helpers.conventions import lint_conventions_file
    if not files:
        raise typer.Exit(0)
    errors = []
    for f in files:
        errors.extend(lint_conventions_file(Path(f)))
    for e in errors:
        console.print(f"[red]{e.path}:[/red] [{e.rule_heading}] {e.message}")
    raise typer.Exit(1 if errors else 0)


@conventions_app.command("check-drift")
def conventions_check_drift_cmd(
    repo: Path = typer.Argument(..., help="Path to pd-* repo"),
) -> None:
    """Show workspace convention rules missing from repo CONVENTIONS.md."""
    from coding_bot.helpers.conventions import check_sibling_drift
    missing = check_sibling_drift(repo)
    if not missing:
        console.print("[green]No drift.[/green]")
    else:
        console.print(f"[yellow]{len(missing)} workspace rules missing from {repo.name}:[/yellow]")
        for rule in missing:
            console.print(f"  - {rule}")
        raise typer.Exit(1)


# ─── triage sub-app ──────────────────────────────────────────────────────────
triage_app = typer.Typer(name="triage", help="Issue triage helpers.", no_args_is_help=True)
app.add_typer(triage_app, name="triage")


@triage_app.command("sweep")
def triage_sweep_cmd(
    repo: str = typer.Argument(...),
    limit: int = typer.Option(200, "--limit"),
) -> None:
    """Categorize open issues by triage bucket."""
    from coding_bot.helpers.triage import sweep, SUGGESTED_ACTIONS
    from coding_bot import gh as gh_module
    results = sweep(repo, gh=gh_module, limit=limit)
    for r in results:
        console.print(f"  [bold]#{r['number']}[/bold] [{r['bucket']}] {r['title']}")
        console.print(f"    → {r['action']}")


@triage_app.command("fork")
def triage_fork_cmd(
    repo: str = typer.Argument(...),
    parent: int = typer.Option(..., "--parent"),
    kind: str = typer.Option(..., "--kind"),
    title: str = typer.Option(..., "--title"),
    body_file: Path = typer.Option(..., "--body-file"),
    label: list[str] = typer.Option([], "--label"),
    output: str = typer.Option("tracking", "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Fork a child issue from a feature-request parent."""
    from coding_bot.helpers.triage import fork_child
    from coding_bot import gh as gh_module
    body = body_file.read_text()
    new_num = fork_child(repo, parent, kind, title, body, label,
                          gh=gh_module, output=output, dry_run=dry_run)
    if dry_run:
        console.print(f"[yellow]Dry run: would create {kind} issue under #{parent}[/yellow]")
    else:
        console.print(f"[green]Created child issue #{new_num}[/green]")


# ─── wip-pr sub-app ──────────────────────────────────────────────────────────
wip_pr_app = typer.Typer(name="wip-pr", help="Rolling PR lifecycle.", no_args_is_help=True)
app.add_typer(wip_pr_app, name="wip-pr")


@wip_pr_app.command("status")
def wip_pr_status_cmd(
    repos: list[str] = typer.Option([], "--repo", "-r"),
) -> None:
    """Print PR state + wip branch ahead-counts."""
    from coding_bot.helpers.wip_pr import wip_status
    from coding_bot import gh as gh_module
    if not repos:
        repos = [
            "pdomain/pdomain-ocr-labeler-spa",
            "pdomain/pdomain-prep-for-pgdp",
        ]
    results = wip_status(repos, gh=gh_module)
    for r in results:
        console.print(f"\n[bold]=== {r['repo']} ===[/bold]")
        for pr in r["prs"]:
            draft = "[draft]" if pr["draft"] else "[ready]"
            console.print(f"  PR #{pr['number']} {draft} {pr['title']}")
            console.print(f"    ci: {pr['ci']}")
        console.print(f"  wip/ship-issue: {r['wip_ahead']} commits ahead")


@wip_pr_app.command("auto-merge")
def wip_pr_auto_merge_cmd(
    repos: list[str] = typer.Option([], "--repo", "-r"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Merge all eligible (bot:merge-ready + green CI) rolling PRs."""
    from coding_bot.helpers.wip_pr import auto_merge
    from coding_bot import gh as gh_module, git as git_module
    if not repos:
        repos = [
            "pdomain/pdomain-ocr-labeler-spa",
            "pdomain/pdomain-prep-for-pgdp",
        ]
    merged = auto_merge(repos, gh=gh_module, git=git_module, dry_run=dry_run)
    for key in merged:
        marker = "[yellow](dry-run)[/yellow]" if dry_run else "[green]merged[/green]"
        console.print(f"  {marker} {key}")
    if not merged:
        console.print("[dim]Nothing eligible to merge.[/dim]")
```

- [ ] **Step 4: Add `bot-workspace`, `protections`, `agents`, `setup`, `budget` sub-apps**

```python
# ─── bot-workspace sub-app ───────────────────────────────────────────────────
bot_workspace_app = typer.Typer(name="bot-workspace", help="Manage bot worktrees.", no_args_is_help=True)
app.add_typer(bot_workspace_app, name="bot-workspace")


@bot_workspace_app.command("bootstrap")
def bot_workspace_bootstrap_cmd(
    workflow: str = typer.Argument(...),
    repo: str = typer.Argument(...),
    slot: int = typer.Option(0, "--slot"),
) -> None:
    """Idempotently create a bot worktree for (workflow, repo, slot)."""
    from coding_bot.helpers.bot_workspace import bootstrap
    paths = bootstrap(workflow, repo, slot=slot)
    console.print(f"[green]Worktree ready:[/green] {paths.worktree}")


@bot_workspace_app.command("list")
def bot_workspace_list_cmd() -> None:
    """List existing bot worktrees."""
    from pathlib import Path
    root = Path("/srv/bot-workspaces")
    if not root.exists():
        console.print("[yellow]/srv/bot-workspaces does not exist.[/yellow]")
        return
    for wf in sorted(root.iterdir()):
        if wf.name.startswith("."):
            continue
        for repo_dir in sorted(wf.iterdir()):
            for slot_dir in sorted(repo_dir.iterdir()):
                console.print(f"  {wf.name}/{repo_dir.name}/{slot_dir.name}")


# ─── protections sub-app ─────────────────────────────────────────────────────
protections_app = typer.Typer(name="protections", help="Security protection checks.", no_args_is_help=True)
app.add_typer(protections_app, name="protections")


@protections_app.command("verify")
def protections_verify_cmd() -> None:
    """Verify claude-bot cannot write to enforcement files."""
    from coding_bot.helpers.protections import check_all, ProtectionResult
    results = check_all()
    failures = [r for r in results if not r.protected]
    for r in results:
        color = "green" if r.protected else "red"
        console.print(f"  [{color}]{'✓' if r.protected else '✗'}[/{color}] {r.path}: {r.message}")
    if failures:
        console.print(f"\n[red]{len(failures)} check(s) failed.[/red]")
        raise typer.Exit(1)
    console.print("\n[green]All protection checks passed.[/green]")


# ─── agents sub-app ──────────────────────────────────────────────────────────
agents_app = typer.Typer(name="agents", help="Agent configuration helpers.", no_args_is_help=True)
app.add_typer(agents_app, name="agents")


@agents_app.command("list")
def agents_list_cmd() -> None:
    """List configured agents from .claude/agents/."""
    agents_dir = Path("/workspaces/ocr-container/.claude/agents")
    if not agents_dir.exists():
        console.print("[yellow]No agents directory found.[/yellow]")
        return
    from rich.table import Table as RTable
    table = RTable(show_header=True)
    table.add_column("Name"); table.add_column("Description (first line)")
    for f in sorted(agents_dir.glob("*.md")):
        lines = f.read_text().splitlines()
        desc = next((l for l in lines if l.startswith("description:")), "")
        table.add_row(f.stem, desc.replace("description:", "").strip()[:80])
    console.print(table)


# ─── budget sub-app ──────────────────────────────────────────────────────────
budget_app = typer.Typer(name="budget", help="Cost budget management.", no_args_is_help=True)
app.add_typer(budget_app, name="budget")


@budget_app.command("add")
def budget_add_cmd(
    name: str = typer.Argument(...),
    backend: str = typer.Option(..., "--backend"),
    plan: str = typer.Option(..., "--plan"),
    limit: float = typer.Option(..., "--limit"),
    window: str = typer.Option("monthly", "--window"),
    warn_at_pct: float = typer.Option(0.8, "--warn-at"),
    action_at_breach: str = typer.Option("pause-schedules", "--action"),
) -> None:
    """Add a cost budget entry."""
    with db_module.cost_session() as session:
        b = db_module.Budget(
            name=name, backend=backend, plan=plan,
            limit_usd=limit, window=window,
            warn_at_pct=warn_at_pct, action_at_breach=action_at_breach,
        )
        session.add(b)
        session.commit()
        console.print(f"[green]Budget '{name}' added (id={b.id}).[/green]")


@budget_app.command("list")
def budget_list_cmd() -> None:
    """List all budget entries."""
    import sqlalchemy as sa
    with db_module.cost_session() as session:
        budgets = session.execute(sa.select(db_module.Budget)).scalars().all()
    if not budgets:
        console.print("No budgets configured.")
        return
    from rich.table import Table as RTable
    table = RTable(show_header=True)
    table.add_column("ID"); table.add_column("Name"); table.add_column("Backend")
    table.add_column("Plan"); table.add_column("Window"); table.add_column("Limit USD")
    table.add_column("Action")
    for b in budgets:
        table.add_row(str(b.id), b.name, b.backend, b.plan, b.window,
                      f"${b.limit_usd:.2f}", b.action_at_breach)
    console.print(table)


@budget_app.command("status")
def budget_status_cmd() -> None:
    """Show current-period spend vs. each budget."""
    import sqlalchemy as sa
    import datetime as dt
    with db_module.cost_session() as session:
        budgets = session.execute(sa.select(db_module.Budget)).scalars().all()
    if not budgets:
        console.print("No budgets configured.")
        return
    for b in budgets:
        now = dt.datetime.utcnow()
        if b.window == "daily":
            window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif b.window == "weekly":
            window_start = (now - dt.timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0)
        else:
            window_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        with db_module.cost_session() as session:
            import sqlalchemy as sa2
            spend = session.execute(
                sa2.select(sa2.func.coalesce(sa2.func.sum(db_module.BackendRun.cost_usd), 0.0))
                .where(db_module.BackendRun.backend == b.backend)
                .where(db_module.BackendRun.started_at >= window_start)
            ).scalar_one()
        pct = float(spend) / b.limit_usd * 100 if b.limit_usd else 0
        color = "red" if pct >= 100 else ("yellow" if pct >= b.warn_at_pct * 100 else "green")
        console.print(f"  [{color}]{b.name}:[/{color}] ${float(spend):.4f} / ${b.limit_usd:.2f} ({pct:.1f}%)")


# ─── setup command ────────────────────────────────────────────────────────────
@app.command("setup")
def cmd_setup() -> None:
    """One-time setup: create /srv/coding-bot, group, permissions."""
    import grp
    import os
    import stat as stat_module
    steps: list[tuple[str, bool, str]] = []

    def step(name: str, ok: bool, remedy: str) -> None:
        steps.append((name, ok, remedy))

    # /srv/coding-bot
    srv = Path("/srv/coding-bot")
    step("/srv/coding-bot exists", srv.is_dir(),
         "sudo mkdir -p /srv/coding-bot")
    if srv.is_dir():
        st = srv.stat()
        step("/srv/coding-bot mode 2770",
             oct(stat_module.S_IMODE(st.st_mode)) == "0o2770",
             "sudo chmod 2770 /srv/coding-bot")

    # group coding-bot exists
    try:
        grp.getgrnam("coding-bot")
        step("group coding-bot exists", True, "")
    except KeyError:
        step("group coding-bot exists", False,
             "sudo groupadd coding-bot && sudo usermod -aG coding-bot vscode && sudo usermod -aG coding-bot claude-bot")

    for name, ok, remedy in steps:
        color = "green" if ok else "red"
        console.print(f"  [{color}]{'✓' if ok else '✗'}[/{color}] {name}")
        if not ok and remedy:
            console.print(f"    → {remedy}")

    if any(not ok for _, ok, _ in steps):
        raise typer.Exit(1)
    console.print("\n[green]Setup complete.[/green]")
```

- [ ] **Step 5: Add remaining `db` commands**

In `cli.py`, add to the existing `db_app` section:

```python
@db_app.command("backup-cost")
def db_backup_cost(
    out: Path = typer.Option(
        None, help="Destination path (default: /srv/coding-bot/backups/cost-YYYY-MM-DD.db)"
    ),
) -> None:
    """Copy cost.db to a backup file."""
    import datetime as dt
    import shutil
    src = Path("/srv/coding-bot/cost.db")
    if not src.exists():
        console.print(f"[red]{src} not found[/red]"); raise typer.Exit(1)
    dest = out or Path(f"/srv/coding-bot/backups/cost-{dt.date.today()}.db")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    console.print(f"[green]Backed up to {dest}[/green]")


@db_app.command("prune-state")
def db_prune_state(
    before: str = typer.Option(..., "--before", help="ISO date: delete runs ended before this date"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Delete old terminal workflow_runs and their events."""
    import sqlalchemy as sa
    import datetime as dt
    cutoff = dt.datetime.fromisoformat(before)
    with db_module.state_session() as session:
        runs = session.execute(
            sa.select(db_module.WorkflowRun)
            .where(db_module.WorkflowRun.status == "terminal")
            .where(db_module.WorkflowRun.ended_at < cutoff)
        ).scalars().all()
        if dry_run:
            console.print(f"[yellow]Dry run:[/yellow] would delete {len(runs)} runs")
            return
        for run in runs:
            session.delete(run)
        session.commit()
    console.print(f"[green]Deleted {len(runs)} runs ended before {before}.[/green]")


@db_app.command("reap-dangling-runs")
def db_reap_dangling_runs() -> None:
    """Close cost.db rows that started but never finished (> 2× max timeout)."""
    from coding_bot.scheduler.daemon import _reap_dangling_backend_runs
    _reap_dangling_backend_runs()
    console.print("[green]Dangling run reap complete.[/green]")
```

- [ ] **Step 6: Smoke-test all new sub-apps**

```bash
cd /workspaces/ocr-container/coding-bot
uv run coding-bot spec --help
uv run coding-bot label --help
uv run coding-bot conventions --help
uv run coding-bot triage --help
uv run coding-bot wip-pr --help
uv run coding-bot bot-workspace --help
uv run coding-bot protections --help
uv run coding-bot agents --help
uv run coding-bot budget --help
uv run coding-bot setup --help
uv run coding-bot db --help
```

Expected: all commands print help without import errors.

- [ ] **Step 7: Commit**

```bash
cd /workspaces/ocr-container/coding-bot
git add src/coding_bot/cli.py
git commit -m "feat(cli): wire spec, label, conventions, triage, wip-pr, bot-workspace, protections, agents, budget, setup sub-apps"
```

---

## Phase H — Update `spec_plan.py` to use native module

The existing `spec_plan.py` delegates to the subprocess script. Now that M4 ports `decompose-spec-plan.py`'s logic into the helpers, update it to call the spec_chain module directly.

**Files:**
- Modify: `src/coding_bot/helpers/spec_plan.py`

- [ ] **Step 1: Check what `decompose-spec-plan.py` does**

```bash
head -60 /workspaces/ocr-container/scripts/decompose-spec-plan.py
```

- [ ] **Step 2: Update `spec_plan.py` to call subprocess only if needed**

The existing implementation is already functional (delegates to the script). Leave it unchanged for now — full in-process port of `decompose-spec-plan.py` is optional in M4. Mark with a TODO:

```python
# TODO (2026-06-01): replace subprocess call with coding_bot.helpers.spec_chain + coding_bot.gh
# when the chain report module is stable enough to drive child-issue proposal logic.
```

This is an explicitly dated TODO — passes the pre-commit hook.

- [ ] **Step 3: Commit**

```bash
cd /workspaces/ocr-container/coding-bot
git add src/coding_bot/helpers/spec_plan.py
git commit -m "chore(helpers): add dated migration note in spec_plan.py"
```

---

## Phase I — CI + tag

### Task I.1: Full CI run, ruff format, mypy, tag

- [ ] **Step 1: Run ruff format**

```bash
cd /workspaces/ocr-container/coding-bot
uv run ruff format src/ tests/
```

- [ ] **Step 2: Run ruff check**

```bash
cd /workspaces/ocr-container/coding-bot
uv run ruff check src/ tests/ --fix
```

- [ ] **Step 3: Run full CI**

```bash
cd /workspaces/ocr-container/coding-bot
make ci AI=1
```

Expected: `✅ ci passed`.

If tests fail, diagnose from the filtered excerpt. Common issues:
- Import errors → check `__init__.py` files exist in test dirs
- Mock call signatures → adjust assert calls to match actual MagicMock usage
- gh.py function not found → verify gh.py edits from Tasks B.2 and D.2 were saved

- [ ] **Step 4: Commit lint fixes if needed**

```bash
cd /workspaces/ocr-container/coding-bot
git add -u && git commit -m "chore(lint): ruff format + check fixes for M4 helpers"
```

- [ ] **Step 5: Tag**

```bash
cd /workspaces/ocr-container/coding-bot
git tag v0.4-m4
```

- [ ] **Step 6: Print summary**

```bash
cd /workspaces/ocr-container/coding-bot
git log --oneline | head -20
uv run coding-bot --help
```

---

## Phase J — Gap-fill: remaining CLI surface from spec §13.1

Self-review against the spec found three items missing from Phases A–H:
1. `coding-bot spec from-issue-finalize` — ports `scripts/spec-from-issue-finalize.py`
2. `coding-bot ci {check, triage}` sub-app — wires `ci_check.py` and ports `ship-issue-triage-ci-failure.py`
3. `coding-bot conventions sync` — syncs workspace conventions block into a repo
4. `coding-bot label migrate-claude-ok` — ports `scripts/migrate-claude-ok-to-bot-label.sh`

`coding-bot conventions extract` intentionally deferred: it requires spawning `claude -p --bare` (LLM call); it belongs in a workflow, not a helper. The `/extract-conventions` skill covers it for interactive use.

### Task J.1: Remaining sub-app commands

**Files:**
- Modify: `src/coding_bot/helpers/conventions.py` — add `sync_workspace_block`
- Modify: `src/coding_bot/cli.py` — add `ci_app`, finish `conventions_app`, add `spec from-issue-finalize`, add `label migrate-claude-ok`

- [ ] **Step 1: Add `sync_workspace_block` to `conventions.py`**

Open `src/coding_bot/helpers/conventions.py` and add:

```python
def sync_workspace_block(repo_conventions: Path, *, workspace: Path = WORKSPACE) -> int:
    """Copy the <!-- workspace-conventions:start/end --> block from workspace into repo.

    Returns number of lines inserted (0 if already in sync).
    """
    ws_conv = workspace / "CONVENTIONS.md"
    if not ws_conv.exists() or not repo_conventions.exists():
        return 0
    block = _extract_sync_block(ws_conv.read_text())
    if not block:
        return 0
    repo_text = repo_conventions.read_text()
    start = repo_text.find(_START_MARKER)
    end = repo_text.find(_END_MARKER)
    if start != -1 and end != -1:
        # Replace existing block
        new_text = (
            repo_text[:start + len(_START_MARKER)]
            + block
            + repo_text[end:]
        )
    else:
        # Append block
        new_text = repo_text.rstrip() + f"\n\n{_START_MARKER}{block}{_END_MARKER}\n"
    repo_conventions.write_text(new_text)
    return new_text.count("\n") - repo_text.count("\n")
```

- [ ] **Step 2: Add `ci_app` to `cli.py`**

In `src/coding_bot/cli.py`, add after the `conventions_app` block:

```python
# ─── ci sub-app ──────────────────────────────────────────────────────────────
ci_app = typer.Typer(name="ci", help="CI helpers.", no_args_is_help=True)
app.add_typer(ci_app, name="ci")


@ci_app.command("check")
def ci_check_cmd(
    repo_path: Path = typer.Argument(..., help="Path to pd-* repo"),
    timeout: int = typer.Option(900, "--timeout"),
) -> None:
    """Run `make ci AI=1` in a pd-* repo and report pass/fail."""
    from coding_bot.helpers.ci_check import run_make_ci
    result = run_make_ci(repo_path, timeout=timeout)
    if result.passed:
        console.print(f"[green]✅ CI passed[/green] ({repo_path.name})")
    else:
        console.print(f"[red]❌ CI failed[/red] ({repo_path.name})")
        console.print(result.excerpt)
        raise typer.Exit(1)


@ci_app.command("triage")
def ci_triage_cmd(
    repo: str = typer.Argument(..., help="owner/repo"),
    pr_number: int = typer.Option(..., "--pr"),
    log_file: Path = typer.Option(..., "--log-file"),
) -> None:
    """Post a CI failure summary comment on a PR."""
    from coding_bot import gh as gh_module
    excerpt = log_file.read_text()[:2000] if log_file.exists() else "(no log)"
    body = f"## CI failure summary\n\n```\n{excerpt}\n```\n"
    gh_module.issue_comment(repo, pr_number, body)
    console.print(f"[green]Posted CI triage comment on {repo}#{pr_number}[/green]")
```

- [ ] **Step 3: Add `spec from-issue-finalize` to `spec_app`**

In `src/coding_bot/cli.py`, add to `spec_app`:

```python
@spec_app.command("from-issue-finalize")
def spec_from_issue_finalize_cmd(
    repo: str = typer.Option(..., "--repo"),
    spec_issue: int = typer.Option(..., "--spec-issue"),
    spec_path: Path = typer.Option(..., "--spec-path"),
    force: bool = typer.Option(False, "--force"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Wire a written spec file back to its issue (add Spec: line + open draft PR)."""
    from coding_bot import gh as gh_module
    import re

    issue = gh_module.issue_view(repo, spec_issue)
    body = issue.get("body") or ""

    spec_line_re = re.compile(r"^Spec:\s*\S.*$", re.MULTILINE)
    if spec_line_re.search(body) and not force:
        console.print(f"[yellow]Issue #{spec_issue} already has a Spec: line. Use --force to override.[/yellow]")
        raise typer.Exit(0)

    new_body = body.rstrip() + f"\n\nSpec: {spec_path}\n"
    if not dry_run:
        gh_module.issue_edit_body(repo, spec_issue, new_body)

    pr_title = f"spec: {issue.get('title', f'issue-{spec_issue}')}"
    pr_body = f"Closes #{spec_issue}\n\nSpec draft for issue #{spec_issue}."
    if not dry_run:
        gh_module.pr_create_draft(repo, title=pr_title, body=pr_body,
                                   head=f"spec/{spec_issue}")
        console.print(f"[green]Wired spec to issue #{spec_issue} and opened draft PR.[/green]")
    else:
        console.print(f"[yellow]Dry run: would add Spec: line to #{spec_issue} and open draft PR.[/yellow]")
```

- [ ] **Step 4: Add `issue_edit_body` and `pr_create_draft` to `gh.py`**

In `src/coding_bot/gh.py`, add:

```python
def issue_edit_body(repo: str, number: int, body: str) -> None:
    _run(["gh", "issue", "edit", str(number), "--repo", repo, "--body", body])


def pr_create_draft(repo: str, *, title: str, body: str, head: str) -> None:
    _run([
        "gh", "pr", "create", "--repo", repo,
        "--title", title, "--body", body, "--head", head, "--draft",
    ])


def issue_view(repo: str, number: int) -> dict[str, Any]:
    return json.loads(_run([
        "gh", "issue", "view", str(number), "--repo", repo,
        "--json", "number,title,body,labels,state",
    ]))
```

- [ ] **Step 5: Add `label migrate-claude-ok` command**

In `src/coding_bot/cli.py`, add to `label_app`:

```python
@label_app.command("migrate-claude-ok")
def label_migrate_claude_ok_cmd(
    repos: list[str] = typer.Option([], "--repo", "-r"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Migrate legacy 'claude-ok' label to 'bot:ship-issue-ready' across repos."""
    from coding_bot import gh as gh_module
    total = 0
    for repo in repos:
        issues = gh_module.issue_list(repo, labels=["claude-ok"], limit=200)
        for issue in issues:
            total += 1
            if not dry_run:
                gh_module.issue_edit(
                    repo, issue["number"],
                    add_labels=["bot:ship-issue-ready"],
                    remove_labels=["claude-ok"],
                )
            console.print(f"  {'[dry]' if dry_run else ''} {repo}#{issue['number']}: claude-ok → bot:ship-issue-ready")
    console.print(f"\n[green]{'Would migrate' if dry_run else 'Migrated'} {total} issues.[/green]")
```

- [ ] **Step 6: Add `conventions sync` command**

In `src/coding_bot/cli.py`, add to `conventions_app`:

```python
@conventions_app.command("sync")
def conventions_sync_cmd(
    repo: Path = typer.Argument(..., help="Path to pd-* repo"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Sync workspace conventions block into repo CONVENTIONS.md."""
    from coding_bot.helpers.conventions import sync_workspace_block
    target = repo / "CONVENTIONS.md"
    if not target.exists():
        console.print(f"[yellow]{target} does not exist.[/yellow]")
        raise typer.Exit(1)
    if dry_run:
        console.print(f"[yellow]Dry run: would sync workspace block into {target}[/yellow]")
        return
    lines_changed = sync_workspace_block(target)
    console.print(f"[green]Synced {lines_changed} lines into {target}[/green]")
```

- [ ] **Step 7: Smoke-test the new commands**

```bash
cd /workspaces/ocr-container/coding-bot
uv run coding-bot ci --help
uv run coding-bot spec from-issue-finalize --help
uv run coding-bot label migrate-claude-ok --help
uv run coding-bot conventions sync --help
```

Expected: all print help without ImportError.

- [ ] **Step 8: Commit**

```bash
cd /workspaces/ocr-container/coding-bot
git add src/coding_bot/cli.py src/coding_bot/helpers/conventions.py src/coding_bot/gh.py
git commit -m "feat(cli): add ci sub-app, spec from-issue-finalize, label migrate-claude-ok, conventions sync"
```

---

## Acceptance criteria

1. `make ci AI=1` exits 0 — all unit tests pass, ruff + mypy clean.
2. All 14 helper modules exist under `src/coding_bot/helpers/`.
3. All 4 hook modules exist under `src/coding_bot/hooks/`.
4. `coding-bot spec lint <file>` lints a spec and exits nonzero on errors.
5. `coding-bot label lint --repo X` reports single-select violations.
6. `coding-bot label arm X 42` arms an issue (with real gh creds).
7. `coding-bot hook trailing-todos <file>` correctly detects unpaired markers.
8. `coding-bot triage sweep <repo>` prints bucketed issues.
9. `coding-bot wip-pr status` prints PR state without error.
10. `coding-bot budget add/list/status` round-trips through cost.db.
11. `coding-bot db backup-cost` copies cost.db (if it exists).
12. `coding-bot setup` reports group/dir status without crashing.
13. `coding-bot ci check <path>` runs make ci and reports pass/fail.
14. `coding-bot conventions sync <repo>` syncs workspace block without error.
15. `coding-bot spec from-issue-finalize --help` prints usage.
16. `coding-bot label migrate-claude-ok --help` prints usage.
17. Tag `v0.4-m4` exists.
18. No scripts in `scripts/` were deleted (that happens in M6).
