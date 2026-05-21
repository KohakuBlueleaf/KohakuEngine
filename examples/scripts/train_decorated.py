"""Training script using the @kogine.entrypoint decorator (Idea 6).

No ``if __name__ == "__main__":`` clause required -- the decorator
is the explicit, unambiguous entrypoint marker.
"""

import kohakuengine as kogine

learning_rate = 0.001
batch_size = 32


def helper():
    return "not the entrypoint"


@kogine.entrypoint
def train():
    print(f"lr={learning_rate} bs={batch_size}")
    return {"lr": learning_rate, "bs": batch_size}
