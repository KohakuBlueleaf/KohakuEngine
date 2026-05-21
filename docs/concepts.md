# Concepts and design philosophy

This document explains the *why* behind KohakuEngine. It is intended for
readers who have skimmed the [Quickstart](quickstart.md) and want to
understand the design before adopting the library in earnest.

## The problem

Research and development codebases routinely accumulate scripts of this
shape:

```python
# train.py
learning_rate = 0.001
batch_size = 32
epochs = 10

def train(): ...

if __name__ == "__main__":
    train()
```

Module-level globals are the natural unit of configuration during
exploration. They are visible, mutable, and trivially overridable by
hand-editing. The trade-off is that this style does not scale: as soon
as you need to run the same script under multiple configurations — for
sweeps, comparisons, or production deployment — the globals become an
obstacle. The script either gets refactored into a class hierarchy with
a config schema, or it gets cloned with hard-coded variants.

The premise of KohakuEngine is that **the original style is fine** and
the missing piece is machinery on top — a way to *inject* configuration
into existing globals without changing how the script is written.

## The mental model

KohakuEngine treats a script's module-level globals as its
**configurable surface**. A `Config` is a snapshot of values intended for
that surface. Running a script under a `Config` means:

1. Import the script as a module (with a non-`__main__` name so its
   guard does not fire).
2. `setattr` each entry of `Config.globals_dict` onto that module.
3. Find an entrypoint function via the [discovery cascade](guides/entrypoints.md).
4. Call it with `Config.args` and `Config.kwargs`.

The script runs as if executed directly — except its globals start out
with the injected values rather than the defaults written in the source.

The Python language enforces no schema on globals, which is what makes
this work. KohakuEngine adds no schema either; the script's own defaults
double as the schema when needed (for type coercion and pre-flight
checks).

## Three layers, no surprises

The codebase is organised as three independent subsystems with a strict
dependency direction:

```
   ┌──────────┐     ┌──────────┐     ┌──────────┐
   │  CONFIG  │  →  │  ENGINE  │  →  │   FLOW   │
   └──────────┘     └──────────┘     └──────────┘
```

- **Config** owns the data structures (`Config`, `ConfigGenerator`) and
  the loader that turns a `.py` file into them.
- **Engine** owns single-script execution: loading, injection,
  entrypoint discovery, cell rewriting.
- **Flow** owns orchestration: sequential and parallel execution of
  multiple scripts or multiple configs.

The CLI and the Python `run()` function sit on top, composing these
three layers. There is no plugin system, no event bus, no inversion of
control. Each layer can be used in isolation.

## Design principles

### 1. Configurations are data, not code

A bare config file is just module-level variables. The user does not
have to learn any KohakuEngine API to write one — they have to know
Python.

The loader's resolution order (`config_gen` → `CONFIG` → `_sweep` →
bare) ensures that the simplest case requires zero ceremony, while
power users keep access to the more expressive forms.

### 2. Scripts should not need to know about KohakuEngine

The vast majority of scripts run with KohakuEngine **with no
modifications**. The `@kogine.entrypoint` decorator exists for users
who want explicit markers, not as a requirement. The mandatory
`if __name__ == "__main__":` block is honoured, but not required —
`main()` and `run()` conventions are also discovered.

This is the single largest difference between KohakuEngine and
configuration frameworks that require structural conformance (Hydra,
some `argparse`-based wrappers).

### 3. Magic must be explainable

Every implicit behaviour can be described in one paragraph and verified
by `kogine config show`. The bare-file loader uses one filter
(`_filter_globals`) shared with `Config.from_globals` so there is a
single source of truth. The cell engine produces a deterministic AST
rewrite that can be inspected with `ast.unparse`. There are no
metaclasses, no import hooks, no global state outside the cell cache.

### 4. Sugar lowers to the explicit core

`_sweep`, `_args`, bare files, CLI `--set` and `--sweep` flags all
lower to the same `Config(globals_dict=..., args=..., kwargs=...,
metadata=...)` core. The lower form is always available as a fallback;
the sugar is purely additive.

### 5. The script is the schema

Type coercion and pre-flight validation use the script's own default
values as the type schema. There is no separate `.yaml` or `.proto`
to keep in sync. This is the simplest possible thing that solves the
real problem (typos and string-vs-int confusion in CLI overrides) and
no more.

### 6. Failures should be loud and informative

Every error path includes the context needed to fix it:

- `EntrypointNotFound` lists every name searched.
- Config-shape errors name the offending field and the bad value.
- `kogine config check` suggests typo fixes via `difflib.get_close_matches`.
- The cell warning identifies the file line where the cell terminated
  unexpectedly.

## Non-goals

KohakuEngine deliberately does **not** try to be:

- **A workflow engine.** Sequential and parallel execution within one
  machine are supported because they are cheap and useful for R&D. For
  multi-machine orchestration, use Airflow, Prefect, Ray, or SLURM.
- **A schema validator.** There is no Pydantic or `attrs` dependency.
  Schema-by-example handles the common case; if you need more,
  validate inside your `config_gen` function.
- **A dependency manager.** It does not pin packages, manage virtual
  environments, or interact with `pip`/`conda`/`poetry`.
- **A cluster orchestrator.** Per-process resource management (GPU
  pick, memory limits) is the responsibility of the script and the
  host system. KohakuEngine sets `KOGINE_WORKER_ID` and gets out of
  the way.

## When KohakuEngine is the right tool

- You have an existing Python script with module-level globals and
  want to run it with different configurations.
- You need hyperparameter sweeps over a handful of axes.
- You have a multi-stage pipeline of independent scripts to run in
  sequence.
- You want a quick way to migrate from "edit the script directly"
  to a config-file-driven workflow without refactoring.
- You need lightweight subprocess isolation between runs.

## When KohakuEngine is not the right tool

- You need a heavyweight production workflow engine with retries,
  scheduling, DAG visualisation, and a UI. (Try Airflow, Prefect,
  Argo.)
- You need a typed configuration system with strict schema enforcement
  and IDE auto-completion of config keys. (Try Hydra + structured
  configs, or `pydantic-settings`.)
- You need distributed training orchestration across machines. (Try
  Ray, Lightning, accelerate, or DeepSpeed launchers; KohakuEngine
  composes happily with them but does not replace them.)

## Glossary

- **Script** — a `.py` file or importable module whose module-level
  globals are the configurable surface.
- **Entrypoint** — the function KohakuEngine calls inside the script.
  Discovered via the cascade documented in [Entrypoints](guides/entrypoints.md).
- **Config** — a `Config` instance: globals to inject, args/kwargs to
  pass, metadata to record.
- **ConfigGenerator** — an iterator of `Config` instances. Produced by
  sweeps, generator config functions, and CLI `--sweep` flags.
- **Loader** — `load_config_file()`: turns a `.py` file into a
  `Config` or `ConfigGenerator`. Resolves `config_gen` / `CONFIG` /
  `_sweep` / bare-file precedence.
- **Injector** — `GlobalInjector.inject()`: applies `Config.globals_dict`
  to a module via `setattr`.
- **Cell** — a region of a script delimited by `# %% kogine:config` and
  `# %% kogine:script` whose assignments are eagerly evaluated and
  frozen.
- **Workflow** — a `Sequential`, `Parallel`, or `Flow` orchestrating one
  or more `Script` objects.
- **Worker** — a process spawned by parallel execution; identified by
  `KOGINE_WORKER_ID`.
