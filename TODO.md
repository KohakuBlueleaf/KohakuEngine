# KohakuEngine: Implementation Roadmap

This document outlines the phased implementation plan for KohakuEngine.

## Status Legend

- ⬜ Not started
- 🟡 In progress
- ✅ Completed
- ⏸️ Blocked/On hold

---

## Phase 0: Project Foundation

**Goal**: Set up project infrastructure and development environment.

**Timeline**: Week 1

### Tasks

- ✅ Project structure created
- ✅ pyproject.toml configured
- ✅ Virtual environment setup
- ⬜ Create directory structure
  - ⬜ `src/kohakuengine/config/`
  - ⬜ `src/kohakuengine/engine/`
  - ⬜ `src/kohakuengine/flow/`
  - ⬜ `examples/scripts/`
  - ⬜ `examples/configs/`
  - ⬜ `examples/workflows/`
  - ⬜ `tests/`
- ⬜ Setup development tools
  - ⬜ Configure pytest
  - ⬜ Setup black formatter
  - ⬜ Setup ruff linter
  - ⬜ Setup mypy type checker
  - ⬜ Create .gitignore
- ⬜ Create test fixtures directory
  - ⬜ `tests/fixtures/scripts/`
  - ⬜ `tests/fixtures/configs/`

**Deliverables**:
- Clean project structure
- Development environment ready
- CI/CD skeleton (optional)

---

## Phase 1: Core Config System

**Goal**: Implement the configuration system with Python-first approach.

**Timeline**: Week 1-2

### Module: `config/base.py`

- ⬜ Implement `Config` dataclass
  - ⬜ Define fields (globals_dict, args, kwargs, metadata)
  - ⬜ Add `__post_init__` validation
  - ⬜ Add type hints
  - ⬜ Add docstrings
- ⬜ Write unit tests
  - ⬜ Test config creation
  - ⬜ Test validation (type errors)
  - ⬜ Test default values
  - ⬜ Test metadata handling

### Module: `config/generator.py`

- ⬜ Implement `ConfigGenerator` class
  - ⬜ `__init__` with generator/iterator param
  - ⬜ `__iter__` and `__next__` methods
  - ⬜ Exhaustion tracking
  - ⬜ Validation (yields Config objects)
- ⬜ Write unit tests
  - ⬜ Test generator wrapping
  - ⬜ Test iteration protocol
  - ⬜ Test exhaustion detection
  - ⬜ Test type validation

### Module: `config/loader.py`

- ⬜ Implement `ConfigLoader` class
  - ⬜ `load_config()` method
    - ⬜ Dynamic module loading (importlib)
    - ⬜ Find `config_gen()` function
    - ⬜ Find `CONFIG` variable
    - ⬜ Detect generator vs static
  - ⬜ `load_from_dict()` helper
  - ⬜ Error handling and validation
- ⬜ Write unit tests
  - ⬜ Test loading static config
  - ⬜ Test loading generator config
  - ⬜ Test file not found
  - ⬜ Test invalid format
  - ⬜ Test from dict conversion

### Module: `config/types.py`

- ⬜ Define type protocols
  - ⬜ `ConfigProvider` protocol
  - ⬜ `Configurable` protocol
- ⬜ Add type aliases
- ⬜ Write tests (type checking)

### Module: `config/__init__.py`

- ⬜ Export public API
  - ⬜ `Config`
  - ⬜ `ConfigGenerator`
  - ⬜ `ConfigLoader`

### Integration

- ⬜ Create example configs
  - ⬜ `examples/configs/simple_config.py`
  - ⬜ `examples/configs/generator_config.py`
  - ⬜ `examples/configs/sweep_config.py`
- ⬜ Integration tests
  - ⬜ Test loading examples
  - ⬜ Test generator iteration

**Deliverables**:
- ✅ Config system fully functional
- ✅ Unit tests passing (>90% coverage)
- ✅ Example configs working

---

## Phase 2: Core Engine System

**Goal**: Implement script execution with config injection.

