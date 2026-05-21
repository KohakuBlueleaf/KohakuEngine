"""Forwarding *imported* callables/classes via use() (Idea 2 gotcha).

Locally-defined functions are captured automatically. But aliases of
imported objects (``__module__`` is not this file) need to be wrapped
in ``use()`` so the loader knows to include them.
"""

import math
import json

from kohakuengine import use

learning_rate = 0.01

# Imported callables -- need use():
loss_fn = use(math.sqrt)
parser = use(json.loads)
