"""Config cell detection, evaluation, and AST rewrite (Idea 7).

A config cell is a region of a script marked by special comments:

    # %% kogine:config
    a = expensive_function()
    b = 42
    # %% kogine:script

When Kogine runs the script:

1. Eval the cell *once* (with override values applied).
2. Mutate the script's AST so the cell's assignments become literal
   constants (or ``_KOGINE_FROZEN[name]`` lookups for non-literal values).
3. Compile the mutated AST with the *original* filename so tracebacks
   stay correct, and prime ``linecache`` so source previews still appear.

This way, any re-execution path inside one script run (fork-mode workers,
``importlib.reload``) sees frozen values -- ``expensive_function`` does
not run more than once.

Scope: per script run. A sweep over N configs = N independent evaluations.
Spawn-mode workers that re-import the file from disk see the original
source and will re-execute the cell -- expected limitation.
"""

import ast
import io
import linecache
import re
import tokenize
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

_MARKER_RE = re.compile(r"^\s*#\s*%%\s*kogine\s*:\s*(\w+)\s*$")
_FROZEN_NAME = "_KOGINE_FROZEN"

# Types that ast.Constant can represent directly. Anything else gets stashed
# in the _KOGINE_FROZEN dict and referenced by Subscript.
_CONSTANT_TYPES: tuple[type, ...] = (
    type(None),
    bool,
    int,
    float,
    complex,
    str,
    bytes,
)


@dataclass
class CellInfo:
    """Metadata about a config cell discovered in a script."""

    config_line: int
    script_line: int | None  # None means cell is open-ended

    def in_cell(self, lineno: int) -> bool:
        if lineno <= self.config_line:
            return False
        if self.script_line is not None and lineno >= self.script_line:
            return False
        return True


def parse_cell(script_path: Path) -> CellInfo | None:
    """
    Find the first config cell in a script. Returns ``None`` if no cell.

    Uses :mod:`tokenize` because ``ast`` drops comments.
    """
    src = Path(script_path).read_text(encoding="utf-8")
    return _parse_cell_from_source(src)


def _parse_cell_from_source(src: str) -> CellInfo | None:
    config_line: int | None = None
    script_line: int | None = None
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except tokenize.TokenError:
        return None
    for tok in tokens:
        if tok.type != tokenize.COMMENT:
            continue
        m = _MARKER_RE.match(tok.string)
        if not m:
            continue
        kind = m.group(1)
        if kind == "config" and config_line is None:
            config_line = tok.start[0]
        elif kind == "script" and config_line is not None and script_line is None:
            script_line = tok.start[0]
    if config_line is None:
        return None
    return CellInfo(config_line=config_line, script_line=script_line)


def _cell_assign_nodes(tree: ast.Module, cell: CellInfo) -> list[ast.Assign]:
    """Return the contiguous run of plain ``Assign`` nodes inside the cell."""
    out: list[ast.Assign] = []
    for node in tree.body:
        if node.lineno <= cell.config_line:
            continue
        if cell.script_line is not None and node.lineno >= cell.script_line:
            break
        if isinstance(node, ast.Assign) and all(
            isinstance(t, ast.Name) for t in node.targets
        ):
            out.append(node)
        else:
            warnings.warn(
                f"Non-assignment statement at line {node.lineno} inside config cell; "
                "cell ends here.",
                stacklevel=3,
            )
            break
    return out


def _preamble_nodes(tree: ast.Module, cell: CellInfo) -> list[ast.stmt]:
    return [n for n in tree.body if n.lineno < cell.config_line]


def _is_constant_safe(value: Any) -> bool:
    if isinstance(value, _CONSTANT_TYPES):
        return True
    if isinstance(value, tuple):
        return all(_is_constant_safe(v) for v in value)
    if isinstance(value, frozenset):
        return all(_is_constant_safe(v) for v in value)
    return False


_EVALUATION_CACHE: dict[tuple[str, float], dict[str, Any]] = {}


