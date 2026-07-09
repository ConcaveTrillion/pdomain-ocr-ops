# Writing Style Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reuse the `oxipng-pybind` writing guidelines as the base for the canonical workspace writing style, refine them so the prose stays natural, and apply that same file to every managed sibling repo.

**Architecture:** The workspace root keeps the canonical copy at `docs/process/writing-style.md`. `scripts/sync-workspace-blocks.py` continues to mirror marker blocks into `CONVENTIONS.md` and `CLAUDE.md`, continues to bootstrap `AGENTS.md` only as a static pointer to those files, and gains one file-copy sync for `docs/process/writing-style.md`. Repos link to the style doc from their synced convention and process blocks, so the AI-read path is `AGENTS.md` -> `CLAUDE.md` / `CONVENTIONS.md` -> `docs/process/writing-style.md`. The process block also tells agents to use the same style for direct user communication, including status updates, handoffs, and final summaries.

**Tech Stack:** Markdown, Python standard library, pytest, git.

---

## File Structure

**Source already exists:**
- `/workspaces/ocr-container/oxipng-pybind/docs/process/writing-style.md` — source text to reuse as the base.

**Modify in workspace root:**
- `/workspaces/ocr-container/docs/process/writing-style.md` — canonical workspace style, based on `oxipng-pybind` with a small local refinement against overly choppy prose.
- `/workspaces/ocr-container/scripts/sync-workspace-blocks.py` — copy the canonical writing-style file to each managed repo.
- `/workspaces/ocr-container/tests/scripts/test_sync_workspace_blocks.py` — test that style sync is discovered, written, dry-run safe, and included in commits.
- `/workspaces/ocr-container/CONVENTIONS.md` — keep only a short pointer to `docs/process/writing-style.md`; do not paste the rules into the convention block.
- `/workspaces/ocr-container/CLAUDE.md` — expand the writing-style note so agents use it for direct user communication, not only checked-in docs.

**Modify in managed sibling repos through sync:**
- `<repo>/docs/process/writing-style.md` — copied canonical style file.
- `<repo>/CONVENTIONS.md` — synced rule continues to point to `docs/process/writing-style.md`.
- `<repo>/CLAUDE.md` — synced process block points agents at the writing-style doc for docs and direct user communication.
- `<repo>/AGENTS.md` — only bootstrapped when missing; it points agents to `CLAUDE.md` and `CONVENTIONS.md`, not directly to the writing-style file.

**Managed repo set:**
- `pd-ocr-labeler`
- `pd-ocr-trainer`
- `pd-png-optimizer`
- `pdomain-book-tools`
- `pdomain-index-npm`
- `pdomain-index-pip`
- `pdomain-ocr-cli`
- `pdomain-ocr-labeler-spa`
- `pdomain-ocr-simple-gui`
- `pdomain-ocr-synth`
- `pdomain-ocr-trainer-spa`
- `pdomain-ocr-training`
- `pdomain-ops`
- `pdomain-prep-for-pgdp`
- `pdomain-ui`
- `se-llm-skills`

`oxipng-pybind` stays excluded from workspace sync. It already owns the source style file. `coding-bot`, `codex-remote-hub`, `stay-awake`, and `tools` are not in the current workspace block sync contract; add them only in a later plan if they should become workspace-managed repos.

---

## Task 1: Canonicalize and Refine Workspace Writing Style

**Files:**
- Read: `/workspaces/ocr-container/oxipng-pybind/docs/process/writing-style.md`
- Modify: `/workspaces/ocr-container/docs/process/writing-style.md`

- [ ] **Step 1: Confirm the source file exists**

Run:

```bash
cd /workspaces/ocr-container
test -f oxipng-pybind/docs/process/writing-style.md
```

Expected: exit code 0.

- [ ] **Step 2: Replace the workspace canonical file with the refined oxipng-pybind text**

Write exactly this content to `docs/process/writing-style.md`:

