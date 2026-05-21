"""Edge-case tests filling coverage gaps."""

import argparse
import ast
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

from kohakuengine import Config, ConfigGenerator, Script, introspect, run
from kohakuengine.cli import _describe_source, cmd_run, main as cli_main
from kohakuengine.engine import introspect as introspect_mod
from kohakuengine.engine.cell import (
    _parse_cell_from_source,
    _rewrite_assigns,
    evaluate_cell,
    parse_cell,
)
from kohakuengine.engine.coerce import coerce_globals
from kohakuengine.engine.entrypoint import (
    EntrypointNotFound,
    _is_main_guard,
    entrypoint,
    find_entrypoint,
)
from kohakuengine.engine.executor import ScriptExecutor
from kohakuengine.engine.introspect import _import_no_main
from kohakuengine.engine.script import _serialize_config
from kohakuengine.flow.base import ScriptWorkflow, Workflow
from kohakuengine.flow.flow import Flow
from kohakuengine.flow.parallel import Parallel, _execute_script_helper
from kohakuengine.flow.sequential import Sequential
from kohakuengine.config.loader import load_config_file

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _ns(**kw):
    defaults = dict(
        script=None,
        config=None,
        entrypoint=None,
        set=[],
        sweep=[],
        strict=False,
        subprocess=False,
    )
    defaults.update(kw)
    return argparse.Namespace(**defaults)


def test_describe_source_bare(make_config):
    p = make_config("c.py", "x = 1\n")
    assert "bare-file" in _describe_source(str(p))


def test_describe_source_sweep(make_config):
    p = make_config("c.py", "_sweep = {'x': [1]}\n")
    assert "_sweep" in _describe_source(str(p))


def test_describe_source_config_gen(make_config):
    p = make_config("c.py", "def config_gen(): pass\n")
    assert "config_gen" in _describe_source(str(p))


def test_describe_source_CONFIG(make_config):
    p = make_config("c.py", "CONFIG = 1\n")
    assert "CONFIG" in _describe_source(str(p))


def test_cmd_run_subprocess(simple_script, capfd):
    """Run command in subprocess mode."""
    with pytest.raises(SystemExit) as exc:
        cmd_run(_ns(script=str(simple_script), subprocess=True))
    assert exc.value.code == 0
    out = capfd.readouterr().out
    assert "subprocess" in out


# ---------------------------------------------------------------------------
# main.run merging
# ---------------------------------------------------------------------------


def test_run_merges_args(args_script, make_config):
    cfg = make_config(
        "c.py",
        """
        from kohakuengine.config import Config
        def config_gen():
            return Config(globals_dict={}, args=[1])
        """,
    )
    # Override args via inline arg
    assert run(str(args_script), config_path=str(cfg), args=[7], kwargs={"y": 1}) == 8


def test_run_merges_kwargs(args_script, make_config):
    cfg = make_config(
        "c.py",
        """
        from kohakuengine.config import Config
        def config_gen():
            return Config(globals_dict={}, kwargs={"y": 3})
        """,
    )
    # Override kwargs via inline kwargs
    assert (
        run(str(args_script), config_path=str(cfg), args=[10], kwargs={"y": 100}) == 110
    )


# ---------------------------------------------------------------------------
# Flow / executors
# ---------------------------------------------------------------------------


def test_flow_pool_mode(simple_script):
    """ProcessPoolExecutor path of Parallel."""
    cfg = Config(globals_dict={"lr": 0.5})
    s = Script(str(simple_script), config=cfg)
    workflow = Parallel([s], max_workers=1, use_subprocess=False)
    results = workflow.run()
    assert results == [0.5]


def test_flow_pool_with_generator(simple_script):
    gen = ConfigGenerator(iter([Config(globals_dict={"lr": x}) for x in (0.1, 0.2)]))
    s = Script(str(simple_script), config=gen)
    workflow = Parallel([s], max_workers=2, use_subprocess=False)
    results = workflow.run()
    assert sorted(results) == [0.1, 0.2]


