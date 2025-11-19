"""Hyperparameter sweep config example."""

from kohakuengine.config import Config


def config_gen():
    """Generate configs for hyperparameter sweep."""
    learning_rates = [0.001, 0.01, 0.1]
    batch_sizes = [16, 32, 64]

    for lr in learning_rates:
        for bs in batch_sizes:
            yield Config(
                globals_dict={
                    "learning_rate": lr,
                    "batch_size": bs,
                    "epochs": 5,  # Fewer epochs for sweep
                },
                metadata={"sweep": "lr_bs", "lr": lr, "bs": bs},
            )
