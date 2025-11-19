# KohakuEngine

**All-in-Python Configuration and Execution Engine for R&D Workloads**

KohakuEngine bridges the gap between quick prototyping with global variables and production-ready configuration systems. It's designed for researchers and engineers who want flexibility without sacrificing structure.

## How It Works

KohakuEngine takes your existing Python scripts and runs them with different configurations **without modifying your code**. It works by:

1. **Importing your script** as a Python module
2. **Injecting global variables** from your config (using `setattr`)
3. **Finding and calling your entrypoint** (the function in `if __name__ == "__main__"`)
4. **Passing arguments** to your entrypoint if specified

### The Magic

Your script runs **exactly as if you executed it directly**, but with different configuration values. No code changes needed!

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

## Complete Example

Let's see a complete example with all files and their contents:

### Step 1: Your Original Script

**File: `train.py`** (no changes needed!)
```python
# Global variables - these will be overridden by KohakuEngine
learning_rate = 0.001
batch_size = 32
epochs = 10
device = "cpu"

def train():
    """Your training logic."""
    print(f"Training with:")
    print(f"  LR: {learning_rate}")
    print(f"  Batch Size: {batch_size}")
    print(f"  Epochs: {epochs}")
    print(f"  Device: {device}")

    # Your actual training code here
    for epoch in range(epochs):
        loss = 1.0 / (epoch + 1)
        print(f"Epoch {epoch+1}/{epochs} - Loss: {loss:.4f}")

    return {"final_loss": loss, "epochs": epochs}

if __name__ == "__main__":
    result = train()
    print(f"Training complete: {result}")
```

### Step 2: Create a Config File

**File: `config.py`**
```python
from kohakuengine.config import Config

def config_gen():
    """
    This function returns a Config object.
    KohakuEngine will call this function to get your configuration.
    """
    return Config(
        # These values override the global variables in train.py
        globals_dict={
            'learning_rate': 0.01,    # Override: 0.001 -> 0.01
            'batch_size': 64,          # Override: 32 -> 64
            'epochs': 5,               # Override: 10 -> 5
            'device': 'cuda',          # Override: 'cpu' -> 'cuda'
        }
    )
```

### Step 3: Run It!

**Option A: Python API**
```python
from kohakuengine import Config, Script

# Load config and create script
config = Config.from_file('config.py')
script = Script('train.py', config=config)

# Run it!
result = script.run()
print(f"Result: {result}")
```

**Option B: Command Line**
```bash
kogine run train.py --config config.py
```

### What Happens?

1. **KohakuEngine loads `train.py`** as a Python module
2. **Injects new values** into global variables:
   - `learning_rate = 0.01` (was 0.001)
   - `batch_size = 64` (was 32)
   - `epochs = 5` (was 10)
   - `device = 'cuda'` (was 'cpu')
3. **Finds the entrypoint**: Detects `train()` is called in `if __name__ == "__main__"`
4. **Calls `train()`**: Executes your function with the new config values
5. **Returns the result**: `{"final_loss": 0.2, "epochs": 5}`

**Output:**
```
Training with:
  LR: 0.01
  Batch Size: 64
  Epochs: 5
  Device: cuda
Epoch 1/5 - Loss: 1.0000
Epoch 2/5 - Loss: 0.5000
Epoch 3/5 - Loss: 0.3333
Epoch 4/5 - Loss: 0.2500
Epoch 5/5 - Loss: 0.2000
Training complete: {'final_loss': 0.2, 'epochs': 5}
```

---

## Advanced Example: Multi-Script Workflow

Now let's see a complete pipeline with multiple scripts:

### The Scripts

**File: `preprocess.py`**
```python
input_file = "data.csv"
output_file = "processed.csv"

def preprocess():
    print(f"Preprocessing {input_file} -> {output_file}")
    # Your preprocessing code
    return {"status": "success", "output": output_file}

if __name__ == "__main__":
    preprocess()
```

**File: `train.py`**
```python
data_file = "processed.csv"
model_output = "model.pt"
epochs = 10

def train():
    print(f"Training on {data_file} for {epochs} epochs")
    print(f"Saving model to {model_output}")
    # Your training code
    return {"model": model_output, "loss": 0.15}

if __name__ == "__main__":
    train()
```

**File: `evaluate.py`**
```python
model_file = "model.pt"
test_data = "test.csv"

def evaluate():
    print(f"Evaluating {model_file} on {test_data}")
    # Your evaluation code
    return {"accuracy": 0.95}

if __name__ == "__main__":
    evaluate()
```

### The Workflow Config

**File: `pipeline_config.py`**
```python
from kohakuengine.config import Config

# Different configs for each stage
preprocess_config = Config(
    globals_dict={
        'input_file': 'raw_data.csv',
        'output_file': 'cleaned_data.csv'
    }
)

train_config = Config(
    globals_dict={
        'data_file': 'cleaned_data.csv',
        'model_output': 'best_model.pt',
        'epochs': 50
    }
)

eval_config = Config(
    globals_dict={
        'model_file': 'best_model.pt',
        'test_data': 'test_set.csv'
    }
)
```

### Run the Pipeline

```python
from kohakuengine import Script, Flow

# Create workflow
scripts = [
    Script('preprocess.py', config=preprocess_config),
    Script('train.py', config=train_config),
    Script('evaluate.py', config=eval_config),
]

# Run sequentially
flow = Flow(scripts, mode='sequential')
results = flow.run()

print(f"Pipeline completed!")
print(f"Preprocess: {results[0]}")
print(f"Train: {results[1]}")
print(f"Evaluate: {results[2]}")
```

**What Happens?**

1. **Preprocess runs** with `input_file='raw_data.csv'`, `output_file='cleaned_data.csv'`
2. **Train runs** with `data_file='cleaned_data.csv'`, `epochs=50`, saves to `best_model.pt`
3. **Evaluate runs** with `model_file='best_model.pt'`, tests on `test_set.csv`

All scripts run in sequence, each with its own configuration!

---

## Documentation

- **[API.md](docs/API.md)** - Complete API reference
- **[GOAL.md](docs/GOAL.md)** - Project vision and objectives
- **[PLAN.md](docs/PLAN.md)** - Technical architecture and design
- **[TODO.md](docs/TODO.md)** - Implementation status and roadmap

## License

Apache-2.0