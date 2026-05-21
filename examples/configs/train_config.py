"""Training config -- bare-file style (Idea 1).

Just module-level variables. No ``def config_gen():``, no imports,
no ``Config()`` construction. The loader auto-captures these as
``Config.globals_dict``.
"""

learning_rate = 0.01
batch_size = 64
epochs = 3
device = "cuda"
