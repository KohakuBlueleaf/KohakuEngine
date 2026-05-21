# Config cells

A **config cell** is a region of a script delimited by special comment
markers. Within that region, assignments behave as configuration:
KohakuEngine evaluates them once per script run, applies any overrides,
and freezes the resulting values into the executed module.

This is the feature to reach for when module-level setup is expensive and
would otherwise re-run inside fork-based worker processes.

## Why config cells exist

Many scripts have setup code at module level — building an index,
opening a network connection, sampling a seed, loading a large array.
When the script later spawns workers (PyTorch DataLoader, `multiprocessing.Pool`,
`torch.multiprocessing`), those workers re-import the module, and the
setup code runs again. For an 8-second setup with 16 workers, that is
two minutes of redundant work.

A config cell instructs KohakuEngine to:

1. Evaluate the cell *once* at the start of the script run.
2. Apply override values from the loaded `Config`.
3. Rewrite the script's AST so the cell's assignments become literal
   constants (or lookups into a module-private dictionary for
   non-literal values).
4. Execute the rewritten code with the original filename preserved, so
   tracebacks and debuggers still point at the source.

The rewrite happens entirely in memory. No file artefacts are produced.

## Syntax

Two comment markers delimit a cell:

```python
# %% kogine:config
... assignments ...
# %% kogine:script
```

The `# %% kogine:script` marker is optional. Without it, the cell ends
at the next non-`Assign` top-level statement.

The marker tokens use `kogine:` as a namespace to avoid clashing with
Jupytext / VS Code Jupyter cell markers (`# %%`).

## Minimal example

```python
# train.py
from data import load_index


# %% kogine:config
learning_rate = 0.001
batch_size    = 32
index         = load_index()
# %% kogine:script


def train():
    print(learning_rate, batch_size, len(index))


if __name__ == "__main__":
    train()
```

Run:

```bash
kogine run train.py --set learning_rate=0.5
```

`load_index()` runs exactly once. `learning_rate` becomes `0.5`;
`batch_size` and `index` keep their cell-evaluated values.

## Scope: "evaluate once" means per script run

A script run is a single `ScriptExecutor.execute()` call (or a single
top-level `kogine run` invocation). The cache key is `(absolute path,
file mtime)`.

| Scenario                                                                 | Cell evaluated |
| ------------------------------------------------------------------------ | -------------- |
| `kogine run train.py` (no overrides)                                     | Once           |
| `kogine run train.py --set learning_rate=0.5`                            | Once           |
| `kogine run train.py --sweep learning_rate=0.001,0.01,0.1` (3 runs)      | Once per run = 3 times |
| Script forks worker processes (Linux default)                            | Workers inherit; not re-run |
| Script spawns worker processes (Windows default, `mp.spawn`)             | **Workers re-import from disk; cell re-runs in each worker** |

The spawn-mode limitation is intentional: keeping the rewrite in memory
means there is no file for spawned workers to re-import. If you need to
avoid re-execution under spawn semantics, move the expensive call into
a function and guard it with your own caching (`functools.lru_cache`,
a sidecar pickle, etc.).

## What the cell can contain

The body of a cell must be a sequence of top-level simple assignments:

```python
# %% kogine:config
a = 1
b = some_function()
c = {"nested": [1, 2, 3]}
# %% kogine:script
```

Anything else inside the cell range — `if`, `for`, function calls used as
statements — terminates the cell early and emits a warning.

Tuple-unpacking targets (`a, b = 1, 2`) are not currently supported as
cell assignments; use separate lines.

## How the rewrite works

Internally, the engine produces this conceptual transformation:

```python
# After rewrite (in memory):
_KOGINE_FROZEN = {"index": <the actual object>}

# %% kogine:config
learning_rate = 0.5      # overridden, was a literal: substituted as ast.Constant
batch_size    = 32       # not overridden, original literal preserved
index         = _KOGINE_FROZEN["index"]   # non-literal: looked up at runtime
# %% kogine:script
```

For values that can be expressed as an `ast.Constant`
(`None`, `bool`, `int`, `float`, `complex`, `str`, `bytes`, and tuples /
frozensets of those), the value is inlined directly. Anything else is
stashed in `_KOGINE_FROZEN` and replaced with a subscript lookup.

Line numbers from the original source are preserved with
`ast.copy_location`, and the rewritten code is compiled with
`compile(tree, filename=str(original_path), mode="exec")`. The result is
that exceptions in `train()` still report `train.py:42`.

## Cells and pre-flight checks

`kogine config check` understands cells. When a cell is present, the
introspection path evaluates *only* the cell and its preamble (imports
that appear above it), then compares the declared cell variables to the
config keys. Code below the cell does not run during introspection.

This makes the check authoritative for cell-marked configurable surface.

## Cells and direct execution

The cell markers are ordinary Python comments. A script with cell markers
runs fine under plain `python train.py` — the cell body executes as
normal module-level code with its default values. KohakuEngine is the
only thing that interprets the markers specially.

## Programmatic access

```python
from kohakuengine.engine import (
    CellInfo,
    has_cell,
    parse_cell,
    evaluate_cell,
    execute_with_cell,
)
```

See [API reference](../reference/api.md#cell-engine) for full signatures.
