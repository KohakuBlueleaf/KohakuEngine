# Overrides and validation

This guide covers `--set`, `--strict`, schema-by-example coercion, and
the `kogine config check` pre-flight inspector.

## CLI overrides with `--set`

`--set KEY=VALUE` overrides a single configuration entry without
touching the config file:

```bash
kogine run train.py --set learning_rate=0.05
kogine run train.py --set learning_rate=0.05 --set batch_size=128
kogine run train.py --config base.py --set epochs=1
```

The flag can be repeated. Later flags override earlier ones for the
same key.

Inline overrides also apply when a config file is loaded — the `--set`
keys win over the file's values. `--set` composes with everything else:

| Combination                          | Result                                               |
| ------------------------------------ | ---------------------------------------------------- |
| `--config base.py --set k=v`         | One run; `k` overrides the file.                     |
| `--set k=v --sweep a=1,2`            | Two runs; every run carries `k`.                     |
| `--config gen.py --set k=v`          | One run per generated config, each carrying `k`.     |
| `--config gen.py --sweep a=1,2`      | Every generated config × every sweep value.          |
| `--set a=1 --sweep a=2,3`            | Error: a key cannot be both set and swept.           |

## Type coercion

CLI overrides arrive as strings. KohakuEngine coerces each one to the
type the **script** declares for that name:

1. The name's **top-level annotation**, if it has one (`lr: float = 1`).
2. Otherwise the **type of its default value** (`lr = 0.001` → `float`).
3. Otherwise (no annotation, `None` default, or a name the script does
   not define) the string is passed through unchanged.

Coercion happens when the script is loaded, against the script's own
namespace. Classes and Enums in annotations are therefore the exact
objects the script uses — `mode is Mode.EVAL` holds for a script-local
`Mode` Enum — and it works the same under `--subprocess` and parallel
workflows.

Given:

```python
# train.py
import enum
from pathlib import Path
from typing import Literal, Optional


class Mode(enum.Enum):
    TRAIN = "train"
    EVAL = "eval"


learning_rate: float = 1        # annotation wins: "0.5" -> 0.5
batch_size = 32                 # inferred int
dims = [64, 128]                # inferred list[int]
steps: Optional[int] = None     # "none" -> None, "100" -> 100
mode: Mode = Mode.TRAIN         # by name or value: "eval" -> Mode.EVAL
out_dir: Path = Path("runs")    # "ckpt/a" -> Path("ckpt/a")
optimizer: Literal["adam", "sgd"] = "adam"
```

Then:

```bash
kogine run train.py --set learning_rate=0.5 --set batch_size=128 \
                    --set dims=256,512 --set steps=100 --set mode=eval \
                    --set out_dir=ckpt/a --set optimizer=sgd
```

### Supported annotations

