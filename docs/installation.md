# Installation

## Requirements

- Python 3.10 or newer.
- An operating system that supports CPython. KohakuEngine is tested on
  Windows and Linux; macOS is expected to work without modification.

KohakuEngine has **no runtime dependencies** outside the Python standard
library. The optional `examples` extra pulls in `OmegaConf` and `toml` for
the demonstration configurations only.

## Install from PyPI

```bash
pip install kohaku-engine
```

This installs the `kohakuengine` Python package and the `kogine`
command-line script.

## Install from source

Clone the repository and install in editable mode:

```bash
git clone https://github.com/KohakuBlueleaf/KohakuEngine.git
cd KohakuEngine
pip install -e .
```

Install the development extras (test runner, formatter, build backend) if
you intend to contribute:

```bash
pip install -e ".[dev]"
```

## Verify the installation

```bash
kogine --version
```

This should print the installed version, for example:

```
kogine 0.2.0
```

You can also verify the Python import:

```python
import kohakuengine
print(kohakuengine.__version__)
```

## Next steps

- Run the [Quickstart](quickstart.md) for a five-minute introduction.
- Work through the [Tutorial](tutorial.md) for a complete walk-through.
