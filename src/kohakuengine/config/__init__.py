"""Configuration system for KohakuEngine."""

from kohakuengine.config.base import (
    CaptureGlobals,
    Config,
    Use,
    capture_globals,
    use,
)
from kohakuengine.config.generator import ConfigGenerator
from kohakuengine.config.loader import (
    ConfigLoader,
    load_config_file,
    load_from_dict,
    use_config,
)
from kohakuengine.config.raw import RawArg


def _config_from_file(config_path, worker_id=None):
    return load_config_file(config_path, worker_id=worker_id)


def _config_from_dict(data):
    return load_from_dict(data)


Config.from_file = staticmethod(_config_from_file)
Config.from_dict = staticmethod(_config_from_dict)


__all__ = [
    "CaptureGlobals",
    "Config",
    "ConfigGenerator",
    "ConfigLoader",
    "RawArg",
    "Use",
    "capture_globals",
    "load_config_file",
    "load_from_dict",
    "use",
    "use_config",
]
