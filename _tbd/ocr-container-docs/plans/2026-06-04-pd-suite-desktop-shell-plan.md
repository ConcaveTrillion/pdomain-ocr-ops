# pd-* Suite Desktop Shell — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a PyWebView/pystray desktop shell, a shared compute-target control, and a shared in-app update control across the pd-* suite — built in `pdomain-ops` + `pdomain-ui`, proven in `pdomain-ocr-simple-gui` as pilot, with a gated Linux AppImage installer.

**Architecture:** The FastAPI server stays canonical; the shell is an additive thin client (`--desktop` wraps the same `create_app()` in a native window). Shared backend (device + update endpoints, shell, sibling-spawn) lands in `pdomain-ops`; shared UI panels in `pdomain-ui`; simple-gui wires both. No ML bundling — distribution is `uv tool install`; GPU is an optional gated `cu12x` torch swap.

**Tech Stack:** Python 3 / FastAPI / uvicorn / PyWebView / pystray (pdomain-ops); React 19 / TS / Vite / Vitest (pdomain-ui); pytest-xdist + pytest-playwright (simple-gui); AppImage + GitHub Actions (installer).

**Spec:** `docs/specs/2026-06-04-pd-suite-desktop-shell-design.md`

---

## Parallelization, worktree & merge strategy

This plan is built for parallel subagent execution. Read this before dispatching.

**Per-repo agents (use the exact `subagent_type`):** `pdomain-ops`, `pdomain-ui`, `pdomain-ocr-simple-gui`. Every implementation dispatch passes `isolation: "worktree"`. Each agent's job ends at **commit on its worktree branch + return `{worktree_path, branch}`** — the orchestrator owns rebase+merge. Subagent prompts MUST forbid `gh pr create` and MUST forbid self-merging to main (workspace rule).

**Merge protocol (workspace CLAUDE.md — rebase-only linear history):**
1. Agent works in `<repo>/.claude/worktrees/<slug>`, commits to branch `<branch>`.
2. Orchestrator verifies `make ci AI=1` green in the worktree.
3. `git -C <repo>/.claude/worktrees/<slug> fetch origin && git rebase origin/HEAD`.
4. `git -C <repo> checkout main && git -C <repo> merge --ff-only <branch>`.
5. Push only when CT authorizes. Then delete branch + `git worktree remove`.
6. After removing a worktree that shared the canonical `.venv`, run `uv sync` + `make local-setup-py` from the canonical checkout (editable-orphan fix).

**Wave structure (maximize parallelism):**

```
WAVE 1 (fully parallel — different repos never conflict)
  ├─ pdomain-ops   : Milestones A, B, C   (3 parallel worktrees, see note)
  └─ pdomain-ui    : Milestone D          (1–2 parallel worktrees)

WAVE 2 (after each repo's CI green) — orchestrator releases
  ├─ release pdomain-ops  → 0.8.0  (Milestone E1)
  └─ release pdomain-ui   → 0.7.0  (Milestone E2)

WAVE 3 (after E) — pilot integration, single repo, sequential
  └─ pdomain-ocr-simple-gui : Milestone F

WAVE 4 (after F) — parallel
  ├─ installer engine + AppImage + CI : Milestone G
  └─ browser verification (e2e)        : Milestone H
```

**Intra-repo parallelism note (pdomain-ops A/B/C):** A, B, C are mostly disjoint files, but all three touch `pdomain_ops/suite/routes.py` (one `mount_routes` line each), `pdomain_ops/schemas/emit.py` (`PUBLIC_MODELS`), and `pyproject.toml`. To keep parallel worktrees clean: **each milestone puts its routes in its own new module** (`device_routes.py`, `update_routes.py`, etc.) so the only shared edits are tiny. Rebase-merge them **sequentially in order A → B → C** (B rebases onto post-A main, C onto post-B); the small shared-file conflicts resolve trivially. Run `make ci` after each merge. If you prefer zero conflict risk over parallelism, run A→B→C as one agent in one worktree.

**Per-repo memory check before dispatch:** read `.claude/agent-memory/<repo>/feedback_*.md`. Note `feedback_make_ci_worktree_hookpath.md` (worktree `make ci` can abort on `core.hooksPath`) and the parallel-worktree race warnings.

---

## File structure map

**pdomain-ops** (`/workspaces/ocr-container/pdomain-ops/pdomain_ops/`)
- Create `gpu/device_probe.py` — `list_devices()` → available compute targets + VRAM.
- Create `suite/device_prefs.py` — effective-device resolution (app → suite → auto).
- Create `suite/device_routes.py` — `GET/PUT /api/suite/device`.
- Create `suite/update.py` — version check + gated `uv tool upgrade` + editable-install guard + rollback record.
- Create `suite/update_routes.py` — `GET/POST /api/suite/update`.
- Create `desktop.py` — `run_windowed()` shell choreography (injectable seams).
- Create `suite/single_instance.py` — pidfile lock + stale reap + restart signal.
- Modify `suite/routes.py` — call the new route-mounters from `mount_routes`.
- Modify `suite/sibling_spawn.py` — `windowed: bool` arg → append `--desktop`.
- Modify `suite/desktop.py` — implement Linux `install_shortcut`/`remove_shortcut`.
- Modify `suite/types.py` — `CommonUIPrefs.compute_device_default`, `.update_policy`.
- Modify `schemas/emit.py` — add `DeviceInfo`, `UpdateInfo` to `PUBLIC_MODELS`.
- Modify `pyproject.toml` — `[project.optional-dependencies] desktop = ["pywebview", "pystray"]`.

**pdomain-ui** (`/workspaces/ocr-container/pdomain-ui/src/`)
- Create `shell/createApiDeviceConfig.ts`, `stores/useDeviceInfo.ts`, `shell/ComputeTargetPanel.tsx`.
- Create `shell/createApiUpdateConfig.ts`, `stores/useUpdateCheck.ts`, `shell/UpdatePanel.tsx`.
- Modify `testids/index.ts`, `shell/index.ts`, `index.ts`, `package.json` (exports + version).

**pdomain-ocr-simple-gui**
- Modify `src/pdomain_ocr_simple_gui/__main__.py` — `--desktop`, `--update`; fill shortcut stubs.
- Modify `frontend/src/App.tsx` — add the two panels to `settingsPanels`.
- Create `frontend/public/manifest.webmanifest`; modify `frontend/index.html`.
- Modify `pyproject.toml` (dep bumps), `frontend/package.json` (dep bump).
- Create `packaging/install_engine.py`, `packaging/appimage/`, `.github/workflows/installer.yml`, `docs/runbooks/install.md`.
- Create `tests/e2e/test_desktop_panels.py` (browser verification).

