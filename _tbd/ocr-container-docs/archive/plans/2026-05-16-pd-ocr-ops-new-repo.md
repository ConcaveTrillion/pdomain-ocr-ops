---
milestone: 7
repo: ConcaveTrillion/ocr-container-meta
status: complete
synced: 2026-05-17
---

# pdomain-ocr-ops — new repo: suite plumbing, prefs, GPU dispatch protocols

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the new Python library + tiny CLI `pdomain-ocr-ops` that every
end-user pd-* SPA depends on for suite plumbing — installed-app registry,
shared UI prefs, sibling launching, desktop-launcher stub, and the
local-mode adapters for GPU dispatch (short stage calls + long-running
jobs). The library defines the **adapter Protocol seams** for hosted mode
(Suite registry / Prefs / Sibling launch / Auth / Storage / Stage dispatch
/ Long job runner) but Phase 1 ships **only the local-mode implementation
of each**.

**Scope position in Phase 1:** This is the largest Phase 1 plan and the
gating one for every app's suite integration (`pd_ocr_ops.suite.mount_routes`
is the contract pdomain-ui's launcher + UIPrefs hooks call against). It is
**independent of plans #1 (pdomain-book-tools), #4 (pdomain-index-npm), and #6
(agent definitions)**. Plan **#7 (Phase 1.7 — migrate pgdp-prep's
`STAGE_IMPL` registry + Modal adapters into pdomain-ocr-ops) depends on this
plan**: the protocols and local adapter must already exist before
pgdp-prep's code moves in.

**Architecture:** Standard pd-* layout (hatchling, `uv`, `make ci AI=1`),
ConcaveTrillion org metadata, `concavetrillion@gmail.com` author. Published
as a wheel to `pdomain-index-pip` (post-rename) — apps `pip install pdomain-ocr-ops`
the same way they install `pdomain-book-tools`. The package surface:

```
pd_ocr_ops/
+- suite/
|   +- types.py            # SuiteApp, InstalledApp, UIPrefs, SuiteAdapters
|   +- registry.py         # SuiteRegistryAdapter Protocol + LocalTomlSuiteRegistry
|   +- prefs.py            # PrefsAdapter Protocol + LocalFilePrefs
|   +- sibling_spawn.py    # SiblingLaunchAdapter Protocol + LocalSpawnLauncher
|   +- desktop.py          # install_shortcut() / remove_shortcut() stubs (Phase 4)
|   +- auth.py             # AuthAdapter Protocol + NoAuthAdapter
|   +- storage.py          # StorageAdapter Protocol + LocalFsStorage
|   +- routes.py           # mount_routes(app, adapters) FastAPI router
|   +- paths.py            # XDG-aware helpers (platformdirs)
|   +- __init__.py         # public re-exports
+- gpu/
|   +- types.py            # StageResult, JobStatus, JobEvent, JobSpec
|   +- protocols.py        # StageDispatcher + LongJobRunner Protocol classes
|   +- device.py           # pick_device() helper
|   +- local_stage.py      # LocalStageDispatcher (in-process registry)
|   +- local_jobs.py       # LocalLongJobRunner + SQLite jobs table
|   +- __init__.py
+- schemas/
|   +- __init__.py
|   +- __main__.py         # `python -m pd_ocr_ops.schemas`
|   +- emit.py             # CLI mirroring pdomain-book-tools' shape
+- __init__.py             # version + public re-exports
```

Per the cross-cut spec's hard design principle (§1.4): **pdomain-ocr-ops is a
library + tiny CLI, not a daemon.** It runs in-process inside each app's
FastAPI server. Each pd-* app stays independently installable; pdomain-ocr-ops
is an optional add-on for apps that participate in the suite.

**Tech Stack:** Python 3.11+ (matches the pd-* baseline), hatchling build
backend, Pydantic v2 for types (matches §8 spec snippets), `platformdirs`
for XDG paths, `filelock` for advisory locks on shared files, `tomli` +
`tomli-w` for `installed.toml` IO, `httpx` for `/healthz` polling, FastAPI
as a peer dep (not a runtime dep — the library mounts onto apps' FastAPI
instances), `sqlite3` from stdlib for the jobs table, pytest via
`uv run pytest -n auto`.

**Working directory for all commands:** `/workspaces/ocr-container/pdomain-ocr-ops/`

> **DO NOT commit. DO NOT push. DO NOT create the repo as part of this plan
> file.** This plan describes the work; an agent executing it will scaffold
> the repo on the first task.

---

## Milestone M0: Repo scaffold

Stand up an empty repo conforming to the pd-* conventions, with the
toolchain (`uv`, `hatchling`, `ruff`, `pytest`, `make ci AI=1`) wired and a
single hello-world test green. No package surface yet — that lands in M1+.

### Task 0.1: Create repo + git init {#create-repo-git-init}

**Why:** Without a repo at `/workspaces/ocr-container/pdomain-ocr-ops/`, nothing
else has a home. Workspace `.gitignore` already lists `/pdomain-ocr-ops/` per
the spec's Phase 1 done criteria, so the workspace clone doesn't accidentally
absorb it.

**What:**
- `mkdir /workspaces/ocr-container/pdomain-ocr-ops && cd` into it
- `git init`
- Copy author/email/repo-URL convention from a sibling pd-* (e.g.
  `pdomain-book-tools/.git/config` `[user]` block and `[remote "origin"]` URL
  pattern — but the new repo is `git@github.com:ConcaveTrillion/pdomain-ocr-ops.git`).
- `git remote add origin git@github.com:ConcaveTrillion/pdomain-ocr-ops.git`
  (the actual remote is **not** created in this plan — defer to the
  release task in M12).

**TDD steps:** None — pure scaffold.

**Acceptance:** `git status` runs from the repo root; remote is configured
but not pushed.

### Task 0.2: `pyproject.toml` with ConcaveTrillion metadata {#pyprojecttoml-with-concavetrillion-metadata}

**Why:** Locks the build system, project name, version, author, deps. Mirrors
`pdomain-book-tools/pyproject.toml`'s shape so the agent that publishes this can
reuse the workspace's release helpers untouched.

**What:** Write `pyproject.toml`:
- `[project] name = "pdomain-ocr-ops"`, `version = "0.1.0"`,
  `description = "Suite plumbing and GPU dispatch adapters for the pd-* OCR suite"`,
  `authors = [{ name = "CT", email = "concavetrillion@gmail.com" }]`,
  `license = { text = "MIT" }`,
  `requires-python = ">=3.11"`,
  `readme = "README.md"`.
- `dependencies = [` (alphabetical): `"fastapi>=0.110"`,
  `"filelock>=3.13"`, `"httpx>=0.27"`, `"platformdirs>=4.2"`,
  `"pydantic>=2.5"`, `"tomli>=2.0"`, `"tomli-w>=1.0"`,
  `"uvicorn>=0.30"`.
- `[project.scripts]` entry: `pdomain-ocr-ops-schemas = "pd_ocr_ops.schemas.emit:main"`
  (mirror pattern; the canonical invocation is still
  `python -m pd_ocr_ops.schemas`).
- `[project.urls]` `Homepage = "https://github.com/ConcaveTrillion/pdomain-ocr-ops"`,
  `Source = "https://github.com/ConcaveTrillion/pdomain-ocr-ops"`.
- `[build-system] requires = ["hatchling"]`, `build-backend = "hatchling.build"`.
- `[tool.hatch.build.targets.wheel] packages = ["pd_ocr_ops"]`.
- `[tool.uv.sources]` — initially empty; if any pd-* dep later lands a
  direct dependency here (none in Phase 1), this is where the
  `pdomain-index-pip` extra index would be wired the way other pd-* repos do.
- `[tool.ruff]` + `[tool.ruff.lint]` copying `pdomain-book-tools/pyproject.toml`
  conventions (line-length 100, target-version py311, select `E,F,W,I`).
- `[tool.pytest.ini_options]` with `addopts = "-ra"`, `testpaths = ["tests"]`,
  `asyncio_mode = "auto"`.

**TDD steps:** None — config file.

**Acceptance:** `uv sync` resolves cleanly into a fresh `.venv/`. `uv run python -c "import sys; print(sys.version_info)"` prints 3.11 or newer.

### Task 0.3: `Makefile` with the pd-* canonical target set {#makefile-with-the-pd-canonical-target-set}

**Why:** Every agent harness (`/ship-slice`, `ship-issue`, bots) calls
`make ci AI=1`. The repo cannot enter the rotation without this target.

**What:** Copy `pdomain-book-tools/Makefile`'s shape, keeping only what pdomain-ocr-ops
needs in Phase 1. Targets:
- `setup` — `uv sync`
- `lint` — `uv run ruff check pd_ocr_ops tests`
- `format` — `uv run ruff format pd_ocr_ops tests`
- `test` — `uv run pytest -n auto`
- `ci` — `lint` + `test`, with `AI=1` capturing to `.ci-ai.log` and printing
  `✅` on pass, filtered failure tail on error (copy the awk filter from
  `pdomain-book-tools/Makefile`).
- `build` — `uv build`
- `clean` — `rm -rf dist .venv .pytest_cache .ruff_cache .ci-ai.log`

**TDD steps:** None.

**Acceptance:** `make ci AI=1` runs (vacuously green at this point — no
tests yet) and writes `.ci-ai.log`.

### Task 0.4: `.gitignore`, `LICENSE`, minimal `README.md` {#gitignore-license-minimal-readmemd}

**Why:** Standard repo hygiene. `LICENSE` mirrors pdomain-book-tools (MIT, CT
copyright). `README.md` is one paragraph; the spec is the source of truth.

**What:**
- `.gitignore`: copy `pdomain-book-tools/.gitignore` verbatim, then ensure
  `.claude/` is listed (so any leaked agent memory stays invisible per
  workspace CLAUDE.md leakage check).
