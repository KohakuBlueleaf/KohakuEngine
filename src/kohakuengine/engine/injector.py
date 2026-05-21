"""Inject runtime globals into Python modules."""

from types import ModuleType
from typing import Any

PROTECTED_NAMES: frozenset[str] = frozenset(
    {
        "__name__",
        "__file__",
        "__package__",
        "__loader__",
        "__spec__",
        "__cached__",
        "__builtins__",
        "__doc__",
    }
)


class GlobalInjector:
    """Inject global variables into Python modules."""

    PROTECTED_NAMES = PROTECTED_NAMES

    @staticmethod
    def inject(module: ModuleType, globals_dict: dict[str, Any]) -> None:
        """Inject ``globals_dict`` into ``module``. Refuses protected names."""
        for name, value in globals_dict.items():
            if name in PROTECTED_NAMES:
                raise ValueError(f"Cannot override protected module attribute: {name}")
            setattr(module, name, value)

    @staticmethod
    def get_user_globals(module: ModuleType) -> dict[str, Any]:
        """Return user-defined data globals (skipping modules, callables, classes)."""
        user_globals: dict[str, Any] = {}
        for name in dir(module):
            if name.startswith("_"):
                continue
            value = getattr(module, name)
            if isinstance(value, (ModuleType, type)):
                continue
            if callable(value):
                continue
            user_globals[name] = value
        return user_globals
