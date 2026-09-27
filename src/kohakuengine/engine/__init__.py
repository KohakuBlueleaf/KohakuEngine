"""Execution engine for KohakuEngine."""

from kohakuengine.engine.cell import (
    CellInfo,
    evaluate_cell,
    evaluate_cell_schema,
    execute_with_cell,
    has_cell,
    parse_cell,
)
from kohakuengine.engine.coerce import (
    FormatArg,
    coerce_globals,
    coerce_value,
    split_top_level,
)
from kohakuengine.engine.entrypoint import (
    EntrypointFinder,
    EntrypointNotFound,
    MultipleEntrypoints,
    call_entrypoint,
    entrypoint,
    find_entrypoint,
)
from kohakuengine.engine.executor import ScriptExecutor
from kohakuengine.engine.injector import GlobalInjector
from kohakuengine.engine.introspect import introspect, introspect_schema
from kohakuengine.engine.overrides import layer_overrides
from kohakuengine.engine.schema import ScriptSchema
from kohakuengine.engine.script import Script


def _script_run(self, config=None, use_subprocess=False):
    """Attached at import time -- breaks the Script <-> Executor import cycle."""
    if use_subprocess:
        return self._run_subprocess(config)
    return ScriptExecutor(self).execute(config)


Script.run = _script_run


__all__ = [
    "CellInfo",
    "EntrypointFinder",
    "EntrypointNotFound",
    "FormatArg",
    "GlobalInjector",
    "MultipleEntrypoints",
    "Script",
    "ScriptExecutor",
    "ScriptSchema",
    "call_entrypoint",
    "coerce_globals",
    "coerce_value",
    "entrypoint",
    "evaluate_cell",
    "evaluate_cell_schema",
    "execute_with_cell",
    "find_entrypoint",
    "has_cell",
    "introspect",
    "introspect_schema",
    "layer_overrides",
    "parse_cell",
    "split_top_level",
]
