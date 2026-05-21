"""Tests for the top-level run() convenience."""

import pytest

from kohakuengine import run


def test_run_with_inline_globals(simple_script):
    assert run(str(simple_script), globals_dict={"lr": 0.7}) == 0.7


def test_run_with_config_file(simple_script, make_config):
    cfg = make_config(
        "c.py",
        """
        from kohakuengine.config import Config
        def config_gen():
            return Config(globals_dict={"lr": 0.25})
        """,
    )
    assert run(str(simple_script), config_path=str(cfg)) == 0.25


def test_run_set_overrides(simple_script):
    out = run(str(simple_script), set_overrides={"lr": "0.4"})
    # Coercion: string -> float because default is 0.1
    assert out == 0.4


def test_run_strict_passes(simple_script):
    out = run(str(simple_script), globals_dict={"lr": 0.9}, strict=True)
    assert out == 0.9


def test_run_strict_rejects_unknown(simple_script):
    with pytest.raises(KeyError):
        run(str(simple_script), set_overrides={"unknown": 1}, strict=True)


def test_run_no_config(simple_script):
    # When no config + no overrides, run() executes with defaults
    assert run(str(simple_script)) == 0.1


def test_run_args_kwargs(args_script):
    assert run(str(args_script), args=[10], kwargs={"y": 2}) == 12


def test_run_merges_config_file_with_globals(simple_script, make_config):
    cfg = make_config(
        "c.py",
        """
        from kohakuengine.config import Config
        def config_gen():
            return Config(globals_dict={"lr": 0.1})
        """,
    )
    # Inline globals merge into the loaded config
    out = run(str(simple_script), config_path=str(cfg), globals_dict={"lr": 0.55})
    assert out == 0.55
