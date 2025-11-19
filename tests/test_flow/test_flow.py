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
