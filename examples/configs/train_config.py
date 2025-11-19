"""Training config for train_simple.py example."""

from kohakuengine.config import Config


def config_gen():
    """Generate config for training script."""
    return Config(
        globals_dict={
            "learning_rate": 0.01,
            "batch_size": 64,
            "epochs": 3,
            "device": "cuda",
        }
    )
