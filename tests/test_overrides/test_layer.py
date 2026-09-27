"""Tests for layer_overrides (engine/overrides.py)."""

import pytest

from kohakuengine import Config, ConfigGenerator, RawArg
from kohakuengine.engine.overrides import check_declared, layer_overrides


def test_nothing_to_do_returns_input():
    assert layer_overrides(None) is None
    cfg = Config(globals_dict={"a": 1})
    out = layer_overrides(cfg)
    assert out == cfg and out is not cfg


def test_set_wraps_raw_and_keeps_base():
    base = Config(globals_dict={"a": 1}, args=[1], kwargs={"k": 2}, metadata={"m": 3})
    out = layer_overrides(base, set_values={"b": "2"}, strict=True)
    assert out == Config(
        globals_dict={"a": 1, "b": RawArg("2", True)},
        args=[1],
        kwargs={"k": 2},
        metadata={"m": 3},
    )
    assert base.globals_dict == {"a": 1}


def test_existing_raw_arg_strict_is_ored():
    out = layer_overrides(None, set_values={"a": RawArg("1")}, strict=True)
    assert out.globals_dict["a"] == RawArg("1", True)
    out = layer_overrides(None, set_values={"a": RawArg("1", True)})
    assert out.globals_dict["a"] == RawArg("1", True)


def test_sweep_product_and_metadata():
    out = layer_overrides(
        Config(metadata={"run": "x"}),
        set_values={"e": "1"},
        sweep_values={"a": ["1", "2"], "b": [RawArg("x")]},
    )
    assert isinstance(out, ConfigGenerator)
    configs = list(out)
    assert [c.globals_dict for c in configs] == [
        {"e": RawArg("1"), "a": RawArg("1"), "b": RawArg("x")},
        {"e": RawArg("1"), "a": RawArg("2"), "b": RawArg("x")},
    ]
    assert [c.metadata for c in configs] == [
        {"run": "x", "a": "1", "b": "x"},
        {"run": "x", "a": "2", "b": "x"},
    ]


def test_generator_base_is_lazy_and_layered():
    pulled = []

    def gen():
        for i in range(2):
            pulled.append(i)
            yield Config(globals_dict={"i": i})

    out = layer_overrides(
        ConfigGenerator(gen()), set_values={"s": "1"}, sweep_values={"a": ["x", "y"]}
    )
    assert pulled == []
    configs = list(out)
    assert pulled == [0, 1]
    assert [(c.globals_dict["i"], c.globals_dict["a"].value) for c in configs] == [
        (0, "x"),
        (0, "y"),
        (1, "x"),
        (1, "y"),
    ]


def test_generator_base_without_sweep_stays_generator():
    gen = ConfigGenerator(iter([Config(globals_dict={"i": 0})]))
    out = layer_overrides(gen, set_values={"s": "1"})
    assert isinstance(out, ConfigGenerator)
    assert [c.globals_dict for c in out] == [{"i": 0, "s": RawArg("1")}]


def test_clash_between_set_and_sweep():
    with pytest.raises(ValueError, match=r"both --set and --sweep: \['a'\]"):
        layer_overrides(None, set_values={"a": "1"}, sweep_values={"a": ["2"]})


def test_declared_check_on_overrides_and_bases():
    with pytest.raises(KeyError, match="'zz'"):
        layer_overrides(None, set_values={"zz": "1"}, declared={"a"})
    with pytest.raises(KeyError, match="'zz'"):
        layer_overrides(Config(globals_dict={"zz": 1}), declared={"a"})
    gen = ConfigGenerator(iter([Config(globals_dict={"zz": 1})]))
    out = layer_overrides(gen, declared={"a"})
    with pytest.raises(KeyError, match="'zz'"):
        list(out)


def test_check_declared_messages():
    check_declared(["a"], {"a"})
    with pytest.raises(KeyError) as exc:
        check_declared(["lerning_rate", "qqq"], {"learning_rate"})
    msg = str(exc.value)
    assert "'lerning_rate' (did you mean 'learning_rate'?)" in msg
    assert "'qqq'" in msg and "qqq' (" not in msg
