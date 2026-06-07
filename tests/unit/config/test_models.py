"""Tests for config models."""

from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from mqtt_mcp.config.models import KNOWN_TOOL_NAMES, AuthMode, MqttConfig


class TestMqttConfigDefaults:
    """Default config has sensible values."""

    def test_default_broker_url(self) -> None:  # noqa: D102
        config = MqttConfig()
        assert config.broker_url == "mqtt://localhost:1883"

    def test_default_topic_prefix(self) -> None:  # noqa: D102
        config = MqttConfig()
        assert config.topic_prefix == "clocks/commands"

    def test_default_qos(self) -> None:  # noqa: D102
        config = MqttConfig()
        assert config.qos == 1

    def test_default_auth_mode(self) -> None:  # noqa: D102
        config = MqttConfig()
        assert config.auth_mode == AuthMode.NONE

    def test_default_retained(self) -> None:  # noqa: D102
        config = MqttConfig()
        assert config.retained is False


class TestMqttConfigValidation:
    """Config validation rules."""

    def test_broker_url_rejected_if_missing_scheme(self) -> None:  # noqa: D102
        with pytest.raises(ValidationError, match="broker_url"):
            MqttConfig(broker_url="localhost:1883")

    def test_broker_url_rejected_if_wrong_scheme(self) -> None:  # noqa: D102
        with pytest.raises(ValidationError, match="broker_url"):
            MqttConfig(broker_url="http://localhost:1883")

    def test_broker_url_accepts_mqtts(self) -> None:  # noqa: D102
        config = MqttConfig(broker_url="mqtts://broker:8883")
        assert config.broker_url == "mqtts://broker:8883"

    def test_qos_rejected_out_of_range(self) -> None:  # noqa: D102
        with pytest.raises(ValidationError):
            MqttConfig(qos=3)

    def test_extra_fields_rejected(self) -> None:  # noqa: D102
        with pytest.raises(ValidationError):
            MqttConfig(invalid_field="value")  # type: ignore[arg-type]

    def test_auth_token_as_secret_str(self) -> None:  # noqa: D102
        config = MqttConfig(auth_token="my-secret-token")
        assert isinstance(config.auth_token, SecretStr)

    def test_static_auth_mode(self) -> None:  # noqa: D102
        config = MqttConfig(auth_mode=AuthMode.STATIC, auth_token="token123")
        assert config.auth_mode == AuthMode.STATIC
        assert config.auth_token is not None


class TestMqttConfigRetained:
    """Retained flag parsing and validation."""

    def test_retained_true_parses(self) -> None:  # noqa: D102
        config = MqttConfig(retained=True)
        assert config.retained is True

    def test_retained_false_parses(self) -> None:  # noqa: D102
        config = MqttConfig(retained=False)
        assert config.retained is False

    def test_invalid_retained_raises_with_field_name(self) -> None:  # noqa: D102
        with pytest.raises(ValidationError, match="retained"):
            MqttConfig(retained="not-a-bool")  # type: ignore[arg-type]


class TestMqttConfigSecretFields:
    """Secret-aware fields stay masked."""

    def test_broker_password_is_secret_str(self) -> None:  # noqa: D102
        config = MqttConfig(broker_password="hunter2")
        assert isinstance(config.broker_password, SecretStr)
        assert "hunter2" not in repr(config.broker_password)

    def test_auth_token_is_secret_str(self) -> None:  # noqa: D102
        config = MqttConfig(auth_token="my-secret-token")
        assert isinstance(config.auth_token, SecretStr)
        assert "my-secret-token" not in repr(config.auth_token)


class TestMqttConfigFieldErrors:
    """Validation errors report the specific field name."""

    def test_broker_url_error_names_field(self) -> None:  # noqa: D102
        with pytest.raises(ValidationError, match="broker_url"):
            MqttConfig(broker_url="http://bad")

    def test_qos_error_names_field(self) -> None:  # noqa: D102
        with pytest.raises(ValidationError, match="qos"):
            MqttConfig(qos=5)

    def test_auth_mode_error_names_field(self) -> None:  # noqa: D102
        with pytest.raises(ValidationError, match="auth_mode"):
            MqttConfig(auth_mode="invalid_mode")  # type: ignore[arg-type]

    def test_retained_error_names_field(self) -> None:  # noqa: D102
        with pytest.raises(ValidationError, match="retained"):
            MqttConfig(retained="bad-value")  # type: ignore[arg-type]


class TestKnownToolNames:
    """KNOWN_TOOL_NAMES contains all expected tools."""

    def test_contains_core_tools(self) -> None:  # noqa: D102
        assert "ping" in KNOWN_TOOL_NAMES
        assert "server_info" in KNOWN_TOOL_NAMES

    def test_contains_command_tools(self) -> None:  # noqa: D102
        assert "set_alarm" in KNOWN_TOOL_NAMES
        assert "display_message" in KNOWN_TOOL_NAMES
        assert "set_brightness" in KNOWN_TOOL_NAMES

    def test_has_correct_count(self) -> None:  # noqa: D102
        assert len(KNOWN_TOOL_NAMES) == 5
