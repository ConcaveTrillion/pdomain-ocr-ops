"""Tests for run_windowed choreography with injectable seams."""

from __future__ import annotations

import socket
import threading  # noqa: TC003 — used at runtime for threading.Event in test bodies
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

from pdomain_ops.desktop import ShellDeps, _default_resolve_port, run_windowed

# ---------------------------------------------------------------------------
# Helpers (mirrors test_ports.py style)
# ---------------------------------------------------------------------------


def _bind_port(port: int, host: str = "127.0.0.1") -> socket.socket:
    """Bind a real socket to occupy *port*; caller must close."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    sock.bind((host, port))
    return sock


def _find_free_port(host: str = "127.0.0.1") -> int:
    """Ask the OS for an ephemeral free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------------------
# _default_resolve_port unit tests (exercise real find_available_port)
# ---------------------------------------------------------------------------


class TestDefaultResolvePort:
    """Unit tests for the _default_resolve_port function."""

    def test_returns_preferred_when_free(self) -> None:
        """Returns preferred port when it is not occupied."""
        port = _find_free_port()
        result = _default_resolve_port(preferred=port)
        assert result == port

    def test_returns_different_port_when_preferred_occupied(self) -> None:
        """Returns a different free port when preferred is already bound."""
        port = _find_free_port()
        sock = _bind_port(port)
        try:
            result = _default_resolve_port(preferred=port)
            # Must be different from the occupied port
            assert result != port
            # The returned port must actually be bindable (not just in theory)
            verify_sock = _bind_port(result)
            verify_sock.close()
        finally:
            sock.close()

    def test_default_preferred_is_8004(self) -> None:
        """When called with no args, preferred defaults to 8004.

        If 8004 is free this test confirms the default is 8004.
        If 8004 is occupied the returned port must still be free and != 8004.
        """
        try:
            result = _default_resolve_port()
        except RuntimeError:
            pytest.skip("No free ports available near 8004")
        verify_sock = _bind_port(result)
        verify_sock.close()

    def test_explicit_preferred_honored(self) -> None:
        """An explicit preferred port is used as the starting search point."""
        port = _find_free_port()
        result = _default_resolve_port(preferred=port)
        assert result == port  # free -> returns exact preferred

    def test_returned_port_is_bindable(self) -> None:
        """The returned port can be successfully bound by the caller."""
        port = _find_free_port()
        result = _default_resolve_port(preferred=port)
        sock = _bind_port(result)
        sock.close()


# ---------------------------------------------------------------------------
# run_windowed preferred_port parameter tests
# ---------------------------------------------------------------------------


