"""Tests for kohakuengine.engine.executor."""

import sys

import pytest

from kohakuengine import Config, ConfigGenerator, Script, ScriptExecutor


def test_execute_basic(simple_script):
    cfg = Config(globals_dict={"lr": 0.99})
    s = Script(str(simple_script), config=cfg)
    assert ScriptExecutor(s).execute() == 0.99


def test_execute_no_config(simple_script):
    s = Script(str(simple_script))
    # main() runs without injection, returns the default lr=0.1
    assert ScriptExecutor(s).execute() == 0.1


def test_execute_with_args_kwargs(args_script):
    cfg = Config(globals_dict={}, args=[3], kwargs={"y": 4})
    s = Script(str(args_script), config=cfg)
    assert ScriptExecutor(s).execute() == 7


def test_execute_rejects_generator_directly(make_script):
    s = make_script("s.py", "def main(): return 1\nif __name__=='__main__':main()\n")
    gen = ConfigGenerator(iter([Config()]))
    script = Script(str(s), config=gen)
    with pytest.raises(TypeError, match="Flow for sweeps"):
        ScriptExecutor(script).execute()


def test_execute_no_entrypoint_returns_none(make_script):
    s = make_script("empty.py", "x = 1\n")
    script = Script(str(s))
    # No config, no entrypoint: returns None silently
    assert ScriptExecutor(script).execute() is None


def test_execute_no_entrypoint_with_config_raises(make_script):
    s = make_script("empty.py", "x = 1\n")
    script = Script(str(s), config=Config(globals_dict={"x": 2}))
    with pytest.raises(RuntimeError, match="No entrypoint"):
        ScriptExecutor(script).execute()


def test_execute_explicit_entrypoint(make_script):
    s = make_script(
        "s.py",
        """
        def helper(): return 'h'
        def main(): return 'm'
        """,
    )
    script = Script(str(s), entrypoint="helper")
    assert ScriptExecutor(script).execute() == "h"


def test_execute_module_path(tmp_path):
    pkg = tmp_path / "pkg_exec"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "mod.py").write_text("def main(): return 'M'\n")
    sys.path.insert(0, str(tmp_path))
    try:
        s = Script("pkg_exec.mod")
        assert ScriptExecutor(s).execute() == "M"
    finally:
        sys.path.remove(str(tmp_path))


def test_execute_module_import_failure(tmp_path, monkeypatch):
    sys.path.insert(0, str(tmp_path))
    pkg = tmp_path / "pkg_bad"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "broken.py").write_text("raise ImportError('nope')\n")
    try:
        s = Script("pkg_bad.broken")
        with pytest.raises(RuntimeError, match="import module"):
            ScriptExecutor(s).execute()
    finally:
        sys.path.remove(str(tmp_path))


def test_execute_module_property(simple_script):
    s = Script(str(simple_script))
    ex = ScriptExecutor(s)
    assert ex.module is None
    ex.execute()
    assert ex.module is not None


def test_execute_with_cell(make_script):
    s = make_script(
        "s.py",
        """
        # %% kogine:config
        lr = 0.1
        # %% kogine:script
        def main():
            return lr
        if __name__ == '__main__':
            main()
        """,
    )
    cfg = Config(globals_dict={"lr": 0.999})
    script = Script(str(s), config=cfg)
    assert ScriptExecutor(script).execute() == 0.999


def test_execute_with_cell_non_cell_override(make_script):
    s = make_script(
        "s.py",
        """
        outside = 1
        # %% kogine:config
        lr = 0.1
        # %% kogine:script
        def main():
            return (lr, outside)
        if __name__ == '__main__':
            main()
        """,
    )
    cfg = Config(globals_dict={"lr": 0.5, "outside": 99})
    script = Script(str(s), config=cfg)
    assert ScriptExecutor(script).execute() == (0.5, 99)
