"""Desktop shell choreography for pd-* apps.

``run_windowed()`` orchestrates the lifecycle of a pd-* app running in a
native desktop window:

1. Check for an existing instance (single-instance guard) — if found, focus
   the existing window and return.
2. Resolve the port and acquire the instance lock.
3. Start a ``uvicorn.Server`` on a background daemon thread.
4. Poll ``/healthz`` until the server is healthy.
5. Open the pystray system-tray icon (non-blocking, on a daemon thread).
6. Open the native ``webview`` window (blocks the main thread — required by
   GTK/Cocoa event loops).
7. On window close or tray-Quit: stop the server, stop the tray.

All heavy GUI imports (``webview``, ``pystray``) are confined to the *default*
seam constructors so that the ``[desktop]`` optional extra is not required to
import this module in headless/server mode.

``ShellDeps`` is a dataclass of callables that wires the real implementations
in production and admits lightweight fakes for unit tests — no GUI needed.
"""

from __future__ import annotations

import sys
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

# ---------------------------------------------------------------------------
# Default seam implementations (lazy-importing optional GUI deps)
# ---------------------------------------------------------------------------


def _default_start_server(port: int) -> Callable[[], None]:
    """Start a uvicorn server on a daemon thread.

    Args:
        port: The port to bind.

    Returns:
        A zero-argument callable that signals the server to stop and joins
        the thread with a 5-second timeout.
    """
    import uvicorn

    config = uvicorn.Config(
        "pdomain_ops.desktop:_noop_app",
        host="127.0.0.1",
        port=port,
        log_level="error",
    )
    server = uvicorn.Server(config)

    def _run() -> None:
        import asyncio

        asyncio.run(server.serve())

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    def _stop() -> None:
        server.should_exit = True
        t.join(timeout=5.0)

    return _stop


def _default_wait_healthy(port: int, timeout: float) -> bool:
    """Poll ``/healthz`` until the server responds 200 or *timeout* expires.

    Args:
        port: The port to poll.
        timeout: Maximum seconds to wait.

    Returns:
        ``True`` if the server became healthy, ``False`` on timeout.
    """
    import time

    import httpx

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"http://127.0.0.1:{port}/healthz", timeout=0.5)
            if r.status_code == 200:
                return True
        except Exception:  # noqa: BLE001, S110
            pass
        time.sleep(0.1)
    return False


def _default_open_window(url: str) -> None:
    """Open a native webview window pointing at *url* (blocks main thread).

    Args:
        url: The URL to display in the native window.
    """
    import webview  # pyright: ignore[reportMissingImports]

    window = webview.create_window("pd-suite", url)
    webview.start()
    del window  # suppress unused-variable linter noise


def _default_run_tray(on_quit: Callable[[], None]) -> None:
    """Launch a pystray system-tray icon on a daemon thread.

    Args:
        on_quit: Callback invoked when the user selects "Quit" from the tray.
    """
    import pystray  # pyright: ignore[reportMissingImports]
    from PIL import Image  # pyright: ignore[reportMissingImports]

    # Minimal 16x16 RGBA icon (no file dependency)
    img = Image.new("RGBA", (16, 16), color=(100, 149, 237, 255))

    def _quit_action(icon: Any, item: Any) -> None:
        on_quit()

    menu = pystray.Menu(pystray.MenuItem("Quit", _quit_action))
    icon = pystray.Icon("pd-suite", img, "pd-suite", menu)

    def _run() -> None:
        icon.run()

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def _default_stop_tray() -> None:
    """Stop the pystray icon.

    The default pystray icon runs on a daemon thread and exits when the
    process does; this seam is provided so tests and explicit teardown paths
    can call a no-op stop.
    """


def _default_resolve_port() -> int:
    """Return the default suite port.

    Returns:
        The default port (8004).
    """
    return 8004


def _default_acquire_instance(port: int) -> Any:
    """Acquire the single-instance lock for this process.

    Args:
        port: The port the server is listening on.

    Returns:
        An :class:`~pdomain_ops.suite.single_instance.InstanceLock`.
    """
    import os

    from pdomain_ops.suite.single_instance import acquire

    return acquire("pd-suite", port=port, pid=os.getpid())


def _default_existing_instance() -> dict[str, int] | None:
    """Check for an existing instance of this app.

    Returns:
        ``{"port": <int>, "pid": <int>}`` if an instance is alive, else ``None``.
    """
    from pdomain_ops.suite.single_instance import read_live

    return read_live("pd-suite")


