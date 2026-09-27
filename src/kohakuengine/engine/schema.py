"""A script's configurable surface: default values plus top-level annotations."""

import ast
import typing
import warnings
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kohakuengine.engine.coerce import has_raw_args, resolve_raw_args

_DROP = object()


@dataclass
class ScriptSchema:
    """``defaults``: ``{name: value}``; ``annotations``: ``{name: annotation}``."""

    defaults: dict[str, Any] = field(default_factory=dict)
    annotations: dict[str, Any] = field(default_factory=dict)

    @property
    def declared(self) -> set[str]:
        return set(self.defaults) | set(self.annotations)


def annotation_nodes(body: Iterable[ast.stmt]) -> list[ast.AnnAssign]:
    """Public ``name: T [= v]`` statements among ``body``."""
    return [
        node
        for node in body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and not node.target.id.startswith("_")
    ]


def _unwrap_final(annotation: Any) -> Any:
    if annotation is typing.Final:
        return _DROP
    if typing.get_origin(annotation) is typing.Final:
        return typing.get_args(annotation)[0]
    return annotation


def evaluate_annotations(
    nodes: Iterable[ast.AnnAssign],
    namespace: dict[str, Any],
    filename: str,
) -> dict[str, Any]:
    """
    Evaluate annotation expressions in ``namespace`` (later wins).

    Works from the AST, so it is independent of ``from __future__ import
    annotations`` and of lazy (PEP 649) module annotations. A string
    annotation is evaluated once more. An unresolvable annotation warns and
    is skipped, leaving the name to default-type inference; bare ``Final``
    is skipped the same way and ``Final[T]`` becomes ``T``.
    """
    out: dict[str, Any] = {}
    for node in nodes:
        name = node.target.id
        expr = ast.fix_missing_locations(ast.Expression(body=node.annotation))
        try:
            annotation = eval(compile(expr, filename, "eval"), namespace)
            if isinstance(annotation, str):
                annotation = eval(annotation, namespace)
        except Exception as exc:  # noqa: BLE001 -- arbitrary user expression
            warnings.warn(
                f"{filename}:{node.lineno}: cannot resolve the annotation of "
                f"{name!r} ({exc!r}); falling back to its default's type",
                stacklevel=2,
            )
            continue
        annotation = _unwrap_final(annotation)
        if annotation is _DROP:
            out.pop(name, None)
            continue
        out[name] = annotation
    return out


def source_annotations(
    source_path: str | Path | None, namespace: dict[str, Any]
) -> dict[str, Any]:
    """Top-level annotations of the file at ``source_path``, in ``namespace``."""
    if source_path is None or not Path(source_path).is_file():
        return {}
    path = Path(source_path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return evaluate_annotations(annotation_nodes(tree.body), namespace, str(path))


def resolve_against_namespace(
    globals_dict: dict[str, Any],
    namespace: dict[str, Any],
    source_path: str | Path | None,
) -> dict[str, Any]:
    """Coerce ``RawArg`` values against a *loaded* module's namespace."""
    if not has_raw_args(globals_dict):
        return globals_dict
    annotations = source_annotations(source_path, namespace)
    return resolve_raw_args(globals_dict, _Defaults(namespace), annotations)


class _Defaults(Mapping[str, Any]):
    """Module namespace view without private / dunder names."""

    def __init__(self, namespace: Mapping[str, Any]) -> None:
        self._ns = namespace

    def __getitem__(self, key: str) -> Any:
        if key.startswith("_"):
            raise KeyError(key)
        return self._ns[key]

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and not key.startswith("_") and key in self._ns

    def __iter__(self):
        return (k for k in self._ns if not k.startswith("_"))

    def __len__(self) -> int:
        return sum(1 for _ in self)
