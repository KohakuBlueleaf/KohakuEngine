"""Script execution orchestration."""

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable

from kohakuengine.config.base import Config
from kohakuengine.engine.cell import execute_with_cell, parse_cell
from kohakuengine.engine.entrypoint import (
    EntrypointNotFound,
    call_entrypoint,
    find_entrypoint,
)
from kohakuengine.engine.injector import GlobalInjector

if TYPE_CHECKING:
    from kohakuengine.engine.script import Script


class ScriptExecutor:
    """Execute Python scripts with configuration."""

    def __init__(self, script: "Script") -> None:
        self.script = script
        self._module: ModuleType | None = None

    @property
    def module(self) -> ModuleType | None:
        return self._module

    def execute(self, config: Config | None = None) -> Any:
        """Execute the script with optional Config; returns entrypoint result."""
        config = config or self.script.config
        if config is not None and not isinstance(config, Config):
            raise TypeError(
                "Pass a Config (not a ConfigGenerator) here; use Flow for sweeps."
            )

        module = self._load_module(config)
        entrypoint = self._find_entrypoint(module)
        if entrypoint is None:
            if config is not None:
                raise EntrypointNotFound(f"No entrypoint found in {self.script.path}.")
            return None
        if config is None:
            return call_entrypoint(entrypoint, [], {})
        return call_entrypoint(entrypoint, list(config.args), dict(config.kwargs))

    def _load_module(self, config: Config | None) -> ModuleType:
        if self.script.is_module and self.script.module_name:
            module = self._load_importable_module()
            if config is not None and config.globals_dict:
                GlobalInjector.inject(module, config.globals_dict)
            self._module = module
            return module

        script_path = self.script.path.resolve()
        if parse_cell(script_path) is not None:
            module = self._load_with_cell(script_path, config)
        else:
            module = self._load_file_module(script_path)
            if config is not None and config.globals_dict:
                GlobalInjector.inject(module, config.globals_dict)

        self._module = module
        return module

    def _load_file_module(self, script_path: Path) -> ModuleType:
        module_name = f"_kohaku_script_{self.script.name}_{id(self)}"
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load script: {script_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(module_name, None)
        return module

    def _load_with_cell(self, script_path: Path, config: Config | None) -> ModuleType:
        module_name = f"_kohaku_script_{self.script.name}_{id(self)}"
        module = ModuleType(module_name)
        module.__file__ = str(script_path)
        module.__name__ = module_name
        overrides = (
            dict(config.globals_dict) if (config and config.globals_dict) else {}
        )
        sys.modules[module_name] = module
        try:
            execute_with_cell(script_path, overrides, module.__dict__)
        finally:
            sys.modules.pop(module_name, None)
        return module

    def _load_importable_module(self) -> ModuleType:
        module_name = self.script.module_name
        try:
            return importlib.import_module(module_name)
        except ImportError as exc:
            raise RuntimeError(f"Cannot import module: {module_name}") from exc

    def _find_entrypoint(self, module: ModuleType) -> Callable | None:
        try:
            return find_entrypoint(
                module,
                None if self.script.is_module else self.script.path,
                explicit_name=self.script.entrypoint,
            )
        except EntrypointNotFound:
            return None
