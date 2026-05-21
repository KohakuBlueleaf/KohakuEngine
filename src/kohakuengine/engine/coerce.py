"""Schema-by-example coercion (Idea 9)."""

import warnings
from typing import Any, Callable

_TRUE_LITERALS: frozenset[str] = frozenset({"true", "1", "yes", "y", "on"})
_FALSE_LITERALS: frozenset[str] = frozenset({"false", "0", "no", "n", "off"})


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.lower().strip()
        if lowered in _TRUE_LITERALS:
            return True
        if lowered in _FALSE_LITERALS:
            return False
    raise ValueError(f"cannot coerce {value!r} to bool")


def _identity(value: Any) -> Any:
    return value


COERCERS: dict[type, Callable[[Any], Any]] = {
    bool: _parse_bool,
    int: int,
    float: float,
    str: str,
}


def coerce_globals(
    globals_dict: dict[str, Any],
    defaults: dict[str, Any],
    *,
    strict: bool = False,
) -> dict[str, Any]:
    """
    Coerce values in ``globals_dict`` to match the types of ``defaults``.

    A string override of an ``int``-typed default becomes an ``int``; a
    string override of a ``bool`` default is parsed via :func:`_parse_bool`;
    etc. Values whose default type is not in :data:`COERCERS` (lists, dicts,
    custom objects) pass through unchanged.

    Args:
        globals_dict: Override values (mutated in-place is avoided -- returns a new dict).
        defaults: Script's default values (from :func:`introspect`).
        strict: If True, an unknown key or failed coercion raises instead of warning.
    """
    out: dict[str, Any] = {}
    for key, value in globals_dict.items():
        if key not in defaults:
            if strict:
                raise KeyError(f"{key!r} is not declared in the script defaults")
            out[key] = value
            continue

        expected = type(defaults[key])
        if expected is bool and isinstance(value, bool):
            out[key] = value
            continue
        if isinstance(value, expected):
            out[key] = value
            continue

        coercer = COERCERS.get(expected, _identity)
        try:
            out[key] = coercer(value)
        except (TypeError, ValueError) as exc:
            if strict:
                raise TypeError(
                    f"cannot coerce {key}={value!r} to {expected.__name__}: {exc}"
                ) from exc
            warnings.warn(
                f"cannot coerce {key}={value!r} to {expected.__name__}; "
                "passing through",
                stacklevel=2,
            )
            out[key] = value
    return out
