"""--set / --sweep / set_overrides obey script annotations end to end."""

# ruff: noqa: UP045 -- Optional[int] is the annotation whose rendering is checked.

import argparse
import sys
from pathlib import Path
from typing import Optional

import pytest

from kohakuengine import Config, ConfigGenerator, RawArg, Script, run
from kohakuengine.cli import cmd_config_check, cmd_run
from kohakuengine.engine import layer_overrides
from kohakuengine.engine.coerce import describe_annotation
from kohakuengine.engine.executor import ScriptExecutor
from kohakuengine.flow import Parallel, Sequential


def _ns(**kw):
    defaults = {
        "script": None,
        "config": None,
        "entrypoint": None,
        "set": [],
        "sweep": [],
        "strict": False,
        "subprocess": False,
    }
    defaults.update(kw)
    return argparse.Namespace(**defaults)


def _set_flags(values: dict[str, str]) -> list[str]:
    return [f"{k}={v}" for k, v in values.items()]


def _run_cli(capsys, **kw) -> str:
    with pytest.raises(SystemExit) as exc:
        cmd_run(_ns(**kw))
    assert exc.value.code == 0
    return capsys.readouterr().out


# ---------------------------------------------------------------------------
# In-process: run() and cmd_run
# ---------------------------------------------------------------------------


def test_run_api_coerces_every_annotation(typed_script, eval_set, eval_expected):
    out = run(str(typed_script) + ":expect_eval", set_overrides=eval_set)
    assert out == eval_expected


def test_run_api_defaults_untouched(typed_script):
    out = run(str(typed_script), set_overrides={"lr": "2"})
    assert type(out["lr"]) is float and out["lr"] == 2.0
    assert out["dims"] == [32] and out["mode"] == "TRAIN"


def test_cli_set_coerces_every_annotation(
    typed_script, eval_set, eval_expected, capsys
):
    out = _run_cli(
        capsys,
        script=str(typed_script),
        entrypoint="expect_eval",
        set=_set_flags(eval_set),
        strict=True,
    )
    assert f"Return value: {eval_expected}" in out


def test_cli_set_strict_rejects_bad_value(typed_script):
    with pytest.raises(TypeError, match="cannot coerce mode='bogus' to Mode"):
        cmd_run(_ns(script=str(typed_script), set=["mode=bogus"], strict=True))


def test_cli_set_non_strict_warns_and_passes_through(typed_script):
    with (
        pytest.warns(UserWarning, match="cannot coerce epochs='0.5' to int"),
        pytest.raises(AssertionError, match="0.5"),
    ):
        cmd_run(_ns(script=str(typed_script), set=["epochs=0.5"]))


def test_cli_strict_unknown_key_suggests(typed_script):
    with pytest.raises(KeyError, match=r"'epoch' \(did you mean 'epochs'\?\)"):
        cmd_run(_ns(script=str(typed_script), set=["epoch=3"], strict=True))


def test_cli_strict_checks_config_file_keys(typed_script, make_config):
    cfg = make_config("c.py", "lr = 0.3\nwholly_unrelated_key = 1\n")
    with pytest.raises(KeyError, match="'wholly_unrelated_key'"):
        cmd_run(_ns(script=str(typed_script), config=str(cfg), strict=True))


def test_cli_set_over_config_file(typed_script, make_config, capsys):
    cfg = make_config("c.py", "epochs = 7\nlr = 0.25\n")
    out = _run_cli(capsys, script=str(typed_script), config=str(cfg), set=["epochs=2"])
    assert "'epochs': 2" in out and "'lr': 0.25" in out


def test_cli_set_and_sweep_combined(typed_script, capsys):
    out = _run_cli(
        capsys,
        script=str(typed_script),
        set=["epochs=4"],
        sweep=["dims=[1,2],[3]", "lr=0.1,0.2"],
    )
    assert "(4 iterations)" in out


def test_cli_set_with_generator_config(typed_script, make_config, capsys):
    cfg = make_config(
        "g.py",
        """
        from kohakuengine.config import Config
        def config_gen():
            for lr in (0.1, 0.2):
                yield Config(globals_dict={"lr": lr})
        """,
    )
    out = _run_cli(
        capsys,
        script=str(typed_script),
        config=str(cfg),
        set=["epochs=5"],
        sweep=["mode=train,eval"],
        strict=True,
    )
    assert "(4 iterations)" in out


def test_cli_sweep_results_are_typed(typed_script):
    config = layer_overrides(
        None,
        set_values={"epochs": "4"},
        sweep_values={"dims": ["[1,2]", "[3]"], "mode": ["train", "eval"]},
    )
    results = Sequential([Script(str(typed_script), config=config)]).run()
    assert [(r["dims"], r["mode"], r["epochs"]) for r in results] == [
        ([1, 2], "TRAIN", 4),
        ([1, 2], "EVAL", 4),
        ([3], "TRAIN", 4),
        ([3], "EVAL", 4),
    ]