def evaluate_cell(script_path: Path, cell: CellInfo) -> dict[str, Any]:
    """
    Evaluate the cell (with its preamble) and return ``{name: value}``.

    Imports above the cell are executed so that names referenced in the
    cell resolve correctly. Code *below* the cell does not run.

    Results are memoized for the lifetime of the Python process, keyed on
    ``(path, mtime)``. This avoids re-evaluating expensive cells when
    introspection and execution touch the same script in one CLI invocation.
    """
    script_path = Path(script_path).resolve()
    mtime = script_path.stat().st_mtime
    cache_key = (str(script_path), mtime)
    if cache_key in _EVALUATION_CACHE:
        return dict(_EVALUATION_CACHE[cache_key])

    src = script_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(script_path))

    preamble = _preamble_nodes(tree, cell)
    assigns = _cell_assign_nodes(tree, cell)

    preamble_mod = ast.Module(body=preamble, type_ignores=[])
    cell_mod = ast.Module(body=list(assigns), type_ignores=[])
    ast.fix_missing_locations(preamble_mod)
    ast.fix_missing_locations(cell_mod)

    sandbox: dict[str, Any] = {
        "__name__": "_kogine_cell_eval",
        "__file__": str(script_path),
        "__builtins__": __builtins__,
    }
    _prime_linecache(script_path, src)
    exec(compile(preamble_mod, str(script_path), "exec"), sandbox)
    exec(compile(cell_mod, str(script_path), "exec"), sandbox)

    result = {
        name: sandbox[name]
        for node in assigns
        for name in (node.targets[0].id,)
        if name in sandbox
    }
    _EVALUATION_CACHE[cache_key] = dict(result)
    return result


def clear_cell_cache() -> None:
    """Clear the cached cell evaluations (test helper / long-running daemons)."""
    _EVALUATION_CACHE.clear()


def _prime_linecache(script_path: Path, src: str) -> None:
    path_str = str(script_path)
    lines = src.splitlines(keepends=True)
    linecache.cache[path_str] = (len(src), None, lines, path_str)


def _build_frozen_node(name: str) -> ast.expr:
    """Build the AST for ``_KOGINE_FROZEN["name"]``."""
    return ast.Subscript(
        value=ast.Name(id=_FROZEN_NAME, ctx=ast.Load()),
        slice=ast.Constant(value=name),
        ctx=ast.Load(),
    )


def _rewrite_assigns(
    cell_nodes: Iterable[ast.Assign],
    resolved: dict[str, Any],
) -> dict[str, Any]:
    """
    Mutate cell assignments to either ``Constant`` or frozen-dict lookups.

    Returns the dict of values that must be injected as ``_KOGINE_FROZEN``
    before the rewritten code is executed.
    """
    frozen: dict[str, Any] = {}
    for node in cell_nodes:
        name = node.targets[0].id
        if name not in resolved:
            continue
        value = resolved[name]
        if _is_constant_safe(value):
            new_value: ast.expr = ast.Constant(value=value)
        else:
            frozen[name] = value
            new_value = _build_frozen_node(name)
        ast.copy_location(new_value, node.value)
        for child in ast.walk(new_value):
            ast.copy_location(child, node.value)
        node.value = new_value
    return frozen


def execute_with_cell(
    script_path: Path,
    overrides: dict[str, Any] | None,
    module_dict: dict[str, Any],
) -> tuple[ast.Module, dict[str, Any], dict[str, Any]]:
    """
    Run the cell pipeline on ``script_path`` and execute the rewritten module.

    Args:
        script_path: Path to a script with a config cell.
        overrides: Override values from a Config (may be ``None``).
        module_dict: The module ``__dict__`` to populate. Must already have
            ``__name__``, ``__file__`` set as desired by the caller.

    Returns:
        Tuple of ``(rewritten_tree, evaluated_cell_state, frozen_dict)``.
        ``module_dict`` is updated in place.
    """
    script_path = Path(script_path)
    src = script_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(script_path))
    cell = _parse_cell_from_source(src)
    if cell is None:
        raise RuntimeError("execute_with_cell called on a script without a cell")

    assigns = _cell_assign_nodes(tree, cell)
    declared = {n.targets[0].id for n in assigns}

    evaluated = evaluate_cell(script_path, cell)
    overrides = overrides or {}
    cell_overrides = {k: v for k, v in overrides.items() if k in declared}
    non_cell_overrides = {k: v for k, v in overrides.items() if k not in declared}

    resolved = {**evaluated, **cell_overrides}
    frozen = _rewrite_assigns(assigns, resolved)
    ast.fix_missing_locations(tree)

    _prime_linecache(script_path, src)
    module_dict[_FROZEN_NAME] = frozen
    code = compile(tree, filename=str(script_path), mode="exec")
    exec(code, module_dict)

    # Apply non-cell overrides via straight setattr-style injection.
    for k, v in non_cell_overrides.items():
        module_dict[k] = v

    return tree, evaluated, frozen


def has_cell(script_path: str | Path) -> bool:
    """Return ``True`` if ``script_path`` contains a config cell marker."""
    return parse_cell(Path(script_path)) is not None
