"""Tests for Parallel workflow."""

import pytest

from kohakuengine import Config, ConfigGenerator, Parallel, Script


def test_parallel_subprocess(simple_script):
    scripts = [
        Script(str(simple_script), config=Config(globals_dict={"lr": i / 10}))
        for i in range(3)
    ]
    workflow = Parallel(scripts, max_workers=2, use_subprocess=True)
    results = workflow.run()
    assert len(results) == 3
    assert all(r.returncode == 0 for r in results)


def test_parallel_with_generator(simple_script):
    gen = ConfigGenerator(iter([Config(globals_dict={"lr": i / 10}) for i in range(2)]))
    scripts = [Script(str(simple_script), config=gen)]
    workflow = Parallel(scripts, max_workers=2, use_subprocess=True)
    results = workflow.run()
    assert len(results) == 2


def test_parallel_no_scripts():
    with pytest.raises(ValueError):
        Parallel([])
