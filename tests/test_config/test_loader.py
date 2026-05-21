"""Tests for kohakuengine.config.loader."""

import pytest

from kohakuengine.config import Config, ConfigGenerator, ConfigLoader
from kohakuengine.config.loader import load_config_file, load_from_dict


def test_load_explicit_config_gen(make_config):
    p = make_config(
        "c.py",
        """
        from kohakuengine.config import Config
        def config_gen():
            return Config(globals_dict={"x": 1})
        """,
    )
    cfg = load_config_file(p)
    assert isinstance(cfg, Config)
    assert cfg.globals_dict == {"x": 1}


def test_load_config_gen_generator(make_config):
    p = make_config(
        "c.py",
        """
        from kohakuengine.config import Config
        def config_gen():
            for i in range(3):
                yield Config(globals_dict={"i": i})
        """,
    )
    cfg = load_config_file(p)
    assert isinstance(cfg, ConfigGenerator)
    items = list(cfg)
    assert [c.globals_dict["i"] for c in items] == [0, 1, 2]


def test_load_config_gen_with_worker_id(make_config):
    p = make_config(
        "c.py",
        """
        from kohakuengine.config import Config
        def config_gen(worker_id=None):
            return Config(globals_dict={"wid": worker_id})
        """,
    )
    cfg = load_config_file(p, worker_id=7)
    assert cfg.globals_dict == {"wid": 7}


def test_load_config_gen_must_be_callable(make_config):
    p = make_config("c.py", "config_gen = 42")
    with pytest.raises(ValueError, match="callable"):
        load_config_file(p)


def test_load_config_gen_wrong_return_type(make_config):
    p = make_config("c.py", "def config_gen(): return 42")
    with pytest.raises(ValueError, match="must return Config"):
        load_config_file(p)


def test_load_CONFIG_variable(make_config):
    p = make_config(
        "c.py",
        """
        from kohakuengine.config import Config
        CONFIG = Config(globals_dict={"a": 1})
        """,
    )
    cfg = load_config_file(p)
    assert isinstance(cfg, Config)
    assert cfg.globals_dict == {"a": 1}


def test_load_CONFIG_wrong_type(make_config):
    p = make_config("c.py", "CONFIG = 42")
    with pytest.raises(ValueError, match="Config instance"):
        load_config_file(p)


def test_load_bare_file(make_config):
    p = make_config(
        "c.py",
        """
        lr = 0.1
        bs = 32
        """,
    )
    cfg = load_config_file(p)
    assert isinstance(cfg, Config)
    assert cfg.globals_dict == {"lr": 0.1, "bs": 32}


def test_load_bare_file_with_meta(make_config):
    p = make_config(
        "c.py",
        """
        lr = 0.1
        _args = [1, 2]
        _kwargs = {"device": "cuda"}
        _metadata = {"tag": "x"}
        """,
    )
    cfg = load_config_file(p)
    assert cfg.globals_dict == {"lr": 0.1}
    assert cfg.args == [1, 2]
    assert cfg.kwargs == {"device": "cuda"}
    assert cfg.metadata == {"tag": "x"}


def test_load_bare_file_meta_type_errors(make_config):
    for line, kind in [
        ("_args = 5", "_args"),
        ("_kwargs = 5", "_kwargs"),
        ("_metadata = 5", "_metadata"),
    ]:
        p = make_config(f"{kind}.py", f"x=1\n{line}\n")
        with pytest.raises(TypeError, match=kind):
            load_config_file(p)


def test_load_bare_file_local_function_captured(make_config):
    p = make_config(
        "c.py",
        """
        def schedule(epoch):
            return 0.1 * 0.9 ** epoch
        """,
    )
    cfg = load_config_file(p)
    assert "schedule" in cfg.globals_dict
    assert callable(cfg.globals_dict["schedule"])


def test_load_sweep_grid(make_config):
    p = make_config(
        "c.py",
        """
        epochs = 5
        _sweep = {"lr": [0.001, 0.01], "bs": [32, 64]}
        """,
    )
    cfg = load_config_file(p)
    assert isinstance(cfg, ConfigGenerator)
    items = list(cfg)
    assert len(items) == 4  # 2 * 2
    combos = {(c.globals_dict["lr"], c.globals_dict["bs"]) for c in items}
    assert combos == {(0.001, 32), (0.001, 64), (0.01, 32), (0.01, 64)}
    # Every config carries the base "epochs"
    assert all(c.globals_dict["epochs"] == 5 for c in items)
    # Metadata carries the swept axes
    assert all("lr" in c.metadata and "bs" in c.metadata for c in items)


