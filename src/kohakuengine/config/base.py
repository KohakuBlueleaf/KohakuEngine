"""Base configuration classes for KohakuEngine."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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
    def from_file(cls, config_path: str | Path) -> "Config":
        """
        Load config from Python file.

        This is a convenience method that internally uses ConfigLoader.

        Args:
            config_path: Path to Python config file

        Returns:
            Config or ConfigGenerator instance

        Examples:
            >>> config = Config.from_file('config.py')
            >>> config.globals_dict
            {'learning_rate': 0.001}
        """
        from kohakuengine.config.loader import ConfigLoader

        return ConfigLoader.load_config(config_path)

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
