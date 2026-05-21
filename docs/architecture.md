# Architecture

This document describes the internal organisation of the KohakuEngine
codebase. Read it if you intend to contribute, embed the engine in a
larger system, or simply understand the implementation in depth.

For the conceptual model and design principles, see
[Concepts](concepts.md). For the public API surface, see the
[Python API reference](reference/api.md).

## High-level structure

```
┌───────────────────────────────────────────────────────────────────┐
│                              kohakuengine                          │
├───────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │    CONFIG    │ →  │    ENGINE    │ →  │     FLOW     │          │
│  │              │    │              │    │              │          │
│  │ - Config     │    │ - Script     │    │ - Sequential │          │
│  │ - Generator  │    │ - Executor   │    │ - Parallel   │          │
│  │ - Loader     │    │ - Injector   │    │ - Flow facade│          │
│  │ - use()      │    │ - Entrypoint │    │              │          │
│  │              │    │ - Cell       │    │              │          │
│  │              │    │ - Introspect │    │              │          │
│  │              │    │ - Coerce     │    │              │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│         │                   │                   │                  │
│         └───────────────────┼───────────────────┘                  │
│                             │                                      │
│                ┌────────────┴────────────┐                         │
│                │                         │                         │
│           ┌────▼────┐                ┌───▼────┐                    │
│           │   CLI   │                │   API  │                    │
│           │  kogine │                │  run() │                    │
│           └─────────┘                └────────┘                    │
└───────────────────────────────────────────────────────────────────┘
```

Three independent subsystems with one strict dependency direction. The
CLI and the Python `run()` helper sit on top, composing them.

## Module layout

```
src/kohakuengine/
├── __init__.py        # public API re-exports
├── main.py            # `run()` convenience function
├── cli.py             # argparse-based CLI
├── utils.py           # tiny helpers (path resolution)
├── py.typed           # PEP 561 marker
│
├── config/
│   ├── __init__.py    # attaches Config.from_file / from_dict
│   ├── base.py        # Config, Use, CaptureGlobals, _filter_globals
│   ├── generator.py   # ConfigGenerator
│   ├── loader.py      # load_config_file, load_from_dict, ConfigLoader
│   └── types.py       # ConfigProvider / Configurable protocols
│
├── engine/
│   ├── __init__.py    # attaches Script.run; re-exports
│   ├── script.py      # Script dataclass + _serialize_config
│   ├── executor.py    # ScriptExecutor
│   ├── entrypoint.py  # cascade + @entrypoint decorator
│   ├── injector.py    # GlobalInjector
│   ├── cell.py        # config-cell engine
│   ├── coerce.py      # coerce_globals (schema-by-example)
│   └── introspect.py  # introspect()
│
└── flow/
    ├── __init__.py
    ├── base.py        # Workflow / ScriptWorkflow ABCs
    ├── flow.py        # unified Flow facade
    ├── sequential.py  # Sequential, Pipeline
    └── parallel.py    # Parallel (subprocess + pool modes)
```

## Dependency direction

| Module     | May import from                                        |
| ---------- | ------------------------------------------------------ |
| `config/`  | stdlib only.                                           |
| `engine/`  | `config/` and stdlib.                                  |
| `flow/`    | `config/`, `engine/`, and stdlib.                      |
| `cli.py`   | `config/`, `engine/`, `flow/`, and stdlib.             |
| `main.py`  | `config/`, `engine/`, and stdlib.                      |
| `__init__` | every module above.                                    |

No upward imports. No circular imports inside the source tree.

## Circular-import resolution

Two natural cycles exist in the public API and are broken by **attaching
methods at import time** in the package `__init__.py` files, rather than
inside the class definitions:

- `Config.from_file` and `Config.from_dict` are attached in
  `config/__init__.py` after both `base.py` and `loader.py` have
  loaded. `base.py` itself does not import `loader.py`.
- `Script.run` is attached in `engine/__init__.py` after both
  `script.py` and `executor.py` have loaded. `script.py` does not
  import `executor.py`; `executor.py` references `Script` only for type
  hints under `if TYPE_CHECKING:`.

This pattern keeps the call sites clean (users still write
`Config.from_file(...)` and `script.run()`) without introducing
in-function imports, which the project forbids.

## Execution flow

A single-script execution under `kogine run script.py --config c.py`:

1. **CLI parses arguments.** `cli.cmd_run` reads `args.script`,
   `args.config`, `--set`, `--sweep`, etc.
2. **Loader runs.** `load_config_file(args.config)` produces a `Config`
   or `ConfigGenerator`.
3. **Optional coercion.** If `--set` or `--strict` is present, the CLI
   calls `introspect(args.script)` to get defaults, then `coerce_globals`
   to apply type coercion.
4. **Script construction.** `Script(args.script, config=config,
   entrypoint=args.entrypoint)` parses the path and detects whether the
   target is a file or an importable module.
5. **Executor.** `ScriptExecutor(script).execute()`:
   - If the script has a cell, `_load_with_cell` delegates to
     `execute_with_cell` (cell engine).
   - Otherwise, `_load_file_module` imports the script under a
     `_kohaku_script_*` name and the injector applies
     `Config.globals_dict`.
