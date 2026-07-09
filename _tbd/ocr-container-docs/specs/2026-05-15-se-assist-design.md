# se-assist Plugin Design

**Date:** 2026-05-15
**Status:** Approved
**Framework:** se-llm-skills (plugin artifact built with that framework)

## 1. What We're Building

`se-assist` — an se-llm-skills plugin for [Standard Ebooks](https://standardebooks.org) producers. It packages a growing set of skills and detection scripts that assist with the most tedious, error-prone stages of SE ebook production. Skills are installable across Claude Code, Gemini CLI, Codex, and any AI coding assistant that supports the se-llm-skills plugin format.

Target audience: SE producers community-wide, not just personal use.

**Constraint:** SE explicitly prohibits AI for writing metadata descriptions. `se-assist` skills assist mechanical and judgment-intensive workflow stages only; they never touch `content.opf` descriptions or author credits.

## 2. Plugin Structure

```
se-assist/                              ← plugin root
├── .claude-plugin/
│   └── plugin.json
└── skills/
    ├── se-semanticate-review/          ← v1 (this spec)
    │   ├── SKILL.md
    │   ├── vocab-fallback.html         ← SE vocab, dated header
    │   ├── manual-fallback.html        ← full SE manual single-page, v1.8.7, dated
    │   └── scripts/
    │       ├── detect-semantics.py     ← candidate finder → JSON
    │       └── generate-review.py      ← git diff + reasoning.json → HTML report
    ├── se-lint-explain/                ← future
    ├── se-verse-markup/                ← future
    ├── se-review-assist/               ← future
    ├── se-ibid-replace/                ← future
    └── se-typogrify-review/            ← future
```

Each skill is self-contained — its scripts and fallback files travel with it inside the plugin artifact. No separate install step beyond the plugin itself. Python 3.10+ is the only external dependency (already present in every SE producer environment via `se-tools`).

## 3. v1 Skill: `se-semanticate-review`

### Invocation
```
/se-semanticate-review [path-to-se-ebook-directory]
```

### Data Flow

```
1. Fetch live resources (with fallback)
   ├── GET standardebooks.org/vocab/1.0
   │   └── fallback: ${SKILL_DIR}/vocab-fallback.html
   └── GET standardebooks.org/manual/latest/single-page
       └── fallback: ${SKILL_DIR}/manual-fallback.html

2. se clean .
   └── Establishes a clean formatting baseline so the final git diff shows only
       semantic changes, not pre-existing indentation noise

3. python3 ${SKILL_DIR}/scripts/detect-semantics.py <path>
   └── stdout: JSON array of candidates

4. AI classifies each candidate
   ├── MW lookup for boundary cases (basic MW only — see §5)
   └── Applies edits to XHTML files via Edit tool

5. se clean .

6. git diff --unified=3  →  actual diff of changes

7. AI writes /tmp/se-assist/<ebook-slug>/reasoning.json
   └── per-hunk: reasoning text + manual_ref (§N.N.N — Section Title) + manual_url

8. python3 ${SKILL_DIR}/scripts/generate-review.py \
       <diff-file> <reasoning.json> \
       > /tmp/se-assist/<ebook-slug>/se-semantics-review.html

9. webbrowser.open("file:///tmp/se-assist/<ebook-slug>/se-semantics-review.html")
```

No modification to `.gitignore`, `.git/info/exclude`, or any git-tracked file beyond the XHTML content edits and `se clean`.

## 4. Detection Script (`detect-semantics.py`)

### Input
Path to SE ebook root or a single `.xhtml` file. Walks `src/epub/text/*.xhtml`.

### Output
JSON array to stdout. One object per candidate.

### Candidate Schema
```json
{
  "file": "src/epub/text/chapter-1.xhtml",
  "line": 42,
  "type": "abbr-title",
  "text": "Mr.",
  "context": "±200 chars of surrounding text",
  "parent_text": "(full parent element text — em-candidate and i-untyped only)",
  "current_markup": "Mr.",
  "suggested_markup": "<abbr epub:type=\"z3998:name-title\">Mr.</abbr>",
  "mw_lookup": false
}
```

`mw_lookup: true` is set only on candidates where the MW boundary is genuinely in question (see §5). High-confidence candidates skip the fetch entirely.

### Candidate Types — V1

**Tier 1 — High confidence (mechanical rules, false positives rare):**

| Type | What triggers it | Notes |
|---|---|---|
| `abbr-title` | Bare honorifics: Mr. Mrs. Dr. Prof. Mme. Mlle. Messrs. Esq. Hon. | Also detect `class="eoc"` needed when abbreviation period = sentence-final period |
| `abbr-era` | Bare BC AD BCE CE with no `<abbr>` wrapper | No period: `AD.` → `AD` (era abbreviations never take trailing period) |
| `initials` | Single-letter-dot patterns preceding or within names: `J. R. R.`, `T. S.` | Distinguish `z3998:given-name` (first-name initials) vs `z3998:personal-name` (ambiguous full-name initials) |

**Tier 2 — Judgment-intensive (with explicit skip criteria):**

| Type | What triggers it | Notes |
|---|---|---|
| `i-untyped` | `<i>` with no `epub:type` and no `xml:lang` | Skip: invented names in non-English invented languages (flag for `xml:lang="und"` or `xml:lang="x-TAG"`) |
| `i-missing-lang` | `<i epub:type="se:name.publication.*">` without `xml:lang` on non-English titles | High confidence fix |
| `em-candidate` | All `<em>` elements | Check: is it emphatic stress, or should it be `<i xml:lang>`, `<i epub:type>`, or `<q>` (internal thoughts)? Set `mw_lookup: true` if text looks foreign |

**Deferred to v2:**

| Type | Notes |
|---|---|
| `abbr-caps` | All-caps initialisms/acronyms/Roman numerals — complex classification tree |
| `allcaps-text` | Prose all-caps → `<b>`, `<strong>`, or lowercase; uses XPath from reviewer step 13 |
| `repeat-foreign` | Subsequent instances of first-italicized foreign word missing `<span xml:lang>` |
| `heading-contrast` | `<i>` inside heading/epigraph needing roman contrast; `xml:lang` must move to parent |

### `class="eoc"` Detection
When an `abbr-title` candidate's terminal period is also the sentence-ending period (i.e., no other sentence-ending punctuation follows within the same text node), add `class="eoc"` to the `<abbr>`. Example: `She loved music, etc.` → `<abbr class="eoc">etc.</abbr>`.

## 5. Merriam-Webster Lookup

Applied only to candidates where `mw_lookup: true` in the JSON.

**URL:** `https://www.merriam-webster.com/dictionary/<word-or-phrase>`

**Logic:**

| MW result | SE treatment | Reasoning note |
|---|---|---|
| Not found | Foreign → `<i xml:lang="...">` | "Not found in MW basic search" |
| Found, entry labeled as French/Latin/etc. | Still foreign → `<i xml:lang="...">` | "MW lists as [language] phrase — treated as foreign" |
| Found, English entry (foreign etymology is fine) | English → keep `<em>` or no markup | "MW English entry ([origin] origin) — treated as English" |
| Found in MW Unabridged only (not basic) | Foreign → `<i xml:lang="...">` | "Found only in MW Unabridged — does not qualify per SEMoS" |
| Ambiguous label ("chiefly British", archaic, etc.) | Skip → flag for human | Reason: label inconclusive |

**Always-italic overrides (skip MW lookup entirely):**
These Latin/foreign phrases are always italicized per SEMoS §8.2.9.9 regardless of MW status:
`sic`, `a posteriori`, `a priori`, `a fortiori`, `ad absurdum`, `ad hominem`, `ad infinitum`, `ad interim`, `ad nauseam`, `in absentia`, `in camera`, `in loco parentis`, `in situ`, `in statu quo`, `in toto`, `in vitro`, `inter alia`, `more suo`.

**Never italicize regardless of script:**
Non-Roman script text (Chinese, Japanese, Arabic, etc.) — never italicized; always `xml:lang`. Exception: Greek IS italicized (`xml:lang="grc"` or `xml:lang="el"`).

## 6. AI Classification Rules (Embedded in SKILL.md)

The skill instruction embeds a compact lookup table of the most common cases. For anything not in the table, the AI searches the live (or fallback) single-page manual by section heading text.

**`<em>` decision tree:**
1. Is the text an internal thought or unspoken reflection? → `<q>` + CSS italic (not `<em>`)
2. Is the text a foreign word/phrase? → set `mw_lookup: true`; see MW logic
3. Is the text a vessel name, publication title, or other named entity? → `<i epub:type="se:name.*">`
4. Is the text a sound written out (e.g., `Ruff, ruff!`)? → bare `<i>` (no epub:type)
5. Is the text a phoneme (letter as sound) or grapheme (letter as character)? → `<i epub:type="z3998:phoneme/grapheme">`
6. Otherwise → keep as `<em>` (genuine emphatic stress)

**`<i>` untyped decision tree:**
1. Is it a non-English word? → `<i xml:lang="IETF-tag">` (check MW first if ambiguous)
2. Is it a publication title (book, play, newspaper, etc.)? → `<i epub:type="se:name.publication.*">`; add `xml:lang` if non-English title
3. Is it a vessel name? → `<i epub:type="se:name.vessel.*">`
4. Is it a taxonomic binomial? → `<i epub:type="z3998:taxonomy">`
5. Is it a sound? → bare `<i>`
6. Is it an invented/alien language word? → `<i xml:lang="x-TAG">` (≤8 char TAG)
7. Is the language unknown? → `<i xml:lang="und">`
8. Cannot determine → skip, add to review log skipped section

**`<abbr>` rules:**
- Post-nominal degrees with initials: `epub:type="z3998:name-title z3998:initialism"` (compound)
- Era abbreviations: `epub:type="se:era z3998:initialism"`, no trailing period
- Compass points: `epub:type="se:compass"`
- US state / postal codes: `epub:type="z3998:place"`

## 7. Review Log

### Location
`/tmp/se-assist/<ebook-slug>/se-semantics-review.html`

No git-tracked or SE-repo files are written. `/tmp/se-assist/` is outside all repos.

### Generation
`generate-review.py` takes the actual `git diff --unified=3` output and the AI-produced `reasoning.json`. It never reconstructs changes from the AI's memory — the diff is the source of truth.

### HTML Structure
```html
<html>
<head>
  <title>Semantic Markup Review — [ebook title]</title>
  <!-- Inline CSS: diff colors, collapsible sections, readable monospace -->
</head>
<body>
  <h1>Semantic Markup Review</h1>
  <p>Generated: [date] | Vocab: live/fallback | Manual: live/fallback (v1.8.7)</p>
  <p>Files: N | Candidates: N | Applied: N | Skipped: N</p>

  <details open data-type="applied">
    <summary>Applied Changes (N)</summary>

    <details data-type="abbr-title">
      <summary>Abbreviations — Honorifics (N changes)</summary>
      <!-- Per-hunk diff block + reasoning annotation -->
      <div class="change" data-file="chapter-1.xhtml" data-line="42" data-status="applied">
        <div class="diff">
          <span class="removed">Mr.</span>
          <span class="added">&lt;abbr epub:type="z3998:name-title"&gt;Mr.&lt;/abbr&gt;</span>
        </div>
        <div class="reasoning">
          z3998:name-title — honorific preceding a name.
          <a href="https://standardebooks.org/manual/latest/single-page">
            §8.10.3 — Abbreviations for Names and Titles
          </a>
        </div>
      </div>
    </details>

    <!-- ... other change type sections ... -->

  </details>

  <details data-type="skipped">
    <summary>Skipped — Needs Human Judgment (N items)</summary>
    <div class="change" data-file="chapter-7.xhtml" data-line="203" data-status="skipped">
      <div class="original">&lt;em&gt;very well&lt;/em&gt;</div>
      <div class="reasoning">
        Ambiguous: could be emphatic stress or ironic delivery. Context inconclusive.
        MW lookup: "very well" found as English → not foreign. Judgment required.
      </div>
    </div>
  </details>
</body>
</html>
```

`data-*` attributes on each `.change` div enable future skills (e.g., `/se-work-skipped`) to parse the review log programmatically.

## 8. Bundled Reference Files

Both files are fetched live at runtime; bundled copies are fallback only.

| File | Source | Notes |
|---|---|---|
| `vocab-fallback.html` | standardebooks.org/vocab/1.0 | ~95 terms, compact. Header: `SE Vocabulary — as of YYYY-MM-DD (v1.8.7). Used as fallback if live fetch fails.` |
| `manual-fallback.html` | standardebooks.org/manual/latest/single-page | Full single-page manual ~25–28k words. Header: `SE Manual of Style v1.8.7 — as of YYYY-MM-DD. Used as fallback if live fetch fails.` |

AI searches the manual by section heading text, not by anchored section number, so the skill stays correct even if section numbers change between manual versions.

Manual citations in `reasoning.json` use both number and title:
`"§8.2.9.1 — Italicizing Non-English Words and Phrases"`

## 9. Future Skills Roadmap

| Skill | Workflow stage | Key automation |
|---|---|---|
| `se-lint-explain` | Post-lint triage | Group lint output by error class; explain each class; draft per-class commit messages |
| `se-verse-markup` | Verse conversion | Detect `<pre>` blocks; convert to `<p>/<span>` stanza/line structure with epub:type |
| `se-typogrify-review` | Post-typogrify review | Guide producer through edge cases: elision apostrophes, prime glyphs, two-em dashes |
| `se-review-assist` | Reviewer 24-step checklist | Walk each step; run commands; surface findings for human decision |
| `se-ibid-replace` | Endnote cleanup | Replace `ibid.` with full prior reference text |
| `se-allcaps-convert` | All-caps normalization | Use reviewer XPath; classify each instance; convert to `<b>`, `<strong>`, or lowercase |

## 10. Open Questions

1. **MW rate limiting** — does MW block automated fetches? May need a small delay between lookups or a user-agent header.
2. **Script packaging** — when se-llm-skills builds the plugin artifact, do `scripts/` subdirectories inside skill directories get included verbatim? (Assumed yes based on plugin docs, but needs verification against actual build output.)
3. **`generate-review.py` diff parsing** — unified diff format is stable but has edge cases (binary files, renames). Scope to text XHTML only; skip anything that looks non-text.
4. **Community distribution** — once polished, should `se-assist` be submitted to the SE mailing list as an unofficial tool? SE's AI prohibition covers metadata authorship only; announcing an optional tool is likely acceptable.
