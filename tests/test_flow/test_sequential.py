"""Tests for flow.sequential module."""

import pytest

from kohakuengine.config import Config
from kohakuengine.config.generator import ConfigGenerator
from kohakuengine.engine import Script
from kohakuengine.flow.sequential import Sequential


def test_sequential_single_script(simple_script):
    """Test sequential execution with single script."""
    script = Script(simple_script)

    workflow = Sequential([script])
    results = workflow.run()

    assert len(results) == 1
    assert results[0] == "success"


def test_sequential_multiple_scripts(simple_script):
    """Test sequential execution with multiple scripts."""
    scripts = [Script(simple_script) for _ in range(3)]

    workflow = Sequential(scripts)
    results = workflow.run()

    assert len(results) == 3
    assert all(r == "success" for r in results)


def test_sequential_with_config(script_with_globals):
    """Test sequential execution with config."""
    config = Config(globals_dict={"learning_rate": 0.01, "batch_size": 64})

    script = Script(script_with_globals, config=config)
    workflow = Sequential([script])

    results = workflow.run()
    assert results[0] == 0.01 * 64


def test_sequential_with_generator(script_with_globals):
    """Test sequential execution with config generator."""

    def my_gen():
        for i in range(3):
            yield Config(globals_dict={"learning_rate": i * 0.01, "batch_size": 32})

    config_gen = ConfigGenerator(my_gen())
    script = Script(script_with_globals, config=config_gen)

    workflow = Sequential([script])
    results = workflow.run()

    # Should run 3 times (one per config)
    assert len(results) == 3
    assert results[0] == 0.0 * 0.01 * 32
    assert results[1] == 1 * 0.01 * 32
    assert results[2] == 2 * 0.01 * 32


def test_sequential_validation_empty():
    """Test that sequential workflow requires at least one script."""
    with pytest.raises(ValueError, match="Workflow must have at least one script"):
        Sequential([])


def test_sequential_validation_missing_file(tmp_path):
    """Test validation with non-existent script."""
    # Create script pointing to non-existent file
    script_file = tmp_path / "missing.py"
    script_file.write_text("x=1")
    script = Script(script_file)

    # Delete the file
    script_file.unlink()

    with pytest.raises(ValueError, match="Script not found"):
        Sequential([script])


def test_sequential_subprocess_mode(tmp_path):
    """Test sequential execution with subprocess mode."""
    script = tmp_path / "script.py"
    script.write_text(
        """
def main():
    print("Subprocess execution")
    return 42

if __name__ == "__main__":
    main()
"""
    )

    workflow = Sequential([Script(script)], use_subprocess=True)
    results = workflow.run()

    assert len(results) == 1
    # Result is a CompletedProcess in subprocess mode
    assert hasattr(results[0], "returncode")


def test_sequential_subprocess_with_config(tmp_path):
    """Test sequential subprocess mode with config."""
    script = tmp_path / "script.py"
    script.write_text(
        """
value = 0

def main():
    print(f"Value: {value}")
    return value

if __name__ == "__main__":
    main()
"""
    )

    config = Config(globals_dict={"value": 100})
    workflow = Sequential([Script(script, config=config)], use_subprocess=True)
    results = workflow.run()

    assert len(results) == 1
    assert hasattr(results[0], "returncode")
    assert results[0].returncode == 0


def test_sequential_subprocess_no_config(tmp_path):
    """Test sequential subprocess mode without config."""
    script = tmp_path / "script.py"
    script.write_text(
        """
def main():
    return 1

if __name__ == "__main__":
    main()
"""
    )

    workflow = Sequential([Script(script)], use_subprocess=True)
    results = workflow.run()

    assert len(results) == 1
    assert results[0].returncode == 0


def test_sequential_iterative_type_error(simple_script):
    """Test _run_iterative with non-generator config."""
    # This tests the internal _run_iterative error path
    script = Script(simple_script, config=Config(globals_dict={}))
    workflow = Sequential([script])

    # Manually call _run_iterative with wrong config type
    with pytest.raises(TypeError, match="Expected ConfigGenerator"):
        workflow._run_iterative(script)


def test_sequential_create_temp_config(tmp_path):
    """Test temp config file creation."""
    script = tmp_path / "script.py"
    script.write_text(
        """
def main():
    return 1

if __name__ == "__main__":
    main()
"""
    )

    config = Config(
        globals_dict={"lr": 0.01, "batch_size": 32},
        args=[1, 2],
        kwargs={"device": "cuda"},
        metadata={"exp": "test"},
    )

    workflow = Sequential([Script(script)], use_subprocess=True)
    temp_path = workflow._create_temp_config(config)

    # Verify temp file exists and contains config
    assert temp_path.exists()
    assert temp_path.suffix == ".py"
    content = temp_path.read_text()
    assert "config_gen" in content
    assert "0.01" in content
    assert "batch_size" in content


def test_sequential_subprocess_multiple_scripts(tmp_path):
    """Test subprocess mode with multiple scripts."""
    script1 = tmp_path / "s1.py"
    script1.write_text(
        """
def main():
    return 1

if __name__ == "__main__":
    main()
"""
    )

    script2 = tmp_path / "s2.py"
    script2.write_text(
        """
def main():
    return 2

if __name__ == "__main__":
    main()
"""
    )

    scripts = [Script(script1), Script(script2)]
    workflow = Sequential(scripts, use_subprocess=True)
    results = workflow.run()

    assert len(results) == 2
    assert all(r.returncode == 0 for r in results)


def test_sequential_mixed_subprocess_and_generator(tmp_path):
    """Test subprocess mode with generator config."""
    script = tmp_path / "script.py"
    script.write_text(
        """
value = 0

def main():
    return value

if __name__ == "__main__":
    main()
"""
    )

    def config_gen():
        for i in range(2):
            yield Config(globals_dict={"value": i})

    generator = ConfigGenerator(config_gen())
    workflow = Sequential([Script(script, config=generator)], use_subprocess=True)
    results = workflow.run()

    assert len(results) == 2
    assert all(r.returncode == 0 for r in results)
