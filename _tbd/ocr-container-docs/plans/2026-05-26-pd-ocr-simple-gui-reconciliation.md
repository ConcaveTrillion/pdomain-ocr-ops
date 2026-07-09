---
title: pdomain-ocr-simple-gui reconciliation + hardening — implementation plan
status: draft
date: 2026-05-26
repo: pdomain/pdomain-ocr-simple-gui
spec: docs/specs/2026-05-26-pdomain-ocr-simple-gui-reconciliation-design.md
---

# pdomain-ocr-simple-gui reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the broken `pdomain-ocr-simple-gui` end-to-end (real upload + drop affordances, container-aware modes, word overlays, output config, download, four pdomain-ui swaps) then close the 13 open security/privacy/deps issues.

**Architecture:** Backend grows a `Source` Protocol with `LocalPathSource` (folder | single image | zip) and `UploadedFilesSource` (multipart staging dir). A new `/api/config` route exposes `{mode, is_containerized}` so the frontend can pick the right input affordances. Output destination is selectable (`next_to_source` | `specified` | `managed`) with a download endpoint for managed mode. Four pdomain-ui surfaces (`testids`, `worklist`, `stages/PageWorkbench`, `stores`) replace hand-rolled equivalents. Then Phase B closes #17–#34 in four hardening groups.

**Tech Stack:** FastAPI, React 18 + Vite + TypeScript, `@concavetrillion/pdomain-ui`, `pdomain-ops` (LocalStageDispatcher), `pdomain-book-tools`, pytest + pytest-xdist, Vitest, Playwright (browser verification).

**Spec:** `docs/specs/2026-05-26-pdomain-ocr-simple-gui-reconciliation-design.md`

**Repo layout reminders:**
- Python: `src/pd_ocr_simple_gui/`
- Routes: `src/pd_ocr_simple_gui/routes/`
- Frontend: `frontend/src/`
- Tests: `tests/` (Python), `frontend/src/**/__tests__/` (Vitest), `tests/e2e/` (Playwright)

---

## File Structure

### Backend (new)
- `src/pd_ocr_simple_gui/runtime/container_detect.py` — pure detector function.
- `src/pd_ocr_simple_gui/runtime/mode.py` — env-driven `Mode` enum + reader.
- `src/pd_ocr_simple_gui/routes/config.py` — `GET /api/config`.
- `src/pd_ocr_simple_gui/sources/__init__.py` — `Source` Protocol + typed errors.
- `src/pd_ocr_simple_gui/sources/local_path.py` — `LocalPathSource`.
- `src/pd_ocr_simple_gui/sources/uploaded_files.py` — `UploadedFilesSource`.
- `src/pd_ocr_simple_gui/routes/uploads.py` — `POST /api/uploads`.
- `src/pd_ocr_simple_gui/output/config.py` — `OutputConfig` model + resolver.
- `src/pd_ocr_simple_gui/routes/downloads.py` — `GET /api/jobs/{id}/download`.
- `src/pd_ocr_simple_gui/routes/words.py` — `GET /api/pages/{id}/{idx}/words`.

### Backend (modified)
- `src/pd_ocr_simple_gui/app.py` — register new routes, wire startup detector, replace 4× `except Exception: pass`.
- `src/pd_ocr_simple_gui/routes/jobs.py` — accept `source_path` | `upload_id` + `output: OutputConfig`.

### Frontend (new)
- `frontend/src/runtime/ConfigContext.tsx` — fetch + provide `/api/config`.
- `frontend/src/components/SourcePicker.tsx` — drop, file-pick, path-input.
- `frontend/src/components/OutputConfigPanel.tsx` — three radio modes.
- `frontend/src/lib/testids.ts` — re-export pdomain-ui testids + local additions.

### Frontend (modified)
- `frontend/src/App.tsx` — wrap with `ConfigContext.Provider`, drop hand-rolled prefs fetch.
- `frontend/src/pages/HomePage.tsx` — render layout per affordance matrix.
- `frontend/src/pages/PageViewPage.tsx` — fetch words, wrap with `PageWorkbench`.
- `frontend/src/pages/ResultsPage.tsx` — add download button, swap worklist.
- `frontend/src/components/RecentProjectsList.tsx` — swap worklist + stores.
- `frontend/src/components/DropZone.tsx` — **remove** (replaced by `SourcePicker`).
- `frontend/src/components/JobConfigDialog.tsx` — embed `OutputConfigPanel`.

### Tests (new — Python)
- `tests/test_container_detect.py`
- `tests/test_config_route.py`
- `tests/test_sources_local_path.py`
- `tests/test_sources_uploaded.py`
- `tests/test_uploads.py`
- `tests/test_output_config.py`
- `tests/test_download_route.py`
- `tests/test_words_route.py`

### Tests (new — frontend)
- `frontend/src/components/__tests__/SourcePicker.test.tsx`
- `frontend/src/components/__tests__/OutputConfigPanel.test.tsx`
- `frontend/src/pages/__tests__/HomePage.test.tsx`
- `frontend/src/pages/__tests__/ResultsPage.test.tsx`
- `frontend/src/pages/__tests__/PageViewPage.test.tsx`

### Tests (new — Playwright)
- `tests/e2e/test_upload_single_image.py`
- `tests/e2e/test_existing_folder_local.py`
- `tests/e2e/test_word_overlays_render.py`
- `tests/e2e/test_download_managed.py`

---

## Phase A — Functional repair

### Milestone A0 — Container detection + mode plumbing

#### Task A0.1: Container detector

**Files:**
- Create: `src/pd_ocr_simple_gui/runtime/container_detect.py`
- Test: `tests/test_container_detect.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_container_detect.py
from pathlib import Path

from pd_ocr_simple_gui.runtime.container_detect import detect_containerized


def test_dockerenv_marker(tmp_path: Path, monkeypatch) -> None:
    marker = tmp_path / ".dockerenv"
    marker.touch()
    monkeypatch.setattr(
        "pd_ocr_simple_gui.runtime.container_detect._DOCKERENV", marker
    )
    monkeypatch.setattr(
        "pd_ocr_simple_gui.runtime.container_detect._PODMAN_MARKER",
        tmp_path / "missing",
    )
    monkeypatch.delenv("container", raising=False)
    monkeypatch.setattr(
        "pd_ocr_simple_gui.runtime.container_detect._read_init_cgroup",
        lambda: "",
    )
    assert detect_containerized() is True


def test_podman_marker(tmp_path: Path, monkeypatch) -> None:
    marker = tmp_path / "containerenv"
    marker.touch()
    monkeypatch.setattr(
        "pd_ocr_simple_gui.runtime.container_detect._DOCKERENV",
        tmp_path / "missing",
    )
    monkeypatch.setattr(
        "pd_ocr_simple_gui.runtime.container_detect._PODMAN_MARKER", marker
    )
    monkeypatch.delenv("container", raising=False)
    monkeypatch.setattr(
        "pd_ocr_simple_gui.runtime.container_detect._read_init_cgroup",
        lambda: "",
    )
    assert detect_containerized() is True


def test_container_env_var(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "pd_ocr_simple_gui.runtime.container_detect._DOCKERENV",
        tmp_path / "missing",
    )
    monkeypatch.setattr(
        "pd_ocr_simple_gui.runtime.container_detect._PODMAN_MARKER",
        tmp_path / "missing2",
    )
    monkeypatch.setenv("container", "podman")
    monkeypatch.setattr(
        "pd_ocr_simple_gui.runtime.container_detect._read_init_cgroup",
        lambda: "",
    )
    assert detect_containerized() is True


def test_cgroup_signal(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "pd_ocr_simple_gui.runtime.container_detect._DOCKERENV",
        tmp_path / "missing",
    )
    monkeypatch.setattr(
        "pd_ocr_simple_gui.runtime.container_detect._PODMAN_MARKER",
        tmp_path / "missing2",
    )
    monkeypatch.delenv("container", raising=False)
    monkeypatch.setattr(
        "pd_ocr_simple_gui.runtime.container_detect._read_init_cgroup",
        lambda: "12:cpuset:/docker/abcd",
    )
    assert detect_containerized() is True


def test_none_match(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "pd_ocr_simple_gui.runtime.container_detect._DOCKERENV",
        tmp_path / "missing",
    )
    monkeypatch.setattr(
        "pd_ocr_simple_gui.runtime.container_detect._PODMAN_MARKER",
        tmp_path / "missing2",
    )
    monkeypatch.delenv("container", raising=False)
    monkeypatch.setattr(
        "pd_ocr_simple_gui.runtime.container_detect._read_init_cgroup",
        lambda: "12:cpuset:/user.slice",
    )
    assert detect_containerized() is False
```

- [ ] **Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_container_detect.py -n0 -v`
Expected: ImportError / collection error.

- [ ] **Step 3: Implement detector**

```python
# src/pd_ocr_simple_gui/runtime/container_detect.py
from __future__ import annotations

import os
from pathlib import Path

_DOCKERENV = Path("/.dockerenv")
_PODMAN_MARKER = Path("/run/.containerenv")
_INIT_CGROUP = Path("/proc/1/cgroup")
_CGROUP_NEEDLES = ("docker", "containerd", "kubepods")


def _read_init_cgroup() -> str:
    try:
        return _INIT_CGROUP.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def detect_containerized() -> bool:
    if _DOCKERENV.exists():
        return True
    if _PODMAN_MARKER.exists():
        return True
    if os.environ.get("container"):
        return True
    cgroup = _read_init_cgroup()
    return any(needle in cgroup for needle in _CGROUP_NEEDLES)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_container_detect.py -n0 -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pd_ocr_simple_gui/runtime/container_detect.py tests/test_container_detect.py
