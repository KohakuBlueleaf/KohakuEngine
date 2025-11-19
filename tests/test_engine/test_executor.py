"""Tests for engine.executor module."""

import pytest

from kohakuengine.config import Config
from kohakuengine.engine import Script
from kohakuengine.engine.executor import ScriptExecutor


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


def test_executor_no_entrypoint(tmp_path):
    """Test executor with script that has no entrypoint."""
    script_file = tmp_path / "no_entry.py"
    script_file.write_text("x = 10")  # No main or if __name__

    script = Script(script_file, config=Config())
    executor = ScriptExecutor(script)

    with pytest.raises(RuntimeError, match="No entrypoint found"):
        executor.execute()


def test_executor_config_override(simple_script):
    """Test executor with config override."""
    script_config = Config(globals_dict={"value": 1})
    script = Script(simple_script, config=script_config)

    executor = ScriptExecutor(script)

    # Override with different config at execution time
    override_config = Config(globals_dict={"value": 2})
    executor.execute(override_config)