```markdown
# Writing Style

Use this style for docs, reports, issue text, PR text, and user-facing copy.

## Goal

Write text that is easy to scan without sounding clipped. Make it clear for
readers who are tired, new to the project, or reading in a second language.
Aim for about a 7th grade English level.

## Rules

- Use short, clear sentences.
- Put one idea in each sentence.
- Do not make every sentence the same length. Vary the rhythm when it helps the
  text feel natural.
- Combine closely related ideas when splitting them would sound stiff.
- Prefer common words.
- Use active voice when it is natural.
- Avoid long chains of clauses.
- Use short paragraphs, but keep closely related sentences together.
- Avoid repeating the same idea in nearby sentences.
- Use lists when they make steps or choices easier to scan.
- Keep technical terms when they are the correct names.
- Explain a technical term the first time it may be unclear.
- Use parentheses rarely. They are fine for first-time acronym write-outs, such
  as `CI (continuous integration)`.
- Do not use parenthetical em dashes.

## Links and Detail

- If another project doc explains a topic, link to it instead of repeating the
  detail.
- Link helpful references on first use.
- Prefer official docs for standard tools.
- Use local source links with line anchors for project behavior.
- Link to related external projects when they add useful context.
- Avoid deep links into external source code unless readers need them.

## Commands

- Combine command steps when readers should run them together before other
  work.
- Do not copy setup, test, release, or dependency details from another doc.
  Link to the source doc instead.

## Before Publishing

Read the text once as if the reader is tired or new to the project. Fix any
sentence that needs a second read. Split long paragraphs. Remove filler.
```

- [ ] **Step 3: Verify the workspace file keeps the source guidance and adds the natural-flow rule**

Run:

```bash
cd /workspaces/ocr-container
rg -n "Use short, clear sentences|Do not make every sentence the same length|Combine closely related ideas" docs/process/writing-style.md
```

Expected: three matches.

- [ ] **Step 4: Commit the canonical doc**

Run:

```bash
cd /workspaces/ocr-container
git add docs/process/writing-style.md
git commit -m "docs: reuse oxipng writing style"
```

Expected: one workspace-root commit.

---

## Task 2: Add Style File Sync Support

**Files:**
- Modify: `/workspaces/ocr-container/scripts/sync-workspace-blocks.py`
- Modify: `/workspaces/ocr-container/tests/scripts/test_sync_workspace_blocks.py`

- [ ] **Step 1: Add failing tests for file sync**

Append these tests to `tests/scripts/test_sync_workspace_blocks.py`:

```python
def test_style_files_contains_writing_style():
    m = _mod()
    style_files = {f.target for f in m.FILE_COPIES}
    assert "docs/process/writing-style.md" in style_files


def test_sync_repo_copies_writing_style_file(tmp_path):
    m = _mod()
    _make_git_repo(tmp_path)
    content = {"conventions": "CONV BODY", "process": "PROCESS BODY"}
    file_content = {"docs/process/writing-style.md": "# Writing Style\n\nCanonical.\n"}
    summary = m.sync_repo(
        tmp_path,
        content,
        file_content,
        "abc1234",
        dry_run=False,
    )
    assert "synced + committed" in summary
    style = tmp_path / "docs" / "process" / "writing-style.md"
    assert style.read_text() == "# Writing Style\n\nCanonical.\n"


def test_sync_repo_dry_run_does_not_copy_writing_style(tmp_path):
    m = _mod()
    _make_git_repo(tmp_path)
    content = {"conventions": "CONV BODY", "process": "PROCESS BODY"}
    file_content = {"docs/process/writing-style.md": "# Writing Style\n"}
    summary = m.sync_repo(
        tmp_path,
        content,
        file_content,
        "abc1234",
        dry_run=True,
    )
    assert "would update" in summary
    assert not (tmp_path / "docs" / "process" / "writing-style.md").exists()
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run:

```bash
cd /workspaces/ocr-container
uv run pytest tests/scripts/test_sync_workspace_blocks.py -q
```

Expected: fails because `FILE_COPIES` does not exist and `sync_repo` does not accept `file_content`.

- [ ] **Step 3: Implement file-copy sync**

In `scripts/sync-workspace-blocks.py`, add this dataclass below `Block`:

```python
@dataclass(frozen=True)
class FileCopy:
    """A workspace file copied verbatim into each managed repo."""

    source: str
    target: str
