# Frequently asked questions

## What is KohakuEngine in one sentence?

A Python library that runs your existing scripts under arbitrary
configurations by injecting values into their module-level globals,
finding their entrypoint, and calling it.

## How is this different from Hydra, OmegaConf, or `argparse`?

| Concern                                    | KohakuEngine                                                                  | Hydra / OmegaConf                                  | `argparse`                              |
| ------------------------------------------ | ----------------------------------------------------------------------------- | -------------------------------------------------- | --------------------------------------- |
| Config format                              | Python (`.py`)                                                                | YAML (+ Python structured configs)                 | CLI flags                               |
| Required script changes                    | None (decorator is optional)                                                  | Wrap entrypoint with `@hydra.main(...)`            | Per-script `argparse.ArgumentParser()`  |
| Schema enforcement                         | Schema-by-example (script defaults define types)                              | Optional structured configs (Pydantic-like)        | Manual                                  |
| Composability of configs                   | Generator functions, `_sweep`                                                 | Group + override syntax, multirun                  | Custom                                  |
| Run multiple configs in parallel           | Yes, via `Flow(mode="parallel")`                                              | Yes, via Hydra launchers                           | No                                      |
| Subprocess isolation by default            | Yes (in `Parallel`)                                                           | Depends on launcher                                | No                                      |
| Dependencies                               | None                                                                          | Several (OmegaConf, antlr)                         | None (stdlib)                           |

In short: KohakuEngine occupies a smaller niche. If you want full
structured-config validation and a launcher ecosystem, use Hydra. If you
want the lightest possible bridge from "globals at the top of the file"
to "configurable script with sweeps," KohakuEngine is the right
abstraction.

## Do I have to modify my script to use KohakuEngine?

No. A script that runs with `python train.py` runs with
`kogine run train.py` without any modification, provided it has an
`if __name__ == "__main__":` block or a `main()` / `run()` function.

The `@kogine.entrypoint` decorator is offered for users who prefer
explicit markers, but it is never required.

## Can I use YAML, TOML, or JSON for configs?

Yes, but you have to parse them yourself inside your `.py` config file.
KohakuEngine does not ship a YAML/TOML/JSON loader. Example:

```python
# config.py
import yaml

with open("config.yaml") as f:
    data = yaml.safe_load(f)

learning_rate = data["learning_rate"]
batch_size    = data["batch_size"]
```

The bare-file loader picks these up. Alternatively, use
`Config.from_dict(data)` if you prefer the dict form.

## How does KohakuEngine compare to Lightning's `LightningCLI` or `accelerate config`?

Those tools are tightly integrated with their respective training
frameworks and assume specific code structures. KohakuEngine is
framework-agnostic — it does not know anything about PyTorch,
JAX, scikit-learn, or any other library. You can use it alongside any
of them.

## Does it work with PyTorch DataLoader workers?

Yes, with a caveat. KohakuEngine itself runs the parent process; what
happens in DataLoader workers depends on the multiprocessing start
method:

- **Fork** (Linux default): workers inherit the parent's already-injected
  state. No re-initialisation needed. Config cells are especially
  useful here — expensive setup runs once in the parent and is
  inherited by every fork worker.
- **Spawn** (Windows default, macOS, `torch.multiprocessing.spawn`):
  workers start a fresh Python interpreter and re-import the script
  from disk. They see the script's *original* source, not KohakuEngine's
  injected values. Use a config file consumed at module level (e.g.
  read environment variables, parse a YAML), or move expensive setup
  into a function guarded with your own caching.

## Why does my `functools.partial(...)` config entry get skipped?

`functools.partial(...)` returns an instance whose `__module__` is
`"functools"`, not your config file. The loader treats it as imported
and skips it. Wrap it explicitly:

```python
import functools
from kohakuengine import use

weighted = use(functools.partial(math.pow, 2))
```

The same applies to anything created by a library that does not set
`__module__` to your config file's name.

## Can I have multiple `@kogine.entrypoint` decorators in one script?

No. KohakuEngine raises `MultipleEntrypoints` when it finds more than
one decorated function. Pass `--entrypoint NAME` to disambiguate, or
remove the extra decorator.

## How do I run a script in a subprocess from Python?

```python
from kohakuengine import Script, Config

script = Script("train.py", config=Config(globals_dict={"lr": 0.05}))
proc   = script.run(use_subprocess=True)
print(proc.returncode)
```

The CLI flag is `--subprocess`.

## Where do parallel-worker results go?

`Parallel.run()` returns a list of results in **completion order**, not
submission order. To correlate a result with the config that produced
it, inspect each `Config.metadata` dict. The bare-file and `_sweep`
loaders include the swept axis values in `metadata` automatically.

## Can I read environment variables in my config?

Yes — it's a `.py` file, so you have full Python:

```python
import os

learning_rate = float(os.environ.get("LR", 0.001))
batch_size    = int(os.environ.get("BS", 32))
```

## Does `kogine config check` execute my script?

No. It imports the script's module under a non-`__main__` name so the
`if __name__ == "__main__":` guard does not fire. Module-level code
(including imports and module-level statements) still runs. If your
script has expensive module-level setup, consider moving it into a
function or behind a config cell — both keep introspection cheap.

## How do I avoid running expensive setup during introspection?

Use a config cell. The introspector evaluates only the cell body
(plus the preamble — imports that appear above it) and skips code below
the cell entirely. See [Config cells](guides/config-cells.md).

## Is KohakuEngine ready for production?

It is used for research workloads and small production pipelines. The
v0.x version number signals that public APIs may evolve based on user
feedback, but the current 0.2 line is stable enough for daily use.
Subscribe to the [changelog](changelog.md) for upgrade notes.

## How do I report a bug?

Open an issue at
[github.com/KohakuBlueleaf/KohakuEngine/issues](https://github.com/KohakuBlueleaf/KohakuEngine/issues)
with:

- The version (`kogine --version`).
- A minimal example reproducing the issue.
- The expected and actual behaviour.

## How do I contribute?

See the [Contributing guide](contributing.md). Small fixes are welcome
without prior discussion; larger changes should start with an issue.

## Where does the name come from?

"Kohaku" (琥珀) is Japanese for "amber." The maintainer's online
handle is *Kohaku-Blueleaf*. The CLI binary `kogine` is a portmanteau
of "Kohaku" and "engine."
