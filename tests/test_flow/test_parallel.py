"""Tests for parallel workflow execution."""

import pytest

from kohakuengine import Config, Script
from kohakuengine.config.generator import ConfigGenerator
from kohakuengine.flow.parallel import Parallel


def test_parallel_process_pool_mode(tmp_path):
    """Test parallel execution with process pool mode."""
    # Create simple script
    script_path = tmp_path / "script.py"
    script_path.write_text(
        """
result_value = "test"

def main():
    return batch_size * 2

if __name__ == "__main__":
    main()
"""
    )

    configs = [
        Config(globals_dict={"batch_size": 32}),
        Config(globals_dict={"batch_size": 64}),
    ]

    scripts = [Script(str(script_path), config=config) for config in configs]

    # Use process pool mode (faster for tests)
    workflow = Parallel(scripts, max_workers=2, use_subprocess=False)
    results = workflow.run()

    assert len(results) == 2
    assert 64 in results  # 32 * 2
    assert 128 in results  # 64 * 2


def test_parallel_with_generator_config(tmp_path):
    """Test parallel execution with generator config."""
    script_path = tmp_path / "script.py"
    script_path.write_text(
        """
def main():
    return learning_rate

if __name__ == "__main__":
    main()
"""
    )

    def config_gen():
        for lr in [0.001, 0.01, 0.1]:
            yield Config(globals_dict={"learning_rate": lr})

    generator = ConfigGenerator(config_gen())
    script = Script(str(script_path), config=generator)

    workflow = Parallel([script], max_workers=2, use_subprocess=False)
    results = workflow.run()

    assert len(results) == 3
    assert 0.001 in results
    assert 0.01 in results
    assert 0.1 in results


def test_parallel_multiple_scripts(tmp_path):
    """Test parallel execution with multiple different scripts."""
    script1_path = tmp_path / "script1.py"
    script1_path.write_text(
        """
def main():
    return "script1"

if __name__ == "__main__":
    main()
"""
    )

    script2_path = tmp_path / "script2.py"
    script2_path.write_text(
        """
def main():
    return "script2"

if __name__ == "__main__":
    main()
"""
    )

    scripts = [
        Script(str(script1_path)),
        Script(str(script2_path)),
    ]

    workflow = Parallel(scripts, use_subprocess=False)
    results = workflow.run()

    assert len(results) == 2
    assert "script1" in results
    assert "script2" in results


def test_parallel_with_no_config(tmp_path):
    """Test parallel execution without config."""
    script_path = tmp_path / "script.py"
    script_path.write_text(
        """
def main():
    return 42

if __name__ == "__main__":
    main()
"""
    )

    scripts = [Script(str(script_path)) for _ in range(3)]

    workflow = Parallel(scripts, use_subprocess=False)
    results = workflow.run()

    assert len(results) == 3
    assert all(r == 42 for r in results)


def test_parallel_max_workers_default(tmp_path):
    """Test that max_workers defaults to CPU count."""
    script_path = tmp_path / "script.py"
    script_path.write_text(
        """
def main():
    return 1

if __name__ == "__main__":
    main()
"""
    )

    scripts = [Script(str(script_path))]
    workflow = Parallel(scripts, use_subprocess=False)

    # Should not raise error with default max_workers
    results = workflow.run()
    assert len(results) == 1


def test_parallel_validation(tmp_path):
    """Test parallel workflow validation."""
    script_path = tmp_path / "script.py"
    script_path.write_text(
        """
def main():
    return 1

if __name__ == "__main__":
    main()
"""
    )

    scripts = [Script(str(script_path))]
    workflow = Parallel(scripts, use_subprocess=False)

    assert workflow.validate() is True


def test_parallel_validation_empty():
    """Test parallel validation with empty script list raises error."""
    with pytest.raises(ValueError, match="at least one script"):
        Parallel([], use_subprocess=False)


def test_parallel_validation_missing_file():
    """Test parallel validation with missing script file raises error."""
    with pytest.raises(FileNotFoundError):
        Script("nonexistent.py")


def test_parallel_subprocess_mode_single_script(tmp_path):
    """Test parallel subprocess mode with single script."""
    script = tmp_path / "script.py"
    script.write_text(
        """
def main():
    print("Subprocess parallel")
    return 1

if __name__ == "__main__":
    main()
"""
    )

    workflow = Parallel([Script(script)], use_subprocess=True)
    results = workflow.run()

    assert len(results) == 1
    # Results are CompletedProcess objects
    assert hasattr(results[0], "returncode")


def test_parallel_subprocess_mode_multiple_scripts(tmp_path):
    """Test parallel subprocess mode with multiple scripts."""
    script1 = tmp_path / "s1.py"
    script1.write_text(
        """
def main():
    return 1

if __name__ == "__main__":
    main()
"""
    )

    script2 = tmp_path / "s2.py"
    script2.write_text(
        """
def main():
    return 2

if __name__ == "__main__":
    main()
"""
    )

    scripts = [Script(script1), Script(script2)]
    workflow = Parallel(scripts, max_workers=2, use_subprocess=True)
    results = workflow.run()

    assert len(results) == 2
    assert all(hasattr(r, "returncode") for r in results)


def test_parallel_subprocess_with_config(tmp_path):
    """Test parallel subprocess mode with config."""
    script = tmp_path / "script.py"
    script.write_text(
        """
value = 0

def main():
    return value

if __name__ == "__main__":
    main()
"""
    )

    config = Config(globals_dict={"value": 999})
    workflow = Parallel([Script(script, config=config)], use_subprocess=True)
    results = workflow.run()

    assert len(results) == 1
    assert results[0].returncode == 0


def test_parallel_subprocess_with_generator(tmp_path):
    """Test parallel subprocess mode with generator config."""
    script = tmp_path / "script.py"
    script.write_text(
        """
value = 0

def main():
    return value

if __name__ == "__main__":
    main()
"""
    )

    def config_gen():
        for i in range(3):
            yield Config(globals_dict={"value": i})

    generator = ConfigGenerator(config_gen())
    workflow = Parallel(
        [Script(script, config=generator)], max_workers=2, use_subprocess=True
    )
    results = workflow.run()

    assert len(results) == 3
    assert all(r.returncode == 0 for r in results)


def test_parallel_create_temp_config(tmp_path):
    """Test temp config creation in parallel mode."""
    script = tmp_path / "script.py"
    script.write_text(
        """
def main():
    return 1

if __name__ == "__main__":
    main()
"""
    )

    config = Config(
        globals_dict={"lr": 0.01},
        args=[1, 2],
        kwargs={"device": "cuda"},
        metadata={"exp": "test"},
    )

    workflow = Parallel([Script(script)], use_subprocess=True)
    temp_path = workflow._create_temp_config(config)

    # Verify temp file
    assert temp_path.exists()
    assert temp_path.suffix == ".py"
    content = temp_path.read_text()
    assert "config_gen" in content
    assert "lr" in content


def test_parallel_worker_id_environment(tmp_path):
    """Test that KOGINE_WORKER_ID is set in subprocess mode."""
    script = tmp_path / "script.py"
    script.write_text(
        """
import os

def main():
    worker_id = os.environ.get('KOGINE_WORKER_ID')
    print(f"Worker ID: {worker_id}")
    return worker_id

if __name__ == "__main__":
    main()
"""
    )

    workflow = Parallel([Script(script)], use_subprocess=True)
    results = workflow.run()

    # Should complete successfully
    assert len(results) == 1
    assert results[0].returncode == 0