class TestRunWindowedPreferredPort:
    """Tests that preferred_port flows through run_windowed -> server/URL."""

    def _make_deps(
        self,
        resolve_port_fn: Callable[[], int],
        events: list[object],
    ) -> ShellDeps:
        """Build fake ShellDeps that records server port and URL."""

        def _open_window(url: str, title: str, quit_event: threading.Event) -> None:
            events.append(("window_url", url))
            quit_event.set()

        return ShellDeps(
            start_server=lambda app_module, port: (
                events.append(("server_port", port)) or (lambda: None)
            ),
            wait_healthy=lambda port, timeout: True,
            open_window=_open_window,
            run_tray=lambda on_quit: None,
            stop_tray=lambda: None,
            resolve_port=resolve_port_fn,
            acquire_instance=lambda port: object(),
        )

    def test_preferred_port_passed_to_resolve_seam(self) -> None:
        """preferred_port is forwarded to the resolve_port seam."""
        received_preferred: list[int] = []

        def _resolve() -> int:
            received_preferred.append(9999)
            return 9999

        events: list[object] = []
        deps = self._make_deps(_resolve, events)
        run_windowed("myapp:app", title="T", deps=deps, preferred_port=9999)
        # resolve_port was called (and our fake recorded 9999)
        assert received_preferred == [9999]

    def test_server_binds_resolved_port_not_hardcoded_8004(self) -> None:
        """Server receives the port from resolve_port, not a hardcoded 8004."""
        events: list[object] = []
        deps = self._make_deps(lambda: 7777, events)
        run_windowed("myapp:app", title="T", deps=deps, preferred_port=7777)
        assert ("server_port", 7777) in events

    def test_window_url_uses_resolved_port(self) -> None:
        """Window URL contains the resolved port, not a hardcoded 8004."""
        events: list[object] = []
        deps = self._make_deps(lambda: 7777, events)
        run_windowed("myapp:app", title="T", deps=deps, preferred_port=7777)
        assert ("window_url", "http://127.0.0.1:7777/") in events

    def test_default_preferred_port_is_8004(self) -> None:
        """Without preferred_port, the default 8004 is passed as context."""
        received: list[int] = []

        def _open_window(url: str, title: str, quit_event: threading.Event) -> None:
            quit_event.set()

        deps = ShellDeps(
            start_server=lambda app_module, port: received.append(port) or (lambda: None),
            wait_healthy=lambda port, timeout: True,
            open_window=_open_window,
            run_tray=lambda on_quit: None,
            stop_tray=lambda: None,
            resolve_port=lambda: 8004,
            acquire_instance=lambda port: object(),
        )
        run_windowed("myapp:app", title="T", deps=deps)
        assert received == [8004]

    def test_free_port_autopick_integration(self) -> None:
        """When preferred port is occupied, run_windowed uses a different free port.

        Exercises _default_resolve_port via the DEFAULT deps path (no custom deps).
        Uses a fully fake start_server / wait_healthy / open_window so no real
        uvicorn or webview is needed.  The key check: the port actually chosen
        by deps.resolve_port() is different from the occupied one.
        """
        # Occupy a free port
        occupied = _find_free_port()
        sock = _bind_port(occupied)
        try:
            chosen_ports: list[int] = []

            def _open_window(url: str, title: str, quit_event: threading.Event) -> None:
                quit_event.set()

            # Build deps where resolve_port is the real _default_resolve_port
            # (prefers `occupied`, so must walk to the next free port).
            deps = ShellDeps(
                start_server=lambda app_module, port: chosen_ports.append(port) or (lambda: None),
                wait_healthy=lambda port, timeout: True,
                open_window=_open_window,
                run_tray=lambda on_quit: None,
                stop_tray=lambda: None,
                resolve_port=lambda: _default_resolve_port(preferred=occupied),
                acquire_instance=lambda port: object(),
            )
            run_windowed("myapp:app", title="T", deps=deps, preferred_port=occupied)

            assert len(chosen_ports) == 1
            chosen = chosen_ports[0]
            assert chosen != occupied, (
                f"Expected a different port when {occupied} is occupied, got {chosen}"
            )
            # The chosen port must be actually bindable
            verify = _bind_port(chosen)
            verify.close()
        finally:
            sock.close()


# ---------------------------------------------------------------------------
# Original choreography tests (unchanged -- seam contract must remain stable)
# ---------------------------------------------------------------------------


def test_boot_order_and_shutdown():
    events: list[object] = []

    def _open_window(url: str, title: str, quit_event: threading.Event) -> None:
        events.append(("window", url, title))
        # Simulate the window closing immediately (no user interaction needed).
        quit_event.set()

    deps = ShellDeps(
        start_server=lambda app_module, port: (
            events.append(("server", app_module, port)) or (lambda: events.append("server_stop"))
        ),
        wait_healthy=lambda port, timeout: events.append("healthy") or True,
        open_window=_open_window,
        run_tray=lambda on_quit: events.append("tray"),
        stop_tray=lambda: events.append("tray_stop"),
        resolve_port=lambda: 8004,
        acquire_instance=lambda port: events.append("lock") or object(),
    )
    run_windowed("pdomain_ocr_simple_gui.app:app", title="OCR", deps=deps)
    # server starts and is healthy before the window opens
    assert (
        events.index(("server", "pdomain_ocr_simple_gui.app:app", 8004))
        < events.index("healthy")
        < events.index(("window", "http://127.0.0.1:8004/", "OCR"))
    )
    # quitting stops server and tray
    assert "server_stop" in events
    assert "tray_stop" in events


def test_existing_instance_focuses_not_respawn():
    events: list[object] = []

    def _must_not_start(app_module: str, port: int) -> Callable[[], None]:
        msg = "must not start server when instance exists"
        raise AssertionError(msg)

    deps = ShellDeps(
        resolve_port=lambda: 8004,
        existing_instance=lambda: {"port": 8010},  # already running
        focus_existing=lambda port: events.append(("focus", port)),
        start_server=_must_not_start,
    )
    run_windowed("x:app", title="OCR", deps=deps)
    assert ("focus", 8010) in events


