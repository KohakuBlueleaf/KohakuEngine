"""Tests for flow.flow module (unified Flow class)."""

import pytest

from kohakuengine.config import Config
from kohakuengine.engine import Script
from kohakuengine.flow import Flow


def test_flow_sequential_mode(simple_script):
    """Test Flow with sequential mode."""
    scripts = [Script(simple_script) for _ in range(3)]

    flow = Flow(scripts, mode="sequential")
    results = flow.run()

    assert len(results) == 3
    assert all(r == "success" for r in results)


def test_flow_invalid_mode(simple_script):
    """Test Flow with invalid mode."""
    scripts = [Script(simple_script)]

    with pytest.raises(ValueError, match="Invalid mode"):
        Flow(scripts, mode="invalid")


def test_flow_with_config(script_with_globals):
    """Test Flow with configuration."""
    config = Config(globals_dict={"learning_rate": 0.01, "batch_size": 64})

    script = Script(script_with_globals, config=config)
    flow = Flow([script], mode="sequential")

    results = flow.run()
    assert results[0] == 0.01 * 64


def test_flow_validation(simple_script):
    """Test Flow validation."""
    scripts = [Script(simple_script)]

    flow = Flow(scripts, mode="sequential")
    assert flow.validate() is True


def test_flow_repr(simple_script):
    """Test Flow string representation."""
    scripts = [Script(simple_script) for _ in range(3)]

    flow = Flow(scripts, mode="sequential")
    repr_str = repr(flow)

    assert "Flow" in repr_str
    assert "scripts=3" in repr_str
    assert "mode=sequential" in repr_str


def test_flow_parallel_mode(simple_script):
    """Test Flow with parallel mode."""
    scripts = [Script(simple_script) for _ in range(2)]

    flow = Flow(scripts, mode="parallel", use_subprocess=False)
    results = flow.run()

    assert len(results) == 2
    assert all(r == "success" for r in results)


def test_flow_parallel_mode_with_workers(simple_script):
    """Test Flow with parallel mode and max_workers."""
    scripts = [Script(simple_script) for _ in range(2)]

    flow = Flow(scripts, mode="parallel", max_workers=2, use_subprocess=False)
    results = flow.run()

    assert len(results) == 2


def test_flow_custom_executor_parallel(simple_script):
    """Test Flow with custom Parallel executor class."""
    from kohakuengine.flow.parallel import Parallel

    scripts = [Script(simple_script) for _ in range(2)]

    flow = Flow(scripts, executor_class=Parallel, max_workers=2, use_subprocess=False)
    results = flow.run()

    assert len(results) == 2


def test_flow_custom_executor_sequential(simple_script):
    """Test Flow with custom Sequential executor class."""
    from kohakuengine.flow.sequential import Sequential

    scripts = [Script(simple_script) for _ in range(2)]

    flow = Flow(scripts, executor_class=Sequential)
    results = flow.run()

    assert len(results) == 2


def test_flow_custom_executor_other(simple_script):
    """Test Flow with custom executor class that's neither Parallel nor Sequential."""
    from kohakuengine.flow.base import ScriptWorkflow

    # Create a simple custom executor
    class CustomExecutor(ScriptWorkflow):
        def run(self):
            return ["custom"] * len(self.scripts)

        def validate(self):
            return True

    scripts = [Script(simple_script)]

    flow = Flow(scripts, executor_class=CustomExecutor)
    results = flow.run()

    assert results == ["custom"]


def test_flow_parallel_subprocess_default(simple_script):
    """Test that parallel mode defaults to use_subprocess=True."""
    scripts = [Script(simple_script)]

    flow = Flow(scripts, mode="parallel")
    # Should default to subprocess mode
    assert flow.use_subprocess is True


def test_flow_sequential_subprocess_false_default(simple_script):
    """Test that sequential mode defaults to use_subprocess=False."""
    scripts = [Script(simple_script)]

    flow = Flow(scripts, mode="sequential")
    # Should default to no subprocess
    assert flow.use_subprocess is False