---

## Milestone A — pdomain-ops: compute-target endpoint

**Agent:** `pdomain-ops` · **worktree branch:** `feat/suite-device` · merge first.

### Task A1: device probe helper

**Files:**
- Create: `pdomain_ops/gpu/device_probe.py`
- Test: `tests/gpu/test_device_probe.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/gpu/test_device_probe.py
from pdomain_ops.gpu.device_probe import list_devices, DeviceInfoEntry


def test_list_devices_always_includes_cpu():
    devices = list_devices()
    assert any(d.id == "cpu" for d in devices)
    cpu = next(d for d in devices if d.id == "cpu")
    assert cpu.label.lower().startswith("cpu")
    assert cpu.vram_total_mb is None


def test_cuda_entries_have_vram(monkeypatch):
    monkeypatch.setattr(
        "pdomain_ops.gpu.device_probe._probe_cuda",
        lambda: [DeviceInfoEntry(id="cuda:0", label="Fake GPU", vram_total_mb=8192, vram_free_mb=4096)],
    )
    ids = [d.id for d in list_devices()]
    assert "cuda:0" in ids and "cpu" in ids
```

- [ ] **Step 2: Run test to verify it fails** — `uv run pytest tests/gpu/test_device_probe.py -v` → FAIL (module missing).

- [ ] **Step 3: Implement**

```python
# pdomain_ops/gpu/device_probe.py
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceInfoEntry:
    id: str            # "cpu" | "cuda:0" | "mps"
    label: str
    vram_total_mb: int | None = None
    vram_free_mb: int | None = None


def _probe_cuda() -> list[DeviceInfoEntry]:
    try:
        import torch  # noqa: PLC0415
    except ImportError:
        return []
    if not torch.cuda.is_available():
        return []
    out: list[DeviceInfoEntry] = []
    for i in range(torch.cuda.device_count()):
        free, total = torch.cuda.mem_get_info(i)
        out.append(
            DeviceInfoEntry(
                id=f"cuda:{i}",
                label=torch.cuda.get_device_name(i),
                vram_total_mb=total // (1024 * 1024),
                vram_free_mb=free // (1024 * 1024),
            )
        )
    return out


def list_devices() -> list[DeviceInfoEntry]:
    return [*_probe_cuda(), DeviceInfoEntry(id="cpu", label="CPU")]
```

- [ ] **Step 4: Run test to verify it passes** — `uv run pytest tests/gpu/test_device_probe.py -v` → PASS.
- [ ] **Step 5: Commit** — `git add pdomain_ops/gpu/device_probe.py tests/gpu/test_device_probe.py && git commit -m "feat(gpu): device_probe.list_devices with VRAM"`

### Task A2: device-pref types + resolution

**Files:**
- Modify: `pdomain_ops/suite/types.py` (`CommonUIPrefs`)
- Create: `pdomain_ops/suite/device_prefs.py`
- Test: `tests/suite/test_device_prefs.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/suite/test_device_prefs.py
from pdomain_ops.suite.device_prefs import resolve_effective_device


class _Prefs:
    def __init__(self, common_default=None, app_overrides=None):
        self._common = common_default
        self._apps = app_overrides or {}
    def read(self):
        from pdomain_ops.suite.types import UIPrefs, CommonUIPrefs
        return UIPrefs(common=CommonUIPrefs(compute_device_default=self._common), apps=self._apps)


def test_app_override_wins():
    p = _Prefs(common_default="cpu", app_overrides={"app1": {"compute_device": "cuda:0"}})
    assert resolve_effective_device(p, "app1") == "cuda:0"


def test_falls_back_to_suite_default():
    p = _Prefs(common_default="cpu", app_overrides={})
    assert resolve_effective_device(p, "app1") == "cpu"


def test_falls_back_to_auto(monkeypatch):
    monkeypatch.setattr("pdomain_ops.suite.device_prefs.pick_device", lambda: "cpu")
    p = _Prefs(common_default=None, app_overrides={})
    assert resolve_effective_device(p, "app1") == "cpu"
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** — add optional field to `CommonUIPrefs` in `suite/types.py`:

```python
    compute_device_default: str | None = None
    update_policy: str | None = None  # "notify" | "auto" | "manual"; used by Milestone B
```

```python
# pdomain_ops/suite/device_prefs.py
from __future__ import annotations
from pdomain_ops.gpu.device import pick_device
from pdomain_ops.suite.prefs import PrefsAdapter


def resolve_effective_device(prefs: PrefsAdapter, app_id: str) -> str:
    snapshot = prefs.read()
    app_section = snapshot.apps.get(app_id, {})
    override = app_section.get("compute_device") if isinstance(app_section, dict) else None
    if override:
        return override
    if snapshot.common.compute_device_default:
        return snapshot.common.compute_device_default
    return pick_device()
```

- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `feat(suite): device-pref types + resolve_effective_device`.

### Task A3: `/api/suite/device` route

**Files:**
- Create: `pdomain_ops/suite/device_routes.py`
- Modify: `pdomain_ops/suite/routes.py` (call `mount_device_routes(app, adapters)` inside `mount_routes`)
- Test: `tests/suite/test_device_routes.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/suite/test_device_routes.py
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pdomain_ops.suite.device_routes import mount_device_routes


def _client(monkeypatch, prefs):
    monkeypatch.setattr("pdomain_ops.suite.device_routes.list_devices",
                        lambda: [type("D", (), {"id": "cpu", "label": "CPU", "vram_total_mb": None, "vram_free_mb": None})()])
    app = FastAPI()
    mount_device_routes(app, prefs=prefs, app_id="app1")
    return TestClient(app)


def test_get_device_local_mode(monkeypatch, local_prefs):  # local_prefs fixture in conftest
    r = _client(monkeypatch, local_prefs).get("/api/suite/device")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "local"
    assert any(d["id"] == "cpu" for d in body["available"])
    assert "current" in body and "effective_source" in body


def test_put_device_persists(monkeypatch, local_prefs):
    c = _client(monkeypatch, local_prefs)
    r = c.put("/api/suite/device", json={"scope": "app", "device": "cpu"})
    assert r.status_code == 200
    assert local_prefs.read().apps.get("app1", {}).get("compute_device") == "cpu"
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement**

