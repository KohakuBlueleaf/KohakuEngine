"""Entrypoint discovery and calling (Ideas 5 + 6)."""

import ast
import asyncio
import inspect
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

_DECORATOR_FLAG = "__kogine_entrypoint__"
_DECORATOR_NAME_ATTR = "__kogine_entrypoint_name__"
_CONVENTIONAL_NAMES: tuple[str, ...] = ("main", "run")


class EntrypointNotFound(RuntimeError):
    """Raised when no entrypoint could be found in a script."""


class MultipleEntrypoints(RuntimeError):
    """Raised when more than one ``@kogine.entrypoint`` is defined."""


def entrypoint(arg: Callable | str | None = None, *, name: str | None = None):
    """
    Mark a function as the explicit entrypoint of a script.

    Usage::

        @kogine.entrypoint
        def train(): ...

        @kogine.entrypoint(name="alias")
        def train_v2(): ...
    """

    def mark(func: Callable) -> Callable:
        setattr(func, _DECORATOR_FLAG, True)
        if name is not None:
            setattr(func, _DECORATOR_NAME_ATTR, name)
        return func

    if callable(arg) and not isinstance(arg, str):
        return mark(arg)
    return mark


def _find_decorated(module: ModuleType) -> list[Callable]:
    found: list[Callable] = []
    seen: set[int] = set()
    for value in vars(module).values():
        if callable(value) and getattr(value, _DECORATOR_FLAG, False):
            if id(value) in seen:
                continue
            seen.add(id(value))
            found.append(value)
    return found


def _find_main_block_function(tree: ast.AST) -> str | None:
    """Find the function called inside ``if __name__ == "__main__":``."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        if not _is_main_guard(node.test):
            continue
        for stmt in node.body:
            if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)):
                continue
            call = stmt.value
            if isinstance(call.func, ast.Name):
                return call.func.id
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


def _is_main_guard(node: ast.expr) -> bool:
    if not isinstance(node, ast.Compare):
        return False
    if not (isinstance(node.left, ast.Name) and node.left.id == "__name__"):
        return False
    if not (len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq)):
        return False
    if not (
        len(node.comparators) == 1
        and isinstance(node.comparators[0], ast.Constant)
        and node.comparators[0].value == "__main__"
    ):
        return False
    return True


def _resolve_explicit(module: ModuleType, name: str) -> Callable:
    if not hasattr(module, name):
        raise EntrypointNotFound(f"Specified entrypoint {name!r} not found in module.")
    fn = getattr(module, name)
    if not callable(fn):
        raise EntrypointNotFound(f"{name!r} exists in module but is not callable.")
    return fn


def find_entrypoint(
    module: ModuleType,
    script_path: Path | None = None,
    *,
    explicit_name: str | None = None,
) -> Callable:
    """
    Discover and return the script's entrypoint.

    Cascade:

    1. ``explicit_name`` (from CLI flag or ``script.py:func`` syntax).
    2. ``@kogine.entrypoint`` decorator.
    3. AST detection of ``if __name__ == "__main__":`` block.
    4. ``main()`` then ``run()`` conventional names.
    5. Raise :class:`EntrypointNotFound` with a diagnostic.
    """
    searched: list[str] = []

    if explicit_name:
        return _resolve_explicit(module, explicit_name)

    decorated = _find_decorated(module)
    searched.append("@kogine.entrypoint decorator")
    if len(decorated) > 1:
        names = [getattr(f, "__name__", "<anon>") for f in decorated]
        raise MultipleEntrypoints(
            f"Multiple @kogine.entrypoint functions found: {names}. "
            "Use --entrypoint NAME to disambiguate."
        )
    if decorated:
        return decorated[0]

    searched.append('if __name__ == "__main__": block')
    if script_path is not None and Path(script_path).exists():
        tree = ast.parse(
            Path(script_path).read_text(encoding="utf-8"),
            filename=str(script_path),
        )
        name = _find_main_block_function(tree)
        if name and hasattr(module, name):
            return getattr(module, name)

    for candidate in _CONVENTIONAL_NAMES:
        searched.append(f"{candidate}()")
        fn = getattr(module, candidate, None)
        if callable(fn):
            return fn

    script_ref = str(script_path) if script_path else "<module>"
    diag = "\n".join(f"  - {s}: not found" for s in searched)
    raise EntrypointNotFound(
        f"No entrypoint found in {script_ref}.\n"
        f"Searched (in priority order):\n{diag}\n"
        "Hint: add @kogine.entrypoint to your function, or pass "
        "--entrypoint NAME."
    )


def call_entrypoint(func: Callable, args: list[Any], kwargs: dict[str, Any]) -> Any:
    """Invoke ``func`` with ``args``/``kwargs`` -- async-aware."""
    sig = inspect.signature(func)
    params = sig.parameters
    has_var_positional = any(
        p.kind == inspect.Parameter.VAR_POSITIONAL for p in params.values()
    )
    has_var_keyword = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
    )

    call_args = list(args) if (has_var_positional or params) else []
    if has_var_keyword:
        call_kwargs = dict(kwargs)
    else:
        call_kwargs = {k: v for k, v in kwargs.items() if k in params}

    if asyncio.iscoroutinefunction(func):
        return asyncio.run(func(*call_args, **call_kwargs))
    return func(*call_args, **call_kwargs)


class EntrypointFinder:
    """Back-compatible facade for the previous AST-based API."""

    @staticmethod
    def find_entrypoint(module: ModuleType, script_path: Path) -> Callable | None:
        try:
            return find_entrypoint(module, script_path)
        except EntrypointNotFound:
            return None

    @staticmethod
    def find_entrypoint_for_module(module: ModuleType) -> Callable | None:
        try:
            return find_entrypoint(module, None)
        except EntrypointNotFound:
            return None

    @staticmethod
    def call_entrypoint(func: Callable, args: list[Any], kwargs: dict[str, Any]) -> Any:
        return call_entrypoint(func, args, kwargs)
