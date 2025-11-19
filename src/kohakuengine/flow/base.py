"""Base classes for workflow orchestration."""

from abc import ABC, abstractmethod
from typing import Any

from kohakuengine.engine.script import Script


class Workflow(ABC):
    """
    Abstract base class for workflows.

    A workflow orchestrates execution of one or more scripts.
    """

    @abstractmethod
    def run(self) -> Any:
        """
        Execute the workflow.

        Returns:
            Workflow result (implementation-specific)
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate workflow configuration.

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        pass


class ScriptWorkflow(Workflow):
    """Base class for workflows that execute scripts."""

    def __init__(self, scripts: list[Script]):
        """
        Initialize workflow with scripts.

        Args:
            scripts: List of scripts to execute

        Raises:
            ValueError: If scripts list is empty or invalid
        """
        if not scripts:
            raise ValueError("Workflow must have at least one script")

        self.scripts = scripts
        self.validate()

    def validate(self) -> bool:
        """
        Validate all scripts exist.

        Returns:
            True if valid

        Raises:
            ValueError: If any script is invalid
        """
        for script in self.scripts:
            if not script.path.exists():
                raise ValueError(f"Script not found: {script.path}")
        return True
