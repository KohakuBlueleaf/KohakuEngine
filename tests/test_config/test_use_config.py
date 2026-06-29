"""Tests for nested-config composition via ``use_config`` (config import)."""

import pytest

from kohakuengine.config import Config, ConfigGenerator
from kohakuengine.config.loader import load_config_file


def test_inherits_and_overrides(make_config):
    make_config(
        "base.py",
        """
        lr = 0.1
        batch_size = 64
        model = "resnet"
        """,
    )
    child = make_config(
        "child.py",
        """
        from kohakuengine import use_config
        use_config("base.py")
        batch_size = 128   # override base
        epochs = 5         # new
        """,
    )
    cfg = load_config_file(child)
    assert isinstance(cfg, Config)
    assert cfg.globals_dict == {
        "lr": 0.1,  # inherited
        "batch_size": 128,  # child wins
        "model": "resnet",  # inherited
        "epochs": 5,  # child's own
    }


def test_inherits_local_function(make_config):
    # The key differentiator vs a plain import: a function defined in the base
    # config (its __module__ is the base file) is preserved, not dropped.
    make_config(
        "base.py",
        """
        lr = 0.1
        def schedule(epoch):
            return lr * 0.9 ** epoch
        """,
    )
    child = make_config(
        "child.py",
        """
        from kohakuengine import use_config
        use_config("base.py")
        """,
    )
    cfg = load_config_file(child)
    assert callable(cfg.globals_dict["schedule"])
    assert cfg.globals_dict["schedule"](0) == 0.1


def test_inherits_from_config_gen_base(make_config):
    # A base defined via config_gen() must resolve through the loader.
    make_config(
        "gen_base.py",
        """
        from kohakuengine import Config
        def config_gen():
            return Config(globals_dict={"opt": "adamw", "wd": 0.01})
        """,
    )
    child = make_config(
        "child.py",
        """
        from kohakuengine import use_config
        use_config("gen_base.py")
        wd = 0.05   # override
        """,
    )
    cfg = load_config_file(child)
    assert cfg.globals_dict == {"opt": "adamw", "wd": 0.05}


def test_layering_order_and_child_precedence(make_config):
    make_config("a.py", "x = 1\ny = 1\nz = 1\n")
    make_config("b.py", "y = 2\nz = 2\n")
    child = make_config(
        "child.py",
        """
        from kohakuengine import use_config
        use_config("a.py")
        use_config("b.py")   # later import wins over earlier
        z = 3                # child wins over all
        """,
    )
    cfg = load_config_file(child)
    assert cfg.globals_dict == {"x": 1, "y": 2, "z": 3}


def test_inherits_and_merges_meta(make_config):
    make_config(
        "base.py",
        """
        lr = 0.1
        _args = [1, 2]
        _kwargs = {"device": "cuda", "amp": True}
        _metadata = {"family": "baseline", "owner": "base"}
        """,
    )
    child = make_config(
        "child.py",
        """
        from kohakuengine import use_config
        use_config("base.py")
        _kwargs = {"amp": False}            # merges; child key wins
        _metadata = {"owner": "child"}      # merges; child key wins
        """,
    )
    cfg = load_config_file(child)
    assert cfg.args == [1, 2]  # inherited (child has none)
    assert cfg.kwargs == {"device": "cuda", "amp": False}
    assert cfg.metadata == {"family": "baseline", "owner": "child"}


def test_child_args_replace_inherited(make_config):
    make_config("base.py", "lr = 0.1\n_args = [1, 2]\n")
    child = make_config(
        "child.py",
        """
        from kohakuengine import use_config
        use_config("base.py")
        _args = [9]
        """,
    )
    cfg = load_config_file(child)
    assert cfg.args == [9]


def test_importing_sweep_raises(make_config):
    make_config("sweep_base.py", '_sweep = {"lr": [0.1, 0.2]}\n')
    child = make_config(
        "child.py",
        """
        from kohakuengine import use_config
        use_config("sweep_base.py")
        """,
    )
    with pytest.raises(TypeError, match="cannot import a sweep"):
        load_config_file(child)


def test_circular_use_config_raises(make_config):
    make_config(
        "cyc_a.py",
        'from kohakuengine import use_config\nuse_config("cyc_b.py")\n',
    )
    make_config(
        "cyc_b.py",
        'from kohakuengine import use_config\nuse_config("cyc_a.py")\n',
    )
    a = make_config(
        "start.py",
        'from kohakuengine import use_config\nuse_config("cyc_a.py")\n',
    )
    with pytest.raises(ValueError, match="Circular use_config"):
        load_config_file(a)


def test_sweep_child_inherits_base(make_config):
    make_config("base.py", 'lr = 0.1\nbatch_size = 64\nmodel = "resnet"\n')
    child = make_config(
        "child.py",
        """
        from kohakuengine import use_config
        use_config("base.py")
        _sweep = {"lr": [0.3, 0.5]}
        """,
    )
    cfg = load_config_file(child)
    assert isinstance(cfg, ConfigGenerator)
    configs = list(cfg)
    assert [c.globals_dict["lr"] for c in configs] == [0.3, 0.5]
    assert all(c.globals_dict["batch_size"] == 64 for c in configs)
    assert all(c.globals_dict["model"] == "resnet" for c in configs)


def test_return_value_usable_in_config_gen(make_config):
    make_config("base.py", 'lr = 0.1\nbatch_size = 64\nmodel = "resnet"\n')
    child = make_config(
        "child.py",
        """
        from kohakuengine import Config, use_config
        def config_gen():
            base = use_config("base.py")
            return Config(globals_dict={**base.globals_dict, "lr": 0.99})
        """,
    )
    cfg = load_config_file(child)
    assert cfg.globals_dict == {"lr": 0.99, "batch_size": 64, "model": "resnet"}


def test_relative_path_from_subdir(make_config, tmp_path):
    make_config("base.py", "lr = 0.1\nbatch_size = 64\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    child = sub / "child.py"
    child.write_text(
        'from kohakuengine import use_config\nuse_config("../base.py")\ntag = "sub"\n',
        encoding="utf-8",
    )
    cfg = load_config_file(child)
    assert cfg.globals_dict == {"lr": 0.1, "batch_size": 64, "tag": "sub"}
