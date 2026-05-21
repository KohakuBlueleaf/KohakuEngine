"""Sweep workflow -- runs train_simple.py over a grid of hyperparameters."""

from pathlib import Path

from kohakuengine import Flow, Script, load_config_file

HERE = Path(__file__).parent.parent


def main():
    sweep_config = load_config_file(HERE / "configs" / "sweep_config.py")
    script = Script(
        str(HERE / "scripts" / "train_simple.py"),
        config=sweep_config,
    )
    workflow = Flow([script], mode="parallel", max_workers=2)
    results = workflow.run()
    print(f"\nSweep completed -- {len(results)} runs")


if __name__ == "__main__":
    main()
