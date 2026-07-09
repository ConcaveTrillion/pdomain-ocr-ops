---
status: complete
---

# se-assist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the `se:se-semanticate-review` skill inside `se-llm-skills` — a detection script that finds semantic markup candidates in SE ebook XHTML, an AI skill that classifies and edits them, and an HTML review report generated from the actual git diff.

**Architecture:** Detection script (`detect_semantics.py`) walks XHTML files and outputs a JSON candidate list. The AI skill (`skill.md`) fetches the live SE vocab + manual (with bundled fallbacks), classifies each candidate using MW lookup where needed, edits files directly, then calls `generate_review.py` to produce an HTML report from the real `git diff` plus AI-authored `reasoning.json`.

**Tech Stack:** Python 3.10+, lxml (already in SE producer environments via se-tools), stdlib only otherwise (json, re, html, webbrowser, urllib). No new pip dependencies.

**Repo:** `/workspaces/ocr-container/se-llm-skills/`
**Spec:** `docs/superpowers/specs/2026-05-15-se-assist-design.md`

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `skills/se-semanticate-review/skill.md` | CREATE | Skill instruction — invocation, workflow, classification rules |
| `skills/se-semanticate-review/vocab-fallback.html` | CREATE | SE vocab fallback (fetched from standardebooks.org/vocab/1.0) |
| `skills/se-semanticate-review/manual-fallback.html` | CREATE | SE manual fallback (fetched from standardebooks.org/manual/latest/single-page) |
| `skills/se-semanticate-review/scripts/detect_semantics.py` | CREATE | Candidate finder — walks XHTML, outputs JSON |
| `skills/se-semanticate-review/scripts/generate_review.py` | CREATE | Diff + reasoning.json → HTML report |
| `tests/conftest.py` | CREATE | sys.path setup so tests can import scripts directly |
| `tests/fixtures/chapter_abbr.xhtml` | CREATE | Fixture with abbr-title, abbr-era, initials candidates |
| `tests/fixtures/chapter_italics.xhtml` | CREATE | Fixture with i-untyped, i-missing-lang, em-candidate |
| `tests/fixtures/sample.diff` | CREATE | Sample unified diff for generate_review tests |
| `tests/fixtures/sample_reasoning.json` | CREATE | Sample reasoning.json for generate_review tests |
| `tests/test_detect_semantics.py` | CREATE | Unit tests for detect_semantics.py |
| `tests/test_generate_review.py` | CREATE | Unit tests for generate_review.py |

---

## Task 1: Plugin scaffold (plugin.json + directory skeleton)

**Files:**
- Create: `skills/se-semanticate-review/.gitkeep` (reserves directory)
- Create: `skills/se-semanticate-review/scripts/.gitkeep`
- Create: `dist/claude/.claude-plugin/plugin.json` (dev-time stub for local testing)

> Note: `dist/` is gitignored — this stub lets you load the plugin with
> `claude --plugin-dir dist/claude` while the build adapter is TBD.

- [ ] **Step 1: Create directory skeleton**

```bash
mkdir -p skills/se-semanticate-review/scripts
mkdir -p dist/claude/.claude-plugin
mkdir -p dist/claude/skills/se-semanticate-review/scripts
touch skills/se-semanticate-review/scripts/.gitkeep
```

- [ ] **Step 2: Write plugin.json**

```json
{
  "name": "se-llm-skills",
  "version": "0.1.0",
  "description": "AI skills for Standard Ebooks ebook production.",
  "skills": "skills/"
}
```

Save to `dist/claude/.claude-plugin/plugin.json`.

- [ ] **Step 3: Verify plugin loads (manual check)**

```bash
# From se-llm-skills root — should list the skill without errors
claude --plugin-dir dist/claude --print "list available skills" 2>&1 | head -5
```

If `claude` CLI is not available in PATH, skip this step — the plugin can be verified after Task 6 is complete.

- [ ] **Step 4: Commit scaffold**

```bash
git add skills/ dist/.gitkeep 2>/dev/null || true
# dist/ is gitignored — commit only the skills skeleton
git add skills/se-semanticate-review/scripts/.gitkeep
git commit -m "chore(se): scaffold se-semanticate-review skill directory"
```

---

## Task 2: Test fixtures and conftest

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/fixtures/chapter_abbr.xhtml`
- Create: `tests/fixtures/chapter_italics.xhtml`
- Create: `tests/fixtures/sample.diff`
- Create: `tests/fixtures/sample_reasoning.json`

- [ ] **Step 1: Create conftest.py**

```python
# tests/conftest.py
import sys
from pathlib import Path

# Allow tests to import scripts directly
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "se-semanticate-review" / "scripts"))
```

- [ ] **Step 2: Create chapter_abbr.xhtml fixture**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB">
<head><title>Chapter 1</title></head>
<body>
<section epub:type="chapter">
<p>Mr. Smith went to see Dr. Jones about his condition.</p>
<p>It happened in AD 1066, before BC 44 when Caesar died.</p>
<p>J. R. R. Tolkien and T. S. Eliot were contemporaries.</p>
<p>She had a pint at the King's Head with Mrs. Wilson.</p>
<p>Already wrapped: <abbr epub:type="z3998:name-title">Mr.</abbr> Brown.</p>
<p>End of sentence: she loved music, etc.</p>
</section>
</body>
</html>
```