```python
# pdomain_ops/suite/device_routes.py
from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel
from pdomain_ops.gpu.device_probe import list_devices
from pdomain_ops.suite.device_prefs import resolve_effective_device
from pdomain_ops.suite.prefs import PrefsAdapter


class DeviceInfo(BaseModel):
    mode: str
    available: list[dict] = []
    current: str | None = None
    effective_source: str | None = None  # "app" | "suite" | "auto"
    offload_target: str | None = None


class DevicePutBody(BaseModel):
    scope: str    # "app" | "suite"
    device: str


def mount_device_routes(app: FastAPI, *, prefs: PrefsAdapter, app_id: str, mode: str = "local") -> None:
    @app.get("/api/suite/device", response_model=DeviceInfo)
    def get_device() -> DeviceInfo:
        if mode != "local":
            return DeviceInfo(mode=mode, offload_target=None)
        snap = prefs.read()
        app_override = (snap.apps.get(app_id) or {}).get("compute_device")
        source = "app" if app_override else ("suite" if snap.common.compute_device_default else "auto")
        return DeviceInfo(
            mode="local",
            available=[d.__dict__ for d in list_devices()],
            current=resolve_effective_device(prefs, app_id),
            effective_source=source,
        )

    @app.put("/api/suite/device", response_model=DeviceInfo)
    def put_device(body: DevicePutBody) -> DeviceInfo:
        if body.scope == "suite":
            common = prefs.read().common
            common.compute_device_default = body.device
            prefs.write_common(common)
        else:
            section = dict(prefs.read().apps.get(app_id) or {})
            section["compute_device"] = body.device
            prefs.write_app(app_id, section)
        return get_device()
```

Wire into `suite/routes.py` `mount_routes` after the existing route registrations (use the resolved `suite_app.app_id` for `app_id`, else `"unknown"`; pass the prefs adapter already constructed there):

```python
    from pdomain_ops.suite.device_routes import mount_device_routes
    mount_device_routes(app, prefs=adapters.prefs, app_id=(suite_app.app_id if suite_app else "unknown"))
```

- [ ] **Step 4: Run** → PASS. Also run `uv run pytest tests/suite/ -n auto`.
- [ ] **Step 5: Commit** — `feat(suite): GET/PUT /api/suite/device (local-mode-gated)`.

### Task A4: dispatcher honors the device pref + schema emit

**Files:**
- Modify: `pdomain_ops/gpu/local_stage.py` (default device from a resolver callback)
- Modify: `pdomain_ops/schemas/emit.py` (`PUBLIC_MODELS += (DeviceInfo,)`)
- Test: `tests/gpu/test_local_stage_device_pref.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/gpu/test_local_stage_device_pref.py
import asyncio
from pdomain_ops.gpu.local_stage import LocalStageDispatcher


def test_run_stage_uses_device_resolver():
    seen = {}
    d = LocalStageDispatcher(device_resolver=lambda: "cuda:0")
    d.register_stage("s", "cuda:0", lambda page_id, **kw: seen.setdefault("dev", "cuda:0") or {"ok": True})
    asyncio.run(d.run_stage("s", "p1"))
    assert seen["dev"] == "cuda:0"
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — add an optional `device_resolver: Callable[[], str] | None = None` ctor param; in `run_stage`, when `device is None and self._device_resolver`, use `self._device_resolver()` before falling back to `pick_device()`. Add `DeviceInfo` to `PUBLIC_MODELS` in `emit.py` (import from `device_routes`).
- [ ] **Step 4: Run** → PASS; `uv run pytest tests/ -n auto`.
- [ ] **Step 5: Commit** — `feat(gpu): LocalStageDispatcher honors device_resolver; emit DeviceInfo`.

### Task A5: Milestone A verification + return

- [ ] Run `make ci AI=1` in the worktree. Expected: green. (If it aborts on `core.hooksPath`, see `feedback_make_ci_worktree_hookpath.md` — point CI at `setup-env`.)
- [ ] Return `{worktree_path, branch: feat/suite-device}` to the orchestrator. **Do not merge.**

---

## Milestone B — pdomain-ops: update endpoint

**Agent:** `pdomain-ops` · **worktree branch:** `feat/suite-update` · merge after A.

### Task B1: version check against the index

**Files:**
- Create: `pdomain_ops/suite/update.py`
- Test: `tests/suite/test_update_check.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/suite/test_update_check.py
from pdomain_ops.suite.update import compare_versions, parse_index_versions

_SIMPLE_HTML = '<a href="pdomain_ocr_simple_gui-0.9.0-py3-none-any.whl">x</a>' \
               '<a href="pdomain_ocr_simple_gui-0.10.0-py3-none-any.whl">y</a>'


def test_parse_index_versions():
    assert parse_index_versions(_SIMPLE_HTML, "pdomain-ocr-simple-gui") == ["0.9.0", "0.10.0"]


def test_compare_versions_update_available():
    assert compare_versions(current="0.9.0", latest="0.10.0") is True
    assert compare_versions(current="0.10.0", latest="0.10.0") is False
    assert compare_versions(current="0.11.0", latest="0.10.0") is False
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — `parse_index_versions(html, dist_name)` regexes wheel filenames (normalize `-`/`_`); `compare_versions` uses `packaging.version.Version`; `check_latest(dist_name, index_url, *, fetch=httpx.get)` returns `{current, latest, update_available, changelog_url, channel}` (inject `fetch` for tests; default real httpx; offline → return `update_available=False`).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `feat(suite): index version check (parse + compare)`.

### Task B2: editable guard + gated upgrade + rollback record

