"""Training script with a config cell (Idea 7).

The cell freezes its values *once per script run* so that any worker
forked from this process (DataLoader on Linux, etc.) sees the same
values without re-executing ``load_index()``.
"""

# Heavy import is fine -- imports run normally outside the cell.
import time


def load_index() -> dict:
    """Pretend this is an 8-second startup hit."""
    print("[load_index] -- expensive setup -- runs at most once per script run")
    time.sleep(0.05)
    return {"docs": list(range(1000))}


# %% kogine:config
learning_rate = 0.001
batch_size = 32
index = load_index()
# %% kogine:script


def train():
    print(f"lr={learning_rate} bs={batch_size} index_size={len(index['docs'])}")
    return {"lr": learning_rate, "bs": batch_size}


if __name__ == "__main__":
    train()
