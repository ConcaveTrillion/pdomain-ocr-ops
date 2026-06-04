"""Tests for run_windowed choreography with injectable seams."""

from __future__ import annotations

from pdomain_ops.desktop import ShellDeps, run_windowed


def test_boot_order_and_shutdown():
    events: list[object] = []

    deps = ShellDeps(
        start_server=lambda port: (
            events.append(("server", port)) or (lambda: events.append("server_stop"))
        ),
        wait_healthy=lambda port, timeout: events.append("healthy") or True,
        open_window=lambda url: events.append(("window", url)),
        run_tray=lambda on_quit: events.append("tray"),
        stop_tray=lambda: events.append("tray_stop"),
        resolve_port=lambda: 8004,
        acquire_instance=lambda port: events.append("lock") or object(),
    )
    run_windowed("pdomain_ocr_simple_gui.app:app", title="OCR", deps=deps)
    # server starts and is healthy before the window opens
    assert (
        events.index(("server", 8004))
        < events.index("healthy")
        < events.index(("window", "http://127.0.0.1:8004/"))
    )
    # quitting stops server and tray
    assert "server_stop" in events
    assert "tray_stop" in events


def test_existing_instance_focuses_not_respawn():
    events: list[object] = []

    def _must_not_start(port: int) -> object:
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
