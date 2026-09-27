"""Annotation-driven coercion of a single value."""

import collections.abc
import enum
import numbers
import types
import typing
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePath
from typing import Annotated, Any, Literal, Union

from kohakuengine.engine.coerce.scalars import COERCERS, NONE_LITERALS
from kohakuengine.engine.coerce.text import (
    guess_scalar,
    parse_literal,
    split_top_level,
    strip_brackets,
)

FORMAT_HOOK = "format_arg"

_SEQUENCE_ORIGINS: dict[Any, type] = {
    list: list,
    tuple: tuple,
    set: set,
    frozenset: frozenset,
    collections.abc.Sequence: list,
    collections.abc.MutableSequence: list,
    collections.abc.Iterable: list,
    collections.abc.Collection: list,
    collections.abc.Set: frozenset,
    collections.abc.MutableSet: set,
}
_MAPPING_ORIGINS: dict[Any, type] = {
    dict: dict,
    collections.abc.Mapping: dict,
    collections.abc.MutableMapping: dict,
}
_VALUE_BASES: tuple[type, ...] = (enum.Enum, PurePath, numbers.Number)


@dataclass(frozen=True)
class FormatArg:
    """
    ``Annotated`` metadata naming the function that parses an override.

    For types you cannot add a ``format_arg`` classmethod to::

        dtype: Annotated[torch.dtype, FormatArg(lambda s: getattr(torch, s))]
    """

    func: Callable[[Any], Any]


def _is_class(tp: Any) -> bool:
    # Python 3.10 reports isinstance(list[int], type) as True.
    return isinstance(tp, type) and typing.get_origin(tp) is None


def _format_hook(tp: Any) -> Callable[[Any], Any] | None:
    hook = getattr(tp, FORMAT_HOOK, None) if _is_class(tp) else None
    return hook if callable(hook) else None


def is_value_type(tp: type) -> bool:
    """True if ``tp`` may be coerced when only *inferred* from a default."""
    return (
        tp in COERCERS
        or tp in _SEQUENCE_ORIGINS
        or tp in _MAPPING_ORIGINS
        or issubclass(tp, _VALUE_BASES)
        or _format_hook(tp) is not None
    )


def infer_annotation(default: Any) -> Any:
    """
    Derive an annotation from a default value.

    ``None`` -> ``Any``; homogeneous containers carry their element type
    (``[1, 2]`` -> ``list[int]``, ``(1, "a")`` -> ``tuple[int, str]``);
    types that are not value types (see :func:`is_value_type`) -> ``Any``,
    so an arbitrary constructor is never called on an un-annotated name.
    """
    tp = type(default)
    if default is None or not is_value_type(tp):
        return Any
    if tp in (list, set, frozenset) and default:
        elem = _common({infer_annotation(v) for v in default})
        return tp if elem is Any else tp[elem]
    if tp is tuple and default:
        elems = tuple(infer_annotation(v) for v in default)
        if Any in elems:
            return tuple
        if len(set(elems)) == 1:
            return tuple[elems[0], ...]
        return tuple[elems]
    if tp is dict and default:
        key = _common({infer_annotation(k) for k in default})
        val = _common({infer_annotation(v) for v in default.values()})
        return tp if Any in (key, val) else dict[key, val]
    return tp


def _common(annotations: set[Any]) -> Any:
    return next(iter(annotations)) if len(annotations) == 1 else Any


def coerce_value(value: Any, annotation: Any, *, explicit: bool = True) -> Any:
    """
    Coerce ``value`` to ``annotation``; raise ``TypeError``/``ValueError``.

    ``explicit=False`` marks an annotation inferred from a default: plain
    classes that are not value types are then passed through untouched.
    """
    if annotation is Any or annotation is object:
        return value
    if annotation is None:
        annotation = type(None)
    if isinstance(annotation, typing.NewType):
        return coerce_value(value, annotation.__supertype__, explicit=explicit)

    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin is Annotated:
        return _coerce_annotated(value, args[0], annotation.__metadata__, explicit)
    if origin is Union or origin is types.UnionType:
        return _coerce_union(value, args, explicit)
    if origin is Literal:
        return _coerce_literal(value, args, explicit)
    if origin in _SEQUENCE_ORIGINS or annotation in _SEQUENCE_ORIGINS:
        kind = _SEQUENCE_ORIGINS[origin if origin is not None else annotation]
        return _coerce_sequence(value, kind, args, explicit)
    if origin in _MAPPING_ORIGINS or annotation in _MAPPING_ORIGINS:
        return _coerce_mapping(value, args, explicit)
    if _is_class(annotation):
        return _coerce_class(value, annotation, explicit)
    return value


def _coerce_annotated(value: Any, base: Any, metadata: tuple, explicit: bool) -> Any:
    formatters = [m for m in metadata if isinstance(m, FormatArg)]
    if not formatters:
        return coerce_value(value, base, explicit=explicit)
    already = _is_class(base) and isinstance(value, base)
    if already and not isinstance(value, str):
        return value
    return formatters[-1].func(value)


