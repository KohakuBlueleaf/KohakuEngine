"""Coercers for scalar builtin types."""

from collections.abc import Callable
from typing import Any

_TRUE_LITERALS: frozenset[str] = frozenset({"true", "1", "yes", "y", "on"})
_FALSE_LITERALS: frozenset[str] = frozenset({"false", "0", "no", "n", "off"})
NONE_LITERALS: frozenset[str] = frozenset({"none", "null"})


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


def _parse_int(value: Any) -> int:
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"{value!r} is not an integral number")
        return int(value)
    if not isinstance(value, str):
        return int(value)
    text = value.strip()
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return int(text, 0)
    except ValueError:
        pass
    return _parse_int(float(text))


def _parse_str(value: Any) -> str:
    return value if isinstance(value, str) else str(value)


def _parse_bytes(value: Any) -> bytes:
    if isinstance(value, str):
        return value.encode("utf-8")
    return bytes(value)


def _parse_none(value: Any) -> None:
    if value is None:
        return
    if isinstance(value, str) and value.strip().lower() in NONE_LITERALS:
        return
    raise ValueError(f"cannot coerce {value!r} to None")


def _parse_float(value: Any) -> float:
    return float(value.strip() if isinstance(value, str) else value)


def _parse_complex(value: Any) -> complex:
    return complex(value.replace(" ", "") if isinstance(value, str) else value)


COERCERS: dict[type, Callable[[Any], Any]] = {
    bool: _parse_bool,
    int: _parse_int,
    float: _parse_float,
    complex: _parse_complex,
    str: _parse_str,
    bytes: _parse_bytes,
    type(None): _parse_none,
}
