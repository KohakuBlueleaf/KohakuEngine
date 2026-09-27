"""KohakuEngine -- All-in-Python configuration and execution engine.

Public API (Idea-numbered for cross-reference with plans/ux-redesign-v0.2/):

- :class:`Config`, :class:`ConfigGenerator` -- the configuration core.
- :class:`Script`, :class:`Flow` -- execution primitives.
- :func:`run` -- one-liner convenience wrapper.
- :func:`use`, :func:`capture_globals` -- legacy capture helpers
  (``capture_globals`` is deprecated in v0.2; see Idea 12).
- :func:`entrypoint` -- decorator marking the explicit script entrypoint (Idea 6).
- :class:`FormatArg`, :class:`RawArg`, :func:`coerce_value` -- typed overrides.
"""

__version__ = "0.2.0"

from kohakuengine.config import (
    CaptureGlobals,
    Config,
    ConfigGenerator,
    RawArg,
    Use,
    capture_globals,
    load_config_file,
    load_from_dict,
    use,
    use_config,
)
from kohakuengine.engine import (
    EntrypointNotFound,
    FormatArg,
    MultipleEntrypoints,
    Script,
    ScriptExecutor,
    ScriptSchema,
    coerce_globals,
    coerce_value,
    entrypoint,
    introspect,
    introspect_schema,
)
from kohakuengine.flow import Flow, Parallel, Pipeline, Sequential
from kohakuengine.main import run

__all__ = [
    "CaptureGlobals",
    "Config",
    "ConfigGenerator",
    "EntrypointNotFound",
    "Flow",
    "FormatArg",
    "MultipleEntrypoints",
    "Parallel",
    "Pipeline",
    "RawArg",
    "Script",
    "ScriptExecutor",
    "ScriptSchema",
    "Sequential",
    "Use",
    "__version__",
    "capture_globals",
    "coerce_globals",
    "coerce_value",
    "entrypoint",
    "introspect",
    "introspect_schema",
    "load_config_file",
    "load_from_dict",
    "run",
    "use",
    "use_config",
]
