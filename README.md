# KohakuEngine

**All-in-Python Configuration and Execution Engine for R&D Workloads**

Write configs as pure Python — no YAML, no JSON, often **no boilerplate at all**.
KohakuEngine takes your existing Python scripts and runs them with different
configurations without modifying your code: it imports the script, injects
global variables from your config, finds your entrypoint, and calls it.

```bash
pip install kohaku-engine
```

---

## A 30-second tour

**Your script** — unchanged:

```python
# train.py
learning_rate = 0.001
batch_size = 32
epochs = 10

def train():
    print(f"lr={learning_rate} bs={batch_size} epochs={epochs}")

if __name__ == "__main__":
    train()
```

**Your config** — just variables, no boilerplate:

```python
# config.py
learning_rate = 0.01
batch_size = 64
epochs = 5
```

**Run it**:

```bash
kogine run train.py --config config.py
# or:
kogine run train.py --set learning_rate=0.01 --set batch_size=64
```

That's it. No `Config(...)` construction, no `def config_gen():`, no imports
in the config file.

---

## Why KohakuEngine

R&D workflows live in the gap between "throw global variables at it" and
"set up a real config system." KohakuEngine *embraces* the global-variable
style and gives you proper machinery on top:

- **Python-first configs.** Computed values, functions, closures — anything
  Python can express, your config can express.
- **Non-invasive.** Works with scripts you already have. No refactor required.
- **Generators for sweeps.** A `_sweep` dict expands to a cartesian product;
  or write a `config_gen()` generator for irregular sweeps.
- **Parallel execution.** Subprocess-isolated workers for true `__main__`
  semantics across sweep iterations.
- **Config cells** (Idea 7). Mark a region of your script as configuration —
  Kogine evaluates it once and freezes the values into the module, so
  expensive setup runs at most once per script run (fork-mode-safe).

---

## Configs are just data

The minimum config file is **just variables**:

```python
# config.py
learning_rate = 0.01
batch_size = 64
```

Want positional args, kwargs, or metadata? Use the reserved underscore names:

```python
# config.py
learning_rate = 0.01
_args = []
_kwargs = {"resume_from": "ckpt.pt"}
_metadata = {"experiment": "baseline"}
```

Want to include a locally-defined function or class? Just define it — locally-
defined callables are captured automatically:

```python
# config.py
learning_rate = 0.01

def lr_schedule(epoch):
    return learning_rate * 0.95**epoch

class ModelConfig:
    hidden_size = 256
```