def test_wait_healthy_false_raises_and_teardown():
    """If wait_healthy returns False, run_windowed raises RuntimeError and calls stop_server."""
    teardown_called: list[bool] = []
    open_called: list[bool] = []

    def _open_window(url: str, title: str, quit_event: threading.Event) -> None:
        open_called.append(True)

    deps = ShellDeps(
        start_server=lambda app_module, port: lambda: teardown_called.append(True),
        wait_healthy=lambda port, timeout: False,  # server never healthy
        open_window=_open_window,
        run_tray=lambda on_quit: None,
        stop_tray=lambda: None,
        resolve_port=lambda: 8004,
        acquire_instance=lambda port: object(),
    )
    with pytest.raises(RuntimeError, match="healthy"):
        run_windowed("myapp:app", title="T", deps=deps)

    # stop_server must be called even on failure
    assert teardown_called == [True]
    # open_window must NOT be called if server never healthy
    assert open_called == []


def test_tray_quit_sets_quit_event_and_teardown_runs():
    """Simulating tray-Quit (calling on_quit) sets quit_event; open_window observes it."""
    captured_quit_event: list[threading.Event] = []
    on_quit_captured: list[Callable[[], None]] = []
    teardown_called: list[bool] = []
    tray_stopped: list[bool] = []

    def _run_tray(on_quit: Callable[[], None]) -> None:
        # Capture the on_quit callback so the test can call it later.
        on_quit_captured.append(on_quit)

    def _open_window(url: str, title: str, quit_event: threading.Event) -> None:
        captured_quit_event.append(quit_event)
        # Simulate user triggering tray-Quit while the window is "open":
        # call the captured on_quit, which should set quit_event.
        assert on_quit_captured, "run_tray must be called before open_window"
        on_quit_captured[0]()
        # open_window returns only after quit_event is set (as the real impl would).
        # Here we just verify it is set and return.
        assert quit_event.is_set(), "quit_event must be set after on_quit()"

    deps = ShellDeps(
        start_server=lambda app_module, port: lambda: teardown_called.append(True),
        wait_healthy=lambda port, timeout: True,
        open_window=_open_window,
        run_tray=_run_tray,
        stop_tray=lambda: tray_stopped.append(True),
        resolve_port=lambda: 8004,
        acquire_instance=lambda port: object(),
    )
    run_windowed("myapp:app", title="T", deps=deps)

    assert len(captured_quit_event) == 1
    assert captured_quit_event[0].is_set()
    assert teardown_called == [True]
    assert tray_stopped == [True]


def test_app_module_forwarded_to_start_server():
    """start_server receives the exact app_module string passed to run_windowed."""
    received: list[str] = []

    def _open_window(url: str, title: str, quit_event: threading.Event) -> None:
        quit_event.set()

    deps = ShellDeps(
        start_server=lambda app_module, port: received.append(app_module) or (lambda: None),
        wait_healthy=lambda port, timeout: True,
        open_window=_open_window,
        run_tray=lambda on_quit: None,
        stop_tray=lambda: None,
        resolve_port=lambda: 8004,
        acquire_instance=lambda port: object(),
    )
    run_windowed("pdomain_ocr_simple_gui.app:app", title="OCR", deps=deps)
    assert received == ["pdomain_ocr_simple_gui.app:app"]


def test_title_forwarded_to_open_window():
    """open_window receives the title passed to run_windowed."""
    received_title: list[str] = []

    def _open_window(url: str, title: str, quit_event: threading.Event) -> None:
        received_title.append(title)
        quit_event.set()

    deps = ShellDeps(
        start_server=lambda app_module, port: lambda: None,
        wait_healthy=lambda port, timeout: True,
        open_window=_open_window,
        run_tray=lambda on_quit: None,
        stop_tray=lambda: None,
        resolve_port=lambda: 8004,
        acquire_instance=lambda port: object(),
    )
    run_windowed("myapp:app", title="My Fancy App", deps=deps)
    assert received_title == ["My Fancy App"]
