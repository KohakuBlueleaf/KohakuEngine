"""Tests for CLI functionality."""

import subprocess
import sys
from pathlib import Path

import pytest


def run_cli(*args, check=True):
    """Helper to run CLI commands."""
    cmd = [sys.executable, "-m", "kohakuengine.cli"] + list(args)
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", check=False
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )
    return result


class TestCLIBasic:
    """Test basic CLI functionality."""

    def test_cli_no_args(self):
        """Test CLI with no arguments shows help."""
        result = run_cli(check=False)
        assert result.returncode == 0
        assert "KohakuEngine" in result.stdout or "usage" in result.stdout.lower()

    def test_cli_help(self):
        """Test --help flag."""
        result = run_cli("--help")
        assert result.returncode == 0
        assert "KohakuEngine" in result.stdout
        assert "run" in result.stdout
        assert "workflow" in result.stdout
        assert "config" in result.stdout

    def test_cli_version(self):
        """Test --version flag."""
        result = run_cli("--version")
        assert result.returncode == 0
        assert "kogine" in result.stdout.lower()


class TestCLIRun:
    """Test 'run' command."""

    def test_run_simple_script(self, tmp_path):
        """Test running a simple script."""
        script = tmp_path / "script.py"
        script.write_text(
            """
def main():
    print("Hello from script")
    return 42

if __name__ == "__main__":
    main()
"""
        )
        result = run_cli("run", str(script))
        assert result.returncode == 0
        assert "✓" in result.stdout or "successfully" in result.stdout.lower()
        assert "Hello from script" in result.stdout

    def test_run_with_config(self, tmp_path):
        """Test running script with config."""
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

        config = tmp_path / "config.py"
        config.write_text(
            """
from kohakuengine import Config

def config_gen():
    return Config(globals_dict={'value': 123})
"""
        )

        result = run_cli("run", str(script), "--config", str(config))
        assert result.returncode == 0
        assert "Value: 123" in result.stdout

    def test_run_with_entrypoint(self, tmp_path):
        """Test running script with custom entrypoint."""
        script = tmp_path / "script.py"
        script.write_text(
            """
def custom_main():
    print("Custom entrypoint")
    return "custom"

def main():
    print("Default main")
    return "default"

if __name__ == "__main__":
    main()
"""
        )

        result = run_cli("run", str(script), "--entrypoint", "custom_main")
        assert result.returncode == 0
        assert "Custom entrypoint" in result.stdout

    def test_run_script_not_found(self):
        """Test error when script not found."""
        result = run_cli("run", "nonexistent.py", check=False)
        assert result.returncode == 1
        assert "Error" in result.stderr

    def test_run_invalid_config(self, tmp_path):
        """Test error with invalid config."""
        script = tmp_path / "script.py"
        script.write_text(
            """
def main():
    pass

if __name__ == "__main__":
    main()
"""
        )

        result = run_cli("run", str(script), "--config", "nonexistent.py", check=False)
        assert result.returncode == 1
        assert "Error" in result.stderr


class TestCLIWorkflowSequential:
    """Test 'workflow sequential' command."""

    def test_sequential_multiple_scripts(self, tmp_path):
        """Test sequential execution of multiple scripts."""
        script1 = tmp_path / "script1.py"
        script1.write_text(
            """
def main():
    print("Script 1")
    return 1

if __name__ == "__main__":
    main()
"""
        )

        script2 = tmp_path / "script2.py"
        script2.write_text(
            """
def main():
    print("Script 2")
    return 2

if __name__ == "__main__":
    main()
"""
        )

        result = run_cli("workflow", "sequential", str(script1), str(script2))
        assert result.returncode == 0
        assert "Script 1" in result.stdout
        assert "Script 2" in result.stdout
        assert "2 executions" in result.stdout

    def test_sequential_with_config(self, tmp_path):
        """Test sequential workflow with config."""
        script = tmp_path / "script.py"
        script.write_text(
            """
value = 0

def main():
    print(f"Value: {value}")

if __name__ == "__main__":
    main()
"""
        )

        config = tmp_path / "config.py"
        config.write_text(
            """
from kohakuengine import Config

def config_gen():
    return Config(globals_dict={'value': 999})
"""
        )

        result = run_cli("workflow", "sequential", str(script), "--config", str(config))
        assert result.returncode == 0
        assert "Value: 999" in result.stdout

    def test_sequential_no_scripts(self):
        """Test error when no scripts provided."""
        result = run_cli("workflow", "sequential", check=False)
        assert result.returncode != 0