For **imported** callables/classes (which the loader can't disambiguate),
wrap with `use()`:

```python
# config.py
import math
from kohakuengine import use

loss_fn = use(math.sqrt)
```

---

## Sweeps

### Declarative grid (`_sweep`)

```python
# sweep.py
epochs = 5
_sweep = {
    "learning_rate": [0.001, 0.01, 0.1],
    "batch_size": [32, 64],
}
# expands to 6 configs (3 x 2)
```

### Paired (zip mode)

```python
_sweep = {
    "__mode__": "zip",
    "learning_rate": [0.001, 0.01, 0.1],
    "batch_size":    [32,    64,   128],
}
# expands to 3 configs (paired)
```

### From the CLI

```bash
kogine run train.py --sweep learning_rate=0.001,0.01,0.1 --sweep batch_size=32,64
```

### Generators for arbitrary sweeps

```python
# sweep.py
from kohakuengine import Config

def config_gen():
    for lr in [0.001, 0.01, 0.1]:
        yield Config(
            globals_dict={"learning_rate": lr},
            metadata={"lr": lr},
        )
```

---

## Entrypoint discovery (Idea 5)

Kogine tries, in priority order:

1. `--entrypoint NAME` CLI flag
2. `script.py:func` colon syntax
3. `@kogine.entrypoint` decorator (most explicit, least magic)
4. `if __name__ == "__main__":` AST detection
5. `main()` or `run()` by convention

The decorator removes all ambiguity:

```python
import kohakuengine as kogine

@kogine.entrypoint
def train():
    ...
```

---

## Config cells (Idea 7)

Mark a region of your script as configuration; Kogine evaluates it once
and freezes the resolved values into the module:

```python
# train.py
import torch
from data import load_huge_index

# %% kogine:config
learning_rate = 0.001
batch_size = 32
index = load_huge_index()   # expensive, runs at most once per script run
# %% kogine:script

def train():
    loader = DataLoader(index, batch_size=batch_size, num_workers=4)
    # Worker subprocesses that fork from this process inherit the
    # already-evaluated state -- load_huge_index() is NOT re-run.
    for batch in loader:
        ...

if __name__ == "__main__":
    train()
```

The cell is rewritten **in memory** — no temp file, tracebacks still point
at the original `train.py` line numbers, debuggers still work.

**Scope:** "evaluate once" applies per script run. A sweep over N configs is
N independent script runs (each evaluating its own cell once). Fork-mode
worker children inherit. Spawn-mode children re-import from disk and will
re-execute the cell — documented limitation.

---

## CLI overview

```bash
# Single run
kogine run script.py --config config.py
kogine run script.py --set lr=0.01 --set bs=64
kogine run script.py --sweep lr=0.001,0.01,0.1

# Sequential / parallel workflows
kogine workflow sequential a.py b.py c.py --config c.py
kogine workflow parallel train.py --config sweep.py --workers 4

# Config utilities
kogine config validate config.py            # syntax / shape check
kogine config show config.py                # lowered Config form
kogine config check script.py --config c.py # diff vs. script defaults, typo hints
```

`kogine config check` is especially useful — it warns about overrides that
don't match any script default (typos like `batch_sz` vs `batch_size`).

---

## Python API

```python
from kohakuengine import Config, Script, Flow, run

# One-shot convenience
run("train.py", globals_dict={"learning_rate": 0.01})

# Build it up
config = Config.from_file("config.py")
script = Script("train.py", config=config)
script.run()

# Workflow
flow = Flow([Script("train.py", config=c) for c in configs], mode="parallel", max_workers=4)
flow.run()
```

---

## Migration notes (v0.0.x → v0.2)

| Before                                                   | After                                       |
| -------------------------------------------------------- | ------------------------------------------- |
| `def config_gen(): return Config.from_globals()`         | *Delete it.* Bare files work.               |
| `lr_scheduler = use(local_func)`                         | `lr_scheduler = local_func` (no wrapper)    |
| `def config_gen(): for ...: yield Config(...)` for grids | `_sweep = {"lr": [...], "bs": [...]}`        |
| `Config(args=..., kwargs=...)` in `config_gen`           | `_args = ...`, `_kwargs = ...` at top level |
| `capture_globals()` context manager                      | Deprecated; emits warning. Removed in v0.3. |

Existing `def config_gen()` and `CONFIG = ...` patterns **continue to work
unchanged**. Migration is opt-in.

---

## Documentation

Full documentation lives in [`docs/`](docs/index.md):

- **Tutorials**
  - [Installation](docs/installation.md)
  - [Quickstart](docs/quickstart.md)
  - [Tutorial](docs/tutorial.md)
- **How-to guides**
  - [Bare config files](docs/guides/bare-configs.md)
  - [Config cells](docs/guides/config-cells.md)
  - [Hyperparameter sweeps](docs/guides/sweeps.md)
  - [Workflows](docs/guides/workflows.md)
  - [Entrypoint discovery](docs/guides/entrypoints.md)
  - [Overrides and validation](docs/guides/overrides-and-validation.md)
  - [Migration from earlier versions](docs/guides/migration.md)
- **Reference**
  - [Python API](docs/reference/api.md)
  - [Command line](docs/reference/cli.md)
- **Explanation**
  - [Concepts and design philosophy](docs/concepts.md)
  - [Architecture](docs/architecture.md)
- **Project**
  - [Contributing](docs/contributing.md)
  - [Changelog](docs/changelog.md)
  - [FAQ](docs/faq.md)

Historical design notes are kept under
[`plans/ux-redesign-v0.2/`](plans/ux-redesign-v0.2/) for reference.

## License

Apache-2.0
