"""Sensible defaults for MQTT MCP configuration."""

from __future__ import annotations

DEFAULTS: dict[str, object] = {
    "broker_url": "mqtt://localhost:1883",
    "broker_username": None,
    "broker_password": None,
    "topic_prefix": "clocks/commands",
    "qos": 1,
    "auth_token": None,
    "auth_credentials": None,
    "auth_mode": "none",
    "log_level": "INFO",
}
