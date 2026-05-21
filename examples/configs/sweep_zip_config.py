"""Paired (zip-mode) sweep (Idea 4). Expands to 3 configs."""

epochs = 5

_sweep = {
    "__mode__": "zip",
    "learning_rate": [0.001, 0.01, 0.1],
    "batch_size": [32, 64, 128],
}
