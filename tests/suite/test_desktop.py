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


@pytest.mark.skipif(sys.platform != "linux", reason="linux shortcut only")
def test_install_shortcut_exec_quoted(monkeypatch, tmp_path):
    """Exec line in .desktop file uses shlex.quote so paths with spaces are safe."""
    monkeypatch.setattr("pdomain_ops.suite.desktop._applications_dir", lambda: tmp_path)
    app = InstalledApp(
        app_id="pdomain-app-b",
        package="pdomain_app_b",
        version="1.0.0",
        binary="/usr/local/bin/my app",  # space in path
        default_port=8002,
        icon="test",
        display_name="My App",
        registered_at=_NOW,
    )
    install_shortcut(app)
    f = tmp_path / "pdomain-pdomain-app-b.desktop"
    text = f.read_text()
    # shlex.quote wraps paths with spaces in single quotes; no --desktop flag
    # (apps launch browser mode by default — the native webview was retired).
    assert "Exec='/usr/local/bin/my app'\n" in text
    assert "--desktop" not in text


@pytest.mark.skipif(sys.platform != "linux", reason="linux shortcut only")
def test_install_shortcut_atomic_write(monkeypatch, tmp_path):
    """install_shortcut writes via a temp file then replaces (no partial writes visible)."""
    monkeypatch.setattr("pdomain_ops.suite.desktop._applications_dir", lambda: tmp_path)
    app = _make_installed()
    install_shortcut(app)
    dest = tmp_path / f"pdomain-{app.app_id}.desktop"
    # The temp file must be gone after a successful write.
    tmp = dest.with_suffix(".desktop.tmp")
    assert not tmp.exists(), "temp file must be cleaned up after atomic replace"
    assert dest.exists()


@pytest.mark.skipif(sys.platform != "linux", reason="linux shortcut only")
def test_install_shortcut_display_name_direct(monkeypatch, tmp_path):
    """Name= in .desktop uses app.display_name directly (no getattr fallback needed for typed field)."""
    monkeypatch.setattr("pdomain_ops.suite.desktop._applications_dir", lambda: tmp_path)
    app = _make_installed()
    install_shortcut(app)
    f = tmp_path / f"pdomain-{app.app_id}.desktop"
    text = f.read_text()
    assert f"Name={app.display_name}" in text


@pytest.mark.skipif(sys.platform != "linux", reason="linux shortcut only")
def test_install_shortcut_empty_display_name_falls_back_to_app_id(monkeypatch, tmp_path):
    """When display_name is empty string, fallback to app_id in the Name= field."""
    monkeypatch.setattr("pdomain_ops.suite.desktop._applications_dir", lambda: tmp_path)
    app = InstalledApp(
        app_id="pdomain-app-c",
        package="pdomain_app_c",
        version="1.0.0",
        binary="/usr/bin/ocr",
        default_port=8003,
        icon="test",
        display_name="",  # empty — should fall back to app_id
        registered_at=_NOW,
    )
    install_shortcut(app)
    f = tmp_path / "pdomain-pdomain-app-c.desktop"
    text = f.read_text()
    assert "Name=pdomain-app-c" in text
