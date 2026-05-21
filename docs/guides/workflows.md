# Workflows: sequential and parallel

The `Flow` class orchestrates multiple `Script` executions. It supports
two execution modes, both with optional subprocess isolation.

## Choosing a mode

| Mode         | Use when                                                                         |
| ------------ | -------------------------------------------------------------------------------- |
| `sequential` | Pipeline of distinct stages; each depends on the previous completing.            |
| `parallel`   | Independent runs (sweeps, replicates); order does not matter.                    |

| Isolation        | Use when                                                                  |
| ---------------- | ------------------------------------------------------------------------- |
| Subprocess       | Default. Scripts run with `__name__ == "__main__"` and a clean interpreter.|
| In-process pool  | You need Python objects to be passed between iterations.                  |

## Sequential pipelines

```python
from kohakuengine import Config, Flow, Script

preprocess = Script("preprocess.py", config=Config(globals_dict={"src": "raw.csv"}))
train      = Script("train.py",      config=Config(globals_dict={"epochs": 5}))
evaluate   = Script("evaluate.py",   config=Config(globals_dict={"split": "val"}))

Flow([preprocess, train, evaluate], mode="sequential").run()
```

`Flow.run()` returns a `list` of results in execution order. For scripts
configured with a `ConfigGenerator`, every yielded config is executed and
the per-iteration results are flattened into the result list.

The CLI equivalent:

```bash
kogine workflow sequential preprocess.py train.py evaluate.py --config shared.py
```

## Parallel sweeps

```python
from kohakuengine import Flow, Script, load_config_file

script = Script("train.py", config=load_config_file("sweep.py"))
results = Flow([script], mode="parallel", max_workers=4).run()
```

CLI equivalent:

```bash
kogine workflow parallel train.py --config sweep.py --workers 4
```

Results are returned in completion order (not submission order). Inspect
each result's metadata (`config.metadata`) to identify which run it
corresponds to.

## Subprocess vs in-process

The default for `parallel` is subprocess isolation. Each iteration spawns
a fresh Python interpreter via `python -m kohakuengine.cli run`. This
guarantees:

- A clean module table — no shared mutable state between iterations.
- `__name__ == "__main__"` semantics preserved.
- Independent GPU contexts on CUDA.

To run in-process (faster startup, shared imports):

```python
Flow([script], mode="parallel", max_workers=4, use_subprocess=False).run()
```

The in-process path uses `concurrent.futures.ProcessPoolExecutor`. The
script and its config must be picklable.

For sequential workflows, subprocess mode is opt-in:

```python
Flow([script], mode="sequential", use_subprocess=True).run()
```

This is useful when the script holds onto resources that need to be
released between iterations (CUDA contexts, file descriptors).

## Mixing scripts with different configs

A workflow can contain heterogeneous scripts and per-script configs:

```python
scripts = [
    Script("download.py",   config=Config(globals_dict={"dataset": "imagenet"})),
    Script("preprocess.py", config=Config(globals_dict={"output": "./proc"})),
    Script("train.py",      config=load_config_file("sweep.py")),  # generator
    Script("evaluate.py",   config=Config(globals_dict={"split": "val"})),
]
Flow(scripts, mode="sequential").run()
```

Sequential mode handles the mix: stages with a `ConfigGenerator`
iterate as if they were a nested loop, while stages with a single
`Config` run once.

## Worker identification

For parallel workflows that spawn subprocesses, KohakuEngine sets the
`KOGINE_WORKER_ID` environment variable per process. A worker-aware
`config_gen` can read it:

```python
import os
from kohakuengine import Config


def config_gen(worker_id=None):
    worker_id = (
        worker_id if worker_id is not None
        else int(os.environ.get("KOGINE_WORKER_ID", 0))
    )
    return Config(
        globals_dict={"device": f"cuda:{worker_id}"},
    )
```

## Error handling

Subprocess-mode workflows raise `RuntimeError` when any subprocess exits
with a non-zero return code. The error message includes the failing
command for diagnosis.

In-process mode lets the underlying exception propagate from the worker.
`ProcessPoolExecutor` wraps it in a `concurrent.futures.process.BrokenProcessPool`
if the worker crashes mid-execution.

## Custom executors

`Flow` accepts an `executor_class` argument for custom workflow logic:

```python
class MyExecutor:
    def __init__(self, scripts):
        self.scripts = scripts
    def run(self):
        ...
    def validate(self):
        return True

Flow(scripts, executor_class=MyExecutor).run()
```

The class must expose `run()` and `validate()`. See
[`flow/base.py`](https://github.com/KohakuBlueleaf/KohakuEngine/blob/main/src/kohakuengine/flow/base.py)
for the abstract base classes.
