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
        path: Path to Python script file
        config: Configuration (Config or ConfigGenerator)
        entrypoint: Name of entrypoint function (default: auto-detect)
        run_as_main: Execute as __main__ process (default: True)

    Examples:
        >>> script = Script('train.py', config=Config(globals_dict={'lr': 0.001}))
        >>> script.name
        'train'
    """

    path: str | Path
    config: Config | ConfigGenerator | None = None
    entrypoint: str | None = None
    run_as_main: bool = True

    def __post_init__(self) -> None:
        """Validate script path."""
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
