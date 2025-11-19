"""Tests for config.generator module."""

import pytest

from kohakuengine.config import Config
from kohakuengine.config.generator import ConfigGenerator


def test_config_generator_iteration():
    """Test basic config generator iteration."""

    def my_gen():
        for i in range(3):
            yield Config(globals_dict={"iteration": i})

    gen = ConfigGenerator(my_gen())

    configs = list(gen)
    assert len(configs) == 3

    for i, cfg in enumerate(configs):
        assert isinstance(cfg, Config)
        assert cfg.globals_dict == {"iteration": i}


def test_config_generator_exhaustion():
    """Test generator exhaustion detection."""

    def my_gen():
        yield Config(globals_dict={"value": 1})

    gen = ConfigGenerator(my_gen())

    # First iteration works
    config = next(gen)
    assert config.globals_dict == {"value": 1}

    # Second iteration raises StopIteration
    with pytest.raises(StopIteration):
        next(gen)

    # Generator is marked as exhausted
    assert gen.exhausted


def test_config_generator_type_validation():
    """Test that generator validates yielded types."""

    def invalid_gen():
        yield "not a config"  # Invalid!

    gen = ConfigGenerator(invalid_gen())

    with pytest.raises(TypeError, match="Generator must yield Config objects"):
        next(gen)
