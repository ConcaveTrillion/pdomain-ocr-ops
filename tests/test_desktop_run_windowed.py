"""Tests for run_windowed choreography with injectable seams."""

from __future__ import annotations

import threading  # noqa: TC003 — used at runtime for threading.Event in test bodies

import pytest

from pdomain_ops.desktop import ShellDeps, run_windowed


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

    def _must_not_start(app_module: str, port: int) -> object:
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
    on_quit_captured: list[object] = []
    teardown_called: list[bool] = []
    tray_stopped: list[bool] = []

    def _run_tray(on_quit: object) -> None:
        # Capture the on_quit callback so the test can call it later.
        on_quit_captured.append(on_quit)

    def _open_window(url: str, title: str, quit_event: threading.Event) -> None:
        captured_quit_event.append(quit_event)
        # Simulate user triggering tray-Quit while the window is "open":
        # call the captured on_quit, which should set quit_event.
        assert on_quit_captured, "run_tray must be called before open_window"
        on_quit_captured[0]()  # type: ignore[operator]
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
