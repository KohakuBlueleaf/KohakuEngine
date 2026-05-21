"""Tests for Sequential workflow."""

import pytest

from kohakuengine import Config, ConfigGenerator, Script, Sequential


def test_sequential_basic(simple_script):
    cfg = Config(globals_dict={"lr": 0.3})
    s = Script(str(simple_script), config=cfg)
    results = Sequential([s]).run()
    assert results == [0.3]


def test_sequential_multiple_scripts(make_script):
    s1 = make_script("a.py", "def main(): return 'a'\nif __name__=='__main__':main()\n")
    s2 = make_script("b.py", "def main(): return 'b'\nif __name__=='__main__':main()\n")
    results = Sequential([Script(str(s1)), Script(str(s2))]).run()
    assert results == ["a", "b"]


def test_sequential_with_generator(make_script):
    s = make_script(
        "a.py", "def main(): return iteration\nif __name__=='__main__':main()\n"
    )
    gen = ConfigGenerator(
        iter([Config(globals_dict={"iteration": i}) for i in range(3)])
    )
    script = Script(str(s), config=gen)
    results = Sequential([script]).run()
    assert results == [0, 1, 2]


def test_sequential_requires_scripts():
    with pytest.raises(ValueError, match="at least one"):
        Sequential([])


def test_sequential_iterative_type_error(make_script):
    # Internal _run_iterative requires ConfigGenerator
    s = make_script("a.py", "def main(): return 1\nif __name__=='__main__':main()\n")
    script = Script(str(s))
    seq = Sequential([script])
    with pytest.raises(TypeError):
        seq._run_iterative(script)


def test_sequential_subprocess_mode(simple_script):
    cfg = Config(globals_dict={"lr": 0.42})
    s = Script(str(simple_script), config=cfg)
    workflow = Sequential([s], use_subprocess=True)
    results = workflow.run()
    # Subprocess mode returns CompletedProcess-like objects
    assert all(r.returncode == 0 for r in results)