**Timeline**: Week 2-3

### Module: `engine/script.py`

- ⬜ Implement `Script` dataclass
  - ⬜ Define fields (path, config, entrypoint, run_as_main)
  - ⬜ Path validation
  - ⬜ `name` property
  - ⬜ `__repr__` method
- ⬜ Write unit tests
  - ⬜ Test script creation
  - ⬜ Test path validation
  - ⬜ Test file not found

### Module: `engine/injector.py`

- ⬜ Implement `GlobalInjector` class
  - ⬜ `inject()` static method
    - ⬜ Protected names check
    - ⬜ setattr on module
  - ⬜ `get_user_globals()` helper
  - ⬜ Error handling
- ⬜ Write unit tests
  - ⬜ Test simple injection
  - ⬜ Test protected names
  - ⬜ Test get_user_globals
  - ⬜ Test with various types (objects, classes)

### Module: `engine/entrypoint.py`

- ⬜ Implement `EntrypointFinder` class
  - ⬜ `find_entrypoint()` method
    - ⬜ AST parsing for `if __name__ == "__main__"`
    - ⬜ Find function call in block
    - ⬜ Fallback to `main()` function
  - ⬜ `_find_main_block_function()` helper
  - ⬜ `_is_main_guard()` helper
  - ⬜ `call_entrypoint()` method
    - ⬜ Signature inspection
    - ⬜ Handle args/kwargs
    - ⬜ Graceful parameter matching
- ⬜ Write unit tests
  - ⬜ Test finding entrypoint (various patterns)
  - ⬜ Test calling with args/kwargs
  - ⬜ Test signature matching
  - ⬜ Test no entrypoint found

### Module: `engine/executor.py`

- ⬜ Implement `ScriptExecutor` class
  - ⬜ `__init__` with Script
  - ⬜ `execute()` method
    - ⬜ Load module
    - ⬜ Inject globals
    - ⬜ Find entrypoint
    - ⬜ Call entrypoint
  - ⬜ `_load_module()` helper
    - ⬜ importlib loading
    - ⬜ Set `__name__` to `'__main__'`
    - ⬜ sys.modules management
  - ⬜ `_find_entrypoint()` helper
  - ⬜ Error handling
- ⬜ Write unit tests
  - ⬜ Test simple execution
  - ⬜ Test with global injection
  - ⬜ Test with args/kwargs
  - ⬜ Test __name__ == "__main__" handling
  - ⬜ Test errors

### Module: `engine/__init__.py`

- ⬜ Export public API
  - ⬜ `Script`
  - ⬜ `ScriptExecutor`

### Integration

- ⬜ Create example scripts
  - ⬜ `examples/scripts/hello.py` (simple)
  - ⬜ `examples/scripts/with_globals.py`
  - ⬜ `examples/scripts/with_args.py`
  - ⬜ `examples/scripts/train_simple.py` (realistic)
- ⬜ Integration tests
  - ⬜ Test running examples with configs
  - ⬜ Test config + engine together
- ⬜ Test fixtures for unit tests
  - ⬜ `tests/fixtures/scripts/simple.py`
  - ⬜ `tests/fixtures/scripts/with_globals.py`

**Deliverables**:
- ✅ Engine system fully functional
- ✅ Scripts execute with config injection
- ✅ Unit tests passing (>90% coverage)
- ✅ Example scripts working

---

## Phase 3: Flow System - Sequential

**Goal**: Implement sequential workflow orchestration.

**Timeline**: Week 3-4

### Module: `flow/base.py`

- ⬜ Implement `Workflow` abstract class
  - ⬜ `run()` abstract method
  - ⬜ `validate()` abstract method
- ⬜ Implement `ScriptWorkflow` base class
  - ⬜ `__init__` with scripts list
  - ⬜ `validate()` implementation
- ⬜ Write unit tests
  - ⬜ Test abstract class behavior
  - ⬜ Test validation

### Module: `flow/sequential.py`

