# KohakuEngine

**All-in-Python Configuration and Execution Engine for R&D Workloads**

KohakuEngine bridges the gap between quick prototyping with global variables and production-ready configuration systems. It's designed for researchers and engineers who want flexibility without sacrificing structure.

## Features

- 🐍 **Python-First Configs**: Use full Python in your configs - objects, classes, computed values, anything
- 🔄 **Iterative Workflows**: Generator-based configs for hyperparameter sweeps and dynamic configurations
- ⚡ **Non-Invasive**: Works with existing scripts - no refactoring required
- 🔧 **Flexible Execution**: Sequential and parallel workflows with subprocess isolation
- 🎯 **Dual Interface**: Both Python API and CLI for maximum flexibility

## Quick Start

### Installation

```bash
# Install in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"
```

### Basic Usage

**Your Script** (`train.py`):
```python
# Global variables (will be overridden by config)
learning_rate = 0.001
batch_size = 32

def main(device='cpu'):
    print(f"Training with LR={learning_rate}, BS={batch_size}, Device={device}")
    # Your training code here...
    return {'loss': 0.5}

if __name__ == "__main__":
    main()
```

**Your Config** (`config.py`):
```python
from kohakuengine.config import Config

def config_gen():
    return Config(
        globals_dict={'learning_rate': 0.01, 'batch_size': 64},
        kwargs={'device': 'cuda'}
    )
```

#### Python API

```python
from kohakuengine import Config, Script, Flow, run

# Quick run with inline config
run('train.py', globals_dict={'learning_rate': 0.001, 'batch_size': 32})

# Or use a config file
config = Config.from_file('config.py')
script = Script('train.py', config=config)
result = script.run()

# Or even simpler
run('train.py', config_path='config.py')

# Specify custom entrypoint
script = Script('train.py:custom_main', config=config)
result = script.run()
```

#### CLI

```bash
# Run a single script
kogine run train.py --config config.py

# Sequential workflow
kogine workflow sequential preprocess.py train.py --config config.py

# Parallel execution
kogine workflow parallel train.py --config sweep_config.py --workers 4
```

## Examples

### Quick Start Examples

**Single Script:**
```python
from kohakuengine import Config, Script

config = Config.from_file('config.py')
script = Script('train.py', config=config)
result = script.run()
```

**Workflow:**
```python
from kohakuengine import Config, Script, Flow

scripts = [
    Script('preprocess.py', config=Config.from_file('prep_config.py')),
    Script('train.py', config=Config.from_file('train_config.py')),
]

flow = Flow(scripts, mode='sequential')
results = flow.run()
```

**Parallel Sweep:**
```python
from kohakuengine import Config, Script, Flow

# Create scripts with different configs
scripts = [
    Script('train.py', config=Config(globals_dict={'lr': 0.001})),
    Script('train.py', config=Config(globals_dict={'lr': 0.01})),
    Script('train.py', config=Config(globals_dict={'lr': 0.1})),
]

flow = Flow(scripts, mode='parallel', max_workers=3)
results = flow.run()
```

### Try It

Run the comprehensive example:
```bash
python examples/run_scripts.py
```

Or try the hello world:
```bash
kogine run examples/scripts/hello.py --config examples/configs/hello_config.py
```

## Documentation

- **[API.md](docs/API.md)** - Complete API reference
- **[GOAL.md](docs/GOAL.md)** - Project vision and objectives
- **[PLAN.md](docs/PLAN.md)** - Technical architecture and design
- **[TODO.md](docs/TODO.md)** - Implementation status and roadmap

## License

Apache-2.0