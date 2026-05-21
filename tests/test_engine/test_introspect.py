"""Tests for kohakuengine.engine.introspect."""

import pytest

from kohakuengine import introspect


def test_introspect_script_without_cell(make_script):
    p = make_script(
        "s.py",
        """
        lr = 0.01
        bs = 32
        def main():
            return lr * bs
        if __name__ == '__main__':
            main()
        """,
    )
    defaults = introspect(p)
    assert defaults["lr"] == 0.01
    assert defaults["bs"] == 32
    # The locally-defined `main` callable is captured under the new filter
    assert "main" in defaults


def test_introspect_skips_imports(make_script):
    p = make_script(
        "s.py",
        """
        import math
        threshold = 0.5
        sq = math.sqrt
        if __name__ == '__main__':
            pass
        """,
    )
    defaults = introspect(p)
    assert defaults["threshold"] == 0.5
    assert "math" not in defaults
    # sq aliases an imported callable -> __module__='math' -> not captured
    assert "sq" not in defaults


def test_introspect_with_cell_only_evaluates_cell(make_script):
    # Code BELOW the cell must NOT run -- we use a SystemExit sentinel.
    p = make_script(
        "s.py",
        """
        # %% kogine:config
        lr = 0.01
        # %% kogine:script
        import sys
        sys.exit('SHOULD NOT RUN')
        """,
    )
    defaults = introspect(p)
    assert defaults == {"lr": 0.01}


def test_introspect_missing_file():
    with pytest.raises(FileNotFoundError):
        introspect("/no/such/file.py")


def test_introspect_does_not_fire_main_guard(make_script):
    p = make_script(
        "s.py",
        """
        marker = 1
        def main():
            raise SystemExit('SHOULD NOT RUN')
        if __name__ == '__main__':
            main()
        """,
    )
    defaults = introspect(p)
    assert defaults["marker"] == 1