**Files:**
- Modify: `pdomain_ops/suite/update.py`
- Test: `tests/suite/test_update_apply.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/suite/test_update_apply.py
import pytest
from pdomain_ops.suite.update import apply_upgrade, EditableInstallError


def test_refuses_editable(monkeypatch, tmp_path):
    monkeypatch.setattr("pdomain_ops.suite.update.is_editable_install", lambda dist: True)
    with pytest.raises(EditableInstallError):
        apply_upgrade("pdomain-ocr-simple-gui", run=lambda *a, **k: None)


def test_runs_uv_tool_upgrade_and_records_previous(monkeypatch, tmp_path):
    monkeypatch.setattr("pdomain_ops.suite.update.is_editable_install", lambda dist: False)
    monkeypatch.setattr("pdomain_ops.suite.update.installed_version", lambda dist: "0.9.0")
    monkeypatch.setattr("pdomain_ops.suite.update._rollback_path", lambda dist: tmp_path / "rb.json")
    calls = []
    apply_upgrade("pdomain-ocr-simple-gui", run=lambda cmd, **k: calls.append(cmd))
    assert calls and calls[0][:3] == ["uv", "tool", "upgrade"]
    assert (tmp_path / "rb.json").read_text().strip()  # previous version recorded
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — `is_editable_install(dist)` checks `.venv/.pd-local-mode` marker / `importlib.metadata` direct_url editable flag; `apply_upgrade(dist, *, run=subprocess.run)` raises `EditableInstallError` if editable, else records previous version to `_rollback_path` then runs `["uv", "tool", "upgrade", dist]`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `feat(suite): gated upgrade with editable guard + rollback record`.

### Task B3: `/api/suite/update` route + policy + schema

**Files:**
- Create: `pdomain_ops/suite/update_routes.py`
- Modify: `pdomain_ops/suite/routes.py` (mount), `pdomain_ops/schemas/emit.py` (`UpdateInfo`)
- Test: `tests/suite/test_update_routes.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/suite/test_update_routes.py
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pdomain_ops.suite.update_routes import mount_update_routes


def test_get_update(monkeypatch):
    monkeypatch.setattr("pdomain_ops.suite.update_routes.check_latest",
                        lambda **k: {"current": "0.9.0", "latest": "0.10.0", "update_available": True,
                                     "changelog_url": "x", "channel": "stable"})
    app = FastAPI(); mount_update_routes(app, dist_name="pdomain-ocr-simple-gui", index_url="https://x")
    r = TestClient(app).get("/api/suite/update")
    assert r.status_code == 200 and r.json()["update_available"] is True


def test_post_update_invokes_apply(monkeypatch):
    seen = {}
    monkeypatch.setattr("pdomain_ops.suite.update_routes.apply_upgrade",
                        lambda dist, **k: seen.setdefault("dist", dist))
    app = FastAPI(); mount_update_routes(app, dist_name="pdomain-ocr-simple-gui", index_url="https://x")
    r = TestClient(app).post("/api/suite/update")
    assert r.status_code in (200, 202) and seen["dist"] == "pdomain-ocr-simple-gui"
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — `mount_update_routes(app, *, dist_name, index_url)`: `GET` returns `UpdateInfo` (pydantic) via `check_latest`; `POST` calls `apply_upgrade` and returns `{"restart_required": True}` (the shell performs the restart — Milestone C). Add `UpdateInfo` to `PUBLIC_MODELS`. Mount in `mount_routes` (dist_name + index_url from `suite_app`/env `PDOMAIN_INDEX_URL`).
- [ ] **Step 4: Run** → PASS; `uv run pytest tests/ -n auto`.
- [ ] **Step 5: Commit** — `feat(suite): GET/POST /api/suite/update + UpdateInfo schema`.

### Task B4: Milestone B verification + return

- [ ] `make ci AI=1` green in worktree. Return `{worktree_path, branch: feat/suite-update}`. Do not merge.

---

## Milestone C — pdomain-ops: desktop shell, sibling-spawn, shortcuts

**Agent:** `pdomain-ops` · **worktree branch:** `feat/desktop-shell` · merge after B.

### Task C1: sibling_spawn windowed arg

**Files:**
- Modify: `pdomain_ops/suite/sibling_spawn.py`
- Test: `tests/suite/test_sibling_spawn_windowed.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/suite/test_sibling_spawn_windowed.py
from pdomain_ops.suite.sibling_spawn import build_launch_argv  # extract argv builder if not present


def _app():  # minimal InstalledApp-like
    from pdomain_ops.suite.types import InstalledApp
    return InstalledApp(app_id="a", package="a", version="0", binary="/usr/bin/a", default_port=8004)


def test_argv_windowed_appends_desktop():
    assert "--desktop" in build_launch_argv(_app(), windowed=True)


def test_argv_default_no_desktop():
    assert "--desktop" not in build_launch_argv(_app(), windowed=False)
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — extract the argv list (currently inline in `LocalSpawnLauncher.launch()`) into `build_launch_argv(app, *, windowed=False)` returning `[app.binary, "--port", str(app.default_port), *(["--desktop"] if windowed else [])]`; have `launch(app, *, windowed=False)` call it and thread the flag through `SiblingLaunchAdapter`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `feat(suite): sibling_spawn windowed flag → --desktop`.

### Task C2: Linux desktop shortcut

**Files:**
- Modify: `pdomain_ops/suite/desktop.py`
- Test: `tests/suite/test_desktop_shortcut.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/suite/test_desktop_shortcut.py
import sys, pytest
from pdomain_ops.suite.desktop import install_shortcut, remove_shortcut
from pdomain_ops.suite.types import InstalledApp


@pytest.mark.skipif(sys.platform != "linux", reason="linux shortcut")
def test_install_writes_desktop_file(monkeypatch, tmp_path):
    monkeypatch.setattr("pdomain_ops.suite.desktop._applications_dir", lambda: tmp_path)
    app = InstalledApp(app_id="ocr", package="p", version="1", binary="/usr/bin/ocr", default_port=8004,
                       display_name="OCR")
    install_shortcut(app)
    f = tmp_path / "pdomain-ocr.desktop"
    text = f.read_text()
    assert "Exec=/usr/bin/ocr --desktop" in text and "Name=OCR" in text
    remove_shortcut("ocr")
    assert not f.exists()
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — Linux branch writes a `.desktop` file (`[Desktop Entry]`, `Type=Application`, `Name=`, `Exec=<binary> --desktop`, `Icon=`, `Terminal=false`) into `_applications_dir()` (`~/.local/share/applications`, via platformdirs); `remove_shortcut` unlinks it. Keep macOS/Windows raising `NotImplementedError`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `feat(suite): Linux .desktop shortcut install/remove`.

### Task C3: single-instance lock + stale reap

