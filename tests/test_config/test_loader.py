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


def test_load_config_gen_not_callable(tmp_path):
    """Test error when config_gen is not callable."""
    config_file = tmp_path / "bad_config.py"
    config_file.write_text(
        """
config_gen = "not a function"
"""
    )

    with pytest.raises(ValueError, match="config_gen must be callable"):
        ConfigLoader.load_config(config_file)


def test_load_config_gen_wrong_return_type(tmp_path):
    """Test error when config_gen returns wrong type."""
    config_file = tmp_path / "bad_config.py"
    config_file.write_text(
        """
def config_gen():
    return {"not": "a config"}
"""
    )

    with pytest.raises(ValueError, match="must return Config or generator"):
        ConfigLoader.load_config(config_file)


def test_load_CONFIG_variable(tmp_path):
    """Test loading config from CONFIG variable."""
    config_file = tmp_path / "config.py"
    config_file.write_text(
        """
from kohakuengine import Config

CONFIG = Config(globals_dict={'method': 'variable'})
"""
    )

    config = ConfigLoader.load_config(config_file)
    assert isinstance(config, Config)
    assert config.globals_dict == {"method": "variable"}


def test_load_CONFIG_wrong_type(tmp_path):
    """Test error when CONFIG is not a Config instance."""
    config_file = tmp_path / "bad_config.py"
    config_file.write_text(
        """
CONFIG = {"not": "a config"}
"""
    )

    with pytest.raises(ValueError, match="CONFIG must be Config instance"):
        ConfigLoader.load_config(config_file)


def test_load_from_dict_full():
    """Test loading config from dictionary with all fields."""
    data = {
        "globals": {"lr": 0.01, "batch_size": 32},
        "args": [1, 2, 3],
        "kwargs": {"device": "cuda"},
        "metadata": {"experiment": "test1"},
    }

    config = ConfigLoader.load_from_dict(data)
    assert config.globals_dict == {"lr": 0.01, "batch_size": 32}
    assert config.args == [1, 2, 3]
    assert config.kwargs == {"device": "cuda"}
    assert config.metadata == {"experiment": "test1"}


def test_load_from_dict_partial():
    """Test loading config from dictionary with partial data."""
    data = {"globals": {"lr": 0.01}}

    config = ConfigLoader.load_from_dict(data)
    assert config.globals_dict == {"lr": 0.01}
    assert config.args == []
    assert config.kwargs == {}
    assert config.metadata == {}


def test_load_from_dict_empty():
    """Test loading config from empty dictionary."""
    config = ConfigLoader.load_from_dict({})
    assert config.globals_dict == {}
    assert config.args == []
    assert config.kwargs == {}
    assert config.metadata == {}


def test_config_gen_returns_list(tmp_path):
    """Test that config_gen can return a list (iterable)."""
    config_file = tmp_path / "list_config.py"
    config_file.write_text(
        """
from kohakuengine import Config

def config_gen():
    # Return a generator expression
    return (Config(globals_dict={'value': i}) for i in range(3))
"""
    )

    config = ConfigLoader.load_config(config_file)
    assert isinstance(config, ConfigGenerator)

    configs = list(config)
    assert len(configs) == 3
    assert configs[0].globals_dict == {"value": 0}
    assert configs[2].globals_dict == {"value": 2}
