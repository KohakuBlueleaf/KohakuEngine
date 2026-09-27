"""KohakuEngine CLI -- ``kogine`` command-line interface."""

import argparse
import difflib
import io
import sys
from pathlib import Path

from kohakuengine import __version__
from kohakuengine.config import Config, ConfigGenerator, load_config_file
from kohakuengine.engine import (
    EntrypointNotFound,
    Script,
    ScriptExecutor,
    introspect_schema,
    layer_overrides,
    split_top_level,
)
from kohakuengine.engine.coerce import describe_annotation
from kohakuengine.flow import Parallel, Sequential

_TYPO_CUTOFF = 0.6


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
    if sys.stderr.encoding != "utf-8":
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )

    parser = create_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kogine",
        description="KohakuEngine: All-in-Python Config and Execution Engine",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(title="commands", dest="command")

    run_parser = subparsers.add_parser("run", help="Execute a single script")
    run_parser.add_argument("script", help="Path to script or module.name")
    run_parser.add_argument("--config", "-c", help="Path to config file")
    run_parser.add_argument("--entrypoint", "-e", help="Entrypoint function name")
    run_parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a config key (repeatable). Coerced from script defaults.",
    )
    run_parser.add_argument(
        "--sweep",
        action="append",
        default=[],
        metavar="KEY=V1,V2,...",
        help="Sweep an axis (repeatable). Multiple flags = cartesian product.",
    )
    run_parser.add_argument(
        "--strict",
        action="store_true",
        help="Error on overrides that don't match a script default.",
    )
    run_parser.add_argument(
        "--subprocess",
        action="store_true",
        help="Run script in a subprocess.",
    )
    run_parser.set_defaults(func=cmd_run)

    workflow_parser = subparsers.add_parser("workflow", help="Execute workflow")
    workflow_subparsers = workflow_parser.add_subparsers(dest="workflow_type")

    seq_parser = workflow_subparsers.add_parser(
        "sequential", help="Sequential execution"
    )
    seq_parser.add_argument("scripts", nargs="+", help="Scripts to execute")
    seq_parser.add_argument("--config", "-c", help="Config file for all scripts")
    seq_parser.set_defaults(func=cmd_workflow_sequential)

    par_parser = workflow_subparsers.add_parser("parallel", help="Parallel execution")
    par_parser.add_argument("scripts", nargs="+", help="Scripts to execute")
    par_parser.add_argument("--config", "-c", help="Config file for all scripts")
    par_parser.add_argument("--workers", "-w", type=int, help="Max workers")
    par_parser.add_argument(
        "--mode",
        choices=["subprocess", "pool"],
        default="subprocess",
        help="Execution mode",
    )
    par_parser.set_defaults(func=cmd_workflow_parallel)

    config_parser = subparsers.add_parser("config", help="Config utilities")
    config_subparsers = config_parser.add_subparsers(dest="config_cmd")

    validate_parser = config_subparsers.add_parser("validate", help="Validate config")
    validate_parser.add_argument("config", help="Config file to validate")
    validate_parser.set_defaults(func=cmd_config_validate)

    show_parser = config_subparsers.add_parser("show", help="Show lowered config")
    show_parser.add_argument("config", help="Config file to show")
    show_parser.set_defaults(func=cmd_config_show)

    check_parser = config_subparsers.add_parser(
        "check", help="Pre-flight diff: config keys vs script defaults"
    )
    check_parser.add_argument("script", help="Script to check against")
    check_parser.add_argument("--config", "-c", required=True, help="Config file")
    check_parser.set_defaults(func=cmd_config_check)

    return parser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_set(items: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--set must be KEY=VALUE, got {item!r}")
        key, _, value = item.partition("=")
        out[key.strip()] = value.strip()
    return out


def _parse_sweep(items: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--sweep must be KEY=V1,V2,..., got {item!r}")
        key, _, values = item.partition("=")
        out[key.strip()] = split_top_level(values)
    return out


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> None:
    script = Script(args.script, entrypoint=args.entrypoint)
    config: Config | ConfigGenerator | None = None
    if args.config:
        config = load_config_file(args.config)

    declared = introspect_schema(script.path).declared if args.strict else None
    config = layer_overrides(
        config,
        set_values=_parse_set(args.set),
        sweep_values=_parse_sweep(args.sweep),
        strict=args.strict,
        declared=declared,
    )
    script.config = config

    if isinstance(config, ConfigGenerator):
        print("Config is a generator, running sequentially.")
        workflow = Sequential([script], use_subprocess=args.subprocess)
        results = workflow.run()
        print(f"Script executed successfully ({len(results)} iterations)")
        sys.exit(0)

    if args.subprocess:
        proc = script._run_subprocess(config)
        if proc.returncode != 0:
            sys.exit(proc.returncode)
        print("Script executed successfully (subprocess)")
        sys.exit(0)

    try:
        result = ScriptExecutor(script).execute()
    except EntrypointNotFound as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    print("Script executed successfully")
    if result is not None:
        print(f"Return value: {result}")
    sys.exit(0)


def cmd_workflow_sequential(args: argparse.Namespace) -> None:
    config = load_config_file(args.config) if args.config else None
    scripts = [Script(p, config=config) for p in args.scripts]
    results = Sequential(scripts).run()
    print(f"Sequential workflow completed ({len(results)} executions)")
    sys.exit(0)


def cmd_workflow_parallel(args: argparse.Namespace) -> None:
    config = load_config_file(args.config) if args.config else None
    scripts = [Script(p, config=config) for p in args.scripts]
    use_subprocess = args.mode == "subprocess"
    workflow = Parallel(
        scripts, max_workers=args.workers, use_subprocess=use_subprocess
    )
    results = workflow.run()
    print(f"Parallel workflow completed ({len(results)} executions)")
    sys.exit(0)


def cmd_config_validate(args: argparse.Namespace) -> None:
    config = load_config_file(args.config)
    print(f"Config valid: {args.config}")
    print(f"  Type: {type(config).__name__}")
    sys.exit(0)


def cmd_config_show(args: argparse.Namespace) -> None:
    config = load_config_file(args.config)
    print(f"Config: {args.config}")
    if isinstance(config, ConfigGenerator):
        print("Source style: generator / sweep")
        configs = list(config)
        print(f"Total configs: {len(configs)}\n")
        for i, cfg in enumerate(configs, start=1):
            print(f"--- Config {i}/{len(configs)} ---")
            _print_config(cfg)
            print()
    else:
        print(_describe_source(args.config))
        print("\nLowered to Config:")
        _print_config(config)
    sys.exit(0)


def _describe_source(path: str) -> str:
    src = Path(path).read_text(encoding="utf-8")
    if "def config_gen" in src:
        return "Source style: explicit config_gen() function"
    if "\nCONFIG" in src or src.startswith("CONFIG"):
        return "Source style: explicit CONFIG variable"
    if "_sweep" in src:
        return "Source style: declarative _sweep"
    return "Source style: bare-file (auto-captured globals)"


def _print_config(config: Config) -> None:
    print("  globals_dict:")
    for k, v in config.globals_dict.items():
        print(f"    {k}: {v!r}  ({type(v).__name__})")
    print(f"  args:     {config.args!r}")
    print(f"  kwargs:   {config.kwargs!r}")
    if config.metadata:
        print(f"  metadata: {config.metadata!r}")


def cmd_config_check(args: argparse.Namespace) -> None:
    config = load_config_file(args.config)
    if isinstance(config, ConfigGenerator):
        configs = list(config)
        provided_keys: set[str] = set()
        for cfg in configs:
            provided_keys.update(cfg.globals_dict.keys())
    else:
        provided_keys = set(config.globals_dict.keys())

    try:
        schema = introspect_schema(args.script)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    defaults = schema.defaults
    declared = schema.declared
    hits = provided_keys & declared
    missing = provided_keys - declared

    print(f"Config: {args.config}    Script: {args.script}\n")
    for k in sorted(hits):
        new_value = (
            config.globals_dict[k]
            if isinstance(config, Config)
            else next(iter(configs)).globals_dict.get(k, "<sweep>")
        )
        old = repr(defaults[k]) if k in defaults else "<no default>"
        if k in schema.annotations:
            old += f" ({describe_annotation(schema.annotations[k])})"
        print(f"  [OK]  {k}: {old} -> {new_value!r}")
    typos = 0
    new_vars = 0
    for k in sorted(missing):
        suggestion = difflib.get_close_matches(k, declared, n=1, cutoff=_TYPO_CUTOFF)
        if suggestion:
            print(f"  [??]  {k}: not in script (did you mean {suggestion[0]!r}?)")
            typos += 1
        else:
            print(f"  [+]   {k}: new var (not in script defaults)")
            new_vars += 1

    print(f"\n{len(hits)} hits, {typos} typo warning(s), {new_vars} new var(s).")
    sys.exit(0 if typos == 0 else 1)


if __name__ == "__main__":  # pragma: no cover
    main()