def test_load_sweep_zip(make_config):
    p = make_config(
        "c.py",
        """
        _sweep = {
            "__mode__": "zip",
            "lr": [0.001, 0.01, 0.1],
            "bs": [32, 64, 128],
        }
        """,
    )
    items = list(load_config_file(p))
    assert len(items) == 3
    assert [c.globals_dict["lr"] for c in items] == [0.001, 0.01, 0.1]
    assert [c.globals_dict["bs"] for c in items] == [32, 64, 128]


def test_load_sweep_empty(make_config):
    p = make_config(
        "c.py",
        """
        epochs = 5
        _sweep = {}
        """,
    )
    items = list(load_config_file(p))
    assert len(items) == 1
    assert items[0].globals_dict == {"epochs": 5}


def test_load_sweep_wrong_mode(make_config):
    p = make_config("c.py", '_sweep = {"__mode__": "bogus", "x": [1]}')
    with pytest.raises(ValueError, match="Unknown _sweep mode"):
        list(load_config_file(p))


def test_load_sweep_axis_not_iterable(make_config):
    p = make_config("c.py", "_sweep = {'x': 5}")
    with pytest.raises(TypeError, match="x"):
        load_config_file(p)


def test_load_sweep_must_be_dict(make_config):
    p = make_config("c.py", "_sweep = [1, 2]")
    with pytest.raises(TypeError, match="dict"):
        load_config_file(p)


def test_load_sweep_zip_length_mismatch(make_config):
    p = make_config(
        "c.py",
        '_sweep = {"__mode__": "zip", "a": [1, 2], "b": [1, 2, 3]}',
    )
    with pytest.raises(ValueError, match="equal-length"):
        load_config_file(p)


def test_load_sweep_warns_when_config_gen_present(make_config, recwarn):
    p = make_config(
        "c.py",
        """
        from kohakuengine.config import Config
        def config_gen():
            return Config(globals_dict={"x": 1})
        _sweep = {"a": [1]}
        """,
    )
    load_config_file(p)
    assert any("_sweep" in str(w.message) for w in recwarn.list)


def test_load_sweep_warns_when_CONFIG_present(make_config, recwarn):
    p = make_config(
        "c.py",
        """
        from kohakuengine.config import Config
        CONFIG = Config(globals_dict={"x": 1})
        _sweep = {"a": [1]}
        """,
    )
    load_config_file(p)
    assert any("_sweep" in str(w.message) for w in recwarn.list)


def test_load_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_config_file("/does/not/exist.py")


def test_load_from_dict():
    cfg = load_from_dict({"globals": {"lr": 0.1}, "kwargs": {"d": "cuda"}})
    assert cfg.globals_dict == {"lr": 0.1}
    assert cfg.kwargs == {"d": "cuda"}


def test_load_from_dict_defaults():
    cfg = load_from_dict({})
    assert cfg.globals_dict == {} and cfg.args == [] and cfg.kwargs == {}


def test_loader_facade(make_config):
    p = make_config("c.py", "x = 1")
    cfg = ConfigLoader.load_config(p)
    assert cfg.globals_dict == {"x": 1}


def test_loader_facade_from_dict():
    cfg = ConfigLoader.load_from_dict({"globals": {"y": 2}})
    assert cfg.globals_dict == {"y": 2}


def test_loader_propagates_module_exec_error(make_config):
    p = make_config("c.py", "raise RuntimeError('boom')")
    with pytest.raises(RuntimeError, match="boom"):
        load_config_file(p)


def test_config_from_file_attached(make_config):
    p = make_config("c.py", "x = 9")
    cfg = Config.from_file(p)
    assert cfg.globals_dict == {"x": 9}


def test_config_from_dict_attached():
    cfg = Config.from_dict({"globals": {"k": "v"}})
    assert cfg.globals_dict == {"k": "v"}
