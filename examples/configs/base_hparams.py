"""Shared base hyperparameters, meant to be composed via ``use_config``.

This file is a normal bare config. Other configs inherit from it with::

    from kohakuengine import use_config
    use_config("base_hparams.py")

See ``nested_config.py`` in this directory for the consumer side.
"""

learning_rate = 0.01
batch_size = 64
epochs = 3
device = "cuda"


def lr_schedule(epoch: int) -> float:
    """Locally-defined helper -- inherited by ``use_config`` (a plain
    ``import`` would drop this, because its ``__module__`` is this file)."""
    return learning_rate * 0.95**epoch


_metadata = {"family": "baseline"}
