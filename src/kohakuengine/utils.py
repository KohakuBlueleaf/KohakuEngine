"""Utility functions for KohakuEngine."""

import keyword
import re
import sys
from pathlib import Path


def add_script_dir_to_path(script_path: str | Path) -> str:
    """
    Put a script's directory on ``sys.path`` the way ``python script.py`` does.

    Plain CPython prepends the directory containing the executed script to
    ``sys.path[0]`` so the script can import its siblings and relative
    (``__init__``-less) packages. ``kogine`` loads scripts through
    :func:`importlib.util.spec_from_file_location`, which does *not* modify
    ``sys.path`` -- so those imports break. This restores the behaviour.

    Args:
        script_path: Path to the script being executed.

    Returns:
        The absolute directory that is now on ``sys.path``.
    """
    script_dir = str(Path(script_path).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    return script_dir


def importable_module_name(script_path: str | Path) -> str:
    """
    Return an importable module name for a file-based script.

    Using the file *stem* (rather than a unique synthetic name) is what makes
    objects defined in the script picklable for :mod:`multiprocessing`: the
    parent resolves ``module.__module__`` via ``sys.modules``, and ``spawn``
    workers -- which inherit the parent's ``sys.path`` (with the script's
    directory on it, see :func:`add_script_dir_to_path`) -- can re-import the
    module by that same name to unpickle the reference.

    Falls back to a sanitized synthetic name when the stem is not a valid
    identifier (e.g. ``my-script.py``); such scripts simply remain
    non-picklable, exactly as they are under plain ``python my-script.py``.

    Args:
        script_path: Path to the script being executed.

    Returns:
        A module name suitable for registration in ``sys.modules``.
    """
    stem = Path(script_path).stem
    if stem.isidentifier() and not keyword.iskeyword(stem):
        return stem
    sanitized = re.sub(r"\W", "_", stem) or "script"
    return f"_kohaku_script_{sanitized}"


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
