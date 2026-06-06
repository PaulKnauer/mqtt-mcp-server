"""MCP tool registration — the single assembly point for all tools.

``register_all()`` instantiates adapters and services and wires them
into MCP tool handlers.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from mqtt_mcp.adapters.mqtt_adapter import MqttAdapter
from mqtt_mcp.config.models import MqttConfig
from mqtt_mcp.services.clock_service import ClockService
from mqtt_mcp.tools.commands import register_commands
from mqtt_mcp.tools.setup_support import register_setup_support

logger = logging.getLogger("mqtt_mcp")


def register_all(app: FastMCP, config: MqttConfig) -> None:
    """Create all adapters, services, and register all MCP tools.

    Args:
        app: The FastMCP application instance.
        config: The validated server configuration.
    """
    adapter = MqttAdapter()
    clock_service = ClockService(adapter, config)

    register_setup_support(app, config)
    register_commands(app, config, clock_service)

    logger.info(
        "All tools registered for broker=%s prefix=%s",
        config.broker_url,
        config.topic_prefix,
    )
