"""Version-check, editable-install guard, and gated upgrade for pdomain-ops."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from packaging.version import Version

if TYPE_CHECKING:
    from collections.abc import Callable


# ---------------------------------------------------------------------------
# Version comparison helpers (no network)
# ---------------------------------------------------------------------------


def _normalise(dist_name: str) -> str:
    """Normalise distribution name: replace - and _ with [_-] for regex."""
    return re.sub(r"[-_]", r"[-_]", dist_name)


def parse_index_versions(html: str, dist_name: str) -> list[str]:
    """Extract ordered version strings from a PEP 503 simple-index HTML page.

    Parameters
    ----------
    html:
        Raw HTML text of the simple-index page.
    dist_name:
        Distribution name, e.g. ``"pdomain-ocr-simple-gui"``.

    Returns:
    -------
    list[str]
        Version strings in document order (not sorted).
    """
    # Wheel filename: <dist_name>-<version>-<pyver>-<abi>-<platform>.whl
    # Distribution name normalisation: - and _ are interchangeable.
    norm = _normalise(dist_name)
    pattern = re.compile(
        rf'href="[^"]*{norm}-([^-]+(?:\.[^-]+)*)-[^"]*\.whl"',
        re.IGNORECASE,
    )
    return pattern.findall(html)


def compare_versions(*, current: str, latest: str) -> bool:
    """Return True when *latest* is strictly newer than *current*.

    Parameters
    ----------
    current:
        The installed version string.
    latest:
        The latest available version string.
    """
    return Version(latest) > Version(current)


# ---------------------------------------------------------------------------
# Network version check (injectable fetch seam)
# ---------------------------------------------------------------------------


def check_latest(
    dist_name: str,
    index_url: str,
    *,
    fetch: Callable[[str], Any] | None = None,
) -> dict[str, object]:
    """Query the PEP 503 index for the latest release of *dist_name*.

    Parameters
    ----------
    dist_name:
        Distribution name, e.g. ``"pdomain-ocr-simple-gui"``.
    index_url:
        Base URL of the simple index, e.g.
        ``"https://concavetrillion.github.io/pdomain-index-pip/simple"``.
    fetch:
        Injectable HTTP GET callable.  Defaults to ``httpx.get``.
        Must accept a URL string and return an object with ``.text`` and
        ``.raise_for_status()``.

    Returns:
    -------
    dict
        Keys: ``current``, ``latest``, ``update_available``, ``changelog_url``,
        ``channel``.  On network/parse failure returns ``update_available=False``.
    """
    import importlib.metadata

    try:
        current = importlib.metadata.version(dist_name)
    except importlib.metadata.PackageNotFoundError:
        current = "unknown"

    # Offline / error-safe sentinel
    _safe: dict[str, object] = {
        "current": current,
        "latest": current,
        "update_available": False,
        "changelog_url": None,
        "channel": "stable",
    }

    if fetch is None:
        try:
            import httpx

            fetch = httpx.get
        except ImportError:  # pragma: no cover
            return _safe

    # Normalise index URL: strip trailing slash, add the dist slug
    base = index_url.rstrip("/")
    norm_name = dist_name.lower().replace("_", "-")
    url = f"{base}/{norm_name}/"

    try:
        resp = fetch(url)
        resp.raise_for_status()
        versions = parse_index_versions(resp.text, dist_name)
        if not versions:
            return _safe
        latest = max(versions, key=Version)
        update_available = compare_versions(current=current, latest=latest)
    except Exception:  # noqa: BLE001
        return _safe
    else:
        return {
            "current": current,
            "latest": latest,
            "update_available": update_available,
            "changelog_url": f"{base}/{norm_name}/",
            "channel": "stable",
        }


# ---------------------------------------------------------------------------
# Editable-install detection
# ---------------------------------------------------------------------------


def is_editable_install(dist_name: str) -> bool:
    """Return True if *dist_name* is installed in editable / local-dev mode.

    Two detection paths:
    1. ``.venv/.pd-local-mode`` marker file in the active venv.
    2. ``direct_url.json`` in the dist-info directory flags editable install
       via ``importlib.metadata``.
    """
    import importlib.metadata
    import sys

    # Check .venv/.pd-local-mode marker
    venv = Path(sys.prefix)
    if (venv / ".pd-local-mode").exists():
        return True

    # Check importlib.metadata direct_url.json for editable flag
    try:
        dist = importlib.metadata.distribution(dist_name)
        # direct_url.json is part of the dist-info when installed editable
        # read_text returns None on missing file — never raises FileNotFoundError
        direct_url_text = dist.read_text("direct_url.json")
        if direct_url_text:
            direct_url = json.loads(direct_url_text)
            # PEP 610: editable installs have dir_info.editable = True
            dir_info = direct_url.get("dir_info", {})
            if dir_info.get("editable", False):
                return True
    except Exception:  # noqa: BLE001, S110  # best-effort: assume not editable on any metadata error
        pass

    return False


# ---------------------------------------------------------------------------
# Rollback path helper
# ---------------------------------------------------------------------------


def _rollback_path(dist_name: str) -> Path:
    """Return the path where the previous version is recorded before upgrade."""
    from platformdirs import user_data_dir

    data_dir = Path(user_data_dir("pd-suite"))
    data_dir.mkdir(parents=True, exist_ok=True)
    safe_name = dist_name.replace("-", "_")
    return data_dir / f"{safe_name}_rollback.json"


def installed_version(dist_name: str) -> str:
    """Return the currently installed version of *dist_name*."""
    import importlib.metadata

    try:
        return importlib.metadata.version(dist_name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


# ---------------------------------------------------------------------------
# Editable-install guard error
# ---------------------------------------------------------------------------


class EditableInstallError(RuntimeError):
    """Raised when an upgrade is requested on an editable / local-dev install."""


# ---------------------------------------------------------------------------
# Gated upgrade + rollback record
# ---------------------------------------------------------------------------


def apply_upgrade(
    dist_name: str,
    *,
    run: Callable[..., Any] | None = None,
) -> None:
    """Run ``uv tool upgrade <dist_name>`` with safety guards.

    Parameters
    ----------
    dist_name:
        Distribution name, e.g. ``"pdomain-ocr-simple-gui"``.
    run:
        Injectable subprocess runner.  Defaults to ``subprocess.run``.

    Raises:
    ------
    EditableInstallError
        When the distribution is detected as an editable / local-dev install.
    """
    if is_editable_install(dist_name):
        raise EditableInstallError(
            f"Refusing to upgrade editable/local-dev install of {dist_name!r}. "
            "Uninstall the editable install first, then use 'uv tool install'."
        )

    if run is None:
        run = subprocess.run

    # Record the previous version for rollback before upgrading
    prev_version = installed_version(dist_name)
    rollback_file = _rollback_path(dist_name)
    rollback_file.write_text(
        json.dumps({"dist_name": dist_name, "previous_version": prev_version}),
        encoding="utf-8",
    )

    cmd = ["uv", "tool", "upgrade", dist_name]
    run(cmd, check=True)
