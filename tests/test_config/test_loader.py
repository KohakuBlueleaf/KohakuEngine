"""Tests for config.loader module."""

import pytest

from kohakuengine.config import Config
from kohakuengine.config.generator import ConfigGenerator
from kohakuengine.config.loader import ConfigLoader


def test_load_static_config(simple_config_file):
    """Test loading a static config."""
    config = ConfigLoader.load_config(simple_config_file)

    assert isinstance(config, Config)
    assert config.globals_dict == {"learning_rate": 0.01, "batch_size": 64}
    assert config.kwargs == {"device": "cuda"}


def test_load_generator_config(generator_config_file):
    """Test loading a generator config."""
    config = ConfigLoader.load_config(generator_config_file)

    assert isinstance(config, ConfigGenerator)

    # Iterate through generator
    configs = list(config)
    assert len(configs) == 3

    for i, cfg in enumerate(configs):
        assert isinstance(cfg, Config)
        assert cfg.globals_dict == {"iteration": i}
        assert cfg.kwargs == {"iter_num": i}


def test_load_config_file_not_found():
    """Test loading non-existent config file."""
    with pytest.raises(FileNotFoundError):
        ConfigLoader.load_config("nonexistent_config.py")


def test_load_config_invalid_format(tmp_path):
    """Test loading config with invalid format."""
    config_file = tmp_path / "invalid_config.py"
    config_file.write_text("x = 10")  # No config_gen or CONFIG

    with pytest.raises(ValueError, match="Config file must define"):
        ConfigLoader.load_config(config_file)


def test_config_from_file(simple_config_file):
    """Test Config.from_file() convenience method."""
    config = Config.from_file(simple_config_file)

    assert isinstance(config, Config)
    assert config.globals_dict == {"learning_rate": 0.01, "batch_size": 64}


def test_config_with_worker_id(tmp_path):
    """Test loading config with worker_id parameter."""
    config_file = tmp_path / "worker_config.py"
    config_file.write_text(
        """
from kohakuengine.config import Config

def config_gen(worker_id=None):
    device = f"cuda:{worker_id}" if worker_id is not None else "cpu"
    return Config(globals_dict={'device': device})
"""
    )

    # Without worker_id
    config = ConfigLoader.load_config(config_file)
    assert config.globals_dict == {"device": "cpu"}

    # With worker_id
    config = ConfigLoader.load_config(config_file, worker_id=0)
    assert config.globals_dict == {"device": "cuda:0"}

    config = ConfigLoader.load_config(config_file, worker_id=3)
    assert config.globals_dict == {"device": "cuda:3"}
