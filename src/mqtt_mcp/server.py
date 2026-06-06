"""Application composition boundary for MQTT MCP server.

``create_server()`` is the single place where the MCP application is assembled.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from mqtt_mcp.config.models import MqttConfig
from mqtt_mcp.tools import register_all

log = logging.getLogger("mqtt_mcp")


def create_server(config: MqttConfig) -> FastMCP:
    """Create and configure the FastMCP application.

    Args:
        config: Validated server configuration.

    Returns:
        A configured FastMCP instance with all tools registered.
    """
    app = FastMCP("mqtt-mcp")

    register_all(app, config)

    log.info(
        "MQTT MCP server created broker=%s prefix=%s qos=%s auth=%s",
        config.broker_url,
        config.topic_prefix,
        config.qos,
        config.auth_mode,
    )
    return app
