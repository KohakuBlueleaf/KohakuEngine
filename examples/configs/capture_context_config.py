"""Example config using capture_globals() context manager."""

from kohakuengine import Config, capture_globals

# capture_globals captures EVERYTHING in the context - modules, functions, classes
with capture_globals() as ctx:
    import math

    learning_rate = 0.01
    batch_size = 64

    # Functions are captured too
    def compute_lr(step):
        return learning_rate * math.cos(step * math.pi / 1000)

    # Even private variables
    _internal_state = {"initialized": True}


def config_gen():
    """Config generator using captured context."""
    return Config.from_context(ctx)