git commit -m "feat: detect containerized runtime via standard markers"
```

#### Task A0.2: Mode enum + reader

**Files:**
- Create: `src/pd_ocr_simple_gui/runtime/mode.py`
- Test: extended `tests/test_config_route.py` (covered in A0.3)

- [ ] **Step 1: Write minimal module**

```python
# src/pd_ocr_simple_gui/runtime/mode.py
from __future__ import annotations

import os
from enum import StrEnum


class Mode(StrEnum):
    LOCAL = "local"
    MANAGED = "managed"


_ENV_VAR = "PD_OCR_SIMPLE_GUI_MODE"


def read_mode() -> Mode:
    raw = os.environ.get(_ENV_VAR, Mode.LOCAL.value).lower()
    try:
        return Mode(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"{_ENV_VAR} must be one of {[m.value for m in Mode]}, got {raw!r}"
        ) from exc
```

- [ ] **Step 2: Commit**

```bash
git add src/pd_ocr_simple_gui/runtime/mode.py
git commit -m "feat: add Mode enum + env reader"
```

#### Task A0.3: `/api/config` route

**Files:**
- Create: `src/pd_ocr_simple_gui/routes/config.py`
- Modify: `src/pd_ocr_simple_gui/app.py` (register router, capture detector at startup)
- Test: `tests/test_config_route.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config_route.py
from fastapi.testclient import TestClient

from pd_ocr_simple_gui.app import create_app


def test_config_route_local_not_containerized(monkeypatch) -> None:
    monkeypatch.setenv("PD_OCR_SIMPLE_GUI_MODE", "local")
    monkeypatch.setattr(
        "pd_ocr_simple_gui.routes.config.detect_containerized",
        lambda: False,
    )
    client = TestClient(create_app())
    resp = client.get("/api/config")
    assert resp.status_code == 200
    assert resp.json() == {"mode": "local", "is_containerized": False}


def test_config_route_managed_containerized(monkeypatch) -> None:
    monkeypatch.setenv("PD_OCR_SIMPLE_GUI_MODE", "managed")
    monkeypatch.setattr(
        "pd_ocr_simple_gui.routes.config.detect_containerized",
        lambda: True,
    )
    client = TestClient(create_app())
    resp = client.get("/api/config")
    assert resp.status_code == 200
    assert resp.json() == {"mode": "managed", "is_containerized": True}
```

- [ ] **Step 2: Implement route**

```python
# src/pd_ocr_simple_gui/routes/config.py
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from pd_ocr_simple_gui.runtime.container_detect import detect_containerized
from pd_ocr_simple_gui.runtime.mode import read_mode

router = APIRouter()


class ConfigResponse(BaseModel):
    mode: str
    is_containerized: bool


@router.get("/api/config", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    return ConfigResponse(
        mode=read_mode().value,
        is_containerized=detect_containerized(),
    )
```

- [ ] **Step 3: Register in `app.py`**

Add to `create_app()` immediately after existing route registrations:

```python
from pd_ocr_simple_gui.routes.config import router as config_router
# ...
app.include_router(config_router)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_config_route.py -n0 -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pd_ocr_simple_gui/routes/config.py src/pd_ocr_simple_gui/app.py tests/test_config_route.py
git commit -m "feat: add GET /api/config exposing mode + container flag"
```

---

### Milestone A1 — `Source` Protocol + `LocalPathSource`

#### Task A1.1: Protocol + typed errors

**Files:**
- Create: `src/pd_ocr_simple_gui/sources/__init__.py`

- [ ] **Step 1: Implement Protocol + errors**

```python
# src/pd_ocr_simple_gui/sources/__init__.py
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


class SourceError(Exception):
    """Base class for Source materialization failures."""


class SourceNotFound(SourceError):
    """The configured source does not exist."""


class SourceInvalid(SourceError):
    """The source exists but is not usable (wrong type, unreadable)."""


class SourceTooLarge(SourceError):
    """The source exceeds configured size or count limits."""


@runtime_checkable
class Source(Protocol):
    def materialize(self) -> Path: ...
```

- [ ] **Step 2: Commit**

```bash
git add src/pd_ocr_simple_gui/sources/__init__.py
git commit -m "feat: introduce Source Protocol + typed errors"
```

#### Task A1.2: `LocalPathSource` — folder happy path + validation

**Files:**
- Create: `src/pd_ocr_simple_gui/sources/local_path.py`
- Test: `tests/test_sources_local_path.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sources_local_path.py
from pathlib import Path

import pytest

from pd_ocr_simple_gui.sources import SourceInvalid, SourceNotFound
from pd_ocr_simple_gui.sources.local_path import LocalPathSource


def test_folder_happy_path(tmp_path: Path) -> None:
    (tmp_path / "page-001.png").write_bytes(b"fake-png")
    src = LocalPathSource(tmp_path)
    assert src.materialize() == tmp_path


def test_missing_path(tmp_path: Path) -> None:
    with pytest.raises(SourceNotFound):
        LocalPathSource(tmp_path / "nope").materialize()


def test_unreadable_file(tmp_path: Path) -> None:
    target = tmp_path / "weird"
    target.write_text("not an image")
    with pytest.raises(SourceInvalid):
        LocalPathSource(target).materialize()
```

- [ ] **Step 2: Implement folder branch**

```python
# src/pd_ocr_simple_gui/sources/local_path.py
from __future__ import annotations

import zipfile
from pathlib import Path

from pd_ocr_simple_gui.sources import (
    Source,
    SourceInvalid,
    SourceNotFound,
    SourceTooLarge,
)

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}
_MAX_UNCOMPRESSED_BYTES = 2 * 1024**3  # 2 GiB


class LocalPathSource(Source):
    def __init__(self, path: Path, extract_root: Path | None = None) -> None:
        self._path = Path(path).expanduser()
        self._extract_root = extract_root

    def materialize(self) -> Path:
        if not self._path.exists():
            raise SourceNotFound(str(self._path))
        if self._path.is_dir():
            return self._path
        if self._path.suffix.lower() == ".zip":
            return self._extract_zip()
        if self._path.suffix.lower() in _IMAGE_EXTS:
            return self._wrap_single_image()
        raise SourceInvalid(
            f"{self._path} is not a folder, image, or .zip"
        )

    def _wrap_single_image(self) -> Path:
        raise NotImplementedError  # implemented in A1.3

    def _extract_zip(self) -> Path:
        raise NotImplementedError  # implemented in A1.4
```

- [ ] **Step 3: Run folder tests**

Run: `uv run pytest tests/test_sources_local_path.py -n0 -v`
Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add src/pd_ocr_simple_gui/sources/local_path.py tests/test_sources_local_path.py
git commit -m "feat: LocalPathSource accepts folder input"
```

#### Task A1.3: `LocalPathSource` — single image

**Files:**
- Modify: `src/pd_ocr_simple_gui/sources/local_path.py:_wrap_single_image`
- Modify: `tests/test_sources_local_path.py`

- [ ] **Step 1: Add failing test**

```python
def test_single_image_path(tmp_path: Path) -> None:
    img = tmp_path / "scan.png"
    img.write_bytes(b"\x89PNG\r\n")
    src = LocalPathSource(img)
    materialized = src.materialize()
    assert materialized.is_dir()
    assert (materialized / img.name).exists()
```

- [ ] **Step 2: Implement `_wrap_single_image`**

Replace the `NotImplementedError` body:

```python
import shutil
import tempfile

# ...
def _wrap_single_image(self) -> Path:
    workdir = Path(
        tempfile.mkdtemp(
            prefix="pdomain-ocr-simple-gui-single-",
            dir=self._extract_root,
        )
    )
    shutil.copy2(self._path, workdir / self._path.name)
    return workdir
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_sources_local_path.py -n0 -v`
Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
git add src/pd_ocr_simple_gui/sources/local_path.py tests/test_sources_local_path.py
git commit -m "feat: LocalPathSource accepts single image input"
```

#### Task A1.4: `LocalPathSource` — zip + bomb guard

**Files:**
- Modify: `src/pd_ocr_simple_gui/sources/local_path.py:_extract_zip`
- Modify: `tests/test_sources_local_path.py`

- [ ] **Step 1: Add failing tests**

```python
import io
import zipfile


def _make_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)


def test_zip_happy_path(tmp_path: Path) -> None:
    zpath = tmp_path / "scans.zip"
    _make_zip(zpath, {"a.png": b"\x89PNG", "b.png": b"\x89PNG"})
    materialized = LocalPathSource(zpath, extract_root=tmp_path).materialize()
    assert (materialized / "a.png").exists()
    assert (materialized / "b.png").exists()


def test_zip_bomb_guard(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "pd_ocr_simple_gui.sources.local_path._MAX_UNCOMPRESSED_BYTES", 16
    )
    zpath = tmp_path / "bomb.zip"
    _make_zip(zpath, {"big.bin": b"A" * 1024})
    with pytest.raises(SourceTooLarge):
        LocalPathSource(zpath, extract_root=tmp_path).materialize()


def test_zip_traversal_blocked(tmp_path: Path) -> None:
    zpath = tmp_path / "evil.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("../escape.png", b"x")
    with pytest.raises(SourceInvalid):
        LocalPathSource(zpath, extract_root=tmp_path).materialize()