```

Add this constant below `BLOCKS`:

```python
FILE_COPIES = (
    FileCopy(
        "docs/process/writing-style.md",
        "docs/process/writing-style.md",
    ),
)
```

Replace the `sync_repo` signature with:

```python
def sync_repo(
    repo_path: Path,
    blocks_content: dict[str, str],
    file_content: dict[str, str],
    workspace_sha: str,
    *,
    dry_run: bool,
) -> str:
```

Inside `sync_repo`, after the block loop and before `AGENTS.md`, add:

```python
    for relative_target, content in file_content.items():
        target = repo_path / relative_target
        current = target.read_text() if target.exists() else ""
        if current != content:
            changed.append(relative_target)
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
```

In `main()`, add this after `blocks_content` is populated:

```python
    file_content = {
        file_copy.target: (WORKSPACE / file_copy.source).read_text()
        for file_copy in FILE_COPIES
    }
```

Replace the call to `sync_repo` in `main()` with:

```python
        print(sync_repo(repo, blocks_content, file_content, workspace_sha, dry_run=args.dry_run))
```

- [ ] **Step 4: Update existing tests for the new `sync_repo` argument**

In every existing test call like this:

```python
summary = m.sync_repo(tmp_path, content, "abc1234", dry_run=False)
```

change it to:

```python
summary = m.sync_repo(tmp_path, content, {}, "abc1234", dry_run=False)
```

Apply the same change for dry-run calls.

- [ ] **Step 5: Run the focused tests**

Run:

```bash
cd /workspaces/ocr-container
uv run pytest tests/scripts/test_sync_workspace_blocks.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Run sync dry-run**

Run:

```bash
cd /workspaces/ocr-container
uv run python scripts/sync-workspace-blocks.py --dry-run
```

Expected: every managed repo that lacks `docs/process/writing-style.md` reports it would update that file. `oxipng-pybind` is not listed.

- [ ] **Step 7: Commit the sync support**

Run:

```bash
cd /workspaces/ocr-container
git add scripts/sync-workspace-blocks.py tests/scripts/test_sync_workspace_blocks.py
git commit -m "chore: sync writing style to managed repos"
```

Expected: one workspace-root commit.

---

## Task 3: Tell Agents to Use the Style in User Communication

**Files:**
- Modify: `/workspaces/ocr-container/CLAUDE.md`

- [ ] **Step 1: Update the workspace writing-style note**

In `/workspaces/ocr-container/CLAUDE.md`, replace the current `## Writing style` body:

```markdown
Follow `docs/process/writing-style.md` for writing style.
```

with:

```markdown
Follow `docs/process/writing-style.md` for docs, reports, issue text, PR text,
user-facing copy, direct user updates, handoffs, and final summaries. Keep
agent communication short, clear, and easy to scan.
```

- [ ] **Step 2: Verify the process block includes direct user communication**

Run:

```bash
cd /workspaces/ocr-container
rg -n "direct user updates|handoffs|final summaries" CLAUDE.md
```

Expected: one match in the `## Writing style` section.

- [ ] **Step 3: Commit the process wording**

Run:

```bash
cd /workspaces/ocr-container
git add CLAUDE.md
git commit -m "docs: apply writing style to agent communication"
```

Expected: one workspace-root commit.

---

## Task 4: Apply Writing Style to Managed Repos

**Files:**
- Modify in each managed repo: `<repo>/docs/process/writing-style.md`
- May also modify in each managed repo: `<repo>/CONVENTIONS.md`, `<repo>/CLAUDE.md`
- May create in each managed repo if missing: `<repo>/AGENTS.md`

- [ ] **Step 1: Run the sync**

Run:

```bash
cd /workspaces/ocr-container
uv run python scripts/sync-workspace-blocks.py
```

Expected: each managed repo with drift is updated and committed locally. The summary includes `docs/process/writing-style.md` for repos where the file was missing or different.

- [ ] **Step 2: Verify every managed repo has the copied file**

Run:

```bash
cd /workspaces/ocr-container
for repo in \
  pd-ocr-labeler \
  pd-ocr-trainer \
  pd-png-optimizer \
  pdomain-book-tools \
  pdomain-index-npm \
  pdomain-index-pip \
  pdomain-ocr-cli \
  pdomain-ocr-labeler-spa \
  pdomain-ocr-simple-gui \
  pdomain-ocr-synth \
  pdomain-ocr-trainer-spa \
  pdomain-ocr-training \
  pdomain-ops \
  pdomain-prep-for-pgdp \
  pdomain-ui \
  se-llm-skills
do
  cmp docs/process/writing-style.md "$repo/docs/process/writing-style.md"
done
```

Expected: no output and exit code 0.

