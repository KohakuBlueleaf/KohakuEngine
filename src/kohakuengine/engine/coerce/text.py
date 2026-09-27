"""Text parsing helpers shared by the coercer and the CLI."""

import ast
import json
from typing import Any

_OPENERS = {"(": ")", "[": "]", "{": "}"}
_QUOTES = frozenset({"'", '"'})
_LITERAL_ERRORS = (ValueError, SyntaxError, TypeError, MemoryError, RecursionError)


def split_top_level(text: str, sep: str = ",") -> list[str]:
    """
    Split ``text`` on ``sep`` outside brackets and quotes; items are stripped.

    ``"1,[2,3],'a,b'"`` -> ``["1", "[2,3]", "'a,b'"]``.
    """
    items: list[str] = []
    stack: list[str] = []
    quote: str | None = None
    start = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if quote is not None:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch in _QUOTES:
            quote = ch
        elif ch in _OPENERS:
            stack.append(_OPENERS[ch])
        elif stack and ch == stack[-1]:
            stack.pop()
        elif ch == sep and not stack:
            items.append(text[start:i].strip())
            start = i + 1
        i += 1
    items.append(text[start:].strip())
    return items


def parse_literal(text: str) -> Any:
    """Parse a Python literal, falling back to JSON; raise ``ValueError``."""
    try:
        return ast.literal_eval(text.strip())
    except _LITERAL_ERRORS:
        pass
    try:
        return json.loads(text)
    except ValueError as exc:
        raise ValueError(f"{text!r} is not a Python or JSON literal") from exc


def guess_scalar(text: str) -> Any:
    """Parse ``text`` as a literal when possible, else keep the stripped text."""
    try:
        return parse_literal(text)
    except ValueError:
        return text.strip()


def strip_brackets(text: str) -> str:
    """Drop one pair of enclosing ``()``, ``[]`` or ``{}``."""
    text = text.strip()
    if len(text) >= 2 and _OPENERS.get(text[0]) == text[-1]:
        return text[1:-1]
    return text
