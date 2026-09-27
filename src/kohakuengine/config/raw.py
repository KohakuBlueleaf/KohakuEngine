"""Marker for override values that still need coercion against a script."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RawArg:
    """
    An override value (typically a CLI string) awaiting type coercion.

    Resolved when the script loads, against its *live* namespace (top-level
    annotation first, then the default's type), so annotation classes are
    the script's own objects. The ``repr`` is valid Python, so it survives
    the repr-based config file written for subprocess execution.

    ``strict=True``: a failed coercion or undeclared key raises instead of
    warning and passing ``value`` through.
    """

    value: Any
    strict: bool = False
