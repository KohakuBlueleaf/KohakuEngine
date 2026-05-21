"""Explicit ``config_gen()`` style -- fully supported (back-compat path)."""

from kohakuengine import Config


def config_gen():
    return Config(
        globals_dict={"learning_rate": 0.05, "batch_size": 64},
        kwargs={"device": "cuda"},
        metadata={"experiment": "baseline"},
    )
