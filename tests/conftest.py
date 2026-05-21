"""Shared pytest fixtures."""

import textwrap

import pytest


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
