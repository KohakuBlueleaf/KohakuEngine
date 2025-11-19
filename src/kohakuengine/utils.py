"""Utility functions for KohakuEngine."""

from pathlib import Path


def resolve_path(path: str | Path) -> Path:
    """
    Resolve path to absolute path.

    Args:
        path: Path to resolve

    Returns:
        Absolute Path object
    """
    return Path(path).resolve()


def ensure_py_extension(path: Path) -> None:
    """
    Ensure file has .py extension.

    Args:
        path: Path to check

    Raises:
        ValueError: If file doesn't have .py extension
    """
    if path.suffix != ".py":
        raise ValueError(f"File must have .py extension: {path}")