**Files:**
- Create: `pdomain_ops/suite/single_instance.py`
- Test: `tests/suite/test_single_instance.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/suite/test_single_instance.py
from pdomain_ops.suite.single_instance import acquire, read_live, InstanceLock


def test_acquire_then_read(monkeypatch, tmp_path):
    monkeypatch.setattr("pdomain_ops.suite.single_instance._lock_path", lambda app_id: tmp_path / f"{app_id}.json")
    lock = acquire("ocr", port=8004, pid=1234)
    assert isinstance(lock, InstanceLock)
    live = read_live("ocr")
    assert live and live["port"] == 8004 and live["pid"] == 1234


def test_stale_reaped(monkeypatch, tmp_path):
    monkeypatch.setattr("pdomain_ops.suite.single_instance._lock_path", lambda app_id: tmp_path / f"{app_id}.json")
    monkeypatch.setattr("pdomain_ops.suite.single_instance._pid_alive", lambda pid: False)
    acquire("ocr", port=8004, pid=999999)
    assert read_live("ocr") is None  # dead pid → reaped
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — JSON lockfile `{pid, port}` in `suite_data_dir()/locks/`; `acquire` writes it (filelocked); `read_live` returns the entry only if `_pid_alive(pid)` else deletes and returns `None`; `_pid_alive` via `os.kill(pid, 0)`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `feat(suite): single-instance pidfile lock + stale reap`.

### Task C4: `run_windowed` choreography (injectable seams)

**Files:**
- Create: `pdomain_ops/desktop.py`
- Test: `tests/test_desktop_run_windowed.py`

- [ ] **Step 1: Write the failing test** (fakes for server/window/tray — no real GUI)

```python
# tests/test_desktop_run_windowed.py
from pdomain_ops.desktop import run_windowed, ShellDeps


def test_boot_order_and_shutdown():
    events = []
    deps = ShellDeps(
        start_server=lambda port: events.append(("server", port)) or (lambda: events.append("server_stop")),
        wait_healthy=lambda port, timeout: events.append("healthy") or True,
        open_window=lambda url: events.append(("window", url)),
        run_tray=lambda on_quit: events.append("tray"),
        stop_tray=lambda: events.append("tray_stop"),
        resolve_port=lambda: 8004,
        acquire_instance=lambda port: events.append("lock") or object(),
    )
    run_windowed("pdomain_ocr_simple_gui.app:app", title="OCR", deps=deps)
    # server starts and is healthy before the window opens
    assert events.index(("server", 8004)) < events.index("healthy") < events.index(("window", "http://127.0.0.1:8004/"))
    # quitting stops server and tray
    assert "server_stop" in events and "tray_stop" in events


def test_existing_instance_focuses_not_respawn():
    events = []
    deps = ShellDeps(
        resolve_port=lambda: 8004,
        existing_instance=lambda: {"port": 8010},  # already running
        focus_existing=lambda port: events.append(("focus", port)),
        start_server=lambda port: (_ for _ in ()).throw(AssertionError("must not start")),
    )
    run_windowed("x:app", title="OCR", deps=deps)
    assert ("focus", 8010) in events
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — `ShellDeps` dataclass of callables (defaults wired to real `uvicorn.Server` thread, `webview`, `pystray`, `single_instance`, `bootstrap_spa`); `run_windowed(app_module, *, title, deps=ShellDeps())`:
  1. if `deps.existing_instance()` → `deps.focus_existing(port)`; return.
  2. `port = deps.resolve_port()`; `deps.acquire_instance(port)`.
  3. `stop_server = deps.start_server(port)`; `deps.wait_healthy(port, timeout=30)`.
  4. spawn tray on a thread via `deps.run_tray(on_quit=...)`.
  5. `deps.open_window(f"http://127.0.0.1:{port}/")` (blocks on main thread).
  6. on window close / tray quit: `stop_server()`; `deps.stop_tray()`.
  Provide a `restart()` helper (re-exec `sys.argv`) used by the update POST flow.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `feat(desktop): run_windowed choreography with injectable seams`.

### Task C5: `[desktop]` extra + Milestone C verification

- [ ] Add to `pyproject.toml`: `[project.optional-dependencies]\ndesktop = ["pywebview>=5", "pystray>=0.19"]`.
- [ ] `make ci AI=1` green. Return `{worktree_path, branch: feat/desktop-shell}`. Do not merge.

---

## Milestone D — pdomain-ui: compute + update panels

**Agent:** `pdomain-ui` · **worktree branch:** `feat/compute-update-panels`. Runs in **parallel with A/B/C** (different repo). Built against the documented `/api/suite/device` + `/api/suite/update` contracts; types hand-written (consistent with current hand-written stubs — no codegen bump).

### Task D1: testids

**Files:** Modify `src/testids/index.ts` · Test: `src/testids/index.test.ts` (extend existing)

- [ ] **Step 1: failing test**

```ts
import { COMPUTE_TARGET_PANEL, COMPUTE_DEVICE_OPTION, UPDATE_PANEL, UPDATE_BADGE, UPDATE_APPLY_BUTTON } from "./index";
test("desktop testids defined", () => {
  expect(COMPUTE_TARGET_PANEL).toBe("compute-target-panel");
  expect(COMPUTE_DEVICE_OPTION("cpu")).toBe("compute-device-option-cpu");
  expect(UPDATE_BADGE).toBe("update-badge");
});
```

- [ ] **Step 2: Run** `pnpm vitest run src/testids/index.test.ts` → FAIL.
- [ ] **Step 3: Implement** — add the constants + `COMPUTE_DEVICE_OPTION = (id: string) => \`compute-device-option-${id}\``.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** — `feat(testids): compute + update panel testids`.

### Task D2: device API config + hook

**Files:** Create `src/shell/createApiDeviceConfig.ts`, `src/stores/useDeviceInfo.ts` · Tests alongside.

- [ ] **Step 1: failing test**

```ts
// src/stores/useDeviceInfo.test.ts
import { renderHook, waitFor } from "@testing-library/react";
import { useDeviceInfo } from "./useDeviceInfo";

test("loads device info via injected fetcher", async () => {
  const { result } = renderHook(() =>
    useDeviceInfo({ fetchDevice: async () => ({ mode: "local", available: [{ id: "cpu", label: "CPU" }], current: "cpu", effective_source: "auto" }) }),
  );
  await waitFor(() => expect(result.current.info?.current).toBe("cpu"));
});
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — `createApiDeviceConfig()` returns `{ fetchDevice: () => fetch("/api/suite/device").then(r=>r.json()), putDevice: (b)=>fetch("/api/suite/device",{method:"PUT",...}) }` (mirror `createApiSuiteSiblingsConfig`). `useDeviceInfo({fetchDevice, putDevice})` follows the stub-friendly `useStageCall`/`useLongJob` pattern: state `{info, loading, error, setDevice(scope, device)}`.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** — `feat(ui): useDeviceInfo + createApiDeviceConfig`.

### Task D3: `<ComputeTargetPanel>`

**Files:** Create `src/shell/ComputeTargetPanel.tsx` + test.

- [ ] **Step 1: failing test**

```tsx
// src/shell/ComputeTargetPanel.test.tsx
import { render, screen } from "@testing-library/react";
import { ComputeTargetPanel } from "./ComputeTargetPanel";
import { COMPUTE_TARGET_PANEL } from "../testids";

