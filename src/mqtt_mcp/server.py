"""
Application composition boundary for MQTT MCP server.

``create_server()`` is the single place where the MCP application is assembled.
The MQTT adapter is created and connected here (the composition root).
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from mqtt_mcp.adapters.mqtt_adapter import MqttAdapter
from mqtt_mcp.config.models import MqttConfig
from mqtt_mcp.config.validation import ensure_preflight_ready
from mqtt_mcp.tools import register_all

log = logging.getLogger("mqtt_mcp")


def create_server(config: MqttConfig) -> FastMCP:
    """
    Create, connect, and configure the FastMCP application.

    Instantiates the MQTT adapter and connects it to the broker
    before registering any tools. This is the single composition
    root — the adapter is injected into ``register_all()``.

    Args:
        config: Validated server configuration.

    Returns:
        A configured FastMCP instance with all tools registered and
        the MQTT adapter connected.

    Raises:
        DispatchError: if MQTT broker connection fails.

    """
    adapter = MqttAdapter()
    adapter.connect(
        broker_url=config.broker_url,
        username=config.broker_username,
        password=config.broker_password.get_secret_value() if config.broker_password else None,
    )
    ensure_preflight_ready(config, adapter)

    app = FastMCP("mqtt-mcp")

    register_all(app, config, adapter)

    log.info(
        "MQTT MCP server created broker=%s prefix=%s qos=%s auth=%s",
        config.broker_url,
        config.topic_prefix,
        config.qos,
        config.auth_mode,
    )
    return app
