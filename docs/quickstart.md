# Quickstart

This page takes you from a fresh install to a running, configurable script
in under five minutes.

## Prerequisites

- KohakuEngine installed — see [Installation](installation.md).
- A working directory you can write to.

## 1. Write a script

Create `train.py`:

```python
# train.py
learning_rate = 0.001
batch_size = 32
epochs = 10


def train():
    print(f"lr={learning_rate}  bs={batch_size}  epochs={epochs}")


if __name__ == "__main__":
    train()
```

This is a normal Python script. It runs unchanged with `python train.py`.

## 2. Run it through KohakuEngine

```bash
kogine run train.py
```

You should see:

```
lr=0.001  bs=32  epochs=10
Script executed successfully
```

KohakuEngine loaded the script, located the entrypoint inside
`if __name__ == "__main__":`, and invoked it. So far this is equivalent to
running the script directly.

## 3. Override values from the command line

```bash
kogine run train.py --set learning_rate=0.05 --set batch_size=128
```

Output:

```
lr=0.05  bs=128  epochs=10
Script executed successfully
```

`--set KEY=VALUE` overrides any module-level global in the script. Values
arrive as strings and are coerced to the type of the script's default
(`int`, `float`, `bool`, `str`), so `0.05` becomes a float.

## 4. Move the overrides to a config file

Create `config.py`:

```python
# config.py
learning_rate = 0.05
batch_size = 128
epochs = 5
```

A bare config file is just module-level variables — no imports, no
`Config()` constructor, no `def config_gen():` boilerplate.

Run with the config:

```bash
kogine run train.py --config config.py
```

## 5. Sweep over a hyperparameter grid

```bash
kogine run train.py --sweep learning_rate=0.001,0.01,0.1 --sweep batch_size=32,64
```

This expands to six runs covering the cartesian product
`{0.001, 0.01, 0.1} × {32, 64}`.

Equivalent file-based form (`sweep.py`):

```python
# sweep.py
epochs = 5
_sweep = {
    "learning_rate": [0.001, 0.01, 0.1],
    "batch_size":    [32, 64],
}
```

```bash
kogine run train.py --config sweep.py
```

## 6. Catch configuration typos before running

```bash
kogine config check train.py --config config.py
```

Output:

```
Config: config.py    Script: train.py

  [OK]  batch_size: 32 -> 128
  [OK]  epochs: 10 -> 5
  [OK]  learning_rate: 0.001 -> 0.05

3 hits, 0 typo warning(s), 0 new var(s).
```

If a config key does not match any script default, you get a typo warning
or a "new variable" notice.

## What just happened

KohakuEngine treats your script as the source of truth for what is
configurable, then *injects* override values into the module's globals
before calling its entrypoint. There is no schema file to maintain, no
class to subclass, no decorator required.

## Next steps

- Read the [Tutorial](tutorial.md) for a complete walk through every feature.
- Browse the [How-to guides](index.md#how-to-guides) for task-oriented recipes.
- Consult the [Reference](index.md#reference) when you need the exact API.
