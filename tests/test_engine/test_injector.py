"""Tests for kohakuengine.engine.injector."""

import math
import types

import pytest

from kohakuengine.engine.injector import PROTECTED_NAMES, GlobalInjector


def test_inject_sets_attributes():
    mod = types.ModuleType("m")
    GlobalInjector.inject(mod, {"a": 1, "b": "x"})
    assert mod.a == 1
    assert mod.b == "x"


@pytest.mark.parametrize("name", sorted(PROTECTED_NAMES))
def test_inject_refuses_protected_names(name):
    mod = types.ModuleType("m")
    with pytest.raises(ValueError, match="protected"):
        GlobalInjector.inject(mod, {name: 0})


def test_get_user_globals_filters():
    mod = types.ModuleType("m")
    mod.x = 1
    mod.y = "s"
    mod._private = 2
    mod.math = math
    mod.cls = type
    mod.fn = lambda: None
    g = GlobalInjector.get_user_globals(mod)
    assert g == {"x": 1, "y": "s"}
