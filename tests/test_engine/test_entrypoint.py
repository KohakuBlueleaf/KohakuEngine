"""Tests for entrypoint finder."""

import ast
from pathlib import Path

import pytest

from kohakuengine.engine.entrypoint import EntrypointFinder


class TestMainBlockFinder:
    """Test finding functions in __main__ block."""

    def test_find_main_block_with_invalid_comparison(self, tmp_path):
        """Test _is_main_guard with invalid comparison types."""
        # Test with non-Compare node
        code = """
x = 5
"""
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                result = EntrypointFinder._is_main_guard(node)
                assert result is False

    def test_find_main_block_wrong_variable(self, tmp_path):
        """Test _is_main_guard with wrong variable name."""
        code = """
if some_var == "__main__":
    main()
"""
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                result = EntrypointFinder._is_main_guard(node)
                assert result is False

    def test_find_main_block_wrong_operator(self, tmp_path):
        """Test _is_main_guard with wrong operator."""
        code = """
if __name__ != "__main__":
    main()
"""
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                result = EntrypointFinder._is_main_guard(node)
                assert result is False

    def test_find_main_block_wrong_value(self, tmp_path):
        """Test _is_main_guard with wrong comparison value."""
        code = """
if __name__ == "other":
    main()
"""
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                result = EntrypointFinder._is_main_guard(node)
                assert result is False

    def test_find_main_block_multiple_comparisons(self, tmp_path):
        """Test _is_main_guard with chained comparisons."""
        code = """
if __name__ == "__main__" == True:
    main()
"""
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                if len(node.ops) > 1:
                    result = EntrypointFinder._is_main_guard(node)
                    assert result is False

    def test_find_main_block_correct(self, tmp_path):
        """Test _is_main_guard with correct pattern."""
        code = """
if __name__ == "__main__":
    main()
"""
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                result = EntrypointFinder._is_main_guard(node)
                assert result is True
                break


class TestEntrypointFinding:
    """Test entrypoint discovery."""

    def test_find_entrypoint_main_block(self, tmp_path):
        """Test finding entrypoint in main block."""
        script = tmp_path / "script.py"
        script.write_text(
            """
def custom_entry():
    return "custom"

if __name__ == "__main__":
    custom_entry()
"""
        )

        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location("test_module", script)
        module = importlib.util.module_from_spec(spec)
        sys.modules["test_module"] = module
        spec.loader.exec_module(module)

        entrypoint = EntrypointFinder.find_entrypoint(module, script)
        assert entrypoint is not None
        assert entrypoint.__name__ == "custom_entry"

    def test_find_entrypoint_fallback_main(self, tmp_path):
        """Test fallback to main() function."""
        script = tmp_path / "script.py"
        script.write_text(
            """
def main():
    return "main"

# No if __name__ == "__main__" block
"""
        )

        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location("test_module2", script)
        module = importlib.util.module_from_spec(spec)
        sys.modules["test_module2"] = module
        spec.loader.exec_module(module)

        entrypoint = EntrypointFinder.find_entrypoint(module, script)
        assert entrypoint is not None
        assert entrypoint.__name__ == "main"

    def test_find_entrypoint_none(self, tmp_path):
        """Test when no entrypoint found."""
        script = tmp_path / "script.py"
        script.write_text(
            """
x = 10
y = 20
"""
        )

        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location("test_module3", script)
        module = importlib.util.module_from_spec(spec)
        sys.modules["test_module3"] = module
        spec.loader.exec_module(module)

        entrypoint = EntrypointFinder.find_entrypoint(module, script)
        assert entrypoint is None

    def test_find_entrypoint_asyncio_run(self, tmp_path):
        """Test finding async entrypoint with asyncio.run()."""
        script = tmp_path / "script.py"
        script.write_text(
            """
import asyncio

async def async_main():
    return "async"

if __name__ == "__main__":
    asyncio.run(async_main())
"""
        )

        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location("test_module4", script)
        module = importlib.util.module_from_spec(spec)
        sys.modules["test_module4"] = module
        spec.loader.exec_module(module)

        entrypoint = EntrypointFinder.find_entrypoint(module, script)
        assert entrypoint is not None
        assert entrypoint.__name__ == "async_main"


class TestCallEntrypoint:
    """Test calling entrypoints."""

    def test_call_with_no_params(self):
        """Test calling function with no parameters."""

        def func():
            return 42

        result = EntrypointFinder.call_entrypoint(func, [], {})
        assert result == 42

    def test_call_with_args(self):
        """Test calling function with args."""

        def func(x, y):
            return x + y

        result = EntrypointFinder.call_entrypoint(func, [10, 20], {})
        assert result == 30

    def test_call_with_kwargs(self):
        """Test calling function with kwargs."""

        def func(x=0, y=0):
            return x * y

        result = EntrypointFinder.call_entrypoint(func, [], {"x": 5, "y": 3})
        assert result == 15

    def test_call_with_var_args(self):
        """Test calling function with *args."""

        def func(*args):
            return sum(args)

        result = EntrypointFinder.call_entrypoint(func, [1, 2, 3, 4], {})
        assert result == 10

    def test_call_with_var_kwargs(self):
        """Test calling function with **kwargs."""

        def func(**kwargs):
            return len(kwargs)

        result = EntrypointFinder.call_entrypoint(func, [], {"a": 1, "b": 2, "c": 3})
        assert result == 3

    def test_call_filters_unknown_kwargs(self):
        """Test that unknown kwargs are filtered out."""

        def func(x=0):
            return x * 2

        # Pass extra kwargs that should be filtered
        result = EntrypointFinder.call_entrypoint(func, [], {"x": 5, "unknown": 10})
        assert result == 10

    def test_call_async_function(self):
        """Test calling async function."""

        async def async_func():
            return "async result"

        result = EntrypointFinder.call_entrypoint(async_func, [], {})
        assert result == "async result"

    def test_call_async_function_with_args(self):
        """Test calling async function with args."""

        async def async_func(x, y):
            return x + y

        result = EntrypointFinder.call_entrypoint(async_func, [100, 200], {})
        assert result == 300

    def test_call_ignores_args_when_no_params(self):
        """Test that args are ignored when function has no params."""

        def func():
            return "no args"

        result = EntrypointFinder.call_entrypoint(func, [1, 2, 3], {"x": 10})
        assert result == "no args"
