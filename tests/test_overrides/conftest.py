"""Scripts whose own code asserts the types it receives."""

import pytest

TYPED_SCRIPT = """
import enum
from pathlib import Path
from typing import Annotated, Literal, Optional

from kohakuengine import FormatArg


class Mode(enum.Enum):
    TRAIN = "train"
    EVAL = "eval"


class Dtype:
    def __init__(self, name):
        self.name = name

    @classmethod
    def format_arg(cls, arg):
        return cls(arg.upper())


lr: float = 1
steps: Optional[int] = None
dims: list[int] = [32]
mode: Mode = Mode.TRAIN
out: Path = Path("runs")
dtype: Dtype = Dtype("FP32")
scale: Annotated[float, FormatArg(lambda s: float(s) / 100)] = 1.0
opt: Literal["adam", "sgd"] = "adam"
tags = {"a": 1}
resume = None
epochs = 10


def snapshot():
    assert type(lr) is float or lr == 1, lr
    assert steps is None or type(steps) is int, steps
    assert all(type(d) is int for d in dims), dims
    assert type(mode) is Mode, mode
    assert isinstance(out, Path), out
    assert type(dtype) is Dtype, dtype
    assert type(scale) is float, scale
    assert type(epochs) is int, epochs
    assert all(type(v) is int for v in tags.values()), tags
    return {
        "lr": lr,
        "steps": steps,
        "dims": dims,
        "mode": mode.name,
        "out": out.as_posix(),
        "dtype": dtype.name,
        "scale": scale,
        "opt": opt,
        "tags": tags,
        "resume": resume,
        "epochs": epochs,
    }


def main():
    return snapshot()


def expect_eval():
    assert mode is Mode.EVAL, mode
    assert dtype.name == "BF16", dtype.name
    return snapshot()


if __name__ == "__main__":
    main()
"""

CELL_SCRIPT = """
import enum
from pathlib import Path


class Mode(enum.Enum):
    TRAIN = 1
    EVAL = 2


# %% kogine:config
lr: float = 1
steps: int
out: Path = Path("runs")
mode: Mode = Mode.TRAIN
width = 8
# %% kogine:script
tail: float = 1


def main():
    return {
        "lr": lr,
        "steps": steps,
        "out": out,
        "mode": mode.name,
        "width": width,
        "tail": tail,
    }
"""


@pytest.fixture
def typed_script(make_script, restore_import_state):
    return make_script("typed_script.py", TYPED_SCRIPT)


@pytest.fixture
def cell_script(make_script, restore_import_state):
    return make_script("typed_cell.py", CELL_SCRIPT)


EVAL_SET = {
    "lr": "0.5",
    "steps": "100",
    "dims": "64,128",
    "mode": "eval",
    "out": "ckpt/a",
    "dtype": "bf16",
    "scale": "50",
    "opt": "sgd",
    "tags": "a=2,b=3",
    "resume": "last.pt",
    "epochs": "3",
}

EVAL_EXPECTED = {
    "lr": 0.5,
    "steps": 100,
    "dims": [64, 128],
    "mode": "EVAL",
    "out": "ckpt/a",
    "dtype": "BF16",
    "scale": 0.5,
    "opt": "sgd",
    "tags": {"a": 2, "b": 3},
    "resume": "last.pt",
    "epochs": 3,
}


@pytest.fixture
def eval_set():
    return dict(EVAL_SET)


@pytest.fixture
def eval_expected():
    return dict(EVAL_EXPECTED)
