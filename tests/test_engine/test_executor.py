"""Tests for engine.executor module."""

import pytest

from kohakuengine.config.base import Config
from kohakuengine.engine.executor import ScriptExecutor
from kohakuengine.engine.script import Script


def test_executor_simple_script(simple_script):
    """Test executing a simple script."""
    script = Script(simple_script)
    executor = ScriptExecutor(script)

    result = executor.execute()
    assert result == "success"


def test_executor_with_global_injection(script_with_globals):
    """Test executor with global variable injection."""
    config = Config(globals_dict={"learning_rate": 0.01, "batch_size": 64})

    script = Script(script_with_globals, config=config)
    executor = ScriptExecutor(script)

    result = executor.execute()
    assert result == 0.01 * 64  # 0.64


def test_executor_with_args(script_with_args):
    """Test executor with arguments."""
    config = Config(args=[10], kwargs={"y": 20})

    script = Script(script_with_args, config=config)
    executor = ScriptExecutor(script)

    result = executor.execute()
    assert result == 30  # 10 + 20


def test_executor_no_config(simple_script):
    """Test executor without config."""
    script = Script(simple_script)
    executor = ScriptExecutor(script)

    result = executor.execute(None)
    # Module loads but entrypoint isn't called without config
    assert result == "success"


def test_executor_invalid_script():
    """Test executor with invalid script path."""
    with pytest.raises(FileNotFoundError):
        Script("nonexistent_script.py")


def test_executor_module_property(simple_script):
    """Test accessing the loaded module."""
    script = Script(simple_script)
    executor = ScriptExecutor(script)

    # Before execution
    assert executor.module is None

    # After execution
    executor.execute()
    assert executor.module is not None
    assert hasattr(executor.module, "main")
