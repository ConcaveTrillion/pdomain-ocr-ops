# Behavior-Driven E2E Capture

> **Status: DRAFT — pending maintainer review.** Authored live during a
> brainstorming session on 2026-05-29. All core decisions are resolved.
> Pilot repo: `pdomain-ocr-simple-gui`.

## Agent Index

- **Kind:** process
- **Use when:** shipped UI, TUI, or CLI behavior needs regression specs.
- **Inputs:** UI definitions, existing implementation, tests, and runbooks.
- **Outputs:** behavior records, flow records, coverage map, and E2E tests.
- **Templates:** `docs/templates/behavior-unit-spec.md`,
  `docs/templates/behavior-flows.md`
- **Upstream:** `docs/process/document-existing-repo.md`,
  `docs/process/ui-definition.md`
- **Feeds:** `docs/superpowers/plans/` or repo-local `docs/plans/`
- **Related:** `docs/process/behavior-e2e-gotchas.md`,
  `docs/process/writing-style.md`
- **Search terms:** behavior capture, E2E capture, behavior records,
  regression specs, observable output, side effects, flow records

## Purpose

A repeatable process for turning a maintainer's knowledge of how an
interface — a web UI, a terminal UI (TUI), or a CLI — *should* behave
into:

1. **Authoritative per-unit behavior specs** that capture the **observable
   output and** the backend/side-effects for every meaningful interaction,
   and
2. **E2E tests** that assert that behavior — not merely that an element
   renders, a key was pressed, or a command exited zero.

The goal is to stop **behavioral regressions** (things fixed once, then
silently re-broken) from slipping back in, by making the intended
behavior explicit, traceable, and continuously verified.

## When to use

Any repo with a user-facing surface — a web SPA (e.g. the FastAPI +
React/Vite `pd-*` apps), a TUI, or a CLI (e.g. `pdomain-ocr-cli`) — where
surface-level tests exist but do not assert observable behavior, and
where regressions recur. The core is identical across surfaces; an
**interface profile** swaps a few slots (see below).

If the target unit does not exist yet, is being redesigned, or came from
Claude Design / visual companion work, run
`docs/process/ui-definition.md` first. Behavior capture should then use
the approved UI definition as its inventory.

A unit can be a whole surface or a behavior-bearing component inside a
surface. For Web / GUI work, that means a screen, route, panel, drawer,
dialog, toolbar, shared component, or widget. Prefer the smallest unit
with a coherent job. Compose larger screen and flow records from smaller
component records when that makes behavior clearer.

## Two levels

- **Level 1 — reusable methodology (this doc + `docs/templates/`):**
  the interview protocol, the behavior-record schema, the document
  architecture, behavior→test mapping rules, coverage tracking, and a
  "how to apply this to a new repo" guide. Lives at the **workspace
  root** so every repo can adopt it.
