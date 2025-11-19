"""Configuration loader for loading configs from Python files."""

import importlib.util
import inspect
import sys
from pathlib import Path

from kohakuengine.config.base import Config
from kohakuengine.config.generator import ConfigGenerator


class ConfigLoader:
    """Load configuration from Python files."""

    @staticmethod
    def load_config(
        config_path: str | Path, worker_id: int | None = None
    ) -> Config | ConfigGenerator:
        """
        Load config from Python file.

        Expected formats:
        1. config_gen() function returning Config
        2. config_gen() generator yielding Config objects
        3. CONFIG variable (Config instance)

        Args:
            config_path: Path to Python config file

        Returns:
            Config or ConfigGenerator

        Raises:
            FileNotFoundError: Config file not found
            ValueError: Invalid config format

        Examples:
            >>> config = ConfigLoader.load_config('config.py')
            >>> isinstance(config, Config)
            True
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Load module dynamically
        spec = importlib.util.spec_from_file_location("config_module", config_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Cannot load config from {config_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules["config_module"] = module
        spec.loader.exec_module(module)

        # Try to find config
        if hasattr(module, "config_gen"):
            config_gen = module.config_gen
            if not callable(config_gen):
                raise ValueError("config_gen must be callable")

            # Check if config_gen accepts worker_id parameter
            sig = inspect.signature(config_gen)
            params = sig.parameters

            # Call config_gen with or without worker_id
            if worker_id is not None and "worker_id" in params:
                result = config_gen(worker_id=worker_id)
            else:
                result = config_gen()

            # Check if it's a generator or Config
            if isinstance(result, Config):
                return result
            elif hasattr(result, "__iter__") and hasattr(result, "__next__"):
                # It's a generator/iterator
                return ConfigGenerator(result)
            else:
                raise ValueError(
                    f"config_gen() must return Config or generator, got {type(result).__name__}"
                )

        elif hasattr(module, "CONFIG"):
            config = module.CONFIG
            if not isinstance(config, Config):
                raise ValueError(
                    f"CONFIG must be Config instance, got {type(config).__name__}"
                )
            return config

        else:
            raise ValueError(
                "Config file must define 'config_gen()' function or 'CONFIG' variable"
            )

    @staticmethod
    def load_from_dict(data: dict) -> Config:
        """
        Create Config from dictionary.

        Useful for loading from JSON/TOML/YAML parsed data.
        Users should parse external formats themselves in config.py.

        Args:
            data: Dictionary with config data

        Returns:
            Config instance

        Examples:
            >>> data = {'globals': {'lr': 0.001}, 'kwargs': {'device': 'cuda'}}
            >>> config = ConfigLoader.load_from_dict(data)
            >>> config.globals_dict['lr']
            0.001
        """
        return Config(
            globals_dict=data.get("globals", {}),
            args=data.get("args", []),
            kwargs=data.get("kwargs", {}),
            metadata=data.get("metadata", {}),
        )
