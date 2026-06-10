"""DocTR export manifest schema and IO helpers.

The manifest file lives at ``<export_root>/manifest.json`` and records
which projects have been exported, when, and with what task item counts.

Forward-compat: ``version > 1`` is accepted with a log warning rather than
raising — the caller decides whether to reject an unexpected version.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
from datetime import datetime  # noqa: TC003  # Pydantic requires runtime import
from pathlib import Path  # noqa: TC003  # Pydantic requires runtime import

from pydantic import BaseModel, ConfigDict, Field

_logger = logging.getLogger(__name__)

_MANIFEST_FILENAME = "manifest.json"
_CURRENT_VERSION = 1


class DoctrExportTaskStats(BaseModel):
    """Per-task item count for one export."""

    model_config = ConfigDict(extra="ignore")

    item_count: int


class DoctrExportProject(BaseModel):
    """Export record for one project."""

    model_config = ConfigDict(extra="ignore")

    exported_at: datetime
    page_count: int
    tasks: dict[str, DoctrExportTaskStats]


class DoctrExportManifest(BaseModel):
    """Top-level DocTR export manifest.

    The JSON key ``"schema"`` maps to the Python field ``schema_id``
    to avoid collision with Pydantic's own ``.model_json_schema()`` method.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    schema_id: str = Field(
        default="pdomain.doctr-export-manifest",
        alias="schema",
    )
    version: int = _CURRENT_VERSION
    generated_at: datetime
    app: str
    projects: dict[str, DoctrExportProject] = {}


def read_manifest(export_root: Path) -> DoctrExportManifest | None:
    """Read the manifest from ``<export_root>/manifest.json``.

    Returns ``None`` if the file does not exist.
    Raises ``ValueError`` with "corrupt" in the message if the file exists
    but cannot be parsed or fails model validation.

    Version > 1 is accepted with a log warning — caller decides to reject.
    """
    path = export_root / _MANIFEST_FILENAME
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"corrupt manifest at {path}: {exc}") from exc
    try:
        manifest = DoctrExportManifest.model_validate(data)
    except Exception as exc:
        raise ValueError(f"corrupt manifest at {path}: {exc}") from exc
    if manifest.version > _CURRENT_VERSION:
        _logger.warning(
            "manifest at %s has version %d > current %d; parsing best-effort",
            path,
            manifest.version,
            _CURRENT_VERSION,
        )
    return manifest


def write_manifest(export_root: Path, manifest: DoctrExportManifest) -> None:
    """Write *manifest* to ``<export_root>/manifest.json`` atomically.

    Uses a temporary file in the same directory + ``os.replace`` so
    readers never see a partial write. Creates ``export_root`` if it
    does not exist.
    """
    export_root.mkdir(parents=True, exist_ok=True)
    dest = export_root / _MANIFEST_FILENAME
    fd, tmp_name = tempfile.mkstemp(dir=export_root, prefix=".manifest-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(by_alias=True, indent=2))
        os.replace(tmp_name, dest)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
