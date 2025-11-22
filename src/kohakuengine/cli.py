"""
KohakuEngine CLI.

Usage:
    kogine run SCRIPT [--config CONFIG] [--subprocess] [options]
    kogine workflow sequential SCRIPT... [--config CONFIG]
    kogine workflow parallel SCRIPT... [--config CONFIG] [--workers N]
    kogine config validate CONFIG
    kogine config show CONFIG
    kogine --version
    kogine --help
"""

import argparse
import sys
from pathlib import Path

from kohakuengine import __version__
from kohakuengine.config import Config, ConfigGenerator, ConfigLoader
from kohakuengine.engine import Script, ScriptExecutor
from kohakuengine.flow import Parallel, Sequential


def main() -> None:
    """CLI entry point."""
    # Ensure UTF-8 encoding for stdout/stderr on Windows
    import io

    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
    if sys.stderr.encoding != "utf-8":
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )

    parser = create_parser()
    args = parser.parse_args()

    if hasattr(args, "func"):
        try:
            args.func(args)
        except Exception as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="kogine",
        description="KohakuEngine: All-in-Python Config and Execution Engine",
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(title="commands", dest="command")

    # run command
    run_parser = subparsers.add_parser("run", help="Execute a single script")
    run_parser.add_argument("script", help="Path to script")
    run_parser.add_argument("--config", "-c", help="Path to config file")
    run_parser.add_argument("--entrypoint", "-e", help="Entrypoint function name")
    run_parser.add_argument(
        "--subprocess",
        action="store_true",
        help="Run in subprocess (useful for asyncio scripts or config generators)",
    )
    run_parser.set_defaults(func=cmd_run)

    # workflow command
    workflow_parser = subparsers.add_parser("workflow", help="Execute workflow")
    workflow_subparsers = workflow_parser.add_subparsers(dest="workflow_type")

    # workflow sequential
    seq_parser = workflow_subparsers.add_parser(
        "sequential", help="Sequential execution"
    )
    seq_parser.add_argument("scripts", nargs="+", help="Scripts to execute")
    seq_parser.add_argument("--config", "-c", help="Config file for all scripts")
    seq_parser.set_defaults(func=cmd_workflow_sequential)

    # workflow parallel
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

    # config command
    config_parser = subparsers.add_parser("config", help="Config utilities")
    config_subparsers = config_parser.add_subparsers(dest="config_cmd")

    # config validate
    validate_parser = config_subparsers.add_parser("validate", help="Validate config")
    validate_parser.add_argument("config", help="Config file to validate")
    validate_parser.set_defaults(func=cmd_config_validate)

    # config show
    show_parser = config_subparsers.add_parser("show", help="Show config contents")
    show_parser.add_argument("config", help="Config file to show")
    show_parser.set_defaults(func=cmd_config_show)

    return parser


def cmd_run(args: argparse.Namespace) -> None:
    """Execute run command."""
    # Load config if provided
    config = None
    if args.config:
        config = ConfigLoader.load_config(args.config)

    # Create script
    script = Script(args.script, config=config, entrypoint=args.entrypoint)

    # Handle ConfigGenerator specially - use Sequential for ordered execution
    if isinstance(config, ConfigGenerator):
        print(f"✓ Config is a generator, running sequentially...")
        use_subprocess = getattr(args, "subprocess", False)
        workflow = Sequential([script], use_subprocess=use_subprocess)
        results = workflow.run()
        print(f"✓ Script executed successfully ({len(results)} iterations)")
        sys.exit(0)

    # Single config execution
    if getattr(args, "subprocess", False):
        result = script.run(use_subprocess=True)
        print("✓ Script executed successfully (subprocess)")
    else:
        executor = ScriptExecutor(script)
        result = executor.execute()
        print("✓ Script executed successfully")
        if result is not None:
            print(f"Return value: {result}")

    sys.exit(0)


def cmd_workflow_sequential(args: argparse.Namespace) -> None:
    """Execute sequential workflow."""
    # Load config
    config = None
    if args.config:
        config = ConfigLoader.load_config(args.config)

    # Create scripts
    scripts = [Script(path, config=config) for path in args.scripts]

    # Execute workflow
    workflow = Sequential(scripts)
    results = workflow.run()

    print(f"✓ Sequential workflow completed ({len(results)} executions)")
    sys.exit(0)


def cmd_workflow_parallel(args: argparse.Namespace) -> None:
    """Execute parallel workflow."""
    # Load config
    config = None
    if args.config:
        config = ConfigLoader.load_config(args.config)

    # Create scripts
    scripts = [Script(path, config=config) for path in args.scripts]

    # Execute workflow
    use_subprocess = args.mode == "subprocess"
    workflow = Parallel(
        scripts, max_workers=args.workers, use_subprocess=use_subprocess
    )
    results = workflow.run()

    print(f"✓ Parallel workflow completed ({len(results)} executions)")
    sys.exit(0)


def cmd_config_validate(args: argparse.Namespace) -> None:
    """Validate config file."""
    config = ConfigLoader.load_config(args.config)
    print(f"✓ Config valid: {args.config}")
    print(f"  Type: {type(config).__name__}")
    sys.exit(0)


def cmd_config_show(args: argparse.Namespace) -> None:
    """Show config contents."""
    config = ConfigLoader.load_config(args.config)

    if isinstance(config, ConfigGenerator):
        print("Config type: Generator")
        print("\nIterating through configs:")
        for i, cfg in enumerate(config):
            print(f"\n--- Config {i+1} ---")
            _print_config(cfg)
    else:
        print("Config type: Static")
        _print_config(config)

    sys.exit(0)


def _print_config(config: Config) -> None:
    """Print config details."""
    print(f"Globals: {config.globals_dict}")
    print(f"Args: {config.args}")
    print(f"Kwargs: {config.kwargs}")
    if config.metadata:
        print(f"Metadata: {config.metadata}")


if __name__ == "__main__":
    main()