- `LICENSE`: MIT, `Copyright (c) 2026 CT`.
- `README.md`: 5 lines — name, one-sentence description ("Library + tiny
  CLI providing suite plumbing, shared prefs, and GPU dispatch adapters
  for the pd-* OCR suite"), pointer to
  `docs/superpowers/specs/2026-05-16-cross-cut-design.md` in the workspace,
  pointer to `python -m pd_ocr_ops.schemas`.

**TDD steps:** None.

**Acceptance:** `git add -A && git status` shows the expected file set;
nothing absent.

### Task 0.5: GitHub Actions CI workflow {#github-actions-ci-workflow}

**Why:** Every pd-* repo has a `.github/workflows/ci.yml` that runs
`make ci AI=1` on `pull_request` and `push` to `main`. The bot rotation
relies on this contract.

**What:** Copy `pdomain-book-tools/.github/workflows/ci.yml` and adjust:
- Job name `pdomain-ocr-ops CI`.
- Python matrix `[3.11, 3.12, 3.13]` (match the sibling).
- Step `make ci AI=1` is the only build step.
- Cache `~/.cache/uv` keyed by `pyproject.toml` hash.

**TDD steps:** None.

**Acceptance:** Workflow file is syntactically valid YAML; `act --list`
(if available locally) shows one job. (Will not actually run until the
repo is pushed; that's in M12.)

### Task 0.6: First sentinel test (`tests/test_sentinel.py`) {#first-sentinel-test-teststestsentinelpy}

**Why:** `make ci AI=1` needs at least one test to exercise the test
harness end-to-end. Also smoke-tests that `pd_ocr_ops` imports.

**TDD steps:**
- [ ] Write `tests/test_sentinel.py` with one test:
  - `test_pd_ocr_ops_imports`: `import pd_ocr_ops; assert pd_ocr_ops.__version__ == "0.1.0"`
- [ ] Run `uv run pytest -v` — fails: `ModuleNotFoundError: No module named 'pd_ocr_ops'`.
- [ ] Create `pd_ocr_ops/__init__.py` with `__version__ = "0.1.0"`.
- [ ] Re-run `uv run pytest -v` — 1 passed.
- [ ] Run `make ci AI=1` — green; `.ci-ai.log` shows the pytest line.

**Acceptance:** 1 test passes; `make ci AI=1` exits 0.

---

## Milestone M1: Suite types (Pydantic models)

Define the data shapes that flow through `mount_routes()` and the adapter
protocols. Per spec §8, these are Pydantic v2 models. They are the
serializable surface that `pd_ocr_ops.schemas.emit` will dump as JSON
Schema in M10 for pdomain-ui to consume.

### Task 1.1: `SuiteApp` (catalog entry from `pd-suite.json`) {#suiteapp-catalog-entry-from-pd-suitejson}

**Why:** The baseline catalog of known suite apps (name, icon, default
port, package) — distinct from the *installed* registry. Per spec §3
"AppShell launcher … `pd-suite.json` cataloging known suite apps."

**What:** Fields per spec §3 / §4 / §8:
- `app_id: str` (slug, e.g. `"pdomain-ocr-labeler-spa"`)
- `display_name: str`
- `package: str` (Python package name)
- `default_port: int`
- `icon: str` (icon-set slug, e.g. `"labeler"`; resolved by pdomain-ui)
- `description: str | None = None`
- `binary_name: str | None = None` (CLI shim name; defaults to
  `app_id` when None)

**TDD steps:**
- [ ] Write `tests/suite/test_types_suite_app.py`:
  - `test_suite_app_constructs_minimum_fields`: build with required fields
    only, assert defaults are None / empty as expected.
  - `test_suite_app_extra_fields_forbidden`: assert `ValidationError` on
    unknown keyword (validates `model_config = ConfigDict(extra="forbid")`).
  - `test_suite_app_roundtrip_json`: `SuiteApp.model_validate(app.model_dump())` equal.
- [ ] Run `uv run pytest tests/suite/test_types_suite_app.py -v` — fails:
  module not found.
- [ ] Create `pd_ocr_ops/suite/__init__.py` (empty stub).
- [ ] Create `pd_ocr_ops/suite/types.py` with the `SuiteApp` model.
- [ ] Re-run — 3 passed.

**Acceptance:** Model exists, `extra="forbid"`, roundtrips JSON.

### Task 1.2: `InstalledApp` (registry-row shape from `installed.toml`) {#installedapp-registry-row-shape-from-installedtoml}

**Why:** A *concrete* install of a `SuiteApp` — has a binary path, an
on-disk version, and an opt-in flag. Per spec §3 "Sibling discovery":
the `[apps.<id>]` TOML block.

**What:** Fields:
- `app_id: str`
- `package: str`
- `version: str`
- `binary: str` (absolute path)
- `default_port: int`
- `icon: str`
- `display_name: str`
- `enabled: bool = True` (opt-in toggle for "show me in the launcher")
- `registered_at: datetime` (ISO 8601 in JSON; `datetime.now(UTC)` default)

**TDD steps:**
- [ ] Write `tests/suite/test_types_installed_app.py`:
  - `test_installed_app_constructs`: positive case.
  - `test_installed_app_requires_absolute_binary`: validator rejects a
    relative binary path with `ValidationError` containing "absolute".
    (Use `@field_validator("binary")`.)
  - `test_installed_app_roundtrip`: `model_dump(mode="json")` -> validate.
- [ ] Run — fails.
- [ ] Add the model to `pd_ocr_ops/suite/types.py`.
- [ ] Re-run — 3 passed.

**Acceptance:** Model exists, validates absolute path, roundtrips.

### Task 1.3: `UIPrefs` (shared cross-app prefs) {#uiprefs-shared-cross-app-prefs}

**Why:** Per spec §4 "Cross-cutting concern: shared UI prefs" — `common`
section with theme/density/accent/font-size/layer-colors, plus per-app
extensions as a free-form `dict[str, Any]`.

**What:** Three nested models:
- `LayerColors`: `word: str`, `line: str`, `para: str`, `block: str`
  (hex strings; validators reject non-`#RRGGBB`).
- `CommonUIPrefs`:
  - `theme: Literal["light","dark"] = "dark"`
  - `density: Literal["compact","normal","comfortable"] = "normal"`
  - `accent: str = "#d6925a"` (hex validator)
  - `font_size_base: int = 12` (range 8..24)
  - `layer_colors: LayerColors`
- `UIPrefs`:
  - `common: CommonUIPrefs`
  - `apps: dict[str, dict[str, Any]] = {}`  # per-app extensions

**TDD steps:**
- [ ] Write `tests/suite/test_types_ui_prefs.py`:
  - `test_ui_prefs_defaults_match_spec`: build `UIPrefs()` and assert
    `common.theme == "dark"`, `common.accent == "#d6925a"`,
    `common.density == "normal"`, and `apps == {}`.
  - `test_ui_prefs_rejects_bad_hex_accent`: `accent="orange"` raises.
  - `test_ui_prefs_rejects_bad_font_size`: `font_size_base=200` raises.
  - `test_ui_prefs_apps_freeform_dict`: setting
    `apps={"pdomain-ocr-labeler-spa": {"show_match_diff_default": "fuzzy-and-mismatch"}}`
    roundtrips through JSON.
- [ ] Run — fails.
- [ ] Add the three models to `pd_ocr_ops/suite/types.py`.
- [ ] Re-run — 4 passed.

**Acceptance:** Defaults match the JSON example in spec §4; hex + font
validators in place.

### Task 1.4: `SuiteAdapters` aggregate model {#suiteadapters-aggregate-model}

**Why:** Per spec §8 "Suite-adapter wiring" — this is the bundle passed
to `mount_routes(app, adapters)`. Phase 1 supplies the local-mode default
via `SuiteAdapters.local()`. `from_env()` is a stub raising
`NotImplementedError("hosted-mode adapters land in Phase 4")` to keep the
shape but make the deferral explicit.

**What:** Per spec §8 snippet:

```python
class SuiteAdapters(BaseModel):
    registry: SuiteRegistryAdapter
    prefs:    PrefsAdapter
    launcher: SiblingLaunchAdapter
    auth:     AuthAdapter
    storage:  StorageAdapter

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def local(cls) -> "SuiteAdapters": ...
    @classmethod
    def from_env(cls) -> "SuiteAdapters":
        raise NotImplementedError(...)
```

Because Protocol classes don't satisfy Pydantic's normal field typing,
`arbitrary_types_allowed=True` is required. The adapters themselves
(M2–M3, M5, M11) are plain Python classes implementing the Protocols.

**TDD steps:**
- [ ] Write `tests/suite/test_types_suite_adapters.py`:
  - `test_suite_adapters_local_returns_bundle`: skipped initially with
    `pytest.skip("requires adapters; lands when each adapter ships")`;
    will be un-skipped per-milestone as adapters land.
  - `test_suite_adapters_from_env_raises_not_implemented`: confirm the
    explicit message mentions "Phase 4" or "hosted".
- [ ] Run — fails: `SuiteAdapters` doesn't exist.
- [ ] Stub Protocols (`SuiteRegistryAdapter`, etc.) as empty Protocol
  classes in their respective module stubs (`suite/registry.py`,
  `suite/prefs.py`, `suite/sibling_spawn.py`, `suite/auth.py`,
  `suite/storage.py`). Each just declares `class XAdapter(Protocol): ...`.
- [ ] Add `SuiteAdapters` to `suite/types.py`, with `local()` raising
  `NotImplementedError("adapter wiring lands in M2–M11; SuiteAdapters.local() is the M11 task")`
  and `from_env()` raising as above.
- [ ] Re-run — 2 tests; one skipped, one passed.

**Acceptance:** Type compiles; both classmethods raise; per-Protocol stubs
exist so later milestones fill in concrete classes.

---

## Milestone M2: `LocalTomlSuiteRegistry` adapter

Implements the `SuiteRegistryAdapter` Protocol for local mode. Reads and
writes `~/.local/share/pd-suite/installed.toml` (resolved via
`platformdirs`). Per spec §3 "Lifecycle":

1. `register_self()` writes/refreshes the app's own block.
2. `--unregister-suite` removes it.
3. Reads prune stale entries when the `binary` path no longer exists.

### Task 2.1: `paths.py` — XDG-aware helpers {#pathspy-xdg-aware-helpers}

**Why:** Centralize the `~/.local/share/pd-suite/...` paths so the
adapters and tests have one canonical location, and so monkey-patching
the directory for tests is one-liner.

**What:** Functions:
- `suite_data_dir() -> Path` — wraps `platformdirs.user_data_dir("pd-suite",
  appauthor=False)` and returns a `Path`. Creates the dir if missing
  (idempotent `mkdir(parents=True, exist_ok=True)`).
- `installed_toml_path() -> Path` — `suite_data_dir() / "installed.toml"`.
- `ui_prefs_json_path() -> Path` — `suite_data_dir() / "ui-prefs.json"`.
- `jobs_db_path() -> Path` — `suite_data_dir() / "jobs.db"`.

All four read `PD_SUITE_DATA_DIR` env var as an override (used by tests
and by future container deployments).

**TDD steps:**
- [ ] Write `tests/suite/test_paths.py`:
  - `test_suite_data_dir_returns_path_and_creates(tmp_path, monkeypatch)`:
    set `PD_SUITE_DATA_DIR=tmp_path`, call, assert dir exists.
  - `test_installed_toml_path_under_data_dir(tmp_path, monkeypatch)`:
    assert path is `tmp_path / "installed.toml"`.
  - Same for `ui_prefs_json_path`, `jobs_db_path`.
- [ ] Run — fails.
- [ ] Create `pd_ocr_ops/suite/paths.py` implementing the four functions.
- [ ] Re-run — 4 passed.

**Acceptance:** All four functions resolve under the env-var override.

### Task 2.2: `SuiteRegistryAdapter` Protocol shape {#suiteregistryadapter-protocol-shape}

**Why:** Locks the API surface that hosted-mode adapters (e.g.
`EnvSuiteRegistry`, `DBSuiteRegistry` per spec §8) will satisfy without
touching app code or pdomain-ui.

**What:** In `pd_ocr_ops/suite/registry.py` (replacing the M1.4 stub):

```python
class SuiteRegistryAdapter(Protocol):
    def list_installed(self) -> list[InstalledApp]: ...
    def register(self, app: InstalledApp) -> None: ...
    def unregister(self, app_id: str) -> None: ...
```

`list_installed()` is the read API — the route helper in M4 calls it.
`register`/`unregister` are the lifecycle calls each pd-* SPA makes on
startup / `--unregister-suite` (those CLI flags live in each app, not in
pdomain-ocr-ops).

**TDD steps:**
- [ ] Write `tests/suite/test_registry_protocol.py`:
  - `test_protocol_methods_present`: assert `hasattr(SuiteRegistryAdapter, "list_installed")` etc.
  - `test_protocol_is_runtime_checkable`: confirm `@runtime_checkable`
    decorator applied (so `isinstance(obj, SuiteRegistryAdapter)` works).
- [ ] Run — fails (stub only).
- [ ] Fill `suite/registry.py`.
- [ ] Re-run — 2 passed.

**Acceptance:** Protocol exists, runtime-checkable.

### Task 2.3: `LocalTomlSuiteRegistry` read {#localtomlsuiteregistry-read}

**Why:** First half of the round-trip — proves the spec §3 TOML shape is
what we serialize, and that stale-entry pruning works.

**TDD steps:**
- [ ] Write `tests/suite/test_local_toml_registry_read.py`:
  - `test_read_empty_when_no_file(tmp_path, monkeypatch)`: no
    `installed.toml`; `list_installed()` returns `[]`.
  - `test_read_parses_spec_example(tmp_path, monkeypatch)`: write the
    spec §3 example TOML to `tmp_path/installed.toml`, point the registry
    at it, get back one `InstalledApp` with `app_id="pdomain-ocr-labeler-spa"`,
    `version="0.4.2"`, `default_port=8001`.
  - `test_read_prunes_stale_entries(tmp_path, monkeypatch)`: TOML lists
    two apps; only one's `binary` path exists on disk; result excludes
    the stale entry. Stale rows are **dropped from the in-memory result**
    only — disk pruning is task 2.4.
  - `test_read_uses_filelock(tmp_path, monkeypatch)`: spy/mock the
    `filelock.FileLock`; assert acquired during read. (Use
    `unittest.mock.patch.object(filelock, "FileLock", spy)` — verify
    `__enter__` called.)
- [ ] Run — fails.
- [ ] Implement `LocalTomlSuiteRegistry.__init__(self, root: Path | None = None)`
  (defaults to `paths.installed_toml_path()`) and
  `list_installed() -> list[InstalledApp]` using `tomllib`/`tomli` for
  parsing and `filelock.FileLock(root.with_suffix(".toml.lock"))` for
  advisory locking.
- [ ] Re-run — 4 passed.

**Acceptance:** Read parses spec example; stale entries pruned in
result; lock acquired.

### Task 2.4: `LocalTomlSuiteRegistry` register + unregister {#localtomlsuiteregistry-register-unregister}

**Why:** Second half — proves apps can self-register on first run.

**TDD steps:**
- [ ] Write `tests/suite/test_local_toml_registry_write.py`:
  - `test_register_writes_new_entry`: empty file -> `register(app)` ->
    file contains `[apps.<id>]` block with matching keys.
  - `test_register_refreshes_existing_entry`: same `app_id`, different
    version -> single block, new version.
  - `test_register_preserves_other_apps`: pre-existing entry for app B;
    register app A; both present in result file.
  - `test_unregister_removes_block`: register then unregister; file
    parses to empty `apps` table.
  - `test_unregister_missing_app_is_noop`: no exception when removing an
    unknown `app_id`.
  - `test_write_uses_filelock`: spy `FileLock`, assert acquired during write.
  - `test_concurrent_registers_serialize`: spin two threads each calling
    `register` with distinct app IDs; final file contains both blocks.
    (Threading shape ok; the lock makes this deterministic.)
- [ ] Run — fails.
- [ ] Implement `register(app)` and `unregister(app_id)` using `tomli_w.dumps`
  and the same `FileLock`. On write, also prune-on-disk any stale entries
  encountered during the read step (so the file converges to truth over
  time without a separate sweep).
- [ ] Re-run — 7 passed.

**Acceptance:** Full read/write/concurrent-write coverage; spec §3 TOML
shape is the round-tripped format.

### Task 2.5: `register_self()` auto-detect helper {#register-self-auto-detect-helper}
model: sonnet  effort: S  area: suite
Blocked-by: #localtomlsuiteregistry-register-unregister

**Why:** Cross-cut §3 promises a one-liner for each pd-* app's startup:
`pd_ocr_ops.suite.register_self()`. Decided #179 (2026-05-17). Reads the
calling package's `pd-suite.json` fragment + `pyproject.toml` metadata +
`sys.argv[0]` for binary, builds `InstalledApp`, calls `register(...)`.
Eliminates ~10 lines of duplicated registration boilerplate in every
end-user app.

**Approach:**
Auto-detect caller package via stack frame `__package__`; read fragment
via `importlib.resources.files(caller_pkg) / 'pd-suite.json'`; fill
`binary` from `sys.argv[0]` and `version` from `importlib.metadata.version`.
Kwargs override any auto-detected field for callers (e.g., self-hosted
operator overriding binary path).

**TDD steps:**
- [ ] Write `tests/suite/test_register_self.py`:
  - `test_register_self_reads_fragment_from_caller_package`: build a
    fixture package with `pd-suite.json` and `[project]` metadata; call
    `register_self()` from a function inside that package; assert
    `installed.toml` contains the fragment's fields.
  - `test_register_self_fills_binary_from_argv`: monkeypatch `sys.argv[0]`;
    assert `installed.toml`'s `binary` field matches.
  - `test_register_self_fills_version_from_importlib_metadata`: assert
    `version` is the fixture package's installed version.
  - `test_register_self_kwargs_override_fragment`: call
    `register_self(default_port=9999)`; assert the override wins.
  - `test_register_self_missing_fragment_raises_clear_error`: caller
    package has no `pd-suite.json`; assert `FileNotFoundError` mentioning
    the package name.
- [ ] Run — fails.
- [ ] Implement `pd_ocr_ops.suite.register_self(**overrides)` calling
  through to `LocalTomlSuiteRegistry().register(InstalledApp(...))`.
- [ ] Re-run — 5 passed.

**Acceptance:** End-user apps register with one line:
`from pd_ocr_ops.suite import register_self; register_self()`.

---

## Milestone M3: `LocalFilePrefs` adapter

Implements the `PrefsAdapter` Protocol for local mode. **Two storage
scopes** (per cross-cut §4 + #184 decision, 2026-05-17):

- Shared cross-app prefs (`common.*`) → `~/.local/share/pd-suite/ui-prefs.json`
- Per-app prefs (`apps.<id>`) → `~/.local/share/pd-suite/<app_id>/app_prefs.json`

Per-app isolation by default: simple-gui's `recent_projects` doesn't sit
behind the shared filelock; one app's domain data doesn't pollute another
app's prefs read. One filelock per file.

### Task 3.1: `PrefsAdapter` Protocol shape {#prefsadapter-protocol-shape}

**Why:** Same rationale as M2.2 — hosted-mode adapters (`PerUserDBPrefs`
per spec §8) plug in here.

**What:** In `pd_ocr_ops/suite/prefs.py`:

```python
class PrefsAdapter(Protocol):
    def read(self) -> UIPrefs: ...
    def write_common(self, common: CommonUIPrefs) -> None: ...
    def write_app(self, app_id: str, payload: dict) -> None: ...
```

`write_common` and `write_app` are partial-update calls matching the
route shapes from spec §4 (`PUT /api/suite/prefs/common` and
`PUT /api/suite/prefs/apps/<app>`).

**TDD steps:**
- [ ] Write `tests/suite/test_prefs_protocol.py` mirroring 2.2.
- [ ] Fill `suite/prefs.py` with the Protocol.
- [ ] Pass: 2 tests.

**Acceptance:** Protocol exists, runtime-checkable.

### Task 3.2: `LocalFilePrefs` read {#localfileprefs-read}

**TDD steps:**
- [ ] Write `tests/suite/test_local_file_prefs_read.py`:
  - `test_read_returns_defaults_when_no_files(tmp_path, monkeypatch)`:
    `UIPrefs()` default object returned; no files created (read is
    non-destructive).
  - `test_read_parses_common_section(tmp_path, monkeypatch)`: write
    `ui-prefs.json` with `{"common":{"theme":"dark",...}}`; assert
    `common.theme=="dark"`, `common.density=="compact"`, layer_colors match.
  - `test_read_aggregates_per_app_files(tmp_path, monkeypatch)`: write
    `<root>/pdomain-ocr-labeler-spa/app_prefs.json` and
    `<root>/pdomain-ocr-simple-gui/app_prefs.json`; assert
    `apps["pdomain-ocr-labeler-spa"]["show_match_diff_default"]=="fuzzy-and-mismatch"`
    and `apps["pdomain-ocr-simple-gui"]["default_engine"]=="doctr"`.
  - `test_read_missing_per_app_file_omits_key`: only labeler's per-app file
    exists; `apps` dict does NOT contain other app IDs.
  - `test_read_unknown_keys_in_common_section_ignored_with_warning`:
    extra top-level key in `common` (`{"common": {"theme":"dark","x":1}}`)
    should fall through Pydantic's `extra="ignore"` (set on
    `CommonUIPrefs`'s `model_config`); test asserts a `warnings.warn`
    line was emitted referencing the dropped key.
  - `test_read_uses_filelock_per_file`: spy `FileLock`; assert one lock
    acquired for `ui-prefs.json` + one per per-app file read.
- [ ] Run — fails.
- [ ] Implement `LocalFilePrefs.__init__(self, root: Path | None = None)`
  and `read() -> UIPrefs`. Read scans `<root>/<app_id>/app_prefs.json`
  for every directory entry under `<root>` to assemble the `apps` dict.
- [ ] Re-run — 6 passed.

**Acceptance:** Defaults are non-destructive; common + per-app files
roundtrip; per-app isolation verified.

### Task 3.3: `LocalFilePrefs` `write_common` + `write_app` {#localfileprefs-writecommon-writeapp}

**TDD steps:**
- [ ] Write `tests/suite/test_local_file_prefs_write.py`:
  - `test_write_common_creates_ui_prefs_file`: write to
    `<root>/ui-prefs.json`.
  - `test_write_common_does_not_touch_per_app_files`: pre-existing per-app
    file unchanged after common update.
  - `test_write_app_creates_per_app_file`: `write_app("simple-gui", ...)`
    creates `<root>/pdomain-ocr-simple-gui/app_prefs.json` (and the directory).
  - `test_write_app_replaces_only_target_app_file`: app A's file changes;
    app B's file untouched.
  - `test_write_app_does_not_touch_ui_prefs_file`: per-app write does NOT
    open or modify the shared `ui-prefs.json`.
  - `test_write_uses_per_file_filelock`: spy `FileLock`; assert lock paths
    correspond to each file written (no cross-app contention).
  - `test_concurrent_per_app_writes_do_not_serialize`: two threads doing
    `write_app("labeler", ...)` and `write_app("pgdp", ...)` complete
    without blocking each other (per-file locks are distinct).
- [ ] Run — fails.
- [ ] Implement `write_common` (locks + writes `ui-prefs.json`) and
  `write_app(app_id, payload)` (mkdir `<root>/<app_id>/`, locks + writes
  `app_prefs.json` in that directory). One lock per target file.
- [ ] Re-run — 7 passed.

**Acceptance:** Atomic partial updates; concurrent writers don't lose data.

---

## Milestone M4: `mount_routes(app, adapters)` FastAPI router

Mounts the suite contract under `/api/suite/*`. This is the single
public function pd-* apps call at startup. Per spec §3 / §4 / §8.

### Task 4.1: Router skeleton + `mount_routes` signature {#router-skeleton-mountroutes-signature}

**Why:** The function signature is the integration point every pd-* app
binds against; getting it stable here unblocks all of Phase 2.

**What:** In `pd_ocr_ops/suite/routes.py`:

```python
def mount_routes(app: FastAPI, adapters: SuiteAdapters | None = None) -> None:
    if adapters is None:
        adapters = SuiteAdapters.local()
    router = APIRouter(prefix="/api/suite", tags=["suite"])
    # endpoints registered below
    app.include_router(router)
```

**TDD steps:**
- [ ] Write `tests/suite/test_mount_routes_signature.py`:
  - `test_mount_routes_accepts_fastapi_app`: build a `FastAPI()`,
    call `mount_routes(app, adapters=stub_adapters)`, assert
    `/api/suite/installed` is in `app.routes` after.
  - `test_mount_routes_defaults_to_local_adapters`: call
    `mount_routes(app)` (no adapters) — currently expected to raise
    `NotImplementedError` from `SuiteAdapters.local()` (until M11 lands).
    Test asserts the raise; will be replaced in M11 with a positive
    assertion that defaults work.
- [ ] Stub the function in `routes.py`; pass first test.

**Acceptance:** Function exists with correct signature.

### Task 4.2: `GET /api/suite/installed` {#get-apisuiteinstalled}

**Why:** AppShell's launcher calls this to render sibling tiles (spec §3).

**TDD steps:**
- [ ] Write `tests/suite/test_routes_installed.py`:
  - `test_get_installed_returns_registry_list`: fixture using a
    `FakeRegistry` that returns two `InstalledApp`s; `GET
    /api/suite/installed` returns 200 with a JSON list of two app dicts.
  - `test_get_installed_serializes_full_shape`: assert `app_id`,
    `version`, `binary`, `default_port`, `icon`, `display_name`,
    `enabled`, `registered_at` all present.
  - `test_get_installed_empty`: empty registry -> `[]`.
- [ ] Implement the GET handler delegating to `adapters.registry.list_installed()`.
- [ ] Pass: 3 tests.

**Acceptance:** Endpoint exists; returns the registry list as JSON.

### Task 4.3: `POST /api/suite/launch?app=<id>` {#post-apisuitelaunchappid}

**Why:** Browser-triggered sibling spawn (spec §3 "Spawn on click").

**TDD steps:**
- [ ] Write `tests/suite/test_routes_launch.py`:
  - `test_launch_unknown_app_returns_404`: registry empty; POST returns
    404 with body `{"detail": "unknown app: <id>"}`.
  - `test_launch_disabled_app_returns_409`: registry has the app but
    `enabled=False`; POST returns 409.
  - `test_launch_calls_launcher_with_app`: fixture using a `FakeLauncher`
    that records the `launch(installed_app)` argument; POST returns 200
    with the launcher's `LaunchResult` body.
  - `test_launch_already_running_no_spawn`: launcher returns
    `{"kind":"opened","url":"http://localhost:8001","spawned":false}`;
    response carries `spawned=false`.
- [ ] Implement the POST handler delegating to `adapters.launcher.launch()`.
- [ ] Pass: 4 tests.

**Acceptance:** Endpoint exists; passes unknown/disabled/launch paths
through; launcher is the source of truth for spawn behavior.

### Task 4.4: `GET /api/suite/prefs` + `PUT /api/suite/prefs/common` {#get-apisuiteprefs-put-apisuiteprefscommon}

**Why:** UIPrefs read + common-section write (spec §4).

**TDD steps:**
- [ ] Write `tests/suite/test_routes_prefs_common.py`:
  - `test_get_prefs_returns_full_shape`: fixture `FakePrefs` returning
    a UIPrefs with both `common` and `apps`; GET returns 200 with both
    sections.
  - `test_put_common_invokes_write_common`: PUT body matching
    `CommonUIPrefs` shape; adapter spy records `write_common(...)` call
    with parsed `CommonUIPrefs`; response is 204.
  - `test_put_common_validates_payload`: bad accent hex -> 422.
- [ ] Implement handlers.
- [ ] Pass: 3 tests.

**Acceptance:** GET + PUT against common section; validation surfaces as 422.

### Task 4.5: `PUT /api/suite/prefs/apps/{app_id}` {#put-apisuiteprefsappsappid}

**TDD steps:**
- [ ] Write `tests/suite/test_routes_prefs_app.py`:
  - `test_put_app_invokes_write_app`: PUT
    `/api/suite/prefs/apps/pdomain-ocr-labeler-spa` with arbitrary JSON;
    adapter spy records `write_app("pdomain-ocr-labeler-spa", payload)`;
    204 returned.
  - `test_put_app_unknown_app_id_still_writes`: pdomain-ocr-ops doesn't
    gatekeep app IDs (apps self-register); spy records the write.
- [ ] Implement the handler.
- [ ] Pass: 2 tests.

**Acceptance:** Per-app PUT routes through adapter.

### Task 4.6: `GET /api/icons/{size}` (suite-wide icon serving) {#get-apiiconssize-suite-wide-icon-serving}

**Why:** Per spec §3 "App icons and desktop launchers" — AppShell tiles
fetch icons from `/api/icons/<size>`. The icons themselves live in each
app's `<repo>/icons/` directory (each app supplies them); pdomain-ocr-ops
provides the route helper that resolves the icon for a given app.

**TDD steps:**
- [ ] Write `tests/suite/test_routes_icons.py`:
  - `test_get_icon_returns_png_for_known_app`: fixture with a stub
    `IconResolver` returning bytes for size=128; response is 200 with
    `content-type: image/png`.
  - `test_get_icon_missing_returns_404`.
  - `test_get_icon_unsupported_size_returns_400`: size=999 not in the
    allowed set `{1024,512,256,128,64,32,16}`.
- [ ] Implement the handler. Note: the actual resolver is plug-in
  (`adapters.icons` could be a Phase 4 extension); for Phase 1 the
  registry's `InstalledApp.binary` + a sibling `icons/` directory
  convention is enough. Skip-if-icon-dir-missing returns 404.
- [ ] Pass: 3 tests.

**Acceptance:** Endpoint resolves icons from app install dirs; gracefully
404s when none.

### Task 4.7: `GET /healthz` (centralized health endpoint) {#get-healthz-centralized-health-endpoint}
model: sonnet  effort: S  area: suite
Blocked-by: #router-skeleton-mountroutes-signature

**Why:** `LocalSpawnLauncher` (M5) polls `/healthz` to detect when a
spawned sibling is ready to serve. Decided #183 (2026-05-17) to mount
centrally in `mount_routes()` so every pd-* app gets `/healthz` with a
consistent shape automatically — no per-app boilerplate, no drift risk.

**Response shape:**
```json
{ "status": "ok", "app_id": "pdomain-ocr-simple-gui", "version": "0.1.0", "uptime_s": 42 }
```

`app_id` and `version` come from the registered `InstalledApp` (read from
`installed.toml` at startup, cached in the FastAPI app state by
`mount_routes()`). `uptime_s` is seconds since process start.

**TDD steps:**
- [ ] Write `tests/suite/test_routes_healthz.py`:
  - `test_healthz_returns_ok_with_metadata`: mount routes on a fixture app
    with a stub `InstalledApp(app_id='test-app', version='0.1.0')`; GET
    `/healthz` returns 200 + JSON with the four fields.
  - `test_healthz_uptime_increases`: two sequential GETs; second response
    has higher `uptime_s`.
  - `test_healthz_no_auth_required`: route is publicly callable (launcher
    must reach it without credentials).
- [ ] Run — fails.
- [ ] Implement `GET /healthz` in the suite router; populate `app_id` /
  `version` from `app.state.suite_app` set by `mount_routes()`; track
  process start via `time.monotonic()`.
- [ ] Re-run — 3 passed.

**Acceptance:** Every consumer of `mount_routes(app)` exposes `/healthz`
without writing app-specific code. `LocalSpawnLauncher` (Task 5.x) polls
this endpoint.

---

## Milestone M5: `LocalSpawnLauncher`

Implements `SiblingLaunchAdapter` for local mode. Spawns `<binary>
--port <N>` as a subprocess, polls `/healthz`, returns
`{url, spawned, pid}`. Per spec §3.

### Task 5.1: `SiblingLaunchAdapter` Protocol + `LaunchResult` type {#siblinglaunchadapter-protocol-launchresult-type}

**TDD steps:**
- [ ] Write `tests/suite/test_sibling_launch_protocol.py`:
  - `test_protocol_present`
  - `test_launch_result_discriminated`: matches the spec §8 hosted-mode
    discriminated result.

  Per spec §8 the hosted-mode result variant is `{ kind:
  'requires-host-config', siblingId }`; the local-mode variant is
  `{ kind: 'opened', url, spawned, pid }`. Both share the `kind` tag.

- [ ] Define in `pd_ocr_ops/suite/sibling_spawn.py`:
  ```python
  class LaunchResultOpened(BaseModel):
      kind: Literal["opened"] = "opened"
      url: str
      spawned: bool
      pid: int | None = None

  class LaunchResultRequiresHostConfig(BaseModel):
      kind: Literal["requires-host-config"] = "requires-host-config"
      sibling_id: str

  LaunchResult = Annotated[
      LaunchResultOpened | LaunchResultRequiresHostConfig,
      Field(discriminator="kind"),
  ]

  class SiblingLaunchAdapter(Protocol):
      async def launch(self, app: InstalledApp) -> LaunchResult: ...
  ```
- [ ] Pass: 2 tests.

**Acceptance:** Discriminated `LaunchResult` matches frontend hook
contract (spec §8 `useSuiteSiblings`).

### Task 5.2: `LocalSpawnLauncher` — already-running detection {#localspawnlauncher-already-running-detection}

**Why:** First branch of the spawn logic: if something is already
listening on `default_port`, return without spawning. Avoids accidentally
double-spawning when the user has the sibling app open already.

**TDD steps:**
- [ ] Write `tests/suite/test_local_spawn_launcher_already_running.py`:
  - `test_launch_returns_opened_no_spawn_when_healthz_passes`: monkeypatch
    `httpx.AsyncClient.get` to return `200` for `http://localhost:<port>/healthz`;
    `launch(app)` returns `LaunchResultOpened(url=..., spawned=False, pid=None)`.
  - `test_already_running_does_not_call_subprocess_popen`: spy on
    `subprocess.Popen`; assert not called when healthz returns 200.
- [ ] Implement the healthz-first check. Use `httpx.AsyncClient` with a
  500 ms timeout.
- [ ] Pass: 2 tests.

**Acceptance:** Healthz-200 short-circuit works.

### Task 5.3: `LocalSpawnLauncher` — spawn + poll {#localspawnlauncher-spawn-poll}

**TDD steps:**
- [ ] Write `tests/suite/test_local_spawn_launcher_spawn.py`:
  - `test_launch_spawns_when_healthz_fails`: monkeypatch httpx to raise
    `ConnectError` on first call, then return 200 on retries (use a
    counter or `side_effect` list); spy `subprocess.Popen` records
    `[binary, "--port", str(port)]`. `launch()` returns
    `spawned=True, pid=<recorded pid>`.
  - `test_launch_polls_until_ready`: httpx returns connect-error 3
    times, then 200; the test asserts `httpx.AsyncClient.get` was
    called 4 times.
  - `test_launch_times_out`: httpx always raises; after `timeout_s=2.0`
    (configurable), `launch()` raises `LaunchTimeout`. Subprocess is
    **not** killed (the user may still want to inspect it); test asserts
    `Popen.terminate` was NOT called. Document this design choice in the
    docstring.
  - `test_launch_returns_pid_from_popen`: spy returns a `Popen` mock
    with `pid=12345`; assert `LaunchResult.pid == 12345`.
- [ ] Implement the spawn-and-poll loop with `asyncio.sleep(0.1)`
  between healthz checks.
- [ ] Pass: 4 tests.

**Acceptance:** Spawns, polls, times out cleanly; PID surfaced to caller.

### Task 5.4: `LocalSpawnLauncher` — environment + working directory {#localspawnlauncher-environment-working-directory}

**Why:** The spawned sibling needs the same `PD_SUITE_DATA_DIR` env var as
the parent (so they share the same `installed.toml` / `ui-prefs.json` /
`jobs.db`). Working directory: the user's home (avoids leaking the
parent app's cwd into the sibling).

**TDD steps:**
- [ ] Write `tests/suite/test_local_spawn_launcher_env.py`:
  - `test_spawn_inherits_pd_suite_data_dir`: parent sets
    `PD_SUITE_DATA_DIR=tmp_path`; spy `Popen` records `env=`; assert key
    is forwarded.
  - `test_spawn_does_not_inherit_arbitrary_parent_env`: parent sets
    `SECRET_KEY=hunter2`; spy asserts that key was **not** in the
    forwarded env (allowlist-only forwarding).
  - `test_spawn_cwd_is_home_dir`: spy asserts `cwd=Path.home()`.
- [ ] Refine the spawn call: build a minimal env dict (allowlist:
  `PATH`, `HOME`, `USER`, `PD_SUITE_*`, `PYTHONPATH`).
- [ ] Pass: 3 tests.

**Acceptance:** Env inheritance is allowlist-shaped; cwd is home.

---

## Milestone M6: `desktop.install_shortcut()` stub

Per spec §3 "App icons and desktop launchers" and §9 deferred items —
Phase 1 ships a `NotImplementedError`-raising stub with a clear message
per platform; real `.desktop` / `.app` / `.lnk` writers land in Phase 4.

### Task 6.1: `desktop.install_shortcut` + `desktop.remove_shortcut` {#desktopinstallshortcut-desktopremoveshortcut}

**Why:** Each pd-* SPA wires `--install-desktop-shortcut` and
`--remove-desktop-shortcut` CLI flags now (per spec §3); the surface is
present but the platform code is deferred.

**TDD steps:**
- [ ] Write `tests/suite/test_desktop.py`:
  - `test_install_shortcut_raises_not_implemented_on_linux`: monkeypatch
    `sys.platform="linux"`; call raises `NotImplementedError("Desktop
    shortcut install not yet implemented on linux (deferred to Phase 4
    of the cross-cut design)")`.
  - Same for `darwin` and `win32`.
  - `test_remove_shortcut_raises_not_implemented_on_each_platform`:
    parametrized across all three.
  - `test_install_shortcut_signature_accepts_installed_app`: pass an
    `InstalledApp`; assert the call still raises (signature is the
    spec-locked contract).
  - `test_install_shortcut_unknown_platform_raises_generic`: monkeypatch
    `sys.platform="aix"`; raises with "unsupported platform".
- [ ] Implement `pd_ocr_ops/suite/desktop.py`:

  ```python
  def install_shortcut(app: InstalledApp) -> None:
      """TODO Phase 4: write .desktop (Linux) / .app (macOS) / .lnk (Windows).
      For Phase 1 this is a stub — each pd-* app's CLI flag exists so the
      surface is wired when the platform code lands."""
      plat = sys.platform
      msg_by_plat = {
          "linux":  "Desktop shortcut install not yet implemented on linux (...Phase 4...).",
          "darwin": "Desktop shortcut install not yet implemented on macOS (...).",
          "win32":  "Desktop shortcut install not yet implemented on Windows (...).",
      }
      raise NotImplementedError(msg_by_plat.get(plat, f"unsupported platform: {plat}"))

  def remove_shortcut(app_id: str) -> None: ...  # same shape
  ```
- [ ] Pass: 8 tests (3 install platforms + 3 remove platforms + signature
  + unknown).

**Acceptance:** Stubs raise per-platform; CLI surface in each app can
call them and surface the message to users.

---

## Milestone M7: GPU adapter Protocols + result types

Define the shared seam (`StageDispatcher` for short stage calls,
`LongJobRunner` for long-running jobs) and the data shapes that flow
across them. Per spec §8 "GPU dispatch" — direct snippet matches.

### Task 7.1: `StageResult`, `JobStatus`, `JobEvent`, `JobSpec` types {#stageresult-jobstatus-jobevent-jobspec-types}

**Why:** Strong-typed return values from the GPU adapters. These types
are also emitted as JSON Schema (M10) for pdomain-ui's `useStageCall` and
`useLongJob` hooks.

**TDD steps:**
- [ ] Write `tests/gpu/test_types.py`:
  - `test_stage_result_shape`:
    - `stage_id: str`, `page_id: str`, `device: Literal["local","mps","cpu","modal","shared_container"]`,
      `duration_ms: int`, `output_key: str | None`, `metadata: dict = {}`.
    - Build, roundtrip JSON.
  - `test_job_status_shape`:
    - `job_id: str`, `kind: str`, `state: Literal["queued","running","succeeded","failed","cancelled"]`,
      `progress: float = 0.0` (0..1), `started_at: datetime | None`,
      `finished_at: datetime | None`, `error: str | None = None`.
    - Validators: `0.0 <= progress <= 1.0`; state-transition logic NOT
      enforced at the type level (the runner enforces).
  - `test_job_event_shape`:
    - `job_id: str`, `seq: int`, `at: datetime`, `kind: Literal["progress","log","state","metric"]`,
      `payload: dict`.
  - `test_job_spec_shape`:
    - `kind: str` (e.g. `"training_run"`, `"batch_synth"`),
      `params: dict = {}`,
      `priority: Literal["interactive","batch"] = "batch"`.
- [ ] Create `pd_ocr_ops/gpu/__init__.py`, `pd_ocr_ops/gpu/types.py`.
- [ ] Pass: 4 tests.

**Acceptance:** All four models exist; roundtrip JSON.

### Task 7.2: `StageDispatcher` Protocol {#stagedispatcher-protocol}

**Why:** Per spec §8 snippet. The frontend's `useStageCall` hook handles
the `503 Retry-After` backoff (which is a hosted-mode concern); the
Protocol itself is sync-completion-shaped from the app's perspective.

**TDD steps:**
- [ ] Write `tests/gpu/test_stage_dispatcher_protocol.py`:
  - `test_protocol_methods_present`: `run_stage(stage_id, page_id, **kwargs) -> StageResult`.
  - `test_protocol_is_runtime_checkable`.
- [ ] In `pd_ocr_ops/gpu/protocols.py`:

  ```python
  @runtime_checkable
  class StageDispatcher(Protocol):
      """Short, sync-ish GPU stage calls (OCR, layout, char-bbox).
      Mirrors pgdp-prep's existing STAGE_IMPL registry shape."""
      async def run_stage(self, stage_id: str, page_id: str, **kwargs) -> StageResult: ...
  ```
- [ ] Pass: 2 tests.

**Acceptance:** Protocol present; matches spec §8 verbatim.

### Task 7.3: `LongJobRunner` Protocol {#longjobrunner-protocol}

**TDD steps:**
- [ ] Write `tests/gpu/test_long_job_runner_protocol.py`:
  - Protocol shape per spec §8:
    - `async submit(self, kind: str, spec: dict) -> str  # job_id`
    - `async status(self, job_id: str) -> JobStatus`
    - `async cancel(self, job_id: str) -> None`
    - `async stream_events(self, job_id: str) -> AsyncIterator[JobEvent]`
  - `test_protocol_methods_present`.
  - `test_protocol_is_runtime_checkable`.
- [ ] Append to `protocols.py`.
- [ ] Pass: 2 tests.

**Acceptance:** Protocol present; signatures match spec §8.

---

## Milestone M8: `LocalStageDispatcher` + `pick_device()`

The Phase-1 local-mode implementation. In-process stage registry
(intentionally **empty** in Phase 1 — pgdp-prep's `STAGE_IMPL` migrates
in plan #7), with `pick_device()` returning `local` / `mps` / `cpu` per
spec §8.

### Task 8.1: `pick_device()` helper {#pickdevice-helper}

**Why:** Used by the local adapters and also exposed to apps that want
to know what'll run. Spec §8 GPU dispatch table; for Phase 1 we limit
the Literal to `local|mps|cpu` (Modal/shared_container land in plan #7).

**TDD steps:**
- [ ] Write `tests/gpu/test_pick_device.py`:
  - `test_picks_local_when_pd_gpu_backend_local(monkeypatch)`: env
    `PD_GPU_BACKEND=local`; returns `"local"`.
  - `test_picks_mps_when_env_mps`: `PD_GPU_BACKEND=mps`; returns `"mps"`.
  - `test_picks_cpu_when_env_cpu`.
  - `test_env_unset_falls_back_to_detection`:
    - Patch `_cuda_available()` to True; expect `"local"`.
    - Patch CUDA False + `_mps_available()` True; expect `"mps"`.
    - Both False; expect `"cpu"`.
  - `test_unknown_env_value_raises`: `PD_GPU_BACKEND=jupiter`; raises
    `ValueError` with the offending value in the message.
- [ ] Implement `pd_ocr_ops/gpu/device.py`:

  ```python
  def pick_device() -> Literal["local","mps","cpu"]: ...

  def _cuda_available() -> bool:
      try:
          import cupy
          return cupy.cuda.runtime.getDeviceCount() > 0
      except Exception:
          return False

  def _mps_available() -> bool:
      try:
          import torch
          return torch.backends.mps.is_available()
      except Exception:
          return False
  ```

  `pick_device()` reads `PD_GPU_BACKEND` first, then auto-detects.
  Per spec §9 (env var rename `PGDP_GPU_BACKEND` -> `PD_GPU_BACKEND`),
  also read `PGDP_GPU_BACKEND` as a deprecation alias with a
  `warnings.warn(DeprecationWarning, ...)` if seen.
- [ ] Add `test_pgdp_env_var_alias_warns(monkeypatch, recwarn)` — sets
  `PGDP_GPU_BACKEND=mps`; returns `"mps"` AND issues `DeprecationWarning`
  mentioning the new name.
- [ ] Pass: 7 tests.

**Acceptance:** `pick_device()` respects env, falls back to detection,
warns on the deprecated alias.

### Task 8.2: `LocalStageDispatcher` — empty registry path {#localstagedispatcher-empty-registry-path}

**Why:** The class exists, accepts a registry, but in Phase 1 the
registry is empty (pgdp-prep's `STAGE_IMPL` migrates in plan #7).
Importantly: the **shape** must be right now so plan #7 is mechanical.

**TDD steps:**
- [ ] Write `tests/gpu/test_local_stage_dispatcher.py`:
  - `test_construct_with_empty_registry`: `LocalStageDispatcher(registry={})`.
  - `test_run_stage_unknown_id_raises`: `await dispatcher.run_stage("missing", "page-1")` raises `UnknownStageError` mentioning the stage id.
  - `test_run_stage_dispatches_to_registered_impl`: register a fake
    `async def fake(page_id, device, **kwargs): return {"foo":"bar"}` under
    `("ocr", "cpu")` (the registry keys by `(stage_id, device)`); call
    `run_stage("ocr", "page-1")`; assert `StageResult(stage_id="ocr",
    page_id="page-1", device="cpu", duration_ms>=0, output_key=None,
    metadata={"foo":"bar"})` — duration measured by `time.monotonic_ns()`.
  - `test_run_stage_falls_through_to_cpu_when_local_missing`: registry
    has `("ocr","cpu")` but no `("ocr","local")`; `pick_device()`
    monkeypatched to `"local"`; dispatcher falls through to `"cpu"`.
  - `test_run_stage_propagates_kwargs`: kwargs dict reaches the impl.
- [ ] Implement `pd_ocr_ops/gpu/local_stage.py`:

  ```python
  class UnknownStageError(KeyError): ...

  class LocalStageDispatcher:
      def __init__(self, registry: dict[tuple[str, str], Callable] | None = None):
          self._registry = registry or {}

      async def run_stage(self, stage_id: str, page_id: str, **kwargs) -> StageResult: ...
  ```

  The fallthrough order matches spec §8 for the pgdp-prep registry: try
  `pick_device()` value first; if missing, fall through to `"cpu"`.
- [ ] Pass: 5 tests.

**Acceptance:** Dispatcher works against a synthetic registry; unknown
stage raises; CPU fallthrough is correct.

### Task 8.3: Public registration helper {#public-registration-helper}

**Why:** Apps and (later) plan #7's pgdp-prep migration need a way to
register stages without poking at the dispatcher's internals.

**TDD steps:**
- [ ] Write `tests/gpu/test_local_stage_register.py`:
  - `test_register_stage_adds_entry`: `dispatcher.register_stage("ocr",
    "cpu", impl)`; then `("ocr","cpu") in dispatcher._registry`.
  - `test_register_stage_replaces_existing`: re-registering same key
    replaces (with a `warnings.warn` mentioning the replace).
  - `test_register_stage_rejects_unknown_device`: device `"jupiter"` raises.
- [ ] Add `register_stage(stage_id, device, impl)` and `unregister_stage`.
- [ ] Pass: 3 tests.

**Acceptance:** Registration API exists; replace-with-warning behavior
keeps plan #7's mechanical migration safe.

---

## Milestone M9: SQLite jobs table + `LocalLongJobRunner`

Per spec §8 "Job table — yes, but minimal": Phase 1 ships a tiny SQLite
jobs table at `~/.local/share/pd-suite/jobs.db` (path from `paths.jobs_db_path()`).

### Task 9.1: SQLite schema + migration helper {#sqlite-schema-migration-helper}

**Why:** A single `jobs` table keyed by `job_id`, plus a `job_events`
table for the event stream. Frontend reload of the long-job page
re-reads from this DB.

**TDD steps:**
- [ ] Write `tests/gpu/test_jobs_db_schema.py`:
  - `test_init_db_creates_jobs_table(tmp_path, monkeypatch)`: call
    `init_jobs_db(path)`; sqlite `PRAGMA table_info(jobs)` returns the
    expected column set:
    `(job_id TEXT PK, kind TEXT, spec_json TEXT, state TEXT, progress REAL,
      started_at TEXT, finished_at TEXT, error TEXT, created_at TEXT)`.
  - `test_init_db_creates_job_events_table`: columns
    `(job_id TEXT FK, seq INT, at TEXT, kind TEXT, payload_json TEXT)`,
    PRIMARY KEY `(job_id, seq)`, FK `(job_id) REFERENCES jobs(job_id)`.
  - `test_init_db_idempotent`: calling twice doesn't error.
  - `test_init_db_adds_index_on_state`: `PRAGMA index_list(jobs)` shows
    an index on `state` (used by the "active jobs" query for the future
    `JobsDrawer` in pdomain-ui).
- [ ] Implement `pd_ocr_ops/gpu/local_jobs.py::init_jobs_db(path)`.
- [ ] Pass: 4 tests.

**Acceptance:** Schema matches; idempotent; indexed.

### Task 9.2: `LocalLongJobRunner.submit` {#locallongjobrunnersubmit}

**TDD steps:**
- [ ] Write `tests/gpu/test_local_long_job_runner_submit.py`:
  - `test_submit_returns_job_id`: call `await runner.submit("training_run",
    {"epochs": 100})`; returns a `uuid4`-shaped string.
  - `test_submit_writes_row_to_db`: row exists with `state="queued"`,
    `kind="training_run"`, `spec_json` JSON-encoding the spec.
  - `test_submit_serializes_complex_spec`: nested dict roundtrips through
    `spec_json`.
- [ ] Implement `submit(kind, spec) -> str` writing to the DB with a
  `filelock` wrapping the connection.
- [ ] Pass: 3 tests.

**Acceptance:** Submit persists a queued row.

### Task 9.3: `LocalLongJobRunner.status` + state transitions {#locallongjobrunnerstatus-state-transitions}

**TDD steps:**
- [ ] Write `tests/gpu/test_local_long_job_runner_status.py`:
  - `test_status_returns_queued_after_submit`.
  - `test_status_unknown_job_raises`: `await runner.status("nope")` raises
    `UnknownJobError`.
  - `test_internal_state_transition_writes_progress`: call internal
    helper `_set_state(job_id, "running", progress=0.5)`; subsequent
    `status` returns `state="running"`, `progress=0.5`, `started_at` set.
  - `test_internal_state_transition_to_succeeded_sets_finished_at`.
  - `test_internal_state_transition_to_failed_records_error`: `_set_failed(job_id, "OOM")`;
    `status.error == "OOM"`.
- [ ] Add `_set_state`, `_set_failed` internal helpers; `status` reads
  back from SQLite.
- [ ] Pass: 5 tests.

**Acceptance:** State transitions persist; status reads truthfully.

### Task 9.4: `LocalLongJobRunner.cancel` {#locallongjobrunnercancel}

**TDD steps:**
- [ ] Write `tests/gpu/test_local_long_job_runner_cancel.py`:
  - `test_cancel_queued_job_marks_cancelled`: state changes to `cancelled`,
    `finished_at` set.
  - `test_cancel_running_job_signals_subprocess`: monkeypatch the running
    job's `Popen` mock; assert `terminate()` called; state set to
    `cancelled` only after the subprocess exits (or after a short grace).
  - `test_cancel_succeeded_job_is_noop`: state stays `succeeded`.
  - `test_cancel_unknown_job_raises`.
- [ ] Implement `cancel(job_id)`. For Phase 1 the actual subprocess
  termination uses an in-process registry of `Popen` handles keyed by
  `job_id` (no cross-process cancellation; that's a Phase 4 concern).
- [ ] Pass: 4 tests.

**Acceptance:** Cancel is idempotent on terminal states; signals running
subprocess.

### Task 9.5: `LocalLongJobRunner.stream_events` (polling-backed) {#locallongjobrunnerstreamevents-polling-backed}

**Why:** Per spec §8 "SSE in hosted mode; polling fallback in local
mode". Local mode reads from the `job_events` table.

**TDD steps:**
- [ ] Write `tests/gpu/test_local_long_job_runner_stream.py`:
  - `test_stream_emits_existing_events_then_blocks_until_new`: pre-seed
    two events; `async for ev in runner.stream_events(job_id):` yields
    both; an internal `_append_event(job_id, "progress", {...})` causes
    a third yield; close after `state="succeeded"` event.
  - `test_stream_terminates_on_terminal_state`: stream auto-completes
    once the job's `state` transitions to `succeeded`/`failed`/`cancelled`.
  - `test_stream_unknown_job_raises_before_yielding`.
- [ ] Implement `stream_events` as an `async generator` that polls every
  500 ms (configurable via `LocalLongJobRunner(poll_interval_s=0.5)`),
  reads new rows beyond the last seen `seq`, and exits on terminal state.
- [ ] Pass: 3 tests.

**Acceptance:** Polling generator yields events monotonically; terminates cleanly.

### Task 9.6: Wire the runner into a smoke-test long job {#wire-the-runner-into-a-smoke-test-long-job}

**Why:** Prove the runner can actually run a child process and have the
runner observe state transitions externally. Smoke test scope only — a
real "training run" launcher is per-app code.

**TDD steps:**
- [ ] Write `tests/gpu/test_local_long_job_runner_smoke.py`:
  - `test_run_sleep_job_succeeds`: helper that submits a job whose
    subprocess is `python -c "import time; time.sleep(0.5)"`. Runner
    observes process exit via a small "supervise" coroutine kicked off
    by `submit`. After the supervise loop sees the process exit code 0,
    state transitions to `succeeded`.
  - `test_run_failing_subprocess_marks_failed`: subprocess exits 1;
    state -> `failed`, `error` field captures stderr's last line (or
    `"exit code 1"` if stderr empty).
- [ ] Add the supervise coroutine to `LocalLongJobRunner`; kick it off
  inside `submit` via `asyncio.create_task` (single-process, single-event-loop
  in Phase 1; cross-process supervision is a Phase 4 problem).
- [ ] Pass: 2 tests.

**Acceptance:** Submit -> subprocess -> state transitions -> events. Foundation
for plan #7's Modal/shared-container variants.

---

## Milestone M10: `schemas.emit` CLI

Mirror of plan #1's `python -m pd_book_tools.schemas.emit` CLI. Emits
JSON Schema for every public Pydantic model in `pd_ocr_ops`. Output
feeds pdomain-ui's codegen.

### Task 10.1: CLI entry point + tests {#cli-entry-point-tests}

**TDD steps:**
- [ ] Write `tests/test_schemas_emit.py` mirroring plan #1's
  `tests/test_schemas_emit.py` shape (subprocess + JSON parse):
  - `test_emit_returns_top_level_dict`.
  - `test_emit_includes_suite_app`: schema for `SuiteApp` present,
    properties match the M1.1 spec.
  - `test_emit_includes_installed_app`.
  - `test_emit_includes_ui_prefs_and_common_ui_prefs`.
  - `test_emit_includes_layer_colors`.
  - `test_emit_includes_stage_result`.
  - `test_emit_includes_job_status_job_event_job_spec`.
  - `test_emit_includes_launch_result_discriminated_union`: validates
    that `LaunchResult` emits as `oneOf` with two members tagged on
    `kind` (so pdomain-ui's TS generator can produce a discriminated union).
  - `test_emit_stage_result_device_enum_values`: enum members exactly
    `["local","mps","cpu","modal","shared_container"]`.
- [ ] Create `pd_ocr_ops/schemas/__init__.py`, `__main__.py`, `emit.py`
  following the pdomain-book-tools shape from plan #1 task 6. `PUBLIC_MODELS`
  tuple contains: `SuiteApp`, `InstalledApp`, `UIPrefs`, `CommonUIPrefs`,
  `LayerColors`, `LaunchResultOpened`, `LaunchResultRequiresHostConfig`,
  `StageResult`, `JobStatus`, `JobEvent`, `JobSpec`. (`SuiteAdapters` is
  NOT emitted — its fields are Protocol classes which Pydantic can't
  JSON-schema cleanly; that's an internal type.)
- [ ] Add a `LaunchResult` union schema separately by using
  `TypeAdapter(LaunchResult).json_schema()` and keying it as
  `"LaunchResult"` so the discriminator survives.
- [ ] Pass: 9 tests.

**Acceptance:** CLI emits a single JSON document; all expected models
present; discriminator preserved; pdomain-ui can re-run this against the
pinned wheel.

### Task 10.2: README section + smoke test {#readme-section-smoke-test}

**TDD steps:**
- [ ] In `README.md` add a "JSON Schema for downstream codegen" section
  mirroring plan #1's task 7:
  - `uv run python -m pd_ocr_ops.schemas > schemas.json`
  - Pointer to `pd_ocr_ops/schemas/emit.py::PUBLIC_MODELS` as the
    registration surface.
- [ ] Manual smoke: `uv run python -m pd_ocr_ops.schemas | python -m json.tool | head -40`.

**Acceptance:** README documents the contract; smoke test produces clean JSON.

---

## Milestone M11: Auth + Storage Protocols + local-mode implementations + `SuiteAdapters.local()`

Closes the §8 adapter-seams table by adding the last two Protocol
shapes, their Phase-1 default implementations, and wiring everything
together via `SuiteAdapters.local()`.

### Task 11.1: `AuthAdapter` Protocol + `NoAuthAdapter` {#authadapter-protocol-noauthadapter}

**Why:** Per spec §8 "Auth" row — hosted-mode adapters (ApiKeyAuth, JWTAuth,
OIDCAuth) plug in later. Phase 1 default is `NoAuthAdapter` (single-user
local). Identity is a constant `SingleUser` per the table's "User
identity" row.

**TDD steps:**
- [ ] Write `tests/suite/test_auth.py`:
  - `test_no_auth_adapter_returns_single_user`: `await adapter.authenticate(request)`
    returns `Identity(user_id="local", display_name="Local User")` regardless
    of input.
  - `test_protocol_runtime_checkable`.
  - `test_protocol_methods_present`: `authenticate(request) -> Identity`,
    `is_authenticated(request) -> bool`.
- [ ] Create `pd_ocr_ops/suite/auth.py`:
  ```python
  class Identity(BaseModel):
      user_id: str
      display_name: str

  @runtime_checkable
  class AuthAdapter(Protocol):
      async def authenticate(self, request) -> Identity: ...
      async def is_authenticated(self, request) -> bool: ...

  class NoAuthAdapter:
      async def authenticate(self, request) -> Identity:
          return Identity(user_id="local", display_name="Local User")
      async def is_authenticated(self, request) -> bool:
          return True
  ```
- [ ] Pass: 3 tests.

**Acceptance:** Protocol + concrete local adapter exist.

### Task 11.2: `StorageAdapter` Protocol + `LocalFsStorage` {#storageadapter-protocol-localfsstorage}

**Why:** Per spec §8 "Storage (sidecar JSON IO + project artifacts)"
row — hosted-mode adapters (`S3Storage`, `GCSStorage`) plug in later.
Phase 1 default is local-filesystem.

**TDD steps:**
- [ ] Write `tests/suite/test_storage.py`:
  - `test_protocol_methods_present`: `read(key) -> bytes`, `write(key, data: bytes) -> None`,
    `exists(key) -> bool`, `delete(key) -> None`, `list_prefix(prefix) -> list[str]`.
  - `test_protocol_runtime_checkable`.
  - `test_local_fs_storage_round_trip(tmp_path)`: write + read + exists + delete + list_prefix.
  - `test_local_fs_storage_rejects_absolute_paths(tmp_path)`: keys must
    be relative; `write("/etc/passwd", b"x")` raises `ValueError`.
  - `test_local_fs_storage_rejects_traversal(tmp_path)`: keys must not
    contain `..`; raises.
  - `test_local_fs_storage_creates_intermediate_dirs(tmp_path)`: write
    to `"a/b/c.json"`; intermediate dirs created.
- [ ] Create `pd_ocr_ops/suite/storage.py` with the Protocol and `LocalFsStorage(root)`.
- [ ] Pass: 6 tests.

**Acceptance:** Protocol + concrete adapter exist; security
guardrails (no absolute, no traversal) tested.

### Task 11.3: `SuiteAdapters.local()` returns the bundle {#suiteadapterslocal-returns-the-bundle}

**Why:** Now that all five adapters exist (`registry`, `prefs`,
`launcher`, `auth`, `storage`), wire the convenience constructor and
un-skip the M1.4 test.

**TDD steps:**
- [ ] Update `tests/suite/test_types_suite_adapters.py`:
  - Un-skip `test_suite_adapters_local_returns_bundle`. Add assertions:
    - `isinstance(bundle.registry, SuiteRegistryAdapter)`
    - `isinstance(bundle.prefs, PrefsAdapter)`
    - `isinstance(bundle.launcher, SiblingLaunchAdapter)`
    - `isinstance(bundle.auth, AuthAdapter)`
    - `isinstance(bundle.storage, StorageAdapter)`
    - Specifically: `bundle.registry.__class__.__name__ == "LocalTomlSuiteRegistry"`.
  - Add `test_local_bundle_uses_xdg_paths(tmp_path, monkeypatch)`: set
    `PD_SUITE_DATA_DIR=tmp_path`; bundle's registry reads from
    `tmp_path/installed.toml`.
- [ ] Implement `SuiteAdapters.local()`:
  ```python
  @classmethod
  def local(cls) -> "SuiteAdapters":
      return cls(
          registry=LocalTomlSuiteRegistry(),
          prefs=LocalFilePrefs(),
          launcher=LocalSpawnLauncher(),
          auth=NoAuthAdapter(),
          storage=LocalFsStorage(root=paths.suite_data_dir() / "storage"),
      )
  ```
- [ ] Re-run M1.4 tests — both pass.
- [ ] Also update `test_mount_routes_defaults_to_local_adapters` in
  `tests/suite/test_mount_routes_signature.py` to assert positive
  behavior (no NotImplementedError) now that `local()` works.
- [ ] Pass: 2 unskipped tests + 1 updated test.

**Acceptance:** `mount_routes(app)` (no adapters) defaults to fully-wired
local adapters with XDG paths.

### Task 11.4: Public API surface in `pd_ocr_ops/__init__.py` {#public-api-surface-in-pdocropsinitpy}

**Why:** Apps shouldn't dig through submodules. Re-export the canonical
public surface.

**TDD steps:**
- [ ] Write `tests/test_public_surface.py`:
  - `test_top_level_exports_present`:
    - `from pd_ocr_ops import mount_routes, SuiteAdapters`
    - `from pd_ocr_ops.suite import SuiteApp, InstalledApp, UIPrefs`
    - `from pd_ocr_ops.gpu import StageDispatcher, LongJobRunner, pick_device`
- [ ] Update `pd_ocr_ops/__init__.py`, `pd_ocr_ops/suite/__init__.py`,
  `pd_ocr_ops/gpu/__init__.py` with the re-exports.
- [ ] Pass: 1 test (multi-assertion).

**Acceptance:** Public API is one import away.

---

## Milestone M12: Final `make ci AI=1` green + 0.1.0 release

### Task 12.1: Full CI green + manual smoke test {#full-ci-green-manual-smoke-test}

**Why:** Verify all 65+ tests added across M0–M11 pass under
`make ci AI=1`, and that the schema emitter, `LocalTomlSuiteRegistry`,
and `mount_routes` all work end-to-end against a real FastAPI app.

**TDD steps:**
- [ ] Run `make ci AI=1`. Expected: green; `.ci-ai.log` shows all tests.
- [ ] Write `tests/test_e2e_smoke.py`:
  - `test_e2e_mount_routes_real_fastapi_app(tmp_path, monkeypatch)`:
    - Set `PD_SUITE_DATA_DIR=tmp_path`.
    - `app = FastAPI(); mount_routes(app)`.
    - Use `httpx.AsyncClient(app=app, base_url="http://test")`.
    - Register an `InstalledApp` via `LocalTomlSuiteRegistry().register(...)`.
    - `GET /api/suite/installed` -> 200 with the registered app.
    - `PUT /api/suite/prefs/common` with a valid common prefs blob -> 204.
    - `GET /api/suite/prefs` -> 200 with the new common values.
  - `test_e2e_schemas_emit_dump_full(tmp_path)`: invoke
    `python -m pd_ocr_ops.schemas`, parse stdout, sanity-check 11+
    schemas present, all valid JSON-Schema-shaped dicts.
- [ ] Run `make ci AI=1` again.

**Acceptance:** End-to-end smoke proves the contract works for an app
that mounts pdomain-ocr-ops.

### Task 12.2: README polish + version tagging dry-run {#readme-polish-version-tagging-dry-run}

**Why:** Publishing to `pdomain-index-pip` is a workspace-release task (uses
the same release helper pdomain-book-tools uses). The repo just needs the
0.1.0 tag and a clean README.

**TDD steps:**
- [ ] Expand `README.md` to:
  - One-paragraph what-and-why.
  - "Quick start" with the smallest snippet:
    ```python
    from fastapi import FastAPI
    from pd_ocr_ops import mount_routes

    app = FastAPI()
    mount_routes(app)  # adds /api/suite/*
    ```
  - Pointer to `docs/superpowers/specs/2026-05-16-cross-cut-design.md`
    in the workspace.
  - Pointer to `python -m pd_ocr_ops.schemas`.
  - Pointer to plan #7 for the upcoming `STAGE_IMPL` migration from
    pgdp-prep.
- [ ] Confirm `pyproject.toml` `version = "0.1.0"`.
- [ ] DO NOT publish in this plan. That happens via the workspace's
  release helper after the repo is pushed to the
  `ConcaveTrillion/pdomain-ocr-ops` remote (out of scope here).

**Acceptance:** README ships the quick-start snippet; version locked at 0.1.0.

### Task 12.3: Final lint + format + commit hygiene {#final-lint-format-commit-hygiene}

**TDD steps:**
- [ ] `make format` — ruff format pass.
- [ ] `make lint` — ruff check green.
- [ ] `make ci AI=1` — final green run.
- [ ] `git status` — only the expected file set; no untracked debris.

**Acceptance:** Clean repo, green CI, ready for tag + push.

---

## Self-review checklist (for the agent; do this before the final commit)

- [ ] Every adapter has a Protocol class AND a Phase-1 local implementation.
- [ ] No hosted-mode adapter classes (ModalStageDispatcher,
  SharedContainerStageDispatcher, K8sScaleLauncher, S3Storage, etc.) are
  implemented — only their Protocol seams.
- [ ] `desktop.install_shortcut()` raises `NotImplementedError` per
  platform with a clear message.
- [ ] `SuiteAdapters.local()` returns a fully-wired bundle.
- [ ] `mount_routes(app)` (no adapters) defaults to `SuiteAdapters.local()`.
- [ ] `python -m pd_ocr_ops.schemas` produces JSON with the discriminator
  preserved for `LaunchResult`.
- [ ] `pick_device()` honors `PD_GPU_BACKEND`, warns on the
  `PGDP_GPU_BACKEND` alias, falls back to auto-detection.
- [ ] `LocalStageDispatcher`'s registry is empty — pgdp-prep's
  `STAGE_IMPL` lives in plan #7, not here.
- [ ] SQLite jobs DB has `state` index for the future `JobsDrawer` query.
- [ ] All file IO that touches `~/.local/share/pd-suite/` is wrapped in
  `filelock` advisory locks.
- [ ] `make ci AI=1` exit code 0.

---

## Follow-up plans (not in scope here)

1. **Plan #7 — Phase 1.7: migrate pgdp-prep's `STAGE_IMPL` registry + Modal
   adapters into pdomain-ocr-ops.** Adds `ModalStageDispatcher`,
   `SharedContainerStageDispatcher`, `ModalLongJobRunner`, and registers
   pgdp-prep's per-page stages into the `LocalStageDispatcher` registry.
   Renames `PGDP_GPU_BACKEND` -> `PD_GPU_BACKEND` everywhere in
   pgdp-prep (deprecation alias preserved). Cross-cut spec §7 row 1.7.

2. **Hosted-mode adapters** (Phase 4 in the cross-cut spec):
   - `EnvSuiteRegistry` (reads sibling URLs from env)
   - `DBSuiteRegistry` (per-tenant SaaS)
   - `PerUserDBPrefs` (per-authenticated-user)
   - `StaticURLLauncher` + `K8sScaleLauncher`
   - `ApiKeyAuth` / `JWTAuth` / `OIDCAuth` (designs already exist in pgdp-prep)
   - `S3Storage` / `GCSStorage`

3. **Real desktop launcher platforms** (Phase 4): Linux `.desktop`,
   macOS `.app`, Windows `.lnk` writers replacing the M6 stubs.

4. **SSE cross-tab UI prefs sync** (Phase 4 — spec §4 + §7 row 4.1):
   `GET /api/suite/prefs/events` server-sent-events channel that
   notifies sibling tabs of prefs changes. Phase 1 ships reload-to-pick-up.

5. **Embedded shell mode** (Phase 4 row 4.3): one app iframes/route-mounts
   others into a single window. New `pd-shell` repo or pdomain-ui module.

6. **Backend OCR mutation primitive extraction**: labeler-spa's edit
   operations (rebox/charfixer/erase) migrate to `pd_ocr_ops.ops`.
   Deferred per cross-cut spec §9 "deferred design items"; lands in
   pdomain-ocr-ops 0.2.x.

7. **Persistent cross-machine job queue** (Redis/Celery): the
   `LocalLongJobRunner` is single-machine by design; multi-machine queue
   becomes a separate adapter if hosted-mode load justifies it.

8. **Multi-pass review model**: per cross-cut spec §9, `ReviewMetadata`
   evolves to `list[ReviewPass]` for DP-style P1/P2/P3/F1/F2 — but that
   lives in pdomain-book-tools (plan #1's follow-up), not here.
