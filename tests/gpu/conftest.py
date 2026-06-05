"""GPU test suite conftest — serialise all GPU tests under xdist.

WHY THIS FILE EXISTS
--------------------
pytest-xdist ``-n auto`` defaults to ``--dist=load``, which scatters tests
across workers with no ordering guarantees.  GPU tests that exercise
CUDA memory (OOM-retry logic, batch-size halving, etc.) contend for the
physical card when two workers run them simultaneously, causing spurious
OOM failures in tests whose whole purpose is to *test* OOM recovery.

FIX: ``--dist=loadgroup`` (set in ``[tool.pytest.ini_options].addopts``)
tells xdist to honour the ``xdist_group`` marker.  The hook below stamps
every test collected from *this* directory with ``xdist_group="gpu"``,
so xdist routes them all to a **single worker** — eliminating concurrent
GPU execution without skipping or xfail-ing any test.

The marker must be registered in ``[tool.pytest.ini_options].markers``
(``pyproject.toml``) so ``--strict-markers`` does not reject it.
"""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Stamp every test in tests/gpu/ with xdist_group='gpu'."""
    gpu_marker = pytest.mark.xdist_group("gpu")
    for item in items:
        # item.fspath is a py.path.local; compare with string suffix
        if "tests/gpu/" in str(item.fspath):
            item.add_marker(gpu_marker, append=False)
