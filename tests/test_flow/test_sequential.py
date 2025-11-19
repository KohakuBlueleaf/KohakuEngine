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
