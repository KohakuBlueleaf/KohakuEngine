# Changelog

All notable changes to KohakuEngine are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] — 2026-09-27

### Added

- **Annotation-driven override coercion.** `--set`, `--sweep`, and
  `run(set_overrides=...)` values are coerced to the name's top-level
  annotation when it has one, else to its default's type:

  ```python
  lr: float = 1                 # --set lr=0.5      -> 0.5 (not a failed int())
  steps: Optional[int] = None   # --set steps=100   -> 100; steps=none -> None
  dims: list[int] = [64]        # --set dims=64,128 -> [64, 128]
  mode: Mode = Mode.TRAIN       # --set mode=eval   -> Mode.EVAL
  ```

  Supported: builtin scalars, `None`, `Optional` / `Union`, `Literal`,
  `list` / `tuple` / `set` / `frozenset` / `dict` and their
  `collections.abc` forms (recursive), `Enum`, `NewType`, `Final[T]`,
  and any annotated class via `cls(value)` (`Path`, `Decimal`, ...).
  Un-annotated container defaults infer their element type
  (`[64, 128]` → `list[int]`).
- **Custom override parsers.** A class with a `format_arg` classmethod
  is built with `Class.format_arg(value)`; for third-party types use
  `Annotated[T, FormatArg(fn)]`.
- **Annotated assignments in config cells.** `name: T = value` and
  annotation-only `name: T` lines are valid cell statements.
- **`introspect_schema()` / `ScriptSchema`.** Defaults plus top-level
  annotations; `--strict` and `kogine config check` accept
  annotation-only names, and `config check` prints annotations.
- **`coerce_value()`, `RawArg`, `layer_overrides()`,
  `evaluate_cell_schema()`, `Script.cli_command()`** in the public API.
- **Bracket-aware `--sweep` splitting.** `--sweep dims=[1,2],[3]` gives
  two values; commas inside brackets or quotes do not split.

### Changed

- **Overrides are coerced when the script loads**, against its live
  namespace, instead of against a separate introspection import. Classes
  and Enums in annotations are the script's own objects (`mode is
  Mode.EVAL` holds for a script-local Enum), and coercion happens in the
  child for `--subprocess` and subprocess workflows. `--set` without
  `--strict` no longer imports the script an extra time.
- **Only override values are coerced.** Values from a config file are
  injected as written, including under `--set` / `--strict`.
- **`int` coercion is lossless.** `"1e3"` and `"0x10"` parse; `"0.5"` or
  `0.5` for an `int` name fails instead of truncating.
- **`--strict` unknown-key errors** list every unknown key with a
  "did you mean" suggestion.
- **Version is single-sourced** from `kohakuengine.__version__`
  (`pyproject.toml` declares it dynamic).

### Fixed

- `--set` combined with `--sweep` was dropped; it now applies to every
  sweep run.
- `--set` / `--strict` with a generator config file were ignored; they
  now apply to every generated config.
- `--sweep` with a generator config file discarded the file; the result
  is now every generated config × every sweep value.
- `--set` / `--sweep` / `--strict` crashed for `script.py:func` and
  `package.module` script specs.
- `--subprocess` (and subprocess workflows) dropped the entrypoint and
  ran module-form scripts by file path.
- `kohakuengine.__version__` reported `0.2.0`.
- Async entrypoints are detected with `inspect.iscoroutinefunction`
  (`asyncio.iscoroutinefunction` is deprecated in Python 3.14).

## [0.4.0] — 2026-06-29

### Added

- **Nested configs via `use_config(path)`.** Compose a config on top of
  another one from within a config file:

  ```python
  from kohakuengine import use_config
  use_config("base.py")   # inherit everything
  batch_size = 128        # then override
  ```

  The base is loaded through the full loader (so `config_gen` / `CONFIG`
  / bare bases all resolve) and inherited functions, classes, and
  `_args` / `_kwargs` / `_metadata` are preserved. The path resolves
  relative to the calling config file; your own values win over imported
  ones; stacking multiple calls layers bases (later wins). Importing a
  sweep config raises, and circular imports are detected.

## [0.3.0] — 2026-06-27

### Fixed

- **Scripts run by `kogine` now match `python script.py` import
  semantics.** The script's directory is prepended to `sys.path`, so
  sibling modules and `__init__`-less (namespace) packages import
  correctly.
- **Functions defined in a `kogine`-run script are now picklable for
  `multiprocessing`.** Scripts are loaded under their importable module
  name and kept in `sys.modules`, so `ProcessPoolExecutor` / `Pool`
  workers can resolve them (previously failed with `Can't pickle ...:
  import of module '_kohaku_script_..._<id>' failed`).

## [0.2.0] — 2026-05-21

A major ergonomic overhaul. Existing v0.1.x configs and scripts continue
to work without modification; the new features are additive.

### Added

- **Bare config files.** A configuration file may now contain just
  module-level variables; the loader synthesizes a `Config`
  automatically. No `def config_gen():` required.
- **Auto-include locally-defined callables.** Functions and classes
  defined inside a config file are captured automatically (their
  `__module__` matches the config file). The `use()` wrapper is now
  only needed for imported callables.
- **Reserved underscore names.** `_args`, `_kwargs`, `_metadata`, and
  `_sweep` at the top of a config file populate the corresponding
  `Config` fields or trigger sweep expansion.
- **Declarative `_sweep`.** A dictionary `_sweep = {"axis1": [...],
  "axis2": [...]}` expands to a cartesian product `ConfigGenerator`.
  Optional `__mode__: "zip"` switches to element-wise pairing.
- **`@kogine.entrypoint` decorator.** Explicit, unambiguous marker for
  the script's entrypoint function.
- **Broadened entrypoint cascade.** In addition to the existing
  `if __name__ == "__main__":` AST detection, KohakuEngine now also
  checks (in priority order): `--entrypoint` CLI flag, `script.py:func`
  colon syntax, `@kogine.entrypoint` decorator, `main()`, `run()`.
- **Config cells.** Mark a region of a script with
  `# %% kogine:config` / `# %% kogine:script`; KohakuEngine evaluates
  it once per script run and rewrites the AST in memory so values are
  frozen for any re-execution path inside that run (fork-mode workers,
  `importlib.reload`).
