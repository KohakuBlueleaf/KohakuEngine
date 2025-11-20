# KohakuEngine API Reference

Quick reference for KohakuEngine's Python API.

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from kohakuengine import run, Config, Script, Sequential

# Simple run
run('script.py', globals_dict={'lr': 0.001})

# With config file
run('script.py', config_path='config.py')
```

---

## Core Classes

### Config

Configuration dataclass for script execution.

```python
from kohakuengine import Config

config = Config(
    globals_dict={'learning_rate': 0.001, 'batch_size': 32},
    args=[],
    kwargs={'device': 'cuda'},
    metadata={'experiment': 'exp1'}
)
```

**Attributes:**
- `globals_dict: dict[str, Any]` - Module-level globals to inject
- `args: list[Any]` - Positional arguments for entrypoint
- `kwargs: dict[str, Any]` - Keyword arguments for entrypoint
- `metadata: dict[str, Any]` - Optional metadata

**Class Methods:**

#### `Config.from_globals()`

Create Config by automatically capturing caller's global variables. This is the **recommended** approach.

```python
from kohakuengine import Config

learning_rate = 0.01
batch_size = 64
epochs = 10

def config_gen():
    return Config.from_globals()  # Captures learning_rate, batch_size, epochs
```

- Skips private variables (starting with `_`)
- Skips modules, functions, and classes
- Use `use()` wrapper to include functions/classes

#### `Config.from_context()`

Create Config from a `capture_globals()` context.

```python
from kohakuengine import Config, capture_globals

with capture_globals() as ctx:
    import numpy as np
    learning_rate = 0.01
    _internal = "captured too"

def config_gen():
    return Config.from_context(ctx)  # Captures everything, including np and _internal
```

#### `Config.from_file()`

Load config from a Python config file.

```python
config = Config.from_file('config.py')
config = Config.from_file('config.py', worker_id=0)  # For parallel execution
```

---

### capture_globals()

Context manager to capture all variables defined within a block.

```python
from kohakuengine import capture_globals, Config

with capture_globals() as ctx:
    import math
    learning_rate = 0.01
    _private = "included"

    def helper():
        pass

def config_gen():
    return Config.from_context(ctx)
```

**Captures everything:** modules, functions, classes, private variables - no filtering.

---

### use()

Wrapper to mark functions/classes for inclusion in `from_globals()`.

```python
from kohakuengine import Config, use

learning_rate = 0.01

# Wrap functions/classes to include them
optimizer_class = use(torch.optim.Adam)
lr_schedule = use(lambda epoch: 0.01 * 0.95 ** epoch)

class MyModel:
    hidden_size = 256

model_config = use(MyModel)

def config_gen():
    return Config.from_globals()  # Includes wrapped items
```

---

### ConfigLoader

Load configs from Python files.

```python
from kohakuengine import ConfigLoader

# Load from file
config = ConfigLoader.load_config('config.py')

# Load from dict
config = ConfigLoader.load_from_dict({
    'globals': {'lr': 0.001},
    'kwargs': {'device': 'cuda'}
})
```

**Methods:**
- `load_config(path) -> Config | ConfigGenerator` - Load from Python file
- `load_from_dict(data) -> Config` - Create from dictionary

**Expected Config File Format:**
```python
from kohakuengine.config import Config

def config_gen():
    return Config(globals_dict={'lr': 0.001})
```

Or for generators:
```python
def config_gen():
    for lr in [0.001, 0.01, 0.1]:
        yield Config(globals_dict={'lr': lr})
```

---

### Script

Represents an executable Python script.

```python
from kohakuengine import Script, Config

script = Script(
    path='train.py',
    config=Config(globals_dict={'lr': 0.001}),
    entrypoint='main',  # Optional, auto-detected
    run_as_main=True    # Execute as __main__
)
```

**Attributes:**
- `path: str | Path` - Path to script
- `config: Config | ConfigGenerator | None` - Configuration
- `entrypoint: str | None` - Entrypoint function name
- `run_as_main: bool` - Execute as `__main__` process

**Properties:**
- `name: str` - Script name (filename without extension)

---

### ScriptExecutor

Execute scripts with configuration.

```python
from kohakuengine import Script, ScriptExecutor, Config