- ⬜ Implement `Sequential` class
  - ⬜ Extend `ScriptWorkflow`
  - ⬜ `run()` method
    - ⬜ Iterate through scripts
    - ⬜ Handle ConfigGenerator (iterative)
    - ⬜ Handle static Config
  - ⬜ `_run_once()` helper
  - ⬜ `_run_iterative()` helper
- ⬜ Implement `Pipeline` class (alias for now)
- ⬜ Write unit tests
  - ⬜ Test single script execution
  - ⬜ Test multiple scripts
  - ⬜ Test with static configs
  - ⬜ Test with generator configs
  - ⬜ Test iteration termination

### Module: `flow/__init__.py`

- ⬜ Export public API
  - ⬜ `Sequential`
  - ⬜ `Pipeline`

### Integration

- ⬜ Create workflow examples
  - ⬜ `examples/workflows/simple_workflow.py`
  - ⬜ `examples/workflows/iterative_workflow.py`
- ⬜ Integration tests
  - ⬜ Test full config → engine → flow pipeline
  - ⬜ Test with example workflows

**Deliverables**:
- ✅ Sequential workflow working
- ✅ Generator-based iteration working
- ✅ Unit tests passing
- ✅ Example workflows working

---

## Phase 4: Flow System - Parallel

**Goal**: Implement parallel execution with subprocess isolation.

**Timeline**: Week 4-5

### Module: `flow/parallel.py`

- ⬜ Implement `Parallel` class
  - ⬜ `__init__` with max_workers and use_subprocess
  - ⬜ `run()` method (dispatcher)
  - ⬜ `_run_subprocess()` implementation
    - ⬜ Iterate scripts
    - ⬜ Spawn subprocess per config
    - ⬜ Wait for completion
    - ⬜ Collect results
  - ⬜ `_spawn_subprocess()` helper
    - ⬜ Create temp config file
    - ⬜ Build kogine command
    - ⬜ Launch subprocess.Popen
  - ⬜ `_create_temp_config()` helper
  - ⬜ `_run_process_pool()` implementation (fallback)
- ⬜ Write unit tests
  - ⬜ Test subprocess spawning
  - ⬜ Test temp config creation
  - ⬜ Test parallel execution
  - ⬜ Test with generators
  - ⬜ Test max_workers limit
  - ⬜ Test process pool mode

### Integration

- ⬜ Create parallel examples
  - ⬜ `examples/workflows/parallel_sweep.py`
  - ⬜ `examples/configs/parallel_config.py`
- ⬜ Integration tests
  - ⬜ Test subprocess isolation
  - ⬜ Test __name__ == "__main__" in subprocess
  - ⬜ Test concurrent execution

**Deliverables**:
- ✅ Parallel execution working
- ✅ Subprocess isolation verified
- ✅ Unit tests passing
- ✅ Example parallel workflows

**Notes**:
- This phase depends on CLI being partially functional (kogine run command)
- May need to implement CLI Phase 5 first, or create minimal CLI stub

---

## Phase 5: Python API Entry Point

**Goal**: Create high-level Python API.

**Timeline**: Week 5

### Module: `main.py`

- ⬜ Implement `run()` convenience function
  - ⬜ Load config from path or kwargs
  - ⬜ Create script
  - ⬜ Execute
- ⬜ Define `__all__` exports
- ⬜ Add module docstring with examples
- ⬜ Write unit tests
  - ⬜ Test run() with config_path
  - ⬜ Test run() with kwargs
  - ⬜ Test run() without config

### Module: `__init__.py`

- ⬜ Re-export all public APIs
  - ⬜ Config classes
  - ⬜ Engine classes
  - ⬜ Flow classes
  - ⬜ run() function
- ⬜ Add `__version__`
- ⬜ Add module docstring

### Module: `utils.py`

- ⬜ Add utility functions
  - ⬜ Path resolution helpers
  - ⬜ Logging setup
  - ⬜ Error formatting
  - ⬜ (Add as needed)

