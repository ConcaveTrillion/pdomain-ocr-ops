"""Unit tests for the Qt backend helpers in desktop.py.

Tests cover:
- _pyqt6_plugin_path: monkeypatched to a tmp dir
- _should_override_qt_plugin_path: pure predicate for all key cases

All tests are pure/unit -- no GUI import, no os.environ mutation.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path

from pdomain_ops.desktop import _pyqt6_plugin_path, _should_override_qt_plugin_path


class TestPyQt6PluginPath:
    """Tests for _pyqt6_plugin_path -- returns Qt6/plugins path or None."""

    def test_returns_path_when_pyqt6_present_and_plugins_dir_exists(self, tmp_path: Path) -> None:
        """Returns the Qt6/plugins dir when PyQt6 is importable and dir exists."""
        # Simulate PyQt6 installed at tmp_path/PyQt6/__init__.py
        pyqt6_dir = tmp_path / "PyQt6"
        pyqt6_dir.mkdir()
        (pyqt6_dir / "__init__.py").write_text("")
        plugins_dir = pyqt6_dir / "Qt6" / "plugins"
        plugins_dir.mkdir(parents=True)

        fake_spec = importlib.util.spec_from_file_location("PyQt6", pyqt6_dir / "__init__.py")

        with patch("importlib.util.find_spec", return_value=fake_spec):
            result = _pyqt6_plugin_path()

        assert result == str(plugins_dir)

    def test_returns_none_when_pyqt6_absent(self) -> None:
        """Returns None when PyQt6 is not installed (find_spec returns None)."""
        with patch("importlib.util.find_spec", return_value=None):
            result = _pyqt6_plugin_path()

        assert result is None

    def test_returns_none_when_plugins_dir_does_not_exist(self, tmp_path: Path) -> None:
        """Returns None when PyQt6 is importable but Qt6/plugins subdir is missing."""
        pyqt6_dir = tmp_path / "PyQt6"
        pyqt6_dir.mkdir()
        (pyqt6_dir / "__init__.py").write_text("")
        # No Qt6/plugins subdir created

        fake_spec = importlib.util.spec_from_file_location("PyQt6", pyqt6_dir / "__init__.py")

        with patch("importlib.util.find_spec", return_value=fake_spec):
            result = _pyqt6_plugin_path()

        assert result is None

    def test_returns_none_when_spec_has_no_origin(self) -> None:
        """Returns None when the spec exists but has no origin (namespace package)."""

        class _FakeSpec:
            origin: Any = None

        with patch("importlib.util.find_spec", return_value=_FakeSpec()):
            result = _pyqt6_plugin_path()

        assert result is None

    def test_does_not_raise_when_find_spec_raises(self) -> None:
        """Returns None (no raise) if find_spec raises ModuleNotFoundError."""
        with patch("importlib.util.find_spec", side_effect=ModuleNotFoundError):
            result = _pyqt6_plugin_path()

        assert result is None


class TestShouldOverrideQtPluginPath:
    """Tests for _should_override_qt_plugin_path -- pure predicate."""

    # Override cases (True)

    def test_none_returns_true(self) -> None:
        """Returns True when the current value is None (unset)."""
        assert _should_override_qt_plugin_path(None) is True

    def test_empty_string_returns_true(self) -> None:
        """Returns True when the current value is an empty string."""
        assert _should_override_qt_plugin_path("") is True

    def test_cv2_path_returns_true(self) -> None:
        """Returns True when the path is OpenCV's bundled plugin dir."""
        assert (
            _should_override_qt_plugin_path(
                "/home/user/.local/lib/python3.11/site-packages/cv2/qt/plugins"
            )
            is True
        )

    def test_cv2_substring_returns_true(self) -> None:
        """Returns True for any path containing 'cv2'."""
        assert _should_override_qt_plugin_path("/x/site-packages/cv2/qt/plugins") is True

    def test_cv2_in_middle_returns_true(self) -> None:
        """Returns True when 'cv2' appears anywhere in the path."""
        assert _should_override_qt_plugin_path("/opt/venv/cv2/someplugins") is True

    # Do NOT override cases (False)

    def test_custom_user_path_returns_false(self) -> None:
        """Returns False for a user-configured path without 'cv2'."""
        assert _should_override_qt_plugin_path("/home/me/custom/qt/plugins") is False

    def test_pyqt6_path_returns_false(self) -> None:
        """Returns False when the path already points to PyQt6's plugins."""
        assert (
            _should_override_qt_plugin_path(
                "/home/user/.local/lib/python3.11/site-packages/PyQt6/Qt6/plugins"
            )
            is False
        )

    def test_system_qt_path_returns_false(self) -> None:
        """Returns False for a system Qt plugins path."""
        assert _should_override_qt_plugin_path("/usr/lib/x86_64-linux-gnu/qt6/plugins") is False

    def test_arbitrary_nonempty_no_cv2_returns_false(self) -> None:
        """Returns False for any non-empty, non-cv2 path."""
        assert _should_override_qt_plugin_path("/opt/qt/plugins") is False