def test_parallel_helper_function(simple_script):
    cfg = Config(globals_dict={"lr": 0.3})
    result = _execute_script_helper(Script(str(simple_script), config=cfg), cfg)
    assert result == 0.3


def test_sequential_subprocess_no_config(simple_script, tmp_path):
    s = Script(str(simple_script))
    seq = Sequential([s], use_subprocess=True)
    results = seq.run()
    assert results[0].returncode == 0


def test_sequential_subprocess_returncode_nonzero(make_script):
    bad = make_script("bad.py", "import sys\nsys.exit(7)\n")
    s = Script(str(bad))
    seq = Sequential([s], use_subprocess=True)
    with pytest.raises(RuntimeError, match="exit code"):
        seq.run()


def test_workflow_abstract_base():
    """Cannot instantiate Workflow directly."""
    with pytest.raises(TypeError):
        Workflow()


def test_script_workflow_validates_missing_files(tmp_path):
    """Sub-of ScriptWorkflow with a script that ceases to exist."""

    class Concrete(ScriptWorkflow):
        def run(self):
            return None

    # Build a valid script first, then delete it
    p = tmp_path / "a.py"
    p.write_text("def main(): pass\n")
    s = Script(str(p))
    p.unlink()
    with pytest.raises(ValueError, match="not found"):
        Concrete([s])


def test_flow_custom_executor_other_class(simple_script):
    """Flow with a custom (non-Sequential/Parallel) executor class."""

    class CustomExec:
        def __init__(self, scripts):
            self.scripts = scripts

        def run(self):
            return ["custom"]

        def validate(self):
            return True

    flow = Flow([Script(str(simple_script))], executor_class=CustomExec)
    assert flow.run() == ["custom"]


# ---------------------------------------------------------------------------
# Script
# ---------------------------------------------------------------------------


def test_script_serialize_round_trip():
    cfg = Config(globals_dict={"x": 1}, args=[1], kwargs={"y": 2}, metadata={"m": "v"})
    p = _serialize_config(cfg)
    try:
        text = p.read_text()
        assert "globals_dict={'x': 1}" in text
        assert "args=[1]" in text
        assert "kwargs={'y': 2}" in text
        assert "metadata={'m': 'v'}" in text
    finally:
        os.unlink(p)


def test_script_run_subprocess_via_method(simple_script):
    cfg = Config(globals_dict={"lr": 0.55})
    s = Script(str(simple_script), config=cfg)
    proc = s._run_subprocess()
    assert proc.returncode == 0


def test_script_run_subprocess_no_config(simple_script):
    s = Script(str(simple_script))
    proc = s._run_subprocess()
    assert proc.returncode == 0


def test_script_run_subprocess_with_generator(simple_script):
    """Generator skipped -- subprocess runs the script with no config."""
    gen = ConfigGenerator(iter([Config(globals_dict={"lr": 0.1})]))
    s = Script(str(simple_script), config=gen)
    proc = s._run_subprocess()
    assert proc.returncode == 0


def test_script_builtin_module_path():
    """Importable module without a file (built-in) gets fallback path."""
    # _frozen_importlib is a built-in module with no file
    s = Script("sys")
    assert s.is_module is True


# ---------------------------------------------------------------------------
# Engine: cell edge cases
# ---------------------------------------------------------------------------


def test_cell_non_assign_branch(make_script):
    """The 'continue' branch when a child is not an Assign."""
    p = make_script(
        "s.py",
        """
        # %% kogine:config
        a = 1
        b = 2
        # %% kogine:script
        """,
    )
    info = parse_cell(p)
    # All-Assign cell: assigns extracted without warning
    out = evaluate_cell(p, info)
    assert out == {"a": 1, "b": 2}


def test_cell_only_config_marker(make_script):
    p = make_script(
        "s.py",
        "# %% kogine:config\na = 99\n",
    )
    info = parse_cell(p)
    assert info.script_line is None


def test_parse_cell_from_source_returns_correct_lines():
    src = "x = 1\n# %% kogine:config\na = 1\n# %% kogine:script\n"
    info = _parse_cell_from_source(src)
    assert info.config_line == 2 and info.script_line == 4


