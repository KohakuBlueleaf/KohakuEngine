"""Simple workflow example using simplified API."""

from kohakuengine import Config, Flow, Script

# Load configs from files using Config.from_file()
hello_config = Config.from_file("examples/configs/hello_config.py")
train_config = Config.from_file("examples/configs/train_config.py")

# Define scripts with configs
hello_script = Script("examples/scripts/hello.py", config=hello_config)
train_script = Script("examples/scripts/train_simple.py", config=train_config)

# Create and run workflow
if __name__ == "__main__":
    # Use Flow with sequential mode
    workflow = Flow([hello_script, train_script], mode="sequential")
    results = workflow.run()

    print(f"\nWorkflow completed with {len(results)} steps")
    print(f"Results: {results}")