def test_cli_module_script_with_set(tmp_path, restore_import_state, capsys):
    pkg = tmp_path / "typed_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "mod.py").write_text(
        "size: float = 1\n"
        "def main():\n"
        "    assert type(size) is float, size\n"
        "    return size\n"
    )
    sys.path.insert(0, str(tmp_path))
    out = _run_cli(capsys, script="typed_pkg.mod", set=["size=3"], strict=True)
    assert "Return value: 3.0" in out


# ---------------------------------------------------------------------------
# Config cells
# ---------------------------------------------------------------------------


def test_cell_script_coerces_cell_and_tail(cell_script):
    out = run(
        str(cell_script),
        set_overrides={
            "lr": "0.5",
            "steps": "9",
            "out": "x/y",
            "mode": "EVAL",
            "width": "16",
            "tail": "2.5",
        },
    )
    assert out == {
        "lr": 0.5,
        "steps": 9,
        "out": Path("x/y"),
        "mode": "EVAL",
        "width": 16,
        "tail": 2.5,
    }
    assert type(out["lr"]) is float and type(out["width"]) is int


def test_cell_strict_surface_is_the_cell(cell_script):
    out = run(str(cell_script), set_overrides={"steps": "1"}, strict=True)
    assert out["steps"] == 1
    with pytest.raises(KeyError, match="'tail'"):
        run(str(cell_script), set_overrides={"steps": "1", "tail": "2"}, strict=True)


def test_cell_annotation_only_name_without_override_is_unbound(cell_script):
    with pytest.raises(NameError, match="steps"):
        run(str(cell_script))


# ---------------------------------------------------------------------------
# Out-of-process: subprocess CLI, workflows, pool
# ---------------------------------------------------------------------------


def test_cli_subprocess_forwards_entrypoint_and_coerces_in_child(typed_script, capfd):
    with pytest.raises(SystemExit) as exc:
        cmd_run(
            _ns(
                script=str(typed_script) + ":expect_eval",
                set=["mode=eval", "dtype=bf16", "lr=0.5"],
                subprocess=True,
                strict=True,
            )
        )
    captured = capfd.readouterr()
    assert exc.value.code == 0, captured.err
    assert "'mode': 'EVAL'" in captured.out and "'lr': 0.5" in captured.out


def test_cli_subprocess_child_strict_failure_propagates(typed_script, capfd):
    with pytest.raises(SystemExit) as exc:
        cmd_run(
            _ns(
                script=str(typed_script),
                set=["lr=abc"],
                subprocess=True,
                strict=True,
            )
        )
    assert exc.value.code != 0
    assert "cannot coerce lr='abc' to float" in capfd.readouterr().err


def test_sequential_subprocess_sweep(typed_script):
    config = layer_overrides(
        None, sweep_values={"mode": ["train", "eval"]}, strict=True
    )
    script = Script(str(typed_script), config=config)
    results = Sequential([script], use_subprocess=True).run()
    assert [r.returncode for r in results] == [0, 0]


def test_parallel_subprocess_raw_args(typed_script):
    cfg = Config(globals_dict={"mode": RawArg("eval", True), "dtype": RawArg("bf16")})
    script = Script(str(typed_script), config=cfg, entrypoint="expect_eval")
    results = Parallel([script], max_workers=1, use_subprocess=True).run()
    assert [r.returncode for r in results] == [0]


def test_parallel_pool_raw_args(typed_script):
    gen = ConfigGenerator(
        iter([Config(globals_dict={"lr": RawArg(v)}) for v in ("0.25", "4")])
    )
    script = Script(str(typed_script), config=gen)
    results = Parallel([script], max_workers=2, use_subprocess=False).run()
    assert sorted(r["lr"] for r in results) == [0.25, 4.0]


def test_executor_without_raw_args_does_not_coerce(typed_script):
    cfg = Config(globals_dict={"resume": 5, "opt": "sgd"})
    out = ScriptExecutor(Script(str(typed_script))).execute(cfg)
    assert out["resume"] == 5 and out["opt"] == "sgd"


# ---------------------------------------------------------------------------
# config check shows annotations
# ---------------------------------------------------------------------------


def test_config_check_shows_annotation(typed_script, make_config, capsys):
    cfg = make_config("c.py", "lr = 0.5\nsteps = 3\n")
    with pytest.raises(SystemExit) as exc:
        cmd_config_check(_ns(script=str(typed_script), config=str(cfg)))
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "[OK]  lr: 1 (float) -> 0.5" in out
    optional_int = describe_annotation(Optional[int])
    assert f"[OK]  steps: None ({optional_int}) -> 3" in out


def test_config_check_annotation_only_name(make_script, make_config, capsys):
    s = make_script("s.py", "count: int\ndef main():\n    return count\n")
    cfg = make_config("c.py", "count = 3\n")
    with pytest.raises(SystemExit):
        cmd_config_check(_ns(script=str(s), config=str(cfg)))
    assert "[OK]  count: <no default> (int) -> 3" in capsys.readouterr().out