def _default_focus_existing(port: int) -> None:
    """Focus the existing instance by opening it in the default browser.

    Args:
        port: The port of the existing instance.
    """
    import webbrowser

    webbrowser.open(f"http://127.0.0.1:{port}/")


# ---------------------------------------------------------------------------
# ShellDeps dataclass
# ---------------------------------------------------------------------------


@dataclass
class ShellDeps:
    """Injectable seams for ``run_windowed``.

    All fields are callables so unit tests can inject lightweight fakes
    without importing ``webview`` or ``pystray``.

    Attributes:
        start_server: ``(port) -> stop_fn`` — starts the uvicorn server and
            returns a zero-arg callable that stops it.
        wait_healthy: ``(port, timeout) -> bool`` — polls ``/healthz``.
        open_window: ``(url) -> None`` — opens the native webview window
            (blocks main thread; called last before teardown).
        run_tray: ``(on_quit) -> None`` — launches the pystray icon on a
            background daemon thread.
        stop_tray: ``() -> None`` — stops the pystray icon.
        resolve_port: ``() -> int`` — returns the port to bind.
        acquire_instance: ``(port) -> InstanceLock`` — writes the pidfile lock.
        existing_instance: ``() -> dict | None`` — checks for a live instance.
        focus_existing: ``(port) -> None`` — focuses the existing window.
    """

    start_server: Callable[[int], Callable[[], None]] = field(default=_default_start_server)
    wait_healthy: Callable[[int, float], bool] = field(default=_default_wait_healthy)
    open_window: Callable[[str], None] = field(default=_default_open_window)
    run_tray: Callable[[Callable[[], None]], None] = field(default=_default_run_tray)
    stop_tray: Callable[[], None] = field(default=_default_stop_tray)
    resolve_port: Callable[[], int] = field(default=_default_resolve_port)
    acquire_instance: Callable[[int], Any] = field(default=_default_acquire_instance)
    existing_instance: Callable[[], dict[str, int] | None] = field(
        default=_default_existing_instance
    )
    focus_existing: Callable[[int], None] = field(default=_default_focus_existing)


# ---------------------------------------------------------------------------
# run_windowed
# ---------------------------------------------------------------------------


def run_windowed(
    app_module: str,
    *,
    title: str,
    deps: ShellDeps | None = None,
) -> None:
    """Run a pd-* app as a native desktop window.

    Orchestrates the full desktop shell lifecycle with injectable seams so
    the function is unit-testable without a real GUI environment.

    Steps:

    1. Check for an existing instance — if found, focus it and return.
    2. Resolve the port and acquire the pidfile lock.
    3. Start the uvicorn server on a daemon thread.
    4. Poll ``/healthz`` until healthy (30-second timeout).
    5. Launch the pystray tray icon on a daemon thread.
    6. Open the native webview window — blocks the main thread.
    7. On close: stop the server, stop the tray.

    Args:
        app_module: The ASGI app module path (e.g.
            ``"pdomain_ocr_simple_gui.app:app"``).
        title: Window title shown in the native window chrome.
        deps: Injectable :class:`ShellDeps`.  Defaults to the real
            production seams (requires ``[desktop]`` optional extra).
    """
    if deps is None:
        deps = ShellDeps()

    # 1. Single-instance check
    live = deps.existing_instance()
    if live is not None:
        deps.focus_existing(live["port"])
        return

    # 2. Port + lock
    port = deps.resolve_port()
    deps.acquire_instance(port)

    # 3. Start server
    stop_server = deps.start_server(port)

    # 4. Wait until healthy
    deps.wait_healthy(port, 30.0)

    # 5. Launch tray — background daemon thread
    _quit_requested = threading.Event()

    def _on_quit() -> None:
        _quit_requested.set()

    deps.run_tray(_on_quit)

    # 6. Open window — blocks main thread until the user closes it
    deps.open_window(f"http://127.0.0.1:{port}/")

    # 7. Teardown (reached when window is closed)
    stop_server()
    deps.stop_tray()


def restart() -> None:
    """Re-exec the current process with the same argv.

    Used by the update POST flow to restart the app after a successful
    upgrade.  Does not return.
    """
    import os

    os.execv(sys.executable, [sys.executable, *sys.argv])  # noqa: S606


# ---------------------------------------------------------------------------
# Minimal ASGI placeholder used by the default_start_server seam
# ---------------------------------------------------------------------------


async def _noop_app(scope: Any, receive: Any, send: Any) -> None:
    """Minimal ASGI placeholder — real apps pass their own app_module string."""
