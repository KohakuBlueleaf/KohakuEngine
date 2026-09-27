"""Coercion of whole override dicts against a script schema."""

import warnings
from collections.abc import Mapping
from typing import Any

from kohakuengine.config.raw import RawArg
from kohakuengine.engine.coerce.value import (
    coerce_value,
    describe_annotation,
    infer_annotation,
)

_EMPTY: Mapping[str, Any] = {}


def _annotation_for(
    key: str, defaults: Mapping[str, Any], annotations: Mapping[str, Any]
) -> tuple[Any, bool]:
    if key in annotations:
        return annotations[key], True
    return infer_annotation(defaults[key]), False


def coerce_globals(
    globals_dict: dict[str, Any],
    defaults: Mapping[str, Any],
    *,
    strict: bool = False,
    annotations: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Coerce every value in ``globals_dict``; returns a new dict.

    A key's type is ``annotations[key]`` if present, else inferred from
    ``defaults[key]``. A ``RawArg`` is unwrapped; its ``strict`` is OR-ed in.
    Strict: undeclared key -> ``KeyError``, failed coercion -> ``TypeError``;
    otherwise both warn (coercion only) and pass the raw value through.
    """
    annotations = annotations if annotations is not None else _EMPTY
    out: dict[str, Any] = {}
    for key, value in globals_dict.items():
        key_strict = strict
        if isinstance(value, RawArg):
            key_strict = strict or value.strict
            value = value.value
        if key not in annotations and key not in defaults:
            if key_strict:
                raise KeyError(f"{key!r} is not declared in the script defaults")
            out[key] = value
            continue

        annotation, explicit = _annotation_for(key, defaults, annotations)
        try:
            out[key] = coerce_value(value, annotation, explicit=explicit)
        except (TypeError, ValueError) as exc:
            if key_strict:
                raise TypeError(
                    f"cannot coerce {key}={value!r} to {describe_annotation(annotation)}: {exc}"
                ) from exc
            warnings.warn(
                f"cannot coerce {key}={value!r} to {describe_annotation(annotation)} "
                f"({exc}); passing through",
                stacklevel=2,
            )
            out[key] = value
    return out


def has_raw_args(globals_dict: Mapping[str, Any]) -> bool:
    return any(isinstance(v, RawArg) for v in globals_dict.values())


def resolve_raw_args(
    globals_dict: dict[str, Any],
    defaults: Mapping[str, Any],
    annotations: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Coerce only the :class:`RawArg` entries; other values pass unchanged."""
    raw = {k: v for k, v in globals_dict.items() if isinstance(v, RawArg)}
    if not raw:
        return globals_dict
    resolved = coerce_globals(raw, defaults, annotations=annotations)
    return {k: resolved.get(k, v) for k, v in globals_dict.items()}
