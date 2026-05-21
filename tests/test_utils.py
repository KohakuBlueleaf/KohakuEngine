"""Tests for kohakuengine.utils."""

from pathlib import Path

import pytest

from kohakuengine.utils import ensure_py_extension, resolve_path


def test_resolve_path(tmp_path):
    p = tmp_path / "x.py"
    p.write_text("")
    assert resolve_path(str(p)) == p.resolve()


def test_ensure_py_extension_ok(tmp_path):
    ensure_py_extension(tmp_path / "x.py")  # no raise


def test_ensure_py_extension_fail(tmp_path):
    with pytest.raises(ValueError, match=".py"):
        ensure_py_extension(tmp_path / "x.txt")
