"""Script representation for KohakuEngine."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kohakuengine.config.base import Config
from kohakuengine.config.generator import ConfigGenerator


@dataclass
class Script:
    """
    Represents an executable Python script.

    Attributes:
        path: Path to Python script file (can include entrypoint as script.py:func_name)
        config: Configuration (Config or ConfigGenerator)
        entrypoint: Name of entrypoint function (default: auto-detect from if __name__ == "__main__")

    Examples:
        >>> script = Script('train.py', config=Config(globals_dict={'lr': 0.001}))
        >>> script.name
        'train'

        >>> # Specify entrypoint explicitly
        >>> script = Script('train.py:custom_train')
        >>> script.entrypoint
        'custom_train'
    """

    path: str | Path
    config: Config | ConfigGenerator | None = None
    entrypoint: str | None = None

    def __post_init__(self) -> None:
        """Validate script path and parse entrypoint if specified."""
        # Check if path contains entrypoint (script.py:function)
        # Handle Windows paths like C:\path\script.py:func correctly
        path_str = str(self.path)

        # Look for pattern: ends with .py:identifier
        # This handles both Unix and Windows paths
        import re

        match = re.search(r"\.py:([a-zA-Z_][a-zA-Z0-9_]*)$", path_str)
        if match:
            entrypoint_name = match.group(1)
            script_path = path_str[: match.start() + 3]  # Include .py
            self.path = Path(script_path)
            if self.entrypoint is None:  # Only override if not already set
                self.entrypoint = entrypoint_name
        else:
            self.path = Path(self.path)

        if not self.path.exists():
            raise FileNotFoundError(f"Script not found: {self.path}")
        if self.path.suffix != ".py":
            raise ValueError(f"Script must be .py file: {self.path}")

    @property
    def name(self) -> str:
        """Get script name (filename without extension)."""
        return self.path.stem

    def __repr__(self) -> str:
        config_type = type(self.config).__name__ if self.config else "None"
        return f"Script(path={self.path}, config={config_type})"

    def run(self, config: Config | None = None) -> Any:
        """
        Execute the script.

        This is a convenience method that internally uses ScriptExecutor.

        Args:
            config: Optional config to override script's config

        Returns:
            Script execution result

        Examples:
            >>> script = Script('train.py', config=Config(globals_dict={'lr': 0.001}))
            >>> result = script.run()
        """
        from kohakuengine.engine.executor import ScriptExecutor

        executor = ScriptExecutor(self)
        return executor.execute(config)
