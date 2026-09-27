"""Tests for annotation-driven coercion (kohakuengine.engine.coerce)."""

# ruff: noqa: UP006, UP007, UP045 -- the typing.* spellings are under test.

import collections.abc
import enum
import typing
from decimal import Decimal
from fractions import Fraction
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, Literal, NewType, Optional, Union

import pytest

from kohakuengine import FormatArg, RawArg, coerce_globals, coerce_value
from kohakuengine.engine.coerce import (
    COERCERS,
    infer_annotation,
    is_value_type,
    parse_literal,
    resolve_raw_args,
    split_top_level,
)
from kohakuengine.engine.coerce.text import guess_scalar, strip_brackets


class Color(enum.Enum):
    RED = "red"
    GREEN = "green"


class Level(enum.IntEnum):
    LOW = 1
    HIGH = 2


class Mixed(enum.Enum):
    lower = 1
    UPPER = 2


class Dtype:
    """Custom type with the ``format_arg`` hook."""

    def __init__(self, name: str) -> None:
        self.name = name

    @classmethod
    def format_arg(cls, arg: str) -> "Dtype":
        return cls(f"parsed:{arg}")


class Plain:
    def __init__(self, arg: str) -> None:
        self.arg = arg


UserId = NewType("UserId", int)


# ---------------------------------------------------------------------------
# text helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1,2,3", ["1", "2", "3"]),
        ("1, [2, 3], (4,5)", ["1", "[2, 3]", "(4,5)"]),
        ("'a,b',\"c,d\"", ["'a,b'", '"c,d"']),
        ("{'k': 1, 'j': 2},x", ["{'k': 1, 'j': 2}", "x"]),
        ("'it\\'s,x',y", ["'it\\'s,x'", "y"]),
        ("[1,2]]x,y", ["[1,2]]x", "y"]),
        ("", [""]),
    ],
)
def test_split_top_level(text, expected):
    assert split_top_level(text) == expected


def test_parse_literal_python_json_and_error():
    assert parse_literal("[1, 'a']") == [1, "a"]
    assert parse_literal('{"a": true, "b": null}') == {"a": True, "b": None}
    with pytest.raises(ValueError, match="not a Python or JSON literal"):
        parse_literal("abc")


def test_guess_scalar_and_strip_brackets():
    assert guess_scalar(" 3 ") == 3
    assert guess_scalar(" abc ") == "abc"
    assert strip_brackets(" [1,2] ") == "1,2"
    assert strip_brackets("(x)") == "x"
    assert strip_brackets("[x)") == "[x)"


# ---------------------------------------------------------------------------
# scalars
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,annotation,expected",
    [
        ("5", int, 5),
        (" 7 ", int, 7),
        ("0x10", int, 16),
        ("1_000", int, 1000),
        ("1e3", int, 1000),
        (4.0, int, 4),
        ("0.5", float, 0.5),
        ("1e-3", float, 0.001),
        (3, float, 3.0),
        ("1+2j", complex, 1 + 2j),
        ("1 + 2j", complex, 1 + 2j),
        ("abc", str, "abc"),
        (5, str, "5"),
        ("ab", bytes, b"ab"),
        ([97], bytes, b"a"),
        ("true", bool, True),
        ("off", bool, False),
        (1, bool, True),
        ("None", type(None), None),
        (None, None, None),
    ],
)
def test_scalar_coercion(raw, annotation, expected):
    out = coerce_value(raw, annotation)
    assert out == expected
    assert type(out) is type(expected)


@pytest.mark.parametrize(
    "raw,annotation",
    [
        ("0.5", int),
        (0.5, int),
        ("abc", int),
        ("abc", float),
        ("maybe", bool),
        ("x", type(None)),
    ],
)
def test_scalar_coercion_rejects(raw, annotation):
    with pytest.raises(ValueError):
        coerce_value(raw, annotation)


def test_coercers_table_covers_scalars():
    assert set(COERCERS) == {bool, int, float, complex, str, bytes, type(None)}


def test_coercers_direct_calls():
    assert COERCERS[int](Decimal(4)) == 4
    assert COERCERS[type(None)](None) is None


# ---------------------------------------------------------------------------
# typing constructs
# ---------------------------------------------------------------------------


def test_any_and_object_pass_through():
    marker = object()
    assert coerce_value(marker, Any) is marker
    assert coerce_value("5", object) == "5"


def test_optional():
    assert coerce_value("none", Optional[int]) is None
    assert coerce_value("NULL", int | None) is None
    assert coerce_value(None, Optional[int]) is None
    assert coerce_value("5", Optional[int]) == 5


