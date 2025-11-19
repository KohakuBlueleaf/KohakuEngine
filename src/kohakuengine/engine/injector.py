"""Global variable injection into Python modules."""

import sys
from types import ModuleType
from typing import Any


class GlobalInjector:
    """Inject global variables into Python modules."""

    # Blacklist of names we should never override
    PROTECTED_NAMES = {
        "__name__",
        "__file__",
        "__package__",
        "__loader__",
        "__spec__",
        "__cached__",
        "__builtins__",
        "__doc__",
    }

    @staticmethod
    def inject(module: ModuleType, globals_dict: dict[str, Any]) -> None:
        """
        Inject global variables into module.

        Args:
            module: Target module
            globals_dict: Dict of {var_name: value} to inject

        Raises:
            ValueError: If trying to override protected names

        Examples:
            >>> import types
            >>> module = types.ModuleType('test')
            >>> GlobalInjector.inject(module, {'learning_rate': 0.001})
            >>> module.learning_rate
            0.001
        """
        for name, value in globals_dict.items():
            if name in GlobalInjector.PROTECTED_NAMES:
                raise ValueError(f"Cannot override protected module attribute: {name}")

            # Set attribute on module
            setattr(module, name, value)

    @staticmethod
    def get_user_globals(module: ModuleType) -> dict[str, Any]:
        """
        Extract user-defined globals from module.

        Filters out built-in attributes, imports, and functions.
        Useful for inspecting what's available to override.

        Args:
            module: Module to inspect

        Returns:
            Dict of user-defined global variables

        Examples:
            >>> import types
            >>> module = types.ModuleType('test')
            >>> module.learning_rate = 0.001
            >>> module.batch_size = 32
            >>> globals_dict = GlobalInjector.get_user_globals(module)
            >>> 'learning_rate' in globals_dict
            True
        """
        user_globals = {}

        for name in dir(module):
            # Skip private/protected
            if name.startswith("_"):
                continue

            value = getattr(module, name)

            # Skip modules, functions, classes (keep only data)
            if isinstance(value, (ModuleType, type)):
                continue
            if callable(value):
                continue

            user_globals[name] = value

        return user_globals
