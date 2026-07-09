---
status: complete
---

# R0 — Lint-First PR Unblock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unblock all 7 open `chore/lint-first-selectors` PRs so CT can merge them; each PR ends in one of two states — (a) CI green and ready to merge, or (b) CI red but with a filed-and-linked pre-existing-debt issue documenting that the failure predates the PR.

**Architecture:** Three repos have CI failures of distinct provenance, so this is three small parallel fixes plus a triage sweep — not a single rewrite. pdomain-ocr-synth has 42 *legitimate* new ruff findings from the selector expansion (we caused these by adding selectors; we fix them in the PR). pd-ocr-labeler and pdomain-prep-for-pgdp have failures that are *unrelated* to lint-first (upstream API drift + missing build artifact); we file pre-existing-debt issues and add `pre-existing-debt: see #N` notes to the PR descriptions so CT can merge with eyes open. The remaining 4 PRs (pdomain-book-tools #34, pdomain-ocr-cli #4, pdomain-ocr-labeler-spa #2, pd-ocr-trainer #2) are already green or have no CI gate; this plan just verifies + updates their PR descriptions for review.

**Tech Stack:** `ruff` (auto-fix + manual rewrites), `gh` CLI (issue + PR mutations), pd-* per-repo agents for in-repo edits.

**Source plans:**
- `docs/superpowers/plans/2026-05-10-code-review-style-cleanup-plan-1.md` (v2 Plan 1 Phase 0)
- `docs/superpowers/plans/2026-05-11-INDEX.md` (this re-plan's index)

**Depends on:** None. Parallel-safe with R1.

**Out of scope:**
- Fixing pre-existing-debt issues themselves — those get filed and assigned to future ship-issue cycles.
- pd-png-optimizer (per v2 spec Open Q #4 — Python-only scope).
- Final CT review/merge of the PRs.

---

## Background context for the engineer

You are unblocking 7 open PRs on the `chore/lint-first-selectors` branch across all 7 published Python pd-* repos. The v2 Plan 1 Phase 0 commit applied a canonical ruff selector block:

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "B", "SIM", "UP", "RUF", "ERA", "T20"]
```

plus pyright strict on `src/`. On most repos this landed cleanly. On three it surfaced problems:

| Repo | PR | CI state | Diagnosis |
|---|---|---|---|
| pdomain-book-tools | #34 | SUCCESS | already green |
| pdomain-ocr-cli | #4 | SUCCESS | already green |
| pd-ocr-labeler | #3 | FAILURE | Playwright Chromium not installed in CI runner + upstream `Page.__init__()` kwarg `blocks` removed in pdomain-book-tools — both pre-existing, not our fault |
| pdomain-ocr-labeler-spa | #2 | (no CI) | TypeScript repo, no GitHub Actions on this branch yet |
| pdomain-ocr-synth | #2 | FAILURE | 42 *new* ruff findings (RUF046×17, RUF007×5, RUF043×4, ERA001×3, SIM108×2, SIM103×2, RUF015×2, RUF005×2, N802×2, SIM105×1, RUF009×1, N814×1) — caused by the selector expansion; legitimately our problem |
| pd-ocr-trainer | #2 | (no CI) | no GitHub Actions on this branch yet |
| pdomain-prep-for-pgdp | #3 | FAILURE | `FileNotFoundError: Forced include not found: src/pd_prep_for_pgdp/static` during `uv sync` — pyproject has `[tool.hatch.build.targets.wheel.force-include]` for `static/` but that directory is git-ignored (Vite build output); pre-existing |

The fix strategy:

1. **pdomain-ocr-synth #2**: Run `ruff check --fix --unsafe-fixes` for auto-fixable subset; manually address the rest in the in-repo agent. Commit on `chore/lint-first-selectors` so CI re-runs.
2. **pd-ocr-labeler #3**: File two pre-existing-debt issues (one for browser-test Chromium install; one for upstream `Page.blocks` cascade). Update PR body with `Pre-existing CI debt: #X, #Y — not blocked on this PR`.
3. **pdomain-prep-for-pgdp #3**: File one pre-existing-debt issue (Vite-static-dir build coupling). Update PR body.
4. **Other 4 PRs**: verify PR description is review-ready; no code changes.

### Worktree ownership caveat (workspace-rc finding)

If any task lands you inside `/srv/bot-workspaces/`, files are owned by `claude-bot` (uid 1001). Use `sudo -u claude-bot bash -c '...'` for edits. Otherwise stay in CT's interactive checkouts at `/workspaces/ocr-container/<repo>/` — that's where these PR branches live for review.

### Routing

For any in-repo edit (e.g. fixing ruff findings in pdomain-ocr-synth, updating a Makefile), delegate to the matching per-repo agent (`pdomain-ocr-synth`, `pd-ocr-labeler`, `pdomain-prep-for-pgdp`). Workspace-level work (filing issues, updating PR descriptions via `gh pr edit`) runs from the orchestrator.

---

## File structure

This plan touches *issues and PR descriptions* on GitHub plus a small number of in-repo files. No new files created in the workspace.

**Modified (per-repo, via per-repo agents):**
- `pdomain-ocr-synth/<various>.py` (ruff fixes; agent decides files based on `ruff check` output)

**GitHub mutations (via orchestrator):**
- 3 new issues filed (1 on pd-ocr-labeler, 1 on pdomain-prep-for-pgdp; pd-ocr-labeler gets 2 nested if the agent confirms both root causes are distinct)
- 3 PR descriptions edited (pd-ocr-labeler #3, pdomain-prep-for-pgdp #3, pdomain-ocr-synth #2)
- (Optional) 4 PR descriptions touched for review polish

---

## Tasks

### Task 1: Verify pre-flight state

**Files:** none

- [ ] **Step 1: Confirm 7 PR head shas and CI states**

Run (from workspace root):

```bash
for r in pdomain-book-tools pdomain-ocr-cli pd-ocr-labeler pdomain-ocr-labeler-spa pdomain-ocr-synth pd-ocr-trainer pdomain-prep-for-pgdp; do
  gh pr list -R "ConcaveTrillion/$r" --head chore/lint-first-selectors \
    --json number,headRefOid,state,statusCheckRollup --jq ".[] | \"$r\tPR#\(.number)\t\(.headRefOid[0:8])\t\(.state)\t\(.statusCheckRollup | map(.conclusion // .status) | join(\",\"))\""
done
```

Expected output: 7 rows. Two SUCCESS (pdomain-book-tools, pdomain-ocr-cli), two empty (labeler-spa, trainer), three with at least one FAILURE (labeler, synth, prep-for-pgdp).

- [ ] **Step 2: Capture sha-pinned diagnosis files**

For each failing PR, save the failure summary to `/tmp/r0-<repo>-failures.txt` so the per-repo agent has it without re-fetching:

```bash
gh run view 25647569809 -R pdomain/pdomain-ocr-synth --log-failed 2>&1 \
  | grep -oE "(RUF|SIM|UP|E[0-9]+|F[0-9]+|N[0-9]+|B[0-9]+|ERA|T20)[0-9]+" \
  | sort | uniq -c | sort -rn > /tmp/r0-pdomain-ocr-synth-failures.txt
gh run view 25647694208 -R ConcaveTrillion/pd-ocr-labeler --log-failed 2>&1 \
  | tail -200 > /tmp/r0-pd-ocr-labeler-failures.txt
gh run view 25647569893 -R pdomain/pdomain-prep-for-pgdp --log-failed 2>&1 \
  | tail -200 > /tmp/r0-pdomain-prep-for-pgdp-failures.txt
```

(Replace run IDs with current ones from Step 1 if PRs have been re-pushed.)

- [ ] **Step 3: Commit point (no commit; this is verification only)**

### Task 2: Fix pdomain-ocr-synth #2 lint failures (delegate to pdomain-ocr-synth agent)

**Files:** in-repo, agent decides

- [ ] **Step 1: Dispatch pdomain-ocr-synth agent with this prompt**

```
You are completing v2 Plan 1 Phase 0 lint-first cleanup on pdomain-ocr-synth.
The chore/lint-first-selectors branch has 42 ruff errors that need fixing
in-place. Failure summary at /tmp/r0-pdomain-ocr-synth-failures.txt:

  17 RUF046  (Value cast to int does not type narrow)
   5 RUF007  (use itertools.pairwise over zip)
   4 RUF043  (raw string for regex)
   3 ERA001  (commented-out code)
   2 SIM108  (ternary instead of if-else)
   2 SIM103  (return condition directly)
   2 RUF015  (next(iter(x)) instead of list(x)[0])
   2 RUF005  (collection-literal unpacking)
   2 N802    (function name not lowercase)
   1 SIM105  (contextlib.suppress)
   1 RUF009  (mutable default)
   1 N814    (lower-camelcase import alias)

Workflow:
1. cd /workspaces/ocr-container/pdomain-ocr-synth; git checkout chore/lint-first-selectors; git pull
2. uv run ruff check --fix --unsafe-fixes src/ tests/ — captures the auto-fixable subset
3. uv run ruff check src/ tests/ — list what's left; address manually file by file
4. For N802 / N814: rename the function/import per ruff suggestion; grep for callers and update.
5. For ERA001: delete the commented-out code; if there's a reason to keep it, replace with a one-line WHY comment instead.
6. For RUF046: read the spec for the rule, then add explicit isinstance() check or remove the redundant cast.
7. uv run make ci — verify green locally before push.
8. Commit batched by rule family (one commit per rule code) for clean review.
9. git push.

Do NOT add `# noqa` suppressions or extend `[tool.ruff.lint] ignore`. Per CONVENTIONS.md (pdomain-book-tools/CONVENTIONS.md "Unicode escape sequences" rule), suppressions paper over the problem.

CI run will retrigger on push. Report back the final ruff-check exit code + count of commits added.
```

- [ ] **Step 2: Verify CI green after push**

Wait for the new CI run (poll every 60s or use `gh run watch`). Expected: `pytest + ruff` job conclusion SUCCESS.

- [ ] **Step 3: Commit point (no orchestrator commit; agent committed in-repo)**

### Task 3: File pre-existing-debt issue on pd-ocr-labeler for browser-test Chromium

**Files:** GitHub issue

- [ ] **Step 1: Confirm the failure is pre-existing**

Read `/tmp/r0-pd-ocr-labeler-failures.txt`. Expect: `RuntimeError: Playwright Chromium is required but could not be launched. Run: make install` in every `tests/browser/test_*.py` ERROR.

Verify it's pre-existing by checking the previous CI run on `main`:

```bash
gh run list -R ConcaveTrillion/pd-ocr-labeler --branch main --limit 3 --json conclusion,headBranch,createdAt
```

If `main` CI passes (or runs `make install` first), the lint-first branch is missing a setup step — that's pre-existing CI config debt, not a lint-first issue. If `main` CI also fails, definitely pre-existing.

- [ ] **Step 2: File the issue**

```bash
gh issue create -R ConcaveTrillion/pd-ocr-labeler \
  --title "CI: Playwright Chromium not installed before browser tests" \
  --label "kind:bug,status:backlog,effort:S" \
  --body "## Summary

CI fails 50+ browser tests with:

\`\`\`
RuntimeError: Playwright Chromium is required but could not be launched. Run: make install
\`\`\`

## Root cause

The CI workflow runs \`uv sync\` + \`pytest\` but does not invoke \`make install\` (which would run \`playwright install chromium\` per the Makefile).

## Repro

\`\`\`bash
gh run view <latest-failed-run-id> -R ConcaveTrillion/pd-ocr-labeler --log-failed
\`\`\`

## Suggested fix

Add a step to \`.github/workflows/ci.yml\` before the pytest step:

\`\`\`yaml
- name: Install Playwright browsers
  run: uv run playwright install chromium --with-deps
\`\`\`

## Surfaced by

PR #3 (\`chore/lint-first-selectors\`) — the lint-first changes did not cause this; the underlying CI gap predates them.

## Acceptance

- [ ] CI workflow installs Playwright Chromium before pytest
- [ ] Browser tests run (pass or fail with real assertion failures, not RuntimeError)"
```

Record the issue number (e.g. `#N1`).

- [ ] **Step 3: Commit point (no commit; issue filed)**

### Task 4: File pre-existing-debt issue on pd-ocr-labeler for upstream `Page.blocks` cascade

**Files:** GitHub issue

- [ ] **Step 1: Confirm the second failure is distinct**

From `/tmp/r0-pd-ocr-labeler-failures.txt`, identify the 10+ FAILED lines matching:

```
TypeError: Page.__init__() got an unexpected keyword argument 'blocks'
```

Verify this is an upstream API change in pdomain-book-tools:

```bash
cd /workspaces/ocr-container/pdomain-book-tools
git log -p --all -- "**/page*.py" | grep -B2 -A2 "def __init__" | grep -i "blocks" | head -10
```

If `Page.__init__` no longer accepts `blocks` but pd-ocr-labeler's persistence code still passes it, that's a cascading API change. Pre-existing relative to PR #3.

- [ ] **Step 2: File the issue**

```bash
gh issue create -R ConcaveTrillion/pd-ocr-labeler \
  --title "Persistence: Page.__init__() 'blocks' kwarg removed upstream" \
  --label "kind:bug,status:backlog,effort:S" \
  --body "## Summary

\`tests/pd_ocr_labeler/operations/persistence/test_save_load_round_trip.py\` fails 10+ tests with:

\`\`\`
TypeError: Page.__init__() got an unexpected keyword argument 'blocks'
\`\`\`

## Root cause

pdomain-book-tools removed (or renamed) the \`blocks\` constructor kwarg on \`Page\`. The persistence round-trip in pd-ocr-labeler still constructs \`Page(blocks=...)\` from the loaded JSON.

## Repro

\`\`\`bash
cd pd-ocr-labeler
uv run pytest tests/pd_ocr_labeler/operations/persistence/test_save_load_round_trip.py -x
\`\`\`

## Suggested fix

Update pd-ocr-labeler's persistence-load path to use the current \`Page\` constructor (likely \`paragraphs=\` or builder API). Cross-reference pdomain-book-tools' \`Page\` class definition.

## Surfaced by

PR #3 (\`chore/lint-first-selectors\`) — predates this PR; first surfaced when CI re-ran on a freshly-synced upstream.

## Acceptance

- [ ] Round-trip tests pass
- [ ] No \`blocks=\` keyword usage in pd-ocr-labeler/src/"
```

Record the issue number (e.g. `#N2`).

- [ ] **Step 3: Commit point (no commit)**

### Task 5: Update pd-ocr-labeler PR #3 description

**Files:** PR description

- [ ] **Step 1: Edit the PR body to reference both issues**

```bash
gh pr edit 3 -R ConcaveTrillion/pd-ocr-labeler \
  --body "$(gh pr view 3 -R ConcaveTrillion/pd-ocr-labeler --json body --jq .body)

## Pre-existing CI debt

This PR's CI run fails on two unrelated pre-existing issues:
- #N1 — Playwright Chromium not installed in CI before browser tests
- #N2 — Upstream pdomain-book-tools removed \`Page.__init__(blocks=...)\` kwarg

Neither failure is introduced by the lint-first selector change in this PR. Reviewer can merge this PR independently of those issues, or wait — CT's call."
```

Replace `#N1`/`#N2` with actual issue numbers from Tasks 3 and 4.

- [ ] **Step 2: Commit point (no commit; PR description updated on GitHub)**

### Task 6: File pre-existing-debt issue on pdomain-prep-for-pgdp for missing static/ dir

**Files:** GitHub issue

- [ ] **Step 1: Confirm root cause**

From `/tmp/r0-pdomain-prep-for-pgdp-failures.txt`, expect:

```
FileNotFoundError: Forced include not found:
/home/runner/work/pdomain-prep-for-pgdp/pdomain-prep-for-pgdp/src/pd_prep_for_pgdp/static
```

Verify `pyproject.toml` has the force-include and `.gitignore` excludes the directory:

```bash
cd /workspaces/ocr-container/pdomain-prep-for-pgdp
grep -n "force-include\|static" pyproject.toml
grep "^static\|^src/pd_prep_for_pgdp/static" .gitignore
```

Expected: `pyproject.toml` has a `[tool.hatch.build.targets.wheel.force-include]` table mapping `src/pd_prep_for_pgdp/static = "pd_prep_for_pgdp/static"`; `.gitignore` excludes that directory (it's a Vite build output).

- [ ] **Step 2: File the issue**

```bash
gh issue create -R pdomain/pdomain-prep-for-pgdp \
  --title "Build: pyproject force-include of static/ fails when Vite build hasn't run" \
  --label "kind:bug,status:backlog,effort:S" \
  --body "## Summary

\`uv sync\` fails in CI with:

\`\`\`
FileNotFoundError: Forced include not found:
.../src/pd_prep_for_pgdp/static
\`\`\`

## Root cause

\`pyproject.toml\` declares \`src/pd_prep_for_pgdp/static\` as a forced wheel include, but the directory is .gitignored (Vite build output). On a fresh checkout (CI runner), the directory doesn't exist until \`npm run build\` (frontend) has produced it, but \`uv sync\` runs first and bails.

## Repro

\`\`\`bash
git clone fresh && cd pdomain-prep-for-pgdp && uv sync
\`\`\`

## Suggested fix paths

1. Make the force-include conditional (only when \`static/\` exists); or
2. Add a placeholder \`static/.gitkeep\` to the repo; or
3. Reorder CI to build frontend before \`uv sync\`; or
4. Drop the force-include and ship static/ via a separate manifest.

CT to triage which path.

## Surfaced by

PR #3 (\`chore/lint-first-selectors\`) — pre-existing build-config issue."
```

Record the issue number (e.g. `#N3`).

- [ ] **Step 3: Commit point (no commit)**

### Task 7: Update pdomain-prep-for-pgdp PR #3 description

**Files:** PR description

- [ ] **Step 1: Edit PR body**

```bash
gh pr edit 3 -R pdomain/pdomain-prep-for-pgdp \
  --body "$(gh pr view 3 -R pdomain/pdomain-prep-for-pgdp --json body --jq .body)

## Pre-existing CI debt

CI fails on pre-existing pyproject build config (force-include of \`static/\` directory that's .gitignored as Vite build output). Filed as #N3. The \`build SPA\` job passes; only \`pytest + ruff\` fails on the \`uv sync\` step before lint even runs."
```

Replace `#N3` with the actual issue number.

- [ ] **Step 2: Commit point (no commit)**

### Task 8: Polish the 4 review-ready PR descriptions

**Files:** PR descriptions on 4 already-green/no-CI PRs

- [ ] **Step 1: For pdomain-book-tools #34, pdomain-ocr-cli #4, pdomain-ocr-labeler-spa #2, pd-ocr-trainer #2 — append a uniform "Ready for review" footer**

```bash
for entry in \
  "pdomain/pdomain-book-tools|34" \
  "pdomain/pdomain-ocr-cli|4" \
  "pdomain/pdomain-ocr-labeler-spa|2" \
  "ConcaveTrillion/pd-ocr-trainer|2"; do
  repo="${entry%|*}"; n="${entry#*|}"
  body=$(gh pr view "$n" -R "$repo" --json body --jq .body)
  gh pr edit "$n" -R "$repo" --body "$body

## Status

Phase 0 lint-first selector adoption per v2 Plan 1. CI green (or no CI gate). Ready for review and merge."
done
```

- [ ] **Step 2: Commit point (no commit)**

### Task 9: Update workspace STATUS.md with R0 outcome

**Files:**
- Modify: `/workspaces/ocr-container/docs/superpowers/plans/STATUS.md`

- [ ] **Step 1: Append a new section**

```bash
cat >> /workspaces/ocr-container/docs/superpowers/plans/STATUS.md <<EOF

## R0 — Lint-first PR unblock (YYYY-MM-DDTHH:MM:SSZ)

7 \`chore/lint-first-selectors\` PRs triaged:
- 4 review-ready (pdomain-book-tools #34, pdomain-ocr-cli #4, pdomain-ocr-labeler-spa #2, pd-ocr-trainer #2)
- 1 fixed in-place after 42 ruff findings (pdomain-ocr-synth #2 — see commits on branch)
- 2 with pre-existing-debt notes pointing at filed issues (pd-ocr-labeler #3 → #N1 #N2; pdomain-prep-for-pgdp #3 → #N3)

CT to merge at convenience. R0 complete.
EOF
```

Replace the timestamp with actual `date -u +%Y-%m-%dT%H:%M:%SZ`. Replace `#N1`/`#N2`/`#N3` with the actual issue numbers from Tasks 3, 4, 6.

- [ ] **Step 2: Commit**

```bash
cd /workspaces/ocr-container
git add docs/superpowers/plans/STATUS.md
git commit -m "$(cat <<'EOF'
chore(status): R0 lint-first PR unblock outcome

7 lint-first PRs triaged. 1 fixed in-place (pdomain-ocr-synth);
2 flagged pre-existing-debt (pd-ocr-labeler, pdomain-prep-for-pgdp);
4 review-ready. CT to merge.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Acceptance

R0 is complete when:

- [ ] `gh pr view 2 -R pdomain/pdomain-ocr-synth --json statusCheckRollup` shows the `pytest + ruff` job as SUCCESS.
- [ ] 3 pre-existing-debt issues exist (2 on pd-ocr-labeler, 1 on pdomain-prep-for-pgdp), labeled `kind:bug, status:backlog, effort:S`.
- [ ] pd-ocr-labeler #3 and pdomain-prep-for-pgdp #3 PR descriptions reference their respective debt issues.
- [ ] pdomain-book-tools #34, pdomain-ocr-cli #4, pdomain-ocr-labeler-spa #2, pd-ocr-trainer #2 PR descriptions have the "Status: Ready for review" footer.
- [ ] STATUS.md committed with R0 outcome summary.

## Trade-offs considered

| Decision | Pro | Con |
|---|---|---|
| Fix pdomain-ocr-synth's 42 ruff findings in the PR vs file as debt | Selectors are *our* change → debt is *our* problem; clean baseline going forward | Adds 1 round-trip of agent work + CI re-run |
| File pd-ocr-labeler failures as debt vs add Chromium install to this PR | Scope discipline — don't entangle lint-first with CI config | The two-issue mention in the PR body is slightly cluttered |
| Force-include fix on pdomain-prep-for-pgdp now vs defer | CT can pick the right of 4 options; not the lint-first PR's job | One more open issue to triage later |

## References

- v2 Plan 1: `docs/superpowers/plans/2026-05-10-code-review-style-cleanup-plan-1.md`
- pdomain-book-tools CONVENTIONS.md (no-noqa rule): `pdomain-book-tools/CONVENTIONS.md`
- Workspace memory: `feedback_ruf001_002_003_convention.md` (pdomain-book-tools agent-memory)
