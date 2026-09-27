"""Schema-driven coercion of override values (annotations, then defaults)."""

from kohakuengine.engine.coerce.globals import (
    coerce_globals,
    has_raw_args,
    resolve_raw_args,
)
from kohakuengine.engine.coerce.scalars import COERCERS, _parse_bool
from kohakuengine.engine.coerce.text import parse_literal, split_top_level
from kohakuengine.engine.coerce.value import (
    FORMAT_HOOK,
    FormatArg,
    coerce_value,
    describe_annotation,
    infer_annotation,
    is_value_type,
)

__all__ = [
    "COERCERS",
    "FORMAT_HOOK",
    "FormatArg",
    "_parse_bool",
    "coerce_globals",
    "coerce_value",
    "describe_annotation",
    "has_raw_args",
    "infer_annotation",
    "is_value_type",
    "parse_literal",
    "resolve_raw_args",
    "split_top_level",
]
