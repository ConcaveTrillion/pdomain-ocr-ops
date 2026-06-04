"""Shared fixtures for suite tests."""

from __future__ import annotations

from typing import Any

import pytest

from pdomain_ops.suite.types import CommonUIPrefs, UIPrefs


class _InMemoryPrefs:
    """A simple in-memory PrefsAdapter for tests."""

    def __init__(self) -> None:
        self._prefs = UIPrefs()

    def read(self) -> UIPrefs:
        """Return current in-memory prefs."""
        return self._prefs

    def write_common(self, common: CommonUIPrefs) -> None:
        """Overwrite the common section."""
        self._prefs = UIPrefs(common=common, apps=self._prefs.apps)

    def write_app(self, app_id: str, payload: dict[str, Any]) -> None:
        """Overwrite the per-app section for app_id."""
        apps = dict(self._prefs.apps)
        apps[app_id] = payload
        self._prefs = UIPrefs(common=self._prefs.common, apps=apps)


@pytest.fixture
def local_prefs() -> _InMemoryPrefs:
    """Return a fresh in-memory PrefsAdapter for each test."""
    return _InMemoryPrefs()