**Deliverables**:
- ✅ Clean Python API
- ✅ `from kohakuengine import ...` works
- ✅ `kohakuengine.run()` works
- ✅ Tests passing

---

## Phase 6: CLI Implementation

**Goal**: Implement command-line interface.

**Timeline**: Week 5-6

### Module: `cli.py`

- ⬜ Implement argument parser
  - ⬜ Main parser with version
  - ⬜ Subcommand: `run`
  - ⬜ Subcommand: `workflow sequential`
  - ⬜ Subcommand: `workflow parallel`
  - ⬜ Subcommand: `config validate`
  - ⬜ Subcommand: `config show`
- ⬜ Implement command handlers
  - ⬜ `cmd_run()`
  - ⬜ `cmd_workflow_sequential()`
  - ⬜ `cmd_workflow_parallel()`
  - ⬜ `cmd_config_validate()`
  - ⬜ `cmd_config_show()`
- ⬜ Add error handling
  - ⬜ User-friendly error messages
  - ⬜ Exit codes
- ⬜ Add `main()` entry point
- ⬜ Write unit tests
  - ⬜ Test argument parsing
  - ⬜ Test each command (with mocks)
- ⬜ Write integration tests
  - ⬜ Test CLI with real scripts (subprocess)
  - ⬜ Test all commands end-to-end

### CLI Testing

- ⬜ Test `kogine run`
  - ⬜ With config file
  - ⬜ Without config
  - ⬜ With entrypoint option
  - ⬜ Error cases
- ⬜ Test `kogine workflow sequential`
  - ⬜ Multiple scripts
  - ⬜ With config
- ⬜ Test `kogine workflow parallel`
  - ⬜ With workers option
  - ⬜ With mode option
- ⬜ Test `kogine config` commands
  - ⬜ Validate
  - ⬜ Show (static and generator)

**Deliverables**:
- ✅ CLI fully functional
- ✅ `kogine` command works
- ✅ All subcommands working
- ✅ Tests passing

---

## Phase 7: Examples and Documentation

**Goal**: Create comprehensive examples and documentation.

**Timeline**: Week 6-7

### Example Scripts

- ⬜ Create basic examples
  - ⬜ `examples/scripts/hello.py`
  - ⬜ `examples/scripts/calculator.py`
  - ⬜ `examples/scripts/file_processor.py`
- ⬜ Create ML-style examples
  - ⬜ `examples/scripts/train_simple.py`
  - ⬜ `examples/scripts/train_with_checkpoint.py`
  - ⬜ `examples/scripts/preprocess.py`
  - ⬜ `examples/scripts/evaluate.py`
- ⬜ Create data processing examples
  - ⬜ `examples/scripts/download_data.py`
  - ⬜ `examples/scripts/transform_data.py`

### Example Configs

- ⬜ Create basic configs
  - ⬜ `examples/configs/hello_config.py`
  - ⬜ `examples/configs/simple_config.py`
- ⬜ Create advanced configs
  - ⬜ `examples/configs/sweep_config.py` (hyperparameter sweep)
  - ⬜ `examples/configs/resume_config.py` (checkpoint resume)
  - ⬜ `examples/configs/pipeline_config.py` (multi-stage)
- ⬜ Create external format examples
  - ⬜ `examples/configs/external_json_config.py`
  - ⬜ `examples/configs/external_yaml_config.py` (with PyYAML)
  - ⬜ `examples/configs/external_toml_config.py` (with tomli)

### Example Workflows

- ⬜ Create workflow examples
  - ⬜ `examples/workflows/simple_workflow.py`
  - ⬜ `examples/workflows/parallel_sweep.py`
  - ⬜ `examples/workflows/resume_training.py`
  - ⬜ `examples/workflows/ml_pipeline.py`
- ⬜ Create CLI workflow examples
  - ⬜ `examples/workflows/cli_examples.sh`

### Documentation

- ⬜ Create README.md
  - ⬜ Project overview
  - ⬜ Installation instructions
  - ⬜ Quick start
  - ⬜ Basic usage examples
  - ⬜ Link to detailed docs
