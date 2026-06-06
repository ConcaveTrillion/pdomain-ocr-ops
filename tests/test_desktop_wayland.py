"""Unit tests for the _preferred_qt_platform helper.

All tests use pure dict inputs -- no GUI import, no os.environ mutation.
"""

from __future__ import annotations

from pdomain_ops.desktop import _preferred_qt_platform


class TestPreferredQtPlatform:
    """Tests for the _preferred_qt_platform env-detection helper."""

    # ------------------------------------------------------------------
    # Wayland detection paths
    # ------------------------------------------------------------------

    def test_wayland_via_xdg_session_type(self) -> None:
        """Returns 'wayland' when XDG_SESSION_TYPE is 'wayland'."""
        env = {"XDG_SESSION_TYPE": "wayland"}
        assert _preferred_qt_platform(env) == "wayland"

    def test_wayland_via_wayland_display(self) -> None:
        """Returns 'wayland' when WAYLAND_DISPLAY is set (non-empty)."""
        env = {"WAYLAND_DISPLAY": "wayland-0"}
        assert _preferred_qt_platform(env) == "wayland"

    def test_wayland_via_wayland_display_any_nonempty_value(self) -> None:
        """Returns 'wayland' for any non-empty WAYLAND_DISPLAY value."""
        env = {"WAYLAND_DISPLAY": "wayland-1"}
        assert _preferred_qt_platform(env) == "wayland"

    def test_both_wayland_signals_returns_wayland(self) -> None:
        """Returns 'wayland' when both XDG_SESSION_TYPE and WAYLAND_DISPLAY are set."""
        env = {"XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-0"}
        assert _preferred_qt_platform(env) == "wayland"

    # ------------------------------------------------------------------
    # Do not override an explicit user QT_QPA_PLATFORM
    # ------------------------------------------------------------------

    def test_explicit_qt_qpa_platform_returns_none(self) -> None:
        """Returns None when QT_QPA_PLATFORM is already set (do not override user choice)."""
        env = {
            "QT_QPA_PLATFORM": "xcb",
            "XDG_SESSION_TYPE": "wayland",
        }
        assert _preferred_qt_platform(env) is None

    def test_explicit_qt_qpa_platform_wayland_returns_none(self) -> None:
        """Returns None even if QT_QPA_PLATFORM is already 'wayland' (no double-set)."""
        env = {
            "QT_QPA_PLATFORM": "wayland",
            "XDG_SESSION_TYPE": "wayland",
            "WAYLAND_DISPLAY": "wayland-0",
        }
        assert _preferred_qt_platform(env) is None

    # ------------------------------------------------------------------
    # Non-Wayland / fallthrough paths -> None
    # ------------------------------------------------------------------

    def test_x11_session_type_returns_none(self) -> None:
        """Returns None on an X11 session (xcb handles it; no override)."""
        env = {"XDG_SESSION_TYPE": "x11"}
        assert _preferred_qt_platform(env) is None

    def test_tty_session_type_returns_none(self) -> None:
        """Returns None on a TTY session."""
        env = {"XDG_SESSION_TYPE": "tty"}
        assert _preferred_qt_platform(env) is None

    def test_empty_env_returns_none(self) -> None:
        """Returns None when no relevant env vars are present."""
        assert _preferred_qt_platform({}) is None

    def test_empty_xdg_session_type_returns_none(self) -> None:
        """Returns None when XDG_SESSION_TYPE is present but empty."""
        env = {"XDG_SESSION_TYPE": ""}
        assert _preferred_qt_platform(env) is None

    def test_empty_wayland_display_returns_none(self) -> None:
        """Returns None when WAYLAND_DISPLAY is present but empty."""
        env = {"WAYLAND_DISPLAY": ""}
        assert _preferred_qt_platform(env) is None

    def test_empty_qt_qpa_platform_does_not_block_wayland(self) -> None:
        """An empty QT_QPA_PLATFORM string is treated as unset (still returns 'wayland')."""
        env = {
            "QT_QPA_PLATFORM": "",
            "XDG_SESSION_TYPE": "wayland",
        }
        assert _preferred_qt_platform(env) == "wayland"
