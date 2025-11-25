"""Script execution orchestration."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from kohakuengine.config.base import Config
from kohakuengine.engine.entrypoint import EntrypointFinder
from kohakuengine.engine.injector import GlobalInjector
from kohakuengine.engine.script import Script


class ScriptExecutor:
    """Execute Python scripts with configuration."""

    def __init__(self, script: Script):
        """
        Initialize executor.

        Args:
            script: Script to execute
        """
        self.script = script
        self._module: ModuleType | None = None

    def execute(self, config: Config | None = None) -> Any:
        """
        Execute script with configuration.

        Execution flow:
        1. Load script as module
        2. Inject global variables from config
        3. Find entrypoint function
        4. Call entrypoint with args/kwargs

        Args:
            config: Configuration to apply (overrides script.config)

        Returns:
            Entrypoint return value

        Raises:
            RuntimeError: If execution fails

        Examples:
            >>> script = Script('train.py', config=Config(globals_dict={'lr': 0.001}))
            >>> executor = ScriptExecutor(script)
            >>> result = executor.execute()
        """
        config = config or self.script.config

        # Load module
        module = self._load_module()

        # Inject global variables if config provided
        if config and config.globals_dict:
            GlobalInjector.inject(module, config.globals_dict)

        # Find and call entrypoint
        entrypoint = self._find_entrypoint(module)
        if entrypoint:
            # Call with args/kwargs if config provided, otherwise no args
            if config:
                result = EntrypointFinder.call_entrypoint(
                    entrypoint, config.args, config.kwargs
                )
            else:
                result = EntrypointFinder.call_entrypoint(entrypoint, [], {})
            return result
        else:
            # If no entrypoint and config is expected, raise error
            if config:
                raise RuntimeError(
                    f"No entrypoint found in {self.script.path}. "
                    f"Expected 'if __name__ == \"__main__\"' block or main() function."
                )
            # No entrypoint and no config - just module import
            return None

    def _load_module(self) -> ModuleType:
        """
        Load script as Python module.

        The module is loaded with a unique name to prevent the
        `if __name__ == "__main__"` block from executing during import.
        The entrypoint is then called explicitly by the executor.

        Returns:
            Loaded module

        Raises:
            RuntimeError: If module cannot be loaded
        """
        # Handle module-based scripts differently
        if self.script.is_module and self.script.module_name:
            return self._load_importable_module()

        return self._load_file_module()

    def _load_file_module(self) -> ModuleType:
        """
        Load script from file path as Python module.

        Returns:
            Loaded module

        Raises:
            RuntimeError: If module cannot be loaded
        """
        script_path = self.script.path.resolve()

        # Use a unique module name to prevent __name__ == "__main__" from executing
        # during import. The entrypoint will be called explicitly after loading.
        module_name = f"_kohaku_script_{self.script.name}_{id(self)}"

        # Create module spec
        spec = importlib.util.spec_from_file_location(module_name, script_path)

        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load script: {script_path}")

        # Create module
        module = importlib.util.module_from_spec(spec)

        # Add to sys.modules temporarily for imports within the script to work
        sys.modules[module_name] = module

        try:
            # Execute module - __name__ will NOT be "__main__" so the guard won't execute
            spec.loader.exec_module(module)
        finally:
            # Clean up from sys.modules
            sys.modules.pop(module_name, None)

        self._module = module
        return module

    def _load_importable_module(self) -> ModuleType:
        """
        Load an importable module by name.

        Returns:
            Loaded module

        Raises:
            RuntimeError: If module cannot be loaded
        """
        import importlib

        module_name = self.script.module_name

        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            raise RuntimeError(f"Cannot import module: {module_name}") from e

        self._module = module
        return module

    def _find_entrypoint(self, module: ModuleType) -> Callable | None:
        """
        Find entrypoint in module.

        Args:
            module: Loaded module

        Returns:
            Entrypoint function or None

        Raises:
            ValueError: If explicit entrypoint specified but not found
        """
        if self.script.entrypoint:
            # Explicit entrypoint specified
            if hasattr(module, self.script.entrypoint):
                return getattr(module, self.script.entrypoint)
            else:
                script_ref = (
                    self.script.module_name
                    if self.script.is_module
                    else self.script.path
                )
                raise ValueError(
                    f"Specified entrypoint '{self.script.entrypoint}' "
                    f"not found in {script_ref}"
                )
        else:
            # Auto-detect entrypoint
            # For module-based scripts, use the path (which points to the module file)
            # or fall back to main() lookup only
            if self.script.is_module:
                return EntrypointFinder.find_entrypoint_for_module(module)
            return EntrypointFinder.find_entrypoint(module, self.script.path)

    @property
    def module(self) -> ModuleType | None:
        """Get loaded module (None if not executed yet)."""
        return self._module
