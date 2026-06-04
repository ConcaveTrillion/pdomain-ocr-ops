"""FastAPI routes for the in-app update control.

Mounts GET/POST /api/suite/update onto a FastAPI application.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from pydantic import BaseModel

from pdomain_ops.suite.update import apply_upgrade, check_latest

if TYPE_CHECKING:
    from fastapi import FastAPI

#: Default index URL from the environment; falls back to the pdomain-index-pip URL.
_DEFAULT_INDEX_URL = os.environ.get(
    "PDOMAIN_INDEX_URL",
    "https://concavetrillion.github.io/pdomain-index-pip/simple",
)


class UpdateInfo(BaseModel):
    """Shape returned by GET /api/suite/update."""

    current: str
    latest: str
    update_available: bool
    changelog_url: str | None = None
    channel: str = "stable"


def mount_update_routes(
    app: FastAPI,
    *,
    dist_name: str,
    index_url: str = _DEFAULT_INDEX_URL,
) -> None:
    """Mount update-check and apply routes onto *app*.

    Parameters
    ----------
    app:
        The FastAPI application to mount routes onto.
    dist_name:
        Distribution name of the application, e.g. ``"pdomain-ocr-simple-gui"``.
    index_url:
        Base URL of the simple index to query for latest releases.
        Defaults to the ``PDOMAIN_INDEX_URL`` env var or the canonical pdomain-index-pip.
    """

    @app.get("/api/suite/update", response_model=UpdateInfo)
    def get_update() -> UpdateInfo:
        result = check_latest(dist_name=dist_name, index_url=index_url)
        return UpdateInfo(
            current=str(result["current"]),
            latest=str(result["latest"]),
            update_available=bool(result["update_available"]),
            changelog_url=str(result["changelog_url"]) if result.get("changelog_url") else None,
            channel=str(result.get("channel", "stable")),
        )

    @app.post("/api/suite/update")
    def post_update() -> dict[str, object]:
        apply_upgrade(dist_name)
        return {"restart_required": True}