class TestCLIWorkflowParallel:
    """Test 'workflow parallel' command."""

    def test_parallel_multiple_scripts(self, tmp_path):
        """Test parallel execution."""
        script1 = tmp_path / "script1.py"
        script1.write_text(
            """
def main():
    print("Parallel 1")
    return 1

if __name__ == "__main__":
    main()
"""
        )

        script2 = tmp_path / "script2.py"
        script2.write_text(
            """
def main():
    print("Parallel 2")
    return 2

if __name__ == "__main__":
    main()
"""
        )

        result = run_cli(
            "workflow", "parallel", str(script1), str(script2), "--mode", "pool"
        )
        assert result.returncode == 0
        assert "2 executions" in result.stdout

    def test_parallel_with_workers(self, tmp_path):
        """Test parallel with worker count."""
        script = tmp_path / "script.py"
        script.write_text(
            """
def main():
    return 1

if __name__ == "__main__":
    main()
"""
        )

        result = run_cli(
            "workflow", "parallel", str(script), "--workers", "2", "--mode", "pool"
        )
        assert result.returncode == 0

    def test_parallel_subprocess_mode(self, tmp_path):
        """Test parallel with subprocess mode."""
        script = tmp_path / "script.py"
        script.write_text(
            """
def main():
    print("Subprocess mode")
    return 1

if __name__ == "__main__":
    main()
"""
        )

        result = run_cli("workflow", "parallel", str(script), "--mode", "subprocess")
        assert result.returncode == 0

    def test_parallel_with_config(self, tmp_path):
        """Test parallel workflow with config."""
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

        config = tmp_path / "config.py"
        config.write_text(
            """
from kohakuengine import Config

def config_gen():
    return Config(globals_dict={'value': 777})
"""
        )

        result = run_cli(
            "workflow",
            "parallel",
            str(script),
            "--config",
            str(config),
            "--mode",
            "pool",
        )
        assert result.returncode == 0


class TestCLIConfig:
    """Test 'config' commands."""

    def test_config_validate_static(self, tmp_path):
        """Test validating static config."""
        config = tmp_path / "config.py"
        config.write_text(
            """
from kohakuengine import Config

def config_gen():
    return Config(globals_dict={'lr': 0.01})
"""
        )

        result = run_cli("config", "validate", str(config))
        assert result.returncode == 0
        assert "✓" in result.stdout or "valid" in result.stdout.lower()
        assert "Config" in result.stdout

    def test_config_validate_generator(self, tmp_path):
        """Test validating generator config."""
        config = tmp_path / "config.py"
        config.write_text(
            """
from kohakuengine import Config

def config_gen():
    for i in range(3):
        yield Config(globals_dict={'value': i})
"""
        )

        result = run_cli("config", "validate", str(config))
        assert result.returncode == 0
        assert "✓" in result.stdout or "valid" in result.stdout.lower()

    def test_config_validate_invalid(self):
        """Test error with invalid config."""
        result = run_cli("config", "validate", "nonexistent.py", check=False)
        assert result.returncode == 1
        assert "Error" in result.stderr

    def test_config_show_static(self, tmp_path):
        """Test showing static config."""
        config = tmp_path / "config.py"
        config.write_text(
            """
from kohakuengine import Config

def config_gen():
    return Config(
        globals_dict={'lr': 0.01, 'batch_size': 32},
        args=[1, 2],
        kwargs={'device': 'cuda'},
        metadata={'exp': 'test'}
    )
"""
        )

        result = run_cli("config", "show", str(config))
        assert result.returncode == 0
        assert "Static" in result.stdout
        assert "lr" in result.stdout
        assert "0.01" in result.stdout
        assert "batch_size" in result.stdout
        assert "32" in result.stdout

    def test_config_show_generator(self, tmp_path):
        """Test showing generator config."""
        config = tmp_path / "config.py"
        config.write_text(
            """
from kohakuengine import Config

def config_gen():
    for lr in [0.001, 0.01]:
        yield Config(globals_dict={'lr': lr})
"""
        )

        result = run_cli("config", "show", str(config))
        assert result.returncode == 0
        assert "Generator" in result.stdout
        assert "Config 1" in result.stdout
        assert "Config 2" in result.stdout
        assert "0.001" in result.stdout
        assert "0.01" in result.stdout


class TestCLIEdgeCases:
    """Test edge cases and error handling."""

    def test_run_script_with_exception(self, tmp_path):
        """Test script that raises exception."""
        script = tmp_path / "script.py"
        script.write_text(
            """
def main():
    raise ValueError("Test error")

if __name__ == "__main__":
    main()
"""
        )

        result = run_cli("run", str(script), check=False)
        assert result.returncode == 1
        assert "Error" in result.stderr

    def test_run_non_python_file(self, tmp_path):
        """Test error with non-.py file."""
        script = tmp_path / "script.txt"
        script.write_text("not python")

        result = run_cli("run", str(script), check=False)
        assert result.returncode == 1
        assert "Error" in result.stderr

    def test_workflow_sequential_script_error(self, tmp_path):
        """Test sequential workflow with script error."""
        script = tmp_path / "script.py"
        script.write_text(
            """
def main():
    raise RuntimeError("Oops")

if __name__ == "__main__":
    main()
"""
        )

        result = run_cli("workflow", "sequential", str(script), check=False)
        assert result.returncode == 1
        assert "Error" in result.stderr

    def test_invalid_command(self):
        """Test invalid command."""
        result = run_cli("invalid", check=False)
        assert result.returncode != 0
