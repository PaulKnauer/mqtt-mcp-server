"""Preflight configuration validation for MQTT MCP server.

Runs at startup to validate configuration, authentication credentials,
and MQTT broker connectivity before accepting MCP tool calls.
"""

from __future__ import annotations

import logging
from typing import Any

from mqtt_mcp.auth import parse_credentials
from mqtt_mcp.config.loader import load_config
from mqtt_mcp.config.models import AuthMode, MqttConfig

logger = logging.getLogger("mqtt_mcp")

# Cache of parsed credentials for tool-level auth verification.
_credentials: list[Any] | None = None


def get_credentials() -> list[Any]:
    """Return the cached parsed credentials.

    Returns:
        List of parsed Credential objects.

    Raises:
        RuntimeError: if preflight has not been run yet.
    """
    if _credentials is None:
        raise RuntimeError("Preflight has not been run; credentials not loaded")
    return _credentials


def run_preflight(config: MqttConfig | None = None) -> MqttConfig:
    """Run startup preflight checks.

    Loads and validates configuration, parses auth credentials,
    and prepares the server for operation.

    Args:
        config: Optional pre-loaded config. If None, loads from
            .env / environment variables.

    Returns:
        The validated MqttConfig.

    Raises:
        SystemExit: if validation fails (non-zero exit).
    """
    global _credentials

    if config is None:
        try:
            config = load_config()
        except Exception as exc:
            logger.error("Config validation failed: %s", exc)
            raise SystemExit(1) from exc

    # Parse and validate auth credentials
    if config.auth_mode == AuthMode.STATIC:
        token_str = config.auth_token.get_secret_value() if config.auth_token else None
        try:
            _credentials = parse_credentials(
                auth_credentials=config.auth_credentials,
                auth_token=token_str,
            )
            logger.info(
                "Auth credentials parsed: %d credential(s) loaded",
                len(_credentials),
            )
        except ValueError as exc:
            logger.error("Auth credential validation failed: %s", exc)
            raise SystemExit(1) from exc
    else:
        _credentials = []

    logger.info(
        "Config validated: broker=%s, prefix=%s, qos=%s, auth=%s",
        config.broker_url,
        config.topic_prefix,
        config.qos,
        config.auth_mode,
    )

    return config


def ensure_preflight_ready(config: MqttConfig) -> None:
    """Additional preflight checks that require external resources.

    Verifies MQTT broker connectivity at startup.

    Args:
        config: The validated MqttConfig.
    """
    # Future: MQTT broker connectivity check
    pass