- [ ] **Step 3: Verify each managed repo points to the style doc from AI-read files**

Run:

```bash
cd /workspaces/ocr-container
for repo in \
  pd-ocr-labeler \
  pd-ocr-trainer \
  pd-png-optimizer \
  pdomain-book-tools \
  pdomain-index-npm \
  pdomain-index-pip \
  pdomain-ocr-cli \
  pdomain-ocr-labeler-spa \
  pdomain-ocr-simple-gui \
  pdomain-ocr-synth \
  pdomain-ocr-trainer-spa \
  pdomain-ocr-training \
  pdomain-ops \
  pdomain-prep-for-pgdp \
  pdomain-ui \
  se-llm-skills
do
  rg -n "docs/process/writing-style.md|Writing Style" "$repo/CONVENTIONS.md" "$repo/CLAUDE.md"
  rg -n "direct user updates|handoffs|final summaries" "$repo/CLAUDE.md"
  rg -n "CLAUDE.md.*CONVENTIONS.md|CONVENTIONS.md.*CLAUDE.md" "$repo/AGENTS.md"
done
```

Expected: each repo prints at least one `CONVENTIONS.md` or `CLAUDE.md` line that points to `docs/process/writing-style.md` or names `Writing Style`, one `CLAUDE.md` line that applies the style to direct user communication, and one `AGENTS.md` line that points agents to both `CLAUDE.md` and `CONVENTIONS.md`.

- [ ] **Step 4: Confirm oxipng-pybind was not modified by sync**

Run:

```bash
cd /workspaces/ocr-container/oxipng-pybind
git status --short
```

Expected: no new changes from this rollout. Existing unrelated changes, if any, must be reviewed separately and not mixed into the rollout.

---

## Task 5: Final Verification and Rollout Notes

**Files:**
- Read: workspace root git status
- Read: managed repo git statuses

- [ ] **Step 1: Run workspace tests for sync tooling**

Run:

```bash
cd /workspaces/ocr-container
uv run pytest tests/scripts/test_sync_workspace_blocks.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run a no-op dry-run**

Run:

```bash
cd /workspaces/ocr-container
uv run python scripts/sync-workspace-blocks.py --dry-run
```

Expected: each managed repo prints `already in sync`.

- [ ] **Step 3: Capture repo commits created by the sync**

Run:

```bash
cd /workspaces/ocr-container
for repo in \
  pd-ocr-labeler \
  pd-ocr-trainer \
  pd-png-optimizer \
  pdomain-book-tools \
  pdomain-index-npm \
  pdomain-index-pip \
  pdomain-ocr-cli \
  pdomain-ocr-labeler-spa \
  pdomain-ocr-simple-gui \
  pdomain-ocr-synth \
  pdomain-ocr-trainer-spa \
  pdomain-ocr-training \
  pdomain-ops \
  pdomain-prep-for-pgdp \
  pdomain-ui \
  se-llm-skills
do
  printf '%s ' "$repo"
  git -C "$repo" log -1 --oneline
done
```

Expected: repos changed by the sync show a latest local commit with `sync workspace conventions + process blocks` or the updated sync commit message. Repos that were already current may show an older unrelated commit.

- [ ] **Step 4: Document out-of-scope repos**

Add a short note to the final handoff:

```text
The writing-style file was applied to the existing managed sync set:
pd-*, pdomain-*, and se-llm-skills. oxipng-pybind already had the source file
and remains excluded from sync. coding-bot, codex-remote-hub, stay-awake, and
tools are outside the current workspace block sync contract.
```

No file change is required for this note unless the user asks to expand the managed repo set.

---

## Self-Review

- Spec coverage: The plan brings the oxipng-pybind guidelines into the main workspace, reuses that text as canonical, and applies it to all repos currently managed by workspace sync.
- AI-read coverage: `AGENTS.md` remains the entry-point pointer to `CLAUDE.md` and `CONVENTIONS.md`; `CLAUDE.md` and `CONVENTIONS.md` carry the direct writing-style link.
- User-communication coverage: `CLAUDE.md` tells agents to use the writing style for direct user updates, handoffs, and final summaries.
- Placeholder scan: No `TBD`, `TODO`, `implement later`, or vague testing steps remain.
- Type consistency: `FileCopy`, `FILE_COPIES`, `file_content`, and `sync_repo` use the same names across tests and implementation steps.
