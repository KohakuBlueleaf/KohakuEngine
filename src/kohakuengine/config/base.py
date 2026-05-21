"""Base configuration classes for KohakuEngine."""

import inspect
import warnings
from dataclasses import dataclass, field
from types import FrameType, ModuleType
from typing import Any

_RESERVED_NAMES: frozenset[str] = frozenset({"_args", "_kwargs", "_metadata", "_sweep"})


class Use:
    """
    Wrapper marking an imported callable/class for inclusion in config capture.

    With v0.2, locally-defined callables and classes are captured automatically
    by ``Config.from_globals`` and the bare-config-file loader path. ``use()``
    is only required when forwarding an imported callable/class as config data.

    Examples:
        >>> import math
        >>> loss_fn = use(math.sqrt)   # imported callable - needs use()
        >>> def local_fn(x): return x  # locally defined - captured automatically
    """

    __slots__ = ("value",)

    def __init__(self, value: Any) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"use({self.value!r})"


def use(value: Any) -> Use:
    """Mark an imported function/class for inclusion in config capture."""
    return Use(value)


class CaptureGlobals:
    """
    Context manager that captures variables introduced inside a ``with`` block.

    .. deprecated:: 0.2
        Define variables at module top-level instead -- they are captured
        automatically. Will be removed in v0.3.
    """

    def __init__(self) -> None:
        warnings.warn(
            "capture_globals() is deprecated in v0.2 and will be removed in v0.3. "
            "Define variables at module top level instead -- they are captured "
            "automatically by the bare-config-file loader.",
            DeprecationWarning,
            stacklevel=3,
        )
        self.captured: dict[str, Any] = {}
        self._before: set[str] = set()
        self._frame_globals: dict[str, Any] = {}

    def __enter__(self) -> "CaptureGlobals":
        caller = inspect.currentframe().f_back
        self._frame_globals = caller.f_globals
        self._before = set(caller.f_globals.keys())
        return self

    def __exit__(self, *args: Any) -> bool:
        after = set(self._frame_globals.keys())
        for name in after - self._before:
            value = self._frame_globals[name]
            if value is self:
                continue
            self.captured[name] = value
        return False


def capture_globals() -> CaptureGlobals:
    """Create a context manager to capture variables defined inside a block."""
    return CaptureGlobals()


def _filter_globals(
    namespace: dict[str, Any],
    module_name: str,
) -> dict[str, Any]:
    """
    Shared filter used by both ``Config.from_globals`` and the loader.

    Captures:

    - Plain data (numbers, strings, lists, dicts, custom instances...)
    - Local callables and classes (``obj.__module__ == module_name``)
    - Anything wrapped in ``use()``

    Skips:

    - Names starting with ``_`` (reserved names, dunders, privates)
    - Module objects
    - Imported callables/classes (they live in another module)

    Args:
        namespace: Module ``__dict__`` or ``frame.f_globals`` to scan.
        module_name: Used to discriminate locally-defined callables from
            imported ones via the ``__module__`` attribute.

    Returns:
        Dict of ``{name: value}`` suitable for ``Config.globals_dict``.
    """
    out: dict[str, Any] = {}
    for name, value in namespace.items():
        if name.startswith("_"):
            continue
        if isinstance(value, ModuleType):
            continue
        if isinstance(value, Use):
            out[name] = value.value
            continue
        if isinstance(value, type) or callable(value):
            if getattr(value, "__module__", None) == module_name:
                out[name] = value
            continue
        out[name] = value
    return out


def _frame_module_name(frame: FrameType) -> str:
    """Best-effort module name for a frame (used by ``Config.from_globals``)."""
    name = frame.f_globals.get("__name__")
    if isinstance(name, str):
        return name
    return "<unknown>"


@dataclass
class Config:
    """
    Configuration for one script execution.

    Holds the inputs the engine needs:

    - ``globals_dict`` -- module-level globals to inject into the script
    - ``args`` -- positional arguments forwarded to the entrypoint
    - ``kwargs`` -- keyword arguments forwarded to the entrypoint
    - ``metadata`` -- arbitrary tracking/logging info (not injected)

    Examples:
        >>> Config(globals_dict={"lr": 0.01}, kwargs={"device": "cuda"})
        Config(globals_dict={'lr': 0.01}, args=[], kwargs={'device': 'cuda'}, metadata={})
    """

    globals_dict: dict[str, Any] = field(default_factory=dict)
    args: list[Any] = field(default_factory=list)
    kwargs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.globals_dict, dict):
            raise TypeError(
                f"globals_dict must be a dict, got {type(self.globals_dict).__name__}"
            )
        if not isinstance(self.args, (list, tuple)):
            raise TypeError(
                f"args must be a list or tuple, got {type(self.args).__name__}"
            )
        if not isinstance(self.kwargs, dict):
            raise TypeError(f"kwargs must be a dict, got {type(self.kwargs).__name__}")
        if not isinstance(self.metadata, dict):
            raise TypeError(
                f"metadata must be a dict, got {type(self.metadata).__name__}"
            )
        if isinstance(self.args, tuple):
            self.args = list(self.args)

    @classmethod
    def from_context(cls, context: CaptureGlobals) -> "Config":
        """Create a Config from the captured globals of a ``with`` block."""
        return cls(globals_dict=dict(context.captured))

    @classmethod
    def from_globals(cls) -> "Config":
        """
        Capture the caller's module-level variables as a Config.

        Locally-defined callables and classes are captured automatically.
        Imported callables/classes are skipped unless wrapped in ``use()``.
        """
        frame = inspect.currentframe().f_back
        module_name = _frame_module_name(frame)
        return cls(globals_dict=_filter_globals(frame.f_globals, module_name))
