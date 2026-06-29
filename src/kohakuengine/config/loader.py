"""Loader for config files (Python source files)."""

import importlib.util
import inspect
import itertools
import sys
import warnings
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator

from kohakuengine.config.base import Config, _filter_globals
from kohakuengine.config.generator import ConfigGenerator

_VALID_SWEEP_MODES: frozenset[str] = frozenset({"grid", "zip"})

# Attribute used by ``use_config`` to record imported parent configs on the
# config module being executed. Underscore-prefixed so ``_filter_globals``
# never captures it as a data global.
_USED_CONFIGS_ATTR = "_kogine_used_configs"

# Absolute paths currently being resolved by ``use_config`` (cycle guard).
_USE_CONFIG_STACK: list[str] = []


def _exec_config_module(config_path: Path) -> ModuleType:
    """Load a config file as an importable module."""
    module_name = f"_kogine_config_{config_path.stem}_{abs(hash(str(config_path)))}"
    spec = importlib.util.spec_from_file_location(module_name, config_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load config from {config_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def _resolve_sibling_path(path: str | Path, caller_globals: dict[str, Any]) -> Path:
    """Resolve ``path`` relative to the *calling* config file's directory."""
    p = Path(path)
    if p.is_absolute():
        return p.resolve()
    caller_file = caller_globals.get("__file__")
    if caller_file:
        return (Path(caller_file).resolve().parent / p).resolve()
    return (Path.cwd() / p).resolve()


def use_config(path: str | Path) -> Config:
    """
    Compose configuration by importing another config file's resolved values.

    Call this at the top level of a bare (or ``_sweep``) config file to merge
    another config into the current one::

        # experiment.py
        from kohakuengine import use_config

        use_config("base.py")      # inherit everything from base.py
        batch_size = 128           # ...then override what you need

    Why a helper (instead of ``import``): a plain ``import`` is blocked (the
    config's directory is deliberately not on ``sys.path``) and would also
    bypass the loader -- so ``config_gen`` / ``CONFIG`` bases would not resolve
    and ``_args`` / ``_kwargs`` / ``_metadata`` and imported helpers would be
    dropped. ``use_config`` loads the file through the full loader instead.

    Semantics:

    - ``path`` is resolved relative to the calling config file's directory.
    - The file is loaded via :func:`load_config_file`, so bare, ``CONFIG`` and
      ``config_gen`` forms all resolve. Importing a sweep / generator config is
      an error (it is not a single value source).
    - **Your own top-level variables win** over imported ones. Stack multiple
      ``use_config(...)`` calls to layer bases; later calls win over earlier.
    - ``_args`` is inherited (your own, if any, replaces it); ``_kwargs`` and
      ``_metadata`` are merged (your own keys win).

    Returns the resolved :class:`Config`, so it is also usable programmatically
    -- e.g. inside ``config_gen``::

        base = use_config("base.py")
        return Config(globals_dict={**base.globals_dict, "lr": 0.5})
    """
    frame = inspect.currentframe()
    caller_globals = frame.f_back.f_globals if frame and frame.f_back else {}
    base_path = _resolve_sibling_path(path, caller_globals)

    key = str(base_path)
    if key in _USE_CONFIG_STACK:
        chain = " -> ".join([*_USE_CONFIG_STACK, key])
        raise ValueError(f"Circular use_config() detected: {chain}")

    _USE_CONFIG_STACK.append(key)
    try:
        cfg = load_config_file(base_path)
    finally:
        _USE_CONFIG_STACK.pop()

    if isinstance(cfg, ConfigGenerator):
        raise TypeError(
            f"use_config() cannot import a sweep/generator config: {base_path}. "
            "Import a single (bare / CONFIG / config_gen) config instead."
        )

    used = caller_globals.setdefault(_USED_CONFIGS_ATTR, [])
    used.append(cfg)
    return cfg


def _apply_used_configs(
    module: ModuleType,
    own_globals: dict[str, Any],
    own_args: list,
    own_kwargs: dict,
    own_metadata: dict,
) -> tuple[dict[str, Any], list, dict, dict]:
    """
    Layer ``use_config`` parents under this module's own values (child wins).

    Imported configs apply in call order (later overrides earlier); the
    module's own top-level values override all of them.
    """
    used = getattr(module, _USED_CONFIGS_ATTR, None)
    if not used:
        return own_globals, own_args, own_kwargs, own_metadata

    globals_dict: dict[str, Any] = {}
    kwargs: dict[str, Any] = {}
    metadata: dict[str, Any] = {}
    args: list = []
    for cfg in used:
        globals_dict.update(cfg.globals_dict)
        kwargs.update(cfg.kwargs)
        metadata.update(cfg.metadata)
        if cfg.args:
            args = list(cfg.args)

    globals_dict.update(own_globals)
    kwargs.update(own_kwargs)
    metadata.update(own_metadata)
    if own_args:
        args = list(own_args)
    return globals_dict, args, kwargs, metadata


def _extract_meta(module: ModuleType) -> tuple[list, dict, dict]:
    """Pull ``_args``, ``_kwargs``, ``_metadata`` off a config module."""
    args_obj = getattr(module, "_args", None)
    kwargs_obj = getattr(module, "_kwargs", None)
    meta_obj = getattr(module, "_metadata", None)

    if args_obj is None:
        args: list[Any] = []
    elif isinstance(args_obj, (list, tuple)):
        args = list(args_obj)
    else:
        raise TypeError(f"_args must be a list or tuple, got {type(args_obj).__name__}")

    if kwargs_obj is None:
        kwargs: dict[str, Any] = {}
    elif isinstance(kwargs_obj, dict):
        kwargs = dict(kwargs_obj)
    else:
        raise TypeError(f"_kwargs must be a dict, got {type(kwargs_obj).__name__}")

    if meta_obj is None:
        metadata: dict[str, Any] = {}
    elif isinstance(meta_obj, dict):
        metadata = dict(meta_obj)
    else:
        raise TypeError(f"_metadata must be a dict, got {type(meta_obj).__name__}")

    return args, kwargs, metadata


def _expand_sweep(module: ModuleType) -> ConfigGenerator:
    """Expand a declarative ``_sweep`` dict into a ConfigGenerator."""
    sweep_obj = module._sweep
    if not isinstance(sweep_obj, dict):
        raise TypeError(f"_sweep must be a dict, got {type(sweep_obj).__name__}")

    sweep = dict(sweep_obj)
    mode = sweep.pop("__mode__", "grid")
    if mode not in _VALID_SWEEP_MODES:
        raise ValueError(
            f"Unknown _sweep mode: {mode!r} (valid: {sorted(_VALID_SWEEP_MODES)})"
        )

    for axis, values in sweep.items():
        if not isinstance(values, (list, tuple)):
            raise TypeError(
                f"_sweep[{axis!r}] must be a list or tuple, got "
                f"{type(values).__name__}"
            )

    if mode == "zip" and len(sweep) > 1:
        lengths = {axis: len(v) for axis, v in sweep.items()}
        unique = set(lengths.values())
        if len(unique) > 1:
            raise ValueError(
                f"_sweep zip mode requires equal-length axes, got {lengths}"
            )

    base = _filter_globals(vars(module), module.__name__)
    args, kwargs, base_metadata = _extract_meta(module)
    base, args, kwargs, base_metadata = _apply_used_configs(
        module, base, args, kwargs, base_metadata
    )

    def generator() -> Iterator[Config]:
        if not sweep:
            yield Config(
                globals_dict=dict(base),
                args=list(args),
                kwargs=dict(kwargs),
                metadata=dict(base_metadata),
            )
            return

        axes = list(sweep.keys())
        value_lists = [list(sweep[k]) for k in axes]
        if mode == "grid":
            combos: Iterator[tuple] = itertools.product(*value_lists)
        else:
            combos = zip(*value_lists)

        for combo in combos:
            overrides = dict(zip(axes, combo))
            new_globals = {**base, **overrides}
            new_metadata = {**base_metadata, **overrides}
            yield Config(
                globals_dict=new_globals,
                args=list(args),
                kwargs=dict(kwargs),
                metadata=new_metadata,
            )

    return ConfigGenerator(generator())


def _synthesize_from_module(module: ModuleType) -> Config:
    """Build a Config from a bare config file (Idea 1)."""
    globals_dict = _filter_globals(vars(module), module.__name__)
    args, kwargs, metadata = _extract_meta(module)
    globals_dict, args, kwargs, metadata = _apply_used_configs(
        module, globals_dict, args, kwargs, metadata
    )
    return Config(
        globals_dict=globals_dict,
        args=args,
        kwargs=kwargs,
        metadata=metadata,
    )


def _invoke_config_gen(
    module: ModuleType, worker_id: int | None
) -> Config | ConfigGenerator:
    """Call the user's ``config_gen`` function and wrap its result."""
    config_gen = module.config_gen
    if not callable(config_gen):
        raise ValueError("config_gen must be callable")

    sig = inspect.signature(config_gen)
    if worker_id is not None and "worker_id" in sig.parameters:
        result = config_gen(worker_id=worker_id)
    else:
        result = config_gen()

    if isinstance(result, Config):
        return result
    if hasattr(result, "__iter__") and hasattr(result, "__next__"):
        return ConfigGenerator(result)
    raise ValueError(
        f"config_gen() must return Config or generator, got {type(result).__name__}"
    )


def load_config_file(
    config_path: str | Path,
    worker_id: int | None = None,
) -> Config | ConfigGenerator:
    """
    Load a config from a Python file.

    Resolution order:

    1. ``config_gen()`` if present -- call it (today's explicit form).
    2. ``CONFIG`` if present -- use it directly.
    3. ``_sweep`` if present -- expand to a ConfigGenerator.
    4. Otherwise -- synthesize a Config from module-level variables.

    Args:
        config_path: Path to a ``.py`` config file.
        worker_id: Optional worker id forwarded to ``config_gen(worker_id=...)``.

    Returns:
        ``Config`` or ``ConfigGenerator``.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    module = _exec_config_module(config_path)

    has_config_gen = hasattr(module, "config_gen")
    has_CONFIG = hasattr(module, "CONFIG")
    has_sweep = hasattr(module, "_sweep")

    if has_config_gen:
        if has_sweep:
            warnings.warn(
                f"{config_path}: _sweep is ignored because config_gen is defined.",
                stacklevel=2,
            )
        return _invoke_config_gen(module, worker_id)

    if has_CONFIG:
        if has_sweep:
            warnings.warn(
                f"{config_path}: _sweep is ignored because CONFIG is defined.",
                stacklevel=2,
            )
        config = module.CONFIG
        if not isinstance(config, Config):
            raise ValueError(
                f"CONFIG must be Config instance, got {type(config).__name__}"
            )
        return config

    if has_sweep:
        return _expand_sweep(module)

    return _synthesize_from_module(module)


def load_from_dict(data: dict) -> Config:
    """Create a Config from a dict (e.g. a parsed YAML/TOML/JSON payload)."""
    return Config(
        globals_dict=data.get("globals", {}),
        args=data.get("args", []),
        kwargs=data.get("kwargs", {}),
        metadata=data.get("metadata", {}),
    )


class ConfigLoader:
    """Back-compatible facade. Prefer the module-level functions."""

    @staticmethod
    def load_config(
        config_path: str | Path,
        worker_id: int | None = None,
    ) -> Config | ConfigGenerator:
        return load_config_file(config_path, worker_id=worker_id)

    @staticmethod
    def load_from_dict(data: dict) -> Config:
        return load_from_dict(data)
