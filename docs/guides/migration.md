# Migration guide

This document describes the behavioural changes between historical
KohakuEngine releases and the current major version.

## v0.1.x → v0.2.0

v0.2.0 is **backwards-compatible**: every config and script that worked
under v0.1.x continues to work without modification. The new features
are opt-in.

That said, several v0.1.x patterns have simpler replacements in v0.2.0.
This section lists them; adopt them at your own pace.

### Configs no longer need `def config_gen():`

A configuration that just exposes a dict of variables can be written as
module-level assignments:

```python
# v0.1.x — required boilerplate
from kohakuengine import Config

learning_rate = 0.01
batch_size = 64

def config_gen():
    return Config.from_globals()
```

```python
# v0.2.0 — bare file
learning_rate = 0.01
batch_size = 64
```

The `def config_gen():` form still works exactly as before; it is now
optional.

### `use()` is no longer needed for locally-defined callables

In v0.1.x, every function or class you wanted to expose had to be
wrapped:

```python
# v0.1.x
from kohakuengine import use


def lr_schedule(epoch): ...
lr_schedule = use(lr_schedule)
```

In v0.2.0 the loader inspects `__module__` and includes any function or
class defined in the same config file automatically:

```python
# v0.2.0
def lr_schedule(epoch): ...
# captured automatically
```

`use()` remains the correct way to forward an **imported** callable
(`__module__` not equal to the config module):

```python
# Still required in v0.2.0
import math
from kohakuengine import use

loss_fn = use(math.sqrt)
```

### Entrypoint args and metadata can use underscore names

Where v0.1.x required constructing a `Config(args=..., kwargs=...)`:

```python
# v0.1.x
def config_gen():
    return Config(
        globals_dict={"lr": 0.01},
        kwargs={"resume_from": "ckpt.pt"},
        metadata={"experiment": "baseline"},
    )
```

v0.2.0 accepts reserved underscore names:

```python
# v0.2.0
lr = 0.01
_kwargs = {"resume_from": "ckpt.pt"}
_metadata = {"experiment": "baseline"}
```

### Grid sweeps no longer require a generator

The most common sweep — a cartesian product over a few axes — can be
declared:

```python
# v0.1.x
from kohakuengine import Config

def config_gen():
    for lr in [0.001, 0.01]:
        for bs in [32, 64]:
            yield Config(globals_dict={"learning_rate": lr, "batch_size": bs})
```

```python
# v0.2.0
_sweep = {
    "learning_rate": [0.001, 0.01],
    "batch_size":    [32, 64],
}
```

Generators remain the right tool for irregular sweeps.

### `capture_globals()` is deprecated

The `capture_globals()` context manager forced awkward indentation and
is redundant now that bare files capture top-level variables
automatically.

```python
# v0.1.x
from kohakuengine import Config, capture_globals

with capture_globals() as ctx:
    lr = 0.01
    bs = 64

def config_gen():
    return Config.from_context(ctx)
```

In v0.2.0 the same effect:

```python
# v0.2.0
lr = 0.01
bs = 64
```

`capture_globals()` still works in v0.2.0 but emits a
`DeprecationWarning`. It will be **removed in v0.3.0**.

## Summary table

| Pattern                                                  | v0.2.0 replacement                       |
| -------------------------------------------------------- | ---------------------------------------- |
| `def config_gen(): return Config.from_globals()`         | Delete it. Bare file works.              |
| `lr = use(local_fn)`                                     | `lr = local_fn` — no wrapper needed.     |
| `Config(args=..., kwargs=..., metadata=...)`             | `_args`, `_kwargs`, `_metadata`.         |
| Grid generator `for x in ...: for y in ...: yield ...`   | `_sweep = {"x": [...], "y": [...]}`      |
| `with capture_globals() as ctx:`                          | Use module-level variables directly.     |

## Forward compatibility

Code written in the v0.2.0 style works in subsequent releases. New
features may be added; existing names will not change semantics within
the 0.x series.

The `capture_globals()` removal is the only deprecation currently
scheduled; everything else is additive.
