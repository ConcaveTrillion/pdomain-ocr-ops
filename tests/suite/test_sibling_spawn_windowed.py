"""Tests for sibling_spawn build_launch_argv with windowed flag."""

from __future__ import annotations


def _app():  # minimal InstalledApp-like
    from pdomain_ops.suite.types import InstalledApp

    return InstalledApp(
        app_id="a",
        package="a",
        version="0",
        binary="/usr/bin/a",
        default_port=8004,
        icon="a",
        display_name="App A",
    )


def test_argv_windowed_appends_desktop():
    from pdomain_ops.suite.sibling_spawn import build_launch_argv

    assert "--desktop" in build_launch_argv(_app(), windowed=True)


def test_argv_default_no_desktop():
    from pdomain_ops.suite.sibling_spawn import build_launch_argv

    assert "--desktop" not in build_launch_argv(_app(), windowed=False)
