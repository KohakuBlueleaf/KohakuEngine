# Python API reference

This document is the authoritative reference for the public Python API of
`kohakuengine`. Function and method signatures use Python 3.10+ syntax.

For task-oriented walk-throughs see the [How-to guides](../index.md#how-to-guides);
for the command line, see the [CLI reference](cli.md).

## Module layout

```
kohakuengine/
├── __init__.py          # public API re-exports
├── main.py              # `run()` convenience function
├── cli.py               # CLI entry point
├── utils.py
├── config/
│   ├── base.py          # Config, Use, CaptureGlobals, capture_globals, use
│   ├── generator.py     # ConfigGenerator
│   ├── loader.py        # load_config_file, load_from_dict, ConfigLoader
│   └── types.py         # ConfigProvider, Configurable Protocols
├── engine/
│   ├── cell.py          # config-cell engine
│   ├── coerce.py        # schema-by-example coercion
│   ├── entrypoint.py    # entrypoint discovery + @entrypoint decorator
│   ├── executor.py      # ScriptExecutor
│   ├── injector.py      # GlobalInjector
│   ├── introspect.py    # introspect()
│   └── script.py        # Script dataclass
└── flow/
    ├── base.py          # Workflow / ScriptWorkflow ABCs
    ├── flow.py          # unified Flow facade
    ├── sequential.py    # Sequential
    └── parallel.py      # Parallel
```

## Top-level re-exports

```python
from kohakuengine import (
    __version__,
    Config,
    ConfigGenerator,
    Script,
    ScriptExecutor,
    Flow,
    Sequential,
    Parallel,
    Pipeline,
    capture_globals,         # deprecated; use module-level variables instead
    CaptureGlobals,          # deprecated
    use,
    use_config,              # compose configs (nested config import)
    Use,
    entrypoint,              # @kogine.entrypoint decorator
    run,
    introspect,
    coerce_globals,
    load_config_file,
    load_from_dict,
    EntrypointNotFound,
    MultipleEntrypoints,
)
```

---

## Configuration

### `class Config`

```python
@dataclass
class Config:
    globals_dict: dict[str, Any] = field(default_factory=dict)
    args:         list[Any]      = field(default_factory=list)
    kwargs:       dict[str, Any] = field(default_factory=dict)
    metadata:     dict[str, Any] = field(default_factory=dict)
```

The container for everything needed to execute one run.

| Field          | Purpose                                                                  |
| -------------- | ------------------------------------------------------------------------ |
| `globals_dict` | Module-level globals to inject into the script before calling its entrypoint. |
| `args`         | Positional arguments forwarded to the entrypoint.                        |
| `kwargs`       | Keyword arguments forwarded to the entrypoint.                           |
| `metadata`     | Arbitrary tracking data. Not injected into the script.                   |

#### Class methods

##### `Config.from_file(path, worker_id=None) -> Config | ConfigGenerator`

Delegates to [`load_config_file`](#load_config_file). Convenience wrapper.

##### `Config.from_dict(data) -> Config`

Delegates to [`load_from_dict`](#load_from_dict).

##### `Config.from_globals() -> Config`

Snapshot the caller's module-level globals as a `Config`. Uses
[`_filter_globals`](#filtering-rules) to decide what to capture.

##### `Config.from_context(ctx) -> Config`

Build a `Config` from a [`CaptureGlobals`](#class-captureglobals) context
object. Required for the deprecated `capture_globals()` API.

#### Validation

`Config.__post_init__` raises `TypeError` if any field is not the
expected type. `args` is normalised from `tuple` to `list`.

---

### `class ConfigGenerator`

```python
class ConfigGenerator:
    def __init__(self, generator: Iterator[Config])
    def __iter__(self) -> "ConfigGenerator"
    def __next__(self) -> Config
    @property
    def exhausted(self) -> bool
```

Wraps any iterator-of-`Config`. Used by `_sweep` expansion, generator
config files, and workflow internals. Raises `TypeError` if the
underlying generator yields a non-`Config`.

---

### `class Use` and `use(value)`

```python
class Use:
    __slots__ = ("value",)
    def __init__(self, value: Any) -> None
    def __repr__(self) -> str

def use(value: Any) -> Use
```

`use()` wraps a value so the loader includes it in configuration even
though it would otherwise be skipped by the filter (typically: imported
callables and classes). The wrapper is transparently unwrapped at
capture time.

---

### `use_config(path)`

```python
def use_config(path: str | Path) -> Config
```

Compose configuration by importing another config file. Call it at the
top level of a bare (or `_sweep`) config file to merge another config's
resolved values into the current one:

```python
# experiment.py
from kohakuengine import use_config

use_config("base.py")   # inherit everything from base.py
batch_size = 128        # ...then override what you need
```

Unlike a plain `import` — which is blocked (the config's directory is
deliberately not on `sys.path`) and would also bypass the loader —
`use_config` loads the file through `load_config_file`, so `config_gen`
/ `CONFIG` bases resolve correctly and locally-defined functions/classes
plus `_args` / `_kwargs` / `_metadata` are inherited.

- `path` is resolved relative to the **calling config file's directory**.
- **Your own top-level variables win** over imported ones. Stack multiple
  `use_config(...)` calls to layer bases; later calls win over earlier.
- `_args` is inherited (your own, if any, replaces it); `_kwargs` and
  `_metadata` are merged (your own keys win).
- Importing a sweep / `ConfigGenerator` config raises `TypeError`;
  circular imports raise `ValueError`.

The resolved `Config` is returned, so it is also usable programmatically
(e.g. inside `config_gen`):

```python
base = use_config("base.py")
return Config(globals_dict={**base.globals_dict, "lr": 0.5})
```

---

### `class CaptureGlobals` and `capture_globals()`

> **Deprecated since 0.2.0.** Emits `DeprecationWarning`. Scheduled for
> removal in 0.3.0. Use module-level variables instead — they are
> captured automatically by the bare-file loader path.

Context manager that captures variables newly bound inside its `with`
block.

---

### Filtering rules

The internal `_filter_globals(namespace, module_name)` helper is shared
between `Config.from_globals()` and the bare-file loader. It captures:

- Plain data values: numbers, strings, lists, dicts, custom instances.
- Locally-defined callables and classes (`__module__ == module_name`).
- Values wrapped in `use()`.

It skips:

- Names beginning with `_` (reserved for `_args`, `_kwargs`, `_metadata`, `_sweep`).
- Module objects (`isinstance(value, ModuleType)`).
- Imported callables and classes.

---

## Loader

### `load_config_file`

```python
def load_config_file(
    config_path: str | Path,
    worker_id: int | None = None,
) -> Config | ConfigGenerator
```

Loads a `.py` config file. Resolution order:

1. If the module defines `config_gen`, call it. Wraps generator returns
   as a `ConfigGenerator`; passes `worker_id` if the function accepts it.
2. If the module defines `CONFIG`, return it. Must be a `Config`
   instance.
3. If the module defines `_sweep`, expand it to a `ConfigGenerator`.
4. Otherwise, synthesize a `Config` from the module's globals via
   `_filter_globals`, applying `_args`, `_kwargs`, `_metadata` if
   present.

Raises:

- `FileNotFoundError` — config file does not exist.
- `ValueError` — module has wrong shape (e.g. `config_gen()` returns a
  non-`Config`).
- `TypeError` — `_args`/`_kwargs`/`_metadata`/`_sweep` have wrong types.

Emits `UserWarning` when `_sweep` is shadowed by `config_gen` or
`CONFIG`.

### `load_from_dict`

```python
def load_from_dict(data: dict) -> Config
```

Creates a `Config` from a dictionary with keys `"globals"`, `"args"`,
`"kwargs"`, `"metadata"`. Useful for loading parsed YAML/TOML/JSON.

### `class ConfigLoader`

Static-method facade preserved for backwards compatibility:

```python
ConfigLoader.load_config(path, worker_id=None)   # == load_config_file
ConfigLoader.load_from_dict(data)                # == load_from_dict
```

Prefer the module-level functions in new code.

### `_sweep` expansion

`_sweep` is a `dict[str, list]`. An optional `__mode__` key chooses the
expansion strategy:

| Mode        | Behaviour                                                |
| ----------- | -------------------------------------------------------- |
| `"grid"`    | (default) Cartesian product of all non-`__mode__` axes.  |
| `"zip"`     | Element-wise pairing. All axes must have equal length.   |

Other entries are interpreted as axis names → list of values.

---

## Scripts and execution

### `class Script`

```python
@dataclass
class Script:
    path: str | Path
    config: Config | ConfigGenerator | None = None
    entrypoint: str | None = None
    is_module: bool       # set in __post_init__
    module_name: str|None # set in __post_init__
```

`Script` accepts one of these `path` shapes:

| Form                          | Interpretation                                  |
| ----------------------------- | ----------------------------------------------- |
| `"train.py"`                  | File path.                                      |
| `"train.py:func"`             | File path with explicit entrypoint `func`.      |
| `"package.module"`            | Importable dotted module name.                  |
| `"package.module:func"`       | Dotted name with explicit entrypoint.           |

An explicit `entrypoint=` keyword wins over the colon syntax.

#### `script.run(config=None, use_subprocess=False) -> Any`

(Attached at import time via `engine/__init__.py`.) Executes the script.
`use_subprocess=True` re-launches via `python -m kohakuengine.cli`.

#### Properties

| Attribute     | Description                                              |
| ------------- | -------------------------------------------------------- |
| `script.name` | File stem or final module-name component.                |
| `script.path` | `Path` object after construction.                        |

---

### `class ScriptExecutor`

```python
class ScriptExecutor:
    def __init__(self, script: Script) -> None
    def execute(self, config: Config | None = None) -> Any
    @property
    def module(self) -> ModuleType | None
```

Executes a single `Script` with a single `Config`. The `module` property
gives access to the loaded module after execution.

Raises:

- `TypeError` — if `config` is a `ConfigGenerator` (use a `Flow` for
  sweeps).
- `EntrypointNotFound` — if the cascade finds no entrypoint and a
  `Config` was supplied.
- `RuntimeError` — if the script cannot be loaded.

---

## Workflows

### `class Flow`

```python
class Flow:
    def __init__(
        self,
        scripts: list[Script],
        mode: str = "sequential",        # "sequential" or "parallel"
        executor_class: type | None = None,
        max_workers: int | None = None,
        use_subprocess: bool | None = None,
    )
    def run(self) -> list[Any]
    def validate(self) -> bool
```

Unified facade. Delegates to `Sequential` or `Parallel` based on `mode`,
or to `executor_class` if supplied.

### `class Sequential`

```python
class Sequential(ScriptWorkflow):
    def __init__(self, scripts: list[Script], use_subprocess: bool = False) -> None
    def run(self) -> list[Any]
```

Runs scripts in order. For scripts with a `ConfigGenerator`, every
yielded config is executed and the results are flattened.

`use_subprocess=True` runs each script via the CLI subprocess for
isolation.

### `class Parallel`

```python
class Parallel(ScriptWorkflow):
    def __init__(
        self,
        scripts: list[Script],
        max_workers: int | None = None,
        use_subprocess: bool = True,
    ) -> None
    def run(self) -> list[Any]
```

Runs scripts (or generator iterations) concurrently. Defaults to
subprocess isolation; `use_subprocess=False` uses
`concurrent.futures.ProcessPoolExecutor`.

Results are returned in completion order, not submission order.

### `class Pipeline`

```python
class Pipeline(Sequential): ...
```

Alias for `Sequential`. Reserved for future state-passing semantics
between stages.

### `class Workflow` and `class ScriptWorkflow`

Abstract base classes. Inherit and provide `run()` and `validate()` to
implement custom executor classes. See [Workflows](../guides/workflows.md#custom-executors).

---

## Engine internals (public)

### `entrypoint` decorator

```python
def entrypoint(arg=None, *, name: str | None = None)
```

Decorator that marks a function as the explicit entrypoint of a script.
Two forms:

```python
@entrypoint
def train(): ...

@entrypoint(name="alias")
def train_v2(): ...
```

Sets `__kogine_entrypoint__ = True` and optionally `__kogine_entrypoint_name__`.

### `find_entrypoint`

```python
def find_entrypoint(
    module: ModuleType,
    script_path: Path | None = None,
    *,
    explicit_name: str | None = None,
) -> Callable
```

Implements the [discovery cascade](../guides/entrypoints.md#the-cascade).
Raises `EntrypointNotFound` if no entrypoint is found and
`MultipleEntrypoints` if more than one decorated function is present.

### `call_entrypoint`

```python
def call_entrypoint(
    func: Callable,
    args: list[Any],
    kwargs: dict[str, Any],
) -> Any
```

Invokes a function with `args`/`kwargs`. Handles async functions via
`asyncio.run`. Filters `kwargs` that the function does not declare and
does not accept via `**kw`.

### `class EntrypointFinder`

Static-method facade for backwards compatibility. New code should use
the module-level functions above.

### `class EntrypointNotFound`, `class MultipleEntrypoints`

Both inherit from `RuntimeError`.

### `class GlobalInjector`

```python
class GlobalInjector:
    PROTECTED_NAMES: frozenset[str]
    @staticmethod
    def inject(module: ModuleType, globals_dict: dict[str, Any]) -> None
    @staticmethod
    def get_user_globals(module: ModuleType) -> dict[str, Any]
```

`inject` `setattr`s each entry onto the module; raises `ValueError` if
a key is in `PROTECTED_NAMES` (the standard dunders).

`get_user_globals` returns the module's data-only globals (skipping
modules, classes, and callables).

---

## Cell engine

### `class CellInfo`

```python
@dataclass
class CellInfo:
    config_line: int
    script_line: int | None
    def in_cell(self, lineno: int) -> bool
```

The location of a config cell in a source file.

### `parse_cell`

```python
def parse_cell(script_path: Path) -> CellInfo | None
```

Returns the first cell found in a script, or `None`.

### `has_cell`

```python
def has_cell(script_path: str | Path) -> bool
```

### `evaluate_cell`

```python
def evaluate_cell(script_path: Path, cell: CellInfo) -> dict[str, Any]
```

Evaluates only the cell (plus preamble imports) and returns the
`{name: value}` dict. Memoized per `(absolute path, mtime)` for the
lifetime of the process.

### `clear_cell_cache`

```python
def clear_cell_cache() -> None
```

Drops the memoized evaluations. Useful in long-running daemons that
reload scripts during their lifetime.

### `execute_with_cell`

```python
def execute_with_cell(
    script_path: Path,
    overrides: dict[str, Any] | None,
    module_dict: dict[str, Any],
) -> tuple[ast.Module, dict[str, Any], dict[str, Any]]
```

The full pipeline: parse, evaluate cell, rewrite AST, prime
`linecache`, compile with the original filename, and execute into
`module_dict`. Returns `(rewritten_tree, evaluated_cell_state, frozen_dict)`.

Non-cell overrides are applied via direct dictionary assignment after
the rewritten module body has run.

---

## Introspection and coercion

### `introspect`

```python
def introspect(script_path: str | Path) -> dict[str, Any]
```

Returns the script's data-only defaults without firing its entrypoint.

For scripts with a config cell, only the cell body is evaluated;
module-level code below the cell does not run. For scripts without a
cell, the module is imported under a `_kogine_introspect_*` name so the
`if __name__ == "__main__":` guard does not fire.

### `coerce_globals`

```python
def coerce_globals(
    globals_dict: dict[str, Any],
    defaults: dict[str, Any],
    *,
    strict: bool = False,
) -> dict[str, Any]
```

Coerces each entry of `globals_dict` to the type of the corresponding
default. Pass-through for unknown types. With `strict=True`, unknown
keys raise `KeyError` and coercion failures raise `TypeError`.

The coercion table (`COERCERS`) ships with handlers for `bool`, `int`,
`float`, `str`. Booleans recognise `true`/`1`/`yes`/`y`/`on` and the
negations as falsy.

---

## Convenience runner

### `run`

```python
def run(
    script_path: str,
    config_path:  str | None             = None,
    globals_dict: dict[str, Any] | None  = None,
    args:         list[Any] | None       = None,
    kwargs:       dict[str, Any] | None  = None,
    set_overrides: dict[str, Any] | None = None,
    strict: bool = False,
) -> Any
```

One-call wrapper mirroring `kogine run`. Loads `config_path`, merges in
inline `globals_dict`/`args`/`kwargs`, applies `set_overrides` with
[`coerce_globals`](#coerce_globals), optionally enforces `strict`, then
executes via `ScriptExecutor`.

---

## Protocols

### `class ConfigProvider`

```python
class ConfigProvider(Protocol):
    def get_config(self) -> Config | Iterator[Config]: ...
```

### `class Configurable`

```python
class Configurable(Protocol):
    def apply_config(self, config: Config) -> None: ...
```

These are structural type aliases for use in third-party code; they are
not enforced by the engine.

---

## Exceptions

| Exception                | Base           | Raised when                                              |
| ------------------------ | -------------- | -------------------------------------------------------- |
| `EntrypointNotFound`     | `RuntimeError` | Discovery cascade finds nothing.                         |
| `MultipleEntrypoints`    | `RuntimeError` | Two or more functions carry `@entrypoint`.               |
| `FileNotFoundError`      | (builtin)      | Config or script path does not exist.                    |
| `ValueError`             | (builtin)      | Malformed config shape; invalid `_sweep` mode.           |
| `TypeError`              | (builtin)      | Wrong type for a `Config` field or for `_args`/`_kwargs`.|
| `RuntimeError`           | (builtin)      | Script module fails to load; subprocess workflow fails.  |

---

## Version

`kohakuengine.__version__` is the canonical version string.
