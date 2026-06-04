"""Tests for update version-check helpers."""

from pdomain_ops.suite.update import compare_versions, parse_index_versions

_SIMPLE_HTML = (
    '<a href="pdomain_ocr_simple_gui-0.9.0-py3-none-any.whl">x</a>'
    '<a href="pdomain_ocr_simple_gui-0.10.0-py3-none-any.whl">y</a>'
)


def test_parse_index_versions() -> None:
    assert parse_index_versions(_SIMPLE_HTML, "pdomain-ocr-simple-gui") == [
        "0.9.0",
        "0.10.0",
    ]


def test_compare_versions_update_available() -> None:
    assert compare_versions(current="0.9.0", latest="0.10.0") is True
    assert compare_versions(current="0.10.0", latest="0.10.0") is False
    assert compare_versions(current="0.11.0", latest="0.10.0") is False
