"""Config generator wrapper for iterative configurations."""

from typing import Iterator

from kohakuengine.config.base import Config


class ConfigGenerator:
    """
    Wrapper for config generators.

    Supports both:
    1. Generator functions (yield)
    2. Iterator protocol (__iter__, __next__)

    Examples:
        >>> def my_config_gen():
        ...     for lr in [0.001, 0.01, 0.1]:
        ...         yield Config(globals_dict={'learning_rate': lr})
        >>> gen = ConfigGenerator(my_config_gen())
        >>> config1 = next(gen)
        >>> config1.globals_dict['learning_rate']
        0.001
    """

    def __init__(self, generator: Iterator[Config]):
        """
        Initialize config generator.

        Args:
            generator: Generator or iterator yielding Config objects
        """
        self._generator = generator
        self._exhausted = False

    def __iter__(self) -> Iterator[Config]:
        """Return iterator."""
        return self

    def __next__(self) -> Config:
        """
        Get next config.

        Returns:
            Next Config object

        Raises:
            StopIteration: When generator is exhausted
            TypeError: If generator yields non-Config object
        """
        if self._exhausted:
            raise StopIteration("Config generator exhausted")

        try:
            config = next(self._generator)
            if not isinstance(config, Config):
                raise TypeError(
                    f"Generator must yield Config objects, got {type(config).__name__}"
                )
            return config
        except StopIteration:
            self._exhausted = True
            raise

    @property
    def exhausted(self) -> bool:
        """Check if generator is exhausted."""
        return self._exhausted