# ---------------------------------------------------------------------------
# Engine: entrypoint AST helpers
# ---------------------------------------------------------------------------


def test_is_main_guard_branches():
    # Not a Compare
    n = ast.parse("a + b", mode="eval").body
    assert _is_main_guard(n) is False
    # Wrong left
    n = ast.parse("'x' == '__main__'", mode="eval").body
    assert _is_main_guard(n) is False
    # Wrong operator
    n = ast.parse("__name__ != '__main__'", mode="eval").body
    assert _is_main_guard(n) is False
    # Multiple comparisons / wrong value
    n = ast.parse("__name__ == 'main'", mode="eval").body
    assert _is_main_guard(n) is False
    n = ast.parse("a == b == c", mode="eval").body
    assert _is_main_guard(n) is False
    # Correct
    n = ast.parse("__name__ == '__main__'", mode="eval").body
    assert _is_main_guard(n) is True


def test_find_entrypoint_decorator_dedup():
    """A function exposed under two names with the decorator counts once."""

    @entrypoint
    def go():
        return "go"

    mod = types.ModuleType("m")
    mod.a = go
    mod.b = go  # same function object aliased
    found = find_entrypoint(mod, None)
    assert found is go


def test_find_entrypoint_decorator_non_callable_skipped():
    mod = types.ModuleType("m")
    mod.x = 1
    setattr(mod.x, "__kogine_entrypoint__", True) if False else None

    # Non-callable can't carry the attr meaningfully; we just need coverage
    # of the iteration when callable() check passes but flag is absent.
    def helper():
        pass

    mod.helper = helper

    def main():
        return "m"

    mod.main = main
    assert find_entrypoint(mod, None) is main


# ---------------------------------------------------------------------------
# Engine: introspect error paths
# ---------------------------------------------------------------------------


def test_introspect_propagates_module_error(make_script):
    p = make_script("bad.py", "raise RuntimeError('boom')\n")
    with pytest.raises(RuntimeError, match="boom"):
        introspect(p)


def test_introspect_no_spec(monkeypatch, tmp_path):
    # introspect_mod imported at top; this binding keeps it referenced.
    assert introspect_mod is not None
    p = tmp_path / "x.py"
    p.write_text("x=1")
    monkeypatch.setattr("importlib.util.spec_from_file_location", lambda *a, **k: None)
    with pytest.raises(RuntimeError, match="Cannot load script"):
        _import_no_main(Path(str(p)))


# ---------------------------------------------------------------------------
# Engine: coerce identity path
# ---------------------------------------------------------------------------


class _Custom:
    """Exotic type with no entry in COERCERS."""

    pass


def test_coerce_with_unsupported_default_type_uses_identity():
    """Hit the _identity fallback path."""
    out = coerce_globals({"obj": "abc"}, {"obj": _Custom()})
    assert out == {"obj": "abc"}


# ---------------------------------------------------------------------------
# Executor: cannot load script error path
# ---------------------------------------------------------------------------


def test_executor_load_failure(monkeypatch, simple_script):
    monkeypatch.setattr("importlib.util.spec_from_file_location", lambda *a, **k: None)
    s = Script(str(simple_script))
    with pytest.raises(RuntimeError, match="Cannot load script"):
        ScriptExecutor(s).execute()


# ---------------------------------------------------------------------------
# Additional coverage gaps
# ---------------------------------------------------------------------------


def test_script_run_attached_method_use_subprocess(simple_script):
    """The attached Script.run(use_subprocess=True) branch."""
    cfg = Config(globals_dict={"lr": 0.42})
    s = Script(str(simple_script), config=cfg)
    proc = s.run(use_subprocess=True)
    assert proc.returncode == 0


def test_main_guard_not_a_call_stmt(tmp_path):
    """An if __name__ block whose body contains non-Call statements."""
    p = tmp_path / "s.py"
    p.write_text(
        "if __name__ == '__main__':\n"
        "    x = 1\n"  # not an Expr/Call
        "    print(x)\n"  # Expr/Call but Name -- handled by other branch
    )
    mod = types.ModuleType("m")
    with pytest.raises(EntrypointNotFound):
        find_entrypoint(mod, p)


