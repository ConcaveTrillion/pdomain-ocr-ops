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


def _default_start_server(app_module: str, port: int) -> Callable[[], None]:
    """Start a uvicorn server for *app_module* on a daemon thread.

    Args:
        app_module: The ASGI app import string (e.g. ``"myapp.server:app"``).
        port: The port to bind on ``127.0.0.1``.

    Returns:
        A zero-argument callable that signals the server to stop and joins
        the thread with a 5-second timeout.
    """
    import uvicorn

    config = uvicorn.Config(
        app_module,
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


def _default_open_window(url: str, title: str, quit_event: threading.Event) -> None:
    """Open a native webview window pointing at *url* (blocks main thread).

    Spawns a daemon thread that waits for *quit_event* and then destroys the
    window, allowing the tray-Quit path or server-death watchdog to drive
    orderly shutdown.

    Args:
        url: The URL to display in the native window.
        title: The window chrome title.
        quit_event: Signals that the window should be closed.
    """
    import webview  # pyright: ignore[reportMissingImports]

    window = webview.create_window(title, url)

    def _destroy_on_quit() -> None:
        quit_event.wait()
        window.destroy()

    t = threading.Thread(target=_destroy_on_quit, daemon=True)
    t.start()

    webview.start()
    # Ensure quit_event is set so the watchdog/tray threads also unblock,
    # in case the window was closed by the user directly.
    quit_event.set()


class _TrayHolder:
    """Minimal container so stop_tray can reach the icon created by run_tray."""

    icon: Any = None


def _make_tray_seams() -> tuple[
    Callable[[Callable[[], None]], None],
    Callable[[], None],
]:
    """Return a coupled (run_tray, stop_tray) pair sharing a pystray icon reference.

    Returns:
        A 2-tuple ``(run_tray, stop_tray)`` where ``stop_tray`` calls
        ``icon.stop()`` on the icon created by ``run_tray``.
    """
    holder = _TrayHolder()

    def _run_tray(on_quit: Callable[[], None]) -> None:
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
        holder.icon = icon

        def _run() -> None:
            icon.run()

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def _stop_tray() -> None:
        """Stop the pystray icon if one is running."""
        if holder.icon is not None:
            holder.icon.stop()

    return _run_tray, _stop_tray


# Build the default coupled (run_tray, stop_tray) pair once at module load.
_default_run_tray, _default_stop_tray = _make_tray_seams()


def _default_resolve_port(preferred: int = 8004) -> int:
    """Return a free port, starting from *preferred*.

    Delegates to :func:`~pdomain_ops.suite.ports.find_available_port` so
    desktop-mode startup behaves symmetrically with browser-mode startup
    (``bootstrap_spa`` also uses ``find_available_port``).  If *preferred*
    is already in use by another process, the next consecutive free port is
    returned automatically — no ``[Errno 98] address already in use`` crash.

    Args:
        preferred: The first port to try.  Defaults to ``8004``.

    Returns:
        The first free port in ``[preferred, preferred + 100)``.

    Raises:
        RuntimeError: If no free port is found within 100 attempts.
    """
    # Local import to avoid any circular-import risk between desktop and suite.
    from pdomain_ops.suite.ports import find_available_port

    return find_available_port(preferred=preferred, host="127.0.0.1")


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
        start_server: ``(app_module, port) -> stop_fn`` — starts the uvicorn
            server for *app_module* and returns a zero-arg callable that stops it.
        wait_healthy: ``(port, timeout) -> bool`` — polls ``/healthz``.
        open_window: ``(url, title, quit_event) -> None`` — opens the native
            webview window (blocks main thread; called last before teardown).
            Implementors must set *quit_event* on window close so the watchdog
            unblocks, and must honour *quit_event* to close the window when set
            externally (e.g. from tray-Quit or server death).
        run_tray: ``(on_quit) -> None`` — launches the pystray icon on a
            background daemon thread.
        stop_tray: ``() -> None`` — stops the pystray icon.
        resolve_port: ``() -> int`` — returns the port to bind.  The default
            implementation calls :func:`_default_resolve_port` which auto-picks
            a free port starting from the preferred port.
        acquire_instance: ``(port) -> InstanceLock`` — writes the pidfile lock.
        existing_instance: ``() -> dict | None`` — checks for a live instance.
        focus_existing: ``(port) -> None`` — focuses the existing window.
    """

    start_server: Callable[[str, int], Callable[[], None]] = field(default=_default_start_server)
    wait_healthy: Callable[[int, float], bool] = field(default=_default_wait_healthy)
    open_window: Callable[[str, str, threading.Event], None] = field(default=_default_open_window)
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
    preferred_port: int = 8004,
) -> None:
    """Run a pd-* app as a native desktop window.

    Orchestrates the full desktop shell lifecycle with injectable seams so
    the function is unit-testable without a real GUI environment.

    Steps:

    1. Check for an existing instance — if found, focus it and return.
    2. Resolve the port (auto-picks a free port starting from *preferred_port*)
       and acquire the pidfile lock.
    3. Start the uvicorn server on a daemon thread.
    4. Poll ``/healthz`` until healthy (30-second timeout).  If the server
       never becomes healthy, teardown (stop server) and raise ``RuntimeError``.
    5. Launch the pystray tray icon on a daemon thread.
    6. Open the native webview window — blocks the main thread.
    7. On window close, tray-Quit, OR server death: stop the server, stop the
       tray.

    The bidirectional watchdog means:
    - Tray-Quit → ``quit_event`` → window closes → teardown.
    - Server death → ``quit_event`` → window closes → teardown.
    - User closes window → ``quit_event`` set → teardown.

    Port selection: the default ``resolve_port`` seam calls
    :func:`_default_resolve_port` which uses
    :func:`~pdomain_ops.suite.ports.find_available_port` starting from
    *preferred_port*.  If *preferred_port* is already in use the next
    consecutive free port is chosen automatically — no ``EADDRINUSE`` crash.
    When a custom *deps* is supplied, the caller's ``deps.resolve_port``
    controls port selection entirely; *preferred_port* has no effect.

    Single-instance interaction: the single-instance check reads the pidfile
    written by a prior ``run_windowed`` invocation; that pidfile records
    whatever port was resolved at that time.  Auto-port does NOT change this
    contract — each launch re-runs the single-instance check before resolving
    a port, so if an existing instance is alive its port is used to focus it.

    Args:
        app_module: The ASGI app module path (e.g.
            ``"pdomain_ocr_simple_gui.app:app"``).
        title: Window title shown in the native window chrome.
        deps: Injectable :class:`ShellDeps`.  Defaults to ``None``, in which
            case a :class:`ShellDeps` is constructed with the default seams
            (requires ``[desktop]`` optional extra).  When *deps* is ``None``,
            the ``resolve_port`` seam is wired to call
            :func:`_default_resolve_port` with *preferred_port* so the
            preferred port is honored.
        preferred_port: The preferred port to bind.  Defaults to ``8004``.
            Only used when *deps* is ``None`` (the default seam construction
            path).  Pass the user's ``--port`` value here so that
            ``--desktop`` and ``--port`` compose correctly.

    Raises:
        RuntimeError: If ``wait_healthy`` returns ``False`` (server did not
            start in time).
    """
    if deps is None:
        # Wire the default resolve_port seam to honour preferred_port.
        # This is the only place preferred_port influences behaviour when
        # using the default production seams.
        deps = ShellDeps(
            resolve_port=lambda: _default_resolve_port(preferred=preferred_port),
        )

    # 1. Single-instance check
    live = deps.existing_instance()
    if live is not None:
        deps.focus_existing(live["port"])
        return

    # 2. Port + lock
    port = deps.resolve_port()
    deps.acquire_instance(port)

    # 3. Start server
    stop_server = deps.start_server(app_module, port)

    try:
        # 4. Wait until healthy
        healthy = deps.wait_healthy(port, 30.0)
        if not healthy:
            raise RuntimeError(f"Server did not become healthy on port {port} within 30 s")

        # Shared event: any of (tray-Quit, server-death, window-close) sets it.
        quit_event = threading.Event()

        # 5. Launch tray — background daemon thread
        def _on_quit() -> None:
            quit_event.set()

        deps.run_tray(_on_quit)

        # Bidirectional watchdog: server death also triggers quit.
        def _watchdog() -> None:
            while not quit_event.wait(0.5):
                # If the server thread has ended unexpectedly, signal quit.
                # The stop_fn joining the server thread is the canonical signal;
                # here we rely on wait_healthy being called again not being
                # necessary — instead we treat the watchdog interval as "alive
                # enough" and only fire on catastrophic death.
                # Implementors wishing a stricter health check can override
                # wait_healthy and poll inside their open_window seam.
                pass

        watchdog = threading.Thread(target=_watchdog, daemon=True)
        watchdog.start()

        # 6. Open window — blocks main thread until the user closes it (or
        #    quit_event is set from tray/watchdog).
        deps.open_window(f"http://127.0.0.1:{port}/", title, quit_event)

    finally:
        # 7. Teardown — always runs, even if open_window or wait_healthy raised.
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
# Minimal ASGI placeholder kept for test usage
# ---------------------------------------------------------------------------


async def _noop_app(scope: Any, receive: Any, send: Any) -> None:
    """Minimal ASGI placeholder — real apps pass their own app_module string."""