script = Script('train.py', config=Config(...))
executor = ScriptExecutor(script)
result = executor.execute()
```

**Methods:**
- `execute(config=None) -> Any` - Execute script with optional config override

**Properties:**
- `module: ModuleType | None` - Loaded module after execution

---

## Workflows

### Sequential

Execute scripts sequentially.

```python
from kohakuengine import Script, Sequential, ConfigLoader

scripts = [
    Script('preprocess.py', config=ConfigLoader.load_config('prep_config.py')),
    Script('train.py', config=ConfigLoader.load_config('train_config.py')),
    Script('evaluate.py', config=ConfigLoader.load_config('eval_config.py'))
]

workflow = Sequential(scripts)
results = workflow.run()  # Returns list of results
```

**Methods:**
- `run() -> list[Any]` - Execute all scripts in order
- `validate() -> bool` - Validate workflow configuration

---

### Parallel

Execute scripts in parallel using subprocesses.

```python
from kohakuengine import Script, Parallel, Config

scripts = [
    Script('train_model_a.py', config=Config(globals_dict={'model': 'resnet'})),
    Script('train_model_b.py', config=Config(globals_dict={'model': 'vit'})),
    Script('train_model_c.py', config=Config(globals_dict={'model': 'transformer'}))
]

workflow = Parallel(
    scripts,
    max_workers=3,
    use_subprocess=True  # True: subprocess, False: ProcessPoolExecutor
)
results = workflow.run()
```

**Arguments:**
- `scripts: list[Script]` - Scripts to execute
- `max_workers: int | None` - Max parallel workers (default: CPU count)
- `use_subprocess: bool` - Execution mode (default: True)

**Methods:**
- `run() -> list[Any]` - Execute all scripts in parallel

---

### Pipeline

Alias to Sequential (state passing planned for future).

```python
from kohakuengine import Pipeline

pipeline = Pipeline([script1, script2, script3])
results = pipeline.run()
```

---

## Convenience Functions

### run()

Execute a script with inline or file-based config.

```python
from kohakuengine import run

# With inline config
result = run(
    'train.py',
    globals_dict={'lr': 0.001, 'batch_size': 32},
    args=[],
    kwargs={'device': 'cuda'}
)

# With config file
result = run('train.py', config_path='config.py')

# No config
result = run('script.py')
```

**Arguments:**
- `script_path: str` - Path to script
- `config_path: str | None` - Path to config file
- `globals_dict: dict | None` - Global variables to inject
- `args: list | None` - Positional arguments
- `kwargs: dict | None` - Keyword arguments

**Returns:** Script execution result

---

## Advanced Usage

### Generator Configs for Sweeps

```python
from kohakuengine import Script, Sequential, ConfigLoader

# Config file with generator
# sweep_config.py:
# def config_gen():
#     for lr in [0.001, 0.01, 0.1]:
#         yield Config(globals_dict={'lr': lr})

config_gen = ConfigLoader.load_config('sweep_config.py')
script = Script('train.py', config=config_gen)

workflow = Sequential([script])
results = workflow.run()  # Runs 3 times with different LRs
```

### Generator with from_globals() Pattern

Use `from_globals()` as base config, then override specific values in a loop:

```python
from kohakuengine import Config

# Base configuration
learning_rate = 0.01
batch_size = 64
epochs = 10
optimizer = "adam"

def config_gen():
    # Get base from globals
    base = Config.from_globals()

    # Sweep over specific parameters
    for lr in [0.001, 0.01, 0.1]:
        for bs in [32, 64, 128]:
            sweep_globals = base.globals_dict.copy()
            sweep_globals["learning_rate"] = lr
            sweep_globals["batch_size"] = bs

            yield Config(
                globals_dict=sweep_globals,
                metadata={"lr": lr, "bs": bs}
            )
