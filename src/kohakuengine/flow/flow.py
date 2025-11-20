"""Unified Flow class for workflow orchestration."""

from typing import Any

from kohakuengine.engine.script import Script
from kohakuengine.flow.parallel import Parallel
from kohakuengine.flow.sequential import Sequential


class Flow:
    """
    Unified workflow orchestration class.

    Supports different execution modes:
    - 'sequential': Execute scripts one after another
    - 'parallel': Execute scripts in parallel using subprocesses

    Examples:
        >>> # Sequential execution
        >>> flow = Flow([script1, script2, script3], mode='sequential')
        >>> results = flow.run()

        >>> # Parallel execution
        >>> flow = Flow([script1, script2, script3], mode='parallel', max_workers=4)
        >>> results = flow.run()

        >>> # Custom executor
        >>> from kohakuengine.flow.parallel import Parallel
        >>> flow = Flow([script1, script2], executor_class=Parallel, max_workers=2)
        >>> results = flow.run()
    """

    def __init__(
        self,
        scripts: list[Script],
        mode: str = "sequential",
        executor_class: type | None = None,
        max_workers: int | None = None,
        use_subprocess: bool | None = None,
    ):
        """
        Initialize workflow.

        Args:
            scripts: List of scripts to execute
            mode: Execution mode ('sequential' or 'parallel')
            executor_class: Custom executor class (overrides mode)
            max_workers: Maximum parallel workers (for parallel mode)
            use_subprocess: Use subprocess for parallel (default: True)

        Raises:
            ValueError: If mode is invalid
        """
        self.scripts = scripts
        self.mode = mode
        self.max_workers = max_workers

        # Set default use_subprocess based on mode if not specified
        if use_subprocess is None:
            use_subprocess = True if mode == "parallel" else False
        self.use_subprocess = use_subprocess

        # Create executor
        if executor_class is not None:
            # Custom executor class provided
            if mode == "parallel" or executor_class == Parallel:
                self._executor = executor_class(
                    scripts, max_workers=max_workers, use_subprocess=use_subprocess
                )
            elif executor_class == Sequential:
                self._executor = executor_class(scripts, use_subprocess=use_subprocess)
            else:
                self._executor = executor_class(scripts)
        else:
            # Use mode to select executor
            match mode:
                case "sequential":
                    self._executor = Sequential(scripts, use_subprocess=use_subprocess)
                case "parallel":
                    self._executor = Parallel(
                        scripts, max_workers=max_workers, use_subprocess=use_subprocess
                    )
                case _:
                    raise ValueError(
                        f"Invalid mode: {mode}. Must be 'sequential' or 'parallel'"
                    )

    def run(self) -> list[Any]:
        """
        Execute the workflow.

        Returns:
            List of results from script executions

        Examples:
            >>> flow = Flow([script1, script2], mode='sequential')
            >>> results = flow.run()
            >>> len(results)
            2
        """
        return self._executor.run()

    def validate(self) -> bool:
        """
        Validate workflow configuration.

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        return self._executor.validate()

    def __repr__(self) -> str:
        return f"Flow(scripts={len(self.scripts)}, mode={self.mode})"
