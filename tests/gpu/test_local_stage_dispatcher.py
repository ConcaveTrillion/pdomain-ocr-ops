import pytest

from pdomain_ops.gpu.local_stage import LocalStageDispatcher, UnknownStageError
from pdomain_ops.gpu.types import StageResult


@pytest.mark.asyncio
async def test_construct_with_empty_registry():
    dispatcher = LocalStageDispatcher(registry={})
    assert dispatcher is not None


@pytest.mark.asyncio
async def test_run_stage_unknown_id_raises():
    dispatcher = LocalStageDispatcher(registry={})
    with pytest.raises(UnknownStageError) as exc_info:
        await dispatcher.run_stage("missing", "page-1")
    assert "missing" in str(exc_info.value)


@pytest.mark.asyncio
async def test_run_stage_dispatches_to_registered_impl(monkeypatch):
    monkeypatch.setenv("PDOMAIN_GPU_BACKEND", "cpu")

    async def fake(page_id, device, **kwargs):
        return {"foo": "bar"}

    registry = {("ocr", "cpu"): fake}
    dispatcher = LocalStageDispatcher(registry=registry)
    result = await dispatcher.run_stage("ocr", "page-1")
    assert isinstance(result, StageResult)
    assert result.stage_id == "ocr"
    assert result.page_id == "page-1"
    assert result.device == "cpu"
    assert result.duration_ms >= 0
    assert result.metadata == {"foo": "bar"}


@pytest.mark.asyncio
async def test_run_stage_falls_through_to_cpu_when_local_missing(monkeypatch):
    monkeypatch.setenv("PDOMAIN_GPU_BACKEND", "local")

    async def cpu_impl(page_id, device, **kwargs):
        return {}

    registry = {("ocr", "cpu"): cpu_impl}
    dispatcher = LocalStageDispatcher(registry=registry)
    # Should fall through from "local" to "cpu"
    result = await dispatcher.run_stage("ocr", "page-1")
    assert result.device == "cpu"


@pytest.mark.asyncio
async def test_run_stage_propagates_kwargs(monkeypatch):
    monkeypatch.setenv("PDOMAIN_GPU_BACKEND", "cpu")
    received_kwargs = {}

    async def impl(page_id, device, **kwargs):
        received_kwargs.update(kwargs)
        return {}

    registry = {("ocr", "cpu"): impl}
    dispatcher = LocalStageDispatcher(registry=registry)
    await dispatcher.run_stage("ocr", "page-1", threshold=0.9, mode="fast")
    assert received_kwargs == {"threshold": 0.9, "mode": "fast"}


@pytest.mark.asyncio
async def test_run_stage_accepts_cuda_id():
    async def fake(page_id, device, **kwargs):
        return {}

    registry = {("ocr", "local"): fake}
    dispatcher = LocalStageDispatcher(registry=registry)
    result = await dispatcher.run_stage("ocr", "p1", device="cuda:0")
    assert result.device == "local"  # registry hit, no silent cpu fallback


@pytest.mark.asyncio
async def test_run_stage_canonicalizes_resolver_output():
    # red-team catch: the resolver path must be canonicalized too, or a stored
    # "cuda:0" pref reintroduces the exact silent-cpu-fallback bug this fixes
    async def fake(page_id, device, **kwargs):
        return {}

    registry = {("ocr", "local"): fake}
    dispatcher = LocalStageDispatcher(registry=registry, device_resolver=lambda: "cuda:0")
    result = await dispatcher.run_stage("ocr", "p1")
    assert result.device == "local"
