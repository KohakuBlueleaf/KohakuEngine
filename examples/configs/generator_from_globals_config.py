"""Example config using from_globals() with generator pattern for sweeps."""

from kohakuengine import Config

# Base configuration - define defaults
learning_rate = 0.01
batch_size = 64
epochs = 10
optimizer = "adam"
device = "cuda"

# Computed values
warmup_steps = epochs // 5


def config_gen():
    """Config generator that uses from_globals() as base, then overrides specific values."""
    # Get base config from globals
    base = Config.from_globals()

    # Sweep over learning rates and batch sizes
    for lr in [0.001, 0.01, 0.1]:
        for bs in [32, 64, 128]:
            # Copy base globals and override
            sweep_globals = base.globals_dict.copy()
            sweep_globals["learning_rate"] = lr
            sweep_globals["batch_size"] = bs

            yield Config(globals_dict=sweep_globals, metadata={"lr": lr, "bs": bs})
