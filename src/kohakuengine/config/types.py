"""Type definitions and protocols for the config system."""

from typing import Iterator, Protocol

from kohakuengine.config.base import Config


class ConfigProvider(Protocol):
    """Protocol for objects that provide configs."""

    def get_config(self) -> Config | Iterator[Config]:
        """Get config or config iterator."""
        ...


class Configurable(Protocol):
    """Protocol for objects that accept configs."""

    def apply_config(self, config: Config) -> None:
        """Apply configuration."""
        ...
