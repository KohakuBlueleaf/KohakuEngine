"""
Example: Running scripts with KohakuEngine from Python.

This demonstrates the flexibility of KohakuEngine:
- Config can be defined in the same file as the runner
- Use generators for parameter sweeps
- Simple, clean API
"""

from kohakuengine import Config, Flow, Script


def get_sweep_config():
    """
    Config generator for hyperparameter sweep.

    This shows that config logic can live anywhere - even in your runner script!
    """
    learning_rates = [0.001, 0.01, 0.1]
    batch_sizes = [16, 32, 64]

    for lr in learning_rates:
        for bs in batch_sizes:
            yield Config(
                globals_dict={
                    "learning_rate": lr,
                    "batch_size": bs,
                    "epochs": 2,  # Fewer epochs for sweep
                },
                metadata={"lr": lr, "bs": bs, "type": "sweep"},
            )


def run_single_script():
    """Run a single script with static config."""
    print("=== Example 1: Single Script ===\n")

    # Config defined right here!
    config = Config(
        globals_dict={"name": "KohakuEngine User", "greeting": "Hi"},
        kwargs={"excited": True},
    )

    script = Script("examples/scripts/hello.py", config=config)
    result = script.run()

    print(f"\nResult: {result}\n")


def run_with_config_file():
    """Run script with config from file."""
    print("=== Example 2: Config from File ===\n")

    config = Config.from_file("examples/configs/train_config.py")
    script = Script("examples/scripts/train_simple.py", config=config)

    result = script.run()
    print(f"\nResult: {result}\n")


def run_sweep_sequential():
    """Run parameter sweep sequentially."""
    print("=== Example 3: Sequential Sweep ===\n")

    # Config generator defined in this file!
    from kohakuengine.config.generator import ConfigGenerator

    config_gen = ConfigGenerator(get_sweep_config())

    script = Script("examples/scripts/train_simple.py", config=config_gen)

    # Sequential execution
    flow = Flow([script], mode="sequential")
    results = flow.run()

    print(f"\nCompleted {len(results)} training runs\n")


def run_sweep_parallel():
    """Run parameter sweep in parallel."""
    print("=== Example 4: Parallel Sweep ===\n")

    # Create separate script instances for each config
    scripts = []
    for config in get_sweep_config():
        scripts.append(Script("examples/scripts/train_simple.py", config=config))

    # Parallel execution with 4 workers
    flow = Flow(scripts, mode="parallel", max_workers=4, use_subprocess=True)
    results = flow.run()

    print(f"\nCompleted {len(results)} parallel training runs\n")


def run_workflow():
    """Run a multi-script workflow."""
    print("=== Example 5: Multi-Script Workflow ===\n")

    scripts = [
        Script(
            "examples/scripts/hello.py",
            config=Config(
                globals_dict={"name": "Workflow Step 1"},
                kwargs={"excited": False},
            ),
        ),
        Script(
            "examples/scripts/train_simple.py",
            config=Config(
                globals_dict={
                    "learning_rate": 0.005,
                    "batch_size": 48,
                    "epochs": 2,
                }
            ),
        ),
        Script(
            "examples/scripts/hello.py",
            config=Config(
                globals_dict={"name": "Workflow", "greeting": "Completed"},
                kwargs={"excited": True},
            ),
        ),
    ]

    flow = Flow(scripts, mode="sequential")
    results = flow.run()

    print(f"\nWorkflow completed with {len(results)} steps\n")


if __name__ == "__main__":
    print("=" * 60)
    print("KohakuEngine Examples")
    print("Demonstrating Config + Script + Flow")
    print("=" * 60)
    print()

    # Run examples
    run_single_script()
    run_with_config_file()
    run_sweep_sequential()

    # Uncomment to run parallel sweep (spawns multiple processes)
    # run_sweep_parallel()

    run_workflow()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