- [ ] **Step 3: Create chapter_italics.xhtml fixture**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB">
<head><title>Chapter 2</title></head>
<body>
<section epub:type="chapter">
<p>He read <i>The Times</i> every morning.</p>
<p>She had studied <i epub:type="se:name.publication.book">Le Rouge et le Noir</i> at school.</p>
<p>Perhaps <em>he</em> was the one who left.</p>
<p>She felt <em>très fatiguée</em> after the journey.</p>
<p>The bonobo is <i epub:type="z3998:taxonomy">Pan paniscus</i>.</p>
</section>
</body>
</html>
```

- [ ] **Step 4: Create sample.diff fixture**

```
--- a/src/epub/text/chapter-1.xhtml
+++ b/src/epub/text/chapter-1.xhtml
@@ -4,7 +4,7 @@
 <section epub:type="chapter">
-<p>Mr. Smith went to see Dr. Jones about his condition.</p>
+<p><abbr epub:type="z3998:name-title">Mr.</abbr> Smith went to see <abbr epub:type="z3998:name-title">Dr.</abbr> Jones about his condition.</p>
 <p>It happened in AD 1066.</p>
 </section>
```

- [ ] **Step 5: Create sample_reasoning.json fixture**

```json
[
  {
    "location": "src/epub/text/chapter-1.xhtml:5",
    "type": "abbr-title",
    "reasoning": "Honorific preceding a personal name — requires z3998:name-title wrapper.",
    "manual_ref": "§8.10.3 — Abbreviations for Names and Titles",
    "manual_url": "https://standardebooks.org/manual/latest/single-page"
  }
]
```

- [ ] **Step 6: Commit**

```bash
git add tests/
git commit -m "test: add fixtures and conftest for se-semanticate-review"
```

---

## Task 3: detect_semantics.py — Tier 1 (abbr-title, abbr-era, initials)

**Files:**
- Create: `skills/se-semanticate-review/scripts/detect_semantics.py`
- Create: `tests/test_detect_semantics.py`

- [ ] **Step 1: Write failing tests for Tier 1 detection**

```python
# tests/test_detect_semantics.py
import json
from pathlib import Path
import detect_semantics

FIXTURES = Path(__file__).parent / "fixtures"


def test_abbr_title_bare_mr_detected(tmp_path):
    xhtml = FIXTURES / "chapter_abbr.xhtml"
    candidates = detect_semantics.process_file(xhtml)
    abbr_title = [c for c in candidates if c["type"] == "abbr-title"]
    texts = [c["text"] for c in abbr_title]
    assert "Mr." in texts
    assert "Dr." in texts
    assert "Mrs." in texts


def test_abbr_title_already_wrapped_skipped(tmp_path):
    xhtml = FIXTURES / "chapter_abbr.xhtml"
    candidates = detect_semantics.process_file(xhtml)
    abbr_title = [c for c in candidates if c["type"] == "abbr-title"]
    # "Mr. Brown" is already inside <abbr>, should not appear twice
    # The fixture has one bare "Mr." and one wrapped "Mr." — only bare should appear
    lines = [c["line"] for c in abbr_title if c["text"] == "Mr."]
    # The wrapped Mr. is on line 9 — should not be in candidates
    assert all(line != 9 for line in lines)


def test_abbr_title_eoc_detected():
    xhtml = FIXTURES / "chapter_abbr.xhtml"
    candidates = detect_semantics.process_file(xhtml)
    eoc_candidates = [c for c in candidates if c.get("eoc") is True]
    assert len(eoc_candidates) >= 1  # "etc." at end of sentence


def test_abbr_era_detected():
    xhtml = FIXTURES / "chapter_abbr.xhtml"
    candidates = detect_semantics.process_file(xhtml)
    era = [c for c in candidates if c["type"] == "abbr-era"]
    texts = [c["text"] for c in era]
    assert "AD" in texts or "AD " in [t.strip() for t in texts]
    assert "BC" in texts or "BC " in [t.strip() for t in texts]


def test_initials_detected():
    xhtml = FIXTURES / "chapter_abbr.xhtml"
    candidates = detect_semantics.process_file(xhtml)
    initials = [c for c in candidates if c["type"] == "initials"]
    assert len(initials) >= 1


def test_candidate_has_required_fields():
    xhtml = FIXTURES / "chapter_abbr.xhtml"
    candidates = detect_semantics.process_file(xhtml)
    assert len(candidates) > 0
    for c in candidates:
        assert "file" in c
        assert "line" in c
        assert "type" in c
        assert "text" in c
        assert "context" in c
        assert "current_markup" in c
        assert "suggested_markup" in c
        assert "mw_lookup" in c


def test_context_length():
    xhtml = FIXTURES / "chapter_abbr.xhtml"
    candidates = detect_semantics.process_file(xhtml)
    for c in candidates:
        # Context should be non-empty and not excessively long
        assert len(c["context"]) > 0
        assert len(c["context"]) <= 500