- **Level 2 — per-repo instantiation (in each repo's `docs/`):** the
  filled-in per-unit + flow behavior specs and the actual E2E tests for
  one specific app. **Pilot: `pdomain-ocr-simple-gui` (Web/GUI profile).**

## Relationship to an existing test audit (reuse + fill)

This process layers **on top of** a bottom-up test audit (e.g.
simple-gui's `docs/specs/2026-05-28-test-suite-audit-reorg-design.md`),
it does not replace it.

**Reuse from the audit:**

- `data-testid` names from the click-path matrix, as selectors in
  behavior records.
- The **good-state / bad-state pairing** standard — every behavior
  yields at least one good-path and one bad-path assertion.
- The `tests/e2e/test_click_paths_<group>.py` grouping — records map
  onto those files.

**Fill (gaps the audit does not cover):**

- **Behavior intent** — the audit records which tests exist, not the
  authoritative behavior each test should prove.
- **Scenario / cross-screen coverage** — the audit is element-level;
  it has no multi-step flows that cross screens.
- **Regression traceability** — no link from a behavior statement to the
  test that verifies it. Our records carry IDs that close that loop.

## Relationship to UI Definition

UI Definition is the upstream process for target UI shape. It defines
layout, regions, elements, selectors, states, composition, and
interaction candidates for a new or redesigned unit. Behavior capture
consumes that UI contract and turns it into testable behavior records.

For a repo that has not been mapped yet, start with
`docs/process/document-existing-repo.md`. That process identifies
user-facing units, shared components, commands, tests, and gaps, then
routes behavior-bearing surfaces here when they need regression specs.

Use the split this way:

- **UI Definition:** what exists on the surface, where it appears, what it
  is called, which states it has, and which selector / widget id / arg
  identifies it.
- **Behavior Capture:** what happens when the user acts, what the user
  observes, what backend or file-system state changes, how errors recover,
  and which tests prove it.

For units with a UI definition, cite it in the behavior spec header:

```markdown
- **UI definition:** `docs/specs/ui/screen-home.md`
```

Behavior capture may start only when the UI definition has:

- An approved target shape.
- A stable unit slug.
- Parent and child unit links, when the unit is composed.
- A complete element inventory.
- Stable selectors, widget ids, or arg names for every interactive
  element.
- A state matrix with good and bad states.
- Interaction candidates that name the immediate UI response.

## Agent Workflow

Use Superpowers before starting behavior capture work.

- In Codex, invoke the relevant `$superpowers:<skill>` form.
- In Claude, use the matching `/superpowers:<skill>` form.
- Use `dispatching-parallel-agents` for independent unit, test, backend,
  and docs discovery.
- Use `verification-before-completion` before claiming records, links, or
  coverage gates are complete.
- Use `writing-plans` only when behavior records are ready to become
  implementation work.

Autonomous discovery should run in parallel when units are independent:

- One agent maps screens, components, commands, and selectors.
- One agent reads tests and extracts existing coverage.
- One agent maps backend calls, files, side effects, and state.
- One agent reads UI definitions, specs, runbooks, and known regressions.
- One agent inspects CI or E2E setup when coverage gating is in scope.

The parent agent owns the behavior model. Subagents should return draft
records, source paths, test paths, and uncertainty. The parent agent
deduplicates records, checks shared components, assigns IDs, and decides
what must be confirmed with the maintainer.

Do not interrupt the user for mechanical findings. Surface items when
the behavior needs judgment:

- Expected behavior is unclear.
- Code and docs disagree.
- A bad-state or recovery path is a product decision.
- A regression tag needs maintainer confirmation.
- A shared component behaves differently by parent context.

## Decisions locked

### Organizing axis — HYBRID

Per-**unit** behavior docs are the **backbone** (they make coverage
auditable, one doc per unit). A *unit* is whatever the surface's profile
says, but it does not have to be a whole screen. It can be a **screen,
route, panel, dialog, drawer, toolbar, shared component, or widget**
(web), a **view/panel/widget** (TUI), or a **command/subcommand/prompt/
output block** (CLI). A small set of named **cross-unit flows** layer on
top to capture multi-step scenarios. Each regression is **tagged** onto
the smallest unit that owns it and, when useful, onto the parent flow.

Shared units should be composable. Define the shared baseline behavior
once, then define context-specific behavior where the parent changes
props, slots, available actions, permissions, or backend collaborators.
Do not duplicate shared behavior across every parent screen.

### Atomic unit — STRUCTURED RECORD with split assertions

Each behavior is a structured record with **separate, required
observable-output and backend/side-effect fields**, so a record is
structurally incomplete until both halves are filled. Completeness is
enforced by the schema, not by discipline.

**Behavior record schema** (frozen; the per-unit template renders each
record as a block, not a table row):

- `ID`: stable identifier, e.g. `B-<UNIT>-NNN`.
- `Unit`: the unit this record lives in.
- `Flow(s)`: cross-unit flow IDs it participates in, if any.
- `Trigger`: the user action that starts the behavior.
- `Preconditions`: required state before the trigger.
- `Observable output`: what the user perceives.
- `Backend / side-effects`: API calls, files, persisted state, or
  downstream calls.
- `Bad-state / error`: the paired failure-path behavior.
- `Tier(s)`: A (deterministic) and/or B (full exercise).
- `Regression`: yes/no plus issue or commit reference.
- `Test`: linked test IDs, using `path::name`.

## Interface profiles

The core above is interface-agnostic. Each surface specializes only a few
**slots**; everything else — the split record, the good/bad pairing, the
interview, IDs, the flow overlay, the two-tier model, and the
ID-traceable generated coverage gate — is **shared**.

**Web / GUI profile**

- Unit: screen, route, or component.
- ID prefix: `B-<SCREEN>` or `B-<COMP>`.
- Trigger: click, type, or keypress.
- Selector: `data-testid`.
- Observable output: DOM text, visible elements, toasts, or route.
- Driver: Playwright.
- Unit file: `screen-<name>.md` or `component-<name>.md`.

**TUI profile**

- Unit: view, panel, or widget.
- ID prefix: `B-<VIEW>` or `B-<WIDGET>`.
- Trigger: keypress or focus change.
- Selector: widget id or role.
- Observable output: rendered terminal frame or widget state.
- Driver: TUI harness, such as Textual `Pilot` or `pexpect`.
- Unit file: `view-<name>.md` or `widget-<name>.md`.

**CLI profile**

- Unit: command, subcommand, prompt, or output block.
- ID prefix: `B-<CMD>`.
- Trigger: command invocation, args, or stdin.
- Selector: flag or arg name.
- Observable output: stdout, stderr, or exit code.
- Driver: subprocess, Click `CliRunner`, Typer, or equivalent.
- Unit file: `command-<name>.md`.

`Backend / side-effects` assertions (API re-query + on-disk artifacts)
are the **same** across profiles — that half of the record never changes.

This repo (`pdomain-ocr-simple-gui`) uses the **Web / GUI** profile. A
sibling like `pdomain-ocr-cli` would use the **CLI** profile with the
identical core.

## Open questions

All core decisions are resolved (see "Decisions locked" and the sections
above). Pending: maintainer review of this doc, then a writing-plans pass
to turn the simple-gui pilot into an executable plan.

## Interview protocol

**Cadence — hybrid drafting, one unit at a time.** The agent does the
heavy lifting from code; the maintainer supplies intent the code can't
reveal and corrects wrong assumptions.

Per unit:

1. **Inventory.** If a UI definition exists, read
   `docs/specs/ui/<unit>.md` first and use its regions, element
   inventory, selectors, states, and interaction candidates as the
   starting inventory. Then read the unit's implementation (web:
   component + route + backend endpoints; TUI: view + widgets + handlers;
   CLI: command + args/flags + what it calls) to find any drift. If the
   unit is new or being redesigned and has no UI definition yet, stop and
   run `docs/process/ui-definition.md`.
2. **Draft.** Agent pre-fills proposed behavior records (full schema) for
   the obvious / mechanical behaviors.
3. **Interview.** Agent presents the draft and actively asks the
   maintainer about the parts code can't settle: ambiguous behaviors,
   edge cases, failure paths, and known regressions. Maintainer
   confirms / corrects / adds.
4. **Lock.** Finalize the unit's records, assign IDs, tag regressions.
   `Test` fields stay empty until the tests are written.
5. **Next unit.**

After the per-unit passes, a final **flow-overlay pass** captures the
named cross-unit scenarios that string locked records together.

## Document architecture

Level 2 (the filled-in specs) lives under each repo's
`docs/specs/behavior/`:

- `README.md` — what's here and how to read the coverage report.
- `<unit>-<name>.md` — **one per unit** (`screen-…` or `component-…`
  web, `view-…` or `widget-…` TUI, `command-…` CLI); holds that unit's
  behavior records (one block per record, per the template) plus a
  "Known regressions" subsection.
- `flows.md` — the cross-unit **flow overlay**: named flows that chain
  record IDs into multi-step scenarios.
- `coverage.md` — **generated** by the audit script; never edited by hand.

If the unit was defined through UI Definition, the source UI contracts
live beside the behavior specs under `docs/specs/ui/`. Store Claude
Design exports, screenshots, or other prototype artifacts under
`docs/specs/ui/assets/<unit-slug>/`.

**IDs.** `B-<UNIT>-NNN` for behaviors (`B-HOME-001`, `B-PAGEVIEW-012`,
`B-UPLOAD-DROPZONE-001`, or e.g. `B-RUN-003` for a CLI command);
`F-<FLOW>-NN` for flows. The simple-gui pilot uses the Web/GUI profile;
its screen-level units are `home`, `results`, `page-view`, and
`app-shell`; component units may be added where behavior is shared or
complex enough to test independently.

**Tests.** For the Web/GUI pilot, Tier A lives in the existing
`tests/e2e/test_click_paths_<group>.py` grouping; Tier B (real engine)
in `tests/e2e/test_real_ocr_<flow>.py` or marked within the same files.
Other profiles use their own driver but the same citation rule: each test
names the IDs it covers.

## Behavior → test mapping

**Backend / side-effects assertions: both API and filesystem.** After
each trigger the test re-queries the relevant endpoint (or re-reads
state) **and** inspects the on-disk artifacts (sidecar JSON, combined
`.txt`, output dir). This half is identical across interface profiles —
only the *driver* that fires the trigger and reads the observable output
changes (Playwright / TUI harness / subprocess). Every record produces at
least one good-path and one bad-path assertion (the audit's good/bad
standard).

**Two execution tiers:**

- **Tier A — deterministic (default CI).** The heavy / external /
  nondeterministic dependency is faked; for an OCR app that means OCR runs
  through the fake dispatcher (the M5 seam), so output is fixed, fast, and
  GPU-free. *Every* behavior record is covered here. For the Web/GUI pilot
  these are the `full-e2e` Playwright tests in
  `tests/e2e/test_click_paths_<group>.py`.
- **Tier B — full exercise with the real dependency (opt-in).** A small
  set of golden-path scenarios run the **real** dependency end to end —
  for this app, the real OCR engine on the GPU (upload → real OCR →
  results → output reflects real text), validating the pipeline the fake
  stands in for. Marked (e.g. `@pytest.mark.real_ocr`) and run locally,
  not in the default fast suite. Because real output varies, Tier B
  asserts against a fixed fixture with a known-good transcript and uses
  tolerant assertions (non-empty, structural invariants, fuzzy match)
  rather than brittle exact-string checks.

Each record's `Tier(s)` field says which tier(s) cover it: OCR-producing
behaviors get both A and B; everything else gets A only.

## Coverage tracking

Single source of truth = the behavior records. Coverage status is
**generated**, never hand-maintained, so it cannot drift.

- **Stable IDs.** Each record has an ID (`B-<UNIT>-NNN`); each flow has
  an ID (`F-<FLOW>-NN`).
- **Tests cite their behavior IDs.** Every E2E test names the record(s)
  it covers — in a docstring (`Covers: B-PAGEVIEW-012`) or a marker
  (`@behavior("B-PAGEVIEW-012")`).
- **Derived status.** The audit script computes each record's status
  rather than storing it: `specified` (record exists, no test cites it) →
  `test-written` (a test cites it) → `passing` (that test is green).
- **Audit script + report.** A script scans the behavior docs for
  declared IDs and the test tree for cited IDs, then writes
  `coverage.md` (generated, do-not-edit) listing per-record tier
  coverage and derived status, and flagging:
  - **orphan records** — specified but no test cites them;
  - **unlinked citations** — a test cites an ID no record declares
    (typo / stale).
- **Gate.** The report runs as a `make` target and a CI / DoD gate
  (mirroring the audit's M6 grep gates): the build fails if a
  regression-tagged record is uncovered, or if a cited ID has no
  declaring record.

## Applying this to a new repo

1. **Pick the interface profile** (Web/GUI, TUI, or CLI).
2. **Define target UI where needed.** For new or redesigned units, copy
   `docs/templates/ui-unit-definition.md` into the target repo's
   `docs/specs/ui/`, store prototype artifacts under
   `docs/specs/ui/assets/<unit-slug>/`, and get maintainer approval.
3. **Surface map.** Run an `Explore` agent to inventory the units
   (screens / views / commands and behavior-bearing components), their
   triggers, the code behind them, backend collaborators, and existing
   tests.
4. **Scaffold.** Copy the templates from `docs/templates/` into the
   repo's `docs/specs/behavior/` (one `<unit>-<name>.md` per unit, plus
   `flows.md` and `README.md`).
5. **Interview per unit** using the hybrid protocol above; lock records,
   assign IDs, tag regressions.
6. **Flow-overlay pass.** Capture named cross-unit flows in `flows.md`.
7. **Write Tier A tests** (heavy dep faked) with the profile's driver,
   each citing its IDs.
8. **Write Tier B tests** (real dep, opt-in) for the golden-path
   behaviors that exercise the real dependency.
9. **Wire the audit.** Add the coverage-audit script, a `make` target,
   and a CI gate; generate `coverage.md`.
10. **Maintain.** Records stay the source of truth; regenerate the report
   on every change. New regressions become new records with a
   `Regression` reference before the fix lands.

## Templates

Blank scaffolds live in `docs/templates/`:

- `behavior-unit-spec.md` — per-unit spec skeleton (screen / component /
  view / widget / command), with the record schema inline, web + CLI
  worked examples, and a "Known regressions" subsection.
- `behavior-flows.md` — the cross-unit flow-overlay skeleton.
- `ui-unit-definition.md` — per-unit UI definition skeleton for new or
  redesigned surfaces.

Copy UI templates into `docs/specs/ui/`. Copy behavior templates into
`docs/specs/behavior/`, renaming `behavior-unit-spec.md` to
`<unit>-<name>.md` per your profile.

## TUI profile notes (se-llm-skills cockpit pilot)

Lessons from the behavior-e2e TUI rollout plan (M0–M4) in
[`se-llm-skills`](../../se-llm-skills/docs/plans/2026-05-30-behavior-e2e-tui-rollout.md).

**In-process router driver is the Tier A baseline.**

The se-llm-skills cockpit uses a custom in-house TUI framework
(`router.py`, `screen_base.py`, `cockpit.py`). The winning Tier A driver
calls `screen.handle(key)` / `screen.render()` directly. This runs
sub-millisecond per test and is fully xdist-safe. See
`se-llm-skills/docs/decisions/2026-05-30-tui-e2e-driver.md` for the
decision and trade-offs.

**Custom in-house TUI: ScreenContext + handle() + injectable seams.**

When the TUI is built on a custom framework (not Textual or similar),
the Pilot-equivalent pattern emerges naturally:

1. `ScreenContext` holds any screen-level state not in `CockpitState`.
2. Each screen exports a `handle(key, ctx) -> CockpitState` and a
   `render(state, ctx) -> str` (or equivalent).
3. Injectable seams (mock `count_uncommitted`, `RunRegistry`, etc.) let
   Tier A tests set up any precondition in-process.

Reusable conceptually for any custom-framework TUI.

**Regression record discipline.**

The simple-gui pattern carries over verbatim: one record per behavior,
`Regression: yes` in the body. NO `-REG` suffix on the ID. The scanner
matches `**Regression:** yes` case-insensitively in the body.

**xdist group naming.**

Use `behavior-tui-<unit>` per behavior unit. Example:
`pytestmark = pytest.mark.xdist_group("behavior-tui-home")`.

**SE_LLM_PTY_TIMEOUT env var for Tier B.**

`SE_LLM_PTY_TIMEOUT` (float seconds, default 10) controls the `wait_for`
timeout in `tests/terminal_app/_pty.py`. Set to 15 in CI for the
pty-marked test suite. Real-runner Tier B tests use their own hard-coded
deadlines (30–120 s) because they wait for a real LLM call.

**launch_code factory injection for pty fixtures.**

The `CockpitPty` constructor accepts an optional `launch_code` string (a
`python -c` body) to inject pre-seeded state (registry records, config)
before `console_main()` starts. Keeps tests hermetic without filesystem
seeding.

**flows.md discipline.**

Cross-unit flows belong in `docs/specs/behavior/flows.md`. Single-screen
key-handling sub-sequences are NOT flows — they are behavior records in
the per-unit spec. If a per-unit spec declares `F-UNIT-NNN` IDs in a
`## Flows` section, audit each one: if it doesn't cross into another
screen, demote it (clear the ID, leave as prose). The scanner detects
declared F-IDs as orphans if they have no test citation.

## CLI profile notes (se-llm-skills wave)

Lessons from the behavior-E2E CLI rollout plan (M0–M-DOD) covering 25
CLI units: 9 skills and 16 `se-llm` subcommands. See
[`se-llm-skills/docs/decisions/2026-05-31-cli-e2e-driver.md`](../../se-llm-skills/docs/decisions/2026-05-31-cli-e2e-driver.md).

**In-process Python pipeline modules as the Tier A baseline.**

Six of the nine skills have callable Python pipeline entry points. Tier
A tests import those modules directly and call the entry function. Same
in-process driver pattern as the TUI plan: no subprocess, no LLM call.

In-process skills: `se-llm-review`, `se-llm-lint-fix`,
`se-llm-commit-check`, `se-llm-commit-check-workflow`, `se-llm-classify`,
`se-llm-tool-verify`. CLI subcommands (`doctor`, `run`, `status`, etc.)
each have an importable handler (`run_doctor`, `run_run`, …) in
`se_llm_skills/cli/main.py`.

**FakeSkillAgent full-lifecycle mock for harness-only skills.**

Three skills have no callable Python entry. Their contract is the
result JSON written to `result_path`. Tier A tests use a
`FakeSkillAgent` fixture (in `tests/e2e/cli/conftest.py`) simulating
the harness dispatch lifecycle: skill load, args/env forwarding,
execution, exit. The harness-only skills: `se-llm-section-review`,
`se-llm-xhtml-rule-review`, `se-llm-preapply-classify`.

**SKILL.md prose IS Tier-A testable where it documents Python-enforced behavior.**

Example: BATCH_SIZE. SKILL.md says "up to N concurrent agents per
wave." The Python enforcement is `ReviewOptions.jobs=N` setting
`max_workers` on the `ThreadPoolExecutor`. Tier A test asserts the
executor fires `ceil(N/B)` batches with ≤B concurrent tasks. The
SKILL.md is the spec; Python is the implementation. Where there is no
Python enforcement (e.g. "ask the user" dialogue), the prose is not
Tier A-testable.

**xdist group naming.**

Every CLI behavior-E2E test gets
`@pytest.mark.xdist_group("behavior-cli-<unit>")`. The `<unit>` slug
matches the behavior spec filename
(`command-se-llm-review` → `behavior-cli-command-se-llm-review`).

**Source-checkout-only commands need explicit gating.**

`rules validate` and `assets build-runtime` only work in a live source
checkout. Behavior records note `Preconditions: source checkout
required`. Tests skip in package-install mode.

**Tier B CLI driver: FakeRunner artifact contract.**

CLI Tier B tests inject a FakeRunner that returns pre-baked structs
(e.g. `LintCommandOutput`, `ReviewResult`). Exercises orchestrator +
file-path discipline without a real LLM. Marked `@pytest.mark.real_runner`
and excluded from `make test`. Run with `make e2e-real-runner` (now
covers both TUI and CLI Tier B tests).

**Tier B skip-vs-pass asymmetry between profiles.**

TUI Tier B tests skip when no runner binary is on `PATH` (they need a
real terminal subprocess). CLI Tier B tests pass unconditionally
because they inject a fake runner, not a real binary. Both modes
satisfy the methodology's "Tier B exercises real dependency end-to-end
contract"; the realness lives at different layers.
