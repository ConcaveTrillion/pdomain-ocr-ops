# pd-* suite desktop shell + shared compute-target control

- **Date:** 2026-06-04
- **Status:** Draft (design approved in brainstorm; pending spec review)
- **Scope:** Suite-wide capability, with `pdomain-ocr-simple-gui` as the pilot consumer.
- **Repos touched:** `pdomain-ops` (backend + shell), `pdomain-ui` (panel), `pdomain-ocr-simple-gui` (pilot wiring).
- **Routing:** Cross-cut → workspace `docs/specs/`; issues sync to `ConcaveTrillion/ocr-container-meta`.

## 1. Problem & motivation

The user asked "what would an Electron app for `pdomain-ocr-simple-gui` look like — would it
even make sense?" The honest answer reshaped the request:

- The React/Vite SPA already runs as a built bundle served by FastAPI over relative `/api`
  calls. The UI needs **zero changes** to run in a desktop window.
- The genuinely hard cost of a "one-click installer" — freezing the multi-GB
  `torch`/DocTR/OpenCV/Tesseract stack — is **explicitly out of scope**: we do not bundle ML
  deps. Distribution stays `uv tool install`; CUDA is documented; CPU fallback is the default.
- Three of the four desired benefits (native window, OS integration, suite launcher) do **not**
  need Electron. Electron's only unique value is cross-platform Chromium distribution, which a
  single-OS personal workflow does not use. **PyWebView + pystray** delivers the same window +
  tray + notifications inside the existing Python wheel, with no Node toolchain and no ~150 MB
  Chromium overhead.

So this is **not** an Electron project. It is a thin, in-stack desktop shell plus a shared
compute-device control, both built once and reused across the suite.

## 2. Core principle — extension, not replacement

**The server is canonical. The shell is an additive thin client.**

- Server mode (`pdomain-ocr-simple-gui`, no flags) keeps working exactly as today: uvicorn + SPA
  over HTTP, browser-accessible, and deployable to a future server. This is the source of truth
  and the deployment target.
- The desktop `[desktop]` extra (PyWebView, pystray) is **optional and never required** for
  headless/server use. If it is not installed, the server still runs fine.
- `--desktop` adds **no** app behavior. It wraps the same `create_app()` server in a native
  window pointed at `http://127.0.0.1:{port}/`. No route, no state, no business logic lives in
  the shell — otherwise server mode and desktop mode would diverge.
- Forward compatibility: this is a strict superset. Everything that works on a server works in
  the window; the server never depends on the shell. The same design supports future
  self-hosted/managed/server deployments unchanged.

## 3. Subsystems

Built shared-first, proven in simple-gui.

### A. Shared desktop shell — `pdomain-ops` (`pd_ocr_ops.desktop`, new module)

- `run_windowed(app_module, *, title, preferred_port, env_port_var)`:
  1. `bootstrap_spa()` resolves the dynamic port and registers in the suite registry (existing).
  2. Start `uvicorn.Server` on a **daemon thread**; poll a health route until ready.
  3. `webview.create_window(title, url=http://127.0.0.1:{port}/)`; `webview.start()` on the
     **main thread** (required by GTK/Cocoa).
  4. pystray tray icon launches alongside: running status, "Open window", "Quit".
- Fills the existing `--install-desktop-shortcut` / `--remove-desktop-shortcut` stubs using
  `pdomain-ops` desktop helpers + `platformdirs`.
- Ships as an optional **`[desktop]` extra** so headless/server installs stay lean.
- **Engine choice (REVISED 2026-06-06):** the Linux backend is **Qt** (`PyQt6` +
  `PyQt6-WebEngine`). The original design picked WebKitGTK, but it does **not** work with this
  project's distribution model: the app installs via `uv tool`, whose venv is **isolated from
  system site-packages**, so PyWebView's GTK backend cannot import `gi`/PyGObject even when the
  system WebKitGTK package is installed (`ModuleNotFoundError: No module named 'gi'` — observed on
  a real user host). Qt's wheels are **self-contained and live inside the tool venv**, arriving via
  the `[desktop]` extra (`pdomain-ocr-simple-gui[desktop]` → `pdomain-ops[desktop]` →
  `PyQt6`/`PyQt6-WebEngine`). WebKitGTK is retained only as a theoretical option if a
  `--system-site-packages` venv model is ever adopted. Trade-off: QtWebEngine is a ~150 MB payload
  vs WebKitGTK's shared lib — accepted because reliability in the isolated-venv model outweighs
  size, and it is dwarfed by the torch download.
