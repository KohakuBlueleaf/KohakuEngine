"""Parallel workflow execution using subprocesses."""

import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from kohakuengine.config.base import Config
from kohakuengine.config.generator import ConfigGenerator
from kohakuengine.engine.executor import ScriptExecutor
from kohakuengine.engine.script import Script
from kohakuengine.flow.base import ScriptWorkflow


class Parallel(ScriptWorkflow):
    """
    Execute scripts in parallel using subprocesses.

    Each script runs in isolated subprocess with __name__ == '__main__'.
    Ensures true isolation (no shared state).

    Examples:
        >>> scripts = [Script('train.py', config=config) for config in configs]
        >>> workflow = Parallel(scripts, max_workers=4)
        >>> results = workflow.run()
    """

    def __init__(
        self,
        scripts: list[Script],
        max_workers: int | None = None,
        use_subprocess: bool = True,
    ):
        """
        Initialize parallel workflow.

        Args:
            scripts: List of scripts to execute
            max_workers: Maximum parallel workers (default: CPU count)
            use_subprocess: If True, use subprocess; if False, use ProcessPoolExecutor
        """
        super().__init__(scripts)
        self.max_workers = max_workers
        self.use_subprocess = use_subprocess

    def run(self) -> list[Any]:
        """
        Execute scripts in parallel.

        Returns:
            List of results (order not guaranteed)
        """
        if self.use_subprocess:
            return self._run_subprocess()
        else:
            return self._run_process_pool()

    def _run_subprocess(self) -> list[subprocess.CompletedProcess]:
        """
        Execute using subprocess.Popen.

        Each script runs as: kogine run script.py --config temp_config.py
        Config is passed via temporary file.

        Returns:
            List of CompletedProcess objects
        """
        # Collect all tasks to execute
        tasks = []
        worker_id = 0

        for script in self.scripts:
            if isinstance(script.config, ConfigGenerator):
                # For generators, we need to iterate
                for config in script.config:
                    tasks.append((script, config, worker_id))
                    worker_id += 1
            else:
                tasks.append((script, script.config, worker_id))
                worker_id += 1

        def run_task(task):
            script, config, wid = task
            proc = self._spawn_subprocess(script, config, wid)
            proc.wait()
            return proc

        # Use ThreadPoolExecutor to limit concurrent subprocesses
        import os

        max_workers = self.max_workers or os.cpu_count() or 1

        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(run_task, task) for task in tasks]
            for future in as_completed(futures):
                results.append(future.result())

        return results

    def _spawn_subprocess(
        self, script: Script, config: Config | None, worker_id: int
    ) -> subprocess.Popen:
        """
        Spawn subprocess for script execution.

        Strategy:
        1. Create temporary config file
        2. Launch: kogine run script.py --config temp_config.py
        3. Set KOGINE_WORKER_ID environment variable
        4. Return process handle

        Args:
            script: Script to execute
            config: Configuration to apply
            worker_id: Worker ID for this process

        Returns:
            Popen process handle
        """
        import os

        # Set up environment with worker ID
        env = os.environ.copy()
        env["KOGINE_WORKER_ID"] = str(worker_id)

        # Create temp config file
        if config:
            temp_config = self._create_temp_config(config)
            cmd = [
                sys.executable,
                "-m",
                "kohakuengine.cli",
                "run",
                str(script.path),
                "--config",
                str(temp_config),
            ]
        else:
            cmd = [sys.executable, "-m", "kohakuengine.cli", "run", str(script.path)]

        return subprocess.Popen(cmd, env=env)

    def _create_temp_config(self, config: Config) -> Path:
        """
        Create temporary Python config file.

        Args:
            config: Config to serialize

        Returns:
            Path to temporary config file
        """
        # Create temp file
        fd, path = tempfile.mkstemp(suffix=".py", prefix="kogine_config_")

        # Write config
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                f"""
from kohakuengine.config import Config

def config_gen():
    return Config(
        globals_dict={config.globals_dict!r},
        args={config.args!r},
        kwargs={config.kwargs!r},
        metadata={config.metadata!r}
    )
"""
            )

        return Path(path)

    def _run_process_pool(self) -> list[Any]:
        """
        Execute using ProcessPoolExecutor.

        Note: This runs scripts in worker processes, not as __main__.
        Use subprocess mode for true __main__ execution.

        Returns:
            List of execution results
        """

        def execute_script(script: Script, config: Config | None) -> Any:
            executor = ScriptExecutor(script)
            return executor.execute(config)

        results = []

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []

            for script in self.scripts:
                if isinstance(script.config, ConfigGenerator):
                    for config in script.config:
                        future = executor.submit(execute_script, script, config)
                        futures.append(future)
                else:
                    future = executor.submit(execute_script, script, script.config)
                    futures.append(future)

            for future in as_completed(futures):
                results.append(future.result())

        return results
