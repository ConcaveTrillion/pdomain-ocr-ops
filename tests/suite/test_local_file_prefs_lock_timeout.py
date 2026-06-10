"""Bounded-lock-acquisition tests for LocalFilePrefs.

Regression coverage for the indefinite-hang bug: ``LocalFilePrefs`` used to
acquire its ``filelock.FileLock`` with the library default ``timeout=-1``
(block forever). When another process/thread held the lock, the next prefs
call would wedge the caller indefinitely. These tests prove the acquisition is
now FINITE and raises a clear, typed error instead of hanging.

Every test that could otherwise block forever runs the prefs call on a worker
thread and joins with a hard wall-clock timeout, so the test suite itself can
never hang even if the fix regresses.
"""

from __future__ import annotations

import threading
from pathlib import Path

import filelock
import pytest

from pdomain_ops.suite.prefs import LocalFilePrefs, PrefsLockTimeout
from pdomain_ops.suite.types import CommonUIPrefs, LayerColors

# Hard wall-clock ceiling for any operation that *should* be bounded. Must be
# comfortably larger than the prefs lock_timeout used in these tests, but small
# enough that a real regression (forever-block) fails the test fast instead of
# hanging CI.
_WATCHDOG_S = 10.0


def _make_common(**kwargs) -> CommonUIPrefs:
    defaults = {
        "theme": "dark",
        "density": "normal",
        "accent": "#d6925a",
        "font_size_base": 12,
        "layer_colors": LayerColors(),
    }
    defaults.update(kwargs)
    return CommonUIPrefs(**defaults)


def _run_bounded(fn, *, watchdog_s: float = _WATCHDOG_S):
    """Run ``fn`` on a worker thread; return (result, exception).

    Joins with a hard wall-clock timeout so a forever-block surfaces as a test
    failure rather than a hung suite.
    """
    box: dict[str, object] = {}

    def target() -> None:
        try:
            box["result"] = fn()
        except BaseException as exc:  # capture for assertion
            box["exc"] = exc

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(timeout=watchdog_s)
    if worker.is_alive():
        pytest.fail(
            f"prefs call did not return within {watchdog_s}s -- lock acquisition "
            "is blocking indefinitely (the bug this test guards against)"
        )
    return box.get("result"), box.get("exc")


def _hold_lock(lock_path: str, held: threading.Event, release: threading.Event) -> None:
    with filelock.FileLock(lock_path):
        held.set()
        release.wait(timeout=_WATCHDOG_S)


def test_read_raises_lock_timeout_when_lock_held(tmp_path):
    prefs_file = tmp_path / "ui-prefs.json"
    prefs = LocalFilePrefs(root=prefs_file, lock_timeout=0.5)

    held = threading.Event()
    release = threading.Event()
    h = threading.Thread(
        target=_hold_lock, args=(str(prefs._lock_path), held, release), daemon=True
    )
    h.start()
    assert held.wait(timeout=_WATCHDOG_S), "holder thread never acquired the lock"

    try:
        _result, exc = _run_bounded(prefs.read)
        assert isinstance(exc, PrefsLockTimeout), f"expected PrefsLockTimeout, got {exc!r}"
    finally:
        release.set()
        h.join(timeout=_WATCHDOG_S)


def test_write_common_raises_lock_timeout_when_lock_held(tmp_path):
    prefs_file = tmp_path / "ui-prefs.json"
    prefs = LocalFilePrefs(root=prefs_file, lock_timeout=0.5)

    held = threading.Event()
    release = threading.Event()
    h = threading.Thread(
        target=_hold_lock, args=(str(prefs._lock_path), held, release), daemon=True
    )
    h.start()
    assert held.wait(timeout=_WATCHDOG_S)

    try:
        _result, exc = _run_bounded(lambda: prefs.write_common(_make_common()))
        assert isinstance(exc, PrefsLockTimeout), f"expected PrefsLockTimeout, got {exc!r}"
    finally:
        release.set()
        h.join(timeout=_WATCHDOG_S)


def test_write_app_raises_lock_timeout_when_lock_held(tmp_path):
    prefs_file = tmp_path / "ui-prefs.json"
    prefs = LocalFilePrefs(root=prefs_file, lock_timeout=0.5)

    held = threading.Event()
    release = threading.Event()
    h = threading.Thread(
        target=_hold_lock, args=(str(prefs._lock_path), held, release), daemon=True
    )
    h.start()
    assert held.wait(timeout=_WATCHDOG_S)

    try:
        _result, exc = _run_bounded(lambda: prefs.write_app("some-app", {"k": "v"}))
        assert isinstance(exc, PrefsLockTimeout), f"expected PrefsLockTimeout, got {exc!r}"
    finally:
        release.set()
        h.join(timeout=_WATCHDOG_S)


def test_default_lock_timeout_is_finite(tmp_path):
    """The default must be a finite positive number, never -1 (block forever)."""
    prefs = LocalFilePrefs(root=tmp_path / "ui-prefs.json")
    assert prefs._lock_timeout > 0
    assert prefs._lock_timeout != -1


def test_lock_timeout_env_var_override(tmp_path, monkeypatch):
    monkeypatch.setenv("PDOMAIN_PREFS_LOCK_TIMEOUT", "1.5")
    prefs = LocalFilePrefs(root=tmp_path / "ui-prefs.json")
    assert prefs._lock_timeout == 1.5


def test_explicit_lock_timeout_beats_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("PDOMAIN_PREFS_LOCK_TIMEOUT", "1.5")
    prefs = LocalFilePrefs(root=tmp_path / "ui-prefs.json", lock_timeout=3.0)
    assert prefs._lock_timeout == 3.0


def test_invalid_env_var_falls_back_to_default(tmp_path, monkeypatch):
    monkeypatch.setenv("PDOMAIN_PREFS_LOCK_TIMEOUT", "not-a-number")
    prefs = LocalFilePrefs(root=tmp_path / "ui-prefs.json")
    assert prefs._lock_timeout > 0


def test_prefs_lock_timeout_is_a_filelock_timeout_subclass():
    """Backward-compat: existing callers catching ``filelock.Timeout`` still work."""
    assert issubclass(PrefsLockTimeout, filelock.Timeout)


def test_uncontended_calls_still_work(tmp_path):
    """The finite timeout must not break the normal happy path."""
    prefs = LocalFilePrefs(root=tmp_path / "ui-prefs.json", lock_timeout=0.5)
    prefs.write_app("app-a", {"k": "v"})
    prefs.write_common(_make_common(theme="light"))
    out = prefs.read()
    assert out.common.theme == "light"
    assert out.apps["app-a"]["k"] == "v"


def test_lock_path_attribute_exists(tmp_path):
    """The private _lock_path the tests reach for is part of the implementation."""
    prefs = LocalFilePrefs(root=tmp_path / "ui-prefs.json")
    assert isinstance(prefs._lock_path, Path)
