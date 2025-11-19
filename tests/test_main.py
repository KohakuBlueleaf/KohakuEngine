"""Tests for main API module."""

import pytest

from kohakuengine import run


def test_run_with_inline_config(script_with_globals):
    """Test run() with inline configuration."""
    result = run(
        str(script_with_globals), globals_dict={"learning_rate": 0.01, "batch_size": 64}
    )

    assert result == 0.01 * 64


def test_run_with_config_file(script_with_globals, simple_config_file):
    """Test run() with config file."""
    # Note: simple_config_file has different globals, but we'll use the values
    result = run(str(script_with_globals), config_path=str(simple_config_file))

    # simple_config_file has lr=0.01, bs=64
    assert result == 0.01 * 64


def test_run_no_config(simple_script):
    """Test run() without any configuration."""
    result = run(str(simple_script))

    assert result == "success"


def test_run_with_args(script_with_args):
    """Test run() with args and kwargs."""
    result = run(str(script_with_args), args=[10], kwargs={"y": 20})

    assert result == 30


def test_run_script_not_found():
    """Test run() with non-existent script."""
    with pytest.raises(FileNotFoundError):
        run("nonexistent.py")
