"""Simple config for hello.py example."""

from kohakuengine.config import Config


def config_gen():
    """Generate config for hello script."""
    return Config(
        globals_dict={"name": "KohakuEngine", "greeting": "Welcome to"},
        kwargs={"excited": True},
    )