- ⬜ Create user guide
  - ⬜ `docs/user_guide.md`
  - ⬜ Config system guide
  - ⬜ Script requirements
  - ⬜ Workflow guide
  - ⬜ CLI reference
- ⬜ Create API reference
  - ⬜ `docs/api_reference.md`
  - ⬜ Document all public classes
  - ⬜ Document all public methods
  - ⬜ Include examples
- ⬜ Create tutorials
  - ⬜ `docs/tutorials/01_basic_usage.md`
  - ⬜ `docs/tutorials/02_config_generators.md`
  - ⬜ `docs/tutorials/03_workflows.md`
  - ⬜ `docs/tutorials/04_parallel_execution.md`
- ⬜ Create cookbook
  - ⬜ `docs/cookbook/hyperparameter_sweep.md`
  - ⬜ `docs/cookbook/checkpoint_resume.md`
  - ⬜ `docs/cookbook/ml_pipeline.md`
  - ⬜ `docs/cookbook/external_configs.md`

### Example Testing

- ⬜ Create `tests/integration/test_examples.py`
  - ⬜ Test all example scripts
  - ⬜ Test all example configs
  - ⬜ Test all example workflows
  - ⬜ Ensure examples work as documented

**Deliverables**:
- ✅ Comprehensive examples
- ✅ Complete documentation
- ✅ All examples tested
- ✅ Ready for users

---

## Phase 8: Testing and Quality Assurance

**Goal**: Achieve high test coverage and code quality.

**Timeline**: Week 7-8

### Unit Tests

- ⬜ Review test coverage
  - ⬜ `pytest --cov=kohakuengine --cov-report=html`
  - ⬜ Target: >90% coverage
- ⬜ Add missing tests
  - ⬜ Edge cases
  - ⬜ Error conditions
  - ⬜ Type errors
- ⬜ Test all error paths
  - ⬜ File not found
  - ⬜ Invalid configs
  - ⬜ Module import errors
  - ⬜ Entrypoint not found

### Integration Tests

- ⬜ End-to-end tests
  - ⬜ Config → Engine → Flow
  - ⬜ Python API
  - ⬜ CLI
- ⬜ Real-world scenario tests
  - ⬜ Hyperparameter sweep
  - ⬜ Multi-stage pipeline
  - ⬜ Checkpoint resume

### Code Quality

- ⬜ Format all code
  - ⬜ Run `black src/ tests/ examples/`
  - ⬜ Verify formatting
- ⬜ Lint all code
  - ⬜ Run `ruff check src/ tests/`
  - ⬜ Fix all issues
- ⬜ Type check all code
  - ⬜ Run `mypy src/`
  - ⬜ Fix all type errors
  - ⬜ Add missing type hints
- ⬜ Review docstrings
  - ⬜ All public APIs documented
  - ⬜ All modules have docstrings
  - ⬜ All classes documented
  - ⬜ All methods documented

### Performance

- ⬜ Basic performance tests
  - ⬜ Module import time
  - ⬜ Config loading time
  - ⬜ Execution overhead
- ⬜ Optimize if needed
  - ⬜ Profile bottlenecks
  - ⬜ Optimize hot paths

### CI/CD

- ⬜ Setup GitHub Actions (or similar)
  - ⬜ Run tests on push
  - ⬜ Run linting
  - ⬜ Run type checking
  - ⬜ Generate coverage report
- ⬜ Setup pre-commit hooks
  - ⬜ Format on commit
  - ⬜ Lint on commit

**Deliverables**:
- ✅ Test coverage >90%
- ✅ All tests passing
- ✅ Code formatted and linted
- ✅ Type checking passing
- ✅ CI/CD working

---

## Phase 9: Release Preparation

**Goal**: Prepare for initial release (v0.1.0).

**Timeline**: Week 8

### Package Preparation

- ⬜ Review pyproject.toml
  - ⬜ Verify dependencies
  - ⬜ Update metadata
  - ⬜ Set version to 0.1.0
