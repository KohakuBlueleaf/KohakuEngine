"""Layer ``--set`` / ``--sweep`` overrides onto a base config."""

import difflib
import itertools
from collections.abc import Iterable, Iterator, Mapping
from typing import Any

from kohakuengine.config.base import Config
from kohakuengine.config.generator import ConfigGenerator
from kohakuengine.config.raw import RawArg

_TYPO_CUTOFF = 0.6


def _raw(value: Any, strict: bool) -> RawArg:
    if isinstance(value, RawArg):
        return RawArg(value.value, value.strict or strict)
    return RawArg(value, strict)


def _plain(value: Any) -> Any:
    return value.value if isinstance(value, RawArg) else value


def check_declared(keys: Iterable[str], declared: set[str]) -> None:
    """Raise ``KeyError`` naming every key not in ``declared``."""
    unknown = sorted(set(keys) - declared)
    if not unknown:
        return
    parts = []
    for key in unknown:
        match = difflib.get_close_matches(key, declared, n=1, cutoff=_TYPO_CUTOFF)
        parts.append(f"{key!r} (did you mean {match[0]!r}?)" if match else repr(key))
    raise KeyError(f"not declared in the script defaults: {', '.join(parts)}")


def layer_overrides(
    config: Config | ConfigGenerator | None,
    *,
    set_values: Mapping[str, Any] | None = None,
    sweep_values: Mapping[str, list[Any]] | None = None,
    strict: bool = False,
    declared: set[str] | None = None,
) -> Config | ConfigGenerator | None:
    """
    Apply overrides to every base config (one ``Config`` or each generated one).

    ``set_values`` apply to every run; ``sweep_values`` expand each base into
    the cartesian product of its axes (axis values also land in ``metadata``).
    Override values are wrapped in :class:`RawArg` so they are coerced when
    the script loads. ``declared`` (the script's declared names) enables the
    strict key check on overrides and on every base config's keys. Returns a
    ``Config`` unless a sweep or a generator base makes it a
    ``ConfigGenerator``; generator bases stay lazy.
    """
    set_values = dict(set_values or {})
    sweep_values = {k: list(v) for k, v in (sweep_values or {}).items()}
    clash = sorted(set(set_values) & set(sweep_values))
    if clash:
        raise ValueError(f"keys given to both --set and --sweep: {clash}")
    if declared is not None:
        check_declared([*set_values, *sweep_values], declared)
    if config is None and not set_values and not sweep_values:
        return None

    set_raw = {k: _raw(v, strict) for k, v in set_values.items()}
    axes = list(sweep_values)
    combos = list(itertools.product(*sweep_values.values())) if axes else [()]

    def layer(base: Config) -> Iterator[Config]:
        for combo in combos:
            sweep_raw = {a: _raw(v, strict) for a, v in zip(axes, combo)}
            yield Config(
                globals_dict={**base.globals_dict, **set_raw, **sweep_raw},
                args=list(base.args),
                kwargs=dict(base.kwargs),
                metadata={
                    **base.metadata,
                    **{a: _plain(v) for a, v in zip(axes, combo)},
                },
            )

    def checked(bases: Iterable[Config]) -> Iterator[Config]:
        for base in bases:
            if declared is not None:
                check_declared(base.globals_dict, declared)
            yield from layer(base)

    if isinstance(config, ConfigGenerator):
        return ConfigGenerator(checked(config))
    base = config if config is not None else Config()
    if declared is not None:
        check_declared(base.globals_dict, declared)
    produced = layer(base)
    if not axes:
        return next(produced)
    return ConfigGenerator(produced)