- **`kogine config check` command.** Pre-flight diff between a config
  file and a script's defaults, with typo suggestions via
  `difflib.get_close_matches`. Exit code is non-zero on typo
  warnings, suitable for CI.
- **`kogine config show` expansion.** Now prints the lowered `Config`
  form (or every expanded config for a sweep) so users can verify
  what the loader actually produced.
- **CLI `--set KEY=VALUE`.** Override a config key from the command
  line without writing a config file. Repeatable. Values are
  type-coerced against the script's defaults.
- **CLI `--sweep KEY=V1,V2,...`.** Sweep one axis from the command
  line. Multiple `--sweep` flags compose as a cartesian product.
- **`--strict` mode.** Reject overrides that do not match any script
  default. Coercion failures become errors. Available on the CLI and
  via `run(strict=True)`.
- **Schema-by-example coercion.** A new `coerce_globals()` helper
  treats the script's default values as a type schema, coercing
  string overrides to the right type (`int`, `float`, `bool`, `str`).
- **`introspect()` function.** Load a script's defaults without firing
  its entrypoint. Used by `kogine config check`, `--set`/`--strict`,
  and the schema-by-example coercer.
- **`py.typed` marker.** The package is now PEP 561 compliant.

### Changed

- **Project requires Python 3.10 or newer.** (No change from v0.1.x;
  re-confirmed.)
- **`Config.from_globals()` filter is now shared** with the bare-file
  loader path. Both paths apply the same rules for which names are
  captured. Local callables are now captured by default; imported
  callables are skipped unless wrapped in `use()`.
- **Entrypoint discovery diagnostic.** `EntrypointNotFound` now lists
  every name searched and recommends `@kogine.entrypoint` or
  `--entrypoint NAME`.
- **`kogine config show` output format.** Now reports the source style
  (bare-file, `config_gen`, `CONFIG`, sweep) and the lowered fields
  with types.
- **`pyproject.toml`.** Full PyPI metadata: classifiers, keywords,
  URLs, maintainers, optional `[dev]` and `[examples]` extras.

### Deprecated

- **`capture_globals()` / `CaptureGlobals`.** Emits
  `DeprecationWarning`. Module-level variables in a bare config file
  achieve the same effect without the awkward indentation. Scheduled
  for removal in v0.3.0.

### Fixed

- Test suite reaches 100% line coverage. No `from __future__` imports
  and no in-function imports anywhere in the source tree.

### Internal

- New modules: `engine/cell.py`, `engine/coerce.py`,
  `engine/introspect.py`.
- Shared `_filter_globals` helper in `config/base.py` is the single
  source of truth for what `from_globals` / bare-file capture.
- Circular imports broken via attach-pattern in `__init__.py` files
  (`Config.from_file` / `from_dict` attached from loader;
  `Script.run` attached from executor).
- All in-function imports removed. Type-only forward references use
  `if TYPE_CHECKING:` blocks.

## [0.0.2] — 2025-11-19

### Added

- Initial core implementation:
  - `Config`, `ConfigGenerator`, `Use`, `capture_globals`, `use`.
  - `Script`, `ScriptExecutor`, `GlobalInjector`, `EntrypointFinder`.
  - `Sequential`, `Parallel`, `Flow`, `Pipeline`.
  - `kogine` CLI with `run`, `workflow sequential`, `workflow
    parallel`, `config validate`, `config show` commands.
  - `examples/` directory with hello world, training, sweep,
    `from_globals`, `capture_globals`, `use`, and worker-aware
    examples.
  - Test suite covering configs, executors, entrypoint discovery, and
    workflows.

[0.5.0]: https://github.com/KohakuBlueleaf/KohakuEngine/releases/tag/v0.5.0
[0.4.0]: https://github.com/KohakuBlueleaf/KohakuEngine/releases/tag/v0.4.0
[0.3.0]: https://github.com/KohakuBlueleaf/KohakuEngine/releases/tag/v0.3.0
[0.2.0]: https://github.com/KohakuBlueleaf/KohakuEngine/releases/tag/v0.2.0
[0.0.2]: https://github.com/KohakuBlueleaf/KohakuEngine/releases/tag/v0.0.2
