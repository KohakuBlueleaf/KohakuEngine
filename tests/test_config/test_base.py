"""Tests for kohakuengine.config.base."""

import math
import warnings

import pytest

from kohakuengine.config import Config, Use, capture_globals, use
from kohakuengine.config.base import _filter_globals, _frame_module_name

# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------


def test_config_defaults():
    c = Config()
    assert c.globals_dict == {}
    assert c.args == []
    assert c.kwargs == {}
    assert c.metadata == {}


def test_config_basic_fields():
    c = Config(globals_dict={"a": 1}, args=[1, 2], kwargs={"b": 3}, metadata={"x": 1})
    assert c.globals_dict == {"a": 1}
    assert c.args == [1, 2]
    assert c.kwargs == {"b": 3}
    assert c.metadata == {"x": 1}


def test_config_tuple_args_normalized():
    c = Config(args=(1, 2))
    assert c.args == [1, 2]
    assert isinstance(c.args, list)


@pytest.mark.parametrize(
    "field,bad,expected",
    [
        ("globals_dict", [], "globals_dict"),
        ("args", {}, "args"),
        ("kwargs", [], "kwargs"),
        ("metadata", [], "metadata"),
    ],
)
def test_config_rejects_wrong_types(field, bad, expected):
    with pytest.raises(TypeError, match=expected):
        Config(**{field: bad})


# ---------------------------------------------------------------------------
# Use wrapper
# ---------------------------------------------------------------------------


def test_use_wraps_value():
    fn = lambda x: x
    wrapped = use(fn)
    assert isinstance(wrapped, Use)
    assert wrapped.value is fn


def test_use_repr():
    wrapped = use(42)
    assert "42" in repr(wrapped)


# ---------------------------------------------------------------------------
# capture_globals (deprecated)
# ---------------------------------------------------------------------------


def test_capture_globals_emits_deprecation():
    with pytest.warns(DeprecationWarning, match="deprecated"):
        capture_globals()


def _run_capture_at_module_scope(src: str) -> dict:
    """Exec ``src`` in a fresh namespace where capture_globals sees globals."""
    ns: dict = {
        "__name__": "_cap_test",
        "__builtins__": __builtins__,
        "capture_globals": capture_globals,
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        exec(src, ns)
    return ns


def test_capture_globals_still_captures():
    ns = _run_capture_at_module_scope(
        "with capture_globals() as ctx:\n    captured_value = 99\n"
    )
    assert ns["ctx"].captured.get("captured_value") == 99


def test_capture_globals_excludes_self():
    ns = _run_capture_at_module_scope("with capture_globals() as ctx:\n    a = 1\n")
    assert "ctx" not in ns["ctx"].captured


# ---------------------------------------------------------------------------
# _filter_globals
# ---------------------------------------------------------------------------


def test_filter_skips_private():
    out = _filter_globals({"_x": 1, "x": 2}, "mod")
    assert out == {"x": 2}


def test_filter_skips_modules():
    out = _filter_globals({"math": math, "y": 5}, "mod")
    assert "math" not in out
    assert out["y"] == 5


def test_filter_unwraps_use():
    fn = lambda x: x
    out = _filter_globals({"f": use(fn)}, "mod")
    assert out["f"] is fn


def test_filter_includes_local_callables():
    def local_fn():
        pass

    local_fn.__module__ = "mod"
    out = _filter_globals({"local_fn": local_fn}, "mod")
    assert out["local_fn"] is local_fn


def test_filter_skips_imported_callables():
    out = _filter_globals({"sq": math.sqrt}, "mod")
    assert "sq" not in out


def test_filter_includes_local_classes():
    class LocalCls:
        pass

    LocalCls.__module__ = "mod"
    out = _filter_globals({"LocalCls": LocalCls}, "mod")
    assert out["LocalCls"] is LocalCls


def test_filter_skips_imported_classes():
    out = _filter_globals({"PathClass": type}, "mod")
    assert "PathClass" not in out


def test_filter_includes_plain_data():
    out = _filter_globals({"x": 1, "y": "s", "z": [1, 2]}, "mod")
    assert out == {"x": 1, "y": "s", "z": [1, 2]}


# ---------------------------------------------------------------------------
# Config.from_globals & from_context
# ---------------------------------------------------------------------------


def test_from_globals_in_function_scope():
    # Within the test's own module
    lr = 0.01
    bs = 64
    cfg = Config.from_globals()
    # globals at this point are the test module's globals, which include
    # things like `pytest`; verify our knowns are present and modules are not.
    assert "Config" not in cfg.globals_dict  # imported class, skipped
    assert "pytest" not in cfg.globals_dict  # imported module
    # `lr`/`bs` are LOCAL to this function, not globals, so they won't appear
    assert "lr" not in cfg.globals_dict
    assert "bs" not in cfg.globals_dict


def test_from_context():
    ns = _run_capture_at_module_scope(
        "with capture_globals() as ctx:\n    captured_x = 1\n"
    )
    cfg = Config.from_context(ns["ctx"])
    assert cfg.globals_dict["captured_x"] == 1


def test_frame_module_name_unknown():
    class FakeFrame:
        f_globals = {}

    assert _frame_module_name(FakeFrame()) == "<unknown>"


def test_frame_module_name_known():
    class FakeFrame:
        f_globals = {"__name__": "x"}

    assert _frame_module_name(FakeFrame()) == "x"
