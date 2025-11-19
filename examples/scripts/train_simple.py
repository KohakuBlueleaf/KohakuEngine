"""Simple training script example."""

# Global configuration variables
learning_rate = 0.001
batch_size = 32
epochs = 10
device = "cpu"


def train():
    """Simulate training."""
    print(f"Training with:")
    print(f"  Learning rate: {learning_rate}")
    print(f"  Batch size: {batch_size}")
    print(f"  Epochs: {epochs}")
    print(f"  Device: {device}")

    # Simulate training loop
    for epoch in range(epochs):
        loss = 1.0 / (epoch + 1)  # Fake decreasing loss
        print(f"Epoch {epoch+1}/{epochs} - Loss: {loss:.4f}")

    print("Training completed!")
    return {"final_loss": loss, "epochs": epochs}


if __name__ == "__main__":
    result = train()
