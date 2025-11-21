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
    assert script.entrypoint is None


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


def test_script_run_subprocess_mode(tmp_path):
    """Test Script.run() with subprocess mode."""
    script_file = tmp_path / "script.py"
    script_file.write_text(
        """
def main():
    print("Subprocess")
    return 42

if __name__ == "__main__":
    main()
"""
    )

    script = Script(script_file)
    result = script.run(use_subprocess=True)

    assert hasattr(result, "returncode")
    assert result.returncode == 0


def test_script_run_subprocess_with_config(tmp_path):
    """Test Script.run() subprocess mode with config."""
    script_file = tmp_path / "script.py"
    script_file.write_text(
        """
value = 0

def main():
    return value

if __name__ == "__main__":
    main()
"""
    )

    config = Config(globals_dict={"value": 123})
    script = Script(script_file, config=config)
    result = script.run(use_subprocess=True)

    assert result.returncode == 0


def test_script_run_subprocess_override_config(tmp_path):
    """Test Script.run() subprocess mode with config override."""
    script_file = tmp_path / "script.py"
    script_file.write_text(
        """
value = 0

def main():
    return value

if __name__ == "__main__":
    main()
"""
    )

    script = Script(script_file)
    override_config = Config(globals_dict={"value": 999})
    result = script.run(config=override_config, use_subprocess=True)

    assert result.returncode == 0


def test_script_create_temp_config(tmp_path):
    """Test _create_temp_config method."""
    script_file = tmp_path / "script.py"
    script_file.write_text(
        """
def main():
    return 1

if __name__ == "__main__":
    main()
"""
    )

    config = Config(
        globals_dict={"lr": 0.01, "bs": 32},
        args=[1, 2],
        kwargs={"device": "cuda"},
        metadata={"exp": "test"},
    )

    script = Script(script_file)
    temp_path = script._create_temp_config(config)

    # Verify temp config file
    assert temp_path.exists()
    assert temp_path.suffix == ".py"
    content = temp_path.read_text()
    assert "config_gen" in content
    assert "0.01" in content
    assert "bs" in content
    assert "device" in content


def test_script_repr(simple_script):
    """Test Script.__repr__ method."""
    script = Script(simple_script)
    repr_str = repr(script)

    assert "Script" in repr_str
    assert "path=" in repr_str
    assert "config=" in repr_str


def test_script_repr_with_config(simple_script):
    """Test Script.__repr__ with config."""
    config = Config(globals_dict={"x": 1})
    script = Script(simple_script, config=config)
    repr_str = repr(script)

    assert "Script" in repr_str
    assert "Config" in repr_str