6. **Entrypoint cascade.** `find_entrypoint` selects the function to
   call.
7. **Call.** `call_entrypoint` invokes it with `Config.args` /
   `Config.kwargs`, awaiting if async.

For a sweep, step 5 onward repeats per yielded `Config`, optionally in
parallel under a `Parallel` workflow.

## The cell engine

Documented in [Config cells](guides/config-cells.md). The implementation
lives in `engine/cell.py`. Key components:

| Function                        | Purpose                                                          |
| ------------------------------- | ---------------------------------------------------------------- |
| `parse_cell` / `_parse_cell_from_source` | Token-based marker detection (AST drops comments).        |
| `_cell_assign_nodes`            | Identify the contiguous run of `Assign` nodes inside the cell range. |
| `_preamble_nodes`               | Statements before the cell, exec'd to resolve imports.           |
| `evaluate_cell`                 | Exec preamble + cell in a sandbox; returns `{name: value}`. Memoized. |
| `_rewrite_assigns`              | Substitute `ast.Constant` for literal-safe values, `_KOGINE_FROZEN[name]` lookups otherwise. |
| `execute_with_cell`             | The full pipeline: parse → evaluate → rewrite → compile → exec.  |

Two design constraints worth highlighting:

- **Line numbers are preserved.** `ast.copy_location` is applied on
  every substituted node so tracebacks point at the original source.
- **Original filename in `compile()`.** The rewritten AST is compiled
  with the absolute path to the original file. Combined with priming
  `linecache.cache`, this means `traceback` modules display source
  previews correctly even though the file on disk and the executed
  code differ.

## The entrypoint cascade

Documented in [Entrypoint discovery](guides/entrypoints.md). Implemented
in `engine/entrypoint.py::find_entrypoint`. The cascade is encoded as a
straight-line function whose ordering reflects priority. The diagnostic
emitted on failure lists every name searched, which means changes to
the cascade are self-documenting in error messages.

## Subsystem responsibilities in detail

### `config/`

Owns *data*. Knows nothing about scripts or processes. The only side
effect is `_filter_globals`, which performs no I/O.

`loader.py` is the only module that executes user code (a config
`.py`). It does so under a stable `_kogine_config_*` name to avoid
polluting `sys.modules` with the user's module name. The module is
inserted into `sys.modules` only briefly so relative imports inside the
config work; on success or failure it is removed.

### `engine/`

Owns *execution*. The `executor` is the only place that calls user
entrypoints. The `cell` engine is the only place that uses `ast` for
mutation. The `introspect` module is read-only — it imports a script
under a non-`__main__` name and reports defaults but never calls the
entrypoint.

### `flow/`

Owns *orchestration*. The `Sequential` and `Parallel` classes each take
a list of `Script` objects, iterate over them, and call into the engine.
The unified `Flow` facade dispatches to the appropriate implementation
based on `mode`.

The `_execute_script_helper` function at the top of `parallel.py` is
module-level so it can be pickled for `ProcessPoolExecutor`.

### `cli.py` and `main.py`

Pure dispatchers. `cli.py` parses argparse namespaces and forwards to
one of `cmd_*` functions; each `cmd_*` is a thin wrapper that loads
config, builds `Script` / `Flow`, calls `.run()`, and exits with the
right code.

`main.run()` is the same logic without argparse. The CLI and the API
share no behaviour code; they share the same underlying engine but
implement their own command dispatch.

## Subprocess invocation protocol

When a workflow runs in subprocess mode, it invokes
`python -m kohakuengine.cli run` with the script path and a
temporarily-written config file (`Script._serialize_config`). The
temporary file contains a generated `def config_gen():` that returns
an equivalent `Config`. This is the entire IPC channel — no pipes, no
shared memory.

The environment variable `KOGINE_WORKER_ID` is set per worker so
`config_gen` can specialise per-worker behaviour. Subprocess return
codes are propagated; non-zero exits raise `RuntimeError` in
`Sequential`.

## Coding conventions

The codebase obeys a small set of strict rules, enforced by code review:

- **No `from __future__` imports.** The minimum supported Python is
  3.10, so deferred-annotation features are unnecessary.
- **No imports inside function or method bodies.** All imports live at
  module top level (or under `if TYPE_CHECKING:` for cycle-breaking
  forward references).
- **Black-formatted.** Line length 88, default Black configuration. The
  `[tool.black]` table in `pyproject.toml` is the source of truth.
- **No silent failures.** Every error path either returns a sentinel
  documented in the docstring (`None` for "not found"-style results) or
  raises an exception with sufficient context.
- **100% line coverage on the source tree.** The CI-equivalent
  invocation is `pytest --cov=kohakuengine`.

## Backwards-compatibility surface

Anything re-exported from `kohakuengine.__init__` is considered public
API and follows SemVer within the 0.x line — breaking changes require a
minor-version bump and a deprecation period with `DeprecationWarning`
emission for at least one release.

Internal modules (`_filter_globals`, `_serialize_config`, the cell
engine internals) are not stability-bound; they may change between
minor versions.

The `ConfigLoader` and `EntrypointFinder` facades exist solely for
backwards compatibility with v0.1.x. They forward to the module-level
functions and are not deprecated.