def _coerce_union(value: Any, args: tuple, explicit: bool) -> Any:
    none_type = type(None)
    if none_type in args:
        if value is None:
            return None
        if isinstance(value, str) and value.strip().lower() in NONE_LITERALS:
            return None
    members = [a for a in args if a is not none_type]
    if not isinstance(value, str) and type(value) in members:
        return value
    errors: list[str] = []
    for member in members:
        try:
            return coerce_value(value, member, explicit=explicit)
        except (TypeError, ValueError) as exc:
            errors.append(f"{describe_annotation(member)}: {exc}")
    raise ValueError(f"{value!r} matches no member of the union ({'; '.join(errors)})")


def _coerce_literal(value: Any, options: tuple, explicit: bool) -> Any:
    for option in options:
        if type(value) is type(option) and value == option:
            return option
    for option in options:
        try:
            if coerce_value(value, type(option), explicit=explicit) == option:
                return option
        except (TypeError, ValueError):
            continue
    raise ValueError(f"{value!r} is not one of {list(options)!r}")


def _split_items(value: str) -> list[Any]:
    body = strip_brackets(value)
    if not body.strip():
        return []
    return [guess_scalar(item) for item in split_top_level(body)]


def _as_items(value: Any) -> list[Any]:
    if isinstance(value, str):
        try:
            parsed = parse_literal(value)
        except ValueError:
            return _split_items(value)
        if isinstance(parsed, (str, bytes)) or not isinstance(
            parsed, collections.abc.Iterable
        ):
            return [parsed]
        return list(parsed)
    if isinstance(value, (bytes, collections.abc.Mapping)) or not isinstance(
        value, collections.abc.Iterable
    ):
        raise TypeError(f"{value!r} is not a sequence")
    return list(value)


def _coerce_sequence(value: Any, kind: type, args: tuple, explicit: bool) -> Any:
    items = _as_items(value)
    if kind is tuple and args and not (len(args) == 2 and args[1] is Ellipsis):
        if len(items) != len(args):
            raise ValueError(f"expected {len(args)} items, got {len(items)}")
        return tuple(
            coerce_value(item, arg, explicit=explicit) for item, arg in zip(items, args)
        )
    if args:
        items = [coerce_value(item, args[0], explicit=explicit) for item in items]
    return kind(items)


def _split_pairs(value: str) -> list[tuple[Any, Any]]:
    pairs: list[tuple[Any, Any]] = []
    for item in split_top_level(strip_brackets(value)):
        if not item:
            continue
        seps = [i for i in (item.find("="), item.find(":")) if i >= 0]
        if not seps:
            raise ValueError(f"{item!r} is not a KEY=VALUE / KEY:VALUE pair")
        sep = min(seps)
        pairs.append((guess_scalar(item[:sep]), guess_scalar(item[sep + 1 :])))
    return pairs


def _as_pairs(value: Any) -> list[tuple[Any, Any]]:
    if isinstance(value, str):
        try:
            value = parse_literal(value)
        except ValueError:
            return _split_pairs(value)
    if not isinstance(value, collections.abc.Mapping):
        raise TypeError(f"{value!r} is not a mapping")
    return list(value.items())


def _coerce_mapping(value: Any, args: tuple, explicit: bool) -> dict:
    pairs = _as_pairs(value)
    if len(args) == 2:
        key_t, val_t = args
        return {
            coerce_value(k, key_t, explicit=explicit): coerce_value(
                v, val_t, explicit=explicit
            )
            for k, v in pairs
        }
    return dict(pairs)


def _coerce_enum(value: Any, cls: type[enum.Enum]) -> enum.Enum:
    if isinstance(value, str):
        name = value.strip().removeprefix(f"{cls.__name__}.")
        if name in cls.__members__:
            return cls.__members__[name]
        folded = [m for n, m in cls.__members__.items() if n.lower() == name.lower()]
        if len(folded) == 1:
            return folded[0]
    for member in cls:
        try:
            if coerce_value(value, type(member.value)) == member.value:
                return member
        except (TypeError, ValueError):
            continue
    raise ValueError(
        f"{value!r} is not a member of {cls.__name__} "
        f"(names: {list(cls.__members__)})"
    )


def _coerce_class(value: Any, cls: type, explicit: bool) -> Any:
    hook = _format_hook(cls)
    if hook is not None:
        return value if isinstance(value, cls) else hook(value)
    if cls is bool:
        return COERCERS[bool](value)
    if isinstance(value, cls):
        return value
    if cls in COERCERS:
        return COERCERS[cls](value)
    if issubclass(cls, enum.Enum):
        return _coerce_enum(value, cls)
    if explicit or is_value_type(cls):
        return cls(value)
    return value


def describe_annotation(annotation: Any) -> str:
    """``int`` -> ``'int'``; ``typing.Optional[int]`` -> ``'Optional[int]'``."""
    if _is_class(annotation):
        return annotation.__name__
    return repr(annotation).replace("typing.", "")
