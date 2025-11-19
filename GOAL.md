# KohakuEngine: Project Goals and Vision

## Project Overview

**KohakuEngine** is an all-in-Python configuration and execution engine system designed specifically for Research & Development (R&D) workloads. It bridges the gap between quick prototyping with global variables and production-ready configuration systems.

## Problem Statement

### Current Pain Points in R&D Workflows

1. **Quick Prototyping vs. Production Gap**
   - R&D workflows often start with global variables for rapid experimentation
   - Migration to mature config systems is non-trivial and time-consuming
   - Developers resist proper configuration due to initial overhead

2. **Computed Configuration Properties**
   - Configs often have computed properties: `xxx = yyy/2 if yyy > k else yyy`
   - Traditional YAML/JSON configs struggle with dynamic values
   - Hard to express dependencies between configuration values

3. **Workflow Orchestration Challenges**
   - Need to chain multiple scripts with different configurations
   - Config sweeps and parameter exploration are cumbersome
   - Workarounds like "kill and resume training every epoch" (PyTorch dataloader memleak) require dynamic config updates

4. **Inflexible Execution Models**
   - Scripts are tightly coupled to specific config formats
   - Hard to reuse existing scripts with different config sources
   - No standard way to inject configuration into running scripts

## Vision

Create a **Python-native configuration and execution engine** that:

1. **Embraces Python's Flexibility**
   - Configs ARE Python code (not limited to declarative formats)
   - Support Python objects, classes, and instances directly
   - Leverage Python's full expressiveness for computed values

2. **Zero-Friction Migration**
   - Works with existing scripts that use global variables
   - No code refactoring required to adopt KohakuEngine
   - Progressive enhancement: start simple, add features as needed

3. **Workflow-First Design**
   - Built-in support for sequential and parallel execution
   - Dynamic configuration generation for iterative workflows
   - First-class support for config sweeps and parameter exploration

4. **Dual Interface**
   - Pythonic API for programmatic control
   - CLI for quick single-run execution
   - Both interfaces support full feature set

## Core Features

### 1. Full Python Config System

**Python-First Approach**
- Config files are `.py` files with full Python capabilities
- Support arbitrary Python objects, classes, and instances
- Computed properties using native Python expressions
- No serialization limitations (YAML/JSON/TOML)

**Flexible Config Structure**
```python
# Example config.py
def config_gen():
    return Config(
        globals_dict={'learning_rate': 0.001, 'batch_size': 32},
        args=['train'],
        kwargs={'epochs': 100}
    )
```

**Optional External Format Support**
- Users can load YAML/TOML/JSON in their Python config
- No forced dependencies (examples provided)
- Full control over deserialization

### 2. Script Execution with Config Injection

**Non-Invasive Execution**
- Import scripts via `importlib`
- Override module-level global variables via `setattr`
- Automatically discover and call entrypoint functions
- Support entrypoint args/kwargs

**Execution Flow**
```
1. Load script as module
2. Inject global variables (setattr on module)
3. Find entrypoint (if __name__ == "__main__" block)
4. Call entrypoint with args/kwargs
5. Execute as if run directly
```

**Requirements for User Scripts**
- Must have entrypoint in `if __name__ == "__main__"` block
- Entrypoint can optionally accept args/kwargs
- Global variables should be defined at module level

### 3. Workflow and Pipeline System

**Sequential Execution**
- Run multiple scripts in sequence
- Pass state between scripts
- Regenerate config at configurable points

**Parallel Execution**
- Subprocess-based parallelism
- Each script runs as `__main__` process (isolated)
- Configurable: run as subprocess or in-process
- Support for distributed parameter sweeps

**Iterative Workflows**
```python
# Generator-based config for iterative workflows
def config_gen():
    for epoch in range(100):
        ckpt_path = find_latest_checkpoint()
        yield Config(
            globals_dict={'checkpoint': ckpt_path, 'epoch': epoch}
        )
```

**Use Cases**
- Config sweeps: iterate over parameter combinations
- Training resume: regenerate config to find latest checkpoint
- Multi-stage pipelines: preprocessing → training → evaluation
- Fault tolerance: kill and restart with updated state

### 4. Dual Execution Interface

**Pythonic API**
```python
from kohakuengine import Script, Config, Sequential, Parallel

# Define workflow
workflow = Sequential([
    Script('preprocess.py', config=Config(...)),
    Script('train.py', config=config_generator),
    Script('evaluate.py', config=Config(...))
])

# Execute
workflow.run()
```

**Command-Line Interface**
```bash
# Single run
kogine run script.py --config config.py

# Sequential workflow
kogine workflow sequential script1.py script2.py --config config.py

# Parallel execution
kogine workflow parallel --sweep learning_rate=0.001,0.01,0.1
```

## Success Criteria

### Must Have (MVP)

1. **Config System**
   - ✅ Load Python config files
   - ✅ Support globals_dict, args, kwargs
   - ✅ Generator-based iterative configs

2. **Execution Engine**
   - ✅ Import and execute scripts
   - ✅ Inject global variables
   - ✅ Call entrypoint with args/kwargs
   - ✅ Proper `__name__ == "__main__"` handling

3. **Basic Workflow**
   - ✅ Sequential execution
   - ✅ Config regeneration per iteration
   - ✅ Python API for workflow definition

4. **CLI**
   - ✅ Single script execution
   - ✅ Config file specification
   - ✅ Basic error handling

### Should Have (v1.0)

5. **Advanced Workflow**
   - ✅ Parallel execution via subprocess
   - ✅ Configurable execution mode (subprocess vs in-process)
   - ✅ State passing between scripts

6. **Enhanced CLI**
   - ✅ Workflow commands
   - ✅ Config sweeps
   - ✅ Logging and output management

