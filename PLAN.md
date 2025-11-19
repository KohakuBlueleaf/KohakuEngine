# KohakuEngine: Technical Architecture and Implementation Plan

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Module Structure](#module-structure)
3. [Config System](#config-system)
4. [Engine System](#engine-system)
5. [Flow System](#flow-system)
6. [API Design](#api-design)
7. [CLI Design](#cli-design)
8. [Implementation Details](#implementation-details)
9. [Testing Strategy](#testing-strategy)
10. [Examples](#examples)

---

## Architecture Overview

### High-Level Design

KohakuEngine is structured into three main subsystems:

```
┌─────────────────────────────────────────────────┐
│              KohakuEngine                       │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐     │
│  │  CONFIG  │   │  ENGINE  │   │   FLOW   │     │
│  │  System  │ → │  System  │ → │  System  │     │
│  └──────────┘   └──────────┘   └──────────┘     │
│       │              │              │           │
│       └──────────────┴──────────────┘           │
│                      │                          │
│            ┌─────────┴─────────┐                │
│            │                   │                │
│       ┌────▼────┐          ┌───▼────┐           │
│       │   CLI   │          │  API   │           │
│       └─────────┘          └────────┘           │
└─────────────────────────────────────────────────┘
```

### Design Principles

1. **Separation of Concerns**
   - `config/`: Pure configuration logic
   - `engine/`: Pure execution logic
   - `flow/`: Pure orchestration logic
   - No circular dependencies

2. **Layered Architecture**
   - Low-level: config + engine (independent)
   - Mid-level: flow (depends on config + engine)
   - High-level: CLI + API (depends on all)

3. **Dependency Flow**
   ```
   CLI/API → Flow → Engine → Config
                  ↘ Config ↗
   ```

---

## Module Structure

### Directory Layout

```
src/kohakuengine/
├── __init__.py              # Public API exports
├── utils.py                 # Global utilities
├── cli.py                   # CLI entry point
├── main.py                  # Python API entry point
│
├── config/                  # Configuration System
│   ├── __init__.py         # Export: Config, ConfigGenerator
│   ├── base.py             # Config dataclass
│   ├── generator.py        # ConfigGenerator wrapper
│   ├── loader.py           # Load Python config files
│   └── types.py            # Type definitions
│
├── engine/                  # Execution System
│   ├── __init__.py         # Export: Script, Executor
│   ├── script.py           # Script class
│   ├── executor.py         # Core execution orchestration
│   ├── injector.py         # Global variable injection
│   └── entrypoint.py       # Entrypoint discovery/calling
│
└── flow/                    # Workflow System
    ├── __init__.py         # Export: Sequential, Parallel, Pipeline
    ├── base.py             # Base workflow classes
    ├── sequential.py       # Sequential execution
    ├── parallel.py         # Parallel execution (subprocess)
    └── pipeline.py         # Pipeline abstraction
```

### Module Dependencies

```python
# config/ - No internal dependencies
config.base → (no deps)
config.generator → config.base
config.loader → config.base, config.generator
config.types → (typing only)

# engine/ - Depends on config/
engine.script → config.base, config.generator
engine.injector → (no deps)
engine.entrypoint → (no deps)
engine.executor → engine.{script,injector,entrypoint}, config.base

# flow/ - Depends on engine/ and config/
flow.base → engine.script, config.base
flow.sequential → flow.base, engine.executor
flow.parallel → flow.base, engine.executor
flow.pipeline → flow.base

# Top-level - Depends on all
cli → flow.*, engine.*, config.*
main → flow.*, engine.*, config.*
```

---

## Config System

### Design Goals

1. **Python-first**: Configs ARE Python code
2. **Flexible**: Support objects, classes, functions
3. **Iterative**: Generator-based for dynamic configs
4. **Simple**: Minimal boilerplate

### Module: `config/base.py`

**Purpose**: Core config data structures

```python
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class Config:
    """
    Configuration for script execution.

    Attributes:
        globals_dict: Module-level global variables to override
        args: Positional arguments for entrypoint function
        kwargs: Keyword arguments for entrypoint function
        metadata: Optional metadata for tracking/logging
    """
    globals_dict: Dict[str, Any] = field(default_factory=dict)
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        """Validate config structure."""
        if not isinstance(self.globals_dict, dict):
            raise TypeError("globals_dict must be a dict")
        if not isinstance(self.args, (list, tuple)):
            raise TypeError("args must be a list or tuple")
        if not isinstance(self.kwargs, dict):
            raise TypeError("kwargs must be a dict")
```

**Design Notes**:
- `globals_dict`: Explicit dict mapping for global vars
  - Keys are variable names (strings)
  - Values are arbitrary Python objects
  - Alternative: Use `globals()` in config and filter defaults
- `args`/`kwargs`: For entrypoint function
- `metadata`: User-extensible, for tracking experiments

### Module: `config/generator.py`

**Purpose**: Wrap generators for iterative configs

```python
from typing import Generator, Iterator, Optional
from .base import Config

class ConfigGenerator:
    """
    Wrapper for config generators.

    Supports both:
    1. Generator functions (yield)
    2. Iterator protocol (__iter__, __next__)
    """

    def __init__(self, generator: Generator[Config, None, None] | Iterator[Config]):
        """
        Args:
            generator: Generator or iterator yielding Config objects
        """
        self._generator = generator
        self._exhausted = False

    def __iter__(self) -> Iterator[Config]:
        """Return iterator."""
        return self

    def __next__(self) -> Config:
        """Get next config."""
        if self._exhausted:
            raise StopIteration("Config generator exhausted")

        try:
            config = next(self._generator)
            if not isinstance(config, Config):
                raise TypeError(f"Generator must yield Config objects, got {type(config)}")
            return config
        except StopIteration:
            self._exhausted = True
            raise

    @property
    def exhausted(self) -> bool:
        """Check if generator is exhausted."""
        return self._exhausted
```

**Usage Pattern**:
```python
def my_config_gen():
    for lr in [0.001, 0.01, 0.1]:
        yield Config(globals_dict={'learning_rate': lr})

gen = ConfigGenerator(my_config_gen())

# Iteration 1
config1 = next(gen)  # Config(globals_dict={'learning_rate': 0.001})
# Execute script with config1

# Iteration 2
config2 = next(gen)  # Config(globals_dict={'learning_rate': 0.01})
# Execute script with config2

# ...until StopIteration
```

### Module: `config/loader.py`

**Purpose**: Load configs from Python files

```python
import importlib.util
import sys
from pathlib import Path
from typing import Callable, Union
from .base import Config
from .generator import ConfigGenerator

class ConfigLoader:
    """Load configuration from Python files."""

    @staticmethod
    def load_config(config_path: Union[str, Path]) -> Config | ConfigGenerator:
        """
        Load config from Python file.

        Expected formats:
        1. config_gen() function returning Config
        2. config_gen() generator yielding Config objects
        3. CONFIG variable (Config instance)

        Args:
            config_path: Path to Python config file

        Returns:
            Config or ConfigGenerator

        Raises:
            FileNotFoundError: Config file not found
            ValueError: Invalid config format
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Load module dynamically
        spec = importlib.util.spec_from_file_location("config_module", config_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Cannot load config from {config_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules["config_module"] = module
        spec.loader.exec_module(module)

        # Try to find config
        if hasattr(module, 'config_gen'):
            config_gen = module.config_gen
            if not callable(config_gen):
                raise ValueError("config_gen must be callable")

            # Call config_gen
            result = config_gen()

            # Check if it's a generator or Config
            if isinstance(result, Config):
                return result
            elif hasattr(result, '__iter__') and hasattr(result, '__next__'):
                # It's a generator/iterator
                return ConfigGenerator(result)
            else:
                raise ValueError(
                    f"config_gen() must return Config or generator, got {type(result)}"
                )

        elif hasattr(module, 'CONFIG'):
            config = module.CONFIG
            if not isinstance(config, Config):
                raise ValueError(f"CONFIG must be Config instance, got {type(config)}")
            return config

        else:
            raise ValueError(
                "Config file must define 'config_gen()' function or 'CONFIG' variable"
            )

    @staticmethod
    def load_from_dict(data: dict) -> Config:
        """
        Create Config from dictionary.

        Useful for loading from JSON/TOML/YAML parsed data.
        Users should parse external formats themselves in config.py.
        """
        return Config(
            globals_dict=data.get('globals', {}),
            args=data.get('args', []),
            kwargs=data.get('kwargs', {}),
            metadata=data.get('metadata', {})
        )
```

**Example Config Files**:

```python
# examples/configs/simple_config.py
from kohakuengine.config import Config

def config_gen():
    return Config(
        globals_dict={
            'learning_rate': 0.001,
            'batch_size': 32,
            'epochs': 100
        },
        kwargs={'device': 'cuda'}
    )
```

```python
# examples/configs/sweep_config.py
from kohakuengine.config import Config

def config_gen():
    """Generator for hyperparameter sweep."""
    for lr in [0.001, 0.01, 0.1]:
        for bs in [16, 32, 64]:
            yield Config(
                globals_dict={
                    'learning_rate': lr,
                    'batch_size': bs
                },
                kwargs={
                    'experiment_name': f'lr{lr}_bs{bs}'
                },
                metadata={
                    'sweep': 'lr_bs',
                    'lr': lr,
                    'bs': bs
                }
            )
```

```python
# examples/configs/resume_config.py
from pathlib import Path
from kohakuengine.config import Config

def find_latest_checkpoint():
    """Find latest checkpoint file."""
    ckpt_dir = Path('./checkpoints')
    if not ckpt_dir.exists():
        return None
    ckpts = list(ckpt_dir.glob('epoch_*.pt'))
    if not ckpts:
        return None
    return max(ckpts, key=lambda p: p.stat().st_mtime)

def config_gen():
    """Iterative config for training with checkpoints."""
    for epoch in range(100):
        ckpt_path = find_latest_checkpoint()
        yield Config(
            globals_dict={
                'checkpoint_path': str(ckpt_path) if ckpt_path else None,
                'current_epoch': epoch,
                'max_epochs': epoch + 1  # Train one epoch at a time
            }
        )
```

```python
# examples/configs/external_format_config.py
import json
from pathlib import Path
from kohakuengine.config import Config

def config_gen():
    """Load from external JSON and convert to Config."""
    # User manages their own parsing
    with open('my_config.json') as f:
        data = json.load(f)

    return Config(
        globals_dict=data['globals'],
        args=data.get('args', []),
        kwargs=data.get('kwargs', {})
    )
```

### Module: `config/types.py`

**Purpose**: Type definitions and protocols

```python
from typing import Protocol, Iterator, Any
from .base import Config

class ConfigProvider(Protocol):
    """Protocol for objects that provide configs."""

    def get_config(self) -> Config | Iterator[Config]:
        """Get config or config iterator."""
        ...

class Configurable(Protocol):
    """Protocol for objects that accept configs."""

    def apply_config(self, config: Config) -> None:
        """Apply configuration."""
        ...
```

---

## Engine System

### Design Goals

1. **Non-invasive**: Work with existing scripts
2. **Isolated**: Proper module import/execution
3. **Flexible**: Support various entrypoint patterns
4. **Debuggable**: Clear error messages

### Module: `engine/script.py`

**Purpose**: Script representation

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union
from ..config.base import Config
from ..config.generator import ConfigGenerator

@dataclass
class Script:
    """
    Represents an executable Python script.

    Attributes:
        path: Path to Python script file
        config: Configuration (Config or ConfigGenerator)
        entrypoint: Name of entrypoint function (default: auto-detect)
        run_as_main: Execute as __main__ process (default: True)
    """
    path: Union[str, Path]
    config: Optional[Config | ConfigGenerator] = None
    entrypoint: Optional[str] = None
    run_as_main: bool = True

    def __post_init__(self):
        """Validate script path."""
        self.path = Path(self.path)
        if not self.path.exists():
            raise FileNotFoundError(f"Script not found: {self.path}")
        if self.path.suffix != '.py':
            raise ValueError(f"Script must be .py file: {self.path}")

    @property
    def name(self) -> str:
        """Get script name (filename without extension)."""
        return self.path.stem

    def __repr__(self) -> str:
        return f"Script(path={self.path}, config={type(self.config).__name__})"
```

### Module: `engine/injector.py`

**Purpose**: Inject global variables into script module

```python
import sys
from types import ModuleType
from typing import Dict, Any

class GlobalInjector:
    """Inject global variables into Python modules."""

    @staticmethod
    def inject(module: ModuleType, globals_dict: Dict[str, Any]) -> None:
        """
        Inject global variables into module.

        Args:
            module: Target module
            globals_dict: Dict of {var_name: value} to inject

        Raises:
            ValueError: If trying to override built-in names
        """
        # Blacklist of names we should never override
        PROTECTED_NAMES = {
            '__name__', '__file__', '__package__', '__loader__',
            '__spec__', '__cached__', '__builtins__'
        }

        for name, value in globals_dict.items():
            if name in PROTECTED_NAMES:
                raise ValueError(
                    f"Cannot override protected module attribute: {name}"
                )

            # Set attribute on module
            setattr(module, name, value)

    @staticmethod
    def get_user_globals(module: ModuleType) -> Dict[str, Any]:
        """
        Extract user-defined globals from module.

        Filters out built-in attributes, imports, and functions.
        Useful for inspecting what's available to override.

        Args:
            module: Module to inspect

        Returns:
            Dict of user-defined global variables
        """
        user_globals = {}

        for name in dir(module):
            # Skip private/protected
            if name.startswith('_'):
                continue

            value = getattr(module, name)

            # Skip modules, functions, classes (keep only data)
            if isinstance(value, (ModuleType, type)):
                continue
            if callable(value):
                continue

            user_globals[name] = value

        return user_globals
```

### Module: `engine/entrypoint.py`

**Purpose**: Discover and call script entrypoints

```python
import ast
import inspect
from pathlib import Path
from types import ModuleType
from typing import Optional, Callable, Any, List, Dict

class EntrypointFinder:
    """Find and call script entrypoints."""

    @staticmethod
    def find_entrypoint(module: ModuleType, script_path: Path) -> Optional[Callable]:
        """
        Find entrypoint function in script.

        Strategy:
        1. Look for function defined in `if __name__ == "__main__"` block
        2. Look for `main()` function
        3. Return None if not found

        Args:
            module: Loaded module
            script_path: Path to script file (for AST parsing)

        Returns:
            Entrypoint function or None
        """
        # Parse AST to find if __name__ == "__main__" block
        with open(script_path) as f:
            tree = ast.parse(f.read(), filename=str(script_path))

        entrypoint_name = EntrypointFinder._find_main_block_function(tree)

        if entrypoint_name and hasattr(module, entrypoint_name):
            return getattr(module, entrypoint_name)

        # Fallback: look for main() function
        if hasattr(module, 'main') and callable(module.main):
            return module.main

        return None

    @staticmethod
    def _find_main_block_function(tree: ast.AST) -> Optional[str]:
        """
        Find function called in if __name__ == "__main__" block.

        Looks for pattern:
            if __name__ == "__main__":
                some_function()

        Returns function name.
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check if condition is __name__ == "__main__"
                if EntrypointFinder._is_main_guard(node.test):
                    # Find function calls in body
                    for stmt in node.body:
                        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                            if isinstance(stmt.value.func, ast.Name):
                                return stmt.value.func.id
        return None

    @staticmethod
    def _is_main_guard(node: ast.expr) -> bool:
        """Check if node is __name__ == "__main__" comparison."""
        if not isinstance(node, ast.Compare):
            return False

        # Check for __name__ on left side
        if not (isinstance(node.left, ast.Name) and node.left.id == '__name__'):
            return False

        # Check for == operator
        if not (len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq)):
            return False

        # Check for "__main__" on right side
        if not (len(node.comparators) == 1 and
                isinstance(node.comparators[0], ast.Constant) and
                node.comparators[0].value == '__main__'):
            return False

        return True

    @staticmethod
    def call_entrypoint(
        func: Callable,
        args: List[Any],
        kwargs: Dict[str, Any]
    ) -> Any:
        """
        Call entrypoint with args/kwargs.

        Handles functions that don't accept args/kwargs gracefully.

        Args:
            func: Function to call
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Function return value
        """
        # Inspect function signature
        sig = inspect.signature(func)

        # Check if function accepts args
        params = sig.parameters
        has_var_positional = any(p.kind == inspect.Parameter.VAR_POSITIONAL
                                  for p in params.values())
        has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD
                             for p in params.values())

        # Prepare call arguments
        call_args = args if (has_var_positional or len(params) > 0) else []
        call_kwargs = kwargs if has_var_keyword else {}

        # If function has named parameters, try to match kwargs
        if not has_var_keyword and kwargs:
            call_kwargs = {k: v for k, v in kwargs.items() if k in params}

        return func(*call_args, **call_kwargs)
```

### Module: `engine/executor.py`

**Purpose**: Orchestrate script execution

```python
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Optional
from .script import Script
from .injector import GlobalInjector
from .entrypoint import EntrypointFinder
from ..config.base import Config

class ScriptExecutor:
    """Execute Python scripts with configuration."""

    def __init__(self, script: Script):
        """
        Args:
            script: Script to execute
        """
        self.script = script
        self._module: Optional[ModuleType] = None

    def execute(self, config: Optional[Config] = None) -> Any:
        """
        Execute script with configuration.

        Execution flow:
        1. Load script as module
        2. Inject global variables from config
        3. Find entrypoint function
        4. Call entrypoint with args/kwargs

        Args:
            config: Configuration to apply (overrides script.config)

        Returns:
            Entrypoint return value

        Raises:
            RuntimeError: If execution fails
        """
        config = config or self.script.config

        # Load module
        module = self._load_module()

        # Apply config if provided
        if config:
            # Inject global variables
            if config.globals_dict:
                GlobalInjector.inject(module, config.globals_dict)

            # Find and call entrypoint
            entrypoint = self._find_entrypoint(module)
            if entrypoint:
                result = EntrypointFinder.call_entrypoint(
                    entrypoint,
                    config.args,
                    config.kwargs
                )
                return result
            else:
                raise RuntimeError(
                    f"No entrypoint found in {self.script.path}. "
                    f"Expected 'if __name__ == \"__main__\"' block or main() function."
                )
        else:
            # No config, just import (module-level code runs)
            return None

    def _load_module(self) -> ModuleType:
        """
        Load script as Python module.

        Sets __name__ to '__main__' if run_as_main=True.
        """
        script_path = self.script.path.resolve()

        # Create module spec
        spec = importlib.util.spec_from_file_location(
            "__main__" if self.script.run_as_main else self.script.name,
            script_path
        )

        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load script: {script_path}")

        # Create module
        module = importlib.util.module_from_spec(spec)

        # Set __name__ appropriately
        if self.script.run_as_main:
            module.__name__ = '__main__'

        # Add to sys.modules (temporary)
        old_main = sys.modules.get('__main__')
        sys.modules['__main__' if self.script.run_as_main else self.script.name] = module

        try:
            # Execute module
            spec.loader.exec_module(module)
        finally:
            # Restore old __main__ if we replaced it
            if self.script.run_as_main and old_main is not None:
                sys.modules['__main__'] = old_main

        self._module = module
        return module

    def _find_entrypoint(self, module: ModuleType) -> Optional[Any]:
        """Find entrypoint in module."""
        if self.script.entrypoint:
            # Explicit entrypoint specified
            if hasattr(module, self.script.entrypoint):
                return getattr(module, self.script.entrypoint)
            else:
                raise ValueError(
                    f"Specified entrypoint '{self.script.entrypoint}' "
                    f"not found in {self.script.path}"
                )
        else:
            # Auto-detect entrypoint
            return EntrypointFinder.find_entrypoint(module, self.script.path)

    @property
    def module(self) -> Optional[ModuleType]:
        """Get loaded module (None if not executed yet)."""
        return self._module
```

---

## Flow System

### Design Goals

1. **Composable**: Workflows can contain workflows
2. **Iterative**: Support generator-based configs
3. **Parallel**: Subprocess-based isolation
4. **Flexible**: Easy to extend with custom flows

### Module: `flow/base.py`

**Purpose**: Base classes for workflows

```python
from abc import ABC, abstractmethod
from typing import Any, List, Optional
from ..engine.script import Script

class Workflow(ABC):
    """
    Abstract base class for workflows.

    A workflow orchestrates execution of one or more scripts.
    """

    @abstractmethod
    def run(self) -> Any:
        """
        Execute the workflow.

        Returns:
            Workflow result (implementation-specific)
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate workflow configuration.

        Returns:
            True if valid, raises ValueError otherwise
        """
        pass


class ScriptWorkflow(Workflow):
    """Base class for workflows that execute scripts."""

    def __init__(self, scripts: List[Script]):
        """
        Args:
            scripts: List of scripts to execute
        """
        if not scripts:
            raise ValueError("Workflow must have at least one script")

        self.scripts = scripts
        self.validate()

    def validate(self) -> bool:
        """Validate all scripts exist."""
        for script in self.scripts:
            if not script.path.exists():
                raise ValueError(f"Script not found: {script.path}")
        return True
```

### Module: `flow/sequential.py`

**Purpose**: Sequential script execution

```python
from typing import Any, List, Optional
from .base import ScriptWorkflow
from ..engine.script import Script
from ..engine.executor import ScriptExecutor
from ..config.base import Config
from ..config.generator import ConfigGenerator

class Sequential(ScriptWorkflow):
    """
    Execute scripts sequentially.

    Supports:
    - Static configs (Config)
    - Iterative configs (ConfigGenerator)
    - Multiple scripts with independent configs
    """

    def run(self) -> List[Any]:
        """
        Execute scripts in sequence.

        For scripts with ConfigGenerator:
        1. Get next config
        2. Execute script with config
        3. Repeat until generator exhausted

        Returns:
            List of results from each script execution
        """
        results = []

        for script in self.scripts:
            if isinstance(script.config, ConfigGenerator):
                # Iterative execution
                script_results = self._run_iterative(script)
                results.extend(script_results)
            else:
                # Single execution
                result = self._run_once(script, script.config)
                results.append(result)

        return results

    def _run_once(self, script: Script, config: Optional[Config]) -> Any:
        """Execute script once with config."""
        executor = ScriptExecutor(script)
        return executor.execute(config)

    def _run_iterative(self, script: Script) -> List[Any]:
        """Execute script iteratively with generator config."""
        results = []
        config_gen = script.config

        if not isinstance(config_gen, ConfigGenerator):
            raise TypeError(f"Expected ConfigGenerator, got {type(config_gen)}")

        for config in config_gen:
            result = self._run_once(script, config)
            results.append(result)

        return results


class Pipeline(Sequential):
    """
    Sequential workflow with state passing.

    Each script can access results from previous scripts.
    (Future enhancement - for now, alias to Sequential)
    """
    pass
```

### Module: `flow/parallel.py`

**Purpose**: Parallel script execution

```python
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Any
from concurrent.futures import ProcessPoolExecutor, as_completed
from .base import ScriptWorkflow
from ..engine.script import Script
from ..config.base import Config
from ..config.generator import ConfigGenerator

class Parallel(ScriptWorkflow):
    """
    Execute scripts in parallel using subprocesses.

    Each script runs in isolated subprocess with __name__ == '__main__'.
    Ensures true isolation (no shared state).
    """

    def __init__(
        self,
        scripts: List[Script],
        max_workers: Optional[int] = None,
        use_subprocess: bool = True
    ):
        """
        Args:
            scripts: List of scripts to execute
            max_workers: Maximum parallel workers (default: CPU count)
            use_subprocess: If True, use subprocess; if False, use ProcessPoolExecutor
        """
        super().__init__(scripts)
        self.max_workers = max_workers
        self.use_subprocess = use_subprocess

    def run(self) -> List[Any]:
        """
        Execute scripts in parallel.

        Returns:
            List of results (order not guaranteed)
        """
        if self.use_subprocess:
            return self._run_subprocess()
        else:
            return self._run_process_pool()

    def _run_subprocess(self) -> List[subprocess.CompletedProcess]:
        """
        Execute using subprocess.Popen.

        Each script runs as: python script.py
        Config is passed via environment or temp file.
        """
        processes = []

        for script in self.scripts:
            if isinstance(script.config, ConfigGenerator):
                # For generators, we need to iterate
                for config in script.config:
                    proc = self._spawn_subprocess(script, config)
                    processes.append(proc)
            else:
                proc = self._spawn_subprocess(script, script.config)
                processes.append(proc)

        # Wait for all processes
        results = []
        for proc in processes:
            proc.wait()
            results.append(proc)

        return results

    def _spawn_subprocess(
        self,
        script: Script,
        config: Optional[Config]
    ) -> subprocess.Popen:
        """
        Spawn subprocess for script execution.

        Strategy:
        1. Create temporary config file
        2. Launch: kogine run script.py --config temp_config.py
        3. Return process handle
        """
        import tempfile
        import json

        # Create temp config file
        if config:
            temp_config = self._create_temp_config(config)
            cmd = [
                sys.executable, '-m', 'kohakuengine.cli',
                'run', str(script.path),
                '--config', str(temp_config)
            ]
        else:
            cmd = [
                sys.executable, '-m', 'kohakuengine.cli',
                'run', str(script.path)
            ]

        return subprocess.Popen(cmd)

    def _create_temp_config(self, config: Config) -> Path:
        """Create temporary Python config file."""
        import tempfile

        # Create temp file
        fd, path = tempfile.mkstemp(suffix='.py', prefix='kogine_config_')

        # Write config
        with open(path, 'w') as f:
            f.write(f"""
from kohakuengine.config import Config

def config_gen():
    return Config(
        globals_dict={config.globals_dict!r},
        args={config.args!r},
        kwargs={config.kwargs!r},
        metadata={config.metadata!r}
    )
""")

        return Path(path)

    def _run_process_pool(self) -> List[Any]:
        """
        Execute using ProcessPoolExecutor.

        Note: This runs scripts in worker processes, not as __main__.
        Use subprocess mode for true __main__ execution.
        """
        from ..engine.executor import ScriptExecutor

        def execute_script(script: Script, config: Optional[Config]) -> Any:
            executor = ScriptExecutor(script)
            return executor.execute(config)

        results = []

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []

            for script in self.scripts:
                if isinstance(script.config, ConfigGenerator):
                    for config in script.config:
                        future = executor.submit(execute_script, script, config)
                        futures.append(future)
                else:
                    future = executor.submit(execute_script, script, script.config)
                    futures.append(future)

            for future in as_completed(futures):
                results.append(future.result())

        return results
```

---

## API Design

### Python API (`main.py`)

**Purpose**: High-level Python API entry point

```python
"""
KohakuEngine Python API.

Quick start:
    from kohakuengine import Script, Config, Sequential

    script = Script('train.py', config=Config(
        globals_dict={'learning_rate': 0.001}
    ))
    script.run()
"""

from .config import Config, ConfigGenerator, ConfigLoader
from .engine import Script, ScriptExecutor
from .flow import Sequential, Parallel, Pipeline

__all__ = [
    # Config
    'Config',
    'ConfigGenerator',
    'ConfigLoader',

    # Engine
    'Script',
    'ScriptExecutor',

    # Flow
    'Sequential',
    'Parallel',
    'Pipeline',

    # Convenience
    'run',
]

def run(
    script_path: str,
    config_path: Optional[str] = None,
    **config_kwargs
) -> Any:
    """
    Convenience function to run a script.

    Args:
        script_path: Path to script
        config_path: Path to config file (optional)
        **config_kwargs: Config parameters (globals_dict, args, kwargs)

    Returns:
        Script execution result

    Examples:
        # Run with inline config
        run('train.py', globals_dict={'learning_rate': 0.001})

        # Run with config file
        run('train.py', config_path='config.py')
    """
    # Load config
    if config_path:
        config = ConfigLoader.load_config(config_path)
    elif config_kwargs:
        config = Config(**config_kwargs)
    else:
        config = None

    # Create and run script
    script = Script(script_path, config=config)
    executor = ScriptExecutor(script)
    return executor.execute()
```

### Public API Exports (`__init__.py`)

```python
"""
KohakuEngine: All-in-Python Config and Execution Engine.

A flexible configuration and workflow system for R&D workloads.
"""

__version__ = "0.0.1"

# Re-export main API
from .main import (
    Config,
    ConfigGenerator,
    ConfigLoader,
    Script,
    ScriptExecutor,
    Sequential,
    Parallel,
    Pipeline,
    run,
)

__all__ = [
    'Config',
    'ConfigGenerator',
    'ConfigLoader',
    'Script',
    'ScriptExecutor',
    'Sequential',
    'Parallel',
    'Pipeline',
    'run',
]
```

---

## CLI Design

### Command Structure

```bash
kogine <command> [options]

Commands:
  run          Execute a single script
  workflow     Execute a workflow (sequential, parallel)
  config       Config utilities (validate, show)
  version      Show version
  help         Show help
```

### CLI Implementation (`cli.py`)

```python
"""
KohakuEngine CLI.

Usage:
    kogine run SCRIPT [--config CONFIG] [options]
    kogine workflow sequential SCRIPT... [--config CONFIG]
    kogine workflow parallel SCRIPT... [--config CONFIG] [--workers N]
    kogine config validate CONFIG
    kogine config show CONFIG
    kogine --version
    kogine --help
"""

import sys
import argparse
from pathlib import Path
from typing import Optional
from .main import (
    Script, Config, ConfigLoader,
    Sequential, Parallel,
    ScriptExecutor
)

def main():
    """CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog='kogine',
        description='KohakuEngine: All-in-Python Config and Execution Engine'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.0.1'
    )

    subparsers = parser.add_subparsers(title='commands', dest='command')

    # run command
    run_parser = subparsers.add_parser('run', help='Execute a single script')
    run_parser.add_argument('script', help='Path to script')
    run_parser.add_argument('--config', '-c', help='Path to config file')
    run_parser.add_argument('--entrypoint', '-e', help='Entrypoint function name')
    run_parser.set_defaults(func=cmd_run)

    # workflow command
    workflow_parser = subparsers.add_parser('workflow', help='Execute workflow')
    workflow_subparsers = workflow_parser.add_subparsers(dest='workflow_type')

    # workflow sequential
    seq_parser = workflow_subparsers.add_parser('sequential', help='Sequential execution')
    seq_parser.add_argument('scripts', nargs='+', help='Scripts to execute')
    seq_parser.add_argument('--config', '-c', help='Config file for all scripts')
    seq_parser.set_defaults(func=cmd_workflow_sequential)

    # workflow parallel
    par_parser = workflow_subparsers.add_parser('parallel', help='Parallel execution')
    par_parser.add_argument('scripts', nargs='+', help='Scripts to execute')
    par_parser.add_argument('--config', '-c', help='Config file for all scripts')
    par_parser.add_argument('--workers', '-w', type=int, help='Max workers')
    par_parser.add_argument('--mode', choices=['subprocess', 'pool'],
                           default='subprocess', help='Execution mode')
    par_parser.set_defaults(func=cmd_workflow_parallel)

    # config command
    config_parser = subparsers.add_parser('config', help='Config utilities')
    config_subparsers = config_parser.add_subparsers(dest='config_cmd')

    # config validate
    validate_parser = config_subparsers.add_parser('validate', help='Validate config')
    validate_parser.add_argument('config', help='Config file to validate')
    validate_parser.set_defaults(func=cmd_config_validate)

    # config show
    show_parser = config_subparsers.add_parser('show', help='Show config contents')
    show_parser.add_argument('config', help='Config file to show')
    show_parser.set_defaults(func=cmd_config_show)

    return parser

def cmd_run(args):
    """Execute run command."""
    try:
        # Load config if provided
        config = None
        if args.config:
            config = ConfigLoader.load_config(args.config)

        # Create script
        script = Script(
            args.script,
            config=config,
            entrypoint=args.entrypoint
        )

        # Execute
        executor = ScriptExecutor(script)
        result = executor.execute()

        print(f"✓ Script executed successfully")
        if result is not None:
            print(f"Return value: {result}")

        sys.exit(0)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_workflow_sequential(args):
    """Execute sequential workflow."""
    try:
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
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_workflow_parallel(args):
    """Execute parallel workflow."""
    try:
        # Load config
        config = None
        if args.config:
            config = ConfigLoader.load_config(args.config)

        # Create scripts
        scripts = [Script(path, config=config) for path in args.scripts]

        # Execute workflow
        use_subprocess = (args.mode == 'subprocess')
        workflow = Parallel(
            scripts,
            max_workers=args.workers,
            use_subprocess=use_subprocess
        )
        results = workflow.run()

        print(f"✓ Parallel workflow completed ({len(results)} executions)")
        sys.exit(0)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_config_validate(args):
    """Validate config file."""
    try:
        config = ConfigLoader.load_config(args.config)
        print(f"✓ Config valid: {args.config}")
        print(f"  Type: {type(config).__name__}")
        sys.exit(0)
    except Exception as e:
        print(f"✗ Config invalid: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_config_show(args):
    """Show config contents."""
    try:
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
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)

def _print_config(config: Config):
    """Print config details."""
    print(f"Globals: {config.globals_dict}")
    print(f"Args: {config.args}")
    print(f"Kwargs: {config.kwargs}")
    if config.metadata:
        print(f"Metadata: {config.metadata}")

if __name__ == '__main__':
    main()
```

---

## Implementation Details

### Module Loading and __name__ Handling

**Challenge**: We need to make scripts think they're running as `__main__`.

**Solution**:
```python
# In executor.py
spec = importlib.util.spec_from_file_location("__main__", script_path)
module = importlib.util.module_from_spec(spec)
module.__name__ = '__main__'  # Critical!
sys.modules['__main__'] = module
spec.loader.exec_module(module)
```

**Why this works**:
- `if __name__ == "__main__":` checks module's `__name__` attribute
- We set it to `'__main__'` before executing
- Code inside the block runs normally

### Global Variable Injection

**Strategy**:
```python
# Explicit dict mapping
setattr(module, 'learning_rate', 0.001)
setattr(module, 'batch_size', 32)
```

**Alternative** (user uses globals() in config):
```python
# In config.py
import sys

def config_gen():
    # User defines globals directly
    learning_rate = 0.001
    batch_size = 32

    # Filter out builtins
    user_globals = {
        k: v for k, v in globals().items()
        if not k.startswith('_') and k not in ['sys', 'config_gen']
    }

    return Config(globals_dict=user_globals)
```

We'll support both patterns.

### Generator Exhaustion Handling

```python
# In sequential.py
for config in config_gen:
    try:
        execute_script(config)
    except StopIteration:
        break  # Generator exhausted
```

### Subprocess Communication

For parallel execution:

**Option 1: Temp config files** (simpler)
```python
# Write config to temp file
with tempfile.NamedTemporaryFile(mode='w', suffix='.py') as f:
    f.write(generate_config_code(config))
    f.flush()

    # Launch subprocess
    subprocess.run(['kogine', 'run', 'script.py', '--config', f.name])
```

**Option 2: Environment variables** (for simple configs)
```python
env = os.environ.copy()
env['KOGINE_GLOBALS'] = json.dumps(config.globals_dict)
subprocess.run(['python', 'script.py'], env=env)
```

We'll use **Option 1** (temp files) for generality.

---

## Testing Strategy

### Test Structure

```
tests/
├── conftest.py                  # Pytest fixtures
├── test_config/
│   ├── test_base.py            # Config dataclass tests
│   ├── test_generator.py       # ConfigGenerator tests
│   └── test_loader.py          # ConfigLoader tests
├── test_engine/
│   ├── test_script.py          # Script class tests
│   ├── test_injector.py        # Global injection tests
│   ├── test_entrypoint.py      # Entrypoint discovery tests
│   └── test_executor.py        # Executor integration tests
├── test_flow/
│   ├── test_sequential.py      # Sequential workflow tests
│   ├── test_parallel.py        # Parallel workflow tests
│   └── test_pipeline.py        # Pipeline tests
├── test_cli/
│   ├── test_cli_run.py         # CLI run command tests
│   └── test_cli_workflow.py    # CLI workflow command tests
├── fixtures/
│   ├── scripts/                # Test scripts
│   │   ├── simple.py
│   │   ├── with_args.py
│   │   └── with_globals.py
│   └── configs/                # Test configs
│       ├── simple_config.py
│       └── generator_config.py
└── integration/
    ├── test_end_to_end.py      # Full integration tests
    └── test_examples.py        # Test example scripts
```

### Key Test Cases

**Config System**:
- Load static config
- Load generator config
- Invalid config format
- Config with Python objects
- Config validation

**Engine System**:
- Import script as module
- Inject global variables
- Find entrypoint (various patterns)
- Call entrypoint with args/kwargs
- __name__ == "__main__" handling

**Flow System**:
- Sequential execution (multiple scripts)
- Generator-based iteration
- Parallel subprocess execution
- Error handling in workflows

**CLI**:
- Single run command
- Workflow commands
- Config validation
- Error messages

### Test Fixtures

```python
# conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def simple_script(tmp_path):
    """Create simple test script."""
    script = tmp_path / "test_script.py"
    script.write_text("""
result = None

def main():
    global result
    result = "success"
    return result

if __name__ == "__main__":
    main()
""")
    return script

@pytest.fixture
def script_with_globals(tmp_path):
    """Script using global variables."""
    script = tmp_path / "globals_script.py"
    script.write_text("""
learning_rate = 0.001
batch_size = 32

def main():
    print(f"LR: {learning_rate}, BS: {batch_size}")
    return learning_rate * batch_size

if __name__ == "__main__":
    main()
""")
    return script

@pytest.fixture
def generator_config(tmp_path):
    """Generator config file."""
    config = tmp_path / "gen_config.py"
    config.write_text("""
from kohakuengine.config import Config

def config_gen():
    for i in range(3):
        yield Config(
            globals_dict={'iteration': i},
            kwargs={'iter_num': i}
        )
""")
    return config
```

---

## Examples

### Example Directory Structure

```
examples/
├── scripts/
│   ├── hello.py                    # Simple hello world
│   ├── train_simple.py             # Simple training script
│   ├── train_with_checkpoint.py    # With checkpoint loading
│   ├── preprocess.py               # Data preprocessing
│   └── evaluate.py                 # Model evaluation
│
├── configs/
│   ├── hello_config.py             # Config for hello.py
│   ├── sweep_config.py             # Hyperparameter sweep
│   ├── resume_config.py            # Resume training config
│   ├── pipeline_config.py          # Multi-stage pipeline
│   └── external_json_config.py     # Load from JSON example
│
└── workflows/
    ├── simple_workflow.py          # Python API example
    ├── parallel_sweep.py           # Parallel sweep example
    └── resume_training.py          # Resume training workflow
```

### Example: Simple Script

```python
# examples/scripts/hello.py
name = "World"
greeting = "Hello"

def main(excited=False):
    msg = f"{greeting}, {name}"
    if excited:
        msg += "!"
    print(msg)
    return msg

if __name__ == "__main__":
    main()
```

### Example: Simple Config

```python
# examples/configs/hello_config.py
from kohakuengine.config import Config

def config_gen():
    return Config(
        globals_dict={
            'name': 'KohakuEngine',
            'greeting': 'Welcome to'
        },
        kwargs={'excited': True}
    )
```

### Example: Sweep Config

```python
# examples/configs/sweep_config.py
from kohakuengine.config import Config

def config_gen():
    """Hyperparameter sweep."""
    learning_rates = [0.001, 0.01, 0.1]
    batch_sizes = [16, 32, 64]

    for lr in learning_rates:
        for bs in batch_sizes:
            yield Config(
                globals_dict={
                    'learning_rate': lr,
                    'batch_size': bs,
                    'experiment_name': f'lr{lr}_bs{bs}'
                },
                metadata={
                    'sweep': 'lr_bs',
                    'lr': lr,
                    'bs': bs
                }
            )
```

### Example: Python API Workflow

```python
# examples/workflows/simple_workflow.py
from kohakuengine import Script, Config, Sequential

# Define scripts with configs
preprocess = Script(
    'examples/scripts/preprocess.py',
    config=Config(globals_dict={'input_dir': './data/raw'})
)

train = Script(
    'examples/scripts/train_simple.py',
    config=Config(globals_dict={'data_dir': './data/processed'})
)

evaluate = Script(
    'examples/scripts/evaluate.py',
    config=Config(globals_dict={'model_path': './checkpoints/best.pt'})
)

# Create and run workflow
workflow = Sequential([preprocess, train, evaluate])
results = workflow.run()

print(f"Workflow completed with {len(results)} steps")
```

### Example: CLI Usage

```bash
# Run single script
kogine run examples/scripts/hello.py --config examples/configs/hello_config.py

# Sequential workflow
kogine workflow sequential \
    examples/scripts/preprocess.py \
    examples/scripts/train_simple.py \
    examples/scripts/evaluate.py \
    --config examples/configs/pipeline_config.py

# Parallel sweep
kogine workflow parallel \
    examples/scripts/train_simple.py \
    --config examples/configs/sweep_config.py \
    --workers 4 \
    --mode subprocess

# Validate config
kogine config validate examples/configs/sweep_config.py

# Show config
kogine config show examples/configs/hello_config.py
```

---

## Dependencies

### Required Dependencies

```toml
[project]
dependencies = [
    # No external dependencies for core!
]

[project.optional-dependencies]
# Examples only
examples = [
    "pyyaml>=6.0",      # For YAML example
    "tomli>=2.0.0",     # For TOML example (Python <3.11)
]

# Development
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]
```

### Python Version

- **Minimum**: Python 3.10
- **Reason**:
  - `match` statement (optional, can avoid)
  - Type hinting improvements
  - Better error messages

---

## Development Workflow

### Setup

```bash
# Clone repo
git clone https://github.com/KohakuBlueLeaf/KohakuEngine
cd KohakuEngine

# Create venv
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in dev mode
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/
ruff check src/ tests/

# Type check
mypy src/
```

### Git Workflow

```
main (stable releases)
  ↑
develop (integration)
  ↑
feature/* (individual features)
```

### Release Process

1. Develop on `feature/*` branches
2. Merge to `develop` via PR
3. Test on `develop`
4. Merge to `main` for release
5. Tag release: `v0.1.0`
6. Publish to PyPI

---

## Future Enhancements

### Phase 3+ Features

1. **Distributed Execution**
   - Multi-machine parallel execution
   - Integration with SLURM, Ray, Dask
   - Remote script execution

2. **Advanced Workflow**
   - Conditional execution (if/else in workflow)
   - Loop constructs in workflows
   - Dependency DAGs

3. **State Management**
   - Checkpoint utilities
   - State passing between scripts
   - Workflow resume/retry

4. **Monitoring**
   - Web UI for workflow status
   - Real-time logging aggregation
   - Resource usage tracking

5. **Config Management**
   - Config versioning
   - Config inheritance
   - Config validation schemas (optional)

6. **Developer Tools**
   - VS Code extension
   - Interactive config builder
   - Migration tools (Hydra → KohakuEngine)

---

## Summary

KohakuEngine provides a **modular, Python-native configuration and execution system** with:

- **Config system**: Python-first configs with generator support
- **Engine system**: Non-invasive script execution with global injection
- **Flow system**: Sequential and parallel workflow orchestration
- **Dual interface**: Pythonic API + CLI

The architecture is **clean, extensible, and well-tested**, ready for R&D workloads.
