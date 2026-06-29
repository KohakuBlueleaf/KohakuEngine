"""Nested config -- compose on top of another config with ``use_config``.

``use_config`` imports another config file *through the loader* and merges
its resolved values into this one. Your own top-level variables win over the
inherited ones; stack multiple calls to layer bases (later calls win).

Run::

    kogine config show examples/configs/nested_config.py
    kogine run examples/scripts/train_simple.py --config examples/configs/nested_config.py

A plain ``import base_hparams`` is intentionally blocked and would also drop
the inherited ``lr_schedule`` function and ``_metadata`` -- use ``use_config``.
"""

from kohakuengine import use_config

use_config("base_hparams.py")  # learning_rate, batch_size, epochs, device, lr_schedule

# Override what this experiment needs:
batch_size = 128
learning_rate = 0.05

# Add experiment-specific values / metadata (merged with the base's):
_metadata = {"experiment": "baseline-bs128", "owner": "kohaku"}
