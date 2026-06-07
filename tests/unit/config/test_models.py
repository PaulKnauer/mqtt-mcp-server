"""Tests for config models."""

from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from mqtt_mcp.config.models import AuthMode, MqttConfig
from mqtt_mcp.tools.permissions import KNOWN_TOOL_NAMES


class TestMqttConfigDefaults:
    """Default config has sensible values."""

    def test_default_broker_url(self) -> None:
        config = MqttConfig()
        assert config.broker_url == "mqtt://localhost:1883"

    def test_default_topic_prefix(self) -> None:
        config = MqttConfig()
        assert config.topic_prefix == "clocks/commands"

    def test_default_qos(self) -> None:
        config = MqttConfig()
        assert config.qos == 1

    def test_default_auth_mode(self) -> None:
        config = MqttConfig()
        assert config.auth_mode == AuthMode.NONE


class TestMqttConfigValidation:
    """Config validation rules."""

    def test_broker_url_rejected_if_missing_scheme(self) -> None:
        with pytest.raises(ValidationError, match="broker_url"):
            MqttConfig(broker_url="localhost:1883")

    def test_broker_url_rejected_if_wrong_scheme(self) -> None:
        with pytest.raises(ValidationError, match="broker_url"):
            MqttConfig(broker_url="http://localhost:1883")

    def test_broker_url_accepts_mqtts(self) -> None:
        config = MqttConfig(broker_url="mqtts://broker:8883")
        assert config.broker_url == "mqtts://broker:8883"

    def test_qos_rejected_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            MqttConfig(qos=3)

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MqttConfig(invalid_field="value")  # type: ignore[arg-type]

    def test_auth_token_as_secret_str(self) -> None:
        config = MqttConfig(auth_token="my-secret-token")
        assert isinstance(config.auth_token, SecretStr)

    def test_static_auth_mode(self) -> None:
        config = MqttConfig(auth_mode=AuthMode.STATIC, auth_token="token123")
        assert config.auth_mode == AuthMode.STATIC
        assert config.auth_token is not None


class TestKnownToolNames:
    """KNOWN_TOOL_NAMES contains all expected tools."""

    def test_contains_core_tools(self) -> None:
        assert "ping" in KNOWN_TOOL_NAMES
        assert "server_info" in KNOWN_TOOL_NAMES

    def test_contains_command_tools(self) -> None:
        assert "set_alarm" in KNOWN_TOOL_NAMES
        assert "display_message" in KNOWN_TOOL_NAMES
        assert "set_brightness" in KNOWN_TOOL_NAMES

    def test_has_correct_count(self) -> None:
        assert len(KNOWN_TOOL_NAMES) == 5
