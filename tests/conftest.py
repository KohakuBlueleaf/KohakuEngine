"""Pytest fixtures for KohakuEngine tests."""

import pytest


@pytest.fixture
def simple_script(tmp_path):
    """Create a simple test script."""
    script = tmp_path / "simple_script.py"
    script.write_text(
        """
result = None

def main():
    global result
    result = "success"
    return result

if __name__ == "__main__":
    main()
"""
    )
    return script


@pytest.fixture
def script_with_globals(tmp_path):
    """Create script that uses global variables."""
    script = tmp_path / "globals_script.py"
    script.write_text(
        """
learning_rate = 0.001
batch_size = 32

def main():
    return learning_rate * batch_size

if __name__ == "__main__":
    main()
"""
    )
    return script


@pytest.fixture
def script_with_args(tmp_path):
    """Create script that accepts args/kwargs."""
    script = tmp_path / "args_script.py"
    script.write_text(
        """
def main(x, y=10):
    return x + y

if __name__ == "__main__":
    main(5)
"""
    )
    return script


@pytest.fixture
def simple_config_file(tmp_path):
    """Create a simple config file."""
    config = tmp_path / "simple_config.py"
    config.write_text(
        """
from kohakuengine.config import Config

def config_gen():
    return Config(
        globals_dict={'learning_rate': 0.01, 'batch_size': 64},
        kwargs={'device': 'cuda'}
    )
"""
    )
    return config


@pytest.fixture
def generator_config_file(tmp_path):
    """Create a generator config file."""
    config = tmp_path / "gen_config.py"
    config.write_text(
        """
from kohakuengine.config import Config

def config_gen():
    for i in range(3):
        yield Config(
            globals_dict={'iteration': i},
            kwargs={'iter_num': i}
        )
"""
    )
    return config