```

This pattern lets you define defaults as normal Python variables, then override only what changes.

### Multiple Different Scripts in Parallel

```python
from kohakuengine import Script, Parallel, ConfigLoader

scripts = [
    Script('download.py', config=ConfigLoader.load_config('download_config.py')),
    Script('preprocess.py', config=ConfigLoader.load_config('preprocess_config.py')),
    Script('validate.py', config=ConfigLoader.load_config('validate_config.py'))
]

workflow = Parallel(scripts, max_workers=3)
results = workflow.run()  # All run in parallel
```

### Mixing Static and Generator Configs

```python
from kohakuengine import Script, Sequential, Config, ConfigLoader

scripts = [
    Script('setup.py', config=Config(globals_dict={'env': 'prod'})),  # Static
    Script('train.py', config=ConfigLoader.load_config('sweep.py')),   # Generator
    Script('cleanup.py', config=Config(globals_dict={'clean': True}))  # Static
]

workflow = Sequential(scripts)
workflow.run()  # setup → train (multiple times) → cleanup
```

---

## CLI Reference

### Run Command

```bash
kogine run SCRIPT [--config CONFIG] [--entrypoint FUNC]
```

**Examples:**
```bash
kogine run train.py --config config.py
kogine run script.py --entrypoint custom_main
```

### Workflow Commands

**Sequential:**
```bash
kogine workflow sequential SCRIPT1 SCRIPT2 SCRIPT3 [--config CONFIG]
```

**Parallel:**
```bash
kogine workflow parallel SCRIPT1 SCRIPT2 SCRIPT3 [--config CONFIG] [--workers N] [--mode MODE]
```

**Options:**
- `--workers N` - Max parallel workers
- `--mode subprocess|pool` - Execution mode

**Examples:**
```bash
# Sequential
kogine workflow sequential prep.py train.py eval.py --config pipeline.py

# Parallel with 4 workers
kogine workflow parallel train.py --config sweep.py --workers 4

# Parallel pool mode
kogine workflow parallel script1.py script2.py script3.py --mode pool
```

### Config Commands

**Validate:**
```bash
kogine config validate CONFIG_FILE
```

**Show:**
```bash
kogine config show CONFIG_FILE
```

---

## Script Requirements

Your scripts should follow this pattern:

```python
# Global variables (will be overridden by config)
learning_rate = 0.001
batch_size = 32

def main(device='cpu', **kwargs):
    """Entrypoint function."""
    print(f"LR: {learning_rate}, BS: {batch_size}, Device: {device}")
    # Your code here
    return result

if __name__ == "__main__":
    main()
```

**Requirements:**
1. Define global variables at module level
2. Have an entrypoint function (auto-detected or specify with `entrypoint=`)
3. Call entrypoint in `if __name__ == "__main__"` block
4. Entrypoint can optionally accept args/kwargs

---

## Error Handling

```python
from kohakuengine import Script, ScriptExecutor

try:
    script = Script('train.py', config=config)
    executor = ScriptExecutor(script)
    result = executor.execute()
except FileNotFoundError:
    print("Script not found")
except ValueError as e:
    print(f"Configuration error: {e}")
except RuntimeError as e:
    print(f"Execution error: {e}")
```

---

## Best Practices

1. **Use config files** instead of inline configs for reproducibility
2. **Use generators** for parameter sweeps
3. **Use subprocess mode** for parallel execution (true isolation)
4. **Keep metadata** in configs for experiment tracking
5. **Test configs** with `kogine config validate` before running

---

## Examples

See `examples/` directory:
- `examples/scripts/` - Example scripts
- `examples/configs/` - Example configs
- `examples/workflows/` - Example workflows

Run the hello world example:
```bash
kogine run examples/scripts/hello.py --config examples/configs/hello_config.py
```

---

## See Also

- [GOAL.md](GOAL.md) - Project vision
- [PLAN.md](PLAN.md) - Architecture details
- [TODO.md](TODO.md) - Implementation status
- [README.md](../README.md) - Quick start guide
