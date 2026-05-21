"""Tests for kohakuengine.config.types (Protocol smoke tests)."""

from kohakuengine.config import Config
from kohakuengine.config.types import Configurable, ConfigProvider


def test_config_provider_protocol():
    class Provider:
        def get_config(self):
            return Config()

    p: ConfigProvider = Provider()
    assert isinstance(p.get_config(), Config)


def test_configurable_protocol():
    class Target:
        applied = False

        def apply_config(self, config):
            self.applied = True

    c: Configurable = Target()
    c.apply_config(Config())
    assert c.applied is True
