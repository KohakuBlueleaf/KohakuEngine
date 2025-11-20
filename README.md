# KohakuEngine

**All-in-Python Configuration and Execution Engine for R&D Workloads**

KohakuEngine bridges the gap between quick prototyping with global variables and production-ready configuration systems. Write configs as pure Python - no YAML, no JSON, just Python variables.

## How It Works

KohakuEngine takes your existing Python scripts and runs them with different configurations **without modifying your code**:

1. **Import your script** as a Python module
2. **Inject global variables** from your config
3. **Find and call your entrypoint** (the function in `if __name__ == "__main__"`)

Your script runs exactly as if you executed it directly, but with different configuration values!

## Features

- 🐍 **Python-First Configs**: Just define variables - `from_globals()` captures them automatically
- 🔧 **Include Anything**: Use `use()` to include functions, classes, objects in your config
- 🔄 **Iterative Workflows**: Generator-based configs for hyperparameter sweeps
- ⚡ **Non-Invasive**: Works with existing scripts - no refactoring required
- 🚀 **Parallel Execution**: Run multiple configs in parallel with subprocess isolation

## Quick Start

### Installation

```bash
pip install -e .
```

## Complete Example

### Step 1: Your Script (No Changes Needed!)

**File: `train.py`**
```python
# Global variables - will be overridden by config
learning_rate = 0.001
batch_size = 32
epochs = 10

def train():
    print(f"Training: LR={learning_rate}, BS={batch_size}, Epochs={epochs}")
    for epoch in range(epochs):
        loss = 1.0 / (epoch + 1)
        print(f"Epoch {epoch+1}/{epochs} - Loss: {loss:.4f}")
    return {"final_loss": loss}

if __name__ == "__main__":
    train()
```

### Step 2: Create a Config

**File: `config.py`** - Just define your variables!
```python
from kohakuengine import Config

# Define config as normal Python variables
learning_rate = 0.01
batch_size = 64
epochs = 5

def config_gen():
    return Config.from_globals()  # Automatically captures all variables!
```

That's it! No manual dict building. `from_globals()` captures everything.

### Step 3: Run It!

**Python API:**
```python
from kohakuengine import Config, Script

config = Config.from_file('config.py')
script = Script('train.py', config=config)
result = script.run()
```

**Command Line:**
```bash
kogine run train.py --config config.py
```

**Output:**
```
Training: LR=0.01, BS=64, Epochs=5
Epoch 1/5 - Loss: 1.0000
Epoch 2/5 - Loss: 0.5000
Epoch 3/5 - Loss: 0.3333
Epoch 4/5 - Loss: 0.2500
Epoch 5/5 - Loss: 0.2000
```

---

## Config Methods

### `from_globals()` - Auto-capture Variables (Recommended)

The simplest way - just define variables and call `from_globals()`:

```python
from kohakuengine import Config

learning_rate = 0.01
batch_size = 64
epochs = 5

def config_gen():
    return Config.from_globals()
```

### `use()` - Include Functions/Classes

By default, `from_globals()` skips functions and classes. Use `use()` to include them:

```python
from kohakuengine import Config, use
import torch

learning_rate = 0.01
batch_size = 64

# Wrap functions/classes to include them
optimizer = use(torch.optim.Adam)
model_class = use(MyModel)
loss_fn = use(lambda x, y: (x - y).pow(2).mean())

def config_gen():
    return Config.from_globals()
```

### `capture_globals()` - Context Manager

Capture everything defined within a block (including modules, functions, etc.):

```python
from kohakuengine import capture_globals, Config

with capture_globals() as ctx:
    import numpy as np
    learning_rate = 0.01
    batch_size = 64

def config_gen():
    return Config.from_context(ctx)
```

### Generator Configs - Hyperparameter Sweeps

Use generators to yield multiple configs:

```python
from kohakuengine import Config

def config_gen():
    for lr in [0.001, 0.01, 0.1]:
        for bs in [16, 32, 64]:
            yield Config(globals_dict={
                'learning_rate': lr,
                'batch_size': bs
            })
```

---

## Workflows

### Sequential Execution

```python
from kohakuengine import Config, Script, Flow

# Define configs using from_globals pattern
preprocess_config = Config(globals_dict={'input': 'data.csv', 'output': 'processed.csv'})
train_config = Config(globals_dict={'data': 'processed.csv', 'epochs': 50})
eval_config = Config(globals_dict={'model': 'model.pt'})

scripts = [
    Script('preprocess.py', config=preprocess_config),
    Script('train.py', config=train_config),
    Script('evaluate.py', config=eval_config),
]

flow = Flow(scripts, mode='sequential')
results = flow.run()
```

### Parallel Execution

Run multiple scripts or configs in parallel:

```python
from kohakuengine import Config, Script, Flow

# Same script with different configs
scripts = [
    Script('train.py', config=Config(globals_dict={'lr': 0.001})),
    Script('train.py', config=Config(globals_dict={'lr': 0.01})),
    Script('train.py', config=Config(globals_dict={'lr': 0.1})),
]

flow = Flow(scripts, mode='parallel', max_workers=3)
results = flow.run()
```

---

## CLI Reference

```bash
# Run single script
kogine run script.py --config config.py

# Sequential workflow
kogine workflow sequential script1.py script2.py --config config.py

# Parallel execution
kogine workflow parallel script.py --config sweep_config.py --workers 4
```

---

## Advanced: Manual Config Dict

For explicit control, you can still use the dict-based approach:

```python
from kohakuengine import Config

def config_gen():
    return Config(
        globals_dict={
            'learning_rate': 0.01,
            'batch_size': 64,
        },
        args=[],          # Positional args for entrypoint
        kwargs={},        # Keyword args for entrypoint
        metadata={}       # Optional tracking metadata
    )
```

---

## Documentation

- **[API.md](docs/API.md)** - Complete API reference
- **[GOAL.md](docs/GOAL.md)** - Project vision and objectives
- **[PLAN.md](docs/PLAN.md)** - Technical architecture and design
- **[TODO.md](docs/TODO.md)** - Implementation status and roadmap

## License

Apache-2.0
