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


def test_executor_no_double_execution(tmp_path):
    """Test that if __name__ == '__main__' does NOT execute during import.

    This is critical - the entrypoint should only be called ONCE by the executor,
    not during the import phase.
    """
    script_file = tmp_path / "count_script.py"
    script_file.write_text(
        """
execution_count = 0

def main():
    global execution_count
    execution_count += 1
    return execution_count

if __name__ == "__main__":
    main()
"""
    )

    script = Script(script_file)
    executor = ScriptExecutor(script)

    result = executor.execute()

    # The main() should only be called ONCE by the executor
    # If the guard executed during import, this would be 2
    assert (
        result == 1
    ), f"Expected 1 execution, got {result}. Main guard executed during import!"
    assert executor.module.execution_count == 1


def test_executor_explicit_entrypoint(tmp_path):
    """Test that user can specify a custom entrypoint function."""
    script_file = tmp_path / "multi_entry.py"
    script_file.write_text(
        """
def train():
    return "trained"

def evaluate():
    return "evaluated"

def main():
    return "main"

if __name__ == "__main__":
    main()
"""
    )

    # Test custom entrypoint via constructor
    script = Script(script_file, entrypoint="evaluate")
    result = script.run()
    assert result == "evaluated"

    # Test custom entrypoint via path syntax
    script = Script(f"{script_file}:train")
    result = script.run()
    assert result == "trained"


def test_executor_async_entrypoint(tmp_path):
    """Test that async functions work as entrypoints."""
    script_file = tmp_path / "async_script.py"
    script_file.write_text(
        """
import asyncio

async def main():
    await asyncio.sleep(0.001)
    return "async success"

if __name__ == "__main__":
    asyncio.run(main())
"""
    )

    script = Script(script_file)
    executor = ScriptExecutor(script)

    result = executor.execute()
    assert result == "async success"


def test_executor_async_with_args(tmp_path):
    """Test async entrypoint with arguments."""
    script_file = tmp_path / "async_args.py"
    script_file.write_text(
        """
import asyncio

async def process(x, y=10):
    await asyncio.sleep(0.001)
    return x + y

if __name__ == "__main__":
    asyncio.run(process(5))
"""
    )

    config = Config(args=[20], kwargs={"y": 30})
    script = Script(script_file, config=config)

    result = script.run()
    assert result == 50


def test_executor_async_explicit_entrypoint(tmp_path):
    """Test explicit async entrypoint selection."""
    script_file = tmp_path / "async_multi.py"
    script_file.write_text(
        """
import asyncio

async def fetch_data():
    await asyncio.sleep(0.001)
    return "fetched"

async def process_data():
    await asyncio.sleep(0.001)
    return "processed"

if __name__ == "__main__":
    asyncio.run(fetch_data())
"""
    )

    script = Script(script_file, entrypoint="process_data")
    result = script.run()
    assert result == "processed"


def test_executor_no_entrypoint_no_config_returns_none(tmp_path):
    """Test that executor returns None when no entrypoint and no config."""
    script_file = tmp_path / "no_entry.py"
    script_file.write_text(
        """
# Just a module with no entrypoint
x = 10
y = 20
"""
    )

    script = Script(script_file)
    executor = ScriptExecutor(script)

    result = executor.execute()
    assert result is None


def test_executor_invalid_entrypoint_name(tmp_path):
    """Test error when specified entrypoint doesn't exist."""
    script_file = tmp_path / "script.py"
    script_file.write_text(
        """
def main():
    return "main"

if __name__ == "__main__":
    main()
"""
    )

    script = Script(script_file, entrypoint="nonexistent")
    executor = ScriptExecutor(script)

    with pytest.raises(ValueError, match="Specified entrypoint.*not found"):
        executor.execute()


def test_executor_module_loading_error(tmp_path):
    """Test error handling when module cannot be loaded."""
    # Create a file that will fail to load as a Python module
    # This is hard to trigger, but we can test the path
    # by creating a script that raises an exception during import
    script_file = tmp_path / "bad_import.py"
    script_file.write_text(
        """
raise ImportError("Forced import error")
"""
    )

    script = Script(script_file)
    executor = ScriptExecutor(script)

    with pytest.raises(ImportError, match="Forced import error"):
        executor.execute()
