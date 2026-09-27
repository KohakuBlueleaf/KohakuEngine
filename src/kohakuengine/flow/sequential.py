"""Sequential workflow execution."""

import os
import subprocess
from typing import Any

from kohakuengine.config.base import Config
from kohakuengine.config.generator import ConfigGenerator
from kohakuengine.engine.executor import ScriptExecutor
from kohakuengine.engine.script import Script
from kohakuengine.flow.base import ScriptWorkflow


class Sequential(ScriptWorkflow):
    """
    Execute scripts sequentially.

    Supports:
    - Static configs (Config)
    - Iterative configs (ConfigGenerator)
    - Multiple scripts with independent configs
    - Subprocess mode for asyncio scripts

    Examples:
        >>> scripts = [
        ...     Script('preprocess.py', config=Config(globals_dict={'input': 'data.csv'})),
        ...     Script('train.py', config=Config(globals_dict={'epochs': 10}))
        ... ]
        >>> workflow = Sequential(scripts)
        >>> results = workflow.run()

        >>> # Use subprocess mode for asyncio scripts
        >>> workflow = Sequential(scripts, use_subprocess=True)
        >>> results = workflow.run()
    """

    def __init__(self, scripts: list[Script], use_subprocess: bool = False):
        """
        Initialize sequential workflow.

        Args:
            scripts: List of scripts to execute
            use_subprocess: If True, run each script in a subprocess
        """
        super().__init__(scripts)
        self.use_subprocess = use_subprocess

    def run(self) -> list[Any]:
        """
        Execute scripts in sequence.

        For scripts with ConfigGenerator:
        1. Get next config
        2. Execute script with config
        3. Repeat until generator exhausted

        Returns:
            List of results from each script execution
        """
        results = []

        for script in self.scripts:
            if isinstance(script.config, ConfigGenerator):
                # Iterative execution
                script_results = self._run_iterative(script)
                results.extend(script_results)
            else:
                # Single execution
                result = self._run_once(script, script.config)
                results.append(result)

        return results

    def _run_once(self, script: Script, config: Config | None) -> Any:
        """
        Execute script once with config.

        Args:
            script: Script to execute
            config: Configuration to apply

        Returns:
            Script execution result
        """
        if self.use_subprocess:
            return self._run_subprocess(script, config)
        executor = ScriptExecutor(script)
        return executor.execute(config)

    def _run_subprocess(
        self, script: Script, config: Config | None
    ) -> subprocess.CompletedProcess:
        """
        Execute script in subprocess.

        Args:
            script: Script to execute
            config: Configuration to apply

        Returns:
            CompletedProcess object
        """
        env = os.environ.copy()
        env["KOGINE_WORKER_ID"] = "0"

        cmd = script.cli_command(config)
        proc = subprocess.Popen(cmd, env=env)
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(
                f"Subprocess failed with exit code {proc.returncode}: {' '.join(cmd)}"
            )
        return proc

    def _run_iterative(self, script: Script) -> list[Any]:
        """
        Execute script iteratively with generator config.

        Args:
            script: Script with ConfigGenerator

        Returns:
            List of results from each iteration

        Raises:
            TypeError: If script.config is not ConfigGenerator
        """
        results = []
        config_gen = script.config

        if not isinstance(config_gen, ConfigGenerator):
            raise TypeError(
                f"Expected ConfigGenerator, got {type(config_gen).__name__}"
            )

        for config in config_gen:
            result = self._run_once(script, config)
            results.append(result)

        return results


class Pipeline(Sequential):
    """
    Sequential workflow with state passing.

    Each script can access results from previous scripts.
    (Future enhancement - for now, alias to Sequential)

    Examples:
        >>> pipeline = Pipeline([script1, script2, script3])
        >>> results = pipeline.run()
    """

    pass
