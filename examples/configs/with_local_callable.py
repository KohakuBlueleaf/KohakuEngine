"""Locally-defined callables and classes are captured automatically (Idea 2).

No ``use()`` wrapper needed -- the loader detects ``__module__`` is this
config file. For *imported* callables you still need ``use()`` (see
``with_use.py``).
"""

learning_rate = 0.01


def lr_schedule(epoch: int) -> float:
    return learning_rate * 0.95**epoch


class ModelConfig:
    hidden_size = 256
    num_layers = 4
