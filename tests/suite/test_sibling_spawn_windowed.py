"""Tests for sibling_spawn build_launch_argv and launch() with windowed flag."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


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


@pytest.mark.asyncio
async def test_launch_windowed_true_passes_desktop_flag():
    """launch(windowed=True) propagates --desktop to the spawned argv."""
    from pdomain_ops.suite.sibling_spawn import LaunchResultOpened, LocalSpawnLauncher

    app = _app()
    launcher = LocalSpawnLauncher()
    mock_proc = MagicMock()
    mock_proc.pid = 42

    call_count = [0]

    async def mock_get(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise httpx.ConnectError("refused")
        resp = MagicMock()
        resp.status_code = 200
        return resp

    with (
        patch("httpx.AsyncClient.get", side_effect=mock_get),
        patch("subprocess.Popen", return_value=mock_proc) as mock_popen,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await launcher.launch(app, windowed=True)

    assert isinstance(result, LaunchResultOpened)
    assert result.spawned is True
    spawned_argv = mock_popen.call_args[0][0]
    assert "--desktop" in spawned_argv, f"Expected --desktop in argv: {spawned_argv}"


@pytest.mark.asyncio
async def test_launch_windowed_false_omits_desktop_flag():
    """launch(windowed=False) does NOT include --desktop in the spawned argv."""
    from pdomain_ops.suite.sibling_spawn import LaunchResultOpened, LocalSpawnLauncher

    app = _app()
    launcher = LocalSpawnLauncher()
    mock_proc = MagicMock()
    mock_proc.pid = 43

    call_count = [0]

    async def mock_get(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise httpx.ConnectError("refused")
        resp = MagicMock()
        resp.status_code = 200
        return resp

    with (
        patch("httpx.AsyncClient.get", side_effect=mock_get),
        patch("subprocess.Popen", return_value=mock_proc) as mock_popen,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await launcher.launch(app, windowed=False)

    assert isinstance(result, LaunchResultOpened)
    spawned_argv = mock_popen.call_args[0][0]
    assert "--desktop" not in spawned_argv, f"Expected no --desktop in argv: {spawned_argv}"
