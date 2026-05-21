# Tutorial

A progressive walk-through of KohakuEngine. By the end you will have used
every major feature: bare configs, declarative sweeps, the `@entrypoint`
decorator, config cells, workflows, the pre-flight checker, and the
Python API.

This tutorial assumes you have completed [Installation](installation.md).

## Part 1 — Configs as data

### A script with knobs

Create `train.py`:

```python
# train.py
learning_rate = 0.001
batch_size = 32
epochs = 10
device = "cpu"


def train():
    print(f"lr={learning_rate} bs={batch_size} epochs={epochs} device={device}")
    return {"learning_rate": learning_rate, "epochs": epochs}


if __name__ == "__main__":
    train()
```

The module-level variables are the script's *configurable surface*.
KohakuEngine will treat any of them as a knob the user can turn.

### Bare config files

Create `config.py`:

```python
# config.py
learning_rate = 0.05
batch_size = 128
epochs = 5
```

That is the whole file. No imports, no decorators, no `Config(...)`
constructor.

Run it:

```bash
kogine run train.py --config config.py
```

The loader walks the config module's globals, builds a `Config` for you,
and the executor injects those values into `train.py` before calling
`train()`.

### Extra arguments via underscore names

If your entrypoint takes positional or keyword arguments, declare them
with the reserved names `_args`, `_kwargs`, `_metadata`:

```python
# config.py
learning_rate = 0.05
batch_size = 128
_args = []
_kwargs = {"resume_from": "ckpt-007.pt"}
_metadata = {"experiment": "baseline-128"}
```

The underscore prefix keeps them out of `globals_dict`; the loader pulls
them into the corresponding `Config` fields.

## Part 2 — Local helpers and imported callables

Suppose your config needs a learning-rate schedule defined in the same
file:

```python
# config.py
learning_rate = 0.01


def lr_schedule(epoch: int) -> float:
    return learning_rate * 0.95**epoch


class ModelConfig:
    hidden_size = 256
    num_layers = 4
```

Both `lr_schedule` and `ModelConfig` are captured automatically. The
loader inspects each object's `__module__` attribute — if the object is
defined in *this* file, it is included as configuration data.

For **imported** callables and classes, wrap with `use()` so the loader
knows you want them forwarded as data:

```python
# config.py
import math

from kohakuengine import use


loss_fn = use(math.sqrt)
```

Without `use()`, `loss_fn` would be skipped because its `__module__` is
`"math"`, not your config file's module name.

## Part 3 — Hyperparameter sweeps

### Declarative grid

A declarative cartesian product:

```python
# sweep.py
epochs = 5
device = "cpu"

_sweep = {
    "learning_rate": [0.001, 0.01, 0.1],
    "batch_size":    [32, 64],
}
```

This expands to six `Config` instances and the script runs once per
combination.

```bash
kogine run train.py --config sweep.py
```

### Paired (zip) sweep

When two axes vary together:

```python
# sweep.py
_sweep = {
    "__mode__":      "zip",
    "learning_rate": [0.001, 0.01, 0.1],
    "batch_size":    [32,    64,   128],
}
```

This produces exactly three runs, paired element-wise.

### Sweeps from the CLI

For ad-hoc sweeps you do not need a file at all:

```bash
kogine run train.py --sweep learning_rate=0.001,0.01,0.1 --sweep batch_size=32,64
```

### Irregular sweeps with generators

For sweeps that cannot be expressed as a grid, fall back to a generator:

```python
# sweep.py
from kohakuengine import Config


def config_gen():
    base = {"epochs": 5}
    for lr in [0.001, 0.01]:
        yield Config(globals_dict={**base, "learning_rate": lr, "stage": "warmup"})
    for lr in [0.1, 1.0]:
        yield Config(globals_dict={**base, "learning_rate": lr, "stage": "anneal"})
```

The bare-file and `_sweep` forms both lower to a generator internally — they
are syntactic sugar, never restrictions.

## Part 4 — Entrypoint discovery

KohakuEngine picks the entrypoint to call using a documented cascade. From
highest priority to lowest:

1. `--entrypoint NAME` on the CLI.
2. The `script.py:func` colon syntax.
3. A function decorated with `@kogine.entrypoint`.
4. The function called inside `if __name__ == "__main__":`.
5. A `main()` function.
6. A `run()` function.

The decorator is the most explicit form. Rewrite `train.py`:

```python
# train.py
import kohakuengine as kogine


learning_rate = 0.001
batch_size = 32


def setup():
    pass  # not the entrypoint


@kogine.entrypoint
def train():
    print(f"lr={learning_rate} bs={batch_size}")
```

The decorator sets a marker on the function. KohakuEngine finds it
unambiguously; the cascade short-circuits without needing the
`if __name__` block.

## Part 5 — Config cells

When module-level setup is *expensive* — building an index, opening a
client connection, sampling a random seed — you do not want it to re-run
every time the module is imported by a worker process (DataLoader, fork
pool, etc.).

A **config cell** marks a region of the script as configuration. The
engine evaluates the cell once per script run and freezes the resolved
values into the module's namespace:

```python
# train.py
from data import load_huge_index


# %% kogine:config
learning_rate = 0.001
batch_size = 32
index = load_huge_index()   # 8-second startup
# %% kogine:script


def train():
    # any fork-mode worker that imports this module inherits the
    # already-evaluated `index` -- load_huge_index() does NOT re-run.
    ...


if __name__ == "__main__":
    train()
```

The cell is rewritten *in memory* — no temp file appears on disk.
Tracebacks still point at `train.py:<lineno>` and the debugger jumps to
the original source.

Cells interact cleanly with overrides:

```bash
kogine run train.py --set learning_rate=0.5
```

`learning_rate` becomes `0.5`; `index` is still the cached return value
from `load_huge_index()`.

See [Config cells](guides/config-cells.md) for the full mechanics
(including the spawn-worker caveat).

## Part 6 — Workflows

Run a single script under multiple configurations, or a pipeline of
different scripts, with `Flow`:

```python
# pipeline.py
from kohakuengine import Config, Flow, Script

preprocess = Script("preprocess.py", config=Config(globals_dict={"src": "raw.csv"}))
train      = Script("train.py",      config=Config(globals_dict={"epochs": 5}))
evaluate   = Script("evaluate.py",   config=Config(globals_dict={"split": "val"}))

if __name__ == "__main__":
    Flow([preprocess, train, evaluate], mode="sequential").run()
```

Or run a sweep in parallel:

```python
from kohakuengine import Flow, Script, load_config_file

script = Script("train.py", config=load_config_file("sweep.py"))
results = Flow([script], mode="parallel", max_workers=4).run()
```

## Part 7 — Pre-flight checks

Before running an expensive job, verify your config keys actually match
the script:

```bash
kogine config check train.py --config config.py
```

```
Config: config.py    Script: train.py

  [OK]  batch_size: 32 -> 128
  [OK]  learning_rate: 0.001 -> 0.05
  [??]  lr: not in script (did you mean learning_rate?)
  [+]   new_var: new var (not in script defaults)

2 hits, 1 typo warning(s), 1 new var(s).
```

The exit code is non-zero when typo warnings are present, so this command
is suitable for CI integration.

You can also see the *lowered* form of a config (what KohakuEngine
actually constructed):

```bash
kogine config show config.py
```

## Part 8 — The Python API

Everything the CLI does is available programmatically. The most common
entry point is `run()`:

```python
from kohakuengine import run

# inline overrides
run("train.py", globals_dict={"learning_rate": 0.05})

# from a config file, plus CLI-style overrides on top
run("train.py", config_path="config.py", set_overrides={"epochs": "20"})
```

For finer control:

```python
from kohakuengine import Config, Script, ScriptExecutor, load_config_file

config = load_config_file("config.py")
script = Script("train.py", config=config)
result = ScriptExecutor(script).execute()
```

## Where to go next

- [How-to guides](index.md#how-to-guides) — recipes for specific tasks.
- [Concepts](concepts.md) — the design philosophy and mental model.
- [Reference](index.md#reference) — the complete API and CLI documentation.