| Annotation                                   | Parsing of the string                                                        |
| -------------------------------------------- | ---------------------------------------------------------------------------- |
| `int`                                        | `int(s)`, then base prefixes (`0x10`), then integral floats (`1e3`); `0.5` fails |
| `float`, `complex`                           | `float(s)`, `complex(s)`                                                     |
| `str`, `bytes`                               | As is; `bytes` is UTF-8 encoded                                              |
| `bool`                                       | `true`, `1`, `yes`, `y`, `on` → True; `false`, `0`, `no`, `n`, `off` → False |
| `None`                                       | `none` / `null` (any case)                                                   |
| `Optional[T]`, `T \| None`, `Union[A, B]`    | `none`/`null` → `None`; else the members in declared order, first success wins |
| `Literal[...]`                               | Must equal one option (compared after coercing to the option's type)       |
| `list[T]`, `set[T]`, `frozenset[T]`, `tuple[T, ...]`, `Sequence[T]` | Python/JSON literal (`[1, 2]`) or comma list (`1,2`); elements coerced to `T` |
| `tuple[A, B]`                                | As above; length must match, elements coerced positionally                  |
| `dict[K, V]`, `Mapping[K, V]`                | Python/JSON literal or `k=v,k2=v2` / `k:v`; keys and values coerced         |
| `enum.Enum` subclass                         | Member name (exact, then case-insensitive, `Mode.EVAL` accepted) or value   |
| `Annotated[T, FormatArg(fn)]`                | `fn(s)`                                                                      |
| a class with `format_arg`                    | `Class.format_arg(s)`                                                        |
| `NewType`                                    | Its supertype                                                                |
| any other class                              | `Class(s)` (e.g. `Path`, `Decimal`)                                          |
| `Any`, `object`, `Callable`, ...             | Passed through                                                               |

Container elements are coerced recursively (`list[Optional[int]]`,
`dict[str, list[float]]`). `Final[T]` is treated as `T`.

When a name has **no annotation**, its default's type is used with two
refinements: homogeneous containers carry their element type
(`[64, 128]` → `list[int]`, `(1, "a")` → `tuple[int, str]`), and an
arbitrary class constructor is never called — only value types are
inferred (builtin scalars and containers, Enums, `pathlib` paths,
`numbers.Number` types, and classes with `format_arg`). Annotate the
name to opt any other class in.

### Custom parsing: `format_arg` and `FormatArg`

Give a class a `format_arg` classmethod to control how an override
string becomes an instance:

```python
class Dtype:
    def __init__(self, name: str) -> None:
        self.name = name

    @classmethod
    def format_arg(cls, arg: str) -> "Dtype":
        return cls(arg.lower())


dtype: Dtype = Dtype("fp32")   # --set dtype=BF16  ->  Dtype.format_arg("BF16")
```

For a type you cannot add a method to, attach the parser with
`typing.Annotated` and `FormatArg`:

```python
from typing import Annotated

import torch
from kohakuengine import FormatArg

dtype: Annotated[torch.dtype, FormatArg(lambda s: getattr(torch, s))] = torch.float32
# --set dtype=bfloat16  ->  torch.bfloat16
```

The parser receives the raw value (a `str` from the CLI) and is skipped
only when the value already is an instance of the annotated class and
not a string.

### Annotation resolution

Annotations are read from the script's top-level `name: T [= v]`
statements and evaluated in the script's namespace, so string
annotations and `from __future__ import annotations` work. An annotation
that cannot be evaluated (for example a name imported only under
`if TYPE_CHECKING:`) emits a `UserWarning` and the name falls back to
default-type inference.

An annotation-only line (`steps: int`, no value) declares a
configurable name without a default: it is accepted by `--strict`, and
an override gives it its value.

### Failures

If coercion fails, a `UserWarning` is emitted and the original string is
passed through. Pair with `--strict` to escalate failures to errors.

Only override values (`--set`, `--sweep`, `run(set_overrides=...)`) are
coerced. Values written in a config file are Python objects and are
injected exactly as written.

## Strict mode

```bash
kogine run train.py --set typo_key=1 --strict
```

`--strict` enforces two invariants:

1. Every `--set` / `--sweep` key, and every key of the loaded config
   file, must be declared by the script (a default or a top-level
   annotation). Unknown keys raise `KeyError` before anything runs, with
   a "did you mean" suggestion for near-misses. For a script with a
   config cell, the cell is the declared surface.
2. Coercion failures raise `TypeError` instead of warning and passing
   the value through.

Strict mode is recommended in CI and production launchers, where a
silent typo would otherwise be expensive to debug.

The Python API exposes the same flag:

```python
from kohakuengine import run

run("train.py", set_overrides={"learning_rate": "0.05"}, strict=True)
```

## Pre-flight validation

```bash
kogine config check train.py --config config.py
```

This command **does not run the script**. It loads the config, imports
the script under a non-`__main__` module name (so the entrypoint does not
fire), and diffs the keys.

Sample output:

```
Config: config.py    Script: train.py

  [OK]  batch_size: 32 -> 128
  [OK]  learning_rate: 0.001 (float) -> 0.05
  [??]  lr: not in script (did you mean learning_rate?)
  [+]   experiment_tag: new var (not in script defaults)

2 hits, 1 typo warning(s), 1 new var(s).
```

An annotated name shows its annotation in parentheses; an
annotation-only name shows `<no default>`.

Symbols:

| Symbol | Meaning                                                     |
| ------ | ----------------------------------------------------------- |
| `[OK]` | Config key matches a script default; override will apply.   |
| `[??]` | Config key is suspiciously close to a script default name.  |
| `[+]`  | Config key does not match any default and is not a typo.    |

The exit code is `0` when no typo warnings are present, `1` otherwise.
This makes the command suitable for use in a CI step:

```yaml
- run: kogine config check train.py --config production.py
```

### How it works under the hood

- For scripts **without** a config cell: introspection imports the
  module under a `_kogine_introspect_*` name (so the `if __name__ ==
  "__main__":` guard does not fire), and `_filter_globals` extracts the
  data-valued attributes.
- For scripts **with** a config cell: the introspector evaluates only
  the cell plus its preamble (imports above the cell). Code below the
  cell does not execute. This is fully side-effect-free for the cell
  body itself.

The cell case is the authoritative form: only names declared in the
cell are recognised as the configurable surface, sharpening the typo
detection.

## Showing the lowered Config

To inspect what KohakuEngine actually builds from a config file:

```bash
kogine config show config.py
```

```
Config: config.py
Source style: bare-file (auto-captured globals)

Lowered to Config:
  globals_dict:
    learning_rate: 0.05  (float)
    batch_size: 128  (int)
    epochs: 5  (int)
  args:     []
  kwargs:   {}
```

For a sweep file, every expanded config is printed:

```
Config: sweep.py
Source style: generator / sweep
Total configs: 6

--- Config 1/6 ---
  globals_dict:
    epochs: 5  (int)
    learning_rate: 0.001  (float)
    batch_size: 32  (int)
  ...
```

## Programmatic equivalents

```python
from kohakuengine import coerce_globals, coerce_value, introspect_schema, run

# Defaults + annotations of a script
schema = introspect_schema("train.py")

# Coerce a dict of strings against that schema
coerced = coerce_globals(
    {"learning_rate": "0.05"}, schema.defaults, annotations=schema.annotations
)

# Coerce one value against one annotation
coerce_value("1,2", list[int])   # [1, 2]

# All-in-one
run("train.py", set_overrides={"learning_rate": "0.05"}, strict=True)
```
