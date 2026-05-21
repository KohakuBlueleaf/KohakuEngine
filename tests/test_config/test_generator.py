"""Tests for kohakuengine.config.generator."""

import pytest

from kohakuengine.config import Config, ConfigGenerator


def _gen():
    yield Config(globals_dict={"i": 0})
    yield Config(globals_dict={"i": 1})


def test_iter_returns_self():
    g = ConfigGenerator(_gen())
    assert iter(g) is g


def test_next_yields_configs():
    g = ConfigGenerator(_gen())
    c1 = next(g)
    c2 = next(g)
    assert (c1.globals_dict["i"], c2.globals_dict["i"]) == (0, 1)
    with pytest.raises(StopIteration):
        next(g)
    assert g.exhausted is True


def test_non_config_yield_raises():
    def bad():
        yield 42

    g = ConfigGenerator(bad())
    with pytest.raises(TypeError, match="Config"):
        next(g)


def test_exhausted_after_stop_iteration():
    g = ConfigGenerator(iter([]))
    with pytest.raises(StopIteration):
        next(g)
    with pytest.raises(StopIteration):
        next(g)  # second call also raises


def test_for_loop_iteration():
    g = ConfigGenerator(_gen())
    items = list(g)
    assert len(items) == 2
