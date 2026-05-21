"""Sequential workflow using bare-file configs (v0.2 style)."""

from pathlib import Path

from kohakuengine import Flow, Script, load_config_file

HERE = Path(__file__).parent.parent

hello_script = Script(
    str(HERE / "scripts" / "hello.py"),
    config=load_config_file(HERE / "configs" / "hello_config.py"),
)
train_script = Script(
    str(HERE / "scripts" / "train_simple.py"),
    config=load_config_file(HERE / "configs" / "train_config.py"),
)


def main():
    workflow = Flow([hello_script, train_script], mode="sequential")
    results = workflow.run()
    print(f"\nWorkflow completed with {len(results)} steps")
    print(f"Results: {results}")


if __name__ == "__main__":
    main()
