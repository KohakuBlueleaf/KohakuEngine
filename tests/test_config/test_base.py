"""Tests for config.base module."""

import pytest

from kohakuengine.config import Config


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


def test_config_invalid_globals_dict():
    """Test config validation with invalid globals_dict."""
    with pytest.raises(TypeError, match="globals_dict must be a dict"):
        Config(globals_dict="invalid")


def test_config_invalid_args():
    """Test config validation with invalid args."""
    with pytest.raises(TypeError, match="args must be a list or tuple"):
        Config(args="invalid")


def test_config_invalid_kwargs():
    """Test config validation with invalid kwargs."""
    with pytest.raises(TypeError, match="kwargs must be a dict"):
        Config(kwargs="invalid")


def test_config_tuple_args_conversion():
    """Test that tuple args are converted to list."""
    config = Config(args=(1, 2, 3))
    assert isinstance(config.args, list)
    assert config.args == [1, 2, 3]


def test_config_from_dict():
    """Test creating config from dictionary."""
    data = {
        "globals": {"lr": 0.001},
        "args": [1, 2],
        "kwargs": {"device": "cuda"},
        "metadata": {"exp": "test"},
    }

    config = Config.from_dict(data)

    assert config.globals_dict == {"lr": 0.001}
    assert config.args == [1, 2]
    assert config.kwargs == {"device": "cuda"}
    assert config.metadata == {"exp": "test"}


def test_config_from_dict_minimal():
    """Test creating config from minimal dictionary."""
    config = Config.from_dict({})

    assert config.globals_dict == {}
    assert config.args == []
    assert config.kwargs == {}
    assert config.metadata == {}


# Tests for capture_globals, from_globals, use()


def test_capture_globals_basic(tmp_path):
    """Test basic capture_globals usage."""
    config_code = """
from kohakuengine import capture_globals, Config

with capture_globals() as ctx:
    learning_rate = 0.01
    batch_size = 64

result = Config.from_context(ctx)
"""
    config_file = tmp_path / "test_config.py"
    config_file.write_text(config_code)

    namespace = {}
    exec(compile(config_file.read_text(), config_file, "exec"), namespace)
    config = namespace["result"]

    assert config.globals_dict["learning_rate"] == 0.01
    assert config.globals_dict["batch_size"] == 64


def test_capture_globals_captures_everything(tmp_path):
    """Test that capture_globals captures modules, functions, and private vars."""
    config_code = """
from kohakuengine import capture_globals, Config

with capture_globals() as ctx:
    import math

    _private = "secret"

    def helper():
        return 42

result = Config.from_context(ctx)
"""
    config_file = tmp_path / "test_config.py"
    config_file.write_text(config_code)

    namespace = {}
    exec(compile(config_file.read_text(), config_file, "exec"), namespace)
    config = namespace["result"]

    # Should capture everything - no filtering
    assert "math" in config.globals_dict
    assert "_private" in config.globals_dict
    assert "helper" in config.globals_dict
    assert config.globals_dict["_private"] == "secret"
    assert config.globals_dict["helper"]() == 42


def test_use_wrapper_with_function():
    """Test use() wrapper with functions."""
    from kohakuengine import use

    def my_func(x):
        return x * 2

    wrapped = use(my_func)
    assert wrapped.value is my_func
    assert wrapped.value(5) == 10


def test_use_wrapper_with_class():
    """Test use() wrapper with classes."""
    from kohakuengine import use

    class MyClass:
        value = 100

    wrapped = use(MyClass)
    assert wrapped.value is MyClass
    assert wrapped.value.value == 100


def test_use_wrapper_with_lambda():
    """Test use() wrapper with lambdas."""
    from kohakuengine import use

    wrapped = use(lambda x: x**2)
    assert wrapped.value(4) == 16


def test_from_globals_basic(tmp_path):
    """Test from_globals() basic usage via exec."""
    # We need to test from_globals in a separate module context
    config_code = """
from kohakuengine import Config

learning_rate = 0.01
batch_size = 64
epochs = 10

def config_gen():
    return Config.from_globals()

result = config_gen()
"""
    config_file = tmp_path / "test_config.py"
    config_file.write_text(config_code)

    # Execute and get result
    namespace = {}
    exec(compile(config_file.read_text(), config_file, "exec"), namespace)
    config = namespace["result"]

    assert config.globals_dict["learning_rate"] == 0.01
    assert config.globals_dict["batch_size"] == 64
    assert config.globals_dict["epochs"] == 10


def test_from_globals_skips_modules(tmp_path):
    """Test that from_globals skips modules."""
    config_code = """
from kohakuengine import Config
import math
import os

learning_rate = 0.01

def config_gen():
    return Config.from_globals()

result = config_gen()
"""
    config_file = tmp_path / "test_config.py"
    config_file.write_text(config_code)

    namespace = {}
    exec(compile(config_file.read_text(), config_file, "exec"), namespace)
    config = namespace["result"]

    assert "learning_rate" in config.globals_dict
    assert "math" not in config.globals_dict
    assert "os" not in config.globals_dict


