"""Tests for config preflight validation."""

from __future__ import annotations

import pytest

from mqtt_mcp.config.models import AuthMode, MqttConfig
from mqtt_mcp.config.validation import run_preflight


class TestRunPreflight:
    """Preflight validation passes with valid config."""

    def test_returns_validated_config(self) -> None:
        config = MqttConfig(broker_url="mqtt://localhost:1883")
        result = run_preflight(config)
        assert result is config
        assert result.broker_url == "mqtt://localhost:1883"

    def test_parses_auth_credentials_with_static_auth(self) -> None:
        config = MqttConfig(
            broker_url="mqtt://localhost:1883",
            auth_mode=AuthMode.STATIC,
            auth_token="my-secret",
        )
        result = run_preflight(config)
        assert result.auth_mode == AuthMode.STATIC

    def test_raises_system_exit_on_invalid_config(self) -> None:
        """Preflight exits with SystemExit when config loading fails."""
        import os

        os.environ["MQTT_MCP_BROKER_URL"] = "invalid-url"
        try:
            with pytest.raises(SystemExit):
                run_preflight()
        finally:
            os.environ.pop("MQTT_MCP_BROKER_URL", None)
            # Reset cached credentials
            import mqtt_mcp.config.validation as v

            v._credentials = None

    def test_raises_system_exit_on_invalid_auth_credentials(self) -> None:
        with pytest.raises(SystemExit):
            run_preflight(
                MqttConfig(
                    broker_url="mqtt://localhost:1883",
                    auth_mode=AuthMode.STATIC,
                )
            )

    def test_no_auth_does_not_parse_credentials(self) -> None:
        config = MqttConfig(broker_url="mqtt://localhost:1883", auth_mode=AuthMode.NONE)
        result = run_preflight(config)
        assert result.auth_mode == AuthMode.NONE
