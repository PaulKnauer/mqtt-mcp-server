"""Shared test fixtures."""

from __future__ import annotations

import pytest

from mqtt_mcp.config.models import AuthMode, MqttConfig


@pytest.fixture
def minimal_config() -> MqttConfig:
    """A minimal valid config for unit tests."""  # noqa: D401
    return MqttConfig(
        broker_url="mqtt://localhost:1883",
    )


@pytest.fixture
def config_with_auth() -> MqttConfig:
    """Config with static bearer auth enabled."""
    return MqttConfig(
        broker_url="mqtt://localhost:1883",
        auth_mode=AuthMode.STATIC,
        auth_credentials="admin|secret123|*",
    )
