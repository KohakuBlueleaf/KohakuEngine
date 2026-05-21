# Entrypoint discovery and the `@entrypoint` decorator

KohakuEngine has to decide which function in your script to call. This
guide documents the discovery cascade and the ways you can influence it.

## The cascade

KohakuEngine tries each of the following in order; the first match wins.

1. **`--entrypoint NAME` CLI flag** — explicit override.
2. **`script.py:func` colon syntax** — explicit override for a single
   script path.
3. **`@kogine.entrypoint` decorator** — explicit marker in source.
4. **AST detection of `if __name__ == "__main__":`** — KohakuEngine
   parses the script and looks for a single function call in that block.
5. **`main()`** — conventional name.
6. **`run()`** — conventional name.
7. **Error** — `EntrypointNotFound` with a diagnostic listing every name
   that was searched.

## Five idiomatic patterns

### Pattern A: existing script with `if __name__ == "__main__":`

```python
def train():
    ...

if __name__ == "__main__":
    train()
```

Works without any KohakuEngine knowledge. The AST detector finds `train`.

### Pattern B: `@kogine.entrypoint` decorator

```python
import kohakuengine as kogine


@kogine.entrypoint
def train():
    ...


def helper():
    ...
```

The decorator removes all ambiguity. It is preferred when:

- The script has several plausible entrypoints.
- The script does not have (or should not have) an `if __name__` block.
- You want the entrypoint to be greppable.

### Pattern C: convention-by-name

```python
def main():
    ...
```

No decorator or guard required. KohakuEngine finds `main()` by name.
The same holds for `run()`.

### Pattern D: explicit colon syntax

```bash
kogine run train.py:custom_train
```

Calls `custom_train()` instead of whatever the cascade would pick.

### Pattern E: CLI flag override

```bash
kogine run train.py --entrypoint custom_train
```

Equivalent to the colon form, but separates the path from the entrypoint
name. Useful in shell scripts that pass `$SCRIPT` and `$ENTRY`
separately.

## The decorator API

```python
import kohakuengine as kogine

@kogine.entrypoint
def train(): ...

@kogine.entrypoint(name="alias")
def train_v2(): ...
```

The decorator sets a marker attribute (`__kogine_entrypoint__ = True`).
Direct execution (`python train.py`) is unaffected — the marker is
inert outside KohakuEngine.

## Async entrypoints

KohakuEngine detects coroutine functions automatically and runs them via
`asyncio.run`:

```python
import asyncio


async def main():
    await asyncio.sleep(0)


if __name__ == "__main__":
    asyncio.run(main())
```

The AST detector also recognises the `asyncio.run(func())` pattern inside
the `__main__` block.

## Multiple decorated functions

If two or more functions carry `@kogine.entrypoint`, KohakuEngine raises
`MultipleEntrypoints` with the list of candidates. Resolve by removing
one decorator or by passing `--entrypoint NAME` to disambiguate.

## Diagnostic on failure

When the cascade finds nothing, the error message lists every name that
was searched:

```
EntrypointNotFound: No entrypoint found in train.py.
Searched (in priority order):
  - @kogine.entrypoint decorator: not found
  - if __name__ == "__main__": block: not found
  - main(): not found
  - run(): not found
Hint: add @kogine.entrypoint to your function, or pass --entrypoint NAME.
```

This makes it easy to diagnose typos and to confirm which form
KohakuEngine actually examines.
