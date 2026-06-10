"""Tests for suite shared-paths API."""

from __future__ import annotations

import filelock

from pdomain_ops.suite.shared_paths import (
    SharedPathsLockTimeout,
)

_WATCHDOG_S = 10.0


def test_shared_paths_lock_timeout_is_filelock_timeout_subclass():
    assert issubclass(SharedPathsLockTimeout, filelock.Timeout)
