---
Status: built
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-13
Kind: architecture
---

# Shared suite services

## Agent Index

- **Kind:** architecture
- **Status:** built
- **Read when:** changing suite device or update routes, desktop launch helpers,
  preferences, single-instance behavior, shared paths, or public schemas.
- **Search terms:** suite services, device routes, update routes, desktop,
  single instance, shared paths, schema emitter.

## Device and preference boundary

The device service exposes `GET` and `PUT /api/suite/device`. In local mode,
`GET` reports discovered devices and resolves the effective target in this
order: application override, suite default, then automatic selection. `PUT`
sets or clears an application or suite preference. Outside local mode, the
route reports the mode without enumerating or mutating local hardware.

Device discovery reports CPU, CUDA, and Apple MPS availability through shared
models. Local stage dispatch consumes the resolved target; the route does not
run OCR itself.

## Update boundary

The update service exposes `GET` and `POST /api/suite/update`. `GET` compares
the installed distribution with the configured pdomain index. `POST` runs the
guarded upgrade and returns `restart_required`. Editable installs are rejected
with HTTP 409, and subprocess upgrade failures surface as HTTP 502. The caller
owns restart UX and policy such as notify, automatic, or manual updates.

The update API is not a background package manager. It does not silently
upgrade an editable checkout, and it does not restart an application inside
the route.

## Desktop and single-instance boundary

The desktop module provides launch choreography with injectable seams for
server startup, health checking, browser or window opening, tray integration,
port resolution, and single-instance acquisition. Suite helpers create and
remove Linux XDG shortcuts. Shortcut commands launch the application binary in
its default browser mode.

Single-instance state is a locked JSON pidfile outside the installed-app
registry. Reads reap corrupt or dead-process files while treating a
permission-denied PID probe as evidence that the process is alive.

Linux shortcuts are the only shipped platform shortcut implementation. macOS
and Windows shortcut functions raise `NotImplementedError`. The package still
contains optional native window seams, but it does not require one desktop UI
transport or claim that pywebview, Qt, or AppImage is the suite-wide frontend.

## Path and schema boundaries

Named filesystem exchange and DocTR export manifests are defined in
[`shared-paths-and-export-manifest.md`](shared-paths-and-export-manifest.md).
The public schema emitter is the supported producer boundary for shared API and
manifest models. Applications own their product-specific schemas and decide
which shared paths they publish.

## Evidence

- **Code:** `pdomain_ops/suite/device_routes.py`,
  `pdomain_ops/suite/device_prefs.py`, `pdomain_ops/gpu/device_probe.py`,
  `pdomain_ops/suite/update.py`, `pdomain_ops/suite/update_routes.py`,
  `pdomain_ops/desktop.py`, `pdomain_ops/suite/desktop.py`,
  `pdomain_ops/suite/single_instance.py`, `pdomain_ops/suite/shared_paths.py`,
  `pdomain_ops/schemas/emit.py`
- **Tests:** `tests/suite/test_device_routes.py`,
  `tests/suite/test_device_prefs.py`, `tests/suite/test_update_check.py`,
  `tests/suite/test_update_apply.py`, `tests/suite/test_update_routes.py`,
  `tests/test_desktop_run_windowed.py`, `tests/suite/test_desktop.py`,
  `tests/suite/test_single_instance.py`, `tests/suite/test_shared_paths.py`,
  `tests/test_schemas_emit.py`
- **Salvaged sources:**
  `_tbd/ocr-container-docs/specs/2026-06-04-pd-suite-desktop-shell-design.md`,
  `_tbd/ocr-container-docs/plans/2026-06-04-pd-suite-desktop-shell-plan.md`,
  `_tbd/ocr-container-docs/runbooks/desktop-launcher-integration.md`,
  `_tbd/ocr-container-docs/plans/2026-06-10-trainer-spa-next-arc.md`
- **Verified:** 2026-07-13 against the current code and focused tests above.
