"""Load a script *without* running its entrypoint.

Used by:

- :func:`kohakuengine.cli.cmd_config_check` -- diff config keys vs. script defaults.
- ``--strict`` pre-flight -- reject override keys the script does not declare.

The script is imported under a non-``__main__`` module name so its
``if __name__ == "__main__":`` guard does not fire.

When the script has a config cell (Idea 7), only the preamble and the cell
are evaluated -- no module-level code below the cell runs.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from kohakuengine.config.base import _filter_globals
from kohakuengine.engine.cell import evaluate_cell_schema, parse_cell
from kohakuengine.engine.schema import ScriptSchema, source_annotations
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


def introspect_schema(script_path: str | Path) -> ScriptSchema:
    """
    Return the script's defaults and top-level annotations.

    With a config cell, only the cell's names form the schema (annotation-only
    ``name: T`` lines included). Otherwise the script is imported without
    firing its ``__main__`` guard; defaults come from :func:`_filter_globals`
    and annotations from its top-level ``name: T [= v]`` statements.
    """
    script_path = Path(script_path)
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    cell = parse_cell(script_path)
    if cell is not None:
        return evaluate_cell_schema(script_path, cell)

    module = _import_no_main(script_path)
    namespace = vars(module)
    return ScriptSchema(
        defaults=_filter_globals(namespace, module.__name__),
        annotations=source_annotations(script_path, namespace),
    )


def introspect(script_path: str | Path) -> dict[str, Any]:
    """Return the script's data-only defaults (``introspect_schema().defaults``)."""
    return introspect_schema(script_path).defaults
