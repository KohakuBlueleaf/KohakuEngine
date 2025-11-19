"""Tests for engine.injector module."""

import types

import pytest

from kohakuengine.engine.injector import GlobalInjector


def test_inject_globals():
    """Test basic global variable injection."""
    module = types.ModuleType("test_module")

    GlobalInjector.inject(module, {"learning_rate": 0.001, "batch_size": 32})

    assert hasattr(module, "learning_rate")
    assert hasattr(module, "batch_size")
    assert module.learning_rate == 0.001
    assert module.batch_size == 32


def test_inject_protected_names():
    """Test that protected names cannot be overridden."""
    module = types.ModuleType("test_module")

    with pytest.raises(ValueError, match="Cannot override protected module attribute"):
        GlobalInjector.inject(module, {"__name__": "fake"})


def test_get_user_globals():
    """Test extracting user-defined globals."""
    module = types.ModuleType("test_module")

    # Add some user globals
    module.learning_rate = 0.001
    module.batch_size = 32

    # Add some things that should be filtered out
    module._private = "should be ignored"

    def my_func():
        pass

    module.my_func = my_func

    user_globals = GlobalInjector.get_user_globals(module)

    assert "learning_rate" in user_globals
    assert "batch_size" in user_globals
    assert "_private" not in user_globals  # Private
    assert "my_func" not in user_globals  # Function


def test_inject_various_types():
    """Test injecting various Python types."""
    module = types.ModuleType("test_module")

    class MyClass:
        pass

    obj = MyClass()

    GlobalInjector.inject(
        module,
        {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "list_val": [1, 2, 3],
            "dict_val": {"key": "value"},
            "object": obj,
            "MyClass": MyClass,
        },
    )

    assert module.string == "hello"
    assert module.number == 42
    assert module.float == 3.14
    assert module.list_val == [1, 2, 3]
    assert module.dict_val == {"key": "value"}
    assert module.object is obj
    assert module.MyClass is MyClass
