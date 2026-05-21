"""Declarative grid sweep (Idea 4). Expands to 6 configs (3 x 2)."""

epochs = 5
device = "cpu"

_sweep = {
    "learning_rate": [0.001, 0.01, 0.1],
    "batch_size": [16, 64],
}
