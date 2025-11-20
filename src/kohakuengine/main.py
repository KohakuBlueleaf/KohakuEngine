"""
KohakuEngine Python API.

Quick start:
    from kohakuengine import Script, Config, Sequential

    script = Script('train.py', config=Config(
        globals_dict={'learning_rate': 0.001}
    ))
    result = script.run()

Or use the run() convenience function:
    from kohakuengine import run

    run('train.py', globals_dict={'learning_rate': 0.001})
"""

from typing import Any

from kohakuengine.config import Config, capture_globals, use
from kohakuengine.engine import Script
from kohakuengine.flow import Flow


__all__ = [
    "Config",
    "Script",
    "Flow",
    "capture_globals",
    "use",
    "run",
]


def run(
    script_path: str,
    config_path: str | None = None,
    globals_dict: dict[str, Any] | None = None,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
) -> Any:
    """
    Convenience function to run a script.

    Args:
        script_path: Path to script
        config_path: Path to config file (optional)
        globals_dict: Global variables to inject (optional)
        args: Positional arguments for entrypoint (optional)
        kwargs: Keyword arguments for entrypoint (optional)

    Returns:
        Script execution result

    Examples:
        # Run with inline config
        >>> run('train.py', globals_dict={'learning_rate': 0.001})

        # Run with config file
        >>> run('train.py', config_path='config.py')

        # Run with args and kwargs
        >>> run('script.py', args=['arg1'], kwargs={'key': 'value'})
    """
    # Load config
    if config_path:
        config = Config.from_file(config_path)
    elif globals_dict is not None or args is not None or kwargs is not None:
        config = Config(
            globals_dict=globals_dict or {},
            args=args or [],
            kwargs=kwargs or {},
        )
    else:
        config = None

    # Create and run script
    script = Script(script_path, config=config)
    return script.run()
