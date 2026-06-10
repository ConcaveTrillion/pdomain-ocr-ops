"""Tests for DoctrExportManifest Pydantic models."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from pdomain_ops.schemas.doctr_export import (
    DoctrExportManifest,
    DoctrExportProject,
    DoctrExportTaskStats,
    read_manifest,
    write_manifest,
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


def _sample_manifest() -> DoctrExportManifest:
    return DoctrExportManifest(
        generated_at=datetime(2026, 6, 10, 12, 0, tzinfo=UTC),
        app="pdomain-ocr-labeler-spa",
        projects={
            "proj-abc": DoctrExportProject(
                exported_at=datetime(2026, 6, 10, 11, 0, tzinfo=UTC),
                page_count=3,
                tasks={
                    "recognition": DoctrExportTaskStats(item_count=90),
                    "detection": DoctrExportTaskStats(item_count=3),
                },
            )
        },
    )


def test_write_then_read_manifest_roundtrip(tmp_path):
    m = _sample_manifest()
    write_manifest(tmp_path, m)
    result = read_manifest(tmp_path)
    assert result is not None
    assert result.app == "pdomain-ocr-labeler-spa"
    assert result.projects["proj-abc"].page_count == 3
    assert result.projects["proj-abc"].tasks["recognition"].item_count == 90


def test_read_manifest_missing_file_returns_none(tmp_path):
    result = read_manifest(tmp_path)
    assert result is None


def test_read_manifest_corrupt_file_raises(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("not valid json", encoding="utf-8")
    with pytest.raises(ValueError, match="corrupt"):
        read_manifest(tmp_path)


def test_write_manifest_creates_parent_dir(tmp_path):
    export_root = tmp_path / "deep" / "nested" / "dir"
    write_manifest(export_root, _sample_manifest())
    assert (export_root / "manifest.json").exists()


def test_write_manifest_is_atomic(tmp_path):
    """write_manifest must not leave a partial file visible to readers."""
    m = _sample_manifest()
    write_manifest(tmp_path, m)
    # A second write should fully replace the first atomically
    m2 = m.model_copy(update={"app": "pdomain-ocr-trainer-spa"})
    write_manifest(tmp_path, m2)
    result = read_manifest(tmp_path)
    assert result is not None
    assert result.app == "pdomain-ocr-trainer-spa"


def test_written_json_has_schema_key_not_schema_id(tmp_path):
    """The on-disk key must be 'schema', not 'schema_id'."""
    write_manifest(tmp_path, _sample_manifest())
    raw = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert "schema" in raw
    assert "schema_id" not in raw


def test_read_manifest_version_gt_1_returns_object(tmp_path):
    """Forward-compat: version > 1 must parse successfully, not crash."""
    data = _minimal_manifest_dict()
    data["version"] = 42
    (tmp_path / "manifest.json").write_text(json.dumps(data), encoding="utf-8")
    result = read_manifest(tmp_path)
    assert result is not None
    assert result.version == 42
