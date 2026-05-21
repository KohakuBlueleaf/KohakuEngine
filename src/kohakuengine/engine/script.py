"""Script representation."""

import importlib.util
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kohakuengine.config.base import Config
from kohakuengine.config.generator import ConfigGenerator

_FILE_ENTRYPOINT_RE = re.compile(r"\.py:([a-zA-Z_][a-zA-Z0-9_]*)$")


@dataclass
class Script:
    """A Python script or importable module to execute."""

    path: str | Path
    config: Config | ConfigGenerator | None = None
    entrypoint: str | None = None
    is_module: bool = field(default=False, init=False)
    module_name: str | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        path_str = str(self.path)
        if self._looks_like_module(path_str):
            self._init_as_module(path_str)
        else:
            self._init_as_file(path_str)

    @staticmethod
    def _looks_like_module(path_str: str) -> bool:
        if "/" in path_str or "\\" in path_str:
            return False
        if re.search(r"\.py(:[a-zA-Z_][a-zA-Z0-9_]*)?$", path_str):
            return False
        return True

    def _init_as_module(self, path_str: str) -> None:
        if ":" in path_str:
            module_part, entry_part = path_str.rsplit(":", 1)
            if self.entrypoint is None:
                self.entrypoint = entry_part
        else:
            module_part = path_str

        spec = importlib.util.find_spec(module_part)
        if spec is None:
            raise ModuleNotFoundError(f"Module not found: {module_part}")

        self.is_module = True
        self.module_name = module_part

        if spec.origin and spec.origin != "built-in":
            self.path = Path(spec.origin)
        else:
            self.path = Path(module_part.replace(".", "/"))

    def _init_as_file(self, path_str: str) -> None:
        match = _FILE_ENTRYPOINT_RE.search(path_str)
        if match:
            entrypoint_name = match.group(1)
            script_path = path_str[: match.start() + 3]
            self.path = Path(script_path)
            if self.entrypoint is None:
                self.entrypoint = entrypoint_name
        else:
            self.path = Path(self.path)

        if not self.path.exists():
            raise FileNotFoundError(f"Script not found: {self.path}")
        if self.path.suffix != ".py":
            raise ValueError(f"Script must be .py file: {self.path}")

        self.is_module = False
        self.module_name = None

    @property
    def name(self) -> str:
        if self.is_module and self.module_name:
            return self.module_name.split(".")[-1]
        return self.path.stem

    def __repr__(self) -> str:
        config_type = type(self.config).__name__ if self.config else "None"
        if self.is_module:
            return f"Script(module={self.module_name}, config={config_type})"
        return f"Script(path={self.path}, config={config_type})"

    def _run_subprocess(
        self, config: Config | None = None
    ) -> subprocess.CompletedProcess:
        """Execute this script in a subprocess via the ``kogine`` CLI."""
        config = config if config is not None else self.config
        env = os.environ.copy()
        env.setdefault("KOGINE_WORKER_ID", "0")

        script_ref = self.module_name if self.is_module else str(self.path)

        if config is not None and not isinstance(config, ConfigGenerator):
            temp_config = _serialize_config(config)
            cmd = [
                sys.executable,
                "-m",
                "kohakuengine.cli",
                "run",
                script_ref,
                "--config",
                str(temp_config),
            ]
        else:
            cmd = [sys.executable, "-m", "kohakuengine.cli", "run", script_ref]

        proc = subprocess.Popen(cmd, env=env)
        proc.wait()
        return proc


def _serialize_config(config: Config) -> Path:
    """Write a Config to a temp ``.py`` file usable by the CLI."""
    fd, path = tempfile.mkstemp(suffix=".py", prefix="kogine_config_")
    body = (
        "from kohakuengine.config import Config\n\n"
        "def config_gen():\n"
        f"    return Config(\n"
        f"        globals_dict={config.globals_dict!r},\n"
        f"        args={config.args!r},\n"
        f"        kwargs={config.kwargs!r},\n"
        f"        metadata={config.metadata!r},\n"
        "    )\n"
    )
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(body)
    return Path(path)