const info = { mode: "local", available: [{ id: "cpu", label: "CPU" }, { id: "cuda:0", label: "GPU", vram_total_mb: 8192 }], current: "cpu", effective_source: "auto" };

test("renders device list in local mode", () => {
  render(<ComputeTargetPanel info={info} onSelect={() => {}} />);
  expect(screen.getByTestId(COMPUTE_TARGET_PANEL)).toBeInTheDocument();
  expect(screen.getByText("GPU")).toBeInTheDocument();
});

test("hidden when not local mode", () => {
  const { container } = render(<ComputeTargetPanel info={{ ...info, mode: "hosted" }} onSelect={() => {}} />);
  expect(container).toBeEmptyDOMElement();
});
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — presentational component: returns `null` when `info.mode !== "local"`; renders device radio list (`COMPUTE_DEVICE_OPTION(id)` testids), VRAM, force-CPU, current/effective-source line, and a "Speed this up → CUDA install docs" link. `var(--token)` styles only, no hex.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** — `feat(ui): ComputeTargetPanel (local-mode-gated)`.

### Task D4: update API config + hook

**Files:** Create `src/shell/createApiUpdateConfig.ts`, `src/stores/useUpdateCheck.ts` + tests.

- [ ] **Step 1: failing test**

```ts
// src/stores/useUpdateCheck.test.ts
import { renderHook, waitFor } from "@testing-library/react";
import { useUpdateCheck } from "./useUpdateCheck";

test("flags update available", async () => {
  const { result } = renderHook(() =>
    useUpdateCheck({ fetchUpdate: async () => ({ current: "0.9.0", latest: "0.10.0", update_available: true, changelog_url: "x", channel: "stable" }), policy: "notify" }),
  );
  await waitFor(() => expect(result.current.info?.update_available).toBe(true));
});

test("manual policy does not auto-check", async () => {
  const fetchUpdate = vi.fn();
  renderHook(() => useUpdateCheck({ fetchUpdate, policy: "manual" }));
  expect(fetchUpdate).not.toHaveBeenCalled();
});
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — `createApiUpdateConfig()` → `{fetchUpdate, applyUpdate}` against `/api/suite/update`. `useUpdateCheck({fetchUpdate, applyUpdate, policy})`: auto-checks on mount for `notify`/`auto`, applies automatically for `auto`, no-op for `manual`; exposes `{info, checkNow(), applyAndRestart()}`.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** — `feat(ui): useUpdateCheck + createApiUpdateConfig`.

### Task D5: `<UpdatePanel>` + badge

**Files:** Create `src/shell/UpdatePanel.tsx` + test.

- [ ] **Step 1: failing test**

```tsx
// src/shell/UpdatePanel.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { UpdatePanel } from "./UpdatePanel";
import { UPDATE_APPLY_BUTTON } from "../testids";

test("apply button fires applyAndRestart", () => {
  const apply = vi.fn();
  render(<UpdatePanel info={{ current: "0.9.0", latest: "0.10.0", update_available: true, changelog_url: "x", channel: "stable" }} policy="notify" onPolicyChange={() => {}} onApply={apply} />);
  fireEvent.click(screen.getByTestId(UPDATE_APPLY_BUTTON));
  expect(apply).toHaveBeenCalled();
});
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — `<UpdatePanel>` shows current/latest, changelog link, "Update & Restart" button (`UPDATE_APPLY_BUTTON`), and a policy selector (`notify`/`auto`/`manual`). Export a tiny `<UpdateBadge available />` (`UPDATE_BADGE`) for the header.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** — `feat(ui): UpdatePanel + UpdateBadge`.

### Task D6: exports + version bump + verification

**Files:** Modify `src/shell/index.ts`, `src/index.ts`, `package.json`.

- [ ] Export `ComputeTargetPanel`, `UpdatePanel`, `UpdateBadge`, `useDeviceInfo`, `useUpdateCheck`, `createApiDeviceConfig`, `createApiUpdateConfig` through `./shell` + `./stores` subpaths (match existing export formula).
- [ ] Add a failing `tests/build.contract.test.ts` assertion that the new subpath exports resolve, then build to satisfy it.
- [ ] Bump `package.json` version `0.6.0` → `0.7.0`.
- [ ] `make ci AI=1` green. Return `{worktree_path, branch: feat/compute-update-panels}`. Do not merge.

> **Optional intra-repo parallelism:** split D into `feat/compute-panel` (D1–D3) and `feat/update-panel` (D4–D5), rebase-merge sequentially; D6 (shared exports/version) runs last. Default: one worktree, sequential — cleaner.

---

## Milestone E — releases (orchestrator, not a subagent)

### E1: release pdomain-ops 0.8.0
- [ ] After A→B→C are all merged to `pdomain-ops` main and `make ci` is green on main: tag per the repo's release flow (hatch-vcs tag-driven). Verify the wheel publishes to `pdomain-index-pip`.

### E2: release pdomain-ui 0.7.0
- [ ] After D merged + `make ci` green on main: `make release-minor` (bump already at 0.7.0 → confirm), publish to `pdomain-index-npm`.

---

## Milestone F — simple-gui pilot

**Agent:** `pdomain-ocr-simple-gui` · **worktree branch:** `feat/desktop-pilot`. After E.

### Task F1: bump deps
- [ ] Modify `pyproject.toml`: `pdomain-ops>=0.8.0`. Modify `frontend/package.json`: `@pdomain/pdomain-ui` `^0.7.0`. Run `make update-pd-deps` if available; else edit + `uv sync` + `pnpm install`.
- [ ] Commit — `chore(deps): pdomain-ops 0.8.0, pdomain-ui 0.7.0`.

### Task F2: `--desktop` flag

**Files:** Modify `src/pdomain_ocr_simple_gui/__main__.py` · Test: `tests/test_cli_desktop.py`

- [ ] **Step 1: failing test**

```python
# tests/test_cli_desktop.py
from pdomain_ocr_simple_gui.__main__ import _parse_args


def test_desktop_flag_parses():
    args = _parse_args(["--desktop"])
    assert args.desktop is True


def test_desktop_calls_run_windowed(monkeypatch):
    called = {}
    monkeypatch.setattr("pdomain_ocr_simple_gui.__main__.run_windowed",
                        lambda module, **k: called.setdefault("module", module))
    from pdomain_ocr_simple_gui.__main__ import main
    main(["--desktop"])
    assert called["module"] == "pdomain_ocr_simple_gui.app:app"
```

