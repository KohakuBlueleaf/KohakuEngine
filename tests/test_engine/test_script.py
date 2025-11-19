"""Tests for engine.script module."""

import pytest

from kohakuengine.config import Config
from kohakuengine.engine import Script


def test_script_creation(simple_script):
    """Test basic script creation."""
    script = Script(simple_script)

    assert script.path == simple_script
    assert script.path.exists()
    assert script.name == "simple_script"
    assert script.config is None
    assert script.run_as_main is True


def test_script_with_config(simple_script):
    """Test script with config."""
    config = Config(globals_dict={"lr": 0.001})
    script = Script(simple_script, config=config)

    assert script.config == config


def test_script_file_not_found():
    """Test script with non-existent file."""
    with pytest.raises(FileNotFoundError):
        Script("nonexistent.py")


def test_script_invalid_extension(tmp_path):
    """Test script with non-.py file."""
    not_python = tmp_path / "file.txt"
    not_python.write_text("hello")

    with pytest.raises(ValueError, match="Script must be .py file"):
        Script(not_python)


def test_script_entrypoint_syntax(simple_script):
    """Test script:entrypoint syntax."""
    script = Script(f"{simple_script}:custom_main")

    assert script.path == simple_script
    assert script.entrypoint == "custom_main"


def test_script_run_method(simple_script):
    """Test Script.run() convenience method."""
    script = Script(simple_script)
    result = script.run()

    assert result == "success"
