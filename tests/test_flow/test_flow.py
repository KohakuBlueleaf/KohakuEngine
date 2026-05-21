"""Tests for the unified Flow facade."""

import pytest

from kohakuengine import Config, Flow, Script
from kohakuengine.flow.parallel import Parallel
from kohakuengine.flow.sequential import Sequential


def test_flow_sequential(make_script):
    s = make_script("a.py", "def main(): return 'a'\nif __name__=='__main__':main()\n")
    flow = Flow([Script(str(s))], mode="sequential")
    assert flow.run() == ["a"]


def test_flow_parallel(simple_script):
    scripts = [
        Script(str(simple_script), config=Config(globals_dict={"lr": i / 10}))
        for i in range(2)
    ]
    flow = Flow(scripts, mode="parallel", max_workers=2)
    results = flow.run()
    assert len(results) == 2


def test_flow_invalid_mode():
    with pytest.raises(ValueError, match="Invalid mode"):
        Flow([], mode="bogus")


def test_flow_validate_passes(simple_script):
    flow = Flow([Script(str(simple_script))], mode="sequential")
    assert flow.validate() is True


def test_flow_repr(simple_script):
    flow = Flow([Script(str(simple_script))], mode="sequential")
    assert "Flow(scripts=1" in repr(flow)


def test_flow_custom_executor_class(simple_script):
    flow = Flow(
        [Script(str(simple_script))],
        executor_class=Sequential,
    )
    assert isinstance(flow._executor, Sequential)


def test_flow_custom_executor_parallel(simple_script):
    flow = Flow(
        [Script(str(simple_script))],
        mode="parallel",
        executor_class=Parallel,
        max_workers=1,
    )
    assert isinstance(flow._executor, Parallel)
