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


# Tests for module import functionality


def test_script_from_module():
    """Test Script creation from importable module."""
    # Use a known stdlib module
    script = Script("json")

    assert script.is_module is True
    assert script.module_name == "json"
    assert script.name == "json"


def test_script_from_module_with_entrypoint():
    """Test Script creation from module with entrypoint syntax."""
    script = Script("json:dumps")

    assert script.is_module is True
    assert script.module_name == "json"
    assert script.entrypoint == "dumps"
    assert script.name == "json"


def test_script_from_nested_module():
    """Test Script creation from nested module."""
    script = Script("kohakuengine.config")

    assert script.is_module is True
    assert script.module_name == "kohakuengine.config"
    assert script.name == "config"


def test_script_module_not_found():
    """Test Script with non-existent module."""
    with pytest.raises(ModuleNotFoundError, match="Module not found"):
        Script("nonexistent_module_xyz")


def test_script_module_repr():
    """Test Script.__repr__ for module-based script."""
    script = Script("json")
    repr_str = repr(script)

    assert "Script" in repr_str
    assert "module=json" in repr_str


def test_script_file_vs_module_detection(tmp_path):
    """Test that file paths are correctly distinguished from modules."""
    # Create a file with dots in parent directory name
    script_file = tmp_path / "test.script.py"
    script_file.write_text("def main(): return 1")

    # This should be treated as a file, not a module
    script = Script(script_file)
    assert script.is_module is False


def test_script_module_with_explicit_entrypoint():
    """Test module with explicit entrypoint parameter."""
    script = Script("json", entrypoint="loads")

    assert script.is_module is True
    assert script.module_name == "json"
    assert script.entrypoint == "loads"


def test_script_module_run_with_entrypoint():
    """Test running a module-based script with entrypoint."""
    # Create a test package in a temp location
    import sys
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test module
        pkg_dir = os.path.join(tmpdir, "test_pkg")
        os.makedirs(pkg_dir)

        # Create __init__.py
        with open(os.path.join(pkg_dir, "__init__.py"), "w") as f:
            f.write("")

        # Create a module with main function
        with open(os.path.join(pkg_dir, "runner.py"), "w") as f:
            f.write(
                """
value = 10

def main():
    return value * 2
"""
            )

        # Add to sys.path temporarily
        sys.path.insert(0, tmpdir)
        try:
            script = Script("test_pkg.runner")
            result = script.run()
            assert result == 20
        finally:
            sys.path.remove(tmpdir)


def test_script_module_run_with_config():
    """Test running a module-based script with config injection."""
    import sys
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_dir = os.path.join(tmpdir, "test_pkg2")
        os.makedirs(pkg_dir)

        with open(os.path.join(pkg_dir, "__init__.py"), "w") as f:
            f.write("")

        with open(os.path.join(pkg_dir, "configurable.py"), "w") as f:
            f.write(
                """
multiplier = 1

def main():
    return 5 * multiplier
"""
            )

        sys.path.insert(0, tmpdir)
        try:
            config = Config(globals_dict={"multiplier": 10})
            script = Script("test_pkg2.configurable", config=config)
            result = script.run()
            assert result == 50
        finally:
            sys.path.remove(tmpdir)


def test_script_module_explicit_entrypoint_run():
    """Test running module with explicit entrypoint function."""
    import sys
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_dir = os.path.join(tmpdir, "test_pkg3")
        os.makedirs(pkg_dir)

        with open(os.path.join(pkg_dir, "__init__.py"), "w") as f:
            f.write("")

        with open(os.path.join(pkg_dir, "multi_entry.py"), "w") as f:
            f.write(
                """
def main():
    return "main"

def alternate():
    return "alternate"
"""
            )

        sys.path.insert(0, tmpdir)
        try:
            # Test with explicit entrypoint via syntax
            script = Script("test_pkg3.multi_entry:alternate")
            result = script.run()
            assert result == "alternate"

            # Test with explicit entrypoint via parameter
            script2 = Script("test_pkg3.multi_entry", entrypoint="alternate")
            result2 = script2.run()
            assert result2 == "alternate"
        finally:
            sys.path.remove(tmpdir)


def test_script_module_missing_entrypoint():
    """Test that missing entrypoint raises error."""
    import sys
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_dir = os.path.join(tmpdir, "test_pkg4")
        os.makedirs(pkg_dir)

        with open(os.path.join(pkg_dir, "__init__.py"), "w") as f:
            f.write("")

        with open(os.path.join(pkg_dir, "no_entry.py"), "w") as f:
            f.write(
                """
def helper():
    return "helper"
"""
            )

        sys.path.insert(0, tmpdir)
        try:
            script = Script("test_pkg4.no_entry:nonexistent")
            with pytest.raises(ValueError, match="not found"):
                script.run()
        finally:
            sys.path.remove(tmpdir)


def test_script_is_module_false_for_files(simple_script):
    """Test that file-based scripts have is_module=False."""
    script = Script(simple_script)
    assert script.is_module is False
    assert script.module_name is None
