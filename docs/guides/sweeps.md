# Hyperparameter sweeps

KohakuEngine offers three ways to express a sweep, in increasing order
of expressiveness:

1. **Command-line flags** — `--sweep KEY=V1,V2,...`. No file needed.
2. **Declarative `_sweep` dict** — file-based grid or zipped sweep.
3. **Generator function** — arbitrary Python for irregular sweeps.

All three lower to a `ConfigGenerator` internally, so they compose
identically with the `Sequential`, `Parallel`, and `Flow` workflow
classes.

## Command-line sweeps

```bash
kogine run train.py --sweep learning_rate=0.001,0.01,0.1 --sweep batch_size=32,64
```

Each `--sweep` flag introduces one axis. Multiple flags combine as a
cartesian product. Values are strings on the wire; they are coerced to
the type of the script's default (`int`, `float`, `bool`, `str`).

This expands to six runs.

CLI sweeps run sequentially. To run them in parallel, write the sweep to
a file and use a workflow (see below).

## Declarative `_sweep` dict

### Grid (cartesian product)

```python
# sweep.py
epochs = 5
device = "cpu"

_sweep = {
    "learning_rate": [0.001, 0.01, 0.1],
    "batch_size":    [32, 64],
}
```

Six configs. Each carries the base values (`epochs=5`, `device="cpu"`)
plus one combination of the swept axes. The swept values also appear in
each config's `metadata` so you can identify runs after the fact.

### Paired (zip mode)

```python
_sweep = {
    "__mode__":      "zip",
    "learning_rate": [0.001, 0.01, 0.1],
    "batch_size":    [32,    64,   128],
}
```

Three configs, paired element-wise.

`zip` mode requires every axis to have the same length. If they differ,
the loader raises `ValueError` at load time, not at iteration time.

### Empty sweep

```python
_sweep = {}
```

Yields exactly one config containing the base values. Useful for toggling
sweeps off without removing the structure.

### Interaction with other forms

If a file contains both `_sweep` and `config_gen` (or `_sweep` and
`CONFIG`), `_sweep` is ignored and a `UserWarning` is emitted. The
explicit form always wins.

## Generator function

When the sweep is not a clean grid:

```python
# sweep.py
from kohakuengine import Config


def config_gen():
    base = {"epochs": 5, "device": "cpu"}
    for lr in [0.001, 0.01]:
        yield Config(
            globals_dict={**base, "learning_rate": lr, "stage": "warmup"},
            metadata={"lr": lr, "stage": "warmup"},
        )
    for lr in [0.1, 1.0]:
        yield Config(
            globals_dict={**base, "learning_rate": lr, "stage": "anneal"},
            metadata={"lr": lr, "stage": "anneal"},
        )
```

The function is called every time the loader runs. It can yield as many
configs as needed.

### Worker-aware generators

`config_gen` may accept a `worker_id=None` keyword. Parallel workflows
pass the worker id automatically; the CLI sets the
`KOGINE_WORKER_ID` environment variable when launching subprocesses.

```python
import os

from kohakuengine import Config


def config_gen(worker_id=None):
    worker_id = (
        worker_id if worker_id is not None
        else int(os.environ.get("KOGINE_WORKER_ID", 0))
    )
    return Config(
        globals_dict={"device": f"cuda:{worker_id % 4}", "random_seed": 42 + worker_id},
        metadata={"worker_id": worker_id},
    )
```

## Running sweeps in parallel

Once the sweep is in a file, run it through a parallel workflow:

```bash
kogine workflow parallel train.py --config sweep.py --workers 4
```

Or from Python:

```python
from kohakuengine import Flow, Script, load_config_file

script = Script("train.py", config=load_config_file("sweep.py"))
results = Flow([script], mode="parallel", max_workers=4).run()
```

Parallel mode defaults to **subprocess isolation**: each iteration runs
in its own Python process, ensuring that `__name__ == "__main__"`
semantics are preserved and worker state does not leak between runs.

For sweeps that need to share Python objects between iterations, use the
in-process pool mode:

```python
Flow([script], mode="parallel", max_workers=4, use_subprocess=False).run()
```

## Inspecting a sweep before running

```bash
kogine config show sweep.py
```

prints every expanded config so you can verify the cardinality and the
exact values before committing compute time.

## Counting expansions

| Source                                         | Count                                     |
| ---------------------------------------------- | ----------------------------------------- |
| `_sweep` grid                                  | Product of axis lengths                   |
| `_sweep` zip                                   | Length of any axis (all must match)       |
| Empty `_sweep = {}`                            | 1                                         |
| Generator `config_gen()`                       | Whatever the generator yields             |
| CLI `--sweep KEY=V1,V2 --sweep OTHER=W1,W2`    | Product of axis lengths                   |