def test_union_order_and_exact_match():
    assert coerce_value("5", Union[int, str]) == 5
    assert coerce_value("5", Union[str, int]) == "5"
    assert coerce_value("abc", int | str) == "abc"
    assert coerce_value(2.5, int | float) == 2.5


def test_union_no_match():
    with pytest.raises(ValueError, match="matches no member"):
        coerce_value("abc", int | float)


def test_literal():
    assert coerce_value("b", Literal["a", "b"]) == "b"
    out = coerce_value("2", Literal[1, 2])
    assert out == 2 and type(out) is int
    assert coerce_value("true", Literal[True, "x"]) is True
    with pytest.raises(ValueError, match="is not one of"):
        coerce_value("c", Literal["a", "b"])
    with pytest.raises(ValueError, match="is not one of"):
        coerce_value("abc", Literal[1, 2])


def test_newtype():
    assert coerce_value("12", UserId) == 12


@pytest.mark.parametrize(
    "raw,annotation,expected",
    [
        ("[1, 2]", list[int], [1, 2]),
        ("1,2,3", list[int], [1, 2, 3]),
        ("5", list[int], [5]),
        ("a,b", list[str], ["a", "b"]),
        ("[a, b]", list[str], ["a", "b"]),
        ("'a,b'", list[str], ["a,b"]),
        ("", list[int], []),
        ("[]", list, []),
        ("[1, 'x']", list, [1, "x"]),
        ("x,2", list, ["x", 2]),
        ((1, 2), list[str], ["1", "2"]),
        ("1,2", tuple[int, ...], (1, 2)),
        ("1,a", tuple[int, str], (1, "a")),
        ("[1, 2]", tuple, (1, 2)),
        ("1,2,2", set[int], {1, 2}),
        ("1,2", frozenset[int], frozenset({1, 2})),
        ("1,2", collections.abc.Sequence[int], [1, 2]),
        ("1,2", typing.List[int], [1, 2]),
        ("1,2", collections.abc.Set[int], frozenset({1, 2})),
        ("[[1, 2], [3]]", list[list[int]], [[1, 2], [3]]),
        ("1,none", list[Optional[int]], [1, None]),
    ],
)
def test_sequences(raw, annotation, expected):
    out = coerce_value(raw, annotation)
    assert out == expected
    assert type(out) is type(expected)


def test_tuple_length_mismatch():
    with pytest.raises(ValueError, match="expected 2 items"):
        coerce_value("1,2,3", tuple[int, int])


def test_sequence_rejects_non_iterables():
    with pytest.raises(TypeError, match="not a sequence"):
        coerce_value(5, list[int])
    with pytest.raises(TypeError, match="not a sequence"):
        coerce_value({"a": 1}, list)


@pytest.mark.parametrize(
    "raw,annotation,expected",
    [
        ("{'a': 1}", dict[str, int], {"a": 1}),
        ('{"a": "2"}', dict[str, int], {"a": 2}),
        ("a=1,b=2", dict[str, int], {"a": 1, "b": 2}),
        ("{a: 1, b: x}", dict, {"a": 1, "b": "x"}),
        ("a=1,", dict, {"a": 1}),
        ({1: "2"}, dict[str, float], {"1": 2.0}),
        ("x=1", collections.abc.Mapping[str, int], {"x": 1}),
    ],
)
def test_mappings(raw, annotation, expected):
    assert coerce_value(raw, annotation) == expected


def test_mapping_rejects():
    with pytest.raises(ValueError, match="KEY=VALUE"):
        coerce_value("a,b", dict)
    with pytest.raises(TypeError, match="not a mapping"):
        coerce_value("[1, 2]", dict)


# ---------------------------------------------------------------------------
# classes
# ---------------------------------------------------------------------------


def test_enum_by_name_value_and_prefix():
    assert coerce_value("RED", Color) is Color.RED
    assert coerce_value("green", Color) is Color.GREEN
    assert coerce_value("Color.GREEN", Color) is Color.GREEN
    assert coerce_value("2", Level) is Level.HIGH
    assert coerce_value(1, Level) is Level.LOW
    assert coerce_value("high", Level) is Level.HIGH
    assert coerce_value("LOWER", Mixed) is Mixed.lower
    assert coerce_value(Color.RED, Color) is Color.RED


def test_enum_rejects():
    with pytest.raises(ValueError, match="not a member of Color"):
        coerce_value("blue", Color)
    with pytest.raises(ValueError, match="not a member of Level"):
        coerce_value("blue", Level)


def test_format_arg_hook():
    out = coerce_value("fp16", Dtype)
    assert isinstance(out, Dtype) and out.name == "parsed:fp16"
    existing = Dtype("keep")
    assert coerce_value(existing, Dtype) is existing


