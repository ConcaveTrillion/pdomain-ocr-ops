---
status: complete
---

# Plan B Pilot Debrief — pdomain-book-tools

> **Status**: Resolved (Session 2 closed all open findings)
> **Last updated**: 2026-05-10 (Session 2)

## TL;DR

Plan B B1-B4 landed cleanly in Session 1. Two B5 attempts surfaced 14 pilot-feedback findings (9 fixed in-line, 5 left as design choices). Session 2 (2026-05-10 follow-up) resolved all 5 remaining findings, surfaced and fixed 6 new ones (#15-#20) during a third B5 attempt, and shipped one real TDD slice end-to-end through the bot — the bot's slice was correct but bounced on a flaky pdomain-book-tools test (unrelated to ship-issue tooling), so the slice was recovered manually as PR #15 and the flaky test was filed + fixed as pdomain-book-tools PR #16. Both PRs merged. Pilot scripts are now considered functionally correct end-to-end and the bot's auth surface is minimized (#20 strips `GH_TOKEN` from the inner `claude -p`).

## Context

Pilot scope chosen by user 2026-05-10: "Full onboarding" of pdomain-book-tools (label seeding, spec discipline, ROADMAP/coverage backlog migration, multi-cycle ship-issue runs).

## Constraints

- Foundation library: changes ripple to 6 downstream pd-* repos.
- Pilot must not break in-flight dev work (user had 65 unpushed master commits at start; now pushed).
- Stop-and-reassess between phases.

## Decision

### Phases done

- **B1 — Label seeding**: 25 workspace labels seeded on `pdomain/pdomain-book-tools`.
- **B2 — Spec skeleton**: `pdomain-book-tools/docs/specs/{01-07,_index}.md`; `docs/architecture/` and `docs/planning/` removed (delegated to `pdomain-book-tools` agent, commit `79ee45a`).
- **B3 — Mechanical migration**: 7 of 8 specs now fully conform; `06-word-reference-lines.md` (914 lines) stays on `.specrc:legacy` pending Procedure 4 split (delegated, commit `84b447a`).
- **B4 — Backlog issue creation**: 12 GitHub issues filed (#2-#13), 4 with `claude-ok` (now `bot:ship-issue-ready` — see Plan-1 rename) (mechanical coverage chores), `status:blocked` on the deferred doctr-from-git item, NOT `claude-ok` on the CI threshold policy issue or the spec-split chore.

### Phase B5 (first ship-issue cycle) attempted twice

Both attempts on issue #11 (cv2_tesseract graceful skip; smallest scope). Both bounced cleanly. Run 2 was significantly further along than run 1 (slash command resolved, file ownership clean, git reset succeeded).

### Pilot-feedback findings (14 total)

Each in-line fix is a workspace commit tagged `[pilot-feedback]`:

| # | Finding | Status | Commit/Action |
|---|---|---|---|
| 1 | `migrate-legacy-spec-auto.py` output trips markdownlint defaults | fixed | `8a63fab` (Status block after H1; prose placeholders) |
| 2 | Orchestrator didn't pass `--model`/`--effort` to claude CLI | fixed | `7d7490a` |
| 3 | Orchestrator invoked `/ship-issue-work`, but skill is named `ship-issue` | fixed | `a1aba3f` |
| 4 | `pick.py` queried `authorAssociation` (not a valid `gh issue list --json` field) | fixed | `bffec69` |
| 5 | `throttle-check.sh` swallowed "dubious ownership" git errors | fixed | `bffec69` |
| 6 | Slash command `/ship-issue` not visible to bot's CC | fixed | Skill installed at `/home/claude-bot/.claude/skills/ship-issue/SKILL.md` (one-time setup) |
| 7 | Bot can't unlink files written by vscode (default umask 022) | fixed | Recursive `chmod g+ws` on `pdomain-book-tools/` (one-time, Phase B6 needs to add a workspace `setfacl` setup) |
| 8 | `pick.py` rebased from `origin/main` (hardcoded) | fixed | `39e140d` (detect via `git symbolic-ref origin/HEAD`) |
| 9 | `origin/master` was 65 commits behind local master | fixed | Pushed (one-time). Solo-dev recurrence prevented in S2 by `pick.py` refuse-if-ahead (workspace `614e9ae`) |
| 10 | Settings.json deny rules block legitimate interactive operations | fixed | `0c3bebc` (deny rules relocated to bot-only hook; settings keeps universal `rm -rf` only) |
| 11 | Bot's CC sandbox blocks `/tmp/ship-issue-acceptance-N.json` | fixed (S2) | `614e9ae` (`.ship-issue-tmp/<N>.json` in working tree) + pdomain-book-tools `d455c86` (.gitignore) |
| 12 | Bot's CC can't call `gh` to query issue details | fixed (S2) | Superseded by #15 — pre-fetch issue JSON to disk, drop `gh` from bot allow list entirely |
| 13 | `make ci` runs `pre-commit install`, fails EPERM on `.git/hooks/pre-commit` | fixed (S2) | pdomain-book-tools `57eeeda` (Makefile guard `[ -f .git/hooks/pre-commit ] \|\| ...`) |
| 14 | Orchestrator exits 0 even when every step failed | fixed (S2) | `614e9ae` (`FAILED` counter, `exit $FAILED`); refined in `73d84d4` (#19) |

### Key architectural learnings

- **Skills vs commands**: `.claude/skills/` are auto-loaded on relevance; slash-command invocation via `/<name>` works but the skill must be visible to the inner CC's project root or user-level (`~/.claude/skills/`). Bot needed user-level install since it works in pdomain-book-tools/ where workspace-level `.claude/skills/` aren't on the path.
- **File ownership pattern**: vscode's default umask 022 creates files without group write. Setgid bits on dirs propagate group ownership but not write bits. Bot needs both `g+w` on files and `g+ws` on dirs. Future-proof: workspace-level `setfacl -d -m g::rw` would set defaults; or vscode's umask should be 002 in dev container.
- **Solo-developer push cadence vs orchestrator's "rebase from origin"**: Plan A's design assumed origin is the source of truth. For solo dev with frequent local commits, that mismatch means the bot starts from stale state. Either push more frequently OR have pick.py rebase from local main with caveats.
- **Settings.json deny is a hard block**: bypass-permissions mode skips PROMPTS, not denies. So workflow rules belonged in the (bot-aware) hook from day one, not in settings. Universal-safety-only in settings; everything else in hook.

### State at pause (end of Session 1)

- pdomain-book-tools master: 84b447a (B3 commit), pushed to origin.
- pdomain-book-tools `wip/ship-issue` branch: exists, sits at 84b447a (clean post-bounce state).
- Issue #11: open, `status:backlog`, no `claude-ok` (bounced twice). Two bounce comments on the issue document each attempt.
- Issues #2-#10, #12-#13: open, in their post-B4 states. 3 still claude-ok'd and ready for piloting once user re-adds `status:ready` (#8, #9, #10).
- Workspace HEAD: `0c3bebc fix(settings): keep deny rules bot-only by relocating them out of settings.json` (39 commits since rebuild start).

## Session 2 (2026-05-10 follow-up)

### Decisions made (5 prior open findings)

User stepped through each as a 2-3 sentence recommendation + tradeoff before any code changed. Outcomes:

- **#11**: move acceptance JSON to `<repo>/.ship-issue-tmp/<N>.json` (gitignored).
- **#12**: bot-specific allow list (defense-in-depth) — later superseded by #15 (drop `gh` allows entirely).
- **#13**: pdomain-book-tools Makefile guard `[ -f .git/hooks/pre-commit ] \|\| pre-commit install`.
- **#14**: `FAILED` counter, `exit $FAILED`; throttle-stop and "no eligible" don't increment.
- **#9 residual**: pick.py refuses with helpful message if local default branch is ahead of origin.

### New findings surfaced during B5 retry (6)

| # | Finding | Status | Commit/Action |
|---|---|---|---|
| 15 | Bot's CC reaching for `gh` was ambient context fishing, not skill-required. Pre-fetch full issue dict to `.ship-issue-tmp/<N>-issue.json` and drop all `gh ...` allows from bot settings | fixed | `614e9ae` (pick.py emits `ISSUE_JSON`, orchestrator passes through, skill says "do not call gh") |
| 16 | Orchestrator inherits caller's cwd; `pick.py` crashed on `git rev-parse HEAD` when invoked from `/home/claude-bot` (sudo login shell) | fixed | `c51fb72` (orchestrator self-cd's to `$WORKSPACE/$(basename $REPO)`) |
| 17 | claude-bot has no `gh auth login`; `pick.py` `claim_issue` and `success.sh`/`failure.sh` `gh` calls returned exit 4 (auth) — only `gh_api()` loaded the secret. Also: workspace `bash-command-guard` hook silently skipped if find-up landed on a leaked `pd-*/.claude/settings.json` | fixed | `1550b41` (orchestrator exports `GH_TOKEN` once; passes `--settings <workspace>/.claude/settings.json` to inner claude) |
| 18 | `bash-command-guard._is_bot_session()` had two bypass paths: `BASH_GUARD_FORCE_INTERACTIVE=1` env override (bot can write its own `~/.bashrc`) and `getpass.getuser()` reading `$USER`/`$LOGNAME` (env-spoofable) | fixed | `73d84d4` (real-UID lookup via `pwd.getpwuid(os.geteuid())`; env overrides ignored for claude-bot, retained for testing on other users) |
| 19 | `success.sh` exits nonzero when `make ci` fails (after invoking `failure.sh` internally), but orchestrator's `\|\| echo` swallowed it — `FAILED` stayed 0, ctask wouldn't alert | fixed | `73d84d4` (orchestrator's `if !` properly captures success.sh exit) |
| 20 | #17 leaked the bot-PAT into `claude -p`'s env — bot's claude inherited `GH_TOKEN` even though its skill says "do not call gh" and #15 dropped gh from the allow list. Bot could `echo $GH_TOKEN` to the transcript log; env-var prints aren't gated by `bash-command-guard` | fixed | `95b8f32` (`env -u GH_TOKEN claude ...` strips the var from the inner claude only; siblings keep it). Residual: bot can still `Read('/run/secrets/gh-token-pd')` via group membership — deferred (bot already has gh write access via the PAT either way) |

### B5 retry outcome (run 3 of issue #11)

After the 5 new findings landed, the third attempt ran end-to-end:

- Throttle-check + claim + ISSUE_JSON write — all clean.
- Bot's `claude -p` (haiku, low effort) completed all 3 acceptance bullets in ~6 minutes:
  - `TestRealImageIntegration` skips cleanly when `tesseract` absent (uses `importlib.util.find_spec()` + `shutil.which()` + `@pytest.mark.skipif`).
  - Tests still execute end-to-end when tesseract is present.
  - `make test` passes locally without `tesseract` installed.
- Two clean commits on `wip/ship-issue`: `bf790f1`, `3b69cdd` (issue-#11-prefixed per skill convention).
- `make ci` failed on a **flaky pdomain-book-tools test** (`test_reorganize_page_expected_text_outputs[plate-chairs-beauvais-tapestry]`) — race in `pytest-xdist` between a session-scoped `rmtree(TEXT_CURRENT_DIR)` fixture and another worker's already-running test. Unrelated to the slice; not reproducible on direct re-run.
- `success.sh` correctly invoked `failure.sh` → wip/ship-issue reset to pre-claim SHA → bounce comment posted on #11 → `success.sh` exited 1 → orchestrator counted the failure (per #19).

### Recovery (manual)

- Cherry-picked the bot's two reflog commits onto `fix/issue-11-cv2-tesseract-skip` (delegated to pdomain-book-tools agent). Tree byte-identical to bot's output. `make test-k K=test_cv2_tesseract` green.
- Draft PR #15 opened against pdomain-book-tools master with `Closes #11`.
- Issue #11 un-bounced: `status:backlog` → `status:in-progress`; no re-add of `bot:ship-issue-ready` (manual PR, not bot).
- Recovery comment on #11 documents the flaky-test false-bounce.

### pdomain-book-tools issue #14 (filed)

Filed `kind:bug` for the flaky test under `-n auto`. Diagnosis: session-scoped `rmtree(TEXT_CURRENT_DIR, ignore_errors=True)` at lines 183-184 of `test_reorganize_page_utils_grouping.py` races xdist worker startup. Three fix paths sketched in the issue body. Not `bot:ship-issue-ready` — needs human triage.

### State at end of Session 2

- pdomain-book-tools master: `1d5859a` (5 commits this session: `d455c86` `.gitignore`, `57eeeda` Makefile, `cc553ad` flaky-test fix, plus PR #15 and PR #16 merge commits `017800c` + `1d5859a`). Local in sync; merged feature branches pruned; `wip/ship-issue` parked at `57eeeda` (pick.py auto-fast-forwards on next run).
- Issue #11: **closed** (via PR #15 merge).
- Issue #14: **closed** (via PR #16 merge).
- PR #15 (cv2_tesseract graceful skip — recovered bot's slice): merged at 03:35 UTC.
- PR #16 (per-worker `current/<gwN>/` subtree to close xdist race): merged at 03:34 UTC.
- Workspace HEAD: `95b8f32 fix(ship-issue): strip GH_TOKEN from inner claude env [pilot-feedback]` (post-merge, post-#20; ~46 commits since rebuild start).
- Bot user (`claude-bot`): home, gitconfig, skills, settings.json all in working steady state.

## Contract / Acceptance

This debrief is complete when:

- [x] Plan B B1-B4 status documented
- [x] All 14 pilot-feedback findings listed with status
- [x] Architectural learnings captured
- [x] Repo + issue state at pause documented
- [x] Open questions captured for next session
- [x] STATUS.md updated with summary line

## Trade-offs considered

| Decision | Pro | Con |
|---|---|---|
| Pause now vs push to green B5 | Clean handoff; remaining 5 findings are design questions | More chasing-tweaks fatigue |
| One run on smallest issue (#11) vs sweep | Cheaper iteration; foundation-first piloting catches issues early | Doesn't exercise success path |
| Inline `[pilot-feedback]` fixes vs deferred backlog | Keeps fixes paired with the finding | Blurs the line between "running the pilot" and "fixing the system" |

## Consequences

- The `[pilot-feedback]` commit tag is now established as a search index for "what we learned in pdomain-book-tools that the next pilot should benefit from."
- Per-repo skill install (`/home/claude-bot/.claude/skills/ship-issue/SKILL.md`) is a one-time bot setup; future pd-* repos won't need it repeated.
- Bot's gitconfig `safe.directory = *` is permanent (in `/home/claude-bot/.gitconfig`).
- The 5 unresolved findings shape next-session scope (see Open questions).

## Open questions (Session 1, all resolved in Session 2)

1. ~~Bot CC sandbox: `--dangerously-skip-permissions` vs explicit allow rules?~~ — **Resolved**: explicit allow rules (defense-in-depth, no second source of truth vs hook). Then narrowed further by #15: bot has *no* `gh` access at all; pre-fetch handles all context.
2. ~~`/tmp` vs working-tree for acceptance JSON?~~ — **Resolved**: working-tree (`<repo>/.ship-issue-tmp/<N>.json`, gitignored). Right abstraction; per-repo gitignore add becomes a pattern for future onboardings.
3. ~~`make ci` pre-commit dependency: skip-if-installed, env-gate, or human-only?~~ — **Resolved**: skip-if-installed via Makefile guard (`[ -f .git/hooks/pre-commit ] \|\| ...`). Idempotent for both bot and human. Same pattern wants rolling into the other 6 pd-* Makefiles in B6+.
4. ~~Origin-as-truth vs local-as-truth?~~ — **Resolved**: refuse-if-ahead with a copy-pasteable error. Bot never picks up stale state; solo-dev pays one extra `git push` per cycle.
5. ~~Orchestrator exit-code semantics: any-fail vs all-fail vs distinct codes?~~ — **Resolved**: nonzero on any iteration failure (good signal for pilot stage; can flip to all-fail later once the bot is stable). Throttle-stop and "no eligible issues" don't count.

## Open questions (Session 2 — for the next session)

1. **flaky pdomain-book-tools test (issue #14)**: which fix path? (a) per-worker `tmp_path` for `current/` then merge, (b) `xdist_group` to serialize, (c) retry-on-FileNotFoundError. The agent prefers (a); awaiting human triage.
2. **Phase B6 multi-cycle stress**: with #15-#19 in, how many runs across mixed kinds (chore/bug/feature) before declaring confidence? Original Plan B said 5; pilot evidence suggests 3-4 might be enough now that the gh + cwd + token + hook surfaces are nailed down.
3. **Roll the `[ -f .git/hooks/pre-commit ] \|\| ...` Makefile pattern into the other 6 pd-* repos**: B6 prep work or fold into each repo's first onboarding?
4. **bash-command-guard hardening (#18) regression test**: should we add a smoke-test that runs the hook with poisoned env (`USER=vscode FORCE_INTERACTIVE=1` as claude-bot) and asserts bot mode wins? Light insurance.
5. **`/run/secrets/*` read hardening (residual from #20)**: bot can still `Read('/run/secrets/gh-token-pd')` directly via filesystem; tightening that requires either an OS-level group split (separate `gh-token-readers` group not including `claude-bot`, with the orchestrator running under a different uid for the secret-loading phase) or expanding bash-command-guard to deny `cat`/`Read` against `/run/secrets/*`. Bot already has gh write access via the PAT either way, so this is "make exfiltration slightly less convenient" not "close a critical hole."

## References

- `docs/superpowers/plans/2026-05-09-workspace-foundation.md` (Plan A)
- `docs/superpowers/plans/2026-05-10-pilot-pdomain-book-tools.md` (Plan B)
- `docs/superpowers/plans/STATUS.md` (rolling status)
- `pdomain-book-tools/CLAUDE.md` (foundation library description)
- Workspace commits tagged `[pilot-feedback]` (15+ commits as of end of S2; see `git log --grep '\[pilot-feedback\]'`)
- pdomain-book-tools PR #15 (manual recovery of bot's slice for #11)
- pdomain-book-tools issue #14 (flaky `test_reorganize_page_expected_text_outputs` race)

## B6 multi-cycle stress (2026-05-11 / R4)

3 cycles run on pdomain-book-tools, all `kind:chore` (no bot-ready bug/feature available):

| Cycle | Issue | Kind | Outcome | PR | Notes |
|---|---|---|---|---|---|
| 1 | #8 | chore | success | PR#17 | Previous session; local make ci passed; GitHub CI failed ruff format (fixed in R4) |
| 2 | #9 | chore | success | PR#17 | Previous session; local make ci passed; GitHub CI failed ruff format (fixed in R4) |
| 3 | #12 | chore | success | PR#17 | Live R4 cycle; orchestrator exit 0; local make ci passed; GitHub CI pending at close |

Extra cycle #10 (ground_truth_matching coverage) also committed to wip/ship-issue from prior sessions, included in PR#17.

**Results:** 3 successes + 0 bounces + 0 orchestrator errors. (Acceptance threshold: 2 successes + 0 orchestrator regressions.) ✓

**New pilot-feedback findings:**
- Issue #42: bot-generated test files fail GitHub CI ruff format + B007 check (pre-commit scope gap). Severity: Low. Root cause: local pre-commit runs incrementally on staged files; GitHub CI runs `--all-files`. Fix: skill prompt should instruct bot to run `uv run ruff format .` and `uv run ruff check .` on full repo before committing.

**Worktree retrofit validated:** Yes. Bot ran inside `/srv/bot-workspaces/ship-issue/pdomain-book-tools/` for all cycles. Flock + detached-HEAD pattern clean. No stuck flocks, no orphan branches, no claude-bot process leaks observed. Lock released cleanly after each orchestrator run. Rebase-on-master worked correctly across multiple cycles.

**Mixed kinds:** All 3 cycles were chores (effort:S, model:haiku). No bug/feature issues were bot-ready. Chore-only is still valid for B6 acceptance since the focus was orchestrator stability, not slice diversity.

## B7 final pilot decision

Pilot **declared DONE** based on B6 outcomes.

Per R4 acceptance threshold (≥2 successes, 0 orchestrator regressions), all criteria met:
- 3 cycles attempted ✓
- 3 cycles produced a draft PR (PR #17) ✓  
- 0 cycles left workspace in broken state ✓
- 0 orchestrator regressions (the ruff format/B007 finding is a skill-quality finding, not an orchestrator regression) ✓
- All findings documented (issue #42 filed) ✓

ship-issue is operationally proven on pdomain-book-tools. Downstream repos (pdomain-ocr-cli, pd-ocr-labeler, pdomain-prep-for-pgdp via R3a/R3b) can adopt the same pattern. The one outstanding finding (#42: ruff full-repo lint in bot prompt) should be incorporated into the skill prompt before rollout.
