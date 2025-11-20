"""Example config using from_globals() - the recommended approach."""

from kohakuengine import Config

# Just define your variables as normal Python code
learning_rate = 0.01
batch_size = 64
epochs = 10
device = "cuda"

# Computed values work too!
warmup_steps = epochs // 5
effective_batch_size = batch_size * 4  # For gradient accumulation


def config_gen():
    """Config generator using from_globals()."""
    return Config.from_globals()
