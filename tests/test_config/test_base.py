"""Tests for config.base module."""

import pytest

from kohakuengine.config.base import Config


def test_config_creation():
    """Test basic config creation."""
    config = Config(
        globals_dict={"learning_rate": 0.001, "batch_size": 32},
        args=[1, 2, 3],
        kwargs={"device": "cuda"},
        metadata={"experiment": "test1"},
    )

    assert config.globals_dict == {"learning_rate": 0.001, "batch_size": 32}
    assert config.args == [1, 2, 3]
    assert config.kwargs == {"device": "cuda"}
    assert config.metadata == {"experiment": "test1"}


def test_config_defaults():
    """Test config with default values."""
    config = Config()

    assert config.globals_dict == {}
    assert config.args == []
    assert config.kwargs == {}
    assert config.metadata == {}


def test_config_validation_invalid_globals_dict():
    """Test config validation with invalid globals_dict."""
    with pytest.raises(TypeError, match="globals_dict must be a dict"):
        Config(globals_dict="invalid")


def test_config_validation_invalid_args():
    """Test config validation with invalid args."""
    with pytest.raises(TypeError, match="args must be a list or tuple"):
        Config(args="invalid")


def test_config_validation_invalid_kwargs():
    """Test config validation with invalid kwargs."""
    with pytest.raises(TypeError, match="kwargs must be a dict"):
        Config(kwargs="invalid")


def test_config_validation_invalid_metadata():
    """Test config validation with invalid metadata."""
    with pytest.raises(TypeError, match="metadata must be a dict"):
        Config(metadata="invalid")


def test_config_tuple_args_conversion():
    """Test that tuple args are converted to list."""
    config = Config(args=(1, 2, 3))
    assert isinstance(config.args, list)
    assert config.args == [1, 2, 3]
