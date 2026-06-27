"""Tests for kohakuengine.utils."""

import sys

import pytest

from kohakuengine.utils import (
    add_script_dir_to_path,
    ensure_py_extension,
    importable_module_name,
    resolve_path,
)


def test_resolve_path(tmp_path):
    p = tmp_path / "x.py"
    p.write_text("")
    assert resolve_path(str(p)) == p.resolve()


def test_ensure_py_extension_ok(tmp_path):
    ensure_py_extension(tmp_path / "x.py")  # no raise


def test_ensure_py_extension_fail(tmp_path):
    with pytest.raises(ValueError, match=".py"):
        ensure_py_extension(tmp_path / "x.txt")


def test_add_script_dir_to_path_inserts_once(tmp_path, restore_import_state):
    script = tmp_path / "x.py"
    script.write_text("", encoding="utf-8")
    target = str(tmp_path.resolve())

    assert add_script_dir_to_path(script) == target
    assert sys.path[0] == target
    # Idempotent: a second call does not duplicate the entry.
    add_script_dir_to_path(script)
    assert sys.path.count(target) == 1


def test_importable_module_name_uses_stem(tmp_path):
    assert importable_module_name(tmp_path / "train.py") == "train"


def test_importable_module_name_falls_back_for_non_identifier(tmp_path):
    name = importable_module_name(tmp_path / "my-script.py")
    assert name.isidentifier()
    assert name == "_kohaku_script_my_script"


def test_importable_module_name_falls_back_for_keyword(tmp_path):
    # 'class' is a valid identifier but a reserved keyword -> not importable.
    name = importable_module_name(tmp_path / "class.py")
    assert name == "_kohaku_script_class"
