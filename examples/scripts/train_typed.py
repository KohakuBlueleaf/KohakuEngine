"""Typed overrides: annotations decide how --set / --sweep strings are parsed.

    kogine run examples/scripts/train_typed.py --strict \
        --set learning_rate=0.05 --set hidden=256,256 --set mode=eval \
        --set precision=BF16 --set warmup=none --set out_dir=runs/typed
"""

import enum
from pathlib import Path
from typing import Annotated, ClassVar, Literal

from kohakuengine import FormatArg


class Mode(enum.Enum):
    TRAIN = "train"
    EVAL = "eval"


class Precision:
    """Parsed from strings like ``bf16`` via the ``format_arg`` hook."""

    BITS: ClassVar[dict[str, int]] = {"fp32": 32, "fp16": 16, "bf16": 16}

    def __init__(self, name: str) -> None:
        if name not in self.BITS:
            raise ValueError(f"unknown precision {name!r}")
        self.name = name

    @classmethod
    def format_arg(cls, arg: str) -> "Precision":
        return cls(arg.strip().lower())

    def __repr__(self) -> str:
        return f"Precision({self.name!r})"


learning_rate: float = 1e-3
hidden: list[int] = [128]
mode: Mode = Mode.TRAIN
precision: Precision = Precision("fp32")
warmup: int | None = 100
optimizer: Literal["adam", "sgd"] = "adam"
out_dir: Annotated[Path, FormatArg(lambda s: Path(s).expanduser())] = Path("runs")


def train():
    print(f"lr={learning_rate!r} hidden={hidden!r} mode={mode} precision={precision}")
    print(f"warmup={warmup!r} optimizer={optimizer!r} out_dir={out_dir!r}")
    return {
        "lr": learning_rate,
        "hidden": hidden,
        "eval": mode is Mode.EVAL,
        "bits": Precision.BITS[precision.name],
    }


if __name__ == "__main__":
    train()
