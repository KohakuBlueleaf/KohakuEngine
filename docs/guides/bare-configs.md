# Bare configuration files

A *bare* configuration file is a Python module that contains nothing but
the variables you want to inject. No imports are required; no
`Config(...)` constructor is needed; no `def config_gen():` boilerplate.

## When to use a bare config

- Single set of hyperparameters for one run.
- Defaults for a script that you tweak occasionally.
- Configurations that are mostly data.

For sweeps, see [Hyperparameter sweeps](sweeps.md). For configurations
that need to construct values dynamically per worker, see the
[`config_gen` form](#when-not-to-use-a-bare-config).

## Minimum example

```python
# config.py
learning_rate = 0.05
batch_size = 128
epochs = 5
```

Run with:

```bash
kogine run train.py --config config.py
```

The loader walks the module's globals, applies a filter (see below), and
constructs `Config(globals_dict={"learning_rate": 0.05, ...})`.

## What the loader captures

| Object kind                              | Captured?                                    |
| ---------------------------------------- | -------------------------------------------- |
| `int`, `float`, `str`, `bool`, `None`    | Yes                                          |
| `list`, `dict`, `tuple`, `set`, ...      | Yes                                          |
| Custom instances                         | Yes                                          |
| Locally-defined `def` / `class`          | Yes — `__module__` matches the config file   |
| Imported callables and classes           | No — unless wrapped in `use()`               |
| `import math` (the module itself)        | No                                           |
| Names beginning with `_`                 | No (reserved for `_args`, `_kwargs`, etc.)   |

## Locally-defined helpers

Functions and classes defined inside your config file are captured under
their own names automatically:

```python
# config.py
learning_rate = 0.01


def lr_schedule(epoch: int) -> float:
    return learning_rate * 0.95**epoch


class ModelConfig:
    hidden_size = 256
```

Both `lr_schedule` and `ModelConfig` become entries in
`Config.globals_dict`.

## Aliasing under a different name

If the script expects a different attribute name than the function's own
name, just write the assignment:

```python
# config.py
def custom_schedule(epoch):
    ...

# Bind under both names
scheduler = custom_schedule
```

Both `custom_schedule` and `scheduler` are captured.

## Imported callables

The loader cannot tell whether you intend to forward an imported
object as data or merely use it. Wrap with `use()` to disambiguate:

```python
# config.py
import math

from kohakuengine import use


loss_fn = use(math.sqrt)
```

Without `use()`, `loss_fn` would be skipped because
`math.sqrt.__module__ == "math"`.

A frequent gotcha is `functools.partial`:

```python
import functools

# __module__ is "functools", so it gets skipped:
weighted = functools.partial(math.pow, 2)

# To include it:
from kohakuengine import use
weighted = use(functools.partial(math.pow, 2))
```

## Composing configs (`use_config`)

To build a config on top of another one, use `use_config()` — **not** a
plain `import`. A direct `import` of a sibling config is blocked (the
config's directory is deliberately kept off `sys.path`) and, even if it
weren't, it would bypass the loader: a `config_gen()` / `CONFIG` base
would not resolve, and inherited functions, classes, and `_args` /
`_kwargs` / `_metadata` would be silently dropped.

```python
# base.py
learning_rate = 0.01
batch_size = 64
model = "resnet"


def lr_schedule(epoch):
    return learning_rate * 0.95**epoch
```

```python
# experiment.py
from kohakuengine import use_config

use_config("base.py")   # inherit everything from base.py
batch_size = 128        # ...then override what you need
epochs = 5              # ...and add new values
```

`kogine config show experiment.py` lowers to:

```text
learning_rate: 0.01      # inherited
batch_size:    128       # overridden (base had 64)
model:         "resnet"  # inherited
lr_schedule:   <function># inherited — a plain import would drop this
epochs:        5         # new
```

Rules:

- The path is resolved **relative to the file calling `use_config`**, so
  `use_config("../shared/base.py")` works regardless of your shell's
  working directory.
- **Your own top-level variables always win** over imported ones. Stack
  multiple `use_config(...)` calls to layer bases — later calls win over
  earlier ones, and your own assignments win over all of them.
- The base is loaded through the full loader, so bare, `CONFIG`, and
  `config_gen` bases all resolve. Importing a **sweep** config is an
  error (it is not a single value source); circular imports are detected
  and raise.
- `_args` is inherited (your own, if present, replaces it); `_kwargs`
  and `_metadata` are merged (your own keys win).

`use_config()` also returns the resolved `Config`, so you can compose
explicitly inside `config_gen`:

```python
from kohakuengine import Config, use_config


def config_gen():
    base = use_config("base.py")
    return Config(globals_dict={**base.globals_dict, "learning_rate": 0.5})
```

## Reserved underscore names

| Name        | Purpose                                                    |
| ----------- | ---------------------------------------------------------- |
| `_args`     | `list` / `tuple` of positional arguments for the entrypoint |
| `_kwargs`   | `dict` of keyword arguments for the entrypoint              |
| `_metadata` | `dict` of arbitrary tracking information                    |
| `_sweep`    | Declarative grid — see [Sweeps](sweeps.md)                  |

Example:

```python
# config.py
learning_rate = 0.05
batch_size = 128

_args = []
_kwargs = {"resume_from": "ckpt-007.pt"}
_metadata = {"experiment": "baseline-128", "owner": "alice"}
```

## When not to use a bare config

Use the explicit `config_gen()` or `CONFIG` form when:

- You need to construct the config conditionally on the worker id
  (parallel runs that should pick different GPUs, for instance).
- You need access to the worker id via a function parameter.
- You want to call helper functions to build the config dynamically.

```python
# worker_aware.py
import os

from kohakuengine import Config


def config_gen(worker_id=None):
    worker_id = worker_id if worker_id is not None else int(
        os.environ.get("KOGINE_WORKER_ID", 0)
    )
    return Config(
        globals_dict={
            "device":      f"cuda:{worker_id % 4}",
            "random_seed": 42 + worker_id,
            "output_dir":  f"./out/worker_{worker_id}",
        },
        metadata={"worker_id": worker_id},
    )
```

The loader detects `config_gen` and `CONFIG` and bypasses the bare-file
fallback entirely.

## Inspecting the result

```bash
kogine config show config.py
```

prints the lowered `Config` so you can verify exactly what KohakuEngine
will inject.
