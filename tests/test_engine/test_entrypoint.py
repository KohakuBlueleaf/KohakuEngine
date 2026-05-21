"""Tests for the entrypoint discovery cascade."""

import asyncio
import types

import pytest

from kohakuengine.engine.entrypoint import (
    EntrypointFinder,
    EntrypointNotFound,
    MultipleEntrypoints,
    call_entrypoint,
    entrypoint,
    find_entrypoint,
)

# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def test_decorator_marks_function():
    @entrypoint
    def fn():
        pass

    assert getattr(fn, "__kogine_entrypoint__", False) is True


def test_decorator_with_name():
    @entrypoint(name="alias")
    def fn():
        pass

    assert fn.__kogine_entrypoint__ is True
    assert fn.__kogine_entrypoint_name__ == "alias"


def test_decorator_bare_returns_func():
    def fn():
        return 1

    assert entrypoint(fn) is fn


# ---------------------------------------------------------------------------
# find_entrypoint cascade
# ---------------------------------------------------------------------------


def _module_with(**attrs):
    mod = types.ModuleType("m")
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


def test_explicit_name_wins():
    def f1():
        return 1

    def f2():
        return 2

    mod = _module_with(f1=f1, f2=f2)
    found = find_entrypoint(mod, None, explicit_name="f2")
    assert found is f2


def test_explicit_name_not_found():
    mod = _module_with()
    with pytest.raises(EntrypointNotFound, match="not found"):
        find_entrypoint(mod, None, explicit_name="ghost")


def test_explicit_name_not_callable():
    mod = _module_with(x=5)
    with pytest.raises(EntrypointNotFound, match="not callable"):
        find_entrypoint(mod, None, explicit_name="x")


def test_decorator_wins_over_main():
    @entrypoint
    def decorated():
        return "decorated"

    def main():
        return "main"

    mod = _module_with(decorated=decorated, main=main)
    found = find_entrypoint(mod, None)
    assert found is decorated


def test_multiple_decorators_raises():
    @entrypoint
    def a():
        pass

    @entrypoint
    def b():
        pass

    mod = _module_with(a=a, b=b)
    with pytest.raises(MultipleEntrypoints):
        find_entrypoint(mod, None)


def test_main_block_detection(tmp_path):
    p = tmp_path / "s.py"
    p.write_text("def go():\n    return 'g'\n\nif __name__ == '__main__':\n    go()\n")
    mod = types.ModuleType("m")

    def go():
        return "g"

    mod.go = go
    found = find_entrypoint(mod, p)
    assert found is go


def test_main_block_async_pattern(tmp_path):
    p = tmp_path / "s.py"
    p.write_text(
        "import asyncio\nasync def go():\n    return 'a'\n"
        "if __name__ == '__main__':\n    asyncio.run(go())\n"
    )
    mod = types.ModuleType("m")

    async def go():
        return "a"

    mod.go = go
    found = find_entrypoint(mod, p)
    assert found is go


def test_main_fallback():
    def main():
        return "m"

    mod = _module_with(main=main)
    assert find_entrypoint(mod, None) is main


def test_run_fallback():
    def run():
        return "r"

    mod = _module_with(run=run)
    assert find_entrypoint(mod, None) is run


def test_main_takes_priority_over_run():
    def main():
        return "m"

    def run():
        return "r"

    mod = _module_with(main=main, run=run)
    assert find_entrypoint(mod, None) is main


def test_no_entrypoint_diagnostic(tmp_path):
    p = tmp_path / "s.py"
    p.write_text("x = 1\n")
    mod = _module_with(x=1)
    with pytest.raises(EntrypointNotFound) as exc:
        find_entrypoint(mod, p)
    msg = str(exc.value)
    assert "decorator" in msg and "main" in msg and "run" in msg


def test_main_block_function_must_exist_in_module(tmp_path):
    p = tmp_path / "s.py"
    p.write_text("if __name__ == '__main__':\n    nonexistent()\n")
    mod = _module_with()  # nothing
    with pytest.raises(EntrypointNotFound):
        find_entrypoint(mod, p)


# ---------------------------------------------------------------------------
# call_entrypoint
# ---------------------------------------------------------------------------


def test_call_with_no_args():
    def f():
        return 1

    assert call_entrypoint(f, [], {}) == 1


def test_call_with_args_kwargs():
    def f(x, y=10):
        return x + y

    assert call_entrypoint(f, [5], {"y": 3}) == 8


def test_call_kwargs_filtered_to_match():
    def f(x):
        return x

    # extra kwargs are dropped because f doesn't accept **kw
    assert call_entrypoint(f, [], {"x": 1, "y": 2}) == 1


def test_call_var_kwargs():
    def f(**kw):
        return kw

    assert call_entrypoint(f, [], {"a": 1, "b": 2}) == {"a": 1, "b": 2}


def test_call_var_args():
    def f(*a):
        return a

    assert call_entrypoint(f, [1, 2, 3], {}) == (1, 2, 3)


def test_call_async_runs_in_loop():
    async def f():
        await asyncio.sleep(0)
        return "done"

    assert call_entrypoint(f, [], {}) == "done"


# ---------------------------------------------------------------------------
# EntrypointFinder facade
# ---------------------------------------------------------------------------


def test_facade_returns_none_on_failure():
    mod = _module_with()
    assert EntrypointFinder.find_entrypoint(mod, None) is None
    assert EntrypointFinder.find_entrypoint_for_module(mod) is None


def test_facade_call_entrypoint():
    def f():
        return 1

    assert EntrypointFinder.call_entrypoint(f, [], {}) == 1
