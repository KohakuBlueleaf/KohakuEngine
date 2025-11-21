"""Base configuration classes for KohakuEngine."""

import inspect
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any


class CaptureGlobals:
    """
    Context manager to capture global variables defined within a block.

    Examples:
        >>> with capture_globals() as ctx:
        ...     learning_rate = 0.001
        ...     batch_size = 32
        >>> config = Config.from_context(ctx)
        >>> config.globals_dict
        {'learning_rate': 0.001, 'batch_size': 32}
    """

    def __init__(self):
        self.captured: dict[str, Any] = {}
        self._before: set[str] = set()
        self._frame_globals: dict = {}

    def __enter__(self) -> "CaptureGlobals":
        frame = inspect.currentframe().f_back
        self._frame_globals = frame.f_globals
        self._before = set(frame.f_globals.keys())
        return self

    def __exit__(self, *args) -> bool:
        # Capture ALL new variables - no filtering (except the context itself)
        after = set(self._frame_globals.keys())
        new_vars = after - self._before

        for name in new_vars:
            value = self._frame_globals[name]
            # Skip the context variable itself to avoid self-capture
            if value is self:
                continue
            self.captured[name] = value

        return False


def capture_globals() -> CaptureGlobals:
    """
    Create a context manager to capture global variables.

    Returns:
        CaptureGlobals context manager

    Examples:
        >>> with capture_globals() as ctx:
        ...     learning_rate = 0.001
        ...     batch_size = 32
        >>> config = Config.from_context(ctx)
    """
    return CaptureGlobals()


class Use:
    """
    Wrapper to mark functions/classes for inclusion in config capture.

    By default, from_globals() skips functions and classes.
    Wrap them with use() to include them.

    Examples:
        >>> from kohakuengine import Config, use
        >>>
        >>> learning_rate = 0.001
        >>> my_func = use(some_function)
        >>> MyModel = use(SomeModelClass)
        >>>
        >>> def config_gen():
        ...     return Config.from_globals()
    """

    def __init__(self, value: Any):
        self.value = value

    def __repr__(self) -> str:
        return f"use({self.value!r})"


def use(value: Any) -> Use:
    """
    Mark a function/class for inclusion in config capture.

    Args:
        value: Function or class to include

    Returns:
        Use wrapper

    Examples:
        >>> my_func = use(some_function)
        >>> MyModel = use(SomeModelClass)
    """
    return Use(value)


@dataclass
class Config:
    """
    Configuration for script execution.

    This class holds all configuration data needed to execute a script:
    - Global variables to inject into the module
    - Positional arguments for the entrypoint function
    - Keyword arguments for the entrypoint function
    - Optional metadata for tracking and logging

    Attributes:
        globals_dict: Module-level global variables to override
        args: Positional arguments for entrypoint function
        kwargs: Keyword arguments for entrypoint function
        metadata: Optional metadata for tracking/logging

    Examples:
        >>> config = Config(
        ...     globals_dict={'learning_rate': 0.001, 'batch_size': 32},
        ...     kwargs={'device': 'cuda'}
        ... )
        >>> config.globals_dict['learning_rate']
        0.001
    """

    globals_dict: dict[str, Any] = field(default_factory=dict)
    args: list[Any] = field(default_factory=list)
    kwargs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate config structure."""
        if not isinstance(self.globals_dict, dict):
            raise TypeError(
                f"globals_dict must be a dict, got {type(self.globals_dict).__name__}"
            )
        if not isinstance(self.args, (list, tuple)):
            raise TypeError(
                f"args must be a list or tuple, got {type(self.args).__name__}"
            )
        if not isinstance(self.kwargs, dict):
            raise TypeError(f"kwargs must be a dict, got {type(self.kwargs).__name__}")
        if not isinstance(self.metadata, dict):
            raise TypeError(
                f"metadata must be a dict, got {type(self.metadata).__name__}"
            )

        # Convert tuple to list for consistency
        if isinstance(self.args, tuple):
            self.args = list(self.args)

    @classmethod
    def from_file(
        cls, config_path: str | Path, worker_id: int | None = None
    ) -> "Config":
        """
        Load config from Python file.

        This is a convenience method that internally uses ConfigLoader.

        Args:
            config_path: Path to Python config file
            worker_id: Optional worker ID for parallel execution

        Returns:
            Config or ConfigGenerator instance

        Examples:
            >>> config = Config.from_file('config.py')
            >>> config.globals_dict
            {'learning_rate': 0.001}

            >>> # With worker ID (for parallel execution)
            >>> config = Config.from_file('config.py', worker_id=0)
        """
        from kohakuengine.config.loader import ConfigLoader

        return ConfigLoader.load_config(config_path, worker_id=worker_id)

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """
        Create Config from dictionary.

        Args:
            data: Dictionary with config data

        Returns:
            Config instance

        Examples:
            >>> config = Config.from_dict({'globals': {'lr': 0.001}})
            >>> config.globals_dict
            {'lr': 0.001}
        """
        from kohakuengine.config.loader import ConfigLoader

        return ConfigLoader.load_from_dict(data)

    @classmethod
    def from_context(cls, context: CaptureGlobals) -> "Config":
        """
        Create Config from captured globals context.

        Args:
            context: CaptureGlobals context manager

        Returns:
            Config instance

        Examples:
            >>> with capture_globals() as ctx:
            ...     learning_rate = 0.001
            ...     batch_size = 32
            >>> config = Config.from_context(ctx)
            >>> config.globals_dict
            {'learning_rate': 0.001, 'batch_size': 32}
        """
        return cls(globals_dict=context.captured)

    @classmethod
    def from_globals(cls) -> "Config":
        """
        Create Config from caller's global variables.

        Captures all user-defined globals (excludes private, modules,
        functions, classes, and common imports).

        Returns:
            Config instance

        Examples:
            >>> # In config.py:
            >>> learning_rate = 0.001
            >>> batch_size = 32
            >>>
            >>> def config_gen():
            ...     return Config.from_globals()
        """
        frame = inspect.currentframe().f_back
        user_globals = {}

        for name, value in frame.f_globals.items():
            # Skip private/protected
            if name.startswith("_"):
                continue

            # Skip modules
            if isinstance(value, ModuleType):
                continue

            # Handle Use wrapper - unwrap and include
            if isinstance(value, Use):
                user_globals[name] = value.value
                continue

            # Skip types/classes (unless wrapped with use())
            if isinstance(value, type):
                continue

            # Skip callables/functions (unless wrapped with use())
            if callable(value):
                continue

            user_globals[name] = value

        return cls(globals_dict=user_globals)
