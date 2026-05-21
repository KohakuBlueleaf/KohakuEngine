"""Tests for kohakuengine.engine.coerce."""

import pytest

from kohakuengine.engine.coerce import _parse_bool, coerce_globals


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("true", True),
        ("TRUE", True),
        ("yes", True),
        ("1", True),
        ("on", True),
        ("false", False),
        ("no", False),
        ("0", False),
        ("off", False),
        (1, True),
        (0, False),
        (True, True),
        (False, False),
    ],
)
def test_parse_bool(raw, expected):
    assert _parse_bool(raw) is expected


def test_parse_bool_invalid():
    with pytest.raises(ValueError):
        _parse_bool("maybe")


def test_coerce_int_from_string():
    out = coerce_globals({"epochs": "5"}, {"epochs": 10})
    assert out == {"epochs": 5}
    assert isinstance(out["epochs"], int)


def test_coerce_float_from_string():
    out = coerce_globals({"lr": "0.05"}, {"lr": 0.001})
    assert out["lr"] == 0.05


def test_coerce_bool_from_string():
    out = coerce_globals({"use_amp": "true"}, {"use_amp": False})
    assert out["use_amp"] is True


def test_coerce_str_passthrough():
    out = coerce_globals({"name": "abc"}, {"name": "default"})
    assert out["name"] == "abc"


def test_coerce_value_already_correct_type():
    out = coerce_globals({"n": 5}, {"n": 0})
    assert out["n"] == 5


def test_coerce_unknown_key_passes_through():
    out = coerce_globals({"foo": "bar"}, {"other": 1})
    assert out == {"foo": "bar"}


def test_coerce_unknown_key_strict_raises():
    with pytest.raises(KeyError, match="not declared"):
        coerce_globals({"foo": "x"}, {"bar": 1}, strict=True)


def test_coerce_failure_warns_passthrough():
    with pytest.warns(UserWarning, match="cannot coerce"):
        out = coerce_globals({"n": "abc"}, {"n": 0})
    assert out["n"] == "abc"


def test_coerce_failure_strict_raises():
    with pytest.raises(TypeError, match="cannot coerce"):
        coerce_globals({"n": "abc"}, {"n": 0}, strict=True)


def test_coerce_list_passthrough():
    out = coerce_globals({"layers": [1, 2, 3]}, {"layers": []})
    assert out["layers"] == [1, 2, 3]


def test_coerce_bool_actual_bool_kept():
    out = coerce_globals({"f": True}, {"f": False})
    assert out["f"] is True
