"""Tests for DoctrExportManifest Pydantic models."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from pdomain_ops.schemas.doctr_export import (
    DoctrExportManifest,
    DoctrExportProject,
    DoctrExportTaskStats,
)


def _minimal_manifest_dict() -> dict:
    return {
        "schema": "pdomain.doctr-export-manifest",
        "version": 1,
        "generated_at": "2026-06-10T12:00:00+00:00",
        "app": "pdomain-ocr-labeler-spa",
        "projects": {},
    }


def test_task_stats_roundtrip():
    s = DoctrExportTaskStats(item_count=42)
    assert s.item_count == 42


def test_project_roundtrip():
    p = DoctrExportProject(
        exported_at=datetime(2026, 6, 10, 12, 0, tzinfo=UTC),
        page_count=12,
        tasks={"recognition": DoctrExportTaskStats(item_count=340)},
    )
    assert p.page_count == 12
    assert p.tasks["recognition"].item_count == 340


def test_manifest_from_json_dict():
    data = _minimal_manifest_dict()
    m = DoctrExportManifest.model_validate(data)
    assert m.schema_id == "pdomain.doctr-export-manifest"
    assert m.version == 1
    assert m.app == "pdomain-ocr-labeler-spa"
    assert m.projects == {}


def test_manifest_round_trips_via_json():
    data = _minimal_manifest_dict()
    data["projects"]["proj-1"] = {
        "exported_at": "2026-06-10T10:00:00+00:00",
        "page_count": 5,
        "tasks": {
            "recognition": {"item_count": 100},
            "detection": {"item_count": 5},
        },
    }
    m = DoctrExportManifest.model_validate(data)
    dumped = json.loads(m.model_dump_json(by_alias=True))
    assert dumped["schema"] == "pdomain.doctr-export-manifest"
    assert dumped["projects"]["proj-1"]["tasks"]["recognition"]["item_count"] == 100


def test_unknown_task_keys_roundtrip():
    """Tasks dict is keyed by arbitrary string — unknown keys must survive."""
    data = _minimal_manifest_dict()
    data["projects"]["p"] = {
        "exported_at": "2026-06-10T10:00:00+00:00",
        "page_count": 1,
        "tasks": {
            "future-task-type": {"item_count": 7},
        },
    }
    m = DoctrExportManifest.model_validate(data)
    assert m.projects["p"].tasks["future-task-type"].item_count == 7


def test_version_gt_1_does_not_crash():
    """Forward-compat: version > 1 must not raise — caller decides to reject."""
    data = _minimal_manifest_dict()
    data["version"] = 99
    m = DoctrExportManifest.model_validate(data)
    assert m.version == 99
