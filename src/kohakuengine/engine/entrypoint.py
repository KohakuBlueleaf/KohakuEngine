"""Entrypoint discovery and calling for scripts."""

import ast
import asyncio
import inspect
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


class EntrypointFinder:
    """Find and call script entrypoints."""

    @staticmethod
    def find_entrypoint(module: ModuleType, script_path: Path) -> Callable | None:
        """
        Find entrypoint function in script.

        Strategy:
        1. Look for function defined in `if __name__ == "__main__"` block
        2. Look for `main()` function
        3. Return None if not found

        Args:
            module: Loaded module
            script_path: Path to script file (for AST parsing)

        Returns:
            Entrypoint function or None

        Examples:
            >>> # Assuming script has main() function
            >>> entrypoint = EntrypointFinder.find_entrypoint(module, Path('script.py'))
            >>> callable(entrypoint)
            True
        """
        # Parse AST to find if __name__ == "__main__" block
        with open(script_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(script_path))

        entrypoint_name = EntrypointFinder._find_main_block_function(tree)

        if entrypoint_name and hasattr(module, entrypoint_name):
            return getattr(module, entrypoint_name)

        # Fallback: look for main() function
        if hasattr(module, "main") and callable(module.main):
            return module.main

        return None

    @staticmethod
    def find_entrypoint_for_module(module: ModuleType) -> Callable | None:
        """
        Find entrypoint function in an importable module.

        For modules loaded via import, we cannot rely on AST parsing of the
        `if __name__ == "__main__"` block since it won't execute. Instead:
        1. Look for `main()` function
        2. Return None if not found

        Args:
            module: Loaded module

        Returns:
            Entrypoint function or None

        Examples:
            >>> import my_module
            >>> entrypoint = EntrypointFinder.find_entrypoint_for_module(my_module)
            >>> callable(entrypoint) if entrypoint else True
            True
        """
        # For imported modules, look for main() function
        if hasattr(module, "main") and callable(module.main):
            return module.main

        return None

    @staticmethod
    def _find_main_block_function(tree: ast.AST) -> str | None:
        """
        Find function called in if __name__ == "__main__" block.

        Looks for patterns:
            if __name__ == "__main__":
                some_function()

            if __name__ == "__main__":
                asyncio.run(some_function())

        Returns function name.
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check if condition is __name__ == "__main__"
                if EntrypointFinder._is_main_guard(node.test):
                    # Find function calls in body
                    for stmt in node.body:
                        if isinstance(stmt, ast.Expr) and isinstance(
                            stmt.value, ast.Call
                        ):
                            call = stmt.value
                            # Direct function call: some_function()
                            if isinstance(call.func, ast.Name):
                                return call.func.id
                            # asyncio.run(func()) pattern
                            if (
                                isinstance(call.func, ast.Attribute)
                                and call.func.attr == "run"
                                and isinstance(call.func.value, ast.Name)
                                and call.func.value.id == "asyncio"
                                and len(call.args) >= 1
                                and isinstance(call.args[0], ast.Call)
                                and isinstance(call.args[0].func, ast.Name)
                            ):
                                return call.args[0].func.id
        return None

    @staticmethod
    def _is_main_guard(node: ast.expr) -> bool:
        """Check if node is __name__ == "__main__" comparison."""
        if not isinstance(node, ast.Compare):
            return False

        # Check for __name__ on left side
        if not (isinstance(node.left, ast.Name) and node.left.id == "__name__"):
            return False

        # Check for == operator
        if not (len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq)):
            return False

        # Check for "__main__" on right side
        if not (
            len(node.comparators) == 1
            and isinstance(node.comparators[0], ast.Constant)
            and node.comparators[0].value == "__main__"
        ):
            return False

        return True

    @staticmethod
    def call_entrypoint(func: Callable, args: list[Any], kwargs: dict[str, Any]) -> Any:
        """
        Call entrypoint with args/kwargs.

        Handles functions that don't accept args/kwargs gracefully.
        Supports both sync and async functions.

        Args:
            func: Function to call (sync or async)
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Function return value

        Examples:
            >>> def my_func(x, y=10):
            ...     return x + y
            >>> result = EntrypointFinder.call_entrypoint(my_func, [5], {'y': 20})
            >>> result
            25

            >>> async def async_func():
            ...     return "async result"
            >>> result = EntrypointFinder.call_entrypoint(async_func, [], {})
            >>> result
            'async result'
        """
        # Inspect function signature
        sig = inspect.signature(func)

        # Check if function accepts args
        params = sig.parameters
        has_var_positional = any(
            p.kind == inspect.Parameter.VAR_POSITIONAL for p in params.values()
        )
        has_var_keyword = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
        )

        # Prepare call arguments
        call_args = args if (has_var_positional or len(params) > 0) else []
        call_kwargs = kwargs if has_var_keyword else {}

        # If function has named parameters, try to match kwargs
        if not has_var_keyword and kwargs:
            call_kwargs = {k: v for k, v in kwargs.items() if k in params}

        # Check if function is async
        if asyncio.iscoroutinefunction(func):
            return asyncio.run(func(*call_args, **call_kwargs))

        return func(*call_args, **call_kwargs)
