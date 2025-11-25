"""Script representation for KohakuEngine."""

import importlib
import importlib.util
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kohakuengine.config.base import Config
from kohakuengine.config.generator import ConfigGenerator


@dataclass
class Script:
    """
    Represents an executable Python script or importable module.

    Attributes:
        path: Path to Python script file (can include entrypoint as script.py:func_name)
              OR importable module name (e.g., 'mypackage.mymodule' or 'mypackage.mymodule:func')
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

        >>> # Use importable module
        >>> script = Script('mypackage.train')
        >>> script.is_module
        True

        >>> # Module with entrypoint
        >>> script = Script('mypackage.train:run')
        >>> script.module_name
        'mypackage.train'
    """

    path: str | Path
    config: Config | ConfigGenerator | None = None
    entrypoint: str | None = None
    # Internal fields set during __post_init__
    is_module: bool = field(default=False, init=False)
    module_name: str | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        """Validate script path/module and parse entrypoint if specified."""
        path_str = str(self.path)

        # First, check if this looks like a module path (contains dots but no path separators
        # before .py, or doesn't end with .py)
        if self._looks_like_module(path_str):
            self._init_as_module(path_str)
        else:
            self._init_as_file(path_str)

    def _looks_like_module(self, path_str: str) -> bool:
        """
        Determine if the path looks like an importable module name.

        Module patterns:
        - 'package.module' (no .py extension)
        - 'package.module:entrypoint'

        File patterns:
        - 'script.py'
        - './script.py'
        - '/path/to/script.py'
        - 'C:\\path\\script.py'
        - 'script.py:entrypoint'
        """
        # If it contains path separators, it's a file
        if "/" in path_str or "\\" in path_str:
            return False

        # If it ends with .py (with optional :entrypoint), it's a file
        if re.search(r"\.py(:[a-zA-Z_][a-zA-Z0-9_]*)?$", path_str):
            return False

        # Otherwise, it's likely a module (e.g., 'package.module' or 'package.module:func')
        return True

    def _init_as_module(self, path_str: str) -> None:
        """Initialize Script from an importable module name."""
        # Parse entrypoint from module:entrypoint syntax
        if ":" in path_str:
            module_part, entrypoint_part = path_str.rsplit(":", 1)
            if self.entrypoint is None:
                self.entrypoint = entrypoint_part
        else:
            module_part = path_str

        # Validate module is importable
        spec = importlib.util.find_spec(module_part)
        if spec is None:
            raise ModuleNotFoundError(f"Module not found: {module_part}")

        self.is_module = True
        self.module_name = module_part

        # Set path to the module's file location if available
        if spec.origin and spec.origin != "built-in":
            self.path = Path(spec.origin)
        else:
            # For built-in or namespace packages, keep as string
            self.path = Path(module_part.replace(".", "/"))

    def _init_as_file(self, path_str: str) -> None:
        """Initialize Script from a file path."""
        # Check if path contains entrypoint (script.py:function)
        # Handle Windows paths like C:\path\script.py:func correctly
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

        self.is_module = False
        self.module_name = None

    @property
    def name(self) -> str:
        """Get script name (module name or filename without extension)."""
        if self.is_module and self.module_name:
            # Return the last part of the module name
            return self.module_name.split(".")[-1]
        return self.path.stem

    def __repr__(self) -> str:
        config_type = type(self.config).__name__ if self.config else "None"
        if self.is_module:
            return f"Script(module={self.module_name}, config={config_type})"
        return f"Script(path={self.path}, config={config_type})"

    def run(self, config: Config | None = None, use_subprocess: bool = False) -> Any:
        """
        Execute the script.

        This is a convenience method that internally uses ScriptExecutor.

        Args:
            config: Optional config to override script's config
            use_subprocess: If True, run in subprocess (useful for asyncio scripts)

        Returns:
            Script execution result (or CompletedProcess if use_subprocess=True)

        Examples:
            >>> script = Script('train.py', config=Config(globals_dict={'lr': 0.001}))
            >>> result = script.run()

            >>> # Use subprocess for asyncio scripts
            >>> result = script.run(use_subprocess=True)
        """
        if use_subprocess:
            return self._run_subprocess(config)

        from kohakuengine.engine.executor import ScriptExecutor

        executor = ScriptExecutor(self)
        return executor.execute(config)

    def _run_subprocess(
        self, config: Config | None = None
    ) -> subprocess.CompletedProcess:
        """
        Execute script in subprocess.

        Args:
            config: Configuration to apply

        Returns:
            CompletedProcess object
        """
        import os

        config = config or self.config
        env = os.environ.copy()
        env["KOGINE_WORKER_ID"] = "0"

        # Use module name if this is a module-based script, otherwise use path
        script_ref = self.module_name if self.is_module else str(self.path)

        if config and not isinstance(config, ConfigGenerator):
            temp_config = self._create_temp_config(config)
            cmd = [
                sys.executable,
                "-m",
                "kohakuengine.cli",
                "run",
                script_ref,
                "--config",
                str(temp_config),
            ]
        else:
            cmd = [sys.executable, "-m", "kohakuengine.cli", "run", script_ref]

        proc = subprocess.Popen(cmd, env=env)
        proc.wait()
        return proc

    def _create_temp_config(self, config: Config) -> Path:
        """
        Create temporary Python config file.

        Args:
            config: Config to serialize

        Returns:
            Path to temporary config file
        """
        fd, path = tempfile.mkstemp(suffix=".py", prefix="kogine_config_")

        with open(path, "w", encoding="utf-8") as f:
            f.write(
                f"""
from kohakuengine.config import Config

def config_gen():
    return Config(
        globals_dict={config.globals_dict!r},
        args={config.args!r},
        kwargs={config.kwargs!r},
        metadata={config.metadata!r}
    )
"""
            )

        return Path(path)
