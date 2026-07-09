# Reminder — desktop launcher integration for pd-* apps

Created during the `cross-cut` brainstorm (2026-05-16). Stubbed in the
cross-cut design as a known capability but deferred from the first pdomain-ui /
pdomain-ops release.

## What we want

Each end-user pd-* app should be able to install itself as a platform-native
launcher entry — Linux `.desktop` file, macOS `.app` bundle or Dock icon,
Windows Start Menu shortcut + Taskbar pin — so a user can click an icon
without remembering the CLI command.

## Design constraint (from cross-cut)

- Apps are installed by `uv tool install <app>`. The Python wheel must bundle
  all icon assets it needs (PNG at multiple resolutions, `.ico` for Windows,
  `.icns` for macOS).
- The shortcut install is **opt-in**, not done on first-run automatically.
  Each app's CLI exposes `--install-desktop-shortcut` and
  `--remove-desktop-shortcut`.
- The cross-platform shortcut logic belongs in **`pdomain-ops`** under
  `pd_ocr_ops.suite.desktop` so every pd-* SPA calls the same helper. The
  helper detects platform and writes the right artifact.

## Stub plan

Ship a stub in the first `pdomain-ops` release:
- `pd_ocr_ops.suite.desktop.install_shortcut(app_meta)` — raises
  `NotImplementedError` with a clear message naming the missing platform
  implementation. Apps wire the CLI flag; runtime tells the user "desktop
  shortcut install not yet supported on this platform — coming soon."
- Stubs let app authors wire the CLI surface now without blocking on the
  platform code.

## Real implementation (deferred)

Three platform back-ends behind the same interface:

| Platform | Artifact | Location |
|----------|----------|----------|
| Linux | `.desktop` file + hicolor icons | `~/.local/share/applications/`, `~/.local/share/icons/hicolor/<size>/apps/` |
| macOS | `.app` bundle wrapper (or use `pyobjc`-built bundle) | `~/Applications/` |
| Windows | `.lnk` + `.ico` | `%APPDATA%/Microsoft/Windows/Start Menu/Programs/`, optional pin |

The shortcut points to the `uv tool` shim binary (already on PATH after
install). No PyInstaller, no Electron, no native bundling beyond writing the
right file with the right metadata.

## Icon asset standards

Each pd-* SPA ships `<repo>/icons/`:
- `icon-1024.png` (master)
- `icon-512.png`, `256.png`, `128.png`, `64.png`, `32.png`, `16.png`
- `icon.ico` (Windows multi-resolution)
- `icon.icns` (macOS)
- All checked into the repo; wheel includes them via `[tool.setuptools.package-data]`

A stub icon set (a placeholder glyph + the app's display name) is acceptable
for the first release of each app. Real artwork can land later.

## Related items

- pdomain-ui's `pd-suite.json` manifest already references `icon` per app — the
  desktop launcher reuses the same icon files.
- The launcher's tile in any pd-* AppShell pulls from the same `icons/` dir
  (served by the app's FastAPI backend at `/api/icons/<size>`).
