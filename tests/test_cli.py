"""Tests for the kogine CLI."""

import argparse
import subprocess
import sys

import pytest

from kohakuengine.cli import (
    _parse_set,
    _parse_sweep,
    cmd_config_check,
    cmd_config_show,
    cmd_config_validate,
    cmd_run,
    cmd_workflow_parallel,
    cmd_workflow_sequential,
    create_parser,
    main,
)

# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------


def test_parser_run_defaults():
    p = create_parser()
    args = p.parse_args(["run", "s.py"])
    assert args.script == "s.py"
    assert args.set == []
    assert args.sweep == []
    assert args.strict is False
    assert args.subprocess is False


def test_parser_run_with_flags():
    p = create_parser()
    args = p.parse_args(
        ["run", "s.py", "--set", "a=1", "--set", "b=2", "--sweep", "x=1,2", "--strict"]
    )
    assert args.set == ["a=1", "b=2"]
    assert args.sweep == ["x=1,2"]
    assert args.strict is True


def test_parser_no_command_prints_help(capfd):
    main([])
    out = capfd.readouterr().out
    assert "kogine" in out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_parse_set_basic():
    assert _parse_set(["a=1", "b=hi"]) == {"a": "1", "b": "hi"}


def test_parse_set_missing_eq():
    with pytest.raises(SystemExit, match="KEY=VALUE"):
        _parse_set(["nope"])


def test_parse_sweep_basic():
    assert _parse_sweep(["lr=0.001,0.01"]) == {"lr": ["0.001", "0.01"]}


def test_parse_sweep_missing_eq():
    with pytest.raises(SystemExit):
        _parse_sweep(["xyz"])


# ---------------------------------------------------------------------------
# cmd_run
# ---------------------------------------------------------------------------


def _ns(**kw):
    defaults = dict(
        script=None,
        config=None,
        entrypoint=None,
        set=[],
        sweep=[],
        strict=False,
        subprocess=False,
    )
    defaults.update(kw)
    return argparse.Namespace(**defaults)


def test_cmd_run_simple(simple_script, capsys):
    with pytest.raises(SystemExit) as exc:
        cmd_run(_ns(script=str(simple_script)))
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "executed successfully" in out


def test_cmd_run_with_set(simple_script, capsys):
    with pytest.raises(SystemExit) as exc:
        cmd_run(_ns(script=str(simple_script), set=["lr=0.55"]))
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "0.55" in out


def test_cmd_run_with_config(simple_script, simple_config, capsys):
    with pytest.raises(SystemExit) as exc:
        cmd_run(_ns(script=str(simple_script), config=str(simple_config)))
    assert exc.value.code == 0


def test_cmd_run_with_sweep(simple_script, capsys):
    with pytest.raises(SystemExit) as exc:
        cmd_run(_ns(script=str(simple_script), sweep=["lr=0.1,0.2"]))
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "iterations" in out


def test_cmd_run_with_generator_config(simple_script, make_config, capsys):
    cfg = make_config(
        "g.py",
        """
        from kohakuengine.config import Config
        def config_gen():
            for i in range(2):
                yield Config(globals_dict={"lr": i / 10})
        """,
    )
    with pytest.raises(SystemExit) as exc:
        cmd_run(_ns(script=str(simple_script), config=str(cfg)))
    assert exc.value.code == 0


def test_cmd_run_no_entrypoint(make_script, capsys):
    s = make_script("e.py", "x = 1\n")
    with pytest.raises(SystemExit) as exc:
        cmd_run(_ns(script=str(s), set=["x=2"]))
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "entrypoint" in err.lower()


# ---------------------------------------------------------------------------
# cmd_config_validate / show / check
# ---------------------------------------------------------------------------


def test_cmd_config_validate(bare_config, capsys):
    with pytest.raises(SystemExit) as exc:
        cmd_config_validate(_ns(config=str(bare_config)))
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "valid" in out.lower()


def test_cmd_config_show_static(bare_config, capsys):
    with pytest.raises(SystemExit) as exc:
        cmd_config_show(_ns(config=str(bare_config)))
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "globals_dict" in out
    assert "lr" in out


