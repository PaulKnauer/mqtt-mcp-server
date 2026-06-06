"""Configuration loading and normalization for MQTT MCP server.

Reads `.env` and environment variables, applies defaults, and produces a
validated MqttConfig. Independent of transports and MQTT operations.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from mqtt_mcp.config.defaults import DEFAULTS
from mqtt_mcp.config.models import MqttConfig

# Maps MQTT_MCP_* env vars to MqttConfig field names.
_ENV_MAP: dict[str, str] = {
    "MQTT_MCP_BROKER_URL": "broker_url",
    "MQTT_MCP_BROKER_USERNAME": "broker_username",
    "MQTT_MCP_BROKER_PASSWORD": "broker_password",
    "MQTT_MCP_TOPIC_PREFIX": "topic_prefix",
    "MQTT_MCP_QOS": "qos",
    "MQTT_MCP_AUTH_MODE": "auth_mode",
    "MQTT_MCP_AUTH_TOKEN": "auth_token",
    "MQTT_MCP_AUTH_CREDENTIALS": "auth_credentials",
    "MQTT_MCP_LOG_LEVEL": "log_level",
}


def load_config(overrides: dict[str, Any] | None = None) -> MqttConfig:
    """Load and validate configuration.

    Resolution order (last wins):
      1. Hardcoded defaults
      2. Project-local ``.env`` file (if present)
      3. MQTT_MCP_* environment variables
      4. ``overrides`` dict (programmatic or test use)
    """
    raw: dict[str, Any] = dict(DEFAULTS)

    raw.update(_read_dotenv(Path.cwd() / ".env"))

    for env_key, field_name in _ENV_MAP.items():
        value = os.environ.get(env_key)
        if value is not None and value.strip() != "":
            raw[field_name] = value.strip()

    if overrides:
        raw.update(overrides)

    return MqttConfig.model_validate(raw)


def _read_dotenv(path: Path) -> dict[str, Any]:
    """Read supported MQTT_MCP_* settings from a project-local `.env` file."""
    if not path.is_file():
        return {}

    raw_dotenv = dotenv_values(path)
    return {
        field_name: value
        for env_key, field_name in _ENV_MAP.items()
        if (value := raw_dotenv.get(env_key)) is not None
    }