- ⬜ Create CHANGELOG.md
  - ⬜ Document features
  - ⬜ Document changes
- ⬜ Create LICENSE file
  - ⬜ Apache 2.0 license
- ⬜ Review README.md
  - ⬜ Clear installation
  - ⬜ Clear examples
  - ⬜ Badges (tests, coverage, version)

### Testing on Clean Environment

- ⬜ Test installation from source
  - ⬜ Fresh venv
  - ⬜ `pip install -e .`
  - ⬜ Run examples
- ⬜ Test wheel build
  - ⬜ `python -m build`
  - ⬜ Install wheel
  - ⬜ Run examples

### Documentation Final Review

- ⬜ Proofread all docs
- ⬜ Fix typos and errors
- ⬜ Verify all links work
- ⬜ Ensure examples are up-to-date

### Release Checklist

- ⬜ All tests passing
- ⬜ Documentation complete
- ⬜ Examples working
- ⬜ CHANGELOG updated
- ⬜ Version bumped
- ⬜ Git tagged: `v0.1.0`
- ⬜ Create GitHub release
- ⬜ (Optional) Publish to PyPI

**Deliverables**:
- ✅ v0.1.0 released
- ✅ Available on GitHub
- ✅ (Optional) Available on PyPI
- ✅ Documentation published

---

## Future Phases (Post v0.1.0)

### Phase 10: Community Feedback and Iteration

- ⬜ Gather user feedback
- ⬜ Fix bugs
- ⬜ Improve documentation based on questions
- ⬜ Add requested features
- ⬜ Performance improvements

### Phase 11: Advanced Features (v0.2.0)

- ⬜ Pipeline with state passing
  - ⬜ Pass results between scripts
  - ⬜ Shared state management
- ⬜ Workflow resume/retry
  - ⬜ Save workflow state
  - ⬜ Resume from checkpoint
- ⬜ Better error handling
  - ⬜ Detailed error messages
  - ⬜ Stack trace management
- ⬜ Logging improvements
  - ⬜ Structured logging
  - ⬜ Log aggregation

### Phase 12: Distributed Execution (v0.3.0)

- ⬜ Multi-machine support
- ⬜ SLURM integration
- ⬜ Ray integration
- ⬜ Remote script execution

### Phase 13: Developer Tools (v0.4.0)

- ⬜ VS Code extension
- ⬜ Config validation schemas
- ⬜ Interactive config builder
- ⬜ Migration tools

### Phase 14: Monitoring and UI (v0.5.0)

- ⬜ Web UI for workflows
- ⬜ Real-time monitoring
- ⬜ Resource tracking
- ⬜ Experiment tracking integration

---

## Development Guidelines

### Code Style

- **Formatting**: Black (line length 100)
- **Linting**: Ruff
- **Type hints**: Required for all public APIs
- **Docstrings**: Google style

### Testing

- **Framework**: pytest
- **Coverage**: Target >90%
- **Structure**: Mirror source structure
- **Fixtures**: Centralize in conftest.py

### Git Workflow

```
main          # Stable releases only
  ↑
develop       # Integration branch
  ↑
feature/*     # Individual features
```

**Branch naming**:
- `feature/config-system`
- `feature/engine-executor`
- `bugfix/issue-123`

**Commit messages**:
```
type(scope): description

- feat: New feature
- fix: Bug fix
- docs: Documentation
- test: Tests
- refactor: Code refactoring
- style: Formatting
- chore: Maintenance
```

### Pull Request Process

1. Create feature branch from `develop`
2. Implement feature with tests
3. Ensure all tests pass
4. Format and lint code
5. Update documentation
6. Create PR to `develop`
7. Code review
8. Merge to `develop`

### Release Process

1. Merge `develop` to `main`
2. Update version in `pyproject.toml`
3. Update CHANGELOG.md
4. Create git tag: `vX.Y.Z`
5. Build package: `python -m build`
6. Publish to PyPI (optional)
7. Create GitHub release

