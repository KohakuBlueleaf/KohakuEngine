"""Tests for script schemas: annotations + defaults (engine/schema.py)."""

# ruff: noqa: UP045 -- Optional[...] is the evaluated annotation under test.

import ast
from pathlib import Path
from typing import Final, Optional

import pytest

from kohakuengine import RawArg, introspect_schema
from kohakuengine.engine.cell import clear_cell_cache, evaluate_cell, parse_cell
from kohakuengine.engine.schema import (
    ScriptSchema,
    _Defaults,
    annotation_nodes,
    evaluate_annotations,
    resolve_against_namespace,
    source_annotations,
)


def _eval(src: str, namespace: dict | None = None) -> dict:
    tree = ast.parse(src)
    ns = namespace if namespace is not None else {}
    return evaluate_annotations(annotation_nodes(tree.body), ns, "<test>")


def test_annotation_nodes_filters_private_and_attributes():
    tree = ast.parse("a: int = 1\n_b: int = 2\nx.y: int = 3\nc = 4\nd: str\n")
    names = [n.target.id for n in annotation_nodes(tree.body)]
    assert names == ["a", "d"]


def test_evaluate_annotations_basic_and_string():
    out = _eval("a: int = 1\nb: 'Optional[float]' = None\n", {"Optional": Optional})
    assert out == {"a": int, "b": Optional[float]}


def test_evaluate_annotations_final():
    out = _eval("a: Final[int] = 1\nb: Final = 2\n", {"Final": Final})
    assert out == {"a": int}


def test_evaluate_annotations_final_drops_earlier_entry():
    out = _eval("a: int = 1\na: Final = 2\n", {"Final": Final})
    assert out == {}


def test_evaluate_annotations_unresolvable_warns_and_skips():
    with pytest.warns(UserWarning, match="cannot resolve the annotation of 'a'"):
        out = _eval("a: Missing = 1\nb: int = 2\n")
    assert out == {"b": int}


def test_source_annotations_missing_file_is_empty(tmp_path):
    assert source_annotations(None, {}) == {}
    assert source_annotations(tmp_path / "nope.py", {}) == {}


def test_script_schema_declared():
    schema = ScriptSchema(defaults={"a": 1}, annotations={"b": int})
    assert schema.declared == {"a", "b"}


def test_resolve_against_namespace_ignores_private_names():
    ns = {"_hidden": 1, "n": 1}
    out = resolve_against_namespace(
        {"_hidden": RawArg("2"), "n": RawArg("3")}, ns, None
    )
    assert out == {"_hidden": "2", "n": 3}


def test_resolve_against_namespace_defaults_view_protocol():
    view = _Defaults({"_x": 1, "a": 2, "b": 3})
    assert list(view) == ["a", "b"]
    assert len(view) == 2
    assert "a" in view and "_x" not in view and 5 not in view
    with pytest.raises(KeyError):
        view["_x"]


def test_introspect_schema_future_annotations(make_script):
    p = make_script(
        "s.py",
        """
        from __future__ import annotations
        from pathlib import Path
        out: Path = Path("runs")
        lr: float = 1
        count: int
        def main():
            return out
        """,
    )
    schema = introspect_schema(p)
    assert schema.annotations == {"out": Path, "lr": float, "count": int}
    assert schema.defaults["lr"] == 1
    assert "count" not in schema.defaults
    assert {"out", "lr", "count", "main"} <= schema.declared


def test_introspect_schema_cell_with_annotations(make_script):
    p = make_script(
        "cell.py",
        """
        from typing import Optional
        # %% kogine:config
        lr: float = 1
        steps: Optional[int]
        name = "x"
        # %% kogine:script
        tail: int = 5
        """,
    )
    clear_cell_cache()
    schema = introspect_schema(p)
    assert schema.defaults == {"lr": 1, "name": "x"}
    assert schema.annotations == {"lr": float, "steps": Optional[int]}
    assert evaluate_cell(p, parse_cell(p)) == {"lr": 1, "name": "x"}
    cached = introspect_schema(p)
    assert cached.annotations == schema.annotations
    cached.annotations.clear()
    assert introspect_schema(p).annotations == schema.annotations


def test_introspect_schema_missing_file():
    with pytest.raises(FileNotFoundError):
        introspect_schema(Path("/no/such/file.py"))
