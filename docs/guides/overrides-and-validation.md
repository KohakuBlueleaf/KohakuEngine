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
keys win over the file's values.

## Schema-by-example type coercion

CLI overrides arrive as strings. KohakuEngine uses the *script's own
defaults* as a type schema and coerces incoming values automatically.

Given:

```python
# train.py
learning_rate = 0.001   # float
batch_size    = 32      # int
device        = "cpu"   # str
use_amp       = False   # bool
```

Then:

```bash
kogine run train.py --set learning_rate=0.05 \
                    --set batch_size=128 \
                    --set device=cuda \
                    --set use_amp=true
```

The coercer maps:

| Default type | Coercion                                                            |
| ------------ | ------------------------------------------------------------------- |
| `int`        | `int(value)`                                                        |
| `float`      | `float(value)`                                                      |
| `str`        | `str(value)`                                                        |
| `bool`       | `true`, `1`, `yes`, `y`, `on` → True; `false`, `0`, `no`, `n`, `off` → False |
| Anything else| Passed through unchanged                                            |

If coercion fails, a `UserWarning` is emitted and the original value is
passed through. Pair with `--strict` to escalate failures to errors.

## Strict mode

```bash
kogine run train.py --set typo_key=1 --strict
```

`--strict` enforces two invariants:

1. Every `--set` key must match a script default. Unknown keys raise.
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
  [OK]  learning_rate: 0.001 -> 0.05
  [??]  lr: not in script (did you mean learning_rate?)
  [+]   experiment_tag: new var (not in script defaults)

2 hits, 1 typo warning(s), 1 new var(s).
```

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
from kohakuengine import coerce_globals, introspect, run

# Introspect a script
defaults = introspect("train.py")

# Coerce a dict of strings against those defaults
coerced = coerce_globals({"learning_rate": "0.05"}, defaults)

# All-in-one
run("train.py", set_overrides={"learning_rate": "0.05"}, strict=True)
```
