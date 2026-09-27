"""High-level Python API for KohakuEngine."""

from typing import Any

from kohakuengine.config import Config, load_config_file
from kohakuengine.engine import (
    ScriptExecutor,
    introspect_schema,
    layer_overrides,
)
from kohakuengine.engine.script import Script

__all__ = ["run"]


def run(
    script_path: str,
    config_path: str | None = None,
    globals_dict: dict[str, Any] | None = None,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    set_overrides: dict[str, Any] | None = None,
    strict: bool = False,
) -> Any:
    """
    Convenience runner that mirrors ``kogine run`` on the command line.

    Resolution:

    1. Load a Config from ``config_path`` (if any).
    2. Override / construct from ``globals_dict``, ``args``, ``kwargs``.
    3. Apply ``set_overrides`` (CLI-style ad-hoc overrides); they are coerced
       when the script loads, against its annotations, then its defaults.
    4. Optionally enforce ``strict`` mode -- unknown keys and failed
       coercions raise.
    """
    script = Script(script_path)
    if config_path is not None:
        config: Config | None = load_config_file(config_path)
        if isinstance(config, Config):
            if globals_dict:
                config.globals_dict = {**config.globals_dict, **globals_dict}
            if args is not None:
                config.args = list(args)
            if kwargs is not None:
                config.kwargs = {**config.kwargs, **kwargs}
    elif globals_dict is not None or args is not None or kwargs is not None:
        config = Config(
            globals_dict=globals_dict or {},
            args=args or [],
            kwargs=kwargs or {},
        )
    else:
        config = None

    if set_overrides or strict:
        declared = introspect_schema(script.path).declared if strict else None
        config = layer_overrides(
            config, set_values=set_overrides, strict=strict, declared=declared
        )

    script.config = config
    return ScriptExecutor(script).execute(config)