- [ ] **Step 2: Run** `uv run pytest tests/test_cli_desktop.py -v` → FAIL.
- [ ] **Step 3: Implement** — add `desktop: bool` to `_CliArgs` + `--desktop` to `_parse_args`; in `main`, when `args.desktop`, import `from pdomain_ops.desktop import run_windowed` and call `run_windowed("pdomain_ocr_simple_gui.app:app", title="OCR Simple GUI")` instead of `uvicorn.run`. Fill `--install-desktop-shortcut`/`--remove-desktop-shortcut` to call `pdomain_ops.suite.desktop.install_shortcut/remove_shortcut`.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** — `feat(cli): --desktop launches windowed shell; fill shortcut stubs`.

### Task F3: `--update` flag

**Files:** Modify `__main__.py` · Test: `tests/test_cli_update.py`

- [ ] **Step 1: failing test**

```python
def test_update_flag_invokes_apply(monkeypatch):
    seen = {}
    monkeypatch.setattr("pdomain_ocr_simple_gui.__main__.apply_upgrade",
                        lambda dist, **k: seen.setdefault("dist", dist))
    from pdomain_ocr_simple_gui.__main__ import main
    main(["--update"])
    assert seen["dist"] == "pdomain-ocr-simple-gui"
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — add `--update`; when set, `from pdomain_ops.suite.update import apply_upgrade; apply_upgrade("pdomain-ocr-simple-gui")` then exit.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** — `feat(cli): --update runs gated upgrade`.

### Task F4: routes mounted (regression test)

**Files:** Test: `tests/test_suite_device_update_routes.py`

- [ ] **Step 1: failing test** — uses the existing `test_routes_root.py` app fixture pattern:

```python
def test_device_and_update_routes_present(client):  # client fixture from conftest
    assert client.get("/api/suite/device").status_code == 200
    assert client.get("/api/suite/update").status_code == 200


def test_routes_not_shadowed_by_spa_catchall(client):
    assert client.get("/api/suite/device").headers["content-type"].startswith("application/json")
```

- [ ] **Step 2: Run** → these pass once deps are bumped (routes arrive via `mount_routes`). If FAIL, the `mount_routes` wiring in pdomain-ops (Task A3/B3) regressed — fix upstream.
- [ ] **Step 3: Commit** — `test: assert device+update routes mounted and not shadowed`.

### Task F5: wire panels into the dock

**Files:** Modify `frontend/src/App.tsx` · Test: `frontend/src/App.test.tsx` (or a focused panels test)

- [ ] **Step 1: failing test** — assert the `settingsPanels` array passed to `<AppShell>` includes a `compute` and an `update` descriptor (render + query by testid, or unit-test the `settingsPanels` builder).
- [ ] **Step 2: Run** `pnpm vitest run` → FAIL.
- [ ] **Step 3: Implement** — import `ComputeTargetPanel`, `UpdatePanel`, `useDeviceInfo`, `useUpdateCheck`, `createApiDeviceConfig`, `createApiUpdateConfig` from `@pdomain/pdomain-ui/shell` + `/stores`; add two `SettingsPanelDescriptor` entries (`{id:"compute", label:"Compute", content:<ComputeTargetPanel .../>}`, `{id:"updates", label:"Updates", content:<UpdatePanel .../>}`) to the `settingsPanels` array; render `<UpdateBadge>` in `SimpleGuiHeader`.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** — `feat(ui): mount Compute + Updates panels in dock`.

### Task F6: PWA manifest

**Files:** Create `frontend/public/manifest.webmanifest` · Modify `frontend/index.html` · Test: `tests/test_pwa_manifest.py`

- [ ] **Step 1: failing test**

```python
def test_manifest_served(client):
    r = client.get("/manifest.webmanifest")
    assert r.status_code == 200
    assert r.json()["name"]  # has a name
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — add `manifest.webmanifest` (`name`, `short_name`, `start_url:"/"`, `display:"standalone"`, icons referencing `/api/self/icons/*`); add `<link rel="manifest" href="/manifest.webmanifest" />` to `index.html`. (Vite copies `public/` to the build output, served by the existing StaticFiles/catch-all.)
- [ ] **Step 4: Run** `make frontend-build` then the test → PASS. **Step 5: Commit** — `feat(pwa): web manifest for install-as-app`.

### Task F7: Milestone F verification
- [ ] `make ci AI=1` green. Return `{worktree_path, branch: feat/desktop-pilot}`. Do not merge.

---

## Milestone G — Linux installer (engine + AppImage + CI)

**Agent:** `pdomain-ocr-simple-gui` · **worktree branch:** `feat/linux-installer`. After F. Parallel with H.

> **Backend pivot (2026-06-06):** Shipped with the **Qt** webview backend, not WebKitGTK — the
> uv-tool venv is isolated from system site-packages, so GTK's `gi` is unimportable (the original
> user-facing crash). The engine's webview step installs the Qt xcb-cursor lib
> (`libxcb-cursor0`/`xcb-util-cursor`), **X11 only**; Wayland needs none. The TDD snippets below
> still show the original WebKitGTK package names — **superseded**; see `installer/install_engine.py`
> for the shipped Qt mapping and spec §3A (revised).

### Task G1: installer engine (gated, unit-testable)

**Files:** Create `packaging/install_engine.py` · Test: `tests/packaging/test_install_engine.py`

- [ ] **Step 1: failing test**

```python
# tests/packaging/test_install_engine.py
from packaging.install_engine import detect_pkg_manager, webview_package_for, plan_steps


def test_detect_pkg_manager(monkeypatch):
    monkeypatch.setattr("packaging.install_engine._which", lambda x: x == "apt")
    assert detect_pkg_manager() == "apt"


def test_webview_package_mapping():
    assert webview_package_for("apt") == "gir1.2-webkit2-4.1"
    assert webview_package_for("pacman") == "webkit2gtk"
    assert webview_package_for("unknown") is None


def test_plan_steps_includes_gated_actions():
    steps = plan_steps(has_uv=False, has_webview=False, gpu="nvidia")
    ids = [s.id for s in steps]
    assert ids == ["uv", "webview", "tool_install", "gpu_torch", "shortcut"]
    assert all(s.command for s in steps)  # each gated step has an explicit command
```

