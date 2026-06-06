"""Desktop shortcut helpers — Linux implemented; macOS/Windows deferred (Phase 4)."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pdomain_ops.suite.types import InstalledApp

#: Known non-Linux platforms and their display names.
_NON_LINUX_PLATFORM_NAMES: dict[str, str] = {
    "darwin": "macOS",
    "win32": "Windows",
}


def _applications_dir() -> Path:
    """Return the XDG applications directory for .desktop files.

    Returns:
        Path to ``~/.local/share/applications`` (creating it if needed).
    """
    import platformdirs

    path = Path(platformdirs.user_data_dir()) / "applications"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _desktop_filename(app_id: str) -> str:
    """Return the .desktop filename for an app_id.

    Args:
        app_id: The application identifier.

    Returns:
        Filename like ``pdomain-<app_id>.desktop``.
    """
    return f"pdomain-{app_id}.desktop"


def install_shortcut(app: InstalledApp) -> None:
    """Install a .desktop shortcut for *app* on Linux.

    Writes a minimal XDG ``.desktop`` file to ``~/.local/share/applications/``.
    On macOS and Windows the function raises ``NotImplementedError`` (Phase 4
    deferred per the cross-cut design spec). Unknown platforms also raise
    ``NotImplementedError`` with an "unsupported platform" message.

    Args:
        app: The installed app to create a shortcut for.

    Raises:
        NotImplementedError: On any non-Linux platform.
    """
    plat = sys.platform
    if plat != "linux":
        if plat in _NON_LINUX_PLATFORM_NAMES:
            plat_name = _NON_LINUX_PLATFORM_NAMES[plat]
            raise NotImplementedError(
                f"Desktop shortcut install not yet implemented on {plat_name} "
                "(deferred to Phase 4 of the cross-cut design)"
            )
        raise NotImplementedError(
            f"Desktop shortcut install not supported on unsupported platform: {plat}"
        )

    display_name = app.display_name or app.app_id
    content = "\n".join(
        [
            "[Desktop Entry]",
            "Version=1.0",
            "Type=Application",
            f"Name={display_name}",
            # No --desktop flag: pd-* apps launch in browser mode by default
            # (start the server + open the system browser).  The native webview
            # window was retired (it conflicts with in-process OpenCV's Qt).
            f"Exec={shlex.quote(app.binary)}",
            f"Icon={app.app_id}",
            "Terminal=false",
            "Categories=Utility;",
            "",
        ]
    )
    dest = _applications_dir() / _desktop_filename(app.app_id)
    tmp = dest.with_suffix(".desktop.tmp")
    tmp.write_text(content, encoding="utf-8")
    _ = tmp.replace(dest)


def remove_shortcut(app_id: str) -> None:
    """Remove the .desktop shortcut for *app_id* on Linux.

    On macOS and Windows the function raises ``NotImplementedError`` (Phase 4
    deferred per the cross-cut design spec). Unknown platforms also raise
    ``NotImplementedError`` with an "unsupported platform" message.

    Args:
        app_id: The application identifier whose shortcut should be removed.

    Raises:
        NotImplementedError: On any non-Linux platform.
    """
    plat = sys.platform
    if plat != "linux":
        if plat in _NON_LINUX_PLATFORM_NAMES:
            plat_name = _NON_LINUX_PLATFORM_NAMES[plat]
            raise NotImplementedError(
                f"Desktop shortcut remove not yet implemented on {plat_name} "
                "(deferred to Phase 4 of the cross-cut design)"
            )
        raise NotImplementedError(
            f"Desktop shortcut remove not supported on unsupported platform: {plat}"
        )

    dest = _applications_dir() / _desktop_filename(app_id)
    dest.unlink(missing_ok=True)
