"""Execution engine for KohakuEngine."""

from kohakuengine.engine.cell import (
    CellInfo,
    evaluate_cell,
    execute_with_cell,
    has_cell,
    parse_cell,
)
from kohakuengine.engine.coerce import coerce_globals
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
from kohakuengine.engine.introspect import introspect
from kohakuengine.engine.script import Script


def _script_run(self, config=None, use_subprocess=False):
    """Attached at import time -- breaks the Script <-> Executor import cycle."""
    if use_subprocess:
        return self._run_subprocess(config)
    return ScriptExecutor(self).execute(config)


Script.run = _script_run


__all__ = [
    "Script",
    "ScriptExecutor",
    "GlobalInjector",
    "EntrypointFinder",
    "EntrypointNotFound",
    "MultipleEntrypoints",
    "entrypoint",
    "find_entrypoint",
    "call_entrypoint",
    "CellInfo",
    "parse_cell",
    "evaluate_cell",
    "execute_with_cell",
    "has_cell",
    "coerce_globals",
    "introspect",
]
