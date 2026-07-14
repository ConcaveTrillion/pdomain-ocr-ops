"""Tests for mount_routes function signature and behavior."""

from fastapi import FastAPI

from pdomain_ops.suite.routes import mount_routes
from pdomain_ops.suite.types import SuiteAdapters


class _FakeRegistry:
    def list_installed(self):
        return []

    def register(self, app):
        pass

    def unregister(self, app_id):
        pass


class _FakePrefs:
    def read(self):
        from pdomain_ops.suite.types import UIPrefs

        return UIPrefs()

    def write_common(self, common):
        pass

    def write_app(self, app_id, payload):
        pass


class _FakeLauncher:
    async def launch(self, app):
        from pdomain_ops.suite.sibling_spawn import LaunchResultOpened

        return LaunchResultOpened(url="http://localhost:8001", spawned=False)


class _FakeAuth:
    async def authenticate(self, request):
        from pdomain_ops.suite.auth import Identity

        return Identity(user_id="local", display_name="Local User")

    async def is_authenticated(self, request):
        return True


class _FakeStorage:
    def read(self, key):
        return b""

    def write(self, key, data):
        pass

    def exists(self, key):
        return False

    def delete(self, key):
        pass

    def list_prefix(self, prefix):
        return []


def _make_stub_adapters():
    return SuiteAdapters(
        registry=_FakeRegistry(),
        prefs=_FakePrefs(),
        launcher=_FakeLauncher(),
        auth=_FakeAuth(),
        storage=_FakeStorage(),
    )


def _all_route_paths(app):
    """Collect route paths, descending into FastAPI's _IncludedRouter wrappers.

    FastAPI >=0.137 wraps ``include_router`` results in an ``_IncludedRouter``
    that exposes no ``.path``; the real routes hang off its nested router.
    """
    paths = []
    pending = list(app.routes)
    while pending:
        route = pending.pop()
        path = getattr(route, "path", None)
        if path is not None:
            paths.append(path)
        nested = (
            getattr(route, "routes", None)
            or getattr(getattr(route, "original_router", None), "routes", None)
            or getattr(getattr(route, "router", None), "routes", None)
        )
        if nested:
            pending.extend(nested)
    return paths


def test_mount_routes_accepts_fastapi_app():
    app = FastAPI()
    mount_routes(app, adapters=_make_stub_adapters())
    assert "/api/suite/installed" in _all_route_paths(app)


def test_mount_routes_defaults_to_local_adapters(tmp_path, monkeypatch):
    monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
    app = FastAPI()
    # Should now work without raising (SuiteAdapters.local() is wired in M11)
    mount_routes(app)
    assert "/api/suite/installed" in _all_route_paths(app)