7. **Testing**
   - ✅ Unit tests for all modules
   - ✅ Integration tests for workflows
   - ✅ Example scripts with configs

### Nice to Have (Future)

8. **Advanced Features**
   - Distributed execution (multi-machine)
   - Config versioning and tracking
   - Checkpoint management utilities
   - Web UI for workflow monitoring
   - Plugin system for extensions

9. **Developer Experience**
   - VS Code extension for config validation
   - Interactive config builder
   - Config migration tools

## Target Users

### Primary Audience

1. **ML/AI Researchers**
   - Running training experiments with config sweeps
   - Managing complex multi-stage pipelines
   - Workarounds for framework limitations (memleak, etc.)

2. **Data Scientists**
   - Orchestrating data processing pipelines
   - Parameter exploration and optimization
   - Reproducible research workflows

3. **Research Engineers**
   - Building reusable experiment infrastructure
   - Managing compute resources efficiently
   - Automating repetitive R&D tasks

### Use Cases

**Use Case 1: Config Sweep for Hyperparameter Tuning**
```python
def config_gen():
    for lr in [0.001, 0.01, 0.1]:
        for bs in [16, 32, 64]:
            yield Config(
                globals_dict={'learning_rate': lr, 'batch_size': bs},
                kwargs={'experiment_name': f'lr{lr}_bs{bs}'}
            )

parallel = Parallel([
    Script('train.py', config=config_gen())
], max_workers=4)
parallel.run()
```

**Use Case 2: Kill-Resume Training Workflow**
```python
# Workaround for PyTorch DataLoader memleak
def config_gen():
    for epoch in range(100):
        ckpt = find_latest_checkpoint()
        yield Config(
            globals_dict={'checkpoint_path': ckpt, 'current_epoch': epoch},
            kwargs={'max_epochs': epoch + 1}  # Train for 1 epoch
        )

# Each iteration: load checkpoint, train 1 epoch, save, kill process
sequential = Sequential([Script('train_one_epoch.py', config=config_gen())])
sequential.run()
```

**Use Case 3: Multi-Stage ML Pipeline**
```python
workflow = Sequential([
    Script('download_data.py', config=Config(
        globals_dict={'dataset': 'imagenet', 'split': 'train'}
    )),
    Script('preprocess.py', config=Config(
        globals_dict={'input_dir': './raw', 'output_dir': './processed'}
    )),
    Script('train.py', config=Config(
        globals_dict={'data_dir': './processed', 'epochs': 100}
    )),
    Script('evaluate.py', config=Config(
        globals_dict={'model_path': './checkpoints/best.pt'}
    ))
])
workflow.run()
```

**Use Case 4: Quick Prototype Migration**
```python
# Original script with global vars
# train.py
learning_rate = 0.001
batch_size = 32

def main():
    # Training code...
    pass

if __name__ == "__main__":
    main()

# Use with KohakuEngine (no script changes needed!)
from kohakuengine import Script, Config

Script('train.py', config=Config(
    globals_dict={'learning_rate': 0.01, 'batch_size': 64}
)).run()
```

## Design Principles

### 1. Python-Native First
- Leverage Python's full power for configs
- No artificial limitations from serialization formats
- Native support for functions, classes, objects

### 2. Non-Invasive Integration
- Work with existing scripts without modification
- Progressive enhancement model
- Backward compatibility with direct execution

### 3. Explicit Over Implicit
- Clear config structure (globals_dict, args, kwargs)
- Explicit entrypoint specification
- Transparent execution model

### 4. Modularity and Composability
- Clean separation: config / engine / flow
- Reusable components
- Easy to extend and customize

### 5. Developer Experience
- Intuitive APIs (pythonic and CLI)
- Clear error messages
- Comprehensive examples and documentation

## Non-Goals

**What KohakuEngine Is NOT**

1. **Not a Workflow Engine Replacement**
   - Not competing with Airflow, Prefect, Luigi
   - Focus on R&D scripts, not production ETL
   - Lighter weight, easier for experiments

2. **Not a Config Validation Framework**
   - Not enforcing schemas like Hydra/OmegaConf
   - Validation is user's responsibility
   - Flexibility over safety

3. **Not a Cluster Orchestrator**
   - Not managing distributed systems (initially)
   - Single-machine parallelism first
   - Can integrate with external orchestrators later

4. **Not a Dependency Manager**
   - Not replacing pip, conda, poetry
   - Focus on execution, not environment management

## Success Metrics

**Adoption Metrics**
- Number of projects using KohakuEngine
- GitHub stars and community engagement
- Package downloads (PyPI)

**Technical Metrics**
- Test coverage > 90%
- Zero critical bugs in core execution
- Documentation coverage for all public APIs

**User Experience Metrics**
- Time to first successful run < 5 minutes
- Config migration effort < 1 hour for typical project
- Positive user feedback on API design

## Timeline

**Phase 1: MVP (4-6 weeks)**
- Core config and execution system
- Basic sequential workflows
- Python API
- Essential CLI commands

**Phase 2: v1.0 (8-10 weeks)**
- Parallel execution
- Advanced workflow features
- Complete CLI
- Comprehensive tests and examples

**Phase 3: Future (beyond v1.0)**
- Community feedback integration
- Performance optimization
- Advanced features (distributed, monitoring, etc.)
- Ecosystem tools (plugins, extensions)

## Conclusion

KohakuEngine aims to make configuration and workflow management in R&D projects as flexible and powerful as Python itself. By embracing Python-native configs and non-invasive execution, we eliminate friction in the development workflow while providing robust orchestration capabilities when needed.

The project succeeds when researchers can focus on their experiments rather than fighting with configuration systems, and when migrating from quick prototypes to production-ready code becomes effortless.
