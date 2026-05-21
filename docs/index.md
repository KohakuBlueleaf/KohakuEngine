# KohakuEngine Documentation

KohakuEngine is an all-in-Python configuration and execution engine for
research, development, and experimentation workloads. It runs your existing
Python scripts with arbitrary configurations — no code refactoring, no
schemas to maintain — and ships with first-class support for hyperparameter
sweeps, multi-stage workflows, and pre-flight validation.

This site is organised along the [Diátaxis](https://diataxis.fr/) framework:

| Goal                                  | Where to start                          |
| ------------------------------------- | --------------------------------------- |
| Install the library and run a script  | [Installation](installation.md) → [Quickstart](quickstart.md) |
| Learn the system end-to-end           | [Tutorial](tutorial.md)                 |
| Solve a specific problem              | [How-to guides](#how-to-guides)         |
| Look up an API or CLI command         | [Reference](#reference)                 |
| Understand the design and trade-offs  | [Concepts](concepts.md), [Architecture](architecture.md) |
| Contribute to the project             | [Contributing](contributing.md)         |
| Track changes between versions        | [Changelog](changelog.md)               |
| Find answers to common questions      | [FAQ](faq.md)                           |

## Tutorials

Step-by-step lessons that teach the system. Read these in order if you are
new to KohakuEngine.

- [Installation](installation.md)
- [Quickstart](quickstart.md) — five minutes to a running script with overrides.
- [Tutorial](tutorial.md) — progressive walk-through covering every major feature.

## How-to guides

Task-oriented recipes for users who already know the basics.

- [Bare config files](guides/bare-configs.md)
- [Config cells](guides/config-cells.md)
- [Hyperparameter sweeps](guides/sweeps.md)
- [Workflows: sequential and parallel](guides/workflows.md)
- [Entrypoint discovery and decorators](guides/entrypoints.md)
- [Overrides and validation](guides/overrides-and-validation.md)
- [Migration from earlier versions](guides/migration.md)

## Reference

Authoritative descriptions of the public surface.

- [Python API reference](reference/api.md)
- [Command-line interface reference](reference/cli.md)

## Explanation

Conceptual background and architectural reasoning.

- [Concepts and design philosophy](concepts.md)
- [Architecture](architecture.md)

## Project

- [Contributing](contributing.md)
- [Changelog](changelog.md)
- [Frequently asked questions](faq.md)

---

**License:** Apache-2.0.
**Repository:** [github.com/KohakuBlueleaf/KohakuEngine](https://github.com/KohakuBlueleaf/KohakuEngine).
