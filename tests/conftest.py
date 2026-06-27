"""Shared pytest fixtures."""

import sys
import textwrap

import pytest


@pytest.fixture
def restore_import_state():
    """Snapshot/restore ``sys.path`` and ``sys.modules`` around a test.

    Loading a file script now (intentionally) leaves it registered in
    ``sys.modules`` under its stem and puts its directory on ``sys.path`` so
    its objects are picklable for multiprocessing. Tests that exercise that
    use this fixture to avoid leaking state into the rest of the session.
    """
    path_snapshot = list(sys.path)
    modules_snapshot = set(sys.modules)
    try:
        yield
    finally:
        sys.path[:] = path_snapshot
        for name in set(sys.modules) - modules_snapshot:
            sys.modules.pop(name, None)


@pytest.fixture
def make_script(tmp_path):
    """Factory: write a script with given source, return its Path."""

    def _factory(name: str, src: str) -> "pathlib.Path":
        path = tmp_path / name
        path.write_text(textwrap.dedent(src), encoding="utf-8")
        return path

    return _factory


@pytest.fixture
def make_config(tmp_path):
    """Factory: write a config file with given source, return its Path."""

    def _factory(name: str, src: str) -> "pathlib.Path":
        path = tmp_path / name
        path.write_text(textwrap.dedent(src), encoding="utf-8")
        return path

    return _factory


@pytest.fixture
def simple_script(make_script):
    return make_script(
        "simple.py",
        """
        result = None
        lr = 0.1

        def main():
            global result
            result = lr
            return result

        if __name__ == "__main__":
            main()
        """,
    )


@pytest.fixture
def args_script(make_script):
    return make_script(
        "args.py",
        """
        def main(x, y=10):
            return x + y

        if __name__ == "__main__":
            main(5)
        """,
    )


@pytest.fixture
def simple_config(make_config):
    return make_config(
        "config.py",
        """
        from kohakuengine.config import Config

        def config_gen():
            return Config(
                globals_dict={"lr": 0.01},
                kwargs={},
            )
        """,
    )


@pytest.fixture
def bare_config(make_config):
    return make_config(
        "bare_config.py",
        """
        lr = 0.5
        batch_size = 64
        """,
    )