def test_from_globals_skips_functions(tmp_path):
    """Test that from_globals skips functions unless wrapped with use()."""
    config_code = """
from kohakuengine import Config, use

learning_rate = 0.01

def my_function():
    return 42

wrapped_func = use(lambda x: x * 2)

def config_gen():
    return Config.from_globals()

result = config_gen()
"""
    config_file = tmp_path / "test_config.py"
    config_file.write_text(config_code)

    namespace = {}
    exec(compile(config_file.read_text(), config_file, "exec"), namespace)
    config = namespace["result"]

    assert "learning_rate" in config.globals_dict
    assert "my_function" not in config.globals_dict
    # wrapped_func should be included and unwrapped
    assert "wrapped_func" in config.globals_dict
    assert config.globals_dict["wrapped_func"](5) == 10


def test_from_globals_skips_classes(tmp_path):
    """Test that from_globals skips classes unless wrapped with use()."""
    config_code = """
from kohakuengine import Config, use

learning_rate = 0.01

class MyClass:
    value = 100

wrapped_class = use(MyClass)

def config_gen():
    return Config.from_globals()

result = config_gen()
"""
    config_file = tmp_path / "test_config.py"
    config_file.write_text(config_code)

    namespace = {}
    exec(compile(config_file.read_text(), config_file, "exec"), namespace)
    config = namespace["result"]

    assert "learning_rate" in config.globals_dict
    assert "MyClass" not in config.globals_dict
    # wrapped_class should be included and unwrapped
    assert "wrapped_class" in config.globals_dict
    assert config.globals_dict["wrapped_class"].value == 100


def test_from_globals_skips_private(tmp_path):
    """Test that from_globals skips private variables."""
    config_code = """
from kohakuengine import Config

learning_rate = 0.01
_private = "secret"
__dunder__ = "also private"

def config_gen():
    return Config.from_globals()

result = config_gen()
"""
    config_file = tmp_path / "test_config.py"
    config_file.write_text(config_code)

    namespace = {}
    exec(compile(config_file.read_text(), config_file, "exec"), namespace)
    config = namespace["result"]

    assert "learning_rate" in config.globals_dict
    assert "_private" not in config.globals_dict
    assert "__dunder__" not in config.globals_dict


def test_generator_with_from_globals(tmp_path):
    """Test generator pattern using from_globals as base."""
    config_code = """
from kohakuengine import Config

learning_rate = 0.01
batch_size = 64
epochs = 10

def config_gen():
    base = Config.from_globals()

    for lr in [0.001, 0.01, 0.1]:
        sweep_globals = base.globals_dict.copy()
        sweep_globals["learning_rate"] = lr
        yield Config(globals_dict=sweep_globals, metadata={"lr": lr})

result = list(config_gen())
"""
    config_file = tmp_path / "test_config.py"
    config_file.write_text(config_code)

    namespace = {}
    exec(compile(config_file.read_text(), config_file, "exec"), namespace)
    configs = namespace["result"]

    assert len(configs) == 3

    # Check each config has the swept learning rate
    assert configs[0].globals_dict["learning_rate"] == 0.001
    assert configs[1].globals_dict["learning_rate"] == 0.01
    assert configs[2].globals_dict["learning_rate"] == 0.1

    # Check that other values are preserved
    for config in configs:
        assert config.globals_dict["batch_size"] == 64
        assert config.globals_dict["epochs"] == 10


def test_generator_with_from_globals_nested_sweep(tmp_path):
    """Test nested sweep using from_globals as base."""
    config_code = """
from kohakuengine import Config

learning_rate = 0.01
batch_size = 64
optimizer = "adam"

def config_gen():
    base = Config.from_globals()

    for lr in [0.001, 0.01]:
        for bs in [32, 64]:
            sweep_globals = base.globals_dict.copy()
            sweep_globals["learning_rate"] = lr
            sweep_globals["batch_size"] = bs
            yield Config(
                globals_dict=sweep_globals,
                metadata={"lr": lr, "bs": bs}
            )

result = list(config_gen())
"""
    config_file = tmp_path / "test_config.py"
    config_file.write_text(config_code)

    namespace = {}
    exec(compile(config_file.read_text(), config_file, "exec"), namespace)
    configs = namespace["result"]

    assert len(configs) == 4  # 2 x 2 sweep

    # Verify all combinations
    combinations = [
        (c.globals_dict["learning_rate"], c.globals_dict["batch_size"]) for c in configs
    ]
    assert (0.001, 32) in combinations
    assert (0.001, 64) in combinations
    assert (0.01, 32) in combinations
    assert (0.01, 64) in combinations

    # Check metadata matches
    for config in configs:
        assert config.metadata["lr"] == config.globals_dict["learning_rate"]
        assert config.metadata["bs"] == config.globals_dict["batch_size"]