def test_cli_outputs_json(tmp_path):
    import subprocess, sys
    script = Path(__file__).parent.parent / "skills" / "se-semanticate-review" / "scripts" / "detect_semantics.py"
    result = subprocess.run(
        [sys.executable, str(script), str(FIXTURES / "chapter_abbr.xhtml")],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /workspaces/ocr-container/se-llm-skills
python -m pytest tests/test_detect_semantics.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'detect_semantics'`

- [ ] **Step 3: Create detect_semantics.py with Tier 1 implementation**

```python
#!/usr/bin/env python3
"""
detect_semantics.py — SE ebook semantic markup candidate finder.
Outputs JSON array to stdout.
Usage: python3 detect_semantics.py <ebook-root-or-xhtml-file>
"""
import json
import re
import sys
from pathlib import Path
from lxml import etree

XHTML_NS = "http://www.w3.org/1999/xhtml"
EPUB_NS = "http://www.idpf.org/2007/ops"
XML_NS = "http://www.w3.org/XML/1998/namespace"
EPUB_TYPE = f"{{{EPUB_NS}}}type"
XML_LANG = f"{{{XML_NS}}}lang"

HONORIFICS_RE = re.compile(
    r"(?<![A-Za-z])(Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.|Mme\.|Mlle\.|Messrs\.|Esq\.|Hon\.)(?![A-Za-z])"
)
ERA_RE = re.compile(r"\b(BC|AD|BCE|CE)(\.)?")
INITIALS_RE = re.compile(r"\b(?:[A-Z]\.\s*){2,}|\b([A-Z]\.)\s+(?=[A-Z][a-z])")

CONTEXT = 200

# Tags whose subtrees we skip entirely (already marked up or irrelevant)
SKIP_TAGS = {
    f"{{{XHTML_NS}}}abbr",
    f"{{{XHTML_NS}}}script",
    f"{{{XHTML_NS}}}style",
}


def xhtml_files(path: Path) -> list:
    if path.is_file() and path.suffix == ".xhtml":
        return [path]
    return sorted(path.glob("src/epub/text/*.xhtml"))


def text_context(text: str, start: int, end: int) -> str:
    lo = max(0, start - CONTEXT)
    hi = min(len(text), end + CONTEXT)
    prefix = "…" if lo > 0 else ""
    suffix = "…" if hi < len(text) else ""
    return prefix + text[lo:hi] + suffix


def is_eoc(text: str, match_end: int) -> bool:
    """True if the abbreviation period also ends the sentence."""
    remaining = text[match_end:].lstrip(" \t")
    return (not remaining) or remaining[0] in ('"', "”", "'", "’", "\n")


def walk_text(elem, skip_tags: set):
    """Yield (text_str, source_elem) for all text not inside skip_tags subtrees."""
    if elem.tag in skip_tags:
        return
    if elem.text:
        yield (elem.text, elem)
    for child in elem:
        yield from walk_text(child, skip_tags)
        if child.tail:
            yield (child.tail, child)


def process_file(filepath: Path) -> list:
    filepath = Path(filepath)
    candidates = []
    parser = etree.XMLParser(load_dtd=False, no_network=True, recover=True)
    try:
        tree = etree.parse(str(filepath), parser)
    except etree.XMLSyntaxError:
        return []
    root = tree.getroot()
    fp = str(filepath)

    for text, elem in walk_text(root, SKIP_TAGS):
        line = getattr(elem, "sourceline", 0) or 0

        # abbr-title
        for m in HONORIFICS_RE.finditer(text):
            eoc = is_eoc(text, m.end())
            suggested = f'<abbr epub:type="z3998:name-title"'
            if eoc:
                suggested += ' class="eoc"'
            suggested += f">{m.group()}</abbr>"
            candidates.append({
                "file": fp,
                "line": line,
                "type": "abbr-title",
                "text": m.group(),
                "context": text_context(text, m.start(), m.end()),
                "current_markup": m.group(),
                "suggested_markup": suggested,
                "mw_lookup": False,
                "eoc": eoc,
            })

        # abbr-era
        for m in ERA_RE.finditer(text):
            has_period = bool(m.group(2))
            era_text = m.group(1)
            suggested = f'<abbr epub:type="se:era z3998:initialism">{era_text}</abbr>'
            note = "trailing period should be removed" if has_period else None
            entry = {
                "file": fp,
                "line": line,
                "type": "abbr-era",
                "text": m.group(),
                "context": text_context(text, m.start(), m.end()),
                "current_markup": m.group(),
                "suggested_markup": suggested,
                "mw_lookup": False,
            }
            if note:
                entry["note"] = note
            candidates.append(entry)

        # initials
        for m in INITIALS_RE.finditer(text):
            initials_str = m.group().rstrip()
            parts = re.findall(r"[A-Z]\.", initials_str)
            etype = "z3998:personal-name" if len(parts) > 3 else "z3998:given-name"
            suggested = f'<abbr epub:type="{etype}">{initials_str}</abbr>'
            candidates.append({
                "file": fp,
                "line": line,
                "type": "initials",
                "text": initials_str,
                "context": text_context(text, m.start(), m.end()),
                "current_markup": initials_str,
                "suggested_markup": suggested,
                "mw_lookup": False,
            })

    return candidates


def main():
    if len(sys.argv) != 2:
        print("Usage: detect_semantics.py <path>", file=sys.stderr)
        sys.exit(1)
    path = Path(sys.argv[1])
    files = xhtml_files(path)
    all_candidates = []
    for f in files:
        all_candidates.extend(process_file(f))
    print(json.dumps(all_candidates, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run Tier 1 tests**

```bash
cd /workspaces/ocr-container/se-llm-skills
python -m pytest tests/test_detect_semantics.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add skills/se-semanticate-review/scripts/detect_semantics.py tests/
git commit -m "feat(se): detect_semantics.py Tier 1 — abbr-title, abbr-era, initials"
```

---

## Task 4: detect_semantics.py — Tier 2 (i-untyped, i-missing-lang, em-candidate)

**Files:**
- Modify: `skills/se-semanticate-review/scripts/detect_semantics.py`
- Modify: `tests/test_detect_semantics.py`

- [ ] **Step 1: Add failing tests for Tier 2**

Append to `tests/test_detect_semantics.py`:

```python
def test_i_untyped_detected():
    xhtml = FIXTURES / "chapter_italics.xhtml"
    candidates = detect_semantics.process_file(xhtml)
    i_untyped = [c for c in candidates if c["type"] == "i-untyped"]
    texts = [c["text"] for c in i_untyped]
    assert "The Times" in texts


def test_i_with_epub_type_not_flagged_as_untyped():
    xhtml = FIXTURES / "chapter_italics.xhtml"
    candidates = detect_semantics.process_file(xhtml)
    i_untyped = [c for c in candidates if c["type"] == "i-untyped"]
    # taxonomy <i> has epub:type — should not appear
    texts = [c["text"] for c in i_untyped]
    assert "Pan paniscus" not in texts


def test_i_missing_lang_detected():
    xhtml = FIXTURES / "chapter_italics.xhtml"
    candidates = detect_semantics.process_file(xhtml)
    missing_lang = [c for c in candidates if c["type"] == "i-missing-lang"]
    # "Le Rouge et le Noir" has epub:type but no xml:lang
    texts = [c["text"] for c in missing_lang]
    assert "Le Rouge et le Noir" in texts


def test_em_candidate_detected():
    xhtml = FIXTURES / "chapter_italics.xhtml"
    candidates = detect_semantics.process_file(xhtml)
    em = [c for c in candidates if c["type"] == "em-candidate"]
    texts = [c["text"] for c in em]
    assert "he" in texts
    assert "très fatiguée" in texts


def test_em_foreign_sets_mw_lookup():
    xhtml = FIXTURES / "chapter_italics.xhtml"
    candidates = detect_semantics.process_file(xhtml)
    em = [c for c in candidates if c["type"] == "em-candidate"]
    foreign_em = [c for c in em if c["text"] == "très fatiguée"]
    assert len(foreign_em) == 1
    assert foreign_em[0]["mw_lookup"] is True


def test_i_untyped_has_parent_text():
    xhtml = FIXTURES / "chapter_italics.xhtml"
    candidates = detect_semantics.process_file(xhtml)
    i_untyped = [c for c in candidates if c["type"] == "i-untyped"]
    for c in i_untyped:
        assert "parent_text" in c
        assert len(c["parent_text"]) > 0
```

- [ ] **Step 2: Run new tests to confirm they fail**

```bash
cd /workspaces/ocr-container/se-llm-skills
python -m pytest tests/test_detect_semantics.py::test_i_untyped_detected -v
```

Expected: FAIL — `AssertionError`

- [ ] **Step 3: Add Tier 2 detection to detect_semantics.py**

Add these constants near the top of `detect_semantics.py` (after the existing constants):

```python
# Heuristic: text that likely needs MW lookup (non-ASCII or common foreign particles)
_FOREIGN_HINT_RE = re.compile(
    r"[^\x00-\x7F]"  # non-ASCII character
    r"|(?<!\w)(par|mon|ma|les|des|une|von|der|die|il|la|el|en|du|au|très|et|le)\b",
    re.IGNORECASE,
)
```

Add a `needs_mw_lookup(text)` function:

```python
def needs_mw_lookup(text: str) -> bool:
    return bool(_FOREIGN_HINT_RE.search(text))
```

Add Tier 2 detection inside `process_file`, after the existing text-walking loop, before `return candidates`:

```python
    # --- Tier 2: element-level candidates ---

    # i-untyped: <i> with no epub:type and no xml:lang
    for elem in root.iter(f"{{{XHTML_NS}}}i"):
        has_type = elem.get(EPUB_TYPE)
        has_lang = elem.get(XML_LANG)
        if has_type or has_lang:
            continue
        text = "".join(elem.itertext())
        parent = elem.getparent()
        p_text = "".join(parent.itertext()) if parent is not None else ""
        current = etree.tostring(elem, encoding="unicode")
        candidates.append({
            "file": fp,
            "line": getattr(elem, "sourceline", 0) or 0,
            "type": "i-untyped",
            "text": text,
            "context": p_text[max(0, p_text.find(text) - CONTEXT):p_text.find(text) + len(text) + CONTEXT],
            "parent_text": p_text,
            "current_markup": current,
            "suggested_markup": f'<i xml:lang="???">{text}</i>',
            "mw_lookup": needs_mw_lookup(text),
        })

    # i-missing-lang: <i epub:type="se:name.publication.*"> without xml:lang
    for elem in root.iter(f"{{{XHTML_NS}}}i"):
        etype = elem.get(EPUB_TYPE) or ""
        if "se:name.publication." not in etype:
            continue
        if elem.get(XML_LANG):
            continue
        text = "".join(elem.itertext())
        parent = elem.getparent()
        p_text = "".join(parent.itertext()) if parent is not None else ""
        current = etree.tostring(elem, encoding="unicode")
        candidates.append({
            "file": fp,
            "line": getattr(elem, "sourceline", 0) or 0,
            "type": "i-missing-lang",
            "text": text,
            "context": p_text,
            "parent_text": p_text,
            "current_markup": current,
            "suggested_markup": f'<i epub:type="{etype}" xml:lang="???">{text}</i>',
            "mw_lookup": False,
        })

    # em-candidate: all <em> elements
    for elem in root.iter(f"{{{XHTML_NS}}}em"):
        text = "".join(elem.itertext())
        parent = elem.getparent()
        p_text = "".join(parent.itertext()) if parent is not None else ""
        current = etree.tostring(elem, encoding="unicode")
        candidates.append({
            "file": fp,
            "line": getattr(elem, "sourceline", 0) or 0,
            "type": "em-candidate",
            "text": text,
            "context": p_text[max(0, p_text.find(text) - CONTEXT):p_text.find(text) + len(text) + CONTEXT],
            "parent_text": p_text,
            "current_markup": current,
            "suggested_markup": "<em>" + text + "</em>",
            "mw_lookup": needs_mw_lookup(text),
        })
```

- [ ] **Step 4: Run all tests**

```bash
cd /workspaces/ocr-container/se-llm-skills
python -m pytest tests/test_detect_semantics.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add skills/se-semanticate-review/scripts/detect_semantics.py tests/test_detect_semantics.py
git commit -m "feat(se): detect_semantics.py Tier 2 — i-untyped, i-missing-lang, em-candidate"
```

---

## Task 5: generate_review.py — diff + reasoning → HTML

**Files:**
- Create: `skills/se-semanticate-review/scripts/generate_review.py`
- Create: `tests/test_generate_review.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_generate_review.py
import json
from pathlib import Path
import generate_review

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_diff_returns_hunks():
    diff_text = (FIXTURES / "sample.diff").read_text()
    hunks = generate_review.parse_diff(diff_text)
    assert len(hunks) >= 1
    assert hunks[0].filepath == "src/epub/text/chapter-1.xhtml"
    assert len(hunks[0].removed_lines) >= 1
    assert len(hunks[0].added_lines) >= 1


def test_parse_diff_extracts_line_numbers():
    diff_text = (FIXTURES / "sample.diff").read_text()
    hunks = generate_review.parse_diff(diff_text)
    assert hunks[0].old_start == 4


def test_html_contains_before_after():
    diff_text = (FIXTURES / "sample.diff").read_text()
    reasoning = json.loads((FIXTURES / "sample_reasoning.json").read_text())
    output = generate_review.make_html(
        hunks=generate_review.parse_diff(diff_text),
        reasoning_list=reasoning,
        vocab_source="live",
        manual_source="live (v1.8.7)",
    )
    assert "Mr." in output
    assert "z3998:name-title" in output


def test_html_contains_manual_ref():
    diff_text = (FIXTURES / "sample.diff").read_text()
    reasoning = json.loads((FIXTURES / "sample_reasoning.json").read_text())
    output = generate_review.make_html(
        hunks=generate_review.parse_diff(diff_text),
        reasoning_list=reasoning,
        vocab_source="live",
        manual_source="live (v1.8.7)",
    )
    assert "§8.10.3" in output
    assert "standardebooks.org/manual/latest/single-page" in output


def test_html_has_data_attributes():
    diff_text = (FIXTURES / "sample.diff").read_text()
    reasoning = json.loads((FIXTURES / "sample_reasoning.json").read_text())
    output = generate_review.make_html(
        hunks=generate_review.parse_diff(diff_text),
        reasoning_list=reasoning,
        vocab_source="live",
        manual_source="live (v1.8.7)",
    )
    assert 'data-status="applied"' in output


def test_skipped_section_present_when_skipped():
    reasoning = [
        {
            "location": "src/epub/text/chapter-1.xhtml:5",
            "type": "em-candidate",
            "status": "skipped",
            "reasoning": "Ambiguous context — could be emphasis or foreign.",
            "manual_ref": "§8.2.2 — Emphasis",
            "manual_url": "https://standardebooks.org/manual/latest/single-page",
        }
    ]
    output = generate_review.make_html(
        hunks=[],
        reasoning_list=reasoning,
        vocab_source="fallback",
        manual_source="fallback (v1.8.7)",
    )
    assert "Skipped" in output
    assert "Ambiguous context" in output
    assert "fallback" in output
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /workspaces/ocr-container/se-llm-skills
python -m pytest tests/test_generate_review.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'generate_review'`

- [ ] **Step 3: Create generate_review.py**

```python
#!/usr/bin/env python3
"""
generate_review.py — Generate HTML review from git diff + AI reasoning.json.
Usage: python3 generate_review.py <diff-file> <reasoning-json> <output-html>
       [--vocab-source=live|fallback] [--manual-source=<description>]
"""
import html as htmllib
import json
import re
import sys
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Hunk:
    filepath: str
    old_start: int
    new_start: int
    removed_lines: list = field(default_factory=list)
    added_lines: list = field(default_factory=list)


def parse_diff(diff_text: str) -> list:
    hunks = []
    current_file = None
    current_hunk = None

    for line in diff_text.splitlines():
        if line.startswith("--- "):
            continue
        if line.startswith("+++ "):
            raw = line[4:].strip()
            current_file = raw[2:] if raw.startswith("b/") else raw
            continue
        if line.startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            if m:
                if current_hunk is not None:
                    hunks.append(current_hunk)
                current_hunk = Hunk(
                    filepath=current_file or "",
                    old_start=int(m.group(1)),
                    new_start=int(m.group(2)),
                )
            continue
        if current_hunk is None:
            continue
        if line.startswith("-"):
            current_hunk.removed_lines.append(line[1:])
        elif line.startswith("+"):
            current_hunk.added_lines.append(line[1:])

    if current_hunk is not None:
        hunks.append(current_hunk)
    return hunks


def _esc(text: str) -> str:
    return htmllib.escape(text)


def _reasoning_key(r: dict) -> str:
    return r.get("location", "")


def make_html(hunks: list, reasoning_list: list, vocab_source: str, manual_source: str) -> str:
    # Index reasoning by location
    reasoning_by_loc = {r.get("location", ""): r for r in reasoning_list}

    applied = [h for h in hunks]
    skipped = [r for r in reasoning_list if r.get("status") == "skipped"]

    # Build change divs for applied hunks
    applied_html = ""
    for hunk in applied:
        loc = f"{hunk.filepath}:{hunk.old_start}"
        r = reasoning_by_loc.get(loc, {})
        removed = "\n".join(hunk.removed_lines)
        added = "\n".join(hunk.added_lines)
        reasoning_text = r.get("reasoning", "")
        manual_ref = r.get("manual_ref", "")
        manual_url = r.get("manual_url", "https://standardebooks.org/manual/latest/single-page")
        change_type = r.get("type", "other")

        ref_link = ""
        if manual_ref:
            ref_link = f'<a href="{_esc(manual_url)}" target="_blank">{_esc(manual_ref)}</a>'

        applied_html += f"""
    <div class="change" data-file="{_esc(hunk.filepath)}" data-line="{hunk.old_start}" data-status="applied" data-type="{_esc(change_type)}">
      <div class="location">{_esc(hunk.filepath)}:{hunk.old_start}</div>
      <div class="diff">
        <div class="removed"><code>{_esc(removed)}</code></div>
        <div class="added"><code>{_esc(added)}</code></div>
      </div>
      <div class="reasoning">{_esc(reasoning_text)} {ref_link}</div>
    </div>"""

    # Build skipped divs
    skipped_html = ""
    for r in skipped:
        loc = r.get("location", "")
        reasoning_text = r.get("reasoning", "")
        manual_ref = r.get("manual_ref", "")
        manual_url = r.get("manual_url", "https://standardebooks.org/manual/latest/single-page")

        ref_link = ""
        if manual_ref:
            ref_link = f'<a href="{_esc(manual_url)}" target="_blank">{_esc(manual_ref)}</a>'

        skipped_html += f"""
    <div class="change skipped" data-location="{_esc(loc)}" data-status="skipped">
      <div class="location">{_esc(loc)}</div>
      <div class="reasoning">{_esc(reasoning_text)} {ref_link}</div>
    </div>"""

    vocab_note = f"Vocab: {_esc(vocab_source)} | Manual: {_esc(manual_source)}"
    if "fallback" in vocab_source or "fallback" in manual_source:
        vocab_note += " ⚠ fallback used — verify edge cases against live manual"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Semantic Markup Review</title>
<style>
  body {{ font-family: monospace; max-width: 960px; margin: 2rem auto; padding: 0 1rem; }}
  h1 {{ font-size: 1.4rem; }}
  .meta {{ color: #666; font-size: 0.85rem; margin-bottom: 1.5rem; }}
  details {{ margin-bottom: 1rem; border: 1px solid #ddd; border-radius: 4px; }}
  summary {{ padding: 0.5rem 1rem; cursor: pointer; background: #f5f5f5; font-weight: bold; }}
  .change {{ padding: 0.75rem 1rem; border-bottom: 1px solid #eee; }}
  .change:last-child {{ border-bottom: none; }}
  .location {{ color: #888; font-size: 0.8rem; margin-bottom: 0.4rem; }}
  .removed {{ background: #ffeef0; padding: 0.3rem 0.5rem; border-radius: 3px; margin-bottom: 0.2rem; }}
  .added {{ background: #e6ffed; padding: 0.3rem 0.5rem; border-radius: 3px; }}
  .reasoning {{ margin-top: 0.5rem; color: #333; font-size: 0.9rem; }}
  .reasoning a {{ color: #0066cc; }}
  .skipped .location {{ color: #c44; }}
</style>
</head>
<body>
<h1>Semantic Markup Review</h1>
<p class="meta">{vocab_note}</p>

<details open>
  <summary>Applied Changes ({len(applied)})</summary>
  {applied_html or "<p style='padding:1rem;color:#666'>No changes applied.</p>"}
</details>

<details{"" if skipped else ""}>
  <summary>Skipped — Needs Human Judgment ({len(skipped)})</summary>
  {skipped_html or "<p style='padding:1rem;color:#666'>Nothing skipped.</p>"}
</details>
</body>
</html>"""


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("diff_file")
    parser.add_argument("reasoning_json")
    parser.add_argument("output_html")
    parser.add_argument("--vocab-source", default="live")
    parser.add_argument("--manual-source", default="live")
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()

    diff_text = Path(args.diff_file).read_text()
    reasoning_list = json.loads(Path(args.reasoning_json).read_text())
    output = make_html(
        hunks=parse_diff(diff_text),
        reasoning_list=reasoning_list,
        vocab_source=args.vocab_source,
        manual_source=args.manual_source,
    )
    out_path = Path(args.output_html)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(output, encoding="utf-8")
    print(f"Review written to: {out_path}", file=sys.stderr)
    if args.open:
        webbrowser.open(f"file://{out_path.resolve()}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

```bash
cd /workspaces/ocr-container/se-llm-skills
python -m pytest tests/test_generate_review.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add skills/se-semanticate-review/scripts/generate_review.py tests/test_generate_review.py
git commit -m "feat(se): generate_review.py — diff + reasoning.json → HTML report"
```

---

## Task 6: Fetch and bundle fallback reference files

**Files:**
- Create: `skills/se-semanticate-review/vocab-fallback.html`
- Create: `skills/se-semanticate-review/manual-fallback.html`

- [ ] **Step 1: Fetch SE vocab and save with dated header**

```bash
python3 - <<'EOF'
import urllib.request, datetime
today = datetime.date.today().isoformat()

url = "https://standardebooks.org/vocab/1.0"
with urllib.request.urlopen(url) as r:
    content = r.read().decode("utf-8")

header = f"<!-- SE Vocabulary — fetched {today} (v1.0). Used as fallback if live fetch fails. -->\n"
out = "skills/se-semanticate-review/vocab-fallback.html"
with open(out, "w") as f:
    f.write(header + content)
print(f"Written {out} ({len(content)} bytes)")
EOF
```

Expected: `Written skills/se-semanticate-review/vocab-fallback.html (NNNNN bytes)`

- [ ] **Step 2: Fetch SE manual single-page and save with dated header**

```bash
python3 - <<'EOF'
import urllib.request, datetime
today = datetime.date.today().isoformat()

url = "https://standardebooks.org/manual/latest/single-page"
with urllib.request.urlopen(url) as r:
    content = r.read().decode("utf-8")

header = f"<!-- SE Manual of Style v1.8.7 — fetched {today}. Used as fallback if live fetch fails. -->\n"
out = "skills/se-semanticate-review/manual-fallback.html"
with open(out, "w") as f:
    f.write(header + content)
print(f"Written {out} ({len(content)} bytes)")
EOF
```

Expected: `Written skills/se-semanticate-review/manual-fallback.html (NNNNN bytes)`

- [ ] **Step 3: Verify both files contain expected content**

```bash
grep -c "epub:type" skills/se-semanticate-review/vocab-fallback.html
grep -c "Merriam-Webster" skills/se-semanticate-review/manual-fallback.html
```

Expected: both return a count > 0

- [ ] **Step 4: Commit**

```bash
git add skills/se-semanticate-review/vocab-fallback.html skills/se-semanticate-review/manual-fallback.html
git commit -m "chore(se): bundle SE vocab and manual fallback files (v1.8.7)"
```

---

## Task 7: skill.md — complete skill instruction

**Files:**
- Create: `skills/se-semanticate-review/skill.md`

- [ ] **Step 1: Create skill.md**

```markdown
---
name: se:se-semanticate-review
description: Review and apply semantic markup to an SE ebook — wraps abbreviations, classifies italics and emphasis, adds xml:lang to foreign words. Edits XHTML directly and produces an HTML review report from the actual git diff.
triggers:
  - se-semanticate-review
  - se semanticate review
  - semantic markup review
  - review se semantics
models: all
---

# se:se-semanticate-review

Apply semantic markup to a Standard Ebooks ebook and produce an HTML review report.

## When invoked

Run this skill against an SE ebook directory after the initial source cleanup
(after `se clean` and before final `se lint`). It finds untagged abbreviations,
untyped italics, and `<em>` elements that may need reclassification, applies
changes to the XHTML files, and opens a review report in your browser.

**SE prohibits AI for metadata.** This skill only touches `src/epub/text/*.xhtml`.
Never edit `content.opf`, `colophon.xhtml`, or cover/titlepage files.

## Steps

### 1 — Fetch authoritative references

Attempt to fetch both:
- `https://standardebooks.org/vocab/1.0` (SE vocabulary)
- `https://standardebooks.org/manual/latest/single-page` (SE Manual of Style)

If either fetch fails, load the bundled fallback:
- `${CLAUDE_SKILL_DIR}/vocab-fallback.html`
- `${CLAUDE_SKILL_DIR}/manual-fallback.html`

Note which source (live or fallback) was used — this appears in the review report header.

### 2 — Run the detection script

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/detect_semantics.py <path>
```

Parse the JSON output. It contains candidates of these types:
- `abbr-title` — bare honorifics (Mr., Dr., etc.)
- `abbr-era` — bare era abbreviations (BC, AD, BCE, CE)
- `initials` — given-name initial sequences
- `i-untyped` — `<i>` elements with no `epub:type` or `xml:lang`
- `i-missing-lang` — `<i epub:type="se:name.publication.*">` without `xml:lang`
- `em-candidate` — all `<em>` elements

### 3 — Run se clean as baseline

```bash
se clean .
```

This establishes a clean formatting baseline so the final git diff shows only your semantic changes.

### 4 — Classify and edit

Process candidates in this order (least to most ambiguous):
1. `abbr-era` — mechanical, apply `suggested_markup` directly
2. `abbr-title` — mechanical, apply `suggested_markup`; respect `eoc: true` flag
3. `initials` — apply `suggested_markup`; use `z3998:personal-name` if >3 initials
4. `i-missing-lang` — add `xml:lang` to the existing element; see Language Rules below
5. `i-untyped` — classify using the `<i>` decision tree below
6. `em-candidate` — classify using the `<em>` decision tree below (most judgment)

Use the Edit tool to apply changes directly to each `.xhtml` file.

### 5 — `<em>` decision tree

For each `em-candidate`:

1. **Internal thought?** If the `parent_text` shows this is an unspoken reflection
   → change to `<q>` and note to add `q { font-style: italic; }` to `local.css`
2. **Foreign word?** If `mw_lookup: true` — look up the word at
   `https://www.merriam-webster.com/dictionary/<word>`:
   - Not found → `<i xml:lang="LANG">` (determine language from context)
   - Found, labeled as French/Latin/etc. → still `<i xml:lang="LANG">`
   - Found as English entry → keep `<em>` (genuine emphatic stress)
   - Found only in MW Unabridged → treat as foreign (Unabridged results don't qualify per SEMoS)
3. **Vessel, publication, artwork name?** → `<i epub:type="se:name.*">`
4. **Sound written out?** → bare `<i>` (no epub:type)
5. **Phoneme** (letter as spoken sound) → `<i epub:type="z3998:phoneme">`
6. **Grapheme** (letter as written character) → `<i epub:type="z3998:grapheme">`
7. **Cannot determine** → skip; add to reasoning.json with `"status": "skipped"`

### 6 — `<i>` untyped decision tree

For each `i-untyped`:

1. Non-English word not in MW → `<i xml:lang="LANG">`
2. Publication title (book, play, newspaper, etc.) → `<i epub:type="se:name.publication.*">`
   — add `xml:lang` if non-English title
3. Vessel name → `<i epub:type="se:name.vessel.ship">` (or `.boat`)
4. Taxonomic binomial → `<i epub:type="z3998:taxonomy">`
5. Sound written out → bare `<i>`
6. Invented/alien language → `<i xml:lang="x-TAG">` (TAG ≤ 8 chars)
7. Unknown language → `<i xml:lang="und">`
8. Cannot determine → skip

### 7 — Language rules

- Use IETF language tags: `fr`, `la`, `de`, `it`, `es`, `grc` (ancient Greek), `el` (modern Greek)
- Script subtags use title-case: `zh-Hant`, `ru-Latn`
- Non-Roman scripts (Chinese, Japanese, Arabic) → never italicize; use `<span xml:lang="LANG">` instead
- Greek IS italicized (`xml:lang="grc"` or `xml:lang="el"`)
- **Always italicize** these Latin phrases regardless of MW status (SEMoS §8.2.9.9):
  `sic`, `a posteriori`, `a priori`, `a fortiori`, `ad absurdum`, `ad hominem`,
  `ad infinitum`, `ad interim`, `ad nauseam`, `in absentia`, `in camera`,
  `in loco parentis`, `in situ`, `in statu quo`, `in toto`, `in vitro`,
  `inter alia`, `more suo`

### 8 — Run se clean after edits

```bash
se clean .
```

### 9 — Capture the diff

```bash
git diff --unified=3 > /tmp/se-assist-diff.diff
```

### 10 — Write reasoning.json

Write `/tmp/se-assist/<ebook-slug>/reasoning.json` — a JSON array. One entry per change or skip:

```json
[
  {
    "location": "src/epub/text/chapter-1.xhtml:42",
    "type": "abbr-title",
    "status": "applied",
    "reasoning": "Honorific preceding a personal name.",
    "manual_ref": "§8.10.3 — Abbreviations for Names and Titles",
    "manual_url": "https://standardebooks.org/manual/latest/single-page"
  },
  {
    "location": "src/epub/text/chapter-7.xhtml:203",
    "type": "em-candidate",
    "status": "skipped",
    "reasoning": "Ambiguous: could be emphatic stress or ironic delivery. Context inconclusive.",
    "manual_ref": "§8.2.2 — Emphasis",
    "manual_url": "https://standardebooks.org/manual/latest/single-page"
  }
]
```

Use the exact section title from the live or fallback manual — do not invent section titles.

### 11 — Generate and open the HTML report

```bash
SLUG=$(basename $(pwd))
mkdir -p /tmp/se-assist/${SLUG}

python3 ${CLAUDE_SKILL_DIR}/scripts/generate_review.py \
  /tmp/se-assist-diff.diff \
  /tmp/se-assist/${SLUG}/reasoning.json \
  /tmp/se-assist/${SLUG}/se-semantics-review.html \
  --vocab-source="<live or fallback>" \
  --manual-source="<live or fallback (v1.8.7)>" \
  --open
```

The report opens automatically in your browser.

## Common SE epub:type values for `<i>`

| Value | Use case |
|---|---|
| `se:name.publication.book` | Books, novels |
| `se:name.publication.play` | Plays |
| `se:name.publication.poem` | Long poems |
| `se:name.publication.newspaper` | Newspapers |
| `se:name.publication.magazine` | Magazines, journals |
| `se:name.vessel.ship` | Ships and boats |
| `z3998:taxonomy` | Binomial species names |
| `z3998:stage-direction` | Stage directions in drama |
| `z3998:phoneme` | Letter as spoken sound |
| `z3998:grapheme` | Letter as written character |

Short works (short stories, songs, essays) go in **quotes** with `<span epub:type="se:name.publication.short-story">`, not `<i>`.
```

- [ ] **Step 2: Run all tests to confirm nothing broken**

```bash
cd /workspaces/ocr-container/se-llm-skills
python -m pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add skills/se-semanticate-review/skill.md
git commit -m "feat(se): se:se-semanticate-review skill.md — complete skill instruction"
```

---

## Task 8: Integration smoke test

**Goal:** Verify the full pipeline works end-to-end on a real (or test) SE ebook directory.

- [ ] **Step 1: Run detect_semantics.py on a fixture and verify output**

```bash
cd /workspaces/ocr-container/se-llm-skills
python3 skills/se-semanticate-review/scripts/detect_semantics.py \
  tests/fixtures/chapter_abbr.xhtml | python3 -m json.tool | head -40
```

Expected: valid JSON with at least one candidate of type `abbr-title`

- [ ] **Step 2: Run generate_review.py on sample fixtures**

```bash
python3 skills/se-semanticate-review/scripts/generate_review.py \
  tests/fixtures/sample.diff \
  tests/fixtures/sample_reasoning.json \
  /tmp/se-assist-smoke/review.html \
  --vocab-source="test" \
  --manual-source="test"

grep -c "data-status" /tmp/se-assist-smoke/review.html
```

Expected: count > 0; no Python errors

- [ ] **Step 3: Run full test suite**

```bash
cd /workspaces/ocr-container/se-llm-skills
make ci
```

Expected: PASS (or `make test` passes — stubs currently exit 0)

- [ ] **Step 4: Final commit**

```bash
git commit --allow-empty -m "chore(se): se:se-semanticate-review v1 complete"
```