- **Linux gotcha (documented):** the Qt wheels bundle the browser engine, but the X11 `xcb` plugin
  needs one small system lib (`libxcb-cursor0` / `xcb-util-cursor`, per distro). The installer
  installs it (§7.2). **Wayland sessions need no system package** — the shell auto-selects the
  bundled Wayland Qt plugin via `pdomain-ops` `_preferred_qt_platform` (sets `QT_QPA_PLATFORM=wayland`
  when `XDG_SESSION_TYPE=wayland`/`WAYLAND_DISPLAY` is set and the user has not chosen a platform).
- **Why embedded webview (not browser-as-app, not a bundled Chromium):** an embedded webview is
  **inherently isolated** (not a browser — no shared profile with the user's Chrome/Firefox),
  **lighter** (shared system lib, not a ~150 MB payload), and carries **no security-patch burden**
  (the OS updates it). Running the user's Chromium in `--app` mode was rejected because it depends
  on a Chromium-class browser being installed (desktop Firefox has no `--app`/PWA-install
  equivalent — its SSB support was removed ~FF85). Bundling our own Chromium was rejected as
  Electron-weight plus an ongoing engine-maintenance burden. See §8.
- **Free bonus:** the SPA ships a **PWA manifest** so a power user *may* "Install as app" via their
  own Chromium if they prefer — zero extra deps, no dependency of the shell on it.

### B. Shared compute-target control — `pdomain-ops` backend + `pdomain-ui` panel

Compute-device selection is a **local-deploy-mode-only** function. Device selection is a property
of `LocalStageDispatcher`; future `Modal*` / `GpuServer*` dispatchers implement the same
Protocol and ignore the device pref (work offloads server-side / batched). The surface is named
"compute target" so it does not need rebuilding when remote dispatch lands.

- `pdomain-ops` backend (mounted under existing `/api/suite/*`):
  - `GET /api/suite/device` → mode-aware:
    `{ mode: "local", available: [{id, label, vram_total, vram_free}], current, effective_source: "app"|"suite"|"auto" }`.
    Non-local mode → `{ mode, offload_target: null }` (panel hides).
  - `PUT /api/suite/device` → `{ scope: "app"|"suite", device: "cpu"|"cuda:N" }`, persists pref.
- Prefs schema:
  - Suite default: `suite.compute.device_default`.
  - Per-app override: `app.<app_id>.compute.device` (unset → inherit suite default).
  - `LocalStageDispatcher` resolves effective device at dispatch:
    per-app override → suite default → `pick_device()` auto.
- `pdomain-ui` `<ComputeTargetPanel>`:
  - Lives in the existing right-side utility dock.
  - Local mode → device list + VRAM, force-CPU, current/effective source, a coarse OOM-risk
    warning, and a "Speed this up → CUDA install docs" link.
  - **Hidden when `deployMode !== "local"`.**

### C. Shared update control — `pdomain-ops` backend + `pdomain-ui` panel

Each app is an isolated `uv tool` install from the self-hosted `pdomain-index-pip`, so
`uv tool upgrade <app>` re-resolves it + all pd-* deps from the index — **per-app isolated**
(upgrading one app cannot break another's pins). The job is to wrap that engine in an easy, safe
flow. Mirrors the compute-target pattern (shared backend + dock panel + simple-gui pilot).

- `pdomain-ops` backend (mounted under existing `/api/suite/*`):
  - `GET /api/suite/update` → `{ current, latest, update_available, changelog_url, channel }`
    (queries the index simple-page for the latest version).
  - `POST /api/suite/update` → runs `uv tool upgrade`, then signals the shell to **restart**
    (a running venv can't be replaced in place: upgrade → relaunch, which the shell owns).
- **Update policy pref** (`suite.update.policy` ∈ `notify` | `auto` | `manual`, default `notify`;
  per-app override allowed like the device pref):
  - `notify` (default) → check on launch (+ optionally daily); show an "Update available" badge;
    user clicks **Update & Restart**. No surprise mid-session upgrades.
  - `auto` → check + apply on next launch silently.
  - `manual` → no automatic check; "Check for updates" button + `--update` CLI only.
- **Safety rails (pre-1.0, no semver guarantee):**
  - **Refuse to upgrade an editable / local-dev install** (detect the `.venv/.pd-local-mode`
    marker / editable resolution) — never `uv tool upgrade` over a dev checkout.
  - Record the previous version so **rollback** is `uv tool install <app>==<old>`.
  - Network/offline failures fail silently (no nag, no block).
- `pdomain-ui` `<UpdatePanel>` (+ a badge): current vs latest, changelog link,
  **Update & Restart**, and the policy selector (`notify`/`auto`/`manual`).
- Secondary paths: re-running the AppImage installer detects an existing install and offers
  **Update**; `pdomain-ocr-simple-gui --update` is the CLI/power path (the engine for all of it).

### D. simple-gui pilot

- Bumps `pdomain-ops` + `pdomain-ui` deps.
- Adds a `--desktop` flag that calls `run_windowed`; ships the PWA manifest (§3A).
- Mounts the device + update routes (already mounts `/api/suite/*`) and drops
  `<ComputeTargetPanel>` + `<UpdatePanel>` into its dock.
- No React app changes beyond panel placement. Other five apps (labeler, prep, synth, trainer,
  future post-process) inherit by bumping deps. The future "proofreading" app does not need the
  compute panel (it does get update control).

## 4. Windows, instances, and the launcher

- **One window per app, one process per app.** Each app runs its own uvicorn + native window +
  tray entry. Independent — one crash does not affect the others.
- **Single backend per app (single-instance lock via the registry).** Re-launching an
  already-running app **focuses/raises the existing window** rather than starting a second
  uvicorn — this avoids concurrent prefs/job-store JSON-sidecar corruption.
- **Multiple windows onto one backend are allowed** (`webview.create_window` again): two views of
  the same state, the native macOS ⌘N idiom. No corruption risk.
- A fully isolated second instance (separate data dir / job store) is **out of scope for v1**.
- **Cross-app launcher reuses what exists:** `AppShell`'s header `launcherSlot` already lists
  installed siblings via `useSuiteSiblings` (suite registry / `installed.toml`). Clicking a
  sibling calls `sibling_spawn`. We extend `sibling_spawn(app_id, windowed: bool)` so that when
  the parent runs windowed, the sibling spawns with `--desktop` → its own window + tray entry.
  If the sibling is already running, focus its live registry port instead of double-spawning.

## 5. Lifecycle & clean shutdown (no zombie threads)

- uvicorn runs via a held `uvicorn.Server` handle; shutdown sets `server.should_exit = True` and
  **joins the thread with a timeout**, letting in-flight jobs finish/abort, then deregisters from
  the suite registry and releases the port.
- **Bidirectional watchdog:** window/tray "Quit" → stop server → join → stop tray → exit. And the
  reverse: if uvicorn dies unexpectedly, the window closes instead of hanging on a dead backend.
- pystray runs on its own thread with an explicit `icon.stop()` in the shutdown path.
- Registry entries carry **PID + port**; on startup, stale entries whose PID is dead are reaped
  (covers the hard-kill case where graceful shutdown never ran).

## 6. Testing & verification

GUI shells are tested headlessly by keeping `run_windowed` thin and injecting webview/tray/server
as seams — we test the choreography, not Chromium.

- **`pdomain-ops` desktop shell** — unit tests with fakes for webview + tray + `uvicorn.Server`:
  boot order (port → server thread → health wait → window), graceful shutdown (`should_exit` set,
  thread joined with timeout, registry deregistered, tray stopped), bidirectional watchdog,
  stale-PID reaping. **No real GUI in CI.**
- **`pdomain-ops` device backend** — mode-aware `GET/PUT /api/suite/device`, pref-resolution
  precedence (app → suite → auto), `sibling_spawn(windowed=True)` appends `--desktop` + reuses a
  live registry port.
- **`pdomain-ui` `<ComputeTargetPanel>`** — Vitest: renders device list + VRAM, force-CPU, fires
  `PUT` on change, hidden when `deployMode !== "local"` (mocked API).
- **`pdomain-ops` update control** — `GET /api/suite/update` version compare (current vs index
  latest), `POST` runs upgrade + signals restart (mocked subprocess), **refuses editable/local-dev
  installs**, records previous version for rollback, offline check fails silently. Policy pref
  resolution (`notify`/`auto`/`manual`, per-app override).
- **`pdomain-ui` `<UpdatePanel>`** — Vitest: badge when `update_available`, Update & Restart fires
  `POST`, policy selector persists, changelog link rendered (mocked API).
- **simple-gui pilot** — existing SPA-serving contract tests stay; add (a) device route mounted +
  not shadowed by the catch-all, (b) panel present in dock, (c) `--desktop` calls `run_windowed`
  (mocked — no window), (d) single-instance: second launch focuses existing.
- **E2E stays server-bound — unchanged.** Playwright drives the running uvicorn server with a
  headless browser over HTTP, exactly as now. We do **not** retarget it at the PyWebView window;
  because the SPA and routes are byte-identical in both modes, server-bound E2E *is* the desktop
  UI's coverage, and it keeps running in CI without a display.
- **Anti-divergence smoke test:** assert `--desktop` boots the *same* `create_app()` the server
  uses (shared factory, no forked app), so the two modes can never drift.
- **Manual verification gate (not CI):** launch `--desktop` on the Linux Mint box — window opens,
  tray works, OCR runs on CPU, device panel flips CPU↔CUDA, second launch focuses, Quit leaves
  **no orphan process** (`ps` / registry clean).

## 7. Distribution & installers

### 7.1 Underlying install (unchanged)

- `uv tool install "pdomain-ocr-simple-gui[desktop]"`; wheel published to `pdomain-index-pip`.
- `[desktop]` optional extra pulls `pywebview` + `pystray`; absent on headless/server installs.
- **No ML bundling.** CUDA setup is documented (a runbook + the in-panel docs link); CPU fallback
  is the default and always works.

### 7.2 Installers — native per platform, double-click GUI

Installers are **bootstrappers, not bundles** — they orchestrate the §7.1 install plus system
prerequisites. No ML inside. **v1 ships Linux only; Windows and macOS are deferred to future**
(see §8). The design is native-per-platform so each future OS gets its own familiar wizard.

**Two layers:**

- **Engine (gated CLI)** — the install logic: prereq detection, `uv` bootstrap, webview runtime,
  `uv tool install`, GPU-torch swap (§7.3), shortcut. Interactive and transparent: each step
  (a) explains what/why, (b) shows the exact command + whether it needs `sudo`, (c) waits for
  `Y/n`, (d) runs, (e) reports. Flags: `--dry-run` (print the plan, change nothing), `--yes`
  (non-interactive). This is the advanced/automation path **and the layer CI smoke-tests.**
- **GUI front-door (the EASE layer)** — a native double-click installer wrapping the engine,
  presenting the same gated steps as wizard pages (explain → consent → run → report).

**Gated step sequence:**

0. Show the prerequisites summary and the full list of what the flow will install.
1. Ensure `uv` (+ its managed Python) — gated.
2. Ensure the webview runtime — gated.
3. `uv tool install "pdomain-ocr-simple-gui[desktop]"` — gated.
4. Detect GPU and offer acceleration (§7.3) — gated.
5. Install the desktop shortcut + icon — gated.

An **uninstall** counterpart mirrors the steps in reverse, equally gated.

**Linux (v1 target) — AppImage GUI wizard, any distro.** A double-click AppImage carries the
wizard, runs on any distro with no prereqs of its own. Its engine detects the package manager
(`apt`/`dnf`-`yum`/`pacman`/`zypper`/`apk`) and maps the WebKitGTK package per distro family
(e.g. Debian/Ubuntu `gir1.2-webkit2-4.1`, Fedora `webkit2gtk4.1`, Arch `webkit2gtk`, openSUSE,
Alpine). `sudo` is used only at the gated package step; unknown distro → printed manual
instructions, then continue. An **optional `.deb`** convenience for apt users declares the
`webkit2gtk` dep and runs the install in `postinst`.

**Windows / macOS (future, stubbed):** Windows → Inno Setup `.exe` (native wizard, ensures the
WebView2 runtime); macOS → `.pkg`/`.app` (WKWebView built in). Both wrap the same engine. Not
built in v1.

**Shared vs pilot.** The engine + wizard are templated and parameterized by `app_id` / title /
icon / port so the other five apps reuse them. The pilot concretely ships
`pdomain-ocr-simple-gui`'s Linux installer.

### 7.3 GPU / CUDA handling

**No CUDA toolkit is needed.** PyTorch's `cu12x` wheels bundle their own CUDA runtime; the only
system requirement is a recent-enough **NVIDIA driver**. So "enable GPU" means installing the
GPU build of torch — a safe, gated `uv`/pip reinstall in the tool environment.

- **Auto + gated:** detect an NVIDIA GPU + working driver → offer "Enable GPU acceleration?" →
  swap the CPU torch for the `cu12x` wheel. No toolkit, no driver touched.
- **Detect + guide (driver):** driver missing/too old → show "NVIDIA GPU found — install the
  driver here" with the official link; **do not** auto-install the driver (invasive; reboot;
  distro- and secure-boot-specific on Linux).
- Ties straight into the runtime device panel (§3B) + `pick_device`: once GPU torch is in, the
  panel lights up CUDA automatically.
- **Out of scope:** auto driver install, CUDA toolkit install.

### 7.4 Installer build & smoke-test (CI)

- **GitHub Actions, release-time only** (fits "release = build + publish"). **v1 = `ubuntu-latest`
  only** (×1 multiplier). Windows (`windows-latest`, ×2) and macOS (`macos-latest`, ×10) runners
  are added when those installers land; EC2 Mac (now ~60 s min billing) is the off-GitHub fallback.
- **Lean smoke test:** build the AppImage and exercise the gated **engine logic** (uv bootstrap,
  webview-runtime detection, GPU branching, shortcut) with the heavy `uv tool install` step
  **stubbed**, and `actions/cache` for any wheels. GUI click-through is a manual gate; Linux GUI
  under `xvfb`. Estimated **~4 billed min/release** for v1.
- This keeps the matrix well inside the Free-tier allowance even at a healthy release cadence; the
  ×10 macOS multiplier only enters the picture when the macOS installer is built (future).

## 8. Explicitly out of scope (v1)

- Electron / Tauri (rejected — PyWebView fits the stack).
- **Browser-as-app shell** (running the user's Chromium in `--app` mode): rejected — depends on a
  Chromium-class browser being installed; desktop Firefox (a common Linux default) has no
  equivalent. The PWA manifest is still shipped as an optional power-user convenience (§3A).
- **Bundling our own Chromium** (isolated browser instance): rejected — ~150 MB Electron-weight
  plus a security-patch maintenance burden; an embedded webview gives the same isolation for free.
- Freezing torch/DocTR into a standalone installer (no ML bundling).
- Isolated multi-instance with separate data dirs.
- Unified single tray icon across all apps (per-app tray is the v1 default).
- Remote/Modal/GPU-server dispatch UI (design is forward-compatible; not built here).
- A device panel for the future "proofreading" app (it does not need one).
- **Windows (Inno `.exe`) and macOS (`.pkg`/`.app`) installers — deferred to future.** v1 ships
  the **Linux AppImage installer only**; the engine + wizard are built so those platforms slot in
  later (their CI runners + signing land with them).
- Auto-installing the NVIDIA driver or the CUDA toolkit (detect + guide only; the gated torch
  `cu12x` swap is the extent of automation).
- Code signing / notarization (macOS) and Authenticode (Windows): when those installers land they
  ship **unsigned** first, documenting the OS-trust workaround (Gatekeeper right-click-Open /
  SmartScreen "More info → Run anyway"). Signing is later work.

## 9. Decomposition & sequencing

1. `pdomain-ops`: `pd_ocr_ops.desktop.run_windowed` + lifecycle + single-instance + windowed
   `sibling_spawn`.
2. `pdomain-ops`: device endpoint + prefs schema + `LocalStageDispatcher` honoring the pref.
3. `pdomain-ops`: update control — `GET/POST /api/suite/update`, policy pref, editable-install
   refusal, rollback record, shell restart signal.
4. `pdomain-ui`: `<ComputeTargetPanel>` (local-mode-gated) + `<UpdatePanel>` + badge, release a
   minor version.
5. `pdomain-ocr-simple-gui` (pilot): bump deps, `--desktop`, `--update`, mount routes, render
   panels, fill shortcut stubs, ship PWA manifest.
6. Installer engine (gated CLI): prereq detection, `uv` bootstrap, webview runtime, `uv tool
   install`, GPU-torch swap (§7.3), shortcut/uninstall, `--update` path — plus the
   prerequisites/CUDA doc.
7. Linux **AppImage GUI wizard** over the engine + optional `.deb`; the `ubuntu-latest`
   release-matrix job with the lean stubbed smoke test (§7.4).
8. Windows + macOS installers (deferred): build on the same engine when prioritized.
9. Remaining apps inherit by bumping deps + generating their installers (separate, later work —
   not this spec).
