"""Load a script *without* running its entrypoint.

Used by:

- :func:`kohakuengine.cli.cmd_config_check` -- diff config keys vs. script defaults.
- :func:`kohakuengine.engine.coerce.coerce_globals` -- type coercion against
  the script's default values.

The script is imported under a non-``__main__`` module name so its
``if __name__ == "__main__":`` guard does not fire.

When the script has a config cell (Idea 7), we extract the declared names
*statically* via the cell parser -- no module-level code below the cell runs.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from kohakuengine.config.base import _filter_globals
from kohakuengine.engine.cell import CellInfo, evaluate_cell, parse_cell
from kohakuengine.utils import add_script_dir_to_path


def _import_no_main(script_path: Path) -> ModuleType:
    add_script_dir_to_path(script_path)
    module_name = f"_kogine_introspect_{script_path.stem}_{abs(hash(str(script_path)))}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def introspect(script_path: str | Path) -> dict[str, Any]:
    """
    Return the script's data-only defaults.

    If the script has a config cell, only the cell's declared names are
    returned and module-level code below the cell is not executed.
    Otherwise the script is imported (without firing its ``__main__``
    guard) and module-level data is extracted via :func:`_filter_globals`.

    Args:
        script_path: Path to a ``.py`` script.

    Returns:
        Dict of ``{name: default_value}`` -- the configurable surface.
    """
    script_path = Path(script_path)
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    cell = parse_cell(script_path)
    if cell is not None:
        return _introspect_cell_only(script_path, cell)

    module = _import_no_main(script_path)
    return _filter_globals(vars(module), module.__name__)


def _introspect_cell_only(script_path: Path, cell: CellInfo) -> dict[str, Any]:
    """Evaluate ONLY the cell + its preamble (imports above the cell)."""
    return evaluate_cell(script_path, cell)