def test_cmd_config_show_sweep(make_config, capsys):
    cfg = make_config("sweep.py", "_sweep = {'lr': [0.1, 0.2], 'bs': [32]}\n")
    with pytest.raises(SystemExit) as exc:
        cmd_config_show(_ns(config=str(cfg)))
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "Total configs: 2" in out


def test_cmd_config_show_explicit_gen(make_config, capsys):
    cfg = make_config(
        "g.py",
        """
        from kohakuengine.config import Config
        def config_gen():
            return Config(globals_dict={"x": 1})
        """,
    )
    with pytest.raises(SystemExit) as exc:
        cmd_config_show(_ns(config=str(cfg)))
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "config_gen" in out


def test_cmd_config_show_explicit_CONFIG(make_config, capsys):
    cfg = make_config(
        "g.py",
        """
        from kohakuengine.config import Config
        CONFIG = Config(globals_dict={"x": 1})
        """,
    )
    with pytest.raises(SystemExit) as exc:
        cmd_config_show(_ns(config=str(cfg)))
    assert exc.value.code == 0


def test_cmd_config_check_hits(simple_script, bare_config, capsys):
    with pytest.raises(SystemExit) as exc:
        cmd_config_check(_ns(script=str(simple_script), config=str(bare_config)))
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "[OK]" in out
    assert "lr" in out


def test_cmd_config_check_typo(make_script, make_config, capsys):
    s = make_script(
        "s.py",
        """
        learning_rate = 0.1
        def main():
            return learning_rate
        if __name__ == '__main__':
            main()
        """,
    )
    cfg = make_config("c.py", "lerning_rate = 0.5\n")
    with pytest.raises(SystemExit) as exc:
        cmd_config_check(_ns(script=str(s), config=str(cfg)))
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "[??]" in out
    assert "learning_rate" in out


def test_cmd_config_check_new_var(simple_script, make_config, capsys):
    cfg = make_config("c.py", "wholly_new_xy = 5\n")
    with pytest.raises(SystemExit) as exc:
        cmd_config_check(_ns(script=str(simple_script), config=str(cfg)))
    # New var (no similar key) -> exit 0
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "[+]" in out


def test_cmd_config_check_script_missing(bare_config, capsys):
    with pytest.raises(SystemExit) as exc:
        cmd_config_check(_ns(script="/nope/x.py", config=str(bare_config)))
    assert exc.value.code == 2


def test_cmd_config_check_generator_config(make_config, simple_script, capsys):
    cfg = make_config(
        "g.py",
        """
        from kohakuengine.config import Config
        def config_gen():
            for i in range(2):
                yield Config(globals_dict={"lr": i / 10})
        """,
    )
    with pytest.raises(SystemExit) as exc:
        cmd_config_check(_ns(script=str(simple_script), config=str(cfg)))
    assert exc.value.code == 0


# ---------------------------------------------------------------------------
# workflow
# ---------------------------------------------------------------------------


def test_cmd_workflow_sequential(simple_script, capsys):
    args = _ns(scripts=[str(simple_script), str(simple_script)])
    with pytest.raises(SystemExit) as exc:
        cmd_workflow_sequential(args)
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "Sequential" in out


def test_cmd_workflow_parallel(simple_script, capsys):
    args = _ns(
        scripts=[str(simple_script)],
        workers=1,
        mode="subprocess",
    )
    with pytest.raises(SystemExit) as exc:
        cmd_workflow_parallel(args)
    assert exc.value.code == 0


# ---------------------------------------------------------------------------
# Top-level main() -- thin smoke test via subprocess for argv handling
# ---------------------------------------------------------------------------


def test_cli_module_entry(simple_script):
    """Spawn `python -m kohakuengine.cli run <script>` end-to-end."""
    cmd = [sys.executable, "-m", "kohakuengine.cli", "run", str(simple_script)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "executed successfully" in result.stdout


def test_cli_main_version(capfd):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    out = capfd.readouterr().out
    assert "kogine" in out