---

## Priority Matrix

### High Priority (MVP)

These features are essential for v0.1.0:

1. ✅ Config system (base, generator, loader)
2. ✅ Engine system (executor, injector, entrypoint)
3. ✅ Sequential workflow
4. ✅ Python API
5. ✅ Basic CLI (run command)
6. ✅ Core documentation
7. ✅ Basic examples

### Medium Priority (v0.1.0)

Nice to have for initial release:

1. Parallel execution (subprocess)
2. Full CLI (all commands)
3. Advanced examples
4. Comprehensive tests

### Low Priority (Post v0.1.0)

Can be added in future versions:

1. ProcessPoolExecutor mode
2. State passing in pipelines
3. Advanced error handling
4. Performance optimization

---

## Risk Mitigation

### Technical Risks

**Risk**: Module import conflicts with __name__ == "__main__"
**Mitigation**: Careful sys.modules management, comprehensive tests

**Risk**: Subprocess communication overhead
**Mitigation**: Use temp files, optimize config serialization

**Risk**: Generator exhaustion tracking
**Mitigation**: Clear exhaustion API, good documentation

### Project Risks

**Risk**: Scope creep
**Mitigation**: Stick to MVP features, defer nice-to-haves

**Risk**: API changes during development
**Mitigation**: Design API upfront, minimal changes after Phase 5

**Risk**: Testing burden
**Mitigation**: Write tests alongside implementation, not after

---

## Success Criteria

### Phase 1-6 (MVP)

- ✅ Config system works with Python configs
- ✅ Scripts execute with global injection
- ✅ Sequential workflows work
- ✅ Python API is intuitive
- ✅ Basic CLI works
- ✅ Examples demonstrate key features

### Phase 7-9 (Release)

- ✅ Test coverage >90%
- ✅ Documentation complete
- ✅ All examples work
- ✅ Ready for external users

### Post-Release

- User adoption (GitHub stars, PyPI downloads)
- No critical bugs
- Positive user feedback
- Active development

---

## Timeline Summary

| Phase | Description | Duration | Cumulative |
|-------|-------------|----------|------------|
| 0 | Foundation | Week 1 | Week 1 |
| 1 | Config System | Weeks 1-2 | Week 2 |
| 2 | Engine System | Weeks 2-3 | Week 3 |
| 3 | Sequential Flow | Weeks 3-4 | Week 4 |
| 4 | Parallel Flow | Weeks 4-5 | Week 5 |
| 5 | Python API | Week 5 | Week 5 |
| 6 | CLI | Weeks 5-6 | Week 6 |
| 7 | Examples & Docs | Weeks 6-7 | Week 7 |
| 8 | Testing & QA | Weeks 7-8 | Week 8 |
| 9 | Release Prep | Week 8 | Week 8 |

**Total MVP Timeline**: ~8 weeks (full-time) or ~12-16 weeks (part-time)

---

## Notes

- This roadmap is flexible and can be adjusted based on feedback
- Some phases can overlap (e.g., tests written during implementation)
- CLI (Phase 6) may need to be partially implemented for Parallel (Phase 4)
- Documentation should be updated throughout, not just in Phase 7
- Consider early user feedback after Phase 6 (before full release)

---

## Getting Started

To start implementation:

1. **Review planning docs**
   - Read GOAL.md (vision)
   - Read PLAN.md (architecture)
   - Review this TODO.md (tasks)

2. **Setup environment**
   - Complete Phase 0 tasks
   - Setup development tools

3. **Start with Phase 1**
   - Implement config system first
   - Write tests alongside code
   - Create examples to validate

4. **Progress sequentially**
   - Complete each phase before moving on
   - Update this TODO as you go
   - Mark tasks as complete ✅

5. **Stay focused**
   - Stick to MVP scope
   - Don't over-engineer
   - Ship early, iterate based on feedback

---

**Last Updated**: 2025-11-19
**Version**: 0.0.1-dev
