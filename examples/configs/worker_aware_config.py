"""Worker-aware config example for parallel execution."""

import os

from kohakuengine.config import Config


def config_gen(worker_id=None):
    """
    Config generator that adapts based on worker ID.

    Useful for:
    - Assigning different GPUs to different workers
    - Setting worker-specific random seeds
    - Creating worker-specific output directories
    """
    # Get worker_id from parameter or environment variable
    if worker_id is None:
        worker_id = int(os.environ.get("KOGINE_WORKER_ID", 0))

    # Assign GPU based on worker_id (cycle through 4 GPUs)
    device = f"cuda:{worker_id % 4}"

    # Worker-specific output directory
    output_dir = f"./output/worker_{worker_id}"

    # Worker-specific random seed
    seed = 42 + worker_id

    return Config(
        globals_dict={
            "device": device,
            "output_dir": output_dir,
            "random_seed": seed,
            "learning_rate": 0.001,
            "batch_size": 32,
            "epochs": 10,
        },
        metadata={"worker_id": worker_id},
    )
