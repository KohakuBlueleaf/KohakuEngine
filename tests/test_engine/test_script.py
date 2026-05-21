"""Tests for kohakuengine.engine.script."""

import pytest

from kohakuengine import Config, Script


def test_script_from_file(simple_script):
    s = Script(str(simple_script))
    assert s.is_module is False
    assert s.path == simple_script
    assert s.entrypoint is None
    assert s.name == "simple"


def test_script_file_with_entrypoint(simple_script):
    s = Script(f"{simple_script}:main")
    assert s.entrypoint == "main"
    assert s.is_module is False


def test_script_missing_file():
    with pytest.raises(FileNotFoundError):
        Script("nope.py")


def test_script_non_py_extension(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("")
    with pytest.raises(ValueError, match=".py"):
        Script(str(p))


def test_script_repr_file(simple_script):
    r = repr(Script(str(simple_script)))
    assert "Script(path=" in r


def test_script_repr_module():
    s = Script("os.path")
    assert "Script(module=os.path" in repr(s)


def test_script_module_simple():
    s = Script("os.path")
    assert s.is_module is True
    assert s.module_name == "os.path"
    assert s.name == "path"


def test_script_module_with_entrypoint():
    s = Script("os.path:join")
    assert s.is_module is True
    assert s.entrypoint == "join"


def test_script_module_not_found():
    with pytest.raises(ModuleNotFoundError):
        Script("totally.not.a.module.xyz")


def test_script_explicit_entrypoint_kwarg(simple_script):
    s = Script(str(simple_script), entrypoint="main")
    assert s.entrypoint == "main"


def test_script_explicit_entrypoint_not_overridden(simple_script):
    s = Script(f"{simple_script}:main", entrypoint="preset")
    # explicit kwarg wins -- colon doesn't override
    assert s.entrypoint == "preset"


def test_script_run_attached_method(simple_script):
    cfg = Config(globals_dict={"lr": 0.7})
    s = Script(str(simple_script), config=cfg)
    result = s.run()
    assert result == 0.7


def test_looks_like_module():
    assert Script._looks_like_module("a.b") is True
    assert Script._looks_like_module("a/b.py") is False
    assert Script._looks_like_module("script.py") is False
    assert Script._looks_like_module("script.py:func") is False
