"""Toy training script. Defaults at top; entrypoint at bottom."""

learning_rate = 0.001
batch_size = 32
epochs = 10
device = "cpu"


def train():
    print(f"Training: lr={learning_rate} bs={batch_size} epochs={epochs} dev={device}")
    loss = 1.0
    for epoch in range(epochs):
        loss = 1.0 / (epoch + 1)
        print(f"  epoch {epoch + 1}/{epochs} loss={loss:.4f}")
    return {"final_loss": loss, "epochs": epochs}


if __name__ == "__main__":
    train()
