"""Packaging regression tests for pdomain-ops.

These assert invariants about how the project is *packaged*, not about the
running library.

Regression guard for the ``py.typed`` marker: hatchling only ships
``pdomain_ops/py.typed`` if the file exists in the package directory. If it
is ever deleted (or excluded by a future build-config change), downstream
consumers stop seeing pdomain-ops as a typed package and every imported
symbol degrades to ``Any`` under basedpyright/mypy. The sibling
``pdomain-book-tools`` ships its marker correctly; this test keeps
pdomain-ops aligned.
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = REPO_ROOT / "pdomain_ops"


def test_py_typed_marker_present_in_source() -> None:
    """The ``py.typed`` marker file must exist in the package directory.

    PEP 561: a package advertises inline type information by shipping an
    empty ``py.typed`` file. Without it, consumers treat every pdomain_ops
    symbol as ``Any``.
    """
    marker = PACKAGE_DIR / "py.typed"
    assert marker.is_file(), (
        f"{marker} is missing — pdomain-ops would ship without its PEP 561 "
        "typing marker and downstream consumers would see all symbols as Any."
    )


def test_py_typed_marker_shipped_in_wheel(tmp_path: Path) -> None:
    """Building a wheel must include ``pdomain_ops/py.typed``.

    The marker existing in source is necessary but not sufficient: a future
    change to ``[tool.hatch.build.targets.wheel]`` (force-include, artifacts,
    exclude globs) could silently drop it from the built distribution. Build
    a real wheel and assert the marker is inside it.
    """
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        # Fall back to `uv build` if the stdlib `build` frontend is unavailable.
        result = subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    assert result.returncode == 0, (
        f"wheel build failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    wheels = list(tmp_path.glob("pdomain_ops-*.whl"))
    assert wheels, f"no wheel produced in {tmp_path}"

    with zipfile.ZipFile(wheels[0]) as zf:
        names = zf.namelist()
    assert "pdomain_ops/py.typed" in names, (
        "pdomain_ops/py.typed is missing from the built wheel — the PEP 561 "
        f"typing marker would not ship. Wheel contents: {sorted(names)}"
    )
