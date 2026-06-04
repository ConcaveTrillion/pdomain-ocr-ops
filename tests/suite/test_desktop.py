"""Tests for desktop shortcut helpers."""

import sys
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from pdomain_ops.suite.desktop import install_shortcut, remove_shortcut
from pdomain_ops.suite.types import InstalledApp

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _make_installed() -> InstalledApp:
    return InstalledApp(
        app_id="pdomain-app-a",
        package="pdomain_app_a",
        version="1.0.0",
        binary="/usr/bin/python3",
        default_port=8001,
        icon="test",
        display_name="pdomain-app-a",
        registered_at=_NOW,
    )


@pytest.mark.parametrize("platform", ["darwin", "win32"])
def test_install_shortcut_raises_not_implemented_on_non_linux(platform):
    """macOS and Windows still raise NotImplementedError (Phase 4 deferred)."""
    with patch.object(sys, "platform", platform):
        with pytest.raises(NotImplementedError) as exc_info:
            install_shortcut(_make_installed())
    msg = str(exc_info.value).lower()
    platform_aliases = {"darwin": "macos", "win32": "windows"}
    expected_platform_str = platform_aliases.get(platform, platform)
    assert expected_platform_str in msg or platform in msg
    assert "phase 4" in msg or "deferred" in msg


@pytest.mark.parametrize("platform", ["darwin", "win32"])
def test_remove_shortcut_raises_not_implemented_on_non_linux(platform):
    """macOS and Windows remove_shortcut still raises NotImplementedError (Phase 4 deferred)."""
    with patch.object(sys, "platform", platform), pytest.raises(NotImplementedError):
        remove_shortcut("pdomain-app-a")


def test_install_shortcut_unknown_platform_raises_generic():
    """Unknown platforms raise NotImplementedError with 'unsupported platform'."""
    with patch.object(sys, "platform", "aix"), pytest.raises(NotImplementedError) as exc_info:
        install_shortcut(_make_installed())
    assert "unsupported platform" in str(exc_info.value)


@pytest.mark.skipif(sys.platform != "linux", reason="linux shortcut only")
def test_install_shortcut_linux_writes_desktop_file(monkeypatch, tmp_path):
    """On Linux, install_shortcut writes a .desktop file."""
    monkeypatch.setattr("pdomain_ops.suite.desktop._applications_dir", lambda: tmp_path)
    app = _make_installed()
    install_shortcut(app)
    f = tmp_path / f"pdomain-{app.app_id}.desktop"
    assert f.exists()
    text = f.read_text()
    assert f"Exec={app.binary} --desktop" in text
    assert f"Name={app.display_name}" in text
    assert "Type=Application" in text
    assert "Terminal=false" in text


@pytest.mark.skipif(sys.platform != "linux", reason="linux shortcut only")
def test_remove_shortcut_linux_removes_desktop_file(monkeypatch, tmp_path):
    """On Linux, remove_shortcut deletes the .desktop file."""
    monkeypatch.setattr("pdomain_ops.suite.desktop._applications_dir", lambda: tmp_path)
    app = _make_installed()
    install_shortcut(app)
    f = tmp_path / f"pdomain-{app.app_id}.desktop"
    assert f.exists()
    remove_shortcut(app.app_id)
    assert not f.exists()


@pytest.mark.skipif(sys.platform != "linux", reason="linux shortcut only")
def test_remove_shortcut_linux_missing_ok(monkeypatch, tmp_path):
    """On Linux, remove_shortcut does not raise if the file doesn't exist."""
    monkeypatch.setattr("pdomain_ops.suite.desktop._applications_dir", lambda: tmp_path)
    remove_shortcut("nonexistent-app")  # should not raise