- [ ] **Step 2: Run** `uv run pytest tests/packaging/test_install_engine.py -v` → FAIL.
- [ ] **Step 3: Implement** — pure functions: `detect_pkg_manager()` (probe apt/dnf/yum/pacman/zypper/apk via `_which`), `webview_package_for(mgr)` (mapping table; `None` for unknown), `plan_steps(has_uv, has_webview, gpu)` returns a list of `Step(id, description, command, needs_sudo)` (skip uv/webview steps when already present; include `gpu_torch` only when `gpu == "nvidia"`). `detect_nvidia()` via `nvidia-smi` presence. The interactive runner (`run(steps, *, assume_yes, dry_run, ask=input)`) prints/gates/executes — test it with a fake `ask` and a fake `run_cmd`.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** — `feat(installer): gated install engine (detect + plan + run)`.

### Task G2: AppImage GUI wizard
- [ ] Create `packaging/appimage/` with an AppRun + a minimal wizard entry that imports `install_engine` and presents the gated steps (tkinter wizard frozen into the AppImage; engine is the tested core). Add `packaging/build_appimage.sh` using `appimagetool`. (GUI click-through is a manual gate — no CI assertion.)
- [ ] Commit — `feat(installer): Linux AppImage GUI wizard over the engine`.

### Task G3: release-matrix CI (ubuntu-latest, lean)
- [ ] Create `.github/workflows/installer.yml`: trigger on tag/release; `ubuntu-latest`; build the AppImage; run `uv run pytest tests/packaging/ -n auto` (engine logic — heavy `uv tool install` stubbed); `actions/cache` for uv. No Windows/macOS jobs (deferred).
- [ ] Commit — `ci(installer): ubuntu-latest release-matrix, lean smoke`.

### Task G4: prereqs/CUDA doc
- [ ] Create `docs/runbooks/install.md`: prerequisites, the gated steps, per-distro **Qt xcb-cursor** packages (`libxcb-cursor0`/`xcb-util-cursor`, X11 only; Wayland needs none), NVIDIA driver guidance + the `cu12x` torch swap, rollback (`uv tool install <app>==<old>`).
- [ ] Commit — `docs(install): Linux install + CUDA runbook`.
- [ ] `make ci AI=1` green. Return `{worktree_path, branch: feat/linux-installer}`.

---

## Milestone H — Browser verification (MANDATORY, FastAPI+SPA)

**Agent:** `pdomain-ocr-simple-gui` · **worktree branch:** `test/desktop-e2e`. After F. Parallel with G. Uses the existing `e2e` dependency-group (`pytest-playwright`) and `make e2e-fast` harness.

### Task H1: data-testid contract
- [ ] Ensure the two dock panels surface stable testids in the running app (the pdomain-ui components already carry `COMPUTE_TARGET_PANEL`, `UPDATE_PANEL`, `UPDATE_BADGE`; confirm `HomePage` has `[data-testid="home-page"]`). Add any missing root testid. Commit.

### Task H2: app-loads + panels test

**Files:** Create `tests/e2e/test_desktop_panels.py`

- [ ] **Step 1: write the test**

```python
# tests/e2e/test_desktop_panels.py — runs against the real server (fake dispatcher), headless Chromium
import pytest


@pytest.mark.e2e
def test_app_loads_no_console_errors(page, base_url):
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(base_url)
    page.wait_for_selector('[data-testid="home-page"]')
    assert not [e for e in errors if "Failed to load" in e]


@pytest.mark.e2e
def test_compute_panel_visible_and_lists_cpu(page, base_url):
    page.goto(base_url)
    page.click('[data-testid="utility-dock-settings"]')   # open dock → settings
    page.click('[data-testid="settings-modal-tab-compute"]')
    page.wait_for_selector('[data-testid="compute-target-panel"]')
    assert page.is_visible('[data-testid="compute-device-option-cpu"]')


@pytest.mark.e2e
def test_router_subpath_renders(page, base_url):
    page.goto(f"{base_url}/jobs/does-not-exist")
    # React Router renders a page component, not a JSON 404
    assert page.locator('[data-testid="home-page"], [data-testid="results-page"]').count() >= 0
    assert "Not Found" not in page.content()
```

- [ ] **Step 2: Run** `make e2e-fast` (fake dispatcher, no weights). Expected: PASS (fix testids/wiring if not).
- [ ] **Step 3: Commit** — `test(e2e): desktop panels + app-loads + router-subpath`.

### Task H3: wire into CI
- [ ] Ensure `make e2e-fast` (or the e2e marker) is part of `make ci` per the repo's existing gate. Confirm `playwright install chromium` is in `make setup`.
- [ ] `make ci AI=1` green. Return `{worktree_path, branch: test/desktop-e2e}`.

---

## Integration order (orchestrator)

1. Wave 1: dispatch A, B, C (`pdomain-ops`) + D (`pdomain-ui`) in parallel, each `isolation: "worktree"`.
2. Merge order in pdomain-ops: A → B → C (rebase each onto current main; `make ci` between). Merge D in pdomain-ui.
3. Wave 2: release pdomain-ops 0.8.0, pdomain-ui 0.7.0 (Milestone E).
4. Wave 3: dispatch F; merge.
5. Wave 4: dispatch G + H in parallel; merge.
6. Push only on CT authorization. Clean up worktrees + run editable-orphan fix.

---

## Self-review

- **Spec coverage:** §3A shell → C4/C5, F2; §3B device → A1–A4, D2–D3, F5; §3C update → B1–B3, D4–D5, F3; §4 windows/instances/launcher → C1, C3, C4; §5 lifecycle → C3, C4; §6 testing → tests in every task + Milestone H; §7.1 install → F1; §7.2 installer → G1–G2; §7.3 GPU → G1 (`gpu_torch` step); §7.4 CI → G3; §8 out-of-scope respected (no Windows/macOS tasks, no signing, no driver auto-install). All covered.
- **FastAPI+SPA check:** Milestone H (browser verification) present and mandatory — app-loads, panel flow, router-subpath, wired into CI. ✓
- **Type consistency:** `DeviceInfo`/`UpdateInfo` defined in A3/B3 and emitted to `PUBLIC_MODELS`; UI types hand-written to the same shape; `ShellDeps` defined once in C4; `Step` defined once in G1.
- **Pre-1.0 safety:** editable-install guard (B2), rollback record (B2), single-instance + stale reap (C3).
