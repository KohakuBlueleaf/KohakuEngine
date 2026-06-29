"""KohakuEngine -- All-in-Python configuration and execution engine.

Public API (Idea-numbered for cross-reference with plans/ux-redesign-v0.2/):

- :class:`Config`, :class:`ConfigGenerator` -- the configuration core.
- :class:`Script`, :class:`Flow` -- execution primitives.
- :func:`run` -- one-liner convenience wrapper.
- :func:`use`, :func:`capture_globals` -- legacy capture helpers
  (``capture_globals`` is deprecated in v0.2; see Idea 12).
- :func:`entrypoint` -- decorator marking the explicit script entrypoint (Idea 6).
"""

__version__ = "0.2.0"

from kohakuengine.config import (
    CaptureGlobals,
    Config,
    ConfigGenerator,
    Use,
    capture_globals,
    load_config_file,
    load_from_dict,
    use,
    use_config,
)
from kohakuengine.engine import (
    EntrypointNotFound,
    MultipleEntrypoints,
    Script,
    ScriptExecutor,
    coerce_globals,
    entrypoint,
    introspect,
)
from kohakuengine.flow import Flow, Parallel, Pipeline, Sequential
from kohakuengine.main import run

__all__ = [
    "__version__",
    "Config",
    "ConfigGenerator",
    "Script",
    "ScriptExecutor",
    "Flow",
    "Sequential",
    "Parallel",
    "Pipeline",
    "capture_globals",
    "CaptureGlobals",
    "use",
    "use_config",
    "Use",
    "entrypoint",
    "run",
    "introspect",
    "coerce_globals",
    "load_config_file",
    "load_from_dict",
    "EntrypointNotFound",
    "MultipleEntrypoints",
]