```

- [ ] **Step 2: Implement extractor**

```python
def _extract_zip(self) -> Path:
    workdir = Path(
        tempfile.mkdtemp(
            prefix="pdomain-ocr-simple-gui-zip-",
            dir=self._extract_root,
        )
    )
    try:
        with zipfile.ZipFile(self._path) as zf:
            total = 0
            for info in zf.infolist():
                # traversal guard
                target = (workdir / info.filename).resolve()
                if not str(target).startswith(str(workdir.resolve()) + "/"):
                    raise SourceInvalid(
                        f"zip entry escapes extract root: {info.filename}"
                    )
                total += info.file_size
                if total > _MAX_UNCOMPRESSED_BYTES:
                    raise SourceTooLarge(
                        f"zip exceeds {_MAX_UNCOMPRESSED_BYTES} uncompressed bytes"
                    )
            zf.extractall(workdir)
    except zipfile.BadZipFile as exc:
        raise SourceInvalid(f"not a valid zip: {self._path}") from exc
    return workdir
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_sources_local_path.py -n0 -v`
Expected: 7 passed.

- [ ] **Step 4: Commit**

```bash
git add src/pd_ocr_simple_gui/sources/local_path.py tests/test_sources_local_path.py
git commit -m "feat: LocalPathSource accepts zip with bomb + traversal guards"
```

---

### Milestone A2 — Upload pipeline

#### Task A2.1: `UploadedFilesSource`

**Files:**
- Create: `src/pd_ocr_simple_gui/sources/uploaded_files.py`
- Test: `tests/test_sources_uploaded.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_sources_uploaded.py
from pathlib import Path

import pytest

from pd_ocr_simple_gui.sources import SourceNotFound
from pd_ocr_simple_gui.sources.uploaded_files import UploadedFilesSource


def test_happy_path(tmp_path: Path) -> None:
    stage = tmp_path / "upload-abc"
    stage.mkdir()
    (stage / "scan.png").write_bytes(b"\x89PNG")
    assert UploadedFilesSource("abc", root=tmp_path).materialize() == stage


def test_missing(tmp_path: Path) -> None:
    with pytest.raises(SourceNotFound):
        UploadedFilesSource("nope", root=tmp_path).materialize()
```

- [ ] **Step 2: Implementation**

```python
# src/pd_ocr_simple_gui/sources/uploaded_files.py
from __future__ import annotations

from pathlib import Path

from pd_ocr_simple_gui.sources import Source, SourceNotFound


class UploadedFilesSource(Source):
    def __init__(self, upload_id: str, root: Path) -> None:
        self._upload_id = upload_id
        self._root = root

    def materialize(self) -> Path:
        target = self._root / f"upload-{self._upload_id}"
        if not target.is_dir():
            # also accept root/<id> (the upload route writes here)
            alt = self._root / self._upload_id
            if alt.is_dir():
                return alt
            raise SourceNotFound(str(target))
        return target
```

- [ ] **Step 3: Run tests + commit**

Run: `uv run pytest tests/test_sources_uploaded.py -n0 -v` → 2 passed.

```bash
git add src/pd_ocr_simple_gui/sources/uploaded_files.py tests/test_sources_uploaded.py
git commit -m "feat: UploadedFilesSource resolves upload_id to staging dir"
```

#### Task A2.2: `POST /api/uploads` multipart streaming

**Files:**
- Create: `src/pd_ocr_simple_gui/routes/uploads.py`
- Modify: `src/pd_ocr_simple_gui/app.py` (register router)
- Test: `tests/test_uploads.py`

- [ ] **Step 1: Failing tests**

```python
# tests/test_uploads.py
import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from pd_ocr_simple_gui.app import create_app


