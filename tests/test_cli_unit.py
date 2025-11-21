"""Unit tests for CLI module functions."""

import argparse
import sys
from io import StringIO
from unittest.mock import patch

import pytest

from kohakuengine import Config
from kohakuengine.cli import (
    cmd_config_show,
    cmd_config_validate,
    cmd_run,
    cmd_workflow_parallel,
    cmd_workflow_sequential,
    create_parser,
    main,
)


class TestParser:
    """Test argument parser creation."""

    def test_create_parser(self):
        """Test that parser is created correctly."""
        parser = create_parser()
        assert parser.prog == "kogine"

    def test_parser_version(self, capsys):
        """Test --version flag."""
        parser = create_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "kogine" in captured.out.lower()

    def test_parser_help(self, capsys):
        """Test --help flag."""
        parser = create_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "KohakuEngine" in captured.out


class TestCmdRun:
    """Test cmd_run function."""

    def test_cmd_run_simple(self, tmp_path):
        """Test cmd_run with simple script."""
        script = tmp_path / "script.py"
        script.write_text(
            """
def main():
    print("Running")
    return 42

if __name__ == "__main__":
    main()
"""
        )

        args = argparse.Namespace(script=str(script), config=None, entrypoint=None)

        with pytest.raises(SystemExit) as exc_info:
            cmd_run(args)
        assert exc_info.value.code == 0

    def test_cmd_run_with_config(self, tmp_path):
        """Test cmd_run with config file."""
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
    return Config(globals_dict={'value': 100})
"""
        )

        args = argparse.Namespace(
            script=str(script), config=str(config), entrypoint=None
        )

        with pytest.raises(SystemExit) as exc_info:
            cmd_run(args)
        assert exc_info.value.code == 0

    def test_cmd_run_with_entrypoint(self, tmp_path):
        """Test cmd_run with custom entrypoint."""
        script = tmp_path / "script.py"
        script.write_text(
            """
def custom():
    return "custom"

def main():
    return "main"

if __name__ == "__main__":
    main()
"""
        )

        args = argparse.Namespace(script=str(script), config=None, entrypoint="custom")

        with pytest.raises(SystemExit) as exc_info:
            cmd_run(args)
        assert exc_info.value.code == 0


class TestCmdWorkflowSequential:
    """Test cmd_workflow_sequential function."""

    def test_sequential_workflow(self, tmp_path):
        """Test sequential workflow command."""
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

        args = argparse.Namespace(scripts=[str(script1), str(script2)], config=None)

        with pytest.raises(SystemExit) as exc_info:
            cmd_workflow_sequential(args)
        assert exc_info.value.code == 0


class TestCmdWorkflowParallel:
    """Test cmd_workflow_parallel function."""

    def test_parallel_workflow(self, tmp_path):
        """Test parallel workflow command."""
        script = tmp_path / "script.py"
        script.write_text(
            """
def main():
    return 1

if __name__ == "__main__":
    main()
"""
        )

        args = argparse.Namespace(
            scripts=[str(script)], config=None, workers=2, mode="pool"
        )

        with pytest.raises(SystemExit) as exc_info:
            cmd_workflow_parallel(args)
        assert exc_info.value.code == 0

    def test_parallel_subprocess_mode(self, tmp_path):
        """Test parallel workflow with subprocess mode."""
        script = tmp_path / "script.py"
        script.write_text(
            """
def main():
    return 1

if __name__ == "__main__":
    main()
"""
        )

        args = argparse.Namespace(
            scripts=[str(script)], config=None, workers=None, mode="subprocess"
        )

        # subprocess mode requires actual subprocess execution
        # Just test that it doesn't crash
        with pytest.raises(SystemExit) as exc_info:
            cmd_workflow_parallel(args)
        assert exc_info.value.code == 0


class TestCmdConfigValidate:
    """Test cmd_config_validate function."""

    def test_validate_config(self, tmp_path):
        """Test config validation command."""
        config = tmp_path / "config.py"
        config.write_text(
            """
from kohakuengine import Config

def config_gen():
    return Config(globals_dict={'x': 1})
"""
        )

        args = argparse.Namespace(config=str(config))

        with pytest.raises(SystemExit) as exc_info:
            cmd_config_validate(args)
        assert exc_info.value.code == 0


class TestCmdConfigShow:
    """Test cmd_config_show function."""

    def test_show_static_config(self, tmp_path):
        """Test showing static config."""
        config = tmp_path / "config.py"
        config.write_text(
            """
from kohakuengine import Config

def config_gen():
    return Config(
        globals_dict={'lr': 0.01},
        args=[1, 2],
        kwargs={'device': 'cuda'},
        metadata={'exp': 'test'}
    )
"""
        )

        args = argparse.Namespace(config=str(config))

        with pytest.raises(SystemExit) as exc_info:
            cmd_config_show(args)
        assert exc_info.value.code == 0

    def test_show_generator_config(self, tmp_path):
        """Test showing generator config."""
        config = tmp_path / "config.py"
        config.write_text(
            """
from kohakuengine import Config

def config_gen():
    for i in range(2):
        yield Config(globals_dict={'i': i})
"""
        )

        args = argparse.Namespace(config=str(config))

        with pytest.raises(SystemExit) as exc_info:
            cmd_config_show(args)
        assert exc_info.value.code == 0


class TestMain:
    """Test main CLI entry point."""

    def test_main_no_args(self):
        """Test main with no arguments."""
        with patch("sys.argv", ["kogine"]):
            main()  # Should just print help

    def test_main_with_command(self, tmp_path):
        """Test main with valid command."""
        script = tmp_path / "script.py"
        script.write_text(
            """
def main():
    return 1

if __name__ == "__main__":
    main()
"""
        )

        with patch("sys.argv", ["kogine", "run", str(script)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_main_with_error(self):
        """Test main with error."""
        with patch("sys.argv", ["kogine", "run", "nonexistent.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_invalid_command(self):
        """Test main with invalid command."""
        with patch("sys.argv", ["kogine", "invalid"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2  # argparse error code
