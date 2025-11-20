"""Example config using use() to include functions and classes."""

from kohakuengine import Config, use

# Regular data variables (captured automatically)
learning_rate = 0.01
batch_size = 64
epochs = 10


# Define a custom function
def custom_lr_schedule(epoch, base_lr):
    """Custom learning rate schedule."""
    if epoch < 5:
        return base_lr * (epoch + 1) / 5
    return base_lr * 0.95 ** (epoch - 5)


# Define a custom class
class ModelConfig:
    hidden_size = 256
    num_layers = 4
    dropout = 0.1


# Use use() to include functions and classes in config
lr_scheduler = use(custom_lr_schedule)
model_config = use(ModelConfig)

# You can also use lambdas
loss_weight = use(lambda x: x**2)


def config_gen():
    """Config generator that includes functions and classes."""
    return Config.from_globals()