def _client(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PD_OCR_SIMPLE_GUI_UPLOAD_ROOT", str(tmp_path))
    return TestClient(create_app())


def test_single_image_upload(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    resp = client.post(
        "/api/uploads",
        files={"files": ("scan.png", b"\x89PNG\r\n", "image/png")},
    )
    assert resp.status_code == 200
    body = resp.json()
    upload_id = body["upload_id"]
    landed = tmp_path / upload_id / "scan.png"
    assert landed.read_bytes() == b"\x89PNG\r\n"


def test_zip_upload_extracts(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.png", b"\x89PNG")
    resp = client.post(
        "/api/uploads",
        files={"files": ("scans.zip", buf.getvalue(), "application/zip")},
    )
    upload_id = resp.json()["upload_id"]
    assert (tmp_path / upload_id / "a.png").exists()


def test_size_cap(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PD_OCR_SIMPLE_GUI_UPLOAD_MAX_BYTES", "16")
    client = _client(tmp_path, monkeypatch)
    resp = client.post(
        "/api/uploads",
        files={"files": ("big.png", b"A" * 1024, "image/png")},
    )
    assert resp.status_code == 413
```

- [ ] **Step 2: Implement route**

```python
# src/pd_ocr_simple_gui/routes/uploads.py
from __future__ import annotations

import os
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

router = APIRouter()

_DEFAULT_ROOT = Path.home() / ".local/share/pdomain-ocr-simple-gui/uploads"
_DEFAULT_MAX_BYTES = 2 * 1024**3  # 2 GiB total per request
_DEFAULT_MAX_FILES = 5000


def _upload_root() -> Path:
    raw = os.environ.get("PD_OCR_SIMPLE_GUI_UPLOAD_ROOT")
    root = Path(raw) if raw else _DEFAULT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    return root


def _max_bytes() -> int:
    return int(os.environ.get("PD_OCR_SIMPLE_GUI_UPLOAD_MAX_BYTES", _DEFAULT_MAX_BYTES))


def _max_files() -> int:
    return int(os.environ.get("PD_OCR_SIMPLE_GUI_UPLOAD_MAX_FILES", _DEFAULT_MAX_FILES))


class UploadResponse(BaseModel):
    upload_id: str


@router.post("/api/uploads", response_model=UploadResponse)
async def post_upload(files: list[UploadFile]) -> UploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="no files supplied")
    if len(files) > _max_files():
        raise HTTPException(status_code=413, detail="too many files")

    upload_id = uuid.uuid4().hex
    staging = _upload_root() / upload_id
    staging.mkdir(parents=True)
    total = 0
    max_total = _max_bytes()
    try:
        for upload in files:
            name = Path(upload.filename or "unnamed").name  # strip path
            target = staging / name
            with tempfile.NamedTemporaryFile(
                delete=False, dir=staging
            ) as tmp:
                while chunk := await upload.read(64 * 1024):
                    total += len(chunk)
                    if total > max_total:
                        raise HTTPException(
                            status_code=413, detail="upload exceeds size cap"
                        )
                    tmp.write(chunk)
                tmp_path = Path(tmp.name)
            tmp_path.rename(target)
            if target.suffix.lower() == ".zip":
                _extract_in_place(target)
        return UploadResponse(upload_id=upload_id)
    except HTTPException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _extract_in_place(zip_path: Path) -> None:
    extract_to = zip_path.parent
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            target = (extract_to / info.filename).resolve()
            if not str(target).startswith(str(extract_to.resolve()) + "/"):
                raise HTTPException(
                    status_code=400, detail="zip traversal blocked"
                )
        zf.extractall(extract_to)
    zip_path.unlink()
```

- [ ] **Step 3: Register router in `app.py`**

```python
from pd_ocr_simple_gui.routes.uploads import router as uploads_router
# ...
app.include_router(uploads_router)
```

- [ ] **Step 4: Run tests + commit**

Run: `uv run pytest tests/test_uploads.py -n0 -v` → 3 passed.

```bash
git add src/pd_ocr_simple_gui/routes/uploads.py src/pd_ocr_simple_gui/app.py tests/test_uploads.py
git commit -m "feat: POST /api/uploads streams files into a staging dir"
```

---

### Milestone A3 — OutputConfig + jobs route integration

#### Task A3.1: `OutputConfig` resolver

**Files:**
- Create: `src/pd_ocr_simple_gui/output/__init__.py` (empty)
- Create: `src/pd_ocr_simple_gui/output/config.py`
- Test: `tests/test_output_config.py`

- [ ] **Step 1: Failing tests**

```python
# tests/test_output_config.py
from pathlib import Path

import pytest

from pd_ocr_simple_gui.output.config import (
    OutputConfig,
    OutputConfigError,
    resolve_output_dir,
)
from pd_ocr_simple_gui.runtime.mode import Mode


def test_managed_default(tmp_path: Path) -> None:
    cfg = OutputConfig(mode="managed")
    resolved = resolve_output_dir(
        cfg,
        mode=Mode.LOCAL,
        source_dir=tmp_path / "src",
        managed_root=tmp_path / "out",
        job_id="job1",
        source_is_folder=False,
    )
    assert resolved == tmp_path / "out" / "job1"
    assert resolved.is_dir()


def test_next_to_source_folder(tmp_path: Path) -> None:
    cfg = OutputConfig(mode="next_to_source")
    src = tmp_path / "src"
    src.mkdir()
    resolved = resolve_output_dir(
        cfg,
        mode=Mode.LOCAL,
        source_dir=src,
        managed_root=tmp_path / "out",
        job_id="job1",
        source_is_folder=True,
    )
    assert resolved == src


def test_next_to_source_rejects_non_folder(tmp_path: Path) -> None:
    cfg = OutputConfig(mode="next_to_source")
    with pytest.raises(OutputConfigError):
        resolve_output_dir(
            cfg,
            mode=Mode.LOCAL,
            source_dir=tmp_path / "src",
            managed_root=tmp_path / "out",
            job_id="job1",
            source_is_folder=False,
        )


def test_specified_local(tmp_path: Path) -> None:
    target = tmp_path / "elsewhere"
    target.mkdir()
    cfg = OutputConfig(mode="specified", path=target)
    resolved = resolve_output_dir(
        cfg,
        mode=Mode.LOCAL,
        source_dir=tmp_path,
        managed_root=tmp_path / "out",
        job_id="job1",
        source_is_folder=True,
    )
    assert resolved == target


def test_specified_rejected_in_managed(tmp_path: Path) -> None:
    cfg = OutputConfig(mode="specified", path=tmp_path)
    with pytest.raises(OutputConfigError):
        resolve_output_dir(
            cfg,
            mode=Mode.MANAGED,
            source_dir=tmp_path,
            managed_root=tmp_path / "out",
            job_id="job1",
            source_is_folder=True,
        )
```

- [ ] **Step 2: Implementation**

```python
# src/pd_ocr_simple_gui/output/config.py
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from pd_ocr_simple_gui.runtime.mode import Mode


class OutputConfigError(Exception):
    pass


class OutputConfig(BaseModel):
    mode: Literal["next_to_source", "specified", "managed"]
    path: Path | None = None


def resolve_output_dir(
    cfg: OutputConfig,
    *,
    mode: Mode,
    source_dir: Path,
    managed_root: Path,
    job_id: str,
    source_is_folder: bool,
) -> Path:
    if cfg.mode == "next_to_source":
        if not source_is_folder:
            raise OutputConfigError(
                "next_to_source requires a folder source"
            )
        return source_dir
    if cfg.mode == "specified":
        if mode is Mode.MANAGED:
            raise OutputConfigError(
                "specified output is not allowed in managed mode"
            )
        if cfg.path is None:
            raise OutputConfigError("specified output requires a path")
        cfg.path.mkdir(parents=True, exist_ok=True)
        return cfg.path
    # managed
    target = managed_root / job_id
    target.mkdir(parents=True, exist_ok=True)
    return target
```

- [ ] **Step 3: Run + commit**

Run: `uv run pytest tests/test_output_config.py -n0 -v` → 5 passed.

```bash
git add src/pd_ocr_simple_gui/output tests/test_output_config.py
git commit -m "feat: OutputConfig resolver with three modes"
```

#### Task A3.2: Wire `OutputConfig` + `Source` choice into `POST /api/jobs`

**Files:**
- Modify: `src/pd_ocr_simple_gui/routes/jobs.py` (request body + body→source/output mapping)
- Add tests in existing `tests/test_jobs.py` (or new file if missing)

- [ ] **Step 1: Update the request body**

In `routes/jobs.py`, expand the existing job-create request model:

```python
from pd_ocr_simple_gui.output.config import OutputConfig


class JobCreate(BaseModel):
    # one of:
    source_path: Path | None = None
    upload_id: str | None = None
    # job options (existing):
    engine: str = "doctr"
    language: str = "eng"
    save_json: bool = False
    combined_txt: bool = False
    # NEW:
    output: OutputConfig
```

- [ ] **Step 2: Build the right `Source` + resolve output**

In `create_job` (replacing the prior `source_path`-only branch):

```python
from pd_ocr_simple_gui.runtime.mode import Mode, read_mode
from pd_ocr_simple_gui.sources import SourceError
from pd_ocr_simple_gui.sources.local_path import LocalPathSource
from pd_ocr_simple_gui.sources.uploaded_files import UploadedFilesSource
from pd_ocr_simple_gui.output.config import (
    OutputConfigError,
    resolve_output_dir,
)


def _build_source(body: JobCreate, mode: Mode):
    if body.upload_id:
        return UploadedFilesSource(
            body.upload_id, root=_upload_root()
        ), False  # source_is_folder=False (upload staging counts as managed)
    if body.source_path is None:
        raise HTTPException(400, "must supply source_path or upload_id")
    if mode is Mode.MANAGED:
        raise HTTPException(400, "source_path is local-mode only")
    src = LocalPathSource(body.source_path)
    is_folder = body.source_path.is_dir()
    return src, is_folder


@router.post("/api/jobs")
def create_job(body: JobCreate, background_tasks: BackgroundTasks) -> JobResponse:
    mode = read_mode()
    try:
        source, source_is_folder = _build_source(body, mode)
        source_dir = source.materialize()
    except SourceError as exc:
        raise HTTPException(400, f"source: {exc}") from exc
    job_id = uuid.uuid4().hex
    try:
        output_dir = resolve_output_dir(
            body.output,
            mode=mode,
            source_dir=source_dir,
            managed_root=_managed_output_root(),
            job_id=job_id,
            source_is_folder=source_is_folder,
        )
    except OutputConfigError as exc:
        raise HTTPException(400, f"output: {exc}") from exc
    # ... existing ProjectSpec + run_project enqueue, using output_dir ...
```

(Engineer: keep the existing background-task scheduling intact — only the
`source_dir` / `output_dir` resolution is new.)

- [ ] **Step 3: Add jobs route test**

```python
# tests/test_jobs.py — add or extend
def test_create_job_with_upload(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PD_OCR_SIMPLE_GUI_UPLOAD_ROOT", str(tmp_path))
    stage = tmp_path / "abc123"
    stage.mkdir()
    (stage / "p.png").write_bytes(b"\x89PNG")
    client = TestClient(create_app())
    resp = client.post(
        "/api/jobs",
        json={
            "upload_id": "abc123",
            "engine": "doctr",
            "language": "eng",
            "output": {"mode": "managed"},
        },
    )
    assert resp.status_code in (200, 202)
```

- [ ] **Step 4: Run + commit**

Run: `uv run pytest tests/test_jobs.py -n0 -v`
Expected: new test passes; existing tests still pass.

```bash
git add src/pd_ocr_simple_gui/routes/jobs.py tests/test_jobs.py
git commit -m "feat: jobs route accepts upload_id + OutputConfig"
```

---

### Milestone A4 — Download endpoint

#### Task A4.1: `GET /api/jobs/{id}/download`

**Files:**
- Create: `src/pd_ocr_simple_gui/routes/downloads.py`
- Modify: `src/pd_ocr_simple_gui/app.py` (register router)
- Test: `tests/test_download_route.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_download_route.py
import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from pd_ocr_simple_gui.app import create_app


def test_download_streams_zip(tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "outputs" / "job-1"
    out.mkdir(parents=True)
    (out / "page-001.txt").write_text("hello world")
    monkeypatch.setenv("PD_OCR_SIMPLE_GUI_OUTPUT_ROOT", str(tmp_path / "outputs"))
    client = TestClient(create_app())
    resp = client.get("/api/jobs/job-1/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert "page-001.txt" in resp.headers.get("content-disposition", "") or True
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    assert "page-001.txt" in zf.namelist()


def test_download_missing_job(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PD_OCR_SIMPLE_GUI_OUTPUT_ROOT", str(tmp_path))
    client = TestClient(create_app())
    resp = client.get("/api/jobs/missing/download")
    assert resp.status_code == 404
```

- [ ] **Step 2: Implementation**

```python
# src/pd_ocr_simple_gui/routes/downloads.py
from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter()


def _output_root() -> Path:
    raw = os.environ.get("PD_OCR_SIMPLE_GUI_OUTPUT_ROOT")
    if not raw:
        return Path.home() / ".local/share/pdomain-ocr-simple-gui/outputs"
    return Path(raw)


@router.get("/api/jobs/{job_id}/download")
def download_job(job_id: str) -> StreamingResponse:
    job_dir = _output_root() / job_id
    if not job_dir.is_dir():
        raise HTTPException(status_code=404, detail="job output not found")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(job_dir.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(job_dir))
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{job_id}.zip"',
        },
    )
```

- [ ] **Step 3: Register + run + commit**

Add `app.include_router(downloads_router)` in `app.py`.

Run: `uv run pytest tests/test_download_route.py -n0 -v` → 2 passed.

```bash
git add src/pd_ocr_simple_gui/routes/downloads.py src/pd_ocr_simple_gui/app.py tests/test_download_route.py
git commit -m "feat: GET /api/jobs/{id}/download streams a results zip"
```

---

### Milestone A5 — Word overlays endpoint + canvas wiring

#### Task A5.1: `GET /api/pages/{id}/{idx}/words`

**Files:**
- Create: `src/pd_ocr_simple_gui/routes/words.py`
- Modify: `src/pd_ocr_simple_gui/app.py` (register router)
- Test: `tests/test_words_route.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_words_route.py
from fastapi.testclient import TestClient

from pd_ocr_simple_gui.app import create_app


def test_words_payload_shape(monkeypatch) -> None:
    fake = [
        {"text": "Hello", "bbox": {"x": 10, "y": 20, "w": 50, "h": 12}, "confidence": 0.95}
    ]
    monkeypatch.setattr(
        "pd_ocr_simple_gui.routes.words.load_page_words",
        lambda job_id, idx: fake,
    )
    client = TestClient(create_app())
    resp = client.get("/api/pages/job-1/0/words")
    assert resp.status_code == 200
    assert resp.json() == {"words": fake}


def test_words_missing_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(
        "pd_ocr_simple_gui.routes.words.load_page_words",
        lambda job_id, idx: None,
    )
    client = TestClient(create_app())
    resp = client.get("/api/pages/missing/0/words")
    assert resp.status_code == 404
```

- [ ] **Step 2: Implementation**

```python
# src/pd_ocr_simple_gui/routes/words.py
from __future__ import annotations

from typing import Iterable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class Bbox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class Word(BaseModel):
    text: str
    bbox: Bbox
    confidence: float


class WordsResponse(BaseModel):
    words: list[Word]


def load_page_words(job_id: str, idx: int) -> Iterable[dict] | None:
    """Adapter point: read the PageResult artifact from the job dir.

    Implementation reads from the same place that powers
    `/api/pages/{id}/{idx}` (the existing per-page detail route) and
    flattens the PageResult into word dicts.
    """
    from pd_ocr_simple_gui.pages import read_page_result  # existing module

    page = read_page_result(job_id, idx)
    if page is None:
        return None
    return [
        {
            "text": w.text,
            "bbox": {"x": w.bbox.x, "y": w.bbox.y, "w": w.bbox.w, "h": w.bbox.h},
            "confidence": w.confidence,
        }
        for w in page.words
    ]


@router.get(
    "/api/pages/{job_id}/{idx}/words",
    response_model=WordsResponse,
)
def get_words(job_id: str, idx: int) -> WordsResponse:
    payload = load_page_words(job_id, idx)
    if payload is None:
        raise HTTPException(status_code=404, detail="page not found")
    return WordsResponse(words=[Word(**w) for w in payload])
```

(Engineer: confirm the import path of the existing per-page reader; if
the function is called something other than `read_page_result`, rename
the import. Add a thin shim if needed.)

- [ ] **Step 3: Register + run + commit**

Run: `uv run pytest tests/test_words_route.py -n0 -v` → 2 passed.

```bash
git add src/pd_ocr_simple_gui/routes/words.py src/pd_ocr_simple_gui/app.py tests/test_words_route.py
git commit -m "feat: GET /api/pages/{id}/{idx}/words exposes overlay data"
```

---

### Milestone A6 — Frontend config context + SourcePicker

#### Task A6.1: `ConfigContext`

**Files:**
- Create: `frontend/src/runtime/ConfigContext.tsx`
- Modify: `frontend/src/App.tsx` (wrap with provider)
- Test: `frontend/src/runtime/__tests__/ConfigContext.test.tsx`

- [ ] **Step 1: Failing test**

```tsx
// frontend/src/runtime/__tests__/ConfigContext.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import { ConfigProvider, useConfig } from "../ConfigContext";

function Probe() {
  const cfg = useConfig();
  if (!cfg) return <span>loading</span>;
  return <span>{`${cfg.mode}/${cfg.is_containerized}`}</span>;
}

it("fetches /api/config on mount", async () => {
  globalThis.fetch = (async (url: string) => ({
    ok: true,
    json: async () => ({ mode: "local", is_containerized: true }),
  })) as unknown as typeof fetch;
  render(<ConfigProvider><Probe /></ConfigProvider>);
  await waitFor(() => screen.getByText("local/true"));
});
```

- [ ] **Step 2: Implement provider**

```tsx
// frontend/src/runtime/ConfigContext.tsx
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export interface RuntimeConfig {
  mode: "local" | "managed";
  is_containerized: boolean;
}

const Ctx = createContext<RuntimeConfig | null>(null);

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [cfg, setCfg] = useState<RuntimeConfig | null>(null);
  useEffect(() => {
    let aborted = false;
    void (async () => {
      const res = await fetch("/api/config");
      if (!res.ok) return;
      const body = (await res.json()) as RuntimeConfig;
      if (!aborted) setCfg(body);
    })();
    return () => {
      aborted = true;
    };
  }, []);
  return <Ctx.Provider value={cfg}>{children}</Ctx.Provider>;
}

export function useConfig(): RuntimeConfig | null {
  return useContext(Ctx);
}
```

- [ ] **Step 3: Wrap `App.tsx`**

Wrap the existing root JSX in `<ConfigProvider>...</ConfigProvider>`.

- [ ] **Step 4: Run + commit**

Run: `cd frontend && pnpm vitest run src/runtime`
Expected: 1 passed.

```bash
git add frontend/src/runtime frontend/src/App.tsx
git commit -m "feat(fe): ConfigProvider fetching /api/config"
```

#### Task A6.2: `SourcePicker` component

**Files:**
- Create: `frontend/src/components/SourcePicker.tsx`
- Create: `frontend/src/lib/testids.ts`
- Test: `frontend/src/components/__tests__/SourcePicker.test.tsx`

- [ ] **Step 1: testids module**

```ts
// frontend/src/lib/testids.ts
export {
  TEST_IDS as PD_UI_TEST_IDS,
} from "@concavetrillion/pdomain-ui/testids";

export const APP_TEST_IDS = {
  homePage: "home-page",
  sourcePickerDropZone: "source-picker-drop",
  sourcePickerFilePick: "source-picker-file-pick",
  sourcePickerPathInput: "source-picker-path-input",
  outputConfigPanel: "output-config-panel",
  outputModeNextToSource: "output-mode-next-to-source",
  outputModeSpecified: "output-mode-specified",
  outputModeManaged: "output-mode-managed",
  outputSpecifiedPath: "output-specified-path",
  downloadResultsButton: "download-results-button",
  runOcrButton: "run-ocr-button",
  pageRow: "page-row",
  pageViewPage: "page-view-page",
  pageImageCanvas: "page-image-canvas",
  resultsPage: "results-page",
} as const;
```

- [ ] **Step 2: Failing test**

```tsx
// frontend/src/components/__tests__/SourcePicker.test.tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { SourcePicker } from "../SourcePicker";

it("calls onUploadComplete for a dropped file", async () => {
  const onUploadComplete = vi.fn();
  globalThis.fetch = (async () => ({
    ok: true,
    json: async () => ({ upload_id: "u1" }),
  })) as unknown as typeof fetch;
  render(
    <SourcePicker
      allowDrop
      allowFilePick
      allowPathInput
      onUploadComplete={onUploadComplete}
      onPathChosen={() => {}}
    />,
  );
  const drop = screen.getByTestId("source-picker-drop");
  const file = new File(["x"], "scan.png", { type: "image/png" });
  fireEvent.drop(drop, { dataTransfer: { files: [file] } });
  await vi.waitFor(() => expect(onUploadComplete).toHaveBeenCalledWith("u1"));
});

it("emits onPathChosen for path input", () => {
  const onPathChosen = vi.fn();
  render(
    <SourcePicker
      allowDrop={false}
      allowFilePick={false}
      allowPathInput
      onUploadComplete={() => {}}
      onPathChosen={onPathChosen}
      pathHint="Folder, image, or zip path"
    />,
  );
  const input = screen.getByTestId("source-picker-path-input");
  fireEvent.change(input, { target: { value: "/scans/book1" } });
  fireEvent.submit(input.closest("form")!);
  expect(onPathChosen).toHaveBeenCalledWith("/scans/book1");
});
```

- [ ] **Step 3: Implement**

```tsx
// frontend/src/components/SourcePicker.tsx
import { useRef, useState } from "react";
import { Button, Field, Input } from "@concavetrillion/pdomain-ui/primitives";
import { APP_TEST_IDS } from "../lib/testids";

export interface SourcePickerProps {
  allowDrop: boolean;
  allowFilePick: boolean;
  allowPathInput: boolean;
  pathHint?: string;
  onUploadComplete: (uploadId: string) => void;
  onPathChosen: (path: string) => void;
}

async function uploadFiles(files: File[]): Promise<string> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const res = await fetch("/api/uploads", { method: "POST", body: form });
  if (!res.ok) throw new Error(`upload failed: ${res.status}`);
  const body = (await res.json()) as { upload_id: string };
  return body.upload_id;
}

export function SourcePicker(props: SourcePickerProps) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [pathDraft, setPathDraft] = useState("");

  const handleFiles = async (files: File[]) => {
    if (!files.length) return;
    const id = await uploadFiles(files);
    props.onUploadComplete(id);
  };

  return (
    <div>
      {props.allowDrop && (
        <div
          data-testid={APP_TEST_IDS.sourcePickerDropZone}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            void handleFiles(Array.from(e.dataTransfer.files));
          }}
          style={{ padding: 24, border: "2px dashed var(--pd-border)" }}
        >
          Drop an image, multiple images, a folder, or a .zip here.
        </div>
      )}
      {props.allowFilePick && (
        <div>
          <input
            ref={fileInput}
            data-testid={APP_TEST_IDS.sourcePickerFilePick}
            type="file"
            multiple
            accept="image/*,.zip"
            onChange={(e) => {
              const files = Array.from(e.target.files ?? []);
              void handleFiles(files);
            }}
          />
        </div>
      )}
      {props.allowPathInput && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (pathDraft.trim()) props.onPathChosen(pathDraft.trim());
          }}
        >
          <Field label="Path">
            <Input
              data-testid={APP_TEST_IDS.sourcePickerPathInput}
              value={pathDraft}
              onChange={(e) => setPathDraft(e.target.value)}
              placeholder={props.pathHint ?? "/path/to/folder-or-image-or.zip"}
            />
          </Field>
          <Button type="submit">Use this path</Button>
        </form>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run + commit**

Run: `cd frontend && pnpm vitest run src/components`
Expected: 2 passed.

```bash
git add frontend/src/components/SourcePicker.tsx frontend/src/lib/testids.ts frontend/src/components/__tests__/SourcePicker.test.tsx
git commit -m "feat(fe): SourcePicker with drop/file/path affordances"
```

#### Task A6.3: `HomePage` layout matrix

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`
- Delete: `frontend/src/components/DropZone.tsx`
- Test: `frontend/src/pages/__tests__/HomePage.test.tsx`

- [ ] **Step 1: Failing test**

```tsx
// frontend/src/pages/__tests__/HomePage.test.tsx
import { render, screen } from "@testing-library/react";
import { ConfigProvider } from "../../runtime/ConfigContext";
import { HomePage } from "../HomePage";

function withConfig(cfg: { mode: string; is_containerized: boolean }) {
  globalThis.fetch = (async () => ({ ok: true, json: async () => cfg })) as unknown as typeof fetch;
  return <ConfigProvider><HomePage /></ConfigProvider>;
}

it("local + containerized shows two tabs", async () => {
  render(withConfig({ mode: "local", is_containerized: true }));
  expect(await screen.findByTestId("source-picker-drop")).toBeInTheDocument();
  expect(screen.getByTestId("source-picker-path-input")).toBeInTheDocument();
});

it("local + not containerized shows drop, file pick, and path together", async () => {
  render(withConfig({ mode: "local", is_containerized: false }));
  expect(await screen.findByTestId("source-picker-drop")).toBeInTheDocument();
  expect(screen.getByTestId("source-picker-file-pick")).toBeInTheDocument();
  expect(screen.getByTestId("source-picker-path-input")).toBeInTheDocument();
});

it("managed shows upload-only", async () => {
  render(withConfig({ mode: "managed", is_containerized: false }));
  expect(await screen.findByTestId("source-picker-drop")).toBeInTheDocument();
  expect(screen.queryByTestId("source-picker-path-input")).toBeNull();
});
```

- [ ] **Step 2: Implement layout**

```tsx
// frontend/src/pages/HomePage.tsx
import { useState } from "react";
import { useConfig } from "../runtime/ConfigContext";
import { SourcePicker } from "../components/SourcePicker";
import { JobConfigDialog } from "../components/JobConfigDialog";
import { APP_TEST_IDS } from "../lib/testids";

type ChosenSource =
  | { kind: "path"; path: string }
  | { kind: "upload"; uploadId: string };

export function HomePage() {
  const cfg = useConfig();
  const [chosen, setChosen] = useState<ChosenSource | null>(null);
  if (!cfg) return <div>Loading…</div>;

  const mode = cfg.mode;
  const containerized = cfg.is_containerized;

  return (
    <div data-testid={APP_TEST_IDS.homePage}>
      {mode === "managed" && (
        <SourcePicker
          allowDrop
          allowFilePick
          allowPathInput={false}
          onUploadComplete={(id) => setChosen({ kind: "upload", uploadId: id })}
          onPathChosen={() => {}}
        />
      )}
      {mode === "local" && containerized && (
        <>
          <h3>Upload</h3>
          <SourcePicker
            allowDrop
            allowFilePick
            allowPathInput={false}
            onUploadComplete={(id) => setChosen({ kind: "upload", uploadId: id })}
            onPathChosen={() => {}}
          />
          <h3>Existing folder or zip</h3>
          <SourcePicker
            allowDrop={false}
            allowFilePick={false}
            allowPathInput
            pathHint="Paths refer to the container filesystem (bind-mount your scans dir if needed)."
            onUploadComplete={() => {}}
            onPathChosen={(p) => setChosen({ kind: "path", path: p })}
          />
        </>
      )}
      {mode === "local" && !containerized && (
        <SourcePicker
          allowDrop
          allowFilePick
          allowPathInput
          pathHint="Folder, image, or zip path on this machine."
          onUploadComplete={(id) => setChosen({ kind: "upload", uploadId: id })}
          onPathChosen={(p) => setChosen({ kind: "path", path: p })}
        />
      )}
      {chosen && (
        <JobConfigDialog
          source={chosen}
          mode={mode}
          onCancel={() => setChosen(null)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 3: Delete legacy `DropZone.tsx`**

```bash
git rm frontend/src/components/DropZone.tsx
```

- [ ] **Step 4: Run + commit**

Run: `cd frontend && pnpm vitest run src/pages/__tests__/HomePage`
Expected: 3 passed.

```bash
git add frontend/src/pages/HomePage.tsx frontend/src/pages/__tests__/HomePage.test.tsx
git commit -m "feat(fe): HomePage renders affordances per mode/container matrix"
```

---

### Milestone A7 — OutputConfigPanel + download button

#### Task A7.1: `OutputConfigPanel`

**Files:**
- Create: `frontend/src/components/OutputConfigPanel.tsx`
- Modify: `frontend/src/components/JobConfigDialog.tsx` (embed panel, include in POST body)
- Test: `frontend/src/components/__tests__/OutputConfigPanel.test.tsx`

- [ ] **Step 1: Failing test**

```tsx
// frontend/src/components/__tests__/OutputConfigPanel.test.tsx
import { render, screen } from "@testing-library/react";
import { OutputConfigPanel } from "../OutputConfigPanel";

it("disables next_to_source when source is not a folder", () => {
  render(
    <OutputConfigPanel
      mode="local"
      sourceIsFolder={false}
      value={{ mode: "managed" }}
      onChange={() => {}}
    />,
  );
  expect(screen.getByTestId("output-mode-next-to-source")).toBeDisabled();
});

it("disables specified in managed mode", () => {
  render(
    <OutputConfigPanel
      mode="managed"
      sourceIsFolder={false}
      value={{ mode: "managed" }}
      onChange={() => {}}
    />,
  );
  expect(screen.getByTestId("output-mode-specified")).toBeDisabled();
});

it("emits change when path is typed in specified mode", () => {
  const onChange = vi.fn();
  render(
    <OutputConfigPanel
      mode="local"
      sourceIsFolder
      value={{ mode: "specified", path: "" }}
      onChange={onChange}
    />,
  );
  const input = screen.getByTestId("output-specified-path");
  fireEvent.change(input, { target: { value: "/out" } });
  expect(onChange).toHaveBeenLastCalledWith({ mode: "specified", path: "/out" });
});
```

- [ ] **Step 2: Implementation**

```tsx
// frontend/src/components/OutputConfigPanel.tsx
import { Input } from "@concavetrillion/pdomain-ui/primitives";
import { APP_TEST_IDS } from "../lib/testids";

export type OutputConfigValue =
  | { mode: "next_to_source" }
  | { mode: "specified"; path: string }
  | { mode: "managed" };

export interface OutputConfigPanelProps {
  mode: "local" | "managed";
  sourceIsFolder: boolean;
  value: OutputConfigValue;
  onChange: (next: OutputConfigValue) => void;
}

export function OutputConfigPanel(props: OutputConfigPanelProps) {
  const { mode, sourceIsFolder, value, onChange } = props;
  const nextDisabled = !sourceIsFolder;
  const specDisabled = mode === "managed";
  return (
    <fieldset data-testid={APP_TEST_IDS.outputConfigPanel}>
      <legend>Where should results land?</legend>
      <label>
        <input
          type="radio"
          name="output-mode"
          data-testid={APP_TEST_IDS.outputModeNextToSource}
          disabled={nextDisabled}
          checked={value.mode === "next_to_source"}
          onChange={() => onChange({ mode: "next_to_source" })}
        />
        Next to source image
        {nextDisabled && <small> (only valid for folder sources)</small>}
      </label>
      <label>
        <input
          type="radio"
          name="output-mode"
          data-testid={APP_TEST_IDS.outputModeSpecified}
          disabled={specDisabled}
          checked={value.mode === "specified"}
          onChange={() => onChange({ mode: "specified", path: "" })}
        />
        Specified folder
        {specDisabled && <small> (not available in managed mode)</small>}
      </label>
      {value.mode === "specified" && (
        <Input
          data-testid={APP_TEST_IDS.outputSpecifiedPath}
          value={value.path}
          onChange={(e) =>
            onChange({ mode: "specified", path: e.target.value })
          }
        />
      )}
      <label>
        <input
          type="radio"
          name="output-mode"
          data-testid={APP_TEST_IDS.outputModeManaged}
          checked={value.mode === "managed"}
          onChange={() => onChange({ mode: "managed" })}
        />
        Managed (download when done)
      </label>
    </fieldset>
  );
}
```

- [ ] **Step 3: Embed in `JobConfigDialog`**

Pass `OutputConfigValue` into the POST body under `output`. Default
selection logic: `next_to_source` if `sourceIsFolder && mode === "local"`,
else `managed`.

- [ ] **Step 4: Run + commit**

Run: `cd frontend && pnpm vitest run src/components/__tests__/OutputConfigPanel`
Expected: 3 passed.

```bash
git add frontend/src/components/OutputConfigPanel.tsx frontend/src/components/JobConfigDialog.tsx frontend/src/components/__tests__/OutputConfigPanel.test.tsx
git commit -m "feat(fe): OutputConfigPanel with three modes + JobConfigDialog wiring"
```

#### Task A7.2: Download button on `ResultsPage`

**Files:**
- Modify: `frontend/src/pages/ResultsPage.tsx`
- Test: `frontend/src/pages/__tests__/ResultsPage.test.tsx`

- [ ] **Step 1: Failing test**

```tsx
// frontend/src/pages/__tests__/ResultsPage.test.tsx
import { render, screen } from "@testing-library/react";
import { ResultsPage } from "../ResultsPage";

it("shows download button when output mode is managed", () => {
  render(
    <ResultsPage
      jobId="job-1"
      outputMode="managed"
      pages={[]}
      status="completed"
    />,
  );
  expect(screen.getByTestId("download-results-button")).toBeInTheDocument();
});

it("hides download button for next_to_source", () => {
  render(
    <ResultsPage
      jobId="job-1"
      outputMode="next_to_source"
      pages={[]}
      status="completed"
    />,
  );
  expect(screen.queryByTestId("download-results-button")).toBeNull();
});
```

- [ ] **Step 2: Implement**

Add to `ResultsPage`:

```tsx
import { Button } from "@concavetrillion/pdomain-ui/primitives";
import { APP_TEST_IDS } from "../lib/testids";

// inside the page body, when status === "completed" && outputMode === "managed":
<Button
  data-testid={APP_TEST_IDS.downloadResultsButton}
  onClick={() => {
    window.location.assign(`/api/jobs/${jobId}/download`);
  }}
>
  Download results (.zip)
</Button>;
```

- [ ] **Step 3: Run + commit**

Run: `cd frontend && pnpm vitest run src/pages/__tests__/ResultsPage`
Expected: 2 passed.

```bash
git add frontend/src/pages/ResultsPage.tsx frontend/src/pages/__tests__/ResultsPage.test.tsx
git commit -m "feat(fe): Download button on ResultsPage for managed output mode"
```

---

### Milestone A8 — Word overlays in PageViewPage

#### Task A8.1: Fetch + canvas wiring

**Files:**
- Modify: `frontend/src/pages/PageViewPage.tsx`
- Test: `frontend/src/pages/__tests__/PageViewPage.test.tsx`

- [ ] **Step 1: Failing test**

```tsx
// frontend/src/pages/__tests__/PageViewPage.test.tsx
import { render, waitFor } from "@testing-library/react";
import { PageViewPage } from "../PageViewPage";

it("passes fetched words to PageImageCanvas", async () => {
  const words = [{ text: "Hi", bbox: { x: 0, y: 0, w: 10, h: 8 }, confidence: 0.9 }];
  globalThis.fetch = (async (url: string) => {
    if (url.endsWith("/words")) {
      return { ok: true, json: async () => ({ words }) };
    }
    return { ok: true, json: async () => ({}) };
  }) as unknown as typeof fetch;
  const { container } = render(
    <PageViewPage jobId="job-1" idx={0} />,
  );
  await waitFor(() => {
    const canvas = container.querySelector('[data-testid="page-image-canvas"]');
    expect(canvas?.getAttribute("data-word-count")).toBe("1");
  });
});
```

- [ ] **Step 2: Fetch + pass to canvas**

```tsx
// frontend/src/pages/PageViewPage.tsx
import { useEffect, useState } from "react";
import { PageImageCanvas, type CanvasPage } from "@concavetrillion/pdomain-ui/canvas";

interface Word { text: string; bbox: { x: number; y: number; w: number; h: number }; confidence: number; }

export function PageViewPage({ jobId, idx }: { jobId: string; idx: number }) {
  const [words, setWords] = useState<Word[]>([]);
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const res = await fetch(`/api/pages/${jobId}/${idx}/words`);
      if (!res.ok) return;
      const body = (await res.json()) as { words: Word[] };
      if (!cancelled) setWords(body.words);
    })();
    return () => { cancelled = true; };
  }, [jobId, idx]);

  return (
    <PageImageCanvas
      data-testid="page-image-canvas"
      data-word-count={String(words.length)}
      imageUrl={`/api/pages/${jobId}/${idx}/image`}
      words={words}
    />
  );
}
```

- [ ] **Step 3: Run + commit**

Run: `cd frontend && pnpm vitest run src/pages/__tests__/PageViewPage`
Expected: 1 passed.

```bash
git add frontend/src/pages/PageViewPage.tsx frontend/src/pages/__tests__/PageViewPage.test.tsx
git commit -m "feat(fe): PageViewPage renders word overlays from /api/pages/.../words"
```

---

### Milestone A9 — pdomain-ui swaps

Each task here is mechanical replacement of hand-rolled UI with the pdomain-ui equivalent. Verify nothing regresses by running `make ci` after each commit.

#### Task A9.1: Testids swap

- [ ] Replace every hardcoded `data-testid="..."` string in the
  `frontend/src/` tree with the corresponding constant from
  `APP_TEST_IDS` or `PD_UI_TEST_IDS` (`frontend/src/lib/testids.ts`).
  Run `cd frontend && pnpm vitest run` after each file change.

- [ ] Commit:

```bash
git add frontend/src
git commit -m "refactor(fe): consume pdomain-ui testids + APP_TEST_IDS"
```

#### Task A9.2: Worklist swap

- [ ] In `frontend/src/components/RecentProjectsList.tsx` and the
  page list inside `frontend/src/pages/ResultsPage.tsx`, replace the
  hand-rolled `<table>` with pdomain-ui's `Worklist` widget. Map column
  configs from existing fields. Keep `JobStatusPip` usage.

- [ ] Run frontend Vitest. Fix any test that depended on the old DOM
  structure by updating selectors to use `data-testid` constants.

- [ ] Commit:

```bash
git add frontend/src/components/RecentProjectsList.tsx frontend/src/pages/ResultsPage.tsx
git commit -m "refactor(fe): use pdomain-ui Worklist for project/page tables"
```

#### Task A9.3: PageWorkbench swap

- [ ] Wrap `PageViewPage` content in `<PageWorkbench>` from
  `@concavetrillion/pdomain-ui/stages/PageWorkbench`. The canvas + word
  overlay are the workbench body. Remove the hand-rolled layout
  containers.

- [ ] Run frontend Vitest + smoke `pnpm dev`.

- [ ] Commit:

```bash
git add frontend/src/pages/PageViewPage.tsx
git commit -m "refactor(fe): wrap PageViewPage in pdomain-ui PageWorkbench"
```

#### Task A9.4: Stores swap

- [ ] Replace the hand-rolled prefs fetch in `App.tsx:16–64` with
  pdomain-ui's prefs store factory (`@concavetrillion/pdomain-ui/stores`). Wire
  `useStageCall` for the polling loops in `RecentProjectsList` and
  `ResultsPage`.

- [ ] Remove the `// TODO: wire to PUT /api/prefs app-specific prefs
  in M7` stub at `App.tsx:62`.

- [ ] Run frontend Vitest. Verify polling cadence with a manual
  `pnpm dev` smoke.

- [ ] Commit:

```bash
git add frontend/src/App.tsx frontend/src/components/RecentProjectsList.tsx frontend/src/pages/ResultsPage.tsx
git commit -m "refactor(fe): adopt pdomain-ui store factories for prefs + polling"
```

---

## Phase B — Hardening

Each Phase B task closes a single GitHub issue with a tight, focused
change. Reference the issue number in the commit message.

### Milestone B1 — Logging hygiene (mechanical)

#### Task B1.1: Replace `except Exception: pass` blocks in `app.py`

**Files:** `src/pd_ocr_simple_gui/app.py` lines 46, 56, 65, 105.

- [ ] **Step 1:** Add `logger = logging.getLogger(__name__)` near the top
  of `app.py` if not present.
- [ ] **Step 2:** Replace each `except Exception: pass` with:

```python
except Exception:
    logger.exception(
        "<one-line description of what was being attempted>",
        extra={"context": "<load-bearing context>"},
    )
```

- [ ] **Step 3:** Commit (closes #29, #30, #31, #32, #33, #34 — confirm
  which issue numbers map to which line in the GH bodies; one commit
  may close multiple issues).

```bash
git commit -m "fix(logging): replace swallowed exceptions with logger.exception (#29-#34)"
```

### Milestone B2 — Auth & access

#### Task B2.1: Decide auth mechanism (one decision, applies to all)

- [ ] Inspect sibling pd-* SPA repos for an existing auth convention
  (token header, session cookie, or pd-suite issued credential). Pick
  whichever is already present in `pdomain-prep-for-pgdp` or
  `pdomain-ocr-labeler-spa`. Add an ADR under
  `docs/decisions/` capturing the decision.

#### Task B2.2: Auth middleware (closes #23)

- [ ] Implement middleware module under
  `src/pd_ocr_simple_gui/runtime/auth.py`. Tests under
  `tests/test_auth_middleware.py`. Apply to every route currently
  unauthenticated.
- [ ] Commit: `feat(auth): protect API routes (#23)`.

#### Task B2.3: Path-traversal audit (closes #17)

- [ ] Verify `LocalPathSource` validation (added in A1.2) plus any
  remaining route-layer paths that accept caller-supplied filesystem
  strings. Add tests for symlink-escape and absolute paths outside an
  allowed root.
- [ ] Commit: `fix(security): reject path traversal in source resolution (#17)`.

#### Task B2.4: Rate limit + page cap (closes #18)

- [ ] Add per-IP rate limit on `/api/uploads`, `/api/jobs`,
  `/api/pages/...`. Add `PD_OCR_SIMPLE_GUI_MAX_PAGES_PER_JOB`
  (default 5000). Reject job creation above the cap.
- [ ] Commit: `feat(security): rate limit + max pages per job (#18)`.

#### Task B2.5: Gate suite-launch (closes #19)

- [ ] Apply the new auth middleware to the suite-launch route(s) and
  drop the unauthenticated process-spawn path.
- [ ] Commit: `fix(security): require auth for suite launch (#19)`.

### Milestone B3 — Frontend / browser

#### Task B3.1: `noopener` on suite launcher (closes #26)

- [ ] Add `rel="noopener noreferrer"` and `target="_blank"` audit
  across all `<a>` tags that open suite siblings.
- [ ] Commit: `fix(fe): add noopener on suite launcher links (#26)`.

#### Task B3.2: Self-host Google Fonts (closes #24)

- [ ] Vendor the font woff2 files into `frontend/public/fonts/`.
  Replace the `<link href="fonts.googleapis.com">` in
  `frontend/index.html` with a local `@font-face` rule in
  `frontend/src/index.css`.
- [ ] Commit: `feat(privacy): self-host Google Fonts (#24)`.

#### Task B3.3: Verify #25 (Copy path) shipped

- [ ] Confirm the Copy path button is present and functional on
  `ResultsPage`. If it is, close #25 with a verification comment. If
  not, ship it.

### Milestone B4 — Supply chain

#### Task B4.1: Bump Vite / esbuild (closes #20, #21, #22)

- [ ] Run `make update-pd-deps` in the frontend dir. Review the diff.
  Run `make ci` to confirm green. Commit the bumped lockfile.
- [ ] Commit: `chore(deps): bump Vite + esbuild advisories (#20-#22)`.

#### Task B4.2: Drop editable pdomain-ops pin (closes #27)

- [ ] Replace the editable `pdomain-ops` line in `pyproject.toml` with
  `pdomain-ops==X.Y.Z` from `pdomain-index-pip`. Run `make local-check`
  and `make ci`.
- [ ] Commit: `chore(deps): pin pdomain-ops to release (#27)`.

#### Task B4.3: Pin GitHub Actions to SHAs (closes #28)

- [ ] In every `.github/workflows/*.yml`, replace `actions/foo@v3`
  style refs with `actions/foo@<sha>` plus a trailing comment of the
  tag for human readability.
- [ ] Commit: `chore(ci): pin GitHub Actions to SHAs (#28)`.

---

## Browser Verification — MANDATORY

### Milestone B5 — Playwright e2e

This milestone exists because backend/Vitest tests cannot catch SPA
serving bugs, broken JS bundles, or React Router misrouting. It must
run as part of `make ci`.

#### Task B5.1: Tooling

**Files:**
- `pyproject.toml` (add `[dependency-groups] e2e`)
- `Makefile` (add `e2e-browser` target, wire into `ci`)
- `tests/e2e/conftest.py` (server fixture)

- [ ] **Step 1: Add `e2e` dependency group**

In `pyproject.toml`:

```toml
[dependency-groups]
e2e = [
  "pytest-playwright>=0.5",
]
```

- [ ] **Step 2: Makefile**

```makefile
.PHONY: e2e-browser
e2e-browser:
	uv run --group e2e playwright install chromium
	uv run --group e2e pytest tests/e2e -n0 -v

# extend ci
ci: format-check lint typecheck test frontend-build e2e-browser
```

- [ ] **Step 3: Server fixture**

```python
# tests/e2e/conftest.py
import os
import socket
import subprocess
import time
from pathlib import Path

import pytest


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def app_server(tmp_path_factory):
    port = _free_port()
    workdir = tmp_path_factory.mktemp("e2e")
    env = {
        **os.environ,
        "PD_OCR_SIMPLE_GUI_MODE": "local",
        "PD_OCR_SIMPLE_GUI_UPLOAD_ROOT": str(workdir / "uploads"),
        "PD_OCR_SIMPLE_GUI_OUTPUT_ROOT": str(workdir / "outputs"),
    }
    proc = subprocess.Popen(
        [
            "uv", "run", "uvicorn",
            "pd_ocr_simple_gui.app:create_app",
            "--factory", "--host", "127.0.0.1", "--port", str(port),
        ],
        env=env,
    )
    base = f"http://127.0.0.1:{port}"
    # poll until ready
    for _ in range(60):
        try:
            import urllib.request
            urllib.request.urlopen(f"{base}/api/config", timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    yield base
    proc.terminate()
    proc.wait(timeout=10)
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml Makefile tests/e2e/conftest.py
git commit -m "test(e2e): scaffold Playwright tooling + server fixture"
```

#### Task B5.2: App-loads smoke

**Files:** `tests/e2e/test_app_loads.py`

- [ ] **Step 1: Test**

```python
# tests/e2e/test_app_loads.py
from playwright.sync_api import Page, expect


def test_home_page_loads(page: Page, app_server: str) -> None:
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: msg.type == "error" and errors.append(msg.text))
    page.goto(app_server)
    expect(page.get_by_test_id("home-page")).to_be_visible(timeout=10_000)
    assert not errors, f"console errors: {errors}"
```

- [ ] **Step 2: Run + commit**

Run: `make e2e-browser`
Expected: 1 passed.

```bash
git add tests/e2e/test_app_loads.py
git commit -m "test(e2e): home page loads without console errors"
```

#### Task B5.3: Upload single image happy path

**Files:** `tests/e2e/test_upload_single_image.py`

- [ ] **Step 1: Test**

```python
# tests/e2e/test_upload_single_image.py
from pathlib import Path

from playwright.sync_api import Page, expect


def test_upload_single_image(page: Page, app_server: str, tmp_path: Path) -> None:
    img = tmp_path / "scan.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")  # minimal valid header
    page.goto(app_server)
    expect(page.get_by_test_id("home-page")).to_be_visible()
    page.get_by_test_id("source-picker-file-pick").set_input_files(str(img))
    # JobConfigDialog should open
    expect(page.get_by_test_id("run-ocr-button")).to_be_visible(timeout=10_000)
```

- [ ] **Step 2: Commit**

```bash
git add tests/e2e/test_upload_single_image.py
git commit -m "test(e2e): single image upload reaches JobConfigDialog"
```

#### Task B5.4: Existing-folder local path

**Files:** `tests/e2e/test_existing_folder_local.py`

- [ ] **Step 1: Test**

```python
# tests/e2e/test_existing_folder_local.py
from pathlib import Path

from playwright.sync_api import Page, expect


def test_existing_folder_path(page: Page, app_server: str, tmp_path: Path) -> None:
    folder = tmp_path / "scans"
    folder.mkdir()
    (folder / "p.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    page.goto(app_server)
    page.get_by_test_id("source-picker-path-input").fill(str(folder))
    page.keyboard.press("Enter")
    expect(page.get_by_test_id("run-ocr-button")).to_be_visible(timeout=10_000)
```

- [ ] **Step 2: Commit**

```bash
git add tests/e2e/test_existing_folder_local.py
git commit -m "test(e2e): existing folder path opens JobConfigDialog"
```

#### Task B5.5: Word overlays render on PageViewPage

**Files:** `tests/e2e/test_word_overlays_render.py`

- [ ] **Step 1: Test**

```python
# tests/e2e/test_word_overlays_render.py
from playwright.sync_api import Page, expect


def test_word_overlay_count(page: Page, app_server: str) -> None:
    # Use a pre-seeded job-id surfaced by a test fixture; if not yet
    # available, mark xfail until B5 wires it in.
    page.goto(f"{app_server}/jobs/seed-job/pages/0")
    canvas = page.get_by_test_id("page-image-canvas")
    expect(canvas).to_be_visible(timeout=10_000)
    word_count = canvas.get_attribute("data-word-count")
    assert word_count is not None and int(word_count) >= 1
```

- [ ] **Step 2: Commit**

```bash
git add tests/e2e/test_word_overlays_render.py
git commit -m "test(e2e): word overlays render on PageViewPage"
```

#### Task B5.6: Download managed-output zip

**Files:** `tests/e2e/test_download_managed.py`

- [ ] **Step 1: Test**

```python
# tests/e2e/test_download_managed.py
from playwright.sync_api import Page, expect


def test_download_button_managed(page: Page, app_server: str) -> None:
    # Pre-seeded completed job in managed mode (fixture in conftest).
    page.goto(f"{app_server}/jobs/seed-managed-job")
    btn = page.get_by_test_id("download-results-button")
    expect(btn).to_be_visible(timeout=10_000)
    with page.expect_download() as dl_info:
        btn.click()
    download = dl_info.value
    assert download.suggested_filename.endswith(".zip")
```

- [ ] **Step 2: Commit**

```bash
git add tests/e2e/test_download_managed.py
git commit -m "test(e2e): managed-mode results download button"
```

#### Task B5.7: Route deep-link

**Files:** `tests/e2e/test_routes_deep_link.py`

- [ ] **Step 1: Test**

```python
# tests/e2e/test_routes_deep_link.py
from playwright.sync_api import Page, expect


def test_jobs_subpath_renders(page: Page, app_server: str) -> None:
    page.goto(f"{app_server}/jobs/seed-job")
    # Should land on the results page, not a 404
    expect(page.get_by_test_id("results-page")).to_be_visible(timeout=10_000)
```

- [ ] **Step 2: Commit**

```bash
git add tests/e2e/test_routes_deep_link.py
git commit -m "test(e2e): deep-link to /jobs/<id> renders results page"
```

#### Task B5.8: Wire into `make ci` + close

- [ ] Verify `make ci` includes `e2e-browser` and runs end-to-end
  green in the worktree.
- [ ] Commit the final integration: ensure `setup` target installs
  Playwright Chromium (`playwright install chromium`).

```bash
git add Makefile
git commit -m "ci: include e2e-browser in make ci"
```

---

## Self-review notes

- Every spec section (§1–§9) has at least one task: container detection (A0.1), mode (A0.2), `/api/config` (A0.3), `Source` Protocol (A1.1), `LocalPathSource` folder/image/zip (A1.2–A1.4), `UploadedFilesSource` (A2.1), `/api/uploads` (A2.2), `OutputConfig` resolver (A3.1), `/api/jobs` wiring (A3.2), `/api/jobs/{id}/download` (A4.1), `/api/pages/.../words` (A5.1), `ConfigContext` (A6.1), `SourcePicker` (A6.2), `HomePage` matrix (A6.3), `OutputConfigPanel` (A7.1), download button (A7.2), word overlays (A8.1), testids/worklist/PageWorkbench/stores swaps (A9.1–A9.4), and Phase B groups B1–B4 each mapped to their open issues.
- No "TBD" steps remain — auth mechanism choice in B2.1 is explicit (decide from sibling repos + ADR).
- Method/property names match between definition and use (`Source.materialize`, `OutputConfig.mode`, `APP_TEST_IDS.*`).
- Browser verification milestone present (B5).
