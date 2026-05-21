# Contributing

Thank you for considering a contribution to KohakuEngine. This document
covers the development setup, repository conventions, and the
pull-request workflow.

## Before you start

- **Discuss large changes first.** Open an issue describing the problem
  and the proposed direction before investing significant time. Small
  fixes (typos, focused bug fixes, additional tests) can go straight to
  a pull request.
- **Match the project's scope.** KohakuEngine intentionally avoids
  becoming a heavyweight workflow engine, a schema validator, or a
  cluster orchestrator. See [Concepts § Non-goals](concepts.md#non-goals).

## Development setup

Clone the repository and install in editable mode with the development
extras:

```bash
git clone https://github.com/KohakuBlueleaf/KohakuEngine.git
cd KohakuEngine
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Verify the install:

```bash
kogine --version
pytest -q
```

The test suite runs in a few seconds and should report all tests
passing.

## Repository layout

| Directory               | Purpose                                                |
| ----------------------- | ------------------------------------------------------ |
| `src/kohakuengine/`     | Library source.                                        |
| `tests/`                | Pytest test suite, mirroring `src/` structure.         |
| `docs/`                 | Documentation (this site).                             |
| `examples/`             | Runnable example scripts and configs.                  |
| `plans/`                | Historical design plans. Read-only reference.          |

See [Architecture](architecture.md) for the module map.

## Coding conventions

The project enforces a small set of rules consistently:

- **Python 3.10+.** Use modern syntax (`X | Y` unions, `list[X]`,
  PEP 604).
- **No `from __future__` imports.** Not necessary on 3.10+.
- **No imports inside function or method bodies.** All imports live at
  module top level, or under `if TYPE_CHECKING:` for cycle-breaking
  forward references.
- **Black formatting.** Run `black src tests examples` before committing.
  Line length 88. The `[tool.black]` section of `pyproject.toml` is the
  source of truth.
- **No silent failures.** Every error path either returns a documented
  sentinel or raises an exception with enough context to fix the issue.
- **Type hints on public APIs.** Internal helpers may omit them when
  the signature is self-evident.
- **Docstrings on public functions and classes.** Keep them short and
  focused; cross-reference longer explanations in `docs/`.

## Testing

Tests live in `tests/`, mirroring the source tree:

```
tests/
├── conftest.py
├── test_main.py
├── test_cli.py
├── test_utils.py
├── test_types.py
├── test_coverage_edges.py
├── test_config/
│   ├── test_base.py
│   ├── test_generator.py
│   └── test_loader.py
├── test_engine/
│   ├── test_cell.py
│   ├── test_coerce.py
│   ├── test_entrypoint.py
│   ├── test_executor.py
│   ├── test_injector.py
│   ├── test_introspect.py
│   └── test_script.py
└── test_flow/
    ├── test_flow.py
    ├── test_parallel.py
    └── test_sequential.py
```

Common commands:

```bash
pytest -q                                              # quick run
pytest --cov=kohakuengine --cov-report=term-missing    # with coverage
pytest -k "test_cell" -v                               # filter by name
pytest tests/test_engine/test_cell.py                  # one file
```

**Coverage target:** 100% line coverage on `src/kohakuengine/`. The
existing suite holds this invariant. New code must come with tests that
maintain it. Defensive error paths that are impossible to trigger in
realistic scenarios may be marked `# pragma: no cover` with a short
comment.

**Fixtures:** `tests/conftest.py` provides `make_script`,
`make_config`, `simple_script`, `args_script`, `simple_config`, and
`bare_config`. Prefer these over ad-hoc file creation.

## Formatting

```bash
black src tests examples
```

Black runs without arguments configured by `pyproject.toml`. The CI
equivalent for verification only:

```bash
black --check src tests examples
```

## Documentation

Documentation lives in `docs/` and follows the
[Diátaxis](https://diataxis.fr/) framework:

- **Tutorials** (`tutorial.md`, `quickstart.md`) — learning-oriented.
- **How-to guides** (`guides/*.md`) — task-oriented.
- **Reference** (`reference/*.md`) — information-oriented.
- **Explanation** (`concepts.md`, `architecture.md`) — understanding-oriented.

When you add or change a public API:

1. Update the relevant `docs/reference/*.md` page.
2. If the feature is user-facing, add or update a how-to guide.
3. If the change is large enough to discuss, add a note to
   `docs/changelog.md`.

Documentation snippets that should always work are exercised by the
test suite where possible. Avoid quoting CLI output that depends on
exact path strings.

## Pull-request workflow

1. **Fork** the repository and create a feature branch off `main`.
2. **Write tests first** for new behaviour, or alongside the change for
   bug fixes.
3. **Run the full suite** locally: `pytest --cov=kohakuengine`.
4. **Run Black**: `black src tests examples`.
5. **Update documentation** if your change is user-visible.
6. **Open a pull request** with:
   - A clear title (`fix:`, `feat:`, `docs:`, `refactor:` prefixes are
     encouraged but not required).
   - A short description of the problem and the chosen solution.
   - A link to the issue if one exists.

Reviewers may request changes around scope, naming, or test coverage
before merging.

## Commit messages

Short, imperative summaries on the first line. The body, if present,
explains the *why* rather than the *what* (the diff already shows the
what). Reference issues with `#NNN`.

Example:

```
Avoid re-evaluating expensive cells across kogine introspect+run

The CLI's --set flag invokes introspect() to obtain script defaults for
coercion, then ScriptExecutor re-runs the cell during execution. This
re-evaluation defeats the "evaluate-once" promise of config cells. Add
a per-(path, mtime) memoization to evaluate_cell so the two callers
share work within one process.

Closes #42.
```

## Release process

Maintainers cut releases by:

1. Bumping `[project] version` in `pyproject.toml`.
2. Updating `docs/changelog.md`.
3. Tagging the commit `vX.Y.Z` and pushing the tag.
4. Building with `python -m build`.
5. Verifying with `python -m twine check dist/*`.
6. Uploading to PyPI with `python -m twine upload dist/*`.

Contributors do not need to perform these steps. Mentioning the
intended version in the PR description is welcome but not required.

## Code of conduct

Be civil, give the benefit of the doubt, and assume good intent.
Disagreements should be technical, not personal. Maintainers reserve
the right to close discussions that become unproductive.

## License

Contributions are accepted under the project's Apache-2.0 license. By
opening a pull request you certify that you have the right to license
your contribution under those terms.
