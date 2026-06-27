"""Tests for kohakuengine.engine.executor."""

import os
import pickle
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


def test_execute_imports_sibling_module(make_script, restore_import_state):
    # Regression: kogine did not put the script's directory on sys.path, so a
    # sibling import that works under `python script.py` failed with
    # ModuleNotFoundError.
    make_script("sibling_helper.py", "def greet():\n    return 'hi'\n")
    main = make_script(
        "uses_sibling.py",
        """
        from sibling_helper import greet
        def main():
            return greet()
        """,
    )
    assert ScriptExecutor(Script(str(main))).execute() == "hi"


def test_execute_imports_namespace_package(make_script, tmp_path, restore_import_state):
    # Regression: a relative package without __init__.py (namespace package) in
    # the script's directory could not be imported under kogine.
    pkg = tmp_path / "datapkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text("VALUE = 42\n", encoding="utf-8")  # no __init__.py
    main = make_script(
        "uses_ns.py",
        """
        from datapkg.mod import VALUE
        def main():
            return VALUE
        """,
    )
    assert ScriptExecutor(Script(str(main))).execute() == 42


def test_loaded_function_is_picklable(make_script, restore_import_state):
    # Regression: scripts were loaded under a synthetic module name that was
    # popped from sys.modules, so functions they defined could not be pickled
    # for multiprocessing ("import of module '_kohaku_script_..._<id>' failed").
    main = make_script(
        "pickle_me.py",
        """
        def worker(x):
            return x * x
        def main():
            return worker(3)
        """,
    )
    ex = ScriptExecutor(Script(str(main)))
    ex.execute()

    # Registered under its importable stem so __module__ resolves.
    assert ex.module is not None
    assert sys.modules.get("pickle_me") is ex.module
    assert ex.module.worker.__module__ == "pickle_me"

    restored = pickle.loads(pickle.dumps(ex.module.worker))
    assert restored(4) == 16


def test_loaded_cell_function_is_picklable(make_script, restore_import_state):
    # Same guarantee for cell-mode scripts (the freeze/AST-rewrite path).
    main = make_script(
        "pickle_cell.py",
        """
        # %% kogine:config
        factor = 2
        # %% kogine:script
        def worker(x):
            return x * factor
        def main():
            return worker(3)
        """,
    )
    ex = ScriptExecutor(Script(str(main), config=Config(globals_dict={"factor": 5})))
    ex.execute()

    assert ex.module is not None
    assert sys.modules.get("pickle_cell") is ex.module
    restored = pickle.loads(pickle.dumps(ex.module.worker))
    assert restored(4) == 20


def test_execute_with_process_pool_end_to_end(make_script, restore_import_state):
    # End-to-end guard for Bug 1: a ProcessPoolExecutor *inside* a kogine-loaded
    # script must be able to pickle a function the script defines and re-import
    # it in spawned workers.
    main = make_script(
        "mp_e2e.py",
        """
        import os
        from concurrent.futures import ProcessPoolExecutor

        def square(x):
            return (x * x, os.getpid())

        def main():
            with ProcessPoolExecutor(max_workers=2) as ex:
                return list(ex.map(square, range(5)))
        """,
    )
    results = ScriptExecutor(Script(str(main))).execute()
    assert [r[0] for r in results] == [0, 1, 4, 9, 16]
    # Work really happened in worker processes, not the parent.
    worker_pids = {r[1] for r in results}
    assert os.getpid() not in worker_pids


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