def test_annotated_format_arg():
    ann = Annotated[int, FormatArg(lambda s: int(s) * 10)]
    assert coerce_value("3", ann) == 30
    assert coerce_value(7, ann) == 7
    generic = Annotated[list[int], FormatArg(lambda s: [len(s)])]
    assert coerce_value("abc", generic) == [3]
    last_wins = Annotated[str, FormatArg(str.upper), FormatArg(str.lower)]
    assert coerce_value("MiX", last_wins) == "mix"


def test_annotated_without_format_arg_uses_base():
    assert coerce_value("3", Annotated[int, "doc"]) == 3


def test_explicit_class_constructor():
    assert coerce_value("a/b", Path) == Path("a/b")
    assert coerce_value("0.1", Decimal) == Decimal("0.1")
    plain = coerce_value("x", Plain)
    assert isinstance(plain, Plain) and plain.arg == "x"


def test_inferred_non_value_class_passes_through():
    assert coerce_value("x", Plain, explicit=False) == "x"


def test_inferred_value_classes_are_coerced():
    assert coerce_value("a/b", PurePosixPath, explicit=False) == PurePosixPath("a/b")
    assert coerce_value("1/3", Fraction, explicit=False) == Fraction(1, 3)
    assert isinstance(coerce_value("x", Dtype, explicit=False), Dtype)


def test_unknown_typing_construct_passes_through():
    T = typing.TypeVar("T")
    assert coerce_value("x", T) == "x"
    assert coerce_value("x", "ForwardName") == "x"
    assert coerce_value("x", typing.Callable[[int], int]) == "x"


def test_is_value_type():
    assert is_value_type(int) and is_value_type(list) and is_value_type(Color)
    assert is_value_type(Path) and is_value_type(Decimal) and is_value_type(Dtype)
    assert not is_value_type(Plain)


# ---------------------------------------------------------------------------
# inference from defaults
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "default,expected",
    [
        (None, Any),
        (1, int),
        (True, bool),
        (Plain("x"), Any),
        (Color.RED, Color),
        ([], list),
        ([1, 2], list[int]),
        ([1, "a"], list),
        ([None], list),
        ([[1], [2]], list[list[int]]),
        ({1, 2}, set[int]),
        ((1, 2), tuple[int, ...]),
        ((1, "a"), tuple[int, str]),
        ((1, None), tuple),
        ((), tuple),
        ({"a": 1}, dict[str, int]),
        ({"a": None}, dict),
        ({}, dict),
    ],
)
def test_infer_annotation(default, expected):
    assert infer_annotation(default) == expected


# ---------------------------------------------------------------------------
# coerce_globals / resolve_raw_args
# ---------------------------------------------------------------------------


def test_coerce_globals_annotation_wins_over_default():
    out = coerce_globals({"lr": "0.5"}, {"lr": 1}, annotations={"lr": float})
    assert out == {"lr": 0.5} and type(out["lr"]) is float


def test_coerce_globals_annotation_only_name():
    assert coerce_globals({"n": "3"}, {}, annotations={"n": int}) == {"n": 3}


def test_coerce_globals_none_default_passes_string():
    assert coerce_globals({"resume": "ckpt.pt"}, {"resume": None}) == {
        "resume": "ckpt.pt"
    }


def test_coerce_globals_inferred_list_elements():
    assert coerce_globals({"dims": "64,128"}, {"dims": [32]}) == {"dims": [64, 128]}


def test_coerce_globals_raw_arg_strict_flag():
    with pytest.raises(TypeError, match="cannot coerce n='x' to int"):
        coerce_globals({"n": RawArg("x", strict=True)}, {"n": 1})
    with pytest.raises(KeyError, match="not declared"):
        coerce_globals({"zz": RawArg("x", strict=True)}, {"n": 1})


def test_coerce_globals_warning_names_annotation():
    with pytest.warns(UserWarning, match=r"to list\[int\]"):
        out = coerce_globals({"d": "a,b"}, {}, annotations={"d": list[int]})
    assert out == {"d": "a,b"}


def test_resolve_raw_args_only_touches_raw():
    values = {"a": RawArg("2"), "b": "3", "c": RawArg("x")}
    out = resolve_raw_args(values, {"a": 1, "b": 1})
    assert out == {"a": 2, "b": "3", "c": "x"}
    plain = {"b": "3"}
    assert resolve_raw_args(plain, {"b": 1}) is plain


def test_raw_arg_repr_round_trips():
    raw = RawArg("0.5", strict=True)
    assert eval(repr(raw), {"RawArg": RawArg}) == raw