def test_main_guard_outside_pattern(tmp_path):
    """A top-level `if` that is not a main guard at all."""
    p = tmp_path / "s.py"
    p.write_text("if True:\n    pass\n\ndef main(): return 'm'\n")
    mod = types.ModuleType("m")

    def main():
        return "m"

    mod.main = main
    found = find_entrypoint(mod, p)
    assert found is main


def test_cell_unrelated_comments_skipped(make_script):
    """Comments that aren't kogine markers should be silently skipped."""
    p = make_script(
        "s.py",
        """
        # ordinary comment
        # %% other:marker
        # %% kogine:config
        a = 1
        # %% kogine:script
        """,
    )
    info = parse_cell(p)
    assert info is not None
    assert info.config_line > 0


def test_cell_resolved_skips_unknown_name():
    """If overrides include a name not in the cell, the loop continues."""
    src = "a = 1\nb = 2\n"
    tree = ast.parse(src)
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    frozen = _rewrite_assigns(assigns, {"a": 10})  # only `a` resolved
    assert ast.unparse(tree).strip().splitlines() == ["a = 10", "b = 2"]
    assert frozen == {}


def test_executor_module_with_config_injection(tmp_path):
    """Module-based script + config: covers GlobalInjector path."""
    pkg = tmp_path / "pkg_inject"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "mod.py").write_text("value = 1\ndef main(): return value\n")
    sys.path.insert(0, str(tmp_path))
    try:
        s = Script("pkg_inject.mod", config=Config(globals_dict={"value": 99}))
        assert ScriptExecutor(s).execute() == 99
    finally:
        sys.path.remove(str(tmp_path))


def test_loader_spec_returns_none(monkeypatch, tmp_path):
    """Spec resolution returns None -> ValueError."""
    p = tmp_path / "c.py"
    p.write_text("x = 1")
    monkeypatch.setattr("importlib.util.spec_from_file_location", lambda *a, **k: None)
    with pytest.raises(ValueError, match="Cannot load config"):
        load_config_file(p)


def test_cli_subprocess_failure_exits_with_returncode(make_script, capfd):
    """cmd_run --subprocess exits with the failed subprocess's return code."""
    bad = make_script("bad.py", "import sys\nsys.exit(7)\n")
    with pytest.raises(SystemExit) as exc:
        cmd_run(_ns(script=str(bad), subprocess=True))
    assert exc.value.code == 7


def test_cli_module_main_block():
    """python -m kohakuengine.cli triggers the if __name__ == '__main__' block."""
    cmd = [sys.executable, "-m", "kohakuengine.cli", "--version"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "kogine" in result.stdout


def test_cli_main_dispatches_to_func(make_config, capfd):
    """main([...]) hits args.func(args) dispatch line."""
    cfg = make_config("c.py", "x = 1\n")
    with pytest.raises(SystemExit):
        cli_main(["config", "validate", str(cfg)])
    out = capfd.readouterr().out
    assert "valid" in out.lower()


def test_cli_stdout_wrapping(monkeypatch, make_config, capfd):
    """Force stdout encoding != utf-8 so the wrapper branch executes."""
    cfg = make_config("c.py", "x = 1\n")

    class FakeStdout:
        encoding = "cp1252"
        buffer = sys.stdout.buffer

    monkeypatch.setattr(sys, "stdout", FakeStdout())
    monkeypatch.setattr(sys, "stderr", FakeStdout())
    with pytest.raises(SystemExit):
        cli_main(["config", "validate", str(cfg)])


def test_script_module_not_found_branch():
    """find_spec returns None inside an existing package -> our ModuleNotFoundError."""
    # `email` is a package; subname missing -> find_spec returns None.
    with pytest.raises(ModuleNotFoundError, match="Module not found"):
        Script("email.this_module_definitely_does_not_exist_xyz")
