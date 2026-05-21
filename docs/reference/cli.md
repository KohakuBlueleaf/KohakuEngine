# Command-line interface reference

The `kogine` command is installed by `pip install kohaku-engine` and is
the primary way to run scripts and inspect configurations from the
shell.

## Synopsis

```
kogine [--version] [--help] <command> [args...]
```

## Global flags

| Flag         | Description                                       |
| ------------ | ------------------------------------------------- |
| `--version`  | Print the installed version and exit.             |
| `--help`     | Print usage information and exit.                 |

## Commands

### `kogine run`

Execute a single script.

```
kogine run SCRIPT [--config CFG] [--entrypoint NAME]
                  [--set KEY=VALUE]... [--sweep KEY=V1,V2,...]...
                  [--strict] [--subprocess]
```

| Argument / flag       | Description                                              |
| --------------------- | -------------------------------------------------------- |
| `SCRIPT`              | Path to a `.py` file, `path.py:func`, or `package.module`. |
| `--config`, `-c`      | Path to a Python config file.                            |
| `--entrypoint`, `-e`  | Explicit entrypoint name (overrides discovery cascade).  |
| `--set KEY=VALUE`     | Override one config key. Repeatable. Type-coerced.       |
| `--sweep KEY=V1,V2`   | Sweep one axis. Repeatable; multiple flags compose as cartesian product. |
| `--strict`            | Error on overrides that do not match a script default.   |
| `--subprocess`        | Run the script in a fresh subprocess via the CLI.        |

**Examples:**

```bash
kogine run train.py
kogine run train.py --config production.py
kogine run train.py --set learning_rate=0.05 --set batch_size=128
kogine run train.py --sweep learning_rate=0.001,0.01,0.1
kogine run train.py --config base.py --set epochs=1 --strict
kogine run train.py:custom_train
kogine run package.module --entrypoint go
```

**Exit codes:**

| Code | Meaning                                                  |
| ---- | -------------------------------------------------------- |
| `0`  | Success.                                                 |
| `2`  | No entrypoint found in the script.                       |
| other| Propagated from a failing subprocess.                    |

### `kogine workflow sequential`

Run multiple scripts in order.

```
kogine workflow sequential SCRIPT [SCRIPT...] [--config CFG]
```

| Argument / flag  | Description                                          |
| ---------------- | ---------------------------------------------------- |
| `SCRIPT`         | One or more script paths.                            |
| `--config`, `-c` | Single config file applied to every script.          |

**Example:**

```bash
kogine workflow sequential preprocess.py train.py evaluate.py
```

### `kogine workflow parallel`

Run multiple scripts (or generator iterations) concurrently.

```
kogine workflow parallel SCRIPT [SCRIPT...] [--config CFG]
                                [--workers N] [--mode MODE]
```

| Argument / flag  | Description                                            |
| ---------------- | ------------------------------------------------------ |
| `SCRIPT`         | One or more script paths.                              |
| `--config`, `-c` | Single config file (often a sweep) applied to every script. |
| `--workers`, `-w`| Maximum concurrent workers (default: CPU count).       |
| `--mode`         | `subprocess` (default) or `pool` (in-process).         |

**Example:**

```bash
kogine workflow parallel train.py --config sweep.py --workers 4
```

### `kogine config validate`

Verify that a config file loads cleanly. Reports the resolved type.

```
kogine config validate CFG
```

**Example:**

```bash
kogine config validate config.py
```

Output:

```
Config valid: config.py
  Type: Config
```

For sweeps the type is `ConfigGenerator`.

### `kogine config show`

Print the lowered form of a config — exactly what KohakuEngine would
inject. For sweeps, every expanded `Config` is printed.

```
kogine config show CFG
```

Output (bare file):

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

Output (sweep):

```
Config: sweep.py
Source style: generator / sweep
Total configs: 6

--- Config 1/6 ---
  globals_dict:
    epochs: 5  (int)
    learning_rate: 0.001  (float)
    batch_size: 32  (int)
  args:     []
  kwargs:   {}
  metadata: {'learning_rate': 0.001, 'batch_size': 32}
...
```

### `kogine config check`

Diff config keys against script defaults. Does not execute the script.

```
kogine config check SCRIPT --config CFG
```

| Argument / flag  | Description                                          |
| ---------------- | ---------------------------------------------------- |
| `SCRIPT`         | Path to the script whose defaults define the schema. |
| `--config`, `-c` | (required) Path to the config to validate.           |

**Example:**

```bash
kogine config check train.py --config production.py
```

Output:

```
Config: production.py    Script: train.py

  [OK]  batch_size: 32 -> 128
  [OK]  learning_rate: 0.001 -> 0.05
  [??]  lr: not in script (did you mean learning_rate?)
  [+]   experiment_tag: new var (not in script defaults)

2 hits, 1 typo warning(s), 1 new var(s).
```

| Symbol | Meaning                                                |
| ------ | ------------------------------------------------------ |
| `[OK]` | Config key matches a script default.                   |
| `[??]` | Config key is suspiciously close to a script default.  |
| `[+]`  | Config key does not match anything.                    |

**Exit codes:**

| Code | Meaning                                              |
| ---- | ---------------------------------------------------- |
| `0`  | All overrides recognised (no typo warnings).         |
| `1`  | At least one typo warning detected.                  |
| `2`  | Script file not found.                               |

Suitable for inclusion in CI:

```yaml
- run: kogine config check train.py --config production.py
```

## Environment variables

| Variable             | Set by KohakuEngine | Read by | Purpose                          |
| -------------------- | ------------------- | ------- | -------------------------------- |
| `KOGINE_WORKER_ID`   | Parallel workflows  | `config_gen(worker_id=None)` | Per-worker context (GPU pick, seed offset, output dir). |

The variable contains a decimal worker index (`"0"`, `"1"`, ...). When
not set, your `config_gen` should treat the worker id as `0`.

## Shell completion

Not currently shipped. The argparse-based parser supports
`argcomplete` if you install and configure it externally.
