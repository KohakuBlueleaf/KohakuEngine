"""Tests for config.loader module."""

import pytest

from kohakuengine.config.base import Config
from kohakuengine.config.generator import ConfigGenerator
from kohakuengine.config.loader import ConfigLoader


def test_load_static_config(simple_config):
    """Test loading a static config."""
    config = ConfigLoader.load_config(simple_config)

    assert isinstance(config, Config)
    assert config.globals_dict == {"learning_rate": 0.01, "batch_size": 64}
    assert config.kwargs == {"device": "cuda"}


def test_load_generator_config(generator_config):
    """Test loading a generator config."""
    config = ConfigLoader.load_config(generator_config)

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


def test_load_from_dict():
    """Test creating config from dictionary."""
    data = {
        "globals": {"learning_rate": 0.001},
        "args": [1, 2],
        "kwargs": {"device": "cuda"},
        "metadata": {"exp": "test"},
    }

    config = ConfigLoader.load_from_dict(data)

    assert isinstance(config, Config)
    assert config.globals_dict == {"learning_rate": 0.001}
    assert config.args == [1, 2]
    assert config.kwargs == {"device": "cuda"}
    assert config.metadata == {"exp": "test"}


def test_load_from_dict_minimal():
    """Test creating config from minimal dictionary."""
    config = ConfigLoader.load_from_dict({})

    assert config.globals_dict == {}
    assert config.args == []
    assert config.kwargs == {}
    assert config.metadata == {}
