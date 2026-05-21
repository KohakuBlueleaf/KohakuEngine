"""Tests for the config cell engine (Idea 7)."""

import ast
import linecache

import pytest

from kohakuengine.engine.cell import (
    CellInfo,
    _is_constant_safe,
    _parse_cell_from_source,
    clear_cell_cache,
    evaluate_cell,
    execute_with_cell,
    has_cell,
    parse_cell,
)


def test_cell_info_in_cell():
    c = CellInfo(config_line=5, script_line=10)
    assert c.in_cell(5) is False
    assert c.in_cell(6) is True
    assert c.in_cell(9) is True
    assert c.in_cell(10) is False
    assert c.in_cell(20) is False


def test_cell_info_open_ended():
    c = CellInfo(config_line=5, script_line=None)
    assert c.in_cell(100) is True


def test_parse_cell_basic(make_script):
    p = make_script(
        "s.py",
        """
        x = 1
        # %% kogine:config
        a = 1
        b = 2
        # %% kogine:script
        c = 3
        """,
    )
    info = parse_cell(p)
    assert info is not None
    assert info.config_line > 0 and info.script_line is not None


def test_parse_cell_open_ended(make_script):
    p = make_script(
        "s.py",
        """
        # %% kogine:config
        a = 1
        """,
    )
    info = parse_cell(p)
    assert info is not None
    assert info.script_line is None


def test_parse_cell_none(make_script):
    p = make_script("s.py", "x = 1\n")
    assert parse_cell(p) is None


def test_parse_cell_tokenize_error_returns_none():
    # Unterminated string token raises TokenizeError internally
    src = "x = '\n"
    assert _parse_cell_from_source(src) is None


def test_has_cell(make_script):
    yes = make_script(
        "y.py",
        "# %% kogine:config\na = 1\n",
    )
    no = make_script("n.py", "x = 1\n")
    assert has_cell(yes) is True
    assert has_cell(no) is False


def test_is_constant_safe():
    assert _is_constant_safe(1) is True
    assert _is_constant_safe("s") is True
    assert _is_constant_safe(None) is True
    assert _is_constant_safe(True) is True
    assert _is_constant_safe(1.5) is True
    assert _is_constant_safe(b"x") is True
    assert _is_constant_safe((1, 2, "a")) is True
    assert _is_constant_safe(frozenset({1, 2})) is True
    assert _is_constant_safe([1, 2]) is False
    assert _is_constant_safe(object()) is False
    assert _is_constant_safe((1, [1, 2])) is False  # nested non-const
    assert _is_constant_safe(frozenset({(1, 2)})) is True


def test_evaluate_cell_basic(make_script):
    p = make_script(
        "s.py",
        """
        import math
        # %% kogine:config
        a = math.sqrt(16)
        b = 42
        # %% kogine:script
        """,
    )
    info = parse_cell(p)
    out = evaluate_cell(p, info)
    assert out == {"a": 4.0, "b": 42}


def test_evaluate_cell_non_assign_warns_and_terminates(make_script):
    p = make_script(
        "s.py",
        """
        # %% kogine:config
        a = 1
        print('x')
        b = 2
        # %% kogine:script
        """,
    )
    info = parse_cell(p)
    with pytest.warns(UserWarning, match="cell ends"):
        out = evaluate_cell(p, info)
    assert "a" in out and "b" not in out


def test_execute_with_cell_constants_baked(make_script):
    p = make_script(
        "s.py",
        """
        # %% kogine:config
        a = 1
        b = 2
        # %% kogine:script
        """,
    )
    md = {"__name__": "_m", "__file__": str(p)}
    tree, evaluated, frozen = execute_with_cell(p, {"a": 99}, md)
    assert md["a"] == 99 and md["b"] == 2
    assert frozen == {}  # both are constants
    # Verify the AST was rewritten to Constants
    sources = ast.unparse(tree).splitlines()
    cfg_lines = [l for l in sources if l.startswith(("a =", "b ="))]
    assert "a = 99" in cfg_lines
    assert "b = 2" in cfg_lines


def test_execute_with_cell_non_constant_uses_frozen(make_script):
    p = make_script(
        "s.py",
        """
        # %% kogine:config
        obj = [1, 2, 3]
        # %% kogine:script
        """,
    )
    md = {"__name__": "_m", "__file__": str(p)}
    _, _, frozen = execute_with_cell(p, None, md)
    assert frozen == {"obj": [1, 2, 3]}
    assert md["obj"] == [1, 2, 3]


def test_execute_with_cell_traceback_filename_preserved(make_script, tmp_path):
    p = make_script(
        "boom.py",
        """
        # %% kogine:config
        x = 1
        # %% kogine:script
        def go():
            raise RuntimeError('here')
        go()
        """,
    )
    md = {"__name__": "_m", "__file__": str(p)}
    with pytest.raises(RuntimeError):
        execute_with_cell(p, None, md)
    # linecache should now contain the script
    assert str(p) in linecache.cache


def test_execute_with_cell_no_cell_raises(make_script):
    p = make_script("s.py", "x = 1\n")
    with pytest.raises(RuntimeError, match="without a cell"):
        execute_with_cell(p, None, {})


def test_execute_with_cell_non_cell_override_applied(make_script):
    p = make_script(
        "s.py",
        """
        outside = 7
        # %% kogine:config
        cell_var = 1
        # %% kogine:script
        """,
    )
    md = {"__name__": "_m", "__file__": str(p)}
    execute_with_cell(p, {"outside": 100}, md)
    assert md["outside"] == 100


def test_evaluate_cell_cached(make_script):
    """A second call hits the cache."""
    p = make_script(
        "s.py",
        """
        # %% kogine:config
        a = 1
        # %% kogine:script
        """,
    )
    clear_cell_cache()
    info = parse_cell(p)
    out1 = evaluate_cell(p, info)
    out2 = evaluate_cell(p, info)
    assert out1 == out2 == {"a": 1}


def test_clear_cell_cache(make_script):
    p = make_script("s.py", "# %% kogine:config\na = 1\n")
    evaluate_cell(p, parse_cell(p))
    clear_cell_cache()
    # No assertion -- just exercising the function for coverage


def test_parse_cell_handles_multiple_kogine_markers(make_script):
    # Only the first config/script marker is recognized
    p = make_script(
        "s.py",
        """
        # %% kogine:config
        a = 1
        # %% kogine:script
        # %% kogine:config
        # %% kogine:script
        """,
    )
    info = parse_cell(p)
    assert info is not None
